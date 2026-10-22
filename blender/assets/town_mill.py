"""The old brick mill, converted: three storeys of dark red brick in bays between pilasters,
segmental-arched windows (brick arches, stone sills), a monitor roof with its clerestory, a
stair tower with a pyramidal cap at the east end; now a brewery taproom on the ground floor
(big new black-framed openings, lit) with a river-side patio under string lights, and lofts
above (lit windows, curtains). +Y = the river side.

Walk-in: the taproom (the west end of the ground floor): a tap wall and bar, long communal
tables and benches, the brewhouse's stainless tanks behind a rail, pendant lights; its light
is baked into COLOR_0. The rest of the ground floor and the lofts are shells.

Origin: floor centre at the street door's sill; front (the street) -Y. Doors:
TownMill_Door_1 (taproom street door), _2 (to the patio).
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

NAME = "TownMill"
P = dict(name=NAME, module="town_mill", x0=-32.0, x1=32.0, y0=-12.0, y1=12.0, storey=4.0, storeys=3, bay=4.0,
         pitch=0.28, tap_x1=-12.0, bake=True)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    x0, x1, y0, y1, T = p["x0"], p["x1"], p["y0"], p["y1"], 0.4
    sh, ns, bw = p["storey"], p["storeys"], p["bay"]
    H = sh * ns
    TX = p["tap_x1"]
    Br = kit.p("Walls", "brick_red")
    kit.tints["Walls"] = (0.78, 0.68, 0.64)
    nb = int((x1 - x0) / bw)
    door_s = (x0 + 2.5 * bw - 0.8, x0 + 2.5 * bw + 0.8, 0.0, 2.8)
    door_n = (x0 + 1.5 * bw - 0.9, x0 + 1.5 * bw + 0.9, 0.0, 2.8)

    def bay_openings(side_is_n):
        ops = []
        for b in range(nb):
            a = x0 + (b + 0.5) * bw
            for s in range(ns):
                if s == 0:
                    if a < TX:                                   # the taproom's big new openings
                        if (side_is_n and abs(a - (door_n[0] + door_n[1]) / 2) < 0.1) or (not side_is_n and abs(a - (door_s[0] + door_s[1]) / 2) < 0.1):
                            continue
                        ops.append((a - 1.4, a + 1.4, 0.4, 3.3))
                    else:
                        ops.append((a - 0.9, a + 0.9, 1.0, 3.0))
                else:
                    ops.append((a - 0.85, a + 0.85, s * sh + 0.9, s * sh + 3.1))
        return ops
    ops_s = bay_openings(False) + [door_s]
    ops_n = bay_openings(True) + [door_n]
    ops_e, ops_w = [], []
    for s in range(ns):
        for a in (-6.0, -2.0, 2.0, 6.0):
            ops_w.append((a - 0.85, a + 0.85, s * sh + 0.9 + (0.0 if s else 0.0), s * sh + 3.1))
            if s:
                ops_e.append((a - 0.85, a + 0.85, s * sh + 0.9, s * sh + 3.1))
    ridge = H + (y1 - y0) / 2 * p["pitch"]
    for side, plane, a0, a1, op in (("S", y0, x0, x1, ops_s), ("N", y1, x0, x1, ops_n), ("E", x1, y0, y1, ops_e), ("W", x0, y0, y1, ops_w)):
        tc.wall(Br, side, plane, a0, a1, 0.0, H, op, gable=ridge if side in "EW" else None)
        tc.reveals(kit.p("Reveals", "brick_red"), side, plane, op, T, sill=True)
        kit.tints["Reveals"] = (0.78, 0.68, 0.64)
        for o in op:
            oa0, oa1, z0, z1 = o
            a = (oa0 + oa1) / 2
            if z0 < 0.1:
                continue
            new = z0 < 1.0 and side in "SN" and a < TX
            if new:
                tc.glazing(kit, side, plane, oa0, oa1, z0, z1, cells=["bk_cafe", "bk_transom"], transom=2.6, mullions=[a], depth=0.15,
                           frame="trim_black")
            else:
                lit = z0 > sh and (int(a * 7 + z0) % 3 != 0)
                cell = ("dh_lamp" if lit else "dh_curtain") if z0 > sh else "bk_dark"
                tc.window(kit, side, plane, a, z0, oa1 - oa0, z1 - z0, cell=cell, trim="trim_black", casing=0.0, depth=0.2)
                # the segmental brick arch over it, the stone sill under it
                Pf, u, nn = tc.frame(side, plane)
                # (a segmental head: a curved band of brick on the face, its soffit in the brick's mean)
                arc = [(oa0 - 0.12 + (oa1 - oa0 + 0.24) * k / 4, z1 + 0.18 * math.sin(math.pi * k / 4)) for k in range(5)]
                kit.p("Arches", "brick_red").face([Pf(a_, z_, 0.03) for a_, z_ in arc] + [Pf(a_, z_ + 0.3, 0.03) for a_, z_ in arc[::-1]],
                                                  toward=nn)
                kit.p("ArchSoffits", "mean:brick_red").face([Pf(oa0 - 0.12, z1, 0.0), Pf(oa1 + 0.12, z1, 0.0), Pf(oa1 + 0.12, z1, 0.03),
                                                              Pf(oa0 - 0.12, z1, 0.03)], toward=(0, 0, -1))
    kit.tints["Arches"] = (0.7, 0.6, 0.56)
    # pilasters between the bays, a corbelled cornice band, floor bands
    for side, plane in (("S", y0), ("N", y1)):
        for b in range(nb + 1):
            a = x0 + b * bw
            a0_, a1_ = max(x0, a - 0.3), min(x1, a + 0.3)
            tc.wbox(kit.p("Pilasters", "mean:brick_red"), side, plane, a0_, a1_, 0.0, H + 0.4, 0, 0.15, skip="back b")
        tc.wbox(kit.p("Cornice", "mean:brick_red"), side, plane, x0, x1, H - 0.4, H, 0, 0.2, skip="back")
        for s in range(1, ns):
            tc.wbox(kit.p("Bands", "stone"), side, plane, x0, x1, s * sh - 0.1, s * sh + 0.05, 0, 0.08, skip="back")
    kit.tints["Pilasters"] = (0.74, 0.64, 0.6)
    kit.tints["Cornice"] = (0.74, 0.64, 0.6)
    # the roof: a low gable with the monitor (clerestory) along the ridge
    tc.gable_roof(kit, x0, x1, y0, y1, H, p["pitch"], axis="x", over_eave=0.5, over_gable=0.3, roof="seam_black", soffit="trim_black",
                  fascia="trim_black", ridge_cap=False)
    mw = 3.0
    mz0 = H + (y1 - y0) / 2 * p["pitch"] - mw * p["pitch"] / 2 + 0.05
    for side, plane in (("S", -mw / 2), ("N", mw / 2)):
        tc.wall(kit.p("Monitor", "bb_charcoal"), side, plane, x0 + 4.0, x1 - 6.0, mz0 - 0.3, mz0 + 1.4)
        for k in range(int((x1 - x0 - 10.0) / 2.0)):
            a = x0 + 5.0 + k * 2.0
            tc.wquad(kit.p("Window", "windows"), side, plane, a - 0.7, a + 0.7, mz0 + 0.2, mz0 + 1.2, 0.02,
                     uvs=tc.cell_uv(tc.WIN["bk_transom"], sub=(0.06, 0.06, 0.94, 0.94)))
    for side, plane in (("E", x1 - 6.0), ("W", x0 + 4.0)):
        tc.wall(kit.p("Monitor", "bb_charcoal"), side, plane, -mw / 2, mw / 2, mz0 - 0.3, mz0 + 1.4)
    tc.gable_roof(kit, x0 + 4.0, x1 - 6.0, -mw / 2, mw / 2, mz0 + 1.4, 0.3, axis="x", over_eave=0.4, over_gable=0.3, roof="seam_black",
                  soffit="trim_black", fascia="trim_black", collide=False)
    kit.collide((x0, y0, 0), (x1, y1, ridge + 2.0))
    # the stair tower at the east end (on the street side), its pyramidal cap
    sx0, sx1, sy0, sy1 = x1 - 8.0, x1 - 3.0, y0 - 2.0, y0
    St = kit.p("Tower", "brick_red")
    kit.tints["Tower"] = (0.74, 0.64, 0.6)
    tz = H + 4.5
    for side, plane, a0, a1 in (("S", sy0, sx0, sx1), ("E", sx1, sy0, sy1), ("W", sx0, sy0, sy1)):
        op = [((a0 + a1) / 2 - 0.5, (a0 + a1) / 2 + 0.5, k * sh + 1.5, k * sh + 3.0) for k in range(ns + 1)] if side == "S" else []
        tc.wall(St, side, plane, a0, a1, 0.0, tz, op)
        for o in op:
            tc.window(kit, side, plane, (o[0] + o[1]) / 2, o[2], 1.0, 1.5, cell="dh_dark", trim="trim_black", casing=0.0, depth=0.2)
    for side, plane, a0, a1 in (("N", y0, sx0, sx1),):
        tc.wall(St, "N", y0 + 0.01, sx0, sx1, H, tz)
    tc.hip_roof(kit, sx0, sx1, sy0, y0 + 0.2, tz, 1.4, over=0.35, roof="seam_black", soffit="trim_black", fascia="trim_black")
    kit.collide((sx0, sy0, 0), (sx1, sy1, tz))

    # ---------------------------------------------------------------- the taproom (walk-in) and the patio
    xi0, yi0, yi1 = x0 + T, y0 + T, y1 - T
    C = sh - 0.3
    kit.sub = 1.5
    tc.room(kit, xi0, TX - 0.1, yi0, yi1, 0.0, C, walls="brick_red", floor="polished", ceiling="deck", name="Taproom", base="trim_black",
            openings={"S": [o for o in ops_s if o[1] < TX and o[2] < 1.0], "N": [o for o in ops_n if o[1] < TX and o[2] < 1.0],
                      "W": [o for o in ops_w if o[2] < sh]})
    kit.sub = None
    kit.tints["TaproomWalls"] = (0.78, 0.68, 0.64)
    tc.wall_collider(kit, "y", TX, y0, y1, 0.2, sh)
    kit.p("TapPartition", "brick_red").face([(TX - 0.1, yi1, 0.0), (TX - 0.1, yi0, 0.0), (TX - 0.1, yi0, C), (TX - 0.1, yi1, C)],
                                            toward=(-1, 0, 0)) if False else None
    for xx in [xi0 + 2.0 + k * 4.0 for k in range(5)]:       # timber beams and columns
        kit.p("Beams", "darkwood").box((xx - 0.18, yi0, C - 0.35), (xx + 0.18, yi1, C), skip="t")
        for yy in (-4.0, 4.0):
            kit.p("Columns", "darkwood").box((xx - 0.15, yy - 0.15, 0.0), (xx + 0.15, yy + 0.15, C - 0.35), skip="bt")
            kit.collide((xx - 0.15, yy - 0.15, 0), (xx + 0.15, yy + 0.15, C))
    # the bar and tap wall along the partition
    bx = TX - 0.1
    kit.p("Bar", "darkwood").box((bx - 3.0, -6.0, 0.0), (bx - 2.3, 4.0, 1.05), skip="bt")
    kit.p("BarTop", "varnish").box((bx - 3.1, -6.1, 1.05), (bx - 2.2, 4.1, 1.1))
    kit.collide((bx - 3.1, -6.1, 0), (bx - 2.2, 4.1, 1.1))
    kit.p("TapWall", "darkwood").box((bx - 0.25, -5.5, 0.0), (bx, 3.5, 2.6), skip="b")
    for k in range(16):
        ty = -5.0 + k * 0.55
        kit.p("Taps", "chrome").box((bx - 0.35, ty - 0.03, 1.3), (bx - 0.25, ty + 0.03, 1.36))
        kit.p("TapHandles", ("paint_orange", "paint_teal", "paint_yellow", "trim_black")[k % 4]).box((bx - 0.33, ty - 0.02, 1.36), (bx - 0.29, ty + 0.02, 1.58))
    kit.p("TapBoard", "trim_black").box((bx - 0.27, -5.5, 1.9), (bx - 0.25, 3.5, 2.5))
    for k in range(16):
        ty = -5.0 + k * 0.55
        kit.p("TapBoard", "paper").box((bx - 0.28, ty - 0.2, 2.0), (bx - 0.27, ty + 0.2, 2.4))
    kit.collide((bx - 0.25, -5.5, 0), (bx, 3.5, 2.6))
    # the brewhouse tanks behind a rail at the north-west corner
    for k, (tx, ty) in enumerate(((xi0 + 1.5, yi1 - 1.5), (xi0 + 3.6, yi1 - 1.5), (xi0 + 5.7, yi1 - 1.5))):
        kit.p("Tanks", "chrome").cyl((tx, ty), 0.85, 0.6, 3.1, sides=12, caps="", r1=0.85)
        kit.p("Tanks", "chrome").cyl((tx, ty), 0.85, 3.1, 3.45, sides=12, caps="t", r1=0.3)
        kit.p("Tanks", "chrome").cyl((tx, ty), 0.85, 0.3, 0.6, sides=12, caps="", r1=0.85) if False else None
        kit.p("Tanks", "chrome").cyl((tx, ty), 0.3, 0.6, 0.6, sides=8)
        for a in (0.4, 2.5, 4.6):
            kit.p("TankLegs", "metal_galv").tube(V(tx + 0.7 * math.cos(a), ty + 0.7 * math.sin(a), 0.0),
                                                 V(tx + 0.7 * math.cos(a), ty + 0.7 * math.sin(a), 0.7), 0.04, 4)
        kit.collide((tx - 0.9, ty - 0.9, 0), (tx + 0.9, ty + 0.9, 3.45))
    tc.railing(kit, (xi0 + 0.2, yi1 - 3.0), (xi0 + 7.0, yi1 - 3.0), 0.0, h=1.0, mat="trim_black", style="bars")
    # communal tables and benches
    for (tx, ty) in ((-26.0, -3.0), (-26.0, 1.5), (-20.0, -3.0), (-20.0, 1.5), (-23.0, -7.5)):
        tc.table(kit, tx, ty, w=3.2, d=0.9, h=0.76, top="varnish", base="trim_black")
        for s in (-1, 1):
            kit.p("Benches", "varnish").box((tx - 1.5, ty + s * 0.75 - 0.18, 0.42), (tx + 1.5, ty + s * 0.75 + 0.18, 0.47))
            for xx in (tx - 1.3, tx + 1.3):
                kit.p("BenchLegs", "trim_black").box((xx - 0.03, ty + s * 0.75 - 0.15, 0.0), (xx + 0.03, ty + s * 0.75 + 0.15, 0.42), skip="tb")
            kit.collide((tx - 1.5, ty + s * 0.75 - 0.18, 0), (tx + 1.5, ty + s * 0.75 + 0.18, 0.47))
        for k in range(3):
            lx = tx - 1.0 + k * 1.0
            kit.p("Pendants", "trim_black").cyl((lx, ty), 0.2, 2.25, 2.45, sides=8, caps="t", r1=0.05)
            kit.p("Pendants", "lamp").cyl((lx, ty), 0.19, 2.245, 2.25, sides=8, caps="b")
            kit.p("Cords", "trim_black").tube(V(lx, ty, 2.45), V(lx, ty, C - 0.35), 0.006, 3)
            kit.light((lx, ty, 2.2), (1.0, 0.7, 0.42), 30, 0.1, kind="SPOT")
    kit.light((bx - 1.5, -1.0, 2.8), (1.0, 0.75, 0.5), 60, 2.5, kind="AREA")
    kit.light((xi0 + 3.6, yi1 - 1.5, 3.4), (0.9, 0.95, 1.0), 40, 2.0, kind="AREA")
    tc.hinged_door(kit, col, root, "S", y0, (door_s[0] + door_s[1]) / 2, 1.6, 2.8, depth=0.2, leaf="trim_black", index=1, style="glass",
                   glass="bk_cafe")
    tc.hinged_door(kit, col, root, "N", y1, (door_n[0] + door_n[1]) / 2, 1.8, 2.8, depth=0.2, leaf="trim_black", index=2, style="glass",
                   glass="bk_cafe")
    tc.sign(kit, "S", y0, (door_s[0] + door_s[1]) / 2, 3.35, 1.6, 0.5, "bar", d=0.02, glow=True) if False else None
    # the patio on the river side: pavers, tables, string lights on poles
    py1 = y1 + 7.0
    kit.p("Patio", "concrete").box((x0, y1, -0.1), (TX + 6.0, py1, 0.0), skip="b")
    kit.collide((x0, y1, -0.1), (TX + 6.0, py1, 0.0))
    for (tx, ty) in ((-28.0, y1 + 2.5), (-23.0, y1 + 2.5), (-18.0, y1 + 2.5), (-28.0, y1 + 5.0), (-23.0, y1 + 5.0), (-13.0, y1 + 4.0)):
        tc.table(kit, tx, ty, w=0.9, h=0.75, round_=True, top="deck", base="trim_black")
        kit.p("Umbrella", "trim_green").cyl((tx, ty), 1.2, 2.2, 2.6, sides=8, caps="", r1=0.05) if (tx + ty) % 2 > 1 else None
    poles = [(x0 + 1.0, y1 + 0.5), (x0 + 1.0, py1 - 0.5), (TX + 5.5, py1 - 0.5), (TX + 5.5, y1 + 0.5)]
    for (px_, py_) in poles:
        kit.p("Poles", "trim_black").cyl((px_, py_), 0.06, 0.0, 3.8, sides=5)
    for (a, b) in ((0, 1), (1, 2), (0, 2), (1, 3)):
        (ax, ay), (bx_, by_) = poles[a], poles[b]
        pts = [V(ax + (bx_ - ax) * t / 12, ay + (by_ - ay) * t / 12, 3.7 - 0.6 * math.sin(math.pi * t / 12)) for t in range(13)]
        kit.p("Cords", "trim_black").polyline(pts, 0.006, sides=3)
        for q in pts[1:-1:2]:
            kit.p("Festoon", "lamp").cyl((q.x, q.y), 0.035, q.z - 0.1, q.z - 0.02, sides=5, caps="tb")

    far = tc.Far(n)
    far.gable(x0, x1, y0, y1, 0.0, H, ridge, axis="x", wall="brick_red", roof="seam_black", over=0.5)
    far.box((x0 + 4.0, -mw / 2, mz0 - 0.3), (x1 - 6.0, mw / 2, mz0 + 1.6), "bb_charcoal", top="seam_black")
    far.box((sx0, sy0, 0), (sx1, sy1, tz + 1.2), "brick_red", top="seam_black")
    for side, plane in (("S", y0), ("N", y1)):
        for s in range(ns):
            far.windows(side, plane, [x0 + (b + 0.5) * bw for b in range(nb)], s * sh + 1.0, 1.7, 2.1,
                        "window_lit" if s else "glass_dark")
    kit.entrance(((door_s[0] + door_s[1]) / 2, y0 - 0.1, 0.0), "-Y", 1.6, kind="door", note="TownMill_Door_1, the taproom")
    kit.entrance(((door_n[0] + door_n[1]) / 2, y1 + 0.1, 0.0), "+Y", 1.8, kind="door", note="TownMill_Door_2, to the patio")
    kit.info.update(walk_in=True, storeys=ns, rooms=[f"taproom {round(TX - xi0, 1)} x {round(yi1 - yi0, 1)} (bar, tap wall, tanks, tables)"],
                    footprint=[round(x0 - 0.5, 3), round(sy0 - 0.35, 3), round(x1 + 0.5, 3), round(py1, 3)])
    parts = tc.finish(kit, col, root, far)
    if p["bake"]:
        meshes = [o for o in root.children_recursive if o.type == "MESH" and not o.name.endswith("_LOD1")]
        town_light.bake(kit, root, meshes, [(xi0, yi0, 0.0, TX - 0.1, yi1, C)])
    return root, parts
