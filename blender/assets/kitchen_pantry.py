"""Scullery pantry bank: smoked-oak full-height cabinetry to the ceiling with a lit
glass-fronted dry-goods cabinet in the middle (jars on shelves visible through the
glass), solid oak doors either side and upper doors above a shadow gap.

2.85 m (plus 25 mm end panels) long along X, 0.62 m deep, back against +Y, fronts face -Y. Origin is the
floor centre."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitchen_lib as L  # noqa: E402

importlib.reload(L)
common, materials = L.common, L.materials

NAME = "KitchenPantry"

P = dict(
    name=NAME,
    length=2.85,
    depth=0.62,
    plinth=0.10,
    tall_z=2.40,
    band_z=2.43,
    top_z=4.19,
)


def build(**overrides):
    p = {**P, **overrides}
    b = L.Builder(p["name"])
    oak = materials.smoked_oak()
    walnut = materials.walnut()
    bronze = materials.bronze()
    black = L.carcass()
    dark = materials.black_metal()
    led = materials.emissive("M_LED_Warm", (1.0, 0.8, 0.55), 4.0)
    glass = materials.glass("M_Glass_Cabinet", (0.8, 0.88, 0.9), 0.14)
    glass_j = materials.glass("M_Glass_Jar", (0.9, 0.95, 0.92), 0.25)
    cer = L.ceramic()
    char = L.dark_glaze()

    Lx, D = p["length"], p["depth"]
    yf, yb = -D / 2, D / 2
    t = 0.02
    ph = p["plinth"]
    x0, x1 = -Lx / 2, Lx / 2
    w3 = Lx / 3
    fr = L.Fronts(b, oak, bronze, yf)

    b.box("Plinth", (Lx - 0.04, D - 0.09, ph), (0, (yf + 0.07 + yb - 0.02) / 2, ph / 2), black, bevel=0, tile=0)
    xa, xb = x0 + w3, x0 + 2 * w3
    zlo, zhi = ph + 0.02, p["tall_z"] - 0.02
    H = p["top_z"] - ph
    dy = yb - (yf + t)
    ym = (yf + t + yb) / 2
    for tag, a, c in (("BodyL", x0, xa), ("BodyR", xb, x1)):
        b.box(tag, (c - a, dy, H), ((a + c) / 2, ym, (ph + p["top_z"]) / 2), black, bevel=0, tile=0)
    # open middle: back, floor and ceiling of the glass cabinet; the upper band is solid
    b.box("BodyM_Back", (xb - xa, 0.02, H), ((xa + xb) / 2, yb - 0.01, (ph + p["top_z"]) / 2), black, bevel=0, tile=0)
    b.box("BodyM_Floor", (xb - xa, dy, zlo - ph), ((xa + xb) / 2, ym, (ph + zlo) / 2), black, bevel=0, tile=0)
    b.box("BodyM_Top", (xb - xa, dy, p["top_z"] - zhi), ((xa + xb) / 2, ym, (zhi + p["top_z"]) / 2), black, bevel=0, tile=0)
    fr.unit("d2", x0, xa, ph, p["tall_z"], "SolidL")
    fr.unit("d2", xb, x1, ph, p["tall_z"], "SolidR")
    for i, (a, c) in enumerate(((x0, xa), (xa, xb), (xb, x1))):
        fr.unit("d2", a, c, p["band_z"], p["top_z"], f"Upper{i}")

    # --- glass-fronted middle: black frame, glass, shelves, jars
    ft = 0.03
    gw = xb - xa
    for k, (size, c) in enumerate((((ft, 0.02, zhi - zlo), (xa + ft / 2 + 0.004, yf + 0.01, (zlo + zhi) / 2)),
                                   ((ft, 0.02, zhi - zlo), (xb - ft / 2 - 0.004, yf + 0.01, (zlo + zhi) / 2)),
                                   ((gw - 0.008, 0.02, ft), ((xa + xb) / 2, yf + 0.01, zlo + ft / 2)),
                                   ((gw - 0.008, 0.02, ft), ((xa + xb) / 2, yf + 0.01, zhi - ft / 2)),
                                   ((0.025, 0.02, zhi - zlo), ((xa + xb) / 2, yf + 0.01, (zlo + zhi) / 2)))):
        b.box(f"GlassFrame{k}", size, c, dark, bevel=0.0015, tile=0)
    b.box("Glass_L", (gw / 2 - 0.03, 0.004, zhi - zlo - 0.05), (xa + gw / 4 - 0.005, yf + 0.014, (zlo + zhi) / 2), glass,
          bevel=0, tile=0, smooth=False)
    b.box("Glass_R", (gw / 2 - 0.03, 0.004, zhi - zlo - 0.05), (xa + 3 * gw / 4 + 0.005, yf + 0.014, (zlo + zhi) / 2), glass,
          bevel=0, tile=0, smooth=False)
    # slim bronze bar pulls on the glass doors' meeting stiles
    zc = (zlo + zhi) / 2
    for k, sx in enumerate((-1, 1)):
        fr.vbar(f"GlassPull{k}", (xa + xb) / 2 + sx * 0.045, zc - 0.3, zc + 0.3, r=0.006, stand=0.026)
    # interior shelves (walnut) with a warm LED under each
    shelf_z = [0.55, 0.95, 1.35, 1.75, 2.12]
    for i, z in enumerate(shelf_z):
        b.box(f"Shelf{i}", (gw - 0.08, D - 0.12, 0.025), ((xa + xb) / 2, (yf + 0.08 + yb) / 2, z), walnut, bevel=0.002,
              seg=1, tile=0.5, shift=(0.2 * i, 0.1))
        b.box(f"ShelfLED{i}", (gw - 0.2, 0.01, 0.008), ((xa + xb) / 2, yf + 0.1, z - 0.017), led, bevel=0, tile=0)
    yc = (yf + 0.08 + yb) / 2
    grain = common.pbr_material("M_Grain_Flour", (0.55, 0.45, 0.28), roughness=0.9)
    grain2 = common.pbr_material("M_Grain_Dark", (0.28, 0.2, 0.12), roughness=0.9)
    xj = xa + 0.12
    L.jars(b, "Jars0", xj, yc, shelf_z[0] + 0.0125, 4, glass_j, bronze, grain, gap=0.2, seed=2)
    L.jars(b, "Jars1", xj, yc, shelf_z[1] + 0.0125, 5, glass_j, walnut, grain2, gap=0.16, seed=4)
    L.jars(b, "Jars2", xj, yc, shelf_z[2] + 0.0125, 5, glass_j, bronze, grain, gap=0.16, seed=6)
    L.stack_plates(b, "Plates3", (xa + 0.25, yc, shelf_z[3] + 0.0125), cer, r=0.13, count=8)
    L.stack_plates(b, "Bowls3", (xa + 0.62, yc, shelf_z[3] + 0.0125), char, r=0.1, count=6, step=0.03)
    L.stack_plates(b, "Plates4", (xa + 0.35, yc, shelf_z[4] + 0.0125), char, r=0.115, count=6)
    L.stack_plates(b, "Plates4b", (xa + 0.7, yc, shelf_z[4] + 0.0125), cer, r=0.115, count=6)
    for k, sx in enumerate((-1, 1)):
        b.box(f"EndPanel{k}", (0.025, D, p["top_z"]), (sx * (Lx / 2 + 0.0125), 0.0, p["top_z"] / 2), oak, bevel=0.002, seg=1,
              shift=(0.4 * k, 0.1))
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
