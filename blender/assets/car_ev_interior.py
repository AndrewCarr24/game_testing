"""Cabin of car_ev (helper module, not an asset): sculpted seats, dashboard with screens,
steering wheel, centre console, door cards, floor mats, belts, mirror.

Everything here is seen through tinted glass from 1-2 m, lit by the room probe, so the
craft goes into silhouette and overlapping soft forms (bolsters, piping, flutes, knee roll),
contrast lines (cream stitching, polished metal) and one small glow (the screens' UI).

Seats are lofted closed sections: each station's section is the upholstery profile across
the seat (fluted insert, seam with piping, side bolster, side panel, back shell), swept
along the cushion (front to back) or the backrest (bottom to top), with rounded ends made
by shrinking the section on a quarter circle. Stitching and piping are generated on the
same analytic profile. car_ev._interior calls build(); car_ev merges the result into one
mesh (CarEV_Interior).
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from lib import common, textures

SCREEN_TEX = "T_CarEV_Screen_Emissive"
SCREEN_VERSION = 4          # bump to regenerate the UI texture


# ------------------------------------------------------------------- helpers

def _sm(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def _bump(t, c, w):
    return math.exp(-((t - c) / w) ** 2)


def _face(bm, verts, mat=0, smooth=True):
    uniq = []
    for v in verts:
        if v not in uniq:
            uniq.append(v)
    if len(uniq) < 3:
        return None
    try:
        f = bm.faces.new(uniq)
    except ValueError:
        return None
    f.material_index = mat
    f.smooth = smooth
    return f


ORIENT = []     # (faces, outward vector) for open sheets; applied after recalc_face_normals


def orient(faces, out):
    ORIENT.append(([f for f in faces if f is not None], Vector(out)))


def loft(bm, rings, closed=True, mat_fn=None, cap0=None, cap1=None, out=None):
    """Quad strips between consecutive rings (lists of Vector, same length).
    cap0 / cap1: material index for an n-gon closing the first / last ring (None: open).
    out: for open sheets, a vector the faces should point along (else recalc decides)."""
    vs = [[bm.verts.new(c) for c in r] for r in rings]
    n = len(vs[0])
    made = []
    for i in range(len(vs) - 1):
        for j in range(n if closed else n - 1):
            j2 = (j + 1) % n
            made.append(_face(bm, [vs[i][j], vs[i][j2], vs[i + 1][j2], vs[i + 1][j]], mat_fn(i, j) if mat_fn else 0))
    if out is not None:
        orient(made, out)
    if cap0 is not None:
        _face(bm, list(reversed(vs[0])), cap0, smooth=False)
    if cap1 is not None:
        _face(bm, vs[-1], cap1, smooth=False)
    return vs


def tube(bm, pts, r, sides=6, mat=0, closed=False, flat=1.0, up=None):
    """Swept tube along pts (parallel-transport frames). flat < 1 squashes the
    section along the frame's second axis (an oval)."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    if n < 2:
        return
    tans = []
    for i in range(n):
        if closed:
            a, b = pts[i - 1], pts[(i + 1) % n]
        else:
            a, b = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        tans.append((b - a).normalized())
    ref = Vector(up) if up is not None else Vector((0, 0, 1))
    if abs(ref.dot(tans[0])) > 0.9:
        ref = Vector((1, 0, 0)) if abs(tans[0].x) < 0.9 else Vector((0, 1, 0))
    u = (ref - tans[0] * ref.dot(tans[0])).normalized()
    rings = []
    for i in range(n):
        t = tans[i]
        u = (u - t * u.dot(t))
        u = u.normalized() if u.length > 1e-9 else u
        v = t.cross(u)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(pts[i] + u * (r * math.cos(a)) + v * (r * flat * math.sin(a)))
        rings.append(ring)
    if closed:
        rings.append(rings[0])
    vs = loft(bm, rings, closed=True, mat_fn=lambda i, j: mat)
    return vs


def ribbon(bm, pts, sides, width, mat=0, out=(0, 0, 1)):
    """Flat strip through pts; sides[i] = unit vector across the strip at pts[i];
    its faces point along `out`."""
    rows = [[p - s * (width / 2), p + s * (width / 2)] for p, s in zip(pts, sides)]
    loft(bm, rows, closed=False, mat_fn=lambda i, j: mat, out=out)


def rbox(bm, size, r, centre=(0, 0, 0), seg=2, mat=0, rot=None, crown=None):
    """Rounded box (core box + radius r on every edge and corner), seg segments per
    45 degrees of each rounded edge. rot: optional 3x3 Matrix; crown: {'+z': m, ...}."""
    half = [s / 2 for s in size]
    rr = [min(r, h * 0.98) for h in half]
    S = []
    for a in range(3):
        c = half[a] - rr[a]
        lst = [(-c, -math.tan(math.pi / 4 * (1 - j / seg))) for j in range(seg)]
        lst += [(-c, 0.0), (c, 0.0)]
        lst += [(c, math.tan(math.pi / 4 * j / seg)) for j in range(1, seg + 1)]
        S.append(lst)
    N = [len(s) - 1 for s in S]
    cache = {}
    crown = crown or {}
    C = Vector(centre)

    def vert(i, j, k):
        key = (i, j, k)
        v = cache.get(key)
        if v is None:
            cs = (S[0][i][0], S[1][j][0], S[2][k][0])
            d = Vector((S[0][i][1], S[1][j][1], S[2][k][1]))
            d.normalize()
            p = Vector(cs) + Vector((d.x * rr[0], d.y * rr[1], d.z * rr[2]))
            for ax, key2 in enumerate("xyz"):
                for sg in "+-":
                    amp = crown.get(sg + key2, 0.0)
                    if amp and (p[ax] > 0) == (sg == "+"):
                        o = [b for b in range(3) if b != ax]
                        f = max(0.0, 1 - (p[o[0]] / half[o[0]]) ** 2) * max(0.0, 1 - (p[o[1]] / half[o[1]]) ** 2)
                        p[ax] += amp * f * (abs(p[ax]) / half[ax])
            if rot is not None:
                p = rot @ p
            v = cache[key] = bm.verts.new(C + p)
        return v
    fs = []
    for ax in range(3):
        a1, a2 = [b for b in range(3) if b != ax]
        for side in (0, N[ax]):
            for p in range(N[a1]):
                for q in range(N[a2]):
                    idx = [0, 0, 0]
                    quad = []
                    for dp, dq in ((0, 0), (1, 0), (1, 1), (0, 1)):
                        idx[ax], idx[a1], idx[a2] = side, p + dp, q + dq
                        quad.append(vert(*idx))
                    f = _face(bm, quad, mat)
                    if f:
                        fs.append(f)
    return fs


def new_obj(name, bm, mats, col, parent, uv_tile=None, sharp=None, recalc=True):
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = common.link(bpy.data.objects.new(name, me), col, parent)
    if sharp is not None:
        me.set_sharp_from_angle(angle=math.radians(sharp))
    if uv_tile:
        common.box_uv(ob, tile=uv_tile)
    return ob


# ------------------------------------------------------------------- seats

