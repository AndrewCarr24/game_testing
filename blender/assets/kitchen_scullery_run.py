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
    # --- worktop: one stainless sheet with the double-bowl cut-out over the 1.7 m unit and a
    #     pressed drainer to its east
    sa, sc, _ = units[2]
    sx = (sa + sc) / 2
    sw, sd = 1.3, 0.44
    sy = yf + 0.04 + (D - 0.04) / 2 - 0.02
    y_lo, y_hi = yf - 0.015, yb
    zc = cz - ct / 2
    bw = (sw - 0.05) / 2
    cA, cB = sx - sw / 4 - 0.006, sx + sw / 4 + 0.006
    holes = [(c - bw / 2, c + bw / 2, sy - sd / 2, sy + sd / 2) for c in (cA, cB)]
    # carcass: solid either side, dropped under the bowls so they hang in a void
    gx0, gx1 = sx - sw / 2 - 0.03, sx + sw / 2 + 0.03
    zs = cz - ct - 0.25
    for tag, a, c, z1_ in (("BodyW", x0, gx0, cz - ct), ("BodyE", gx1, x1, cz - ct), ("BodySink", gx0, gx1, zs)):
        b.box(tag, (c - a, yb - (yf + t), z1_ - ph), ((a + c) / 2, (yf + t + yb) / 2, (ph + z1_) / 2),
              black, bevel=0, tile=0)
    for i, (a, c, kind) in enumerate(units):
        fr.unit(kind, a, c, ph, cz - ct, f"Base{i}")
    L.slab_with_holes(b, "Top", x0, x1, y_lo, y_hi, zc, ct, holes, steel, bevel=0.002, seg=1, tile=0)
    for tag, cx in (("SinkA", cA), ("SinkB", cB)):
        L.undermount_sink(b, tag, cx, sy, bw, sd, 0.21, cz - ct, steel, polished, corner=0.03, drain=(0.0, 0.1))
    # pressed drainer: shallow grooves fanning to the bowl (dark lines)
    xb = sx + sw / 2
    for k in range(9):
        gx = xb + 0.06 + k * 0.034
        if gx < x1 - 0.1 and gx < xb + 0.5:
            b.box(f"Groove{k}_NoCollide", (0.008, 0.40, 0.002), (gx, sy + 0.0, cz + 0.0005), black, bevel=0, tile=0)
    # --- bronze gooseneck tap at the back, centred, with a matching rinse spray beside it
    tx, ty = sx, y_hi - 0.075
    L.gooseneck_tap(b, "Tap", tx, ty, cz, bronze, reach=0.38, rise=0.42, lever=1, toward=-1)
    b.lathe("Rinse", [(0.0, cz), (0.02, cz), (0.016, cz + 0.012), (0.011, cz + 0.03), (0.011, cz + 0.11),
                      (0.014, cz + 0.12), (0.0, cz + 0.12)], bronze, loc=(tx - 0.3, ty, 0), segs=12, sharp=30, uv_tile=0)

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
