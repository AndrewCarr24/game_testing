"""The bar (hero, walk-in): the roadhouse by the river and the rail tunnel, the one place
in town that predates the polish. A long low 1950s building of painted cinder block with
board-and-batten gables under a shallow corrugated roof; a deep porch along the lot side
with neon in the windows (BAR, a beer bottle, a cocktail glass, a star) and a neon BAR over
the door; a lit cocktail sign on the roof with an amber arrow; a stone chimney at the stage
end; a river deck at the back with steps down to the water.

Inside, lit like a film set by emissive pieces only (their light baked into COLOR_0, dark
between the pools):
  * the 14 m bar: dark wood front, varnished top, brass foot rail, an amber glow under the
    lip, beer towers, a register, thirteen red stools; the back bar: mirrored bays, three
    shelves of back-lit bottles, a pink neon cocktail glass, cage pendants over the bar;
  * five red booths under the porch windows, each with a shaded lamp;
  * the pool table in the middle under its low billiard lamp, a cue rack, a dartboard;
  * the jukebox glowing by the stage; the stage with a red pleated curtain, a blue neon
    star, festoon lights, a drum kit, amps and two mics; two ceiling fans, a TV;
  * a restroom corridor (two doors, closed; the back exit) and, behind a door by the bar's
    end (left ajar), the back room: a store room with a table, a rail of hooks on the wall,
    a wall of security monitors, a safe, kegs and crates, a pegboard of charging radios.

Origin: floor centre at the front door's sill; front (the lot, the porch) faces -Y; the
river deck is at +Y (its steps go down to below_m). Doors: TownBar_Door_1 (front), _2 (back
exit), _3 (the back room, ajar), _4 (the river deck), _5 (the back room from the hall).
"""
import importlib
import math
import os
import random
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
    name=NAME, module="town_bar",
    x0=-14.0, x1=14.0, y0=-6.0, y1=6.0, thick=0.2,
    plate=3.9, ceiling=3.5, back_ceiling=3.0, pitch=0.25,
    partition=8.0, porch=3.0, deck=3.0, water_drop=1.8,
    ext="block", gable="bb_charcoal", roof="corrugated", bake=True,
)

# neon letters on a unit cell (a, z in 0..1): B, A, R; a beer bottle
LETTERS = {
    "B": [[(0, 0), (0, 1), (0.42, 1), (0.58, 0.88), (0.58, 0.64), (0.42, 0.53), (0, 0.53)],
          [(0.42, 0.53), (0.62, 0.4), (0.62, 0.13), (0.46, 0), (0, 0)]],
    "A": [[(0, 0), (0.33, 1), (0.66, 0)], [(0.13, 0.4), (0.53, 0.4)]],
    "R": [[(0, 0), (0, 1), (0.42, 1), (0.58, 0.86), (0.58, 0.66), (0.42, 0.53), (0, 0.53)], [(0.28, 0.53), (0.62, 0)]],
}
BOTTLE = [(-0.14, 0), (0.14, 0), (0.14, 0.55), (0.06, 0.7), (0.06, 0.95), (-0.06, 0.95), (-0.06, 0.7), (-0.14, 0.55)]