class SeatSection:
    """Upholstery section across a seat part: (x, h) with h out of the seated surface."""

    def __init__(self, W, xi, B, D, crown, grooves, gd=0.0045, rear=0.0, side=0.55):
        self.W, self.xi, self.B, self.D, self.crown = W, xi, B, D, crown
        self.grooves, self.gd = grooves, gd

        def c(x):
            return crown * max(0.0, 1 - (x / xi) ** 2)
        self.c = c
        top = [(0.0, crown)]
        for g in grooves:
            top += [(g, c(g) - gd)]
        top += [(xi - 0.012, c(xi - 0.012)), (xi, -0.007)]
        bw = W - xi
        top += [(xi + 0.010, 0.28 * B), (xi + 0.40 * bw, 0.86 * B), (xi + 0.70 * bw, B),
                (W - 0.012, 0.62 * B), (W, 0.0)]
        sidep = [(W + 0.002, -side * D), (W - 0.016, -D)]
        back = [(0.55 * W, -D - 0.7 * rear), (0.0, -D - rear)]
        half = top + sidep + back
        self.top = top
        self.loop = half + [(-x, h) for x, h in reversed(half[1:-1])]
        self.back_flags = [h <= -D + 1e-9 for _, h in self.loop]
        hs = [h for _, h in self.loop]
        self.hc = (max(hs) + min(hs)) / 2
        self.Hh = (max(hs) - min(hs)) / 2
        self.Wm = max(abs(x) for x, _ in self.loop)

    def h_at(self, x):
        x = abs(x)
        for (x0, h0), (x1, h1) in zip(self.top, self.top[1:]):
            if x0 <= x <= x1:
                return h0 + (h1 - h0) * (x - x0) / max(x1 - x0, 1e-9)
        return self.top[-1][1]

    def shrink(self, x, h, e):
        return x * (1 - e / self.Wm), self.hc + (h - self.hc) * (1 - e / self.Hh)


