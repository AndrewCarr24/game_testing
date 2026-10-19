"""Mature olive tree in a large limestone bowl planter.

An old, gnarled olive: three fluted stems (plus two younger ones) that rise twisted round
each other out of a buttressed root flare, part at about 1.3 m and wander outward as the main limbs; each
limb forks into thinner branches and twigs, and the crown is many separate clumps of
alpha-tested leaf cards (silver-green sprigs from the shared foliage atlas) at the twig
ends, so the sky and the wood show between them. Card normals are bent outward from
their clump and the crown (volumetric shading, no noise).

Trunk, limbs and canopy are separate meshes, and the lower stems belong to the trunk
mesh (below 2.1 m) so the collision boxes (one per mesh) leave the ground under the
canopy free. Origin: planter centre on the floor. Units are metres.
"""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import courtyard_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common

NAME = "CourtyardOliveTree"

P = dict(
    name=NAME,
    seed=7,
    planter_h=0.64,
    soil_z=0.50,
    cards_per_lobe=30,          # leaf cards per clump
    clumps=36,                  # leaf clumps in the crown
    card_size=(0.34, 0.50),     # min / max card edge (m); sprig leaves ~7 cm
    split_z=2.1,                # trunk mesh ends here, limbs mesh above
    bark=(0.165, 0.142, 0.112),  # weathered grey-brown olive bark
    # overall footprint of the tree (kept from the first version so placements hold)
    extent_lo=(-2.329, -2.467),
    extent_hi=(2.661, 2.338),
    top_z=5.037,
)


# ------------------------------------------------------------------ curves and sweeps

def spline(pts, per=6):
    q = [Vector(pts[0])] + [Vector(p) for p in pts] + [Vector(pts[-1])]
    out = []
    for i in range(1, len(q) - 2):
        p0, p1, p2, p3 = q[i - 1], q[i], q[i + 1], q[i + 2]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(Vector(pts[-1]))
    return out


class Bark:
    """Smooth, deterministic surface relief for a stem: flutes that twist up the
    stem, two octaves of gnarl, and a few burls (Gaussian swellings)."""

    def __init__(self, rng, lobes=3, lobe=0.15, twist=0.5, gnarl=0.06, burls=0, length=1.0):
        self.lobes, self.lobe, self.twist, self.gnarl = lobes, lobe, twist, gnarl
        self.ph = [rng.uniform(0, 2 * math.pi) for _ in range(4)]
        self.burls = [(rng.uniform(0.1, 0.85) * length, rng.uniform(0, 2 * math.pi),
                       rng.uniform(0.10, 0.22), rng.uniform(0.07, 0.14)) for _ in range(burls)]

    def __call__(self, th, s):
        f = 1 + self.lobe * math.sin(self.lobes * th + self.twist * s * 2 * math.pi + self.ph[0])
        f += self.gnarl * (0.6 * math.sin(2 * th + 6.1 * s + self.ph[1]) +
                           0.4 * math.sin(5 * th - 9.7 * s + self.ph[2]) +
                           0.3 * math.sin(3 * th + 17.0 * s + self.ph[3]))
        for s0, t0, amp, w in self.burls:
            d = math.atan2(math.sin(th - t0), math.cos(th - t0))
            f += amp * math.exp(-((s - s0) / w) ** 2 - (d / 0.7) ** 2)
        return f


