"""Procedural hands for the Grimble (blender/assets/grimble.py).

The sculpt's hands were blobs fused to the staff. Each hand is rebuilt on its grip:
a palm / back of the hand against the staff on the side the arm comes from, a
wrist running back into the sleeve, four long thin fingers that ride the staff's
actual surface round its front (knuckle bulges at the joints, tapering), a thumb
wrapping the other way above them, and a dark curved claw at every tip.

Skin: tube UVs (u around, v along, one unit = P['hand_tile'] metres) for a
tileable leathery texture; claws: their own dark, glossier material (index 1).
"""
import math

import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def _frames(pts):
    """Parallel-transport frames (T, N, B) along a polyline."""
    T = np.gradient(pts, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    ref = np.array([0, 0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([1.0, 0, 0])
    N = np.zeros_like(T)
    N[0] = np.cross(T[0], ref)
    N[0] /= np.linalg.norm(N[0])
    for i in range(1, len(T)):
        v = N[i - 1] - (N[i - 1] @ T[i]) * T[i]
        N[i] = v / (np.linalg.norm(v) + 1e-12)
    return T, N, np.cross(T, N)


def tube(bm, uvl, pts, radii, sides, tile, mat=0, cap_end=True, cap_start=False, phase=0.0):
    """Sweep a round profile of varying radius along pts into bm (quads + fan caps)."""
    pts = np.asarray(pts, float)
    T, N, B = _frames(pts)
    th = np.linspace(0, 2 * math.pi, sides, endpoint=False) + phase
    rings = [[bm.verts.new(tuple(pts[i] + radii[i] * (math.cos(a) * N[i] + math.sin(a) * B[i]))) for a in th]
             for i in range(len(pts))]
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    circ = 2 * math.pi * float(np.mean(radii))
    for i in range(len(pts) - 1):
        for j in range(sides):
            j2 = (j + 1) % sides
            f = bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]))
            f.material_index = mat
            u0, u1 = j / sides * circ / tile, (j + 1) / sides * circ / tile
            for l, uv in zip(f.loops, ((u0, s[i] / tile), (u1, s[i] / tile), (u1, s[i + 1] / tile), (u0, s[i + 1] / tile))):
                l[uvl].uv = uv
    for idx, flip, on in ((0, True, cap_start), (len(pts) - 1, False, cap_end)):
        if not on:
            continue
        c = bm.verts.new(tuple(pts[idx] + (T[idx] * radii[idx] * 0.4 * (1 if not flip else -1))))
        for j in range(sides):
            a, b = rings[idx][j], rings[idx][(j + 1) % sides]
            f = bm.faces.new((c, b, a) if flip else (c, a, b))
            f.material_index = mat
            for l in f.loops:
                l[uvl].uv = (0.0, s[idx] / tile)


def ellipsoid(bm, uvl, centre, axes, radii, tile, segs=(14, 9), mat=0):
    """An ellipsoid (axes: 3 unit vectors, radii: their half lengths)."""
    nu, nv = segs
    verts = []
    for i in range(nv + 1):
        th = math.pi * i / nv
        row = []
        for j in range(nu):
            ph = 2 * math.pi * j / nu
            d = (math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th))
            p = centre + sum(axes[k] * radii[k] * d[k] for k in range(3))
            row.append(bm.verts.new(tuple(p)))
        verts.append(row)
    for i in range(nv):
        for j in range(nu):
            j2 = (j + 1) % nu
            q = (verts[i][j], verts[i][j2], verts[i + 1][j2], verts[i + 1][j])
            if i == 0:
                q = (verts[i][j], verts[i + 1][j2], verts[i + 1][j])
            elif i == nv - 1:
                q = (verts[i][j], verts[i][j2], verts[i + 1][j])
            try:
                f = bm.faces.new(q)
            except ValueError:
                continue
            f.material_index = mat
            for l in f.loops:
                co = np.array(l.vert.co) - centre
                l[uvl].uv = (math.atan2(co @ axes[1], co @ axes[0]) / (2 * math.pi) * 2 * math.pi * radii[1] / tile,
                             (co @ axes[2]) / tile)
    bmesh.ops.remove_doubles(bm, verts=[v for r in (verts[0], verts[-1]) for v in r], dist=1e-6)