def neon(kit, side, plane, pts, colour, d=0.04, r=0.012, closed=False, mounts=True):
    """A neon tube along a polyline of (a, z) points on a wall face, standing off by d."""
    Pf, u, n = tc.frame(side, plane)
    P3 = [Pf(a, z, d) for a, z in pts]
    kit.p("Neon", colour).polyline(P3, r, sides=5, closed=closed)
    if mounts:
        M = kit.p("NeonMounts", "chrome")
        for q in P3[:: max(1, len(P3) // 3)]:
            M.tube(q, q - n * d, 0.004, 3)


def neon_word(kit, side, plane, word, a, z, h, colour, d=0.04, r=0.014, mounts=True):
    """A word in neon letters, h tall, starting at a."""
    sign = 1 if side in ("S", "E") else -1
    for i, ch in enumerate(word):
        for stroke in LETTERS[ch]:
            neon(kit, side, plane, [(a + sign * (i * 0.85 + x) * h, z + y * h) for x, y in stroke], colour, d, r, mounts=mounts)


def arc(c, r, a0, a1, n):
    return [(c[0] + r * math.cos(a0 + (a1 - a0) * i / n), c[1] + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def star(cx, cz, ro, ri):
    return [(cx + (ro if k % 2 == 0 else ri) * math.cos(math.pi / 2 + k * math.pi / 5),
             cz + (ro if k % 2 == 0 else ri) * math.sin(math.pi / 2 + k * math.pi / 5)) for k in range(10)]


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    x0, x1, y0, y1, T = p["x0"], p["x1"], p["y0"], p["y1"], p["thick"]
    xi0, xi1, yi0, yi1 = x0 + T, x1 - T, y0 + T, y1 - T
    XP = p["partition"]
    H, C, CB = p["plate"], p["ceiling"], p["back_ceiling"]
    ridge = H + (y1 - y0) / 2 * p["pitch"]
    rng = random.Random(5)

    # ================================================================ the shell
    door_f = (4.9, 6.1, 0.0, 2.3)                       # the front door, at the bar's east end
    booths = [-8.4, -6.25, -4.1, -1.95, 0.2]
    win_s = [(c - 0.6, c + 0.6, 1.25, 2.45) for c in booths] + [(2.4, 3.6, 1.25, 2.45)]
    win_s += [(9.4, 10.2, 1.9, 2.5), (12.0, 12.8, 1.9, 2.5)]          # the restrooms, high
    door_x = (-1.5, -0.5, 0.0, 2.2)                     # the back exit (E), off the hall
    door_r = (-10.0, -9.0, 0.0, 2.2)                    # to the river deck (N)
    win_n = [(-12.6, -11.0, 1.2, 2.4), (10.0, 11.4, 1.2, 2.2)]          # stage end; the back room
    win_w = [(4.0, 5.0, 1.6, 2.6)]
    openings = {"S": [door_f] + win_s, "E": [door_x], "N": [door_r] + win_n, "W": win_w}
    rv = kit.p("Reveals", "darkwood")
    tc.shell(kit, x0, x1, y0, y1, H, openings, p["ext"], thick=T, reveal_part=rv)
    for side, plane in (("E", x1), ("W", x0)):               # board-and-batten gables over the block
        tc.wall(kit.p("Gables", p["gable"]), side, plane, y0, y1, H, H, gable=ridge, d=0.01)
        tc.wbox(kit.p("Trim", "trim_black"), side, plane, y0, y1, H - 0.1, H + 0.05, 0, 0.04, skip="back")
    tc.gable_roof(kit, x0, x1, y0, y1, H, p["pitch"], axis="x", over_eave=0.5, over_gable=0.45, roof=p["roof"],
                  soffit="deck", fascia="trim_black")
    for a0, a1, z0, z1 in win_s[:6]:
        tc.window(kit, "S", y0, (a0 + a1) / 2, z0, a1 - a0, z1 - z0, cell="bk_dark", trim="trim_black", casing=0.07, depth=0.1)
    for a0, a1, z0, z1 in win_s[6:]:
        tc.window(kit, "S", y0, (a0 + a1) / 2, z0, a1 - a0, z1 - z0, cell="bk_blinds", trim="trim_black", casing=0.05, depth=0.1)
    for a0, a1, z0, z1 in win_n:
        tc.window(kit, "N", y1, (a0 + a1) / 2, z0, a1 - a0, z1 - z0, cell="bk_dark", trim="trim_black", casing=0.07)
    tc.window(kit, "W", x0, 4.5, 1.6, 1.0, 1.0, cell="bk_dark", trim="trim_black", casing=0.07)
    # neon in the porch windows, between the glass and the porch (seen from both sides)
    c = booths
    neon_word(kit, "S", y0, "BAR", c[0] - 0.5, 1.6, 0.42, "neon_red", d=-0.05, mounts=False)
    neon(kit, "S", y0, [(c[1] + x * 1.2, 1.4 + z * 0.95) for x, z in BOTTLE], "neon_amber", d=-0.05, closed=True, mounts=False)
    neon(kit, "S", y0, [(c[2] - 0.35, 2.25), (c[2] + 0.35, 2.25), (c[2], 1.75), (c[2] - 0.35, 2.25)], "neon_pink", d=-0.05, mounts=False)
    neon(kit, "S", y0, [(c[2], 1.75), (c[2], 1.45)], "neon_pink", d=-0.05, mounts=False)
    neon(kit, "S", y0, [(c[2] - 0.18, 1.42), (c[2] + 0.18, 1.42)], "neon_pink", d=-0.05, mounts=False)
    neon(kit, "S", y0, [(c[3] - 0.45 + 0.9 * i / 16, 1.85 + 0.12 * math.sin(i / 16 * 4 * math.pi)) for i in range(17)],
         "neon_blue", d=-0.05, mounts=False)
    neon(kit, "S", y0, star(c[4], 1.85, 0.42, 0.17), "neon_red", d=-0.05, closed=True, mounts=False)
    neon(kit, "S", y0, [(3.0 + x * 1.2, 1.4 + z * 0.95) for x, z in BOTTLE], "neon_green", d=-0.05, closed=True, mounts=False)
    # the doors
    tc.hinged_door(kit, col, root, "S", y0, 5.5, 1.2, 2.3, depth=0.1, leaf="door_red", index=1, style="panel", glass="bk_dark")
    tc.hinged_door(kit, col, root, "E", x1, -1.0, 1.0, 2.2, depth=0.1, leaf="metal_galv", index=2)
    tc.hinged_door(kit, col, root, "N", y1, -9.5, 1.0, 2.2, depth=0.1, leaf="darkwood", index=4, style="glass", glass="bk_dark")
    tc.wbox(kit.p("Sill", "stone"), "S", y0, 4.8, 6.2, 0.0, 0.02, -0.2, 0.06, skip="back")

    # ---------------------------------------------------------------- the porch (lot side)
    pd, py0 = p["porch"], y0 - p["porch"]
    kit.p("Porch", "deck").box((x0 - 0.2, py0, -0.25), (x1 + 0.2, y0, 0.0), skip="b")
    kit.p("Porch", "trim_black").box((x0 - 0.22, py0 - 0.03, -0.25), (x1 + 0.22, py0, -0.02), skip="bk")
    kit.collide((x0 - 0.2, py0, -0.25), (x1 + 0.2, y0, 0.0))
    zp_w, zp_o = H - 0.35, H - 0.35 - pd * 0.18
    posts = [x0 + 0.3 + i * (x1 - x0 - 0.6) / 7 for i in range(8)]
    Pp = kit.p("PorchPosts", "cedar")
    for x in posts:
        Pp.box((x - 0.1, py0 + 0.1, 0.0), (x + 0.1, py0 + 0.3, zp_o - 0.2), skip="bt")
        kit.collide((x - 0.1, py0 + 0.1, 0), (x + 0.1, py0 + 0.3, zp_o - 0.2))
    kit.p("PorchBeam", "cedar").box((x0 - 0.1, py0 + 0.08, zp_o - 0.22), (x1 + 0.1, py0 + 0.32, zp_o))
    tc.shed_roof(kit, x0 - 0.2, x1 + 0.2, y0, py0 + 0.2, zp_w, zp_o, roof=p["roof"], soffit="deck", fascia="trim_black")
    for x in (posts[1], posts[3], posts[5]):                     # bare bulbs under the porch
        kit.p("PorchBulbs", "lamp").cyl((x + 0.9, py0 + 1.2), 0.06, zp_o - 0.06, zp_o + 0.08, sides=6, caps="b")
    # neon BAR over the door, on a black board hung from the porch beam
    kit.p("PorchSign", "trim_black").box((4.1, py0 + 0.18, zp_o - 1.05), (7.0, py0 + 0.24, zp_o - 0.3))
    for x in (4.3, 6.8):
        kit.p("PorchSign", "chrome").tube(V(x, py0 + 0.21, zp_o - 0.3), V(x, py0 + 0.21, zp_o - 0.22), 0.008, 3)
    neon_word(kit, "S", py0 + 0.18, "BAR", 4.45, zp_o - 0.95, 0.55, "neon_red", d=0.03, r=0.02)
    neon(kit, "S", py0 + 0.18, [(4.2, zp_o - 1.0), (6.9, zp_o - 1.0), (6.9, zp_o - 0.35), (4.2, zp_o - 0.35)], "neon_amber",
         d=0.03, r=0.01, closed=True, mounts=False)
    # the roof sign: a lit cocktail glass on black steel, red neon round it, an amber arrow
    sx0, sx1, sz0, sz1, sy = -7.0, -3.0, 5.2, 7.2, y0 + 2.0
    S = kit.p("SignSteel", "trim_black")
    roof_z = H + (sy - y0) * p["pitch"] + 0.1
    for x in (sx0 + 0.5, sx1 - 0.5):
        S.box((x - 0.07, sy, roof_z - 0.3), (x + 0.07, sy + 0.14, sz0 + 0.3))
        S.beam((x, sy + 0.14, sz0 + 1.0), (x, sy + 1.6, roof_z + 0.4), 0.06, 0.06)
    S.box((sx0 - 0.08, sy - 0.12, sz0 - 0.08), (sx1 + 0.08, sy, sz1 + 0.08))
    kit.p("Sign", "signs", glow=True).face([(sx0, sy - 0.125, sz0), (sx1, sy - 0.125, sz0), (sx1, sy - 0.125, sz1),
                                           (sx0, sy - 0.125, sz1)], uvs=tc.sign_uv("bar"), toward=(0, -1, 0))
    neon(kit, "S", sy - 0.12, [(sx0 - 0.25, sz0 - 0.25), (sx1 + 0.25, sz0 - 0.25), (sx1 + 0.25, sz1 + 0.25),
                                (sx0 - 0.25, sz1 + 0.25)], "neon_red", d=0.06, closed=True, r=0.02)
    neon(kit, "S", sy - 0.12, [(sx1 + 0.6, sz1 - 0.2), (sx1 + 1.6, sz0 + 0.4), (sx1 + 2.4, sz0 - 0.3)], "neon_amber", d=0.06, r=0.025)
    neon(kit, "S", sy - 0.12, [(sx1 + 2.0, sz0 - 0.4), (sx1 + 2.4, sz0 - 0.3), (sx1 + 2.35, sz0 + 0.1)], "neon_amber", d=0.06, r=0.025)
    # the stone chimney at the stage end, the back, kegs, a dumpster
    tc.chimney(kit, x0 - 0.45, 0.0, 0.0, ridge + 0.9, w=0.9, d=1.6, mat="fieldstone")
    kit.collide((x0 - 0.9, -0.8, 0), (x0, 0.8, ridge + 0.9))
    tc.gooseneck(kit, "E", x1, -1.0, 2.7, arm=0.35)
    tc.hvac(kit, x1 + 0.9, 2.5)
    tc.meter(kit, "E", x1, 1.2)
    D = kit.p("Dumpster", "trim_green")
    D.box((x1 + 0.5, -5.6, 0.15), (x1 + 1.9, -3.6, 1.3))
    kit.p("Dumpster", "rubber").box((x1 + 0.45, -5.65, 1.3), (x1 + 1.95, -3.55, 1.38))
    kit.collide((x1 + 0.5, -5.6, 0), (x1 + 1.9, -3.6, 1.38))
    for i in range(3):
        kit.p("Kegs", "metal_galv").cyl((x1 + 0.4 + 0.42 * (i % 2), 0.4 + 0.45 * (i // 2)), 0.2, 0.0, 0.6, sides=8)
    kit.collide((x1, 0.1, 0), (x1 + 1.0, 1.1, 0.6))

    # ---------------------------------------------------------------- the river deck
    dx0, dx1, dy1 = x0 - 0.2, -2.0, y1 + p["deck"]
    kit.p("RiverDeck", "deck").box((dx0, y1, -0.25), (dx1, dy1, 0.0), skip="b")
    kit.collide((dx0, y1, -0.25), (dx1, dy1, 0.0))
    for x in [dx0 + 0.2 + i * (dx1 - dx0 - 0.4) / 5 for i in range(6)]:
        kit.p("DeckPosts", "cedar").box((x - 0.1, dy1 - 0.3, -p["water_drop"]), (x + 0.1, dy1 - 0.1, -0.25), skip="bt")
    tc.railing(kit, (dx0 + 0.05, dy1 - 0.05), (-6.9, dy1 - 0.05), 0.0, h=1.0, mat="cedar", style="bars", spacing=0.16)
    tc.railing(kit, (-5.1, dy1 - 0.05), (dx1 - 0.05, dy1 - 0.05), 0.0, h=1.0, mat="cedar", style="bars", spacing=0.16)
    tc.railing(kit, (dx0 + 0.05, y1 + 0.05), (dx0 + 0.05, dy1 - 0.05), 0.0, h=1.0, mat="cedar", style="bars", spacing=0.16)
    tc.railing(kit, (dx1 - 0.05, y1 + 0.05), (dx1 - 0.05, dy1 - 0.05), 0.0, h=1.0, mat="cedar", style="bars", spacing=0.16)
    tc.steps(kit, -6.9, -5.1, dy1, 0.0, n=10, run=0.3, direction=1, mat="deck", stringer="cedar",
             z_bottom=-p["water_drop"])
    for (tx, ty) in ((-11.5, y1 + 1.5), (-8.0, y1 + 1.6), (-3.8, y1 + 1.5)):
        tc.table(kit, tx, ty, w=0.8, h=0.75, round_=True, top="deck", base="trim_black")
    fest = [V(dx0 + 0.3 + (dx1 - dx0 - 0.6) * i / 16, dy1 - 0.2, 2.7 - 0.4 * math.sin(math.pi * i / 16)) for i in range(17)]
    kit.p("Cords", "trim_black").polyline(fest, 0.006, sides=3)
    for q in fest[1:-1:2]:
        kit.p("Festoon", "lamp").cyl((q.x, q.y), 0.035, q.z - 0.1, q.z - 0.02, sides=5, caps="tb")
    for x in (dx0 + 0.3, dx1 - 0.3):
        kit.p("DeckPosts", "cedar").box((x - 0.06, dy1 - 0.26, 0.0), (x + 0.06, dy1 - 0.14, 2.8), skip="b")

    # ================================================================ the bar room
    rx0, rx1 = xi0, XP - T / 2
    hall_door = (-1.5, -0.5, 0.0, 2.2)
    back_door = (4.4, 5.4, 0.0, 2.2)                   # to the back room, at the bar's end
    kit.sub = 0.7
    tc.room(kit, rx0, rx1, yi0, yi1, 0.0, C, walls="brick_red", floor="woodfloor", ceiling="trim_black",
            wainscot="darkwood", wainscot_h=1.1, base="trim_black", name="Bar",
            openings={"S": [door_f] + win_s[:6], "E": [hall_door, back_door], "W": win_w, "N": [door_r, win_n[0]]})
    kit.sub = None
    tc.reveals(rv, "E", XP + T / 2, [hall_door, back_door], T, sill=False)
    tc.wall_collider(kit, "y", XP, y0, y1, T, C, [(hall_door[0], hall_door[1]), (back_door[0], back_door[1])])
    Bm = kit.p("Beams", "darkwood")
    for x in [rx0 + 1.5 + i * 2.6 for i in range(8)]:
        Bm.box((x - 0.12, yi0, C - 0.3), (x + 0.12, yi1, C), skip="t")
    for fx, fy in ((-6.0, -1.0), (1.5, -1.0)):
        F = kit.p("Fans", "trim_black")
        F.cyl((fx, fy), 0.02, C - 0.55, C - 0.3, sides=4, caps="")
        F.cyl((fx, fy), 0.12, C - 0.68, C - 0.55, sides=8, caps="tb")
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2 + 0.2
            hub = V(fx, fy, C - 0.62)
            tip = V(fx + math.cos(a) * 0.62, fy + math.sin(a) * 0.62, C - 0.62)
            kit.p("Fans", "darkwood").beam(hub.lerp(tip, 0.2), tip, 0.13, 0.01)

    # ---------------------------------------------------------------- the bar and back bar
    bx0, bx1, by_f, by_b = -7.4, 6.6, 3.4, 4.15            # 14 m
    Dk = kit.p("BarFront", "darkwood")
    Dk.box((bx0, by_f + 0.05, 0.0), (bx1, by_b - 0.05, 1.0), skip="bt")
    Dk.box((bx1 - 0.05, by_f + 0.05, 0.0), (bx1, yi1 - 0.7, 1.0), skip="bt") if False else None
    for x in [bx0 + 0.58 + i * 1.165 for i in range(12)]:
        Dk.box((x - 0.48, by_f + 0.03, 0.18), (x + 0.48, by_f + 0.05, 0.85), skip="k")
    Vt = kit.p("BarTop", "varnish")
    Vt.box((bx0 - 0.1, by_f - 0.12, 1.0), (bx1 + 0.1, by_b + 0.05, 1.07))
    kit.p("BarGlow", "neon_amber").face([(bx0, by_f - 0.1, 0.995), (bx1, by_f - 0.1, 0.995), (bx1, by_f + 0.02, 0.995),
                                         (bx0, by_f + 0.02, 0.995)], toward=(0, 0, -1))
    Br = kit.p("Brass", "brass")
    Br.tube(V(bx0 + 0.1, by_f - 0.2, 0.22), V(bx1 - 0.1, by_f - 0.2, 0.22), 0.025, 6)
    for x in (bx0 + 0.3, bx0 + 4.7, bx0 + 9.3, bx1 - 0.3):
        Br.tube(V(x, by_f - 0.2, 0.22), V(x, by_f + 0.05, 0.3), 0.012, 4)
    kit.collide((bx0 - 0.1, by_f - 0.12, 0), (bx1 + 0.1, by_b + 0.05, 1.07))
    for x in (-5.0, -1.0, 3.0):
        Ch = kit.p("Taps", "chrome")
        Ch.box((x - 0.25, by_f + 0.25, 1.07), (x + 0.25, by_f + 0.4, 1.12))
        Ch.tube(V(x, by_f + 0.32, 1.12), V(x, by_f + 0.32, 1.42), 0.03, 6)
        Ch.box((x - 0.24, by_f + 0.26, 1.38), (x + 0.24, by_f + 0.38, 1.46))
        for k, colr in enumerate(("paint_orange", "paint_teal", "paint_yellow", "paint_red")):
            hx = x - 0.18 + k * 0.12
            kit.p("TapHandles", colr).box((hx - 0.018, by_f + 0.18, 1.34), (hx + 0.018, by_f + 0.22, 1.56))
    kit.p("Register", "metal_dark").box((5.3, by_f + 0.3, 1.07), (5.75, by_f + 0.7, 1.25))
    kit.p("Register", "glow_cool").face([(5.32, by_f + 0.29, 1.15), (5.73, by_f + 0.29, 1.15), (5.73, by_f + 0.29, 1.23),
                                         (5.32, by_f + 0.29, 1.23)], toward=(0, -1, 0))
    for i in range(13):
        tc.stool(kit, bx0 + 0.55 + i * (bx1 - bx0 - 1.1) / 12, by_f - 0.55, h=0.76)
    bb_f = yi1 - 0.6
    Dk2 = kit.p("BackBar", "darkwood")
    Dk2.box((bx0, bb_f, 0.0), (bx1, yi1, 0.95), skip="bk")
    kit.p("BackBarTop", "varnish").box((bx0 - 0.05, bb_f - 0.05, 0.95), (bx1 + 0.05, yi1, 1.0), skip="k")
    for x in [bx0 + 0.3 + i * 0.9 for i in range(15)]:
        Dk2.box((x - 0.38, bb_f - 0.02, 0.1), (x + 0.38, bb_f, 0.85), skip="k")
    kit.collide((bx0 - 0.05, bb_f - 0.05, 0), (bx1 + 0.05, yi1, 1.0))
    bays = [(bx0 + 0.2, -3.0), (-2.6, 1.6), (2.0, bx1 - 0.2)]
    Mr = kit.p("Mirror", "mirror")
    for a0, a1 in bays:
        Mr.face([(a0, yi1 - 0.01, 1.05), (a1, yi1 - 0.01, 1.05), (a1, yi1 - 0.01, 2.5), (a0, yi1 - 0.01, 2.5)], toward=(0, -1, 0))
    for x in (bx0, -2.8, 1.8, bx1):
        Dk2.box((x - 0.15, yi1 - 0.3, 1.0), (x + 0.15, yi1, 2.75), skip="kb")
    Dk2.box((bx0 - 0.15, yi1 - 0.42, 2.5), (bx1 + 0.15, yi1, 2.8), skip="k")
    Sh = kit.p("Shelves", "trim_black")
    for zs in (1.22, 1.66, 2.1):
        for a0, a1 in bays:
            Sh.box((a0, yi1 - 0.3, zs - 0.025), (a1, yi1 - 0.01, zs), skip="k")
            kit.p("ShelfGlow", "neon_amber").face([(a0, yi1 - 0.29, zs - 0.027), (a1, yi1 - 0.29, zs - 0.027),
                                                   (a1, yi1 - 0.22, zs - 0.027), (a0, yi1 - 0.22, zs - 0.027)], toward=(0, 0, -1))
            x = a0 + 0.12
            while x < a1 - 0.1:
                if rng.random() > 0.18:
                    tc.bottle(kit, x, yi1 - 0.16 + rng.uniform(-0.05, 0.05), zs, kind=rng.randrange(5), glow=zs > 1.5)
                x += rng.uniform(0.19, 0.28)
    cx, cz = -0.5, 3.05
    neon(kit, "S", yi1, [(cx - 0.5, cz + 0.4), (cx + 0.5, cz + 0.4), (cx, cz - 0.08), (cx - 0.5, cz + 0.4)], "neon_pink", d=-0.06, r=0.015)
    neon(kit, "S", yi1, [(cx, cz - 0.08), (cx, cz - 0.33)], "neon_pink", d=-0.06, r=0.015)
    neon(kit, "S", yi1, arc((cx + 0.2, cz + 0.29), 0.08, 0, 2 * math.pi, 8), "neon_green", d=-0.07, r=0.012)
    for x in (-6.0, -3.0, 0.0, 3.0, 5.8):
        pz = 2.3
        kit.p("Cords", "trim_black").tube(V(x, 3.8, pz + 0.25), V(x, 3.8, C), 0.006, 3)
        Cg = kit.p("Cages", "trim_black")
        Cg.cyl((x, 3.8), 0.13, pz + 0.18, pz + 0.25, sides=8, caps="b")
        for k in range(4):
            a = k * math.pi / 2
            Cg.tube(V(x + 0.11 * math.cos(a), 3.8 + 0.11 * math.sin(a), pz + 0.18),
                    V(x + 0.09 * math.cos(a), 3.8 + 0.09 * math.sin(a), pz - 0.05), 0.006, 3)
        kit.p("Bulbs", "lamp").cyl((x, 3.8), 0.065, pz - 0.03, pz + 0.17, sides=6, caps="tb")
        kit.light((x, 3.8, 2.35), (1.0, 0.66, 0.36), 45, 0.08)
    kit.p("TV", "metal_dark").box((rx1 - 0.12, 1.6, 2.2), (rx1, 3.0, 3.0))
    kit.p("TV", "glow_cool").face([(rx1 - 0.125, 1.65, 2.25), (rx1 - 0.125, 2.95, 2.25), (rx1 - 0.125, 2.95, 2.95),
                                   (rx1 - 0.125, 1.65, 2.95)], toward=(-1, 0, 0))

    # ---------------------------------------------------------------- the booths
    for xc in booths:
        yb0, yb1 = yi0, yi0 + 1.3
        for s in (-1, 1):
            xb, xo = xc + s * 0.375, xc + s * 0.95
            lo, hi = sorted((xb, xo))
            kit.p("BoothFrames", "darkwood").box((lo, yb0, 0.0), (hi, yb1, 0.36), skip="b")
            kit.p("BoothSeats", "vinyl_red").box((lo, yb0, 0.36), (hi, yb1 - 0.02, 0.46))
            bl, bh_ = sorted((xo, xo - s * 0.1))
            kit.p("BoothFrames", "darkwood").box((bl, yb0, 0.0), (bh_, yb1, 1.18), skip="b")
            cl, ch = sorted((xo - s * 0.1, xo - s * 0.2))
            kit.p("BoothSeats", "vinyl_red").box((cl, yb0, 0.46), (ch, yb1 - 0.04, 1.12), skip="b")
            kit.collide((lo, yb0, 0), (hi, yb1, 0.46))
            kit.collide((bl, yb0, 0), (bh_, yb1, 1.18))
        tc.table(kit, xc, yb0 + 0.62, w=0.72, d=1.1, h=0.76)
        kit.p("BoothLamps", "trim_black").cyl((xc, yb0 + 0.62), 0.2, 1.75, 1.95, sides=8, caps="", r1=0.05)
        kit.p("BoothLamps", "lamp").cyl((xc, yb0 + 0.62), 0.19, 1.755, 1.76, sides=8, caps="b")
        kit.p("Cords", "trim_black").tube(V(xc, yb0 + 0.62, 1.95), V(xc, yb0 + 0.62, C), 0.006, 3)
        kit.p("Tabletop", "chrome").cyl((xc - 0.12, yb0 + 0.3), 0.02, 0.76, 0.86, sides=5)
        kit.p("Tabletop", "chrome").cyl((xc - 0.06, yb0 + 0.3), 0.02, 0.76, 0.86, sides=5)
        kit.p("Tabletop", "neon_red").cyl((xc + 0.1, yb0 + 0.32), 0.035, 0.76, 0.84, sides=6)
        kit.light((xc, yb0 + 0.62, 1.72), (1.0, 0.66, 0.36), 40, 0.15, kind="SPOT")

    # ---------------------------------------------------------------- the pool table
    px, py = -3.0, -1.0
    L, Wd = 1.35, 0.75
    Pt = kit.p("PoolRails", "varnish")
    for (a0, b0, a1, b1) in ((-L, -Wd, L, -Wd + 0.12), (-L, Wd - 0.12, L, Wd), (-L, -Wd, -L + 0.12, Wd), (L - 0.12, -Wd, L, Wd)):
        Pt.box((px + a0, py + b0, 0.62), (px + a1, py + b1, 0.81))
    kit.p("Felt", "felt").box((px - L + 0.12, py - Wd + 0.12, 0.62), (px + L - 0.12, py + Wd - 0.12, 0.77), skip="b")
    for (a0, b0, a1, b1) in ((-L + 0.12, -Wd + 0.12, L - 0.12, -Wd + 0.16), (-L + 0.12, Wd - 0.16, L - 0.12, Wd - 0.12),
                             (-L + 0.12, -Wd + 0.16, -L + 0.16, Wd - 0.16), (L - 0.16, -Wd + 0.16, L - 0.12, Wd - 0.16)):
        kit.p("Felt", "felt").box((px + a0, py + b0, 0.77), (px + a1, py + b1, 0.8), skip="b")
    kit.p("PoolApron", "darkwood").box((px - L + 0.04, py - Wd + 0.04, 0.5), (px + L - 0.04, py + Wd - 0.04, 0.62), skip="t")
    for sx in (-1, 1):
        kit.p("PoolLegs", "darkwood").box((px + sx * 0.95 - 0.15, py - 0.55, 0.0), (px + sx * 0.95 + 0.15, py + 0.55, 0.5), skip="bt")
    for (a, b) in ((-L + 0.06, -Wd + 0.06), (0, -Wd + 0.05), (L - 0.06, -Wd + 0.06), (-L + 0.06, Wd - 0.06), (0, Wd - 0.05),
                   (L - 0.06, Wd - 0.06)):
        kit.p("Pockets", "tar").box((px + a - 0.06, py + b - 0.06, 0.805), (px + a + 0.06, py + b + 0.06, 0.812), skip="b")
    kit.collide((px - L, py - Wd, 0), (px + L, py + Wd, 0.81))
    cols = ("paint_yellow", "paint_blue", "paint_red", "trim_bronze", "paint_orange", "trim_green", "door_red", "trim_black",
            "paint_yellow", "paint_blue")
    k = 0
    for row in range(4):
        for j in range(row + 1):
            kit.p("Balls", cols[k % len(cols)]).cyl((px + 0.55 + row * 0.05, py + (j - row / 2) * 0.058), 0.028, 0.77, 0.826,
                                                    sides=6, caps="t")
            k += 1
    kit.p("Balls", "paint_white").cyl((px - 0.6, py + 0.1), 0.028, 0.77, 0.826, sides=6, caps="t")
    kit.p("Cues", "varnish").beam(V(px - 0.9, py - 0.3, 0.83), V(px + 0.4, py - 0.45, 0.82), 0.02, 0.02)
    lz = 1.55                                            # the one low hanging lamp: three shades on a bar
    kit.p("Brass", "brass").box((px - 1.0, py - 0.03, lz + 0.22), (px + 1.0, py + 0.03, lz + 0.27))
    for dx in (-0.75, 0.0, 0.75):
        kit.p("LampShades", "trim_green").cyl((px + dx, py), 0.24, lz, lz + 0.2, sides=8, caps="", r1=0.08)
        kit.p("LampShades", "lamp").cyl((px + dx, py), 0.23, lz + 0.005, lz + 0.01, sides=8, caps="b")
        kit.light((px + dx, py, lz - 0.02), (1.0, 0.8, 0.55), 55, 0.18, kind="SPOT")
    for dx in (-0.9, 0.9):
        kit.p("Cords", "brass").tube(V(px + dx, py, lz + 0.27), V(px + dx, py, C), 0.008, 3)
    Rk = kit.p("CueRack", "varnish")
    Rk.box((xi0, 4.4, 0.9), (xi0 + 0.05, 5.6, 1.0))
    Rk.box((xi0, 4.4, 1.7), (xi0 + 0.05, 5.6, 1.8))
    for k in range(6):
        kit.p("Cues", "varnish").beam(V(xi0 + 0.06, 4.5 + k * 0.2, 0.05), V(xi0 + 0.06, 4.5 + k * 0.2, 1.6), 0.025, 0.025)
    for rr, colr, d in ((0.3, "trim_black", 0.01), (0.22, "paint_red", 0.015), (0.16, "paper", 0.018), (0.08, "trim_green", 0.021),
                        (0.03, "paint_red", 0.024)):
        ring = [(-2.6 + rr * math.cos(2 * math.pi * i / 12), 1.73 + rr * math.sin(2 * math.pi * i / 12)) for i in range(12)]
        kit.p("Dart", colr).face([(rx1 - d, a, z) for a, z in ring[::-1]], toward=(-1, 0, 0))
    kit.p("Dart", "trim_black").box((rx1 - 0.01, -3.05, 1.25), (rx1, -2.15, 2.2))

    # ---------------------------------------------------------------- the stage
    st_x0, st_x1, st_y0, st_y1, st_h = xi0, -10.6, -3.5, 3.5, 0.45
    kit.p("Stage", "darkwood").box((st_x0, st_y0, 0.0), (st_x1, st_y1, st_h), skip="bl")
    kit.p("StageEdge", "trim_black").box((st_x1, st_y0, 0.0), (st_x1 + 0.03, st_y1, st_h + 0.02), skip="b")
    kit.collide((st_x0, st_y0, 0), (st_x1, st_y1, st_h))
    tc.steps(kit, -12.6, -11.6, st_y1, st_h, direction=1, mat="darkwood", z_bottom=0.0)
    Cr = kit.p("Curtain", "trim_red")
    k = 28
    for i in range(k):
        ya = st_y0 - 0.3 + (st_y1 - st_y0 + 0.6) * i / k
        yb = st_y0 - 0.3 + (st_y1 - st_y0 + 0.6) * (i + 1) / k
        xa, xb = xi0 + (0.02 if i % 2 == 0 else 0.1), xi0 + (0.1 if i % 2 == 0 else 0.02)
        Cr.face([(xa, ya, st_h), (xb, yb, st_h), (xb, yb, C - 0.05), (xa, ya, C - 0.05)], toward=(1, 0, 0))
    kit.p("CurtainRod", "brass").tube(V(xi0 + 0.06, st_y0 - 0.35, C - 0.08), V(xi0 + 0.06, st_y1 + 0.35, C - 0.08), 0.02, 5)
    stp = [(a, b - 2.3) for a, b in star(0.0, 2.3, 0.85, 0.36)]
    neon(kit, "E", xi0 + 0.1, [(a, 2.2 + b) for a, b in stp], "neon_blue", d=0.08, closed=True, r=0.018)
    neon(kit, "E", xi0 + 0.1, [(a * 0.8, 2.2 + b * 0.8) for a, b in stp], "neon_blue", d=0.08, closed=True, r=0.012)
    neon(kit, "E", xi0 + 0.1, [(-2.3, 3.1), (-1.85, 2.45), (-2.15, 2.4), (-1.6, 1.5)], "neon_red", d=0.08, r=0.018)
    neon(kit, "E", xi0 + 0.1, [(2.3, 3.1), (1.85, 2.45), (2.15, 2.4), (1.6, 1.5)], "neon_red", d=0.08, r=0.018)
    pts = [V(st_x1 + 0.1, st_y0 + (st_y1 - st_y0) * i / 20, C - 0.35 - 0.4 * math.sin(math.pi * i / 20)) for i in range(21)]
    kit.p("Cords", "trim_black").polyline(pts, 0.006, sides=3)
    for q in pts[1:-1]:
        kit.p("Festoon", "lamp").cyl((q.x, q.y), 0.035, q.z - 0.1, q.z - 0.02, sides=5, caps="tb")
    dz = st_h
    Dr = kit.p("Drums", "paint_red")
    Dr.tube(V(-12.95, 0.6, dz + 0.3), V(-12.55, 0.6, dz + 0.3), 0.28, 10)
    kit.p("DrumHeads", "paper").face([V(-12.55, 0.6 + 0.28 * math.cos(2 * math.pi * i / 10), dz + 0.3 + 0.28 * math.sin(2 * math.pi * i / 10))
                                      for i in range(10)], toward=(1, 0, 0))
    for (ty, tz, tr) in ((0.15, 0.75, 0.13), (1.0, 0.72, 0.15)):
        Dr.cyl((-12.6, ty), tr, dz + tz, dz + tz + 0.16, sides=8, caps="")
        kit.p("DrumHeads", "paper").cyl((-12.6, ty), tr, dz + tz + 0.16, dz + tz + 0.165, sides=8)
    Cb, Chs = kit.p("Cymbals", "brass"), kit.p("Stands", "chrome")
    for (cx_, cy_, cz_) in ((-12.4, -0.35, 1.05), (-12.9, 1.45, 1.35), (-13.0, -0.15, 1.45)):
        Cb.cyl((cx_, cy_), 0.22, dz + cz_, dz + cz_ + 0.015, sides=10, caps="tb")
        Chs.tube(V(cx_, cy_, dz), V(cx_, cy_, dz + cz_), 0.01, 4)
    for sy_ in (-2.5, 2.5):
        kit.p("Amps", "trim_black").box((-13.75, sy_ - 0.38, dz), (-13.3, sy_ + 0.38, dz + 1.25))
        kit.p("AmpGrille", "screen").face([(-13.299, sy_ - 0.32, dz + 0.1), (-13.299, sy_ + 0.32, dz + 0.1),
                                           (-13.299, sy_ + 0.32, dz + 0.95), (-13.299, sy_ - 0.32, dz + 0.95)], toward=(1, 0, 0))
        kit.p("AmpGrille", "neon_red").box((-13.3, sy_ + 0.25, dz + 1.1), (-13.29, sy_ + 0.3, dz + 1.15))
    for my in (-1.2, 1.4):
        Chs.cyl((-11.2, my), 0.16, dz, dz + 0.02, sides=6)
        Chs.tube(V(-11.2, my, dz), V(-11.2, my, dz + 1.45), 0.012, 4)
        Chs.tube(V(-11.2, my, dz + 1.45), V(-11.0, my, dz + 1.55), 0.01, 4)
        kit.p("Mics", "trim_black").cyl((-10.98, my), 0.028, dz + 1.53, dz + 1.62, sides=6)
    for (hx, hy) in ((-9.2, 2.0), (-9.2, -1.6)):
        tc.table(kit, hx, hy, w=0.7, h=1.05, round_=True)
        for a in (0.4, 0.4 + math.pi):
            tc.stool(kit, hx + 0.55 * math.cos(a), hy + 0.55 * math.sin(a), h=0.76, seat="vinyl_black")
    for yy in (-2.5, 0.0, 2.5):
        kit.light((st_x1 + 0.1, yy, C - 0.6), (1.0, 0.66, 0.36), 10, 0.1)
    kit.light((xi0 + 0.5, 0.0, 2.2), (0.25, 0.4, 1.0), 30, 0.6)
    kit.light((xi0 + 0.5, -2.0, 2.3), (1.0, 0.1, 0.06), 8, 0.3)
    kit.light((xi0 + 0.5, 2.0, 2.3), (1.0, 0.1, 0.06), 8, 0.3)
    kit.light((-11.6, 0.2, 2.9), (1.0, 0.8, 0.6), 60, 0.1, kind="SPOT", direction=(-0.6, 0.0, -0.8))

    # ---------------------------------------------------------------- the jukebox, by the stage
    jx0, jx1, jy0, jy1 = -10.15, -9.15, yi0, yi0 + 0.68          # against the front wall, facing +Y
    J = kit.p("Jukebox", "varnish")
    J.box((jx0, jy0, 0.0), (jx1, jy1, 1.0), skip="b")
    jc, jr = (jx0 + jx1) / 2, (jx1 - jx0) / 2
    archp = arc((jc, 1.0), jr, 0, math.pi, 10)
    J.face([(a, jy0, z) for a, z in archp], toward=(0, -1, 0))
    J.face([(a, jy1, z) for a, z in archp[::-1]], toward=(0, 1, 0))
    for i in range(10):
        (a0_, z0_), (a1_, z1_) = archp[i], archp[i + 1]
        J.face([(a0_, jy0, z0_), (a0_, jy1, z0_), (a1_, jy1, z1_), (a1_, jy0, z1_)], toward=(a0_ - jc, 0, z0_ - 1.0))
    neon(kit, "N", jy1, arc((jc, 1.0), jr - 0.05, 0, math.pi, 10), "neon_amber", d=0.03, r=0.02, mounts=False)
    neon(kit, "N", jy1, arc((jc, 1.0), jr - 0.16, 0, math.pi, 8), "neon_pink", d=0.03, r=0.016, mounts=False)
    for a in (jx0 + 0.07, jx1 - 0.07):
        kit.p("Neon", "neon_blue").tube(V(a, jy1 + 0.03, 0.1), V(a, jy1 + 0.03, 1.0), 0.02, 5)
    kit.p("JukeFace", "lamp").face([(jx0 + 0.2, jy1 + 0.005, 0.62), (jx1 - 0.2, jy1 + 0.005, 0.62), (jx1 - 0.2, jy1 + 0.005, 0.92),
                                    (jx0 + 0.2, jy1 + 0.005, 0.92)], toward=(0, 1, 0))
    for k in range(5):
        z = 0.15 + k * 0.08
        kit.p("JukeGrille", "chrome").box((jx0 + 0.18, jy1, z), (jx1 - 0.18, jy1 + 0.02, z + 0.025), skip="f")
    kit.collide((jx0, jy0, 0), (jx1, jy1, 1.5))
    kit.light((jc, jy1 + 0.4, 1.2), (1.0, 0.45, 0.3), 16, 0.3)

    # ================================================================ the back: hall, restrooms, the back room
    hx0, hx1 = XP + T / 2, xi1
    hy0, hy1 = -2.0 + T / 2, 0.0 - T / 2
    room_door = (10.5, 11.5, 0.0, 2.2)
    rest_doors = [(8.8, 9.7, 0.0, 2.1), (12.1, 13.0, 0.0, 2.1)]
    kit.sub = 0.8
    tc.room(kit, hx0, hx1, hy0, hy1, 0.0, CB, walls="plaster", floor="checker", ceiling="plaster", name="Hall",
            base="trim_black", openings={"W": [hall_door], "E": [door_x], "N": [room_door], "S": rest_doors})
    for a0, a1, z0, z1 in rest_doors:
        tc.door(kit, "N", hy0, (a0 + a1) / 2, a1 - a0, z1 - z0, leaf="darkwood", trim="trim_black",
                wall_part=kit.p("HallWalls", "plaster"), casing=0.07)
    tc.reveals(rv, "N", hy1 + T, [room_door], T, sill=False)
    tc.wall_collider(kit, "x", 0.0, XP, x1, T, CB, [(room_door[0], room_door[1])])
    tc.wall_collider(kit, "x", -2.0, XP, x1, T, CB)
    kit.p("ExitGlow", "neon_green").box((hx1 - 0.06, -1.2, 2.45), (hx1, -0.8, 2.62))
    kit.p("HallLight", "glow_white").face([(9.0, -1.2, CB - 0.01), (12.8, -1.2, CB - 0.01), (12.8, -0.8, CB - 0.01),
                                           (9.0, -0.8, CB - 0.01)], toward=(0, 0, -1))
    kit.light((11.0, -1.0, CB - 0.05), (0.8, 0.88, 1.0), 14, 1.2, kind="AREA")
    # the back room (store room)
    ox0, ox1, oy0, oy1 = XP + T / 2, xi1, 0.0 + T / 2, yi1
    tc.room(kit, ox0, ox1, oy0, oy1, 0.0, CB, walls="block", floor="concrete", ceiling="plaster", name="BackRoom",
            base="trim_black", openings={"S": [room_door], "W": [back_door], "N": [win_n[1]]})
    kit.sub = None
    d3 = tc.hinged_door(kit, col, root, "E", XP + T / 2, (back_door[0] + back_door[1]) / 2, 1.0, 2.2, depth=0.1,
                        leaf="darkwood", index=3, swing=1)
    d3.rotation_euler.z = math.radians(28)              # left ajar (the shot)
    d3["town_ajar_deg"] = 28
    tc.hinged_door(kit, col, root, "N", hy1 + T, (room_door[0] + room_door[1]) / 2, 1.0, 2.2, depth=0.1, leaf="darkwood",
                   index=5, swing=-1)
    kit.p("BackRoomLight", "glow_white").face([(10.0, 2.6, CB - 0.01), (11.6, 2.6, CB - 0.01), (11.6, 3.0, CB - 0.01),
                                               (10.0, 3.0, CB - 0.01)], toward=(0, 0, -1))
    kit.light((10.8, 2.8, CB - 0.05), (0.9, 0.92, 1.0), 10, 1.0, kind="AREA")
    # the table in the middle, chairs, a bare bulb over it
    tc.table(kit, 11.0, 3.0, w=1.8, d=0.9, h=0.76, top="deck", base="metal_dark")
    for (cx_, cy_) in ((10.4, 2.3), (11.6, 2.3), (10.4, 3.7), (11.6, 3.7)):
        kit.p("Chairs", "metal_dark").box((cx_ - 0.2, cy_ - 0.2, 0.44), (cx_ + 0.2, cy_ + 0.2, 0.48))
        kit.p("Chairs", "metal_dark").box((cx_ - 0.2, cy_ + (0.18 if cy_ > 3 else -0.22), 0.48), (cx_ + 0.2, cy_ + (0.22 if cy_ > 3 else -0.18), 0.9))
        kit.collide((cx_ - 0.2, cy_ - 0.2, 0), (cx_ + 0.2, cy_ + 0.2, 0.48))
    kit.p("Cords", "trim_black").tube(V(11.0, 3.0, 2.1), V(11.0, 3.0, CB), 0.006, 3)
    kit.p("Bulbs", "lamp").cyl((11.0, 3.0), 0.06, 1.95, 2.12, sides=6, caps="tb")
    kit.light((11.0, 3.0, 1.9), (1.0, 0.7, 0.42), 30, 0.06)
    # the rail of hooks on the east wall (the layout hangs the masks here)
    kit.p("HookRail", "darkwood").box((ox1 - 0.04, 1.0, 1.65), (ox1, 4.6, 1.8))
    for k in range(10):
        hy = 1.2 + k * 0.36
        kit.p("Hooks", "metal_dark").box((ox1 - 0.14, hy - 0.01, 1.68), (ox1 - 0.04, hy + 0.01, 1.71))
        kit.p("Hooks", "metal_dark").box((ox1 - 0.15, hy - 0.01, 1.71), (ox1 - 0.13, hy + 0.01, 1.76))
    kit.info["hooks"] = {"rail": [round(ox1 - 0.15, 3), 1.0, 1.7, round(ox1, 3), 4.6, 1.8], "count": 10, "spacing": 0.36}
    # the monitor wall over a cabinet on the north wall, a safe, kegs and crates, the radios
    kit.p("Cabinet", "metal_dark").box((8.6, oy1 - 0.5, 0.0), (10.0, oy1, 0.9), skip="b")
    kit.collide((8.6, oy1 - 0.5, 0), (10.0, oy1, 0.9))
    for i in range(2):
        for j in range(3):
            mx, mz = 8.65 + i * 0.67, 1.1 + j * 0.5
            kit.p("Monitors", "metal_dark").box((mx, oy1 - 0.25, mz), (mx + 0.62, oy1 - 0.02, mz + 0.44))
            kit.p("Screens", "glow_cool").face([(mx + 0.04, oy1 - 0.255, mz + 0.04), (mx + 0.58, oy1 - 0.255, mz + 0.04),
                                                (mx + 0.58, oy1 - 0.255, mz + 0.4), (mx + 0.04, oy1 - 0.255, mz + 0.4)],
                                               toward=(0, -1, 0))
    kit.light((9.3, oy1 - 0.7, 1.8), (0.6, 0.75, 1.0), 20, 1.0, kind="AREA", direction=(0, -1, 0))
    kit.p("Safe", "metal_dark").box((ox1 - 0.75, oy1 - 0.75, 0.0), (ox1 - 0.05, oy1 - 0.05, 0.95), skip="b")
    kit.p("Safe", "chrome").cyl((ox1 - 0.4, oy1 - 0.76), 0.06, 0.5, 0.5, sides=6)
    kit.collide((ox1 - 0.75, oy1 - 0.75, 0), (ox1 - 0.05, oy1 - 0.05, 0.95))
    for i in range(6):
        kit.p("Kegs", "metal_galv").cyl((ox0 + 0.35 + (i % 3) * 0.45, oy0 + 0.35 + (i // 3) * 0.45), 0.2, 0.0, 0.6, sides=8)
    kit.collide((ox0 + 0.1, oy0 + 0.1, 0), (ox0 + 1.55, oy0 + 1.05, 0.6))
    for (cx_, cy_, cz_) in ((ox0 + 0.4, 3.6, 0.0), (ox0 + 0.4, 3.6, 0.32), (ox0 + 0.4, 4.15, 0.0)):
        kit.p("Crates", "deck").box((cx_ - 0.25, cy_ - 0.2, cz_), (cx_ + 0.25, cy_ + 0.2, cz_ + 0.3))
    kit.collide((ox0 + 0.1, 3.35, 0), (ox0 + 0.7, 4.4, 0.62))
    kit.p("Pegboard", "deck").box((ox1 - 0.02, 4.8, 1.0), (ox1, 5.6, 1.8)) if False else None
    kit.p("Pegboard", "deck").box((12.0, oy0, 1.1), (13.4, oy0 + 0.02, 1.9))
    for k in range(6):
        rx = 12.15 + k * 0.21
        kit.p("Radios", "metal_dark").box((rx, oy0 + 0.02, 1.2), (rx + 0.09, oy0 + 0.07, 1.45))
        kit.p("Radios", "trim_black").box((rx + 0.06, oy0 + 0.03, 1.45), (rx + 0.075, oy0 + 0.045, 1.62))
        kit.p("RadioLEDs", "neon_green").box((rx + 0.02, oy0 + 0.07, 1.4), (rx + 0.035, oy0 + 0.075, 1.415))

    # ================================================================ the rest of the bake's lamps
    amber = (1.0, 0.5, 0.15)
    for a0, a1 in bays:
        kit.light(((a0 + a1) / 2, yi1 - 0.35, 1.85), amber, 18, 0.3)
    kit.light((-0.5, yi1 - 0.35, 3.1), (1.0, 0.2, 0.5), 12, 0.3)
    kit.light((rx1 - 0.5, 2.3, 2.6), (0.6, 0.75, 1.0), 6, 0.3)
    for (xx, colr) in ((c[0], (1.0, 0.12, 0.06)), (c[1], (1.0, 0.55, 0.15)), (c[2], (1.0, 0.2, 0.5)), (c[3], (0.3, 0.45, 1.0)),
                       (c[4], (1.0, 0.12, 0.06))):
        kit.light((xx, y0 + 0.45, 1.85), colr, 5, 0.2)
    kit.light((bx0 + 0.3, by_f - 0.3, 0.9), amber, 4, 0.2)
    kit.light((bx1 - 0.3, by_f - 0.3, 0.9), amber, 4, 0.2)

    # ================================================================ LOD1
    far = tc.Far(n)
    far.gable(x0, x1, y0, y1, 0.0, H, ridge, axis="x", wall="paint_white", roof="metal_galv", over=0.5)
    for a0, a1, z0, z1 in win_s[:6]:
        far.quad("S", y0, a0, a1, z0, z1, "neon_red" if a0 < -8 else "window_lit", d=0.02)
    far.shed(x0 - 0.2, x1 + 0.2, y0, py0 + 0.2, zp_w, zp_o, roof="metal_galv")
    far.box((x0 - 0.2, py0, -0.25), (x1 + 0.2, y0, 0.0), "deck", skip="b")
    far.quad("S", sy, sx0, sx1, sz0, sz1, "neon_red", d=0.15)
    far.box((x0 - 0.9, -0.8, 0), (x0, 0.8, ridge + 0.9), "fieldstone", skip="b")
    far.box((dx0, y1, -0.25), (dx1, dy1, 0.0), "deck", skip="b")

    kit.entrance((5.5, py0 - 0.1, 0.0), "-Y", 1.2, kind="door", note="TownBar_Door_1, across the porch")
    kit.entrance((x1 + 0.1, -1.0, 0.0), "+X", 1.0, kind="door", note="TownBar_Door_2, back exit from the hall")
    kit.entrance((-9.5, y1 + 0.1, 0.0), "+Y", 1.0, kind="door", note="TownBar_Door_4, to the river deck (steps down at x -6.9..-5.1)")
    kit.info.update(walk_in=True, storeys=1,
                    rooms=["bar room 21.7 x 11.6 (14 m bar, back bar, 5 booths, pool table, jukebox, stage)",
                           "hall 5.8 x 1.8 (restroom doors closed, back exit)",
                           "back room 5.8 x 5.7 (table, hook rail, monitors, safe, kegs): TownBar_Door_3 ajar 28 deg from the bar's end"],
                    footprint=[round(x0 - 0.9, 3), round(py0 - 0.05, 3), round(x1 + 1.95, 3), round(dy1 + 10 * 0.3, 3)],
                    lighting="emissive only (M_Town_Glow) + lamps baked into COLOR_0")
    parts = tc.finish(kit, col, root, far)
    if p["bake"]:
        meshes = [o for o in root.children_recursive if o.type == "MESH" and not o.name.endswith("_LOD1")]
        town_light.bake(kit, root, meshes, [(rx0, yi0, 0.0, rx1, yi1, C), (hx0, hy0, 0.0, hx1, hy1, CB),
                                            (ox0, oy0, 0.0, ox1, oy1, CB)])
    return root, parts
