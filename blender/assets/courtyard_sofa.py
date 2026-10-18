"""Outdoor lounge sofa: slatted teak frame (legs, rails, slat arms and back) with deep
sand-linen seat and back cushions and two scatter pillows. Also the generator behind
courtyard_armchair (same construction, one seat wide).

Front faces -Y, origin at the floor centre. Units are metres."""
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

NAME = "CourtyardSofa"

P = dict(
    name=NAME,
    width=2.60,
    depth=0.98,
    seat_n=3,              # seat cushions across
    leg_h=0.17,
    arm_w=0.13,
    arm_h=0.62,
    back_h=0.80,
    slat_h=0.046,
    slat_gap=0.018,
    slat_t=0.034,
    seat_t=0.17,
    back_cushion_h=0.46,
    back_cushion_t=0.15,
    back_tilt_deg=13.0,
    pillows=2,
)


def slat_rows(z0, z1, h, gap):
    n = max(1, round((z1 - z0 + gap) / (h + gap)))
    hh = (z1 - z0 - gap * (n - 1)) / n
    return [(z0 + i * (hh + gap) + hh / 2, hh) for i in range(n)]


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    teak = cc.teak_mat()
    sand, sage, clay = cc.sand_fabric(), cc.sage_fabric(), cc.clay_fabric()

    W, D = p["width"], p["depth"]
    t = p["slat_t"]
    aw = p["arm_w"]
    lh = p["leg_h"]
    rail_z0, rail_h = lh, 0.075

    # legs
    lx, ly = W / 2 - 0.05, D / 2 - 0.05
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        rbox(f"{n}_Leg{i}", (0.06, 0.06, lh + 0.01), (sx * lx, sy * ly, (lh + 0.01) / 2), teak, col, root,
             bevel=0.004, uv_tile=0.5)
    # base rails and deck
    rbox(f"{n}_RailFront", (W - 0.12, 0.04, rail_h), (0, -D / 2 + 0.03, rail_z0 + rail_h / 2), teak, col, root, bevel=0.004)
    rbox(f"{n}_RailBack", (W - 0.12, 0.04, rail_h), (0, D / 2 - 0.03, rail_z0 + rail_h / 2), teak, col, root, bevel=0.004)
    deck_top = rail_z0 + rail_h
    rbox(f"{n}_Deck", (W - 0.08, D - 0.12, 0.03), (0, 0, deck_top - 0.015), teak, col, root, bevel=0.003)

    # slatted side panels (arms) and back
    for side, sx in (("L", -1), ("R", 1)):
        for k, (zc, hh) in enumerate(slat_rows(rail_z0, p["arm_h"], p["slat_h"], p["slat_gap"])):
            rbox(f"{n}_ArmSlat{side}{k}", (t, D - 0.02, hh), (sx * (W / 2 - t / 2), 0, zc), teak, col, root,
                 bevel=0.003, seg=1)
        rbox(f"{n}_ArmCap{side}", (aw, D, 0.032), (sx * (W / 2 - aw / 2), 0, p["arm_h"] + 0.016), teak, col, root,
             bevel=0.006, seg=2)
        rbox(f"{n}_ArmPost{side}", (0.05, 0.05, p["arm_h"] - rail_z0), (sx * (W / 2 - aw + 0.05), -D / 2 + 0.04,
             (rail_z0 + p["arm_h"]) / 2), teak, col, root, bevel=0.003, seg=1)
    for k, (zc, hh) in enumerate(slat_rows(rail_z0, p["back_h"], p["slat_h"], p["slat_gap"])):
        rbox(f"{n}_BackSlat{k}", (W - 2 * t + 0.004, t, hh), (0, D / 2 - t / 2, zc), teak, col, root,
             bevel=0.003, seg=1)
    rbox(f"{n}_BackCap", (W, 0.09, 0.03), (0, D / 2 - 0.045, p["back_h"] + 0.015), teak, col, root, bevel=0.006, seg=2)

    # cushions
    inner = W - 2 * t
    ns = p["seat_n"]
    cw = inner / ns
    seat_front = -D / 2 + 0.012
    seat_back = D / 2 - t - 0.02
    sd = seat_back - seat_front
    st = p["seat_t"]
    seat_z0 = deck_top
    for i in range(ns):
        cx = -inner / 2 + cw * (i + 0.5)
        size = (cw - 0.012, sd, st)
        ob = common.mesh_object(f"{n}_SeatCushion{i}",
                                common.cushion_bmesh(size, cuts=3, edge=0.035, crown={"+z": 0.022, "+x": 0.006, "-x": 0.006, "-y": 0.01}),
                                col, sand, root)
        ob.location = (cx, (seat_front + seat_back) / 2, seat_z0 + st / 2)
        common.add_subsurf(ob)
        common.box_uv(ob, tile=0.25)
    bh, bt = p["back_cushion_h"], p["back_cushion_t"]
    tilt = math.radians(p["back_tilt_deg"])
    seat_top = seat_z0 + st + 0.012
    for i in range(ns):
        cx = -inner / 2 + cw * (i + 0.5)
        size = (cw - 0.012, bt, bh)
        ob = common.mesh_object(f"{n}_BackCushion{i}",
                                common.cushion_bmesh(size, cuts=3, edge=0.035, crown={"+y": 0.02, "-y": 0.02, "+x": 0.006, "-x": 0.006}),
                                col, sand, root)
        # bottom edge sits on the seat against the back slats, top leans back
        by = seat_back - bt / 2 - 0.005 + (bh / 2) * math.sin(tilt) * 0.5
        ob.location = (cx, by, seat_top + (bh / 2) * math.cos(tilt))
        ob.rotation_euler = (-tilt, 0, 0)
        common.add_subsurf(ob)
        common.box_uv(ob, tile=0.25)
    # scatter pillows
    mats = [clay, sage]
    for k in range(p["pillows"]):
        sx = -1 if k % 2 == 0 else 1
        px = sx * (inner / 2 - 0.36) if ns > 1 else 0.0
        ob = common.mesh_object(f"{n}_Pillow{k}",
                                common.cushion_bmesh((0.46, 0.13, 0.44), cuts=3, edge=0.04, crown={"+y": 0.05, "-y": 0.05}),
                                col, mats[k % 2], root)
        ob.location = (px, seat_back - bt - 0.14 + 0.02, seat_top + 0.25 + 0.0)
        ob.rotation_euler = (-math.radians(18), 0, math.radians(8 * sx))
        common.add_subsurf(ob)
        common.box_uv(ob, tile=0.25)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
