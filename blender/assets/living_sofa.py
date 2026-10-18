"""Low-slung modern sofa: upholstered plinth deck with squared padded arms, loose
seat and back cushions (soft crowns, piped seams), two scatter pillows, on a recessed
black plinth. Also provides `module()` which living_sectional builds on.

Units are metres. The sofa faces -Y (backrest at +Y); the origin is the floor centre.
"""
import importlib
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "LivingSofa"

P = dict(
    name=NAME,
    width=2.60,
    depth=1.00,
    fabric_name="M_Fabric_Oat",
    fabric=(0.50, 0.44, 0.35),
    pillow_name="M_Fabric_Ink",
    pillow=(0.020, 0.032, 0.060),
    pillows=2,
    arm_w=0.20,
    deck_z=(0.07, 0.27),      # plinth top, deck top
    seat_t=0.19,              # seat cushion thickness
    back_h=0.40,              # back cushion height
    back_t=0.21,
    back_tilt_deg=11.0,
    frame_back_top=0.64,
    arm_top=0.60,
    cuts=3,
    cuts_small=2,
    leg="black",              # recessed plinth colour: "black" or "bronze"
)


def cushion(col, parent, mat, name, size, crown, loc, rot=(0, 0, 0), cuts=4, edge=0.03, uv=0.25):
    ob = common.mesh_object(name, common.cushion_bmesh(size, cuts=cuts, edge=edge, crown=crown),
                            col, mat, parent)
    ob.location = loc
    ob.rotation_euler = rot
    common.add_subsurf(ob)
    common.box_uv(ob, tile=uv)
    return ob


def module(p, col, root, mat, pmat, n, x0, x1, y0, y1, back=True, arms=None, tag="", seat_w=0.95):
    """One upholstered module occupying plan rect x0..x1, y0..y1 (back at y1).
    arms: {"L": (ya, yb) | None, "R": ...} y extent of each side arm."""
    arms = arms or {}
    z0, z1 = p["deck_z"]
    aw = p["arm_w"]
    parts = []
    # deck (hidden structure the cushions sit on), full footprint between the arms
    ax0 = x0 + (aw if arms.get("L") else 0)
    ax1 = x1 - (aw if arms.get("R") else 0)
    deck = common.mesh_object(f"{n}_Deck{tag}", common.box_bmesh((x1 - x0, y1 - y0, z1 - z0)), col, mat, root)
    deck.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    common.add_bevel(deck, 0.012, segments=2)
    common.box_uv(deck, 0.25)
    parts.append(deck)
    # plinth
    inset = 0.07
    plinth = common.mesh_object(f"{n}_Plinth{tag}",
                                common.box_bmesh((x1 - x0 - 2 * inset, y1 - y0 - 2 * inset, z0)),
                                col, materials.black_metal() if p["leg"] == "black" else materials.bronze(), root)
    plinth.location = ((x0 + x1) / 2, (y0 + y1) / 2, z0 / 2)
    parts.append(plinth)
    # back rail frame
    bt = 0.16
    if back:
        rail = cushion(col, root, mat, f"{n}_BackFrame{tag}", (ax1 - ax0, bt, p["frame_back_top"] - z1 + 0.04),
                       {"+z": 0.008}, ((ax0 + ax1) / 2, y1 - bt / 2, (z1 - 0.04 + p["frame_back_top"]) / 2),
                       cuts=p["cuts_small"], edge=0.035)
        parts.append(rail)
    # arms
    for side, sx in (("L", x0 + aw / 2), ("R", x1 - aw / 2)):
        ext = arms.get(side)
        if not ext:
            continue
        ya, yb = ext
        arm = cushion(col, root, mat, f"{n}_Arm{side}{tag}", (aw, yb - ya, p["arm_top"] - z0 + 0.0),
                      {"+z": 0.012, "+x": 0.006, "-x": 0.006}, (sx, (ya + yb) / 2, (z0 + p["arm_top"]) / 2),
                      cuts=p["cuts_small"], edge=0.04)
        parts.append(arm)
    # seat cushions
    seat_y1 = y1 - (bt if back else 0.0) - 0.005
    sw_total = ax1 - ax0
    k = max(1, round(sw_total / seat_w))
    sw = sw_total / k
    st = p["seat_t"]
    for i in range(k):
        cx = ax0 + sw * (i + 0.5)
        parts.append(cushion(col, root, mat, f"{n}_Seat{tag}{i}", (sw - 0.012, seat_y1 - y0 + 0.01, st),
                             {"+z": 0.018, "-y": 0.01, "+x": 0.006, "-x": 0.006},
                             (cx, (y0 - 0.01 + seat_y1) / 2, z1 + st / 2 - 0.005),
                             cuts=p["cuts"], edge=0.03))
    # back cushions
    if back:
        bh, bth = p["back_h"], p["back_t"]
        tilt = math.radians(p["back_tilt_deg"])
        for i in range(k):
            cx = ax0 + sw * (i + 0.5)
            zc = z1 + st + bh / 2 * math.cos(tilt) - 0.005
            yc = y1 - bt - bth / 2 * math.cos(tilt) - 0.002 - (bh / 2) * math.sin(tilt) * 0.0
            parts.append(cushion(col, root, mat, f"{n}_BackCushion{tag}{i}", (sw - 0.012, bth, bh),
                                 {"-y": 0.02, "+y": 0.004, "+z": 0.012, "+x": 0.006, "-x": 0.006},
                                 (cx, yc, zc), rot=(-tilt, 0, 0), cuts=p["cuts"], edge=0.035))
    return parts


def pillow(col, root, mat, name, loc, rot, size=0.46, cuts=2):
    return cushion(col, root, mat, name, (size, 0.14, size * 0.92),
                   {"+y": 0.025, "-y": 0.025},
                   loc, rot, cuts=cuts, edge=0.04, uv=0.25)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    mat = materials.fabric(p["fabric_name"], p["fabric"])
    pmat = materials.fabric(p["pillow_name"], p["pillow"])
    w, d = p["width"], p["depth"]
    module(p, col, root, mat, pmat, n, -w / 2, w / 2, -d / 2, d / 2,
           arms={"L": (-d / 2, d / 2), "R": (-d / 2, d / 2)})
    z_seat = p["deck_z"][1] + p["seat_t"]
    for i in range(p["pillows"]):
        sx = -1 if i == 0 else 1
        pillow(col, root, pmat, f"{n}_Pillow{i}",
               (sx * (w / 2 - p["arm_w"] - 0.27), 0.0, z_seat + 0.20),
               (-math.radians(12), 0, math.radians(-8 if i == 0 else 7)))
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
