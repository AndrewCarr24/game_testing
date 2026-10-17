"""Bedroom rug: thick oat/cream wool with a quiet tone-on-tone inset border.
Origin is the floor centre. The base colour and normal maps are mapped once
across the whole rug (planar UVs), so the border always hugs the edge."""
import importlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)

NAME = "BedroomRug"

P = dict(name=NAME, size=(3.2, 2.6), thickness=0.015, corner=0.05, bevel=0.005)


# ------------------------------------------------------------------ textures

def _grids(n, size):
    """World-space metre coordinates (x, y) of every texel, row 0 = +Y edge."""
    w, d = size
    x = ((np.arange(n) + 0.5) / n - 0.5) * w
    y = (0.5 - (np.arange(n) + 0.5) / n) * d
    return np.broadcast_to(x[None, :], (n, n)), np.broadcast_to(y[:, None], (n, n))


def _band(n, size, rng, wavelength, width=0.45):
    """Isotropic (in metres) band-passed noise in [-1, 1]: tufts of roughly
    `wavelength` metres. Texture is stretched over a non-square rug, so the
    frequency axes are scaled by the rug dimensions."""
    w, d = size
    white = rng.standard_normal((n, n))
    kx = np.fft.fftfreq(n)[None, :] * n / w      # cycles per metre along x
    ky = np.fft.fftfreq(n)[:, None] * n / d
    k = np.sqrt(kx ** 2 + ky ** 2)
    f0 = 1.0 / wavelength
    spec = np.fft.fft2(white) * np.exp(-0.5 * (np.log((k + 1e-6) / f0) / width) ** 2)
    out = np.real(np.fft.ifft2(spec))
    return out / (np.abs(out).max() + 1e-9)


def _layout(n, size):
    """Pattern masks: border line grooves and a field/border split, in metres."""
    w, d = size
    x, y = _grids(n, size)
    edge = np.minimum(np.minimum(w / 2 - np.abs(x), d / 2 - np.abs(y)), 1.0)  # distance to edge
    # rounded inner corners: use the rounded-box distance
    def groove(centre, half_w):
        return np.clip(1.0 - np.abs(edge - centre) / half_w, 0, 1)
    return x, y, edge, groove