class SeatPart:
    """A swept seat part: origin O, sweep axis A, out-of-surface axis Hn, across = +x."""

    def __init__(self, O, A, Hn, L, sec_fn, r0, r1, n_mid):
        self.O, self.A, self.Hn, self.L = Vector(O), Vector(A).normalized(), Vector(Hn).normalized(), L
        self.X = Vector((1, 0, 0))
        st = []          # (s, e) station distance and shrink
        if r0 > 0:
            for a in (0.0, math.pi / 6, math.pi / 3):
                st.append((r0 * (1 - math.cos(a)), r0 * (1 - math.sin(a))))
        s_a, s_b = r0, L - r1
        for k in range(n_mid + 1):
            st.append((s_a + (s_b - s_a) * k / n_mid, 0.0))
        if r1 > 0:
            for a in (math.pi / 3, math.pi / 6, 0.0):
                st.append((L - r1 * (1 - math.cos(a)), r1 * (1 - math.sin(a))))
        self.st = st
        self.secs = [sec_fn(s / L) for s, _ in st]

    def P(self, s, x, h):
        return self.O + self.A * s + self.X * x + self.Hn * h

    def build(self, bm, mat_top, mat_back, cap0=True, cap1=True):
        rings = []
        for (s, e), sec in zip(self.st, self.secs):
            ring = []
            for x, h in sec.loop:
                xx, hh = sec.shrink(x, h, e)
                ring.append(self.P(s, xx, hh))
            rings.append(ring)
        flags = self.secs[len(self.secs) // 2].back_flags
        n = len(flags)

        def mf(i, j):
            return mat_back if flags[j] and flags[(j + 1) % n] else mat_top
        loft(bm, rings, closed=True, mat_fn=mf, cap0=mat_back if cap0 else None, cap1=mat_top if cap1 else None)

    def line(self, x, dh=0.0, k0=1, k1=None):
        """Points along the part at constant x on the top profile (skipping the end caps)."""
        k1 = len(self.st) - 1 if k1 is None else k1
        pts = []
        for (s, e), sec in list(zip(self.st, self.secs))[k0:k1]:
            xx, hh = sec.shrink(x, sec.h_at(x) + dh, e)
            pts.append(self.P(s, xx, hh))
        return pts


def _seat(bm, M, x0, front, rear_seat=False, centre=False):
    """One seat. front = (y, z) of the cushion's front top edge."""
    LEA, SHELL, SATIN, STITCH, STEEL = M["lea"], M["shell"], M["satin"], M["stitch"], M["steel"]
    yf, zf = front
    if centre:
        Lc, th_c, Wc = 0.44, math.radians(5), 0.112
    elif rear_seat:
        Lc, th_c, Wc = 0.46, math.radians(6), 0.245
    else:
        Lc, th_c, Wc = 0.50, math.radians(4), 0.255
    Ac = Vector((0, math.cos(th_c), -math.sin(th_c)))
    Hc = Vector((0, math.sin(th_c), math.cos(th_c)))
    grooves = [] if centre else [0.044, 0.088]
    xi = 0.10 if centre else 0.132

    def cush_sec(t):
        if centre:
            return SeatSection(Wc, xi, 0.004, 0.09, 0.010, [], rear=0.0)
        B = 0.030 + 0.042 * math.sin(math.pi * min(max(t, 0), 1)) ** 0.6
        if rear_seat:
            B *= 0.7
        return SeatSection(Wc, xi, B, 0.10, 0.013, grooves, rear=0.0)
    cush = SeatPart((x0, yf, zf), Ac, Hc, Lc, cush_sec, 0.036, 0.03, 4 if (rear_seat or centre) else 5)
    cush.build(bm, LEA, SATIN)

    # backrest
    tilt = math.radians(24 if (rear_seat or centre) else 19)
    Ab = Vector((0, math.sin(tilt), math.cos(tilt)))
    Hb = Vector((0, -math.cos(tilt), math.sin(tilt)))
    end = cush.O + Ac * Lc
    Ob = end + Vector((0, -0.012, -0.05)) - Hb * 0.0
    Lb = 0.54 if (rear_seat or centre) else 0.62

    def back_sec(t):
        if centre:
            return SeatSection(Wc, xi, 0.004, 0.075, 0.008, [], rear=0.012)
        W = Wc + 0.010 * _bump(t, 0.3, 0.2) - 0.030 * _sm(0.55, 1.0, t)
        B = 0.022 + 0.058 * _bump(t, 0.33, 0.2) * (0.65 if rear_seat else 1.0)
        crown = 0.010 + 0.014 * _bump(t, 0.18, 0.12)
        return SeatSection(W, xi - 0.012 * _sm(0.55, 1.0, t), B, 0.085 - 0.02 * t, crown, grooves,
                           rear=0.018 if not rear_seat else 0.0)
    back = SeatPart(Ob, Ab, Hb, Lb, back_sec, 0.0, 0.042, 5 if (rear_seat or centre) else 7)
    back.build(bm, LEA, SATIN if rear_seat or centre else SHELL, cap0=True, cap1=True)

    # piping along the insert seams, stitching in the flutes and beside the piping
    if not centre:
        for part in (cush, back):
            k1 = len(part.st) - 1
            for sx in (1, -1):
                xs = sx * part.secs[len(part.secs) // 2].xi
                tube(bm, part.line(xs, 0.004, 1, k1), 0.0042, sides=4, mat=LEA)
                for g in grooves:
                    pts = part.line(sx * g, 0.0012, 1, k1)
                    ribbon(bm, pts, [part.X] * len(pts), 0.0026, STITCH, out=part.Hn)
                if not rear_seat:
                    pts = part.line(xs + sx * 0.016, 0.0015, 1, k1)
                    ribbon(bm, pts, [part.X] * len(pts), 0.0024, STITCH, out=part.Hn)

    # headrest on two posts
    if not centre:
        hcen = Ob + Ab * (Lb + 0.10) - Hb * 0.012
        hw, hd, hh = (0.125, 0.052, 0.085) if not rear_seat else (0.12, 0.048, 0.075)
        n = 14
        loop = []
        for k in range(n):
            a = 2 * math.pi * k / n
            c, s = math.cos(a), math.sin(a)
            x = hw * math.copysign(abs(c) ** 0.45, c)
            h = hd * math.copysign(abs(s) ** 0.6, s) + (0.012 * c * c if s > 0 else 0.0)
            loop.append((x, h))
        rings = []
        r = 0.035
        sts = [(-hh + r * (1 - math.cos(a)), r * (1 - math.sin(a))) for a in (0.0, math.pi / 6, math.pi / 3)]
        sts += [(-hh + r + (2 * hh - 2 * r) * k / 2, 0.0) for k in range(3)]
        sts += [(hh - r * (1 - math.cos(a)), r * (1 - math.sin(a))) for a in (math.pi / 3, math.pi / 6, 0.0)]
        for sv, e in sts:
            f = 1 - e / hd
            fx = 1 - e / hw
            rings.append([hcen + Ab * sv + Vector((x * fx, 0, 0)) + Hb * (h * f) for x, h in loop])
        loft(bm, rings, closed=True, mat_fn=lambda i, j: LEA, cap0=LEA, cap1=LEA)
        for px in (-0.065, 0.065):
            a = Ob + Ab * (Lb - 0.03) - Hb * 0.02 + Vector((x0 * 0 + px, 0, 0))
            b = hcen + Ab * (-hh + 0.01) + Vector((px, 0, 0)) - Hb * 0.0
            a.x = b.x = x0 + px
            tube(bm, [a, b], 0.0065, sides=6, mat=STEEL)

    # pan, side trim and rails under the cushion (front seats)
    if not rear_seat and not centre:
        yc = yf + Lc / 2
        rbox(bm, (2 * Wc - 0.03, Lc - 0.06, 0.08), 0.02, (x0, yc + 0.01, zf - 0.13), seg=1, mat=SATIN)
        for rx in (-0.17, 0.17):
            rbox(bm, (0.03, 0.62, 0.025), 0.0, (x0 + rx, yc + 0.02, 0.312), seg=0, mat=SATIN)
        # outboard seat-adjust switches
        sx = 1 if x0 > 0 else -1
        rbox(bm, (0.012, 0.12, 0.03), 0.0, (x0 + sx * (Wc + 0.004), yf + 0.10, zf - 0.07), seg=0, mat=SHELL)
    return cush, back


# --------------------------------------------------------------- dashboard

def _dash(bm, M, p, body):
    DARK, LEA, SATIN, WOOD, GLOSS, STEEL, STITCH = (M["dark"], M["lea"], M["satin"], M["wood"], M["gloss"],
                                                    M["steel"], M["stitch"])
    # (y, z, material of the segment that starts here); runs top-front -> cabin -> under -> back
    prof = [(-0.80, 0.846, DARK), (-0.66, 0.852, DARK), (-0.53, 0.851, DARK), (-0.475, 0.846, DARK),
            (-0.445, 0.832, DARK), (-0.428, 0.812, DARK), (-0.421, 0.790, SATIN), (-0.419, 0.776, DARK),
            (-0.417, 0.734, DARK), (-0.418, 0.716, LEA), (-0.426, 0.690, LEA), (-0.444, 0.664, LEA),
            (-0.474, 0.642, LEA), (-0.515, 0.630, SATIN), (-0.62, 0.612, SATIN), (-0.73, 0.595, SATIN),
            (-0.79, 0.65, SATIN), (-0.80, 0.78, SATIN)]
    yc = sum(q[0] for q in prof) / len(prof)
    zc = sum(q[1] for q in prof) / len(prof)
    xs = []
    xd = 0.775
    r = 0.03
    for a in (0.0, math.pi / 4):
        xs.append((-xd + r * (1 - math.cos(a)), r * (1 - math.sin(a))))
    for k in range(13):
        xs.append((-xd + r + (2 * xd - 2 * r) * k / 12, 0.0))
    for a in (math.pi / 4, 0.0):
        xs.append((xd - r * (1 - math.cos(a)), r * (1 - math.sin(a))))

    def at(x, i, e=0.0, off=0.0):
        y, z = prof[i][0], prof[i][1]
        u = (x / xd) ** 2
        if i < 14:                       # the cabin face wraps round towards the doors
            y += 0.035 * (1 - u) * min(1.0, (y + 0.80) / 0.25)
            z += 0.006 * (1 - u) * (1.0 if i < 6 else 0.0)
        f = 1 - e / 0.12
        v = Vector((x, yc + (y - yc) * f, zc + (z - zc) * f))
        if off:
            a, b = prof[max(i - 1, 0)], prof[min(i + 1, len(prof) - 1)]
            t = Vector((0, b[0] - a[0], b[1] - a[1])).normalized()
            v += Vector((0, -t.z, t.y)) * off
        return v
    rings = [[at(x, i, e) for i in range(len(prof))] for x, e in xs]
    loft(bm, rings, closed=True, mat_fn=lambda i, j: prof[j][2], cap0=SATIN, cap1=SATIN)
    xi = [x for x, e in xs if e == 0.0]
    # walnut band across the face (between profile points 7 and 8), proud with thickness
    wx = [x for x in xi if abs(x) < 0.74]
    band = []
    for x in wx:
        a, b = at(x, 7, off=0.0005), at(x, 8, off=0.0005)
        a2, b2 = at(x, 7, off=0.0045), at(x, 8, off=0.0045)
        band.append([a, a2, b2, b])
    loft(bm, band, closed=True, mat_fn=lambda i, j: WOOD, cap0=WOOD, cap1=WOOD)
    # air vent slot across the face (segment 6: satin) with a polished vane
    vx = [x for x in xi if abs(x) < 0.70]
    pts = [(at(x, 6, off=0.0008) + at(x, 7, off=0.0008)) / 2 for x in vx]
    ribbon(bm, pts, [(at(x, 7) - at(x, 6)).normalized() for x in vx], 0.010, GLOSS, out=(0, 1, 0))
    pts = [(at(x, 6, off=0.0016) + at(x, 7, off=0.0016)) / 2 for x in vx]
    ribbon(bm, pts, [(at(x, 7) - at(x, 6)).normalized() for x in vx], 0.0022, STEEL, out=(0, 1, 0))
    # piping where the knee roll meets the face, cream stitch below it
    kx = [x for x in xi if abs(x) < 0.76]
    tube(bm, [at(x, 9, off=0.002) for x in kx], 0.004, sides=4, mat=LEA)
    pts = [(at(x, 9, off=0.0012) * 0.55 + at(x, 10, off=0.0012) * 0.45) for x in kx]
    ribbon(bm, pts, [(at(x, 10) - at(x, 9)).normalized() for x in kx], 0.003, STITCH, out=(0, 1, 0))
    # glovebox shut line on the passenger knee roll (x -0.66 .. -0.22, profile 10 .. 12)
    loop = [at(-0.66, 10, off=0.0012), at(-0.22, 10, off=0.0012), at(-0.22, 11, off=0.0012),
            at(-0.22, 12, off=0.0012), at(-0.66, 12, off=0.0012), at(-0.66, 11, off=0.0012)]
    pts = common.fillet_polyline(loop, 0.015, segments=3, closed=True)
    tube(bm, pts, 0.0018, sides=3, mat=GLOSS, closed=True)

    # dash top: stitched seam across, defrost grille at the windscreen base, corner
    # tweeters, a head-up display window in front of the driver
    tx = [x for x in xi if abs(x) < 0.74]
    for dy in (-0.004, 0.004):
        pts = []
        for x in tx:
            v = at(x, 2) * 0.62 + at(x, 3) * 0.38
            pts.append(v + Vector((0, dy, 0.0012)))
        ribbon(bm, pts, [Vector((0, 1, 0))] * len(pts), 0.0026, STITCH)
    gx = [x for x in xi if abs(x) < 0.66]
    pts = [at(x, 0) * 0.55 + at(x, 1) * 0.45 + Vector((0, 0, 0.0012)) for x in gx]
    ribbon(bm, pts, [Vector((0, 1, 0))] * len(pts), 0.028, GLOSS)
    for dy in (-0.008, 0.0, 0.008):
        ribbon(bm, [q + Vector((0, dy, 0.0006)) for q in pts], [Vector((0, 1, 0))] * len(pts), 0.0018, SATIN)
    for sx in (1, -1):
        cc = Vector((sx * 0.66, -0.60, 0.0))
        cc.z = (at(0.66, 1).z + at(0.66, 2).z) / 2 + 0.0012
        ring = [cc + Vector((0.032 * math.cos(2 * math.pi * k / 16), 0.032 * math.sin(2 * math.pi * k / 16), 0)) for k in range(16)]
        tube(bm, ring, 0.0028, sides=3, mat=STEEL, closed=True)
        orient([_face(bm, [bm.verts.new(q + (cc - q) * 0.08) for q in ring], GLOSS, smooth=False)], (0, 0, 1))
    hz = at(0.40, 1).z + 0.0015
    rbox(bm, (0.20, 0.09, 0.003), 0.012, (0.40, -0.66, hz), seg=1, mat=GLOSS)
    return at


def _screen(bm, M, centre, w, h, tilt_deg, uv_rect, stem_to=None):
    GLOSS, SCREEN, SATIN = M["gloss"], M["screen"], M["satin"]
    t = math.radians(tilt_deg)
    ex = Vector((1, 0, 0))
    ey = Vector((0, -math.sin(t), math.cos(t)))     # up the screen, leaning away from the viewer
    nz = ey.cross(ex)                                # towards the occupants (+y, up)
    rot = np.array([ex, ey, nz]).T
    from mathutils import Matrix
    R = Matrix(rot.tolist())
    C = Vector(centre)
    rbox(bm, (w, h, 0.018), 0.006, C - nz * 0.004, seg=1, mat=GLOSS, rot=R)
    # lit face: a grid so the UV rect maps cleanly, 0.6 mm proud of the glass
    m = 0.008
    u0, v0, u1, v1 = uv_rect
    verts = []
    for j in range(2):
        row = []
        for i in range(2):
            co = C + ex * ((-w / 2 + m) + (w - 2 * m) * i) + ey * ((-h / 2 + m) + (h - 2 * m) * j) + nz * 0.0056
            row.append(bm.verts.new(co))
        verts.append(row)
    f = bm.faces.new([verts[0][0], verts[0][1], verts[1][1], verts[1][0]])
    f.material_index = SCREEN
    f.smooth = False
    orient([f], nz)
    if stem_to is not None:
        a = C - nz * 0.012 - ey * (h * 0.15)
        tube(bm, [a, Vector(stem_to)], 0.012, sides=8, mat=SATIN, flat=0.5)
    return f


def screen_texture(force=False):
    path = os.path.join(textures.TEX_DIR, SCREEN_TEX + ".png")
    stamp = os.path.join(textures.TEX_DIR, "..", "..", "build", "texture_stamps", f"{SCREEN_TEX}.v{SCREEN_VERSION}")
    os.makedirs(os.path.dirname(stamp), exist_ok=True)
    if os.path.exists(path) and not force and os.path.exists(stamp):
        return path
    N = 1024
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) + 0.5
    img = np.zeros((N, N, 3), np.float32)

    def put(cov, col):
        cov = np.clip(cov, 0, 1)[..., None]
        img[:] = img * (1 - cov) + np.array(col, np.float32) * cov

    def cov(d, w=1.2):
        return np.clip(0.5 - d / w, 0, 1)

    def rrect(cx, cy, hx, hy, r):
        qx, qy = np.abs(xx - cx) - hx + r, np.abs(yy - cy) - hy + r
        return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r

    def seg(ax, ay, bx, by, r):
        px, py, dx, dy = xx - ax, yy - ay, bx - ax, by - ay
        h = np.clip((px * dx + py * dy) / max(dx * dx + dy * dy, 1e-9), 0, 1)
        return np.hypot(px - dx * h, py - dy * h) - r

    def circ(cx, cy, r):
        return np.hypot(xx - cx, yy - cy) - r

    def arc(cx, cy, r, w, a0, a1):
        ang = np.arctan2(-(yy - cy), xx - cx)
        d = np.abs(np.hypot(xx - cx, yy - cy) - r) - w
        inside = (ang >= a0) & (ang <= a1)
        return np.where(inside, d, 1e3)

    # 7-segment digits drawn with round-capped strokes (cx, cy = centre, s = height)
    SEGS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc",
            "7": "abc", "8": "abcdefg", "9": "abcdfg"}

    def digit(ch, cx, cy, s, wgt, col):
        w2, h2 = s * 0.28, s * 0.5
        P = {"a": ((-w2, -h2), (w2, -h2)), "b": ((w2, -h2), (w2, 0)), "c": ((w2, 0), (w2, h2)),
             "d": ((-w2, h2), (w2, h2)), "e": ((-w2, 0), (-w2, h2)), "f": ((-w2, -h2), (-w2, 0)),
             "g": ((-w2, 0), (w2, 0))}
        d = np.full_like(xx, 1e3)
        for sg in SEGS[ch]:
            (x0, y0), (x1, y1) = P[sg]
            d = np.minimum(d, seg(cx + x0, cy + y0, cx + x1, cy + y1, wgt))
        put(cov(d), col)

    def text(s, cx, cy, size, wgt, col, gap=0.72):
        x = cx - (len(s) - 1) * size * gap / 2
        for ch in s:
            if ch in SEGS:
                digit(ch, x, cy, size, wgt, col)
            x += size * gap

    def letter(ch, cx, cy, s, wgt, col):
        w2, h2 = s * 0.26, s * 0.5
        L = []
        if ch == "P":
            L = [((-w2, -h2), (-w2, h2)), ((-w2, -h2), (w2 * 0.6, -h2)), ((-w2, 0), (w2 * 0.6, 0)),
                 ((w2, -h2 * 0.6), (w2, -h2 * 0.4))]
        elif ch == "R":
            L = [((-w2, -h2), (-w2, h2)), ((-w2, -h2), (w2 * 0.6, -h2)), ((-w2, 0), (w2 * 0.6, 0)),
                 ((w2, -h2 * 0.6), (w2, -h2 * 0.4)), ((0, 0), (w2, h2))]
        elif ch == "N":
            L = [((-w2, -h2), (-w2, h2)), ((w2, -h2), (w2, h2)), ((-w2, -h2), (w2, h2))]
        elif ch == "D":
            L = [((-w2, -h2), (-w2, h2)), ((-w2, -h2), (w2 * 0.3, -h2)), ((-w2, h2), (w2 * 0.3, h2)),
                 ((w2 * 0.3, -h2), (w2, -h2 * 0.4)), ((w2 * 0.3, h2), (w2, h2 * 0.4)), ((w2, -h2 * 0.4), (w2, h2 * 0.4))]
        d = np.full_like(xx, 1e3)
        for (x0, y0), (x1, y1) in L:
            d = np.minimum(d, seg(cx + x0, cy + y0, cx + x1, cy + y1, wgt))
        put(cov(d), col)

    WHITE = (0.80, 0.84, 0.88)
    DIM = (0.10, 0.11, 0.13)
    MID = (0.28, 0.30, 0.34)
    CYAN = (0.10, 0.52, 0.95)
    # -------- cluster: rows 0..380 (aspect 2.7 : 1)
    cl = yy < 380
    img[cl] = (0.0015, 0.002, 0.0035)
    # lane view in the middle: road edges converging, the car, a lead car
    for sx in (-1, 1):
        put(cov(seg(512 + sx * 150, 370, 512 + sx * 40, 70, 3.0)) * 0.9, MID)
        put(cov(seg(512 + sx * 52, 370, 512 + sx * 13, 70, 2.0)) * 0.5, MID)
    put(cov(rrect(512, 300, 34, 50, 16)), (0.62, 0.66, 0.72))
    put(cov(rrect(512, 300, 26, 16, 6)) * 0.8, (0.05, 0.06, 0.07))
    put(cov(rrect(512, 138, 14, 20, 7)), (0.30, 0.33, 0.38))
    # speed and units (left)
    text("68", 205, 175, 150, 9.0, WHITE)
    put(cov(seg(170, 280, 240, 280, 3.5)), MID)
    # gear letters with P lit
    for k, ch in enumerate("PRND"):
        letter(ch, 145 + k * 42, 335, 30, 3.0, WHITE if ch == "P" else DIM)
    # range bar and percentage (right)
    put(cov(np.abs(rrect(820, 175, 120, 18, 18)) - 2.5), MID)
    put(cov(rrect(820 - 120 + 0.78 * 120, 175, 0.78 * 120 - 6, 12, 12)), CYAN)
    text("412", 820, 98, 70, 6.0, WHITE)
    put(cov(seg(770, 250, 870, 250, 3.0)), MID)
    put(cov(seg(770, 280, 840, 280, 3.0)), DIM)
    # thin arc framing the cluster

    # -------- centre display: rows 392..1024 (aspect 1.62 : 1)
    y0 = 392
    cs = yy >= y0
    img[cs] = (0.0035, 0.004, 0.0055)
    rng = np.random.default_rng(5)
    mask = cs.astype(np.float32)
    # parks / water blocks
    for _ in range(6):
        cx, cy = rng.uniform(360, 1000), rng.uniform(y0 + 40, 1000)
        put(cov(rrect(cx, cy, rng.uniform(30, 80), rng.uniform(20, 60), 14)) * mask, (0.004, 0.012, 0.006))
    put(cov(rrect(930, 520, 120, 90, 50)) * mask, (0.003, 0.007, 0.018))
    # street grid (slightly rotated)
    ang = math.radians(14)
    ca, sa = math.cos(ang), math.sin(ang)
    for k in range(-6, 9):
        o = k * 78 + 20
        ax, ay = 640 + o * ca - 800 * sa, 700 + o * sa + 800 * ca
        bx, by = 640 + o * ca + 800 * sa, 700 + o * sa - 800 * ca
        put(cov(seg(ax, ay, bx, by, 2.6 if k % 3 else 4.5)) * mask, (0.018, 0.019, 0.022))
        ax, ay = 640 - 800 * ca - o * sa, 700 - 800 * sa + o * ca
        bx, by = 640 + 800 * ca - o * sa, 700 + 800 * sa + o * ca
        put(cov(seg(ax, ay, bx, by, 2.2 if k % 2 else 4.0)) * mask, (0.018, 0.019, 0.022))
    # route and position
    route = [(560, 960), (600, 820), (720, 790), (760, 640), (900, 600), (950, 470)]
    for a, b in zip(route, route[1:]):
        put(cov(seg(*a, *b, 7.0)) * mask, CYAN)
    put(cov(circ(950, 470, 12)) * mask, WHITE)
    put(cov(circ(560, 960, 16)) * mask, WHITE)
    put(cov(circ(560, 960, 8)) * mask, CYAN)
    # left card: next turn + ETA
    put(cov(rrect(170, y0 + 150, 140, 110, 18)) * mask, (0.010, 0.011, 0.014))
    put(cov(seg(110, y0 + 190, 110, y0 + 110, 7)) * mask, WHITE)
    put(cov(seg(110, y0 + 110, 150, y0 + 110, 7)) * mask, WHITE)
    put(cov(seg(150, y0 + 96, 165, y0 + 110, 6)) * mask, WHITE)
    put(cov(seg(150, y0 + 124, 165, y0 + 110, 6)) * mask, WHITE)
    text("350", 240, y0 + 130, 44, 4.0, WHITE)
    put(cov(seg(200, y0 + 185, 290, y0 + 185, 3.0)) * mask, MID)
    put(cov(seg(200, y0 + 215, 260, y0 + 215, 3.0)) * mask, DIM)
    # media card
    put(cov(rrect(170, y0 + 400, 140, 90, 18)) * mask, (0.010, 0.011, 0.014))
    g = np.clip((xx - 60) / 120, 0, 1)
    art = cov(rrect(120, y0 + 390, 50, 50, 8)) * mask
    put(art, (0.0, 0.0, 0.0))
    img[:] += art[..., None] * (np.array((0.55, 0.22, 0.08)) * (1 - g[..., None]) + np.array((0.25, 0.05, 0.20)) * g[..., None])
    put(cov(seg(195, y0 + 370, 290, y0 + 370, 4.0)) * mask, WHITE)
    put(cov(seg(195, y0 + 400, 260, y0 + 400, 3.0)) * mask, MID)
    put(cov(seg(60, y0 + 465, 280, y0 + 465, 2.5)) * mask, DIM)
    put(cov(seg(60, y0 + 465, 160, y0 + 465, 2.5)) * mask, WHITE)
    # status bar and dock
    text("1045", 512, y0 + 30, 26, 2.6, MID)
    for k in range(3):
        put(cov(circ(960 - k * 26, y0 + 30, 6)) * mask, MID)
    put(cov(rrect(512, 1000, 470, 26, 14)) * mask, (0.008, 0.009, 0.012))
    for k in range(8):
        cx = 512 + (k - 3.5) * 104
        put(cov(rrect(cx, 1000, 16, 16, 5)) * mask, CYAN if k == 1 else MID)
    # soft vignette towards the edges of each display (cheap glass look)
    vig = 1 - 0.25 * (np.abs(xx - 512) / 512) ** 3
    img *= vig[..., None]
    rgb = textures._to_srgb(img)
    out = textures._save(SCREEN_TEX, rgb)
    open(stamp, "w").close()
    return out


