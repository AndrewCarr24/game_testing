"""Laurel Fork Cove: the water's own data (the river-look pass, design/wilderness/blue_ridge/water.md).

Called by laurel_fork_world.run after the rocks and the canopy are placed:
  river_rocks(R, C, trails_d, r)      the Laurel River's boulders (ledges, rapids, pools, bars)
  strainers(R, r, rocks)              driftwood lodged on the rocks and the banks (logs, kind "drift")
  water_fx(R, wl, rocks, logs, top, out_dir)  -> world.json "water_fx" and three files:
      water_flow.png   RGBA8 per cell: current x / z (three.js, m/s: 128 + v * 127 / VMAX),
                       foam potential, standing-wave strength
      water_env.png    RGBA16 per cell: the skyline over the water in 8 directions (three.js, k * 45
                       deg from +x toward +z), two 8-bit elevation angles per channel (k even in the
                       high byte), 0..255 = 0..90 deg: what the surface reflects, forest or sky
      water_aux16.png  grey+alpha 16-bit: the standing waves' phase (cycles x PHASE_SCALE, along the
                       main stem), bed kind (0 cobbles, 65535 bedrock)
The runtime (viewer/wild/water.js) reads them into the water mesh's vertices and the CPU field
behind water.flowAt; without them it falls back to the surface's slope.

Rasters are the terrain grid (row j = local y, i = x); the estate frame is y north; three.js z = -local y.
"""
import math
import os

import numpy as np

import terrain
import laurel_fork as LF

OY = LF.OFFSET_Y
VMAX = 7.0                 # m/s at 255 in water_flow.png
PHASE_SCALE = 120.0        # water_aux16 phase units per cycle (546 cycles of range)
Q_MAIN = 24.0              # m³/s: the Laurel River in June (a Nantahala release is ~28)
G = 9.81


def _masked_blur(a, m, sigma):
    num = terrain.blur(np.where(m, a, 0.0), sigma)
    den = terrain.blur(m.astype(float), sigma)
    return np.where(den > 1e-3, num / np.maximum(den, 1e-6), 0.0), den


def _bilinear(A, R, x, y):
    """A (grid) at estate points."""
    return terrain.sample(A, R.grid, np.asarray(x, float), np.asarray(y, float) + OY)


def main_line(R):
    """The main stem's carved centreline (terrain stats channels[0].centerline), estate frame, with s."""
    ch = (R.stats.get("channels") or [None])[0]
    if not ch or not ch.get("centerline"):
        return None
    cl = np.array(ch["centerline"], float)
    cl[:, 1] -= OY
    return cl


def steps_estate(R):
    """The main stem's drops: (kind, centre (x, y), length) from the level config."""
    return [(st.get("kind", "rapid"), st["at"], st.get("length", 30.0)) for st in LF.RIVER_CHANNEL["steps"]]


