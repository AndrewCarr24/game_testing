"""Glass-fronted climate wall for the cellar: a black plinth and smoked-oak base cabinet,
a four-door black-metal and glass display case lit from within (warm glowing back, LED
shelf edges) holding upright bottles on oak shelves, and the same fluted smoked-oak
crown as the racking up to the ceiling. 3.6 m wide.

Units are metres. The front faces -Y (the back goes against a wall), origin at the floor
centre, centred on x = 0.
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)
sys.path.insert(0, HERE)
import dining_wine_rack as rack  # noqa: E402  (shared reeded crown)

importlib.reload(rack)

NAME = "DiningClimateWall"

P = dict(
    name=NAME,
    width=4.0,
    depth=0.55,
    height=4.2,
    plinth_h=0.08,
    base_h=0.66,           # top of the oak base cabinet
    case_top=2.86,
    shelves=5,
    doors=4,
    open_door=1,          # this glass door opens (a lockable `rotate`, hinged at its right stile); None = all fixed
    pitch=0.15,           # bottle spacing along a shelf
    seed=11,
)


def _rand(i, j, k):
    return (math.sin(i * 12.9898 + j * 78.233 + k * 37.719) * 43758.5453) % 1.0


def bottle_upright(bm, x, y, z, s=1.0, segs=8, foil=None, spin=0.0):
    """A standing Bordeaux bottle: body, rounded shoulder and neck as one open lathe
    (it stands on a shelf, so no base), the neck end under a foil capsule with a domed
    top. 11 * segs triangles."""
    def ring(r, h, bm_):
        return [bm_.verts.new((x + r * s * math.cos(spin + 2 * math.pi * k / segs),
                               y + r * s * math.sin(spin + 2 * math.pi * k / segs), z + h * s)) for k in range(segs)]

    def skin(prof, bm_, cap=False):
        rows = [ring(r, h, bm_) for r, h in prof]
        for a, b in zip(rows[:-1], rows[1:]):
            for k in range(segs):
                t = (k + 1) % segs
                bm_.faces.new((a[k], a[t], b[t], b[k]))
        if cap:
            c = bm_.verts.new((x, y, z + prof[-1][1] * s))
            for k in range(segs):
                bm_.faces.new((rows[-1][k], rows[-1][(k + 1) % segs], c))

    skin([(0.0372, 0.0), (0.0372, 0.168), (0.030, 0.198), (0.0172, 0.222), (0.0128, 0.240)], bm)
    if foil is not None:
        skin([(0.0142, 0.236), (0.0142, 0.292)], foil, cap=True)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402  (react definitions, prompts/interactivity.md)

importlib.reload(ix_common)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    oak = materials.smoked_oak()
    dark = materials.black_metal()
    bronze = materials.bronze()
    backing = common.pbr_material("M_Rack_Backing", (0.010, 0.0075, 0.006), roughness=0.9)
    glass_g = common.pbr_material("M_Bottle_Green", (0.022, 0.060, 0.028), roughness=0.15)
    glass_k = common.pbr_material("M_Bottle_Black", (0.020, 0.018, 0.022), roughness=0.15)
    glass_w = common.pbr_material("M_Bottle_Gold", (0.16, 0.13, 0.04), roughness=0.15)
    glow = materials.emissive("M_ClimateGlow", (1.0, 0.62, 0.30), 0.9)
    led = materials.emissive("M_LED_Warm", (1.0, 0.82, 0.55), 5.0)
    glass = materials.glass("M_Glass_Display", tint=(0.8, 0.88, 0.9), alpha=0.10, roughness=0.02)

    W, D, H = p["width"], p["depth"], p["height"]
    yb, yf = D / 2, -D / 2
    ph, bh, ct = p["plinth_h"], p["base_h"], p["case_top"]

    plinth = common.mesh_object(f"{n}_Plinth", common.box_bmesh((W - 0.06, D - 0.10, ph)), col, dark, root)
    plinth.location = (0, yb - (D - 0.10) / 2, ph / 2)
    base = common.mesh_object(f"{n}_Base", common.box_bmesh((W, D - 0.03, bh - ph)), col, oak, root)
    base.location = (0, yb - (D - 0.03) / 2, ph + (bh - ph) / 2)
    common.add_bevel(base, 0.004, 2)
    common.box_uv(base, 0.5)

    # base cabinet doors + pulls
    db, pb = bmesh.new(), bmesh.new()
    nd = p["doors"]
    for i in range(nd):
        cx = -W / 2 + (i + 0.5) * W / nd
        bmesh.ops.create_cube(db, size=1.0, matrix=Matrix.Translation((cx, yf + 0.003, ph + (bh - ph) / 2)) @
                              Matrix.Diagonal((W / nd - 0.008, 0.02, bh - ph - 0.02, 1)))
        px = cx + (W / nd / 2 - 0.04) * (1 if i % 2 == 0 else -1)
        bmesh.ops.create_cone(pb, cap_ends=True, cap_tris=False, segments=6, radius1=0.005, radius2=0.005, depth=0.30,
                              matrix=Matrix.Translation((px, yf - 0.018, bh - 0.22)))
    doors = common.mesh_object(f"{n}_BaseDoors", db, col, oak, root, smooth=False)
    pulls = common.mesh_object(f"{n}_BasePulls", pb, col, bronze, root)
    common.box_uv(doors, 0.5)
    common.box_uv(pulls, 0.5)

    # --- case interior: glowing back, side/top panels, shelves, LED edges
    inner_w = W - 0.08
    back = common.mesh_object(f"{n}_Glow", common.box_bmesh((inner_w, 0.012, ct - bh - 0.04)), col, glow, root)
    back.location = (0, yb - 0.006, (bh + ct) / 2)
    common.box_uv(back, 1.0)
    for sx in (-1, 1):
        side = common.mesh_object(f"{n}_Side{'L' if sx < 0 else 'R'}",
                                  common.box_bmesh((0.04, D - 0.03, ct - bh)), col, oak, root)
        side.location = (sx * (W / 2 - 0.02), yb - (D - 0.03) / 2, (bh + ct) / 2)
        common.box_uv(side, 0.5)
    ceil = common.mesh_object(f"{n}_CaseTop", common.box_bmesh((W, D - 0.03, 0.05)), col, oak, root)
    ceil.location = (0, yb - (D - 0.03) / 2, ct + 0.025)
    common.box_uv(ceil, 0.5)
    deck = common.mesh_object(f"{n}_Deck", common.box_bmesh((W, D - 0.03, 0.04)), col, oak, root)
    deck.location = (0, yb - (D - 0.03) / 2, bh + 0.02)
    common.box_uv(deck, 0.5)

    ns = p["shelves"]
    z_levels = [bh + 0.04 + i * (ct - bh - 0.04) / ns for i in range(ns)]
    shelf_b, led_b = bmesh.new(), bmesh.new()
    sd = D - 0.12
    for i, z in enumerate(z_levels):
        if i > 0:
            bmesh.ops.create_cube(shelf_b, size=1.0, matrix=Matrix.Translation((0, yb - 0.012 - sd / 2, z - 0.01)) @
                                  Matrix.Diagonal((inner_w, sd, 0.02, 1)))
        bmesh.ops.create_cube(led_b, size=1.0, matrix=Matrix.Translation((0, yb - 0.012 - sd - 0.004, z - 0.006)) @
                              Matrix.Diagonal((inner_w - 0.02, 0.008, 0.008, 1)))
    shelves = common.mesh_object(f"{n}_Shelves", shelf_b, col, oak, root, smooth=False)
    leds = common.mesh_object(f"{n}_LEDs", led_b, col, led, root, smooth=False)
    common.box_uv(shelves, 0.5)
    common.box_uv(leds, 0.5)

    # --- bottles standing on the shelves (two rows front/back, staggered)
    bg, bk, bw_, foil = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    pitch = p["pitch"]
    per = int((inner_w - 0.1) / pitch)
    for lvl, z in enumerate(z_levels):
        for i in range(per):
            for row in range(2):
                u = _rand(i, lvl * 2 + row, p["seed"])
                if u < (0.12 if row == 0 else 0.80):      # front row nearly full, a few behind
                    continue
                x = -(per - 1) * pitch / 2 + i * pitch + (pitch / 2 if row else 0)
                if row and i == per - 1:
                    continue
                y = yb - 0.20 - 0.11 * (1 - row)       # front row nearer the glass
                v = _rand(i, lvl * 2 + row, p["seed"] + 4)
                target = bg if v < 0.5 else (bk if v < 0.86 else bw_)
                bottle_upright(target, x, y, z, 0.97 + 0.06 * _rand(i, row, 8), segs=8 if row == 0 else 6,
                               foil=foil, spin=_rand(i, lvl, 3))
    for bm_, nm, mat in ((bg, "BottlesGreen", glass_g), (bk, "BottlesBlack", glass_k), (bw_, "BottlesGold", glass_w),
                         (foil, "Foil", bronze)):
        ob = common.mesh_object(f"{n}_{nm}", bm_, col, mat, root)
        common.box_uv(ob, 0.5)

    # --- glass doors: each a slim black-metal frame (3 mm reveal to its neighbour) holding
    #     an inset pane, long bronze bar pulls on standoffs at the meeting stiles
    fb, gb, hb = bmesh.new(), bmesh.new(), bmesh.new()
    # locks, keys and caches: the opening door's frame, pane and pull go in their own meshes,
    # in its hinge's space (built in place, then moved under the hinge below)
    od = p["open_door"]
    ofb, ogb, ohb = bmesh.new(), bmesh.new(), bmesh.new()
    dwid = W / nd
    fz0, fz1 = bh + 0.04, ct
    gy = yf + 0.012
    fw, fd, rv = 0.026, 0.028, 0.0015          # frame face width, depth, half reveal
    fh = fz1 - fz0
    for i in range(nd):
        cx = -W / 2 + (i + 0.5) * dwid
        dw_ = dwid - 2 * rv
        for size, c in (((fw, fd, fh), (cx - dw_ / 2 + fw / 2, gy, fz0 + fh / 2)),
                        ((fw, fd, fh), (cx + dw_ / 2 - fw / 2, gy, fz0 + fh / 2)),
                        ((dw_ - 2 * fw, fd, fw * 1.4), (cx, gy, fz0 + fw * 0.7)),
                        ((dw_ - 2 * fw, fd, fw), (cx, gy, fz1 - fw / 2))):
            bmesh.ops.create_cube(ofb if i == od else fb, size=1.0, matrix=Matrix.Translation(c) @ Matrix.Diagonal((*size, 1)))
        bmesh.ops.create_cube(ogb if i == od else gb, size=1.0, matrix=Matrix.Translation((cx, gy + 0.004, fz0 + fh / 2)) @
                              Matrix.Diagonal((dw_ - 2 * fw + 0.01, 0.006, fh - 2.4 * fw + 0.01, 1)))
    for i in range(nd):
        cx = -W / 2 + (i + 0.5) * dwid
        side = 1 if i % 2 == 0 else -1                     # pulls pair up at the meeting stiles
        x = cx + side * (dwid / 2 - rv - fw - 0.03)
        zc, hl = fz0 + fh * 0.5, 0.62
        hbm = ohb if i == od else hb
        bmesh.ops.create_cone(hbm, cap_ends=True, cap_tris=False, segments=8, radius1=0.0075, radius2=0.0075,
                              depth=hl, matrix=Matrix.Translation((x, gy - fd / 2 - 0.016, zc)))
        for dz in (-hl / 2 + 0.05, hl / 2 - 0.05):
            bmesh.ops.create_cone(hbm, cap_ends=False, segments=6, radius1=0.0045, radius2=0.0045, depth=0.016,
                                  matrix=Matrix.Translation((x, gy - fd / 2 - 0.008, zc + dz)) @
                                  Matrix.Rotation(math.pi / 2, 4, "X"))
    # the case's own black-metal jambs either side, just proud of the oak sides
    for sx in (-1, 1):
        bmesh.ops.create_cube(fb, size=1.0, matrix=Matrix.Translation((sx * W / 2, gy + 0.004, fz0 + fh / 2)) @
                              Matrix.Diagonal((0.03, fd + 0.008, fh + 0.006, 1)))
    frames = common.mesh_object(f"{n}_Frames", fb, col, dark, root, smooth=False)
    panes = common.mesh_object(f"{n}_Glass", gb, col, glass, root, smooth=False)
    handles = common.mesh_object(f"{n}_Handles", hb, col, bronze, root)
    for ob in (frames, panes, handles):
        common.box_uv(ob, 0.5)
    if od is not None:
        # hinge on the door's right stile (its pull is on the left, at the meeting stiles),
        # on the frame's front face; it swings out 100 degrees
        hx, hy = -W / 2 + (od + 1) * dwid - rv, gy - fd / 2
        hinge = common.empty(f"{n}_Door", col, (hx, hy, fz0))
        hinge.parent = root
        hinge["interact"] = {
            "type": "rotate", "axis": common.to_gltf((0, 0, 1)), "angle": 100, "duration": 0.8,
            "range": 1.5, "side": "both", "prompt": "Open cabinet", "promptActive": "Close cabinet",
        }
        for bm_, nm, mat in ((ofb, "Door_Frame", dark), (ogb, "Door_Glass", glass), (ohb, "Door_Pull", bronze)):
            bmesh.ops.translate(bm_, vec=(-hx, -hy, -fz0), verts=bm_.verts)
            ob = common.mesh_object(f"{n}_{nm}", bm_, col, mat, hinge, smooth=(nm == "Door_Pull"))
            common.box_uv(ob, 0.5)
        # what the level puts in the cabinet sits on the first shelf behind that door, in front
        # of the bottles (attach to <n>_Inside; takeable only while the door is open)
        inside = common.empty(f"{n}_Inside", col, (-W / 2 + (od + 0.5) * dwid, yb - 0.012 - sd + 0.05, z_levels[1]))
        inside.parent = root
        inside["inside"] = f"{n}_Door"
    # a warm LED line in the case soffit, behind the door head
    soff = common.mesh_object(f"{n}_SoffitLED", common.box_bmesh((inner_w - 0.04, 0.012, 0.006)), col, led, root)
    soff.location = (0, gy + 0.05, ct - 0.003)

    # --- fluted crown to the ceiling (same language as the racking)
    zc0, zc1 = ct + 0.05, H
    cb = common.mesh_object(f"{n}_Crown", common.box_bmesh((W, 0.05, zc1 - zc0)), col, backing, root)
    cb.location = (0, yb - 0.025, (zc0 + zc1) / 2)
    common.box_uv(cb, 1.0)
    rib = bmesh.new()
    rack.reeded_panel(rib, -W / 2, W / 2, yb - 0.05, 0.035, zc0 + 0.01, zc1, 0.075)
    ribs = common.mesh_object(f"{n}_CrownRibs", rib, col, oak, root, smooth=True)
    common.box_uv(ribs, 0.5)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    ix_common.tag_emissive(root)   # interactivity: glowing parts follow the room's light switch
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