def screen_material(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = common.pbr_material(name, (0.006, 0.0065, 0.008), roughness=0.06, coat=0.0)
    bsdf = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.006, 0.0065, 0.008, 1)
    bsdf.inputs["Roughness"].default_value = 0.06
    img = textures.load(screen_texture())
    if not any(nd.type == "TEX_IMAGE" for nd in m.node_tree.nodes):
        tex = m.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.location = (-400, -200)
        m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 1.4
    return m


# ------------------------------------------------------------ steering wheel

def _wheel(bm, M):
    SATIN, STEEL, GLOSS, STITCH = M["satin"], M["steel"], M["gloss"], M["stitch"]
    c = Vector((0.40, -0.30, 0.80))
    tilt = math.radians(24)
    nz = Vector((0, math.cos(tilt), math.sin(tilt)))       # towards the driver
    ex = Vector((1, 0, 0))
    ey = nz.cross(ex).normalized()                          # wheel "up"
    if ey.z < 0:
        ey = -ey
    R = 0.178
    # D-shaped rim: flat bottom, slightly fuller grips at 9 and 3
    pts = []
    n = 40
    for k in range(n):
        a = 2 * math.pi * k / n
        x, y = math.cos(a), math.sin(a)
        y = y if y > -0.88 else -0.88 - 0.012 * (1 - abs(x) / 0.48)
        pts.append(c + (ex * x + ey * y) * R)
    pts = [pts[i] for i in range(n)]
    # oval section (thicker front-to-back), drawn as a ring of rings
    rings = []
    for i in range(n):
        p0, p1 = pts[i - 1], pts[(i + 1) % n]
        t = (p1 - p0).normalized()
        radial = (pts[i] - c)
        radial = (radial - nz * radial.dot(nz)).normalized()
        grip = 1.0 + 0.12 * (abs(radial.dot(ex)) ** 6)
        ring = []
        for k in range(8):
            a = 2 * math.pi * (k + 0.5) / 8
            ring.append(pts[i] + radial * (0.0145 * grip * math.cos(a)) + nz * (0.0175 * grip * math.sin(a)))
        rings.append(ring)
    rings.append(rings[0])
    loft(bm, rings, closed=True, mat_fn=lambda i, j: SATIN)
    # 12 o'clock cream marker
    k12 = n // 4
    seg_pts = [pts[k] for k in (k12 - 1, k12, k12 + 1)]
    for sgn in (1,):
        mk = [p + (p - c).normalized() * 0.0148 for p in seg_pts]
        ribbon(bm, mk, [nz] * 3, 0.028, STITCH, out=ey)
    # spokes: two horizontal blades and a lower one, satin with a polished inlay
    def spoke(direction, w0, w1, z_off):
        rs = []
        for f in (0.0, 0.33, 0.66, 1.0):
            rr = 0.045 + (R - 0.004 - 0.045) * f
            w = w0 + (w1 - w0) * f
            o = c + direction * rr + nz * (z_off * (1 - f))
            side = nz.cross(direction).normalized()
            q = []
            for k in range(8):
                a = 2 * math.pi * (k + 0.5) / 8
                q.append(o + side * (w / 2 * math.copysign(abs(math.cos(a)) ** 0.5, math.cos(a)))
                         + nz * (0.009 * math.copysign(abs(math.sin(a)) ** 0.5, math.sin(a))))
            rs.append(q)
        loft(bm, rs, closed=True, mat_fn=lambda i, j: SATIN)
        a = c + direction * 0.06 + nz * (0.0095 + z_off * 0.7)
        b = c + direction * (R - 0.03) + nz * 0.0095
        ribbon(bm, [a, b], [nz.cross(direction).normalized()] * 2, 0.006, STEEL, out=nz)
    spoke(ex, 0.050, 0.030, 0.012)
    spoke(-ex, 0.050, 0.030, 0.012)
    spoke((-ey * 0.97 + ex * 0.0).normalized(), 0.050, 0.036, 0.012)
    # centre pad
    from mathutils import Matrix
    Rm = Matrix(np.array([ex, ey, nz]).T.tolist())
    rbox(bm, (0.125, 0.092, 0.040), 0.016, c + nz * 0.012, seg=2, mat=SATIN, rot=Rm, crown={"+z": 0.006})
    rbox(bm, (0.040, 0.010, 0.004), 0.002, c + nz * 0.035 - ey * 0.02, seg=1, mat=STEEL, rot=Rm)
    # column shroud + stalks
    rs = []
    for f, (w, h) in zip((0.0, 0.5, 1.0), ((0.07, 0.06), (0.085, 0.072), (0.10, 0.085))):
        o = c - nz * (0.03 + 0.20 * f) - ey * 0.01
        q = []
        for k in range(10):
            a = 2 * math.pi * (k + 0.5) / 10
            q.append(o + ex * (w / 2 * math.cos(a)) + ey * (h / 2 * math.sin(a)))
        rs.append(q)
    loft(bm, rs, closed=True, mat_fn=lambda i, j: SATIN, cap0=SATIN)
    for sx in (1, -1):
        a = c - nz * 0.07 + ex * (sx * 0.035)
        b = a + ex * (sx * 0.09) + ey * 0.015 + nz * 0.01
        tube(bm, [a, b], 0.006, sides=6, mat=SATIN)


