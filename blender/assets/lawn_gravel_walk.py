"""The sculpture lawn's gravel walk: a squircle loop (long straights, generous corners) with
a spur up to the house terrace and an apron in front of the bench wall. Pale raked gravel
in 1.5 m cells (so tree and sculpture shadows read), a fine dark-steel edge on both sides.

This asset is authored directly in the zone's local metres ((0, 0) = centre of the south
lawn rect), so it is placed at (0, 0). Origin: lawn level."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lawn_common as lc  # noqa: E402

importlib.reload(lc)
common, outdoor = lc.common, lc.outdoor

NAME = "LawnGravelWalk"

P = dict(
    name=NAME,
    centre=(-1.5, -1.5),
    half=(17.0, 7.4),          # semi-axes of the loop
    power=2.6,                 # squircle exponent (2 = ellipse)
    width=2.0,                 # gravel width
    edge=0.09,                 # steel edging width
    z=0.03, z_edge=0.045,      # heights above the lawn
    cell=1.5,
    spur_x=8.5, spur_top=17.4,        # spur from the terrace edge down to the loop (north side)
    bench_x=-11.4, bench_apron=(4.6, 2.9),   # apron in front of the seat wall, south side (width, depth)
    apron_y=-11.6,                    # far edge of the apron (against the bench)
)


def squircle(p, n=720):
    cx, cy = p["centre"]
    a, b = p["half"]
    e = 2.0 / p["power"]
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        pts.append(Vector((cx + a * math.copysign(abs(c) ** e, c), cy + b * math.copysign(abs(s) ** e, s), 0)))
    return pts


def resample_closed(pts, step):
    """Equal-ish steps along the closed polyline, shorter (down to 60%) where it turns
    tightly so the corners stay round."""
    n0 = len(pts)
    d = [0.0]
    for i in range(n0):
        d.append(d[-1] + (pts[(i + 1) % n0] - pts[i]).length)
    total = d[-1]

    def local_step(i):
        k = max(2, int(2.0 / (total / n0)))            # ~2 m either side
        a, b, c = pts[(i - k) % n0], pts[i], pts[(i + k) % n0]
        t1, t2 = (b - a).normalized(), (c - b).normalized()
        turn = math.acos(max(-1.0, min(1.0, t1.dot(t2))))
        radius = (2.0 * k * total / n0) / max(turn, 1e-4)
        return max(0.6 * step, min(step, 0.22 * radius))

    out, s, j = [], 0.0, 0
    while s < total - 0.4 * step:
        while d[j + 1] < s:
            j += 1
        f = (s - d[j]) / (d[j + 1] - d[j])
        out.append(pts[j].lerp(pts[(j + 1) % n0], f))
        s += local_step(j)
    return out


def up(bm, verts):
    f = bm.faces.new(verts)
    if f.normal.z < 0:
        f.normal_flip()
    return f


def drop_face(bm, a, b, z_top, direction):
    """Vertical face under the edge a-b (points at z=0 .. z_top) facing `direction`."""
    v = [bm.verts.new((a.x, a.y, z_top)), bm.verts.new((b.x, b.y, z_top)),
         bm.verts.new((b.x, b.y, 0.0)), bm.verts.new((a.x, a.y, 0.0))]
    f = bm.faces.new(v)
    if f.normal.dot(direction) < 0:
        f.normal_flip()
    return f


def strip(bm, centres, normals, closed, p, z, z_edge, skip_edge=None, edge_every=2):
    """Gravel (two cells across) plus both steel edges along a centre line."""
    hw, we = p["width"] / 2, p["edge"]
    n = len(centres)
    seg = n if closed else n - 1
    for i in range(seg):
        j = (i + 1) % n
        c0, c1, n0, n1 = centres[i], centres[j], normals[i], normals[j]
        L0, L1, R0, R1 = c0 + n0 * hw, c1 + n1 * hw, c0 - n0 * hw, c1 - n1 * hw
        V = lambda v, zz: bm.verts.new((v.x, v.y, zz))
        m0, m1 = V(c0, z), V(c1, z)
        l0, l1, r0, r1 = V(L0, z), V(L1, z), V(R0, z), V(R1, z)
        up(bm, (l0, m0, m1, l1))
        up(bm, (m0, r0, r1, m1))
    # steel edging: long cells (every `edge_every` stations)
    for side in (1, -1):
        i = 0
        while i < seg:
            j2 = min(i + edge_every, seg)
            mid = (centres[i] + centres[j2 % n]) / 2
            if skip_edge and any((mid - q).length < r for q, r in skip_edge):
                i = j2
                continue
            pts = []
            for k in (i, j2 % n):
                a = centres[k] + normals[k] * (hw * side)
                b = centres[k] + normals[k] * ((hw + we) * side)
                pts.append((a, b))
            (a0, b0), (a1, b1) = pts
            v = [bm.verts.new((q.x, q.y, z_edge)) for q in (a0, b0, b1, a1)]
            up(bm, v)
            drop_face(bm, b0, b1, z_edge, (b0 - a0) * 1.0)       # the steel plate down to the lawn
            i = j2


def line_pts(a, b, cell):
    n = max(1, math.ceil((b - a).length / cell))
    return [a.lerp(b, k / n) for k in range(n + 1)]


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    gravel, steel = outdoor.gravel(), outdoor.dark_metal()

    # ---- loop
    centres = resample_closed(squircle(p), p["cell"])
    N = len(centres)
    normals = []
    for i in range(N):
        t = (centres[(i + 1) % N] - centres[i - 1]).normalized()
        normals.append(Vector((-t.y, t.x, 0)))           # points to the left = the loop's inside (counter-clockwise)
    # junctions with the spur and the apron
    def nearest(x, north):
        best = min((c for c in centres if (c.y > p["centre"][1]) == north), key=lambda c: abs(c.x - x))
        return best
    jn = nearest(p["spur_x"], True)
    js = nearest(p["bench_x"], False)
    skip = [(jn, 1.9), (js, 3.0)]

    bm = bmesh.new()
    strip(bm, centres, normals, True, p, p["z"], p["z_edge"], skip_edge=skip)
    # ---- spur: terrace edge down to the loop's outer edge (straight, a hair higher than the loop)
    a = Vector((p["spur_x"], p["spur_top"], 0))
    b = Vector((p["spur_x"], jn.y + p["width"] / 2 - 0.05, 0))
    pts = line_pts(a, b, p["cell"])
    nor = [Vector((1, 0, 0))] * len(pts)
    strip(bm, pts, nor, False, p, p["z"] + 0.004, p["z_edge"] + 0.004)
    # ---- apron in front of the bench: a gravel pad meeting the loop's south side
    w, dpt = p["bench_apron"]
    y0 = p["apron_y"]
    y1 = js.y - p["width"] / 2 + 0.05
    nx, ny = max(1, math.ceil(w / p["cell"])), max(1, math.ceil((y1 - y0) / p["cell"]))
    vs = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            vs[i, j] = bm.verts.new((p["bench_x"] - w / 2 + w * i / nx, y0 + (y1 - y0) * j / ny, p["z"] + 0.004))
    for i in range(nx):
        for j in range(ny):
            up(bm, (vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
    za = p["z"] + 0.004
    for i in range(nx):                                      # its three open sides drop to the lawn
        a = Vector((p["bench_x"] - w / 2 + w * i / nx, y0, 0))
        b = Vector((p["bench_x"] - w / 2 + w * (i + 1) / nx, y0, 0))
        drop_face(bm, a, b, za, Vector((0, -1, 0)))
    for j in range(ny):
        ya, yb = y0 + (y1 - y0) * j / ny, y0 + (y1 - y0) * (j + 1) / ny
        drop_face(bm, Vector((p["bench_x"] - w / 2, ya, 0)), Vector((p["bench_x"] - w / 2, yb, 0)), za, Vector((-1, 0, 0)))
        drop_face(bm, Vector((p["bench_x"] + w / 2, ya, 0)), Vector((p["bench_x"] + w / 2, yb, 0)), za, Vector((1, 0, 0)))
    ob = common.mesh_object(f"{n}_Gravel", bm, col, gravel, root, smooth=False)
    # separate the steel edges into their own mesh by material
    me = ob.data
    me.materials.append(steel)
    for poly in me.polygons:
        zs = [me.vertices[v].co.z for v in poly.vertices]
        vertical = abs(poly.normal.z) < 0.5
        # steel: the edging strip tops and the plates under them; gravel: everything else
        poly.material_index = 1 if (min(zs) > p["z"] + 0.006 or (vertical and max(zs) > p["z"] + 0.01)) else 0
    common.box_uv(ob, tile=2.0)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
