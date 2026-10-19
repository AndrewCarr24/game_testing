"""Floor lantern for the courtyard lounge: an open black steel cage (four slim corner
posts between a square base tray and a top frame, a low pyramid cap and a ring handle)
round a fat ivory pillar candle with a warm glowing flame.

Collision: the cage is one mesh (one small box); the candle and flame are NoCollide.
Origin: floor centre. Units are metres."""
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
import courtyard_festoon as festoon  # noqa: E402

importlib.reload(cc)
importlib.reload(festoon)
common = cc.common

NAME = "CourtyardLantern"

P = dict(
    name=NAME,
    width=0.26,
    height=0.56,
    post=0.012,
    candle=(0.055, 0.17),       # radius, height
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rng = random.Random(3)
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    black, wax, glow = cc.black_mat(), cc.ceramic_mat(), cc.bulb_mat()
    w, H, s = p["width"], p["height"], p["post"]

    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    # base tray (on four tiny feet), top frame, posts
    cc.piece(bm, uvl, (w, w, 0.03), Matrix.Translation((0, 0, 0.03)), bevel=0.003, rng=rng)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cc.piece(bm, uvl, (0.02, 0.02, 0.016), Matrix.Translation((sx * (w / 2 - 0.02), sy * (w / 2 - 0.02), 0.008)),
                     bevel=0, rng=rng, skip=("-z", "+z"))
            cc.piece(bm, uvl, (s, s, H - 0.10), Matrix.Translation((sx * (w / 2 - s / 2), sy * (w / 2 - s / 2),
                                                                     0.045 + (H - 0.10) / 2)),
                     bevel=0, rng=rng, skip=("-z", "+z"))
    zt = H - 0.055
    for k in range(4):
        rot = Matrix.Rotation(k * math.pi / 2, 4, "Z")
        cc.piece(bm, uvl, (w, s, 0.02), rot @ Matrix.Translation((0, w / 2 - s / 2, zt)), bevel=0, rng=rng,
                 skip=("-x", "+x"))
    # pyramid cap and a ring handle
    cc.lathe_bm(bm, [(w / 2 * 1.414 + 0.004, zt + 0.01), (0.03, H - 0.012), (0.0, H - 0.008)], 4,
                Matrix.Rotation(math.pi / 4, 4, "Z"))
    ring = [Vector((0, math.cos(a) * 0.035, H + 0.028 + math.sin(a) * 0.035))
            for a in [2 * math.pi * i / 10 for i in range(11)]]
    festoon.tube(bm, ring, 0.004, 4)
    common.mesh_object(f"{n}_Cage", bm, col, black, root, smooth=False)

    r, ch = p["candle"]
    cb = bmesh.new()
    cc.lathe_bm(cb, [(r, 0.045), (r, 0.045 + ch - 0.008), (r - 0.008, 0.045 + ch), (0.0, 0.045 + ch - 0.006)], 12)
    common.mesh_object(f"{n}_CandleNoCollide", cb, col, wax, root, smooth=True)
    fb = bmesh.new()
    fh = 0.04
    cc.lathe_bm(fb, [(0.0, 0.0), (0.009, fh * 0.3), (0.006, fh * 0.7), (0.0, fh)], 6,
                Matrix.Translation((0, 0, 0.045 + ch - 0.004)))
    bmesh.ops.recalc_face_normals(fb, faces=fb.faces[:])
    common.mesh_object(f"{n}_FlameNoCollide", fb, col, glow, root, smooth=True)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
