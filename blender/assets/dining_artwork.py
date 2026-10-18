"""Large abstract canvas for the dining room wall: soft-edged colour fields (deep olive,
ochre, rust, bone) with dry-brush texture, in a black-metal shadow-gap float frame.

Hangs on a wall. Origin: centre of the canvas on the wall plane; the picture faces -Y
and spans +-w/2 in X and +-h/2 in Z (it stands 4.5 cm off the wall). Units are metres.
"""
import importlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(materials)
importlib.reload(textures)

NAME = "DiningArtwork"

P = dict(name=NAME, size=(2.4, 1.5), canvas_t=0.035, frame_face=0.018, gap=0.016, seed=12)


def paint(n=1024, seed=12, force=False):
    path = os.path.join(textures.TEX_DIR, "T_Dining_Art.png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n] / n          # y: 0 top .. 1 bottom (image rows)
    brush = textures._noise(n, 0.02, 1.0, 0.9, rng)       # horizontal dry-brush streaks
    cloud = textures._noise(n, 1.0, 1.0, 2.0, rng)
    grain = textures._noise(n, 1.0, 1.0, 0.4, rng)

    def soft(v, a, b, s):           # smooth step window a..b along a coordinate
        return 1 / (1 + np.exp(-(v - a) / s)) * (1 - 1 / (1 + np.exp(-(v - b) / s)))

    wob = 0.010 * cloud
    bone = np.array([0.50, 0.43, 0.32])
    olive = np.array([0.040, 0.055, 0.028])
    ochre = np.array([0.46, 0.25, 0.05])
    rust = np.array([0.27, 0.065, 0.03])
    ink = np.array([0.018, 0.024, 0.036])
    bronze = np.array([0.30, 0.17, 0.07])

    lin = np.broadcast_to(bone, (n, n, 3)).copy()
    lin = lin * (1 - 0.45 * np.clip(y * 1.1 + cloud * 0.3, 0, 1)[..., None]) + ochre * (0.45 * np.clip(y * 1.1 + cloud * 0.3, 0, 1)[..., None])

    def blend(m, col, amt=0.95):
        nonlocal lin
        m = (m * amt)[..., None]
        lin = lin * (1 - m) + col * m

    blend(soft(x + wob, -0.1, 0.40, 0.012), olive)                                   # tall olive field
    d = np.sqrt(((x - 0.64) * 1.6) ** 2 + (y - 0.56) ** 2) + wob
    blend(1 - 1 / (1 + np.exp(-(d - 0.30) / 0.005)), rust)                            # terracotta disc
    d2 = np.sqrt(((x - 0.82) * 1.6) ** 2 + (y - 0.27) ** 2) + wob
    blend(1 - 1 / (1 + np.exp(-(d2 - 0.13) / 0.005)), ochre, 0.9)                     # ochre moon
    d3 = np.sqrt(((x - 0.64) * 1.6) ** 2 + (y - 0.56) ** 2) + wob
    blend((1 - 1 / (1 + np.exp(-(d3 - 0.305) / 0.003))) * (1 / (1 + np.exp(-(d3 - 0.295) / 0.003))), bronze, 0.8)
    blend(soft(x + wob, 0.47, 1.1, 0.01) * soft(y + wob, 0.80, 0.88, 0.006), ink)     # dark band
    blend(soft(x + wob, 0.47, 1.1, 0.01) * soft(y + wob, 0.89, 0.905, 0.004), bronze, 0.9)
    # dry brush: streaks lighten/darken, edges break up
    lin *= (1 + 0.14 * brush[..., None] + 0.06 * grain[..., None])
    lin = np.clip(lin, 0, 1)
    return textures._save("T_Dining_Art", textures._to_srgb(lin))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    path = paint(seed=p["seed"])
    canvas_mat = common.pbr_material("M_Dining_Canvas", (0.5, 0.45, 0.4), roughness=0.85)
    common.set_base_color_map(canvas_mat, textures.load(path))
    black = materials.black_metal()

    w, h = p["size"]
    ct, ff, gap = p["canvas_t"], p["frame_face"], p["gap"]
    spacer = 0.012
    cy = -(spacer + ct / 2)
    # the canvas: a box; the front face carries the painting (planar UV), sides are painted edge
    canvas = common.mesh_object(f"{n}_Canvas", common.box_bmesh((w, ct, h)), col, canvas_mat, root, smooth=False)
    canvas.location = (0, cy, 0)
    me = canvas.data
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (co.x / w + 0.5, co.z / h + 0.5)
    # float frame: four thin black-metal bars around the canvas with a shadow gap
    fw, fh = w + 2 * gap + 2 * ff, h + 2 * gap + 2 * ff
    fd = ct + 0.012
    bars = [((fw, fd, ff), (0, 0, (h / 2 + gap + ff / 2))), ((fw, fd, ff), (0, 0, -(h / 2 + gap + ff / 2))),
            ((ff, fd, h + 2 * gap), (-(w / 2 + gap + ff / 2), 0, 0)),
            ((ff, fd, h + 2 * gap), ((w / 2 + gap + ff / 2), 0, 0))]
    for i, (size, loc) in enumerate(bars):
        b = common.mesh_object(f"{n}_Frame{i}", common.box_bmesh(size), col, black, root)
        b.location = (loc[0], cy - 0.003, loc[2])
        common.add_bevel(b, 0.002, 2)
        common.box_uv(b, 0.5)
    # hidden spacer so nothing floats
    sp = common.mesh_object(f"{n}_Spacer", common.box_bmesh((w * 0.6, spacer + 0.004, h * 0.6)), col, black, root)
    sp.location = (0, -(spacer + 0.004) / 2 + 0.002, 0)
    common.box_uv(sp, 0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
