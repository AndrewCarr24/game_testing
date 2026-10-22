"""Smaller buildings of the town kit (not an asset: exported by thin modules town_<name>.py):

  church_hall   the fellowship hall wing: one storey of white lap siding, a low gable, a glass
                door at -Y; walk-in: one hall with a long run of folding tables and chairs, a
                serving hatch, a coffee urn (its side at +X joins the church)
  garage        a detached two-car garage, white lap, an up-and-over door (closed)
  garage_open   the same with its door up: walk-in, an empty concrete floor (the layout puts the
                estate's stolen furniture in it), a bare bulb, shelves
  shed          a board-and-batten garden shed, a door and a window
  motel_office  the motor lodge's office: a lobby window, a carport over the drive-in, walk-in
                lobby (a counter, a key board, a rack of brochures as blank cards)
  motel_wing    six units in a row under one low gable, a covered walk on posts at -Y, matching
                doors, a window and an AC unit each, bathroom windows at +Y; unit 3 is walk-in
                (`_Door_3`: bed, nightstand, TV, a bathroom door)
  school        the 1930s brick school, still in use: two storeys of window bands, a flat roof
                behind a parapet, a central entry pavilion with a new steel canopy (a shell)
Origins: floor centre at the door sill; fronts -Y.
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
B = {}


def builder(name):
    def deco(fn):
        B[name] = fn
        return fn
    return deco


def _bake(kit, root, boxes):
    meshes = [o for o in root.children_recursive if o.type == "MESH" and not o.name.endswith("_LOD1")]
    town_light.bake(kit, root, meshes, boxes)


# ---------------------------------------------------------------- the fellowship hall

@builder("church_hall")
def church_hall(kit, col, root, bake=True):
    x0, x1, y0, y1, T, H, C = -6.0, 6.0, -8.0, 8.0, 0.2, 3.6, 3.1
    ridge = H + 6.0 * 0.3
    door = (-0.7, 0.7, 0.0, 2.3)
    win = [(y - 0.6, y + 0.6, 1.0, 2.3) for y in (-5.0, -1.5, 2.0, 5.5)]
    ops = {"S": [door, (-4.5, -3.0, 1.0, 2.3), (3.0, 4.5, 1.0, 2.3)], "W": win, "N": [(-0.5, 0.5, 0.0, 2.1)], "E": [(5.0, 6.5, 1.0, 2.0)]}
    tc.shell(kit, x0, x1, y0, y1, H, ops, "lap_white", base="fieldstone", base_h=0.4, thick=T, gables={"S": ridge, "N": ridge},
             reveal_part=kit.p("Reveals", "trim"))
    tc.gable_roof(kit, x0, x1, y0, y1, H, 0.3, axis="y", over_eave=0.4, over_gable=0.3, roof="seam_black", soffit="trim", fascia="trim")
    for side, plane in (("S", y0), ("W", x0), ("N", y1), ("E", x1)):
        for a0, a1, z0, z1 in ops[side]:
            if z0 > 0.1:
                tc.window(kit, side, plane, (a0 + a1) / 2, z0, a1 - a0, z1 - z0, cell="dh_blind", trim="trim", casing=0.08)
    tc.hinged_door(kit, col, root, "S", y0, 0.0, 1.4, 2.3, depth=0.1, leaf="trim_black", index=1, style="glass", glass="bk_dark")
    tc.door(kit, "N", y1, 0.0, 1.0, 2.1, leaf="door_wood", trim="trim", casing=0.08)
    kit.p("Canopy", "trim_black").box((-1.6, y0 - 1.4, 2.6), (1.6, y0, 2.75))
    tc.corner_boards(kit, x0, x1, y0, y1, 0.4, H)
    kit.sub = 1.0
    tc.room(kit, x0 + T, x1 - T, y0 + T, y1 - T, 0.0, C, walls="plaster", floor="tile_floor", ceiling="paint_white", name="Hall",
            wainscot="darkwood", wainscot_h=1.0, base="trim_black", openings={k: v for k, v in ops.items()})
    kit.sub = None
    for k in range(5):                                       # the long table: five folding tables end to end
        y = -5.6 + k * 2.6
        kit.p("Tables", "plastic_white").box((-0.4, y - 1.2, 0.71), (0.4, y + 1.2, 0.75))
        for xx in (-0.3, 0.3):
            kit.p("TableLegs", "metal_galv").box((xx - 0.015, y - 1.1, 0.0), (xx + 0.015, y - 1.07, 0.71))
            kit.p("TableLegs", "metal_galv").box((xx - 0.015, y + 1.07, 0.0), (xx + 0.015, y + 1.1, 0.71))
        kit.collide((-0.4, y - 1.2, 0), (0.4, y + 1.2, 0.75))
        for s in (-1, 1):
            for j in (-0.6, 0.6):
                cx, cy = s * 0.75, y + j
                kit.p("Chairs", "metal_dark").box((cx - 0.2, cy - 0.2, 0.43), (cx + 0.2, cy + 0.2, 0.47))
                bx = cx + s * 0.18
                kit.p("Chairs", "metal_dark").box((min(bx, bx + s * 0.03), cy - 0.19, 0.47), (max(bx, bx + s * 0.03), cy + 0.19, 0.88))
    kit.p("Hatch", "darkwood").box((x1 - 0.5, -2.0, 0.0), (x1 - T, 1.0, 1.0), skip="b")
    kit.p("Urn", "chrome").cyl((x1 - 0.35, 0.4), 0.15, 1.0, 1.45, sides=8)
    kit.collide((x1 - 0.5, -2.0, 0), (x1 - T, 1.0, 1.0))
    kit.info["table_spot"] = [0.0, 0.0, 0.75]
    for y in (-5.0, 0.0, 5.0):
        kit.p("CeilingPanels", "glow_white").face([(-1.0, y - 0.3, C - 0.01), (1.0, y - 0.3, C - 0.01), (1.0, y + 0.3, C - 0.01),
                                                  (-1.0, y + 0.3, C - 0.01)], toward=(0, 0, -1))
        kit.light((0.0, y, C - 0.05), (0.92, 0.94, 1.0), 40, 1.2, kind="AREA")
    far = tc.Far(kit.name)
    far.gable(x0, x1, y0, y1, 0.0, H, ridge, axis="y", wall="bb_white", roof="seam_black", over=0.4)
    kit.entrance((0.0, y0 - 0.1, 0.0), "-Y", 1.4, kind="door", note=f"{kit.name}_Door_1")
    kit.info.update(walk_in=True, rooms=["hall 11.6 x 15.6 (the long table)"], joins="its +X side meets the church's side",
                    footprint=[x0 - 0.4, y0 - 1.4, x1 + 0.4, y1 + 0.3])
    parts = tc.finish(kit, col, root, far)
    if bake:
        _bake(kit, root, [(x0 + T, y0 + T, 0.0, x1 - T, y1 - T, C)])
    return parts


# ---------------------------------------------------------------- garages, shed

def _garage(kit, col, root, open_=False, bake=True):
    x0, x1, y0, y1, T, H = -3.5, 3.5, -3.5, 3.5, 0.15, 2.7
    ridge = H + 3.5 * 0.5
    gd = (-2.6, 2.6, 0.0, 2.25)
    ops = {"S": [gd], "E": [(0.5, 1.4, 0.0, 2.1)], "W": [(-0.6, 0.6, 1.1, 1.9)], "N": []}
    tc.shell(kit, x0, x1, y0, y1, H, ops, "lap_white", thick=T, gables={"S": ridge, "N": ridge}, reveal_part=kit.p("Reveals", "trim"))
    kit.colliders = [c for c in kit.colliders if not (c[1] < y0 + 0.01 and c[4] <= y0 + T + 0.01)]
    kit.collide((x0, y0, 0), (gd[0], y0 + T, H))
    kit.collide((gd[1], y0, 0), (x1, y0 + T, H))
    tc.gable_roof(kit, x0, x1, y0, y1, H, 0.5, axis="y", over_eave=0.3, over_gable=0.25, roof="shingle", soffit="trim", fascia="trim")
    tc.corner_boards(kit, x0, x1, y0, y1, 0.0, H)
    tc.window(kit, "W", x0, 0.0, 1.1, 1.2, 0.8, cell="dh_dark", trim="trim", casing=0.07)
    tc.door(kit, "E", x1, 0.95, 0.9, 2.1, leaf="door_wood", trim="trim", casing=0.07)
    D = kit.p("GarageDoor", "paint_white")
    if not open_:
        tc.wbox(D, "S", y0, gd[0], gd[1], 0.0, gd[3], -0.08, -0.03)
        for k in range(4):
            tc.wbox(kit.p("GarageDoor", "trim"), "S", y0, gd[0] + 0.05, gd[1] - 0.05, 0.1 + k * 0.54, 0.12 + k * 0.54, -0.03, -0.02)
        kit.collide((gd[0], y0, 0), (gd[1], y0 + T, gd[3]))
    else:                                                       # the door up under the ceiling
        D.box((gd[0], y0 + 0.2, gd[3] - 0.02), (gd[1], y0 + 2.4, gd[3] + 0.04))
        kit.p("Tracks", "metal_galv").box((gd[0] - 0.05, y0 + 0.1, gd[3] - 0.03), (gd[0], y0 + 2.6, gd[3] + 0.05))
        kit.p("Tracks", "metal_galv").box((gd[1], y0 + 0.1, gd[3] - 0.03), (gd[1] + 0.05, y0 + 2.6, gd[3] + 0.05))
    kit.p("Apron", "concrete").box((gd[0] - 0.3, y0 - 1.2, 0.0), (gd[1] + 0.3, y0, 0.02), skip="b")
    if open_:
        tc.room(kit, x0 + T, x1 - T, y0 + T, y1 - T, 0.0, H - 0.05, walls="block", floor="concrete", ceiling="deck", name="Inside",
                base=None, openings={k: v for k, v in ops.items()})
        kit.p("Shelves", "deck").box((x0 + T, 1.8, 0.0), (x0 + T + 0.5, y1 - T, 1.9), skip="b")
        kit.collide((x0 + T, 1.8, 0), (x0 + T + 0.5, y1 - T, 1.9))
        kit.p("Bulbs", "lamp").cyl((0.0, 0.5), 0.06, H - 0.3, H - 0.1, sides=6, caps="tb")
        kit.light((0.0, 0.5, H - 0.35), (1.0, 0.7, 0.42), 30, 0.06)
        kit.info["goods_area"] = [round(x0 + T + 0.6, 3), round(y0 + T, 3), round(x1 - T, 3), round(y1 - T, 3)]
    far = tc.Far(kit.name)
    far.gable(x0, x1, y0, y1, 0.0, H, ridge, axis="y", wall="bb_white", roof="shingle", over=0.3)
    far.quad("S", y0, gd[0], gd[1], 0.0, gd[3], "shade" if open_ else "paint_white")
    kit.entrance((0.0, y0 - 0.1, 0.0), "-Y", round(gd[1] - gd[0], 2), kind="garage", note="door up (walk-in)" if open_ else "door down")
    kit.info.update(walk_in=open_, footprint=[x0 - 0.3, y0 - 1.2, x1 + 0.3, y1 + 0.25])
    parts = tc.finish(kit, col, root, far)
    if open_ and bake:
        _bake(kit, root, [(x0 + T, y0 + T, 0.0, x1 - T, y1 - T, H)])
    return parts


@builder("garage")
def garage(kit, col, root):
    return _garage(kit, col, root, False)


@builder("garage_open")
def garage_open(kit, col, root):
    return _garage(kit, col, root, True)


@builder("shed")
def shed(kit, col, root):
    x0, x1, y0, y1, H = -1.5, 1.5, -2.0, 2.0, 2.2
    ridge = H + 1.5 * 0.7
    ops = {"S": [(-0.5, 0.5, 0.0, 1.95)], "E": [(-0.4, 0.4, 1.1, 1.7)]}
    for side, plane, a0, a1 in (("S", y0, x0, x1), ("N", y1, x0, x1), ("E", x1, y0, y1), ("W", x0, y0, y1)):
        tc.wall(kit.p("Walls", "bb_sage"), side, plane, a0, a1, 0.0, H, ops.get(side, []), gable=ridge if side in "SN" else None)
    tc.door(kit, "S", y0, 0.0, 1.0, 1.95, leaf="door_wood", trim="trim", wall_part=kit.p("Walls", "bb_sage"), casing=0.07)
    tc.window(kit, "E", x1, 0.0, 1.1, 0.8, 0.6, cell="dh_dark", trim="trim", casing=0.06, wall_part=kit.p("Walls", "bb_sage"))
    tc.gable_roof(kit, x0, x1, y0, y1, H, 0.7, axis="y", over_eave=0.2, over_gable=0.2, roof="seam_black", soffit="trim", fascia="trim")
    kit.collide((x0, y0, 0), (x1, y1, H))
    far = tc.Far(kit.name)
    far.gable(x0, x1, y0, y1, 0.0, H, ridge, axis="y", wall="trim_green", roof="seam_black", over=0.2)
    kit.entrance((0.0, y0 - 0.1, 0.0), "-Y", 1.0, kind="door", note="closed")
    kit.info.update(walk_in=False, footprint=[x0 - 0.2, y0 - 0.2, x1 + 0.2, y1 + 0.2])
    return tc.finish(kit, col, root, far)


# ---------------------------------------------------------------- the motor lodge

@builder("motel_office")
def motel_office(kit, col, root, bake=True):
    x0, x1, y0, y1, T, H, C = -5.0, 3.0, -4.5, 4.5, 0.2, 3.4, 2.9
    ridge = H + 4.5 * 0.3
    door = (-3.8, -2.8, 0.0, 2.2)
    lobby = (-2.2, 1.8, 0.8, 2.6)
    ops = {"S": [door, lobby], "N": [(-1.0, 0.0, 0.0, 2.1)], "W": [(-1.0, 1.0, 1.0, 2.2)], "E": [(-2.0, -0.5, 0.0, 2.1)]}
    tc.shell(kit, x0, x1, y0, y1, H, ops, "block", thick=T, gables={"E": ridge, "W": ridge}, reveal_part=kit.p("Reveals", "trim"))
    tc.gable_roof(kit, x0, x1, y0, y1, H, 0.3, axis="x", over_eave=0.6, over_gable=0.4, roof="seam_green", soffit="trim", fascia="trim")
    tc.glazing(kit, "S", y0, lobby[0], lobby[1], lobby[2], lobby[3], cell="bk_office", mullions=[-0.2], depth=0.1, frame="trim")
    tc.window(kit, "W", x0, 0.0, 1.0, 2.0, 1.2, cell="dh_blind", trim="trim", casing=0.06)
    tc.hinged_door(kit, col, root, "S", y0, -3.3, 1.0, 2.2, depth=0.1, leaf="door_red", index=1, style="glass", glass="bk_office")
    tc.door(kit, "N", y1, -0.5, 1.0, 2.1, leaf="door_red", trim="trim", casing=0.06)
    tc.door(kit, "E", x1, -1.25, 1.0, 2.1, leaf="door_red", trim="trim", casing=0.06)
    # the carport: a flat roof on two steel posts over the drive-in at +X
    kit.p("Carport", "trim_black").box((x1, y0 - 0.5, 2.9), (x1 + 4.0, y1 + 0.5, 3.1))
    for y in (y0 - 0.3, y1 + 0.3):
        kit.p("CarportPosts", "trim_black").box((x1 + 3.7, y - 0.08, 0.0), (x1 + 3.86, y + 0.08, 2.9), skip="b")
        kit.collide((x1 + 3.7, y - 0.08, 0), (x1 + 3.86, y + 0.08, 2.9))
    kit.p("CarportGlow", "glow_white").face([(x1 + 1.5, -0.5, 2.895), (x1 + 2.5, -0.5, 2.895), (x1 + 2.5, 0.5, 2.895),
                                             (x1 + 1.5, 0.5, 2.895)], toward=(0, 0, -1))
    tc.sign(kit, "S", y0, -0.2, 2.75, 2.0, 0.6, "motel" if "motel" in tc.tt.SIGN_KINDS else "bar", d=0.02, glow=True) if False else None
    kit.p("Walk", "concrete").box((x0, y0 - 1.5, 0.0), (x1, y0, 0.02), skip="b")
    kit.sub = 0.8
    tc.room(kit, x0 + T, x1 - T, y0 + T, y1 - T, 0.0, C, walls="plaster", floor="tile_floor", ceiling="paint_white", name="Lobby",
            wainscot="cedar", wainscot_h=1.0, base="trim_black", openings={k: v for k, v in ops.items()})
    kit.sub = None
    kit.p("Counter", "cedar").box((-1.5, 1.6, 0.0), (2.6, 2.3, 1.05), skip="bt")
    kit.p("CounterTop", "formica").box((-1.6, 1.55, 1.05), (2.7, 2.35, 1.1))
    kit.collide((-1.6, 1.55, 0), (2.7, 2.35, 1.1))
    kit.p("KeyBoard", "darkwood").box((-1.0, y1 - T - 0.04, 1.4), (1.0, y1 - T, 2.2))
    for k in range(12):
        kx = -0.85 + (k % 6) * 0.34
        kz = 1.6 + (k // 6) * 0.35
        kit.p("Keys", "brass").box((kx, y1 - T - 0.07, kz), (kx + 0.04, y1 - T - 0.04, kz + 0.12))
    kit.p("Brochures", "darkwood").box((x0 + T, -3.4, 0.0), (x0 + T + 0.35, -2.2, 1.5), skip="b")
    for k in range(4):
        for j in range(3):
            kit.p("Brochures", ("paper", "paint_teal", "paint_orange")[j]).box((x0 + T + 0.34, -3.3 + j * 0.38, 0.4 + k * 0.28),
                                                                               (x0 + T + 0.36, -3.0 + j * 0.38, 0.62 + k * 0.28))
    kit.collide((x0 + T, -3.4, 0), (x0 + T + 0.35, -2.2, 1.5))
    kit.light((0.0, 0.0, C - 0.05), (1.0, 0.85, 0.65), 45, 1.5, kind="AREA")
    far = tc.Far(kit.name)
    far.gable(x0, x1, y0, y1, 0.0, H, ridge, axis="x", wall="paint_white", roof="trim_green", over=0.6)
    far.box((x1, y0 - 0.5, 2.9), (x1 + 4.0, y1 + 0.5, 3.1), "trim_black", skip="")
    far.quad("S", y0, lobby[0], lobby[1], lobby[2], lobby[3], "window_lit")
    kit.entrance((-3.3, y0 - 0.1, 0.0), "-Y", 1.0, kind="door", note=f"{kit.name}_Door_1, the lobby")
    kit.info.update(walk_in=True, rooms=["lobby 7.6 x 8.6 (counter, key board, brochures)"],
                    footprint=[x0 - 0.4, y0 - 1.5, x1 + 4.0, y1 + 0.6])
    parts = tc.finish(kit, col, root, far)
    if bake:
        _bake(kit, root, [(x0 + T, y0 + T, 0.0, x1 - T, y1 - T, C)])
    return parts


@builder("motel_wing")
def motel_wing(kit, col, root, bake=True):
    x0, x1, y0, y1, T, H, C = -13.0, 13.0, -4.0, 6.0, 0.2, 3.2, 2.7
    walk = 2.0
    ridge = H + 5.0 * 0.25
    uw = (x1 - x0) / 6
    S_ops, N_ops, units = [], [], []
    for i in range(6):
        ux0 = x0 + i * uw
        d = (ux0 + 0.8, ux0 + 1.75, 0.0, 2.15)
        w = (ux0 + 2.3, ux0 + 3.6, 1.0, 2.2)
        S_ops += [d, w]
        N_ops.append((ux0 + 1.2, ux0 + 1.8, 1.7, 2.2))
        units.append((ux0, d, w))
    ops = {"S": S_ops, "N": N_ops, "E": [], "W": []}
    tc.shell(kit, x0, x1, y0, y1, H, ops, "block", thick=T, gables={"E": ridge, "W": ridge}, reveal_part=kit.p("Reveals", "trim"))
    tc.gable_roof(kit, x0, x1, y0 - walk, y1, H, 0.25, axis="x", over_eave=0.3, over_gable=0.4, roof="seam_green", soffit="trim",
                  fascia="trim", collide=True)
    for i in range(1, 6):
        tc.wall_collider(kit, "y", x0 + i * uw, y0, y1, T, H)
    for k in range(8):                                           # the covered walk's posts
        x = x0 + 0.3 + k * (x1 - x0 - 0.6) / 7
        kit.p("Posts", "trim").box((x - 0.07, y0 - walk + 0.1, 0.0), (x + 0.07, y0 - walk + 0.24, H - 0.4), skip="b")
        kit.collide((x - 0.07, y0 - walk + 0.1, 0), (x + 0.07, y0 - walk + 0.24, H - 0.4))
    kit.p("Walk", "concrete").box((x0, y0 - walk, 0.0), (x1, y0, 0.12), skip="b")
    kit.collide((x0, y0 - walk, 0), (x1, y0, 0.12))
    for i, (ux0, d, w) in enumerate(units):
        n = i + 1
        if n == 3:
            tc.hinged_door(kit, col, root, "S", y0, (d[0] + d[1]) / 2, d[1] - d[0], 2.15, depth=0.1, leaf="door_red", index=3)
        else:
            tc.door(kit, "S", y0, (d[0] + d[1]) / 2, d[1] - d[0], 2.15, leaf="door_red", trim="trim", casing=0.06)
        tc.window(kit, "S", y0, (w[0] + w[1]) / 2, w[2], w[1] - w[0], w[3] - w[2], cell=("dh_curtain", "dh_blind", "dh_curtain")[i % 3],
                  trim="trim", casing=0.06)
        A = kit.p("AC", "plastic_white")
        A.box((w[0] + 0.3, y0 - 0.35, 0.35), (w[0] + 1.0, y0, 0.9))
        kit.p("ACGrille", "metal_dark").face([(w[0] + 0.35, y0 - 0.355, 0.4), (w[0] + 0.95, y0 - 0.355, 0.4), (w[0] + 0.95, y0 - 0.355, 0.85),
                                              (w[0] + 0.35, y0 - 0.355, 0.85)], toward=(0, -1, 0))
        kit.collide((w[0] + 0.3, y0 - 0.35, 0), (w[0] + 1.0, y0, 0.9))
        kit.p("PorchLights", "lamp").cyl((d[1] + 0.25, y0 - 0.05), 0.06, 2.2, 2.4, sides=6)
        tc.window(kit, "N", y1, (N_ops[i][0] + N_ops[i][1]) / 2, 1.7, 0.6, 0.5, cell="bk_blinds", trim="trim", casing=0.04)
    # unit 3, walk-in: bed, nightstand, TV, a bathroom door
    ux0 = units[2][0]
    rx0, rx1 = ux0 + T / 2, ux0 + uw - T / 2
    kit.sub = 0.8
    tc.room(kit, rx0, rx1, y0 + T, y1 - T - 2.2, 0.0, C, walls="plaster", floor="woodfloor", ceiling="paint_white", name="Unit",
            base="trim_black", openings={"S": [units[2][1], units[2][2]], "N": [(rx1 - 1.2, rx1 - 0.4, 0.0, 2.1)]})
    kit.sub = None
    tc.door(kit, "S", y1 - T - 2.2, rx1 - 0.8, 0.8, 2.1, leaf="door_wood", trim="trim", casing=0.05, depth=0.05)
    kit.collide((rx0, y1 - T - 2.25, 0), (rx1, y1, C))
    kit.p("Bed", "darkwood").box((rx0 + 0.2, 0.2, 0.0), (rx0 + 1.8, 2.3, 0.45), skip="b")
    kit.p("Bed", "paint_white").box((rx0 + 0.22, 0.25, 0.45), (rx0 + 1.78, 2.28, 0.6))
    kit.p("Bed", "trim_red").box((rx0 + 0.2, 0.2, 0.5), (rx0 + 1.8, 1.4, 0.64))
    kit.p("Bed", "darkwood").box((rx0 + 0.2, 2.3, 0.0), (rx0 + 1.8, 2.4, 1.1))
    kit.collide((rx0 + 0.2, 0.2, 0), (rx0 + 1.8, 2.4, 0.64))
    kit.p("Nightstand", "darkwood").box((rx0 + 1.9, 2.0, 0.0), (rx0 + 2.4, 2.45, 0.6), skip="b")
    kit.p("Lamp", "lamp").cyl((rx0 + 2.15, 2.2), 0.12, 0.6, 0.95, sides=6, caps="tb", r1=0.08)
    kit.light((rx0 + 2.15, 2.2, 0.9), (1.0, 0.7, 0.42), 25, 0.1)
    kit.p("TV", "metal_dark").box((rx1 - 0.6, 0.4, 0.7), (rx1 - 0.1, 1.4, 1.35))
    kit.p("TV", "glow_cool").face([(rx1 - 0.605, 0.45, 0.75), (rx1 - 0.605, 1.35, 0.75), (rx1 - 0.605, 1.35, 1.3), (rx1 - 0.605, 0.45, 1.3)],
                                  toward=(-1, 0, 0))
    kit.p("Dresser", "darkwood").box((rx1 - 0.6, 0.2, 0.0), (rx1 - T, 1.6, 0.7), skip="b")
    kit.collide((rx1 - 0.6, 0.2, 0), (rx1 - T, 1.6, 0.7))
    kit.light(((rx0 + rx1) / 2, 0.0, C - 0.05), (1.0, 0.85, 0.65), 15, 1.0, kind="AREA")
    far = tc.Far(kit.name)
    far.gable(x0, x1, y0 - walk, y1, 0.0, H, ridge, axis="x", wall="paint_white", roof="trim_green", over=0.3)
    far.windows("S", y0 - walk, [(d[0] + d[1]) / 2 for _, d, _ in units], 0.0, 0.95, 2.15, "door_red", d=0.02)
    for i, (ux0, d, w) in enumerate(units):
        kit.entrance(((d[0] + d[1]) / 2, y0 - walk - 0.1, 0.0), "-Y", round(d[1] - d[0], 2), kind="door",
                     note=f"unit {i + 1}" + (f", {kit.name}_Door_3 (walk-in)" if i == 2 else ", closed"))
    kit.info.update(walk_in=True, units=6, rooms=["unit 3: 4.1 x 7.4 (bed, nightstand, TV)"],
                    footprint=[x0 - 0.4, y0 - walk - 0.3, x1 + 0.4, y1 + 0.3])
    parts = tc.finish(kit, col, root, far)
    if bake:
        _bake(kit, root, [(rx0, y0 + T, 0.0, rx1, y1 - T - 2.2, C)])
    return parts


# ---------------------------------------------------------------- the school

@builder("school")
def school(kit, col, root):
    x0, x1, y0, y1, T, sh = -22.0, 22.0, -7.5, 7.5, 0.3, 4.2
    H = sh * 2 + 0.6
    pav = (-5.0, 5.0)
    ops = {"S": [], "N": [], "E": [], "W": []}
    for side, a0, a1 in (("S", x0, x1), ("N", x0, x1)):
        for s in range(2):
            z0 = s * sh + 1.0
            for k in range(int((a1 - a0) / 3.5)):
                a = a0 + 1.75 + k * 3.5
                if side == "S" and pav[0] - 0.5 < a < pav[1] + 0.5:
                    continue
                ops[side].append((a - 1.2, a + 1.2, z0, z0 + 2.6))
    for side, a0, a1 in (("E", y0, y1), ("W", y0, y1)):
        for s in range(2):
            for a in (-3.5, 0.0, 3.5):
                ops[side].append((a - 0.9, a + 0.9, s * sh + 1.0, s * sh + 3.6))
    Wl = kit.p("Walls", "brick_red")
    kit.tints["Walls"] = (0.86, 0.76, 0.7)
    for side, plane, a0, a1 in (("S", y0, x0, x1), ("N", y1, x0, x1), ("E", x1, y0, y1), ("W", x0, y0, y1)):
        tc.wall(Wl, side, plane, a0, a1, 0.0, H, ops[side])
        tc.reveals(kit.p("Reveals", "brick_red"), side, plane, ops[side], T)
        for a0_, a1_, z0, z1 in ops[side]:
            tc.glazing(kit, side, plane, a0_, a1_, z0, z1, cells=["dh_blind", "dh_blind_low", "dh_venetian"],
                       mullions=[(a0_ + a1_) / 2] if a1_ - a0_ > 2 else [], transom=z0 + 1.9, depth=0.15, frame="trim")
            tc.wbox(kit.p("Sills", "stone"), side, plane, a0_ - 0.05, a1_ + 0.05, z0 - 0.12, z0, -0.1, 0.06, skip="back")
    kit.tints["Reveals"] = (0.86, 0.76, 0.7)
    for s in range(1, 3):
        tc.band(kit, x0, x1, y0, y1, s * sh - 0.05 if s < 2 else H - 0.5, s * sh + 0.15 if s < 2 else H - 0.3, proud=0.05, mat="stone")
    tc.flat_roof(kit, x0, x1, y0, y1, H, parapet=0.0001, wall="brick_red", coping="stone") if False else None
    kit.p("RoofDeck", "tar").face([(x0, y0, H), (x1, y0, H), (x1, y1, H), (x0, y1, H)], toward=(0, 0, 1))
    tc.wbox(kit.p("Coping", "stone"), "S", y0, x0, x1, H, H + 0.1, -T, 0.05)
    tc.wbox(kit.p("Coping", "stone"), "N", y1, x0, x1, H, H + 0.1, -T, 0.05)
    tc.wbox(kit.p("Coping", "stone"), "E", x1, y0, y1, H, H + 0.1, -T, 0.05)
    tc.wbox(kit.p("Coping", "stone"), "W", x0, y0, y1, H, H + 0.1, -T, 0.05)
    # the entry pavilion: proud of the front, taller, stone surround, double doors, the new canopy
    py0 = y0 - 1.2
    PV = kit.p("Pavilion", "brick_red")
    kit.tints["Pavilion"] = (0.8, 0.7, 0.64)
    tc.wall(PV, "S", py0, pav[0], pav[1], 0.0, H + 1.2, [(-1.5, 1.5, 0.0, 2.8), (-1.2, 1.2, sh + 1.0, sh + 3.4)])
    for side, plane in (("E", pav[1]), ("W", pav[0])):
        tc.wall(PV, side, plane, py0, y0, 0.0, H + 1.2)
    tc.wall(PV, "N", y0, pav[0], pav[1], H, H + 1.2)
    kit.p("PavilionTop", "tar").face([(pav[0], py0, H + 1.2), (pav[1], py0, H + 1.2), (pav[1], y0, H + 1.2), (pav[0], y0, H + 1.2)],
                                     toward=(0, 0, 1))
    tc.wbox(kit.p("Coping", "stone"), "S", py0, pav[0], pav[1], H + 1.2, H + 1.32, -1.2, 0.05)
    tc.wbox(kit.p("Surround", "stone"), "S", py0, -1.9, 1.9, 0.0, 3.4, 0.0, 0.1, skip="back") if False else None
    for a0, a1 in ((-1.9, -1.5), (1.5, 1.9)):
        tc.wbox(kit.p("Surround", "stone"), "S", py0, a0, a1, 0.0, 3.2, 0.0, 0.1, skip="back")
    tc.wbox(kit.p("Surround", "stone"), "S", py0, -1.9, 1.9, 2.8, 3.2, 0.0, 0.1, skip="back")
    tc.door(kit, "S", py0, -0.75, 1.5, 2.8, leaf="trim_black", trim="stone", style="glass", glass="bk_dark", casing=0.0)
    tc.door(kit, "S", py0, 0.75, 1.5, 2.8, leaf="trim_black", trim="stone", style="glass", glass="bk_dark", casing=0.0)
    tc.glazing(kit, "S", py0, -1.2, 1.2, sh + 1.0, sh + 3.4, cell="dh_blind", mullions=[0.0], depth=0.15, frame="trim")
    kit.p("Canopy", "trim_black").box((-4.0, py0 - 3.0, 3.3), (4.0, py0, 3.5))
    for x in (-3.7, 3.7):
        kit.p("CanopyPosts", "trim_black").box((x - 0.1, py0 - 2.9, 0.0), (x + 0.1, py0 - 2.7, 3.3), skip="b")
        kit.collide((x - 0.1, py0 - 2.9, 0), (x + 0.1, py0 - 2.7, 3.3))
    kit.p("CanopyGlow", "glow_white").face([(-3.0, py0 - 2.0, 3.295), (3.0, py0 - 2.0, 3.295), (3.0, py0 - 1.6, 3.295),
                                            (-3.0, py0 - 1.6, 3.295)], toward=(0, 0, -1))
    kit.p("Walk", "concrete").box((-4.2, py0 - 3.2, 0.0), (4.2, py0, 0.02), skip="b")
    kit.collide((x0, y0, 0), (x1, y1, H))
    kit.collide((pav[0], py0, 0), (pav[1], y0, H + 1.2))
    for k in range(3):
        tc.hvac(kit, -12.0 + k * 12.0, 2.0, z=H, w=1.6, d=1.2, h=1.0)
    far = tc.Far(kit.name)
    far.box((x0, y0, 0), (x1, y1, H), "brick_red", top="tar")
    far.box((pav[0], py0, 0), (pav[1], y0, H + 1.2), "brick_red", top="tar")
    for side, plane in (("S", y0), ("N", y1)):
        for s in range(2):
            far.windows(side, plane, [(o[0] + o[1]) / 2 for o in ops[side] if o[2] < sh], s * sh + 1.0, 2.4, 2.6, "glass_dark")
    kit.entrance((0.0, py0 - 0.1, 0.0), "-Y", 3.0, kind="door", note="double doors under the canopy, closed")
    kit.info.update(walk_in=False, storeys=2, footprint=[x0, round(py0 - 3.2, 3), x1, y1])
    return tc.finish(kit, col, root, far)


def build(name, module=None, **overrides):
    module = module or f"town_{name}"
    nm = "Town" + "".join(w.capitalize() for w in module[5:].split("_"))
    col, root, kit = tc.begin(nm, module)
    parts = B[name](kit, col, root, **overrides)
    return root, parts
