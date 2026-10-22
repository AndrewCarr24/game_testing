"""Modern gas station: a walk-in convenience store (ledgestone base, charcoal board-and-batten,
a flat roof behind a parapet, a black-framed glass front) and, to the street, a flat canopy on
four stone-clad columns over two pump islands (four dispensers), LED panels underneath, a
price pylon with blank lit panels, an ice chest, a propane cage, an air pump. Brand-neutral:
white fascia with a teal stripe, a pump pictogram, no lettering.

Inside: three gondola aisles, a wall of lit coolers, the counter (register, a wall of
cigarette packs), a coffee station, restroom and stock-room doors (closed); its fluorescent
panels and coolers are baked into COLOR_0.

Origin: the store's floor centre at its door sill; the canopy and pumps lie to -Y (the
street). Doors: TownGasStation_Door_1 (front, glass), _2 (back).
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import town_common as tc  # noqa: E402
import town_light  # noqa: E402

importlib.reload(tc.tt)
importlib.reload(tc)
importlib.reload(town_light)
V = tc.V

NAME = "TownGasStation"

P = dict(name=NAME, module="town_gas_station", x0=-9.0, x1=9.0, y0=-6.0, y1=6.0, thick=0.2, height=4.6,
         ceiling=3.4, canopy=(-10.5, 10.5, -20.0, -9.5), canopy_z=4.9, bake=True)


def dispenser(kit, x, y, facing_x=True):
    """A modern fuel dispenser (1.15 x 0.55 x 2.0): white body, dark screen, holsters, hoses."""
    B = kit.p("Pumps", "paint_white")
    B.box((x - 0.55, y - 0.27, 0.15), (x + 0.55, y + 0.27, 1.9), skip="b")
    kit.p("Pumps", "metal_dark").box((x - 0.58, y - 0.3, 1.9), (x + 0.58, y + 0.3, 2.15))
    kit.p("Pumps", "paint_teal").box((x - 0.58, y - 0.305, 2.0), (x + 0.58, y + 0.305, 2.06))
    for s in (-1, 1):
        yy = y + s * 0.28
        kit.p("PumpScreens", "glow_cool").face([(x - 0.3, yy + s * 0.002, 1.35), (x + 0.3, yy + s * 0.002, 1.35),
                                                 (x + 0.3, yy + s * 0.002, 1.65), (x - 0.3, yy + s * 0.002, 1.65)], toward=(0, s, 0))
        kit.p("PumpPanels", "metal_dark").box((x - 0.45, min(yy, yy + s * 0.01), 0.9), (x + 0.45, max(yy, yy + s * 0.01), 1.3))
        for hx in (-0.35, 0.0, 0.35):
            kit.p("Nozzles", "trim_black").box((x + hx - 0.05, min(yy, yy + s * 0.12), 0.95), (x + hx + 0.05, max(yy, yy + s * 0.12), 1.15))
            kit.p("Hoses", "rubber").polyline([V(x + hx, yy + s * 0.1, 0.95), V(x + hx + 0.1, yy + s * 0.35, 0.5),
                                               V(x + hx + 0.2, yy + s * 0.15, 0.3), V(x + 0.5, y, 0.8)], 0.012, sides=4)
    kit.collide((x - 0.58, y - 0.3, 0), (x + 0.58, y + 0.3, 2.15))


def gondola(kit, x, y0, y1, h=1.5):
    """A double-sided shelf aisle along y: base, upright, four shelves of goods each side."""
    G = kit.p("Gondolas", "paint_white")
    G.box((x - 0.45, y0, 0.0), (x + 0.45, y1, 0.12), skip="b")
    G.box((x - 0.04, y0, 0.12), (x + 0.04, y1, h), skip="b")
    for s in (-1, 1):
        for k in range(4):
            z = 0.12 + k * 0.34
            sx0, sx1 = sorted((x + s * 0.04, x + s * 0.45))
            G.box((sx0, y0, z + 0.3), (sx1, y1, z + 0.32), skip="")
            gx = x + s * 0.44
            uvs = tc.cell_uv(tc.WIN["bk_shop" if k % 2 == 0 else "bk_video"], sub=(0.05, 0.22 + 0.1 * k, 0.95, 0.34 + 0.1 * k))
            kit.p("Goods", "windows").face([(gx, y0 + 0.05, z + 0.02), (gx, y1 - 0.05, z + 0.02), (gx, y1 - 0.05, z + 0.29),
                                            (gx, y0 + 0.05, z + 0.29)][:: (1 if s > 0 else -1)],
                                           uvs=uvs if s > 0 else uvs[::-1], toward=(s, 0, 0))
    G.box((x - 0.45, y0 - 0.02, 0.0), (x + 0.45, y0, h), skip="k")
    G.box((x - 0.45, y1, 0.0), (x + 0.45, y1 + 0.02, h), skip="f")
    kit.collide((x - 0.45, y0, 0), (x + 0.45, y1, h))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    x0, x1, y0, y1, T, Hh, C = p["x0"], p["x1"], p["y0"], p["y1"], p["thick"], p["height"], p["ceiling"]
    xi0, xi1, yi0, yi1 = x0 + T, x1 - T, y0 + T, y1 - T

    # ================================================================ the store's shell
    door = (-1.2, 1.2, 0.0, 2.3)
    front_glass = [(-7.6, -1.6, 0.5, 2.9), (1.6, 7.6, 0.5, 2.9)]
    back_door = (5.0, 6.0, 0.0, 2.2)
    side_w = [(-3.0, -1.0, 1.4, 2.4)]
    openings = {"S": [door] + front_glass, "N": [back_door], "W": side_w}
    tc.shell(kit, x0, x1, y0, y1, Hh, openings, "bb_charcoal", base="ledgestone", base_h=0.9, thick=T,
             reveal_part=kit.p("Reveals", "trim_black"))
    tc.flat_roof(kit, x0, x1, y0, y1, Hh, parapet=0.7, wall="bb_charcoal", coping="trim_black")
    for a0, a1, z0, z1 in front_glass:
        mull = [a0 + (a1 - a0) * k / 3 for k in (1, 2)]
        tc.glazing(kit, "S", y0, a0, a1, z0, z1, cells=["bk_shop", "bk_display", "bk_shop", "bk_transom", "bk_transom", "bk_transom"],
                   mullions=mull, transom=2.35, depth=0.1)
    tc.glazing(kit, "S", y0, -1.2, 1.2, 2.35, 2.9, cell="bk_transom", depth=0.1, mullions=[0.0])
    tc.window(kit, "W", x0, -2.0, 1.4, 2.0, 1.0, cell="bk_blinds", trim="trim_black", casing=0.05)
    tc.hinged_door(kit, col, root, "S", y0, -0.6, 1.2, 2.3, depth=0.1, leaf="trim_black", index=1, style="glass", glass="bk_shop")
    tc.door(kit, "S", y0, 0.6, 1.2, 2.3, leaf="trim_black", style="glass", glass="bk_shop", casing=0.0, depth=0.1)
    tc.hinged_door(kit, col, root, "N", y1, 5.5, 1.0, 2.2, depth=0.1, leaf="metal_galv", index=2)
    # the storefront's canopy band, two goosenecks over the doors, a pump pictogram
    kit.p("Awning", "trim_black").box((-8.2, y0 - 1.1, 3.05), (8.2, y0, 3.25))
    kit.p("AwningGlow", "glow_white").face([(-8.0, y0 - 1.0, 3.045), (8.0, y0 - 1.0, 3.045), (8.0, y0 - 0.9, 3.045),
                                            (-8.0, y0 - 0.9, 3.045)], toward=(0, 0, -1))
    tc.sign(kit, "S", y0, 0.0, 3.55, 2.2, 1.1, "gas", glow=True)
    # outside the store: ice chest, propane cage, air pump, bins, HVAC on the roof, the back
    kit.p("IceChest", "plastic_white").box((-8.6, y0 - 1.0, 0.0), (-6.6, y0 - 0.2, 1.2), skip="b")
    kit.p("IceChest", "glow_cool").face([(-8.4, y0 - 1.005, 0.85), (-6.8, y0 - 1.005, 0.85), (-6.8, y0 - 1.005, 1.1),
                                         (-8.4, y0 - 1.005, 1.1)], toward=(0, -1, 0))
    kit.collide((-8.6, y0 - 1.0, 0), (-6.6, y0 - 0.2, 1.2))
    Cg = kit.p("Cage", "metal_galv")
    Cg.box((6.6, y0 - 1.0, 0.0), (8.6, y0 - 0.2, 0.05), skip="b")
    for k in range(9):
        x = 6.6 + k * 0.25
        Cg.box((x - 0.01, y0 - 1.0, 0.05), (x + 0.01, y0 - 0.98, 1.6))
    Cg.box((6.6, y0 - 1.0, 1.55), (8.6, y0 - 0.2, 1.6))
    for k in range(6):
        kit.p("PropaneTanks", "plastic_white").cyl((6.85 + k * 0.32, y0 - 0.6), 0.15, 0.05, 0.6, sides=8)
    kit.collide((6.6, y0 - 1.0, 0), (8.6, y0 - 0.2, 1.6))
    for (hx, hy) in ((-4.0, 1.5), (3.0, -2.5)):
        tc.hvac(kit, hx, hy, z=Hh, w=1.2, d=1.0, h=0.9)
    tc.meter(kit, "N", y1, 2.0)
    D = kit.p("Dumpster", "trim_green")
    D.box((-6.0, y1 + 0.8, 0.15), (-4.0, y1 + 2.2, 1.3))
    kit.p("Dumpster", "rubber").box((-6.05, y1 + 0.75, 1.3), (-3.95, y1 + 2.25, 1.38))
    kit.collide((-6.0, y1 + 0.8, 0), (-4.0, y1 + 2.2, 1.38))
    Ap = kit.p("AirPump", "paint_red")
    Ap.box((x1 + 0.5, y0 + 1.0, 0.0), (x1 + 0.9, y0 + 1.4, 1.3), skip="b")
    kit.p("AirPump", "rubber").polyline([V(x1 + 0.7, y0 + 0.99, 1.1), V(x1 + 0.8, y0 + 0.7, 0.5), V(x1 + 0.95, y0 + 0.9, 0.1)], 0.015, 4)
    kit.collide((x1 + 0.5, y0 + 1.0, 0), (x1 + 0.9, y0 + 1.4, 1.3))
    kit.p("Apron", "concrete").box((x0 - 1.0, y0 - 1.6, 0.0), (x1 + 1.5, y0, 0.02), skip="b")

    # ================================================================ the canopy and pumps
    cx0, cx1, cy0, cy1 = p["canopy"]
    cz = p["canopy_z"]
    F = kit.p("Fascia", "paint_white")
    F.box((cx0, cy0, cz), (cx1, cy1, cz + 1.0), skip="")
    kit.p("Stripe", "paint_teal").box((cx0 - 0.01, cy0 - 0.01, cz + 0.55), (cx1 + 0.01, cy1 + 0.01, cz + 0.75), skip="tb")
    kit.p("FasciaGlow", "glow_white").box((cx0 - 0.015, cy0 - 0.015, cz + 0.02), (cx1 + 0.015, cy1 + 0.015, cz + 0.06), skip="tb")
    tc.sign(kit, "S", cy0, -6.0, cz + 0.15, 1.4, 0.7, "gas", d=0.0, glow=True, thick=0.03)
    for i in range(3):
        for j in range(2):
            px_ = cx0 + 2.5 + i * 7.75
            py_ = cy0 + 2.5 + j * 5.5
            kit.p("CanopyLEDs", "glow_white").face([(px_ - 0.6, py_ - 0.6, cz - 0.005), (px_ + 0.6, py_ - 0.6, cz - 0.005),
                                                   (px_ + 0.6, py_ + 0.6, cz - 0.005), (px_ - 0.6, py_ + 0.6, cz - 0.005)],
                                                  toward=(0, 0, -1))
    for x in (-4.0, 4.0):
        for y in (cy0 + 2.6, cy1 - 2.6):
            kit.p("Columns", "ledgestone").box((x - 0.4, y - 0.4, 0.0), (x + 0.4, y + 0.4, 1.2), skip="b")
            kit.p("Columns", "trim_black").box((x - 0.42, y - 0.42, 1.2), (x + 0.42, y + 0.42, 1.28), skip="b")
            kit.p("Columns", "paint_white").box((x - 0.3, y - 0.3, 1.28), (x + 0.3, y + 0.3, cz), skip="bt")
            kit.collide((x - 0.42, y - 0.42, 0), (x + 0.42, y + 0.42, cz))
        # the island: a curb, two dispensers, bollards at the ends, a bin
        kit.p("Islands", "concrete").box((x - 0.6, cy0 + 1.2, 0.0), (x + 0.6, cy1 - 1.2, 0.18), skip="b")
        kit.p("Islands", "paint_yellow").box((x - 0.62, cy0 + 1.18, 0.0), (x + 0.62, cy0 + 1.3, 0.19), skip="b")
        kit.collide((x - 0.6, cy0 + 1.2, 0), (x + 0.6, cy1 - 1.2, 0.18))
        for y in ((cy0 + cy1) / 2 - 1.6, (cy0 + cy1) / 2 + 1.6):
            dispenser(kit, x, y)
        for y in (cy0 + 1.4, cy1 - 1.4):
            kit.p("Bollards", "paint_yellow").cyl((x, y), 0.1, 0.18, 1.2, sides=8)
            kit.collide((x - 0.1, y - 0.1, 0), (x + 0.1, y + 0.1, 1.2))
        kit.p("Bins", "trim_black").cyl((x + 0.35, (cy0 + cy1) / 2), 0.22, 0.18, 1.0, sides=8)
    kit.p("CanopyDeck", "concrete").box((cx0, cy0, 0.0), (cx1, cy1, 0.01), skip="b")
    # the price pylon at the street corner: stone base, a lit pump pictogram, blank price panels
    plx, ply = cx1 - 0.5, cy0 - 1.5
    kit.p("Pylon", "ledgestone").box((plx - 1.1, ply - 0.35, 0.0), (plx + 1.1, ply + 0.35, 1.4), skip="b")
    kit.p("Pylon", "trim_black").box((plx - 1.0, ply - 0.25, 1.4), (plx + 1.0, ply + 0.25, 6.2))
    tc.sign(kit, "S", ply - 0.25, plx, 4.7, 1.8, 0.9, "gas", d=0.0, glow=True, thick=0.02)
    tc.sign(kit, "N", ply + 0.25, plx, 4.7, 1.8, 0.9, "gas", d=0.0, glow=True, thick=0.02)
    for k in range(3):
        z = 2.0 + k * 0.82
        for sd, side in ((ply - 0.25, "S"), (ply + 0.25, "N")):
            tc.wbox(kit.p("PricePanels", "metal_dark"), side, sd, plx - 0.85, plx + 0.85, z, z + 0.62, 0, 0.02, skip="back")
            for dgt in range(4):                    # four seven-segment-ish digits, blank of meaning
                a = plx - 0.05 + dgt * 0.2
                tc.wquad(kit.p("PriceGlow", "neon_red"), side, sd, a, a + 0.12, z + 0.12, z + 0.15, 0.022)
                tc.wquad(kit.p("PriceGlow", "neon_red"), side, sd, a, a + 0.12, z + 0.47, z + 0.5, 0.022)
                tc.wquad(kit.p("PriceGlow", "neon_red"), side, sd, a + 0.1, a + 0.13, z + 0.14, z + 0.48, 0.022)
    kit.collide((plx - 1.1, ply - 0.35, 0), (plx + 1.1, ply + 0.35, 6.2))

    # ================================================================ inside the store
    kit.sub = 0.75
    tc.room(kit, xi0, xi1, yi0, yi1, 0.0, C, walls="block", floor="tile_floor", ceiling="paint_white", name="Store",
            base="trim_black", openings={"S": [door] + front_glass, "N": [back_door], "W": side_w})
    kit.sub = None
    for x in (-5.0, -2.2, 0.6):
        gondola(kit, x, -2.6, 2.4)
    # coolers along the back wall: glowing glass doors over lit shelves of drinks
    for k in range(8):
        a0 = -8.4 + k * 1.05
        kit.p("Coolers", "metal_dark").box((a0, yi1 - 0.9, 0.0), (a0 + 1.05, yi1, 2.3), skip="b")
        tc.wquad(kit.p("CoolerDoors", "windows", glow=True), "S", yi1 - 0.9, a0 + 0.05, a0 + 1.0, 0.12, 2.15, 0.005,
                 uvs=tc.cell_uv(tc.WIN["bk_shop"], sub=(0.02, 0.05, 0.98, 0.98)))
        kit.p("CoolerHandles", "chrome").box((a0 + 0.88, yi1 - 0.93, 0.9), (a0 + 0.91, yi1 - 0.9, 1.5))
    kit.collide((-8.4, yi1 - 0.9, 0), (0.0, yi1, 2.3))
    kit.p("Coolers", "trim_black").box((-8.4, yi1 - 0.95, 2.3), (0.0, yi1, 2.7), skip="")
    # the counter (L-shaped, by the door), register, card reader, the cigarette wall behind
    Ct = kit.p("Counter", "darkwood")
    Ct.box((3.6, -3.8, 0.0), (7.6, -3.1, 1.0), skip="bt")
    Ct.box((3.6, -3.1, 0.0), (4.3, 0.2, 1.0), skip="bt")
    Tp = kit.p("CounterTop", "polished")
    Tp.box((3.5, -3.9, 1.0), (7.7, -3.0, 1.05))
    Tp.box((3.5, -3.0, 1.0), (4.4, 0.3, 1.05))
    kit.collide((3.5, -3.9, 0), (7.7, -3.0, 1.05))
    kit.collide((3.5, -3.0, 0), (4.4, 0.3, 1.05))
    kit.p("Register", "metal_dark").box((5.0, -3.6, 1.05), (5.5, -3.2, 1.25))
    kit.p("Register", "glow_cool").face([(5.03, -3.605, 1.12), (5.47, -3.605, 1.12), (5.47, -3.605, 1.23), (5.03, -3.605, 1.23)],
                                        toward=(0, -1, 0))
    kit.p("Register", "metal_dark").box((6.2, -3.75, 1.05), (6.35, -3.6, 1.2))
    kit.p("CigWall", "trim_black").box((4.9, xi1 * 0 - 0.9, 1.2), (7.7, -0.75, 2.5))
    tc.wquad(kit.p("CigPacks", "windows"), "S", -0.9, 5.0, 7.6, 1.3, 2.4, 0.002, uvs=tc.cell_uv(tc.WIN["bk_video"], sub=(0.02, 0.1, 0.98, 0.75)))
    kit.collide((4.9, -0.9, 0), (7.7, -0.75, 2.5))
    # the coffee station on the west wall
    kit.p("Coffee", "darkwood").box((xi0, -1.5, 0.0), (xi0 + 0.6, 1.5, 0.9), skip="b")
    kit.p("Coffee", "polished").box((xi0, -1.55, 0.9), (xi0 + 0.65, 1.55, 0.95))
    for k in range(3):
        kit.p("Brewers", "metal_dark").box((xi0 + 0.05, -1.2 + k * 0.8, 0.95), (xi0 + 0.45, -0.8 + k * 0.8, 1.55))
        kit.p("Brewers", "neon_red").box((xi0 + 0.45, -1.1 + k * 0.8, 1.4), (xi0 + 0.46, -1.05 + k * 0.8, 1.45))
    kit.collide((xi0, -1.55, 0), (xi0 + 0.65, 1.55, 0.95))
    # restroom and stock-room doors (closed), the ceiling panels
    for a in (2.0, 3.6):
        tc.door(kit, "S", yi1, a, 0.9, 2.1, leaf="metal_galv", trim="trim_black", casing=0.06, depth=0.05)
    for i in range(3):
        for j in range(3):
            lx, ly = -6.0 + i * 6.0, -3.5 + j * 3.5
            kit.p("CeilingPanels", "glow_white").face([(lx - 1.2, ly - 0.3, C - 0.01), (lx + 1.2, ly - 0.3, C - 0.01),
                                                      (lx + 1.2, ly + 0.3, C - 0.01), (lx - 1.2, ly + 0.3, C - 0.01)],
                                                     toward=(0, 0, -1))
            kit.light((lx, ly, C - 0.05), (0.92, 0.95, 1.0), 55, 1.4, kind="AREA")
    kit.light((-4.2, yi1 - 1.3, 1.2), (0.85, 0.92, 1.0), 40, 2.5, kind="AREA", direction=(0, -1, 0))

    # ================================================================ LOD1
    far = tc.Far(n)
    far.box((x0, y0, 0), (x1, y1, Hh + 0.7), "bb_charcoal", top="tar")
    far.box((x0, y0, 0), (x1, y1, 0.9), "ledgestone", skip="bt")
    for a0, a1, z0, z1 in front_glass:
        far.quad("S", y0, a0, a1, z0, z1, "window_lit", d=0.02)
    far.box((cx0, cy0, cz), (cx1, cy1, cz + 1.0), "paint_white", top="paint_white", skip="")
    for x in (-4.0, 4.0):
        for y in (cy0 + 2.6, cy1 - 2.6):
            far.box((x - 0.35, y - 0.35, 0), (x + 0.35, y + 0.35, cz), "paint_white", skip="bt")
        far.box((x - 0.6, cy0 + 1.2, 0), (x + 0.6, cy1 - 1.2, 2.1), "paint_white", skip="b")
    far.box((plx - 1.0, ply - 0.25, 0.0), (plx + 1.0, ply + 0.25, 6.2), "trim_black", skip="b")

    kit.entrance((0.0, y0 - 0.1, 0.0), "-Y", 2.4, kind="door", note="glass pair: TownGasStation_Door_1 (left leaf) opens")
    kit.entrance((5.5, y1 + 0.1, 0.0), "+Y", 1.0, kind="door", note="TownGasStation_Door_2, back")
    kit.info.update(walk_in=True, storeys=1, rooms=["store 17.6 x 11.6 (aisles, coolers, counter, coffee)"],
                    footprint=[round(cx0, 3), round(ply - 0.4, 3), round(x1 + 1.5, 3), round(y1 + 2.3, 3)],
                    lighting="store interior baked into COLOR_0; canopy LEDs and pylon are glow")
    parts = tc.finish(kit, col, root, far)
    if p["bake"]:
        meshes = [o for o in root.children_recursive if o.type == "MESH" and not o.name.endswith("_LOD1")]
        town_light.bake(kit, root, meshes, [(xi0, yi0, 0.0, xi1, yi1, C)])
    return root, parts
