"""Tool wall for the showroom garage: a perforated graphite panel in an aluminium
frame with an LED hood, hung with a spanner set, screwdrivers, hammers, pliers, a
spirit level, a cordless drill on its dock and two shelves of bins, plus a
graphite rolling tool chest with aluminium rim, drawers and castors in front of it.

Units are metres. The front faces -Y (the panel is at the back), the origin is
the floor centre.
"""
import importlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import garage_cabinets as gk  # noqa: E402
from lib import common, textures  # noqa: E402

importlib.reload(gk)
common, materials = gk.common, gk.materials

NAME = "GarageToolwall"

P = dict(
    name=NAME,
    width=4.2,
    depth=0.50,
    panel_z0=0.30,
    panel_z1=2.55,
    chest_w=0.95,
    chest_d=0.52,
    chest_h=1.02,
    chest_x=-1.35,
)


def peg_texture(n=1024, force=False):
    """Perforated panel: 16 x 16 round holes per 0.5 m tile on graphite."""
    path = os.path.join(textures.TEX_DIR, "T_Garage_Peg_BaseColor.png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(41)
    pitch = n // 16
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    cx = (x % pitch) - pitch / 2 + 0.5
    cy = (y % pitch) - pitch / 2 + 0.5
    r = np.sqrt(cx ** 2 + cy ** 2) / pitch
    hole = np.clip((0.17 - r) / 0.025, 0, 1)                 # soft-edged hole
    rim = np.clip(1 - np.abs(r - 0.2) / 0.03, 0, 1) * (cy < 0)  # lit upper edge of each hole
    noise = textures._noise(n, 1.0, 1.0, 1.0, rng) * 0.5 + 0.5
    base = 0.050 + 0.014 * noise
    lin = base * (1 - hole) + 0.004 * hole + 0.035 * rim
    return textures._save("T_Garage_Peg_BaseColor", textures._to_srgb(np.repeat(lin[..., None], 3, axis=2)))


def accent():
    return common.pbr_material("M_Garage_Accent", (0.55, 0.07, 0.025), roughness=0.5)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    b = gk.Builder(n)
    gr, grd, al, qz = gk.graphite(), gk.graphite_dark(), gk.aluminium(), gk.quartz()
    glow, ac, white = gk.led(), accent(), gk.white_lacquer()

    peg = common.pbr_material("M_Garage_Peg", (0.8, 0.8, 0.8), roughness=0.55)
    common.set_base_color_map(peg, textures.load(peg_texture()))

    W, D = p["width"], p["depth"]
    yb = D / 2
    z0, z1 = p["panel_z0"], p["panel_z1"]
    fr = 0.03

    # --- panel, frame, LED hood
    pan = b.lo_hi("Panel", (-W / 2, yb - 0.03, z0), (W / 2, yb, z1), peg, bevel=0, tile=0.5)
    b.lo_hi("Frame_Top", (-W / 2, yb - 0.05, z1), (W / 2, yb, z1 + fr), al, bevel=0.002, seg=1)
    b.lo_hi("Frame_Bottom", (-W / 2, yb - 0.05, z0 - fr), (W / 2, yb, z0), al, bevel=0.002, seg=1)
    for s, sx in (("L", -1), ("R", 1)):
        xa, xb = sorted((sx * W / 2, sx * (W / 2 + fr)))
        b.lo_hi(f"Frame_{s}", (xa, yb - 0.05, z0 - fr), (xb, yb, z1 + fr), al, bevel=0.002, seg=1)
    # hood with a warm LED line washing down the panel
    b.lo_hi("Hood", (-W / 2, yb - 0.17, z1 + fr), (W / 2, yb, z1 + fr + 0.05), grd, bevel=0.002, seg=1)
    b.lo_hi("Hood_LED", (-W / 2 + 0.05, yb - 0.15, z1 + fr - 0.004), (W / 2 - 0.05, yb - 0.06, z1 + fr), glow, bevel=0, tile=1.0)
    b.lo_hi("Rail_Spanner", (-1.95, yb - 0.065, 2.19), (-0.55, yb - 0.045, 2.205), al, bevel=0, tile=0.5)
    py = yb - 0.03                                       # panel face

    def hang(name, size, x, z, mat, off=0.012, bevel=0.001):
        return b.box(name, size, (x, py - size[1] / 2 - off, z), mat, bevel=bevel, seg=1)

    # --- spanner set: 12 flat open-end spanners, longest to shortest, hung from a rail
    for i in range(12):
        L = 0.27 - i * 0.012
        x = -1.92 + i * 0.115
        hang(f"Spanner{i}", (0.022, 0.005, L), x, 2.19 - L / 2 - 0.01, al)
        hang(f"Spanner{i}_Head", (0.034, 0.005, 0.034), x, 2.19 - L - 0.012, al, bevel=0.0015)
    # --- screwdrivers on a rack at mid height
    b.lo_hi("Rack_Driver", (-1.95, py - 0.04, 1.70), (-0.55, py - 0.012, 1.72), al, bevel=0, tile=0.5)
    for i in range(10):
        x = -1.9 + i * 0.14
        b.cyl(f"Driver{i}_Handle", 0.014, 0.11, (x, py - 0.032, 1.77), ac if i % 2 == 0 else grd, axis="z", seg=8)
        b.cyl(f"Driver{i}_Shaft", 0.0035, 0.13, (x, py - 0.032, 1.66), al, axis="z", seg=6)
    # --- hammers and pliers on the lower part of the left field
    for i, x in enumerate((-1.8, -1.45)):
        hang(f"Hammer{i}_Haft", (0.03, 0.03, 0.34), x, 1.30, grd, off=0.015, bevel=0.004)
        hang(f"Hammer{i}_Head", (0.11, 0.035, 0.05), x, 1.50, al, off=0.015, bevel=0.002)
    for i in range(4):
        x = -1.05 + i * 0.16
        hang(f"Pliers{i}_Jaw", (0.03, 0.012, 0.09), x, 1.40, al, off=0.012, bevel=0.002)
        hang(f"Pliers{i}_Grip", (0.044, 0.016, 0.12), x, 1.27, ac, off=0.012, bevel=0.004)
    # --- spirit level
    hang("Level", (0.05, 0.026, 1.2), -0.15, 1.45, al, off=0.015, bevel=0.004)
    hang("Level_Vial", (0.03, 0.003, 0.08), -0.15, 1.45, ac, off=0.0, bevel=0)
    # --- cordless drill on its dock
    hang("Dock", (0.16, 0.03, 0.09), 0.55, 1.40, grd, off=0.0, bevel=0.003)
    b.box("Drill_Body", (0.07, 0.2, 0.09), (0.55, py - 0.14, 1.47), ac, bevel=0.006, seg=2)
    b.box("Drill_Grip", (0.05, 0.05, 0.14), (0.55, py - 0.18, 1.39), grd, bevel=0.006, seg=2)
    b.cyl("Drill_Chuck", 0.016, 0.05, (0.55, py - 0.265, 1.47), al, axis="y", seg=10)
    b.box("Drill_Battery", (0.06, 0.08, 0.05), (0.55, py - 0.18, 1.31), grd, bevel=0.004, seg=1)
    # --- two shelves of bins on the right
    for k, zs in enumerate((1.22, 1.78)):
        b.lo_hi(f"Shelf{k}", (0.95, py - 0.28, zs), (2.0, py, zs + 0.025), al, bevel=0.002, seg=1)
        for m in range(5):
            bw = 0.18
            x = 1.05 + m * 0.2
            hh = 0.2 if (m + k) % 2 else 0.15
            b.box(f"Bin{k}_{m}", (bw, 0.22, hh), (x, py - 0.14, zs + 0.025 + hh / 2), grd if m % 2 else white, bevel=0.005, seg=1)
            b.box(f"Bin{k}_{m}_Label", (0.09, 0.004, 0.03), (x, py - 0.253, zs + 0.025 + hh - 0.05), al, bevel=0, tile=0.25)
    # --- tyre-pressure gauge and a coiled air line on hooks (round bits for relief)
    b.cyl("Coil", 0.12, 0.05, (-0.8, py - 0.05, 2.0), grd, axis="y", seg=16)
    b.cyl("Coil_Hole", 0.05, 0.052, (-0.8, py - 0.05, 2.0), peg, axis="y", seg=12)
    b.cyl("Gauge", 0.04, 0.03, (-0.2, py - 0.03, 2.05), al, axis="y", seg=14)
    b.cyl("Gauge_Face", 0.032, 0.004, (-0.2, py - 0.047, 2.05), white, axis="y", seg=14)

    # --- rolling tool chest
    cw, cd, ch = p["chest_w"], p["chest_d"], p["chest_h"]
    cx = p["chest_x"]
    cy = yb - cd / 2 - 0.02
    yf = cy - cd / 2
    b.lo_hi("Chest_Body", (cx - cw / 2, yf + 0.02, 0.1), (cx + cw / 2, cy + cd / 2, ch - 0.04), grd, bevel=0.003)
    b.lo_hi("Chest_Top", (cx - cw / 2 - 0.01, yf, ch - 0.04), (cx + cw / 2 + 0.01, cy + cd / 2, ch), al, bevel=0.004)
    z = ch - 0.06
    hs = [0.09, 0.09, 0.12, 0.12, 0.2, 0.2]
    for k, h in enumerate(hs):
        b.lo_hi(f"Chest_Drawer{k}", (cx - cw / 2 + 0.012, yf, z - h), (cx + cw / 2 - 0.012, yf + 0.025, z), ac if k == 0 else gr, bevel=0.002)
        b.box(f"Chest_Drawer{k}_Pull", (cw - 0.2, 0.02, 0.014), (cx, yf - 0.01, z - 0.02), al, bevel=0.0015, seg=1)
        z -= h + 0.004
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.cyl(f"Chest_Castor{sx}{sy}", 0.045, 0.04, (cx + sx * (cw / 2 - 0.08), cy + sy * (cd / 2 - 0.08), 0.043), grd, axis="x", seg=10)
            b.box(f"Chest_Fork{sx}{sy}", (0.03, 0.04, 0.05), (cx + sx * (cw / 2 - 0.08), cy + sy * (cd / 2 - 0.08), 0.085), al, bevel=0.002, seg=1)
    # a few items on the chest top
    b.cyl("Chest_Mug", 0.04, 0.1, (cx + 0.3, cy, ch + 0.05), white, seg=14)

    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
