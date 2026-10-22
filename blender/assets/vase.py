"""Heavy hand-blown smoked-glass vase, empty. A throwable pickup (item "vase").

Lathed from a hand-made profile: a thick solid glass base (puck), then a wall of
real thickness (outer surface, rounded lip, inner surface) with shallow vertical
flutes that fade out on the shoulder. Alpha-blended glass only.

Origin: centre of the underside, sitting on z = 0. Units are metres.
"""
import importlib
import math
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "Vase"

P = dict(
    name=NAME,
    segments=24,            # around the vase (multiple of flutes; 4 per flute keeps them round)
    flutes=6,
    flute_depth=0.0090,     # groove depth on the body
    flute_z=(0.032, 0.20),  # flutes fade in above the base and out over the shoulder
    base_h=0.020,           # solid glass base height
    wall=0.0045,            # wall thickness
    lip_top=0.280,          # overall height
    outer_rings=12,         # rings on the outer wall (above the base)
    inner_rings=4,          # rings on the inner wall (seen dimly through the glass)
    # outer profile control points (z, r): foot, swelling body, shoulder, neck, flared lip
    profile=[(0.020, 0.0505), (0.050, 0.0585), (0.095, 0.0650), (0.135, 0.0655),
             (0.170, 0.0560), (0.199, 0.0385), (0.222, 0.0285), (0.248, 0.0262),
             (0.268, 0.0295), (0.2775, 0.0345)],
    tint=(0.42, 0.40, 0.37),
    item="vase",
    label="Glass vase",
)


# ------------------------------------------------------------------ profile maths

