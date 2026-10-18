"""Adjustable weight bench: graphite frame on two rubber-capped feet, a charcoal seat
pad and a back pad inclined 35 degrees on a steel support. Long axis along Y: the
lifter's head is at -Y when lying, feet toward +Y... (the seat end is +Y); front faces
-Y (head end). Origin is the floor centre."""
import importlib
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestWeightBench"

P = dict(name=NAME, incline_deg=32.0, seat_h=0.46)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    gr, rub = guest_mats.graphite(), guest_mats.rubber()
    pad = guest_mats.pad("M_Pad_Charcoal")
    own = (col, root, n)
    A = guest_mats.add
    SH = p["seat_h"]
    inc = math.radians(p["incline_deg"])
    # spine runs along y at seat height - pad
    A(own, "Spine", common.box_bmesh((0.06, 1.08, 0.06)), gr, (0, -0.03, SH - 0.08), 0.006)
    # front (head) and rear feet: T-shaped
    A(own, "FootRear", common.box_bmesh((0.56, 0.05, 0.05)), gr, (0, 0.46, 0.025), 0.006)
    A(own, "FootFront", common.box_bmesh((0.56, 0.05, 0.05)), gr, (0, -0.52, 0.025), 0.006)
    for sx in (-1, 1):
        A(own, f"CapR{sx}", common.box_bmesh((0.06, 0.07, 0.035)), rub, (sx * 0.28, 0.46, 0.0175), 0.004)
        A(own, f"CapF{sx}", common.box_bmesh((0.06, 0.07, 0.035)), rub, (sx * 0.28, -0.52, 0.0175), 0.004)
    A(own, "UprightRear", common.box_bmesh((0.06, 0.05, SH - 0.1)), gr, (0, 0.46, (SH - 0.1) / 2 + 0.03), 0.006)
    A(own, "UprightFront", common.box_bmesh((0.06, 0.05, SH - 0.1)), gr, (0, -0.52, (SH - 0.1) / 2 + 0.03), 0.006)
    # seat pad
    seat = common.mesh_object(f"{n}_Seat", common.cushion_bmesh((0.30, 0.36, 0.075), cuts=4, edge=0.025,
                              crown={"+z": 0.012}), col, pad, root)
    seat.location = (0, 0.30, SH - 0.0375 + 0.0)
    common.add_subsurf(seat)
    common.box_uv(seat, 0.25)
    # back pad: hinged at the seat's front edge, rising toward -Y
    from mathutils import Vector
    top0 = Vector((0, 0.115, SH))
    d = Vector((0, -math.cos(inc), math.sin(inc)))
    nrm = Vector((0, math.sin(inc), math.cos(inc)))
    bl = 0.82
    back = common.mesh_object(f"{n}_Back", common.cushion_bmesh((0.30, bl, 0.075), cuts=5, edge=0.025,
                              crown={"+z": 0.012}), col, pad, root)
    back.rotation_euler = (-inc, 0, 0)
    back.location = top0 + d * (bl / 2 + 0.01) - nrm * 0.0375
    common.add_subsurf(back)
    common.box_uv(back, 0.25)
    under = top0 + d * (bl * 0.72) - nrm * 0.075
    strut = common.tube_object(f"{n}_Strut", [(0, -0.20, SH - 0.08), tuple(under)], 0.016, col, gr, root, closed=False, profile_res=2)
    common.box_uv(strut, 0.5)
    parts = guest_mats.consolidate(root, max_dim=0.35)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