# -------------------------------------------------------------- console

def _console(bm, M):
    DARK, LEA, SATIN, WOOD, GLOSS, STEEL, STITCH = (M["dark"], M["lea"], M["satin"], M["wood"], M["gloss"],
                                                    M["steel"], M["stitch"])
    # body: rounded section lofted along y; the top rises to meet the dash at the front
    ys = [-0.43, -0.40, -0.34, -0.25, -0.12, 0.0, 0.12, 0.24, 0.36, 0.40]
    rings = []
    for y in ys:
        ztop = 0.585 + 0.05 * _sm(-0.22, -0.42, y)
        hw = 0.118 if y < 0.38 else 0.105
        r = 0.03
        q = []
        for k in range(14):
            a = 2 * math.pi * k / 14
            cx, cz = math.cos(a), math.sin(a)
            x = hw * math.copysign(abs(cx) ** 0.25, cx)
            zmid = (ztop + 0.30) / 2
            hz = (ztop - 0.30) / 2
            z = zmid + hz * math.copysign(abs(cz) ** 0.25, cz)
            q.append(Vector((x, y, z)))
        rings.append(q)
    loft(bm, rings, closed=True, mat_fn=lambda i, j: SATIN, cap0=SATIN, cap1=SATIN)
    # walnut top plate (front part) and leather armrest lid (rear part)
    rbox(bm, (0.205, 0.40, 0.012), 0.004, (0, -0.19, 0.588), seg=1, mat=WOOD)
    # cupholders: steel rims and dark wells
    for cx in (-0.048, 0.048):
        cc = Vector((cx, -0.08, 0.596))
        rim = [cc + Vector((0.036 * math.cos(2 * math.pi * k / 16), 0.036 * math.sin(2 * math.pi * k / 16), 0)) for k in range(16)]
        tube(bm, rim, 0.0035, sides=3, mat=STEEL, closed=True)
        disc = [bm.verts.new(cc + Vector((0.034 * math.cos(2 * math.pi * k / 16), 0.034 * math.sin(2 * math.pi * k / 16), -0.002))) for k in range(16)]
        orient([_face(bm, disc, GLOSS, smooth=False)], (0, 0, 1))
    # wireless pad and rotary selector
    rbox(bm, (0.12, 0.15, 0.006), 0.012, (0, -0.28, 0.596), seg=1, mat=GLOSS)
    selc = Vector((0.0, -0.185, 0.594))
    ring = [selc + Vector((0.022 * math.cos(2 * math.pi * k / 16), 0.022 * math.sin(2 * math.pi * k / 16), 0)) for k in range(16)]
    rings = [[p + Vector((0, 0, dz)) for p in ring] for dz in (0.0, 0.022)]
    rings.append([selc + (p - selc) * 0.85 + Vector((0, 0, 0.026)) for p in ring])
    loft(bm, rings, closed=True, mat_fn=lambda i, j: STEEL, cap1=STEEL)
    # armrest lid
    rbox(bm, (0.215, 0.34, 0.055), 0.020, (0, 0.20, 0.612), seg=1, mat=LEA)
    pts = [Vector((x, 0.20 - 0.14, 0.6402)) for x in np.linspace(-0.08, 0.08, 6)]
    ribbon(bm, pts, [Vector((0, 1, 0))] * len(pts), 0.003, STITCH)
    for sx in (-1, 1):
        pts = [Vector((sx * 0.08, y, 0.6402)) for y in np.linspace(0.06, 0.34, 6)]
        ribbon(bm, pts, [Vector((1, 0, 0))] * len(pts), 0.003, STITCH)
    # rear face vents for the back seats
    for sx in (-1, 1):
        rbox(bm, (0.075, 0.010, 0.035), 0.006, (sx * 0.05, 0.402, 0.50), seg=1, mat=GLOSS)
        for dz in (-0.008, 0.0, 0.008):
            rbox(bm, (0.065, 0.004, 0.002), 0.0, (sx * 0.05, 0.408, 0.50 + dz), seg=0, mat=STEEL)


