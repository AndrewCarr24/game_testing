"""Outdoor teak dining chair for the courtyard table: square tapered legs, the back legs
raking back above the seat, deep side and front/back seat rails, three slightly curved
horizontal back slats, and a loose sand-linen seat cushion with a soft crown, tied on.

Collision (one box per mesh): the two side frames (front leg + back leg + side rail),
the seat (front/back rails + cushion) and the back (slats) are separate meshes, so the
boxes follow the chair instead of filling the space between its legs.

Front faces -Y, origin at the floor centre. Units are metres."""
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

NAME = "CourtyardDiningChair"

P = dict(
    name=NAME,
    width=0.50,
    depth=0.54,
    seat_h=0.445,          # top of the seat rails
    back_h=0.86,
    leg=0.040,             # leg section at the seat
    leg_foot=0.030,        # at the floor (taper)
    rake_deg=9.0,          # back legs above the seat
    rail_h=0.075,
    cushion_t=0.05,
    slats=3,
    seed=11,
)


def tapered_leg(bm, uvl, x, y, z0, z1, s0, s1, rng, rot=None, pivot=None):
    """Square leg, section s0 at z0 tapering to s1 at z1 (inner faces taper only)."""
    h = z1 - z0
    piece_bm = bmesh.new()
    luv = piece_bm.loops.layers.uv.new("UVMap")
    cc.piece(piece_bm, luv, (s0, s0, h), Matrix.Translation((0, 0, h / 2)), bevel=0.0035, tile=0.5, rng=rng)
    for v in piece_bm.verts:
        t = v.co.z / h
        k = (s1 + (s0 - s1) * t) / s0          # thinner at the foot
        v.co.x *= k
        v.co.y *= k
    m = Matrix.Translation((x, y, z0))
    if rot is not None:
        m = Matrix.Translation(pivot) @ rot @ Matrix.Translation(Vector((x, y, z0)) - Vector(pivot))
    for v in piece_bm.verts:
        v.co = m @ v.co
    # copy into bm
    vmap = {v: bm.verts.new(v.co) for v in piece_bm.verts}
    for f in piece_bm.faces:
        nf = bm.faces.new([vmap[v] for v in f.verts])
        for a, b in zip(nf.loops, f.loops):
            a[uvl].uv = b[luv].uv
    piece_bm.free()


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rng = random.Random(p["seed"])
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    teak, sand = cc.teak_mat(), cc.sand_fabric()

    W, D, SH, BH = p["width"], p["depth"], p["seat_h"], p["back_h"]
    s, sf, rh = p["leg"], p["leg_foot"], p["rail_h"]
    rake = math.radians(p["rake_deg"])
    xl = W / 2 - s / 2
    yf, yb = -D / 2 + s / 2, D / 2 - s / 2 - 0.02
    rot = Matrix.Rotation(-rake, 4, "X")       # top of the back leg leans to +y
    pivot = (0, yb, SH)

    # side frames: front leg, back leg (straight to the seat, raked above), side rail
    for side, sx in (("L", -1), ("R", 1)):
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        x = sx * xl
        tapered_leg(bm, uvl, x, yf, 0.0, SH, sf, s, rng)
        tapered_leg(bm, uvl, x, yb, 0.0, SH + 0.01, sf, s, rng)
        # upper back leg: raked, tapering a little toward the top
        up = bmesh.new()
        luv = up.loops.layers.uv.new("UVMap")
        hb = BH - SH
        cc.piece(up, luv, (s * 0.92, s * 0.92, hb), Matrix.Translation((0, 0, hb / 2)), bevel=0.0035, rng=rng,
                 skip=("-z",))
        for v in up.verts:
            k = 1 - 0.18 * (v.co.z / hb)
            v.co.y *= k
        m = Matrix.Translation((x, yb, SH)) @ rot
        vmap = {v: bm.verts.new(m @ v.co) for v in up.verts}
        for f in up.faces:
            nf = bm.faces.new([vmap[v] for v in f.verts])
            for a, b in zip(nf.loops, f.loops):
                a[uvl].uv = b[luv].uv
        up.free()
        # side rail between the legs (inset 6 mm from the leg's outer face)
        cc.piece(bm, uvl, (s * 0.62, yb - yf - s + 0.004, rh),
                 Matrix.Translation((x - sx * 0.006, (yf + yb) / 2, SH - rh / 2 - 0.004)), bevel=0.003, rng=rng,
                 skip=("-y", "+y"))
        ob = common.mesh_object(f"{n}_Side{side}", bm, col, teak, root, smooth=False)

    # seat: front and back rails (between the side frames) and the cushion
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    span = 2 * xl - s + 0.004
    cc.piece(bm, uvl, (span, s * 0.62, rh), Matrix.Translation((0, yf + 0.004, SH - rh / 2 - 0.004)), bevel=0.003,
             rng=rng, skip=("-x", "+x"))
    cc.piece(bm, uvl, (span, s * 0.62, rh), Matrix.Translation((0, yb - 0.004, SH - rh / 2 - 0.004)), bevel=0.003,
             rng=rng, skip=("-x", "+x"))
    common.mesh_object(f"{n}_Seat", bm, col, teak, root, smooth=False)

    # cushion: crowned, rounded edges, sits on the deck between the back legs
    cw, cd, ct = W - 0.035, yb - yf - 0.004, p["cushion_t"]
    cb = common.cushion_bmesh((cw, cd, ct), cuts=2, edge=0.016, crown={"+z": 0.010, "-y": 0.005})
    cush = common.mesh_object(f"{n}_Cushion", cb, col, sand, root, smooth=True)
    cush.location = (0, (yf + yb) / 2 + 0.002, SH + ct / 2 - 0.002)
    common.box_uv(cush, tile=0.25)

    # back: three slats between the raked back legs, gently curved (bowed back by 12 mm)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    hb = BH - SH
    for k in range(p["slats"]):
        zl = hb * (0.50 + 0.19 * k) if k < p["slats"] - 1 else hb - 0.045
        sh = 0.075 if k == p["slats"] - 1 else 0.058
        tmp = bmesh.new()
        luv = tmp.loops.layers.uv.new("UVMap")
        cc.piece(tmp, luv, (2 * xl - s + 0.004, 0.020, sh), None, bevel=0.0025, rng=rng, skip=("-x", "+x"))
        bmesh.ops.subdivide_edges(tmp, edges=[e for e in tmp.edges
                                              if abs(e.verts[0].co.x - e.verts[1].co.x) > 0.3], cuts=2)
        for v in tmp.verts:
            v.co.y += 0.012 * (1 - (2 * v.co.x / (2 * xl)) ** 2)
        m = Matrix.Translation((0, yb, SH)) @ rot @ Matrix.Translation((0, 0.004, zl))
        vmap = {v: bm.verts.new(m @ v.co) for v in tmp.verts}
        for f in tmp.faces:
            nf = bm.faces.new([vmap[v] for v in f.verts])
            for a, b in zip(nf.loops, f.loops):
                a[uvl].uv = b[luv].uv
        tmp.free()
    common.mesh_object(f"{n}_Back", bm, col, teak, root, smooth=False)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
