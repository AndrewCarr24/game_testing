"""Restored two-storey brick shopfronts (1900-1930, the downtown of Saluda / Dillsboro / Bryson
City, polished): cast-iron pilasters, panelled bulkheads, big display windows under prism
transoms, a recessed entry, a painted sign band with a pictogram and goosenecks, a fabric
awning, two tall windows above with stone lintels and flower boxes, a corbelled cornice and
parapet. Placed shoulder to shoulder: party walls flush at x = +-width/2; back door at +Y.

Variants (build(variant=...); exported as town_shop_<v> by thin modules):
  a     boutique / outdoor gear: red brick, forest-green awning (shell)
  b     coffee: browner brick, burgundy awning, a bench out front; walk-in front room
  c     ice cream / sweets: painted brick (pale pink), striped awning (shell)
  d     the bank branch: dark brick, stone pilasters and cornice, no awning, an ATM; walk-in
  wide  16 m double front, outfitter / fly shop: navy awnings (shell)
  realty 16 m double front, the real-estate office: photo boards of estates in the windows
        (blank photo rectangles); walk-in front room
Origin: floor centre at the door sill; front -Y.
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

NAME = "TownShop"
P = dict(name=NAME, module="town_shop", width=8.0, depth=18.0, height=9.0, brick="brick_red", tint=(1.0, 1.0, 1.0),
         iron="trim_green", awning=("trim_green",), sign="outfitter", glass="bk_display", walk_in=False, kind="shop",
         stone_trim=False, bench=False, bays=1, bake=True)

VARIANTS = {
    "a": dict(name="TownShopA", module="town_shop_a", iron="trim_green", awning=("trim_green",), sign="outfitter", glass="bk_display"),
    "b": dict(name="TownShopB", module="town_shop_b", tint=(0.86, 0.78, 0.72), iron="trim_black", awning=("trim_red",),
              sign="cafe", glass="bk_cafe", walk_in=True, kind="coffee", bench=True),
    "c": dict(name="TownShopC", module="town_shop_c", brick="brick_white", tint=(1.0, 0.86, 0.84), iron="paint_white",
              awning=("paint_white", "trim_red"), sign="cafe", glass="bk_shop"),
    "d": dict(name="TownShopD", module="town_shop_d", tint=(0.72, 0.66, 0.64), iron="stone", awning=(), sign="museum",
              glass="bk_office", walk_in=True, kind="bank", stone_trim=True),
    "wide": dict(name="TownShopWide", module="town_shop_wide", width=16.0, bays=2, awning=("fabric_blue",), iron="trim_black",
                 sign="outfitter", glass="bk_display"),
    "realty": dict(name="TownShopRealty", module="town_shop_realty", width=16.0, bays=2, awning=("trim_green",),
                   iron="trim_black", sign="museum", glass="bk_dark", walk_in=True, kind="realty", tint=(0.92, 0.9, 0.86)),
}


def storefront(kit, col, root, p, ox, bw, y0, door_index):
    """One storefront bay centred at x = ox, bw wide, on the front wall at y = y0."""
    iron = p["iron"]
    I = kit.p("Iron", iron)
    zt = 3.4
    for x in (ox - bw / 2, ox + bw / 2):
        a0, a1 = (x, x + 0.4) if x < ox else (x - 0.4, x)
        tc.wbox(I, "S", y0, a0, a1, 0.0, 3.75, 0, 0.1, skip="back")
        tc.wbox(I, "S", y0, a0 - 0.05, a1 + 0.05, 0.0, 0.35, 0, 0.14, skip="back")
    tc.wbox(I, "S", y0, ox - bw / 2, ox + bw / 2, zt, 3.75, 0, 0.12, skip="back")
    gx0, gx1 = ox - bw / 2 + 0.4, ox + bw / 2 - 0.4
    dw, rec = 1.1, 1.2
    ex0, ex1 = ox - 0.85, ox + 0.85
    # bulkheads (panelled), display windows, prism transoms
    B = kit.p("Bulkheads", iron)
    for a0, a1 in ((gx0, ex0), (ex1, gx1)):
        tc.wbox(B, "S", y0, a0, a1, 0.0, 0.55, -0.15, 0.0, skip="back")
        n = max(1, round((a1 - a0) / 0.9))
        for k in range(n):
            pa = a0 + (a1 - a0) * k / n
            tc.wbox(B, "S", y0, pa + 0.08, pa + (a1 - a0) / n - 0.08, 0.1, 0.45, 0.0, 0.02, skip="back")
        tc.glazing(kit, "S", y0, a0, a1, 0.55, 2.9, cells=[p["glass"]], mullions=[(a0 + a1) / 2] if a1 - a0 > 2.5 else [],
                   depth=0.15, frame=iron)
        tc.glazing(kit, "S", y0, a0, a1, 2.95, zt, cell="bk_transom", mullions=[a0 + (a1 - a0) * k / 4 for k in (1, 2, 3)],
                   depth=0.12, frame=iron)
        kit.collide((a0, y0, 0), (a1, y0 + 0.2, zt))
        if p["kind"] == "realty":                   # photo boards of estates for sale (blank rectangles)
            for k in range(3):
                for j in range(2):
                    px0 = a0 + 0.25 + k * (a1 - a0 - 0.5) / 3
                    tc.wquad(kit.p("Photos", "paper"), "S", y0, px0, px0 + (a1 - a0 - 0.5) / 3 - 0.12, 1.0 + j * 0.85,
                             1.65 + j * 0.85, -0.12)
                    tc.wquad(kit.p("Photos", ("fieldstone", "seam_black", "bb_charcoal")[k]), "S", y0, px0 + 0.05,
                             px0 + (a1 - a0 - 0.5) / 3 - 0.17, 1.2 + j * 0.85, 1.6 + j * 0.85, -0.118)
    # the recessed entry: side glazing, a tiled floor, the door and its transom at the back
    yr = y0 + rec
    for x, side in ((ex0, "E"), (ex1, "W")):
        a0, a1 = (y0, yr) if side == "E" else (y0, yr)
        tc.glazing(kit, side, x, a0, a1, 0.55, 2.9, cell=p["glass"], depth=0.0, frame=iron)
        tc.wbox(B, side, x, a0, a1, 0.0, 0.55, 0.0, 0.05, skip="back")
        kit.collide((x - 0.06, y0, 0), (x + 0.06, yr, zt))
    kit.p("Entry", "checker").face([(ex0, y0, 0.002), (ex1, y0, 0.002), (ex1, yr, 0.002), (ex0, yr, 0.002)], toward=(0, 0, 1))
    kit.p("EntrySoffit", iron).face([(ex0, y0, zt), (ex1, y0, zt), (ex1, yr, zt), (ex0, yr, zt)], toward=(0, 0, -1))
    kit.p("EntrySoffit", iron).face([(ex0, yr, 2.45), (ex1, yr, 2.45), (ex1, yr, zt), (ex0, yr, zt)], toward=(0, -1, 0))
    for x, side in ((ex0, "W"), (ex1, "E")):
        kit.p("EntrySoffit", iron).face([(x, y0, 2.9), (x, yr, 2.9), (x, yr, zt), (x, y0, zt)], toward=(1 if side == "W" else -1, 0, 0))
    tc.glazing(kit, "S", yr, ex0, ex1, 2.45, 2.9, cell="bk_transom", depth=0.0, frame=iron)
    if p["walk_in"]:
        tc.hinged_door(kit, col, root, "S", yr, ox - 0.4 + dw / 2 - 0.15, dw, 2.4, depth=0.0, leaf=iron, index=door_index,
                       style="glass", glass=p["glass"])
        lo = ox - 0.4 + 0.1 - 0.15
        kit.collide((ex0, yr - 0.1, 0), (lo, yr + 0.1, 2.45))
        kit.collide((lo + dw, yr - 0.1, 0), (ex1, yr + 0.1, 2.45))
    else:
        tc.wbox(kit.p("EntryWall", iron), "S", yr, ex0, ex1, 0.0, 2.45, -0.05, 0.0, skip="back")
        tc.door(kit, "S", yr, ox, dw, 2.4, leaf=iron, trim=iron, style="glass", glass=p["glass"], casing=0.0, depth=0.0)
        kit.collide((ex0, yr - 0.1, 0), (ex1, yr + 0.1, 2.45))
    kit.entrance((ox, y0 - 0.1, 0.0), "-Y", dw, kind="door",
                 note=(f"{kit.name}_Door_{door_index}, recessed 1.2 m" if p["walk_in"] else "closed, recessed 1.2 m"))
    # the sign band, goosenecks, the awning
    sw = min(3.0, bw - 1.6)
    tc.wbox(kit.p("SignBand", iron), "S", y0, ox - bw / 2 + 0.4, ox + bw / 2 - 0.4, 3.75, 4.55, 0, 0.06, skip="back")
    tc.sign(kit, "S", y0, ox, 3.85, sw, 0.6, p["sign"], d=0.06, frame=iron, thick=0.02)
    for a in (ox - sw / 2 + 0.3, ox + sw / 2 - 0.3):
        tc.gooseneck(kit, "S", y0, a, 4.85, arm=0.5)
    if p["awning"]:
        A = p["awning"]
        ax0, ax1 = ox - bw / 2 + 0.35, ox + bw / 2 - 0.35
        z_w, z_o, out = 3.62, 2.95, 1.5
        nst = 1 if len(A) == 1 else 14
        for k in range(nst):
            a0 = ax0 + (ax1 - ax0) * k / nst
            a1 = ax0 + (ax1 - ax0) * (k + 1) / nst
            Fb = kit.p("Awning", A[k % len(A)])
            Fb.face([(a0, y0 - 0.1, z_w), (a1, y0 - 0.1, z_w), (a1, y0 - out, z_o), (a0, y0 - out, z_o)], toward=(0, -0.4, 1))
            Fb.face([(a0, y0 - 0.1, z_w - 0.01), (a1, y0 - 0.1, z_w - 0.01), (a1, y0 - out, z_o - 0.01), (a0, y0 - out, z_o - 0.01)],
                    toward=(0, 0.4, -1))
            Fb.face([(a0, y0 - out, z_o - 0.28), (a1, y0 - out, z_o - 0.28), (a1, y0 - out, z_o), (a0, y0 - out, z_o)], toward=(0, -1, 0))
            Fb.face([(a0, y0 - out + 0.005, z_o - 0.28), (a1, y0 - out + 0.005, z_o - 0.28), (a1, y0 - out + 0.005, z_o),
                     (a0, y0 - out + 0.005, z_o)], toward=(0, 1, 0))
        for x in (ax0 + 0.1, ax1 - 0.1):
            kit.p("AwningArms", "trim_black").beam(V(x, y0, 2.6), V(x, y0 - out, z_o - 0.02), 0.03, 0.03)
            kit.p("AwningArms", "trim_black").beam(V(x, y0, z_w), V(x, y0 - out, z_o), 0.02, 0.02)
    return gx0, gx1


def build(**overrides):
    variant = overrides.pop("variant", None)
    p = {**P, **(VARIANTS.get(variant, {}) if variant else {}), **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    W, D, Ht = p["width"], p["depth"], p["height"]
    x0, x1, y0, y1, T = -W / 2, W / 2, -D / 2, D / 2, 0.25
    roof_z = Ht - 0.7
    bays = p["bays"]
    bw = W / bays
    Br = kit.p("Walls", p["brick"])
    kit.tints["Walls"] = p["tint"]
    # front wall: storefronts below, two (or four) tall windows above
    up = []
    for b in range(bays):
        ox = x0 + bw * (b + 0.5)
        for a in (ox - bw * 0.22, ox + bw * 0.22):
            up.append((a - 0.55, a + 0.55, 5.1, 7.1))
    sf = [(x0 + bw * b + 0.0, x0 + bw * (b + 1) - 0.0, 0.0, 3.75) for b in range(bays)]
    tc.wall(Br, "S", y0, x0, x1, 0.0, Ht, sf + up)
    for b in range(bays):
        storefront(kit, col, root, p, x0 + bw * (b + 0.5), bw, y0, b + 1)
    St = "stone" if not p["stone_trim"] else "polished"
    for a0, a1, z0, z1 in up:
        a = (a0 + a1) / 2
        tc.window(kit, "S", y0, a, z0, a1 - a0, z1 - z0, cell="dh_blind" if (a0 * 7) % 2 > 1 else "dh_lace", trim="trim",
                  casing=0.0, wall_part=Br, sill=False, depth=0.14)
        tc.wbox(kit.p("Lintels", St), "S", y0, a0 - 0.12, a1 + 0.12, z1, z1 + 0.28, 0, 0.05, skip="back")
        tc.wbox(kit.p("Lintels", St), "S", y0, a0 - 0.08, a1 + 0.08, z0 - 0.12, z0, -0.14, 0.07, skip="back")
        # flower boxes, too tidy
        tc.wbox(kit.p("FlowerBoxes", "trim_black"), "S", y0, a0 - 0.05, a1 + 0.05, z0 - 0.4, z0 - 0.13, 0.07, 0.3, skip="back")
        for k in range(5):
            fa = a0 + 0.05 + k * (a1 - a0) / 5
            colr = ("paint_red", "paint_white", "neon_pink", "paint_red", "trim_green")[k] if False else (
                "door_red", "paint_white", "trim_red", "paint_yellow", "trim_green")[k]
            tc.wbox(kit.p("Flowers", colr), "S", y0, fa, fa + (a1 - a0) / 5 - 0.02, z0 - 0.13, z0 - 0.02, 0.09, 0.28)
    # the cornice: a corbel table, a projecting cornice, the parapet cap
    Co = kit.p("Cornice", p["brick"] if not p["stone_trim"] else "polished")
    if not p["stone_trim"]:
        kit.tints["Cornice"] = p["tint"]
    tc.wbox(Co, "S", y0, x0, x1, 7.7, 7.85, 0, 0.06, skip="back")
    k = int(W / 0.4)
    for i in range(k):
        a = x0 + 0.2 + i * (W - 0.4) / (k - 1)
        tc.wbox(Co, "S", y0, a - 0.1, a + 0.1, 7.85, 8.15, 0, 0.12, skip="back")
    tc.wbox(Co, "S", y0, x0, x1, 8.15, 8.4, 0, 0.18, skip="back")
    tc.wbox(kit.p("Coping", St), "S", y0, x0 - 0.02, x1 + 0.02, Ht - 0.12, Ht, -0.25, 0.08, skip="back")
    if p["stone_trim"]:
        for x in (x0 + 0.05, x1 - 0.05):
            tc.wbox(kit.p("Pilasters", "polished"), "S", y0, x - 0.35, x + 0.35, 3.75, Ht - 0.1, 0, 0.1, skip="back")
    # sides (party walls), back, roof
    for side, plane in (("E", x1), ("W", x0)):
        tc.wall(Br, side, plane, y0, y1, 0.0, Ht)
    back_op = [(x1 - 2.0, x1 - 1.0, 0.0, 2.2), (x0 + 1.0, x0 + 2.2, 1.2, 2.4), (x0 + 1.0, x0 + 2.2, 5.0, 6.6),
               (x1 - 2.2, x1 - 1.0, 5.0, 6.6)]
    tc.wall(Br, "N", y1, x0, x1, 0.0, Ht - 0.4, back_op)
    tc.door(kit, "N", y1, x1 - 1.5, 1.0, 2.2, leaf="metal_galv", trim="stone", wall_part=Br, casing=0.06)
    for a0, a1, z0, z1 in back_op[1:]:
        tc.window(kit, "N", y1, (a0 + a1) / 2, z0, a1 - a0, z1 - z0, cell="dh_blind_low", trim="trim", casing=0.0,
                  wall_part=Br, depth=0.14)
    kit.p("RoofDeck", "tar").face([(x0 + T, y0 + T, roof_z), (x1 - T, y0 + T, roof_z), (x1 - T, y1 - T, roof_z),
                                   (x0 + T, y1 - T, roof_z)], toward=(0, 0, 1))
    for side, plane, a0, a1, zt in (("S", y0 + T, x0 + T, x1 - T, Ht), ("N", y1 - T, x0 + T, x1 - T, Ht - 0.4),
                                    ("E", x1 - T, y0 + T, y1 - T, Ht), ("W", x0 + T, y0 + T, y1 - T, Ht)):
        tc.wall(kit.p("ParapetIn", "brick_red"), side, plane, a0, a1, roof_z, zt, inward=True)
    for side, plane, a0, a1, zt in (("E", x1, y0, y1, Ht), ("W", x0, y0, y1, Ht), ("N", y1, x0, x1, Ht - 0.4)):
        tc.wbox(kit.p("Coping", St), side, plane, a0, a1, zt, zt + 0.06, -T, 0.03)
    kit.p("RoofDeck", "tar").face([(x0, y0, Ht), (x1, y0, Ht), (x1, y0 + 0.01, Ht), (x0, y0 + 0.01, Ht)], toward=(0, 0, 1))
    tc.hvac(kit, 0.0, y1 - 3.0, z=roof_z, w=1.2, d=1.0, h=0.9)
    tc.meter(kit, "N", y1, x0 + 3.2)
    kit.collide((x0, y0 + 1.2 if p["walk_in"] else y0, 0), (x1, y1, Ht))      # (walk-ins: replaced below)
    if p["bench"]:
        Bn = kit.p("Bench", "varnish")
        Bn.box((x0 + 0.6, y0 - 1.0, 0.42), (x0 + 2.4, y0 - 0.6, 0.47))
        Bn.box((x0 + 0.6, y0 - 0.65, 0.47), (x0 + 2.4, y0 - 0.6, 0.85))
        for x in (x0 + 0.7, x0 + 2.3):
            kit.p("BenchLegs", "trim_black").box((x - 0.03, y0 - 1.0, 0.0), (x + 0.03, y0 - 0.6, 0.47), skip="b")
        kit.collide((x0 + 0.6, y0 - 1.0, 0), (x0 + 2.4, y0 - 0.6, 0.85))

    # ---------------------------------------------------------------- the walk-in front room
    if p["walk_in"]:
        kit.colliders.pop()
        ry0, ry1 = y0 + T, y0 + 8.0
        C = 3.6
        kit.sub = 0.8
        tc.room(kit, x0 + T, x1 - T, ry0, ry1, 0.0, C, walls="plaster" if p["kind"] != "coffee" else "brick_red",
                floor="woodfloor", ceiling="paint_white", name="Front", wainscot="darkwood", wainscot_h=1.0, base="trim_black",
                openings={"S": [(x0 + 0.2, x1 - 0.2, 0.0, 3.4)]})
        kit.sub = None
        # the back wall's door to the rest (closed), colliders for the room
        tc.door(kit, "S", ry1, x1 - 1.4, 0.9, 2.1, leaf="darkwood", trim="trim_black", casing=0.06, depth=0.05)
        kit.collide((x0, ry0, 0), (x0 + T, ry1, Ht))
        kit.collide((x1 - T, ry0, 0), (x1, ry1, Ht))
        kit.collide((x0, ry1, 0), (x1, y1, Ht))
        kit.collide((x0, y0, C), (x1, ry1, Ht))
        if p["kind"] == "coffee":
            kit.p("Counter", "cedar").box((x0 + 0.5, ry1 - 2.4, 0.0), (x1 - 2.2, ry1 - 1.7, 1.0), skip="bt")
            kit.p("CounterTop", "polished").box((x0 + 0.4, ry1 - 2.45, 1.0), (x1 - 2.1, ry1 - 1.65, 1.05))
            kit.collide((x0 + 0.4, ry1 - 2.45, 0), (x1 - 2.1, ry1 - 1.65, 1.05))
            kit.p("Espresso", "chrome").box((x0 + 1.0, ry1 - 2.2, 1.05), (x0 + 1.8, ry1 - 1.8, 1.45))
            kit.p("PastryCase", "glow_white").box((x0 + 2.4, ry1 - 2.35, 1.05), (x0 + 3.6, ry1 - 1.75, 1.4))
            kit.p("BackShelf", "darkwood").box((x0 + 0.3, ry1 - 0.4, 0.0), (x1 - 2.2, ry1, 2.2), skip="b")
            for (tx, ty) in ((x0 + 1.4, y0 + 3.0), (x0 + 3.2, y0 + 3.0), (x1 - 1.4, y0 + 3.2)):
                tc.table(kit, tx, ty, w=0.7, h=0.75, round_=True, top="varnish")
                for a in (0.0, math.pi):
                    tc.stool(kit, tx + 0.55 * math.cos(a), ty + 0.55 * math.sin(a), h=0.46, seat="fabric_tan", post="trim_black")
            for x in (x0 + 1.2, 0.0, x1 - 1.4):
                kit.p("Pendants", "trim_black").cyl((x, ry1 - 2.0), 0.18, 2.4, 2.6, sides=8, caps="t", r1=0.05)
                kit.p("Pendants", "lamp").cyl((x, ry1 - 2.0), 0.17, 2.395, 2.4, sides=8, caps="b")
                kit.light((x, ry1 - 2.0, 2.35), (1.0, 0.7, 0.42), 35, 0.12, kind="SPOT")
            kit.light((0.0, y0 + 3.0, C - 0.1), (1.0, 0.85, 0.7), 40, 2.0, kind="AREA")
        elif p["kind"] == "bank":
            kit.p("Teller", "varnish").box((x0 + 0.4, ry1 - 2.6, 0.0), (x1 - 0.4, ry1 - 2.0, 1.1), skip="bt")
            kit.p("Teller", "polished").box((x0 + 0.3, ry1 - 2.65, 1.1), (x1 - 0.3, ry1 - 1.95, 1.15))
            tc.wquad(kit.p("TellerGlass", "windows"), "S", ry1 - 2.3, x0 + 0.4, x1 - 0.4, 1.15, 2.2, 0.0,
                     uvs=tc.cell_uv(tc.WIN["bk_transom"], sub=(0.06, 0.06, 0.94, 0.94)))
            kit.collide((x0 + 0.3, ry1 - 2.65, 0), (x1 - 0.3, ry1 - 1.95, 2.2))
            V_ = kit.p("Vault", "chrome")
            ring = [(1.2 * math.cos(2 * math.pi * i / 16), 1.6 + 1.2 * math.sin(2 * math.pi * i / 16)) for i in range(16)]
            V_.face([(xx, ry1 - 0.02, z) for xx, z in ring], toward=(0, -1, 0))
            kit.p("Vault", "metal_dark").cyl((0.0, ry1 - 0.06), 0.25, 1.4, 1.8, sides=8)
            for (tx, ty) in ((x0 + 1.4, y0 + 3.2), (x1 - 1.4, y0 + 3.2)):
                tc.table(kit, tx, ty, w=1.4, d=0.7, h=0.75, top="varnish", base="darkwood")
            for x in (-1.2, 1.2):
                kit.p("RopePosts", "brass").cyl((x, y0 + 4.6), 0.05, 0.0, 0.95, sides=6)
            kit.p("RopePosts", "trim_red").beam(V(-1.2, y0 + 4.6, 0.85), V(1.2, y0 + 4.6, 0.8), 0.03, 0.03)
            kit.light((0.0, y0 + 3.0, C - 0.1), (0.95, 0.95, 1.0), 45, 2.5, kind="AREA")
            kit.light((0.0, ry1 - 1.2, C - 0.1), (0.95, 0.95, 1.0), 30, 2.0, kind="AREA")
            # the ATM in the pilaster at the right of the front
            tc.wbox(kit.p("ATM", "metal_dark"), "S", y0, x1 - 0.95, x1 - 0.45, 0.9, 1.7, -0.1, 0.05, skip="back")
            tc.wquad(kit.p("ATM", "glow_cool"), "S", y0, x1 - 0.88, x1 - 0.52, 1.3, 1.55, 0.052)
        elif p["kind"] == "realty":
            for (tx, ty) in ((x0 + 3.0, y0 + 4.5), (x1 - 3.0, y0 + 4.5), (0.0, y0 + 6.3)):
                tc.table(kit, tx, ty, w=1.6, d=0.8, h=0.75, top="varnish", base="trim_black")
                kit.p("Monitors", "metal_dark").box((tx - 0.3, ty + 0.15, 0.75), (tx + 0.3, ty + 0.2, 1.15))
                kit.p("Monitors", "glow_cool").face([(tx - 0.27, ty + 0.145, 0.8), (tx + 0.27, ty + 0.145, 0.8), (tx + 0.27, ty + 0.145, 1.12),
                                                     (tx - 0.27, ty + 0.145, 1.12)], toward=(0, -1, 0))
            for k in range(8):
                a0 = x0 + 0.8 + k * (W - 1.6) / 8
                tc.wquad(kit.p("Photos", "paper"), "W" if False else "N", ry1, a0, a0 + (W - 1.6) / 8 - 0.2, 1.4, 2.1, 0.0, inward=True)
            kit.light((-3.0, y0 + 4.0, C - 0.1), (1.0, 0.92, 0.8), 40, 2.0, kind="AREA")
            kit.light((3.0, y0 + 4.0, C - 0.1), (1.0, 0.92, 0.8), 40, 2.0, kind="AREA")

    far = tc.Far(n)
    far.box((x0, y0, 0), (x1, y1, Ht), "brick_red" if p["brick"] == "brick_red" else "paint_white", top="tar")
    for b in range(bays):
        ox = x0 + bw * (b + 0.5)
        far.quad("S", y0, ox - bw / 2 + 0.4, ox + bw / 2 - 0.4, 0.3, 3.4, "window_lit" if p["kind"] == "coffee" else "glass_dark")
        if p["awning"]:
            far.shed(ox - bw / 2 + 0.35, ox + bw / 2 - 0.35, y0, y0 - 1.5, 3.62, 2.95, roof=p["awning"][-1])
    for a0, a1, z0, z1 in up:
        far.quad("S", y0, a0, a1, z0, z1, "glass_dark")
    far.box((x0, y0 - 0.18, 7.7), (x1, y0, 8.4), "brick_red" if p["brick"] == "brick_red" else "paint_white", skip="bk")
    kit.entrance((x1 - 1.5, y1 + 0.1, 0.0), "+Y", 1.0, kind="door", note="back door, closed")
    kit.info.update(variant=variant or "default", walk_in=p["walk_in"], storeys=2, party_walls=f"flush at x = +-{W / 2}",
                    footprint=[x0, round(y0 - 1.5, 3), x1, round(y1 + 0.3, 3)])
    parts = tc.finish(kit, col, root, far)
    if p["walk_in"] and p["bake"]:
        meshes = [o for o in root.children_recursive if o.type == "MESH" and not o.name.endswith("_LOD1")]
        town_light.bake(kit, root, meshes, [(x0 + T, y0 + 1.25, 0.0, x1 - T, y0 + 8.0, 3.6)])
    return root, parts
