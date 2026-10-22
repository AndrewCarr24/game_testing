"""Fast-food drive-through (generic, no brand): a low flat-roofed box in the town's mountain
dress (ledgestone base, charcoal board-and-batten, cedar panels) with a brick entry tower
carrying a lit burger pictogram; a drive-through window on the east side under a black
canopy, a lit menu board, a speaker post and a clearance bar on the lane.

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
P = dict(name=NAME, module="town_fastfood", x0=-8.0, x1=8.0, y0=-5.5, y1=5.5, thick=0.2, height=4.2, ceiling=3.2,
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
    win_s = [(-2.2, -0.6, 0.9, 2.6)]
    win_w = [(-4.6, -1.6, 0.9, 2.6), (1.6, 4.6, 0.9, 2.6)]
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
    # the entry tower: brick, a black cap, the burger pictogram lit high up
    tx0, tx1, ty0, ty1 = -6.6, -2.4, y0 - 0.5, y0 + 1.5
    tc.wall(kit.p("Tower", "brick_red"), "S", ty0, tx0, tx1, 0.0, 6.8, [(-5.1, -3.9, 0.0, 2.3)])
    for side, plane, a0, a1 in (("E", tx1, ty0, y0), ("W", tx0, ty0, y0)):
        tc.wall(kit.p("Tower", "brick_red"), side, plane, a0, a1, 0.0, 6.8)
    for side, plane, a0, a1 in (("E", tx1, y0, ty1), ("W", tx0, y0, ty1), ("N", ty1, tx0, tx1)):
        tc.wall(kit.p("Tower", "brick_red"), side, plane, a0, a1, Hh + 0.6, 6.8)
    tc.reveals(kit.p("Reveals", "trim_black"), "S", ty0, [(-5.1, -3.9, 0.0, 2.3)], 0.5, sill=False)
    kit.p("TowerCap", "trim_black").box((tx0 - 0.1, ty0 - 0.1, 6.8), (tx1 + 0.1, ty1 + 0.1, 7.0))
    kit.p("TowerCap", "trim_black").face([(tx0, ty0, 6.8), (tx1, ty0, 6.8), (tx1, ty1, 6.8), (tx0, ty1, 6.8)], toward=(0, 0, -1))
    tc.sign(kit, "S", ty0, (tx0 + tx1) / 2, 4.4, 3.0, 1.5, "burger", glow=True)
    kit.collide((tx0, ty0, 0), (-5.1, y0, 6.8))
    kit.collide((-3.9, ty0, 0), (tx1, y0, 6.8))
    kit.p("Awning", "trim_black").box((tx0 - 0.2, ty0 - 1.2, 2.6), (tx1 + 0.2, ty0, 2.75))
    kit.p("AwningGlow", "glow_white").face([(tx0, ty0 - 1.0, 2.595), (tx1, ty0 - 1.0, 2.595), (tx1, ty0 - 0.9, 2.595),
                                            (tx0, ty0 - 0.9, 2.595)], toward=(0, 0, -1))
    kit.p("Walk", "concrete").box((x0 - 1.0, y0 - 2.5, 0.0), (x1, y0, 0.02), skip="b")
    # the drive-through: a canopy over the window, a menu board, speaker post, clearance bar
    kit.p("DTCanopy", "trim_black").box((x1, -3.4, 2.9), (x1 + 2.2, -0.4, 3.1))
    kit.p("DTCanopy", "glow_white").face([(x1 + 0.2, -3.2, 2.895), (x1 + 2.0, -3.2, 2.895), (x1 + 2.0, -0.6, 2.895),
                                          (x1 + 0.2, -0.6, 2.895)], toward=(0, 0, -1))
    kit.p("DTCanopy", "trim_black").beam((x1, -1.9, 3.8), (x1 + 2.1, -1.9, 3.1), 0.04, 0.04)
    kit.p("DTShelf", "metal_galv").box((x1, dt_win[0], 0.95), (x1 + 0.4, dt_win[1], 1.0))
    mbx, mby = x1 + 3.6, 3.5
    M = kit.p("MenuBoard", "trim_black")
    M.box((mbx, mby - 1.3, 0.6), (mbx + 0.25, mby + 1.3, 2.6))
    for k, kind in enumerate(("burger", "cafe")):
        a = mby - 0.6 + k * 1.2
        kit.p("MenuGlow", "signs", glow=True).face([(mbx - 0.005, a + 0.55, 1.2), (mbx - 0.005, a - 0.55, 1.2),
                                                    (mbx - 0.005, a - 0.55, 1.75), (mbx - 0.005, a + 0.55, 1.75)],
                                                   uvs=tc.sign_uv(kind), toward=(-1, 0, 0))
        kit.p("MenuGlow", "glow_white").face([(mbx - 0.005, a + 0.55, 0.75), (mbx - 0.005, a - 0.55, 0.75),
                                              (mbx - 0.005, a - 0.55, 1.15), (mbx - 0.005, a + 0.55, 1.15)], toward=(-1, 0, 0))
    M.box((mbx + 0.05, mby - 0.1, 0.0), (mbx + 0.2, mby + 0.1, 0.6), skip="b")
    kit.p("MenuBoard", "ledgestone").box((mbx - 0.1, mby - 1.4, 0.0), (mbx + 0.35, mby + 1.4, 0.6), skip="b")
    kit.collide((mbx - 0.1, mby - 1.4, 0), (mbx + 0.35, mby + 1.4, 2.6))
    sp = kit.p("Speaker", "trim_black")
    sp.box((mbx - 0.05, 1.4, 0.0), (mbx + 0.25, 1.75, 1.45), skip="b")
    kit.p("Speaker", "neon_amber").box((mbx - 0.06, 1.5, 1.2), (mbx - 0.05, 1.65, 1.3))
    kit.collide((mbx - 0.05, 1.4, 0), (mbx + 0.25, 1.75, 1.45))
    G = kit.p("Clearance", "paint_yellow")
    for gx in (x1 + 0.4, x1 + 4.4):
        G.box((gx - 0.08, 7.9, 0.0), (gx + 0.08, 8.1, 3.1), skip="b")
        kit.collide((gx - 0.08, 7.9, 0), (gx + 0.08, 8.1, 3.1))
    G.box((x1 + 0.4, 7.92, 2.8), (x1 + 4.4, 8.08, 2.95))
    kit.p("Clearance", "trim_black").box((x1 + 1.6, 7.91, 2.8), (x1 + 2.0, 8.09, 2.95))
    kit.p("Clearance", "trim_black").box((x1 + 2.8, 7.91, 2.8), (x1 + 3.2, 8.09, 2.95))
    tc.hvac(kit, 2.5, 2.5, z=Hh, w=1.4, d=1.1, h=0.9)
    kit.p("Exhaust", "metal_galv").cyl((5.5, 4.0), 0.35, Hh, Hh + 1.1, sides=8)
    kit.p("Exhaust", "metal_galv").cyl((5.5, 4.0), 0.5, Hh + 1.1, Hh + 1.3, sides=8, r1=0.1)
    D = kit.p("Dumpster", "trim_green")
    D.box((1.0, y1 + 0.8, 0.15), (3.0, y1 + 2.2, 1.3))
    kit.p("Dumpster", "rubber").box((0.95, y1 + 0.75, 1.3), (3.05, y1 + 2.25, 1.38))
    kit.collide((1.0, y1 + 0.8, 0), (3.0, y1 + 2.2, 1.38))

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
    for xc in (-6.5, -1.4):
        for s in (-1, 1):
            xb = xc + s * 0.4
            lo, hi = sorted((xb, xc + s * 0.95))
            kit.p("BoothFrames", "darkwood").box((lo, yi0, 0.0), (hi, yi0 + 1.3, 0.36), skip="b")
            kit.p("BoothSeats", "vinyl_red").box((lo, yi0, 0.36), (hi, yi0 + 1.28, 0.46))
            bl, bh = sorted((xc + s * 0.95, xc + s * 0.85))
            kit.p("BoothFrames", "darkwood").box((bl, yi0, 0.0), (bh, yi0 + 1.3, 1.1), skip="b")
            kit.collide((min(lo, bl), yi0, 0), (max(hi, bh), yi0 + 1.3, 1.1))
        tc.table(kit, xc, yi0 + 0.65, w=0.75, d=1.1, h=0.75, top="formica")
    for (tx, ty) in ((-6.0, 0.5), (-6.0, 3.0), (-3.2, 0.5), (-3.2, 3.0)):
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
    far.box((tx0, ty0, 0), (tx1, ty1, 7.0), "brick_red", top="trim_black")
    far.quad("S", ty0, tx0 + 0.6, tx1 - 0.6, 4.4, 5.9, "paint_orange", d=0.05)
    for a0, a1, z0, z1 in win_s:
        far.quad("S", y0, a0, a1, z0, z1, "window_lit", d=0.02)
    far.box((mbx, mby - 1.3, 0.0), (mbx + 0.25, mby + 1.3, 2.6), "trim_black", skip="b")

    kit.entrance((-4.5, ty0 - 0.1, 0.0), "-Y", 1.2, kind="door", note="TownFastFood_Door_1, in the tower")
    kit.entrance((6.0, y1 + 0.1, 0.0), "+Y", 1.0, kind="door", note="TownFastFood_Door_2, kitchen back door")
    kit.info.update(walk_in=True, storeys=1, rooms=["dining 7.7 x 10.6", "kitchen 7.6 x 10.6"],
                    footprint=[round(x0 - 1.0, 3), round(y0 - 2.5, 3), round(mbx + 0.35, 3), round(y1 + 2.3, 3)],
                    lane="drive-through lane along +X: clearance bar at y 8, menu board at x 11.6..11.95, window at x 8, y -2.6..-1.2")
    parts = tc.finish(kit, col, root, far)
    if p["bake"]:
        meshes = [o for o in root.children_recursive if o.type == "MESH" and not o.name.endswith("_LOD1")]
        town_light.bake(kit, root, meshes, [(xi0, yi0, 0.0, XP - T / 2, yi1, C), (XP + T / 2, yi0, 0.0, xi1, yi1, C)])
    return root, parts