def bedroom_rug(size=P["size"], n=1024, seed=31, force=False):
    """Writes T_BedroomRug_BaseColor and T_BedroomRug_Normal; returns both paths."""
    base_path = os.path.join(textures.TEX_DIR, "T_BedroomRug_BaseColor.png")
    nrm_path = os.path.join(textures.TEX_DIR, "T_BedroomRug_Normal.png")
    if os.path.exists(base_path) and os.path.exists(nrm_path) and not force:
        return base_path, nrm_path

    rng = np.random.default_rng(seed)
    x, y, edge, groove = _layout(n, size)

    # --- pile height map -----------------------------------------------------
    tuft = _band(n, size, rng, 0.020, 0.5)       # loops / tufts ~2 cm
    fibre = _band(n, size, rng, 0.0075, 0.45)    # individual yarn ~7 mm
    pile = _band(n, size, rng, 0.055, 0.6)       # pile lying different ways ~5 cm
    lump = _band(n, size, rng, 0.16, 0.7)        # soft undulation
    h = 0.50 * tuft + 0.45 * fibre + 0.35 * pile + 0.2 * lump

    # --- pattern -------------------------------------------------------------
    # inset border: sculpted (slightly lower, tighter pile) strip between two
    # carved grooves, then the open field with broad pile-direction stripes.
    wob = 0.0015 * _band(n, size, rng, 0.25, 0.6)           # hand-made wobble
    e = edge + wob
    g1 = np.clip(1 - np.abs(e - 0.075) / 0.013, 0, 1) ** 1.5    # outer groove
    g2 = np.clip(1 - np.abs(e - 0.205) / 0.013, 0, 1) ** 1.5    # inner groove
    border = ((e > 0.075) & (e < 0.205)).astype(float)
    border = border * 1.0
    # soften the strip edges a touch
    in_field = (e >= 0.205).astype(float)

    stripe_w = 0.26
    stripes = np.where((np.floor(y / stripe_w + 0.37) % 2) == 0, 1.0, 0.0)
    stripes = (stripes - 0.5)
    # soften stripe transitions with a small blur along y
    ky = np.fft.fftfreq(n)[:, None] * n / size[1]
    kernel = np.exp(-0.5 * (ky * 0.012) ** 2 * (2 * np.pi) ** 2)
    stripes = np.real(np.fft.ifft2(np.fft.fft2(stripes) * kernel))

    # height: grooves are carved down, border strip a little lower
    h = h - 0.7 * (g1 + g2) - 0.25 * border
    h /= np.abs(h).max()

    # --- albedo ---------------------------------------------------------------
    oat = np.array([0.60, 0.475, 0.31])          # linear, warm cream-oat
    deep = np.array([0.26, 0.19, 0.115])         # shadow between tufts / grooves
    t = 0.5 + 0.30 * tuft + 0.30 * fibre + 0.30 * pile + 0.15 * lump
    t = np.clip(t, 0, 1)
    # tone-on-tone: border strip a little warmer/darker, field stripes +-3 %
    tone = 1.0 + 0.06 * stripes * in_field - 0.07 * border + 0.02 * (lump * in_field)
    cavity = np.clip(0.5 - 0.5 * h, 0, 1)        # darker in the low pile
    lin = deep[None, None, :] + (oat - deep)[None, None, :] * (0.30 + 0.70 * t[..., None])
    lin = lin * (1 - 0.22 * g1[..., None] - 0.22 * g2[..., None])
    lin = lin * (0.90 + 0.10 * (1 - cavity)[..., None]) * tone[..., None]
    # the outermost 3 mm darkens a little, as if the pile turned under at the edge
    lin *= (1 - 0.15 * np.clip(1 - edge / 0.02, 0, 1))[..., None]

    # --- normal map -----------------------------------------------------------
    sx, sy = size[0] / n, size[1] / n           # metres per texel
    strength = 0.0075
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * sx) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * sy) * strength
    # image rows run down (-y); OpenGL normal map wants +v up, so flip dy
    nrm = np.stack([-dx, dy, np.ones_like(h)], axis=-1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)

    textures._save("T_BedroomRug_BaseColor", textures._to_srgb(lin))
    textures._save("T_BedroomRug_Normal", nrm * 0.5 + 0.5)
    return base_path, nrm_path


# --------------------------------------------------------------------- model

def _planar_uv(ob, size):
    """One planar projection over the whole rug: u = x/w + .5, v = y/d + .5."""
    me = ob.data
    w, d = size
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (co.x / w + 0.5, co.y / d + 0.5)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    base_path, nrm_path = bedroom_rug(p["size"])
    wool = common.pbr_material("M_Wool_Oat", (0.45, 0.40, 0.32), roughness=1.0)
    common.set_base_color_map(wool, textures.load(base_path))
    common.set_normal_map(wool, textures.load(nrm_path, non_color=True), 1.0)
    bsdf = next(nd for nd in wool.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Sheen Weight"].default_value = 0.7        # soft fibre halo at grazing angles
    bsdf.inputs["Sheen Roughness"].default_value = 0.5
    bsdf.inputs["Sheen Tint"].default_value = (0.75, 0.68, 0.55, 1)

    w, d = p["size"]
    rug = common.mesh_object(f"{n}_Body",
                             common.rounded_slab_bmesh(w, d, p["thickness"], p["corner"]),
                             col, wool, root)
    rug.location = (0, 0, p["thickness"] / 2)
    common.add_bevel(rug, p["bevel"], segments=3)
    _planar_uv(rug, p["size"])

    parts = [rug]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
