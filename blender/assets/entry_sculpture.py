"""Entry sculpture: a polished-bronze trefoil knot (a swept tube) standing on a
honed limestone plinth. About 2.2 m tall, 1.3 m wide. The plinth uses the entry's
limestone (`M_Entry_Limestone`, texture T_Entry_Limestone, generated here when
missing and shared with the entry floor).

Origin: floor centre of the plinth. Units are metres.
"""
import importlib
import math
import os
import sys

import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(materials)
importlib.reload(textures)

NAME = "EntrySculpture"

P = dict(
    name=NAME,
    plinth=(0.62, 0.62, 0.92),
    scale=0.205,            # trefoil units -> metres
    tube_r=0.034,
    points=220,
    steps=0.04,
)


# ------------------------------------------------------------------ limestone texture

def limestone(n=1024, seed=19, force=False):
    """Pale honed limestone, 1 m slabs in a running bond. One tile = 2 m x 2 m
    (two rows of two slabs). Albedo only; tiny pits and soft cloudy bedding."""
    name = "T_Entry_Limestone"
    path = os.path.join(textures.TEX_DIR, name + ".png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    u = np.linspace(0, 1, n, endpoint=False)[None, :] * np.ones((n, 1))
    v = np.linspace(0, 1, n, endpoint=False)[:, None] * np.ones((1, n))
    row = np.floor(v * 2).astype(int)
    col = np.floor((u + 0.25 * row) * 2).astype(int) % 2            # offset joints on the second row
    slab = (row * 2 + col)
    tone = rng.uniform(-1, 1, 4)[slab]
    cloud = textures._noise(n, 1.0, 1.0, 2.0, rng) * 0.5 + 0.5
    bed = textures._noise(n, 0.08, 1.0, 1.6, rng) * 0.5 + 0.5          # faint horizontal bedding
    fine = textures._noise(n, 1.0, 1.0, 0.5, rng)
    pits = (textures._noise(n, 1.0, 1.0, 0.1, rng) > 0.93).astype(float)
    base = np.array([0.80, 0.765, 0.69])
    warm = np.array([0.76, 0.70, 0.60])
    t = np.clip(0.55 * cloud + 0.35 * bed + 0.1 * (tone * 0.5 + 0.5), 0, 1)
    rgb = base + (warm - base) * t[..., None]
    rgb *= (1 + 0.025 * tone + 0.02 * fine)[..., None]
    rgb *= (1 - 0.18 * pits)[..., None]
    # seams: ~3 mm darker joints (2 m tile: 1 px = 2 mm)
    jw = 1.6 / n
    d_v = np.minimum((v * 2) % 1.0, 1 - (v * 2) % 1.0) / 2        # metres/2 -> tile fraction
    d_u = np.minimum(((u + 0.25 * row) * 2) % 1.0, 1 - ((u + 0.25 * row) * 2) % 1.0) / 2
    seam = (d_v < jw) | (d_u < jw)
    rgb[seam] *= 0.78
    return textures._save(name, np.clip(rgb, 0, 1))


def limestone_material():
    m = common.pbr_material("M_Entry_Limestone", (0.80, 0.765, 0.69), roughness=0.78)
    common.set_base_color_map(m, textures.load(limestone()))
    return m


# ------------------------------------------------------------------------- build

def trefoil(t, s):
    x = math.sin(t) + 2 * math.sin(2 * t)
    y = math.cos(t) - 2 * math.cos(2 * t)
    z = -math.sin(3 * t)
    return Vector((x * s, z * s * 1.5, y * s))      # knot in the XZ plane, depth along Y


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    stone = limestone_material()
    bronze = common.pbr_material("M_Entry_Bronze_Polished", (0.50, 0.30, 0.14), roughness=0.2, metallic=1.0)
    black = materials.black_metal()

    pw, pd, ph = p["plinth"]
    plinth = common.mesh_object(f"{n}_Plinth", common.box_bmesh((pw, pd, ph - 0.03)), col, stone, root, smooth=False)
    plinth.location = (0, 0, 0.03 + (ph - 0.03) / 2)
    common.add_bevel(plinth, 0.004, segments=2)
    common.box_uv(plinth, tile=8.0)       # a small patch of the texture, kept inside one slab (no joints)
    uvl = plinth.data.uv_layers["UVMap"]
    for d in uvl.data:
        d.uv = (d.uv[0] + 0.22, d.uv[1] + 0.22)
    base = common.mesh_object(f"{n}_Base", common.box_bmesh((pw - 0.08, pd - 0.08, 0.03)), col, black, root, smooth=False)
    base.location = (0, 0, 0.015)

    s = p["scale"]
    N = p["points"]
    pts = [trefoil(2 * math.pi * i / N, s) for i in range(N)]
    zmin = min(v.z for v in pts)
    lift = ph + p["tube_r"] + 0.05 - zmin
    pts = [Vector((v.x, v.y, v.z + lift)) for v in pts]
    knot = common.tube_object(f"{n}_Knot", [tuple(v) for v in pts], p["tube_r"], col, bronze, root, closed=True,
                              profile_res=3)
    # a short bronze pin from the plinth up into the lowest part of the knot
    low = min(pts, key=lambda v: v.z)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.016, radius2=0.016, depth=0.09,
                          matrix=__import__("mathutils").Matrix.Translation((low.x, low.y, ph + 0.045)))
    common.mesh_object(f"{n}_Pin", bm, col, bronze, root)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
