"""Chef's kitchen island: a 4.8 m Calacatta slab with waterfall ends, smoked-oak
drawer fronts on the working (-Y) side, a flush steel prep sink with a bronze
gooseneck tap, a 0.45 m overhang on the stool (+Y) side, a ceramic bowl of lemons.

Long axis along X; working side faces -Y; stools go on +Y. Origin is the floor centre."""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitchen_lib as L  # noqa: E402

importlib.reload(L)
common, materials = L.common, L.materials

NAME = "KitchenIsland"

P = dict(
    name=NAME,
    length=4.8,
    y_front=-0.76,          # working face of the cabinetry
    y_back=0.30,            # back of the cabinetry (the knee space begins)
    y_over=0.76,            # edge of the stool overhang
    top_z=0.93,
    top_t=0.06,
    end_t=0.07,
    plinth=0.10,
    units=[(0.95, "dr3"), (0.95, "dr3"), (1.2, "d2"), (0.8, "dr3"), (0.76, "dr3")],
    sink=(0.17, -0.30, 0.86, 0.44),     # centre x, centre y, width, depth
)


def build(**overrides):
    p = {**P, **overrides}
    b = L.Builder(p["name"])
    oak = materials.smoked_oak()
    bronze = materials.bronze()
    steel = materials.steel()
    brushed = L.brushed_steel()
    black = L.carcass()
    marble = L.calacatta_mat()

    Lx = p["length"]
    yf, yb, yo = p["y_front"], p["y_back"], p["y_over"]
    zt, tt, et, ph = p["top_z"], p["top_t"], p["end_t"], p["plinth"]
    t = 0.02
    ybody0 = yf + t
    D_total = yo - yf + 0.02

    # ---- waterfall ends: full-depth slabs under the top
    for side, sx in (("L", -1), ("R", 1)):
        b.box(f"End_{side}", (et, D_total, zt - tt), (sx * (Lx / 2 - et / 2), (yf - 0.02 + yo) / 2, (zt - tt) / 2),
              marble, bevel=0.003, seg=2, tile=1.5, world_uv=True)

    # ---- top: one slab with the sink cut-out (veins continue by world UVs)
    sx0, sy0, sw, sd = p["sink"]
    xa, xb = sx0 - sw / 2, sx0 + sw / 2
    ya, yb2 = sy0 - sd / 2, sy0 + sd / 2
    y_lo, y_hi = yf - 0.02, yo
    zc = zt - tt / 2
    L.slab_with_holes(b, "Top", -Lx / 2, Lx / 2, y_lo, y_hi, zc, tt, [(xa, xb, ya, yb2)], marble,
                      bevel=0.003, seg=2, tile=1.5)

    # ---- undermount prep sink: brushed-steel bowl with a drain toward the back
    L.undermount_sink(b, "Sink", sx0, sy0, sw, sd, 0.20, zt - tt, brushed, steel, corner=0.035,
                      drain=(0.0, 0.08))

    # ---- tap: bronze gooseneck behind the sink, lever on the right
    L.gooseneck_tap(b, "Tap", sx0, yb2 + 0.07, zt, bronze, reach=0.40, rise=0.40, lever=1, toward=-1)
    # soap / filtered-water lever beside it
    b.lathe("Tap_Filter", [(0.0, zt), (0.02, zt), (0.016, zt + 0.012), (0.009, zt + 0.03), (0.009, zt + 0.17),
                           (0.0, zt + 0.17)], bronze, loc=(sx0 + 0.24, yb2 + 0.07, 0), segs=12, sharp=30, uv_tile=0)
    b.tube("Tap_FilterSpout", [(sx0 + 0.24, yb2 + 0.07, zt + 0.16), (sx0 + 0.24, yb2 + 0.07 - 0.07, zt + 0.19),
                               (sx0 + 0.24, yb2 + 0.07 - 0.12, zt + 0.17)], 0.006, bronze, closed=False, res=2)

    # ---- cabinetry: black carcass, plinth, smoked-oak fronts
    x0 = -Lx / 2 + et
    x1 = Lx / 2 - et
    b.box("Plinth", (x1 - x0, yb - (yf + 0.07), ph), ((x0 + x1) / 2, (yf + 0.07 + yb) / 2, ph / 2), black, bevel=0, tile=0)
    # carcass in three blocks so the sink bowl hangs in a real void (not under a lid)
    zs = zt - tt - 0.23
    gx0, gx1 = xa - 0.03, xb + 0.03
    for tag, a, c, z1_ in (("BodyL", x0, gx0, zt - tt), ("BodyR", gx1, x1, zt - tt), ("BodySink", gx0, gx1, zs)):
        b.box(tag, (c - a, yb - ybody0, z1_ - ph), ((a + c) / 2, (ybody0 + yb) / 2, (ph + z1_) / 2),
              black, bevel=0, tile=0)
    fr = L.Fronts(b, oak, bronze, yf)
    for i, (a, c, kind) in enumerate(L.span(x0, p["units"])):
        fr.unit(kind, a, c, ph, zt - tt - 0.005, f"Unit{i}")

    # stool side: smoked-oak panelled back with a shadow line, knee space beneath the overhang
    b.box("Back_Panel", (x1 - x0, 0.03, zt - tt - ph), ((x0 + x1) / 2, yb + 0.015, (ph + zt - tt) / 2), oak,
          bevel=0.002, shift=(0.3, 0.3))
    b.box("Back_Reveal", (x1 - x0 - 0.08, 0.004, 0.012), ((x0 + x1) / 2, yb + 0.032, zt - tt - 0.03), black,
          bevel=0, tile=0)
    # under-top LED shadow gap on the overhang
    led = materials.emissive("M_LED_Warm", (1.0, 0.8, 0.55), 4.0)
    b.box("Overhang_LED", (x1 - x0 - 0.2, 0.012, 0.012), ((x0 + x1) / 2, yo - 0.05, zt - tt - 0.006), led, bevel=0, tile=0)

    # ---- bowl of lemons
    cer = L.ceramic("M_Ceramic_White")
    lemon = common.pbr_material("M_Lemon", (0.75, 0.55, 0.03), roughness=0.5)
    lime = common.pbr_material("M_Lime", (0.12, 0.30, 0.03), roughness=0.5)
    L.fruit_bowl(b, (-1.45, 0.20, zt), cer, lemon, lime, r=0.17)

    # prep corner left of the sink: an end-grain walnut board with a chef's knife, and a pair
    # of turned walnut pepper and salt mills
    walnut = materials.walnut()
    bx_, by_ = sx0 - 0.95, sy0 - 0.02
    b.box("Board", (0.50, 0.34, 0.035), (bx_, by_, zt + 0.0175), walnut, bevel=0.006, seg=2, tile=0.5, shift=(0.3, 0.6))
    knife = b.box("Knife_Blade_NoCollide", (0.21, 0.045, 0.002), (bx_ + 0.04, by_ - 0.06, zt + 0.036), steel, bevel=0, tile=0)
    knife.rotation_euler = (0, 0, math.radians(12))
    hnd = b.box("Knife_Handle_NoCollide", (0.12, 0.022, 0.018), (bx_ - 0.115, by_ - 0.083, zt + 0.044), black, bevel=0.005,
                seg=2, tile=0)
    hnd.rotation_euler = (0, 0, math.radians(12))
    for k, (mx, mh) in enumerate(((bx_ + 0.42, 0.21), (bx_ + 0.50, 0.17))):
        b.lathe(f"Mill{k}", [(0.024, 0.0), (0.026, 0.006), (0.022, 0.03), (0.019, mh * 0.55), (0.024, mh * 0.82),
                             (0.02, mh - 0.008), (0.008, mh), (0.0, mh + 0.004)], walnut if k == 0 else black,
                loc=(mx, by_ + 0.12, zt), segs=12, sharp=40, uv_tile=0.3, closed=False)

    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
