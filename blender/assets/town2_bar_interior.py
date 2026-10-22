"""The bar's interior (town2_bar.py): the 14 m bar (oxblood diamond-tufted vinyl front between
dark wood pilasters, a padded arm rail, a brass foot rail, a dark varnished top, beer towers)
and its stools; the back-bar (cabinets, a lit beer cooler, three tiers of bottles lit from
below in front of foxed mirrors, a cornice); six booths under the front windows, each with a
red glass candle lamp, neon in every window; a coin-op bar-box pool table mid-game under a
three-shade green lamp; a bubbler jukebox; the stage (pleated red curtain, a blue neon star,
drums, amps, a mic); café tables on the dance floor; ceiling fans; a CRT on a bracket; the
corridor (payphone, exit sign, the restroom doors); the back room (door ajar 28 deg: the hook
rail of white masks, a wall of security monitors, the briefing table with the estate's
blueprint, kegs, a safe).

Every lamp is a Kit.light (baked by the driver); emissive pieces use the props atlas."""
import math
import random

import bmesh
from mathutils import Matrix, Vector

from town2_bar_kit import arc_pts, place, rot_z, rounded_rect
import town2_bar_tex as tex
import town2_bar_glow as glow
from town2_bar_shell import _beam

WARM = (1.0, 0.68, 0.40)           # 2700 K incandescent
WARM2 = (1.0, 0.6, 0.32)
NEON = {"pink": (1.0, 0.12, 0.42), "green": (0.18, 1.0, 0.26), "blue": (0.12, 0.32, 1.0), "red": (1.0, 0.07, 0.035),
        "amber": (1.0, 0.45, 0.08), "white": (1.0, 0.85, 0.72), "purple": (0.55, 0.12, 1.0)}

LETTERS = {
    "B": [[(0, 0), (0, 1), (0.42, 1), (0.58, 0.9), (0.58, 0.64), (0.42, 0.54), (0, 0.54)],
          [(0.42, 0.54), (0.62, 0.42), (0.62, 0.12), (0.46, 0), (0, 0)]],
    "A": [[(0, 0), (0.31, 1), (0.62, 0)], [(0.12, 0.38), (0.5, 0.38)]],
    "R": [[(0, 0), (0, 1), (0.42, 1), (0.58, 0.88), (0.58, 0.66), (0.42, 0.54), (0, 0.54)], [(0.26, 0.54), (0.62, 0)]],
}


def smooth_poly(pts, closed, n=3):
    """Chaikin-rounded polyline (neon is bent glass: no sharp corners)."""
    P = [Vector(p) for p in pts]
    for _ in range(n):
        Q = []
        m = len(P)
        rng = range(m) if closed else range(m - 1)
        if not closed:
            Q.append(P[0])
        for i in rng:
            a, b = P[i], P[(i + 1) % m]
            Q.append(a.lerp(b, 0.25))
            Q.append(a.lerp(b, 0.75))
        if not closed:
            Q.append(P[-1])
        P = Q
    return [tuple(p) for p in P]


def neon_shape(name):
    """Pictogram strokes [(colour, closed, [(a, z), ...])] in a unit box (a, z in about -0.5..0.5)."""
    S = []
    if name == "star":
        out = [(0.5 * math.sin(math.radians(i * 36)) * (1 if i % 2 == 0 else 0.42), 0.5 * math.cos(math.radians(i * 36)) * (1 if i % 2 == 0 else 0.42)) for i in range(10)]
        S.append(("blue", True, out))
        S.append(("red", True, [(x * 0.55, z * 0.55) for x, z in out]))
    elif name == "cocktail":
        S.append(("pink", True, [(-0.42, 0.42), (0.42, 0.42), (0.03, -0.05), (0.03, -0.38), (0.24, -0.46), (-0.24, -0.46), (-0.03, -0.38), (-0.03, -0.05)]))
        S.append(("green", True, [(0.1 + 0.08 * math.cos(a), 0.25 + 0.08 * math.sin(a)) for a in [i * math.pi / 6 for i in range(12)]]))
        S.append(("white", False, [(-0.1, 0.05), (0.3, 0.5)]))
    elif name == "bottle":
        S.append(("amber", True, [(-0.17, -0.5), (0.17, -0.5), (0.17, 0.08), (0.06, 0.24), (0.06, 0.48), (-0.06, 0.48), (-0.06, 0.24), (-0.17, 0.08)]))
        S.append(("white", True, [(-0.11, -0.3), (0.11, -0.3), (0.11, -0.05), (-0.11, -0.05)]))
    elif name == "mug":
        S.append(("amber", True, [(-0.3, -0.45), (0.2, -0.45), (0.2, 0.25), (-0.3, 0.25)]))
        S.append(("amber", False, [(0.2, 0.12), (0.38, 0.12), (0.42, 0.0), (0.42, -0.22), (0.38, -0.32), (0.2, -0.32)]))
        S.append(("white", False, [(-0.33, 0.25)] + [(-0.33 + 0.11 * i + 0.055, 0.25 + 0.09 * abs(math.sin((i + 0.5) * math.pi / 1))) for i in range(5)] + [(0.24, 0.25)]))
    elif name == "horseshoe":
        S.append(("green", False, [(0.32 * math.cos(a), 0.05 + 0.38 * math.sin(a)) for a in [math.radians(-50 + i * 280 / 16) for i in range(17)]]))
        S.append(("white", False, [(-0.05, -0.45), (0.05, -0.45)]))
    elif name == "guitar":
        body = [(0.0, -0.5), (0.2, -0.45), (0.26, -0.28), (0.18, -0.1), (0.22, 0.02), (0.14, 0.1), (0.0, 0.08),
                (-0.14, 0.1), (-0.22, 0.02), (-0.18, -0.1), (-0.26, -0.28), (-0.2, -0.45)]
        S.append(("pink", True, body))
        S.append(("white", False, [(0.0, -0.2), (0.0, 0.5)]))
    elif name in ("BAR", "BAR_pink"):
        # letters a unit tall, 0.62 wide, 0.22 apart: the word 2.3 wide, centred
        col = "pink" if name == "BAR_pink" else "red"
        x = -1.15
        for ch in "BAR":
            for st in LETTERS[ch]:
                S.append((col, False, [(x + a, -0.5 + z) for a, z in st]))
            x += 0.62 + 0.22
    return S


