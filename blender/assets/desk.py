"""Executive desk: walnut top and modesty panel on two polished steel sled
frames (same family as the lounge chair). Visitor side faces -Y; the person
sitting at the desk is on +Y. Origin is the floor centre."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)

NAME = "Desk"

P = dict(
    name=NAME,
    top=(2.0, 0.9, 0.045),     # width, depth, thickness
    height=0.74,               # top surface
    corner=0.02,               # plan-view corner radius of the top
    tube_r=0.014,
    bend_r=0.07,
    frame_inset=0.14,          # frames sit this far in from the top's ends
    frame_depth_inset=0.08,
    modesty=(1.5, 0.018, 0.36),
    modesty_y=-0.32,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    walnut = common.pbr_material("M_Walnut", (0.105, 0.042, 0.016), roughness=0.5, coat=0.25)
    common.set_base_color_map(walnut, textures.load(textures.walnut()))
    steel = common.pbr_material("M_Steel_Polished", (0.85, 0.85, 0.86), roughness=0.18, metallic=1.0)

    w, d, t = p["top"]
    top = common.mesh_object(f"{n}_Top", common.rounded_slab_bmesh(w, d, t, p["corner"]),
                             col, walnut, root)
    top.location = (0, 0, p["height"] - t / 2)
    common.add_bevel(top, 0.005)

    r = p["tube_r"]
    z_rail = p["height"] - t - r
    hd = d / 2 - p["frame_depth_inset"]
    for side, sx in (("L", -1), ("R", 1)):
        x = sx * (w / 2 - p["frame_inset"])
        pts = common.sled_loop(x, -hd, hd, z_rail, r, p["bend_r"])
        common.tube_object(f"{n}_Frame_{side}", pts, r, col, steel, root)

    mw, mt, mh = p["modesty"]
    panel = common.mesh_object(f"{n}_ModestyPanel", common.box_bmesh((mw, mt, mh)), col, walnut, root)
    panel.location = (0, p["modesty_y"], p["height"] - t - mh / 2)
    common.add_bevel(panel, 0.003)

    for ob in (top, panel):
        common.box_uv(ob, tile=0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
