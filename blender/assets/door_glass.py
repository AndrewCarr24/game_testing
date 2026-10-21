"""Exterior glass door for an opening in one of the house's glass walls (the entry's front
doors, the kitchen and dining room doors to the garden): a black aluminium leaf (slim stiles,
a deeper bottom rail) round one clear pane, a long bronze bar pull on both faces, and a slim
black surround (jambs and head) that meets the window mullions either side.

Origin: bottom centre of the opening, on the glass line (the window glass's plane). The leaf
swings toward local +Y about a hinge on the -X jamb (`hinge="right"`: the +X jamb, for the
other leaf of a pair); the level turns it so it opens outward (plan.CUTS `swing_out`).
The hinge empty carries the `interact` (rotate), like every door."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "DoorGlass"

P = dict(
    name=NAME,
    opening=(1.5, 3.0),     # width, height: one window bay
    hinge="left",           # "left" = the -X jamb, "right" = the +X jamb
    surround=(0.03, 0.10),  # jamb / head face width, depth (the window frames are 0.12 deep)
    gap=0.004,
    floor_gap=0.01,
    leaf_t=0.05,
    stile=0.065,            # leaf frame widths: stiles + top rail, bottom rail
    bottom_rail=0.14,
    pane_t=0.012,
    pull_len=1.3,
    pull_z=1.15,            # centre height of the pull
    pull_r=0.014,
    pull_off=0.07,          # pull bar's distance from the leaf face
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    black = common.pbr_material("M_Aluminium_Black", (0.02, 0.02, 0.022), roughness=0.35, metallic=0.7)
    bronze = common.pbr_material("M_Bronze_Pull", (0.30, 0.20, 0.11), roughness=0.3, metallic=1.0)
    glass = materials.glass("M_Glass_Door", tint=(0.02, 0.026, 0.026), alpha=0.1, roughness=0.02)

    w, h = p["opening"]
    sj, sd = p["surround"]
    g, lt = p["gap"], p["leaf_t"]
    right = p["hinge"] == "right"
    s = -1 if right else 1                       # +1: hinge at -X, the leaf runs toward +X
    lw = w - 2 * sj - 2 * g                      # leaf width
    lh = h - sj - g - p["floor_gap"]             # leaf height
    hx = (w / 2 - sj - g) * (1 if right else -1)

    # surround: jambs + head, static (the mullions' black, flush with the leaf's faces)
    for name, size, loc in (
        ("Jamb_L", (sj, sd, h), (-w / 2 + sj / 2, 0, h / 2)),
        ("Jamb_R", (sj, sd, h), (w / 2 - sj / 2, 0, h / 2)),
        ("Head", (w, sd, sj), (0, 0, h - sj / 2)),
    ):
        ob = common.mesh_object(f"{n}_{name}", common.box_bmesh(size), col, black, root, smooth=False)
        ob.location = loc

    # the hinge on the leaf's +Y face so the opened leaf clears the jamb
    hinge = common.empty(f"{n}_Hinge", col, (hx, lt / 2, 0))
    hinge.parent = root
    hinge["interact"] = {
        "type": "rotate",
        "axis": common.to_gltf((0, 0, s)),       # opens toward +Y whichever jamb it hangs on
        "angle": 95,
        "duration": 1.0,
        "range": 1.8,
        "side": "both",
        "collide": True,
        "prompt": "Open door",
        "promptActive": "Close door",
        "lockedPrompt": "Locked",
        "unlockPrompt": "Unlock",
    }

    # leaf, in hinge space: x from 0 (hinge edge) to s * lw, y from -lt to 0
    st, br, pt = p["stile"], p["bottom_rail"], p["pane_t"]
    z0 = p["floor_gap"]
    cx = s * lw / 2
    for name, size, loc in (
        ("StileHinge", (st, lt, lh), (s * st / 2, -lt / 2, z0 + lh / 2)),
        ("StileLatch", (st, lt, lh), (s * (lw - st / 2), -lt / 2, z0 + lh / 2)),
        ("RailTop", (lw - 2 * st, lt, st), (cx, -lt / 2, z0 + lh - st / 2)),
        ("RailBottom", (lw - 2 * st, lt, br), (cx, -lt / 2, z0 + br / 2)),
    ):
        ob = common.mesh_object(f"{n}_{name}", common.box_bmesh(size), col, black, hinge, smooth=False)
        ob.location = loc
    pane = common.mesh_object(f"{n}_Pane", common.box_bmesh((lw - 2 * st + 0.01, pt, lh - st - br + 0.01)),
                              col, glass, hinge, smooth=False)
    pane.location = (cx, -lt / 2, z0 + br + (lh - st - br) / 2)

    # bar pulls on both faces near the latch stile: a long bronze D-pull
    px = s * (lw - st - 0.06)
    za, zb = p["pull_z"] - p["pull_len"] / 2, p["pull_z"] + p["pull_len"] / 2
    for side, face, out in (("Out", 0.0, p["pull_off"]), ("In", -lt, -p["pull_off"])):
        pts = common.fillet_polyline([(px, face, za), (px, face + out, za), (px, face + out, zb), (px, face, zb)],
                                     0.02, segments=5, closed=False)
        common.tube_object(f"{n}_Pull_{side}", pts, p["pull_r"], col, bronze, hinge, closed=False)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