def neon_sign(k, origin, right, up, size, shape, mat="Props", lights=True, power=7.0, backing=True, lmw=0.2, mounts=True,
              tube=0.008, halo=None):
    """A neon pictogram at `origin` in the plane (right, up), `size` m tall; the tubes `tube`
    radius, a soft glow band along every stroke (halo: its width, default from the size)."""
    o, r, u = Vector(origin), Vector(right).normalized(), Vector(up).normalized()
    n = r.cross(u)
    cols = {}
    hw = halo if halo is not None else 0.05 + 0.07 * size
    for colour, closed, pts in neon_shape(shape):
        pts3 = [tuple(o + r * (a * size) + u * (z * size)) for a, z in smooth_poly(pts, closed, 2)]
        k.tube(mat, pts3, tube, sides=5, closed=closed, uv=("cell", f"neon_{colour}"), lmw=lmw)
        glow.ribbon(k, pts3, n, hw, colour, closed=closed)
        cols[colour] = cols.get(colour, 0) + len(pts3)
        if mounts:
            for q in pts3[:: max(4, len(pts3) // 3)]:
                q = Vector(q)
                k.cyl(mat, q - n * 0.006, q - n * 0.03, 0.004, sides=4, uv=("cell", "chrome"), lmw=0.05, caps=False)
    if backing:
        # the sign's wire frame: two bars and the chains to the window head
        for zz in (-0.55, 0.55):
            a = o + r * (-0.55 * size) + u * (zz * size) - n * 0.03
            b = o + r * (0.55 * size) + u * (zz * size) - n * 0.03
            k.tube(mat, [tuple(a), tuple(b)], 0.004, sides=4, uv=("cell", "iron_black"), lmw=0.05)
    if lights:
        main = max(cols, key=cols.get)
        c = NEON[main]
        k.light("POINT", tuple(o), c, power, radius=0.25 * size)
        if len(cols) > 1:
            second = sorted(cols, key=cols.get)[-2]
            k.light("POINT", tuple(o + u * 0.1 * size), NEON[second], power * 0.4, radius=0.2 * size)


# ------------------------------------------------------------------ the bar
def tufted_panel(k, x0, x1, y, z0, z1, n_x=6, n_z=3, depth=0.035, tint=(1, 1, 1)):
    """A diamond-tufted vinyl panel facing -y (buttons on a diamond lattice, the vinyl
    pillowing between them)."""
    W, H = x1 - x0, z1 - z0
    nu, nv = n_x * 6, n_z * 6

    def fn(u, v):
        # diamond lattice: buttons where (u*n_x + v*n_z) and (u*n_x - v*n_z) are integers + 0.5 offsets
        a = u * n_x
        b = v * n_z
        p = (a + b) % 1.0
        q = (a - b) % 1.0
        d = min(p, 1 - p) + min(q, 1 - q)          # 0 at the buttons
        puff = math.sin(min(1.0, d) * math.pi / 2) ** 0.7
        edge = min(u, 1 - u, v, 1 - v)
        e = min(1.0, edge * 18)
        return (x0 + W * u, y - depth * puff * e - 0.004, z0 + H * v)
    k.grid("Vinyl", fn, nu, nv, tint=tint, lmw=0.9, vlit=True)
    # buttons
    for i in range(n_x + 1):
        for j in range(n_z + 1):
            for (a, b) in ((i, j), (i + 0.5, j + 0.5)):
                if 0 < a < n_x and 0 < b < n_z:
                    x, z = x0 + W * a / n_x, z0 + H * b / n_z
                    k.lathe("Vinyl", [(0.012, 0), (0.0, 0.008)], sides=5,
                            M=Matrix.Translation((x, y - 0.002, z)) @ Matrix.Rotation(math.pi / 2, 4, "X"), tint=tint, lmw=0.05)


def bar_counter(k, P):
    f = P["floor"]
    x0, x1, yf, H = P["bar_x0"], P["bar_x1"], P["bar_front"], P["bar_h"]
    top = f + H
    # the straight run (front faces -y), then a short return at the west end
    xr = x1 - 0.66
    # kick (recessed, black)
    k.box("Wood", (x0, yf + 0.1, f), (xr, yf + 0.62, f + 0.13), tint=(0.25, 0.25, 0.25), skip=("-z",))
    # pilasters every ~1.8 m with the tufted vinyl panels between them
    n = max(1, round((xr - x0) / 1.8))
    xs = [x0 + (xr - x0) * i / n for i in range(n + 1)]
    for x in xs:
        k.box("Wood", (x - 0.07, yf - 0.02, f), (x + 0.07, yf + 0.1, top - 0.08), bevel=0.012, lmw=0.6)
        k.box("Wood", (x - 0.09, yf - 0.04, f), (x + 0.09, yf + 0.1, f + 0.16), bevel=0.01, tint=(0.8, 0.8, 0.8), lmw=0.4)
    for a, b in zip(xs[:-1], xs[1:]):
        k.box("Wood", (a + 0.07, yf + 0.06, f + 0.13), (b - 0.07, yf + 0.1, top - 0.08), lmw=0.2, skip=("+y",))
        tufted_panel(k, a + 0.07, b - 0.07, yf + 0.06, f + 0.17, top - 0.13, n_x=5, n_z=2)
        # piping frames around the panel
        for zz in (f + 0.15, top - 0.11):
            k.tube("Vinyl", [(a + 0.07, yf + 0.045, zz), (b - 0.07, yf + 0.045, zz)], 0.012, sides=6, lmw=0.1)
    k.box("Wood", (x0, yf - 0.03, top - 0.1), (xr, yf + 0.1, top - 0.05), bevel=0.01, tint=(0.8, 0.8, 0.8), lmw=0.5)   # apron moulding
    # the top: a bullnose front edge, varnished
    prof = [(yf + 0.66, top - 0.045), (yf - 0.05, top - 0.045)] + \
           [(yf - 0.05 - 0.035 * math.sin(math.radians(a)), top - 0.0225 - 0.0225 * math.cos(math.radians(a))) for a in range(0, 181, 30)][1:] + \
           [(yf + 0.66, top)]
    k.prism("Wood", [(y, z) for y, z in prof][::-1], x0, xr + 0.62, M=_yz_to_x(), tint=(0.75, 0.75, 0.75), lmw=1.0, smooth=False,
            uv=lambda co, nn: (co.x / 2.0, co.y / 2.0))
    # the padded arm rail (oxblood roll) along the front edge, end caps
    k.tube("Vinyl", [(x0 + 0.02, yf - 0.02, top + 0.04), (xr + 0.02, yf - 0.02, top + 0.04)], 0.05, sides=12, lmw=0.6)
    k.lathe("Vinyl", [(0.05, 0), (0.035, 0.03), (0.0, 0.04)], sides=12, M=Matrix.Translation((xr + 0.02, yf - 0.02, top + 0.04)) @ Matrix.Rotation(math.pi / 2, 4, "Y"), lmw=0.1)
    k.lathe("Vinyl", [(0.05, 0), (0.035, 0.03), (0.0, 0.04)], sides=12, M=Matrix.Translation((x0 + 0.02, yf - 0.02, top + 0.04)) @ Matrix.Rotation(-math.pi / 2, 4, "Y"), lmw=0.1)
    # brass foot rail on brackets
    k.tube("Props", [(x0 + 0.1, yf - 0.2, f + 0.2), (xr - 0.05, yf - 0.2, f + 0.2)], 0.024, sides=10, uv=("cell", "brass"), lmw=0.3)
    x = x0 + 0.5
    while x < xr - 0.2:
        _beam(k, "Props", (x, yf + 0.02, f + 0.28), (x, yf - 0.2, f + 0.2), 0.03, 0.03, uv=("cell", "brass"), lmw=0.1)
        x += 1.2
    # the return (x xr..x1 + ...): a short run toward the back with a lift flap
    rx0, rx1 = xr, xr + 0.62
    ry0, ry1 = yf, yf + 1.2
    k.box("Wood", (rx0 + 0.02, ry0, f), (rx1, ry1, f + 0.13), tint=(0.25, 0.25, 0.25), skip=("-z",))
    k.box("Wood", (rx1 - 0.1, ry0 - 0.02, f + 0.13), (rx1 + 0.02, ry1, top - 0.08), bevel=0.01, lmw=0.6)
    tufted_panel_x(k, ry0 + 0.1, ry1 - 0.1, rx1 + 0.02, f + 0.17, top - 0.13)
    k.box("Wood", (rx0, ry0 + 0.6, top - 0.045), (rx1 + 0.05, ry1 + 0.05, top), bevel=0.01, tint=(0.75, 0.75, 0.75))
    k.collider(x0, yf - 0.06, f, xr + 0.62, yf + 0.66, top + 0.09)
    k.collider(rx0, ry0, f, rx1 + 0.05, ry1 + 0.05, top)
    # the bartender's side: a stainless under-bar (sinks, ice bin), a rubber mat
    k.box("Props", (x0 + 0.2, yf + 0.66, f), (xr - 0.1, yf + 1.05, f + 0.86), uv=("cell", "stainless"), lmw=0.4, skip=("-z",))
    for x in [x0 + 0.8 + i * 2.6 for i in range(5)]:
        k.box("Props", (x, yf + 0.72, f + 0.8), (x + 0.5, yf + 1.0, f + 0.87), uv=("cell", "steel_dark"), lmw=0.1)
    k.box("Props", (x0 + 0.2, yf + 1.05, f), (xr - 0.1, yf + 1.75, f + 0.012), uv=("cell", "rubber"), lmw=0.3, skip=("-z",))
    # beer towers (chrome T, four taps each) and drip trays
    for tx in (-6.6, -1.6):
        k.cyl("Props", (tx, yf + 0.38, top), (tx, yf + 0.38, top + 0.36), 0.04, sides=12, uv=("cell", "chrome"), lmw=0.3)
        k.tube("Props", [(tx - 0.3, yf + 0.38, top + 0.4), (tx + 0.3, yf + 0.38, top + 0.4)], 0.045, sides=12, uv=("cell", "chrome"), lmw=0.3)
        for i in range(4):
            hx = tx - 0.24 + i * 0.16
            k.cyl("Props", (hx, yf + 0.36, top + 0.38), (hx, yf + 0.3, top + 0.34), 0.012, sides=6, uv=("cell", "chrome"), lmw=0.05)
            k.cyl("Props", (hx, yf + 0.38, top + 0.44), (hx, yf + 0.38, top + 0.66), 0.016, r1=0.022, sides=6,
                  uv=("cell", ["paint_black", "wood_light", "paint_red", "plastic_white"][i]), lmw=0.05)
        k.box("Props", (tx - 0.32, yf + 0.22, top), (tx + 0.32, yf + 0.36, top + 0.015), uv=("cell", "stainless"), lmw=0.1)
    # things on the bar: bottles, glasses, an ashtray, napkins, a bowl
    rnd = random.Random(7)
    for x in (-8.7, -7.9, -4.8, -3.6, -0.2, 0.8, 2.3):
        dx = rnd.uniform(-0.15, 0.15)
        kind = rnd.choice(["beer", "beer", "glass", "rocks"])
        _bar_item(k, kind, x + dx, yf + rnd.uniform(0.05, 0.25), top)
    for x in (-5.4, 1.6):
        k.lathe("Props", [(0.06, 0), (0.06, 0.02), (0.045, 0.025), (0.0, 0.02)], sides=12, M=Matrix.Translation((x, yf + 0.3, top)), uv=("cell", "glass_clear"), lmw=0.05)
    for x in (-9.2, -3.0, 2.8):
        k.box("Props", (x - 0.07, yf + 0.4, top), (x + 0.07, yf + 0.48, top + 0.12), bevel=0.005, uv=("cell", "chrome"), lmw=0.05)
        k.box("Props", (x - 0.05, yf + 0.41, top + 0.02), (x + 0.05, yf + 0.47, top + 0.11), uv=("cell", "paper"), lmw=0.05)


def tufted_panel_x(k, y0, y1, x, z0, z1):
    """The same panel on a face looking +x (the return's side)."""
    W, H = y1 - y0, z1 - z0

    def fn(u, v):
        a, b = u * 1.2, v * 2
        p, q = (a + b) % 1.0, (a - b) % 1.0
        d = min(p, 1 - p) + min(q, 1 - q)
        puff = math.sin(min(1.0, d) * math.pi / 2) ** 0.7
        e = min(1.0, min(u, 1 - u, v, 1 - v) * 18)
        return (x + 0.035 * puff * e, y0 + W * (1 - u), z0 + H * v)
    k.grid("Vinyl", fn, 10, 16, lmw=0.8, vlit=True, flip=True)


def _yz_to_x():
    """Matrix: a prism drawn in (y, z) extruded along local z -> extruded along +x."""
    return Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def _bar_item(k, kind, x, y, z):
    if kind == "beer":
        k.lathe("Props", [(0.032, 0), (0.033, 0.13), (0.028, 0.16), (0.012, 0.2), (0.012, 0.235), (0.0, 0.24)], sides=8,
                M=Matrix.Translation((x, y, z)), uv=lambda co, nn: _cell_v("b_beer", co, z, 0.24), lmw=0.05)
    elif kind == "glass":
        k.lathe("Props", [(0.03, 0), (0.036, 0.0), (0.043, 0.15), (0.04, 0.15), (0.03, 0.01), (0.0, 0.01)], sides=10,
                M=Matrix.Translation((x, y, z)), uv=("cell", "glass_clear"), lmw=0.05)
        k.lathe("Props", [(0.0, 0.012), (0.029, 0.012), (0.035, 0.1), (0.0, 0.1)], sides=10,
                M=Matrix.Translation((x, y, z)), uv=("cell", "glass_amber"), lmw=0.05)
    else:
        k.lathe("Props", [(0.04, 0), (0.042, 0.09), (0.038, 0.09), (0.036, 0.012), (0.0, 0.012)], sides=10,
                M=Matrix.Translation((x, y, z)), uv=("cell", "glass_clear"), lmw=0.05)
        k.lathe("Props", [(0.0, 0.013), (0.035, 0.013), (0.036, 0.05), (0.0, 0.05)], sides=10,
                M=Matrix.Translation((x, y, z)), uv=("cell", "glass_brown"), lmw=0.05)


def _cell_v(name, co, z0, h, u=0.5):
    """UV in a 1x2 swatch by height (a bottle body's label bands)."""
    r = __import__("town2_bar_kit").cell_rect(tex.CELLS[name], inset=0.18)
    t = max(0.0, min(1.0, (co.z - z0) / h))
    return (r[0] + (r[2] - r[0]) * u, r[1] + (r[3] - r[1]) * t)


def stools(k, P):
    f = P["floor"]
    y = P["bar_front"] - 0.52
    rnd = random.Random(3)
    x = P["bar_x0"] + 0.55
    while x < P["bar_x1"] - 0.9:
        dx, dy, rot = rnd.uniform(-0.06, 0.06), rnd.uniform(-0.08, 0.05), rnd.uniform(0, 360)
        sx, sy = x + dx, y + dy
        M = place(sx, sy, f, rot)
        k.lathe("Props", [(0.0, 0.0), (0.22, 0.0), (0.22, 0.015), (0.16, 0.03), (0.05, 0.06), (0.032, 0.1)], sides=12, M=M,
                uv=("cell", "iron_black"), lmw=0.3, cap0=False)
        k.cyl("Props", (sx, sy, f + 0.1), (sx, sy, f + 0.68), 0.028, sides=10, uv=("cell", "chrome"), lmw=0.15)
        ring = [(sx + 0.19 * math.cos(a), sy + 0.19 * math.sin(a), f + 0.32) for a in [i * math.pi / 8 for i in range(16)]]
        k.tube("Props", ring, 0.011, sides=6, closed=True, uv=("cell", "chrome"), lmw=0.1)
        for a in (0, 120, 240):
            ra = math.radians(a + rot)
            k.cyl("Props", (sx, sy, f + 0.3), (sx + 0.18 * math.cos(ra), sy + 0.18 * math.sin(ra), f + 0.32), 0.008, sides=4, uv=("cell", "chrome"), lmw=0.02)
        # the seat: a chrome band, a rolled oxblood cushion with a button
        k.lathe("Props", [(0.17, f + 0.68), (0.2, f + 0.7), (0.2, f + 0.74)], sides=16, M=place(sx, sy, 0, rot), uv=("cell", "chrome"), lmw=0.2, cap0=False, cap1=False)
        k.lathe("Vinyl", [(0.2, f + 0.735), (0.215, f + 0.76), (0.205, f + 0.79), (0.17, f + 0.805), (0.04, f + 0.81), (0.0, f + 0.802)], sides=16,
                M=place(sx, sy, 0, rot), lmw=0.5, cap0=False)
        k.collider(sx - 0.2, sy - 0.2, f, sx + 0.2, sy + 0.2, f + 0.8)
        x += 1.0


def back_bar(k, P):
    f = P["floor"]
    D, W = P["D"], P["wall"]
    yb = D / 2 - W - 0.05                      # the lining's face
    x0, x1 = P["bar_x0"] + 0.2, P["bar_x1"] - 0.9
    d = 0.58
    zc = f + 0.95
    # lower cabinet: doors, a lit glass-door beer cooler in the middle
    cx0, cx1 = -4.2, -0.6
    for (a, b) in ((x0, cx0), (cx1, x1)):
        k.box("Wood", (a, yb - d, f), (b, yb, zc - 0.04), bevel=0.01, tint=(0.7, 0.7, 0.7), lmw=0.5, skip=("-z", "+y"))
        k.box("Wood", (a, yb - d + 0.02, f), (b, yb - d + 0.06, f + 0.12), tint=(0.3, 0.3, 0.3), lmw=0.2)
    # the beer cooler: a lit, shelved box behind three glass doors in a stainless frame
    k.box("Props", (cx0, yb - 0.1, f + 0.12), (cx1, yb - 0.08, zc - 0.06), uv=("cell", "cooler_glow"), lmw=0.0)
    k.box("Props", (cx0, yb - d, f), (cx1, yb, f + 0.14), uv=("cell", "stainless"), lmw=0.2)
    k.box("Props", (cx0, yb - d, zc - 0.1), (cx1, yb, zc - 0.04), uv=("cell", "stainless"), lmw=0.2)
    for z_ in (f + 0.44,):
        k.box("Props", (cx0, yb - d + 0.06, z_ - 0.01), (cx1, yb - 0.1, z_), uv=("cell", "chrome"), lmw=0.0)
    for i in range(4):
        xx = cx0 + i * (cx1 - cx0) / 3
        k.box("Props", (xx - 0.03, yb - d - 0.02, f + 0.12), (xx + 0.03, yb - d + 0.03, zc - 0.06), uv=("cell", "stainless"), lmw=0.1)
    for i in range(3):
        a = cx0 + i * (cx1 - cx0) / 3 + 0.03
        b = cx0 + (i + 1) * (cx1 - cx0) / 3 - 0.03
        k.box("Glass", (a, yb - d - 0.01, f + 0.14), (b, yb - d, zc - 0.1), lmw=0.05)
        k.box("Props", (b - 0.06, yb - d - 0.05, f + 0.3), (b - 0.04, yb - d - 0.01, zc - 0.3), uv=("cell", "chrome"), lmw=0.0)
        # bottles standing in the cooler, two shelves of them
        for j in range(6):
            for r_ in range(2):
                bx = a + 0.07 + j * (b - a - 0.14) / 5
                bz = f + 0.15 + r_ * 0.3
                k.lathe("Props", [(0.03, 0.0), (0.031, 0.13), (0.013, 0.19), (0.012, 0.23), (0.0, 0.235)], sides=6,
                        M=Matrix.Translation((bx, yb - d + 0.18 + 0.1 * ((j + r_) % 2), bz)),
                        uv=("cell", "glass_amber" if (i + j) % 2 else "glass_green"), lmw=0.02)
    k.light("AREA", ((cx0 + cx1) / 2, yb - d - 0.06, f + 0.5), (0.85, 0.9, 1.0), 6.0, size=(cx1 - cx0, 0.55), aim=((cx0 + cx1) / 2, yb - 2, f + 0.5))
    # cabinet doors on the rest
    for (a, b) in ((x0 + 0.05, cx0 - 0.05), (cx1 + 0.05, x1 - 0.05)):
        n = max(1, round((b - a) / 0.6))
        for i in range(n):
            da, db = a + (b - a) * i / n + 0.015, a + (b - a) * (i + 1) / n - 0.015
            k.box("Wood", (da, yb - d - 0.02, f + 0.16), (db, yb - d + 0.005, zc - 0.1), bevel=0.008, lmw=0.3)
            k.box("Props", ((da + db) / 2 - 0.01, yb - d - 0.04, zc - 0.25), ((da + db) / 2 + 0.01, yb - d - 0.02, zc - 0.17), uv=("cell", "brass"), lmw=0.01)
    k.box("Wood", (x0 - 0.03, yb - d - 0.04, zc - 0.045), (x1 + 0.03, yb, zc), bevel=0.012, tint=(0.75, 0.75, 0.75), lmw=0.8)
    k.collider(x0, yb - d - 0.04, f, x1, yb, zc)
    # the mirrored back with pilasters, three tiers of bottles lit from below, a cornice
    zt = f + 2.62
    n = max(1, round((x1 - x0) / 2.2))
    xs = [x0 + (x1 - x0) * i / n for i in range(n + 1)]
    k.box("Props", (x0, yb - 0.02, zc), (x1, yb, zt), uv=("cell", "mirror"), lmw=0.4, skip=("+y",))
    for x in xs:
        k.box("Wood", (x - 0.09, yb - 0.16, zc), (x + 0.09, yb, zt), bevel=0.012, lmw=0.5)
        k.box("Wood", (x - 0.12, yb - 0.19, zt - 0.14), (x + 0.12, yb, zt), bevel=0.012, tint=(0.8, 0.8, 0.8), lmw=0.4)
    k.box("Wood", (x0 - 0.06, yb - 0.32, zt), (x1 + 0.06, yb, zt + 0.12), bevel=0.015, lmw=0.6)        # cornice
    k.box("Wood", (x0 - 0.1, yb - 0.36, zt + 0.12), (x1 + 0.1, yb, zt + 0.18), bevel=0.015, tint=(0.8, 0.8, 0.8), lmw=0.5)
    # a lit valance under the cornice (a warm downlight onto the bottles)
    k.box("Props", (x0, yb - 0.3, zt - 0.015), (x1, yb - 0.2, zt), uv=("cell", "glow_amber"), lmw=0.05)
    tiers = [(zc, yb - 0.5, yb - 0.02), (f + 1.32, yb - 0.3, yb - 0.02), (f + 1.72, yb - 0.24, yb - 0.02), (f + 2.12, yb - 0.2, yb - 0.02)]
    rnd = random.Random(11)
    styles = list(tex.BOTTLES)
    for ti, (zs, ya, yb_) in enumerate(tiers):
        if ti > 0:
            # a glass shelf with a chrome nosing and an amber strip under its front edge
            for (a, b) in zip(xs[:-1], xs[1:]):
                k.box("Glass", (a + 0.09, ya, zs - 0.012), (b - 0.09, yb_, zs), lmw=0.05)
                k.box("Props", (a + 0.09, ya - 0.012, zs - 0.03), (b - 0.09, ya, zs), uv=("cell", "chrome"), lmw=0.05)
        # the amber LED strip lighting the tier from below (tier 0: on the counter's back edge)
        k.box("Props", (x0 + 0.1, ya + 0.02, zs + 0.0), (x1 - 0.1, ya + 0.04, zs + 0.012), uv=("cell", "glow_amber"), lmw=0.02)
        for (a, b) in zip(xs[:-1], xs[1:]):
            k.light("AREA", ((a + b) / 2, ya + 0.08, zs + 0.03), (1.0, 0.62, 0.3), 2.2, size=(b - a - 0.2, 0.05), aim=((a + b) / 2, ya + 0.12, zs + 2))
        # bottles, packed, sorted loosely by kind
        x = x0 + 0.14
        while x < x1 - 0.12:
            if any(abs(x - px) < 0.12 for px in xs):
                x += 0.05
                continue
            st = styles[int((x * 1.7 + ti * 3 + rnd.random() * 2.5)) % len(styles)]
            if ti == 0 and rnd.random() < 0.6:
                x += 0.12
                continue
            y = (ya + yb_) / 2 + rnd.uniform(-0.04, 0.04) if ti > 0 else yb - 0.12 - rnd.uniform(0, 0.25)
            w = bottle(k, st, x, y, zs, rnd)
            x += w + rnd.uniform(0.01, 0.05)
    k.light("AREA", ((x0 + x1) / 2, yb - 0.3, zt - 0.04), (1.0, 0.7, 0.42), 9.0, size=(x1 - x0, 0.12), aim=((x0 + x1) / 2, yb - 0.3, zc))
    # the cash register (brass, an old one) on the counter at the west end; a pictogram mirror over it
    rx = x1 - 1.1
    _register(k, rx, yb - 0.34, zc)
    k.box("Props", (-2.6, yb - 0.03, zt + 0.2), (-1.3, yb - 0.01, zt + 0.72), uv=("cell", "beer_mirror"), lmw=0.2)


def bottle(k, style, x, y, z, rnd):
    """A liquor bottle (lathe; label bands from the style's swatch); returns its width."""
    shapes = {
        "tall": [(0.04, 0.0), (0.042, 0.005), (0.042, 0.19), (0.036, 0.215), (0.015, 0.25), (0.013, 0.31), (0.015, 0.315), (0.0, 0.318)],
        "square": [(0.045, 0.0), (0.047, 0.005), (0.047, 0.17), (0.03, 0.2), (0.016, 0.215), (0.015, 0.25), (0.0, 0.252)],
        "fat": [(0.05, 0.0), (0.052, 0.006), (0.052, 0.15), (0.04, 0.19), (0.017, 0.215), (0.015, 0.26), (0.0, 0.262)],
        "wine": [(0.036, 0.0), (0.038, 0.005), (0.038, 0.2), (0.032, 0.235), (0.014, 0.27), (0.013, 0.33), (0.0, 0.333)],
        "flask": [(0.038, 0.0), (0.04, 0.005), (0.04, 0.13), (0.03, 0.16), (0.012, 0.18), (0.012, 0.21), (0.0, 0.212)],
    }
    kind = rnd.choice(["tall", "tall", "square", "fat", "wine", "flask"])
    if style == "b_wine":
        kind = "wine"
    prof = shapes[kind]
    s = rnd.uniform(0.92, 1.08)
    h = prof[-1][1] * s
    sides = 4 if kind == "square" else 6
    prof = [(r * (1.0 if kind != "square" else 1.3), zz * s) for r, zz in prof]
    M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(45 if sides == 4 else rnd.uniform(0, 360)), 4, "Z")
    k.lathe("Props", prof, sides=sides, M=M, uv=lambda co, nn: _cell_v(style, co, z, h, 0.25 + 0.5 * (0.5 + 0.5 * math.atan2(co.y - y, co.x - x) / math.pi)),
            lmw=0.08, smooth=sides > 4)
    return 2 * prof[2][0]


def _register(k, x, y, z):
    k.box("Props", (x - 0.22, y - 0.2, z), (x + 0.22, y + 0.2, z + 0.12), bevel=0.01, uv=("cell", "brass"), lmw=0.1)
    k.box("Props", (x - 0.2, y - 0.12, z + 0.12), (x + 0.2, y + 0.2, z + 0.34), bevel=0.012, uv=("cell", "brass"), lmw=0.1)
    for i in range(4):
        for j in range(3):
            k.cyl("Props", (x - 0.15 + i * 0.1, y - 0.21, z + 0.15 + j * 0.06), (x - 0.15 + i * 0.1, y - 0.24, z + 0.14 + j * 0.06), 0.016, sides=6,
                  uv=("cell", "plastic_white"), lmw=0.01)
    k.box("Props", (x - 0.14, y - 0.05, z + 0.36), (x + 0.14, y + 0.1, z + 0.44), bevel=0.01, uv=("cell", "brass"), lmw=0.05)


# ------------------------------------------------------------------ booths
def booths(k, P):
    f = P["floor"]
    D, W = P["D"], P["wall"]
    yw = -D / 2 + W + 0.05                    # the lining's face
    L = 1.32                                   # booth length out from the wall
    ye = yw + L
    zs = f + 0.45                              # seat height
    zt = f + 0.76                              # table height
    zb = f + 1.2                               # back height
    xs = [x for x in P["front_windows"] if x < 6]
    pitch = 1.95
    for i, xc in enumerate(xs):
        # table: wood top, chrome edge band, a pedestal
        k.box("Wood", (xc - 0.36, yw, zt - 0.035), (xc + 0.36, ye - 0.08, zt), bevel=0.006, tint=(0.8, 0.8, 0.8), lmw=0.8)
        k.box("Props", (xc - 0.365, ye - 0.085, zt - 0.04), (xc + 0.365, ye - 0.075, zt + 0.002), uv=("cell", "chrome"), lmw=0.1)
        for sx in (-1, 1):
            k.box("Props", (xc + sx * 0.36 - 0.004, yw, zt - 0.04), (xc + sx * 0.36 + 0.004, ye - 0.08, zt + 0.002), uv=("cell", "chrome"), lmw=0.05)
        k.cyl("Props", (xc, ye - 0.45, f), (xc, ye - 0.45, zt - 0.04), 0.04, sides=10, uv=("cell", "chrome"), lmw=0.1)
        k.lathe("Props", [(0.0, 0.0), (0.24, 0.0), (0.22, 0.02), (0.04, 0.04)], sides=12, M=Matrix.Translation((xc, ye - 0.45, f)),
                uv=("cell", "iron_black"), lmw=0.1, cap0=False)
        k.collider(xc - 0.36, yw, f, xc + 0.36, ye - 0.08, zt)
        # the red glass candle lamp, a napkin holder, salt, an ashtray, a bottle or two
        _candle(k, xc + 0.12, yw + 0.35, zt)
        k.box("Props", (xc - 0.2, yw + 0.12, zt), (xc - 0.08, yw + 0.2, zt + 0.1), bevel=0.004, uv=("cell", "chrome"), lmw=0.02)
        k.cyl("Props", (xc - 0.02, yw + 0.15, zt), (xc - 0.02, yw + 0.15, zt + 0.08), 0.018, sides=8, uv=("cell", "glass_clear"), lmw=0.02)
        if i % 2 == 0:
            _bar_item(k, "beer", xc - 0.18, ye - 0.4, zt)
            _bar_item(k, "beer", xc + 0.1, ye - 0.32, zt)
        else:
            _bar_item(k, "rocks", xc + 0.05, ye - 0.45, zt)
        # benches either side
        for sx in (-1, 1):
            a = xc + sx * 0.42                 # seat's inner edge
            b = xc + sx * (pitch / 2 - 0.05)   # the back's face
            lo_x, hi_x = min(a, b), max(a, b)
            # base (wood panel facing the table) and the end panel at the aisle
            k.box("Wood", (lo_x, yw, f), (hi_x, ye, zs - 0.12), bevel=0.008, tint=(0.75, 0.75, 0.75), lmw=0.4)
            # seat cushion
            cu = _cushion((hi_x - lo_x - 0.02, L - 0.06, 0.12), crown={"+z": 0.018})
            k.add(cu, "Vinyl", M=Matrix.Translation(((lo_x + hi_x) / 2, yw + L / 2 - 0.02, zs - 0.06)), smooth=True, lmw=0.6)
            # back: five tuck-and-roll channels, leaning back a little
            bx = b - sx * 0.07
            for j in range(5):
                c0 = yw + 0.04 + j * (L - 0.1) / 5
                c1 = c0 + (L - 0.1) / 5 - 0.008
                cu = _cushion((0.1, c1 - c0, zb - zs - 0.12), crown={"-x" if sx > 0 else "+x": 0.025})
                k.add(cu, "Vinyl", M=Matrix.Translation((bx, (c0 + c1) / 2, (zs + zb) / 2 + 0.01)) @ Matrix.Rotation(math.radians(-6 * sx), 4, "Y"),
                      smooth=True, lmw=0.5)
            k.collider(lo_x, yw, f, hi_x, ye, zs)
        for e in (xc - pitch / 2, xc + pitch / 2):
            k.box("Wood", (e - 0.05, yw, f), (e + 0.05, ye, zb), bevel=0.01, tint=(0.85, 0.85, 0.85), lmw=0.5)
            k.box("Wood", (e - 0.07, yw, zb), (e + 0.07, ye + 0.02, zb + 0.05), bevel=0.012, tint=(0.75, 0.75, 0.75), lmw=0.4)
            # the end panel facing the aisle: a curved-top board
            k.collider(e - 0.06, yw, f, e + 0.06, ye, zb)
    # neon in the windows (the outward face is -y)
    signs = ["star", "cocktail", "bottle", "BAR_pink", "mug", "horseshoe", "guitar"]
    for i, xw in enumerate(P["front_windows"]):
        shp = signs[i % len(signs)]
        size = 0.62 if not shp.startswith("BAR") else 0.3
        neon_sign(k, (xw, yw - 0.16, f + 1.62), (1, 0, 0), (0, 0, 1), size, shp, power=12.0)
    # a small shaded sconce on the wall pier between each pair of booths (the booths' own light)
    for xw in [x for x in P["front_windows"] if x < 6][:-1]:
        sx_ = xw + 0.975
        M = Matrix.Translation((sx_, yw + 0.02, f + 1.72))
        k.box("Props", (sx_ - 0.05, yw, f + 1.62), (sx_ + 0.05, yw + 0.02, f + 1.78), uv=("cell", "brass"), lmw=0.0)
        k.cyl("Props", (sx_, yw + 0.02, f + 1.7), (sx_, yw + 0.14, f + 1.7), 0.008, sides=5, uv=("cell", "brass"), lmw=0.0)
        k.lathe("Props", [(0.09, 0.0), (0.075, 0.06), (0.04, 0.13)], sides=12, M=Matrix.Translation((sx_, yw + 0.15, f + 1.62)),
                uv=("cell", "glow_red"), lmw=0.0, cap0=False, cap1=False)
        k.light("POINT", (sx_, yw + 0.16, f + 1.66), (1.0, 0.42, 0.22), 9.0, radius=0.05)
        glow.halo(k, (sx_, yw + 0.16, f + 1.66), 0.3, "warm", normal=(0, 1, 0))


def _cushion(size, crown):
    from lib import common
    return common.cushion_bmesh(size, cuts=2, edge=0.02, crown=crown)


def _candle(k, x, y, z):
    """A red netted-glass candle jar: the glow (emissive) and its light."""
    k.lathe("Props", [(0.035, 0.0), (0.045, 0.02), (0.048, 0.07), (0.04, 0.1), (0.033, 0.105)], sides=10, M=Matrix.Translation((x, y, z)),
            uv=("cell", "glow_red"), lmw=0.02, cap1=False)
    k.lathe("Props", [(0.0, 0.05), (0.006, 0.05), (0.004, 0.075), (0.0, 0.08)], sides=5, M=Matrix.Translation((x, y, z)), uv=("cell", "bulb"), lmw=0.01)
    k.light("POINT", (x, y, z + 0.08), (1.0, 0.22, 0.1), 5.0, radius=0.04)
    glow.halo(k, (x, y, z + 0.07), 0.22, "red")


# ------------------------------------------------------------------ pool table
def pool_table(k, P):
    f = P["floor"]
    cx, cy = P["pool"]
    Lx, Ly = 2.24, 1.32                # outer (a 7 ft bar box)
    zr = f + 0.8                       # rail top
    zp = f + 0.76                      # playing surface
    rw = 0.13                          # rail width
    # cabinet (slab sides to the floor), a plinth, the coin mechanism at the foot end
    k.box("Wood", (cx - Lx / 2 + 0.06, cy - Ly / 2 + 0.06, f), (cx + Lx / 2 - 0.06, cy + Ly / 2 - 0.06, zp - 0.12), bevel=0.012, tint=(0.8, 0.8, 0.8), lmw=0.6, skip=("-z",))
    k.box("Wood", (cx - Lx / 2 + 0.04, cy - Ly / 2 + 0.04, f), (cx + Lx / 2 - 0.04, cy + Ly / 2 - 0.04, f + 0.08), bevel=0.01, tint=(0.4, 0.4, 0.4), lmw=0.3, skip=("-z",))
    k.box("Wood", (cx - Lx / 2, cy - Ly / 2, zp - 0.14), (cx + Lx / 2, cy + Ly / 2, zp - 0.02), bevel=0.02, tint=(0.9, 0.9, 0.9), lmw=0.6)
    k.box("Props", (cx + Lx / 2 - 0.08, cy - 0.16, f + 0.32), (cx + Lx / 2 - 0.04, cy + 0.16, f + 0.5), bevel=0.006, uv=("cell", "chrome"), lmw=0.1)
    for i in range(3):
        k.box("Props", (cx + Lx / 2 - 0.1, cy - 0.1 + i * 0.1, f + 0.4), (cx + Lx / 2 - 0.03, cy - 0.06 + i * 0.1, f + 0.43), uv=("cell", "steel_dark"), lmw=0.01)
    k.box("Props", (cx - Lx / 2 + 0.03, cy - 0.25, f + 0.12), (cx - Lx / 2 + 0.07, cy + 0.25, f + 0.24), uv=("cell", "plastic_black"), lmw=0.05)
    # the bed (felt), cushions, rails with diamond sights
    k.box("Props", (cx - Lx / 2 + rw, cy - Ly / 2 + rw, zp - 0.03), (cx + Lx / 2 - rw, cy + Ly / 2 - rw, zp), uv=("cell", "felt"), lmw=1.3)
    for s in (-1, 1):
        k.box("Props", (cx - Lx / 2 + rw + 0.06, cy + s * (Ly / 2 - rw) - (0.045 if s > 0 else 0), zp), (cx + Lx / 2 - rw - 0.06, cy + s * (Ly / 2 - rw) + (0.045 if s < 0 else 0), zr - 0.005),
              bevel=0.015, uv=("cell", "felt_rail"), lmw=0.4)
        k.box("Props", (cx + s * (Lx / 2 - rw) - (0.045 if s > 0 else 0), cy - Ly / 2 + rw + 0.06, zp), (cx + s * (Lx / 2 - rw) + (0.045 if s < 0 else 0), cy + Ly / 2 - rw - 0.06, zr - 0.005),
              bevel=0.015, uv=("cell", "felt_rail"), lmw=0.4)
    for s in (-1, 1):
        k.box("Wood", (cx - Lx / 2, cy + s * Ly / 2 - (rw if s > 0 else 0), zp - 0.03), (cx + Lx / 2, cy + s * Ly / 2 + (rw if s < 0 else 0), zr), bevel=0.02, lmw=0.6)
        k.box("Wood", (cx + s * Lx / 2 - (rw if s > 0 else 0), cy - Ly / 2 + rw, zp - 0.03), (cx + s * Lx / 2 + (rw if s < 0 else 0), cy + Ly / 2 - rw, zr), bevel=0.02, lmw=0.6)
        for i in (1, 2, 3, 5, 6, 7):
            x = cx - Lx / 2 + rw + (Lx - 2 * rw) * i / 8
            k.box("Props", (x - 0.01, cy + s * (Ly / 2 - rw / 2) - 0.006, zr), (x + 0.01, cy + s * (Ly / 2 - rw / 2) + 0.006, zr + 0.002), uv=("cell", "plastic_white"), lmw=0.0)
        for i in (1, 2, 3):
            y = cy - Ly / 2 + rw + (Ly - 2 * rw) * i / 4
            k.box("Props", (cx + s * (Lx / 2 - rw / 2) - 0.006, y - 0.01, zr), (cx + s * (Lx / 2 - rw / 2) + 0.006, y + 0.01, zr + 0.002), uv=("cell", "plastic_white"), lmw=0.0)
    # pockets: black liners at the corners and the sides
    for px in (cx - Lx / 2 + rw - 0.02, cx, cx + Lx / 2 - rw + 0.02):
        for s in (-1, 1):
            py = cy + s * (Ly / 2 - rw + 0.02)
            k.cyl("Props", (px, py, zp - 0.06), (px, py, zr + 0.003), 0.058, sides=12, uv=("cell", "rubber"), lmw=0.05, caps=True)
    k.collider(cx - Lx / 2, cy - Ly / 2, f, cx + Lx / 2, cy + Ly / 2, zr)
    # a game in progress: the cue ball, ten balls scattered, a cue across the table, chalk
    rnd = random.Random(21)
    balls = ["ball_white", "ball_yellow", "ball_blue", "ball_red", "ball_purple", "ball_orange", "ball_green", "ball_maroon", "ball_black",
             "ball_yellow", "ball_blue", "ball_red"]
    placed = []
    for b in balls:
        for _ in range(40):
            bx = cx + rnd.uniform(-(Lx / 2 - rw - 0.06), Lx / 2 - rw - 0.06)
            by = cy + rnd.uniform(-(Ly / 2 - rw - 0.06), Ly / 2 - rw - 0.06)
            if all(math.hypot(bx - qx, by - qy) > 0.07 for qx, qy in placed):
                break
        placed.append((bx, by))
        k.lathe("Props", [(0.0, -0.0286), (0.02, -0.0245), (0.0286, -0.005), (0.0286, 0.005), (0.02, 0.0245), (0.0, 0.0286)], sides=10,
                M=Matrix.Translation((bx, by, zp + 0.0286)), uv=("cell", b), lmw=0.05)
    a = (cx - 0.55, cy - 0.2, zr + 0.015)
    b = (cx + 0.85, cy + 0.42, zp + 0.02)
    k.cyl("Props", a, b, 0.014, r1=0.0065, sides=8, uv=lambda co, nn: _cell_v("cue", co, zp, 0.05), lmw=0.05)
    k.box("Props", (cx + Lx / 2 - 0.09, cy + 0.3, zr), (cx + Lx / 2 - 0.068, cy + 0.322, zr + 0.022), uv=("cell", "chalk"), lmw=0.0)
    # the lamp: three green enamel shades on a brass bar, chains to the ceiling
    zl = f + 1.72
    ci = f + P["ceiling"]
    k.tube("Props", [(cx - 0.85, cy, zl + 0.12), (cx + 0.85, cy, zl + 0.12)], 0.016, sides=8, uv=("cell", "brass"), lmw=0.1)
    for sx in (-0.55, 0.55):
        k.tube("Props", [(cx + sx, cy, zl + 0.12), (cx + sx * 0.9, cy, ci - 0.24)], 0.004, sides=4, uv=("cell", "brass"), lmw=0.01)
    for sx in (-0.62, 0.0, 0.62):
        M = Matrix.Translation((cx + sx, cy, zl))
        k.lathe("Props", [(0.23, 0.0), (0.2, 0.03), (0.12, 0.1), (0.05, 0.14), (0.025, 0.155)], sides=16, M=M, uv=("cell", "shade_green"), lmw=0.2, cap0=False, cap1=False)
        k.lathe("Props", [(0.022, 0.15), (0.045, 0.137), (0.115, 0.098), (0.195, 0.032), (0.225, 0.002)], sides=16, M=M, uv=("cell", "shade_inner"), lmw=0.02, cap0=False, cap1=False)
        k.lathe("Props", [(0.0, 0.04), (0.035, 0.06), (0.03, 0.1), (0.0, 0.11)], sides=8, M=M, uv=("cell", "bulb"), lmw=0.0)
        k.cyl("Props", (cx + sx, cy, zl + 0.15), (cx + sx, cy, zl + 0.12), 0.02, sides=8, uv=("cell", "brass"), lmw=0.0)
        k.light("SPOT", (cx + sx, cy, zl + 0.05), (1.0, 0.84, 0.62), 45.0, radius=0.05, angle=95.0, blend=0.35, aim=(cx + sx, cy, f))
        glow.cone(k, (cx + sx, cy, zl + 0.0), 0.8, 0.19, 0.5, "warm", planes=2)
    # the cue rack on the partition by the entrance, cues in it
    rxp = P["px"] + 0.09
    ry0 = -3.9
    k.box("Wood", (rxp, ry0, f + 0.25), (rxp + 0.06, ry0 + 0.9, f + 0.33), bevel=0.006, lmw=0.2)
    k.box("Wood", (rxp, ry0, f + 1.35), (rxp + 0.1, ry0 + 0.9, f + 1.45), bevel=0.006, lmw=0.2)
    for i in range(6):
        y = ry0 + 0.1 + i * 0.14
        k.cyl("Props", (rxp + 0.05, y, f + 0.27), (rxp + 0.07, y + 0.01, f + 1.5), 0.014, r1=0.0065, sides=6, uv=lambda co, nn: _cell_v("cue", co, f + 0.25, 1.2), lmw=0.02)


# ------------------------------------------------------------------ the jukebox
def jukebox(k, P):
    f = P["floor"]
    x, y = P["jukebox"]
    w, d = 0.84, 0.62
    yb = y + d / 2
    yf = y - d / 2
    M = Matrix.Translation((x, y, f))
    # cabinet sides (wood, rounded fronts), plinth, speaker grille, the coin entry
    for s in (-1, 1):
        k.box("Wood", (x + s * w / 2 - (0.09 if s > 0 else 0), yf + 0.04, f), (x + s * w / 2 + (0.0 if s > 0 else 0.09), yb, f + 1.05), bevel=0.03, segs=2, lmw=0.5)
    k.box("Wood", (x - w / 2, yf + 0.06, f), (x + w / 2, yb, f + 0.07), tint=(0.4, 0.4, 0.4), lmw=0.2, skip=("-z",))
    k.box("Wood", (x - w / 2 + 0.09, yf + 0.1, f + 0.07), (x + w / 2 - 0.09, yb, f + 1.02), lmw=0.2)
    k.box("Props", (x - w / 2 + 0.1, yf + 0.06, f + 0.12), (x + w / 2 - 0.1, yf + 0.09, f + 0.52), uv=("cell", "grille"), lmw=0.3)
    k.box("Props", (x - w / 2 + 0.08, yf + 0.04, f + 0.52), (x + w / 2 - 0.08, yf + 0.1, f + 0.6), bevel=0.01, uv=("cell", "chrome"), lmw=0.2)
    # the lit front pilasters (bubble tubes: amber, red), the selection window, the arch
    for s in (-1, 1):
        k.cyl("Props", (x + s * (w / 2 - 0.045), yf + 0.05, f + 0.1), (x + s * (w / 2 - 0.045), yf + 0.05, f + 1.0), 0.028, sides=10,
              uv=lambda co, nn: _cell_v("juke_orange", co, f + 0.1, 0.9), lmw=0.05)
        k.cyl("Props", (x + s * (w / 2 - 0.045), yf + 0.02, f + 0.25), (x + s * (w / 2 - 0.045), yf + 0.02, f + 0.95), 0.012, sides=6,
              uv=lambda co, nn: _cell_v("juke_yellow", co, f + 0.25, 0.7), lmw=0.02)
    k.box("Props", (x - 0.3, yf + 0.08, f + 0.62), (x + 0.3, yf + 0.1, f + 0.98), uv=("cell", "juke_cards"), lmw=0.05)
    k.box("Glass", (x - 0.31, yf + 0.06, f + 0.61), (x + 0.31, yf + 0.065, f + 0.99), lmw=0.02)
    k.box("Props", (x - 0.33, yf + 0.04, f + 0.6), (x + 0.33, yf + 0.08, f + 0.62), uv=("cell", "chrome"), lmw=0.02)
    k.box("Props", (x - 0.33, yf + 0.04, f + 0.98), (x + 0.33, yf + 0.08, f + 1.0), uv=("cell", "chrome"), lmw=0.02)
    # the arch over it: concentric lit bands (red outside, orange, yellow), a chrome rim, the dome
    zc = f + 1.03
    for r_, nm, dy in ((0.42, "juke_red", 0.05), (0.38, "juke_orange", 0.04), (0.34, "juke_yellow", 0.03), (0.3, "juke_green", 0.02)):
        pts = arc_pts((x, yf + dy, zc), r_, 0, 180, 18, plane="xz")
        k.tube("Props", pts, 0.022, sides=8, uv=lambda co, nn, nm=nm: _cell_v(nm, co, zc, 0.45), lmw=0.03)
    k.tube("Props", arc_pts((x, yf + 0.06, zc), 0.45, 0, 180, 18, plane="xz"), 0.012, sides=6, uv=("cell", "chrome"), lmw=0.03)
    k.lathe("Wood", [(0.43, 0.0), (0.43, d - 0.1)], sides=18, a0=0, a1=math.pi, cap0=False, cap1=False,
            M=Matrix.Translation((x, yf + 0.08, zc)) @ Matrix.Rotation(-math.pi / 2, 4, "X"), lmw=0.4)
    # (the half-disc behind the arch, the cabinet's top)
    k.prism("Wood", [(0.43 * math.cos(math.radians(a)), 0.43 * math.sin(math.radians(a))) for a in range(0, 181, 15)], 0, 0.02,
            M=Matrix.Translation((x, yb, zc)) @ Matrix.Rotation(math.pi / 2, 4, "X"), lmw=0.2)
    k.prism("Props", [(0.3 * math.cos(math.radians(a)), 0.3 * math.sin(math.radians(a))) for a in range(0, 181, 15)], 0, 0.02,
            M=Matrix.Translation((x, yf + 0.14, zc)) @ Matrix.Rotation(math.pi / 2, 4, "X"), uv=("cell", "juke_blue"), lmw=0.05)
    k.collider(x - w / 2, yf, f, x + w / 2, yb, f + 1.48)
    # its light on the floor and the room: warm orange, a little red
    k.light("POINT", (x, yf - 0.25, f + 0.95), (1.0, 0.5, 0.18), 22.0, radius=0.3)
    k.light("POINT", (x, yf - 0.15, f + 0.35), (1.0, 0.25, 0.1), 8.0, radius=0.2)


# ------------------------------------------------------------------ stage
def stage(k, P):
    f = P["floor"]
    D, W, L = P["D"], P["wall"], P["L"]
    xs0, xw = P["stage_x"], L / 2 - W - 0.05
    hy = 4.5
    zs = f + 0.5
    k.box("Wood", (xs0, -hy, f), (xw, hy, zs), tint=(0.12, 0.12, 0.12), bevel=0.01, lmw=0.8, skip=("-z",), uv_rot=True)
    k.box("Wood", (xs0 - 0.03, -hy, zs - 0.04), (xs0 + 0.02, hy, zs + 0.005), tint=(0.5, 0.5, 0.5), bevel=0.005, lmw=0.3)
    k.collider(xs0, -hy, f, xw, hy, zs)
    for i in range(2):
        z = f + (i + 1) * 0.5 / 3
        k.box("Wood", (xs0 - 0.3 * (2 - i), hy - 1.1, f), (xs0 - 0.3 * (1 - i), hy - 0.2, z), tint=(0.15, 0.15, 0.15), bevel=0.006, lmw=0.3, skip=("-z",))
        k.collider(xs0 - 0.3 * (2 - i), hy - 1.1, f, xs0 - 0.3 * (1 - i), hy - 0.2, z)
    # the curtain: pleated red velvet from a track at the ceiling, its hem on the stage
    ci = f + P["ceiling"]
    xc = xw - 0.12
    zt = ci - 0.08
    folds = 44
    span = 2 * hy + 0.3

    def cur(u, v):
        y = -hy - 0.15 + span * u
        ph = u * folds * 2 * math.pi
        a = 0.075 * (0.55 + 0.45 * v)
        return (xc - a * (0.5 + 0.5 * math.sin(ph)) - 0.02 * (1 - v) * math.sin(ph * 0.5 + 1.3), y, zs + 0.01 + (zt - zs - 0.01) * v)
    k.grid("Props", cur, folds * 4, 8, uv=("cell", "velvet"), lmw=0.9, vlit=True, flip=True)
    # the valance (tighter pleats) and the side legs
    def val(u, v):
        y = -hy - 0.3 + (span + 0.3) * u
        ph = u * folds * 3 * math.pi
        return (xc - 0.16 - 0.05 * (0.5 + 0.5 * math.sin(ph)), y, zt - 0.4 + 0.4 * v - 0.03 * math.sin(math.pi * v) * 0)
    k.grid("Props", val, folds * 4, 2, uv=("cell", "velvet"), lmw=0.4, flip=True)
    for s in (-1, 1):
        def leg(u, v, s=s):
            x = xs0 + 0.5 + (xc - 0.2 - xs0 - 0.5) * u
            ph = u * 8 * 2 * math.pi
            return (x, s * (hy + 0.05 + 0.06 * (0.5 + 0.5 * math.sin(ph))), zs + 0.01 + (zt - zs) * v)
        k.grid("Props", leg, 32, 5, uv=("cell", "velvet"), lmw=0.4, both=True)
    k.box("Props", (xc - 0.25, -hy - 0.4, zt), (xc + 0.05, hy + 0.4, zt + 0.05), uv=("cell", "iron_black"), lmw=0.1)
    # the blue neon star hung in front of the curtain on two chains
    sx = xc - 0.32
    neon_sign(k, (sx, 0.0, f + 2.35), (0, 1, 0), (0, 0, 1), 0.95, "star", power=10.0, backing=False)
    for yy in (-0.3, 0.3):
        k.tube("Props", [(sx, yy, f + 2.75), (sx, yy * 0.9, zt)], 0.003, sides=4, uv=("cell", "steel_dark"), lmw=0.0)
    # gear: drums (x 14.5), two amps, a mic on a stand, a monitor wedge, a guitar on a stand, cables
    _drums(k, xw - 1.15, 0.9, zs)
    for (ay, h) in ((-2.6, 0.62), (2.7, 0.5)):
        k.box("Props", (xw - 0.85, ay - 0.35, zs), (xw - 0.5, ay + 0.35, zs + h), bevel=0.02, uv=("cell", "tolex"), lmw=0.3)
        k.box("Props", (xw - 0.86, ay - 0.3, zs + 0.06), (xw - 0.84, ay + 0.3, zs + h - 0.12), uv=("cell", "speaker"), lmw=0.1)
        k.box("Props", (xw - 0.86, ay - 0.3, zs + h - 0.1), (xw - 0.84, ay + 0.3, zs + h - 0.03), uv=("cell", "brass"), lmw=0.05)
        k.light("POINT", (xw - 0.9, ay + 0.25, zs + h - 0.06), (1.0, 0.1, 0.05), 0.4, radius=0.01)
    mx, my = xs0 + 0.45, -0.4
    k.lathe("Props", [(0.0, 0.0), (0.16, 0.0), (0.15, 0.015), (0.015, 0.03)], sides=12, M=Matrix.Translation((mx, my, zs)), uv=("cell", "iron_black"), lmw=0.05, cap0=False)
    k.cyl("Props", (mx, my, zs), (mx, my, zs + 1.45), 0.009, sides=6, uv=("cell", "chrome"), lmw=0.02)
    k.cyl("Props", (mx, my, zs + 1.45), (mx - 0.14, my, zs + 1.52), 0.017, r1=0.024, sides=8, uv=("cell", "steel_dark"), lmw=0.01)
    k.prism("Props", [(-0.25, 0.0), (0.25, 0.0), (0.25, 0.16), (-0.25, 0.32)], -0.22, 0.22,
            M=Matrix.Translation((xs0 + 0.35, 1.4, zs)) @ _wedge_frame(), bevel=0.01, uv=("cell", "tolex"), lmw=0.1)
    _guitar(k, xw - 0.7, -1.6, zs)
    rnd = random.Random(5)
    for (a, b) in (((mx, my), (xw - 0.7, -2.4)), ((xw - 0.85, 2.5), (xw - 1.3, 0.6)), ((xs0 + 0.35, 1.4), (xw - 0.7, 2.5))):
        pts = []
        for i in range(9):
            t = i / 8
            pts.append((a[0] + (b[0] - a[0]) * t + 0.15 * math.sin(t * 7 + rnd.random()), a[1] + (b[1] - a[1]) * t + 0.12 * math.sin(t * 5), zs + 0.008))
        k.tube("Props", pts, 0.007, sides=4, uv=("cell", "rubber"), lmw=0.02)
    # stage lights: a pipe batten with three PAR cans aimed at the stage, gelled red / amber / blue
    bx = xs0 + 0.2
    k.cyl("Props", (bx, -3.0, ci - 0.4), (bx, 3.0, ci - 0.4), 0.024, sides=8, uv=("cell", "iron_black"), lmw=0.05)
    for yy in (-3.0, 3.0):
        k.cyl("Props", (bx, yy, ci - 0.4), (bx, yy, ci), 0.012, sides=6, uv=("cell", "iron_black"), lmw=0.02)
    for yy, col, pw in ((-1.8, (1.0, 0.08, 0.05), 160.0), (0.2, (1.0, 0.45, 0.12), 120.0), (2.1, (0.2, 0.3, 1.0), 130.0)):
        a = Vector((bx, yy, ci - 0.5))
        t = Vector((xw - 1.0, yy * 0.4, zs + 0.6))
        dvec = (t - a).normalized()
        k.cyl("Props", a - dvec * 0.12, a + dvec * 0.14, 0.1, sides=12, uv=("cell", "iron_black"), lmw=0.05)
        k.cyl("Props", a + dvec * 0.141, a + dvec * 0.142, 0.085, sides=12, uv=("cell", "glow_red" if col[0] > 0.9 and col[1] < 0.2 else "glow_amber" if col[1] > 0.3 else "neon_blue"), lmw=0.0)
        k.light("SPOT", tuple(a + dvec * 0.2), col, pw, radius=0.06, angle=34.0, blend=0.5, aim=tuple(t))


def _wedge_frame():
    return Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def _drums(k, x, y, z):
    # bass drum on its side (axis along x), the front head facing the room (-x)
    k.lathe("Props", [(0.27, 0.0), (0.28, 0.01), (0.28, 0.4), (0.27, 0.41)], sides=20,
            M=Matrix.Translation((x - 0.2, y, z + 0.29)) @ Matrix.Rotation(math.pi / 2, 4, "Y"), uv=("cell", "paint_red"), lmw=0.3)
    k.lathe("Props", [(0.0, -0.002), (0.27, -0.002)], sides=20, M=Matrix.Translation((x - 0.2, y, z + 0.29)) @ Matrix.Rotation(math.pi / 2, 4, "Y"),
            uv=("cell", "plastic_white"), lmw=0.2, cap0=False, cap1=False)
    for (dx, dy, r, h, zz) in ((-0.35, -0.42, 0.18, 0.14, 0.62), (0.05, 0.42, 0.22, 0.4, 0.2), (-0.05, 0.05, 0.15, 0.16, 0.78), (-0.05, -0.2, 0.16, 0.17, 0.8)):
        k.lathe("Props", [(r, 0.0), (r + 0.005, 0.005), (r + 0.005, h - 0.005), (r, h), (0.0, h)], sides=16, M=Matrix.Translation((x + dx, y + dy, z + zz)),
                uv=("cell", "paint_red"), lmw=0.2)
        k.cyl("Props", (x + dx, y + dy, z), (x + dx, y + dy, z + zz), 0.01, sides=5, uv=("cell", "chrome"), lmw=0.02)
    for (dx, dy, r, zz) in ((-0.4, -0.75, 0.18, 0.95), (0.2, -0.6, 0.22, 1.35), (0.25, 0.75, 0.24, 1.25)):
        k.lathe("Props", [(0.0, 0.02), (0.05, 0.018), (r, 0.0), (r, -0.004), (0.0, 0.012)], sides=16, M=Matrix.Translation((x + dx, y + dy, z + zz)),
                uv=("cell", "brass"), lmw=0.1, smooth=True)
        k.cyl("Props", (x + dx, y + dy, z), (x + dx, y + dy, z + zz), 0.01, sides=5, uv=("cell", "chrome"), lmw=0.02)
    k.lathe("Props", [(0.0, 0.5), (0.17, 0.5), (0.18, 0.56), (0.0, 0.58)], sides=12, M=Matrix.Translation((x + 0.45, y, z)), uv=("cell", "plastic_black"), lmw=0.05)
    k.cyl("Props", (x + 0.45, y, z), (x + 0.45, y, z + 0.5), 0.02, sides=6, uv=("cell", "chrome"), lmw=0.02)


def _guitar(k, x, y, z):
    body = [(0.0, 0.0), (0.18, 0.03), (0.22, 0.16), (0.15, 0.3), (0.17, 0.4), (0.1, 0.46), (0.0, 0.44), (-0.1, 0.46), (-0.17, 0.4), (-0.15, 0.3), (-0.22, 0.16), (-0.18, 0.03)]
    M = Matrix.Translation((x, y, z + 0.12)) @ Matrix.Rotation(math.radians(-12), 4, "Y") @ _wedge_frame()
    k.prism("Props", [(a, b) for a, b in body], -0.025, 0.025, M=M, uv=("cell", "cooler_red"), lmw=0.1, bevel=0.008)
    k.box("Props", (-0.025, 0.44, -0.012), (0.025, 1.02, 0.012), M=M, uv=("cell", "wood_light"), lmw=0.02)
    k.box("Props", (-0.035, 1.0, -0.015), (0.035, 1.14, 0.015), M=M, uv=("cell", "paint_black"), lmw=0.02)
    for (a, b) in (((-0.15, -0.12), (0.0, 0.05)), ((0.15, -0.12), (0.0, 0.05))):
        k.cyl("Props", (x + a[0] * 0.2, y + a[1], z), (x + 0.02, y, z + 0.5), 0.008, sides=4, uv=("cell", "iron_black"), lmw=0.01)


# ------------------------------------------------------------------ the dance floor, fans, signs, TV
def floor_dressing(k, P):
    f = P["floor"]
    ci = f + P["ceiling"]
    D, W = P["D"], P["wall"]
    rnd = random.Random(17)
    for (tx, ty, n) in ((7.1, -5.6, 3), (11.0, -5.3, 2), (11.0, 5.4, 3), (7.6, 1.6, 3)):
        k.lathe("Wood", [(0.0, 0.72), (0.38, 0.72), (0.385, 0.735), (0.38, 0.75), (0.0, 0.75)], sides=20, M=Matrix.Translation((tx, ty, f)), lmw=0.5, tint=(0.8, 0.8, 0.8))
        k.lathe("Props", [(0.38, 0.715), (0.388, 0.72), (0.388, 0.75), (0.38, 0.755)], sides=20, M=Matrix.Translation((tx, ty, f)), uv=("cell", "chrome"), lmw=0.05, cap0=False, cap1=False)
        k.cyl("Props", (tx, ty, f), (tx, ty, f + 0.72), 0.035, sides=8, uv=("cell", "chrome"), lmw=0.05)
        k.lathe("Props", [(0.0, 0.0), (0.24, 0.0), (0.22, 0.02), (0.04, 0.04)], sides=12, M=Matrix.Translation((tx, ty, f)), uv=("cell", "iron_black"), lmw=0.05, cap0=False)
        k.collider(tx - 0.38, ty - 0.38, f, tx + 0.38, ty + 0.38, f + 0.75)
        for j in range(n):
            a = rnd.uniform(0, 360) if n < 3 else j * 120 + rnd.uniform(-20, 20)
            _chair(k, tx + 0.6 * math.cos(math.radians(a)), ty + 0.6 * math.sin(math.radians(a)), f, a + 180 + rnd.uniform(-15, 15))
        if rnd.random() < 0.7:
            _bar_item(k, rnd.choice(["beer", "rocks"]), tx + rnd.uniform(-0.15, 0.15), ty + rnd.uniform(-0.15, 0.15), f + 0.75)
    # ceiling fans
    for fx in (-3.0, 7.6):
        z = ci - 0.55
        k.cyl("Props", (fx, 0.0, ci - 0.3), (fx, 0.0, z + 0.12), 0.014, sides=6, uv=("cell", "brass"), lmw=0.02)
        k.lathe("Props", [(0.0, 0.0), (0.1, 0.02), (0.12, 0.07), (0.1, 0.12), (0.03, 0.14)], sides=12, M=Matrix.Translation((fx, 0.0, z)), uv=("cell", "brass"), lmw=0.1)
        for b in range(5):
            a = b * 72 + 13
            M = Matrix.Translation((fx, 0.0, z + 0.05)) @ Matrix.Rotation(math.radians(a), 4, "Z") @ Matrix.Rotation(math.radians(8), 4, "X")
            k.box("Wood", (0.14, -0.065, -0.006), (0.66, 0.065, 0.006), M=M, bevel=0.004, lmw=0.1, tint=(0.6, 0.6, 0.6))
    # the CRT on a bracket over the bar's east end, aimed at the stools
    tvx, tvy, tvz = P["px"] + 0.6, 3.1, f + 2.35
    k.box("Props", (tvx - 0.27, tvy - 0.3, tvz - 0.25), (tvx + 0.27, tvy + 0.3, tvz + 0.22), bevel=0.04, segs=2, uv=("cell", "plastic_black"), lmw=0.2)
    k.box("Props", (tvx + 0.27, tvy - 0.24, tvz - 0.19), (tvx + 0.29, tvy + 0.24, tvz + 0.16), uv=("cell", "tv_game"), lmw=0.0)
    k.box("Props", (P["px"] + 0.08, tvy - 0.05, tvz - 0.32), (tvx, tvy + 0.05, tvz - 0.27), uv=("cell", "iron_black"), lmw=0.02)
    k.light("AREA", (tvx + 0.34, tvy, tvz - 0.02), (0.55, 0.75, 0.6), 2.5, size=(0.46, 0.34), aim=(tvx + 3, tvy, tvz - 0.5))
    # pendant lamps over the bar (amber schoolhouse glass on cords)
    yp = P["bar_front"] + 0.32
    for i in range(5):
        x = P["bar_x0"] + 1.0 + i * (P["bar_x1"] - P["bar_x0"] - 2.2) / 4
        z = f + 2.25
        k.cyl("Props", (x, yp, z + 0.2), (x, yp, ci), 0.004, sides=4, uv=("cell", "plastic_black"), lmw=0.0)
        k.lathe("Props", [(0.02, 0.2), (0.05, 0.19), (0.09, 0.1), (0.12, 0.03), (0.125, 0.0)], sides=16, M=Matrix.Translation((x, yp, z)),
                uv=("cell", "amber_glass"), lmw=0.05, cap0=False, cap1=False)
        k.cyl("Props", (x, yp, z + 0.2), (x, yp, z + 0.25), 0.025, sides=8, uv=("cell", "brass"), lmw=0.0)
        k.lathe("Props", [(0.0, 0.03), (0.035, 0.05), (0.03, 0.1), (0.0, 0.12)], sides=8, M=Matrix.Translation((x, yp, z)), uv=("cell", "bulb"), lmw=0.0)
        k.light("POINT", (x, yp, z + 0.08), WARM, 48.0, radius=0.06)
        glow.halo(k, (x, yp, z + 0.04), 0.5, "amber")
    # lit beer signs (pictogram mirrors) on the walls; booth-side wall sconces between windows
    yb = D / 2 - W - 0.05
    k.box("Props", (5.0, yb - 0.02, f + 1.75), (6.2, yb, f + 2.45), uv=("cell", "beer_mirror"), lmw=0.2)
    k.box("Props", (P["L"] / 2 - W - 0.07, -5.9, f + 1.7), (P["L"] / 2 - W - 0.05, -4.9, f + 2.3), uv=("cell", "beer_mirror"), lmw=0.2)
    k.light("POINT", (5.6, yb - 0.4, f + 2.1), (1.0, 0.7, 0.35), 4.0, radius=0.2)
    # the dartboard on the partition by the entrance, its cabinet open
    dx, dy, dz = P["px"] + 0.1, -2.55, f + 1.73
    k.box("Wood", (P["px"] + 0.075, dy - 0.38, dz - 0.4), (dx + 0.06, dy + 0.38, dz + 0.4), bevel=0.01, tint=(0.4, 0.4, 0.4), lmw=0.3)
    for s in (-1, 1):
        k.box("Wood", (dx + 0.04, dy + s * 0.38 - (0.0 if s > 0 else 0.02), dz - 0.4), (dx + 0.4, dy + s * 0.38 + (0.02 if s > 0 else 0.0), dz + 0.4), bevel=0.005,
              tint=(0.5, 0.5, 0.5), lmw=0.2)
    k.cyl("Props", (dx + 0.06, dy, dz), (dx + 0.1, dy, dz), 0.225, sides=24, uv=lambda co, nn: _disc_uv("dartboard", co.y - dy, co.z - dz, 0.225), lmw=0.2)
    k.light("SPOT", (dx + 0.6, dy, dz + 0.6), WARM, 6.0, radius=0.03, angle=40.0, blend=0.5, aim=(dx, dy, dz))
    k.box("Props", (P["px"] + 2.37 + 0.08, dy - 0.3, f), (P["px"] + 2.37 + 0.12, dy + 0.3, f + 0.004), uv=("cell", "paint_white"), lmw=0.0)
    # the cigarette machine by the door
    cmx, cmy = P["px"] + 0.1, -5.9
    k.box("Props", (cmx, cmy - 0.42, f), (cmx + 0.5, cmy + 0.42, f + 1.65), bevel=0.02, uv=("cell", "steel_dark"), lmw=0.4)
    k.box("Props", (cmx + 0.5, cmy - 0.36, f + 0.75), (cmx + 0.52, cmy + 0.36, f + 1.5), uv=("cell", "cig_machine"), lmw=0.0)
    for i in range(6):
        k.box("Props", (cmx + 0.5, cmy - 0.33 + i * 0.12, f + 0.55), (cmx + 0.56, cmy - 0.27 + i * 0.12, f + 0.62), uv=("cell", "chrome"), lmw=0.01)
    k.collider(cmx, cmy - 0.42, f, cmx + 0.5, cmy + 0.42, f + 1.65)
    k.light("AREA", (cmx + 0.58, cmy, f + 1.1), (1.0, 0.92, 0.8), 1.2, size=(0.7, 0.7), aim=(cmx + 3, cmy, f + 0.9))
    # coat hooks by the door, a trash can
    for i in range(4):
        hx = P["door_x"] - 1.45 + i * 0.25
        k.cyl("Props", (hx, -D / 2 + W + 0.05, f + 1.65), (hx, -D / 2 + W + 0.12, f + 1.7), 0.008, sides=4, uv=("cell", "brass"), lmw=0.01)
    k.lathe("Props", [(0.17, 0.0), (0.19, 0.6), (0.2, 0.62)], sides=12, M=Matrix.Translation((P["px"] + 0.35, -4.0, f)), uv=("cell", "plastic_black"), lmw=0.1, cap1=False)


def _fillet(pts, r, n):
    from lib import common
    return common.fillet_polyline(pts, r, n, closed=False)


def _disc_uv(name, a, b, r):
    rr = __import__("town2_bar_kit").cell_rect(tex.CELLS[name], inset=0.05)
    u = 0.5 + 0.5 * a / r
    v = 0.5 + 0.5 * b / r
    return (rr[0] + (rr[2] - rr[0]) * u, rr[1] + (rr[3] - rr[1]) * v)


def _chair(k, x, y, f, yaw):
    """A chrome tube café chair with an oxblood vinyl seat and back."""
    M = place(x, y, f, yaw)
    for sx in (-1, 1):
        pts = [(sx * 0.2, -0.2, 0.0), (sx * 0.2, -0.2, 0.43), (sx * 0.2, 0.18, 0.45), (sx * 0.19, 0.2, 0.86)]
        k.tube("Props", [tuple(M @ Vector(p)) for p in _fillet(pts, 0.05, 4)], 0.011, sides=6, uv=("cell", "chrome"), lmw=0.05)
        k.tube("Props", [tuple(M @ Vector((sx * 0.2, 0.18, 0.45))), tuple(M @ Vector((sx * 0.2, 0.2, 0.0)))], 0.011, sides=6, uv=("cell", "chrome"), lmw=0.05)
    cu = _cushion((0.42, 0.42, 0.06), crown={"+z": 0.012})
    k.add(cu, "Vinyl", M=M @ Matrix.Translation((0, 0, 0.48)), smooth=True, lmw=0.3)
    cu = _cushion((0.4, 0.05, 0.22), crown={"-y": 0.01})
    k.add(cu, "Vinyl", M=M @ Matrix.Translation((0, 0.2, 0.74)) @ Matrix.Rotation(math.radians(-8), 4, "X"), smooth=True, lmw=0.3)
    lo = M @ Vector((-0.22, -0.22, 0))
    hi = M @ Vector((0.22, 0.22, 0))
    k.collider(min(lo.x, hi.x), min(lo.y, hi.y), f, max(lo.x, hi.x), max(lo.y, hi.y), f + 0.5)


# ------------------------------------------------------------------ service block
def corridor(k, P):
    f = P["floor"]
    ci = f + P["ceiling"]
    L, W = P["L"], P["wall"]
    xe = -L / 2 + W + 0.05
    yc = (P["pr"] + P["pc"]) / 2
    # the doors: two restrooms (closed), the back room (closed), the back exit (closed, a push bar)
    for (x, y, s) in ((-14.875, P["pr"] + 0.075, 1), (-11.975, P["pr"] + 0.075, 1)):
        k.box("Wood", (x - 0.42, y - 0.02, f + 0.01), (x + 0.42, y + 0.025, f + 2.08), bevel=0.006, tint=(0.55, 0.55, 0.55), lmw=0.4)
        k.box("Props", (x + 0.3, y + 0.025, f + 0.95), (x + 0.36, y + 0.06, f + 1.0), uv=("cell", "brass"), lmw=0.01)
        k.box("Props", (x - 0.08, y + 0.025, f + 1.5), (x + 0.08, y + 0.03, f + 1.66), uv=("cell", "plastic_white"), lmw=0.02)
    # the back room's corridor door: open, swung in against the wall (the way in; the bar's is ajar)
    Md = Matrix.Translation((-12.97, P["pc"] + 0.075, f + 0.01)) @ Matrix.Rotation(math.radians(-90), 4, "Z")
    k.box("Wood", (-0.9, -0.045, 0.0), (0.0, 0.0, 2.07), M=Md, bevel=0.006, tint=(0.55, 0.55, 0.55), lmw=0.4)
    k.box("Props", (-0.84, -0.075, 0.95), (-0.78, -0.045, 1.0), M=Md, uv=("cell", "brass"), lmw=0.01)
    c = Md @ Vector((-0.45, -0.02, 0))
    k.collider(c.x - 0.1, c.y - 0.46, f, c.x + 0.1, c.y + 0.46, f + 2.08)
    k.box("Props", (xe, -1.2, f + 0.01), (xe + 0.05, -0.3, f + 2.08), uv=("cell", "paint_grey"), lmw=0.4)
    k.box("Props", (xe + 0.05, -1.15, f + 0.95), (xe + 0.11, -0.35, f + 1.02), uv=("cell", "stainless"), lmw=0.02)
    # exit sign (a red glowing box, no words), the caged bulb, a payphone, a mop bucket
    k.box("Props", (xe, -0.95, f + 2.25), (xe + 0.08, -0.55, f + 2.45), uv=("cell", "exit_red"), lmw=0.02)
    k.light("POINT", (xe + 0.2, -0.75, f + 2.3), (1.0, 0.1, 0.05), 1.2, radius=0.1)
    bx = -13.2
    k.lathe("Props", [(0.0, 0.0), (0.06, 0.0), (0.06, 0.03), (0.0, 0.035)], sides=8, M=Matrix.Translation((bx, yc, ci - 0.04)), uv=("cell", "iron_black"), lmw=0.0)
    k.lathe("Props", [(0.0, -0.13), (0.03, -0.13), (0.035, -0.07), (0.0, -0.03)], sides=8, M=Matrix.Translation((bx, yc, ci - 0.04)), uv=("cell", "bulb"), lmw=0.0)
    for a in range(0, 360, 60):
        ra = math.radians(a)
        k.tube("Props", [(bx + 0.06 * math.cos(ra), yc + 0.06 * math.sin(ra), ci - 0.04), (bx + 0.065 * math.cos(ra), yc + 0.065 * math.sin(ra), ci - 0.17),
                         (bx, yc, ci - 0.2)], 0.003, sides=3, uv=("cell", "iron_black"), lmw=0.0)
    k.light("POINT", (bx, yc, ci - 0.12), (1.0, 0.66, 0.36), 9.0, radius=0.03)
    glow.halo(k, (bx, yc, ci - 0.12), 0.35, "warm")
    px_, py_ = -11.0, P["pc"] - 0.075 - 0.02
    k.box("Props", (px_ - 0.18, py_ - 0.15, f + 1.0), (px_ + 0.18, py_, f + 1.72), bevel=0.015, uv=("cell", "stainless"), lmw=0.2)
    k.box("Props", (px_ - 0.05, py_ - 0.2, f + 1.35), (px_ + 0.1, py_ - 0.14, f + 1.6), uv=("cell", "plastic_black"), lmw=0.02)
    k.cyl("Props", (px_ - 0.13, py_ - 0.17, f + 1.35), (px_ - 0.13, py_ - 0.17, f + 1.62), 0.025, sides=6, uv=("cell", "plastic_black"), lmw=0.02)
    k.tube("Props", [(px_ - 0.13, py_ - 0.17, f + 1.35), (px_ - 0.1, py_ - 0.2, f + 1.15), (px_ - 0.05, py_ - 0.18, f + 1.1)], 0.005, sides=4, uv=("cell", "chrome"), lmw=0.0)
    k.lathe("Props", [(0.14, 0.0), (0.16, 0.3), (0.165, 0.31)], sides=10, M=Matrix.Translation((-15.3, -1.25, f)), uv=("cell", "paint_yellow"), lmw=0.05, cap1=False)
    k.cyl("Props", (-15.3, -1.25, f + 0.1), (-15.15, -1.0, f + 1.4), 0.012, sides=5, uv=("cell", "wood_light"), lmw=0.01)


def back_room(k, P):
    f = P["floor"]
    ci = f + P["ceiling"]
    L, D, W = P["L"], P["D"], P["wall"]
    xe = -L / 2 + W + 0.05                    # the east wall's lining face
    yn = D / 2 - W - 0.05                     # the back wall's lining face
    ys = P["pc"] + 0.075                      # the corridor wall's face
    xp = P["px"] - 0.075                      # the partition's face
    # the door from behind the bar, ajar 28 deg: hinged at its front jamb, swung into the room, so
    # the gap opens by the back-bar: from the bartender's aisle it shows the back wall (the
    # monitors, the hooks)
    d0, d1 = P["backroom_door"]
    hy = d0
    ang = math.radians(28.0)
    wdoor = d1 - d0
    M = Matrix.Translation((xp, hy, f + 0.01)) @ Matrix.Rotation(ang, 4, "Z")
    k.box("Wood", (-0.045, 0.0, 0.0), (0.0, wdoor - 0.01, 2.07), M=M, bevel=0.006, tint=(0.6, 0.6, 0.6), lmw=0.6)
    k.box("Props", (-0.065, wdoor - 0.14, 0.95), (-0.045, wdoor - 0.08, 1.0), M=M, uv=("cell", "brass"), lmw=0.01)
    k.box("Props", (0.0, wdoor - 0.14, 0.95), (0.02, wdoor - 0.08, 1.0), M=M, uv=("cell", "brass"), lmw=0.01)
    c = M @ Vector((-0.02, wdoor / 2, 1.0))
    k.collider(c.x - 0.3, c.y - 0.42, f, c.x + 0.3, c.y + 0.42, f + 2.08)
    # the hook rail on the east wall, opposite the door: white masks, two dark jackets
    rz = f + 1.75
    k.box("Wood", (xe, 2.6, rz - 0.05), (xe + 0.03, 6.3, rz + 0.07), bevel=0.006, tint=(0.6, 0.6, 0.6), lmw=0.4)
    for i in range(10):
        y = 2.8 + i * 0.37
        k.tube("Props", [(xe + 0.03, y, rz + 0.01), (xe + 0.1, y, rz + 0.0), (xe + 0.12, y, rz + 0.04)], 0.006, sides=4, uv=("cell", "steel_dark"), lmw=0.01)
        if i in (2, 6):
            _jacket(k, xe + 0.06, y, rz)
        elif i != 8:
            _mask(k, xe + 0.12, y, rz - 0.17, tilt=random.Random(i).uniform(-8, 8))
    # a second hook rail on the back wall by the door, in the gap's view: more masks
    k.box("Wood", (-14.6, yn - 0.03, rz + 0.4), (-13.25, yn, rz + 0.52), bevel=0.006, tint=(0.6, 0.6, 0.6), lmw=0.4)
    for i in range(4):
        x = -14.45 + i * 0.36
        k.tube("Props", [(x, yn - 0.03, rz + 0.46), (x, yn - 0.1, rz + 0.45), (x, yn - 0.12, rz + 0.49)], 0.006, sides=4, uv=("cell", "steel_dark"), lmw=0.01)
        _mask(k, x, yn - 0.12, rz + 0.28, tilt=random.Random(40 + i).uniform(-8, 8), facing=-1)
    # and one on a nail by the monitors, where the door's gap shows it
    k.tube("Props", [(-10.86, yn, f + 1.72), (-10.86, yn - 0.06, f + 1.71)], 0.004, sides=4, uv=("cell", "steel_dark"), lmw=0.0)
    _mask(k, -10.86, yn - 0.08, f + 1.56, tilt=6.0, facing=-1)
    # the monitor wall: a steel desk against the back wall, four CRTs (2 x 2) and a recorder
    mx0, mx1 = -13.0, -10.65
    k.box("Props", (mx0, yn - 0.7, f + 0.72), (mx1, yn, f + 0.76), uv=("cell", "steel_dark"), lmw=0.6)
    for x in (mx0 + 0.05, mx1 - 0.05):
        for y in (yn - 0.65, yn - 0.05):
            k.box("Props", (x - 0.025, y - 0.025, f), (x + 0.025, y + 0.025, f + 0.72), uv=("cell", "steel_dark"), lmw=0.02)
    k.collider(mx0, yn - 0.7, f, mx1, yn, f + 0.76)
    k.box("Props", (mx0 + 0.15, yn - 0.6, f + 1.5), (mx1 - 0.15, yn - 0.05, f + 1.53), uv=("cell", "steel_dark"), lmw=0.2)
    for i, (cx_, cz_) in enumerate(((-12.4, f + 1.04), (-11.3, f + 1.04), (-12.4, f + 1.8), (-11.3, f + 1.8))):
        z0 = cz_ - 0.28 if i < 2 else f + 1.53
        k.box("Props", (cx_ - 0.24, yn - 0.55, z0), (cx_ + 0.24, yn - 0.12, z0 + 0.44), bevel=0.03, uv=("cell", "plastic_black"), lmw=0.2)
        k.box("Props", (cx_ - 0.19, yn - 0.565, z0 + 0.06), (cx_ + 0.19, yn - 0.55, z0 + 0.36), uv=("cell", "crt_" + "abcd"[i]), lmw=0.0)
    k.box("Props", (-12.15, yn - 0.6, f + 0.76), (-11.55, yn - 0.25, f + 0.84), bevel=0.005, uv=("cell", "plastic_black"), lmw=0.05)
    k.box("Props", (-11.8, yn - 0.605, f + 0.79), (-11.6, yn - 0.6, f + 0.81), uv=("cell", "neon_green"), lmw=0.0)
    k.light("AREA", (-11.85, yn - 0.62, f + 1.4), (0.3, 0.55, 1.0), 30.0, size=(1.0, 0.8), aim=(-11.85, yn - 3, f + 1.1))
    glow.halo(k, (-11.85, yn - 0.6, f + 1.4), 1.3, "blue", normal=(0, -1, 0))
    # the briefing table: folding table, six chairs; the estate's blueprint, photos, radios, a coffee can
    tx, ty = -13.1, 2.7
    k.box("Props", (tx - 0.95, ty - 0.4, f + 0.71), (tx + 0.95, ty + 0.4, f + 0.75), bevel=0.008, uv=("cell", "paint_cream"), lmw=1.0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            k.cyl("Props", (tx + sx * 0.85, ty + sy * 0.32, f), (tx + sx * 0.85, ty + sy * 0.32, f + 0.71), 0.012, sides=5, uv=("cell", "steel_dark"), lmw=0.01)
    k.collider(tx - 0.95, ty - 0.4, f, tx + 0.95, ty + 0.4, f + 0.75)
    k.box("Props", (tx - 0.55, ty - 0.3, f + 0.751), (tx + 0.25, ty + 0.25, f + 0.753), uv=("cell", "blueprint"), lmw=0.4,
          M=rot_z(4, (tx, ty, 0)))
    k.box("Props", (tx + 0.35, ty - 0.25, f + 0.751), (tx + 0.75, ty + 0.05, f + 0.754), uv=("cell", "photos"), lmw=0.2, M=rot_z(-9, (tx, ty, 0)))
    for i in range(3):
        rx = tx - 0.8 + i * 0.12
        k.box("Props", (rx, ty + 0.15, f + 0.75), (rx + 0.06, ty + 0.19, f + 0.93), bevel=0.006, uv=("cell", "plastic_black"), lmw=0.02)
        k.cyl("Props", (rx + 0.015, ty + 0.17, f + 0.93), (rx + 0.015, ty + 0.17, f + 1.05), 0.005, sides=4, uv=("cell", "plastic_black"), lmw=0.0)
    k.cyl("Props", (tx + 0.6, ty + 0.25, f + 0.75), (tx + 0.6, ty + 0.25, f + 0.9), 0.05, sides=10, uv=("cell", "paint_red"), lmw=0.02)
    rnd = random.Random(31)
    for j in range(6):
        sx = -1 if j < 3 else 1
        cx_ = tx - 0.6 + (j % 3) * 0.6
        _folding_chair(k, cx_ + rnd.uniform(-0.05, 0.05), ty + sx * 0.62, f, 90 + (0 if sx > 0 else 180) + rnd.uniform(-12, 12))
    # the bare bulb over it (low), the cork board with the topo map on the corridor wall
    k.cyl("Props", (tx, ty, ci), (tx, ty, f + 2.4), 0.004, sides=4, uv=("cell", "plastic_black"), lmw=0.0)
    k.lathe("Props", [(0.0, -0.11), (0.03, -0.1), (0.032, -0.05), (0.012, -0.02), (0.012, 0.0)], sides=8, M=Matrix.Translation((tx, ty, f + 2.4)), uv=("cell", "bulb_dim"), lmw=0.0)
    k.light("POINT", (tx, ty, f + 2.32), (1.0, 0.62, 0.32), 5.0, radius=0.03)
    glow.halo(k, (tx, ty, f + 2.33), 0.3, "warm")
    k.box("Props", (-15.6, ys, f + 1.1), (-14.05, ys + 0.02, f + 2.1), uv=("cell", "corkboard"), lmw=0.3)
    k.box("Props", (-12.95, ys, f + 1.2), (-11.6, ys + 0.015, f + 2.0), uv=("cell", "map_board"), lmw=0.3)
    # kegs along the back wall's east end, crates and cases, a wire shelf, the safe in the corner
    for i in range(4):
        for j in range(2 if i < 2 else 1):
            kx, ky = xe + 0.32 + i * 0.0, yn - 0.32 - i * 0.62
            if i >= 2:
                kx, ky = xe + 0.32 + 0.62 * (i - 2) + 0.62, yn - 0.32
            _keg(k, kx, ky, f + j * 0.6)
    for (cx_, cy_, nz) in ((-14.6, 4.7, 3), (-11.0, 3.4, 2), (-11.45, 3.4, 4)):
        for z in range(nz):
            k.box("Props", (cx_ - 0.2, cy_ - 0.17, f + z * 0.26), (cx_ + 0.2, cy_ + 0.17, f + z * 0.26 + 0.25), bevel=0.01,
                  uv=("cell", "plastic_red" if z % 2 == 0 else "cardboard"), lmw=0.15)
        k.collider(cx_ - 0.2, cy_ - 0.17, f, cx_ + 0.2, cy_ + 0.17, f + nz * 0.26)
    shx = xe
    for z in (f + 0.05, f + 0.6, f + 1.15, f + 1.7):
        k.box("Props", (shx, 0.35, z), (shx + 0.45, 2.3, z + 0.02), uv=("cell", "chrome"), lmw=0.2)
    for (yy) in (0.37, 2.28):
        for xx in (shx + 0.02, shx + 0.43):
            k.cyl("Props", (xx, yy, f), (xx, yy, f + 1.8), 0.01, sides=4, uv=("cell", "chrome"), lmw=0.01)
    for z in (f + 0.07, f + 0.62, f + 1.17):
        for b in range(3):
            k.box("Props", (shx + 0.05, 0.45 + b * 0.6, z), (shx + 0.4, 0.95 + b * 0.6, z + 0.3 - (b % 2) * 0.08), bevel=0.006, uv=("cell", "cardboard"), lmw=0.1)
    k.collider(shx, 0.35, f, shx + 0.45, 2.3, f + 1.8)
    sx_, sy_ = -11.2, 0.55
    k.box("Props", (sx_ - 0.38, sy_ - 0.34, f), (sx_ + 0.38, sy_ + 0.34, f + 0.95), bevel=0.02, segs=2, uv=("cell", "safe"), lmw=0.4)
    k.cyl("Props", (sx_ - 0.05, sy_ + 0.34, f + 0.62), (sx_ - 0.05, sy_ + 0.37, f + 0.62), 0.05, sides=12, uv=("cell", "chrome"), lmw=0.01)
    k.cyl("Props", (sx_ + 0.2, sy_ + 0.34, f + 0.5), (sx_ + 0.2, sy_ + 0.38, f + 0.5), 0.015, sides=6, uv=("cell", "brass"), lmw=0.01)
    k.collider(sx_ - 0.38, sy_ - 0.34, f, sx_ + 0.38, sy_ + 0.34, f + 0.95)


def _keg(k, x, y, z):
    prof = [(0.0, 0.0), (0.2, 0.0), (0.205, 0.03), (0.2, 0.05), (0.205, 0.06), (0.2, 0.08), (0.205, 0.5), (0.2, 0.52),
            (0.205, 0.54), (0.2, 0.56), (0.12, 0.585), (0.04, 0.59), (0.0, 0.59)]
    k.lathe("Props", prof, sides=16, M=Matrix.Translation((x, y, z)), uv=("cell", "keg"), lmw=0.2)
    k.collider(x - 0.2, y - 0.2, z, x + 0.2, y + 0.2, z + 0.59)


def _mask(k, x, y, z, tilt=0.0, facing=0):
    """A blank white face mask (the invaders'), hung by its strap: eye holes, a nose ridge."""
    w, h, d = 0.085, 0.115, 0.06

    def fn(u, v):
        a = (u - 0.5) * 2
        b = (v - 0.5) * 2
        r = min(1.0, a * a + b * b)
        depth = d * math.sqrt(max(0.0, 1 - 0.85 * r))
        nose = 0.012 * math.exp(-(a / 0.12) ** 2) * math.exp(-((b + 0.05) / 0.35) ** 2)
        brow = -0.006 * math.exp(-((b - 0.3) / 0.08) ** 2)
        return (depth + nose + brow, a * w * (1 - 0.15 * max(0, -b)), b * h)
    bm = bmesh.new()
    nu, nv = 12, 14
    V = [[bm.verts.new(fn(i / nu, j / nv)) for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            uc, vc = (i + 0.5) / nu, (j + 0.5) / nv
            a, b = (uc - 0.5) * 2, (vc - 0.5) * 2
            if a * a + b * b > 1.02:
                continue
            if abs(abs(a) - 0.38) < 0.13 and abs(b - 0.18) < 0.1:      # eye holes
                continue
            bm.faces.new([V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]])
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    # facing 0: the face looks +x (the east wall's rail); -1: it looks -y (the back wall's)
    M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(-90 * facing * -1) if facing else 0.0, 4, "Z") @ Matrix.Rotation(math.radians(tilt), 4, "X")
    k.add(bm, "Props", M=M, uv=("cell", "mask"), smooth=True, lmw=0.4)
    if facing:
        return
    k.tube("Props", [(x + 0.005, y - w, z + 0.02), (x - 0.02, y - 0.04, z + 0.14), (x - 0.07, y, z + 0.17), (x - 0.02, y + 0.04, z + 0.14), (x + 0.005, y + w, z + 0.02)],
           0.004, sides=4, uv=("cell", "plastic_black"), lmw=0.01)


def _jacket(k, x, y, z):
    """A dark work jacket on a hook: a draped shape (a lathe-ish sack) with shoulders."""
    def fn(u, v):
        a = u * 2 * math.pi
        zz = -0.75 * (1 - v)
        r = 0.13 + 0.09 * min(1.0, (1 - v) * 4) - 0.03 * (1 - v)
        wx = 0.6 + 0.15 * math.sin(v * 9)
        return (x + 0.08 + r * 0.45 * math.cos(a), y + r * 1.6 * math.sin(a) * (0.6 + 0.4 * min(1, (1 - v) * 3)), z + 0.04 + zz)
    k.grid("Props", fn, 16, 8, uv=("cell", "canvas"), lmw=0.2, tint=(0.25, 0.25, 0.28))


def _folding_chair(k, x, y, f, yaw):
    M = place(x, y, f, yaw)
    for sx in (-1, 1):
        k.tube("Props", [tuple(M @ Vector((sx * 0.19, -0.2, 0.0))), tuple(M @ Vector((sx * 0.19, 0.16, 0.46))), tuple(M @ Vector((sx * 0.19, 0.2, 0.82)))], 0.01, sides=5,
               uv=("cell", "steel_dark"), lmw=0.02)
        k.tube("Props", [tuple(M @ Vector((sx * 0.19, 0.2, 0.0))), tuple(M @ Vector((sx * 0.19, -0.18, 0.46)))], 0.01, sides=5, uv=("cell", "steel_dark"), lmw=0.02)
    k.box("Props", (-0.2, -0.2, 0.44), (0.2, 0.18, 0.47), M=M, bevel=0.01, uv=("cell", "steel_dark"), lmw=0.1)
    k.box("Props", (-0.2, 0.17, 0.62), (0.2, 0.2, 0.8), M=M, bevel=0.008, uv=("cell", "steel_dark"), lmw=0.05)


# ------------------------------------------------------------------ the whole interior
def build_interior(k, P):
    P.setdefault("pool", (-2.6, -1.05))
    P.setdefault("jukebox", (5.55, 6.33))
    P.setdefault("stage_x", 12.35)
    for fn in (bar_counter, stools, back_bar, booths, pool_table, jukebox, stage, floor_dressing, corridor, back_room):
        k.section = fn.__name__
        fn(k, P)
    # faint fill so the bar room isn't pitch black between the pools (bounce off a smoky ceiling)
    f = P["floor"]
    k.light("AREA", (1.5, 0.0, f + P["ceiling"] - 0.05), (1.0, 0.7, 0.45), 40.0, size=(20.0, 9.0), aim=(1.5, 0.0, 0.0))
