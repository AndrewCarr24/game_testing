"""Houses of the town kit (solid shells): one parametric frame house, exported as
  cottage_a/b/c  the mill-hill cottages restored as vacation rentals: the same four-room house
                 in a row (only the paint changes: mint, sky blue, butter), a hip roof, a central
                 chimney, a front porch on posts, brick piers (below_m 0.9, build(below=...)), a
                 back deck with a covered hot tub, a key lockbox by every door
  house_a        Church Street: a restored Victorian (two storeys, a cross gable with scrolled
                 gable trim, a wraparound porch, a bay)
  house_b        Church Street: a foursquare (two storeys, hip roof, a hipped dormer, a full
                 porch on brick piers), in brick
  house_c        Church Street: a craftsman bungalow (a low side gable with deep bracketed
                 eaves, a gabled porch on tapered columns over fieldstone piers, cedar shakes)
Origin: floor centre at the front door's sill (the porch floor is a step lower); front -Y.
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import town_common as tc  # noqa: E402

importlib.reload(tc.tt)
importlib.reload(tc)
V = tc.V

P = dict(name="TownHouse", module="town_house", w=7.2, d=7.6, storeys=1, storey_h=2.9, roof="hip", pitch=0.75,
         siding="lap_white", tint=(1.0, 1.0, 1.0), trim="trim", roof_surf="seam_black", porch=2.1, wrap=False,
         post="square", post_mat="trim", foundation="piers", below=0.9, base="brick_red", deck=True, hot_tub=False,
         lockbox=False, chimney="brick_red", dormer=False, bay=False, gable_trim=False, eave=0.35, door="door_wood",
         windows=2, cells=("dh_curtain", "dh_blind", "dh_lace", "dh_dark"), porch_roof_gable=False)

VARIANTS = {
    "cottage_a": dict(name="TownCottageA", module="town_cottage_a", tint=(0.74, 0.92, 0.82), hot_tub=True, lockbox=True,
                      roof_surf="seam_black", door="door_green"),
    "cottage_b": dict(name="TownCottageB", module="town_cottage_b", tint=(0.76, 0.86, 0.98), hot_tub=True, lockbox=True,
                      roof_surf="seam_black", door="door_red"),
    "cottage_c": dict(name="TownCottageC", module="town_cottage_c", tint=(1.0, 0.92, 0.70), hot_tub=True, lockbox=True,
                      roof_surf="seam_black", door="door_wood"),
    "house_a": dict(name="TownHouseA", module="town_house_a", w=8.0, d=9.0, storeys=2, roof="cross", pitch=1.0, siding="lap_cream",
                    tint=(0.95, 0.95, 0.9), trim="trim", roof_surf="shingle", wrap=True, porch=2.4, foundation="brick", below=0.6,
                    deck=False, gable_trim=True, bay=True, door="door_red", post="turned"),
    "house_b": dict(name="TownHouseB", module="town_house_b", w=8.6, d=8.6, storeys=2, roof="hip", pitch=0.6, siding="brick_red",
                    tint=(0.92, 0.86, 0.82), trim="trim", roof_surf="shingle", porch=2.6, foundation="brick", below=0.6,
                    deck=False, dormer=True, post="column", post_mat="trim", door="door_green", base="brick_red"),
    "house_c": dict(name="TownHouseC", module="town_house_c", w=9.6, d=10.0, storeys=1, storey_h=3.0, roof="gable_x", pitch=0.5,
                    siding="cedar", tint=(1.0, 1.0, 1.0), trim="trim_green", roof_surf="shingle", porch=2.6, foundation="stone",
                    below=0.6, base="fieldstone", deck=False, eave=0.8, post="tapered", post_mat="trim_green", door="door_wood",
                    porch_roof_gable=True, chimney="fieldstone"),
}


def build(**overrides):
    variant = overrides.pop("variant", None)
    p = {**P, **(VARIANTS.get(variant, {}) if variant else {}), **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    w, d = p["w"], p["d"]
    x0, x1, y0, y1 = -w / 2, w / 2, -d / 2, d / 2
    sh, ns = p["storey_h"], p["storeys"]
    H = sh * ns + 0.15
    below = p["below"]
    trim = p["trim"]
    Wl = kit.p("Walls", p["siding"])
    kit.tints["Walls"] = p["tint"]

    # ---------------------------------------------------------------- foundation
    if p["foundation"] == "piers":
        tc.piers(kit, x0, x1, y0, y1, 0.0, spacing=2.4, size=0.36, mat=p["base"], skirt=None) if False else None
        B = kit.p("Piers", p["base"])
        for i in range(4):
            for j in range(4):
                if i in (0, 3) or j in (0, 3):
                    cx = x0 + 0.18 + (w - 0.36) * i / 3
                    cy = y0 + 0.18 + (d - 0.36) * j / 3
                    B.box((cx - 0.18, cy - 0.18, -below), (cx + 0.18, cy + 0.18, -0.12), skip="b")
        Lt = kit.p("Skirt", "lattice") if False else kit.p("Skirt", "shade")
        for side, plane, a0, a1 in (("S", y0 + 0.3, x0, x1), ("N", y1 - 0.3, x0, x1), ("E", x1 - 0.3, y0, y1), ("W", x0 + 0.3, y0, y1)):
            tc.wall(Lt, side, plane, a0 + 0.3, a1 - 0.3, -below, -0.12)
        kit.p("Sill", trim).box((x0 - 0.03, y0 - 0.03, -0.3), (x1 + 0.03, y1 + 0.03, -0.12), skip="")
    else:
        tc.wall(kit.p("Foundation", p["base"]), "S", y0, x0, x1, -below, 0.25)
        for side, plane, a0, a1 in (("N", y1, x0, x1), ("E", x1, y0, y1), ("W", x0, y0, y1)):
            tc.wall(kit.p("Foundation", p["base"]), side, plane, a0, a1, -below, 0.25)
    kit.collide((x0, y0, -below), (x1, y1, H))

    # ---------------------------------------------------------------- walls, windows, door
    dw = 0.95
    door = (-dw / 2 - (0.9 if p["bay"] else 0.0), dw / 2 - (0.9 if p["bay"] else 0.0), 0.0, 2.15)
    dc = (door[0] + door[1]) / 2
    ops = {"S": [door], "N": [(x1 - 2.0, x1 - 1.1, 0.0, 2.1)], "E": [], "W": []}
    cells = p["cells"]
    ci = 0
    for s in range(ns):
        zb = s * sh + 0.85
        for side, plane, a0, a1 in (("S", y0, x0, x1), ("N", y1, x0, x1), ("E", x1, y0, y1), ("W", x0, y0, y1)):
            L = a1 - a0
            k = p["windows"]
            for i in range(k):
                a = a0 + L * (i + 0.5) / k
                if side == "S" and s == 0:
                    a = (x0 + door[0]) / 2 if i == 0 else (door[1] + x1) / 2
                    if p["bay"] and i == 1:
                        continue
                if side == "N" and s == 0 and i == k - 1:
                    a = a0 + L * 0.35
                ops[side].append((a - 0.42, a + 0.42, zb, zb + 1.5))
    walls_top = H
    gables = {}
    ridge = None
    if p["roof"] == "gable_x":
        ridge = H + d / 2 * p["pitch"]
        gables = {"E": ridge, "W": ridge}
    for side, plane, a0, a1 in (("S", y0, x0, x1), ("N", y1, x0, x1), ("E", x1, y0, y1), ("W", x0, y0, y1)):
        tc.wall(Wl, side, plane, a0, a1, -0.12 if p["foundation"] == "piers" else 0.25, walls_top, ops[side], gable=gables.get(side))
        for o in ops[side]:
            if o[2] > 0.1:
                tc.window(kit, side, plane, (o[0] + o[1]) / 2, o[2], o[1] - o[0], o[3] - o[2], cell=cells[ci % len(cells)],
                          trim=trim, casing=0.09, wall_part=Wl)
                ci += 1
    tc.door(kit, "S", y0, dc, dw, 2.15, leaf=p["door"], trim=trim, wall_part=Wl, glass="dh_lace")
    tc.door(kit, "N", y1, x1 - 1.55, 0.9, 2.1, leaf=p["door"], trim=trim, wall_part=Wl, glass="dh_blind")
    if p["siding"] != "brick_red":
        tc.corner_boards(kit, x0, x1, y0, y1, -0.12 if p["foundation"] == "piers" else 0.25, H, mat=trim)
    if ns > 1:
        tc.band(kit, x0, x1, y0, y1, sh - 0.05, sh + 0.12, mat=trim)
    tc.meter(kit, "E", x1, y1 - 1.5, z=1.4)
    if p["lockbox"]:                                      # the key lockbox by the door
        tc.wbox(kit.p("Lockbox", "trim_black"), "S", y0, door[1] + 0.25, door[1] + 0.42, 1.25, 1.5, 0.0, 0.07, skip="back")
        tc.wbox(kit.p("Lockbox", "neon_green"), "S", y0, door[1] + 0.3, door[1] + 0.33, 1.44, 1.46, 0.07, 0.072)
        tc.wbox(kit.p("Lockbox", "trim_black"), "N", y1, x1 - 1.0 + 0.0, x1 - 0.83, 1.25, 1.5, 0.0, 0.07, skip="back")

    # ---------------------------------------------------------------- roof
    if p["roof"] == "hip":
        rz = tc.hip_roof(kit, x0, x1, y0, y1, H, p["pitch"], over=p["eave"], roof=p["roof_surf"], soffit=trim, fascia=trim)
    elif p["roof"] == "gable_x":
        rz = tc.gable_roof(kit, x0, x1, y0, y1, H, p["pitch"], axis="x", over_eave=p["eave"], over_gable=p["eave"] * 0.8,
                           roof=p["roof_surf"], soffit=trim, fascia=trim)
        for side, plane in (("E", x1), ("W", x0)):              # bracketed eaves
            Pf, u, nn = tc.frame(side, plane)
            for a in (y0 + 0.4, 0.0, y1 - 0.4):
                kit.p("Brackets", trim).beam(Pf(a, H - 0.7, 0.0), Pf(a, ridge - (abs(a) + p["eave"]) * p["pitch"] - 0.1, p["eave"] * 0.7),
                                             0.12, 0.12, up=V(0, 0, 1))
    else:                                                       # cross: a side gable + a front gable
        rz = tc.gable_roof(kit, x0, x1, y0, y1, H, p["pitch"], axis="x", over_eave=p["eave"], over_gable=0.25,
                           roof=p["roof_surf"], soffit=trim, fascia=trim)
        fw = w * 0.5
        fx0, fx1 = x1 - fw - 0.3, x1 - 0.3
        fr = H + fw / 2 * p["pitch"]
        tc.wall(Wl, "S", y0 - 0.01, fx0, fx1, H, H, gable=fr)
        tc.gable_roof(kit, fx0, fx1, y0 - 0.01, 0.0, H, p["pitch"], axis="y", over_eave=0.25, over_gable=0.3,
                      roof=p["roof_surf"], soffit=trim, fascia=trim, collide=False)
        for side, plane in (("E", x1), ("W", x0)):
            tc.wall(Wl, side, plane, y0, y1, H, H, gable=H + d / 2 * p["pitch"], d=0.0)
        tc.wall(Wl, "N", y1, x0, x1, H, H)
        if p["gable_trim"]:                                     # scrolled gable trim: a sunburst of boards
            cxg = (fx0 + fx1) / 2
            for k in range(7):
                ang = math.pi * (k + 0.5) / 7
                kit.p("GableTrim", trim).beam(V(cxg, y0 - 0.35, H + 0.3), V(cxg + 0.9 * math.cos(ang), y0 - 0.35, H + 0.3 + 0.7 * math.sin(ang)),
                                              0.05, 0.03)
        rz = max(rz, fr)
    if p["dormer"]:
        dx0, dx1 = -1.0, 1.0
        dzb = H + 0.5
        kit.p("Dormer", p["siding"]).box((dx0, y0 + 0.8, dzb - 0.4), (dx1, y0 + 2.0, dzb + 1.2), skip="b")
        kit.tints["Dormer"] = p["tint"]
        tc.window(kit, "S", y0 + 0.8, 0.0, dzb + 0.1, 1.2, 0.8, cell="dh_dark", trim=trim, casing=0.06)
        tc.hip_roof(kit, dx0, dx1, y0 + 0.8, y0 + 2.0, dzb + 1.2, 0.6, over=0.25, roof=p["roof_surf"], soffit=trim, fascia=trim,
                    collide=False)
    if p["chimney"]:
        tc.chimney(kit, 0.4 if p["roof"] == "hip" else x0 + 1.2, 0.3, H - 0.5, rz + 0.7, w=0.6, d=0.5, mat=p["chimney"])

    # ---------------------------------------------------------------- porch, steps, deck
    pd = p["porch"]
    pz = -0.18                                                  # the porch floor, a step below the door sill
    pts = tc.porch(kit, x0 - (0.0 if not p["wrap"] else 0.0), x1, y0, pd, pz, H - 0.25 if ns == 1 else sh - 0.1, posts=4,
                   roof=p["roof_surf"], rail=True, steps_at=dc, step_w=1.3, deck="deck", trim=trim, post_mat=p["post_mat"],
                   rail_style="bars", rail_mat=trim)
    xs, y_out = pts
    # the steps from the porch down to the ground (below the pad)
    nsteps = max(1, round((below + pz) / 0.18))
    tc.steps(kit, dc - 0.65, dc + 0.65, y_out, pz, n=nsteps, run=0.28, mat="deck", z_bottom=-below)
    kit.p("PorchUnder", "shade").face([(x0, y_out, -below), (x1, y_out, -below), (x1, y_out, pz - 0.3), (x0, y_out, pz - 0.3)],
                                      toward=(0, -1, 0))
    if p["post"] in ("tapered", "column", "turned"):            # dress the posts
        for x in xs:
            if p["post"] == "tapered":
                kit.p("PostPiers", p["base"]).box((x - 0.25, y_out + 0.0, pz), (x + 0.25, y_out + 0.36, pz + 1.0), skip="b")
                kit.p("PostTaper", p["post_mat"]).cyl((x, y_out + 0.18), 0.2, pz + 1.0, H - 0.5, sides=4, caps="", r1=0.12)
            elif p["post"] == "column":
                kit.p("PostPiers", p["base"]).box((x - 0.25, y_out + 0.0, pz), (x + 0.25, y_out + 0.36, pz + 0.9), skip="b")
                kit.p("PostTaper", "paint_white").cyl((x, y_out + 0.18), 0.14, pz + 0.9, sh - 0.3, sides=8, caps="")
            else:
                for zz in (0.9, 1.6, 2.2):
                    kit.p("PostTaper", p["post_mat"]).cyl((x, y_out + 0.15), 0.1, pz + zz, pz + zz + 0.12, sides=6, caps="")
    if p["porch_roof_gable"]:
        tc.gable_roof(kit, dc - 1.6, dc + 1.6, y_out - 0.1, y0, H - 0.25, 0.5, axis="y", over_eave=0.3, over_gable=0.25,
                      roof=p["roof_surf"], soffit=trim, fascia=trim, collide=False)
    if p["wrap"]:                                               # the side porch round the east corner
        kit.p("Deck", "deck").box((x1, y_out, pz - 0.06), (x1 + pd, y1 - 2.0, pz), skip="b")
        kit.collide((x1, y_out, -below), (x1 + pd, y1 - 2.0, pz))
        tc.shed_roof(kit, x1, x1 + pd, y_out, y1 - 2.0, sh - 0.1, sh - 0.6, roof=p["roof_surf"], soffit=trim, fascia=trim) if False else None
        R = kit.p("Roof", p["roof_surf"])
        R.face([(x1, y_out - 0.2, sh), (x1 + pd + 0.2, y_out - 0.2, sh - 0.55), (x1 + pd + 0.2, y1 - 1.8, sh - 0.55), (x1, y1 - 1.8, sh)],
               toward=(1, 0, 1))
        kit.p("Soffit", trim).face([(x1, y_out - 0.2, sh - 0.1), (x1 + pd + 0.2, y_out - 0.2, sh - 0.65),
                                    (x1 + pd + 0.2, y1 - 1.8, sh - 0.65), (x1, y1 - 1.8, sh - 0.1)], toward=(-1, 0, -1))
        for y in (y_out + 1.6, y_out + 4.0, y1 - 2.2):
            kit.p("Posts", p["post_mat"]).box((x1 + pd - 0.25, y - 0.07, pz), (x1 + pd - 0.11, y + 0.07, sh - 0.65), skip="bt")
        tc.railing(kit, (x1 + pd - 0.18, y_out + 0.3), (x1 + pd - 0.18, y1 - 2.1), pz, mat=trim, style="bars")
    if p["bay"]:                                                # a canted bay on the front, right of the door
        bx0, bx1, bd = 0.6, 2.8, 0.7
        Bv = kit.p("Bay", p["siding"])
        kit.tints["Bay"] = p["tint"]
        Bv.box((bx0, y0 - bd, 0.25), (bx1, y0, sh - 0.2), skip="kb")
        tc.window(kit, "S", y0 - bd, (bx0 + bx1) / 2, 0.85, 1.2, 1.5, cell="dh_lamp", trim=trim, casing=0.08)
        kit.p("BayRoof", p["roof_surf"]).face([(bx0 - 0.1, y0 - bd - 0.1, sh - 0.2), (bx1 + 0.1, y0 - bd - 0.1, sh - 0.2),
                                               (bx1 + 0.1, y0, sh + 0.25), (bx0 - 0.1, y0, sh + 0.25)], toward=(0, -1, 1))
    if p["deck"]:
        dy1 = y1 + 2.6
        kit.p("BackDeck", "deck").box((x0 + 0.6, y1, -0.3), (x1 - 0.6, dy1, -0.24), skip="b")
        kit.collide((x0 + 0.6, y1, -below), (x1 - 0.6, dy1, -0.24))
        for x in (x0 + 0.7, 0.0, x1 - 0.7):
            kit.p("DeckPosts", "deck").box((x - 0.08, dy1 - 0.2, -below), (x + 0.08, dy1 - 0.04, -0.3), skip="bt")
        tc.railing(kit, (x0 + 0.65, dy1 - 0.06), (x1 - 0.65, dy1 - 0.06), -0.24, mat=trim, style="bars")
        tc.railing(kit, (x0 + 0.65, y1 + 0.1), (x0 + 0.65, dy1 - 0.1), -0.24, mat=trim, style="bars")
        if p["hot_tub"]:
            ht = kit.p("HotTub", "darkwood")
            ht.box((x1 - 2.9, y1 + 0.35, -0.24), (x1 - 0.8, dy1 - 0.25, 0.62), skip="b")
            kit.p("HotTubCover", "trim_brown").box((x1 - 2.95, y1 + 0.3, 0.62), (x1 - 0.75, dy1 - 0.2, 0.72))
            kit.collide((x1 - 2.95, y1 + 0.3, -0.24), (x1 - 0.75, dy1 - 0.2, 0.72))
        tc.steps(kit, x0 + 0.8, x0 + 1.9, dy1, -0.24, n=max(1, round((below - 0.24) / 0.18)), run=0.28, direction=1, mat="deck",
                 z_bottom=-below)
    kit.p("PorchLight", "lamp").cyl((dc + 0.8, y0 - 0.1), 0.06, 2.3, 2.45, sides=6)

    far = tc.Far(n)
    if p["roof"] == "hip":
        far.box((x0, y0, -below), (x1, y1, H), p["siding"], skip="b")
        far.hip(x0, x1, y0, y1, H, rz, roof=p["roof_surf"], over=p["eave"])
    else:
        far.gable(x0, x1, y0, y1, -below, H, ridge or (H + d / 2 * p["pitch"]), axis="x", wall=p["siding"], roof=p["roof_surf"],
                  over=p["eave"])
    far.shed(x0, x1, y0, y_out, H - 0.25 if ns == 1 else sh - 0.1, (H - 0.25 if ns == 1 else sh - 0.1) - pd * 0.25, roof=p["roof_surf"])
    far.windows("S", y0, [(x0 + door[0]) / 2, (door[1] + x1) / 2], 0.85, 0.84, 1.5)
    kit.entrance((dc, y_out - nsteps * 0.28, -below), "-Y", dw, kind="door", note="front door, closed (up the porch steps)")
    kit.info.update(variant=variant or "default", walk_in=False, storeys=ns,
                    footprint=[round(x0 - p["eave"], 3), round(y_out - nsteps * 0.28, 3),
                               round(x1 + (pd if p["wrap"] else p["eave"]), 3), round((y1 + 2.6 + 0.28 * 4) if p["deck"] else y1 + p["eave"], 3)])
    parts = tc.finish(kit, col, root, far)
    return root, parts
