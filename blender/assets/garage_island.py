"""Mudroom island: a cream lacquer base with an open oak shelf of linen baskets on
both long sides, a thick oak worktop with a rounded end, a bronze rail on one side
and, on top, a folded-linen stack, a wooden tray with a plant and a pair of glass
carafes. Seats three on the stool side, with two oak-and-linen stools.

Units are metres. The front faces -Y, the origin is the floor centre.
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import garage_cabinets as gk  # noqa: E402

importlib.reload(gk)
common, materials = gk.common, gk.materials

NAME = "GarageIsland"

P = dict(name=NAME, width=2.6, depth=1.0, height=0.92, top_t=0.05)


def build(**overrides):
    p = {**P, **overrides}
    b = gk.Builder(p["name"])
    grd = gk.graphite_dark()
    cream, oak, sage = gk.cream(), gk.oak_light(), gk.sage()
    bronze = materials.bronze()
    oat = gk.linen("M_Fabric_Oat", (0.42, 0.37, 0.30))
    ink = gk.linen("M_Fabric_Sage", (0.16, 0.22, 0.16))
    leaf = common.pbr_material("M_Mudroom_Leaf", (0.04, 0.12, 0.035), roughness=0.6)
    terracotta = common.pbr_material("M_Mudroom_Pot", (0.30, 0.13, 0.07), roughness=0.7)
    glass = materials.glass("M_Garage_ShelfGlass", tint=(0.6, 0.8, 0.8), alpha=0.35, roughness=0.05)

    W, D, H, tt = p["width"], p["depth"], p["height"], p["top_t"]
    yf, yb = -D / 2, D / 2
    bh = H - tt
    ph = 0.09
    g = 0.003

    b.lo_hi("Plinth", (-W / 2 + 0.06, yf + 0.08, 0), (W / 2 - 0.06, yb - 0.08, ph), grd, bevel=0)
    # frame: two end panels and a centre panel, a bottom, a mid shelf
    t = 0.03
    for k, x in enumerate((-W / 2 + 0.03, 0, W / 2 - 0.03 - t)):
        xa = x if k != 1 else -t / 2
        b.lo_hi(f"Panel{k}", (xa if k != 1 else -t / 2, yf + 0.03, ph), ((xa + t) if k != 1 else t / 2, yb - 0.03, bh), cream, bevel=0.002)
    b.lo_hi("Bottom", (-W / 2 + 0.03, yf + 0.03, ph), (W / 2 - 0.03, yb - 0.03, ph + t), cream, bevel=0.002)
    b.lo_hi("Mid", (-W / 2 + 0.03, yf + 0.03, 0.5), (W / 2 - 0.03, yb - 0.03, 0.5 + t), oak, bevel=0.002)
    # baskets: one set facing the front, one set facing the back (linen boxes in the cubbies)
    for side, sy in (("F", -1), ("B", 1)):
        ya, yb2 = (yf + 0.03, yf + 0.03 + 0.42) if sy < 0 else (yb - 0.03 - 0.42, yb - 0.03)
        for k, (xa, xb) in enumerate(((-W / 2 + 0.065, -t / 2 - 0.02), (t / 2 + 0.02, W / 2 - 0.065))):
            for lvl, z in enumerate((ph + t, 0.5 + t)):
                hh = 0.3 if lvl == 0 else bh - (0.5 + t) - 0.05
                n = 2
                w_ = (xb - xa) / n
                for q in range(n):
                    b.lo_hi(f"Basket{side}{k}{lvl}{q}", (xa + q * w_ + 0.02, ya + 0.02, z + 0.005), (xa + (q + 1) * w_ - 0.02, yb2 - 0.0, z + 0.005 + min(hh, 0.3) * (0.8 if (q + lvl) % 2 else 1.0)),
                           oat if (q + k + lvl) % 3 else ink, bevel=0.03, tile=0.25, seg=3)
    # worktop: oak with an overhang on the stool side
    b.lo_hi("Top", (-W / 2, yf - 0.03, bh), (W / 2, yb, H), oak, bevel=0.01, seg=3, tile=0.5)
    # bronze towel rail on the end
    for sy in (-1, 1):
        b.cyl(f"Rail_Post{sy}", 0.008, 0.08, (W / 2 + 0.04, sy * 0.3, 0.7), bronze, axis="x", seg=8)
    b.cyl("Rail", 0.011, 0.66, (W / 2 + 0.08, 0, 0.7), bronze, axis="y", seg=10)
    b.lo_hi("Towel", (W / 2 + 0.06, -0.12, 0.45), (W / 2 + 0.075, 0.12, 0.7), oat, bevel=0.004, tile=0.25, seg=1)

    # --- on top: linen stack, tray with plant, carafes
    for k in range(5):
        b.lo_hi(f"Stack{k}", (-1.1, -0.3, H + k * 0.045), (-0.72, 0.1, H + (k + 1) * 0.045 - 0.002), ink if k % 2 else oat, bevel=0.012, tile=0.25, seg=2)
    b.lo_hi("Tray", (0.1, -0.2, H), (0.7, 0.2, H + 0.025), oak, bevel=0.006, seg=2)
    b.cyl("Pot", 0.07, 0.14, (0.25, 0.0, H + 0.025 + 0.07), terracotta, seg=14, r2=0.055)
    for k in range(7):
        a = k * 2.4
        b.sphere(f"Leaf{k}", 0.06, (0.25 + 0.05 * math.cos(a), 0.05 * math.sin(a), H + 0.25 + 0.04 * (k % 3)), leaf, scale=(1, 1, 0.8), seg=8, rings=6)
    for k in range(2):
        b.cyl(f"Carafe{k}", 0.045, 0.2, (0.5 + k * 0.12, 0.0, H + 0.025 + 0.1), glass, seg=10)

    # --- two stools on the front
    for i, sx in enumerate((-0.6, 0.6)):
        sy = yf - 0.4
        b.cyl(f"Stool{i}_Seat", 0.19, 0.05, (sx, sy, 0.66), oak, seg=20, bevel=0.0)
        b.cyl(f"Stool{i}_Pad", 0.18, 0.03, (sx, sy, 0.705), oat, seg=20)
        for k in range(4):
            a = k * math.pi / 2 + math.pi / 4
            b.cyl(f"Stool{i}_Leg{k}", 0.014, 0.64, (sx + 0.14 * math.cos(a), sy + 0.14 * math.sin(a), 0.32), bronze, seg=8)
        b.cyl(f"Stool{i}_Ring", 0.15, 0.012, (sx, sy, 0.26), bronze, seg=18)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
