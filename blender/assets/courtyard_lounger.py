"""Teak sun lounger: slatted frame on four legs with two small wheels, a hinged reclined
back section, a sand-linen mattress in two parts and a bolster. Foot end toward -Y (it
faces -Y like a chair), head end at +Y. Origin: floor centre. Units are metres."""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import courtyard_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common
rbox = cc.rbox

NAME = "CourtyardLounger"

P = dict(
    name=NAME,
    width=0.74,
    length=2.05,
    frame_z=0.34,         # top of the rails
    hinge_y=0.05,         # y where the back section hinges
    back_deg=34.0,
    back_len=0.95,
    slat_w=0.062,
    slat_gap=0.016,
    mattress_t=0.09,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    teak, sand = cc.teak_mat(), cc.sand_fabric()
    from lib import materials
    black = materials.black_metal()

    W, L, fz = p["width"], p["length"], p["frame_z"]
    y_foot, hinge = -L / 2, p["hinge_y"]
    seat_len = hinge - y_foot
    rh, rt = 0.06, 0.045

    # side rails and legs for the flat part
    for side, sx in (("L", -1), ("R", 1)):
        x = sx * (W / 2 - rt / 2)
        rbox(f"{n}_Rail{side}", (rt, seat_len + 0.04, rh), (x, (y_foot + hinge) / 2 + 0.0, fz - rh / 2), teak, col, root, bevel=0.005)
        # legs: foot end (short, with wheel behind), hinge end
        rbox(f"{n}_LegFoot{side}", (0.05, 0.05, fz - rh), (x, y_foot + 0.08, (fz - rh) / 2), teak, col, root, bevel=0.004)
        rbox(f"{n}_LegHinge{side}", (0.05, 0.05, fz - rh), (x, hinge - 0.02, (fz - rh) / 2), teak, col, root, bevel=0.004)
    rbox(f"{n}_CrossFoot", (W - 2 * rt + 0.01, 0.05, 0.05), (0, y_foot + 0.08, fz - 0.1), teak, col, root, bevel=0.004)
    rbox(f"{n}_CrossHinge", (W - 2 * rt + 0.01, 0.05, 0.05), (0, hinge - 0.02, fz - 0.1), teak, col, root, bevel=0.004)
    # wheels on a black axle at the head end
    for side, sx in (("L", -1), ("R", 1)):
        w = cc.lathe([(0.0, -0.016), (0.055, -0.016), (0.06, -0.008), (0.06, 0.008), (0.055, 0.016), (0.0, 0.016)],
                     20, f"{n}_Wheel{side}", col, black, root, sharp=30)
        w.rotation_euler = (0, math.radians(90), 0)
        w.location = (sx * (W / 2 + 0.005), hinge - 0.02, 0.06)
    # slat deck (flat part)
    n_slat = int((seat_len) / (p["slat_w"] + p["slat_gap"]))
    for i in range(n_slat):
        y = y_foot + 0.03 + p["slat_w"] / 2 + i * (p["slat_w"] + p["slat_gap"])
        rbox(f"{n}_Slat{i}", (W - 0.01, p["slat_w"], 0.024), (0, y, fz + 0.012 - 0.0), teak, col, root, bevel=0.003, seg=1)

    # back section: a rotated frame with its own slats; hinge at (y=hinge, z=fz)
    a = math.radians(p["back_deg"])
    bl = p["back_len"]
    hinge_pt = (0.0, hinge, fz + 0.012)
    import mathutils
    rot = mathutils.Matrix.Rotation(a, 4, "X")         # top toward +y? (see sign below)
    # local frame: +Y along the panel, +Z up out of it; rotate about X so the far end rises
    def place(ob, ly, lz=0.0, lx=0.0):
        ob.location = hinge_pt
        v = mathutils.Vector((lx, ly, lz))
        v = mathutils.Matrix.Rotation(a, 3, "X") @ v
        ob.location = (hinge_pt[0] + v.x, hinge_pt[1] + v.y, hinge_pt[2] + v.z)
        ob.rotation_euler = (a, 0, 0)

    for side, sx in (("L", -1), ("R", 1)):
        r = rbox(f"{n}_BackRail{side}", (rt, bl, rh), (0, 0, 0), teak, col, root, bevel=0.005)
        r.location = hinge_pt
        place(r, bl / 2 + 0.01, -rh / 2 - 0.012, sx * (W / 2 - rt / 2))
    ns = int((bl - 0.04) / (p["slat_w"] + p["slat_gap"]))
    for i in range(ns):
        s = rbox(f"{n}_BackSlat{i}", (W - 0.01, p["slat_w"], 0.024), (0, 0, 0), teak, col, root, bevel=0.003, seg=1)
        place(s, 0.03 + p["slat_w"] / 2 + i * (p["slat_w"] + p["slat_gap"]), 0.0)
    # prop strut: foot on the floor, top under the middle of the back section
    top = (hinge + 0.55 * math.cos(a), fz + 0.012 - 0.03 + 0.55 * math.sin(a))
    bot = (top[0] - 0.20, 0.02)
    ln = math.hypot(top[0] - bot[0], top[1] - bot[1])
    strut = rbox(f"{n}_Strut", (0.04, 0.04, ln), (0, (top[0] + bot[0]) / 2, (top[1] + bot[1]) / 2), teak, col, root, bevel=0.004)
    strut.rotation_euler = (-math.atan2(top[0] - bot[0], top[1] - bot[1]), 0, 0)

    # mattress: seat part and back part
    mt = p["mattress_t"]
    mw = W - 0.06
    seat_m = common.mesh_object(f"{n}_MattressSeat",
                                common.cushion_bmesh((mw, seat_len - 0.02, mt), cuts=3, edge=0.03, crown={"+z": 0.015}),
                                col, sand, root)
    seat_m.location = (0, (y_foot + hinge) / 2 - 0.005, fz + 0.024 + mt / 2)
    common.add_subsurf(seat_m)
    common.box_uv(seat_m, tile=0.25)
    back_m = common.mesh_object(f"{n}_MattressBack",
                                common.cushion_bmesh((mw, bl - 0.03, mt), cuts=3, edge=0.03, crown={"+z": 0.015}),
                                col, sand, root)
    place(back_m, bl / 2 + 0.01, 0.024 + mt / 2)
    common.add_subsurf(back_m)
    common.box_uv(back_m, tile=0.25)
    # bolster at the head
    cl = cc.clay_fabric()
    pil = common.mesh_object(f"{n}_Pillow",
                             common.cushion_bmesh((mw - 0.1, 0.26, 0.10), cuts=3, edge=0.04, crown={"+z": 0.04}),
                             col, cl, root)
    place(pil, bl - 0.17, 0.024 + mt + 0.045)
    common.add_subsurf(pil)
    common.box_uv(pil, tile=0.25)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
