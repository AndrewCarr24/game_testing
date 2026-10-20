"""The hood's front edge for the Grimble (blender/assets/grimble.py): a soft, rolled,
frayed wool hem framing the face, replacing the scan's torn rim shards.

Works in the face's view (U, V across the face, W toward the viewer, from a point
inside the head), which is how the player sees it:
1. the face's outline: per angle around the face, its outer radius in (U, V);
2. the opening: that outline plus a margin, with a gently irregular wavy line;
3. the cloak faces inside the opening and in front of the face's edge (the torn
   shards) are deleted;
4. a folded-hem profile is swept along the opening at the depth of the hood surface
   there: a rounded lip toward the face, a tail lying back on the hood;
5. a dark strip (lining) closes the hood's inside between the face's edge and the lip;
6. a fringe of short tapered strand clusters hangs off the lip.
Returns per-triangle materials: 0 = the cloak's weave, 1 = the dark lining.
"""
import math

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def _lowpass(n, rng, k_max=7):
    t = np.linspace(0, 1, n)
    out = np.zeros(n)
    for k in range(1, k_max + 1):
        out += rng.standard_normal() / k * np.sin(2 * math.pi * (k * t + rng.random()))
    return out / (np.abs(out).max() + 1e-9)


def _circ_smooth(x, w=4):
    k = np.exp(-np.linspace(-2, 2, 2 * w + 1) ** 2)
    k /= k.sum()
    return np.convolve(np.r_[x[-w:], x, x[:w]], k, mode="valid")


