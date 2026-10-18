"""Long limestone trough planter with low planting: golden ornamental grass and blue-green
sedge (alpha-tested crossed cards from the shared foliage atlas) between clipped boxwood
balls. Long axis along X, origin the floor centre. Units are metres."""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import courtyard_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common

NAME = "CourtyardPlanter"

P = dict(
    name=NAME,
    length=4.0,
    width=0.80,
    height=0.55,
    wall=0.10,
    soil_z=0.47,
    seed=3,
    ball_r=0.27,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rng = random.Random(p["seed"])
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    stone, soil, leaf, box = cc.limestone_mat(), cc.soil_mat(), cc.foliage_mat(), cc.boxwood_mat()

    L, W, H, t = p["length"], p["width"], p["height"], p["wall"]
    cc.rbox(f"{n}_Base", (L - 2 * t + 0.002, W - 2 * t + 0.002, 0.10), (0, 0, 0.05), stone, col, root, bevel=0, uv_tile=2.0)
    for side, sy in (("S", -1), ("N", 1)):
        cc.rbox(f"{n}_Wall_{side}", (L, t, H), (0, sy * (W / 2 - t / 2), H / 2), stone, col, root,
                bevel=0.012, uv_tile=2.0)
    for side, sx in (("W", -1), ("E", 1)):
        cc.rbox(f"{n}_End_{side}", (t, W - 2 * t + 0.002, H), (sx * (L / 2 - t / 2), 0, H / 2), stone, col, root,
                bevel=0.012, uv_tile=2.0)
    cc.rbox(f"{n}_Soil", (L - 2 * t, W - 2 * t, p["soil_z"] - 0.09), (0, 0, 0.09 + (p["soil_z"] - 0.09) / 2),
            soil, col, root, bevel=0, uv_tile=0)

    # clipped boxwood balls
    zs = p["soil_z"]
    ball_x = [-L * 0.39, 0.0, L * 0.39] if L > 2.6 else [0.0]
    for i, bx in enumerate(ball_x):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=p["ball_r"])
        for v in bm.verts:
            v.co.z *= 0.86
            v.co *= 1 + 0.035 * (rng.random() - 0.5)
        ob = common.mesh_object(f"{n}_Boxwood{i}", bm, col, box, root)
        ob.location = (bx, 0, zs + p["ball_r"] * 0.74)

    # grass clusters: five crossed cards each
    cb = bmesh.new()
    uvl = cb.loops.layers.uv.new("UVMap")
    slots = [x for x in (-L * 0.25, -L * 0.14, L * 0.14, L * 0.25)
             if all(abs(x - b) > p["ball_r"] + 0.14 for b in ball_x)]
    for k, x in enumerate(slots):
        cell = "grassA" if k % 2 == 0 else "grassB"
        size = rng.uniform(0.78, 0.95) if cell == "grassA" else rng.uniform(0.55, 0.7)
        base = Vector((x + rng.uniform(-0.05, 0.05), rng.uniform(-0.08, 0.08), zs - 0.02))
        a0 = rng.uniform(0, math.pi)
        for j in range(5):
            ang = a0 + j * math.pi / 5
            right = Vector((math.cos(ang), math.sin(ang), 0)) * size * 0.5
            cc.add_card(cb, uvl, base + Vector((0, 0, size * 0.5)), right, Vector((0, 0, size * 0.5)), cell,
                        flip=rng.random() < 0.5)
    common.mesh_object(f"{n}_Grass", cb, col, leaf, root, smooth=False)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
