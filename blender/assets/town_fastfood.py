"""Fast-food drive-through (generic, chain-style, no brand): a flat-roofed box (ledgestone base,
charcoal board-and-batten, cedar panels) under a tilted red-brown metal band round the
roofline with a lit underside and a lit burger pictogram, big windows, an entry canopy, a
drive-through window on the east side under a black canopy (the menu board, speaker and
clearance bar are town_menu_board / town_clearance_bar, placed on the layout's lane).

Walk-in: the dining room (booths under the windows, tables and chairs, a drink station),
the order counter under three lit menu boards, a pass-through to the kitchen (grills,
fryers, a hood, prep tables, the drive-through window), its lights baked into COLOR_0.

Origin: floor centre at the door sill; the front (the door in the tower) faces -Y; the lane
runs along +X. Doors: TownFastFood_Door_1 (front), _2 (kitchen, back).
"""
import importlib
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

NAME = "TownFastFood"
P = dict(name=NAME, module="town_fastfood", x0=-9.0, x1=9.0, y0=-7.0, y1=7.0, thick=0.2, height=4.2, ceiling=3.2,
         partition=0.0, bake=True)


def chair(kit, x, y, facing):
    """A simple metal-and-vinyl chair facing +-X (facing = +1/-1)."""
    S = kit.p("Chairs", "vinyl_red")
    S.box((x - 0.22, y - 0.22, 0.44), (x + 0.22, y + 0.22, 0.5))
    bx = x - facing * 0.2
    S.box((min(bx, bx - facing * 0.05), y - 0.21, 0.5), (max(bx, bx - facing * 0.05), y + 0.21, 0.9))
    L = kit.p("ChairLegs", "metal_dark")
    for dx in (-0.18, 0.18):
        for dy in (-0.18, 0.18):
            L.box((x + dx - 0.015, y + dy - 0.015, 0.0), (x + dx + 0.015, y + dy + 0.015, 0.44), skip="tb")
    kit.collide((x - 0.22, y - 0.22, 0), (x + 0.22, y + 0.22, 0.5))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    x0, x1, y0, y1, T, Hh, C, XP = p["x0"], p["x1"], p["y0"], p["y1"], p["thick"], p["height"], p["ceiling"], p["partition"]
    xi0, xi1, yi0, yi1 = x0 + T, x1 - T, y0 + T, y1 - T

    # ================================================================ shell
    door = (-5.1, -3.9, 0.0, 2.3)
    win_s = [(-8.3, -6.0, 0.9, 2.6), (-3.0, -0.6, 0.9, 2.6)]
    win_w = [(-5.8, -2.2, 0.9, 2.6), (1.0, 4.6, 0.9, 2.6)]
    dt_win = (-2.6, -1.2, 1.0, 2.2)                      # the drive-through window (E)
    k_door = (5.5, 6.5, 0.0, 2.2)                        # kitchen back door (N)
    openings = {"S": [door] + win_s, "W": win_w, "E": [dt_win], "N": [k_door]}
    tc.shell(kit, x0, x1, y0, y1, Hh, openings, "bb_charcoal", base="ledgestone", base_h=0.9, thick=T,
             reveal_part=kit.p("Reveals", "trim_black"))
    tc.flat_roof(kit, x0, x1, y0, y1, Hh, parapet=0.6, wall="bb_charcoal", coping="trim_black")
    # cedar accent panels on the east and north walls
    for side, plane, a0, a1 in (("E", x1, 0.5, 4.8), ("N", y1, -7.0, 3.5)):
        tc.wbox(kit.p("Cedar", "cedar"), side, plane, a0, a1, 1.0, Hh - 0.3, 0, 0.04, skip="back")
    for a0, a1, z0, z1 in win_s + win_w[:1]:
        side, plane = ("S", y0) if (a0, a1, z0, z1) in win_s else ("W", x0)
        tc.glazing(kit, side, plane, a0, a1, z0, z1, cells=["bk_cafe", "bk_transom"], transom=2.2,
                   mullions=[(a0 + a1) / 2], depth=0.1)
    tc.glazing(kit, "W", x0, win_w[1][0], win_w[1][1], 0.9, 2.6, cells=["bk_shop", "bk_transom"], transom=2.2,
               mullions=[(win_w[1][0] + win_w[1][1]) / 2], depth=0.1)
    tc.glazing(kit, "E", x1, dt_win[0], dt_win[1], dt_win[2], dt_win[3], cell="bk_shop", mullions=[(dt_win[0] + dt_win[1]) / 2],
               depth=0.1)
    tc.hinged_door(kit, col, root, "S", y0, -4.5, 1.2, 2.3, depth=0.1, leaf="trim_black", index=1, style="glass", glass="bk_cafe")
    tc.hinged_door(kit, col, root, "N", y1, 6.0, 1.0, 2.2, depth=0.1, leaf="metal_galv", index=2)
    # the chain-style tilted band round the roofline (red-brown metal), the burger pictogram on it
    zb0, zb1, tilt = Hh - 0.6, Hh + 1.6, 0.55
    Bd = kit.p("Band", "trim_red")
    for side, plane, a0, a1 in (("S", y0, x0, x1), ("N", y1, x0, x1), ("E", x1, y0, y1), ("W", x0, y0, y1)):
        Pf, u, nn = tc.frame(side, plane)
        lo, hi = min(a0, a1), max(a0, a1)
        e = tilt
        q = [Pf(lo - e, zb0, e), Pf(hi + e, zb0, e), Pf(hi, zb1, 0.0), Pf(lo, zb1, 0.0)]
        if side in "NE":
            q = [Pf(hi + e, zb0, e), Pf(lo - e, zb0, e), Pf(lo, zb1, 0.0), Pf(hi, zb1, 0.0)]
        Bd.face(q, toward=nn + V(0, 0, 0.4))
        kit.p("BandSoffit", "trim_black").face([Pf(lo - e, zb0, e), Pf(hi + e, zb0, e), Pf(hi, zb0, 0.0), Pf(lo, zb0, 0.0)],
                                               toward=(0, 0, -1))
        kit.p("BandGlow", "glow_white").face([Pf(lo - e, zb0 - 0.001, e - 0.02), Pf(hi + e, zb0 - 0.001, e - 0.02),
                                              Pf(hi + e - 0.06, zb0 - 0.001, e - 0.08), Pf(lo - e + 0.06, zb0 - 0.001, e - 0.08)],
                                             toward=(0, 0, -1))
    kit.p("RoofDeckTop", "tar").face([(x0, y0, zb1), (x1, y0, zb1), (x1, y1, zb1), (x0, y1, zb1)], toward=(0, 0, 1))
    tc.sign(kit, "S", y0 - tilt * 0.5, -4.5, zb0 + 0.35, 2.6, 1.3, "burger", glow=True, d=0.05) if False else None
    Pf, u, nn = tc.frame("S", y0)
    sq = [Pf(-6.0, zb0 + 0.3, tilt * 0.9 + 0.05), Pf(-3.0, zb0 + 0.3, tilt * 0.9 + 0.05), Pf(-3.0, zb0 + 1.8, 0.05 - 0.1),
          Pf(-6.0, zb0 + 1.8, 0.05 - 0.1)]
    kit.p("Sign", "signs", glow=True).face(sq, uvs=tc.sign_uv("burger"), toward=nn + V(0, 0, 0.4))
    # the entry canopy over the door, the drive-through window's canopy
    kit.p("Awning", "trim_black").box((-6.4, y0 - 1.4, 2.6), (-2.6, y0, 2.75))
    kit.p("AwningGlow", "glow_white").face([(-6.2, y0 - 1.2, 2.595), (-2.8, y0 - 1.2, 2.595), (-2.8, y0 - 1.1, 2.595),
                                            (-6.2, y0 - 1.1, 2.595)], toward=(0, 0, -1))
    kit.p("Walk", "concrete").box((x0, y0 - 2.0, 0.0), (x1, y0, 0.02), skip="b")
    kit.p("DTCanopy", "trim_black").box((x1, -3.4, 2.9), (x1 + 2.2, -0.4, 3.1))
    kit.p("DTCanopy", "glow_white").face([(x1 + 0.2, -3.2, 2.895), (x1 + 2.0, -3.2, 2.895), (x1 + 2.0, -0.6, 2.895),
                                          (x1 + 0.2, -0.6, 2.895)], toward=(0, 0, -1))
    kit.p("DTCanopy", "trim_black").beam((x1, -1.9, 3.8), (x1 + 2.1, -1.9, 3.1), 0.04, 0.04)
    kit.p("DTShelf", "metal_galv").box((x1, dt_win[0], 0.95), (x1 + 0.4, dt_win[1], 1.0))
    tc.hvac(kit, 2.5, 2.5, z=Hh, w=1.4, d=1.1, h=0.9)
    kit.p("Exhaust", "metal_galv").cyl((5.5, 4.0), 0.35, Hh, Hh + 1.1, sides=8)
    kit.p("Exhaust", "metal_galv").cyl((5.5, 4.0), 0.5, Hh + 1.1, Hh + 1.3, sides=8, r1=0.1)
    D = kit.p("Dumpster", "trim_green")
    D.box((1.0, y1 - 1.6, 0.15), (3.0, y1 - 0.2, 1.3)) if False else None

    # ================================================================ dining room
    pass_op = (-2.2, 2.2, 1.15, 2.4)
    k_in = (3.4, 4.4, 0.0, 2.2)
    kit.sub = 0.7
    tc.room(kit, xi0, XP - T / 2, yi0, yi1, 0.0, C, walls="plaster", floor="checker", ceiling="paint_white", name="Dining",
            wainscot="cedar", wainscot_h=1.0, base="trim_black",
            openings={"S": [door] + win_s, "W": win_w, "E": [pass_op, k_in]})
    tc.room(kit, XP + T / 2, xi1, yi0, yi1, 0.0, C, walls="block", floor="tile_floor", ceiling="paint_white", name="Kitchen",
            base="trim_black", openings={"W": [pass_op, k_in], "E": [dt_win], "N": [k_door]})
    kit.sub = None
    tc.reveals(kit.p("Reveals", "trim_black"), "E", XP + T / 2, [pass_op, k_in], T, sill=True)
    tc.wall_collider(kit, "y", XP, y0, y1, T, C, [(3.4, 4.4)])
    # booths under the south windows, tables + chairs, a drink station
    for xc in (-7.15, -1.8):
        for s in (-1, 1):
            xb = xc + s * 0.4
            lo, hi = sorted((xb, xc + s * 0.95))
            kit.p("BoothFrames", "darkwood").box((lo, yi0, 0.0), (hi, yi0 + 1.3, 0.36), skip="b")
            kit.p("BoothSeats", "vinyl_red").box((lo, yi0, 0.36), (hi, yi0 + 1.28, 0.46))
            bl, bh = sorted((xc + s * 0.95, xc + s * 0.85))
            kit.p("BoothFrames", "darkwood").box((bl, yi0, 0.0), (bh, yi0 + 1.3, 1.1), skip="b")
            kit.collide((min(lo, bl), yi0, 0), (max(hi, bh), yi0 + 1.3, 1.1))
        tc.table(kit, xc, yi0 + 0.65, w=0.75, d=1.1, h=0.75, top="formica")
    for (tx, ty) in ((-7.0, -0.5), (-7.0, 2.5), (-4.0, -0.5), (-4.0, 2.5), (-6.2, 5.2)):
        tc.table(kit, tx, ty, w=0.75, d=0.75, h=0.75, top="formica")
        chair(kit, tx - 0.6, ty, 1)
        chair(kit, tx + 0.6, ty, -1)
    kit.p("Drinks", "trim_black").box((-1.8, yi1 - 0.7, 0.0), (0.0 - T / 2, yi1, 1.0), skip="b")
    kit.p("Drinks", "metal_galv").box((-1.6, yi1 - 0.5, 1.0), (-0.3, yi1, 1.75))
    kit.p("Drinks", "glow_cool").face([(-1.5, yi1 - 0.505, 1.4), (-0.4, yi1 - 0.505, 1.4), (-0.4, yi1 - 0.505, 1.7),
                                       (-1.5, yi1 - 0.505, 1.7)], toward=(0, -1, 0))
    kit.collide((-1.8, yi1 - 0.7, 0), (-0.1, yi1, 1.75))
    # the order counter along the partition, menu boards over the pass-through
    kit.p("Counter", "cedar").box((-1.0, -2.6, 0.0), (-0.3, 2.6, 1.0), skip="bt")
    kit.p("CounterTop", "polished").box((-1.1, -2.7, 1.0), (-0.25, 2.7, 1.05))
    kit.collide((-1.1, -2.7, 0), (-0.25, 2.7, 1.05))
    for yy in (-1.4, 1.4):
        kit.p("Registers", "metal_dark").box((-0.8, yy - 0.2, 1.05), (-0.45, yy + 0.2, 1.25))
        kit.p("Registers", "glow_cool").face([(-0.805, yy - 0.17, 1.12), (-0.805, yy + 0.17, 1.12), (-0.805, yy + 0.17, 1.23),
                                              (-0.805, yy - 0.17, 1.23)], toward=(-1, 0, 0))
    for k, kind in enumerate(("burger", "cafe", "burger")):
        a = -2.0 + k * 2.0
        tc.wbox(kit.p("MenuFrames", "trim_black"), "W", XP - T / 2, a - 0.9, a + 0.9, 2.45, 3.1, 0, 0.05, skip="back")
        kit.p("Menus", "signs", glow=True).face([(XP - T / 2 - 0.055, a + 0.85, 2.5), (XP - T / 2 - 0.055, a - 0.85, 2.5),
                                                 (XP - T / 2 - 0.055, a - 0.85, 3.05), (XP - T / 2 - 0.055, a + 0.85, 3.05)],
                                                uvs=tc.sign_uv(kind), toward=(-1, 0, 0))
    # ================================================================ kitchen
    S = kit.p("Steel", "metal_galv")
    S.box((XP + 0.4, -2.2, 0.0), (XP + 1.1, 2.2, 0.95), skip="b")               # the pass shelf / heat lamps
    kit.p("HeatLamps", "lamp").box((XP + 0.5, -2.0, 2.0), (XP + 1.0, 2.0, 2.05))
    kit.collide((XP + 0.4, -2.2, 0), (XP + 1.1, 2.2, 0.95))
    for (ax0, ax1) in ((1.6, 3.0), (3.2, 4.6), (4.8, 6.2)):                    # grills and fryers on the north wall
        S.box((ax0, yi1 - 0.9, 0.0), (ax1, yi1, 0.92), skip="b")
        kit.p("Griddles", "metal_dark").box((ax0 + 0.05, yi1 - 0.85, 0.92), (ax1 - 0.05, yi1 - 0.05, 0.95))
    kit.collide((1.6, yi1 - 0.9, 0), (6.2, yi1, 0.95))
    S.box((1.4, yi1 - 1.2, 2.1), (6.4, yi1, 2.7))                               # the hood
    S.box((3.0, -2.0, 0.0), (6.5, -0.8, 0.9), skip="b")                         # prep table
    kit.collide((3.0, -2.0, 0), (6.5, -0.8, 0.9))
    S.box((xi1 - 0.6, 0.3, 0.0), (xi1, 2.8, 2.2), skip="b")                     # walk-in cooler face
    kit.p("CoolerHandle", "chrome").box((xi1 - 0.62, 2.3, 0.9), (xi1 - 0.6, 2.4, 1.3))
    kit.collide((xi1 - 0.6, 0.3, 0), (xi1, 2.8, 2.2))
    for i in range(2):
        for j in range(2):
            lx, ly = -5.5 + i * 3.5, -2.2 + j * 4.4
            kit.p("CeilingPanels", "glow_white").face([(lx - 0.9, ly - 0.25, C - 0.01), (lx + 0.9, ly - 0.25, C - 0.01),
                                                      (lx + 0.9, ly + 0.25, C - 0.01), (lx - 0.9, ly + 0.25, C - 0.01)],
                                                     toward=(0, 0, -1))
            kit.light((lx, ly, C - 0.05), (1.0, 0.9, 0.75), 40, 1.0, kind="AREA")
    for (lx, ly) in ((2.5, -2.0), (5.5, -2.0), (4.0, 2.2)):
        kit.p("CeilingPanels", "glow_white").face([(lx - 0.9, ly - 0.25, C - 0.01), (lx + 0.9, ly - 0.25, C - 0.01),
                                                  (lx + 0.9, ly + 0.25, C - 0.01), (lx - 0.9, ly + 0.25, C - 0.01)], toward=(0, 0, -1))
        kit.light((lx, ly, C - 0.05), (0.9, 0.95, 1.0), 45, 1.0, kind="AREA")
    kit.light((-0.6, 0.0, 2.8), (1.0, 0.8, 0.6), 25, 1.5, kind="AREA", direction=(-1, 0, -0.3))   # the menu boards

    far = tc.Far(n)
    far.box((x0, y0, 0), (x1, y1, Hh + 0.6), "bb_charcoal", top="tar")
    far.box((x0, y0, 0), (x1, y1, 0.9), "ledgestone", skip="bt")
    far.box((x0 - 0.55, y0 - 0.55, Hh - 0.6), (x1 + 0.55, y1 + 0.55, Hh + 1.6), "trim_red", top="tar", skip="")
    for a0, a1, z0, z1 in win_s:
        far.quad("S", y0, a0, a1, z0, z1, "window_lit", d=0.02)

    kit.entrance((-4.5, y0 - 0.1, 0.0), "-Y", 1.2, kind="door", note="TownFastFood_Door_1, under the entry canopy")
    kit.entrance((6.0, y1 + 0.1, 0.0), "+Y", 1.0, kind="door", note="TownFastFood_Door_2, kitchen back door")
    kit.info.update(walk_in=True, storeys=1, rooms=["dining 7.7 x 10.6", "kitchen 7.6 x 10.6"],
                    footprint=[round(x0 - 0.55, 3), round(y0 - 2.0, 3), round(x1 + 2.2, 3), round(y1 + 0.55, 3)],
                    lane=f"drive-through window on +X at x {x1}, y -2.6..-1.2 (sill 1.0); menu board / speaker / clearance bar: town_menu_board")
    parts = tc.finish(kit, col, root, far)
    if p["bake"]:
        meshes = [o for o in root.children_recursive if o.type == "MESH" and not o.name.endswith("_LOD1")]
        town_light.bake(kit, root, meshes, [(xi0, yi0, 0.0, XP - T / 2, yi1, C), (XP + T / 2, yi0, 0.0, xi1, yi1, C)])
    return root, parts
