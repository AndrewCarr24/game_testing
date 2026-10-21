"""Long outdoor teak dining table for ten (four a side and one at each end): a top of five
long boards with 6 mm drainage gaps and eased edges over a deep apron, on four square
tapered legs; dressed with a sand-linen runner, clusters of pillar candles (warm glowing
flames), two ceramic bud vases of olive and jasmine sprigs and a wide terracotta bowl.

Collision: the top (boards + aprons) and each leg are separate meshes; the table dressing
is NoCollide. Long axis along X, origin at the floor centre. Units are metres."""
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

NAME = "CourtyardDiningTable"

P = dict(
    name=NAME,
    length=3.50,
    width=1.05,
    height=0.75,
    top_t=0.045,
    boards=5,
    gap=0.006,
    apron_h=0.10,
    leg=0.085,
    leg_foot=0.062,
    leg_inset=0.07,
    seed=23,
    dressing=True,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rng = random.Random(p["seed"])
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    teak = cc.teak_mat()
    L, Wd, H, t = p["length"], p["width"], p["height"], p["top_t"]

    # top: boards along X with drainage gaps, plus the apron frame under it
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    nb, g = p["boards"], p["gap"]
    bw = (Wd - g * (nb - 1)) / nb
    for k in range(nb):
        y = -Wd / 2 + bw / 2 + k * (bw + g)
        cc.piece(bm, uvl, (L, bw, t), Matrix.Translation((0, y, H - t / 2)), bevel=0.004, rng=rng)
    li, ah, s = p["leg_inset"], p["apron_h"], p["leg"]
    ax, ay = L / 2 - li - s / 2, Wd / 2 - li - s / 2         # leg centres
    at = 0.028
    for sy in (-1, 1):
        cc.piece(bm, uvl, (2 * ax - s + 0.004, at, ah), Matrix.Translation((0, sy * (ay + s / 2 - at / 2 - 0.006),
                                                                             H - t - ah / 2)),
                 bevel=0.003, rng=rng, skip=("+z", "-x", "+x"))
    for sx in (-1, 1):
        cc.piece(bm, uvl, (at, 2 * ay - s + 0.004, ah), Matrix.Translation((sx * (ax + s / 2 - at / 2 - 0.006), 0,
                                                                             H - t - ah / 2)),
                 bevel=0.003, rng=rng, skip=("+z", "-y", "+y"))
    # a centre stretcher under the top (carries the boards over the long span)
    cc.piece(bm, uvl, (at, 2 * ay - s, ah * 0.8), Matrix.Translation((0, 0, H - t - ah * 0.4)), bevel=0.003,
             rng=rng, skip=("+z", "-y", "+y"))
    common.mesh_object(f"{n}_Top", bm, col, teak, root, smooth=False)

    # legs: square, tapering on the inside faces toward the foot
    for k, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        h = H - t
        cc.piece(bm, uvl, (s, s, h), Matrix.Translation((0, 0, h / 2)), bevel=0.004, rng=rng, skip=("+z",))
        f = p["leg_foot"] / s
        for v in bm.verts:
            tz = v.co.z / h
            k2 = f + (1 - f) * tz
            # outer faces stay plumb, inner faces taper
            v.co.x *= k2
            v.co.y *= k2
            v.co.x += sx * (s / 2) * (1 - k2)
            v.co.y += sy * (s / 2) * (1 - k2)
        ob = common.mesh_object(f"{n}_Leg{k}", bm, col, teak, root, smooth=False)
        ob.location = (sx * ax, sy * ay, 0)

    if p["dressing"]:
        dress(p, col, root, rng)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


def dress(p, col, root, rng):
    n = p["name"]
    H = p["height"]
    cer, sand, terra = cc.ceramic_mat(), cc.sand_fabric(), cc.terracotta_mat()
    glow, leaf = cc.bulb_mat(), cc.foliage_mat()

    # linen runner down the middle, hanging 12 cm over each end
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rl, rw, rt = p["length"] - 0.5, 0.40, 0.003
    cc.piece(bm, uvl, (rl, rw, rt), Matrix.Translation((0, 0, H + rt / 2)), bevel=0, tile=0.25, rng=rng,
             skip=("-z",))
    common.mesh_object(f"{n}_RunnerNoCollide", bm, col, sand, root, smooth=False)

    ware = bmesh.new()
    wuv = ware.loops.layers.uv.new("UVMap")
    flames = bmesh.new()
    z0 = H + 0.003
    # pillar candles in three clusters along the runner (heights vary), each with a flame
    for cx in (-1.05, 0.0, 1.05):
        for dx, dy, r, h in ((-0.07, 0.03, 0.040, 0.20), (0.05, -0.045, 0.035, 0.13), (0.07, 0.06, 0.03, 0.09)):
            x, y = cx + dx + rng.uniform(-0.01, 0.01), dy
            prof = [(r, 0.0), (r, h - 0.006), (r - 0.006, h), (0.0, h - 0.005)]
            cc.lathe_bm(ware, prof, 8, Matrix.Translation((x, y, z0)), wuv, tile=0.25)
            fh = 0.028
            fl = [(0.0, 0.0), (0.006, fh * 0.3), (0.0045, fh * 0.7), (0.0, fh)]
            cc.lathe_bm(flames, fl, 5, Matrix.Translation((x, y, z0 + h - 0.002)))
    # two ceramic bud vases with sprigs
    vase = [(0.0, 0.0), (0.035, 0.0), (0.05, 0.05), (0.048, 0.10), (0.022, 0.16), (0.018, 0.19), (0.022, 0.20),
            (0.016, 0.20)]
    sprigs = bmesh.new()
    suv = sprigs.loops.layers.uv.new("UVMap")
    for vx, cell in ((-0.55, "sprigA"),):
        cc.lathe_bm(ware, vase, 12, Matrix.Translation((vx, -0.02, z0)), wuv, tile=0.25)
        for j in range(3):
            a = rng.uniform(0, math.pi) + j * math.pi / 3
            right = Vector((math.cos(a), math.sin(a), 0)) * 0.13
            lean = Vector((rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), 0))
            cc.add_strip(sprigs, suv, [(vx, -0.02, z0 + 0.12), Vector((vx, -0.02, z0 + 0.27)) + lean,
                                       Vector((vx, -0.02, z0 + 0.40)) + lean * 2.5], right, cell, flip=j % 2 == 1)
    for m_ in (ware,):
        bmesh.ops.recalc_face_normals(m_, faces=m_.faces[:])
    common.mesh_object(f"{n}_WareNoCollide", ware, col, cer, root, smooth=True)
    bmesh.ops.recalc_face_normals(flames, faces=flames.faces[:])
    common.mesh_object(f"{n}_FlameNoCollide", flames, col, glow, root, smooth=True)
    common.mesh_object(f"{n}_SprigsNoCollide", sprigs, col, leaf, root, smooth=False)
    # wide terracotta bowl between the candles
    bowl = [(0.0, 0.0), (0.07, 0.0), (0.075, 0.008), (0.15, 0.05), (0.19, 0.085), (0.195, 0.092), (0.185, 0.094),
            (0.14, 0.06), (0.0, 0.035)]
    bb = bmesh.new()
    buv = bb.loops.layers.uv.new("UVMap")
    cc.lathe_bm(bb, bowl, 16, Matrix.Translation((0.56, 0.0, z0)), buv, tile=0.25)
    bowl = common.mesh_object(f"{n}_BowlNoCollide", bb, col, terra, root, smooth=True)
    # the bowl is a throwable pickup (lib/pickups.py); the lit candles and the bud vase stay
    from lib import pickups
    importlib.reload(pickups)
    pickups.adopt(f"{n}_Bowl", col, root, "bowl", [bowl], (0.56, 0.0, z0))


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
