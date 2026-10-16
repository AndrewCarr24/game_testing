"""Low coffee table: white marble top on two polished steel sled frames.
Long axis along X. Origin is the floor centre."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)

NAME = "CoffeeTable"

P = dict(
    name=NAME,
    top=(1.05, 0.58, 0.03),
    height=0.38,
    corner=0.06,
    tube_r=0.011,
    bend_r=0.05,
    frame_inset=0.12,
    frame_depth_inset=0.06,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    marble = common.pbr_material("M_Marble_White", (0.8, 0.79, 0.77), roughness=0.12, coat=0.0)
    common.set_base_color_map(marble, textures.load(textures.marble()))
    steel = common.pbr_material("M_Steel_Polished", (0.85, 0.85, 0.86), roughness=0.18, metallic=1.0)

    w, d, t = p["top"]
    top = common.mesh_object(f"{n}_Top", common.rounded_slab_bmesh(w, d, t, p["corner"]),
                             col, marble, root)
    top.location = (0, 0, p["height"] - t / 2)
    common.add_bevel(top, 0.004)
    common.box_uv(top, tile=1.0)

    r = p["tube_r"]
    hd = d / 2 - p["frame_depth_inset"]
    for side, sx in (("L", -1), ("R", 1)):
        x = sx * (w / 2 - p["frame_inset"])
        pts = common.sled_loop(x, -hd, hd, p["height"] - t - r, r, p["bend_r"])
        common.tube_object(f"{n}_Frame_{side}", pts, r, col, steel, root)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
