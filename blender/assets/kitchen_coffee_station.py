"""Scullery coffee station: a smoked-oak niche between two tall units, a Calacatta
counter with a steel espresso machine, a grinder, canisters and a row of cups, and a
lit walnut shelf with more cups on a dark glass splashback.

2.9 m long along X, 0.62 m deep, back against +Y, fronts face -Y. Origin is the
floor centre."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitchen_lib as L  # noqa: E402

importlib.reload(L)
common, materials = L.common, L.materials

NAME = "KitchenCoffee"

P = dict(
    name=NAME,
    length=2.9,
    depth=0.62,
    plinth=0.10,
    counter_z=0.92,
    counter_t=0.04,
    tall_w=0.6,
    tall_z=2.40,
    band_z=2.43,
    top_z=4.19,
    niche_top=2.05,
)


def cups(b, name, x0, y, z, count, mat, gap=0.1, r=0.04, h=0.07, handles=False):
    """A row of cups (or mugs, with loop handles turned a little toward the room). The
    foot ring sits on the shelf, so the underside isn't modelled."""
    bms = []
    for i in range(count):
        prof = [(r * 0.62, 0.0), (r * 0.8, 0.004), (r, h), (r - 0.003, h), (r * 0.78 - 0.002, 0.008), (0.0, 0.008)]
        bm = L.lathe(prof, 10, closed=False, sharp=60)
        bm.transform(Matrix.Translation((x0 + i * gap, y, z)))
        bms.append(bm)
    ob = common.mesh_object(f"{b.n}_{name}", L.merged(bms), b.col, mat, b.root)
    L.planar_uv(ob, 0.3)
    if handles:
        for i in range(count):
            a = math.radians(-60 + 25 * (i % 3))
            c, s_ = math.cos(a), math.sin(a)
            cx, cy = x0 + i * gap, y
            pts = []
            for k in range(5):
                t = k / 4
                rr = r * 0.98 + 0.024 * math.sin(math.pi * t)
                pts.append((cx + rr * c, cy + rr * s_, z + h * (0.82 - 0.6 * t)))
            b.tube(f"{name}_Handle{i}_NoCollide", pts, 0.0045, mat, closed=False, res=1)
    return ob


