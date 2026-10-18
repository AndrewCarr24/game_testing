"""Treadmill: graphite frame, black running belt between brushed side rails, a
motor hood at the front, two raked uprights, a console with a dark screen and
steel handrails. The runner faces -Y (console end at -Y); origin is the floor
centre. Runs for 1.95 m, 0.85 m wide, 1.45 m tall."""
import importlib
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestTreadmill"

P = dict(name=NAME, width=0.86, length=1.95, deck_z=0.12, deck_t=0.08)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    gr, rub, steel = guest_mats.graphite(), guest_mats.rubber(), guest_mats.steel() if hasattr(guest_mats, "steel") else guest_mats.materials.steel()
    pad = guest_mats.pad("M_Pad_Charcoal")
    own = (col, root, n)
    A = guest_mats.add
    W, L, dz, dt = p["width"], p["length"], p["deck_z"], p["deck_t"]
    y0, y1 = -L / 2, L / 2
    hood_y = y0 + 0.62
    parts = []
    # feet and deck
    for sx in (-1, 1):
        A(own, f"Foot_F{sx}", common.box_bmesh((0.07, 0.30, dz - 0.02)), rub, (sx * (W / 2 - 0.08), y0 + 0.2, (dz - 0.02) / 2 + 0.0), 0.004)
        A(own, f"Foot_B{sx}", common.box_bmesh((0.07, 0.22, dz - 0.02)), rub, (sx * (W / 2 - 0.08), y1 - 0.15, (dz - 0.02) / 2 + 0.0), 0.004)
    A(own, "Deck", common.box_bmesh((W - 0.18, L - 0.62 - 0.08, dt)), gr, (0, (hood_y + y1) / 2, dz + dt / 2 - 0.02), 0.01)
    # side rails (brushed) with the belt between them
    belt_w = W - 0.28
    for sx in (-1, 1):
        A(own, f"Rail{sx}", common.box_bmesh((0.10, L - 0.62 - 0.02, 0.05)), gr, (sx * (W / 2 - 0.12), (hood_y + y1) / 2, dz + dt - 0.01 + 0.025), 0.012)
    belt = A(own, "Belt", common.box_bmesh((belt_w, L - 0.62 - 0.08, 0.012)), rub, (0, (hood_y + y1) / 2, dz + dt + 0.016), 0.004)
    # front and rear rollers just visible
    A(own, "RollerRear", guest_mats.cyl_bmesh(0.04, belt_w + 0.01, seg=16, axis="x"), rub, (0, y1 - 0.05, dz + dt + 0.0), 0)
    # motor hood: a wedge-ish rounded box
    hood = common.mesh_object(f"{n}_Hood", common.cushion_bmesh((W - 0.06, 0.62, 0.24), cuts=4, edge=0.06,
                              crown={"+z": 0.0}), col, gr, root)
    hood.location = (0, y0 + 0.31, 0.04 + 0.12)
    common.add_subsurf(hood)
    common.box_uv(hood, 0.5)
    # raked uprights
    top_y = y0 + 0.40
    for sx in (-1, 1):
        r = 0.022
        pts = [(sx * (W / 2 - 0.10), y0 + 0.50, 0.22), (sx * (W / 2 - 0.10), top_y, 1.14)]
        t = common.tube_object(f"{n}_Upright{sx}", pts, r, col, gr, root, closed=False, profile_res=3)
        common.box_uv(t, 0.5)
    # console
    cons = common.mesh_object(f"{n}_Console", common.cushion_bmesh((W - 0.08, 0.16, 0.30), cuts=4, edge=0.05,
                              crown={"+y": 0.01}), col, gr, root)
    cons.rotation_euler = (math.radians(20), 0, 0)
    cons.location = (0, top_y - 0.02, 1.20)
    common.add_subsurf(cons)
    common.box_uv(cons, 0.5)
    scr = common.mesh_object(f"{n}_Screen", common.box_bmesh((0.46, 0.006, 0.17)), col, guest_mats.screen(), root)
    scr.rotation_euler = (math.radians(20), 0, 0)
    scr.location = (0, top_y - 0.02 + 0.08, 1.20 + 0.02)
    # handrails: from the console back along the deck, bent steel tube
    rail_r = 0.017
    for sx in (-1, 1):
        x = sx * (W / 2 - 0.10)
        pts = common.fillet_polyline([(x, top_y + 0.03, 1.10), (x, y0 + 0.62, 1.0), (x, y0 + 1.15, 0.99)], 0.12, 8, closed=False)
        t = common.tube_object(f"{n}_Handrail{sx}", pts, rail_r, col, gr, root, closed=False, profile_res=3)
        common.box_uv(t, 0.5)
        # grip sleeve
        sl = common.tube_object(f"{n}_Grip{sx}", [(x, y0 + 0.64, 1.0), (x, y0 + 1.1, 0.99)], 0.021, col, rub, root, closed=False, profile_res=3)
        common.box_uv(sl, 0.5)
    # cross bar behind the console + bottle holder
    A(own, "ConsoleBar", guest_mats.cyl_bmesh(0.014, W - 0.20, seg=12, axis="x"), gr, (0, top_y + 0.1, 1.05), 0)
    parts = guest_mats.consolidate(root, max_dim=0.35)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
