"""Fiddle-leaf fig in a limestone planter: a slender trunk, ~50 big glossy leaves
painted with a small leaf texture (T_Library_Leaf, double-sided). Origin: floor centre.
About 0.55 x 0.55 x 1.95 m."""
import importlib
import math
import os
import random
import sys

import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import library_kit as kit  # noqa: E402
from library_kit import Mesh, common, materials, textures  # noqa: E402

importlib.reload(kit)

NAME = "LibraryPlant"

P = dict(name=NAME, seed=3, leaves=66, height=1.95, pot_r=0.23, pot_h=0.46)


def leaf_texture(n=256, force=False):
    path = os.path.join(textures.TEX_DIR, "T_Library_Leaf.png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(12)
    u = np.linspace(-1, 1, n)[None, :] * np.ones((n, 1))        # across the leaf
    v = np.linspace(0, 1, n)[:, None] * np.ones((1, n))         # along it (0 = base at the bottom row)
    base = np.array([0.018, 0.085, 0.022])
    light = np.array([0.06, 0.20, 0.05])
    rib = np.exp(-(u / 0.035) ** 2)
    veins = np.exp(-((((np.abs(u) * 9 - v * 6) % 1.0) - 0.5) / 0.07) ** 2) * (np.abs(u) < 0.95)
    mott = textures._noise(n, 1.0, 1.0, 1.4, rng) * 0.5 + 0.5
    t = np.clip(0.35 + 0.35 * mott + 0.25 * rib + 0.12 * veins - 0.25 * np.abs(u) ** 3, 0, 1)
    img = base + (light - base) * t[..., None]
    img[(rib > 0.4)] = img[(rib > 0.4)] * 0.6 + np.array([0.18, 0.28, 0.08]) * 0.4
    img *= (1 - 0.35 * v ** 4)[..., None]
    return textures._save("T_Library_Leaf", textures._to_srgb(np.clip(img, 0, 1)))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rnd = random.Random(p["seed"])
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    stone = common.pbr_material("M_Library_Planter", (0.46, 0.42, 0.35), roughness=0.85)
    bark = common.pbr_material("M_Plant_Bark", (0.10, 0.07, 0.045), roughness=0.8)
    soil = common.pbr_material("M_Plant_Soil", (0.025, 0.016, 0.010), roughness=1.0)
    leaf_m = common.pbr_material("M_Library_Leaf", (1, 1, 1), roughness=0.38)
    common.set_base_color_map(leaf_m, textures.load(leaf_texture()))
    leaf_m.use_backface_culling = False

    R, PH = p["pot_r"], p["pot_h"]
    pot = Mesh(0.5)
    pot.lathe([(0, 0.0), (R * 0.82, 0.0), (R * 0.9, 0.04), (R, PH * 0.55), (R * 1.02, PH - 0.03), (R * 1.04, PH),
               (R * 0.93, PH), (R * 0.9, PH - 0.05)], segs=32)
    pot.to_object(f"{n}_Planter", col, stone, root, smooth=True)
    sm = Mesh(0.5)
    sm.lathe([(0, PH - 0.05), (R * 0.9, PH - 0.05), (0, PH - 0.05)], segs=24)
    sm.lathe([(0.0, PH - 0.045), (R * 0.9, PH - 0.045)], segs=24)
    sm.to_object(f"{n}_Soil", col, soil, root)

    # trunk: a gently curved, tapering tube
    H = p["height"]
    pts = [(0.012 * math.sin(i * 0.9), 0.01 * math.cos(i * 0.8), PH - 0.03 + (H - 0.18 - PH) * i / 8) for i in range(9)]
    common.tube_object(f"{n}_Trunk", pts, 0.016, col, bark, root, closed=False, profile_res=3)

    # leaves
    leaves = Mesh(0.5)
    z_lo, z_hi = PH + 0.35, H - 0.1
    for i in range(p["leaves"]):
        f = i / (p["leaves"] - 1)
        zb = z_lo + (z_hi - z_lo) * (f ** 0.85)
        phi = i * 2.399963 + rnd.uniform(-0.2, 0.2)
        trunk_pt = pts[min(8, int((zb - pts[0][2]) / (pts[-1][2] - pts[0][2]) * 8))]
        L = rnd.uniform(0.27, 0.36) * (1.0 - 0.25 * f)
        Wd = L * rnd.uniform(0.62, 0.78)
        pitch = math.radians(rnd.uniform(18, 52) + 25 * f)         # above horizontal, higher near the top
        droop = rnd.uniform(0.05, 0.14) * L / 0.3
        d = Vector((math.cos(phi), math.sin(phi), 0))
        side = Vector((-math.sin(phi), math.cos(phi), 0))
        base = Vector((trunk_pt[0], trunk_pt[1], zb)) + d * 0.03
        rows = 6
        grid = []
        for r in range(rows + 1):
            t = r / rows
            dist = t * L
            along = d * (math.cos(pitch) * dist) + Vector((0, 0, math.sin(pitch) * dist - droop * t * t))
            half = Wd * 0.5 * (math.sin(math.pi * min(t * 1.15 + 0.07, 1.0)) ** 0.7) * (0.35 + 0.65 * math.sin(math.pi * t * 0.5 + 0.2))
            crest = 0.012 * math.sin(math.pi * t)
            centre = base + along
            grid.append((centre + side * -half + Vector((0, 0, crest * -0.3)),
                         centre + Vector((0, 0, crest)),
                         centre + side * half + Vector((0, 0, crest * -0.3))))
        for r in range(rows):
            for c in range(2):
                a, b = grid[r][c], grid[r][c + 1]
                cc, dd = grid[r + 1][c + 1], grid[r + 1][c]
                u0, u1 = (c * 0.5) * 1.0, (c * 0.5 + 0.5)
                leaves.quad([a, b, cc, dd], [(u0, r / rows), (u1, r / rows), (u1, (r + 1) / rows), (u0, (r + 1) / rows)])
    # leaf texture's u runs 0..1 across the leaf; the texture is painted symmetrically
    lf = leaves.to_object(f"{n}_Leaves", col, leaf_m, root, smooth=True)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