def build(**overrides):
    p = {**P, **overrides}
    b = L.Builder(p["name"])
    oak = materials.smoked_oak()
    walnut = materials.walnut()
    bronze = materials.bronze()
    steel = L.brushed_steel()
    polished = materials.steel()
    black = L.carcass()
    glass = L.black_glass()
    marble = L.calacatta_mat()
    cer = L.ceramic()
    char = L.dark_glaze()
    led = materials.emissive("M_LED_Warm", (1.0, 0.8, 0.55), 4.0)

    Lx, D = p["length"], p["depth"]
    yf, yb = -D / 2, D / 2
    t = 0.02
    ph, cz, ct = p["plinth"], p["counter_z"], p["counter_t"]
    x0, x1 = -Lx / 2, Lx / 2
    tw = p["tall_w"]
    xa, xb = x0 + tw, x1 - tw
    fr = L.Fronts(b, oak, bronze, yf)
    top = p["top_z"]

    b.box("Plinth", (Lx - 0.04, D - 0.09, ph), (0, (yf + 0.07 + yb - 0.02) / 2, ph / 2), black, bevel=0, tile=0)
    dy = yb - (yf + t)
    ym = (yf + t + yb) / 2

    # tall units either side
    for k, (a, c) in enumerate(((x0, xa), (xb, x1))):
        b.box(f"Tall{k}_Body", (c - a, dy, top - ph), ((a + c) / 2, ym, (ph + top) / 2), black, bevel=0, tile=0)
        fr.unit("d1", a, c, ph, p["tall_z"], f"Tall{k}_Lower")
        fr.unit("d1", a, c, p["band_z"], top, f"Tall{k}_Upper")
    # niche: base cabinet, counter, glass splashback, soffit and upper doors
    b.box("Base_Body", (xb - xa, dy, cz - ct - ph), ((xa + xb) / 2, ym, (ph + cz - ct) / 2), black, bevel=0, tile=0)
    fr.unit("dr2", xa, (xa + xb) / 2, ph, cz - ct, "Base0")
    fr.unit("d1", (xa + xb) / 2, xb, ph, cz - ct, "Base1")
    b.box("Counter", (xb - xa, D + 0.02, ct), ((xa + xb) / 2, yf - 0.02 + (D + 0.02) / 2, cz - ct / 2), marble, bevel=0.003,
          seg=2, tile=1.5, world_uv=True)
    nz1 = p["niche_top"]
    b.box("Niche_Back", (xb - xa, 0.02, nz1 - cz), ((xa + xb) / 2, yb - 0.01, (cz + nz1) / 2), glass, bevel=0, tile=0)
    b.box("Soffit_Body", (xb - xa, dy, top - nz1), ((xa + xb) / 2, ym, (nz1 + top) / 2), black, bevel=0, tile=0)
    mid = (xa + xb) / 2
    fr.unit("d2", xa, xb, p["band_z"] - 0.0, top, "NicheUpper")
    fr.slab("Soffit", xa, xb, nz1, p["band_z"] - 0.004)
    b.box("Soffit_LED", (xb - xa - 0.1, 0.02, 0.01), ((xa + xb) / 2, yb - 0.1, nz1 - 0.005), led, bevel=0, tile=0)
    # lit walnut shelf in the niche with cups and canisters
    sz = 1.45
    b.box("Shelf", (xb - xa, 0.22, 0.035), ((xa + xb) / 2, yb - 0.11, sz), walnut, bevel=0.003, seg=1, tile=0.5, shift=(0.3, 0.2))
    b.box("Shelf_LED", (xb - xa - 0.2, 0.01, 0.008), ((xa + xb) / 2, yb - 0.17, sz - 0.022), led, bevel=0, tile=0)
    yc = yb - 0.11
    cups(b, "ShelfCups", xa + 0.16, yc, sz + 0.0175, 6, cer, gap=0.105)
    cups(b, "ShelfMugs", xa + 0.9, yc, sz + 0.0175, 5, char, gap=0.105, r=0.042, h=0.09, handles=True)
    L.stack_plates(b, "Saucers", (xb - 0.2, yc, sz + 0.0175), cer, r=0.075, count=8, step=0.012)

    # --- espresso machine (left of centre)
    ex, ey = mid - 0.45, (yb - 0.02 - 0.2)
    mw, md, mh = 0.46, 0.40, 0.42
    b.box("Machine_Body", (mw, md, mh), (ex, ey, cz + mh / 2), steel, bevel=0.012, seg=3, tile=0)
    b.box("Machine_Panel", (mw - 0.1, 0.006, 0.12), (ex, ey - md / 2 - 0.002, cz + mh - 0.14), glass, bevel=0.002, tile=0)
    b.box("Machine_Tray", (mw - 0.04, 0.2, 0.025), (ex, ey - md / 2 + 0.06, cz + 0.0125), black, bevel=0.003, tile=0)
    b.box("Machine_Grate", (mw - 0.08, 0.17, 0.004), (ex, ey - md / 2 + 0.06, cz + 0.027), polished, bevel=0, tile=0)
    for i, sx in enumerate((-1, 1)):
        gx = ex + sx * 0.1
        b.lathe(f"Group{i}", [(0, 0), (0.032, 0), (0.032, -0.05), (0.024, -0.055), (0, -0.055)], black,
                loc=(gx, ey - md / 2 - 0.016, cz + mh - 0.22), segs=14, uv_tile=0)
        b.box(f"Portafilter{i}", (0.026, 0.12, 0.022), (gx, ey - md / 2 - 0.08, cz + mh - 0.255), bronze, bevel=0.004, tile=0)
    # steam wand and hot-water spout either side of the groups, two pressure gauges in the panel
    for k, sx in enumerate((-1, 1)):
        wx = ex + sx * 0.19
        b.tube(f"Machine_Wand{k}_NoCollide", [(wx, ey - md / 2 + 0.01, cz + mh - 0.12), (wx, ey - md / 2 - 0.04, cz + mh - 0.14),
                                              (wx + sx * 0.01, ey - md / 2 - 0.05, cz + 0.1)], 0.005, polished, closed=False, res=2)
        gxk = ex + sx * 0.09
        b.lathe(f"Machine_Gauge{k}", [(0.0, 0.0), (0.024, 0.0), (0.024, 0.008), (0.02, 0.01), (0.0, 0.01)], polished,
                loc=(gxk, ey - md / 2 - 0.004, cz + mh - 0.14), segs=14, sharp=30, uv_tile=0).rotation_euler = (math.radians(90), 0, 0)
    b.box("Machine_Cupwarmer", (mw - 0.02, md - 0.04, 0.012), (ex, ey, cz + mh + 0.006), black, bevel=0.002, tile=0)
    b.lathe("Machine_Dial", [(0, 0), (0.026, 0), (0.026, 0.022), (0, 0.022)], bronze, loc=(ex + 0.12, ey - md / 2 - 0.001, cz + mh - 0.28),
            segs=14, uv_tile=0).rotation_euler = (math.radians(-90), 0, 0)
    # --- grinder
    gx2 = mid + 0.0
    gy = ey - 0.02
    b.lathe("Grinder_Base", [(0, 0), (0.07, 0), (0.07, 0.2), (0.055, 0.25), (0, 0.25)], steel, loc=(gx2, gy, cz), segs=20, uv_tile=0)
    b.lathe("Grinder_Hopper", [(0, 0.25), (0.06, 0.25), (0.09, 0.40), (0.0, 0.40)], black, loc=(gx2, gy, cz), segs=20, uv_tile=0)
    # --- canisters and a tray
    canis = common.pbr_material("M_Coffee_Beans", (0.05, 0.03, 0.02), roughness=0.5)
    L.jars(b, "Canisters", mid + 0.3, ey - 0.06, cz, 3, materials.glass("M_Glass_Jar", (0.9, 0.95, 0.92), 0.25), bronze, canis,
           gap=0.12, seed=7)
    cups(b, "CounterCups", mid - 0.05, yf + 0.14, cz, 4, cer, gap=0.1)
    b.box("Tray", (0.36, 0.2, 0.02), (mid + 0.4, yf + 0.18, cz + 0.01), walnut, bevel=0.004, tile=0.5, shift=(0.1, 0.5))
    cups(b, "TrayCups", mid + 0.3, yf + 0.18, cz + 0.02, 3, char, gap=0.09, r=0.042, h=0.09, handles=True)

    # --- end panels
    for k, sx in enumerate((-1, 1)):
        b.box(f"EndPanel{k}", (0.025, D, top), (sx * (Lx / 2 + 0.0125), 0.0, top / 2), oak, bevel=0.002, seg=1, shift=(0.4 * k, 0.1))
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