# -------------------------------------------------------------- door cards

def _door_cards(bm, M, p, body):
    DARK, LEA, SATIN, WOOD, GLOSS, STEEL, STITCH = (M["dark"], M["lea"], M["satin"], M["wood"], M["gloss"],
                                                    M["steel"], M["stitch"])

    def wall(y):
        F = body.frame(body.s_of_y(y))
        t = F.top(0.05)
        return t.x, t.z
    # (inward offset, height relative to belt, material); top -> bottom
    def prof(belt, arm):
        a = arm
        return [(0.0, belt + 0.004, WOOD), (0.012, belt - 0.004, WOOD), (0.018, belt - 0.022, LEA),
                (0.020, belt - 0.075, LEA), (0.024, 0.69, LEA),
                (0.028 + 0.004 * a, 0.672, LEA), (0.028 + 0.050 * a, 0.668, LEA), (0.030 + 0.064 * a, 0.655, LEA),
                (0.030 + 0.062 * a, 0.636, DARK), (0.030 + 0.035 * a, 0.622, DARK), (0.028, 0.60, DARK),
                (0.030, 0.37, DARK), (0.0, 0.305, DARK)]
    doors = [(-0.70, 0.275, (-0.30, 0.22)), (0.325, 1.02, (0.58, 0.98)), (1.06, 1.42, (1.08, 1.30))]
    for sx in (1, -1):
        for y0, y1, (a0, a1) in doors:
            nk = 9 if y1 - y0 > 0.5 else 5
            ys = [y0 + (y1 - y0) * k / nk for k in range(nk + 1)]
            rings = []
            for y in ys:
                xw, zb = wall(y)
                arm = _sm(a0 - 0.05, a0 + 0.06, y) * (1 - _sm(a1 - 0.06, a1 + 0.02, y))
                taper = _sm(y0, y0 + 0.035, y) * (1 - _sm(y1 - 0.035, y1, y))
                pr = prof(zb, arm)
                rings.append([Vector((sx * (xw - 0.002 - off * (0.3 + 0.7 * taper)), y, z)) for off, z, _ in pr])
            mats = [m for _, _, m in prof(0.88, 1.0)]
            loft(bm, rings, closed=False, mat_fn=lambda i, j, mats=mats: mats[j], out=(-sx, 0, 0))
            # piping on the armrest's outer edge, cream stitch on its top
            pts, pts2 = [], []
            for y in ys[1:-1]:
                arm = _sm(a0 - 0.05, a0 + 0.06, y) * (1 - _sm(a1 - 0.06, a1 + 0.02, y))
                if arm < 0.5:
                    continue
                xw, zb = wall(y)
                pts.append(Vector((sx * (xw - 0.002 - (0.030 + 0.066 * arm)), y, 0.646)))
                pts2.append(Vector((sx * (xw - 0.002 - (0.028 + 0.030 * arm)), y, 0.6715)))
            if len(pts) > 1:
                tube(bm, pts, 0.0038, sides=4, mat=LEA)
                ribbon(bm, pts2, [Vector((1, 0, 0))] * len(pts2), 0.003, STITCH)
            # walnut inlay line under the cap
            pts = [Vector((sx * (wall(y)[0] - 0.002 - 0.0195), y, wall(y)[1] - 0.045)) for y in ys[1:-1]]
            ribbon(bm, pts, [Vector((0, 0, 1))] * len(pts), 0.018, WOOD, out=(-sx, 0, 0))
            if y1 - y0 < 0.5:
                continue
            # door pull + release, window switches, speaker
            xw, zb = wall(y0 + 0.16)
            xin = sx * (xw - 0.026)
            c = Vector((xin - sx * 0.004, y0 + 0.16, zb - 0.11))
            rbox(bm, (0.012, 0.10, 0.03), 0.006, c, seg=1, mat=GLOSS)
            tube(bm, [c + Vector((-sx * 0.006, -0.04, 0)), c + Vector((-sx * 0.012, 0.0, 0)), c + Vector((-sx * 0.006, 0.04, 0))],
                 0.005, sides=6, mat=STEEL)
            if a1 - a0 > 0.3:
                xa, _ = wall(a0 + 0.10)
                sw = Vector((sx * (xa - 0.002 - 0.062), a0 + 0.10, 0.668))
                rbox(bm, (0.04, 0.10, 0.008), 0.004, sw, seg=1, mat=GLOSS)
                for k in range(2):
                    rbox(bm, (0.014, 0.022, 0.006), 0.0, sw + Vector((0, -0.025 + 0.05 * k, 0.005)), seg=0, mat=STEEL)
            xs_, _ = wall(y0 + 0.22)
            sc = Vector((sx * (xs_ - 0.002 - 0.031), y0 + 0.22, 0.43))
            ring = [sc + Vector((0, 0.065 * math.cos(2 * math.pi * k / 16), 0.065 * math.sin(2 * math.pi * k / 16))) for k in range(16)]
            tube(bm, ring, 0.004, sides=3, mat=STEEL, closed=True)
            disc = [bm.verts.new(sc + Vector((-sx * 0.001, 0.062 * math.cos(2 * math.pi * k / 16), 0.062 * math.sin(2 * math.pi * k / 16)))) for k in range(16)]
            orient([_face(bm, disc, SATIN, smooth=False)], (-sx, 0, 0))


