"""Tasting table for the cellar: a thick honed white-marble top on two chunky smoked-oak
slab legs joined by a recessed oak apron, with a round bronze foot rail along each long
side. Counter height (0.92 m) for tall stools.

Units are metres. Long axis along X, faces -Y, origin at the floor centre.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
sys.path.insert(0, HERE)
import dining_table  # noqa: E402  (profiled slab edge)

importlib.reload(dining_table)
importlib.reload(materials)
importlib.reload(textures)

NAME = "DiningTastingTable"

P = dict(
    name=NAME,
    length=3.0,
    width=1.0,
    height=0.92,
    top_t=0.045,
    corner=0.05,
    leg_t=0.12,
    leg_w=0.74,
    leg_inset=0.55,
    rail_z=0.25,
    rail_off=0.50,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    oak = materials.smoked_oak()
    bronze = materials.bronze()
    marble = common.pbr_material("M_Marble_White", (0.8, 0.79, 0.77), roughness=0.3)
    common.set_base_color_map(marble, textures.load(textures.marble()))

    L, W, H, T = p["length"], p["width"], p["height"], p["top_t"]
    # honed marble slab: eased top arris, a square 30 mm face, then a bevel back underneath so
    # the slab reads thinner than it is
    prof = [(0.004, 0.0), (0.0008, -0.0012), (0.0, -0.004), (0.0, -0.03), (0.003, -0.033), (0.02, -T)]
    top = common.mesh_object(f"{n}_Top", dining_table.profiled_slab_bmesh(L, W, p["corner"], prof, segments=6),
                             col, marble, root)
    top.location = (0, 0, H)
    common.box_uv(top, 1.0)

    apron_t = 0.07
    apron = common.mesh_object(f"{n}_Apron", common.box_bmesh((L - 0.5, W - 0.34, apron_t)), col, oak, root)
    apron.location = (0, 0, H - T - apron_t / 2 + 0.002)
    common.add_bevel(apron, 0.004, 2)
    common.box_uv(apron, 0.5)

    lt, lw = p["leg_t"], p["leg_w"]
    lh = H - T - apron_t + 0.01
    for side, sx in (("L", -1), ("R", 1)):
        x = sx * (L / 2 - p["leg_inset"])
        leg = common.mesh_object(f"{n}_Leg_{side}", common.box_bmesh((lt, lw, lh)), col, oak, root)
        leg.location = (x, 0, lh / 2)
        common.add_bevel(leg, 0.006, 2)
        common.box_uv(leg, 0.5)
        foot = common.mesh_object(f"{n}_Foot_{side}", common.box_bmesh((lt + 0.05, lw + 0.06, 0.02)), col, bronze, root)
        foot.location = (x, 0, 0.01)
        common.add_bevel(foot, 0.003, 1)
        common.box_uv(foot, 0.5)

    span = L - 2 * p["leg_inset"]
    ro = p["rail_off"]
    for sy in (-1, 1):
        pts = [(-span / 2 - lt / 2, sy * (lw / 2 - 0.005), p["rail_z"]),
               (-span / 2 - lt / 2 - 0.0, sy * ro, p["rail_z"]),
               (span / 2 + lt / 2, sy * ro, p["rail_z"]),
               (span / 2 + lt / 2, sy * (lw / 2 - 0.005), p["rail_z"])]
        pts = common.fillet_polyline(pts, 0.05, segments=5, closed=False)
        common.tube_object(f"{n}_FootRail_{'F' if sy < 0 else 'B'}", pts, 0.018, col, bronze, root,
                           closed=False, profile_res=3)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
