"""The sheriff's office: a 1990s public building of red brick on a ledgestone base, a flat roof
behind a parapet with a metal coping, a stone entry portico, a big front window (the office
desk with its phone faces it: it looks across the bridge), a star-badge pictogram on a stone
monument sign, a flagpole with a flag, and a sally port for the cruiser (an overhead door at
the back).

Walk-in: the lobby with its counter, the front office (two desks, the window desk with the
phone, filing cabinets, a gun cabinet, a bulletin board of blank sheets), the corridor to
two holding cells with barred fronts (bunks, steel toilets), its light baked into COLOR_0.

Origin: floor centre at the door sill; front -Y. Doors: TownSheriff_Door_1 (front),
_2 (back, from the corridor).
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

NAME = "TownSheriff"
P = dict(name=NAME, module="town_sheriff", x0=-9.0, x1=9.0, y0=-7.0, y1=7.0, height=4.6, ceiling=3.0, bay_x=3.6, bake=True)


def bars(kit, x0, x1, y, z1, gap=(None, None)):
    """A barred cell front along x at y (flat bars, cross bands), gap = a door's x range."""
    B = kit.p("Bars", "metal_dark")
    k = int((x1 - x0) / 0.13)
    for i in range(k + 1):
        x = x0 + (x1 - x0) * i / k
        B.box((x - 0.012, y - 0.012, 0.0), (x + 0.012, y + 0.012, z1), skip="tb")
    for z in (0.08, 1.1, z1 - 0.08):
        B.box((x0, y - 0.03, z - 0.03), (x1, y + 0.03, z + 0.03))
    kit.collide((x0, y - 0.05, 0), (x1, y + 0.05, z1))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    x0, x1, y0, y1, T, Hh, C = p["x0"], p["x1"], p["y0"], p["y1"], 0.25, p["height"], p["ceiling"]
    xi0, xi1, yi0, yi1 = x0 + T, x1 - T, y0 + T, y1 - T
    BX = p["bay_x"]

    # ---------------------------------------------------------------- shell
    door = (-5.6, -4.4, 0.0, 2.4)
    big = (-2.4, 2.6, 0.9, 2.6)
    win_s = [(-8.2, -6.8, 1.1, 2.5), big, (4.6, 5.8, 1.1, 2.5), (6.8, 8.0, 1.1, 2.5)]
    cells_w = [(-7.6, -7.0, 2.2, 2.6), (-4.4, -3.8, 2.2, 2.6)]       # small high cell windows (N)
    back_door = (-1.0, 0.0, 0.0, 2.2)
    bay_door = (BX + 0.6, x1 - 0.6, 0.0, 3.0)
    openings = {"S": [door] + win_s, "N": cells_w + [back_door, bay_door], "W": [(-2.0, -0.8, 1.1, 2.5)], "E": [(-3.0, -1.6, 1.1, 2.5)]}
    tc.shell(kit, x0, x1, y0, y1, Hh, openings, "brick_red", base="ledgestone", base_h=0.8, thick=T,
             reveal_part=kit.p("Reveals", "stone"))
    kit.tints["Walls"] = (0.9, 0.84, 0.8)
    tc.flat_roof(kit, x0, x1, y0, y1, Hh, parapet=0.6, wall="brick_red", coping="metal_galv")
    tc.band(kit, x0, x1, y0, y1, Hh - 0.35, Hh - 0.15, proud=0.03, mat="stone")
    for side, plane, ops in (("S", y0, [w for w in win_s if w != big]), ("W", x0, [(-2.0, -0.8, 1.1, 2.5)]),
                             ("E", x1, [(-3.0, -1.6, 1.1, 2.5)])):
        for a0, a1, z0, z1 in ops:
            tc.window(kit, side, plane, (a0 + a1) / 2, z0, a1 - a0, z1 - z0, cell="bk_blinds", trim="metal_galv", casing=0.0,
                      depth=0.12)
            tc.wbox(kit.p("Lintels", "stone"), side, plane, a0 - 0.1, a1 + 0.1, z1, z1 + 0.25, 0, 0.04, skip="back")
    tc.glazing(kit, "S", y0, big[0], big[1], big[2], big[3], cell="bk_office", mullions=[0.1], depth=0.12, frame="metal_galv")
    tc.wbox(kit.p("Lintels", "stone"), "S", y0, big[0] - 0.15, big[1] + 0.15, big[3], big[3] + 0.3, 0, 0.05, skip="back")
    for a0, a1, z0, z1 in cells_w:
        tc.window(kit, "N", y1, (a0 + a1) / 2, z0, a1 - a0, z1 - z0, cell="bk_dark", trim="metal_dark", casing=0.0, depth=0.12)
        for k in range(4):
            a = a0 + (a1 - a0) * (k + 0.5) / 4
            tc.wbox(kit.p("Bars", "metal_dark"), "N", y1, a - 0.012, a + 0.012, z0, z1, -0.05, -0.03)
    tc.hinged_door(kit, col, root, "S", y0, -5.0, 1.2, 2.4, depth=0.12, leaf="metal_galv", index=1, style="glass", glass="bk_office")
    tc.hinged_door(kit, col, root, "N", y1, -0.5, 1.0, 2.2, depth=0.12, leaf="metal_galv", index=2)
    # the sally port's overhead door (closed), the bay is a solid volume behind the office
    a0, a1, z0, z1 = bay_door
    tc.wbox(kit.p("BayDoor", "metal_galv"), "N", y1, a0, a1, z0, z1, -0.12, -0.05)
    for k in range(8):
        tc.wbox(kit.p("BayDoor", "metal_dark"), "N", y1, a0, a1, z0 + k * 0.375, z0 + k * 0.375 + 0.02, -0.05, -0.04)
    kit.p("BayFill", "shade").box((BX, -1.0, 0.0), (xi1, yi1 - 0.13, C), skip="b")
    kit.collide((BX - 0.1, -1.0, 0), (x1, y1, Hh))
    # the portico: two stone columns, a flat stone roof, the star sign over the door
    for x in (-6.4, -3.6):
        kit.p("Portico", "ledgestone").box((x - 0.3, y0 - 2.0, 0.0), (x + 0.3, y0 - 1.4, 3.0), skip="b")
        kit.collide((x - 0.3, y0 - 2.0, 0), (x + 0.3, y0 - 1.4, 3.0))
    kit.p("PorticoRoof", "stone").box((-7.0, y0 - 2.2, 3.0), (-3.0, y0, 3.35))
    kit.p("PorticoRoof", "glow_white").face([(-5.6, y0 - 1.2, 2.995), (-4.4, y0 - 1.2, 2.995), (-4.4, y0 - 0.8, 2.995),
                                             (-5.6, y0 - 0.8, 2.995)], toward=(0, 0, -1))
    tc.sign(kit, "S", y0 - 2.2, -5.0, 3.05, 0.6, 0.3, "sheriff", d=0.0, frame="stone", thick=0.01) if False else None
    kit.p("Walk", "concrete").box((-7.2, y0 - 2.4, 0.0), (-2.8, y0, 0.02), skip="b")
    # the monument sign and the flagpole out front
    kit.p("Monument", "ledgestone").box((2.0, y0 - 4.0, 0.0), (5.0, y0 - 3.4, 1.4), skip="b")
    kit.p("Monument", "stone").box((1.9, y0 - 4.05, 1.4), (5.1, y0 - 3.35, 1.5))
    kit.p("MonumentSign", "signs").face([(2.3, y0 - 4.005, 0.45), (4.7, y0 - 4.005, 0.45), (4.7, y0 - 4.005, 1.25),
                                         (2.3, y0 - 4.005, 1.25)], uvs=tc.sign_uv("sheriff"), toward=(0, -1, 0))
    kit.collide((2.0, y0 - 4.0, 0), (5.0, y0 - 3.4, 1.5))
    fx, fy = 7.5, y0 - 3.5
    kit.p("Flagpole", "chrome").cyl((fx, fy), 0.07, 0.0, 9.0, sides=6, caps="", r1=0.04)
    kit.p("Flagpole", "brass").cyl((fx, fy), 0.08, 9.0, 9.15, sides=6)
    kit.p("Flagpole", "concrete").cyl((fx, fy), 0.4, 0.0, 0.15, sides=8)
    kit.collide((fx - 0.1, fy - 0.1, 0), (fx + 0.1, fy + 0.1, 9.0))
    for k in range(7):                                          # the flag: stripes and a canton, two-sided
        z = 8.9 - k * 0.12
        colr = "paint_red" if k % 2 == 0 else "paint_white"
        q = [(fx + 0.08, fy, z - 0.12), (fx + 1.6, fy + 0.05 * math.sin(k), z - 0.12), (fx + 1.6, fy + 0.05 * math.sin(k), z),
             (fx + 0.08, fy, z)]
        kit.p("Flag", colr).face(q, toward=(0, -1, 0))
        kit.p("Flag", colr).face(q, toward=(0, 1, 0))
    q = [(fx + 0.08, fy - 0.005, 8.42), (fx + 0.75, fy - 0.005, 8.42), (fx + 0.75, fy - 0.005, 8.9), (fx + 0.08, fy - 0.005, 8.9)]
    kit.p("Flag", "paint_blue").face(q, toward=(0, -1, 0))
    kit.p("Flag", "paint_blue").face([(x, fy + 0.01, z) for x, _, z in q], toward=(0, 1, 0))
    tc.hvac(kit, -4.0, 3.0, z=Hh, w=1.4, d=1.1, h=0.9)
    tc.meter(kit, "E", x1, 2.0)

    # ---------------------------------------------------------------- inside: lobby, office, corridor, cells
    kit.sub = 0.8
    lob_y1 = -0.2                                   # the front rooms run to here; the corridor behind
    tc.room(kit, xi0, BX - 0.1, yi0, lob_y1, 0.0, C, walls="plaster", floor="tile_floor", ceiling="paint_white", name="Office",
            wainscot="darkwood", wainscot_h=1.0, base="trim_black",
            openings={"S": [door, big, win_s[0]], "W": [(-2.0, -0.8, 1.1, 2.5)], "N": [(-8.2, -7.2, 0.0, 2.2), (-1.5, -0.5, 0.0, 2.2)]})
    tc.room(kit, xi0, BX - 0.1, lob_y1 + 0.2, 1.8, 0.0, C, walls="block", floor="concrete", ceiling="paint_white", name="Corridor",
            base="trim_black", openings={"S": [(-8.2, -7.2, 0.0, 2.2), (-1.5, -0.5, 0.0, 2.2)], "N": [(-8.6, -2.2, 0.0, C)]})
    tc.room(kit, xi0, BX - 0.1, 1.8, yi1, 0.0, C, walls="block", floor="concrete", ceiling="paint_white", name="Cells",
            base="trim_black", sides="NEW", openings={"N": cells_w + [back_door]})
    kit.sub = None
    tc.wall_collider(kit, "x", lob_y1 + 0.1, x0, BX, 0.2, C, [(-8.2, -7.2), (-1.5, -0.5)])
    tc.wall_collider(kit, "y", BX, y0, y1, 0.2, C)
    tc.reveals(kit.p("Reveals", "stone"), "N", lob_y1 + 0.2, [(-8.2, -7.2, 0.0, 2.2), (-1.5, -0.5, 0.0, 2.2)], 0.2, sill=False)
    # the lobby counter (a waist-high wall with a top and a gate), the office desks
    kit.p("Counter", "darkwood").box((xi0, -4.0, 0.0), (-3.4, -3.6, 1.05), skip="b")
    kit.p("Counter", "polished").box((xi0, -4.05, 1.05), (-3.4, -3.55, 1.1))
    kit.collide((xi0, -4.05, 0), (-3.4, -3.55, 1.1))
    kit.p("Counter", "darkwood").box((-3.4, -4.0, 0.0), (-3.35, -3.6, 1.05))
    tc.table(kit, 0.1, y0 + 1.4, w=1.8, d=0.8, h=0.76, top="varnish", base="darkwood")       # the window desk
    kit.p("Phone", "metal_dark").box((0.6, y0 + 1.25, 0.76), (0.85, y0 + 1.45, 0.84))
    kit.p("Phone", "metal_dark").box((0.58, y0 + 1.3, 0.84), (0.87, y0 + 1.38, 0.88))
    kit.p("DeskChair", "vinyl_black").box((-0.15, y0 + 2.1, 0.45), (0.35, y0 + 2.6, 0.52))
    kit.p("DeskChair", "vinyl_black").box((-0.15, y0 + 2.55, 0.52), (0.35, y0 + 2.62, 1.1))
    kit.p("DeskChair", "metal_dark").cyl((0.1, y0 + 2.35), 0.25, 0.0, 0.05, sides=5)
    kit.p("DeskChair", "metal_dark").cyl((0.1, y0 + 2.35), 0.03, 0.05, 0.45, sides=4, caps="")
    kit.info["window_desk"] = {"desk": [0.1, round(y0 + 1.4, 3), 0.76], "phone": [0.72, round(y0 + 1.35, 3), 0.84], "faces": "-Y (the window)"}
    tc.table(kit, -1.2, -2.0, w=1.6, d=0.8, h=0.76, top="varnish", base="darkwood")
    kit.p("Monitors", "metal_dark").box((-1.5, -1.8, 0.76), (-0.9, -1.75, 1.15))
    kit.p("Monitors", "glow_cool").face([(-1.47, -1.805, 0.8), (-0.93, -1.805, 0.8), (-0.93, -1.805, 1.12), (-1.47, -1.805, 1.12)],
                                        toward=(0, -1, 0))
    for fy_ in (-3.2, -2.6):
        kit.p("Files", "metal_galv").box((BX - 0.7, fy_, 0.0), (BX - 0.1, fy_ + 0.55, 1.35), skip="b")
    kit.collide((BX - 0.7, -3.2, 0), (BX - 0.1, -2.05, 1.35))
    kit.p("GunCabinet", "darkwood").box((BX - 0.55, -1.6, 0.0), (BX - 0.1, -0.5, 1.9), skip="b")
    tc.wquad(kit.p("GunCabinet", "windows"), "W", BX - 0.55, -1.5, -0.6, 0.3, 1.8, 0.0, uvs=tc.cell_uv(tc.WIN["bk_dark"], sub=(0.06, 0.06, 0.94, 0.94)))
    for k in range(4):
        kit.p("Guns", "metal_dark").box((BX - 0.45, -1.45 + k * 0.22, 0.5), (BX - 0.4, -1.42 + k * 0.22, 1.6))
    kit.collide((BX - 0.55, -1.6, 0), (BX - 0.1, -0.5, 1.9))
    kit.p("Bulletin", "deck").box((-8.6, lob_y1 - 0.02, 1.2), (-5.2, lob_y1, 2.2))
    for k in range(8):
        bx = -8.4 + (k % 4) * 0.8
        bz = 1.35 + (k // 4) * 0.42
        kit.p("Bulletin", "paper").box((bx, lob_y1 - 0.03, bz), (bx + 0.5, lob_y1 - 0.02, bz + 0.35))
    for (lx, ly) in ((-6.0, -4.5), (0.0, -4.5), (-6.0, -1.6), (0.0, -1.8), (-3.0, 0.8), (-5.0, 4.2)):
        kit.p("CeilingPanels", "glow_white").face([(lx - 0.6, ly - 0.3, C - 0.01), (lx + 0.6, ly - 0.3, C - 0.01),
                                                  (lx + 0.6, ly + 0.3, C - 0.01), (lx - 0.6, ly + 0.3, C - 0.01)], toward=(0, 0, -1))
        kit.light((lx, ly, C - 0.05), (0.9, 0.93, 1.0), 28, 1.0, kind="AREA")
    # the cells: barred fronts along y = 1.8 (each with its barred door), bunks, toilets; a blank back office
    for cx0, cx1 in ((-8.75, -5.6), (-5.4, -2.25)):
        bars(kit, cx0, cx1, 1.85, C - 0.05)
        kit.p("Bunks", "metal_galv").box((cx0 + 0.1, yi1 - 0.85, 0.4), (cx0 + 2.0, yi1 - 0.05, 0.46))
        kit.p("Bunks", "fabric_blue").box((cx0 + 0.15, yi1 - 0.8, 0.46), (cx0 + 1.95, yi1 - 0.1, 0.52))
        for x in (cx0 + 0.15, cx0 + 1.95):
            kit.p("Bunks", "metal_galv").box((x - 0.03, yi1 - 0.85, 0.0), (x + 0.03, yi1 - 0.8, 0.4))
        kit.collide((cx0 + 0.1, yi1 - 0.85, 0), (cx0 + 2.0, yi1 - 0.05, 0.52))
        kit.p("Toilets", "metal_galv").box((cx1 - 0.6, yi1 - 0.65, 0.0), (cx1 - 0.15, yi1 - 0.05, 0.45))
        kit.p("Toilets", "metal_galv").box((cx1 - 0.6, yi1 - 0.2, 0.45), (cx1 - 0.15, yi1 - 0.05, 0.95))
        kit.collide((cx1 - 0.6, yi1 - 0.65, 0), (cx1 - 0.15, yi1 - 0.05, 0.95))
    kit.p("CellWall", "block").box((-5.6, 1.85, 0.0), (-5.4, yi1, C), skip="tb")
    kit.collide((-5.6, 1.8, 0), (-5.4, yi1, C))
    tc.wall_collider(kit, "x", 1.8, -2.25, BX, 0.2, C)
    kit.p("CellLight", "glow_white").face([(-7.6, 4.0, C - 0.01), (-6.6, 4.0, C - 0.01), (-6.6, 4.3, C - 0.01), (-7.6, 4.3, C - 0.01)],
                                          toward=(0, 0, -1))
    kit.p("CellLight", "glow_white").face([(-4.3, 4.0, C - 0.01), (-3.3, 4.0, C - 0.01), (-3.3, 4.3, C - 0.01), (-4.3, 4.3, C - 0.01)],
                                          toward=(0, 0, -1))
    kit.light((-7.1, 4.15, C - 0.05), (0.85, 0.9, 1.0), 14, 0.6, kind="AREA")
    kit.light((-3.8, 4.15, C - 0.05), (0.85, 0.9, 1.0), 14, 0.6, kind="AREA")
    kit.p("CellsBack", "block").face([(-2.25, 1.85, 0.0), (BX - 0.1, 1.85, 0.0), (BX - 0.1, 1.85, C), (-2.25, 1.85, C)], toward=(0, -1, 0))
    tc.door(kit, "S", 1.85, 0.8, 0.9, 2.1, leaf="metal_galv", trim="trim_black", casing=0.05, depth=0.03)

    far = tc.Far(n)
    far.box((x0, y0, 0), (x1, y1, Hh + 0.6), "brick_red", top="tar")
    far.box((x0, y0, 0), (x1, y1, 0.8), "ledgestone", skip="bt")
    far.quad("S", y0, big[0], big[1], big[2], big[3], "window_lit")
    far.box((-7.0, y0 - 2.2, 3.0), (-3.0, y0, 3.35), "stone", skip="b")
    far.box((fx - 0.06, fy - 0.06, 0), (fx + 0.06, fy + 0.06, 9.0), "chrome", skip="b")
    kit.entrance((-5.0, y0 - 2.5, 0.0), "-Y", 1.2, kind="door", note="TownSheriff_Door_1, under the portico")
    kit.entrance((-0.5, y1 + 0.1, 0.0), "+Y", 1.0, kind="door", note="TownSheriff_Door_2, back, from the cell corridor")
    kit.entrance(((bay_door[0] + bay_door[1]) / 2, y1 + 0.1, 0.0), "+Y", round(bay_door[1] - bay_door[0], 2), kind="garage",
                 note="sally port overhead door, closed")
    kit.info.update(walk_in=True, storeys=1, rooms=["lobby + front office 12.4 x 6.5 (counter, window desk with phone, gun cabinet)",
                                                    "corridor", "two holding cells 3.1 x 4.9 (barred fronts, bunks)"],
                    footprint=[x0, round(y0 - 4.1, 3), x1, y1])
    parts = tc.finish(kit, col, root, far)
    if p["bake"]:
        meshes = [o for o in root.children_recursive if o.type == "MESH" and not o.name.endswith("_LOD1")]
        town_light.bake(kit, root, meshes, [(xi0, yi0, 0.0, BX - 0.1, lob_y1, C), (xi0, lob_y1 + 0.2, 0.0, BX - 0.1, 1.8, C),
                                            (xi0, 1.8, 0.0, BX - 0.1, yi1, C)])
    return root, parts