# ------------------------------------------------------------------ rocks
def river_rocks(R, C, trails_d, r, CID, jitter_grid, poisson_thin):
    """The Laurel River's boulders, by what the channel does: lines of 2-4.5 m blocks across each
    ledge's lip and below it, 1-3.5 m boulders through the rapids (more on the outside), a few
    huge gneiss blocks (3-5.5 m) standing in and beside the pools against the gorge walls, scattered
    0.4-2 m rocks breaking the surface and cobble-bar rocks (0.3-0.9 m). Each sits on the bed; in
    the channel its top clears the water by a third of its height or more (so it breaks the
    surface and parts the current)."""
    water = C == CID["water"]
    bars = R.mask("bars") > 0.5
    x, y = jitter_grid(R, 2.2, r)
    j, i = R.ij(x, y)
    main = (x < -480) & ((y < -752) | (x < -560))
    _, _, dwc = terrain.nearest_seed(water)
    dw = dwc[j, i] * R.cell
    p = np.zeros(len(x))
    kind = np.zeros(len(x), np.int8)                       # 0 scatter, 1 rapid, 2 ledge, 3 huge, 4 bar
    p[water[j, i] & main] = 0.03
    p[bars[j, i] & main & ~water[j, i]] = 0.05
    kind[bars[j, i] & main & ~water[j, i]] = 4
    for k_, (cx, cy), L in steps_estate(R):
        dd = np.hypot(x - cx, y - cy)
        if k_ == "ledge":
            m = (dd < 22) & main & (dw < 6)
            p[m] = 0.55; kind[m] = 2
        elif k_ == "rapid":
            m = (dd < L * 0.6 + 16) & main & (dw < 8)
            p[m] = np.maximum(p[m], 0.3); kind[m] = 1
        else:
            m = (dd < L * 0.5 + 10) & main & (dw < 5)
            p[m] = np.maximum(p[m], 0.12); kind[m] = 1
    # the Narrows' and the cascade's rapids (below the reach the channel hook shapes)
    for cx, cy, rad in [(-575.0, -792.0, 34.0), (-600.0, -762.0, 26.0), (-640.0, -748.0, 30.0)]:
        m = (np.hypot(x - cx, y - cy) < rad) & main & (dw < 8)
        p[m] = np.maximum(p[m], 0.3); kind[m] = 1
    # huge blocks: along the deep pools' outer edges, in and beside the water
    deep = water & np.isfinite(R.river_level) & ((R.river_level - R.H) > 2.0)
    _, _, ddeep = terrain.nearest_seed(deep)
    near_deep = ddeep[j, i] * R.cell < 9
    huge = main & near_deep & (dw < 7) & (r.random(len(x)) < 0.02)
    p[huge] = 1.0; kind[huge] = 3
    ok = (r.random(len(x)) < p) & (trails_d[j, i] > 3.5)
    x, y, kind = x[ok], y[ok], kind[ok]
    n = len(x)
    rad = np.select([kind == 2, kind == 1, kind == 3, kind == 4],
                    [r.uniform(1.8, 4.5, n), r.uniform(1.0, 3.5, n), r.uniform(3.0, 5.5, n), r.uniform(0.3, 0.9, n)],
                    np.clip(r.lognormal(-0.1, 0.5, n), 0.4, 2.2))
    keep = poisson_thin(x, y, rad * 1.05, r, order=np.argsort(-rad))
    x, y, rad, kind = x[keep], y[keep], rad[keep], kind[keep]
    z = R.h(x, y)
    wl = np.where(np.isfinite(R.lake_level) & (R.H < R.lake_level), R.lake_level, R.river_level)
    jj, ii = R.ij(x, y)
    w = wl[jj, ii]
    sq = r.uniform(0.5, 0.8, len(x))
    sq = np.where(kind == 3, r.uniform(0.6, 0.85, len(x)), np.where(kind == 2, r.uniform(0.45, 0.65, len(x)), sq))
    # (the kit boulder's top sits ~ (1.25 sq - 0.25) r over its centre: in the channel the top
    # clears the water by >= 0.3 r; bar cobbles bed into the gravel)
    top_k = 1.25 * sq - 0.25
    zc = np.where(np.isfinite(w), np.maximum(z - 0.3 * rad, w + 0.3 * rad - top_k * rad), z - 0.35 * rad)
    zc = np.where(kind == 4, z - 0.45 * rad, zc)
    return [dict(x=float(a), y=float(b), z=float(zz), r=float(rr), sq=float(q), yaw=float(r.uniform(0, 6.283)),
                 seed=float(r.random()), river=int(k)) for a, b, zz, rr, q, k in zip(x, y, zc, rad, sq, kind)]


def strainers(R, r, rocks, n=14):
    """Driftwood: silver, barkless logs washed down and lodged against boulders or the bank, angled
    downstream, partly in the water (the Nantahala's strainers). Logs of kind "ghost" (the kit's
    chestnut ghost), so they draw with the logs."""
    out = []
    wl = np.where(np.isfinite(R.lake_level) & (R.H < R.lake_level), R.lake_level, R.river_level)
    big = [b for b in rocks if b.get("river") in (1, 2, 3) and b["r"] > 1.5]
    order = r.permutation(len(big))
    gy, gx = np.gradient(terrain.blur(np.where(np.isfinite(wl), wl, R.H), 3.0), R.cell)
    for k in order:
        if len(out) >= n:
            break
        b = big[k]
        j, i = R.ij(b["x"], b["y"])
        fx, fy = -gx[j, i], -gy[j, i]
        L0 = math.hypot(fx, fy)
        if L0 < 1e-5:
            fx, fy, L0 = 0.0, 1.0, 1.0                    # (flat pool: the river runs north here)
        fx, fy = fx / L0, fy / L0
        # pinned on the rock's upstream face, swung 35-70 deg off the current toward the nearer bank
        yaw = math.atan2(fy, fx) + math.pi + r.choice([-1, 1]) * r.uniform(0.6, 1.2)
        L = r.uniform(7, 15)
        d = r.uniform(0.35, 0.7)
        ax, ay = b["x"] - fx * b["r"] * 0.9, b["y"] - fy * b["r"] * 0.9
        bx, by = ax + math.cos(yaw) * L, ay + math.sin(yaw) * L
        za = b["z"] + b["r"] * 0.4
        w_b = float(_bilinear(np.nan_to_num(wl, nan=-1e4), R, bx, by))
        g_b = float(R.h(bx, by))
        zb = max(g_b + d * 0.3, w_b - d * 0.2) if w_b > -1e3 else g_b + d * 0.4
        if abs(za - zb) > L * 0.45:
            continue
        out.append(dict(kind="ghost", x0=float(ax), y0=float(ay), z0=float(za), x1=float(bx), y1=float(by), z1=float(zb),
                        r=d / 2, wad=False, drift=True))
    return out