def _catmull(pts, per=24):
    """Catmull-Rom spline through pts (list of (z, r)), returns dense polyline."""
    pts = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t +
                                    (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 +
                                    (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(pts[-2])
    return out


def _resample(poly, n, bend=0.09):
    """n points along a polyline of (z, r), spaced evenly in arc length plus `bend`
    metres per radian of turning, so tight curves (shoulder, lip flare) get more rings."""
    d = [0.0]
    for i in range(1, len(poly)):
        a, b = poly[i - 1], poly[i]
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        turn = 0.0
        if 1 < i < len(poly) - 1:
            c = poly[i + 1]
            a1 = math.atan2(b[1] - a[1], b[0] - a[0])
            a2 = math.atan2(c[1] - b[1], c[0] - b[0])
            turn = abs((a2 - a1 + math.pi) % (2 * math.pi) - math.pi)
        d.append(d[-1] + seg + bend * turn)
    total = d[-1]
    out, j = [], 0
    for i in range(n):
        s = total * i / (n - 1)
        while j < len(d) - 2 and d[j + 1] < s:
            j += 1
        seg = max(d[j + 1] - d[j], 1e-12)
        t = (s - d[j]) / seg
        out.append((poly[j][0] + (poly[j + 1][0] - poly[j][0]) * t,
                    poly[j][1] + (poly[j + 1][1] - poly[j][1]) * t))
    return out


def _normals(poly):
    """Outward (z, r) normals of a (z, r) polyline travelling upward (+z)."""
    out = []
    for i in range(len(poly)):
        a = poly[max(i - 1, 0)]
        b = poly[min(i + 1, len(poly) - 1)]
        tz, tr = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(tz, tr)
        tz, tr = tz / ln, tr / ln
        out.append((-tr, tz))   # (nz, nr)
    return out


def _smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------- lathe helper

def _lathe(bm, rings, segments, flute=None, close_poles=True):
    """Spin a list of rings [(z, r, depth)] around Z. Each ring's radius is reduced
    by depth * (0.5 + 0.5 cos(flutes * theta)). A ring with r ~ 0 becomes one vertex.
    Faces wind so the normal is phi x tangent (outward for an upward-travelling
    profile). Returns the ring vertex lists."""
    verts = []
    for z, r, depth in rings:
        if r < 1e-7:
            verts.append([bm.verts.new((0, 0, z))] * segments)
            continue
        row = []
        for j in range(segments):
            th = 2 * math.pi * j / segments
            rr = r - depth * (0.5 + 0.5 * math.cos(flute * th)) ** 4 if flute else r
            row.append(bm.verts.new((rr * math.cos(th), rr * math.sin(th), z)))
        verts.append(row)
    faces = []
    for i in range(len(verts) - 1):
        a, b = verts[i], verts[i + 1]
        for j in range(segments):
            k = (j + 1) % segments
            quad = [a[j], a[k], b[k], b[j]]
            uniq = []
            for v in quad:
                if v not in uniq:
                    uniq.append(v)
            if len(uniq) >= 3:
                faces.append(bm.faces.new(uniq))
    return verts, faces


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    seg, fl = p["segments"], p["flutes"]
    t = p["wall"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    smoke = materials.glass("M_Glass_Smoke", tint=p["tint"], alpha=0.35, roughness=0.04)
    # the same pickup as every glass vase of the decor kits (lib/pickups.py)
    from lib import pickups
    importlib.reload(pickups)
    if pickups.ENABLED:             # (items off, GT_ITEMS unset: a vase is decor, not a pickup)
        root["interact"] = {**pickups.define("vase", smoke), "item": p["item"], "name": p["label"],
                            "prompt": f"Take {p['label'].lower()}"}
    dense = materials.glass("M_Glass_Smoke_Dense", tint=tuple(c * 0.85 for c in p["tint"]),
                            alpha=0.55, roughness=0.04)

    z0 = p["base_h"]
    z_lo, z_hi = p["flute_z"]

    def depth(z, k=1.0):
        return p["flute_depth"] * k * _smoothstep(z_lo, z_lo + 0.035, z) * (1 - _smoothstep(z_hi - 0.045, z_hi, z))

    # ---- wall: outer (up) -> lip (over) -> inner (down) ----------------------------
    dense_prof = _catmull(p["profile"])
    outer = _resample(dense_prof, p["outer_rings"])
    nrm = _normals(dense_prof)
    # offset curve inward by wall thickness (using dense normals), then resample
    inner_dense = [(z - t * nz, r - t * nr) for (z, r), (nz, nr) in zip(dense_prof, nrm)]
    inner_dense = [pt for pt in inner_dense if pt[0] >= z0]
    # start the inner wall exactly at the floor
    inner_dense.insert(0, (z0, inner_dense[0][1] - (inner_dense[0][0] - z0) * 0.0))
    inner = _resample(inner_dense, p["inner_rings"])
    inner = [(z0 if i == 0 else z, r) for i, (z, r) in enumerate(inner)]
    wall_rings = [(z, r, depth(z)) for z, r in outer]

    # rounded lip: half circle over the top joining outer and inner
    (nz, nr) = nrm[-1]
    a, b = dense_prof[-2], dense_prof[-1]
    tzz, trr = b[0] - a[0], b[1] - a[1]
    ln = math.hypot(tzz, trr)
    tzz, trr = tzz / ln, trr / ln
    cz, cr = b[0] - nz * t / 2, b[1] - nr * t / 2
    for ang in (math.pi / 4, math.pi / 2, 3 * math.pi / 4):
        wall_rings.append((cz + (t / 2) * (math.cos(ang) * nz + math.sin(ang) * tzz),
                           cr + (t / 2) * (math.cos(ang) * nr + math.sin(ang) * trr), 0.0))
    for z, r in reversed(inner):
        wall_rings.append((z, r, depth(z, 0.75)))

    bm = bmesh.new()
    _lathe(bm, wall_rings, seg, flute=fl)
    wall = common.mesh_object(f"{n}_Wall", bm, col, smoke, root)

    # ---- solid base: a thick puck of denser glass ------------------------------------
    R = outer[0][1]
    rf = 0.0035      # bottom edge fillet
    # bottom edge arc from (z=0, r=R-rf) to (z=rf, r=R)
    puck = [(0.0, 0.0, 0.0)]
    for k in range(2):
        a_ = math.pi / 2 * k
        puck.append((rf - rf * math.cos(a_), R - rf + rf * math.sin(a_), 0.0))
    puck.append((z0, R, 0.0))
    puck.append((z0, 0.0, 0.0))
    bm = bmesh.new()
    verts, faces = _lathe(bm, puck, seg, flute=None)
    # crisp edge where the side meets the flat top (the cavity floor)
    top_ring = verts[-2]
    for e in bm.edges:
        if all(v in top_ring for v in e.verts):
            e.smooth = False
    base = common.mesh_object(f"{n}_Base", bm, col, dense, root)
    for me in (wall.data, base.data):
        for poly in me.polygons:
            poly.use_smooth = True

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
