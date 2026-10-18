"""Long dining table for 12-14: a thick walnut top with soft corners over a recessed
smoked-oak under-plate (so it appears to float), two slab trestle ends on bronze
plinths and a smoked-oak stretcher beam.

Units are metres. Faces -Y (long axis along X), origin at the floor centre.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "DiningTable"


def grain_along_length(ob):
    """The walnut map's grain runs along v; swap u/v so it follows the table's length."""
    uv = ob.data.uv_layers["UVMap"]
    for d in uv.data:
        d.uv = (d.uv[1], d.uv[0])

P = dict(
    name=NAME,
    length=5.2,
    width=1.3,
    height=0.76,
    top_t=0.05,
    corner=0.10,
    leg_t=0.10,            # slab thickness (along x)
    leg_w=0.92,            # slab width (along y)
    leg_inset=1.0,        # slab centre from the table end
    plinth_h=0.03,
    stretcher=(0.09, 0.11),   # width (y), height (z)
    stretcher_z=0.48,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    walnut = materials.walnut()
    oak = materials.smoked_oak()
    bronze = materials.bronze()

    L, W, H, T = p["length"], p["width"], p["height"], p["top_t"]
    top = common.mesh_object(f"{n}_Top", common.rounded_slab_bmesh(L, W, T, p["corner"]),
                             col, walnut, root)
    top.location = (0, 0, H - T / 2)
    common.add_bevel(top, 0.008, 3)
    common.box_uv(top, 0.5)
    grain_along_length(top)

    under_t = 0.035
    plate = common.mesh_object(
        f"{n}_Underplate", common.rounded_slab_bmesh(L - 0.34, W - 0.34, under_t, 0.06),
        col, oak, root)
    plate.location = (0, 0, H - T - under_t / 2 + 0.002)
    common.add_bevel(plate, 0.004, 2)
    common.box_uv(plate, 0.5)

    ph = p["plinth_h"]
    leg_top = H - T - under_t + 0.004
    lh = leg_top - ph
    for side, sx in (("L", -1), ("R", 1)):
        x = sx * (L / 2 - p["leg_inset"])
        leg = common.mesh_object(f"{n}_Leg_{side}", common.box_bmesh((p["leg_t"], p["leg_w"], lh)),
                                 col, oak, root)
        leg.location = (x, 0, ph + lh / 2)
        common.add_bevel(leg, 0.006, 2)
        common.box_uv(leg, 0.5)
        foot = common.mesh_object(f"{n}_Plinth_{side}",
                                  common.box_bmesh((p["leg_t"] + 0.06, p["leg_w"] + 0.08, ph)),
                                  col, bronze, root)
        foot.location = (x, 0, ph / 2)
        common.add_bevel(foot, 0.006, 2)
        common.box_uv(foot, 0.5)

    sw, sz = p["stretcher"]
    span = L - 2 * p["leg_inset"]
    bar = common.mesh_object(f"{n}_Stretcher", common.box_bmesh((span + p["leg_t"], sw, sz)),
                             col, oak, root)
    bar.location = (0, 0, p["stretcher_z"])
    common.add_bevel(bar, 0.005, 2)
    common.box_uv(bar, 0.5)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
