"""Guest desk chair: slim tapered oak legs, a linen-upholstered seat and a curved
sage back panel between two oak uprights. Faces -Y; origin is the floor centre."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402
import guest_wardrobe  # noqa: E402

importlib.reload(guest_mats)
importlib.reload(guest_wardrobe)
common = guest_mats.common

NAME = "GuestChair"

P = dict(name=NAME, width=0.46, depth=0.46, seat_h=0.46, back_h=0.84, leg=0.034)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    oak, linen, sage = guest_mats.oak(), guest_mats.linen(), guest_mats.sage()
    own = (col, root, n)
    A = guest_mats.add
    W, D, SH, BH, L = p["width"], p["depth"], p["seat_h"], p["back_h"], p["leg"]
    hx, hy = W / 2 - L / 2, D / 2 - L / 2
    rail_h = 0.06
    for s, sx in (("L", -1), ("R", 1)):
        # front legs: straight taper
        A(own, f"LegF_{s}", guest_mats.taper_bmesh(L, 0.022, SH - 0.06), oak, (sx * hx, -hy, (SH - 0.06) / 2), 0.002)
        # back legs run up into the back uprights, raked back
        bl = A(own, f"LegB_{s}", guest_mats.taper_bmesh(L, 0.022, SH - 0.06), oak, (sx * hx, hy, (SH - 0.06) / 2), 0.002)
        # back upright above the seat, leaning back
        up_h = BH - (SH - 0.06)
        ob = common.mesh_object(f"{n}_Upright_{s}", common.box_bmesh((0.03, 0.026, up_h)), col, oak, root)
        ob.rotation_euler = (math.radians(-9), 0, 0)
        ob.location = (sx * hx, hy + 0.012 + math.sin(math.radians(9)) * up_h / 2, SH - 0.06 + up_h / 2 * math.cos(math.radians(9)))
        common.add_bevel(ob, 0.002, segments=2)
        common.box_uv(ob, 0.5)
    # seat frame rails
    A(own, "RailF", common.box_bmesh((W - 0.02, 0.03, rail_h)), oak, (0, -hy, SH - 0.06 - rail_h / 2 + rail_h), 0.002)
    A(own, "RailB", common.box_bmesh((W - 0.02, 0.03, rail_h)), oak, (0, hy, SH - 0.06 - rail_h / 2 + rail_h), 0.002)
    for s, sx in (("L", -1), ("R", 1)):
        A(own, f"RailS_{s}", common.box_bmesh((0.03, D - 0.02, rail_h)), oak, (sx * hx, 0, SH - 0.06 - rail_h / 2 + rail_h), 0.002)
    # seat cushion
    seat = common.mesh_object(f"{n}_Seat", common.cushion_bmesh((W - 0.01, D - 0.01, 0.07), cuts=3, edge=0.02,
                              crown={"+z": 0.014}), col, linen, root)
    seat.location = (0, 0, SH - 0.035)
    common.add_subsurf(seat)
    common.box_uv(seat, 0.25)
    # welt round the seat's top edge
    pts = common.piping_loop((W - 0.01, D - 0.01, 0.07), "z", 0.02 / 6, 0.02 * 0.9)[0]
    # (parented to the seat, so consolidate() leaves the seat whole and solid)
    sp = common.tube_object(f"{n}_Seat_Piping", pts, 0.0035, col, linen, seat, closed=True, profile_res=0)
    common.box_uv(sp, 0.25)
    # side stretchers between the legs, low down
    for s_, sx in (("L", -1), ("R", 1)):
        A(own, f"Stretcher_{s_}", common.box_bmesh((0.018, D - 0.05, 0.022)), oak, (sx * hx, 0, 0.17), 0.002)
    # back panel: a gently curved sage cushion
    bsize = (W - 0.07, 0.04, 0.28)
    bbm = common.cushion_bmesh(bsize, cuts=3, edge=0.016, crown={"-y": 0.012})
    bend = 0.022                                   # the back wraps round the sitter
    for v in bbm.verts:
        v.co.y += bend * (1 - (2 * v.co.x / bsize[0]) ** 2) - bend
    bp = common.mesh_object(f"{n}_BackPanel", bbm, col, sage, root)
    t = math.radians(-9)
    zc = SH - 0.06 + 0.42
    bp.rotation_euler = (t, 0, 0)
    bp.location = (0, hy + 0.012 - 0.03 + math.sin(math.radians(9)) * (zc - (SH - 0.06)) , zc)
    common.add_subsurf(bp)
    common.box_uv(bp, 0.25)
    bpts = [v.copy() for v in common.piping_loop(bsize, "y", 0.016 / 6, 0.016 * 0.9)[1]]
    for v in bpts:
        v.y += bend * (1 - (2 * v.x / bsize[0]) ** 2) - bend
    bpp = common.tube_object(f"{n}_BackPanel_Piping", bpts, 0.0032, col, sage, bp, closed=True, profile_res=0)
    common.box_uv(bpp, 0.25)
    guest_wardrobe.fix_oak(root)
    parts = guest_mats.consolidate(root, max_dim=0.55)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
