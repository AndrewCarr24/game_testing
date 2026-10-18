"""Workshop island for the showroom garage: a graphite base with drawers on both
long sides, a thick brushed-steel top with a bullnose edge, a pegged rail with
sockets, a machinist vice, a small bench grinder, tool trays, a laptop on a stand and
two tall aluminium-and-leather stools.

Units are metres. The front (drawers, stools) faces -Y, the origin is the floor centre
of the bench itself.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import garage_cabinets as gk  # noqa: E402

importlib.reload(gk)
common, materials = gk.common, gk.materials

NAME = "GarageWorkbench"

P = dict(name=NAME, width=2.6, depth=0.9, height=0.95, top_t=0.05, stools=2)


def build(**overrides):
    p = {**P, **overrides}
    b = gk.Builder(p["name"])
    gr, grd, al, glow = gk.graphite(), gk.graphite_dark(), gk.aluminium(), gk.led()
    steel = materials.steel()
    ac = common.pbr_material("M_Garage_Accent", (0.55, 0.07, 0.025), roughness=0.5)
    leather = common.pbr_material("M_Garage_Leather", (0.30, 0.17, 0.09), roughness=0.55)
    white = gk.white_lacquer()
    screen = common.pbr_material("M_Garage_Screen", (0.01, 0.014, 0.02), roughness=0.12, coat=0.4)

    W, D, H, tt = p["width"], p["depth"], p["height"], p["top_t"]
    ph = 0.1
    bh = H - tt
    g, dt = 0.003, 0.02
    yf, yb = -D / 2, D / 2

    # base carcass (dark), recessed plinth, drawer fronts on the front and the back
    b.lo_hi("Carcass", (-W / 2 + 0.06, yf + 0.03, ph), (W / 2 - 0.06, yb - 0.03, bh), grd, bevel=0)
    b.lo_hi("Plinth", (-W / 2 + 0.1, yf + 0.08, 0), (W / 2 - 0.1, yb - 0.08, ph), grd, bevel=0)
    for side, sy in (("F", -1), ("B", 1)):
        ya, yb2 = (yf + 0.03 - dt + 0.0, yf + 0.03) if sy < 0 else (yb - 0.03, yb - 0.03 + dt)
        cols = 4 if sy < 0 else 3
        cw = (W - 0.12) / cols
        for c in range(cols):
            xa = -W / 2 + 0.06 + c * cw
            hs = [0.15, 0.15, bh - ph - 0.3 - 4 * g]
            z = bh - g
            for k, h in enumerate(hs):
                b.lo_hi(f"Drawer{side}{c}_{k}", (xa + g / 2, ya, z - h), (xa + cw - g / 2, yb2, z), gr, bevel=0.002)
                py = ya - 0.007 if sy < 0 else yb2 + 0.007
                b.box(f"Drawer{side}{c}_{k}_Pull", (cw - 0.2, 0.014, 0.016), (xa + cw / 2, py, z - 0.03), al, bevel=0.0015, seg=1)
                z -= h + g
    # top: brushed steel with a thick bullnose edge, a thin black underlay
    b.lo_hi("Top", (-W / 2, yf, bh), (W / 2, yb, H), steel, bevel=0.012, seg=3, tile=1.0)
    b.lo_hi("Top_Shadow", (-W / 2 + 0.02, yf + 0.02, bh - 0.012), (W / 2 - 0.02, yb - 0.02, bh), grd, bevel=0)

    # --- on the bench
    # socket / pegged rail along the back
    b.lo_hi("Rail", (-W / 2 + 0.2, yb - 0.1, H), (W / 2 - 0.2, yb - 0.04, H + 0.06), al, bevel=0.004, seg=2)
    for i in range(6):
        b.box(f"Socket{i}", (0.07, 0.004, 0.04), (-0.9 + i * 0.36, yb - 0.102, H + 0.03), grd, bevel=0.003, seg=1)
    b.lo_hi("Rail_LED", (-W / 2 + 0.22, yb - 0.104, H + 0.055), (W / 2 - 0.22, yb - 0.1, H + 0.062), glow, bevel=0, tile=1.0)
    # vice on the right end: jaw block, moving jaw, screw and handle
    vx = W / 2 - 0.25
    b.box("Vice_Base", (0.16, 0.2, 0.07), (vx, yf + 0.2, H + 0.035), gr, bevel=0.004, seg=2)
    b.box("Vice_Jaw", (0.16, 0.05, 0.075), (vx, yf + 0.08, H + 0.105), ac, bevel=0.004, seg=2)
    b.cyl("Vice_Screw", 0.009, 0.2, (vx, yf + 0.1, H + 0.04), steel, axis="y", seg=8)
    b.cyl("Vice_Handle", 0.007, 0.2, (vx, yf + 0.0, H + 0.04), steel, axis="x", seg=8)
    # bench grinder at the left end
    gx = -W / 2 + 0.3
    b.box("Grinder_Base", (0.3, 0.17, 0.05), (gx, yb - 0.3, H + 0.025), gr, bevel=0.004, seg=2)
    b.box("Grinder_Motor", (0.2, 0.12, 0.11), (gx, yb - 0.3, H + 0.105), ac, bevel=0.01, seg=2)
    for s in (-1, 1):
        b.cyl(f"Grinder_Wheel{s}", 0.075, 0.025, (gx + s * 0.12, yb - 0.3, H + 0.11), grd, axis="x", seg=14)
    # tool trays with spanners
    for i, x in enumerate((-0.45, 0.15)):
        b.lo_hi(f"Tray{i}", (x - 0.25, yf + 0.25, H), (x + 0.25, yf + 0.5, H + 0.03), grd, bevel=0.004, seg=1)
        for k in range(6):
            b.box(f"Tray{i}_Tool{k}", (0.025, 0.14 + 0.01 * k, 0.012), (x - 0.19 + k * 0.075, yf + 0.375, H + 0.036), steel, bevel=0.002, seg=1)
    # laptop on a stand, an engine-part sculpture (brake caliper block and disc)
    b.box("Stand", (0.28, 0.2, 0.012), (0.75, yf + 0.38, H + 0.09), al, bevel=0.003, seg=1)
    for sx in (-1, 1):
        b.box(f"Stand_Leg{sx}", (0.012, 0.18, 0.09), (0.75 + sx * 0.12, yf + 0.38, H + 0.045), al, bevel=0.002, seg=1)
    b.box("Laptop_Base", (0.3, 0.21, 0.012), (0.75, yf + 0.37, H + 0.102), al, bevel=0.003, seg=1)
    scr = b.box("Laptop_Screen", (0.3, 0.008, 0.2), (0.75, yf + 0.27, H + 0.21), screen, bevel=0.003, seg=1)
    scr.rotation_euler = (-0.18, 0, 0)
    b.cyl("Disc", 0.14, 0.012, (0.1, yb - 0.32, H + 0.006 + 0.14), steel, axis="y", seg=24).location.z = H + 0.14
    b.cyl("Disc_Hub", 0.055, 0.03, (0.1, yb - 0.32, H + 0.14), grd, axis="y", seg=14)
    b.box("Caliper", (0.07, 0.06, 0.12), (0.1 + 0.1, yb - 0.32, H + 0.2), ac, bevel=0.008, seg=2)
    b.cyl("Mug", 0.04, 0.1, (-0.1, yf + 0.7, H + 0.05), white, seg=14)

    # --- stools (front side), bar-height
    for i in range(p["stools"]):
        sx = -0.6 + i * 1.2 if p["stools"] > 1 else 0
        sy = yf - 0.45
        b.cyl(f"Stool{i}_Seat", 0.2, 0.06, (sx, sy, 0.72), leather, seg=20, bevel=0.0)
        b.cyl(f"Stool{i}_Pad", 0.19, 0.03, (sx, sy, 0.765), leather, seg=20)
        for k in range(4):
            import math
            a = k * math.pi / 2 + math.pi / 4
            lx, ly = sx + 0.15 * math.cos(a), sy + 0.15 * math.sin(a)
            fx, fy = sx + 0.19 * math.cos(a), sy + 0.19 * math.sin(a)
            b.cyl(f"Stool{i}_Leg{k}", 0.012, 0.69, ((lx + fx) / 2, (ly + fy) / 2, 0.345), al, seg=8)
        b.cyl(f"Stool{i}_Ring", 0.17, 0.014, (sx, sy, 0.3), al, seg=20, r2=0.17)
        b.cyl(f"Stool{i}_Foot", 0.2, 0.01, (sx, sy, 0.005), grd, seg=20)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
