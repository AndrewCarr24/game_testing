"""Texture painting for the Grimble (blender/assets/grimble.py): numpy only.

body:  repaints the body's baked source colour using per-texel position / normal
       (fur, muzzle, nose, smile, eye rims, leathery hands, dark claws) and builds
       its normal map (baked sculpt detail + fur strands / skin wrinkles).
cloak: tileable coarse woven near-black wool (base colour + normal).
eye:   iris / pupil / sclera, planar-mapped onto the eyeball's front.
staff: tileable gnarled dark wood (base colour + normal), grain along v.
All saved through lib/textures._save as T_Grimble_*.
"""
import math
import os

import numpy as np

from lib import textures

VERSION = 15


def version():
    return VERSION


def body_names():
    return ("T_Grimble_Body_BaseColor", "T_Grimble_Body_Normal")


# ------------------------------------------------------------------ helpers

def srgb(lin):
    return textures._to_srgb(lin)


def lin(srgb_):
    s = np.clip(srgb_, 0, 1)
    return np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def noise2(n, lx, ly, beta, rng):
    """Periodic fractal noise in [-1, 1]; lx / ly: larger = longer features along
    x (columns) / y (rows)."""
    white = rng.standard_normal((n, n))
    ky = np.fft.fftfreq(n)[:, None] * n
    kx = np.fft.fftfreq(n)[None, :] * n
    k = np.sqrt((kx * lx) ** 2 + (ky * ly) ** 2)
    k[0, 0] = 1.0
    spec = np.fft.fft2(white) / k ** beta
    spec[0, 0] = 0
    out = np.real(np.fft.ifft2(spec))
    return out / (np.abs(out).max() + 1e-9)


