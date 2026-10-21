"""Sleek luxury electric car (an original design, no brand) for the garage.

Units are metres. The car faces -Y, its origin is the floor centre (tyres on z = 0).
Run inside Blender (see blender/run.py) or headless with blender/tools/build_asset.py;
re-running rebuilds it. Two cars: build(name="CarEV_B", paint="pearl") gives a second
one with its own paint material and object names.

How the body is made
- One shell, built for x >= 0 and mirrored. Its stations run round the plan outline
  (nose centre -> front corner -> flank -> rear corner -> tail centre), so the nose and
  tail are part of the same smooth surface as the flanks.
- Each station's section: an arch-liner / underbody flange, a lipped bottom edge (the
  sill, or the wheel-arch curve: the arch is simply where the station's bottom edge
  rises), the flank (undercut below the widest line, tumblehome above), a shoulder
  blend and the top. The top (hood, belt ledge, deck) is one height field H(x, y); in
  the cabin it drops to the floor so the interior is open under the glass.
- The greenhouse is a separate glass canopy lofted along y on the belt ledge: side
  glass with tumblehome, a fillet (black rail / A-pillar), a crowned roof. One mesh, with
  clear glass, dark roof glass and gloss-black pillar faces.
- Shut lines, lamps, intakes, sill trim, handles are thin "decal" strips generated on
  the same analytic surface, a millimetre or two proud of it.
"""
import bisect
import importlib
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)
importlib.reload(materials)
sys.path.insert(0, HERE)
import car_ev_interior as cabin  # noqa: E402

importlib.reload(cabin)

NAME = "CarEV"

# linear RGB paint presets (paint= also takes any (r, g, b) tuple or "r,g,b")
PAINTS = {
    "silver": (0.42, 0.43, 0.44),
    "pearl": (0.74, 0.73, 0.70),
    "ink": (0.010, 0.017, 0.040),
    "graphite": (0.030, 0.032, 0.035),
    "bronze": (0.20, 0.105, 0.045),
    "sage": (0.10, 0.13, 0.105),
    "red": (0.32, 0.018, 0.015),
}

P = dict(
    name=NAME,
    paint="silver",
    analytic_normals=True,  # body vertex normals from the analytic surface (smooth reflections)
    paint_metallic=0.55,
    paint_roughness=0.30,
    # ---- package
    length=4.90,
    cap_y=2.09,             # nose plan cap starts here (|y|)
    tail_cap_y=2.0,         # tail plan cap starts here
    half_width=0.958,       # flank half width between the arches
    front_flare=0.022,      # extra half width over the front wheels
    rear_flare=0.034,       # rear haunches
    tail_taper=0.035,       # boat-tail taper in plan behind the rear wheels
    nose_plan_m=3.0,        # superellipse exponent of the nose in plan (higher = squarer)
    tail_plan_m=2.7,
    front_axle=-1.55,
    rear_axle=1.50,
    track=0.822,            # wheel centre |x|
    wheel_z=0.352,          # wheel centre height (tyre radius 0.36, 8 mm squash)
    arch_r=0.455,
    arch_zc=0.30,           # arch circle centre height (below the axle: tighter top gap)
    arch_drop=4.0,          # slope of the short vertical part of the arch down to the sill
    sill_z=0.20,
    floor_z=0.30,
    # ---- flank section
    side_zw=0.53,           # height of the widest line
    haunch_zw=0.07,         # widest line rises over the rear wheels
    side_under=0.05,        # sill tuck-under
    side_tumble=0.072,      # flank leans in by this much at the shoulder
    side_rc=0.04,           # shoulder blend size
    scoop=0.014,            # concave sweep along the lower doors (catches a highlight)
    scoop_z=0.40,
    scoop_w=0.075,
    nose=dict(zb=0.165, zw=0.30, under=0.05, zref=0.15, tumble=0.17, ptop=1.35, rc=0.08, liner=0.30),
    tail=dict(zb=0.25, zw=0.70, under=0.17, zref=0.25, tumble=0.075, ptop=1.6, rc=0.032, liner=0.30),
    # ---- top surface: centre-line and shoulder heights along y
    hood_centre=[(-2.6, 0.58), (-2.33, 0.638), (-2.0, 0.705), (-1.5, 0.785), (-1.1, 0.835),
                 (-0.95, 0.850), (-0.5, 0.875), (0.5, 0.885), (1.3, 0.915), (1.9, 0.935),
                 (2.2, 0.950), (2.45, 0.975), (2.6, 0.98)],
    shoulder=[(-2.6, 0.60), (-2.33, 0.652), (-2.0, 0.745), (-1.5, 0.835), (-1.1, 0.855),
              (-0.95, 0.860), (-0.5, 0.870), (0.5, 0.885), (1.0, 0.905), (1.5, 0.94),
              (1.9, 0.950), (2.2, 0.955), (2.45, 0.975), (2.6, 0.98)],
    # ---- greenhouse
    cowl_y=-0.80,           # windscreen base
    glass_end_y=1.98,       # rear glass meets the deck
    roof=[(-0.55, 1.03), (-0.30, 1.16), (-0.05, 1.28), (0.25, 1.365), (0.55, 1.40),
          (0.90, 1.385), (1.20, 1.34), (1.55, 1.24), (1.80, 1.12)],
    roof_crown=0.06,
    glass_tumble=0.50,      # dx/dz of the side glass
    glass_corner_r=0.12,
    roof_glass=(-0.04, 1.08),   # dark roof panel between these y
    dlo=(-0.68, 1.70),          # side glass between these y (pillars outside)
    b_pillar_y=0.30,
    # ---- cabin
    firewall_y=-0.72,
    bulkhead_y=1.45,
    door_lines=(-1.00, 0.30),   # front door front edge, door split
)

# section column layout (see Body.section)
WALL_F = (0.0, 0.1, 0.24, 0.42, 0.6, 0.78, 1.0)
CORNER_T = (0.25, 0.5, 0.75)
TOP_D = (0.0, 0.012, 0.05, 0.055)
TOP_G = (0.16, 0.36, 0.58, 0.8, 1.0)

# wheel profiles (axial a, radius r); outer face at +a
TYRE = [(-0.100, 0.262), (-0.113, 0.352),                       # inner sidewall: only seen from under the car
        (-0.050, 0.360), (-0.042, 0.351), (-0.034, 0.360),       # tread with two circumferential grooves
        (0.034, 0.360), (0.042, 0.351), (0.050, 0.360),
        (0.104, 0.356), (0.118, 0.348), (0.129, 0.330), (0.1325, 0.309), (0.130, 0.293),
        (0.1325, 0.286), (0.122, 0.272), (0.102, 0.262)]        # outer sidewall, rim protector rib, bead
TYRE_GROOVE_RINGS = (2, 3, 4, 5, 6, 7)
TYRE_SEGS = 40
TYRE_REPEAT = 10            # tread texture tiles round the circumference (one tile ~ 0.2 m)
RIM = [(0.098, 0.266), (0.114, 0.270), (0.121, 0.264), (0.119, 0.256), (0.108, 0.249),
       (0.092, 0.246), (-0.110, 0.246)]
HUB = [(0.060, 0.092), (0.090, 0.092), (0.098, 0.083), (0.101, 0.055), (0.104, 0.050), (0.106, 0.0)]
DISC = [(-0.004, 0.188), (0.007, 0.188), (0.015, 0.188), (0.026, 0.188), (0.026, 0.118), (0.050, 0.100)]
# outer band: plate, vent gap (dark), plate; then the face and the hat (hidden behind the hub)


# ------------------------------------------------------------------- textures

TYRE_TEX_VERSION = 1


