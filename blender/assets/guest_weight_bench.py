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


def drop_underside(ob, z_cut):
    """Apply the modifiers and delete the pad's flat underside (it sits on its board)."""
    import bmesh
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear()
    bm = bmesh.new()
    bm.from_mesh(me)
    gone = [f for f in bm.faces if f.normal.z < -0.9 and max(v.co.z for v in f.verts) < z_cut]
    bmesh.ops.delete(bm, geom=gone, context="FACES")
    old = ob.data
    name = old.name
    bm.to_mesh(me)
    bm.free()
    ob.data = me
    bpy.data.meshes.remove(old)
    me.name = name


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
        # transport wheels on the head-end foot (tip the bench up by the seat to roll it)
        A(own, f"WheelF{sx}", guest_mats.cyl_bmesh(0.034, 0.028, seg=14, axis="x"), rub, (sx * 0.295, -0.52, 0.034), 0)
        A(own, f"HubF{sx}", guest_mats.cyl_bmesh(0.013, 0.032, seg=8, axis="x"), gr, (sx * 0.295, -0.52, 0.034), 0)
    A(own, "UprightRear", common.box_bmesh((0.06, 0.05, SH - 0.1)), gr, (0, 0.46, (SH - 0.1) / 2 + 0.03), 0.006)
    A(own, "UprightFront", common.box_bmesh((0.06, 0.05, SH - 0.1)), gr, (0, -0.52, (SH - 0.1) / 2 + 0.03), 0.006)
    # seat pad
    seat = common.mesh_object(f"{n}_Seat", common.cushion_bmesh((0.30, 0.36, 0.062), cuts=3, edge=0.022,
                              crown={"+z": 0.012}), col, pad, root)
    seat.location = (0, 0.30, SH - 0.031)
    common.add_subsurf(seat)
    drop_underside(seat, -0.029)
    common.box_uv(seat, 0.25)
    A(own, "SeatBoard", common.box_bmesh((0.28, 0.34, 0.014)), gr, (0, 0.30, SH - 0.062 - 0.007 + 0.002), 0.003)
    # back pad: hinged at the seat's front edge, rising toward -Y
    from mathutils import Vector
    top0 = Vector((0, 0.115, SH))
    d = Vector((0, -math.cos(inc), math.sin(inc)))
    nrm = Vector((0, math.sin(inc), math.cos(inc)))
    bl = 0.82
    back = common.mesh_object(f"{n}_Back", common.cushion_bmesh((0.30, bl, 0.062), cuts=4, edge=0.022,
                              crown={"+z": 0.012}), col, pad, root)
    back.rotation_euler = (-inc, 0, 0)
    back.location = top0 + d * (bl / 2 + 0.01) - nrm * 0.031
    common.add_subsurf(back)
    drop_underside(back, -0.029)
    common.box_uv(back, 0.25)
    board = common.mesh_object(f"{n}_BackBoard", common.box_bmesh((0.28, bl - 0.02, 0.014)), col, gr, root)
    board.rotation_euler = (-inc, 0, 0)
    board.location = top0 + d * (bl / 2 + 0.01) - nrm * 0.067
    common.add_bevel(board, 0.003, 2)
    common.box_uv(board, 0.5)
    # adjustment ladder: a notched steel bar under the back pad that the strut drops into
    lad0 = top0 + d * 0.30 - nrm * 0.076
    for k in range(5):
        q = lad0 + d * (0.07 * k)
        A(own, f"Notch{k}", common.box_bmesh((0.07, 0.012, 0.022)), gr, tuple(q), 0.002)
    under = top0 + d * (bl * 0.72) - nrm * 0.075
    strut = common.tube_object(f"{n}_Strut", [(0, -0.20, SH - 0.08), tuple(under)], 0.016, col, gr, root, closed=False, profile_res=2)
    common.box_uv(strut, 0.5)
    parts = guest_mats.consolidate(root, max_dim=0.35)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