# ------------------------------------------------------------------ the field
def _upstream(A, vx, vy, R, step):
    """A sampled one `step` m upstream of every cell (semi-Lagrangian), estate-frame velocity."""
    sp = np.hypot(vx, vy) + 1e-6
    X, Y = R.X, R.Y
    return _bilinear(A, R, X - vx / sp * step, Y - vy / sp * step)


def water_fx(R, wl, rocks, logs, top, out_dir):
    cell = R.cell
    wm = np.isfinite(wl)
    H = R.H
    depth = np.where(wm, np.maximum(wl - H, 0.0), 0.0)
    # ---- direction: down the water surface (masked blur over ~5 m), bank-parallel near the banks,
    # the main stem's centreline tangent where the surface is flat (the pools)
    lv, den = _masked_blur(np.where(wm, wl, 0), wm, 5.0 / cell)
    gy, gx = np.gradient(np.where(den > 0.05, lv, np.nan_to_num(wl)), cell)
    slope = np.hypot(gx, gy)
    dx, dy = -gx / (slope + 1e-9), -gy / (slope + 1e-9)
    cl = main_line(R)
    tan_w = np.zeros(H.shape)
    s_main = np.full(H.shape, np.nan)
    n_main = np.zeros(H.shape)
    if cl is not None:
        P = cl.copy(); P[:, 1] += OY                      # (terrain local for poly_field)
        d_c, _, s_c, side = terrain.poly_field(R.grid, P[:, :2], 60.0)
        fin = np.isfinite(d_c) & wm
        tx, ty = np.gradient(cl[:, 0]), np.gradient(cl[:, 1])
        tl = np.hypot(tx, ty) + 1e-9
        tx, ty = tx / tl, ty / tl
        T_x = np.interp(np.where(fin, s_c, 0), cl[:, 2], tx)
        T_y = np.interp(np.where(fin, s_c, 0), cl[:, 2], ty)
        flat = 1 - terrain.smoothstep(0.002, 0.012, slope)
        tan_w = np.where(fin, np.maximum(flat, 0.35), 0.0)
        dx = np.where(fin, dx * (1 - tan_w) + T_x * tan_w, dx)
        dy = np.where(fin, dy * (1 - tan_w) + T_y * tan_w, dy)
        s_main = np.where(fin & (s_c > 0.5) & (s_c < cl[-1, 2] - 0.5), s_c, np.nan)
        n_main = np.where(fin, side * np.where(fin, d_c, 0.0), 0.0)
    # banks: no flow into them (remove the component along the bank normal within 4 m of the edge)
    _, _, dry_d = terrain.nearest_seed(~wm)
    dd = dry_d * cell
    by_, bx_ = np.gradient(terrain.blur(np.minimum(dd, 12.0), 1.0), cell)
    bl = np.hypot(bx_, by_) + 1e-9
    nx_, ny_ = bx_ / bl, by_ / bl
    wb = 1 - terrain.smoothstep(0.0, 5.0, dd)
    dot = dx * nx_ + dy * ny_
    dx, dy = dx - nx_ * dot * wb, dy - ny_ * dot * wb
    for _ in range(2):
        dx, _ = _masked_blur(dx, wm, 1.2)
        dy, _ = _masked_blur(dy, wm, 1.2)
    L = np.hypot(dx, dy) + 1e-9
    dx, dy = dx / L, dy / L
    # ---- speed: continuity on the main stem (Q / section area, distributed as h^(2/3)), Manning
    # elsewhere (the creek), never slower than a steep surface's own: rapids, ledges, the cascade
    slope_s = terrain.blur(slope, 2.0 / cell)
    v_man = np.clip(depth ** (2 / 3) * np.sqrt(np.maximum(slope_s, 2e-4)) / 0.055, 0.1, 6.0)
    v = v_man.copy()
    if cl is not None:
        sm = np.isfinite(s_main) & wm
        nb = int(cl[-1, 2] / 3.0) + 2
        b = np.clip((np.nan_to_num(s_main) / 3.0).astype(int), 0, nb - 1)
        A = np.bincount(b[sm], weights=depth[sm] * cell * cell, minlength=nb) / 3.0     # m² section area
        Wd = np.bincount(b[sm], minlength=nb) * cell * cell / 3.0                      # m width
        A = np.convolve(np.pad(A, 2, mode="edge"), np.ones(5) / 5, mode="valid")
        Wd = np.convolve(np.pad(Wd, 2, mode="edge"), np.ones(5) / 5, mode="valid")
        hm = A / np.maximum(Wd, 1.0)
        V = Q_MAIN / np.maximum(A, 4.0)
        vloc = V[b] * (np.maximum(depth, 0.05) / np.maximum(hm[b], 0.1)) ** (2 / 3)
        v = np.where(sm, np.clip(vloc, 0.08, 6.5), v)
    v = np.maximum(v, np.where(wm, np.clip(1.0 + 22.0 * slope_s, 0, 6.5) * terrain.smoothstep(0.008, 0.03, slope_s), 0))
    # (thin water slows at the very edge, but a steep skin of water over a drop still runs fast)
    v = np.where(wm, v, 0.0) * np.maximum(terrain.smoothstep(0.0, 0.25, depth + 0.02), terrain.smoothstep(0.02, 0.08, slope_s))
    vx, vy = dx * v, dy * v
    # ---- the rocks in the water: the current parts around each (potential flow round a cylinder),
    # slows and turns back in its lee (an eddy); foam on its upstream pillow, its eddy lines and wake
    foam_src = np.zeros(H.shape)
    # (each rock perturbs the unperturbed current; the changes add up, as potential flows superpose)
    vx0, vy0 = vx.copy(), vy.copy()
    dvx, dvy = np.zeros(H.shape), np.zeros(H.shape)
    inside = np.zeros(H.shape, bool)
    eddy = np.zeros(H.shape)
    X, Y = R.X, R.Y
    for bk in rocks:
        j, i = R.ij(bk["x"], bk["y"])
        if not wm[j, i]:
            continue
        w0 = float(wl[j, i])
        top_z = bk["z"] + bk["r"] * (1.25 * bk["sq"] - 0.25)
        sub = top_z < w0                                   # (a submerged rock: a boil, a pour-over)
        Rr = bk["r"] * 0.85
        k = int(Rr * 7 / cell) + 2
        j0, j1, i0, i1 = max(j - k, 0), min(j + k + 1, R.n), max(i - k, 0), min(i + k + 1, R.n)
        if j0 >= j1 or i0 >= i1:
            continue
        U = math.hypot(vx0[j, i], vy0[j, i])
        if U < 0.05:
            continue
        ex, ey = vx[j, i] / U, vy[j, i] / U
        rx, ry = X[j0:j1, i0:i1] - bk["x"], Y[j0:j1, i0:i1] - bk["y"]
        xu, yw = rx * ex + ry * ey, -rx * ey + ry * ex        # along / across the current
        rho2 = xu * xu + yw * yw + 1e-6
        out = rho2 > Rr * Rr
        R2 = Rr * Rr * (0.35 if sub else 1.0)
        uu = U * (1 - R2 * (xu * xu - yw * yw) / (rho2 * rho2))
        ww = -U * 2 * R2 * xu * yw / (rho2 * rho2)
        # the lee: an eddy 0.6-3 R behind (reversed, slow), its shear lines at |y| ~ R
        lee = (xu > 0) & (np.abs(yw) < Rr * (1.0 + 0.15 * xu / Rr))
        f = np.exp(-np.maximum(xu - Rr, 0) / (1.5 * Rr)) * np.clip(1 - (yw / (Rr * 0.9 + 0.12 * xu)) ** 2, 0, 1)
        f = np.where(lee, f, 0.0) * (0.45 if sub else 1.0)
        uu = uu * (1 - 1.2 * f)              # (a small reversed eddy right behind the rock)
        ww = ww * (1 - f)
        nvx, nvy = uu * ex - ww * ey, uu * ey + ww * ex
        msk = out & wm[j0:j1, i0:i1]
        bx0, by0 = vx0[j0:j1, i0:i1], vy0[j0:j1, i0:i1]
        # (the rock's own change, scaled to the local current so a fast tongue past a slow eddy keeps both)
        loc = np.hypot(bx0, by0) / max(U, 1e-3)
        dvx[j0:j1, i0:i1] += np.where(msk, (nvx - ex * U) * np.clip(loc, 0, 1.5), 0.0)
        dvy[j0:j1, i0:i1] += np.where(msk, (nvy - ey * U) * np.clip(loc, 0, 1.5), 0.0)
        if not sub:
            inside[j0:j1, i0:i1] |= ~out
        eddy[j0:j1, i0:i1] = np.maximum(eddy[j0:j1, i0:i1], np.where(msk, f, 0))
        Uf = min(1.0, U / 1.4)
        rr = np.sqrt(rho2)
        pillow = (xu < 0) & (rr < Rr * 1.55) & (np.abs(yw) < Rr * 1.1)
        shear = lee & (np.abs(np.abs(yw) - Rr * (1.0 + 0.12 * xu / Rr)) < 0.9) & (xu < 7 * Rr)
        vwake = (xu > 0) & (np.abs(np.abs(yw) - (Rr + 0.3 * xu)) < 0.7) & (xu < 6 * Rr)
        src = np.maximum.reduce([pillow * 0.9, shear * 0.65 * np.exp(-xu / (5 * Rr)), vwake * 0.45 * np.exp(-xu / (4 * Rr)),
                                 (rr < Rr * 1.25) * 0.8])
        if sub:
            src = src * 0.5
        foam_src[j0:j1, i0:i1] = np.maximum(foam_src[j0:j1, i0:i1], np.where(msk, src * Uf, 0))
    vx, vy = np.where(inside, 0.0, vx0 + dvx), np.where(inside, 0.0, vy0 + dvy)
    sp = np.hypot(vx, vy)
    cap = np.minimum(1.0, 6.5 / np.maximum(sp, 1e-6))
    vx, vy, sp = vx * cap, vy * cap, sp * cap
    Fr = sp / np.sqrt(G * np.maximum(depth, 0.05))
    # white water where the flow is supercritical or the surface steep (riffles break over the
    # cobbles when shallow and quick), plus the rocks' pillows and wakes
    f_fr = terrain.smoothstep(0.55, 1.15, Fr) * terrain.smoothstep(0.05, 0.25, depth)
    f_sl = terrain.smoothstep(0.03, 0.12, slope_s)
    f_sh = terrain.smoothstep(0.7, 0.2, depth) * terrain.smoothstep(0.5, 1.4, sp) * 0.55
    src = np.maximum.reduce([f_fr * 0.85, f_sl, f_sh, foam_src])
    src = np.where(wm, src, 0.0)
    # foam drifts downstream and thins (half-life ~8 s): foam lines out of every rapid into the pool
    F = src.copy()
    step = 1.5
    vxs, vys = np.where(wm, vx, 0), np.where(wm, vy, 0)
    keep = np.where(wm, 0.5 ** (step / (np.maximum(sp, 0.15) * 8.0)), 0.0)
    for _ in range(45):
        F = np.maximum(src, keep * _upstream(F, vxs, vys, R, step))
    foam = np.clip(F, 0, 1)
    # standing waves: the tongue below each drop, where the flow is fast and still deep enough
    lat = np.ones(H.shape)
    if cl is not None:
        hwm = np.maximum(terrain.blur(np.minimum(dd, 30.0), 2.0), 1.0)
        lat = terrain.smoothstep(1.0, 4.0, dd) * (1 - terrain.smoothstep(0.55, 1.0, np.abs(n_main) / np.maximum(hwm * 2, 1)))
    wave = terrain.smoothstep(0.5, 0.85, Fr) * (1 - terrain.smoothstep(1.5, 2.3, Fr)) * terrain.smoothstep(0.3, 0.75, depth) * lat
    wave = np.where(wm & np.isfinite(s_main), wave, 0.0)
    wave = terrain.blur(wave, 1.0)
    # their phase along the main stem: crests every 2 pi v² / g (stationary in a current of v)
    phase = np.zeros(H.shape)
    if cl is not None:
        sm = np.isfinite(s_main)
        nb = int(cl[-1, 2] / 1.5) + 2
        b = np.clip((np.nan_to_num(s_main) / 1.5).astype(int), 0, nb - 1)
        vb = np.bincount(b[sm], weights=sp[sm] * (1 + wave[sm] * 4), minlength=nb) / np.maximum(np.bincount(b[sm], weights=1 + wave[sm] * 4, minlength=nb), 1e-6)
        vb = np.convolve(np.pad(vb, 3, mode="edge"), np.ones(7) / 7, mode="valid")
        lam = np.clip(2 * math.pi * vb * vb / G, 1.6, 9.0)
        cyc = np.concatenate([[0], np.cumsum(1.5 / lam[:-1])])
        phase = np.where(sm, np.interp(np.nan_to_num(s_main), np.arange(nb) * 1.5, cyc), 0.0)
    # bed kind: bedrock where the channel hook cut shelves or the cut banks reach into the water
    rock = R.mask("cliff") > 0.45
    bedrock = wm & (rock | ((depth < 0.4) & (R.mask("slope") * 90 > 25)))
    # ---- the skyline over the water, 8 directions: terrain or canopy tops, whichever is higher
    E = np.maximum(H, np.where(top > -1e8, top, -1e9))
    jj, ii = np.nonzero(wm)
    xs, ys = R.X[jj, ii], R.Y[jj, ii]
    z0 = wl[jj, ii] + 0.3
    rs = np.geomspace(2.0, 650.0, 40)
    hor = np.zeros((len(jj), 8))
    for k in range(8):
        th = k * math.pi / 4                               # three.js: from +x toward +z (= estate -y)
        ex_, ey_ = math.cos(th), -math.sin(th)
        best = np.zeros(len(jj))
        for rr in rs:
            e = _bilinear(E, R, xs + ex_ * rr, ys + ey_ * rr)
            best = np.maximum(best, np.arctan2(e - z0, rr))
        hor[:, k] = best
    hq = np.clip(np.round(hor / (math.pi / 2) * 255), 0, 255).astype(np.uint16)
    env = np.zeros(H.shape + (4,), np.uint16)
    for c in range(4):
        env[jj, ii, c] = (hq[:, 2 * c] << 8) | hq[:, 2 * c + 1]
    # ---- write (three.js frame: vz = -vy)
    flow = np.zeros(H.shape + (4,), np.uint8)
    enc = lambda a: np.clip(np.round(128 + a * 127 / VMAX), 1, 255).astype(np.uint8)
    flow[..., 0] = np.where(wm, enc(vx), 128)
    flow[..., 1] = np.where(wm, enc(-vy), 128)
    flow[..., 2] = np.round(np.clip(foam, 0, 1) * 255).astype(np.uint8)
    flow[..., 3] = np.round(np.clip(wave, 0, 1) * 255).astype(np.uint8)
    aux = np.zeros(H.shape + (2,), np.uint16)
    aux[..., 0] = np.clip(np.round(phase * PHASE_SCALE), 0, 65535).astype(np.uint16)
    aux[..., 1] = np.where(bedrock, 65535, 0).astype(np.uint16)
    files = {}
    files["water_flow.png"] = terrain.write_png(os.path.join(out_dir, "water_flow.png"), flow)
    files["water_env.png"] = terrain.write_png(os.path.join(out_dir, "water_env.png"), env)
    files["water_aux16.png"] = terrain.write_png(os.path.join(out_dir, "water_aux16.png"), aux)
    st = dict(speed_p50=round(float(np.median(sp[wm & (depth > 0.2)])), 2), speed_p95=round(float(np.percentile(sp[wm & (depth > 0.2)], 95)), 2),
              foam_share=round(float((foam[wm] > 0.4).mean()), 3), wave_share=round(float((wave[wm] > 0.3).mean()), 3),
              eddy_cells=int((eddy > 0.3).sum()), bedrock_cells=int(bedrock.sum()))
    meta = dict(flow="water_flow.png", env="water_env.png", aux="water_aux16.png", vmax=VMAX, phase_scale=PHASE_SCALE,
                env_dirs="three.js: k * 45 deg from +x toward +z; k even in the high byte; 255 = 90 deg", q_main=Q_MAIN, stats=st)
    return meta, files
