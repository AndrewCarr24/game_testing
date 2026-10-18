"""Scullery working wall: smoked-oak base cabinets under a brushed-stainless worktop
with a double-bowl sink and a bronze gooseneck tap, a stainless splashback, and three
open walnut shelves stocked with plates, bowls, glasses and jars.

5.2 m long along X, back against +Y, fronts face -Y. Origin is the floor centre."""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitchen_lib as L  # noqa: E402

importlib.reload(L)
common, materials = L.common, L.materials

NAME = "KitchenScullery"

P = dict(
    name=NAME,
    length=5.2,
    depth=0.64,
    plinth=0.10,
    counter_z=0.92,
    counter_t=0.04,
    units=[(0.9, "dr3"), (0.6, "dr1"), (1.7, "d2"), (0.9, "dr3"), (1.1, "d2")],
    sink_x=0.0,            # computed from units: centred over the 1.7 unit
    shelf_z=(1.50, 1.95, 2.40),
    shelf_depth=0.30,
)


def build(**overrides):
    p = {**P, **overrides}
    b = L.Builder(p["name"])
    oak = materials.smoked_oak()
    walnut = materials.walnut()
    bronze = materials.bronze()
    steel = L.brushed_steel()
    polished = materials.steel()
    black = L.carcass()
    cer = L.ceramic()
    char = L.dark_glaze()
    led = materials.emissive("M_LED_Warm", (1.0, 0.8, 0.55), 4.0)
    glass_m = materials.glass("M_Glass_Jar", (0.9, 0.95, 0.92), 0.25)

    Lx, D = p["length"], p["depth"]
    yf, yb = -D / 2, D / 2
    t = 0.02
    ph, cz, ct = p["plinth"], p["counter_z"], p["counter_t"]
    x0, x1 = -Lx / 2, Lx / 2
    units = L.span(x0, p["units"])
    fr = L.Fronts(b, oak, bronze, yf)

    b.box("Plinth", (Lx - 0.04, D - 0.09, ph), (0, (yf + 0.07 + yb - 0.02) / 2, ph / 2), black, bevel=0, tile=0)
    b.box("Body", (Lx, yb - (yf + t), cz - ct - ph), (0, (yf + t + yb) / 2, (ph + cz - ct) / 2), black, bevel=0, tile=0)
    for i, (a, c, kind) in enumerate(units):
        fr.unit(kind, a, c, ph, cz - ct, f"Base{i}")

    # --- stainless worktop with the double sink cut into the d2 unit
    sa, sc, _ = units[2]
    sx = (sa + sc) / 2
    sw, sd = 1.3, 0.44
    sy = yf + 0.04 + (D - 0.04) / 2 - 0.02
    xa, xb = sx - sw / 2, sx + sw / 2
    ya, yb2 = sy - sd / 2, sy + sd / 2
    y_lo, y_hi = yf - 0.015, yb
    zc = cz - ct / 2

    def top(name, a, c, d, e):
        b.box(name, (c - a, e - d, ct), ((a + c) / 2, (d + e) / 2, zc), steel, bevel=0.002, seg=1, tile=0)

    top("Top_Front", x0, x1, y_lo, ya)
    top("Top_Back", x0, x1, yb2, y_hi)
    top("Top_West", x0, xa, ya, yb2)
    top("Top_East", xb, x1, ya, yb2)
    # ribbed drainer on the east side (grooves = dark stripes)
    for k in range(9):
        gx = xb + 0.06 + k * 0.034
        if gx < x1 - 0.1 and gx < xb + 0.5:
            b.box(f"Groove{k}", (0.008, 0.40, 0.002), (gx, sy + 0.0, cz + 0.0005), black, bevel=0, tile=0)
    # basins
    bh, th = 0.21, 0.003
    bw = (sw - 0.02) / 2 - 0.02
    for tag, cx in (("A", sx - sw / 4 - 0.005), ("B", sx + sw / 4 + 0.005)):
        zb = cz - ct - bh + 0.04
        b.box(f"Sink{tag}_Floor", (bw, sd - 0.02, th), (cx, sy, zb + th / 2), steel, bevel=0, tile=0)
        for wn, size, c in (("W", (th, sd - 0.02, bh), (cx - bw / 2 + th / 2, sy, zb + bh / 2)),
                            ("E", (th, sd - 0.02, bh), (cx + bw / 2 - th / 2, sy, zb + bh / 2)),
                            ("S", (bw, th, bh), (cx, sy - (sd - 0.02) / 2 + th / 2, zb + bh / 2)),
                            ("N", (bw, th, bh), (cx, sy + (sd - 0.02) / 2 - th / 2, zb + bh / 2))):
            b.box(f"Sink{tag}_{wn}", size, c, steel, bevel=0, tile=0)
        b.lathe(f"Drain{tag}", [(0, 0), (0.03, 0), (0.03, 0.003), (0, 0.003)], polished, loc=(cx, sy, zb + th),
                segs=14, uv_tile=0)

    # --- bronze gooseneck tap at the back, centred
    tx, ty = sx, y_hi - 0.075
    b.lathe("Tap_Base", [(0, cz), (0.03, cz), (0.025, cz + 0.014), (0.017, cz + 0.06), (0, cz + 0.06)], bronze,
            loc=(tx, ty, 0), segs=18, uv_tile=0)
    R = 0.19
    pts = [(tx, ty, cz + 0.05), (tx, ty, cz + 0.42)]
    for i in range(0, 19):
        a = math.pi * i / 18
        pts.append((tx, ty - R + R * math.cos(a), cz + 0.42 + R * math.sin(a) * 0.85))
    pts.append((tx, ty - 2 * R, cz + 0.42 - 0.04))
    b.tube("Tap_Spout", pts, 0.0115, bronze, closed=False, res=4)
    b.lathe("Tap_Head", [(0, 0), (0.015, 0), (0.015, -0.05), (0, -0.05)], bronze, loc=(tx, ty - 2 * R, cz + 0.42 - 0.04),
            segs=12, uv_tile=0)
    for k, sgn in enumerate((-1, 1)):
        b.box(f"Tap_Lever{k}", (0.075, 0.012, 0.012), (tx + sgn * 0.075, ty - 0.005, cz + 0.06), bronze, bevel=0.002, tile=0)

    # --- stainless splashback
    b.box("Splashback", (Lx, 0.012, 0.56), (0, yb - 0.006, cz + 0.28), steel, bevel=0.001, tile=0)

    # --- open walnut shelves
    sdp = p["shelf_depth"]
    shelf_y = yb - sdp / 2
    for i, z in enumerate(p["shelf_z"]):
        b.box(f"Shelf{i}", (Lx, sdp, 0.04), (0, shelf_y, z), walnut, bevel=0.003, seg=1, tile=0.5, shift=(0.17 * i, 0.3 * i))
        b.box(f"ShelfLED{i}", (Lx - 0.3, 0.012, 0.01), (0, shelf_y - sdp / 2 + 0.03, z - 0.025), led, bevel=0, tile=0)
    # black steel end uprights keep the shelves honest
    for k, sxk in enumerate((x0 + 0.02, x1 - 0.02)):
        b.box(f"Upright{k}", (0.04, sdp, p["shelf_z"][-1] - p["shelf_z"][0] + 0.2),
              (sxk, shelf_y, (p["shelf_z"][0] + p["shelf_z"][-1]) / 2 + 0.0), black, bevel=0.002, tile=0)

    z0 = p["shelf_z"][0] + 0.02
    z1 = p["shelf_z"][1] + 0.02
    z2 = p["shelf_z"][2] + 0.02
    yc = shelf_y
    # top shelf: stacked plates and bowls
    L.stack_plates(b, "PlatesA", (x0 + 0.45, yc, z2), cer, r=0.13, count=9)
    L.stack_plates(b, "PlatesB", (x0 + 0.85, yc, z2), cer, r=0.115, count=8)
    L.stack_plates(b, "BowlsA", (x0 + 1.4, yc, z2), char, r=0.09, count=6, step=0.03)
    L.stack_plates(b, "BowlsB", (x0 + 1.75, yc, z2), char, r=0.09, count=5, step=0.03)
    L.jars(b, "JarsTop", x0 + 2.4, yc, z2, 7, glass_m, bronze,
           common.pbr_material("M_Grain_Flour", (0.55, 0.45, 0.28), roughness=0.9), gap=0.14, seed=5)
    L.stack_plates(b, "PlatesC", (x1 - 1.0, yc, z2), cer, r=0.13, count=9)
    L.stack_plates(b, "BowlsC", (x1 - 0.55, yc, z2), char, r=0.095, count=7, step=0.03)
    # middle shelf: jars of pasta, grains and beans
    L.jars(b, "JarsMid", x0 + 0.35, yc, z1, 14, glass_m, bronze,
           common.pbr_material("M_Grain_Dark", (0.28, 0.2, 0.12), roughness=0.9), gap=0.155, seed=8)
    L.jars(b, "JarsMid2", x0 + 2.65, yc, z1, 14, glass_m, walnut,
           common.pbr_material("M_Grain_Flour", (0.55, 0.45, 0.28), roughness=0.9), gap=0.15, seed=11)
    # lower shelf: more crockery and a row of glasses/vases
    L.stack_plates(b, "BowlsL", (x0 + 0.6, yc, z0), cer, r=0.13, count=6, step=0.04)
    L.stack_plates(b, "PlatesL", (x0 + 1.0, yc, z0), char, r=0.12, count=8)
    L.jars(b, "Glasses", x0 + 1.6, yc, z0, 9, glass_m, glass_m,
           common.pbr_material("M_Water", (0.8, 0.85, 0.85), roughness=0.1), gap=0.10, seed=3)
    L.stack_plates(b, "PlatesR2", (x1 - 1.5, yc, z0), cer, r=0.14, count=10)
    L.stack_plates(b, "BowlsR2", (x1 - 0.95, yc, z0), char, r=0.1, count=5, step=0.035)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
