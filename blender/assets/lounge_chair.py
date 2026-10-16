"""Modern sled-base lounge chair: polished steel tube frame, walnut seat
platform / back panel / arm caps, cognac leather cushions.

Units are metres. The chair faces -Y, its origin is the floor centre.
Run inside Blender (see blender/run.py); re-running rebuilds it.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import importlib  # noqa: E402

from lib import common, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)

NAME = "LoungeChair"

P = dict(
    name=NAME,             # collection / object prefix; override to make variants
    leather_name="M_Leather_Cognac",
    # frame
    tube_r=0.011,          # tube radius (22 mm stock)
    bend_r=0.06,           # bend radius at frame corners
    half_width=0.38,       # x of the side loops' centre lines
    runner_front=-0.40,    # y where the floor runner starts (front)
    runner_back=0.38,      # y of the rear upright
    front_rake=0.06,       # front upright leans back by this much at arm height
    arm_z=0.62,            # arm tube centre height
    low_rail_z=0.26,       # cross rails supporting the seat platform
    back_rail_z=0.52,      # cross rail the back panel leans on
    # walnut
    board_t=0.025,
    board_half_width=0.36,
    back_tilt_deg=14.0,
    back_panel_h=0.52,
    back_panel_t=0.02,
    arm_cap=(0.07, 0.58, 0.022),
    # leather
    cushion_half_width=0.35,
    seat_cushion_t=0.145,
    seat_overhang=0.02,
    back_cushion_t=0.13,
    back_cushion_h=0.47,
    cushion_edge=0.028,
    piping_r=0.0045,
    # colours (linear)
    leather=(0.23, 0.075, 0.025),
    walnut=(0.105, 0.042, 0.016),
    steel=(0.85, 0.85, 0.86),
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    leather = common.pbr_material(p["leather_name"], p["leather"], roughness=0.62)
    common.set_normal_map(leather, textures.load(textures.leather_normal(), non_color=True), 0.6)
    walnut = common.pbr_material("M_Walnut", p["walnut"], roughness=0.5, coat=0.25)
    common.set_base_color_map(walnut, textures.load(textures.walnut()))
    steel = common.pbr_material("M_Steel_Polished", p["steel"], roughness=0.08, metallic=1.0)
    wood_parts, leather_parts = [], []

    r = p["tube_r"]
    yf, yb = p["runner_front"], p["runner_back"]
    y_front_top = yf + p["front_rake"]

    def front_y_at(z):  # y of the raked front upright's centre line at height z
        return yf + (z - r) / (p["arm_z"] - r) * p["front_rake"]

    # --- side loops: runner -> rear upright -> arm -> raked front upright
    for side, sx in (("L", -1), ("R", 1)):
        x = sx * p["half_width"]
        corners = [
            (x, yf, r),
            (x, yb, r),
            (x, yb, p["arm_z"]),
            (x, y_front_top, p["arm_z"]),
        ]
        pts = common.fillet_polyline(corners, p["bend_r"], segments=8, closed=True)
        common.tube_object(f"{n}_Frame_{side}", pts, r, col, steel, root, closed=True)

    # --- cross rails between the loops
    hw = p["half_width"]
    rails = {
        "RailFront": (front_y_at(p["low_rail_z"]), p["low_rail_z"]),
        "RailRear": (yb, p["low_rail_z"]),
        "RailBack": (yb, p["back_rail_z"]),
    }
    for name, (y, z) in rails.items():
        common.tube_object(f"{n}_{name}", [(-hw, y, z), (hw, y, z)], r * 0.9,
                           col, steel, root, closed=False)

    # --- walnut seat platform resting on the low rails
    board_bottom = p["low_rail_z"] + r * 0.9
    board_top = board_bottom + p["board_t"]
    by0 = rails["RailFront"][0] - 0.004
    by1 = yb - 0.004
    board = common.mesh_object(
        f"{n}_SeatBoard",
        common.box_bmesh((2 * p["board_half_width"], by1 - by0, p["board_t"])),
        col, walnut, root)
    board.location = (0, (by0 + by1) / 2, (board_bottom + board_top) / 2)
    common.add_bevel(board, 0.004)
    wood_parts.append(board)

    # --- back assembly, pivoting about the panel's rear-bottom edge so the
    #     panel's back face just touches the back rail
    tilt = math.radians(p["back_tilt_deg"])
    rail_front_y = yb - r * 0.9
    pivot_y = rail_front_y - (p["back_rail_z"] - board_top) * math.tan(tilt)
    back = common.empty(f"{n}_Back", col, (0, pivot_y, board_top))
    back.parent = root
    back.rotation_euler = (-tilt, 0, 0)

    pt = p["back_panel_t"]
    panel = common.mesh_object(
        f"{n}_BackPanel",
        common.box_bmesh((2 * p["board_half_width"], pt, p["back_panel_h"])),
        col, walnut, back)
    panel.location = (0, -pt / 2, p["back_panel_h"] / 2)
    common.add_bevel(panel, 0.004)
    wood_parts.append(panel)

    def cushion(name, size, crown, piping_axis, parent, location):
        ob = common.mesh_object(name, common.cushion_bmesh(size, edge=p["cushion_edge"], crown=crown),
                                col, leather, parent)
        ob.location = location
        common.add_subsurf(ob)
        leather_parts.append(ob)
        e = p["cushion_edge"]
        # Catmull-Clark pulls a box edge in by e/6 per axis, so centre the welt there
        for i, pts in enumerate(common.piping_loop(size, piping_axis, e / 6, e * 0.9)):
            pipe = common.tube_object(f"{name}_Piping{i}", pts, p["piping_r"], col, leather,
                                      parent, closed=True, profile_res=2)
            pipe.location = location
            leather_parts.append(pipe)
        return ob

    ct = p["back_cushion_t"]
    cw = 2 * p["cushion_half_width"]
    cushion(f"{n}_BackCushion", (cw, ct, p["back_cushion_h"]),
            {"-y": 0.018, "+y": 0.004, "+z": 0.01, "-z": 0.0, "+x": 0.006, "-x": 0.006},
            "y", back, (0, -pt - ct / 2, p["back_cushion_h"] / 2 + 0.004))

    # --- seat cushion: from the front overhang back to the back cushion's face
    back_face_y = pivot_y - (pt + ct) / math.cos(tilt)
    sy0 = by0 - p["seat_overhang"]
    sy1 = back_face_y + 0.012
    st = p["seat_cushion_t"]
    cushion(f"{n}_SeatCushion", (cw, sy1 - sy0, st),
            {"+z": 0.016, "-z": 0.0, "-y": 0.008, "+y": 0.002, "+x": 0.006, "-x": 0.006},
            "z", root, (0, (sy0 + sy1) / 2, board_top + st / 2))

    # --- walnut arm caps on the straight part of each arm tube
    cx, cy, cz = p["arm_cap"]
    for side, sx in (("L", -1), ("R", 1)):
        cap = common.mesh_object(f"{n}_ArmCap_{side}", common.box_bmesh((cx, cy, cz)),
                                 col, walnut, root)
        arm_mid = (y_front_top + p["bend_r"] + yb - p["bend_r"]) / 2
        cap.location = (sx * hw, arm_mid, p["arm_z"] + r + cz / 2 - 0.002)
        common.add_bevel(cap, 0.006)
        wood_parts.append(cap)

    for ob in wood_parts:
        common.box_uv(ob, tile=0.5)
    for ob in leather_parts:
        common.box_uv(ob, tile=0.2)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
