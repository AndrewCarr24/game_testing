"""Powder-room vanity: a floating walnut cabinet (two drawers, bronze edge pulls, a dark
shadow recess under it) with a thick white-marble counter, a hand-thrown white vessel
basin and a tall polished-bronze deck faucet.

Also holds the powder room's dark veined marble (`dark_marble()`, texture
T_Entry_DarkMarble, generated when missing; `dark_marble_material(...)`).

Origin: floor centre of the cabinet footprint; the front faces -Y (the wall is on +Y).
Counter height 0.86 m. Units are metres.
"""
import importlib
import math
import os
import sys

import bmesh
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials, textures  # noqa: E402
import table_lamp  # noqa: E402

importlib.reload(common)
importlib.reload(materials)
importlib.reload(textures)

NAME = "EntryVanity"

P = dict(
    name=NAME,
    width=1.8,
    depth=0.56,
    cab_h=0.42,               # cabinet body height
    cab_z=0.34,               # floats this far off the floor
    cab_inset=0.02,           # cabinet sits slightly inside the counter
    top_t=0.045,
    drawer_gap=0.004,
    basin_r=0.205,
    basin_h=0.14,
    basin_x=0.0,
)


# --------------------------------------------------------------- dark marble texture

def dark_marble(n=1024, seed=27, force=False):
    """Nero-marquina style: near-black stone with sharp white veins and a few fine gold
    threads. One tile = 1.5 m."""
    name = "T_Entry_DarkMarble"
    path = os.path.join(textures.TEX_DIR, name + ".png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 1, n, endpoint=False)[None, :] * np.ones((n, 1))
    y = np.linspace(0, 1, n, endpoint=False)[:, None] * np.ones((1, n))
    t1 = textures._noise(n, 1.0, 1.0, 2.8, rng)       # smooth, large-scale warps: long sweeping veins
    t2 = textures._noise(n, 1.0, 1.0, 2.6, rng)
    t3 = textures._noise(n, 1.0, 1.0, 2.6, rng)
    fine = textures._noise(n, 1.0, 1.0, 1.0, rng)
    v1 = np.abs(np.sin(2 * np.pi * (1 * x + 1 * y + 0.40 * t1)))
    v2 = np.abs(np.sin(2 * np.pi * (1 * x - 2 * y + 0.5 * t2)))
    v3 = np.abs(np.sin(2 * np.pi * (2 * x + 1 * y + 0.45 * t3)))
    bold = (1 - v1) ** 16 * (0.55 + 0.45 * (fine * 0.5 + 0.5))      # thick white veins, broken up
    thin = 0.35 * (1 - v2) ** 140
    gold = 0.55 * (1 - v3) ** 90
    cloud = textures._noise(n, 1.0, 1.0, 2.4, rng) * 0.5 + 0.5
    base = np.array([0.011, 0.011, 0.013]) * (0.7 + 0.8 * cloud)[..., None]
    lin = (base + np.array([0.60, 0.59, 0.57]) * (0.95 * bold + 0.25 * thin)[..., None]
           + np.array([0.42, 0.28, 0.10]) * gold[..., None])
    return textures._save(name, textures._to_srgb(np.clip(lin, 0, 1)))


def dark_marble_material(name="M_Entry_DarkMarble", roughness=0.18):
    m = common.pbr_material(name, (0.2, 0.2, 0.2), roughness=roughness)
    common.set_base_color_map(m, textures.load(dark_marble()))
    return m


# ------------------------------------------------------------------------- geometry

def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    walnut = materials.walnut()
    bronze_p = common.pbr_material("M_Entry_Bronze_Polished", (0.50, 0.30, 0.14), roughness=0.2, metallic=1.0)
    black = materials.black_metal()
    marble = common.pbr_material("M_Marble_White", (0.8, 0.79, 0.77), roughness=0.12)
    common.set_base_color_map(marble, textures.load(textures.marble()))
    ceramic = common.pbr_material("M_Entry_Ceramic", (0.80, 0.80, 0.78), roughness=0.10)

    W, D = p["width"], p["depth"]
    cz, ch = p["cab_z"], p["cab_h"]
    tt = p["top_t"]
    top_z0 = cz + ch                  # underside of the counter
    cin = p["cab_inset"]

    # ---- counter ----------------------------------------------------------------------
    top = common.mesh_object(f"{n}_Counter", common.rounded_slab_bmesh(W, D, tt, 0.02), col, marble, root)
    top.location = (0, 0, top_z0 + tt / 2)
    common.add_bevel(top, 0.004, segments=2)
    common.box_uv(top, tile=1.0)

    # ---- cabinet carcass: dark recess + two walnut drawer fronts -------------------------
    cw, cd = W - 2 * 0.07, D - 0.10
    recess = common.mesh_object(f"{n}_Recess", common.box_bmesh((cw + 0.02, cd - 0.02, ch + 0.01)), col, black, root,
                                smooth=False)
    recess.location = (0, D / 2 - 0.05 - cd / 2 + 0.01 + 0.02, cz + ch / 2)
    g = p["drawer_gap"]
    fh = (ch - 3 * g) / 2
    ft = 0.022
    y_front = -D / 2 + 0.05
    wood = []
    for i in range(2):
        zc = cz + g + fh / 2 + i * (fh + g)
        front = common.mesh_object(f"{n}_Drawer_{i}", common.box_bmesh((cw, ft, fh)), col, walnut, root, smooth=False)
        front.location = (0, y_front - ft / 2 + 0.003, zc)
        common.add_bevel(front, 0.0025, segments=2)
        wood.append(front)
        # bronze edge pull: a thin bar along the top edge of the front
        pull = common.mesh_object(f"{n}_Pull_{i}", common.box_bmesh((cw * 0.55, 0.014, 0.012)), col, bronze_p, root,
                                  smooth=False)
        pull.location = (0, y_front - ft - 0.004 + 0.003, zc + fh / 2 - 0.016)
        common.add_bevel(pull, 0.002, segments=2)
    # side panels so the cabinet reads as a solid floating box from the sides
    for sx in (-1, 1):
        side = common.mesh_object(f"{n}_Side_{'L' if sx < 0 else 'R'}", common.box_bmesh((0.03, cd, ch)), col, walnut,
                                  root, smooth=False)
        side.location = (sx * (cw / 2 + 0.015), y_front + cd / 2 - ft / 2 + 0.01, cz + ch / 2)
        common.add_bevel(side, 0.002, segments=2)
        wood.append(side)
    for ob in wood:
        common.box_uv(ob, tile=0.5)

    # ---- vessel basin (thin-walled bowl, flat foot) ----------------------------------------
    r, h = p["basin_r"], p["basin_h"]
    cx = p["basin_x"]
    cy = -0.02
    outer = table_lamp.catmull([(0.075, 0.0), (0.10, 0.006), (0.165, 0.045), (r, 0.10), (r - 0.004, h - 0.012)], per=6)
    inner = table_lamp.catmull([(r - 0.016, h - 0.006), (r - 0.026, h - 0.022), (r - 0.048, 0.085), (0.12, 0.05),
                                (0.05, 0.026)], per=6)
    rim = [(r - 0.010, h - 0.003)]
    prof = []
    for pt in [(0.0, 0.0)] + outer + rim + inner + [(0.0, 0.022)]:
        if not prof or abs(pt[0] - prof[-1][0]) + abs(pt[1] - prof[-1][1]) > 1e-4:
            prof.append(pt)
    basin = common.mesh_object(f"{n}_Basin", table_lamp.lathe(prof, 56, sharp=55), col, ceramic, root)
    basin.location = (cx, cy, top_z0 + tt)
    # drain
    drain = common.mesh_object(f"{n}_Drain", table_lamp.lathe([(0.0, 0.0), (0.022, 0.0), (0.022, 0.003), (0.0, 0.003)], 20),
                               col, bronze_p, root)
    drain.location = (cx, cy, top_z0 + tt + 0.0235)

    # ---- faucet: a column rising from the counter behind the basin, arcing over it -------------
    fy = D / 2 - 0.09
    base_z = top_z0 + tt
    col_h = 0.30
    spout_len = fy - cy + 0.02
    pts = [(cx, fy, base_z), (cx, fy, base_z + col_h - 0.06), (cx, fy - 0.10, base_z + col_h + 0.02),
           (cx, cy + 0.07, base_z + col_h + 0.02), (cx, cy + 0.015, base_z + col_h - 0.08)]
    path = common.fillet_polyline(pts, 0.07, segments=6, closed=False)
    common.tube_object(f"{n}_Spout", [tuple(v) for v in path], 0.0115, col, bronze_p, root, closed=False, profile_res=3)
    flange = common.mesh_object(f"{n}_Flange", table_lamp.lathe([(0.0, 0.0), (0.038, 0.0), (0.034, 0.012), (0.0, 0.012)], 28),
                                col, bronze_p, root)
    flange.location = (cx, fy, base_z)
    # a lever handle beside the column
    hx = cx + 0.09
    hb = bmesh.new()
    table_lamp.cylinder_between(hb, (hx, fy, base_z), (hx, fy, base_z + 0.12), 0.011, segs=14)
    common.mesh_object(f"{n}_HandleStem", hb, col, bronze_p, root)
    hb2 = bmesh.new()
    table_lamp.cylinder_between(hb2, (hx, fy, base_z + 0.12), (hx + 0.002, fy - 0.07, base_z + 0.13), 0.008, segs=12)
    common.mesh_object(f"{n}_HandleLever", hb2, col, bronze_p, root)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
