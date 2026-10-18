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
    pitch=0.15,           # bottle spacing along a shelf
    seed=11,
)


def _rand(i, j, k):
    return (math.sin(i * 12.9898 + j * 78.233 + k * 37.719) * 43758.5453) % 1.0


def bottle_upright(bm, x, y, z, s=1.0, segs=8, foil=None):
    prof = [(0.0, 0.0), (0.037, 0.0), (0.037, 0.17), (0.0145, 0.245), (0.0125, 0.292), (0.0, 0.292)]
    rows = []
    for r, h in prof:
        if r < 1e-9:
            rows.append([bm.verts.new((x, y, z + h * s))] * segs)
        else:
            rows.append([bm.verts.new((x + r * s * math.cos(2 * math.pi * k / segs),
                                       y + r * s * math.sin(2 * math.pi * k / segs), z + h * s)) for k in range(segs)])
    for a, b in zip(rows[:-1], rows[1:]):
        for k in range(segs):
            t = (k + 1) % segs
            quad = []
            for v in (a[k], b[k], b[t], a[t]):
                if v not in quad:
                    quad.append(v)
            if len(quad) >= 3:
                bm.faces.new(quad)
    if foil is not None:
        m = Matrix.Translation((x, y, z + 0.272 * s))
        bmesh.ops.create_cone(foil, cap_ends=True, cap_tris=False, segments=6, radius1=0.0145 * s,
                              radius2=0.0145 * s, depth=0.05 * s, matrix=m)


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
        zt = z + (0.0 if lvl > 0 else 0.0)
        for i in range(per):
            for row in range(2):
                u = _rand(i, lvl * 2 + row, p["seed"])
                if u < (0.12 if row == 0 else 0.72):
                    continue
                x = -(per - 1) * pitch / 2 + i * pitch + (pitch / 2 if row else 0)
                if row and i == per - 1:
                    continue
                y = yb - 0.07 - 0.065 - (0.115 if row == 0 else 0.0) + (0.0 if row == 0 else 0.0)
                y = yf + 0.12 + 0.09 * (0 if row == 0 else 1) + 0.0
                y = yb - 0.20 - 0.11 * (1 - row)       # front row nearer the glass
                v = _rand(i, lvl * 2 + row, p["seed"] + 4)
                target = bg if v < 0.5 else (bk if v < 0.86 else bw_)
                bottle_upright(target, x, y, zt, 0.97 + 0.06 * _rand(i, row, 8), foil=foil)
    for bm_, nm, mat in ((bg, "BottlesGreen", glass_g), (bk, "BottlesBlack", glass_k), (bw_, "BottlesGold", glass_w),
                         (foil, "Foil", bronze)):
        ob = common.mesh_object(f"{n}_{nm}", bm_, col, mat, root)
        common.box_uv(ob, 0.5)

    # --- glass doors: black frames + glass panes + bronze handles
    fb, gb, hb = bmesh.new(), bmesh.new(), bmesh.new()
    dwid = W / nd
    fz0, fz1 = bh + 0.04, ct
    gy = yf + 0.012
    for i in range(nd + 1):
        x = -W / 2 + i * dwid
        bmesh.ops.create_cube(fb, size=1.0, matrix=Matrix.Translation((x, gy, (fz0 + fz1) / 2)) @
                              Matrix.Diagonal((0.024 if 0 < i < nd else 0.03, 0.03, fz1 - fz0, 1)))
    for z in (fz0, fz1 - 0.012):
        bmesh.ops.create_cube(fb, size=1.0, matrix=Matrix.Translation((0, gy, z + 0.006)) @
                              Matrix.Diagonal((W, 0.03, 0.026, 1)))
    for i in range(nd):
        cx = -W / 2 + (i + 0.5) * dwid
        bmesh.ops.create_cube(gb, size=1.0, matrix=Matrix.Translation((cx, gy, (fz0 + fz1) / 2)) @
                              Matrix.Diagonal((dwid - 0.03, 0.006, fz1 - fz0 - 0.03, 1)))
    for i in range(1, nd):
        x = -W / 2 + i * dwid + (0.035 if i % 2 else -0.035)
        bmesh.ops.create_cone(hb, cap_ends=True, cap_tris=False, segments=6, radius1=0.007, radius2=0.007, depth=0.55,
                              matrix=Matrix.Translation((x, gy - 0.03, (fz0 + fz1) / 2)))
    frames = common.mesh_object(f"{n}_Frames", fb, col, dark, root, smooth=False)
    panes = common.mesh_object(f"{n}_Glass", gb, col, glass, root, smooth=False)
    handles = common.mesh_object(f"{n}_Handles", hb, col, bronze, root)
    for ob in (frames, panes, handles):
        common.box_uv(ob, 0.5)

    # --- fluted crown to the ceiling (same language as the racking)
    zc0, zc1 = ct + 0.05, H
    cb = common.mesh_object(f"{n}_Crown", common.box_bmesh((W, 0.05, zc1 - zc0)), col, backing, root)
    cb.location = (0, yb - 0.025, (zc0 + zc1) / 2)
    common.box_uv(cb, 1.0)
    rib = bmesh.new()
    k = int(W / 0.075)
    for i in range(k):
        x = -W / 2 + (i + 0.5) * W / k
        bmesh.ops.create_cube(rib, size=1.0, matrix=Matrix.Translation((x, yb - 0.07, (zc0 + zc1) / 2)) @
                              Matrix.Diagonal((0.048, 0.04, zc1 - zc0 - 0.02, 1)))
    ribs = common.mesh_object(f"{n}_CrownRibs", rib, col, oak, root, smooth=False)
    common.box_uv(ribs, 0.5)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