# ---------------------------------------------------------- floor and bits

def _floor_bits(bm, M, p):
    DARK, LEA, SATIN, GLOSS, STEEL = M["dark"], M["lea"], M["satin"], M["gloss"], M["steel"]
    fz = p["floor_z"]
    mats = [((0.44, -0.40), (0.50, 0.56)), ((-0.44, -0.40), (0.50, 0.56)),
            ((0.42, 0.565), (0.46, 0.22)), ((-0.42, 0.565), (0.46, 0.22))]
    for (cx, cy), (w, d) in mats:
        rbox(bm, (w, d, 0.012), 0.0, (cx, cy, fz + 0.006), seg=0, mat=DARK)
        loop = common.fillet_polyline([(cx - w / 2, cy - d / 2, fz + 0.009), (cx + w / 2, cy - d / 2, fz + 0.009),
                                       (cx + w / 2, cy + d / 2, fz + 0.009), (cx - w / 2, cy + d / 2, fz + 0.009)],
                                      0.04, segments=2, closed=True)
        tube(bm, loop, 0.0055, sides=4, mat=LEA, closed=True, flat=0.7)
    # pedals (driver)
    for px, w, h in ((0.47, 0.05, 0.09), (0.36, 0.10, 0.07)):
        from mathutils import Matrix
        rot = Matrix.Rotation(math.radians(-55), 3, "X")
        rbox(bm, (w, h, 0.012), 0.0, (px, -0.62, 0.40), seg=0, mat=SATIN, rot=rot)
        rbox(bm, (w - 0.01, h - 0.012, 0.004), 0.0, (px, -0.62 + 0.006, 0.40 + 0.004), seg=0, mat=STEEL, rot=rot)
    # rear-view camera mirror under the windscreen header
    rbox(bm, (0.23, 0.03, 0.05), 0.012, (0.0, -0.28, 1.095), seg=1, mat=GLOSS)
    rbox(bm, (0.21, 0.004, 0.04), 0.008, (0.0, -0.264, 1.095), seg=1, mat=M["screen_dark"])
    tube(bm, [Vector((0, -0.29, 1.11)), Vector((0, -0.305, 1.152))], 0.008, sides=6, mat=GLOSS)
    # seat belts: B-pillar to the front seats, C-pillar to the rear ones, D-rings at the top
    belts = [((0.695, 0.33, 1.05), (0.66, 0.36, 0.86), (0.67, 0.37, 0.47)),
             ((0.685, 1.33, 1.03), (0.65, 1.25, 0.80), (0.62, 1.17, 0.46))]
    for a, b, c in belts:
        for sx in (1, -1):
            pts = [Vector((sx * a[0], a[1], a[2])), Vector((sx * b[0], b[1], b[2])), Vector((sx * c[0], c[1], c[2]))]
            ribbon(bm, pts, [Vector((0, 1, 0))] * 3, 0.045, SATIN, out=(-sx, 0, 0))
            rbox(bm, (0.008, 0.05, 0.016), 0.0, (sx * (a[0] + 0.004), a[1], a[2] + 0.012), seg=0, mat=GLOSS)
    # buckles inboard of each seat
    for bx, by in ((0.17, 0.38), (-0.17, 0.38), (0.13, 1.16), (-0.13, 1.16), (0.60, 1.16), (-0.60, 1.16)):
        rbox(bm, (0.022, 0.035, 0.07), 0.0, (bx, by, 0.50), seg=0, mat=SATIN)
        rbox(bm, (0.018, 0.02, 0.02), 0.0, (bx, by - 0.004, 0.545), seg=0, mat=STEEL)