def _tyre_normal(n=1024, force=False):
    """Tyre normal map: u runs round the tyre (one tile = 1/TYRE_REPEAT of it), v across
    the TYRE profile (arc-length fraction): directional tread blocks and sipes on the tread,
    fine ribs on the rim protector, a lightly stippled sidewall."""
    import numpy as np
    path = os.path.join(textures.TEX_DIR, "T_CarEV_Tyre_Normal.png")
    stamp = os.path.join(textures.TEX_DIR, "..", "..", "build", "texture_stamps", f"T_CarEV_Tyre_Normal.v{TYRE_TEX_VERSION}")
    os.makedirs(os.path.dirname(stamp), exist_ok=True)
    if os.path.exists(path) and os.path.exists(stamp) and not force:
        return path
    vs = _profile_v(TYRE)
    u = (np.arange(n) + 0.5)[None, :] / n * np.ones((n, 1))
    v = 1.0 - (np.arange(n) + 0.5)[:, None] / n * np.ones((1, n))   # image row 0 = top = v 1
    a = np.interp(v, vs, [q[0] for q in TYRE])           # axial position (m) at each row
    r = np.interp(v, vs, [q[1] for q in TYRE])
    on_tread = (r > 0.3505) & (np.abs(a) < 0.112)
    h = np.zeros((n, n))
    circ = 2 * math.pi * 0.36 / TYRE_REPEAT              # metres of tread per tile
    x = u * circ                                         # metres round the tyre
    # shoulder blocks: lateral grooves every 1/6 tile, slanted (directional), on |a| > 0.05
    pitch = circ / 6
    slant = 0.35 * np.sign(a) * (np.abs(a) - 0.05)
    ph = np.mod(x + slant * 1.0, pitch) / pitch
    groove = np.exp(-((ph - 0.5) / 0.06) ** 2)
    outer = (np.abs(a) > 0.052) & on_tread
    h -= groove * outer
    # centre rib: thin sipes every 1/12 tile
    ph2 = np.mod(x + 0.25 * a, pitch / 2) / (pitch / 2)
    sipe = np.exp(-((ph2 - 0.5) / 0.035) ** 2)
    centre = (np.abs(a) < 0.032) & on_tread
    h -= 0.6 * sipe * centre
    # middle ribs (between grooves and shoulders): short notches from the groove edges
    mid = (np.abs(a) > 0.050) & (np.abs(a) < 0.07) & on_tread
    h -= 0.5 * sipe * mid
    # outer sidewall: fine radial ribs on the protector band, faint stipple elsewhere
    side = (a > 0.115) & (r < 0.35)
    band = (r > 0.280) & (r < 0.296) & side
    h += 0.25 * band * (0.5 + 0.5 * np.cos(2 * math.pi * x / 0.004))
    rng = np.random.default_rng(13)
    h += 0.04 * side * textures._noise(n, 1.0, 1.0, 0.6, rng)
    strength = 3.0
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    nrm = np.stack([-dx, dy, np.ones_like(h)], axis=-1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    out = textures._save("T_CarEV_Tyre_Normal", nrm * 0.5 + 0.5, non_color=True)
    open(stamp, "w").close()
    return out


# ---------------------------------------------------------------------- maths

def _smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def _smax(a, b, k):
    """Smooth max with a blend of width k (exactly max outside the blend)."""
    h = min(max(0.5 + 0.5 * (b - a) / k, 0.0), 1.0)
    return a + (b - a) * h + k * h * (1 - h)


def _pchip(pts):
    """Monotone cubic through (x, y) points (no overshoot); clamped outside."""
    xs = [float(a) for a, _ in pts]
    ys = [float(b) for _, b in pts]
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = min(bisect.bisect_right(xs, x) - 1, n - 2)
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def _paint_rgb(paint):
    if isinstance(paint, str):
        if paint in PAINTS:
            return PAINTS[paint]
        return tuple(float(c) for c in paint.split(","))
    return tuple(paint)


# ----------------------------------------------------------------------- body

class Frame:
    """Everything about one body station that doesn't depend on the column layout."""


class Body:
    def __init__(self, p):
        self.p = p
        self.Zc = _pchip(p["hood_centre"])
        self.Ze = _pchip(p["shoulder"])
        self._outline()
        y0, y1 = p["cowl_y"], p["glass_end_y"]
        self.Rf = _pchip([(y0, self.H(0.0, y0))] + list(p["roof"]) + [(y1, self.H(0.0, y1))])
        self._frames = {}

    # ---- plan
    def hw(self, y):
        p = self.p
        return (p["half_width"] + p["front_flare"] * math.exp(-((y - p["front_axle"]) / 0.45) ** 2)
                + p["rear_flare"] * math.exp(-((y - p["rear_axle"]) / 0.55) ** 2)
                - p["tail_taper"] * _smoothstep(1.65, 2.45, y))

    def _outline(self):
        p = self.p
        capf, capr, tip = p["cap_y"], p["tail_cap_y"], p["length"] / 2
        pts = []
        N, M = 500, 900
        W, m, L = self.hw(-capf), p["nose_plan_m"], tip - capf
        for k in range(N):
            th = math.pi / 2 * (1 - k / N)
            c, s = max(math.cos(th), 0.0), math.sin(th)
            pts.append((0.0 if k == 0 else W * c ** (2 / m), -capf - L * s ** (2 / m)))
        for k in range(M + 1):
            y = -capf + (capf + capr) * k / M
            pts.append((self.hw(y), y))
        W, m, L = self.hw(capr), p["tail_plan_m"], tip - capr
        for k in range(1, N + 1):
            th = math.pi / 2 * k / N
            c, s = max(math.cos(th), 0.0), math.sin(th)
            pts.append((0.0 if k == N else W * c ** (2 / m), capr + L * s ** (2 / m)))
        S = [0.0]
        for i in range(1, len(pts)):
            S.append(S[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
        nrm = []
        for i in range(len(pts)):
            a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(tx, ty)
            nrm.append((ty / ln, -tx / ln))
        nrm[0] = (0.0, -1.0)
        nrm[-1] = (0.0, 1.0)
        self.pts, self.S, self.nrm = pts, S, nrm
        self.Ys = [q[1] for q in pts]
        self.s_side0, self.s_side1, self.s_end = S[N], S[N + M], S[-1]

    def outline(self, s):
        S = self.S
        s = min(max(s, 0.0), S[-1])
        i = min(max(bisect.bisect_right(S, s) - 1, 0), len(S) - 2)
        t = (s - S[i]) / max(S[i + 1] - S[i], 1e-12)
        a, b = self.pts[i], self.pts[i + 1]
        na, nb = self.nrm[i], self.nrm[i + 1]
        x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        nx, ny = na[0] + (nb[0] - na[0]) * t, na[1] + (nb[1] - na[1]) * t
        ln = math.hypot(nx, ny)
        nx, ny = nx / ln, ny / ln
        if s <= 1e-9 or s >= S[-1] - 1e-9:
            x, nx = 0.0, 0.0
            ny = -1.0 if s <= 1e-9 else 1.0
        return x, y, nx, ny

    def s_of_y(self, y):
        """Arc length of the outline point at y (side stations)."""
        Ys = self.Ys
        i = min(max(bisect.bisect_right(Ys, y) - 1, 0), len(Ys) - 2)
        t = (y - Ys[i]) / max(Ys[i + 1] - Ys[i], 1e-12)
        return self.S[i] + (self.S[i + 1] - self.S[i]) * t

    def s_of_x(self, x, front=True):
        """Arc length on the nose (front) or tail cap where the outline is at x."""
        lo, hi = (0.0, self.s_side0) if front else (self.s_side1, self.s_end)
        for _ in range(50):
            mid = (lo + hi) / 2
            xm = self.outline(mid)[0]
            if (xm < x) == front:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    # ---- heights
    def H(self, x, y):
        zc, ze = self.Zc(y), self.Ze(y)
        return zc + (ze - zc) * _smoothstep(0.0, 0.86, abs(x))

    def H_normal(self, x, y):
        e = 0.003
        gx = (self.H(x + e, y) - self.H(x - e, y)) / (2 * e)
        gy = (self.H(x, y + e) - self.H(x, y - e)) / (2 * e)
        return Vector((-gx, -gy, 1.0)).normalized()

    def zb_side(self, y):
        p = self.p
        z = p["sill_z"]
        R, zc = p["arch_r"], p["arch_zc"]
        for a in (p["front_axle"], p["rear_axle"]):
            dy = abs(y - a)
            za = zc + math.sqrt(R * R - dy * dy) if dy <= R else zc - (dy - R) * p["arch_drop"]
            z = _smax(z, za, 0.03)
        return z

    def params(self, y, ny):
        p = self.p
        yc = min(max(y, -p["cap_y"]), p["tail_cap_y"])
        side = dict(zb=self.zb_side(yc),
                    zw=p["side_zw"] + p["haunch_zw"] * math.exp(-((yc - p["rear_axle"]) / 0.6) ** 2),
                    under=p["side_under"], zref=p["sill_z"] - 0.02, tumble=p["side_tumble"],
                    ptop=1.7, rc=p["side_rc"], liner=0.36,
                    scoop=p["scoop"] * _smoothstep(p["front_axle"] + 0.50, p["front_axle"] + 0.85, yc)
                    * (1 - _smoothstep(p["rear_axle"] - 0.75, p["rear_axle"] - 0.42, yc)))
        wf, wr = max(0.0, -ny) ** 2, max(0.0, ny) ** 2
        ws = 1.0 - wf - wr
        nose, tail = dict(p["nose"], scoop=0.0), dict(p["tail"], scoop=0.0)
        return {k: ws * side[k] + wf * nose[k] + wr * tail[k] for k in side}

    # ---- one station
    def frame(self, s):
        F = self._frames.get(s)
        if F is not None:
            return F
        p = self.p
        F = Frame()
        x0, y0, nx, ny = self.outline(s)
        q = self.params(y0, ny)
        T, rc = q["tumble"], q["rc"]

        def at(d):
            return x0 - nx * d, y0 - ny * d
        zc = self.H(*at(T))
        zA = zc - rc
        zw = min(q["zw"], zA - 0.06)
        zref = min(q["zref"], zw - 0.05)
        under, ptop = q["under"], q["ptop"]

        sc, zs, wsc = q["scoop"], p["scoop_z"], p["scoop_w"]

        def inset(z):
            d = sc * math.exp(-((z - zs) / wsc) ** 2) if sc > 1e-6 else 0.0
            if z < zw:
                return d + under * ((zw - z) / (zw - zref)) ** 2
            return d + T * ((z - zw) / (zc - zw)) ** ptop

        def dinset(z):
            if z < zw:
                return -2 * under * (zw - z) / (zw - zref) ** 2
            return T * ptop * ((z - zw) / (zc - zw)) ** (ptop - 1) / (zc - zw)

        def dP_dz(z):
            e = 0.002
            dd = (inset(z + e) - inset(z - e)) / (2 * e)
            return Vector((-nx * dd, -ny * dd, 1.0))

        def dcorner(t):
            dd = 2 * (1 - t) * (dC - dA) + 2 * t * (dB - dC)
            dz = 2 * (1 - t) * (zC - zA) + 2 * t * (zB - zC)
            return Vector((-nx * dd, -ny * dd, dz))

        dA, sA = inset(zA), dinset(zA)
        dB = T + rc
        zB = self.H(*at(dB))
        e = 0.004
        sB = (self.H(*at(dB + e)) - zB) / e
        den = 1 - sA * sB
        dC = (dA + sA * (zB - sB * dB - zA)) / den
        zC = zB + sB * (dC - dB)
        dC = min(max(dC, dA), dB)
        zC = max(zC, zA)

        def P(d, z):
            return Vector((x0 - nx * d, y0 - ny * d, z))

        def corner(t):
            d = (1 - t) ** 2 * dA + 2 * (1 - t) * t * dC + t * t * dB
            z = (1 - t) ** 2 * zA + 2 * (1 - t) * t * zC + t * t * zB
            return P(d, z)

        bx, by = at(dB)
        sx, sy = 0.0, min(max(y0, -p["cap_y"]), p["tail_cap_y"])
        Lt = math.hypot(sx - bx, sy - by)

        def top(d):
            t = min(d / Lt, 1.0)
            px, py = bx + (sx - bx) * t, by + (sy - by) * t
            return Vector((px, py, self.H(px, py)))

        side = self.s_side0 - 1e-6 <= s <= self.s_side1 + 1e-6
        F.__dict__.update(
            s=s, x0=x0, y0=y0, nx=nx, ny=ny, q=q, zc=zc, zA=zA, zB=zB, zb=q["zb"], dB=dB,
            inset=inset, P=P, corner=corner, top=top, dP_dz=dP_dz, dcorner=dcorner, Lt=Lt, spine=(sx, sy), base=(bx, by),
            side=side,
            cabin=side and p["firewall_y"] <= y0 <= p["bulkhead_y"],
            gh=side and p["cowl_y"] - 1e-6 <= y0 <= p["glass_end_y"] + 1e-6)
        self._frames[s] = F
        return F

    def wall(self, s, z):
        F = self.frame(s)
        z = min(z, F.zA)
        return F.P(F.inset(z), z)

    def wall_normal(self, s, z):
        e = 0.004
        a = self.wall(s + e, z) - self.wall(s - e, z)
        b = self.wall(s, z + e) - self.wall(s, z - e)
        n = a.cross(b)
        return n.normalized() if n.length > 1e-12 else Vector((self.frame(s).nx, self.frame(s).ny, 0))

    def wall_z(self, F, z0, f):
        """Height of flank row f (WALL_F). Rows stay at the same heights from station to
        station (fixed spacing above the sill), and only the rows below a rising arch edge
        bunch up just above it: rows that jump in height between neighbouring stations
        made the reflections step in front of the wheel arches."""
        p = self.p
        if not F.side:
            return z0 + f * (F.zA - z0)
        zs = min(p["sill_z"] + 0.012, z0)
        H = F.zA - z0

        def S(t):
            return _smax(zs + t * (F.zA - zs) - z0, 0.35 * t * H, 0.03)
        return min(z0 + S(f) - S(0.0) * (1 - f), F.zA)

    def section(self, s):
        F = self.frame(s)
        p = self.p
        zb = F.zb
        db = F.inset(zb)
        cols = [F.P(F.q["liner"], zb), F.P(db + 0.03, zb), F.P(db + 0.008, zb + 0.003)]
        tans = [None, None, None]        # column-direction tangent (None: from neighbours)
        nrms = [None] * 3                # exact normal where known (top surface)
        z0 = zb + 0.012
        for f in WALL_F:
            z = self.wall_z(F, z0, f)
            cols.append(F.P(F.inset(z), z))
            tans.append(F.dP_dz(z))
            nrms.append(None)
        for t in CORNER_T:
            cols.append(F.corner(t))
            tans.append(F.dcorner(t))
            nrms.append(None)
        jB = len(cols)
        ds = list(TOP_D) + [TOP_D[-1] + (F.Lt - TOP_D[-1]) * g for g in TOP_G]
        for d in ds:
            v = F.top(d)
            nn = self.H_normal(v.x, v.y)
            if F.cabin and d >= TOP_D[-1] - 1e-9:
                v.z = p["floor_z"]
                nn = Vector((0.0, 0.0, 1.0))
            cols.append(v)
            tans.append(None)
            nrms.append(nn)
        cols[-1].x = 0.0
        self._last = (tans, nrms)
        return cols, jB

    def section_normals(self, s, cols):
        """Vertex normals of one station from the analytic surface (smooth reflections):
        flank at constant height, shoulder blend at constant parameter, top from H."""
        _, nrms = self._last
        F = self.frame(s)
        e = 0.002
        Fa, Fb = self.frame(min(s + e, self.s_end)), self.frame(max(s - e, 0.0))

        def edge(G):
            return G.P(G.inset(G.zb), G.zb)
        t2 = edge(Fa) - edge(Fb)
        t1 = Vector((-F.nx, -F.ny, 0.0))
        nf = t1.cross(t2)
        nf = nf.normalized() if nf.length > 1e-12 else Vector((0, 0, -1))
        z0 = F.zb + 0.012
        out = [nf, nf, (nf + self.wall_normal(s, z0)).normalized()]
        for f in WALL_F:
            out.append(self.wall_normal(s, self.wall_z(F, z0, f)))
        for t in CORNER_T:
            nn = (Fa.corner(t) - Fb.corner(t)).cross(F.dcorner(t))
            out.append(nn.normalized())
        out += nrms[len(out):]
        for c, nn in zip(cols, out):
            if abs(c.x) < 1e-6:
                nn.x = 0.0
                nn.normalize()
        return out

    # ---- station lists
    def stations(self):
        p = self.p
        capf, capr, R = p["cap_y"], p["tail_cap_y"], p["arch_r"]
        ys = []
        for a in (p["front_axle"], p["rear_axle"]):
            n = 16
            for k in range(n + 1):
                ys.append(a - R * math.cos(math.pi * k / n))
            for dd in (0.012, 0.025, 0.05):
                ys += [a - R - dd, a + R + dd]
        y0, y1 = p["front_axle"] + R + 0.05, p["rear_axle"] - R - 0.05
        n = 12
        ys += [y0 + (y1 - y0) * k / n for k in range(1, n)]
        fw, bh = p["firewall_y"], p["bulkhead_y"]
        special = [p["cowl_y"], fw - 0.004, fw + 0.004, bh - 0.004, bh + 0.004, p["glass_end_y"],
                   -capf, capr, (-capf + p["front_axle"] - R - 0.05) / 2, (capr + p["rear_axle"] + R + 0.05) / 2]
        ys = sorted(set(round(y, 5) for y in ys if -capf < y < capr))
        out = []
        for y in ys:   # drop stations crowding a special one
            if all(abs(y - sp) > 0.012 for sp in special):
                out.append(y)
        ys = sorted(out + special)
        st = self._cap_stations(0.0, self.s_side0, 17)[:-1]
        st += [self.s_of_y(y) for y in ys]
        st += self._cap_stations(self.s_side1, self.s_end, 12)[1:]
        st[0], st[-1] = 0.0, self.s_end
        return st

    def _cap_stations(self, s0, s1, n, bend=0.35):
        """n+1 stations from s0 to s1, evenly spaced in arc length plus `bend` metres per
        radian of turning, so the tight plan corners get more stations."""
        k = 400
        ss = [s0 + (s1 - s0) * i / k for i in range(k + 1)]
        ang = [math.atan2(self.outline(q)[3], self.outline(q)[2]) for q in ss]
        meas = [0.0]
        for i in range(1, k + 1):
            meas.append(meas[-1] + (ss[i] - ss[i - 1]) + bend * abs(ang[i] - ang[i - 1]))
        out = []
        for j in range(n + 1):
            target = meas[-1] * j / n
            i = min(max(bisect.bisect_left(meas, target), 1), k)
            t = (target - meas[i - 1]) / max(meas[i] - meas[i - 1], 1e-12)
            out.append(ss[i - 1] + (ss[i] - ss[i - 1]) * t)
        return out


# ------------------------------------------------------------------- mesh bits

def _new_mesh(name, bm, mats, col, parent, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = smooth
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    return common.link(ob, col, parent)


def _face(bm, verts, mat=0, flip=False):
    uniq = []
    for v in verts:
        if v not in uniq:
            uniq.append(v)
    if len(uniq) < 3:
        return None
    if flip:
        uniq.reverse()
    try:
        f = bm.faces.new(uniq)
    except ValueError:
        return None
    f.material_index = mat
    f.smooth = True
    return f


def _grid(bm, rows, mat=0, mirror=False, mat_fn=None):
    """Quad grid from rows (list of lists of Vector). Face normal = d(row) x d(col).
    mirror=True also adds the x-mirrored copy (winding reversed)."""
    for sign in ((1, -1) if mirror else (1,)):
        vs = [[bm.verts.new((sign * c.x, c.y, c.z)) for c in row] for row in rows]
        for i in range(len(vs) - 1):
            for j in range(len(vs[i]) - 1):
                m = mat_fn(i, j) if mat_fn else mat
                _face(bm, [vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]], m, flip=sign < 0)


def _ribbon(bm, pts, nrms, width, off, mat=0, mirror=False):
    """Flat strip of `width` along a polyline lying on a surface (normals nrms), `off` proud."""
    left, right = [], []
    for i, (p, n) in enumerate(zip(pts, nrms)):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        t = (b - a).normalized()
        side = n.cross(t).normalized()
        c = p + n * off
        left.append(c + side * width / 2)
        right.append(c - side * width / 2)
    rows = [[right[i], left[i]] for i in range(len(pts))]
    # face normal = d(row) x d(col) = t x side = n  (side = n x t)
    _grid(bm, rows, mat, mirror)


# ---------------------------------------------------------------------- build

def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    body = Body(p)

    # ---- materials
    paint = common.pbr_material(f"M_{n}_Paint", _paint_rgb(p["paint"]), roughness=p["paint_roughness"],
                                metallic=p["paint_metallic"], coat=1.0)
    bsdf = next(nd for nd in paint.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    if "Coat Roughness" in bsdf.inputs:
        bsdf.inputs["Coat Roughness"].default_value = 0.03
    satin = common.pbr_material("M_CarEV_Satin", (0.018, 0.018, 0.019), roughness=0.75)
    gloss = common.pbr_material("M_CarEV_GlossBlack", (0.008, 0.008, 0.009), roughness=0.12, coat=1.0)
    shut = common.pbr_material("M_CarEV_Shut", (0.003, 0.003, 0.003), roughness=0.9)
    interior = materials.fabric("M_CarEV_Interior", (0.026, 0.026, 0.028), roughness=0.85)
    leather = common.pbr_material("M_Leather_Cognac", (0.23, 0.075, 0.025), roughness=0.62)
    common.set_normal_map(leather, textures.load(textures.leather_normal(), non_color=True), 0.6)
    walnut = materials.walnut()
    steel = materials.steel()
    glass = materials.glass("M_Glass_CarEV", tint=(0.20, 0.22, 0.23), alpha=0.42, roughness=0.02)
    roof_glass = materials.glass("M_Glass_CarEV_Roof", tint=(0.025, 0.028, 0.03), alpha=0.78, roughness=0.02)
    rubber = common.pbr_material("M_CarEV_Rubber", (0.016, 0.016, 0.017), roughness=0.86)
    common.set_normal_map(rubber, textures.load(_tyre_normal(), non_color=True), 1.0)
    graphite = common.pbr_material("M_CarEV_WheelGraphite", (0.05, 0.052, 0.056), roughness=0.32, metallic=0.85)
    machined = common.pbr_material("M_CarEV_WheelMachined", (0.62, 0.63, 0.64), roughness=0.2, metallic=1.0)
    disc_m = common.pbr_material("M_CarEV_Disc", (0.30, 0.30, 0.31), roughness=0.5, metallic=1.0)
    caliper_m = materials.bronze()
    lens = common.pbr_material("M_CarEV_Lens", (0.006, 0.006, 0.008), roughness=0.05, coat=1.0)
    lamp_w = materials.emissive("M_CarEV_LampWhite", (1.0, 0.97, 0.92), 6.0)
    lamp_r = materials.emissive("M_CarEV_LampRed", (1.0, 0.03, 0.02), 5.0)
    screen = cabin.screen_material("M_CarEV_Screen")
    stitch = common.pbr_material("M_CarEV_Stitch", (0.40, 0.32, 0.22), roughness=0.7)

    # ---- body shell
    st = body.stations()
    bm = bmesh.new()
    cache = {}

    def V(co):
        key = (round(co.x, 6), round(co.y, 6), round(co.z, 6))
        v = cache.get(key)
        if v is None:
            v = cache[key] = bm.verts.new(co)
        return v
    sections, frames, normals = [], [], []
    jB = 0
    for s in st:
        cols, jB = body.section(s)
        normals.append(body.section_normals(s, cols))
        sections.append(cols)
        frames.append(body.frame(s))
    vnorm = {}
    PAINT, LINER, TRIM, INTER = 0, 1, 2, 3
    for sign in (1, -1):   # both halves share the centre-line vertices through the cache
        grid = [[V(Vector((sign * c.x, c.y, c.z))) for c in cols] for cols in sections]
        for row, nrow in zip(grid, normals):
            for v, nn in zip(row, nrow):
                vnorm[v] = Vector((sign * nn.x, nn.y, nn.z))
        for i in range(len(st) - 1):
            fa, fb = frames[i], frames[i + 1]
            gh = fa.gh and fb.gh
            cab = fa.cabin or fb.cabin
            for j in range(len(grid[i]) - 1):
                if j == 0:
                    m = LINER
                elif j < jB or not (gh or cab):
                    m = PAINT
                elif j < jB + 2:
                    m = TRIM
                else:
                    m = INTER if cab else TRIM
                _face(bm, [grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]], m, flip=sign < 0)
    bm.verts.index_update()
    order = [vnorm.get(v, Vector((0, 0, 1))) for v in bm.verts]
    shell = _new_mesh(f"{n}_Body", bm, [paint, satin, gloss, interior], col, root)
    if p["analytic_normals"]:
        shell.data.normals_split_custom_set_from_vertices([tuple(v) for v in order])
    common.box_uv(shell, tile=0.25)

    # ---- greenhouse
    _greenhouse(p, body, col, root, n, [glass, roof_glass, gloss, steel])

    # ---- underbody + wheel houses
    _underbody(p, body, col, root, n, satin)

    # ---- trim decals (shut lines, sill, intakes, handles, lamps)
    _trim(p, body, col, root, n, [shut, satin, gloss, steel, lens, lamp_w, lamp_r])

    # ---- mirrors (camera pods)
    _mirrors(p, body, col, root, n, paint, gloss)

    # ---- wheels
    _wheels(p, col, root, n, [rubber, graphite, machined, disc_m, caliper_m, shut])

    # ---- interior
    before = set(col.objects)
    cabin.build(p, body, col, root, n, dict(lea=leather, dark=interior, satin=satin, wood=walnut, gloss=gloss,
                                            steel=steel, stitch=stitch, screen=screen, shell=gloss,
                                            screen_dark=lens))
    _merge(f"{n}_Interior", [o for o in col.objects if o not in before], col, root)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    _checks(p, body)
    return root, parts


# ------------------------------------------------------------------ greenhouse

def _glass_section(p, body, y):
    """Half section of the canopy at y: 11 points from the base (+x) to the centre line."""
    s = body.s_of_y(y)
    F = body.frame(s)
    b = F.top(0.012).x
    htot = max(body.Rf(y) - body.H(0.0, y), 0.0)
    cr = min(p["roof_crown"], 0.45 * htot)
    hs = htot - cr
    ta = p["glass_tumble"]
    xk = b - hs * ta
    r = min(p["glass_corner_r"], 0.45 * hs, 0.3 * xk)
    dl = Vector((-ta, 1.0)).normalized()            # side glass direction (x, h)
    K = Vector((xk, hs))
    T1 = K - dl * r
    x2 = xk - r * 0.9

    def roof_h(x):
        return htot - cr * (x / xk) ** 2 if xk > 1e-6 else htot
    T2 = Vector((x2, roof_h(x2)))
    pts2 = []
    S0 = Vector((b, 0.0))
    for f in (0.0, 0.4, 0.75):
        pts2.append(S0.lerp(T1, f))
    for t in (0.0, 0.33, 0.67, 1.0):
        pts2.append((1 - t) ** 2 * T1 + 2 * (1 - t) * t * K + t * t * T2)
    for f in (0.3, 0.6, 0.85, 1.0):
        x = x2 * (1 - f)
        pts2.append(Vector((x, roof_h(x))))
    out = [Vector((q.x, y, body.H(q.x, y) + q.y)) for q in pts2]
    out[-1].x = 0.0
    return out


def _glass_ys(p):
    y0, y1 = p["cowl_y"], p["glass_end_y"]
    N = 30
    ys = [y0 + (y1 - y0) * (0.5 - 0.5 * math.cos(math.pi * k / N)) for k in range(N + 1)]
    special = [p["roof_glass"][0], p["roof_glass"][1], p["dlo"][0], p["dlo"][1],
               p["b_pillar_y"] - 0.035, p["b_pillar_y"] + 0.035]
    ys = [y for y in ys if all(abs(y - sp) > 0.02 for sp in special) or y in (y0, y1)]
    return sorted(ys + special)


def _greenhouse(p, body, col, root, n, mats):
    CLEAR, ROOF, BLACK, STEEL = 0, 1, 2, 3
    ys = _glass_ys(p)
    rows = [_glass_section(p, body, y) for y in ys]
    r0, r1 = p["roof_glass"]
    d0, d1 = p["dlo"]
    bp = p["b_pillar_y"]

    def mat_fn(i, k):
        ym = (ys[i] + ys[i + 1]) / 2
        if i == 0 or i == len(ys) - 2:
            return BLACK                       # frit at the base of windscreen / rear glass
        if k == 4:
            return BLACK                       # roof rail / A-pillar band
        if k >= 5:
            return ROOF if r0 <= ym <= r1 else CLEAR
        if not (d0 <= ym <= d1):
            return BLACK
        if bp - 0.036 <= ym <= bp + 0.036:
            return BLACK                       # B-pillar
        return CLEAR
    bm = bmesh.new()
    _grid(bm, rows, mirror=True, mat_fn=mat_fn)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    _new_mesh(f"{n}_Glass", bm, mats[:3], col, root)

    # polished strip along the bottom of the side glass
    bm = bmesh.new()
    strip = []
    for y in ys:
        if d0 <= y <= d1:
            sec = _glass_section(p, body, y)
            a, b = sec[0], sec[1]
            up = (b - a).normalized()
            nrm = Vector((up.z, 0.0, -up.x)).normalized()
            if nrm.x < 0:
                nrm = -nrm
            strip.append([a + nrm * 0.0015, a + up * 0.016 + nrm * 0.0015])
    _grid(bm, strip, mirror=True)
    _new_mesh(f"{n}_BeltTrim", bm, [mats[STEEL]], col, root)


# ------------------------------------------------------------------- underbody

def _underbody(p, body, col, root, n, satin):
    bm = bmesh.new()
    hx, y0, y1, z = 0.64, -2.12, 2.18, 0.175
    vs = [bm.verts.new(c) for c in ((-hx, y0, z), (hx, y0, z), (hx, y1, z), (-hx, y1, z))]
    _face(bm, vs, flip=True)
    R, zc = p["arch_r"], p["arch_zc"]
    for a in (p["front_axle"], p["rear_axle"]):
        for sx in (-1, 1):
            x = sx * 0.605
            pts = [(x, a + R + 0.03, z)]
            for k in range(17):
                th = math.pi * k / 16
                pts.append((x, a + R * math.cos(th), zc + R * math.sin(th)))
            pts.append((x, a - R - 0.03, z))
            _face(bm, [bm.verts.new(c) for c in pts], flip=sx < 0)
    _new_mesh(f"{n}_Underbody", bm, [satin], col, root, smooth=False)


# ------------------------------------------------------------------------ trim

def _trim(p, body, col, root, n, mats):
    SHUT, SATIN, GLOSS, STEEL, LENS, WHITE, RED = range(7)
    bm = bmesh.new()

    def wall_rows(s_list, zfun, nz, off):
        rows = []
        for s in s_list:
            z0, z1 = zfun(s)
            rows.append([body.wall(s, z0 + (z1 - z0) * k / (nz - 1)) + body.wall_normal(s, z0 + (z1 - z0) * k / (nz - 1)) * off
                         for k in range(nz)])
        return rows

    def lin(a, b, k):
        return [a + (b - a) * i / (k - 1) for i in range(k)]

    def side_line(yz, off=0.0012, width=0.005, mirror=True, mat=SHUT):
        pts, nrms = [], []
        for y, z in yz:
            s = body.s_of_y(y)
            pts.append(body.wall(s, z))
            nrms.append(body.wall_normal(s, z))
        _ribbon(bm, pts, nrms, width, off, mat, mirror)

    def door_line(y, z0):
        s = body.s_of_y(y)
        F = body.frame(s)
        pts, nrms = [], []
        for k in range(9):
            z = z0 + (F.zA - z0) * k / 8
            pts.append(body.wall(s, z))
            nrms.append(body.wall_normal(s, z))
        prev = pts[-1]
        for t in (0.3, 0.6, 1.0):
            c = F.corner(t)
            # normal from neighbouring stations
            a = body.frame(s + 0.004).corner(t) - body.frame(s - 0.004).corner(t)
            nn = a.cross(c - prev).normalized()
            pts.append(c)
            nrms.append(nn)
            prev = c
        nrms[-1] = nrms[-2]
        _ribbon(bm, pts, nrms, 0.005, 0.0012, SHUT, True)

    sill_top = 0.285
    yf, ys_ = p["door_lines"]
    door_line(yf, sill_top)
    door_line(ys_, sill_top)
    # rear door rear edge: down the C-pillar, then round the rear arch
    ra, zc, R = p["rear_axle"], p["arch_zc"], p["arch_r"] + 0.07
    s_top = body.s_of_y(1.04)
    yz = [(1.04, body.frame(s_top).zA), (1.055, 0.75)]
    for k in range(10):
        z = 0.66 - (0.66 - zc) * k / 9
        yz.append((ra - math.sqrt(max(R * R - (z - zc) ** 2, 0.0)), z))
    yz.append((ra - R, sill_top))
    side_line(yz)

    # sill trim between the arches
    def zb_at(y):
        return body.zb_side(y)

    def find(y_lo, y_hi, target):
        for _ in range(40):
            mid = (y_lo + y_hi) / 2
            if (zb_at(mid) > target) == (zb_at(y_lo) > target):
                y_lo = mid
            else:
                y_hi = mid
        return (y_lo + y_hi) / 2
    ya = find(p["front_axle"], p["front_axle"] + 0.6, 0.27)
    yb = find(p["rear_axle"] - 0.6, p["rear_axle"], 0.27)
    s_list = [body.s_of_y(y) for y in lin(ya, yb, 40)]
    rows = wall_rows(s_list, lambda s: (body.frame(s).zb + 0.012, sill_top - 0.002), 3, 0.0015)
    _grid(bm, rows, SATIN, mirror=True)

    # door handles (flush, polished)
    for y0, y1 in ((-0.33, -0.15), (0.66, 0.84)):
        s_list = [body.s_of_y(y) for y in lin(y0, y1, 5)]
        rows = wall_rows(s_list, lambda s: (body.frame(s).zA - 0.085, body.frame(s).zA - 0.066), 2, 0.002)
        _grid(bm, rows, STEEL, mirror=True)

    # charge port flap (left rear quarter, +x side only)
    loop = []
    cy, cz, hy, hz, rr = 1.24, 0.775, 0.06, 0.045, 0.02
    for k in range(25):
        a = 2 * math.pi * k / 24
        c, s_ = math.cos(a), math.sin(a)
        e = 0.25
        y = cy + hy * math.copysign(abs(c) ** e, c)
        z = cz + hz * math.copysign(abs(s_) ** e, s_)
        loop.append((y, z))
    side_line(loop, mirror=False, width=0.004)

    # ---- hood shut lines (on the top surface)
    def top_line(xy, mirror=True):
        pts = [Vector((x, y, body.H(x, y))) for x, y in xy]
        nrms = [body.H_normal(x, y) for x, y in xy]
        _ribbon(bm, pts, nrms, 0.005, 0.0015, SHUT, mirror)
    hx, hy0, hy1, hr = 0.70, -1.02, -2.20, 0.22
    xy = [(0.0, hy0)] + [(hx * k / 6, hy0) for k in range(1, 7)]
    xy += [(hx, hy0 - (hy0 - (hy1 + hr)) * k / 10) for k in range(1, 11)]
    for k in range(1, 9):
        a = math.pi / 2 * k / 8
        xy.append((hx - hr + hr * math.cos(a), hy1 + hr - hr * math.sin(a)))
    xy += [((hx - hr) * (1 - k / 6), hy1) for k in range(1, 7)]
    top_line(xy)

    # trunk lid side lines: deck, over the tail edge, down to the lamp band
    for xl in (0.78,):
        s = body.s_of_x(xl, front=False)
        F = body.frame(s)
        ybt = F.top(0.0).y
        xy = [(xl, 1.955 + (ybt - 0.004 - 1.955) * k / 8) for k in range(9)]
        pts = [Vector((x, y, body.H(x, y))) for x, y in xy]
        nrms = [body.H_normal(x, y) for x, y in xy]
        for t in (0.75, 0.5, 0.25, 0.0):
            c = F.corner(t)
            a = body.frame(s + 0.004).corner(t) - body.frame(s - 0.004).corner(t)
            nn = a.cross(c - pts[-1]).normalized()
            if nn.z < -0.5 or nn.dot(Vector((F.nx, F.ny, 0))) < 0:
                nn = -nn
            pts.append(c)
            nrms.append(nn)
        for k in range(1, 4):
            z = F.zA - 0.018 * k
            pts.append(body.wall(s, z))
            nrms.append(body.wall_normal(s, z))
        _ribbon(bm, pts, nrms, 0.005, 0.0015, SHUT, True)

    # ---- front: light bar under the hood's leading edge, headlamps at the corners
    s_hl0, s_hl1 = body.s_of_x(0.56), body.s_of_x(0.89)
    s_list = lin(0.0, s_hl1, 34)
    rows = wall_rows(s_list, lambda s: (body.frame(s).zA - 0.020, body.frame(s).zA - 0.011), 2, 0.003)
    _grid(bm, rows, WHITE, mirror=True)

    def hl_z(s):
        F = body.frame(s)
        x = F.x0
        h = 0.062 * _smoothstep(0.56, 0.66, x) * (1 - _smoothstep(0.84, 0.89, x))
        return F.zA - 0.006 - h - 0.004, F.zA - 0.006
    rows = wall_rows(lin(s_hl0, s_hl1, 16), hl_z, 4, 0.002)
    _grid(bm, rows, LENS, mirror=True)
    rows = wall_rows(lin(body.s_of_x(0.64), body.s_of_x(0.83), 8),
                     lambda s: (body.frame(s).zA - 0.063, body.frame(s).zA - 0.057), 2, 0.003)
    _grid(bm, rows, WHITE, mirror=True)
    # projector modules inside the lens: polished cups round dark domed lenses
    for xp in (0.675, 0.728, 0.781):
        sp = body.s_of_x(xp)
        zp = body.frame(sp).zA - 0.037
        _projector(bm, body.wall(sp, zp), _out_normal(body, sp, zp), 0.0115, STEEL, LENS)
    # chrome bezel along the bottom edge of the lens
    rows = wall_rows(lin(s_hl0, s_hl1, 16), lambda s: (hl_z(s)[0] - 0.0005, hl_z(s)[0] + 0.0025), 2, 0.0026)
    _grid(bm, rows, STEEL, mirror=True)
    # lower intake and corner air curtains
    s_in = body.s_of_x(0.64)

    def intake_z(s):
        x = body.frame(s).x0
        e = math.sqrt(max(1 - ((x - 0.56) / 0.08) ** 2, 0.0)) if x > 0.56 else 1.0
        zm, h = 0.275, 0.06 * e
        return zm - h, zm + h
    rows = wall_rows(lin(0.0, body.s_of_x(0.56), 12) + lin(body.s_of_x(0.56), s_in, 7)[1:], intake_z, 3, 0.0015)
    _grid(bm, rows, GLOSS, mirror=True)
    # two satin slats across the intake (sensor/radar bar look)
    for zz in (0.252, 0.298):
        rows = wall_rows(lin(0.0, body.s_of_x(0.55), 12), lambda s, zz=zz: (zz - 0.0035, zz + 0.0035), 2, 0.0028)
        _grid(bm, rows, SATIN, mirror=True)

    # ---- rear: full-width lamp band, diffuser
    s_r0 = body.s_of_x(0.93, front=False)
    s_list = lin(s_r0, body.s_end, 30)
    rows = wall_rows(s_list, lambda s: (body.frame(s).zA - 0.085, body.frame(s).zA - 0.022), 3, 0.002)
    _grid(bm, rows, LENS, mirror=True)
    rows = wall_rows(s_list, lambda s: (body.frame(s).zA - 0.058, body.frame(s).zA - 0.046), 2, 0.003)
    _grid(bm, rows, RED, mirror=True)
    # layered light guides at the outer ends of the band (thin lines above and below the
    # main bar, staggered) and a polished line along the band's top
    for x0_, z0_, z1_ in ((0.80, 0.034, 0.031), (0.86, 0.040, 0.037), (0.80, 0.070, 0.067), (0.86, 0.064, 0.061)):
        rows = wall_rows(lin(body.s_of_x(x0_, front=False), body.s_of_x(0.925, front=False), 8),
                         lambda s, z0_=z0_, z1_=z1_: (body.frame(s).zA - z0_, body.frame(s).zA - z1_), 2, 0.0032)
        _grid(bm, rows, RED, mirror=True)
    rows = wall_rows(s_list, lambda s: (body.frame(s).zA - 0.0245, body.frame(s).zA - 0.0215), 2, 0.0026)
    _grid(bm, rows, STEEL, mirror=True)
    s_d0 = body.s_of_x(0.78, front=False)
    rows = wall_rows(lin(s_d0, body.s_end, 16), lambda s: (body.frame(s).zb + 0.012, 0.40), 3, 0.0015)
    _grid(bm, rows, GLOSS, mirror=True)
    # diffuser strakes
    for xf in (0.16, 0.40, 0.62):
        sf = body.s_of_x(xf, front=False)
        F = body.frame(sf)
        zs = [F.zb + 0.014, 0.25, 0.37]
        rows = []
        for z in zs:
            w = body.wall(sf, z)
            nrm = _out_normal(body, sf, z)
            d = 0.035 * (1 - _smoothstep(0.25, 0.37, z))
            t = (body.wall(sf + 0.004, z) - body.wall(sf - 0.004, z)).normalized()
            rows.append([w - t * 0.003, w - t * 0.003 + nrm * (d + 0.002), w + t * 0.003 + nrm * (d + 0.002), w + t * 0.003])
        _grid(bm, rows, GLOSS, mirror=True)

    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    _new_mesh(f"{n}_Trim", bm, mats, col, root)


def _out_normal(body, s, z):
    nrm = body.wall_normal(s, z)
    F = body.frame(s)
    if nrm.dot(Vector((F.nx, F.ny, 0.0))) < 0:
        nrm = -nrm
    return nrm


def _projector(bm, P, N, r, m_cup, m_lens, segs=14):
    """A headlamp projector on the lens surface at P (outward normal N): polished cup
    ring and a dark domed lens (both x-mirrored)."""
    t1 = N.cross(Vector((0, 0, 1)))
    if t1.length < 1e-6:
        t1 = N.cross(Vector((1, 0, 0)))
    t1.normalize()
    t2 = N.cross(t1).normalized()
    prof = [(0.0021, r * 1.25, m_cup), (0.0032, r * 1.08, m_cup), (0.0026, r * 0.92, m_lens),
            (0.0040, r * 0.60, m_lens), (0.0046, 0.0, m_lens)]
    for sign in (1, -1):
        rings = []
        for h, rr, _ in prof:
            ring = []
            for k in range(segs):
                a = 2 * math.pi * k / segs
                c = P + N * h + (t1 * math.cos(a) + t2 * math.sin(a)) * rr
                ring.append(bm.verts.new((sign * c.x, c.y, c.z)))
            rings.append(ring)
        for i in range(len(rings) - 1):
            for k in range(segs):
                k2 = (k + 1) % segs
                _face(bm, [rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]], prof[i][2], flip=sign < 0)


# --------------------------------------------------------------------- mirrors

def _mirrors(p, body, col, root, n, paint, gloss):
    y = -0.60
    F = body.frame(body.s_of_y(y))
    base = F.top(0.01)
    bm = bmesh.new()
    pod = common.cushion_bmesh((0.055, 0.15, 0.048), cuts=2, edge=0.02,
                               crown={"+x": 0.008, "-y": 0.02, "+z": 0.005, "-z": 0.003})
    me_pod = bpy.data.meshes.new("tmp")
    pod.to_mesh(me_pod)
    pod.free()
    for sx in (1, -1):
        cx = sx * (base.x + 0.105)
        centre = Vector((cx, y + 0.02, base.z + 0.065))
        tmp = bmesh.new()
        tmp.from_mesh(me_pod)
        if sx < 0:
            bmesh.ops.scale(tmp, vec=(-1, 1, 1), verts=tmp.verts)
            bmesh.ops.reverse_faces(tmp, faces=tmp.faces)
        bmesh.ops.translate(tmp, vec=centre, verts=tmp.verts)
        tmp.normal_update()
        for f in tmp.faces:
            f.material_index = 1 if f.normal.y < -0.6 else 0
        me_t = bpy.data.meshes.new("tmp2")
        tmp.to_mesh(me_t)
        tmp.free()
        bm.from_mesh(me_t)
        bpy.data.meshes.remove(me_t)
        # stalk
        a = Vector((sx * (base.x - 0.01), y + 0.03, base.z))
        b = centre + Vector((-sx * 0.02, 0.02, -0.01))
        prof = [(0.014, 0.006), (0.014, -0.006), (-0.014, -0.006), (-0.014, 0.006)]
        ring0, ring1 = [], []
        for dy, dz in prof:
            ring0.append(bm.verts.new(a + Vector((0, dy * 1.4, dz))))
            ring1.append(bm.verts.new(b + Vector((0, dy, dz))))
        for k in range(4):
            k2 = (k + 1) % 4
            _face(bm, [ring0[k], ring0[k2], ring1[k2], ring1[k]], 1, flip=sx < 0)
    bpy.data.meshes.remove(me_pod)
    _new_mesh(f"{n}_Mirrors", bm, [paint, gloss], col, root)


# ---------------------------------------------------------------------- wheels

def _profile_v(prof):
    """Arc-length fraction of each profile point (texture v)."""
    L = [0.0]
    for (a0, r0), (a1, r1) in zip(prof, prof[1:]):
        L.append(L[-1] + math.hypot(a1 - a0, r1 - r0))
    return [x / L[-1] for x in L]


def _revolve(bm, prof, segs, centre, side, mat, sharp=(), flatten=None, phase=0.0, uv_repeat=None):
    cx, cy, cz = centre
    rings = []
    idx = {}
    for i_r, (a0, r0) in enumerate(prof):
        if r0 < 1e-7:
            v = bm.verts.new((cx + side * a0, cy, cz))
            rings.append([v] * segs)
            continue
        ring = []
        for k in range(segs):
            a, r = a0, r0
            th = phase + 2 * math.pi * k / segs
            z = cz + r * math.sin(th)
            if flatten is not None:
                z = max(z, flatten)
            ring.append(bm.verts.new((cx + side * a, cy + r * math.cos(th), z)))
            idx[ring[-1]] = (i_r, k)
        rings.append(ring)
    mats = mat if isinstance(mat, (list, tuple)) else [mat] * (len(prof) - 1)
    if uv_repeat:
        vs = _profile_v(prof)
        uvl = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        for k in range(segs):
            k2 = (k + 1) % segs
            f = _face(bm, [A[k], A[k2], B[k2], B[k]], mats[i], flip=side < 0)
            if f and uv_repeat:
                for lp in f.loops:
                    ir, kk = idx[lp.vert]
                    if kk == 0 and k == segs - 1:
                        kk = segs
                    lp[uvl].uv = (uv_repeat * kk / segs, vs[ir])
    for i in sharp:
        ring = set(rings[i])
        for v in rings[i]:
            for e in v.link_edges:
                if e.other_vert(v) in ring:
                    e.smooth = False
    return rings


def _spokes(bm, centre, side, m_face, m_side, phase=0.0):
    cx, cy, cz = centre
    r0, r1 = 0.074, 0.250
    rs = [r0, 0.13, 0.19, r1]
    for pair in range(5):
        base = phase + 2 * math.pi * pair / 5
        for sgn in (-1, 1):
            rings = []
            for r in rs:
                f = (r - r0) / (r1 - r0)
                ang = base + sgn * (0.06 + 0.10 * f)
                hw = (0.046 - 0.016 * f) / 2
                af = 0.093 + 0.022 * f
                depth = 0.034 - 0.016 * f
                dth = hw / r
                ring = []
                for da, dt in ((af, -dth), (af, dth), (af - depth, dth), (af - depth, -dth)):
                    th = ang + dt
                    ring.append(bm.verts.new((cx + side * da, cy + r * math.cos(th), cz + r * math.sin(th))))
                rings.append(ring)
            for i in range(len(rings) - 1):
                A, B = rings[i], rings[i + 1]
                for e in range(4):
                    e2 = (e + 1) % 4
                    _face(bm, [A[e], B[e], B[e2], A[e2]], m_face if e == 0 else m_side, flip=side < 0)


def _disc_face(bm, centre, side, mat):
    """Curved cooling slots on the disc's outer face (dark, a hair proud)."""
    cx, cy, cz = centre
    a = 0.0265
    for k in range(10):
        base = 2 * math.pi * k / 10
        pts = []
        for f in (0.0, 0.5, 1.0):
            r = 0.128 + 0.050 * f
            th = base + 0.22 * f
            pts.append((r, th))
        rows = []
        for r, th in pts:
            dth = 0.0028 / r
            rows.append([bm.verts.new((cx + side * a, cy + r * math.cos(th + d), cz + r * math.sin(th + d))) for d in (-dth, dth)])
        for i in range(len(rows) - 1):
            _face(bm, [rows[i][0], rows[i][1], rows[i + 1][1], rows[i + 1][0]], mat, flip=side < 0)


def _lug_nuts(bm, centre, side, mat):
    cx, cy, cz = centre
    for k in range(5):
        th = math.pi / 2 + 2 * math.pi * k / 5
        oy, oz = cy + 0.066 * math.cos(th), cz + 0.066 * math.sin(th)
        rings = []
        for a, rr in ((0.097, 0.0105), (0.108, 0.0105), (0.111, 0.007)):
            rings.append([bm.verts.new((cx + side * a, oy + rr * math.cos(2 * math.pi * j / 6), oz + rr * math.sin(2 * math.pi * j / 6)))
                          for j in range(6)])
        for i in range(2):
            for j in range(6):
                j2 = (j + 1) % 6
                f = _face(bm, [rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]], mat, flip=side < 0)
                if f:
                    f.smooth = False
        f = _face(bm, rings[-1], mat, flip=side < 0)
        if f:
            f.smooth = False


def _caliper(bm, centre, side, mat, ang_c):
    cx, cy, cz = centre
    span, nseg = 1.05, 10
    sec = [(0.060, 0.150), (0.062, 0.168), (0.062, 0.200), (0.058, 0.212), (0.048, 0.218), (-0.030, 0.218),
           (-0.036, 0.205), (-0.036, 0.155), (-0.030, 0.142), (0.052, 0.142)]
    rings = []
    for k in range(nseg + 1):
        th = ang_c - span / 2 + span * k / nseg
        rings.append([bm.verts.new((cx + side * a, cy + r * math.cos(th), cz + r * math.sin(th))) for a, r in sec])
    m = len(sec)
    for k in range(nseg):
        A, B = rings[k], rings[k + 1]
        for e in range(m):
            e2 = (e + 1) % m
            f = _face(bm, [A[e], A[e2], B[e2], B[e]], mat, flip=side > 0)
            if f:
                f.smooth = e not in (0, 4, 5, 9)
    for ring, fl in ((rings[0], side < 0), (rings[-1], side > 0)):
        f = _face(bm, list(ring), mat, flip=fl)
        if f:
            f.smooth = False


def _wheels(p, col, root, n, mats):
    RUB, GRA, MAC, DISC_, CAL, SHUT_ = range(6)
    bm = bmesh.new()
    segs = 40
    for ya, ang in ((p["front_axle"], 0.35), (p["rear_axle"], 0.35)):
        for sx in (1, -1):
            c = (sx * p["track"], ya, p["wheel_z"])
            _revolve(bm, TYRE, TYRE_SEGS, c, sx, RUB, sharp=TYRE_GROOVE_RINGS, flatten=0.0, phase=-math.pi / 2,
                     uv_repeat=TYRE_REPEAT)
            _revolve(bm, RIM, segs, c, sx, [GRA, MAC, MAC, GRA, GRA, GRA], sharp=(2,))
            _revolve(bm, HUB, 24, c, sx, [GRA, GRA, GRA, MAC, MAC], sharp=(1, 3))
            _revolve(bm, DISC, 28, c, sx, [DISC_, SHUT_, DISC_, DISC_, DISC_], sharp=(1, 2, 3, 4))
            _disc_face(bm, c, sx, SHUT_)
            _lug_nuts(bm, c, sx, MAC)
            _spokes(bm, c, sx, MAC, GRA, phase=math.pi / 2)
            _caliper(bm, c, sx, CAL, math.pi - ang if sx > 0 else math.pi - ang)
    _new_mesh(f"{n}_Wheels", bm, mats, col, root)


# -------------------------------------------------------------------- interior

def _merge(name, objects, col, parent):
    """Join many small parts into one mesh (one draw call per material in the engine):
    modifiers applied, world transforms baked (the root sits at the origin)."""
    dg = bpy.context.evaluated_depsgraph_get()
    mats, bm = [], bmesh.new()
    for ob in objects:
        if ob.type != "MESH":
            continue
        ev = ob.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev)
        me.transform(ev.matrix_world)
        remap = []
        for m in me.materials:
            if m not in mats:
                mats.append(m)
            remap.append(mats.index(m))
        for poly in me.polygons:
            poly.material_index = remap[poly.material_index] if remap else 0
        if me.uv_layers and me.uv_layers[0].name != "UVMap":
            me.uv_layers[0].name = "UVMap"
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    for ob in objects:
        data = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if data is not None and data.users == 0:
            bpy.data.meshes.remove(data)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    return common.link(bpy.data.objects.new(name, me), col, parent)


# ---------------------------------------------------------------------- checks

def _checks(p, body):
    """Fitment numbers printed with the build (catch what a 512 px preview hides)."""
    tyre_r = max(r for _, r in TYRE)
    tyre_out = p["track"] + max(a for a, _ in TYRE)
    for tag, ya in (("front", p["front_axle"]), ("rear", p["rear_axle"])):
        F = body.frame(body.s_of_y(ya))
        arch_top = body.zb_side(ya)
        lip_x = F.x0 - F.inset(arch_top)
        widest = F.x0
        print(f"CHECK {tag}: arch gap over tyre {arch_top - (p['wheel_z'] + tyre_r):.3f} m, "
              f"tyre outer x {tyre_out:.3f} vs arch lip x {lip_x:.3f}, body x {widest:.3f}; "
              f"shoulder z {F.zc:.3f}")


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
