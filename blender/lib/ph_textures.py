"""The bathhouse's surfaces (blender/levels/rooms/bathhouse.py), numpy-generated and tileable like
lib/textures.py: coursed thin stone for the walls (Zumthor's Therme Vals: Valser quartzite laid
in thin courses; here the Blue Ridge's own grey-green gneiss, with its rusty iron stains), long
honed slabs of the same stone for the floors and pool, Tadao Ando's board-formed concrete for the
secret stair (910 x 1820 panels, six tie holes each), the fire bath's oxblood lime plaster and the
steam room's small dark-teal glazed mosaic."""
import os

import numpy as np

from . import textures as tx

N = 1024


def _grid(n=N):
    u = np.linspace(0, 1, n, endpoint=False)[None, :] * np.ones((n, 1))
    v = np.linspace(0, 1, n, endpoint=False)[:, None] * np.ones((1, n))
    return u, v


def _path(name):
    return os.path.join(tx.TEX_DIR, f"{name}.png")


def _courses(total, lo, hi, rng):
    """Course heights between lo and hi summing to total."""
    hs = []
    while sum(hs) < total:
        hs.append(rng.uniform(lo, hi))
    hs = np.array(hs)
    return hs * total / hs.sum()


def coursed_stone(force=False, name="T_PH_Stone_BaseColor", seed=71, tile=2.0, dark=False):
    """Dry-laid thin courses (2.5..9 cm) of grey-green gneiss, stones 0.25..1.2 m long, the joints
    a dark shadow line under each course. One tile = `tile` m square; courses run along u."""
    path = _path(name)
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    n = N
    u, v = _grid(n)
    heights = _courses(tile, 0.018, 0.075, rng)
    edges = np.concatenate([[0], np.cumsum(heights)]) / tile           # course boundaries in v (0..1)
    row = np.clip(np.searchsorted(edges, v, side="right") - 1, 0, len(heights) - 1)
    vin = (v - edges[row]) / (heights[row] / tile)                     # 0 at a course's top .. 1 at its bottom
    # stones along each course: lengths 0.25..1.2 m, a random phase so the joints don't line up
    stone_id = np.zeros_like(u, dtype=int)
    jdist = np.ones_like(u)
    sid = 0
    for r in range(len(heights)):
        lens = _courses(tile, 0.3, 1.5, rng) / tile
        cuts = (np.concatenate([[0], np.cumsum(lens)]) + rng.random()) % 1.0
        cuts.sort()
        m = row == r
        uu = u[m]
        k = np.searchsorted(cuts, uu, side="right") - 1        # -1 = wrapped round from the last stone
        stone_id[m] = sid + (k % len(cuts))
        d = np.min(np.abs(((uu[:, None] - cuts[None, :]) + 0.5) % 1.0 - 0.5), axis=1) * tile   # metres to a joint
        jdist[m] = d
        sid += len(cuts)
    tone = rng.normal(0, 1, sid + 1)[stone_id]
    hue = rng.random(sid + 1)[stone_id]
    rust = (rng.random(sid + 1) < 0.035)[stone_id]
    deep = (rng.random(sid + 1) < 0.06)[stone_id]
    grain = tx._noise(n, 0.02, 1.0, 1.1, rng)                 # long horizontal grain within the stone
    speck = tx._noise(n, 1.0, 1.0, 0.3, rng)
    cloud = tx._noise(n, 0.3, 1.0, 2.0, rng)
    grey = np.array([0.20, 0.20, 0.182]) if not dark else np.array([0.10, 0.106, 0.10])
    green = np.array([0.18, 0.19, 0.17]) if not dark else np.array([0.085, 0.095, 0.088])
    warm = np.array([0.215, 0.198, 0.17]) if not dark else np.array([0.112, 0.104, 0.092])
    base = grey + (green - grey) * np.clip(hue, 0, 0.7)[..., None] / 0.7
    base = np.where(hue[..., None] > 0.86, warm, base)
    lin = base * (1 + 0.085 * tone + 0.06 * grain + 0.05 * cloud + 0.035 * speck)[..., None]
    lin = np.where(rust[..., None], lin * np.array([1.16, 1.03, 0.9]), lin)
    lin = np.where(deep[..., None], lin * 0.74, lin)
    # the joints: under each course a shadow (the stones are dry-laid, the bed recessed), and a
    # fine dark vertical joint between stones; the top arris of each stone catches a little light
    ch = heights[row]
    from_bottom = (1 - vin) * ch
    shade = np.clip(from_bottom / 0.006, 0, 1) ** 0.6
    shade = np.minimum(shade, np.clip(jdist / 0.004, 0, 1) ** 0.6)
    lin = lin * (0.28 + 0.72 * shade)[..., None]
    lin = lin * (1 + 0.10 * np.clip(1 - vin * ch / 0.004, 0, 1))[..., None]
    return tx._save(name, tx._to_srgb(lin))