# ------------------------------------------------------------------ build

def build(p, body, col, root, n, mats):
    """Create the cabin parts (separate objects; car_ev merges them)."""
    names = ["lea", "dark", "satin", "wood", "gloss", "steel", "stitch", "screen", "shell", "screen_dark"]
    order = [mats[k] for k in names]
    M = {k: i for i, k in enumerate(names)}
    tile = {}

    def part(tag, fn, *args, uv=0.2):
        bm = bmesh.new()
        ORIENT.clear()
        fn(bm, M, *args)
        fixed = set()
        for faces, _ in ORIENT:
            fixed.update(faces)
        bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces if f not in fixed])
        for faces, out in ORIENT:
            s = 0.0
            for f in faces:
                f.normal_update()
                s += f.normal.dot(out) * f.calc_area()
            if s < 0:
                bmesh.ops.reverse_faces(bm, faces=faces)
        ORIENT.clear()
        ob = new_obj(f"{n}_{tag}", bm, order, col, root, sharp=50, recalc=False)
        common.box_uv(ob, tile=1.0)
        tiles = {M["wood"]: 0.5, M["lea"]: 0.2, M["dark"]: 0.25}
        uvl = ob.data.uv_layers["UVMap"]
        for poly in ob.data.polygons:
            k = 1.0 / tiles.get(poly.material_index, uv)
            for li in poly.loop_indices:
                uvl.data[li].uv = uvl.data[li].uv * k
        return ob

    def seats(bm, M):
        _seat(bm, M, 0.40, (-0.115, 0.505))
        _seat(bm, M, -0.40, (-0.115, 0.505))
        _seat(bm, M, 0.365, (0.69, 0.475), rear_seat=True)
        _seat(bm, M, -0.365, (0.69, 0.475), rear_seat=True)
        _seat(bm, M, 0.0, (0.72, 0.47), centre=True)
    part("Seats", seats)
    part("Dash", lambda bm, M: _dash(bm, M, p, body))

    def screens(bm, M):
        # cluster behind the wheel: rows 0..380 of the atlas (v from 1 - 380/1024 to 1)
        _screen(bm, M, (0.40, -0.535, 0.905), 0.30, 0.111, 28, (0.0, 1 - 380 / 1024, 1.0, 1.0))
        # centre display: rows 392..1024 (v 0 .. 632/1024)
        _screen(bm, M, (0.0, -0.455, 0.948), 0.34, 0.21, 26, (0.0, 0.0, 1.0, 632 / 1024),
                stem_to=(0.0, -0.49, 0.85))
    ob = part("Screens", screens)
    # keep the screen UVs exact (box_uv would overwrite them): redo the lit faces
    _fix_screen_uv(ob, M["screen"])
    part("Wheel", _wheel)
    part("Console", _console)
    part("DoorCards", lambda bm, M: _door_cards(bm, M, p, body))
    part("Floor", lambda bm, M: _floor_bits(bm, M, p))


def _fix_screen_uv(ob, mat_index):
    """box_uv rewrote every UV; map the lit screen faces to their atlas rects (from
    their own geometry: u along +x, v up the screen)."""
    me = ob.data
    uv = me.uv_layers["UVMap"]
    for poly in me.polygons:
        if poly.material_index != mat_index:
            continue
        cen = poly.center
        u0, v0, u1, v1 = (0.0, 1 - 380 / 1024, 1.0, 1.0) if cen.x > 0.2 else (0.0, 0.0, 1.0, 632 / 1024)
        nrm = poly.normal
        ey = nrm.cross(Vector((1, 0, 0))).normalized()
        if ey.z < 0:
            ey = -ey
        cos = [me.vertices[me.loops[li].vertex_index].co for li in poly.loop_indices]
        xs = [c.x for c in cos]
        vs = [c.dot(ey) for c in cos]
        for li, c in zip(poly.loop_indices, cos):
            uu = (max(xs) - c.x) / (max(xs) - min(xs))      # the occupants look along -y: +x is their left
            vv = (c.dot(ey) - min(vs)) / (max(vs) - min(vs))
            uv.data[li].uv = (u0 + (u1 - u0) * uu, v0 + (v1 - v0) * vv)
