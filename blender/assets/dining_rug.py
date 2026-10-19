"""Dining rug: a dense, low wool pile in warm greige with soft cloudy tone-on-tone
movement and a fine bronze-brown double border line. Origin is the floor centre; the
base colour and normal maps are mapped once across the whole rug (planar UVs).
"""
import importlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, textures  # noqa: E402

importlib.reload(common)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rug as rug_mod  # noqa: E402  (shared bound-edge rug mesh)

importlib.reload(rug_mod)
importlib.reload(textures)

NAME = "DiningRug"

P = dict(name=NAME, size=(7.2, 3.9), thickness=0.014, corner=0.04, bevel=0.005)


def _band(n, size, rng, wavelength, width=0.5):
    """Isotropic (in metres) band-passed noise in [-1, 1]."""
    w, d = size
    white = rng.standard_normal((n, n))
    kx = np.fft.fftfreq(n)[None, :] * n / w
    ky = np.fft.fftfreq(n)[:, None] * n / d
    k = np.sqrt(kx ** 2 + ky ** 2)
    f0 = 1.0 / wavelength
    spec = np.fft.fft2(white) * np.exp(-0.5 * (np.log((k + 1e-6) / f0) / width) ** 2)
    out = np.real(np.fft.ifft2(spec))
    return out / (np.abs(out).max() + 1e-9)


def make_textures(size, n=1024, seed=44, force=False):
    base_path = os.path.join(textures.TEX_DIR, "T_Dining_Rug_BaseColor.png")
    nrm_path = os.path.join(textures.TEX_DIR, "T_Dining_Rug_Normal.png")
    if os.path.exists(base_path) and os.path.exists(nrm_path) and not force:
        return base_path, nrm_path
    rng = np.random.default_rng(seed)
    w, d = size
    x = ((np.arange(n) + 0.5) / n - 0.5) * w
    y = (0.5 - (np.arange(n) + 0.5) / n) * d
    X, Y = np.broadcast_to(x[None, :], (n, n)), np.broadcast_to(y[:, None], (n, n))
    edge = np.minimum(w / 2 - np.abs(X), d / 2 - np.abs(Y))

    fibre = _band(n, size, rng, 0.012, 0.5)
    tuft = _band(n, size, rng, 0.035, 0.5)
    cloud = _band(n, size, rng, 0.9, 0.8)       # soft movement across the field
    cloud2 = _band(n, size, rng, 0.35, 0.7)
    wob = 0.002 * _band(n, size, rng, 0.3, 0.6)
    e = edge + wob
    line1 = np.clip(1 - np.abs(e - 0.11) / 0.012, 0, 1) ** 1.5
    line2 = np.clip(1 - np.abs(e - 0.145) / 0.007, 0, 1) ** 1.5
    band = ((e > 0.11) & (e < 0.145)).astype(float)

    h = 0.5 * tuft + 0.45 * fibre + 0.2 * cloud2 - 0.5 * (line1 + line2)
    h /= np.abs(h).max()

    greige = np.array([0.215, 0.185, 0.150])       # linear
    deep = np.array([0.095, 0.080, 0.062])
    line_col = np.array([0.27, 0.17, 0.085])       # bronze
    t = np.clip(0.55 + 0.20 * tuft + 0.22 * fibre + 0.30 * cloud + 0.18 * cloud2, 0, 1)
    lin = deep + (greige - deep) * t[..., None]
    lin = lin * (1 - 0.35 * (e < 0.09)[..., None] * 0)      # (outer margin keeps the field colour)
    k = np.clip(line1 + line2, 0, 1)[..., None]
    lin = lin * (1 - 0.8 * k) + line_col * 0.8 * k
    lin *= (1 - 0.18 * np.clip(1 - edge / 0.02, 0, 1))[..., None]

    sx, sy = w / n, d / n
    s = 0.0065
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * sx) * s
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * sy) * s
    nrm = np.stack([-dx, dy, np.ones_like(h)], axis=-1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    textures._save("T_Dining_Rug_BaseColor", textures._to_srgb(lin))
    textures._save("T_Dining_Rug_Normal", nrm * 0.5 + 0.5)
    return base_path, nrm_path


def _planar_uv(ob, size):
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

    base_path, nrm_path = make_textures(p["size"])
    wool = common.pbr_material("M_Wool_Greige_Dining", (0.2, 0.18, 0.15), roughness=1.0)
    common.set_base_color_map(wool, textures.load(base_path))
    common.set_normal_map(wool, textures.load(nrm_path, non_color=True), 1.0)
    bsdf = next(nd for nd in wool.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Sheen Weight"].default_value = 0.5
    bsdf.inputs["Sheen Roughness"].default_value = 0.5

    w, d = p["size"]
    rug = common.mesh_object(f"{n}_Body", rug_mod.rug_bmesh(w, d, p["thickness"], max(p["corner"], 0.03),
                                                          roll=min(p["bevel"], 0.003)), col, wool, root)
    _planar_uv(rug, p["size"])
    return root, [rug]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
