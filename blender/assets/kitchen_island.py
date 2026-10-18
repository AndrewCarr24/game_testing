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

    # ---- top: four slabs round the sink hole (veins continue by world UVs)
    sx0, sy0, sw, sd = p["sink"]
    xa, xb = sx0 - sw / 2, sx0 + sw / 2
    ya, yb2 = sy0 - sd / 2, sy0 + sd / 2
    y_lo, y_hi = yf - 0.02, yo
    x_lo, x_hi = -Lx / 2, Lx / 2
    zc = zt - tt / 2

    def slab(name, x0, x1, y0, y1):
        b.box(name, (x1 - x0, y1 - y0, tt), ((x0 + x1) / 2, (y0 + y1) / 2, zc), marble, bevel=0.003, seg=2,
              tile=1.5, world_uv=True)

    slab("Top_South", x_lo, x_hi, y_lo, ya)
    slab("Top_North", x_lo, x_hi, yb2, y_hi)
    slab("Top_West", x_lo, xa, ya, yb2)
    slab("Top_East", xb, x_hi, ya, yb2)

    # ---- sink basin (steel) under the hole
    bw, bd, bh, th = sw - 0.02, sd - 0.02, 0.20, 0.003
    zb = zt - tt - bh + 0.0
    b.box("Sink_Floor", (bw, bd, th), (sx0, sy0, zb + th / 2), brushed, bevel=0, tile=0)
    for tag, size, c in (("W", (th, bd, bh), (sx0 - bw / 2 + th / 2, sy0, zb + bh / 2)),
                         ("E", (th, bd, bh), (sx0 + bw / 2 - th / 2, sy0, zb + bh / 2)),
                         ("S", (bw, th, bh), (sx0, sy0 - bd / 2 + th / 2, zb + bh / 2)),
                         ("N", (bw, th, bh), (sx0, sy0 + bd / 2 - th / 2, zb + bh / 2))):
        b.box(f"Sink_{tag}", size, c, brushed, bevel=0, tile=0)
    # drain
    b.lathe("Drain", [(0, 0), (0.035, 0), (0.035, 0.003), (0, 0.003)], steel, loc=(sx0 - 0.15, sy0, zb + th), segs=16,
            uv_tile=0)

    # ---- tap: bronze gooseneck behind the sink
    tx, ty = sx0, yb2 + 0.07
    b.lathe("Tap_Base", [(0, zt), (0.030, zt), (0.026, zt + 0.012), (0.017, zt + 0.045), (0, zt + 0.045)], bronze,
            loc=(tx, ty, 0), segs=20, uv_tile=0)
    pts = [(tx, ty, zt + 0.04), (tx, ty, zt + 0.40)]
    arc = []
    R = 0.20
    for i in range(0, 19):
        a = math.pi * i / 18
        arc.append((tx, ty - R + R * math.cos(a), zt + 0.40 + R * math.sin(a) * 0.9))
    pts += arc
    pts += [(tx, ty - 2 * R, zt + 0.40 - 0.05)]
    b.tube("Tap_Spout", pts, 0.012, bronze, closed=False, res=4)
    b.lathe("Tap_Head", [(0, 0), (0.016, 0), (0.016, -0.05), (0, -0.05)], bronze,
            loc=(tx, ty - 2 * R, zt + 0.40 - 0.05), segs=14, uv_tile=0)
    b.box("Tap_Lever", (0.012, 0.07, 0.012), (tx + 0.05, ty - 0.015, zt + 0.07), bronze, bevel=0.002, tile=0)

    # ---- cabinetry: black carcass, plinth, smoked-oak fronts
    x0 = -Lx / 2 + et
    x1 = Lx / 2 - et
    b.box("Plinth", (x1 - x0, yb - (yf + 0.07), ph), ((x0 + x1) / 2, (yf + 0.07 + yb) / 2, ph / 2), black, bevel=0, tile=0)
    b.box("Body", (x1 - x0, yb - ybody0, zt - tt - ph), ((x0 + x1) / 2, (ybody0 + yb) / 2, (ph + zt - tt) / 2),
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

    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
