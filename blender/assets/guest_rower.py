"""Air rower: a long graphite monorail on two legs, a caged flywheel at the front
(-Y), a sliding seat, foot plates with straps, a handle on a chain and a small
console. The rower faces -Y (flywheel end); 0.60 wide, 2.15 long, 0.95 tall."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestRower"

P = dict(name=NAME, length=2.15, width=0.60)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    gr, rub, steel = guest_mats.graphite(), guest_mats.rubber(), guest_mats.materials.steel()
    oak = guest_mats.oak()
    pad = guest_mats.pad("M_Pad_Charcoal")
    own = (col, root, n)
    A = guest_mats.add
    L, W = p["length"], p["width"]
    y0, y1 = -L / 2, L / 2
    rail_z = 0.20
    # monorail: sloped slightly up toward the flywheel
    A(own, "Rail", common.box_bmesh((0.085, L - 0.28, 0.07)), gr, (0, (y0 + 0.28 + y1) / 2, rail_z + 0.035), 0.01)
    # rear support leg (a wide T) and front support under the flywheel
    A(own, "LegRear", common.box_bmesh((W, 0.09, 0.05)), gr, (0, y1 - 0.12, 0.025), 0.008)
    A(own, "PostRear", common.box_bmesh((0.07, 0.07, rail_z)), gr, (0, y1 - 0.12, rail_z / 2), 0.006)
    for sx in (-1, 1):
        A(own, f"CapR{sx}", common.box_bmesh((0.1, 0.12, 0.03)), rub, (sx * (W / 2 - 0.05), y1 - 0.12, 0.015), 0.004)
        A(own, f"FootPost{sx}", common.box_bmesh((0.04, 0.05, 0.22)), gr, (sx * 0.17, y0 + 0.80, 0.14), 0.004)
        A(own, f"Strut{sx}", common.box_bmesh((0.05, 0.05, 0.40)), gr, (sx * 0.12, y0 + 0.33, 0.24), 0.005)
    # flywheel cage: a drum with a vented front, brass logo disc
    fw = common.mesh_object(f"{n}_Flywheel", guest_mats.cyl_bmesh(0.19, 0.2, seg=32, axis="x"), col, gr, root)
    fw.location = (0, y0 + 0.28, 0.40)
    common.add_bevel(fw, 0.01, segments=2)
    common.box_uv(fw, 0.5)
    for sx in (-1, 1):
        A(own, f"Hub{sx}", guest_mats.cyl_bmesh(0.07, 0.012, seg=20, axis="x"), steel, (sx * 0.106, y0 + 0.28, 0.40), 0)
    A(own, "FrontFoot", common.box_bmesh((W, 0.07, 0.04)), gr, (0, y0 + 0.28, 0.02), 0.006)
    A(own, "FootBar", common.box_bmesh((0.46, 0.05, 0.04)), gr, (0, y0 + 0.80, 0.02), 0.006)
    A(own, "FootBrace", common.box_bmesh((0.05, 0.05, 0.14)), gr, (0, y0 + 0.80, 0.13), 0.004)
    # foot plates and straps
    for sx in (-1, 1):
        fp = common.mesh_object(f"{n}_FootPlate{sx}", common.box_bmesh((0.12, 0.34, 0.025)), col, rub, root)
        fp.rotation_euler = (math.radians(-35), 0, 0)
        fp.location = (sx * 0.17, y0 + 0.80, 0.30)
        common.add_bevel(fp, 0.004, segments=2)
        common.box_uv(fp, 0.5)
    # console on a stalk
    A(own, "Stalk", guest_mats.cyl_bmesh(0.015, 0.40, seg=10), gr, (0, y0 + 0.28, 0.78), 0)
    cons = A(own, "Console", common.box_bmesh((0.20, 0.05, 0.14)), gr, (0, y0 + 0.28, 0.97), 0.01)
    scr = A(own, "Screen", common.box_bmesh((0.16, 0.006, 0.09)), guest_mats.screen(), (0, y0 + 0.308, 0.97), 0, tile=0.25)
    # seat sliding on the rail
    seat = common.mesh_object(f"{n}_Seat", common.cushion_bmesh((0.30, 0.30, 0.06), cuts=4, edge=0.022,
                              crown={"+z": 0.01}), col, pad, root)
    seat.location = (0, 0.55, rail_z + 0.07 + 0.045 + 0.02)
    common.add_subsurf(seat)
    common.box_uv(seat, 0.25)
    A(own, "Carriage", common.box_bmesh((0.16, 0.22, 0.04)), gr, (0, 0.55, rail_z + 0.09), 0.006)
    # handle + chain
    A(own, "Handle", guest_mats.cyl_bmesh(0.016, 0.40, seg=12, axis="x"), rub, (0, y0 + 0.95, rail_z + 0.07 + 0.017), 0)
    ch = common.tube_object(f"{n}_Chain", [(0, y0 + 0.28 + 0.19, 0.40), (0, y0 + 0.62, rail_z + 0.087), (0, y0 + 0.95, rail_z + 0.087)], 0.006, col, steel, root, closed=False, profile_res=1)
    common.box_uv(ch, 0.5)
    parts = guest_mats.consolidate(root, max_dim=0.45)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
