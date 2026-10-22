"""The old Southern Railway combination depot, restored as the little history museum: white
board-and-batten with green trim on a fieldstone base, a green standing-seam roof with deep
eaves on big knee brackets that carry on as the platform canopy, the agent's bay window to
the track, a passenger platform at grade and a raised freight platform (1.25 m) whose
underside is open: a crawl space 1.15 m clear (a hiding place).

Walk-in: the waiting room (benches, vitrines along the walls, the ticket window into the
agent's office) and, up five steps, the freight room (sliding freight doors, an open floor
for the layout's scale-model table = town_estate_model), lit through COLOR_0.

Origin: the waiting room's floor centre at the street door's sill; front (the street) -Y;
the heritage line runs along +Y beyond the platforms. Doors: TownDepot_Door_1 (street),
_2 (to the track platform).
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

NAME = "TownDepot"
P = dict(name=NAME, module="town_depot", x0=-16.0, x1=16.0, y0=-5.0, y1=5.0, plate=4.2, pitch=0.6, eave=1.6,
         platform=4.0, freight_z=1.25, ceiling=3.6, bake=True)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    x0, x1, y0, y1, T, H = p["x0"], p["x1"], p["y0"], p["y1"], 0.2, p["plate"]
    FZ, C = p["freight_z"], p["ceiling"]
    ridge = H + (y1 - y0) / 2 * p["pitch"]
    XW, XF = -2.0, 2.0                       # waiting room | office | freight room

    # ---------------------------------------------------------------- shell
    door_s = (-9.6, -8.4, 0.0, 2.5)
    door_n = (-6.6, -5.4, 0.0, 2.5)
    fr_s = (6.0, 8.6, FZ, FZ + 2.6)          # sliding freight doors (closed)
    fr_n = (6.0, 8.6, FZ, FZ + 2.6)
    w_s = [(-14.0, -13.0, 1.0, 3.0), (-12.0, -11.0, 1.0, 3.0), (-5.0, -4.0, 1.0, 3.0), (-0.5, 0.5, 1.0, 3.0)]
    w_n = [(-14.0, -13.0, 1.0, 3.0), (-11.5, -10.5, 1.0, 3.0), (-3.0, -2.2, 1.0, 3.0)]
    bay = (-1.2, 1.2, 0.9, 3.0)              # the agent's bay (N)
    w_f = [(11.0, 12.0, FZ + 1.0, FZ + 2.4), (13.6, 14.6, FZ + 1.0, FZ + 2.4)]
    openings = {"S": [door_s, fr_s] + w_s + w_f, "N": [door_n, fr_n, bay] + w_n + w_f, "W": [(-1.2, 1.2, 1.0, 3.0)], "E": []}
    W = kit.p("Walls", "bb_white")
    Bp = kit.p("Base", "fieldstone")
    for side, plane, a0, a1 in (("S", y0, x0, x1), ("N", y1, x0, x1), ("E", x1, y0, y1), ("W", x0, y0, y1)):
        op = openings[side]
        tc.wall(Bp, side, plane, a0, a1, -0.3, 0.45, [o for o in op if o[2] < 0.45])
        tc.wall(W, side, plane, a0, a1, 0.45, H, op, gable=ridge if side in "EW" else None)
        tc.reveals(kit.p("Reveals", "trim_green"), side, plane, op, T)
    tc.corner_boards(kit, x0, x1, y0, y1, 0.45, H, mat="trim_green")
    tc.band(kit, x0, x1, y0, y1, 0.45, 0.6, mat="trim_green")
    tc.band(kit, x0, x1, y0, y1, H - 0.25, H, mat="trim_green", sides="SN")
    tc.gable_roof(kit, x0, x1, y0, y1, H, p["pitch"], axis="x", over_eave=p["eave"], over_gable=0.9, roof="seam_green",
                  soffit="deck", fascia="trim_green")
    for side, plane, ops in (("S", y0, w_s), ("N", y1, w_n), ("W", x0, [(-1.2, 1.2, 1.0, 3.0)])):
        for a0, a1, z0, z1 in ops:
            tc.window(kit, side, plane, (a0 + a1) / 2, z0, a1 - a0, z1 - z0, cell="dh_lamp" if a0 < XW else "dh_blind", trim="trim_green",
                      casing=0.1)
    for side, plane in (("S", y0), ("N", y1)):
        for a0, a1, z0, z1 in w_f:
            tc.window(kit, side, plane, (a0 + a1) / 2, z0, a1 - a0, z1 - z0, cell="dh_dark", trim="trim_green", casing=0.1)
        # the sliding freight door on its track, closed
        a0, a1, z0, z1 = fr_s
        tc.wbox(kit.p("FreightDoors", "bb_sage"), side, plane, a0 - 0.15, a1 + 0.15, z0, z1, -0.02, 0.08)
        tc.wbox(kit.p("FreightDoors", "trim_green"), side, plane, a0 - 0.15, a1 + 0.15, z1, z1 + 0.15, 0.0, 0.12, skip="back")
        Pf, u, nn = tc.frame(side, plane)
        kit.p("FreightDoors", "trim_green").beam(Pf(a0 - 0.1, z0 + 0.1, 0.09), Pf(a1 + 0.1, z1 - 0.1, 0.09), 0.08, 0.02, up=nn)
        kit.p("FreightDoors", "trim_green").beam(Pf(a1 + 0.1, z0 + 0.1, 0.09), Pf(a0 - 0.1, z1 - 0.1, 0.09), 0.08, 0.02, up=nn)
    # the bay window: three faces of glazing standing out 0.9 m toward the track, its own roof
    bx0, bx1, bd = -1.2, 1.2, 0.9
    By = kit.p("Bay", "bb_white")
    for side, plane, a0, a1 in (("N", y1 + bd, bx0 + 0.3, bx1 - 0.3), ("E", bx1, y1, y1 + bd - 0.0), ("W", bx0, y1, y1 + bd)):
        if side == "N":
            tc.wall(By, side, plane, a0, a1, 0.45, H - 0.3, [(a0 + 0.2, a1 - 0.2, 0.9, 3.0)])
            tc.window(kit, side, plane, (a0 + a1) / 2, 0.9, a1 - a0 - 0.4, 2.1, cell="dh_blind", trim="trim_green", casing=0.08)
        else:
            tc.wall(By, side, plane, a0, a1, 0.45, H - 0.3, [(a0 + 0.15, a1 - 0.15, 0.9, 3.0)])
            tc.window(kit, side, plane, (a0 + a1) / 2, 0.9, a1 - a0 - 0.3, 2.1, cell="dh_blind", trim="trim_green", casing=0.06)
    kit.p("Bay", "fieldstone").box((bx0, y1, -0.3), (bx1, y1 + bd, 0.45), skip="b")
    kit.p("BayRoof", "seam_green").face([(bx0 - 0.1, y1, H - 0.05), (bx1 + 0.1, y1, H - 0.05), (bx1 + 0.1, y1 + bd + 0.15, H - 0.4),
                                         (bx0 - 0.1, y1 + bd + 0.15, H - 0.4)], toward=(0, 1, 1))
    kit.collide((bx0, y1, 0), (bx1, y1 + bd, H - 0.3))
    # knee brackets under the eaves, both sides
    for side, plane in (("S", y0), ("N", y1)):
        Pf, u, nn = tc.frame(side, plane)
        for k in range(12):
            a = x0 + 1.2 + k * (x1 - x0 - 2.4) / 11
            if bx0 - 0.4 < a < bx1 + 0.4 and side == "N":
                continue
            Br = kit.p("Brackets", "trim_green")
            Br.beam(Pf(a, H - 1.2, 0.0), Pf(a, H - 0.05, p["eave"] * 0.8), 0.14, 0.14, up=V(0, 0, 1))
            Br.beam(Pf(a, H - 0.12, 0.0), Pf(a, H - 0.12, p["eave"] * 0.95), 0.14, 0.18, up=V(0, 0, 1))
    # doors
    tc.hinged_door(kit, col, root, "S", y0, -9.0, 1.2, 2.5, depth=0.1, leaf="door_green", index=1, glass="dh_lamp")
    tc.hinged_door(kit, col, root, "N", y1, -6.0, 1.2, 2.5, depth=0.1, leaf="door_green", index=2)
    kit.p("Stoop", "stone").box((-10.2, y0 - 1.0, -0.3), (-7.8, y0, 0.0), skip="b")
    tc.sign(kit, "S", y0, -9.0, 2.75, 1.6, 0.8, "museum", frame="trim_green", d=0.02)
    # platforms: at grade by the waiting room, raised at the freight room (open below)
    pd = p["platform"]
    kit.p("Platform", "concrete").box((x0, y1, -0.3), (XW + 0.5, y1 + pd, 0.0), skip="b")
    kit.collide((x0, y1, -0.3), (XW + 0.5, y1 + pd, 0.0))
    kit.p("PlatformEdge", "paint_yellow").face([(x0, y1 + pd - 0.3, 0.003), (XW + 0.5, y1 + pd - 0.3, 0.003),
                                                (XW + 0.5, y1 + pd - 0.05, 0.003), (x0, y1 + pd - 0.05, 0.003)], toward=(0, 0, 1))
    Fp = kit.p("FreightPlatform", "deck")
    Fp.box((XF - 0.5, y1, FZ - 0.1), (x1, y1 + pd, FZ), skip="")
    kit.p("Crib", "darkwood")
    for x in [XF - 0.3 + k * (x1 - XF + 0.1) / 7 for k in range(8)]:
        for y in (y1 + 0.4, y1 + pd - 0.4):
            kit.p("Crib", "darkwood").box((x - 0.15, y - 0.15, -0.3), (x + 0.15, y + 0.15, FZ - 0.1), skip="bt")
            kit.collide((x - 0.15, y - 0.15, -0.3), (x + 0.15, y + 0.15, FZ - 0.1))
    kit.p("CrawlDark", "shade").face([(XF - 0.5, y1 + 0.02, -0.3), (x1, y1 + 0.02, -0.3), (x1, y1 + 0.02, FZ - 0.1),
                                      (XF - 0.5, y1 + 0.02, FZ - 0.1)], toward=(0, 1, 0))
    kit.collide((XF - 0.5, y1, FZ - 0.1), (x1, y1 + pd, FZ))
    kit.info["crawl_space"] = {"box": [XF - 0.5, round(y1, 3), -0.3, x1, round(y1 + pd, 3), round(FZ - 0.1, 3)],
                               "clear_m": round(FZ - 0.1, 3), "open": "+Y and both ends"}
    tc.steps(kit, XF - 0.5 - 1.2, XF - 0.5, y1 + pd, FZ, n=7, run=0.3, direction=-1, mat="deck") if False else None
    for k in range(7):                                         # steps down from the freight platform's west end
        z = FZ - k * FZ / 7
        kit.p("Steps", "deck").box((XF - 0.5 - (k + 1) * 0.3, y1 + 1.0, z - FZ / 7 if k < 6 else -0.3), (XF - 0.5 - k * 0.3, y1 + 2.6, z),
                                   skip="b")
        kit.collide((XF - 0.5 - (k + 1) * 0.3, y1 + 1.0, -0.3), (XF - 0.5 - k * 0.3, y1 + 2.6, z))
    for x in (x0 + 2.0, XW, x1 - 2.0):
        kit.p("PlatformLamps", "trim_green").box((x - 0.04, y1 + 0.3, H - 1.0), (x + 0.04, y1 + 1.6, H - 0.9))
        kit.p("PlatformLamps", "trim_green").cyl((x, y1 + 1.6), 0.2, H - 1.4, H - 1.0, sides=8, caps="t", r1=0.06)
        kit.p("PlatformLamps", "lamp").cyl((x, y1 + 1.6), 0.19, H - 1.405, H - 1.4, sides=8, caps="b")
    tc.chimney(kit, XW + 0.3, 0.0, ridge - 1.0, ridge + 0.8, w=0.6, d=0.6, mat="brick_red")

    # ---------------------------------------------------------------- inside
    xi0, xi1, yi0, yi1 = x0 + T, x1 - T, y0 + T, y1 - T
    kit.sub = 1.0
    tc.room(kit, xi0, XW - 0.1, yi0, yi1, 0.0, C, walls="plaster", floor="woodfloor", ceiling="bb_white", name="Waiting",
            wainscot="darkwood", wainscot_h=1.1, base="trim_black",
            openings={"S": [door_s] + w_s[:3], "N": [door_n] + w_n[:2], "W": [(-1.2, 1.2, 1.0, 3.0)],
                      "E": [(-3.2, -1.2, 1.0, 2.0), (2.2, 3.2, 0.0, 2.2)]})
    tc.room(kit, XW + 0.1, XF - 0.1, yi0, yi1, 0.0, C, walls="plaster", floor="woodfloor", ceiling="bb_white", name="Office",
            wainscot="darkwood", wainscot_h=1.1, base="trim_black",
            openings={"S": [w_s[3]], "N": [bay, w_n[2]], "W": [(-3.2, -1.2, 1.0, 2.0), (2.2, 3.2, 0.0, 2.2)], "E": [(-4.2, -2.4, 0.0, 2.2)]})
    tc.room(kit, XF + 0.1, xi1, yi0, yi1, FZ, FZ + 3.4, walls="bb_white", floor="woodfloor", ceiling="deck", name="Freight",
            base="trim_black", openings={"S": [fr_s] + w_f, "N": [fr_n] + w_f, "W": [(-4.2, -2.4, FZ, FZ + 2.2)]})
    kit.sub = None
    tc.wall_collider(kit, "y", XW, y0, y1, T, C, [(2.2, 3.2)])
    tc.wall_collider(kit, "y", XF, y0, y1, T, C, [(-4.2, -2.4)])
    kit.collide((XF, y0, 0.0), (x1, y1, FZ))                       # the freight room's raised floor
    # the step-up from the office into the freight room (five risers inside the office)
    for k in range(5):
        z = (k + 1) * FZ / 5
        kit.p("InnerSteps", "darkwood").box((XF - 0.1 - (5 - k) * 0.3, -4.2, 0.0), (XF - 0.1 - (4 - k) * 0.3, -2.4, z), skip="b")
        kit.collide((XF - 0.1 - (5 - k) * 0.3, -4.2, 0.0), (XF - 0.1 - (4 - k) * 0.3, -2.4, z))
    tc.reveals(kit.p("Reveals", "trim_green"), "E", XF + 0.1, [(-4.2, -2.4, FZ, FZ + 2.2)], 0.2, sill=False)
    kit.p("RiserFace", "darkwood").face([(XF + 0.1, -4.2, 0.0), (XF + 0.1, -2.4, 0.0), (XF + 0.1, -2.4, FZ), (XF + 0.1, -4.2, FZ)],
                                        toward=(-1, 0, 0))
    # waiting room: benches along the walls, vitrines, the ticket window
    for (a0, a1, y, s) in ((xi0 + 0.5, -10.5, yi0 + 0.3, 1), (-8.0, -3.5, yi0 + 0.3, 1), (xi0 + 3.2, -7.2, yi1 - 0.3, -1)):
        Bn = kit.p("Benches", "varnish")
        ya, yb = sorted((y, y + s * 0.45))
        Bn.box((a0, ya, 0.42), (a1, yb, 0.47))
        Bn.box((a0, min(y, y - s * 0.05), 0.47), (a1, max(y, y - s * 0.05), 0.95))
        kit.collide((a0, ya, 0), (a1, yb, 0.95))
    for k in range(3):
        vx = -14.0 + k * 3.6
        kit.p("Vitrines", "darkwood").box((vx - 0.8, -0.6, 0.0), (vx + 0.8, 0.6, 0.85), skip="b")
        kit.p("Vitrines", "windows").face([(vx - 0.75, -0.55, 0.86), (vx + 0.75, -0.55, 0.86), (vx + 0.75, 0.55, 0.86),
                                           (vx - 0.75, 0.55, 0.86)], uvs=tc.cell_uv(tc.WIN["bk_display"], sub=(0.1, 0.1, 0.9, 0.9)),
                                          toward=(0, 0, 1))
        kit.p("Vitrines", "brass").box((vx - 0.82, -0.62, 0.85), (vx + 0.82, 0.62, 0.87), skip="b") if False else None
        kit.collide((vx - 0.8, -0.6, 0), (vx + 0.8, 0.6, 0.9))
        kit.light((vx, 0.0, 2.8), (1.0, 0.8, 0.55), 28, 0.3, kind="SPOT")
    tc.wbox(kit.p("TicketGrille", "brass"), "W", XW - 0.1, -3.2, -1.2, 1.0, 2.0, -0.02, 0.0, skip="back")
    for k in range(9):
        a = -3.15 + k * 0.24
        tc.wbox(kit.p("TicketGrille", "brass"), "W", XW - 0.1, a, a + 0.02, 1.0, 2.0, 0.0, 0.02)
    for x in (-13.0, -8.0, -4.5):
        kit.p("Pendants", "trim_green").cyl((x, 0.0), 0.25, 2.7, 2.95, sides=8, caps="t", r1=0.08)
        kit.p("Pendants", "lamp").cyl((x, 0.0), 0.24, 2.695, 2.7, sides=8, caps="b")
        kit.p("Cords", "trim_black").tube(V(x, 0.0, 2.95), V(x, 0.0, C), 0.006, 3)
        kit.light((x, 0.0, 2.65), (1.0, 0.74, 0.46), 45, 0.2)
    # office: the agent's desk in the bay, a telegraph table
    tc.table(kit, 0.0, y1 - 0.6, w=2.0, d=0.6, h=0.78, top="varnish", base="darkwood")
    kit.p("Telegraph", "brass").box((-0.3, y1 - 0.7, 0.78), (0.1, y1 - 0.5, 0.88))
    kit.light((0.0, 0.0, 3.2), (1.0, 0.8, 0.55), 30, 0.3)
    # freight room: an open floor (the model table goes here), hand trucks, crates
    kit.p("HandTruck", "trim_black").polyline([V(14.8, 3.6, FZ), V(14.9, 3.8, FZ + 1.3), V(14.6, 3.8, FZ + 1.3)], 0.02, 4)
    kit.p("Crates", "deck").box((13.8, 3.0, FZ), (14.6, 3.8, FZ + 0.7))
    kit.collide((13.8, 3.0, FZ), (14.6, 3.8, FZ + 0.7))
    for x in (5.0, 9.0, 13.0):
        kit.p("FreightLamps", "trim_black").cyl((x, 0.0), 0.3, FZ + 2.7, FZ + 2.95, sides=8, caps="t", r1=0.08)
        kit.p("FreightLamps", "lamp").cyl((x, 0.0), 0.29, FZ + 2.695, FZ + 2.7, sides=8, caps="b")
        kit.light((x, 0.0, FZ + 2.65), (1.0, 0.78, 0.5), 55, 0.2)
    kit.info["model_table_spot"] = [9.0, 0.0, FZ]

    far = tc.Far(n)
    far.gable(x0, x1, y0, y1, 0.0, H, ridge, axis="x", wall="bb_white", roof="trim_green", over=p["eave"])
    far.box((XF - 0.5, y1, -0.3), (x1, y1 + pd, FZ), "deck", skip="b")
    for side, plane, ops in (("S", y0, w_s), ("N", y1, w_n)):
        far.windows(side, plane, [(a0 + a1) / 2 for a0, a1, _, _ in ops], 1.0, 1.0, 2.0, "glass_dark")
    kit.entrance((-9.0, y0 - 1.1, -0.3), "-Y", 1.2, kind="door", note="TownDepot_Door_1, the street door (one step)")
    kit.entrance((-6.0, y1 + 0.1, 0.0), "+Y", 1.2, kind="door", note="TownDepot_Door_2, to the passenger platform")
    kit.info.update(walk_in=True, storeys=1, rooms=["waiting room 13.7 x 9.6 (benches, vitrines, ticket window)",
                                                    "agent's office 3.8 x 9.6 (bay window, steps up)",
                                                    f"freight room 13.7 x 9.6 at z {FZ} (open floor, model table spot)"],
                    footprint=[round(x0 - 0.9, 3), round(y0 - 1.6, 3), round(x1 + 0.9, 3), round(y1 + pd, 3)])
    parts = tc.finish(kit, col, root, far)
    if p["bake"]:
        meshes = [o for o in root.children_recursive if o.type == "MESH" and not o.name.endswith("_LOD1")]
        town_light.bake(kit, root, meshes, [(xi0, yi0, 0.0, XW - 0.1, yi1, C), (XW + 0.1, yi0, 0.0, XF - 0.1, yi1, C),
                                            (XF + 0.1, yi0, FZ, xi1, yi1, FZ + 3.4)])
    return root, parts
