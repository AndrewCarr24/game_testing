"""Teak sun lounger: a full-length frame (side rails, cross rails, legs at the foot,
legs and two small wheels at the head end) with a slatted seat deck and a slatted back
section that hinges up out of the frame on a U-shaped prop resting in notched racks.
A sand-linen mattress in two piped parts and a clay headrest cushion.
Foot end toward -Y (it faces -Y like a chair), head end at +Y. Origin: floor centre.
Units are metres."""
import importlib
import math
import os
import sys

import mathutils

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import courtyard_common as cc  # noqa: E402
import courtyard_sofa as sofa  # noqa: E402  (welt / cushion helpers)

importlib.reload(cc)
importlib.reload(sofa)
common = cc.common
rbox = cc.rbox

NAME = "CourtyardLounger"

P = dict(
    name=NAME,
    width=0.74,
    length=2.05,
    frame_z=0.34,         # top of the rails
    hinge_y=0.05,         # y where the back section hinges
    back_deg=36.0,
    back_len=0.95,
    slat_w=0.062,
    slat_gap=0.016,
    mattress_t=0.09,
    head_y=0.851,         # head end of the frame (inside of the end rail)
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    teak, sand, clay = cc.teak_mat(), cc.sand_fabric(), cc.clay_fabric()
    from lib import materials
    black = materials.black_metal()

    W, L, fz = p["width"], p["length"], p["frame_z"]
    y_foot, hinge, y_head = -L / 2 + 0.02, p["hinge_y"], p["head_y"]
    rh, rt = 0.06, 0.045
    leg = 0.05
    frame_len = y_head - y_foot

    # full-length side rails; legs at the foot, legs + wheels at the head
    for side, sx in (("L", -1), ("R", 1)):
        x = sx * (W / 2 - rt / 2)
        rbox(f"{n}_Rail{side}", (rt, frame_len, rh), (x, (y_foot + y_head) / 2, fz - rh / 2), teak, col, root,
             bevel=0.006, seg=2)
        xl = sx * (W / 2 - rt - leg / 2 + 0.002)          # legs tucked inside the rails
        rbox(f"{n}_LegFoot{side}", (leg, leg, fz - rh), (xl, y_foot + 0.07, (fz - rh) / 2), teak, col, root,
             bevel=0.004, seg=1)
        rbox(f"{n}_LegHinge{side}", (leg, leg, fz - rh), (xl, y_head - 0.10, (fz - rh) / 2), teak, col, root,
             bevel=0.004, seg=1)
        w = cc.lathe([(0.0, -0.016), (0.052, -0.016), (0.06, -0.008), (0.06, 0.008), (0.052, 0.016), (0.0, 0.016)],
                     16, f"{n}_Wheel{side}", col, black, root, sharp=30)
        w.rotation_euler = (0, math.radians(90), 0)
        w.location = (sx * (W / 2 + 0.005), y_head - 0.10, 0.061)
        rbox(f"{n}_Axle{side}", (0.07, 0.016, 0.016), (sx * (W / 2 - 0.035), y_head - 0.10, 0.061), black, col, root,
             bevel=0, uv_tile=0)
    inner = W - 2 * rt
    for nm, y in (("CrossFoot", y_foot + 0.07), ("CrossHinge", y_head - 0.10), ("CrossMid", hinge - 0.02)):
        rbox(f"{n}_{nm}", (inner + 0.004, 0.045, 0.05), (0, y, fz - rh - 0.0), teak, col, root, bevel=0.004, seg=1)
    rbox(f"{n}_EndFoot", (W, 0.035, rh), (0, y_foot - 0.0175 + 0.001, fz - rh / 2), teak, col, root, bevel=0.006, seg=2)
    rbox(f"{n}_EndHead", (W, 0.035, rh), (0, y_head + 0.0175 - 0.001, fz - rh / 2), teak, col, root, bevel=0.006, seg=2)

    # slat deck of the flat part, resting on battens inside the rails
    sw, sg = p["slat_w"], p["slat_gap"]
    for side, sx in (("L", -1), ("R", 1)):
        rbox(f"{n}_Batten{side}", (0.022, hinge - y_foot, 0.022), (sx * (inner / 2 - 0.011), (y_foot + hinge) / 2,
             fz - 0.032), teak, col, root, bevel=0, uv_tile=0.5)
    n_slat = int((hinge - y_foot - 0.01) / (sw + sg))
    for i in range(n_slat):
        y = y_foot + 0.01 + sw / 2 + i * (sw + sg)
        rbox(f"{n}_Slat{i}", (inner - 0.006, sw, 0.022), (0, y, fz - 0.011), teak, col, root, bevel=0.003, seg=1)

    # back section: its own rails and slats, rotated up about the hinge line
    a = math.radians(p["back_deg"])
    bl = p["back_len"]
    hinge_pt = mathutils.Vector((0.0, hinge, fz))
    rot = mathutils.Matrix.Rotation(a, 3, "X")

    def place(ob, ly, lz=0.0, lx=0.0):
        v = rot @ mathutils.Vector((lx, ly, lz))
        ob.location = hinge_pt + v
        ob.rotation_euler = (a, 0, 0)
        return ob

    bw = inner - 0.012
    for side, sx in (("L", -1), ("R", 1)):
        place(rbox(f"{n}_BackRail{side}", (0.035, bl, 0.045), (0, 0, 0), teak, col, root, bevel=0.004, seg=1),
              bl / 2, -0.0225 - 0.012, sx * (bw / 2 - 0.0175))
    place(rbox(f"{n}_BackRailTop", (bw, 0.035, 0.045), (0, 0, 0), teak, col, root, bevel=0.004, seg=1),
          bl - 0.0175, -0.0225 - 0.012)
    ns = int((bl - 0.05) / (sw + sg))
    for i in range(ns):
        place(rbox(f"{n}_BackSlat{i}", (bw, sw, 0.022), (0, 0, 0), teak, col, root, bevel=0.003, seg=1),
              0.02 + sw / 2 + i * (sw + sg), -0.001)

    # U-shaped prop: two arms from the back rails down to a cross bar resting in notched
    # racks screwed to the inside of the side rails
    pivot_l = 0.62 * bl
    top = hinge_pt + rot @ mathutils.Vector((0, pivot_l, -0.04))
    rack_z = fz - rh + 0.015
    bar = mathutils.Vector((0, hinge + 0.50, rack_z + 0.03))
    v = top - bar
    ln = v.length
    ang = -math.atan2(v.y, v.z)
    for side, sx in (("L", -1), ("R", 1)):
        xa = sx * (bw / 2 - 0.05)
        s = rbox(f"{n}_Strut{side}", (0.03, 0.03, ln), (xa, (top.y + bar.y) / 2, (top.z + bar.z) / 2), teak, col, root,
                 bevel=0.003, seg=1)
        s.rotation_euler = (ang, 0, 0)
        rack = rbox(f"{n}_Rack{side}", (0.02, 0.30, 0.03), (sx * (inner / 2 - 0.01), hinge + 0.46, rack_z),
                    teak, col, root, bevel=0.002, seg=1)
    rbox(f"{n}_StrutBar", (inner - 0.03, 0.03, 0.03), (0, bar.y, bar.z), teak, col, root, bevel=0.003, seg=1)

    # mattress: seat part and back part, piped; headrest cushion
    mt = p["mattress_t"]
    mw = W - 0.05
    e = 0.03
    seat_len = hinge - y_foot + 0.005
    size = (mw, seat_len, mt)
    loc = (0, (y_foot + hinge) / 2 - 0.002, fz + mt / 2)
    sofa.cushion(f"{n}_MattressSeat", size, {"+z": 0.014, "-y": 0.006}, col, sand, root, loc, edge=e)
    sofa.face_welt(f"{n}_MattressSeat_PipingTop", size, "z", 1, e, 0.005, col, sand, root, loc)
    sofa.face_welt(f"{n}_MattressSeat_PipingBottom", size, "z", -1, e, 0.005, col, sand, root, loc)
    size = (mw, bl - 0.01, mt)
    bm = sofa.cushion(f"{n}_MattressBack", size, {"+z": 0.014}, col, sand, root, (0, 0, 0), edge=e)
    place(bm, bl / 2 + 0.003, 0.011 + mt / 2)
    pw = sofa.face_welt(f"{n}_MattressBack_PipingTop", size, "z", 1, e, 0.005, col, sand, root, (0, 0, 0))
    place(pw, bl / 2 + 0.003, 0.011 + mt / 2)
    size = (mw - 0.12, 0.28, 0.10)
    pil = sofa.cushion(f"{n}_Pillow", size, {"+z": 0.045, "-z": 0.01, "-y": 0.025, "+y": 0.025, "+x": -0.012, "-x": -0.012},
                       col, clay, root, (0, 0, 0), edge=0.045)
    place(pil, bl - 0.19, 0.011 + mt + 0.04)
    pp = sofa.face_welt(f"{n}_Pillow_Piping", size, "z", 1, 0.045, 0.0045, col, clay, root, (0, 0, 0))
    place(pp, bl - 0.19, 0.011 + mt + 0.04)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
