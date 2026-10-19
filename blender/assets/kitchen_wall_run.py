"""Kitchen wall of full-height walnut cabinetry, floor to ceiling (4.2 m): a pantry
bank, two integrated steel fridge-freezer columns, a double-oven tower and a run of
base drawers with a Calacatta counter and slab backsplash under lit upper cabinets.

Run along X (left = counter end, right = pantry end), 6.7 m long, back against +Y,
fronts face -Y. Origin is the floor centre of the footprint."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitchen_lib as L  # noqa: E402

importlib.reload(L)
common, materials = L.common, L.materials

NAME = "KitchenWallRun"

P = dict(
    name=NAME,
    depth=0.66,
    plinth=0.10,
    counter_z=0.92,
    counter_t=0.04,
    tall_z=2.40,           # top of the lower fronts in the tall zones
    band_z=2.43,           # bottom of the upper band
    top_z=4.19,            # just below the 4.2 m ceiling
    upper_depth=0.38,
    counter=[(0.9, "dr3"), (0.6, "dr1"), (0.9, "d2"), (0.7, "dr3")],   # sink over the 0.9 d2, dishwasher beside
    fridge_w=0.9,
    oven_w=0.8,
    pantry_w=1.0,
)


def build(**overrides):
    p = {**P, **overrides}
    b = L.Builder(p["name"])
    walnut = materials.walnut()
    bronze = materials.bronze()
    steel = L.brushed_steel()
    black = L.carcass()
    glass = L.black_glass()
    marble = L.calacatta_mat()
    led = materials.emissive("M_LED_Warm", (1.0, 0.8, 0.55), 4.0)

    D = p["depth"]
    yf = -D / 2
    yb = D / 2
    t = 0.02
    ph = p["plinth"]
    cz, ct = p["counter_z"], p["counter_t"]
    fr = L.Fronts(b, walnut, bronze, yf)
    fr_up = L.Fronts(b, walnut, bronze, yb - p["upper_depth"])

    cw = sum(w for w, _ in p["counter"])
    widths = [("counter", cw), ("oven", p["oven_w"]), ("fridge", 2 * p["fridge_w"]), ("pantry", p["pantry_w"])]
    total = sum(w for _, w in widths)
    x = -total / 2
    xs = {}
    for k, w in widths:
        xs[k] = (x, x + w)
        x += w

    # --- shared plinth (recessed, black) and one carcass block per zone
    b.box("Plinth", (total - 0.04, D - 0.07 - 0.02, ph), (0, (yf + 0.07 + yb - 0.02) / 2 - 0.0, ph / 2),
          black, bevel=0, tile=0)

    def tall_body(k):
        x0, x1 = xs[k]
        b.box(f"{k}_Body", (x1 - x0, yb - (yf + t), p["top_z"] - ph), ((x0 + x1) / 2, (yf + t + yb) / 2, (ph + p["top_z"]) / 2),
              black, bevel=0, tile=0)

    # --- counter zone: drawers, an integrated dishwasher, the sink base and a Calacatta top
    x0, x1 = xs["counter"]
    units = L.span(x0, p["counter"])
    sa, sc, _ = units[2]
    sx = (sa + sc) / 2
    sw, sd = 0.76, 0.42
    sy = yf + 0.06 + sd / 2
    hxa, hxb, hya, hyb = sx - sw / 2, sx + sw / 2, sy - sd / 2, sy + sd / 2
    zs = cz - ct - 0.25
    for tag, a, c, z1_ in (("Counter_BodyL", x0, hxa - 0.03, cz - ct), ("Counter_BodyR", hxb + 0.03, x1, cz - ct),
                           ("Counter_BodySink", hxa - 0.03, hxb + 0.03, zs)):
        b.box(tag, (c - a, yb - (yf + t), z1_ - ph), ((a + c) / 2, (yf + t + yb) / 2, (ph + z1_) / 2),
              black, bevel=0, tile=0)
    for i, (a, c, kind) in enumerate(units):
        fr.unit(kind, a, c, ph, cz - ct, f"Base{i}")
    L.slab_with_holes(b, "Counter_Top", x0, x1, yf - 0.02, yb, cz - ct / 2, ct, [(hxa, hxb, hya, hyb)], marble,
                      bevel=0.003, seg=2, tile=1.5)
    L.undermount_sink(b, "Sink", sx, sy, sw, sd, 0.22, cz - ct, steel, materials.steel(), corner=0.035,
                      drain=(0.18, 0.06))
    L.gooseneck_tap(b, "Tap", sx, hyb + 0.065, cz, bronze, reach=0.34, rise=0.36, lever=1, toward=-1)
    b.box("Backsplash", (x1 - x0, 0.02, p["tall_z"] - cz), ((x0 + x1) / 2, yb - 0.01, (cz + p["tall_z"]) / 2),
          marble, bevel=0.001, tile=1.5, world_uv=True)
    b.box("Upper_Body", (x1 - x0, p["upper_depth"] - t, p["top_z"] - p["tall_z"]),
          ((x0 + x1) / 2, yb - (p["upper_depth"] - t) / 2, (p["tall_z"] + p["top_z"]) / 2), black, bevel=0, tile=0)
    mid = (x0 + x1) / 2
    for i, (a, c) in enumerate(((x0, mid), (mid, x1))):
        fr_up.unit("d2", a, c, p["band_z"], p["top_z"], f"Upper{i}")
    # LED strip under the upper cabinets
    b.box("Counter_LED", (x1 - x0 - 0.1, 0.02, 0.012), ((x0 + x1) / 2, yb - p["upper_depth"] + 0.05, p["tall_z"] - 0.006),
          led, bevel=0, tile=0)
    # open end panel on the visible (left) end of the run
    b.box("EndPanel", (0.03, D + 0.0, p["top_z"]), (x0 - 0.015 + 0.0, 0.0, p["top_z"] / 2),
          walnut, bevel=0.002, seg=1, shift=(0.5, 0.1))

    # --- oven tower: carcass above and below; between them a black fascia with the oven
    #     cavities set into it, behind three steel doors with smoked windows
    x0, x1 = xs["oven"]
    xm = (x0 + x1) / 2
    zlo, zhi = 0.53, 2.23
    for tag, za_, zb_ in (("oven_BodyLow", ph, zlo), ("oven_BodyHigh", zhi, p["top_z"])):
        b.box(tag, (x1 - x0, yb - (yf + t), zb_ - za_), (xm, (yf + t + yb) / 2, (za_ + zb_) / 2), black, bevel=0, tile=0)
    b.box("oven_Back", (x1 - x0, 0.02, zhi - zlo), (xm, yb - 0.01, (zlo + zhi) / 2), black, bevel=0, tile=0)
    b.box("oven_SideL", (0.02, yb - (yf + t), zhi - zlo), (x0 + 0.01, (yf + t + yb) / 2, (zlo + zhi) / 2), black,
          bevel=0, tile=0)
    fr.unit("dr1", x0, x1, ph, 0.52, "OvenDrawer")
    ow = x1 - x0 - 0.04
    oglass = L.oven_glass()
    band = L.black_glass()
    cavity = L.dark_glaze()
    polished = materials.steel()
    holes = []
    for tag, z0_, z1_, dep in (("OvenA", 0.54, 1.14, 0.42), ("OvenB", 1.16, 1.76, 0.42), ("Steam", 1.78, 2.22, 0.36)):
        xa, xb, za, zb = L.oven_door(b, tag, xm - ow / 2, xm + ow / 2, z0_, z1_, yf, steel, oglass, band, led, steel,
                                     band=0.08 if tag != "Steam" else 0.07)
        holes.append((xa - 0.004, xb + 0.004, za - 0.004, zb + 0.004))
        L.oven_cavity(b, tag, xa - 0.004, xb + 0.004, za - 0.004, zb + 0.004, yf + t + 0.012, dep, cavity, polished,
                      racks=2 if tag != "Steam" else 1)
    L.panel_with_holes(b, "oven_Fascia", x0, x1, zlo, zhi, yf + t, 0.012, holes, black, bevel=0, seg=1)
    fr.slab("OvenFiller", x0, x1, 2.24, p["tall_z"])
    fr_t = L.Fronts(b, walnut, bronze, yf)
    fr_t.unit("d1", x0, x1, p["band_z"], p["top_z"], "OvenUpper")

    # --- fridge columns (integrated, steel)
    tall_body("fridge")
    x0, x1 = xs["fridge"]
    fw = p["fridge_w"]
    for i, (a, c) in enumerate(((x0, x0 + fw), (x0 + fw, x1))):
        b.box(f"Fridge{i}_Door", (fw - 0.004, 0.026, p["tall_z"] - ph - 0.004), ((a + c) / 2, yf + 0.013, (ph + p["tall_z"]) / 2),
              steel, bevel=0.003, seg=2, tile=0)
        # long steel bar handle near the meeting edge
        hx = (x0 + fw) + (-0.045 if i == 0 else 0.045)
        fr.vbar(f"Fridge{i}_Handle", hx, 0.75 if i == 0 else 0.85, 1.9, r=0.011, stand=0.04)
        fr_t.unit("d1", a, c, p["band_z"], p["top_z"], f"FridgeUpper{i}")
    # narrow dark vents at the foot
    b.box("Fridge_Grille", (2 * fw - 0.1, 0.006, 0.05), ((x0 + x1) / 2, yf + 0.06, ph - 0.015), black, bevel=0, tile=0)

    # --- pantry bank
    tall_body("pantry")
    x0, x1 = xs["pantry"]
    fr.unit("d2", x0, x1, ph, p["tall_z"], "Pantry")
    fr_t.unit("d2", x0, x1, p["band_z"], p["top_z"], "PantryUpper")

    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