def slabs(force=False, name="T_PH_Slab_BaseColor", seed=73, tile=2.4, color=(0.24, 0.235, 0.215), rows=4):
    """Long honed slabs of the same stone in 0.6 m rows (random lengths 0.9..2.4 m), 2 mm joints.
    One tile = `tile` m; rows run along u."""
    path = _path(name)
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    n = N
    u, v = _grid(n)
    row = np.floor(v * rows).astype(int)
    vin = (v * rows) % 1.0
    slab = np.zeros_like(u, dtype=int)
    jd = np.ones_like(u)
    sid = 0
    for r in range(rows):
        lens = _courses(tile, 0.9, 2.4, rng) / tile
        cuts = (np.concatenate([[0], np.cumsum(lens)[:-1]]) + rng.random()) % 1.0
        cuts.sort()
        m = row == r
        uu = u[m]
        k = np.searchsorted(cuts, uu, side="right") - 1
        slab[m] = sid + (k % len(cuts))
        jd[m] = np.min(np.abs(((uu[:, None] - cuts[None, :]) + 0.5) % 1.0 - 0.5), axis=1) * tile
        sid += len(cuts)
    tone = rng.normal(0, 1, sid + 1)[slab]
    vein = np.abs(tx._noise(n, 0.08, 1.0, 1.6, rng))
    grain = tx._noise(n, 0.03, 1.0, 1.0, rng)
    cloud = tx._noise(n, 0.5, 1.0, 2.2, rng)
    c = np.array(color)
    lin = c * (1 + 0.09 * tone + 0.06 * grain + 0.07 * cloud)[..., None]
    lin = lin * (1 - 0.18 * (vein < 0.03))[..., None]
    joint = (np.minimum(vin, 1 - vin) * (tile / rows) < 0.0012) | (jd < 0.0012)
    lin[joint] *= 0.45
    return tx._save(name, tx._to_srgb(lin))


def ando_concrete(force=False, name="T_PH_Concrete_BaseColor", seed=79):
    """Tadao Ando's board-formed concrete: smooth, pale, faintly mottled; one tile = 1.82 m square =
    two 0.91 x 1.82 m form panels, each with its six tie holes (three across, two up, 2.4 cm)."""
    path = _path(name)
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    n = N
    u, v = _grid(n)
    W = 1.82
    x, y = u * W, v * W
    panel = np.floor(y / 0.91).astype(int)
    py = y - panel * 0.91
    tone = np.array([0.0, 1.0])[panel % 2] * rng.normal(0, 0.03) + rng.normal(0, 0.02, 2)[panel % 2]
    mott = tx._noise(n, 1.0, 1.0, 2.4, rng)
    fine = tx._noise(n, 1.0, 1.0, 0.6, rng)
    streak = tx._noise(n, 1.0, 0.04, 1.4, rng)                # faint vertical bleeding
    c = np.array([0.33, 0.325, 0.31])
    lin = c * (1 + 0.05 * mott + 0.025 * fine + 0.03 * streak + tone)[..., None]
    # form joints: a hairline (the panels' edges), slightly darker
    seam = (np.minimum(py, 0.91 - py) < 0.0015) | (np.minimum(x % W, W - x % W) < 0.0015)
    lin[seam] *= 0.82
    # tie holes: a dark ring round a slightly recessed cone
    for hx in (0.3, 0.91, 1.52):
        for hy in (0.2, 0.71):
            for p in range(2):
                d = np.hypot(((x - hx) + W / 2) % W - W / 2, ((y - (hy + p * 0.91)) + W / 2) % W - W / 2)
                lin = np.where((d < 0.012)[..., None], lin * 0.55, lin)
                lin = np.where(((d >= 0.012) & (d < 0.016))[..., None], lin * 0.8, lin)
    return tx._save(name, tx._to_srgb(lin))


def lime_plaster(force=False, name="T_PH_Red_BaseColor", seed=83, color=(0.30, 0.042, 0.026)):
    """Oxblood lime plaster (the Vals fire bath's red): soft clouds and trowel marks. Tile 2 m."""
    path = _path(name)
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    n = N
    cloud = tx._noise(n, 1.0, 1.0, 2.3, rng)
    trowel = tx._noise(n, 0.35, 1.0, 1.5, rng)
    fine = tx._noise(n, 1.0, 1.0, 0.5, rng)
    c = np.array(color)
    lin = c * (1 + 0.16 * cloud + 0.08 * trowel + 0.04 * fine)[..., None]
    lin[..., 0] *= 1 + 0.05 * cloud
    return tx._save(name, tx._to_srgb(lin))


def mosaic(force=False, name="T_PH_Mosaic_BaseColor", seed=89, tiles=20):
    """2.5 cm glazed tiles, deep teal-black with a few lighter ones, pale grey grout. Tile 0.5 m."""
    path = _path(name)
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    n = N
    u, v = _grid(n)
    i, j = np.floor(u * tiles).astype(int), np.floor(v * tiles).astype(int)
    fu, fv = (u * tiles) % 1.0, (v * tiles) % 1.0
    t = rng.normal(0, 1, (tiles, tiles))[j, i]
    light = (rng.random((tiles, tiles)) < 0.06)[j, i]
    c = np.array([0.016, 0.05, 0.05])
    lin = c * (1 + 0.22 * t)[..., None]
    lin = np.where(light[..., None], lin * 2.2, lin)
    # a soft glaze highlight toward each tile's top-left, darker edges
    edge = np.minimum(np.minimum(fu, 1 - fu), np.minimum(fv, 1 - fv))
    lin = lin * (0.85 + 0.25 * np.clip(edge / 0.15, 0, 1))[..., None]
    grout = edge < 0.06
    lin[grout] = np.array([0.11, 0.115, 0.11])
    return tx._save(name, tx._to_srgb(lin))
