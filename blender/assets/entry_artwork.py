"""Monumental entry painting: a 3.4 x 2.3 m gallery-wrapped abstract canvas (ink-blue
field under an oat sky, a terracotta sun, a bronze horizon line) floating on a recessed
black backer so a shadow gap reads round it.

Painted with numpy into T_Entry_Art (1024 x 768), regenerated only when missing.
Hangs on a wall: origin = the centre of the picture on the wall plane, the picture
faces -Y and extends +-w/2 in X and +-h/2 in Z. Units are metres.
"""
import importlib
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)

NAME = "EntryArtwork"

P = dict(
    name=NAME,
    size=(3.4, 2.3),
    canvas_t=0.045,
    backer_inset=0.12,
    backer_t=0.035,
    tex="T_Entry_Art",
    style="sun",
    seed=41,
)


def paint(name, size_px=(1024, 768), seed=41, force=False):
    path = os.path.join(textures.TEX_DIR, name + ".png")
    if os.path.exists(path) and not force:
        return path
    w, h = size_px
    rng = np.random.default_rng(seed)
    n = 1024

    def noise(beta, ax, ay):
        a = textures._noise(n, ax, ay, beta, rng)[:h, :w]
        return a

    ys, xs = np.mgrid[0:h, 0:w]
    aspect = 3.4 / 2.3
    X = xs / w * aspect
    Y = ys / h                        # 0 top .. 1 bottom; X runs 0..w/h
    grain = noise(1.2, 0.03, 1.0)     # horizontal dry-brush streaks
    cloud = noise(2.2, 1.0, 1.0)
    fine = noise(0.6, 1.0, 1.0)

    def mix(a, b, t):
        t = np.clip(t, 0, 1)[..., None]
        return np.array(a) * (1 - t) + np.array(b) * t

    # sky: oat to a warmer sand toward the horizon, mottled
    sky = mix((0.80, 0.74, 0.63), (0.86, 0.70, 0.52), Y * 1.6 + cloud * 0.35)
    # sun: a terracotta disc with a soft edge and a pale glow
    sx, sy, sr = 0.64 * aspect, 0.37, 0.19
    d = np.sqrt((X - sx) ** 2 + (Y - sy) ** 2)
    glow = np.exp(-((d - sr) / 0.22) ** 2) * (d > sr) * 0.35
    img = sky + glow[..., None] * np.array([0.10, 0.04, -0.02])
    disc = textures_smooth(sr - 0.006, sr + 0.006, d)
    sun = mix((0.74, 0.34, 0.20), (0.62, 0.24, 0.15), (Y - (sy - sr)) / (2 * sr) + cloud * 0.3)
    img = img * disc[..., None] + sun * (1 - disc[..., None])
    # sea: an ink-blue field with a wavy upper edge and layered glazes
    edge = 0.56 + 0.03 * noise(3.0, 0.5, 1.0) * 3.0 + 0.01 * np.sin(X * 9)
    sea_t = textures_smooth(edge - 0.004, edge + 0.004, Y)
    sea = mix((0.055, 0.085, 0.16), (0.13, 0.19, 0.30), (Y - edge) * 2.0 + cloud * 0.5)
    # a lighter reflected band under the sun
    refl = np.exp(-((X - sx) / 0.10) ** 2) * np.exp(-((Y - edge - 0.07) / 0.09) ** 2)
    sea = sea + refl[..., None] * np.array([0.35, 0.16, 0.08]) * (0.6 + 0.4 * grain[..., None])
    img = img * (1 - sea_t[..., None]) + sea * sea_t[..., None]
    # bronze horizon line
    line = textures_smooth(0.003, 0.0, np.abs(Y - edge + 0.012))
    img = img * (1 - line[..., None] * 0.9) + np.array([0.55, 0.38, 0.20]) * line[..., None] * 0.9
    # paint texture
    img = img * (1 + 0.05 * grain[..., None] + 0.025 * fine[..., None])
    img = np.clip(img, 0, 1)
    return textures._save(name, img)


