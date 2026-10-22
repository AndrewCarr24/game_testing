"""The white frame church: a gable-front nave in white lap siding on a fieldstone foundation,
a black standing-seam roof, tall windows with pointed heads, and the square steeple tower on
the front centre (belfry with louvres, a clock face without numerals, a white spire with a
brass cross at 21 m: the cove's backdrop shows it). Double doors up five steps.

Walk-in: the nave (pews either side of an aisle, a raised chancel with a pulpit and a
communion rail, pendant lanterns), its light baked into COLOR_0.

Origin: the nave's floor centre at the door sill (z = 0); the steps and the foundation hang
below (below_m 0.9); front (the tower, the doors) faces -Y. Door: TownChurch_Door_1.
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

NAME = "TownChurch"
P = dict(name=NAME, module="town_church", W=12.0, D=24.0, plate=6.0, pitch=1.0, tower=4.2, tower_out=2.2,
         tower_top=13.0, belfry_top=16.2, spire_top=21.0, below=0.9, ceiling=5.8, bake=True)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    W, D, H, T = p["W"], p["D"], p["plate"], 0.2
    x0, x1, y0, y1 = -W / 2, W / 2, -D / 2, D / 2
    ridge = H + W / 2 * p["pitch"]
    bz = -p["below"]
    C = p["ceiling"]
    tw = p["tower"]
    tx0, tx1, ty0, ty1 = -tw / 2, tw / 2, y0 - p["tower_out"], y0 + 0.01

    # ================================================================ the nave
    lan = [y0 + 4.0 + i * 4.4 for i in range(4)]
    win_side = [(y - 0.6, y + 0.6, 1.4, 4.4) for y in lan]
    win_front = [(x0 + 1.6, x0 + 2.6, 1.6, 4.4), (x1 - 2.6, x1 - 1.6, 1.6, 4.4)]
    win_back = [(-0.7, 0.7, 2.0, 4.6)]
    door = (-0.85, 0.85, 0.0, 2.9)
    openings = {"E": win_side, "W": [(-a1, -a0, z0, z1) for a0, a1, z0, z1 in win_side][::-1] if False else win_side,
                "S": win_front, "N": win_back}
    E = kit.p("Walls", "lap_white")
    Bp = kit.p("Base", "fieldstone")
    for side, plane, a0, a1 in (("S", y0, x0, x1), ("N", y1, x0, x1), ("E", x1, y0, y1), ("W", x0, y0, y1)):
        op = openings[side]
        tc.wall(Bp, side, plane, a0, a1, bz, 0.35)
        tc.wall(E, side, plane, a0, a1, 0.35, H, op, gable=ridge if side in "SN" else None)
        tc.reveals(kit.p("Reveals", "trim"), side, plane, op, T)
        for a0_, a1_, z0, z1 in op:
            a = (a0_ + a1_) / 2
            w = a1_ - a0_
            tc.window(kit, side, plane, a, z0, w, z1 - z0, cell="dh_lamp", trim="trim", casing=0.1, depth=0.1)
            # the pointed head: a glass gablet and its trim, over the opening
            Pf, u, nn = tc.frame(side, plane)
            hz = z1 + w * 0.75
            kit.p("Window", "windows").face([Pf(a0_, z1 + 0.14, 0.005), Pf(a1_, z1 + 0.14, 0.005), Pf(a, hz, 0.005)],
                                            uvs=tc.cell_uv(tc.WIN["dh_lamp"], sub=(0.1, 0.55, 0.9, 0.95))[:2] +
                                            [tc.cell_uv(tc.WIN["dh_lamp"], sub=(0.45, 0.9, 0.55, 0.95))[2]], toward=nn)
            Tr = kit.p("Trim", "trim")
            Tr.beam(Pf(a0_ - 0.1, z1 + 0.12, 0.03), Pf(a, hz + 0.12, 0.03), 0.06, 0.1, up=nn)
            Tr.beam(Pf(a, hz + 0.12, 0.03), Pf(a1_ + 0.1, z1 + 0.12, 0.03), 0.06, 0.1, up=nn)
    tc.corner_boards(kit, x0, x1, y0, y1, 0.35, H, mat="trim")
    tc.band(kit, x0, x1, y0, y1, H - 0.3, H, mat="trim", sides="EW")
    tc.gable_roof(kit, x0, x1, y0, y1, H, p["pitch"], axis="y", over_eave=0.45, over_gable=0.35, roof="seam_black",
                  soffit="trim", fascia="trim")
    tc.wall_collider(kit, "x", y0, x0, x1, T, H, [(-0.85, 0.85)], side_in=1)
    tc.wall_collider(kit, "x", y1, x0, x1, T, H, side_in=-1)
    tc.wall_collider(kit, "y", x1, y0, y1, T, H, side_in=-1)
    tc.wall_collider(kit, "y", x0, y0, y1, T, H, side_in=1)
    kit.collide((x0, y0, bz), (x1, y1, 0.0))

    # ================================================================ the tower and steeple
    Tw = kit.p("TowerWalls", "lap_white")
    tdoor = (-0.85, 0.85, 0.0, 2.9)
    for side, plane, a0, a1 in (("S", ty0, tx0, tx1), ("E", tx1, ty0, ty1), ("W", tx0, ty0, ty1)):
        op = [tdoor] if side == "S" else []
        tc.wall(Bp, side, plane, a0, a1, bz, 0.35, op)
        tc.wall(Tw, side, plane, a0, a1, 0.35, p["tower_top"], op + ([(-0.5, 0.5, 7.0, 8.6)] if side == "S" else []))
    for side, plane, a0, a1 in (("E", tx1, ty1, ty1 + tw - p["tower_out"]), ("W", tx0, ty1, ty1 + tw - p["tower_out"]),
                                ("N", ty0 + tw, tx0, tx1)):
        tc.wall(Tw, side, plane, a0, a1, ridge - 1.0, p["tower_top"])
    tc.window(kit, "S", ty0, 0.0, 7.0, 1.0, 1.6, cell="dh_dark", trim="trim", casing=0.1)
    tc.reveals(kit.p("Reveals", "trim"), "S", ty0, [tdoor], p["tower_out"] - 0.05, sill=False)
    tc.corner_boards(kit, tx0, tx1, ty0, ty0 + tw, 0.35, p["tower_top"], mat="trim")
    tc.band(kit, tx0, tx1, ty0, ty0 + tw, p["tower_top"] - 0.35, p["tower_top"], proud=0.06, mat="trim")
    kit.collide((tx0, ty0, bz), (-0.85, ty1, p["tower_top"]))
    kit.collide((0.85, ty0, bz), (tx1, ty1, p["tower_top"]))
    # the double doors (one hinged), a transom, the steps down to the ground
    tc.hinged_door(kit, col, root, "S", ty0, -0.425, 0.85, 2.6, depth=0.12, leaf="door_red", index=1)
    tc.door(kit, "S", ty0, 0.425, 0.85, 2.6, leaf="door_red", trim="trim", casing=0.0, depth=0.12)
    tc.glazing(kit, "S", ty0, -0.85, 0.85, 2.62, 2.9, cell="dh_lamp", frame="trim", depth=0.08)
    for a0, a1 in ((-1.05, -0.85), (0.85, 1.05)):
        tc.wbox(kit.p("Trim", "trim"), "S", ty0, a0, a1, 0.0, 3.3, 0, 0.04, skip="back")
    tc.wbox(kit.p("Trim", "trim"), "S", ty0, -0.85, 0.85, 2.9, 3.3, 0, 0.04, skip="back")
    tc.wbox(kit.p("Trim", "trim"), "S", ty0, -1.25, 1.25, 3.3, 3.5, 0, 0.12, skip="back")
    kit.p("Stoop", "concrete").box((-1.6, ty0 - 1.0, bz), (1.6, ty0, 0.0), skip="b")
    kit.collide((-1.6, ty0 - 1.0, bz), (1.6, ty0, 0.0))
    tc.steps(kit, -1.6, 1.6, ty0 - 1.0, 0.0, n=5, run=0.32, mat="concrete", z_bottom=bz)
    for x in (-1.75, 1.75):
        tc.railing(kit, (x, ty0 - 1.0), (x, ty0 - 2.6), bz + 0.0, h=0.95 - bz * 0.5, mat="trim_black", style="cable")
    # the belfry: an open stage on corner posts with louvres, a cornice, the clock face
    bt0, bt1 = p["tower_top"], p["belfry_top"]
    bw = tw - 0.6
    bx0, bx1, by0, by1 = -bw / 2, bw / 2, ty0 + 0.3, ty0 + 0.3 + bw
    Bf = kit.p("Belfry", "paint_white")
    Bf.box((bx0 - 0.2, by0 - 0.2, bt0), (bx1 + 0.2, by1 + 0.2, bt0 + 0.25))
    for (x, y) in ((bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)):
        Bf.box((x - 0.25, y - 0.25, bt0 + 0.25), (x + 0.25, y + 0.25, bt1 - 0.3), skip="bt")
    for side, plane, a0, a1 in (("S", by0, bx0, bx1), ("N", by1, bx0, bx1), ("E", bx1, by0, by1), ("W", bx0, by0, by1)):
        Pf, u, nn = tc.frame(side, plane)
        kit.p("BelfryDark", "shade").face([Pf(a0, bt0 + 0.25, -0.15), Pf(a1, bt0 + 0.25, -0.15), Pf(a1, bt1 - 0.3, -0.15),
                                          Pf(a0, bt0 + 0.25, -0.15) * 0 + Pf(a0, bt1 - 0.3, -0.15)], toward=nn)
        for k in range(9):
            z = bt0 + 0.5 + k * 0.27
            kit.p("Louvres", "paint_white").beam(Pf(a0 + 0.25, z, 0.0), Pf(a1 - 0.25, z, 0.0), 0.2, 0.03, up=nn + V(0, 0, 1.2))
    Bf.box((bx0 - 0.35, by0 - 0.35, bt1 - 0.3), (bx1 + 0.35, by1 + 0.35, bt1))
    kit.collide((bx0 - 0.35, by0 - 0.35, bt0), (bx1 + 0.35, by1 + 0.35, bt1))
    # clock faces (no numerals: twelve ticks and two hands) on the tower's front and sides
    cz = p["tower_top"] - 1.6
    for side, plane, a in (("S", ty0, 0.0), ("E", tx1, ty0 + tw / 2), ("W", tx0, ty0 + tw / 2)):
        Pf, u, nn = tc.frame(side, plane)
        ring = [Pf(a + 0.75 * math.cos(2 * math.pi * i / 16), cz + 0.75 * math.sin(2 * math.pi * i / 16), 0.05) for i in range(16)]
        kit.p("ClockFace", "paint_white").face(ring, toward=nn)
        rim = [Pf(a + 0.85 * math.cos(2 * math.pi * i / 16), cz + 0.85 * math.sin(2 * math.pi * i / 16), 0.04) for i in range(16)]
        kit.p("ClockRim", "trim_black").face(rim, toward=nn)
        H_ = kit.p("ClockHands", "trim_black")
        for k in range(12):
            ang = 2 * math.pi * k / 12
            H_.beam(Pf(a + 0.6 * math.cos(ang), cz + 0.6 * math.sin(ang), 0.06), Pf(a + 0.7 * math.cos(ang), cz + 0.7 * math.sin(ang), 0.06),
                    0.04, 0.01, up=nn)
        H_.beam(Pf(a, cz, 0.07), Pf(a + 0.45 * math.cos(1.9), cz + 0.45 * math.sin(1.9), 0.07), 0.05, 0.01, up=nn)
        H_.beam(Pf(a, cz, 0.08), Pf(a + 0.62 * math.cos(-0.3), cz + 0.62 * math.sin(-0.3), 0.08), 0.035, 0.01, up=nn)
    # the spire: octagonal, white, on a short drum; a brass cross
    sx, sy = 0.0, (by0 + by1) / 2
    Sp = kit.p("Spire", "paint_white")
    Sp.cyl((sx, sy), bw / 2 * 0.95, bt1, bt1 + 0.6, sides=8, caps="")
    Sp.cyl((sx, sy), bw / 2 * 0.95, bt1 + 0.6, p["spire_top"] - 0.9, sides=8, caps="", r1=0.08)
    Cr = kit.p("Cross", "brass")
    Cr.box((sx - 0.04, sy - 0.04, p["spire_top"] - 0.95), (sx + 0.04, sy + 0.04, p["spire_top"]))
    Cr.box((sx - 0.3, sy - 0.04, p["spire_top"] - 0.35), (sx + 0.3, sy + 0.04, p["spire_top"] - 0.27))

    # ================================================================ inside the nave
    xi0, xi1, yi0, yi1 = x0 + T, x1 - T, y0 + T, y1 - T
    kit.sub = 1.0
    tc.room(kit, xi0, xi1, yi0, yi1, 0.0, C, walls="plaster", floor="woodfloor", ceiling="paint_white", name="Nave",
            wainscot="darkwood", wainscot_h=1.0, base="trim_black",
            openings={"E": win_side, "W": win_side, "S": win_front + [door], "N": win_back})
    tc.room(kit, tx0 + T, tx1 - T, ty0 + T, y0, 0.0, 3.2, walls="plaster", floor="woodfloor", ceiling="paint_white",
            name="Vestibule", wainscot="darkwood", wainscot_h=1.0, base="trim_black", openings={"S": [tdoor], "N": [door]})
    kit.sub = None
    kit.light((0.0, (ty0 + y0) / 2, 3.0), (1.0, 0.74, 0.46), 25, 0.2)
    tc.reveals(kit.p("Reveals", "trim"), "S", y0, [door], T, sill=False)
    # pews: 10 rows each side of a 1.6 m aisle
    Pw = kit.p("Pews", "varnish")
    for r in range(10):
        y = yi0 + 3.0 + r * 1.05
        for (a0, a1) in ((xi0 + 0.4, -0.8), (0.8, xi1 - 0.4)):
            Pw.box((a0, y, 0.0), (a1, y + 0.45, 0.45), skip="b")
            Pw.box((a0, y + 0.42, 0.45), (a1, y + 0.5, 0.95), skip="b")
            Pw.box((a0, y - 0.02, 0.0), (a0 + 0.06, y + 0.55, 1.0), skip="b")
            Pw.box((a1 - 0.06, y - 0.02, 0.0), (a1, y + 0.55, 1.0), skip="b")
            kit.collide((a0, y, 0), (a1, y + 0.5, 0.95))
    # the chancel: a platform, the rail, the pulpit, a cross on the back wall
    cy0 = yi1 - 3.6
    kit.p("Chancel", "darkwood").box((xi0, cy0, 0.0), (xi1, yi1, 0.45), skip="b")
    kit.collide((xi0, cy0, 0), (xi1, yi1, 0.45))
    tc.steps(kit, -1.5, 1.5, cy0, 0.45, n=2, run=0.32, direction=-1, mat="darkwood")
    R = kit.p("ChancelRail", "varnish")
    for (a0, a1) in ((xi0 + 0.3, -1.6), (1.6, xi1 - 0.3)):
        R.box((a0, cy0 + 0.1, 0.45), (a1, cy0 + 0.2, 1.35), skip="b")
        kit.collide((a0, cy0 + 0.1, 0.45), (a1, cy0 + 0.2, 1.35))
    kit.p("Pulpit", "varnish").box((1.6, cy0 + 1.0, 0.45), (2.6, cy0 + 1.8, 1.65), skip="b")
    kit.collide((1.6, cy0 + 1.0, 0.45), (2.6, cy0 + 1.8, 1.65))
    kit.p("Table", "varnish").box((-1.0, yi1 - 1.6, 0.45), (1.0, yi1 - 0.9, 1.4), skip="b")
    kit.p("Table", "paper").box((-1.05, yi1 - 1.65, 1.4), (1.05, yi1 - 0.85, 1.42))
    kit.collide((-1.0, yi1 - 1.6, 0.45), (1.0, yi1 - 0.9, 1.4))
    Cx = kit.p("WallCross", "varnish")
    Cx.box((-0.09, yi1 - 0.08, 1.9), (0.09, yi1, 4.7))
    Cx.box((-0.8, yi1 - 0.08, 3.7), (0.8, yi1, 3.88))
    # pendant lanterns down the nave
    for y in (yi0 + 4.0, yi0 + 9.0, yi0 + 14.0, yi0 + 19.0):
        for x in (-2.8, 2.8):
            kit.p("Cords", "trim_black").tube(V(x, y, 3.9), V(x, y, C), 0.008, 3)
            kit.p("Lanterns", "trim_black").cyl((x, y), 0.25, 3.55, 3.9, sides=6, caps="t")
            kit.p("Lanterns", "lamp").cyl((x, y), 0.18, 3.2, 3.55, sides=6, caps="b")
            kit.light((x, y, 3.35), (1.0, 0.74, 0.46), 70, 0.2)
    kit.light((0.0, yi1 - 1.5, 4.8), (1.0, 0.85, 0.65), 60, 1.5, kind="AREA")

    far = tc.Far(n)
    far.gable(x0, x1, y0, y1, 0.0, H, ridge, axis="y", wall="bb_white", roof="seam_black", over=0.4)
    far.box((x0, y0, bz), (x1, y1, 0.35), "fieldstone", skip="b")
    for a0, a1, z0, z1 in win_side:
        far.quad("E", x1, a0, a1, z0, z1 + 0.6, "glass_dark")
        far.quad("W", x0, -a1, -a0, z0, z1 + 0.6, "glass_dark")
    far.box((tx0, ty0, bz), (tx1, ty0 + tw, p["tower_top"]), "bb_white", skip="b")
    far.box((bx0 - 0.3, by0 - 0.3, bt0), (bx1 + 0.3, by1 + 0.3, bt1), "paint_white", top="paint_white", skip="b")
    far.cyl((sx, sy), bw / 2 * 0.95, bt1, p["spire_top"] - 0.9, "paint_white", sides=8, cap=False, r1=0.08)
    far.box((sx - 0.05, sy - 0.05, p["spire_top"] - 0.95), (sx + 0.05, sy + 0.05, p["spire_top"]), "brass")
    far.quad("S", ty0, -0.85, 0.85, 0.0, 2.6, "door_red")

    kit.entrance((0.0, ty0 - 1.0 - 5 * 0.32, bz), "-Y", 1.7, kind="door", note="TownChurch_Door_1 (left leaf), up five steps")
    kit.info.update(walk_in=True, storeys=1, rooms=["nave 11.6 x 23.6 (20 pews, chancel, pulpit)"],
                    footprint=[round(x0 - 0.45, 3), round(ty0 - 2.7, 3), round(x1 + 0.45, 3), round(y1 + 0.35, 3)],
                    top_m=p["spire_top"])
    parts = tc.finish(kit, col, root, far)
    if p["bake"]:
        meshes = [o for o in root.children_recursive if o.type == "MESH" and not o.name.endswith("_LOD1")]
        town_light.bake(kit, root, meshes, [(xi0, yi0, 0.0, xi1, yi1, C), (tx0 + T, ty0 + T, 0.0, tx1 - T, y0, 3.2)])
    return root, parts
