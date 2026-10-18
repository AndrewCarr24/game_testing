"""Procedural, tileable texture maps written to PNG.

Generated with numpy (not Blender shader nodes) so the result is a plain image
that exports to glTF and looks the same in Blender and in the game engine.
Every map tiles seamlessly because all noise is built in the frequency domain.
"""
import os

import bpy
import numpy as np

TEX_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "textures"))


def _noise(n, scale_u, scale_v, beta, rng):
    """Periodic fractal noise in [-1, 1]. scale_u / scale_v stretch the
    features along u (columns) and v (rows): larger -> longer features."""
    white = rng.standard_normal((n, n))
    ky = np.fft.fftfreq(n)[:, None] * n
    kx = np.fft.fftfreq(n)[None, :] * n
    k = np.sqrt((kx * scale_u) ** 2 + (ky * scale_v) ** 2)
    k[0, 0] = 1.0
    spec = np.fft.fft2(white) / k ** beta
    spec[0, 0] = 0
    out = np.real(np.fft.ifft2(spec))
    return out / (np.abs(out).max() + 1e-9)


def _to_srgb(lin):
    lin = np.clip(lin, 0, 1)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)


def _save(name, rgb, non_color=False, fmt="PNG", quality=90, folder=None):
    folder = folder or TEX_DIR
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name + (".webp" if fmt == "WEBP" else ".png"))
    h, w, _ = rgb.shape
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, w, h, alpha=False)
    rgba = np.concatenate([rgb, np.ones((h, w, 1))], axis=2)
    img.pixels.foreach_set(rgba[::-1].astype(np.float32).ravel())  # Blender rows go bottom-up
    img.filepath_raw = path
    img.file_format = fmt
    img.save(quality=quality) if fmt == "WEBP" else img.save()
    bpy.data.images.remove(img)
    return path


def load(path, non_color=False):
    img = bpy.data.images.load(path, check_existing=True)
    img.reload()
    img.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    return img