def height_to_normal(h, strength):
    """Tangent-space normal map (OpenGL / glTF: green = +v) from a height field
    whose row 0 is the top of the image."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    nrm = np.stack([-dx, dy, np.ones_like(h)], axis=-1)
    return nrm / np.linalg.norm(nrm, axis=-1, keepdims=True)


def blend_normals(base, detail):
    """Whiteout blend of two unit tangent-space normals."""
    out = np.stack([base[..., 0] + detail[..., 0], base[..., 1] + detail[..., 1],
                    base[..., 2] * detail[..., 2]], axis=-1)
    return out / (np.linalg.norm(out, axis=-1, keepdims=True) + 1e-9)


def value_noise3(p, freq, seed=0):
    """Smooth 3D value noise in [-1, 1] at points p (..., 3), lattice spacing 1/freq."""
    q = p * freq
    i = np.floor(q).astype(np.int64)
    f = q - i
    u = f * f * (3 - 2 * f)

    def h(ix, iy, iz):
        x = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
        x = (x ^ (x >> 13)) * 1274126177
        x = x ^ (x >> 16)
        return (x & 0xFFFF).astype(np.float32) / 32767.5 - 1.0

    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (u[..., 0] if dx else 1 - u[..., 0]) * (u[..., 1] if dy else 1 - u[..., 1]) * \
                    (u[..., 2] if dz else 1 - u[..., 2])
                out = out + w * h(i[..., 0] + dx, i[..., 1] + dy, i[..., 2] + dz)
    return out


def fbm3(p, freq, octaves=4, gain=0.5, seed=0):
    out, amp, tot = 0, 1.0, 0
    for o in range(octaves):
        out = out + amp * value_noise3(p, freq * 2 ** o, seed + o)
        tot += amp
        amp *= gain
    return out / tot


def _path(name):
    return os.path.join(textures.TEX_DIR, name + ".png")


# --------------------------------------------------------------------- body

def _hash2(ix, iy, seed):
    x = (ix * 73856093) ^ (iy * 19349663) ^ (seed * 83492791)
    x = (x ^ (x >> 13)) * 1274126177
    x = x ^ (x >> 16)
    return (x & 0xFFFF).astype(np.float32) / 32767.5 - 1.0


def vnoise2(x, y, period, seed=0):
    """Smooth 2D value noise in [-1, 1], periodic in x with `period` cells."""
    ix, iy = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = x - ix, y - iy
    ux, uy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    x0, x1 = ix % period, (ix + 1) % period
    a = _hash2(x0, iy, seed) * (1 - ux) + _hash2(x1, iy, seed) * ux
    b = _hash2(x0, iy + 1, seed) * (1 - ux) + _hash2(x1, iy + 1, seed) * ux
    return a * (1 - uy) + b * uy


def box_blur(x, r):
    """Separable box blur of an (H, W[, C]) image (edges clamped)."""
    for ax in (0, 1):
        pad = [(r + 1, r) if i == ax else (0, 0) for i in range(x.ndim)]
        c = np.cumsum(np.pad(x, pad, mode="edge"), axis=ax)
        n = x.shape[ax]
        x = (np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=ax) -
             np.take(c, np.arange(0, n), axis=ax)) / (2 * r + 1)
    return x


def fur_strands(theta, rho, width, seg, seed):
    """Hair strands radiating along rho (log-radius), `width` in radians at unit
    radius equivalents: blends angular bands so strands keep a similar width."""
    out = np.zeros_like(theta)
    tot = np.zeros_like(theta)
    for i, K in enumerate((96, 192, 384, 768, 1536)):
        # band weight: centred where 2*pi*r/K ~ width (r = exp(rho))
        kr = 2 * np.pi * np.exp(rho) / width
        w = np.exp(-(np.log2(np.maximum(kr, 1e-3) / K)) ** 2 / 0.5)
        n1 = vnoise2(theta / (2 * np.pi) * K, rho / seg, K, seed + i)
        n2 = vnoise2(theta / (2 * np.pi) * K * 2, rho / (seg * 0.6), K * 2, seed + 10 + i)
        out += w * (0.65 * n1 + 0.35 * n2)
        tot += w
    return out / np.maximum(tot, 1e-6)


def nearest_distance(points, targets, cell):
    """Distance from each point to the nearest target, capped at `cell` (a hashed
    grid: only targets in the 27 neighbouring cells are tested)."""
    out = np.full(len(points), cell)
    key = lambda q: np.floor(q / cell).astype(np.int64)
    tk = key(targets)
    buckets = {}
    for i, k in enumerate(map(tuple, tk)):
        buckets.setdefault(k, []).append(i)
    pk = key(points)
    cells = {}
    for i, k in enumerate(map(tuple, pk)):
        cells.setdefault(k, []).append(i)
    for k, idx in cells.items():
        near = [j for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)
                for j in buckets.get((k[0] + dx, k[1] + dy, k[2] + dz), ())]
        if not near:
            continue
        idx = np.array(idx)
        d = np.linalg.norm(points[idx, None, :] - targets[near][None, :, :], axis=2).min(1)
        out[idx] = np.minimum(out[idx], d)
    return out


def fur_tufts(theta, rho, K, aspect, seed):
    """Overlapping tapered fur tufts on a staggered log-polar grid (theta around,
    rho = log radius along the flow): conformal, so tufts grow with the distance
    from the centre (short fur at the nose, long on the cheeks). Rows nearer the
    centre lie on top. Returns (shade ~0.4..1.25, height 0..1, tip 0..1)."""
    X = theta / (2 * np.pi) * K
    Y = rho / (aspect * 2 * np.pi / K)
    j = np.floor(Y).astype(np.int64)
    v = Y - j
    best_t = np.full(theta.shape, -1.0)
    best_u = np.zeros(theta.shape)
    best_r = np.zeros(theta.shape)
    for back in (1, 0):            # the row nearer the centre (back=1) is on top
        jj = j - back
        X2 = X + 0.5 * (jj % 2) + 0.35 * _hash2(jj, jj * 7 + 3, seed)
        i = np.floor(X2).astype(np.int64)
        u = X2 - i
        i = i % K
        rnd = _hash2(i, jj, seed + 1)
        u = u + 0.18 * _hash2(i, jj, seed + 5)          # break the rows' regularity
        length = 1.45 + 0.6 * (0.5 + 0.5 * _hash2(i, jj, seed + 6))
        t = (v + back) / length                     # 0 at the root, 1 at the tip
        bend = 0.12 * _hash2(i, jj, seed + 2) * t * t
        half = 0.62 * (1 - t ** 1.6)                # tapers to a point
        inside = (t < 1) & (np.abs(u - 0.5 - bend) < half) & (best_t < 0)
        best_t = np.where(inside, t, best_t)
        best_u = np.where(inside, (u - 0.5 - bend) / np.maximum(half, 1e-3), best_u)
        best_r = np.where(inside, rnd, best_r)
    have = best_t >= 0
    t = np.clip(best_t, 0, 1)
    across = 1 - best_u ** 2
    shade = np.where(have, (0.66 + 0.48 * t) * (0.75 + 0.25 * across) * (1 + 0.16 * best_r), 0.5)
    height = np.where(have, across * (0.4 + 0.6 * t), 0.0)
    return shade, height, np.where(have, smoothstep(0.55, 1.0, t), 0.0), np.where(have, best_r, 0.0)


def pull_push(img, mask):
    """Fill the texels outside `mask` with a smooth extension of the ones inside
    (pull-push pyramid), so nothing samples black: collapsed triangles and bilinear
    filtering at island edges get the colour around them."""
    levels = []
    c, w = img * mask[..., None], mask.astype(np.float32)
    while min(c.shape[:2]) > 1:
        levels.append((c, w))
        h2, w2 = c.shape[0] // 2, c.shape[1] // 2
        c = c[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2, -1).sum((1, 3))
        w = w[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2).sum((1, 3))
        nz = w > 0
        c[nz] /= w[nz][:, None]
        w = np.minimum(w, 1.0)
        c = c * w[..., None]
    up = c / np.maximum(w, 1e-6)[..., None]
    for c, w in reversed(levels):
        upx = np.repeat(np.repeat(up, 2, 0), 2, 1)[:c.shape[0], :c.shape[1]]
        cur = np.where((w > 0)[..., None], c / np.maximum(w, 1e-6)[..., None], 0)
        up = cur * np.minimum(w, 1)[..., None] + upx * (1 - np.minimum(w, 1))[..., None]
    return up


def paint_body(b, p, eyes, seam=None):
    """b: baked maps (H, W, 3; row 0 = top): albedo (linear, the sculpt's colour),
    tnormal (0..1, high-res detail), pos (m, source frame), nrm, cov (bool).
    Everything is painted from per-texel 3D position: the face in 'face space'
    (eyes at U = +-1, V = 0; one unit = half the eye spacing), hands and feet
    from 3D noise and curvature."""
    pos, nrm, alb = b["pos"], b["nrm"], b["albedo"]
    H, W, _ = pos.shape
    valid = np.linalg.norm(pos, axis=-1) > 1e-3
    src = srgb(alb)
    L_src = src @ np.array([0.2126, 0.7152, 0.0722])
    # curvature from the position map: cavity (fine, crevices) and convexity (coarse, tips)
    cw = b["cov"].astype(np.float32)[..., None]

    def nblur(x, r):          # blur inside the islands only (normalised by coverage)
        return box_blur(x * cw, r) / np.maximum(box_blur(cw, r), 1e-4)
    cav = ((nblur(pos, 8) - pos) * nrm).sum(-1) * cw[..., 0]
    conv = ((pos - nblur(pos, 28)) * nrm).sum(-1) * cw[..., 0]
    tn = b["tnormal"] * 2 - 1
    tn /= np.linalg.norm(tn, axis=-1, keepdims=True) + 1e-9
    # the high-res bake misfires on the sculpt's tiny folds (texels tilted far over
    # shade as dark specks): keep its gentle detail, flatten the outliers
    keep = smoothstep(0.55, 0.85, tn[..., 2])[..., None]
    tn = tn * keep + np.array([0.0, 0.0, 1.0]) * (1 - keep)
    # the bake is against the unsmoothed sculpt: where the low mesh was smoothed (the nose's
    # sides, the face) its broad tilts are a mismatch, not detail (the pale specular streak
    # beside the nose); keep only a third of it (the fur's own normals carry the detail)
    tn = tn * 0.33 + np.array([0.0, 0.0, 1.0]) * 0.67
    tn /= np.linalg.norm(tn, axis=-1, keepdims=True) + 1e-9

    col = np.zeros((H, W, 3), np.float32)
    hgt = np.zeros((H, W), np.float32)
    rng = np.random.default_rng(7)

    # ---- face
    cl, rl = np.array(eyes["L"][0]), eyes["L"][1]
    cr, rr = np.array(eyes["R"][0]), eyes["R"][1]
    ax = (cl - cr) / np.linalg.norm(cl - cr)
    fw = np.array([0, -1.0, 0]) - ax * (-ax[1])
    fw /= np.linalg.norm(fw)
    up = np.cross(fw, ax)
    M = (cl + cr) / 2
    h = np.linalg.norm(cl - cr) / 2
    dall = pos - M
    Ua, Va = (dall @ ax) / h, (dall @ up) / h
    face = valid & (pos[..., 2] > 4.0)
    P = pos[face]
    d = P - M
    U, V, D = Ua[face], Va[face], d @ fw
    # nose tip: the most forward point near the nose landmark
    near = (np.abs(U - 0.1) < 0.6) & (np.abs(V + 0.75) < 0.6)
    ni = np.argmax(np.where(near, D, -9))
    Un, Vn = U[ni], V[ni]
    nose_p = P[ni]
    dx, dy = U - Un, V - Vn
    r = np.hypot(dx, dy)
    th = np.arctan2(dy, dx)
    # eye distance (to the eyeball surface)
    de = np.minimum(np.linalg.norm(P - cl, axis=1) - rl, np.linalg.norm(P - cr, axis=1) - rr)
    dn = np.linalg.norm(P - nose_p, axis=1)
    edge = smoothstep(1.7, 2.7, np.hypot(U, V * 0.95))         # toward the hood

    # fur flow: radial from the nose (log-polar), gently warped so it isn't a sunburst
    rho = np.log(np.maximum(r, 0.04))
    warp = vnoise2(th / (2 * np.pi) * 9, rho / 0.6, 9, 31)
    thw = th + 0.10 * warp
    tshade, theight, ttip, tid = fur_tufts(thw, rho, 84, 2.6, 13)
    tshade2, theight2, _, _ = fur_tufts(thw + 0.021, rho + 0.09, 168, 2.2, 17)
    fine = fur_strands(thw, rho, 0.012, 0.4, 41)
    clumps2 = vnoise2(thw / (2 * np.pi) * 26, rho / 0.8, 26, 29)
    furlen = smoothstep(0.25, 1.4, r)
    # short fur near the nose: the small tufts dominate; long fur outside: the big ones
    tsh = tshade2 + (tshade - tshade2) * furlen
    thh = theight2 + (theight - theight2) * furlen
    # colour zones (linear)
    # the concept's hues (sampled: ~24-27 deg, saturation 0.5-0.65): cream muzzle and
    # chin, orange-tan cheeks, brown brow, dark crown into the hood (linear values of
    # sRGB (202, 146, 96), (160, 98, 52), (104, 58, 30), (58, 34, 20), tips (226, 178, 128))
    cream = np.array([0.5906, 0.2874, 0.117])
    tan = np.array([0.3515, 0.1221, 0.0343])
    brown = np.array([0.1384, 0.0423, 0.013])
    crown = np.array([0.0423, 0.016, 0.007])
    tipc = np.array([0.7605, 0.4452, 0.2159])
    muzzle = np.exp(-((dx / 1.05) ** 2 + ((dy + 0.42) / 0.62) ** 2))
    cheek = np.exp(-(((np.abs(U) - 1.05) / 0.9) ** 2 + ((V + 0.75) / 0.75) ** 2))
    brow = np.exp(-(((np.abs(U) - 0.85) / 0.75) ** 2 + ((V - 0.75) / 0.45) ** 2))
    crown_w = smoothstep(0.45, 1.8, V) * (1 - 0.5 * muzzle)
    bib = smoothstep(-1.55, -2.3, V)
    c = tan + (cream - tan) * np.clip(1.2 * muzzle + 0.55 * cheek + 0.35 * bib, 0, 1)[:, None]
    c = c + (brown - c) * np.clip(0.75 * brow, 0, 1)[:, None]
    c = c + (crown - c) * np.clip(crown_w, 0, 1)[:, None]
    c = c + (brown * 0.7 - c) * (0.55 * edge)[:, None]
    # fur detail: tufts (dark roots, light tips), fine strands, soft clumps
    amt = 0.45 + 0.55 * furlen
    shade = 1 + amt * (tsh - 1) + 0.10 * fine + 0.08 * clumps2
    c = c * np.clip(shade, 0.3, 1.5)[:, None]
    # per-tuft hue drift: some tufts paler / creamier, some redder brown
    drift = tid * furlen
    c = c * (1 + 0.10 * drift[:, None] * np.array([1.0, 0.6, 0.1]))
    tips = ttip * furlen * (1 - crown_w * 0.7) * (1 - edge * 0.6)
    c = c + (tipc - c) * (0.30 * tips)[:, None]
    # eye rims: dark moist lids hugging the eyeball, then a pale ring of short fur
    # the lid: a clean ring just outside each eyeball's silhouette seen from the front
    # (measured in face space, not by 3D distance: the sculpt's skin comes close to the
    # ball in blotches), only where the skin is near the ball
    lid = np.zeros_like(de)
    ring = np.zeros_like(de)
    for cc, R in ((cl, rl), (cr, rr)):
        dc = cc - M
        rho = np.hypot(U - (dc @ ax) / h, V - (dc @ up) / h) * h / R      # 1 = the silhouette
        near = 1 - smoothstep(0.06, 0.14, np.linalg.norm(P - cc, axis=1) - R)
        lid = np.maximum(lid, (1 - smoothstep(1.02, 1.13, rho)) * near)
        ring = np.maximum(ring, np.exp(-((rho - 1.3) / 0.15) ** 2))
    c = c + (cream * 1.05 - c) * (0.35 * ring)[:, None]
    c = c + (np.array([0.05, 0.022, 0.013]) - c) * (0.9 * lid)[:, None]
    # nose: leathery brown-pink skin with cross wrinkles on the bridge, dark nostrils
    bridge = np.exp(-((dx / 0.22) ** 2)) * smoothstep(-0.05, 0.1, dy) * (1 - smoothstep(0.35, 0.75, dy))
    nose = np.clip(1 - smoothstep(0.10, 0.19, dn) + 0.8 * bridge, 0, 1)
    wr = np.sin(2 * np.pi * (dy * 11 + 0.15 * np.sin(dx * 9))) * 0.5 + 0.5
    nose_col = np.array([0.2159, 0.0685, 0.0423]) * (0.75 + 0.3 * wr)[:, None]
    c = c + (nose_col - c) * nose[:, None]
    nostril = np.zeros_like(dx)
    for sx in (-1, 1):
        nostril = np.maximum(nostril, np.exp(-(((dx - sx * 0.13) / 0.06) ** 2 + ((dy + 0.12) / 0.035) ** 2)))
    c = c * (1 - 0.85 * nostril)[:, None]
    # mouth: the sculpt's crease, painted as a closed sly smile (corners turned up),
    # a short philtrum groove to the nose, slightly darker lips
    corner = 1.0
    ym = -1.18 + 0.20 * (U / corner) ** 2 + 0.06 * U          # smile centre line
    span = 1 - smoothstep(0.85, 1.12, np.abs(U - 0.0))
    dm = np.abs(V - ym)
    line = np.exp(-(dm / 0.022) ** 2) * span
    lips = np.exp(-(dm / 0.09) ** 2) * span
    curl = np.zeros_like(dx)
    for sx in (-1, 1):                                         # dimples at the corners
        curl = np.maximum(curl, np.exp(-(((U - sx * 0.98) / 0.07) ** 2 + ((V - (-0.96)) / 0.07) ** 2)))
    philtrum = np.exp(-(dx / 0.03) ** 2) * (dy < -0.15) * (V > ym + 0.03)
    c = c * (1 - 0.18 * lips)[:, None]
    c = c + (np.array([0.02, 0.009, 0.006]) - c) * np.clip(line + 0.7 * curl, 0, 1)[:, None]
    c = c * (1 - 0.3 * philtrum)[:, None]
    # toward the seam with the hood / cloak the fur sinks into shadow (hides the seam)
    if seam is not None and len(seam):
        fade = 1 - smoothstep(0.03, 0.30, nearest_distance(P, seam, 0.3))
        c = c + (crown * 0.8 - c) * (0.85 * fade)[:, None]
    # the head's back and top behind the face (inside the hood): the face-space zones
    # don't apply there (its points project onto the muzzle); dark crown fur
    behind = smoothstep(-0.25, -0.7, D)
    c = c + (crown * 0.9 * 1.0 - c) * behind[:, None]
    col[face] = c
    # height for the normal map: strands, partings, nose wrinkles, mouth groove
    hf = amt * (0.9 * thh + 0.15 * fine) + 0.2 * clumps2
    hf = hf * (1 - nose) + nose * (0.4 * wr) - 1.2 * line - 0.6 * curl
    hgt[face] = hf * (1 - lid)

    # ---- hands and feet: leathery wrinkled skin, darker creases, dark claws
    limb = valid & ~face
    Q = pos[limb]
    feet = Q[:, 2] < 1.0
    wrink = 1 - np.abs(fbm3(Q * np.array([1.0, 1.0, 2.2]), 9.0, 4, 0.55, 3))
    wrink = wrink ** 6
    pores = fbm3(Q, 60.0, 2, 0.5, 5)
    mott = fbm3(Q, 3.0, 3, 0.5, 9)
    skin_h = np.array([0.21, 0.115, 0.058])
    skin_f = np.array([0.10, 0.062, 0.038])
    sc = np.where(feet[:, None], skin_f, skin_h) * (0.85 + 0.25 * mott)[:, None]
    sc = sc * (1 - 0.45 * wrink)[:, None] * (1 + 0.06 * pores)[:, None]
    # claws: the most convex extremities (finger and toe tips)
    cv = conv[limb]
    claw = np.where(feet, smoothstep(0.012, 0.03, cv) * smoothstep(0.35, 0.05, Q[:, 2]),
                    smoothstep(0.03, 0.05, cv))
    claw_col = np.array([0.022, 0.016, 0.013])
    sc = sc + (claw_col - sc) * np.clip(claw, 0, 1)[:, None]
    col[limb] = sc
    # the hands' baked sculpt normals fight their smoothed geometry: wrinkles only
    hand_t = np.zeros(limb.shape, bool)
    hand_t[limb] = True               # (the hands are separate meshes now: this is the feet)
    tn[hand_t] = (0.0, 0.0, 1.0)      # their baked sculpt normals are noise: glints at the hem
    hgt[limb] = 0.25 * ((-0.9 * wrink + 0.15 * pores) * (1 - claw) + 0.3 * claw)

    # crevices darken everywhere (the sculpt's folds: mouth, eye sockets, knuckles)
    cavd = smoothstep(0.004, 0.02, cav)
    col *= (1 - 0.45 * cavd)[..., None]
    col = np.clip(col, 0, 1)
    # outside the islands (bake margin already extends positions): fill with nearby colour
    painted = valid & (np.abs(col).sum(-1) > 0)
    col = pull_push(col, painted)
    base = srgb(col)
    nm_detail = height_to_normal(hgt, 1.6)
    nrm_out = blend_normals(tn, nm_detail)
    nrm_out = pull_push(nrm_out, painted)
    nrm_out /= np.linalg.norm(nrm_out, axis=-1, keepdims=True) + 1e-9
    textures._save(body_names()[0], np.clip(base, 0, 1))
    textures._save(body_names()[1], nrm_out * 0.5 + 0.5, non_color=True)


# -------------------------------------------------------------------- cloak

def cloak_textures(n=1024, seed=61, force=False):
    """Coarse, hairy hand-woven wool: an irregular plain weave of thick, uneven
    yarns, felted fuzz over it; near black with heathered brown-grey yarns and
    sparse copper fibres (the concept's flecks). Tileable; one tile = P['cloak_tile']."""
    names = ("T_Grimble_Cloak_DetailAlbedo", "T_Grimble_Cloak_DetailNormal")
    paths = [_path(nm) for nm in names]
    if all(os.path.exists(pp) for pp in paths) and not force:
        return paths
    rng = np.random.default_rng(seed)
    threads = 16                                   # yarns per tile each way (~3.7 cm at 0.6 m): coarse, no moire
    x = (np.arange(n) + 0.5) / n
    X, Y = np.meshgrid(x, x)
    wob_x = 0.28 * noise2(n, 0.12, 2.5, 1.6, rng)
    wob_y = 0.28 * noise2(n, 2.5, 0.12, 1.6, rng)
    gx = X * threads + wob_x
    gy = Y * threads + wob_y
    ix, iy = np.floor(gx).astype(int), np.floor(gy).astype(int)
    fx, fy = gx - ix, gy - iy
    # uneven yarn thickness (slubs) per yarn and along it
    thick_w = 0.75 + 0.25 * noise2(n, 0.05, 1.2, 1.2, rng)
    thick_f = 0.75 + 0.25 * noise2(n, 1.2, 0.05, 1.2, rng)
    warp_prof = np.clip(1 - ((fx - 0.5) / (0.5 * thick_w)) ** 2, 0, 1) ** 0.6
    weft_prof = np.clip(1 - ((fy - 0.5) / (0.5 * thick_f)) ** 2, 0, 1) ** 0.6
    up = ((ix + iy) % 2) == 0                      # plain weave
    along_w = np.sin(np.pi * fy)                   # the yarn bulges between crossings
    along_f = np.sin(np.pi * fx)
    h = np.where(up, warp_prof * (0.6 + 0.4 * along_w), weft_prof * (0.6 + 0.4 * along_f))
    # felted fuzz: fine hairs in all directions, matted clumps, a few stray long fibres
    fib_w = noise2(n, 0.02, 0.5, 0.6, rng)
    fib_f = noise2(n, 0.5, 0.02, 0.6, rng)
    fibres = np.where(up, fib_w, fib_f)
    fuzz = noise2(n, 1.0, 1.0, 0.3, rng)
    matted = noise2(n, 1.0, 1.0, 1.4, rng)
    hh = h * (0.75 + 0.25 * matted) + 0.25 * fibres + 0.18 * fuzz + 0.2 * matted
    nrm = height_to_normal(hh, 1.8)
    yarn_id = np.where(up, ix % threads, threads + iy % threads)
    tone = rng.uniform(-1, 1, 2 * threads + 2)[yarn_id]
    # colour: mostly heathered, felted wool; only a hint of the weave grid (a strong
    # regular grid reads as moire at mid distance)
    blot = noise2(n, 1.0, 1.0, 2.2, rng)
    t = np.clip(0.12 * h + 0.2 * (fibres * 0.5 + 0.5) + 0.13 * (tone * 0.5 + 0.5) + 0.3 * (matted * 0.5 + 0.5)
                + 0.25 * (blot * 0.5 + 0.5), 0, 1)
    dark = np.array([0.0050, 0.0042, 0.0036])
    light = np.array([0.046, 0.037, 0.029])
    col = dark + (light - dark) * (t ** 1.6)[..., None]
    fl = noise2(n, 0.02, 0.02, 0.1, rng)
    cmask = (fl > 0.55) & (h > 0.3)
    col = np.where(cmask[..., None], np.array([0.085, 0.040, 0.018]) * (0.6 + 0.4 * t[..., None]), col)
    textures._save(names[0], srgb(col))
    textures._save(names[1], nrm * 0.5 + 0.5, non_color=True)
    return paths


# ---------------------------------------------------------------------- eye

def eye_texture(n=512, force=False):
    """Front of the eyeball, planar mapped: u = 0.5 + x / 2.2R, v = 0.5 + z / 2.2R."""
    name = "T_Grimble_Eye_BaseColor"
    path = _path(name)
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(71)
    c = (np.arange(n) + 0.5) / n - 0.5
    X, Z = np.meshgrid(c, -c)                     # row 0 = top (v = 1)
    rho = np.sqrt(X ** 2 + Z ** 2) * 2.2          # = sin(angle from the gaze axis)
    ang = np.arctan2(Z, X)
    r_pupil, r_iris = 0.40, 0.74
    # radial iris fibres: a sum of angular cosines that drift with the radius
    k = rng.standard_normal(180)
    fibres = np.zeros_like(rho)
    for m in range(1, 60):
        fibres += k[m] * np.cos(m * 3 * ang + k[m + 60] * 6 * rho + k[m + 120] * 3) / m ** 0.5
    fibres = fibres / np.abs(fibres).max()
    t_iris = np.clip((rho - r_pupil) / (r_iris - r_pupil), 0, 1)
    # iris: dark umber at the pupil, a warm amber-brown band, darker toward the limbus
    deep = np.array([0.045, 0.016, 0.006])
    amber = np.array([0.16, 0.065, 0.020])
    band = np.exp(-((t_iris - 0.42) / 0.25) ** 2)
    iris = deep + (amber - deep) * (band * (0.75 + 0.25 * fibres))[..., None]
    iris *= (1 - 0.55 * smoothstep(0.75, 1.0, t_iris))[..., None]         # limbal ring
    iris *= (1 - 0.35 * smoothstep(0.12, 0.0, t_iris))[..., None]         # collarette shadow
    pupil = np.array([0.0035, 0.0028, 0.0025])
    sclera = np.array([0.075, 0.030, 0.022]) * (0.85 + 0.15 * noise2(n, 1, 1, 1.5, rng))[..., None]
    col = pupil + (iris - pupil) * smoothstep(r_pupil - 0.01, r_pupil + 0.02, rho)[..., None]
    s = smoothstep(r_iris - 0.01, r_iris + 0.04, rho)[..., None]
    col = col * (1 - s) + sclera * s
    textures._save(name, srgb(col))
    return path


# --------------------------------------------------------------------- hand

def hand_textures(n=1024, seed=91, force=False):
    """Leathery, wrinkled brown skin for the rebuilt hands: fine creases running
    across the fingers (along u), coarser folds, pores and mottling. Tileable; one
    tile = P['hand_tile'] metres; v runs along the finger."""
    names = ("T_Grimble_Hand_BaseColor", "T_Grimble_Hand_Normal")
    paths = [_path(nm) for nm in names]
    if all(os.path.exists(pp) for pp in paths) and not force:
        return paths
    rng = np.random.default_rng(seed)
    x = (np.arange(n) + 0.5) / n
    X, Y = np.meshgrid(x, x)
    warp = 0.04 * noise2(n, 0.3, 0.3, 1.8, rng)
    fine = np.abs(np.sin(2 * np.pi * (Y * 46 + warp * 6 + 0.3 * noise2(n, 0.2, 1.0, 1.5, rng))))
    crease = (1 - fine) ** 6 * (0.5 + 0.5 * noise2(n, 0.06, 0.6, 1.2, rng))      # broken creases
    folds = (1 - np.abs(noise2(n, 0.08, 0.5, 1.6, rng))) ** 8
    pores = noise2(n, 1.0, 1.0, 0.2, rng)
    mott = noise2(n, 1.0, 1.0, 2.0, rng)
    h = -0.9 * crease - 0.7 * folds + 0.12 * pores + 0.25 * mott
    nrm = height_to_normal(h, 2.2)
    base = np.array([0.19, 0.095, 0.045])          # sRGB ~ (121, 87, 60): leathery warm brown
    col = base * (0.85 + 0.25 * mott[..., None]) * (1 - 0.5 * crease - 0.35 * folds)[..., None]
    col = col * (1 + 0.05 * pores)[..., None]
    textures._save(names[0], srgb(np.clip(col, 0, 1)))
    textures._save(names[1], nrm * 0.5 + 0.5, non_color=True)
    return paths


# -------------------------------------------------------------------- staff

def staff_textures(n=1024, seed=81, force=False):
    """Gnarled, twisted dark wood: fibres along v (the staff's length), darker
    crevices, lighter worn ridges, a few knots. Tileable."""
    names = ("T_Grimble_Staff_BaseColor", "T_Grimble_Staff_Normal")
    paths = [_path(nm) for nm in names]
    if all(os.path.exists(pp) for pp in paths) and not force:
        return paths
    rng = np.random.default_rng(seed)
    x = (np.arange(n) + 0.5) / n
    X, Y = np.meshgrid(x, x)
    # a slow twist: fibres lean across u as they run along v
    warp = 0.6 * noise2(n, 0.4, 2.0, 2.0, rng)
    u = X + 0.25 * Y + 0.05 * warp
    fib1 = np.sin(2 * np.pi * (u * 22 + 0.6 * noise2(n, 0.05, 1.2, 1.4, rng)))
    fib2 = noise2(n, 0.025, 0.8, 0.8, rng)
    crev = (1 - np.abs(np.sin(2 * np.pi * (u * 7 + 0.9 * noise2(n, 0.1, 1.5, 1.8, rng))))) ** 6
    # knots: periodic placement
    knots = np.zeros_like(X)
    for _ in range(3):
        cx, cy = rng.uniform(0, 1, 2)
        dxk = (X - cx + 0.5) % 1 - 0.5
        dyk = (Y - cy + 0.5) % 1 - 0.5
        r = np.sqrt((dxk / 0.05) ** 2 + (dyk / 0.08) ** 2)
        knots = np.maximum(knots, np.exp(-r ** 2))
    h = 0.35 * fib1 + 0.4 * fib2 - 0.9 * crev + 0.8 * knots * np.sin(r * 4)
    h += 0.15 * noise2(n, 1.0, 1.0, 1.0, rng)
    nrm = height_to_normal(h, 2.5)
    t = np.clip(0.55 + 0.25 * fib2 + 0.12 * fib1 - 0.4 * crev - 0.1 * knots, 0, 1)
    dark = np.array([0.018, 0.009, 0.004])
    mid = np.array([0.085, 0.042, 0.018])
    light = np.array([0.20, 0.105, 0.048])
    col = np.where((t < 0.6)[..., None], dark + (mid - dark) * (t / 0.6)[..., None],
                   mid + (light - mid) * ((t - 0.6) / 0.4)[..., None])
    textures._save(names[0], srgb(col))
    textures._save(names[1], nrm * 0.5 + 0.5, non_color=True)
    return paths