def build(body, cloak, frame, p, rng):
    from grimble import _mesh_arrays

    c, a, b, f = frame
    bv, bt = _mesh_arrays(body.data)
    cv, ct = _mesh_arrays(cloak.data)

    def uvw(x):
        d = x - c
        return d @ a, d @ b, d @ f

    # 1. the face's outline (front part of the body above the neck)
    U, V, W = uvw(bv)
    front = (W > p["rim_face_w"]) & (bv[:, 2] > 4.3)
    ang = np.arctan2(U, V)                        # 0 = up, + toward a (the creature's left)
    rad = np.hypot(U, V)
    nb = p["rim_bins"]
    edges = np.linspace(-math.pi, math.pi, nb + 1)
    R_face = np.full(nb, np.nan)
    W_face = np.full(nb, np.nan)
    for i in range(nb):
        m = front & (ang >= edges[i]) & (ang < edges[i + 1])
        if m.sum() > 3:
            j = np.argsort(rad[m])[-max(3, m.sum() // 30):]
            R_face[i] = rad[m][j].mean()
            W_face[i] = W[m][j].mean()
    ok = ~np.isnan(R_face)
    idx = np.arange(nb)
    R_face = _circ_smooth(np.interp(idx, idx[ok], R_face[ok], period=nb))
    W_face = _circ_smooth(np.interp(idx, idx[ok], W_face[ok], period=nb))
    angc = (edges[:-1] + edges[1:]) / 2

    # 2. the opening
    n = p["rim_segments"]
    amax = math.radians(p["rim_phi_max"])
    angs = np.linspace(-amax, amax, n)
    wave = _lowpass(n, rng)
    thick = _lowpass(n, rng)
    Rf = np.interp(angs, angc, R_face, period=2 * math.pi)
    Wf = np.interp(angs, angc, W_face, period=2 * math.pi)
    Rc = Rf + p["rim_margin"] + p["rim_wave"] * wave

    # 3. the rim's centre line: just outside the face's edge, at the depth of the hood
    #    surface beside it or the face's edge, whichever is nearer the viewer
    full = BVHTree.FromPolygons([tuple(x) for x in cv], [tuple(t) for t in ct], all_triangles=True)
    pts, T2, Wr = [], [], []
    for k in range(n):
        dir2 = math.sin(angs[k]) * a + math.cos(angs[k]) * b      # outward in the face plane
        q = c + dir2 * (Rc[k] + 0.1)
        h = full.ray_cast(Vector((q + f * 4.0).tolist()), Vector((-f).tolist()), 8.0)
        wh = (h[0] - Vector(c.tolist())).dot(Vector(f.tolist())) if h[0] is not None else Wf[k]
        w = min(max(wh, Wf[k]), Wf[k] + 0.3) + p["rim_lift"]
        Wr.append(w)
        pts.append(c + dir2 * Rc[k] + f * w)
        T2.append(dir2)
    Wr = np.array(Wr)
    # 4. delete the shards: cloak faces inside the opening in front of the face's edge, and
    #    the hood's torn flaps around it that stand in front of the rim
    fc = cv[ct].mean(1)
    Uc, Vc, Wc = uvw(fc)
    angf = np.arctan2(Uc, Vc)
    radf = np.hypot(Uc, Vc)
    Rc_f = np.interp(angf, angs, Rc, left=np.nan, right=np.nan)
    Wf_f = np.interp(angf, angs, Wf, left=np.nan, right=np.nan)
    Wr_f = np.interp(angf, angs, Wr, left=np.nan, right=np.nan)
    inside = (radf < Rc_f + p["rim_cut"]) & (Wc > Wf_f - p["rim_depth"])
    flaps = (radf < Rc_f + p["rim_cut_out"]) & (Wc > Wr_f - p["rim_radius"] * 1.2)
    band = ~np.isnan(Rc_f) & (inside | flaps) & (fc[:, 2] > 4.0)
    pts = np.array(pts)
    T2 = np.array(T2)
    for _ in range(4):
        pts[1:-1] = 0.5 * pts[1:-1] + 0.25 * (pts[:-2] + pts[2:])
    N = np.tile(f, (n, 1))                        # toward the viewer

    # the hem profile in (t = outward along the hood, y = toward the viewer), x radius
    prof = [(math.cos(t), math.sin(t)) for t in np.linspace(math.pi * 0.5, math.pi * 1.5, 7)]
    prof += [(0.6, -1.0), (1.6, -0.8), (2.8, -0.4), (2.8, 0.1), (1.6, 0.55), (0.6, 0.95)]
    prof = np.array(prof)
    m = len(prof)
    R0 = p["rim_radius"]
    s_acc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    tile = p["cloak_tile"]
    verts, uvs, inner = [], [], []
    for i in range(n):
        taper = min(1.0, (i + 1) / 6, (n - i) / 6)
        r = R0 * (1 + p["rim_thick_var"] * thick[i]) * (0.35 + 0.65 * taper)
        sink = (1 - taper) * R0 * 1.5
        for j, (x, y) in enumerate(prof):
            verts.append(pts[i] + T2[i] * (x * r) + N[i] * (y * r - sink))
            uvs.append((s_acc[i] / tile, j / m * 2 * math.pi * R0 * 1.6 / tile))
            inner.append(x < -0.3)
    verts = np.array(verts)
    tris = []
    for i in range(n - 1):
        for j in range(m):
            j2 = (j + 1) % m
            a0, a1, b0, b1 = i * m + j, i * m + j2, (i + 1) * m + j, (i + 1) * m + j2
            tris += [(a0, b0, b1), (a0, b1, a1)]
    for i, flip in ((0, True), (n - 1, False)):
        ci = len(verts)
        verts = np.vstack([verts, verts[i * m:(i + 1) * m].mean(0)])
        uvs.append((s_acc[i] / tile, 0.0))
        inner.append(False)
        for j in range(m):
            j2 = (j + 1) % m
            tris.append((ci, i * m + j2, i * m + j) if flip else (ci, i * m + j, i * m + j2))
    tris = np.array(tris)
    # outward: the middle ring's faces point away from its centre
    mid = (n // 2) * m
    ring_c = verts[mid:mid + m].mean(0)
    sel = np.nonzero((tris[:, 0] >= mid) & (tris[:, 0] < mid + m))[0]
    fn = np.cross(verts[tris[sel, 1]] - verts[tris[sel, 0]], verts[tris[sel, 2]] - verts[tris[sel, 0]])
    if ((fn * (verts[tris[sel]].mean(1) - ring_c)).sum(1) < 0).mean() > 0.5:
        tris = tris[:, ::-1]
    mats = [0] * len(tris)

    # 5. the hood's dark inside: from just behind the face's edge to under the lip
    o = len(verts)
    rows = 4
    strip = []
    for rr in range(rows):
        w_ = rr / (rows - 1)
        for i in range(n):
            inner_p = c + T2[i] * (Rf[i] - 0.03) + f * (Wf[i] - 0.06)
            lip = pts[i] + T2[i] * (-0.6 * R0) + N[i] * (-0.6 * R0)
            q = inner_p * (1 - w_) + lip * w_ - f * 0.08 * math.sin(math.pi * w_)
            strip.append(q)
            uvs.append((s_acc[i] / tile, w_ * 0.3 / tile))
            inner.append(True)
    strip = np.array(strip)
    st = []
    for rr in range(rows - 1):
        for i in range(n - 1):
            a0, a1 = o + rr * n + i, o + rr * n + i + 1
            b0, b1 = o + (rr + 1) * n + i, o + (rr + 1) * n + i + 1
            st += [(a0, b0, b1), (a0, b1, a1)]
    st = np.array(st)
    allv = np.vstack([verts, strip])
    fn2 = np.cross(allv[st[:, 1]] - allv[st[:, 0]], allv[st[:, 2]] - allv[st[:, 0]])
    if (fn2 @ f).mean() < 0:
        st = st[:, ::-1]
    allt = np.vstack([tris, st])
    mats += [1] * len(st)

    # 6. the fringe: short tapered strands off the lip, toward the face, drooping
    fr_v, fr_t, k = [], [], 0
    for i in range(2, n - 2, p["rim_fringe_step"]):
        for _ in range(p["rim_fringe_per"]):
            r = R0 * (1 + p["rim_thick_var"] * thick[i])
            x, y = prof[rng.integers(1, 6)]
            base = pts[i] + T2[i] * (x * r) + N[i] * (y * r)
            L = p["rim_fringe_len"] * (0.5 + rng.random())
            dirn = -T2[i] * 0.8 + N[i] * rng.uniform(-0.2, 0.5) + rng.standard_normal(3) * 0.15
            dirn /= np.linalg.norm(dirn)
            tip = base + dirn * L + np.array([0, 0, -0.25 * L])
            wdt = 0.012 + 0.008 * rng.random()
            side = np.cross(dirn, f)
            side /= np.linalg.norm(side) + 1e-9
            up = np.cross(side, dirn)
            ob = len(allv) + len(fr_v)
            ring = [base + (side * math.cos(2 * math.pi * q / 3) + up * math.sin(2 * math.pi * q / 3)) * wdt
                    for q in range(3)]
            fr_v += ring + [tip]
            axis_p = (np.mean(ring, axis=0) + tip) / 2
            for q in range(3):
                tri = (ob + q, ob + (q + 1) % 3, ob + 3)
                P = [ring[q], ring[(q + 1) % 3], tip]
                if np.cross(P[1] - P[0], P[2] - P[0]) @ (np.mean(P, axis=0) - axis_p) < 0:
                    tri = (tri[0], tri[2], tri[1])
                fr_t.append(tri)
            for q in range(4):
                uvs.append((s_acc[i] / tile + 0.02 * q, 0.1))
                inner.append(False)
            k += 1
    if fr_v:
        allv = np.vstack([allv, np.array(fr_v)])
        allt = np.vstack([allt, np.array(fr_t)])
        mats += [0] * len(fr_t)
    return band, allv, allt, np.array(uvs), np.array(inner), k, np.array(mats)