def walnut(n=1024, seed=7, force=False):
    """Walnut albedo, grain running along u. One tile = 0.5 m."""
    path = os.path.join(TEX_DIR, "T_Walnut_BaseColor.png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    v = np.linspace(0, 1, n, endpoint=False)[:, None] * np.ones((1, n))
    warp = _noise(n, 0.015, 1.0, 2.0, rng)          # long, gentle figure
    rings = 0.5 + 0.5 * np.sin(2 * np.pi * (v * 46 + warp * 1.1))
    rings = rings ** 3.0                              # thin dark latewood lines
    streak = _noise(n, 0.02, 1.0, 0.8, rng)          # fine pore streaks
    blotch = _noise(n, 0.25, 1.0, 2.4, rng)          # broad colour drift
    t = np.clip(0.28 * (1 - rings) + 0.42 * (streak * 0.5 + 0.5) + 0.3 * (blotch * 0.5 + 0.5), 0, 1)
    dark = np.array([0.045, 0.019, 0.008])
    light = np.array([0.13, 0.06, 0.026])
    lin = dark + (light - dark) * t[..., None]
    return _save("T_Walnut_BaseColor", _to_srgb(lin))


def leather_normal(n=1024, seed=3, strength=2.5, force=False):
    """Pebbled leather grain normal map (OpenGL / glTF convention). One tile = 0.2 m."""
    path = os.path.join(TEX_DIR, "T_Leather_Normal.png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    pebble = _noise(n, 1.0, 1.0, 0.0, rng)
    # band-pass: keep features ~1-2 mm across
    spec = np.fft.fft2(pebble)
    k = np.sqrt((np.fft.fftfreq(n)[:, None] * n) ** 2 + (np.fft.fftfreq(n)[None, :] * n) ** 2)
    spec *= np.exp(-((k - 110) / 45) ** 2)
    h = np.real(np.fft.ifft2(spec))
    h = np.abs(h) ** 0.7 * np.sign(h)               # flatter tops, creased valleys
    h += 0.35 * _noise(n, 1.0, 1.0, 1.8, rng)        # soft wrinkles
    h /= np.abs(h).max()
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    nrm = np.stack([-dx, dy, np.ones_like(h)], axis=-1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    return _save("T_Leather_Normal", nrm * 0.5 + 0.5, non_color=True)


def oak_floor(n=1024, seed=11, force=False):
    """Wide-plank light oak, planks run along u. One tile = 2 m x 2 m,
    10 rows of 0.2 m planks, each 2 m long with a staggered butt joint."""
    path = os.path.join(TEX_DIR, "T_OakFloor_BaseColor.png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    rows = 10
    u = np.linspace(0, 1, n, endpoint=False)[None, :] * np.ones((n, 1))
    v = np.linspace(0, 1, n, endpoint=False)[:, None] * np.ones((1, n))
    row = np.floor(v * rows).astype(int)
    joint = rng.random(rows)                         # butt-joint position per row
    plank = (row * 2 + (u > joint[row])).astype(int)  # two plank ids per row
    tone = rng.uniform(-1, 1, rows * 2 + 2)[plank]
    phase = rng.uniform(0, 10, rows * 2 + 2)[plank]
    vin = (v * rows) % 1.0                            # position across the plank
    warp = _noise(n, 0.02, 1.0, 2.0, rng)
    rings = 0.5 + 0.5 * np.sin(2 * np.pi * (vin * 5 + phase + warp * 0.8))   # gentle, mostly straight grain
    rings = rings ** 3
    streak = _noise(n, 0.015, 1.0, 0.7, rng) * 0.5 + 0.5
    t = np.clip(0.18 * rings + 0.62 * streak + 0.2 * (tone * 0.5 + 0.5), 0, 1)
    light = np.array([0.46, 0.32, 0.185])
    dark = np.array([0.33, 0.215, 0.115])
    lin = dark + (light - dark) * t[..., None]
    lin *= (1 + 0.05 * tone)[..., None]
    # seams: 1.5 mm dark gaps along rows and at the butt joints
    px = 2.0 / n
    seam_v = (np.minimum(vin, 1 - vin) * (2.0 / rows)) < 0.0015
    du = np.abs(((u - joint[row]) + 0.5) % 1.0 - 0.5) * 2.0
    seam_u = (du < 0.0015) | ((np.minimum(u, 1 - u) * 2.0) < px)
    lin[seam_v | seam_u] *= 0.35
    return _save("T_OakFloor_BaseColor", _to_srgb(lin))


def marble(n=1024, seed=5, force=False):
    """White marble with soft grey veins. One tile = 1 m."""
    path = os.path.join(TEX_DIR, "T_Marble_BaseColor.png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 1, n, endpoint=False)[None, :] * np.ones((n, 1))
    y = np.linspace(0, 1, n, endpoint=False)[:, None] * np.ones((1, n))
    turb = _noise(n, 1.0, 1.0, 1.7, rng)
    turb2 = _noise(n, 1.0, 1.0, 1.4, rng)
    v1 = np.abs(np.sin(2 * np.pi * (2 * x + y + 1.4 * turb)))
    v2 = np.abs(np.sin(2 * np.pi * (x - 3 * y + 2.0 * turb2)))
    veins = 0.75 * (1 - v1) ** 14 + 0.35 * (1 - v2) ** 22
    cloud = _noise(n, 1.0, 1.0, 2.2, rng) * 0.5 + 0.5
    base = np.array([0.80, 0.79, 0.765]) * (0.94 + 0.06 * cloud)[..., None]
    vein_col = np.array([0.36, 0.36, 0.37])
    lin = base * (1 - veins[..., None]) + vein_col * veins[..., None]
    return _save("T_Marble_BaseColor", _to_srgb(lin))


def wool(n=1024, seed=9, force=False):
    """Heathered charcoal wool for rugs. One tile = 0.5 m."""
    path = os.path.join(TEX_DIR, "T_Wool_BaseColor.png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    fibre = _noise(n, 1.0, 1.0, 0.3, rng)
    loops = _noise(n, 1.0, 1.0, 1.2, rng)
    mottle = _noise(n, 1.0, 1.0, 2.4, rng)
    t = np.clip(0.5 + 0.35 * fibre + 0.25 * loops + 0.2 * mottle, 0, 1)
    dark = np.array([0.028, 0.029, 0.032])
    light = np.array([0.12, 0.118, 0.115])
    lin = dark + (light - dark) * (t ** 1.6)[..., None]
    return _save("T_Wool_BaseColor", _to_srgb(lin))


def wood(name, dark, light, n=1024, seed=21, rings=40, force=False):
    """Generic straight-grained hardwood albedo (grain along u). One tile = 0.5 m.
    dark / light: linear RGB of latewood / earlywood."""
    path = os.path.join(TEX_DIR, f"{name}.png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    v = np.linspace(0, 1, n, endpoint=False)[:, None] * np.ones((1, n))
    warp = _noise(n, 0.01, 1.0, 2.2, rng)
    # gentle warp so the grain stays mostly straight (strong warp reads as zebra stripes)
    ring = (0.5 + 0.5 * np.sin(2 * np.pi * (v * rings + warp * 0.35))) ** 3
    streak = _noise(n, 0.015, 1.0, 0.8, rng)
    blotch = _noise(n, 0.25, 1.0, 2.4, rng)
    t = np.clip(0.16 * (1 - ring) + 0.56 * (streak * 0.5 + 0.5) + 0.28 * (blotch * 0.5 + 0.5), 0, 1)
    lin = np.array(dark) + (np.array(light) - np.array(dark)) * t[..., None]
    return _save(name, _to_srgb(lin))


def fabric(name, n=1024, seed=17, strength=1.6, force=False):
    """Woven fabric normal map (fine plain weave + slubs). One tile = 0.25 m.
    Tint the material's base colour; this only adds the weave."""
    path = os.path.join(TEX_DIR, f"{name}.png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 1, n, endpoint=False)[None, :] * np.ones((n, 1))
    y = np.linspace(0, 1, n, endpoint=False)[:, None] * np.ones((1, n))
    threads = 180
    warp_t = np.sin(2 * np.pi * x * threads) * (0.5 + 0.5 * np.sign(np.sin(np.pi * y * threads)))
    weft_t = np.sin(2 * np.pi * y * threads) * (0.5 - 0.5 * np.sign(np.sin(np.pi * x * threads)))
    h = 0.5 * (np.abs(warp_t) + np.abs(weft_t)) + 0.35 * _noise(n, 0.05, 1.0, 1.2, rng)
    h /= np.abs(h).max()
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    nrm = np.stack([-dx, dy, np.ones_like(h)], axis=-1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    return _save(name, nrm * 0.5 + 0.5, non_color=True)


def grass(n=512, seed=31, force=False):
    """Mown lawn albedo: fine blades, clover-ish clumps and faint dry patches. One tile
    = 3 m. (The engine adds the mowing stripes and large-scale variation, so the tile
    doesn't repeat visibly across a big lawn.)"""
    path = os.path.join(TEX_DIR, "T_Grounds_Grass_BaseColor.png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    # fine detail only: anything large in a 3 m tile repeats visibly across the lawn
    blades = _noise(n, 1.0, 0.35, 0.2, rng)          # fine, slightly streaky
    clumps = _noise(n, 1.0, 1.0, 0.9, rng)
    t = np.clip(0.5 + 0.34 * blades + 0.22 * clumps, 0, 1)
    dark = np.array([0.020, 0.048, 0.011])
    light = np.array([0.070, 0.140, 0.028])
    lin = dark + (light - dark) * t[..., None]
    return _save("T_Grounds_Grass_BaseColor", _to_srgb(lin))


def hedge(n=512, seed=37, force=False):
    """Clipped boxwood/yew hedge albedo: small dark leaves with lit edges and deep gaps.
    One tile = 1.5 m."""
    path = os.path.join(TEX_DIR, "T_Grounds_Hedge_BaseColor.png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    leaves = _noise(n, 1.0, 1.0, 0.6, rng)
    clusters = _noise(n, 1.0, 1.0, 1.6, rng)
    t = np.clip(0.5 + 0.45 * leaves + 0.3 * clusters, 0, 1) ** 1.4
    dark = np.array([0.006, 0.016, 0.006])
    light = np.array([0.050, 0.100, 0.025])
    lin = dark + (light - dark) * t[..., None]
    return _save("T_Grounds_Hedge_BaseColor", _to_srgb(lin))


def gravel(n=512, seed=41, force=False):
    """Pale raked gravel / decomposed granite: small stones, a few darker, faint rake
    lines. One tile = 2 m."""
    path = os.path.join(TEX_DIR, "T_Out_Gravel_BaseColor.png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    stones = _noise(n, 1.0, 1.0, 0.1, rng)
    clumps = _noise(n, 1.0, 1.0, 0.8, rng)
    v = np.linspace(0, 1, n, endpoint=False)[:, None] * np.ones((1, n))
    rake = 0.5 + 0.5 * np.sin(2 * np.pi * v * 40)
    t = np.clip(0.55 + 0.35 * stones + 0.15 * clumps + 0.06 * rake, 0, 1)
    dark = np.array([0.20, 0.18, 0.15])
    light = np.array([0.62, 0.58, 0.51])
    lin = dark + (light - dark) * t[..., None]
    return _save("T_Out_Gravel_BaseColor", _to_srgb(lin))