def build_hands(bm, uvl, hands, line, sl, staff_tree, p):
    """hands: dicts with s (grip centre arc length), span, wrist (point in the sleeve),
    and line / sl: the staff's centre line and arc lengths."""
    rng = np.random.default_rng(p["hand_seed"])
    tile = p["hand_tile"]

    def axis_at(s):
        k = int(np.clip(np.searchsorted(sl, s), 1, len(sl) - 1))
        t = (s - sl[k - 1]) / max(sl[k] - sl[k - 1], 1e-9)
        pt = line[k - 1] * (1 - t) + line[k] * t
        tg = line[k] - line[k - 1]
        return pt, tg / np.linalg.norm(tg)

    def surf(s, d):
        """Distance from the staff's axis to its surface along d at arc length s."""
        pt, _ = axis_at(s)
        hit = staff_tree.ray_cast(Vector(pt.tolist()), Vector(d.tolist()), 0.6)
        return hit[3] if hit[0] is not None else p["staff_r"][1]

    def smooth01(a, b, x):
        t = min(max((x - a) / (b - a), 0.0), 1.0)
        return t * t * (3 - 2 * t)

    info = []
    for h in hands:
        v_start = len(bm.verts)
        G, T = axis_at(h["s"])
        A = h["wrist"] - G
        A -= (A @ T) * T
        A /= np.linalg.norm(A)                     # toward the wrist, across the staff
        Bp = np.cross(T, A)

        def rot(phi):
            return A * math.cos(phi) + Bp * math.sin(phi)

        F = np.array([0, -1.0, 0]) - T * (-T[1])   # toward the viewer
        phi_f = math.atan2(F @ Bp, F @ A)          # the front's angle from the wrist side
        sign = 1.0 if phi_f >= 0 else -1.0
        rf = p["finger_r"]
        pitch = 2 * rf * p["finger_gap"]           # finger spacing along the shaft (touching)
        n_f = 4
        top = h["s"] + 1.5 * pitch                  # index finger's arc length
        # the knuckle row: on the front, toward the wrist side, so the back of the hand faces
        # the viewer; the fingers wrap from there across the front and round the far side
        phi_k = phi_f * p["knuckle_angle"]
        # back of the hand: a broad, flattened pad from the knuckle row back to the wrist,
        # lying against the shaft on the viewer's / wrist side
        phi_b = phi_k * 0.35
        db = rot(phi_b)
        rb = surf(h["s"], db)
        w = np.asarray(h["wrist"], float)
        kn = G + db * (rb + rf * 1.2)
        ax1 = w - kn
        L1 = np.linalg.norm(ax1)
        ax1 /= L1
        ax3 = np.cross(ax1, T)
        ax3 /= np.linalg.norm(ax3)
        ax2 = np.cross(ax3, ax1)
        pc = kn + ax1 * (L1 * 0.32)
        ellipsoid(bm, uvl, pc, (ax1, ax2, ax3),
                  (L1 * 0.36 + rf * 1.5, n_f * pitch * 0.62, rf * 1.55), tile, segs=(18, 11))
        # wrist: a thick tube from inside the pad deep into the sleeve (its end is hidden)
        tube(bm, uvl, np.array([pc - ax1 * rf, (pc + w) / 2, w, w + ax1 * 0.45]),
             [rf * 2.6, rf * 2.4, rf * 2.6, rf * 2.8], 10, tile, cap_end=True)
        # fingers, index (top) to little finger; each is recorded for the rig (its centre
        # line, the inward direction at each sample, its tube's and claw's vertex ranges)
        fingers = []
        for k in range(n_f):
            a_k = top - k * pitch
            r_k = rf * (1.0 - 0.06 * k) * (1 + 0.04 * rng.standard_normal())
            wrap = math.radians(p["finger_wrap"] - 8 * k + 5 * rng.standard_normal())
            pts, rad, inward = [], [], []
            n = 24
            ts = np.linspace(-0.18, 1.0, n)
            for t in ts:
                phi = phi_k + sign * wrap * max(t, 0) + sign * wrap * 0.4 * min(t, 0)
                a = a_k - p["finger_slant"] * pitch * max(t, 0)
                d = rot(phi)
                # knobbly: fat joints, slim between them, taper only near the tip
                rt = r_k * (1 - 0.38 * smooth01(0.72, 1.0, t))
                rt *= 1 + sum(amp * math.exp(-((t - kt) / 0.06) ** 2)
                              for kt, amp in ((0.0, 0.32), (0.38, 0.26), (0.68, 0.2)))
                rt *= 1 - 0.07 * sum(math.exp(-((t - kt) / 0.07) ** 2) for kt in (0.19, 0.53))
                lift = 0.0 if t >= 0 else -t * rf * 2.2       # the roots rise into the hand's back
                pt_, _ = axis_at(a)
                pts.append(pt_ + d * (surf(a, d) + rt * 0.8 + lift))
                rad.append(rt)
                inward.append(-d)
            v0 = len(bm.verts)
            tube(bm, uvl, np.array(pts), rad, 8, tile, cap_end=True, phase=0.3 * k)
            v1 = len(bm.verts)
            _claw(bm, uvl, np.array(pts), rad[-1], d, tile, p)
            fingers.append(dict(name=("Index", "Middle", "Ring", "Pinky")[k], ts=ts, pts=np.array(pts),
                                inward=np.array(inward), joints=(0.0, 0.38, 0.68, 1.0), sides=8,
                                tube=(v0, v1), claw=(v1, len(bm.verts))))
        # thumb: from the hand's back up over the index finger, pressing along the shaft
        pts, rad, inward = [], [], []
        ts = np.linspace(-0.2, 1.0, 14)
        for t in ts:
            phi = phi_k * (0.55 + 0.25 * max(t, 0)) - sign * math.radians(p["thumb_wrap"]) * max(t, 0)
            a = top + pitch * (0.2 + 1.9 * max(t, 0)) - (0.0 if t >= 0 else -t * pitch)
            d = rot(phi)
            rt = rf * 1.2 * (1 - 0.35 * smooth01(0.7, 1.0, t)) * (1 + 0.28 * math.exp(-((t - 0.45) / 0.08) ** 2))
            lift = 0.0 if t >= 0 else -t * rf * 2.5
            pt_, _ = axis_at(a)
            pts.append(pt_ + d * (surf(a, d) + rt * 0.8 + lift))
            rad.append(rt)
            inward.append(-d)
        v0 = len(bm.verts)
        tube(bm, uvl, np.array(pts), rad, 8, tile, cap_end=True)
        v1 = len(bm.verts)
        _claw(bm, uvl, np.array(pts), rad[-1], d, tile, p)
        fingers.append(dict(name="Thumb", ts=ts, pts=np.array(pts), inward=np.array(inward),
                            joints=(0.0, 0.42, 0.72, 1.0), sides=8, tube=(v0, v1), claw=(v1, len(bm.verts))))
        info.append(dict(verts=(v_start, len(bm.verts)), wrist=w.copy(), pad=pc.copy(), grip=G.copy(),
                         axis=T.copy(), knuckle_dir=db.copy(), s=h["s"], fingers=fingers))
    return info


def _claw(bm, uvl, finger, r_tip, radial, tile, p):
    """A short, thick dark claw growing out of the fingertip's top and curling over it,
    down toward the staff (radial: outward from the staff at the tip)."""
    tg = finger[-1] - finger[-3]
    tg /= np.linalg.norm(tg)
    out = radial - (radial @ tg) * tg
    out /= np.linalg.norm(out) + 1e-9
    base = finger[-1] - tg * r_tip * 0.6 + out * r_tip * 0.35
    L = p["claw_len"]
    pts, rad = [], []
    for t in np.linspace(0, 1, 7):
        ang = t * math.radians(110)                 # curls over the tip
        pts.append(base + tg * (L * 0.55 * math.sin(ang)) + out * (L * 0.55 * (1 - math.cos(ang)) * -0.6
                                                                  + L * 0.25 * math.sin(ang)))
        rad.append(r_tip * 0.62 * (1 - t) ** 1.1 + 0.003)
    tube(bm, uvl, np.array(pts), rad, 7, tile, mat=1, cap_end=True)
