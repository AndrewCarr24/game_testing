"""Festoon lights over the courtyard dining table: four slim black steel masts (tapered
round poles with a cap and a forged eye at the top, a square foot plate) with star
jasmine twining up their lower half, and black cables strung between them (the two long
sides and an X across the middle) in shallow catenary sags, carrying warm 2200 K globe
bulbs on short black sockets every ~0.7 m.

Collision: each mast is its own mesh (a slim box); cables, sockets, bulbs and the jasmine
are NoCollide. Origin: the centre of the mast rectangle on the floor. Units are metres."""
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
import ix_common  # noqa: E402  (react definitions, prompts/interactivity.md)

importlib.reload(cc)
importlib.reload(ix_common)
common = cc.common

NAME = "CourtyardFestoon"

P = dict(
    name=NAME,
    half=(5.55, 4.40),          # masts at (+-x, +-y)
    mast_h=3.70,
    mast_r=(0.034, 0.026),      # foot / top radius
    anchor_drop=0.10,           # cables tie on this far below the top
    # spans between masts (indices: 0 SW, 1 SE, 2 NW, 3 NE) and their sag (m)
    spans=((0, 1, 0.55), (2, 3, 0.55), (0, 3, 0.85), (1, 2, 0.85)),
    spacing=0.90,               # bulb pitch along a cable
    cable_r=0.0045,
    globe_r=0.026,
    jasmine=True,
    seed=5,
)


def masts(p):
    hx, hy = p["half"]
    return [Vector((-hx, -hy, 0)), Vector((hx, -hy, 0)), Vector((-hx, hy, 0)), Vector((hx, hy, 0))]


def catenary(a, b, sag, n):
    """Points from a to b sagging by `sag` at mid-span (parabola: fine at these sags)."""
    out = []
    for i in range(n + 1):
        t = i / n
        q = a.lerp(b, t)
        q.z -= 4 * sag * t * (1 - t)
        out.append(q)
    return out


def span_points(p):
    """Every span's cable polyline and bulb positions (also used for the room's LIGHTS)."""
    ms = masts(p)
    z = p["mast_h"] - p["anchor_drop"]
    spans = []
    for i, j, sag in p["spans"]:
        a = ms[i] + Vector((0, 0, z))
        b = ms[j] + Vector((0, 0, z))
        d = (b - a)
        # tie on at the mast's surface, not its axis
        dn = Vector((d.x, d.y, 0)).normalized()
        a, b = a + dn * 0.05, b - dn * 0.05
        L = (b - a).length
        nb = max(2, round(L / p["spacing"]))
        # the cable kinks a little at each bulb (their weight), so one segment per bulb gap
        pts = catenary(a, b, sag, nb * 2)
        bulbs = [pts[k] for k in range(1, nb * 2, 2)]
        cable = [pts[0]] + bulbs + [pts[-1]]
        spans.append((cable, bulbs))
    return spans


def tube(bm, pts, r, sides, uvl=None):
    """Tube along pts (parallel-transport frames), open ends."""
    n = len(pts)
    tang = [(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(n)]
    ref = Vector((0, 0, 1)) if abs(tang[0].z) < 0.9 else Vector((1, 0, 0))
    nrm = (ref - tang[0] * ref.dot(tang[0])).normalized()
    rings = []
    for i in range(n):
        t = tang[i]
        nrm = (nrm - t * nrm.dot(t)).normalized()
        bi = t.cross(nrm)
        rr = r[i] if isinstance(r, (list, tuple)) else r
        rings.append([bm.verts.new(pts[i] + (nrm * math.cos(2 * math.pi * k / sides) +
                                             bi * math.sin(2 * math.pi * k / sides)) * rr) for k in range(sides)])
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((a[k], a[j], b[j], b[k]))
    return rings


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rng = random.Random(p["seed"])
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    black, glow, leaf = cc.black_mat(), cc.bulb_mat(), cc.foliage_mat()
    H = p["mast_h"]
    r0, r1 = p["mast_r"]

    # masts: tapered 10-sided pole, domed cap, an eye ring for the cables, foot plate
    for k, m in enumerate(masts(p)):
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        ez = H - p["anchor_drop"]
        prof = [None, None, None, (r0 + 0.010, 0.012), (r0, 0.035),
                (r1 + 0.001, ez - 0.02), (r1 + 0.008, ez - 0.012), (r1 + 0.008, ez + 0.012), (r1, ez + 0.02),
                (r1, H - 0.012), (r1 * 0.55, H), (0.0, H + 0.004)]
        cc.lathe_bm(bm, [(0.11, 0.0), (0.11, 0.012), (0.0, 0.012)], 4, Matrix.Rotation(math.pi / 4, 4, "Z"),
                    uvl)                                                             # square foot plate
        cc.lathe_bm(bm, prof[3:], 8, None, uvl)     # pole, tie-on collar, cap
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        ob = common.mesh_object(f"{n}_Mast{k}", bm, col, black, root, smooth=True)
        ob.location = m

    # cables and bulb sockets (black), globes (glow)
    cb = bmesh.new()
    gb = bmesh.new()
    for cable, bulbs in span_points(p):
        tube(cb, cable, p["cable_r"], 3)
        for q in bulbs:
            # socket: short black cylinder hanging under the cable
            sk = [(0.0115, 0.0), (0.0105, -0.040)]
            top = q + Vector((0, 0, -p["cable_r"]))
            cc.lathe_bm(cb, sk, 4, Matrix.Translation(top) @ Matrix.Rotation(math.pi / 4, 4, "Z"))
            gr = p["globe_r"]
            gl = [(0.009, -0.040), (gr, -0.040 - gr * 0.9), (gr * 0.7, -0.040 - gr * 1.75), (0.0, -0.040 - gr * 2.0)]
            cc.lathe_bm(gb, gl, 5, Matrix.Translation(top))
    bmesh.ops.recalc_face_normals(gb, faces=gb.faces[:])
    common.mesh_object(f"{n}_CablesNoCollide", cb, col, black, root, smooth=True)
    bulbs = common.mesh_object(f"{n}_BulbsNoCollide", gb, col, glow, root, smooth=True)
    bulbs["react"] = ix_common.glow()      # interactivity: the bulbs follow the courtyard's lights (and power)

    # star jasmine twining up the lower half of each mast
    if p["jasmine"]:
        jb = bmesh.new()
        uvl = jb.loops.layers.uv.new("UVMap")
        for m in masts(p):
            for s in range(4):
                a0 = rng.uniform(0, 2 * math.pi) + s * 1.6
                top = rng.uniform(1.6, 2.3)
                pts, widths = [], []
                steps = 6
                for i in range(steps + 1):
                    t = i / steps
                    a = a0 + t * rng.uniform(2.2, 3.2)
                    rr = r0 + 0.05 + 0.04 * math.sin(t * math.pi)
                    pts.append(m + Vector((math.cos(a) * rr, math.sin(a) * rr, 0.25 + t * top)))
                    widths.append(1.0 - 0.35 * t)
                # the card faces outward from the pole: half-width along the tangent of the twist
                hw = []
                for i, q in enumerate(pts):
                    out = Vector((q.x - m.x, q.y - m.y, 0)).normalized()
                    hw.append(out.cross(Vector((0, 0, 1))) * 0.17)
                cc.add_strip(jb, uvl, pts, hw, "jasmine", flip=s % 2 == 1, widths=widths)
        common.mesh_object(f"{n}_JasmineNoCollide", jb, col, leaf, root, smooth=False)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