def rings_along(pts, radii, sides, relief=None, ref=None):
    """Ring vertex positions swept along pts (parallel-transport frames)."""
    n = len(pts)
    tang = [(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(n)]
    ref = ref or (Vector((1, 0, 0)) if abs(tang[0].x) < 0.9 else Vector((0, 1, 0)))
    nrm = (ref - tang[0] * ref.dot(tang[0])).normalized()
    rings, s = [], 0.0
    for i in range(n):
        if i:
            s += (pts[i] - pts[i - 1]).length
        t = tang[i]
        nrm = (nrm - t * nrm.dot(t)).normalized()
        bi = t.cross(nrm)
        ring = []
        for k in range(sides):
            th = 2 * math.pi * k / sides
            f = relief(th, s) if relief else 1.0
            ring.append(pts[i] + (nrm * math.cos(th) + bi * math.sin(th)) * radii[i] * f)
        rings.append(ring)
    return rings, tang


def emit(bm, rings, i0, i1, cap_tip=None):
    """Quads between rings i0..i1 into bm; optional cone cap to cap_tip."""
    vs = [[bm.verts.new(p) for p in rings[i]] for i in range(i0, i1 + 1)]
    sides = len(vs[0])
    for a, b in zip(vs[:-1], vs[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((a[k], a[j], b[j], b[k]))
    if cap_tip is not None:
        tip = bm.verts.new(cap_tip)
        for k in range(sides):
            bm.faces.new((vs[-1][k], vs[-1][(k + 1) % sides], tip))


def taper(n, r0, r1, power=0.85):
    return [r0 + (r1 - r0) * (i / max(n - 1, 1)) ** power for i in range(n)]


def smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ planter

BOWL = [  # (r, z): outer belly, rounded rim, inner wall down into the soil
    (0.74, 0.0), (0.775, 0.03), (0.84, 0.095), (0.92, 0.19), (0.99, 0.30), (1.045, 0.42),
    (1.075, 0.52), (1.085, 0.585), (1.072, 0.625), (1.035, 0.642), (0.965, 0.642),
    (0.932, 0.622), (0.915, 0.59), (0.905, 0.47),
]


def tri(x):
    """Triangle wave 0..1..0 with period 2 (mirrored tiling, continuous)."""
    return 1 - abs((x % 2) - 1)


# One stone of the shared limestone texture (its joints sit at u = 0.096 + 0.2k,
# v = 0.2k): mirrored tiling inside it never shows a paving joint on cast stone.
SLAB = (0.506, 0.41, 0.179, 0.18)        # u0, v0, du, dv in UV units (0.36 m of stone)


def bowl_uv(ob, segs, prof):
    """u mirrored back and forth round the bowl (20 runs of ~0.3 m, an even count so
    the ring closes seamlessly), v mirrored along the profile's arc length."""
    me = ob.data
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    arc = [0.0]
    for (r0, z0), (r1, z1) in zip(prof[:-1], prof[1:]):
        arc.append(arc[-1] + math.hypot(r1 - r0, z1 - z0))
    u0, v0, du, dv = SLAB
    for poly in me.polygons:
        angs = [math.atan2(me.vertices[me.loops[li].vertex_index].co.y,
                           me.vertices[me.loops[li].vertex_index].co.x) % (2 * math.pi)
                for li in poly.loop_indices]
        wrap = max(angs) - min(angs) > math.pi
        for li, a in zip(poly.loop_indices, angs):
            co = me.vertices[me.loops[li].vertex_index].co
            if wrap and a < math.pi:
                a += 2 * math.pi
            x = a / (2 * math.pi) * segs / 2
            r = math.hypot(co.x, co.y)
            i = min(range(len(prof)), key=lambda k: (prof[k][0] - r) ** 2 + (prof[k][1] - co.z) ** 2)
            uv.data[li].uv = (u0 + du * tri(x), v0 + dv * tri(arc[i] / 0.36))


def build_planter(p, col, root, stone, soil):
    segs = 32
    bowl = cc.lathe(BOWL, segs, f"{p['name']}_Planter", col, stone, root, sharp=40)
    bowl_uv(bowl, segs, BOWL)
    sp = [(0.0, p["soil_z"] + 0.035), (0.30, p["soil_z"] + 0.03), (0.62, p["soil_z"] + 0.01),
          (0.912, p["soil_z"] - 0.01), (0.905, 0.40)]
    s = cc.lathe(sp, 16, f"{p['name']}_Soil", col, soil, root, sharp=80)
    return bowl, s


# ------------------------------------------------------------------ tree

# The stems, soil to first fork. The three big ones wind round each other up to ~1.3 m
# (the fused, fluted bole), then part as the main limbs; two younger ones lean out.
STEMS = [
    dict(pts=[(0.12, 0.02, 0.42), (0.14, 0.11, 0.78), (0.01, 0.18, 1.12), (-0.26, 0.24, 1.48),
              (-0.56, 0.26, 1.88), (-0.84, 0.40, 2.28), (-1.08, 0.58, 2.62)], r=(0.23, 0.035)),
    dict(pts=[(-0.10, 0.09, 0.42), (-0.16, -0.05, 0.78), (0.02, -0.17, 1.10), (0.29, -0.26, 1.46),
              (0.57, -0.40, 1.86), (0.84, -0.48, 2.24), (1.06, -0.60, 2.58)], r=(0.22, 0.035)),
    dict(pts=[(-0.02, -0.12, 0.42), (0.09, -0.05, 0.85), (0.14, 0.09, 1.25), (0.15, 0.34, 1.70),
              (0.04, 0.58, 2.15), (0.14, 0.84, 2.60), (0.34, 0.97, 3.00)], r=(0.19, 0.03)),
    dict(pts=[(-0.05, -0.06, 0.62), (-0.14, -0.18, 1.05), (-0.32, -0.36, 1.55), (-0.54, -0.60, 2.05),
              (-0.82, -0.86, 2.50), (-1.00, -1.02, 2.85)], r=(0.11, 0.025)),
    dict(pts=[(0.06, 0.06, 0.70), (0.20, 0.17, 1.15), (0.44, 0.37, 1.65), (0.68, 0.58, 2.08),
              (0.92, 0.82, 2.50), (1.08, 1.02, 2.85)], r=(0.10, 0.025)),
]


def crown_points(rng, n, spacing):
    """Clump centres spread through a broad, flattened dome with an irregular edge:
    Poisson-disk rejection keeps them apart, so sky shows between clumps."""
    pts, tries = [], 0
    while len(pts) < n and tries < 20000:
        tries += 1
        az = rng.uniform(0, 2 * math.pi)
        R = 2.05 * (1 + 0.10 * math.sin(3 * az + 1.3) + 0.06 * math.sin(5 * az + 0.4))
        rh = R * rng.random() ** 0.45
        hmax = 1.55 * math.sqrt(max(1 - (rh / (R + 0.15)) ** 2, 0.0))
        z = 2.62 + hmax * rng.uniform(0.45, 1.0) - 0.12 * (rh / R) ** 2
        q = Vector((rh * math.cos(az), rh * math.sin(az), z))
        if rh < 0.55 and z < 3.6:          # keep the middle open above the bole
            continue
        if all((q - o).length > spacing for o in pts):
            pts.append(q)
    return pts


def build_tree(p, col, root, bark, leaf):
    rng = random.Random(p["seed"])
    n = p["name"]
    sz = p["split_z"]
    trunk_bm, limb_bm = bmesh.new(), bmesh.new()

    # buttressed root flare, buried a little in the soil
    flare_pts = spline([(0.0, 0.0, p["soil_z"] - 0.08), (0.01, 0.0, p["soil_z"] + 0.12),
                        (0.02, 0.02, p["soil_z"] + 0.40)], per=4)
    z0 = p["soil_z"] - 0.08
    flare_r = [0.25 + 0.20 * math.exp(-max(q.z - z0 - 0.05, 0) / 0.11) for q in flare_pts]
    rings, _ = rings_along(flare_pts, flare_r, 18,
                           Bark(rng, lobes=5, lobe=0.15, twist=0.25, gnarl=0.09, burls=3, length=0.5))
    emit(trunk_bm, rings, 0, len(rings) - 1)

    # stems: one continuous sweep each, split into the trunk / limbs meshes at split_z;
    # every ring centre above the bole becomes a node branches can grow from
    nodes = []         # (point, radius)
    for k, st in enumerate(STEMS):
        pts = spline(st["pts"], per=3)
        length = sum((b - a).length for a, b in zip(pts[:-1], pts[1:]))
        rad = taper(len(pts), st["r"][0], st["r"][1], 0.6)
        relief = Bark(rng, lobes=4 if k < 3 else 2, lobe=0.20 if k < 3 else 0.12, twist=0.7 + 0.25 * k,
                      gnarl=0.10, burls=3 if k < 3 else 1, length=length)
        rings, tang = rings_along(pts, rad, 14 if k < 3 else 9, relief)
        cut = next((i for i, q in enumerate(pts) if q.z >= sz), len(pts) - 1)
        emit(trunk_bm, rings, 0, cut)
        emit(limb_bm, rings, cut, len(rings) - 1, cap_tip=pts[-1] + tang[-1] * rad[-1])
        nodes += [(q, r) for q, r in zip(pts, rad) if q.z > 1.9]

    def branch(start, end, r0, r1, sides, bend=0.14, droop=0.10):
        """A sinuous branch start -> end (olive wood kinks rather than arcs)."""
        d = end - start
        L = d.length
        dn = d.normalized()
        side = dn.cross(Vector((0, 0, 1)))
        side = side.normalized() if side.length > 1e-3 else Vector((1, 0, 0))
        upv = side.cross(dn).normalized()
        ctrl = [start]
        for j in (1, 2):
            t = j / 3
            q = start + d * t + side * rng.uniform(-bend, bend) * L + upv * rng.uniform(-bend, bend) * L * 0.6
            q.z += droop * L * (0.6 if j == 1 else 0.3)        # arch up, then reach out
            ctrl.append(q)
        ctrl.append(end)
        pts = spline(ctrl, per=2)
        rings, tang = rings_along(pts, taper(len(pts), r0, r1, 0.9), sides,
                                  Bark(rng, lobes=2, lobe=0.06, twist=0.5, gnarl=0.05, length=L))
        emit(limb_bm, rings, 0, len(rings) - 1, cap_tip=pts[-1] + tang[-1] * r1 * 1.5)
        return pts, taper(len(pts), r0, r1, 0.9)

    # crown: clumps first, then the wood that reaches each one (nearest clumps first,
    # so farther ones fork off the branches already grown: a natural hierarchy)
    centres = crown_points(rng, p["clumps"], 0.70)
    centres.sort(key=lambda q: Vector((q.x, q.y)).length)
    clumps = []
    for c in centres:
        # branch end sits a little inside the clump, from below
        tip = c - Vector((c.x, c.y, 0)).normalized() * 0.12 - Vector((0, 0, 0.10))
        best = min(nodes, key=lambda nr: (nr[0] - tip).length * (1.0 + 0.35 * max(0.0, nr[0].z - tip.z)))
        q, r = best
        L = (tip - q).length
        if L < 0.12:
            continue
        r0 = min(r * 0.75, 0.010 + 0.035 * L)
        sides = 5 if r0 > 0.03 else 4 if r0 > 0.016 else 3
        pts, rads = branch(q, tip, r0, 0.008, sides)
        nodes += [(pt, rr) for pt, rr in zip(pts[1:-1], rads[1:-1])]
        clumps.append((c, (tip - q).normalized()))

    trunk = common.mesh_object(f"{n}_Trunk", trunk_bm, col, bark, root)
    limbs = common.mesh_object(f"{n}_Limbs", limb_bm, col, bark, root)

    # leaf cards in an open shell round each clump; sprig base inside, tip outward
    cb = bmesh.new()
    uvl = cb.loops.layers.uv.new("UVMap")
    smin, smax = p["card_size"]
    normals = []
    crown_c = Vector((0.0, 0.0, 3.3))
    for c, cd in clumps:
        s = rng.uniform(0.8, 1.2)
        rx, ry, rz = 0.50 * s, 0.50 * s, 0.32 * s
        cen = c.copy()
        cen.z = max(cen.z, 2.3 + rz * 0.85)          # lowest leaves stay above ~2.3 m
        for _ in range(p["cards_per_lobe"]):
            while True:
                d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
                if 0.05 < d.length <= 1.0:
                    break
            d.normalize()
            if d.z < -0.55 and rng.random() < 0.6:   # thinner underneath
                d.z *= -0.4
                d.normalize()
            f = 0.30 + 0.55 * rng.random() ** 0.6
            pos = cen + Vector((d.x * rx, d.y * ry, d.z * rz)) * f
            out = Vector((d.x / rx, d.y / ry, d.z / rz)).normalized()
            up = (out * 0.8 + cd * 0.35 + Vector((0, 0, -0.15)) +
                  Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * 0.55).normalized()
            helper = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
            right = up.cross(helper)
            if right.length < 1e-3:
                right = up.cross(Vector((1, 0, 0)))
            right.normalize()
            if right.cross(up).dot(out) < 0:          # front face looks out of the clump
                right = -right
            size = rng.uniform(smin, smax)
            cc.add_card(cb, uvl, pos + up * size * 0.42, right * size * 0.5, up * size * 0.5,
                        "sprigA" if rng.random() < 0.5 else "sprigB")
            vn = ((pos - cen).normalized() * 0.55 + (pos - crown_c).normalized() * 0.45 +
                  Vector((0, 0, 0.35))).normalized()
            normals.extend([vn] * 4)
    canopy = common.mesh_object(f"{n}_Canopy", cb, col, leaf, root, smooth=True)
    return trunk, limbs, canopy, normals


def fit_extent(p, objs):
    """Scale the crown (not the bole) so the tree keeps its original footprint."""
    meshes = [o.data for o in objs]
    for _ in range(6):
        lo = Vector((1e9, 1e9, 1e9))
        hi = Vector((-1e9, -1e9, -1e9))
        for me in meshes:
            for v in me.vertices:
                for a in range(3):
                    lo[a] = min(lo[a], v.co[a])
                    hi[a] = max(hi[a], v.co[a])
        sx = (p["extent_hi"][0] / hi.x, p["extent_lo"][0] / lo.x)
        sy = (p["extent_hi"][1] / hi.y, p["extent_lo"][1] / lo.y)
        szz = (p["top_z"] - 2.3) / (hi.z - 2.3)
        for me in meshes:
            for v in me.vertices:
                x, y, z = v.co
                w = smoothstep(2.1, 2.6, z)
                fx = sx[0] if x > 0 else sx[1]
                fy = sy[0] if y > 0 else sy[1]
                v.co.x = x * (1 + w * (fx - 1))
                v.co.y = y * (1 + w * (fy - 1))
                if z > 2.3:
                    v.co.z = 2.3 + (z - 2.3) * szz
            me.update()


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    stone, soil, bark, leaf = cc.limestone_mat(), cc.soil_mat(), cc.bark_mat(), cc.foliage_mat()
    bsdf = next(nd for nd in bark.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*p["bark"], 1.0)
    bark.diffuse_color = (*p["bark"], 1.0)
    build_planter(p, col, root, stone, soil)
    trunk, limbs, canopy, normals = build_tree(p, col, root, bark, leaf)
    fit_extent(p, [limbs, canopy])
    cc.set_vertex_normals(canopy.data, normals)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
