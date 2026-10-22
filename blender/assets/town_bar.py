"""The bar (hero, walk-in): a roadhouse tavern on the edge of town, the one old building the
resort town kept and polished. Charcoal board-and-batten on a fieldstone base, a black
standing-seam roof carrying a big lit sign (a cocktail glass, outlined in red neon, an amber
arrow pointing at the door), a cedar portico, neon in the windows.

Inside (lit like a film set, all by emissive: neon tubes, lamp shades, back-lit bottles):
  * a 9.5 m bar: dark wood front, varnished top, brass foot rail, an amber glow under the
    top's lip, beer towers, a register, nine red-vinyl stools;
  * the back bar: mirrored bays, three shelves of back-lit bottles, a pink neon cocktail
    glass over it, cage pendants;
  * four high-backed red booths under the front windows, each with its own pendant;
  * a pool table under a three-shade billiard lamp, a cue rack, a dartboard;
  * a jukebox (glowing arch), a small stage with a red pleated curtain, a blue neon star,
    festoon lights, a drum kit, amps and two mic stands;
  * through the back: a hall (restroom doors, the back exit) and the office: a wall of
    security monitors, a desk, a safe, kegs and crates, a pegboard of charging radios.

Origin: floor centre at the front door's sill; front (the road, the door under the portico)
faces -Y. Doors: TownBar_Door_1 (front), _2 (back exit), _3 (office).
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

NAME = "TownBar"

P = dict(
    name=NAME,
    module="town_bar",
    x0=-12.0, x1=12.0, y0=-7.0, y1=7.0,
    thick=0.2,
    plate=4.4,
    ceiling=3.9,
    back_ceiling=3.0,
    pitch=0.42,
    partition=6.0,         # x of the wall between the bar room and the back
    ext="bb_charcoal",
    base="fieldstone",
    base_h=0.7,
    roof="seam_black",
)


def neon(kit, side, plane, pts, colour, d=0.04, r=0.012, closed=False, mounts=True):
    """A neon tube along a polyline of (a, z) points on a wall face, standing off by d."""
    Pf, u, n = tc.frame(side, plane)
    P3 = [Pf(a, z, d) for a, z in pts]
    kit.p("Neon", colour).polyline(P3, r, sides=5, closed=closed)
    if mounts:
        M = kit.p("NeonMounts", "chrome")
        for p in P3[:: max(1, len(P3) // 4)]:
            M.tube(p, p - n * d, 0.004, 3)


def arc(c, r, a0, a1, n):
    return [(c[0] + r * math.cos(a0 + (a1 - a0) * i / n), c[1] + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    x0, x1, y0, y1, T = p["x0"], p["x1"], p["y0"], p["y1"], p["thick"]
    xi0, xi1, yi0, yi1 = x0 + T, x1 - T, y0 + T, y1 - T
    XP = p["partition"]
    H, C, CB = p["plate"], p["ceiling"], p["back_ceiling"]
    ridge = H + (y1 - y0) / 2 * p["pitch"]

    # ================================================================ the shell
    door_f = (1.4, 2.6, 0.0, 2.3)                     # front door (S)
    booths = [-7.0, -4.95, -2.9, -0.85]
    win_s = [(c - 0.6, c + 0.6, 1.25, 2.45) for c in booths] + [(3.6, 4.8, 1.25, 2.45)]
    win_s += [(7.4, 8.2, 1.9, 2.5), (10.2, 11.0, 1.9, 2.5)]          # the restrooms, high
    door_x = (-3.5, -2.5, 0.0, 2.2)                   # back exit (E)
    win_e = [(1.9, 3.1, 1.0, 2.2)]                    # the office
    win_n = [(8.9, 10.1, 1.0, 2.2)]
    win_w = [(5.0, 6.0, 1.6, 2.6)]                    # a small one by the cue rack
    openings = {"S": [door_f] + win_s, "E": [door_x] + win_e, "N": win_n, "W": win_w}
    tc.shell(kit, x0, x1, y0, y1, H, openings, p["ext"], base=p["base"], base_h=p["base_h"],
             gables={"E": ridge, "W": ridge}, thick=T, reveal_part=kit.p("Reveals", "darkwood"))
    tc.gable_roof(kit, x0, x1, y0, y1, H, p["pitch"], axis="x", over_eave=0.6, over_gable=0.5, roof=p["roof"],
                  soffit="cedar", fascia="trim_black")
    # windows (painted glass outside, see-through from inside) and their trim
    for a0, a1, z0, z1 in win_s[:5]:
        tc.window(kit, "S", y0, (a0 + a1) / 2, z0, a1 - a0, z1 - z0, cell="bk_dark", trim="trim_black", casing=0.07, depth=0.1)
    for a0, a1, z0, z1 in win_s[5:]:
        tc.window(kit, "S", y0, (a0 + a1) / 2, z0, a1 - a0, z1 - z0, cell="bk_blinds", trim="trim_black", casing=0.05, depth=0.1)
    tc.window(kit, "E", x1, 2.5, 1.0, 1.2, 1.2, cell="bk_blinds", trim="trim_black", casing=0.07)
    tc.window(kit, "N", y1, 9.5, 1.0, 1.2, 1.2, cell="bk_office", trim="trim_black", casing=0.07)
    tc.window(kit, "W", x0, 5.5, 1.6, 1.0, 1.0, cell="bk_dark", trim="trim_black", casing=0.07)
    # neon in the front windows (between the glass and the street: both sides see them)
    c0 = booths[0]
    neon(kit, "S", y0, [(c0 - 0.35, 2.25), (c0 + 0.35, 2.25), (c0, 1.75), (c0 - 0.35, 2.25)], "neon_pink", d=-0.05, mounts=False)
    neon(kit, "S", y0, [(c0, 1.75), (c0, 1.45)], "neon_pink", d=-0.05, mounts=False)
    neon(kit, "S", y0, [(c0 - 0.18, 1.42), (c0 + 0.18, 1.42)], "neon_pink", d=-0.05, mounts=False)
    c2 = booths[2]
    neon(kit, "S", y0, [(c2 - 0.45 + 0.9 * i / 16, 1.85 + 0.12 * math.sin(i / 16 * 4 * math.pi)) for i in range(17)],
         "neon_blue", d=-0.05, mounts=False)
    neon(kit, "S", y0, [(c2 - 0.45 + 0.9 * i / 16, 1.6 + 0.12 * math.sin(i / 16 * 4 * math.pi + 1)) for i in range(17)],
         "neon_blue", d=-0.05, mounts=False)
    cs = 4.2
    star = [(cs + (0.42 if k % 2 == 0 else 0.17) * math.cos(math.pi / 2 + k * math.pi / 5),
             1.85 + (0.42 if k % 2 == 0 else 0.17) * math.sin(math.pi / 2 + k * math.pi / 5)) for k in range(10)]
    neon(kit, "S", y0, star, "neon_red", d=-0.05, closed=True, mounts=False)
    # the doors
    tc.hinged_door(kit, col, root, "S", y0, 2.0, 1.2, 2.3, depth=0.1, leaf="door_red", index=1, style="panel", swing=1)
    tc.hinged_door(kit, col, root, "E", x1, -3.0, 1.0, 2.2, depth=0.1, leaf="metal_galv", index=2, swing=1)
    kit.p("Trim", "trim_black")
    tc.wbox(kit.p("Trim", "trim_black"), "S", y0, 1.3, 2.7, 2.3, 2.42, 0, 0.04, skip="back")
    tc.wbox(kit.p("Sill", "stone"), "S", y0, 1.3, 2.7, 0.0, 0.02, -0.2, 0.06, skip="back")
    # the portico: cedar posts and beams, a small gable in black seam
    Tm = kit.p("Timber", "cedar")
    for x in (0.75, 3.25):
        Tm.box((x - 0.11, y0 - 2.15, 0.0), (x + 0.11, y0 - 1.93, 2.75), skip="b")
        Tm.box((x - 0.17, y0 - 2.21, 0.0), (x + 0.17, y0 - 1.87, 0.45), skip="b")       # stone plinth -> timber
        kit.collide((x - 0.17, y0 - 2.21, 0), (x + 0.17, y0 - 1.87, 2.75))
    Tm.box((0.5, y0 - 2.2, 2.75), (3.5, y0 - 1.9, 3.0))
    for x in (0.75, 3.25):
        Tm.box((x - 0.09, y0 - 2.15, 2.75), (x + 0.09, y0, 3.0))
    tc.gable_roof(kit, 0.4, 3.6, y0 - 2.3, y0 - 0.05, 3.0, 0.75, axis="y", over_eave=0.25, over_gable=0.3,
                  roof=p["roof"], soffit="cedar", fascia="trim_black", collide=False)
    kit.p("Stoop", "concrete").box((0.2, y0 - 2.5, 0.0), (3.8, y0, 0.03), skip="b")
    kit.p("PorchLight", "lamp").cyl((2.0, y0 - 1.0), 0.12, 2.82, 2.9, sides=8, caps="b")
    # the roof sign: a lit pictogram board on black steel posts, red neon round it, an amber arrow
    sx0, sx1, sz0, sz1, sy = -7.2, -2.8, 6.0, 8.2, y0 + 2.6
    S = kit.p("SignSteel", "trim_black")
    roof_z = H + (sy - y0) * p["pitch"] + 0.1
    for x in (sx0 + 0.5, sx1 - 0.5):
        S.box((x - 0.07, sy, roof_z - 0.3), (x + 0.07, sy + 0.14, sz0 + 0.3))
        S.beam((x, sy + 0.14, sz0 + 1.2), (x, sy + 1.5, roof_z + 0.45), 0.06, 0.06)
    S.box((sx0 - 0.08, sy - 0.12, sz0 - 0.08), (sx1 + 0.08, sy, sz1 + 0.08))
    kit.p("Sign", "signs", glow=True).face([(sx0, sy - 0.125, sz0), (sx1, sy - 0.125, sz0), (sx1, sy - 0.125, sz1),
                                           (sx0, sy - 0.125, sz1)], uvs=tc.sign_uv("bar"), toward=(0, -1, 0))
    neon(kit, "S", sy - 0.12, [(sx0 - 0.25, sz0 - 0.25), (sx1 + 0.25, sz0 - 0.25), (sx1 + 0.25, sz1 + 0.25),
                                (sx0 - 0.25, sz1 + 0.25)], "neon_red", d=0.06, closed=True, r=0.02)
    arrow = [(sx1 + 0.6, sz1 - 0.2), (sx1 + 1.6, sz0 + 0.4), (sx1 + 2.4, sz0 - 0.4)]
    neon(kit, "S", sy - 0.12, arrow, "neon_amber", d=0.06, r=0.025)
    neon(kit, "S", sy - 0.12, [(sx1 + 2.0, sz0 - 0.45), (sx1 + 2.4, sz0 - 0.4), (sx1 + 2.35, sz0 + 0.0)], "neon_amber", d=0.06, r=0.025)
    # goosenecks along the front, a stone chimney at the stage end, the back
    for a in (-9.5, -5.95, -1.9, 5.5):
        tc.gooseneck(kit, "S", y0, a, 3.6, arm=0.5)
    tc.chimney(kit, x0 - 0.45, 0.0, 0.0, ridge + 0.9, w=0.9, d=1.6, mat="fieldstone")
    kit.collide((x0 - 0.9, -0.8, 0), (x0, 0.8, ridge + 0.9))
    tc.gooseneck(kit, "E", x1, -3.0, 2.7, arm=0.35)
    tc.hvac(kit, 4.0, y1 + 0.8)
    tc.hvac(kit, 5.4, y1 + 0.8)
    tc.meter(kit, "N", y1, 2.8)
    D = kit.p("Dumpster", "trim_green")
    D.box((8.0, y1 + 0.6, 0.15), (10.0, y1 + 2.0, 1.3))
    kit.p("Dumpster", "rubber").box((7.95, y1 + 0.55, 1.3), (10.05, y1 + 2.05, 1.38))
    kit.collide((8.0, y1 + 0.6, 0), (10.0, y1 + 2.0, 1.38))
    for i, (kx, ky) in enumerate(((11.2, -4.3), (11.6, -4.3), (11.4, -4.75))):
        kit.p("Kegs", "metal_galv").cyl((x1 + 0.35 + 0.42 * (i % 2), -4.3 - 0.45 * (i // 2)), 0.2, 0.0, 0.6, sides=8)
    kit.collide((x1, -5.0, 0), (x1 + 1.0, -3.9, 0.6))

    # ================================================================ the bar room
    rx0, rx1 = xi0, XP - T / 2
    hall_door = (-3.5, -2.5, 0.0, 2.2)
    back_door = (5.3, 6.3, 0.0, 2.2)
    kit.sub = 0.6                       # finer faces inside, for the baked light
    tc.room(kit, rx0, rx1, yi0, yi1, 0.0, C, walls="brick_red", floor="woodfloor", ceiling="trim_black",
            wainscot="darkwood", wainscot_h=1.1, base="trim_black", name="Bar",
            openings={"S": [door_f] + win_s[:5], "E": [hall_door, back_door], "W": win_w})
    kit.sub = None
    tc.reveals(kit.p("Reveals", "darkwood"), "E", XP + T / 2, [hall_door, back_door], T, sill=False)
    tc.wall_collider(kit, "y", XP, y0, y1, T, C, [(-3.5, -2.5), (5.3, 6.3)])
    # ceiling beams, two fans
    Bm = kit.p("Beams", "darkwood")
    for x in (-10.0, -7.5, -5.0, -2.5, 0.0, 2.5, 5.0):
        Bm.box((x - 0.12, yi0, C - 0.32), (x + 0.12, yi1, C), skip="t")
    for fx, fy in ((-5.5, -1.5), (1.5, -1.5)):
        F = kit.p("Fans", "trim_black")
        F.cyl((fx, fy), 0.02, C - 0.55, C - 0.32, sides=4, caps="")
        F.cyl((fx, fy), 0.12, C - 0.68, C - 0.55, sides=8, caps="tb")
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2 + 0.2
            c_ = V(fx + math.cos(a) * 0.45, fy + math.sin(a) * 0.45, C - 0.62)
            kit.p("Fans", "darkwood").beam(V(fx, fy, C - 0.62) + (c_ - V(fx, fy, C - 0.62)) * 0.25, c_ * 1.0 + (c_ - V(fx, fy, C - 0.62)) * 0.7,
                                           0.13, 0.01)

    # ---------------------------------------------------------------- the bar
    bx0, bx1, by_f, by_b = -5.0, 4.4, 4.6, 5.35
    Dk = kit.p("BarFront", "darkwood")
    Dk.box((bx0, by_f + 0.05, 0.0), (bx1, by_b - 0.05, 1.0), skip="bt")
    for x in [bx0 + 0.6 + i * 1.2 for i in range(8)]:                  # raised panels on the front
        Dk.box((x - 0.5, by_f + 0.03, 0.18), (x + 0.5, by_f + 0.05, 0.85), skip="k")
    Vt = kit.p("BarTop", "varnish")
    Vt.box((bx0 - 0.1, by_f - 0.12, 1.0), (bx1 + 0.1, by_b + 0.05, 1.07))
    kit.p("BarGlow", "neon_amber").face([(bx0, by_f - 0.1, 0.995), (bx1, by_f - 0.1, 0.995), (bx1, by_f + 0.02, 0.995),
                                         (bx0, by_f + 0.02, 0.995)], toward=(0, 0, -1))
    Br = kit.p("Brass", "brass")
    Br.tube(V(bx0 + 0.1, by_f - 0.2, 0.22), V(bx1 - 0.1, by_f - 0.2, 0.22), 0.025, 6)
    for x in (bx0 + 0.3, (bx0 + bx1) / 2, bx1 - 0.3):
        Br.tube(V(x, by_f - 0.2, 0.22), V(x, by_f + 0.05, 0.3), 0.012, 4)
    kit.collide((bx0 - 0.1, by_f - 0.12, 0), (bx1 + 0.1, by_b + 0.05, 1.07))
    for x in (-3.2, -0.6, 2.0):                                         # beer towers
        Ch = kit.p("Taps", "chrome")
        Ch.box((x - 0.25, by_f + 0.25, 1.07), (x + 0.25, by_f + 0.4, 1.12))
        Ch.tube(V(x, by_f + 0.32, 1.12), V(x, by_f + 0.32, 1.42), 0.03, 6)
        Ch.box((x - 0.24, by_f + 0.26, 1.38), (x + 0.24, by_f + 0.38, 1.46))
        for k, colr in enumerate(("paint_orange", "paint_teal", "paint_yellow", "paint_red")):
            hx = x - 0.18 + k * 0.12
            kit.p("TapHandles", colr).box((hx - 0.018, by_f + 0.18, 1.34), (hx + 0.018, by_f + 0.22, 1.56))
    kit.p("Register", "metal_dark").box((3.3, by_f + 0.3, 1.07), (3.75, by_f + 0.7, 1.25))
    kit.p("Register", "glow_cool").face([(3.32, by_f + 0.29, 1.15), (3.73, by_f + 0.29, 1.15), (3.73, by_f + 0.29, 1.23),
                                         (3.32, by_f + 0.29, 1.23)], toward=(0, -1, 0))
    for i in range(9):
        tc.stool(kit, bx0 + 0.55 + i * (bx1 - bx0 - 1.1) / 8, by_f - 0.55, h=0.76)
    # the back bar
    bb_f = yi1 - 0.6
    Dk2 = kit.p("BackBar", "darkwood")
    Dk2.box((bx0, bb_f, 0.0), (bx1, yi1, 0.95), skip="bk")
    kit.p("BackBarTop", "varnish").box((bx0 - 0.05, bb_f - 0.05, 0.95), (bx1 + 0.05, yi1, 1.0), skip="k")
    for x in [bx0 + 0.3 + i * 0.9 for i in range(11)]:
        Dk2.box((x - 0.38, bb_f - 0.02, 0.1), (x + 0.38, bb_f, 0.85), skip="k")
    kit.collide((bx0 - 0.05, bb_f - 0.05, 0), (bx1 + 0.05, yi1, 1.0))
    bays = [(bx0 + 0.2, -1.8), (-1.5, 1.2), (1.5, bx1 - 0.2)]
    Mr = kit.p("Mirror", "mirror")
    for a0, a1 in bays:
        Mr.face([(a0, yi1 - 0.01, 1.05), (a1, yi1 - 0.01, 1.05), (a1, yi1 - 0.01, 2.6), (a0, yi1 - 0.01, 2.6)], toward=(0, -1, 0))
    for x in (bx0, -1.65, 1.35, bx1):
        Dk2.box((x - 0.15, yi1 - 0.3, 1.0), (x + 0.15, yi1, 2.85), skip="kb")
    Dk2.box((bx0 - 0.15, yi1 - 0.42, 2.6), (bx1 + 0.15, yi1, 2.9), skip="k")
    Sh = kit.p("Shelves", "trim_black")
    import random
    rng = random.Random(5)
    for zs in (1.25, 1.72, 2.19):
        for a0, a1 in bays:
            Sh.box((a0, yi1 - 0.3, zs - 0.025), (a1, yi1 - 0.01, zs), skip="k")
            kit.p("ShelfGlow", "neon_amber").face([(a0, yi1 - 0.29, zs - 0.027), (a1, yi1 - 0.29, zs - 0.027),
                                                   (a1, yi1 - 0.22, zs - 0.027), (a0, yi1 - 0.22, zs - 0.027)], toward=(0, 0, -1))
            x = a0 + 0.12
            while x < a1 - 0.1:
                if rng.random() > 0.15:
                    tc.bottle(kit, x, yi1 - 0.16 + rng.uniform(-0.05, 0.05), zs, kind=rng.randrange(5), glow=zs > 1.5)
                x += rng.uniform(0.15, 0.23)
    # the pink neon cocktail glass over the back bar, cage pendants over the bar
    cx, cz = -0.15, 3.25
    neon(kit, "S", yi1, [(cx - 0.55, cz + 0.45), (cx + 0.55, cz + 0.45), (cx, cz - 0.1), (cx - 0.55, cz + 0.45)],
         "neon_pink", d=-0.06, r=0.015)
    neon(kit, "S", yi1, [(cx, cz - 0.1), (cx, cz - 0.42), (cx - 0.25, cz - 0.45), (cx + 0.25, cz - 0.45)], "neon_pink", d=-0.06, r=0.015)
    neon(kit, "S", yi1, arc((cx + 0.22, cz + 0.32), 0.09, 0, 2 * math.pi, 8), "neon_green", d=-0.07, r=0.012)
    for x in (-4.0, -2.0, 0.0, 2.0, 3.8):
        pz = 2.55
        kit.p("Cords", "trim_black").tube(V(x, 5.0, pz + 0.25), V(x, 5.0, C), 0.006, 3)
        Cg = kit.p("Cages", "trim_black")
        Cg.cyl((x, 5.0), 0.13, pz + 0.18, pz + 0.25, sides=8, caps="b")
        for k in range(4):
            a = k * math.pi / 2
            Cg.tube(V(x + 0.11 * math.cos(a), 5.0 + 0.11 * math.sin(a), pz + 0.18),
                    V(x + 0.09 * math.cos(a), 5.0 + 0.09 * math.sin(a), pz - 0.05), 0.006, 3)
        kit.p("Bulbs", "lamp").cyl((x, 5.0), 0.065, pz - 0.03, pz + 0.17, sides=6, caps="tb")
    # a TV high on the partition, over the end of the bar
    kit.p("TV", "metal_dark").box((rx1 - 0.12, 3.2, 2.35), (rx1, 4.6, 3.15))
    kit.p("TV", "glow_cool").face([(rx1 - 0.125, 3.25, 2.4), (rx1 - 0.125, 4.55, 2.4), (rx1 - 0.125, 4.55, 3.1),
                                   (rx1 - 0.125, 3.25, 3.1)], toward=(-1, 0, 0))

    # ---------------------------------------------------------------- the booths
    for xc in booths:
        yb0, yb1 = yi0, yi0 + 1.3
        for s in (-1, 1):
            xb = xc + s * 0.375
            xo = xc + s * 0.95
            Fr = kit.p("BoothFrames", "darkwood")
            lo, hi = sorted((xb, xo))
            Fr.box((lo, yb0, 0.0), (hi, yb1, 0.36), skip="b")
            kit.p("BoothSeats", "vinyl_red").box((lo + (0.02 if s < 0 else 0.0), yb0, 0.36), (hi - (0.0 if s < 0 else 0.02), yb1 - 0.02, 0.46))
            bl, bh_ = sorted((xo, xo - s * 0.1))
            Fr.box((bl, yb0, 0.0), (bh_, yb1, 1.18), skip="b")
            cl, ch = sorted((xo - s * 0.1, xo - s * 0.2))
            kit.p("BoothSeats", "vinyl_red").box((cl, yb0, 0.46), (ch, yb1 - 0.04, 1.12), skip="b")
            kit.collide((lo, yb0, 0), (hi, yb1, 0.46))
            kit.collide((bl, yb0, 0), (bh_, yb1, 1.18))
        tc.table(kit, xc, yb0 + 0.62, w=0.72, d=1.1, h=0.76)
        kit.p("BoothLamps", "trim_black").cyl((xc, yb0 + 0.62), 0.2, 1.75, 1.95, sides=8, caps="", r1=0.05)
        kit.p("BoothLamps", "lamp").cyl((xc, yb0 + 0.62), 0.19, 1.755, 1.76, sides=8, caps="b")
        kit.p("Cords", "trim_black").tube(V(xc, yb0 + 0.62, 1.95), V(xc, yb0 + 0.62, C), 0.006, 3)
        # salt, pepper, a napkin box, a candle jar (red glow)
        kit.p("Tabletop", "chrome").cyl((xc - 0.12, yb0 + 0.3), 0.02, 0.76, 0.86, sides=5)
        kit.p("Tabletop", "chrome").cyl((xc - 0.06, yb0 + 0.3), 0.02, 0.76, 0.86, sides=5)
        kit.p("Tabletop", "neon_red").cyl((xc + 0.1, yb0 + 0.32), 0.035, 0.76, 0.84, sides=6)

    # ---------------------------------------------------------------- the pool table
    px, py = -2.0, 0.0
    Pt = kit.p("PoolRails", "varnish")
    L, Wd = 1.35, 0.75
    for (a0, b0, a1, b1) in ((-L, -Wd, L, -Wd + 0.12), (-L, Wd - 0.12, L, Wd), (-L, -Wd, -L + 0.12, Wd), (L - 0.12, -Wd, L, Wd)):
        Pt.box((px + a0, py + b0, 0.62), (px + a1, py + b1, 0.81))
    kit.p("Felt", "felt").box((px - L + 0.12, py - Wd + 0.12, 0.62), (px + L - 0.12, py + Wd - 0.12, 0.77), skip="b")
    Cu = kit.p("Felt", "felt")
    for (a0, b0, a1, b1) in ((-L + 0.12, -Wd + 0.12, L - 0.12, -Wd + 0.16), (-L + 0.12, Wd - 0.16, L - 0.12, Wd - 0.12),
                             (-L + 0.12, -Wd + 0.16, -L + 0.16, Wd - 0.16), (L - 0.16, -Wd + 0.16, L - 0.12, Wd - 0.16)):
        Cu.box((px + a0, py + b0, 0.77), (px + a1, py + b1, 0.8), skip="b")
    kit.p("PoolApron", "darkwood").box((px - L + 0.04, py - Wd + 0.04, 0.5), (px + L - 0.04, py + Wd - 0.04, 0.62), skip="t")
    for sx in (-1, 1):
        kit.p("PoolLegs", "darkwood").box((px + sx * 0.95 - 0.15, py - 0.55, 0.0), (px + sx * 0.95 + 0.15, py + 0.55, 0.5), skip="bt")
    for (a, b) in ((-L + 0.06, -Wd + 0.06), (0, -Wd + 0.05), (L - 0.06, -Wd + 0.06), (-L + 0.06, Wd - 0.06), (0, Wd - 0.05), (L - 0.06, Wd - 0.06)):
        kit.p("Pockets", "tar").box((px + a - 0.06, py + b - 0.06, 0.805), (px + a + 0.06, py + b + 0.06, 0.812), skip="b")
    kit.collide((px - L, py - Wd, 0), (px + L, py + Wd, 0.81))
    cols = ("paint_yellow", "paint_blue", "paint_red", "trim_bronze", "paint_orange", "trim_green", "door_red", "trim_black",
            "paint_yellow", "paint_blue")
    k = 0
    for row in range(4):
        for j in range(row + 1):
            bxp = px + 0.55 + row * 0.05
            byp = py + (j - row / 2) * 0.058
            kit.p("Balls", cols[k % len(cols)]).cyl((bxp, byp), 0.028, 0.77, 0.826, sides=6, caps="t")
            k += 1
    kit.p("Balls", "paint_white").cyl((px - 0.6, py + 0.1), 0.028, 0.77, 0.826, sides=6, caps="t")
    kit.p("Cues", "varnish").beam(V(px - 0.9, py - 0.3, 0.83), V(px + 0.4, py - 0.45, 0.82), 0.02, 0.02)
    # the billiard lamp: three green shades on a brass bar, chains
    lz = 1.7
    kit.p("Brass", "brass").box((px - 1.0, py - 0.03, lz + 0.22), (px + 1.0, py + 0.03, lz + 0.27))
    for dx in (-0.75, 0.0, 0.75):
        kit.p("LampShades", "trim_green").cyl((px + dx, py), 0.24, lz, lz + 0.2, sides=8, caps="", r1=0.08)
        kit.p("LampShades", "lamp").cyl((px + dx, py), 0.23, lz + 0.005, lz + 0.01, sides=8, caps="b")
    for dx in (-0.9, 0.9):
        kit.p("Cords", "brass").tube(V(px + dx, py, lz + 0.27), V(px + dx, py, C), 0.008, 3)
    # cue rack and dartboard
    Rk = kit.p("CueRack", "varnish")
    Rk.box((xi0, 4.9, 0.9), (xi0 + 0.05, 6.1, 1.0))
    Rk.box((xi0, 4.9, 1.7), (xi0 + 0.05, 6.1, 1.8))
    for k in range(6):
        y = 5.0 + k * 0.2
        kit.p("Cues", "varnish").beam(V(xi0 + 0.06, y, 0.05), V(xi0 + 0.06, y, 1.6), 0.025, 0.025)
    Db = kit.p("Dart", "trim_black")
    Db.cyl((rx1 - 0.04, 1.5), 0.32, 0.0, 0.0, sides=3)          # (placeholder ring removed below)
    Db.f.clear(), Db.v.clear(), Db.uv.clear()
    for rr, colr, d in ((0.3, "trim_black", 0.01), (0.22, "paint_red", 0.015), (0.16, "paper", 0.018), (0.08, "trim_green", 0.021),
                        (0.03, "paint_red", 0.024)):
        ring = [(1.5 + rr * math.cos(2 * math.pi * i / 12), 1.73 + rr * math.sin(2 * math.pi * i / 12)) for i in range(12)]
        kit.p("Dart", colr).face([(rx1 - d, a, z) for a, z in ring[::-1]], toward=(-1, 0, 0))
    kit.p("Dart", "trim_black").box((rx1 - 0.01, 1.05, 1.25), (rx1, 1.95, 2.2))

    # ---------------------------------------------------------------- the stage
    st_x0, st_x1, st_y0, st_y1, st_h = xi0, -8.6, -3.5, 3.5, 0.45
    kit.p("Stage", "darkwood").box((st_x0, st_y0, 0.0), (st_x1, st_y1, st_h), skip="bl")
    kit.p("StageEdge", "trim_black").box((st_x1, st_y0, 0.0), (st_x1 + 0.03, st_y1, st_h + 0.02), skip="b")
    kit.collide((st_x0, st_y0, 0), (st_x1, st_y1, st_h))
    tc.steps(kit, -10.6, -9.6, st_y1, st_h, direction=1, mat="darkwood", z_bottom=0.0)
    # a red pleated curtain behind it, the blue neon star on it, a red bolt
    Cr = kit.p("Curtain", "trim_red")
    k = 28
    for i in range(k):
        ya, yb = st_y0 - 0.3 + (st_y1 - st_y0 + 0.6) * i / k, st_y0 - 0.3 + (st_y1 - st_y0 + 0.6) * (i + 1) / k
        xa, xb = xi0 + (0.02 if i % 2 == 0 else 0.1), xi0 + (0.1 if i % 2 == 0 else 0.02)
        Cr.face([(xa, ya, st_h), (xb, yb, st_h), (xb, yb, C - 0.05), (xa, ya, C - 0.05)], toward=(1, 0, 0))
    kit.p("CurtainRod", "brass").tube(V(xi0 + 0.06, st_y0 - 0.35, C - 0.08), V(xi0 + 0.06, st_y1 + 0.35, C - 0.08), 0.02, 5)
    star = [((0.95 if k % 2 == 0 else 0.4) * math.cos(math.pi / 2 + k * math.pi / 5),
             (0.95 if k % 2 == 0 else 0.4) * math.sin(math.pi / 2 + k * math.pi / 5)) for k in range(10)]
    neon(kit, "E", xi0 + 0.1, [(a, 2.4 + b) for a, b in star], "neon_blue", d=0.08, closed=True, r=0.018)
    neon(kit, "E", xi0 + 0.1, [(a * 0.8, 2.4 + b * 0.8) for a, b in star], "neon_blue", d=0.08, closed=True, r=0.012)
    neon(kit, "E", xi0 + 0.1, [(-2.3, 3.3), (-1.85, 2.6), (-2.15, 2.55), (-1.6, 1.6)], "neon_red", d=0.08, r=0.018)
    neon(kit, "E", xi0 + 0.1, [(2.3, 3.3), (1.85, 2.6), (2.15, 2.55), (1.6, 1.6)], "neon_red", d=0.08, r=0.018)
    # festoon lights along the stage front
    pts = [V(st_x1 + 0.1, st_y0 + (st_y1 - st_y0) * i / 20, C - 0.35 - 0.45 * math.sin(math.pi * i / 20)) for i in range(21)]
    kit.p("Cords", "trim_black").polyline(pts, 0.006, sides=3)
    for q in pts[1:-1]:
        kit.p("Festoon", "lamp").cyl((q.x, q.y), 0.035, q.z - 0.1, q.z - 0.02, sides=5, caps="tb")
    # the band's kit: drums, cymbals, amps, two mics
    dz = st_h
    Dr = kit.p("Drums", "paint_red")
    Dr.tube(V(-10.95, 0.6, dz + 0.3), V(-10.55, 0.6, dz + 0.3), 0.28, 10)
    kit.p("DrumHeads", "paper").face([V(-10.55, 0.6 + 0.28 * math.cos(2 * math.pi * i / 10), dz + 0.3 + 0.28 * math.sin(2 * math.pi * i / 10))
                                      for i in range(10)], toward=(1, 0, 0))
    for (ty, tz, tr) in ((0.15, 0.75, 0.13), (1.0, 0.72, 0.15)):
        Dr.cyl((-10.6, ty), tr, dz + tz, dz + tz + 0.16, sides=8, caps="")
        kit.p("DrumHeads", "paper").cyl((-10.6, ty), tr, dz + tz + 0.16, dz + tz + 0.165, sides=8)
    Cb = kit.p("Cymbals", "brass")
    Ch = kit.p("Stands", "chrome")
    for (cx_, cy_, cz_) in ((-10.4, -0.35, 1.05), (-10.9, 1.45, 1.35), (-11.0, -0.15, 1.45)):
        Cb.cyl((cx_, cy_), 0.22, dz + cz_, dz + cz_ + 0.015, sides=10, caps="tb")
        Ch.tube(V(cx_, cy_, dz), V(cx_, cy_, dz + cz_), 0.01, 4)
    for sy_ in (-2.5, 2.5):
        A = kit.p("Amps", "trim_black")
        A.box((-11.75, sy_ - 0.38, dz), (-11.3, sy_ + 0.38, dz + 1.25))
        kit.p("AmpGrille", "screen").face([(-11.299, sy_ - 0.32, dz + 0.1), (-11.299, sy_ + 0.32, dz + 0.1),
                                           (-11.299, sy_ + 0.32, dz + 0.95), (-11.299, sy_ - 0.32, dz + 0.95)], toward=(1, 0, 0))
        kit.p("AmpGrille", "neon_red").box((-11.3, sy_ + 0.25, dz + 1.1), (-11.29, sy_ + 0.3, dz + 1.15))
    for my in (-1.2, 1.4):
        Ch.cyl((-9.2, my), 0.16, dz, dz + 0.02, sides=6)
        Ch.tube(V(-9.2, my, dz), V(-9.2, my, dz + 1.45), 0.012, 4)
        Ch.tube(V(-9.2, my, dz + 1.45), V(-9.0, my, dz + 1.55), 0.01, 4)
        kit.p("Mics", "trim_black").cyl((-8.98, my), 0.028, dz + 1.53, dz + 1.62, sides=6)
    # high tables by the stage
    for (hx, hy) in ((-7.3, 2.3), (-7.3, -2.2)):
        tc.table(kit, hx, hy, w=0.7, h=1.05, round_=True)
        for a in (0.4, 0.4 + math.pi):
            tc.stool(kit, hx + 0.55 * math.cos(a), hy + 0.55 * math.sin(a), h=0.76, seat="vinyl_black")

    # ---------------------------------------------------------------- the jukebox
    jx0, jx1, jy0, jy1 = rx1 - 0.7, rx1 - 0.02, -6.15, -5.15
    J = kit.p("Jukebox", "varnish")
    J.box((jx0, jy0, 0.0), (jx1, jy1, 1.0), skip="b")
    jc, jr = (jy0 + jy1) / 2, (jy1 - jy0) / 2
    archp = arc((jc, 1.0), jr, 0, math.pi, 10)
    J.face([(jx0, a, z) for a, z in archp[::-1]], toward=(-1, 0, 0))
    J.face([(jx1, a, z) for a, z in archp], toward=(1, 0, 0))
    for i in range(10):
        (a0_, z0_), (a1_, z1_) = archp[i], archp[i + 1]
        J.face([(jx0, a0_, z0_), (jx1, a0_, z0_), (jx1, a1_, z1_), (jx0, a1_, z1_)], toward=(0, a0_ - jc, z0_ - 1.0))
    neon(kit, "W", jx0, [(-a, z) for a, z in arc((-jc, 1.0), jr - 0.05, 0, math.pi, 10)], "neon_amber", d=0.03, r=0.02, mounts=False)
    neon(kit, "W", jx0, [(-a, z) for a, z in arc((-jc, 1.0), jr - 0.16, 0, math.pi, 8)], "neon_pink", d=0.03, r=0.016, mounts=False)
    for a in (jy0 + 0.07, jy1 - 0.07):
        kit.p("Neon", "neon_blue").tube(V(jx0 - 0.03, a, 0.1), V(jx0 - 0.03, a, 1.0), 0.02, 5)
    kit.p("JukeFace", "lamp").face([(jx0 - 0.005, jy1 - 0.2, 0.62), (jx0 - 0.005, jy0 + 0.2, 0.62), (jx0 - 0.005, jy0 + 0.2, 0.92),
                                    (jx0 - 0.005, jy1 - 0.2, 0.92)], toward=(-1, 0, 0))
    G = kit.p("JukeGrille", "chrome")
    for k in range(5):
        z = 0.15 + k * 0.08
        G.box((jx0 - 0.02, jy0 + 0.18, z), (jx0, jy1 - 0.18, z + 0.025), skip="r")
    kit.collide((jx0, jy0, 0), (jx1, jy1, 1.5))

    # ================================================================ the back: hall, restrooms, office
    hx0, hx1 = XP + T / 2, xi1
    hy0, hy1 = -4.0 + T / 2, -2.0 - T / 2
    office_door = (8.5, 9.5, 0.0, 2.2)
    rest_doors = [(6.8, 7.7, 0.0, 2.1), (10.3, 11.2, 0.0, 2.1)]
    kit.sub = 0.8
    tc.room(kit, hx0, hx1, hy0, hy1, 0.0, CB, walls="plaster", floor="checker", ceiling="plaster", name="Hall",
            base="trim_black", openings={"W": [hall_door], "E": [door_x], "N": [office_door], "S": rest_doors})
    for a0, a1, z0, z1 in rest_doors:
        tc.door(kit, "N", hy0, (a0 + a1) / 2, a1 - a0, z1 - z0, leaf="darkwood", trim="trim_black",
                wall_part=kit.p("HallWalls", "plaster"), casing=0.07)
    tc.reveals(kit.p("Reveals", "darkwood"), "N", hy1 + T, [office_door], T, sill=False)
    tc.wall_collider(kit, "x", -2.0, XP, x1, T, CB, [(8.5, 9.5)])
    tc.wall_collider(kit, "x", -4.0, XP, x1, T, CB)
    kit.p("ExitGlow", "neon_green").box((hx1 - 0.06, -3.2, 2.45), (hx1, -2.8, 2.62))
    kit.p("HallLight", "glow_white").face([(7.0, -3.2, CB - 0.01), (10.8, -3.2, CB - 0.01), (10.8, -2.8, CB - 0.01),
                                           (7.0, -2.8, CB - 0.01)], toward=(0, 0, -1))
    # the bar-back door: a pair of saloon half-doors left ajar
    Sd = kit.p("SaloonDoors", "darkwood")
    for (yh, ang) in ((5.3, 0.5), (6.3, -0.6)):
        L_ = 0.48
        e = V(XP, yh, 0.0) + V(math.sin(abs(ang)) * L_ * (1 if ang > 0 else 1) * 0.0, 0, 0)
        d = V(-math.sin(abs(ang)), math.cos(abs(ang)) * (1 if ang > 0 else -1), 0) * L_
        Sd.face([e + V(0, 0, 0.45), e + d + V(0, 0, 0.45), e + d + V(0, 0, 1.65), e + V(0, 0, 1.65)], toward=V(-d.y, d.x, 0))
        Sd.face([e + V(0, 0, 0.45), e + d + V(0, 0, 0.45), e + d + V(0, 0, 1.65), e + V(0, 0, 1.65)], toward=V(d.y, -d.x, 0))
    # the office
    ox0, ox1, oy0, oy1 = XP + T / 2, xi1, -2.0 + T / 2, yi1
    tc.room(kit, ox0, ox1, oy0, oy1, 0.0, CB, walls="plaster", floor="woodfloor", ceiling="plaster", name="Office",
            wainscot="darkwood", wainscot_h=0.9, base="trim_black",
            openings={"S": [office_door], "W": [back_door], "E": win_e, "N": win_n})
    kit.sub = None
    tc.hinged_door(kit, col, root, "N", hy1 + T, 9.0, 1.0, 2.2, depth=0.1, leaf="darkwood", index=3, swing=-1)
    kit.p("OfficeLight", "glow_white").face([(8.0, 2.0, CB - 0.01), (10.0, 2.0, CB - 0.01), (10.0, 2.5, CB - 0.01),
                                             (8.0, 2.5, CB - 0.01)], toward=(0, 0, -1))
    # the monitor wall (security feeds) over a low cabinet on the north wall
    kit.p("Cabinet", "metal_dark").box((7.2, oy1 - 0.5, 0.0), (10.8, oy1, 0.9), skip="b")
    kit.collide((7.2, oy1 - 0.5, 0), (10.8, oy1, 0.9))
    for i in range(4):
        for j in range(2):
            mx = 7.5 + i * 0.85
            mz = 1.35 + j * 0.6
            kit.p("Monitors", "metal_dark").box((mx, oy1 - 0.25, mz), (mx + 0.75, oy1 - 0.02, mz + 0.5))
            kit.p("Screens", "glow_cool").face([(mx + 0.04, oy1 - 0.255, mz + 0.04), (mx + 0.71, oy1 - 0.255, mz + 0.04),
                                                (mx + 0.71, oy1 - 0.255, mz + 0.46), (mx + 0.04, oy1 - 0.255, mz + 0.46)],
                                               toward=(0, -1, 0))
    # desk and chair (facing the monitors), the safe, filing cabinets
    tc.table(kit, 9.2, 4.4, w=1.7, d=0.8, h=0.76, top="varnish", base="darkwood")
    kit.p("Chair", "vinyl_black").box((8.95, 3.4, 0.42), (9.45, 3.9, 0.5))
    kit.p("Chair", "vinyl_black").box((8.95, 3.35, 0.5), (9.45, 3.42, 1.05))
    kit.p("Chair", "metal_dark").cyl((9.2, 3.65), 0.03, 0.05, 0.42, sides=5, caps="")
    kit.p("Chair", "metal_dark").cyl((9.2, 3.65), 0.28, 0.0, 0.05, sides=5)
    kit.p("Safe", "metal_dark").box((ox1 - 0.75, oy1 - 0.75, 0.0), (ox1 - 0.05, oy1 - 0.05, 0.95), skip="b")
    kit.p("Safe", "chrome").cyl((ox1 - 0.4, oy1 - 0.76), 0.06, 0.5, 0.5, sides=6)
    kit.collide((ox1 - 0.75, oy1 - 0.75, 0), (ox1 - 0.05, oy1 - 0.05, 0.95))
    for fy in (0.2, 0.75):
        kit.p("Files", "metal_galv").box((ox1 - 0.65, fy, 0.0), (ox1 - 0.05, fy + 0.5, 1.35), skip="b")
        for k in range(3):
            kit.p("Files", "chrome").box((ox1 - 0.66, fy + 0.2, 0.3 + k * 0.42), (ox1 - 0.65, fy + 0.3, 0.33 + k * 0.42))
    kit.collide((ox1 - 0.65, 0.2, 0), (ox1 - 0.05, 1.25, 1.35))
    # kegs and crates by the bar-back door
    for i in range(6):
        kx, ky = ox0 + 0.35 + (i % 3) * 0.45, 2.4 + (i // 3) * 0.45
        kit.p("Kegs", "metal_galv").cyl((kx, ky), 0.2, 0.0, 0.6, sides=8)
    kit.collide((ox0 + 0.1, 2.15, 0), (ox0 + 1.55, 3.1, 0.6))
    for i, (cx_, cy_, cz_) in enumerate(((ox0 + 0.4, 0.2, 0.0), (ox0 + 0.4, 0.2, 0.32), (ox0 + 0.95, 0.2, 0.0), (ox0 + 0.4, 0.75, 0.0))):
        kit.p("Crates", "deck").box((cx_ - 0.25, cy_ - 0.2, cz_), (cx_ + 0.25, cy_ + 0.2, cz_ + 0.3))
    kit.collide((ox0 + 0.15, 0.0, 0), (ox0 + 1.2, 0.95, 0.62))
    # the pegboard of charging radios on the south wall
    kit.p("Pegboard", "deck").box((10.1, oy0, 1.1), (11.5, oy0 + 0.02, 1.9))
    for k in range(6):
        rx = 10.25 + k * 0.21
        kit.p("Radios", "metal_dark").box((rx, oy0 + 0.02, 1.2), (rx + 0.09, oy0 + 0.07, 1.45))
        kit.p("Radios", "trim_black").box((rx + 0.06, oy0 + 0.03, 1.45), (rx + 0.075, oy0 + 0.045, 1.62))
        kit.p("RadioLEDs", "neon_green").box((rx + 0.02, oy0 + 0.07, 1.4), (rx + 0.035, oy0 + 0.075, 1.415))

    # ================================================================ lamps for the light bake
    warm, amber, cool = (1.0, 0.66, 0.36), (1.0, 0.5, 0.15), (0.6, 0.75, 1.0)
    for x in (-4.0, -2.0, 0.0, 2.0, 3.8):
        kit.light((x, 5.0, 2.6), warm, 45, 0.08)
    for xc in booths:
        kit.light((xc, yi0 + 0.62, 1.72), warm, 40, 0.15, kind="SPOT")
    for dx in (-0.75, 0.0, 0.75):
        kit.light((px + dx, py, 1.68), (1.0, 0.8, 0.55), 55, 0.18, kind="SPOT")
    for yy in (-2.5, 0.0, 2.5):
        kit.light((st_x1 + 0.1, yy, C - 0.6), warm, 10, 0.1)
    kit.light((xi0 + 0.5, 0.0, 2.4), (0.25, 0.4, 1.0), 30, 0.6)                 # the blue star
    kit.light((xi0 + 0.5, -2.0, 2.5), (1.0, 0.1, 0.06), 8, 0.3)
    kit.light((xi0 + 0.5, 2.0, 2.5), (1.0, 0.1, 0.06), 8, 0.3)
    kit.light((-9.6, 0.2, 2.9), (1.0, 0.8, 0.6), 60, 0.1, kind="SPOT", direction=(-0.6, 0.0, -0.8))   # a stage spot
    for a0, a1 in bays:
        kit.light(((a0 + a1) / 2, yi1 - 0.35, 1.9), amber, 18, 0.3)
    kit.light((-0.15, yi1 - 0.35, 3.3), (1.0, 0.2, 0.5), 12, 0.3)               # the pink neon
    kit.light((jx0 - 0.4, (jy0 + jy1) / 2, 1.2), (1.0, 0.45, 0.3), 14, 0.3)    # the jukebox
    kit.light((rx1 - 0.5, 3.9, 2.75), cool, 6, 0.3)                            # the TV
    kit.light((c0, y0 + 0.4, 1.9), (1.0, 0.2, 0.5), 5, 0.2)                    # window neon
    kit.light((c2, y0 + 0.4, 1.75), (0.3, 0.45, 1.0), 5, 0.2)
    kit.light((cs, y0 + 0.4, 1.85), (1.0, 0.12, 0.06), 5, 0.2)
    kit.light((9.0, -3.0, CB - 0.05), (0.8, 0.88, 1.0), 14, 1.2, kind="AREA")
    kit.light((9.0, 2.25, CB - 0.05), (0.8, 0.88, 1.0), 12, 1.5, kind="AREA")
    kit.light((9.0, oy1 - 0.6, 1.9), cool, 30, 1.2, kind="AREA", direction=(0, -1, 0))   # the monitor wall
    kit.light((bx0 + 0.3, by_f - 0.3, 0.9), amber, 4, 0.2)
    kit.light((bx1 - 0.3, by_f - 0.3, 0.9), amber, 4, 0.2)

    # ================================================================ LOD1
    far = tc.Far(n)
    far.gable(x0, x1, y0, y1, 0.0, H, ridge, axis="x", wall=p["ext"], roof=p["roof"], over=0.55)
    far.box((x0, y0, 0), (x1, y1, p["base_h"]), p["base"], skip="bt")
    for a0, a1, z0, z1 in win_s[:5]:
        far.quad("S", y0, a0, a1, z0, z1, "window_lit", d=0.02)
    far.quad("S", y0, 1.4, 2.6, 0.0, 2.3, "door_red", d=0.02)
    far.box((0.4, y0 - 2.3, 2.75), (3.6, y0, 3.6), "seam_black", skip="b")
    far.quad("S", sy, sx0, sx1, sz0, sz1, "neon_red", d=0.15)
    far.box((x0 - 0.9, -0.8, 0), (x0, 0.8, ridge + 0.9), "fieldstone", skip="b")

    kit.entrance((2.0, y0 - 0.1, 0.0), "-Y", 1.2, kind="door", note="TownBar_Door_1, under the portico")
    kit.entrance((x1 + 0.1, -3.0, 0.0), "+X", 1.0, kind="door", note="TownBar_Door_2, the back exit from the hall")
    kit.info.update(walk_in=True, storeys=1, rooms=["bar room 17.7 x 13.6 (stage, booths, pool, jukebox)",
                                                    "hall 5.7 x 1.8 (two restroom doors, closed; back exit)",
                                                    "office 5.7 x 8.7 (monitor wall, desk, safe, kegs)"],
                    footprint=[round(x0 - 0.9, 3), round(y0 - 2.5, 3), round(x1 + 1.0, 3), round(y1 + 2.05, 3)],
                    lighting="emissive only (M_Town_Glow: neon, shades, bulbs, bottles, screens)")
    parts = tc.finish(kit, col, root, far)
    meshes = [o for o in root.children_recursive if o.type == "MESH" and not o.name.endswith("_LOD1")]
    if p.get("bake", True):
        town_light.bake(kit, root, meshes, [(rx0, yi0, 0.0, rx1, yi1, C), (hx0, hy0, 0.0, hx1, hy1, CB),
                                            (ox0, oy0, 0.0, ox1, oy1, CB)])
        town_light.fill([o for o in parts if o.name.endswith("_LOD1")])
    return root, parts
