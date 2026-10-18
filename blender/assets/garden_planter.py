"""Square limestone planter with a clipped boxwood ball, for the head of the garden.
0.95 m square, 0.7 m tall plus the ball (1.45 m overall). Origin at the floor centre."""
import importlib
import os
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garden_common as gc  # noqa: E402

importlib.reload(gc)
common, outdoor = gc.common, gc.outdoor

NAME = "GardenPlanter"

P = dict(name=NAME, size=0.95, height=0.7, wall=0.1, ball_r=0.46)


def build(**overrides):
    p = {**P, **overrides}
    col, root = gc.new_asset(p["name"])
    s, h, t = p["size"], p["height"], p["wall"]
    b = gc.Builder()
    stone, soil, leaf = gc.coping(), outdoor.soil(), outdoor.foliage()
    b.box(stone, (-s / 2, -s / 2, 0), (s / 2, s / 2, h), skip=("-z", "+z"))
    # rim (top ring) and soil
    for (x0, y0, x1, y1) in ((-s / 2, -s / 2, s / 2, -s / 2 + t), (-s / 2, s / 2 - t, s / 2, s / 2),
                             (-s / 2, -s / 2 + t, -s / 2 + t, s / 2 - t), (s / 2 - t, -s / 2 + t, s / 2, s / 2 - t)):
        b.grid(stone, (x0, y0, h), (x1 - x0, 0, 0), (0, y1 - y0, 0))
    b.grid(soil, (-s / 2 + t, -s / 2 + t, h - 0.06), (s - 2 * t, 0, 0), (0, s - 2 * t, 0))
    b.finish(p["name"], col, root)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=p["ball_r"])
    for v in bm.verts:
        v.co.z *= 0.9
    ob = common.mesh_object(f"{p['name']}_Boxwood", bm, col, leaf, root)
    ob.location = (0, 0, h + p["ball_r"] * 0.7)
    common.box_uv(ob, tile=1.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