def paint_ink(name, size_px=(768, 1024), seed=57, force=False):
    """Portrait ink-wash: a dry-brush enso on rice paper with a gold-leaf panel."""
    path = os.path.join(textures.TEX_DIR, name + ".png")
    if os.path.exists(path) and not force:
        return path
    w, h = size_px
    rng = np.random.default_rng(seed)
    n = 1024

    def noise(beta, ax, ay):
        return textures._noise(n, ax, ay, beta, rng)[:h, :w]

    ys, xs = np.mgrid[0:h, 0:w]
    aspect = 1.3 / 1.8
    X = xs / w * aspect
    Y = ys / h
    fibre = noise(0.8, 1.0, 1.0)
    cloud = noise(2.2, 1.0, 1.0)
    paper = np.array([0.88, 0.84, 0.76])[None, None, :] * (1 + 0.03 * fibre[..., None] + 0.03 * cloud[..., None])
    # gold-leaf panel: a tall rectangle at the upper right, broken into leaf squares
    gx0, gx1, gy0, gy1 = 0.52 * aspect, 0.93 * aspect, 0.07, 0.55
    inside = (X > gx0) & (X < gx1) & (Y > gy0) & (Y < gy1)
    cell = (np.floor((X - gx0) / 0.034) * 7 + np.floor((Y - gy0) / 0.034)) % 5
    leaf = np.array([0.72, 0.56, 0.27])[None, None, :] * (0.88 + 0.025 * cell[..., None] + 0.10 * cloud[..., None])
    seam = ((((X - gx0) % 0.034) < 0.0010) | (((Y - gy0) % 0.034) < 0.0010))
    leaf = np.where(seam[..., None], leaf * 0.82, leaf)
    img = np.where(inside[..., None], leaf, paper)
    # enso: a broad dry-brush ring, thinning toward its open end
    cx, cy, R = 0.46 * aspect, 0.55, 0.215
    dx, dy = X - cx, Y - cy
    d = np.sqrt(dx ** 2 + dy ** 2)
    th = (np.arctan2(dy, dx) + math.radians(-60)) % (2 * math.pi)
    t = th / (2 * math.pi * 0.94)
    width = 0.044 * (1 - 0.82 * t ** 1.5)
    wob = 0.012 * noise(2.5, 0.6, 0.6) * 3
    core = (np.abs(d - R - wob) < width) & (t < 1.0)
    edge = textures_smooth(width, width * 0.55, np.abs(d - R - wob))
    # dry-brush streaks follow the stroke: modulate by angle/radius noise
    streak = noise(1.0, 0.04, 1.0)
    dry = np.clip(0.9 - 0.9 * np.clip(t, 0, 1) ** 2 + 0.35 * streak, 0, 1)
    ink_a = edge * (t < 1.0) * np.clip(dry * 1.6, 0, 1)
    ink = np.array([0.035, 0.035, 0.04])[None, None, :]
    img = img * (1 - ink_a[..., None]) + ink * ink_a[..., None]
    # a small red seal
    seal = (X > 0.84 * aspect) & (X < 0.90 * aspect) & (Y > 0.86) & (Y < 0.915)
    img = np.where(seal[..., None], np.array([0.62, 0.12, 0.08])[None, None, :], img)
    return textures._save(name, np.clip(img, 0, 1))


def textures_smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def planar_uv(ob, w, h):
    uv = ob.data.uv_layers.get("UVMap") or ob.data.uv_layers.new(name="UVMap")
    for poly in ob.data.polygons:
        for li in poly.loop_indices:
            co = ob.data.vertices[ob.data.loops[li].vertex_index].co
            uv.data[li].uv = (co.x / w + 0.5, co.z / h + 0.5)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    w, h = p["size"]

    canvas_m = common.pbr_material("M_Entry_Canvas" if p["style"] == "sun" else "M_Entry_Canvas_Ink", (1, 1, 1), roughness=0.85)
    painter = paint_ink if p["style"] == "ink" else paint
    common.set_base_color_map(canvas_m, textures.load(painter(p["tex"], seed=p["seed"])))
    black = materials.black_metal()

    bt, ct = p["backer_t"], p["canvas_t"]
    ins = p["backer_inset"]
    backer = common.mesh_object(f"{n}_Backer", common.box_bmesh((w - 2 * ins, bt, h - 2 * ins)), col, black, root,
                                smooth=False)
    backer.location = (0, -bt / 2, 0)
    canvas = common.mesh_object(f"{n}_Canvas", common.box_bmesh((w, ct, h)), col, canvas_m, root, smooth=False)
    canvas.location = (0, -(bt + ct / 2), 0)
    common.add_bevel(canvas, 0.004, segments=2)
    planar_uv(canvas, w, h)

    parts = [backer, canvas]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
