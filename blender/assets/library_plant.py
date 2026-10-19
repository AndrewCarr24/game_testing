"""Fiddle-leaf fig in a limestone planter: a bare standard trunk, ~40 big glossy leaves in the crown
painted with a small leaf texture (T_Library_Leaf, double-sided). Origin: floor centre.
About 0.55 x 0.55 x 1.95 m."""
import importlib
import math
import os
import random
import sys

import bmesh
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import library_kit as kit  # noqa: E402
from library_kit import Mesh, common, materials, textures  # noqa: E402

importlib.reload(kit)

NAME = "LibraryPlant"

P = dict(name=NAME, seed=3, leaves=40, height=1.95, pot_r=0.23, pot_h=0.46)


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
    # planter: open at the bottom (it stands on the floor), a softly eased foot, a slight
    # belly and a thin rolled rim, the inside visible down to the soil
    pot = Mesh(0.5)
    pot.lathe([(R * 0.84, 0.0), (R * 0.9, 0.03), (R, PH * 0.55), (R * 1.02, PH - 0.03), (R * 1.035, PH - 0.008),
               (R * 1.02, PH), (R * 0.95, PH), (R * 0.935, PH - 0.01), (R * 0.92, PH - 0.06)], segs=24)
    pot.to_object(f"{n}_Planter", col, stone, root, smooth=True)
    sm = Mesh(0.5)
    sm.lathe([(0.0, PH - 0.045), (R * 0.55, PH - 0.05), (R * 0.93, PH - 0.058)], segs=16)
    sm.to_object(f"{n}_Soil", col, soil, root, smooth=True)

    # trunk: a bare, gently curved standard stem that forks into two short crown branches
    H = p["height"]
    crown_z = PH + 0.62
    pts = [(0.010 * math.sin(i * 0.9), 0.008 * math.cos(i * 0.8), PH - 0.05 + (H - 0.10 - PH) * i / 6) for i in range(7)]
    common.tube_object(f"{n}_Trunk", pts, 0.015, col, bark, root, closed=False, profile_res=1)
    stems = [pts]
    for b, (dx, dy) in enumerate(((0.09, 0.05), (-0.07, -0.08))):
        k0 = 4 + b
        a = Vector(pts[k0])
        bp = [a + Vector((dx * t * 0.7, dy * t * 0.7, 0.22 * t + 0.02 * t * t)) for t in (0.0, 0.5, 1.0)]
        common.tube_object(f"{n}_Branch{b}", [tuple(v) for v in bp], 0.009, col, bark, root, closed=False,
                           profile_res=1)
        stems.append([tuple(v) for v in bp])

    # leaves: big violin-shaped leaves clustered in the crown, on short petioles, each a
    # 4-row strip folded along the midrib (shared vertices, so it shades as one surface)
    leaves = Mesh(0.5)
    bm, uvl = leaves.bm, leaves.uv
    rows = 4
    count = p["leaves"]
    for i in range(count):
        f = i / (count - 1)
        stem = stems[i % len(stems)]
        lo_z = crown_z if stem is pts else stem[0][2] + 0.05
        hi_z = stem[-1][2] + (0.12 if stem is pts else 0.06)
        zb = lo_z + (hi_z - lo_z) * (rnd.random() ** 0.8)
        phi = i * 2.399963 + rnd.uniform(-0.3, 0.3)
        seg_i = min(len(stem) - 2, max(0, int((zb - stem[0][2]) / max(stem[-1][2] - stem[0][2], 1e-3) * (len(stem) - 1))))
        sp = Vector(stem[seg_i]).lerp(Vector(stem[seg_i + 1]), 0.5)
        hgt = (zb - crown_z) / max(H - crown_z, 1e-3)
        L = rnd.uniform(0.25, 0.33) * (1.0 - 0.3 * max(hgt, 0.0) ** 2)
        Wd = L * rnd.uniform(0.62, 0.74)
        pitch = math.radians(rnd.uniform(5, 40) + 40 * max(hgt, 0.0) ** 1.5)
        droop = rnd.uniform(0.06, 0.15) * L / 0.3
        d = Vector((math.cos(phi), math.sin(phi), 0))
        side = Vector((-math.sin(phi), math.cos(phi), 0))
        roll = rnd.uniform(-0.25, 0.25)
        base = Vector((sp.x, sp.y, zb)) + d * 0.04 + Vector((0, 0, 0.02))
        grid = []
        for r in range(rows + 1):
            t = r / rows
            dist = t * L
            along = d * (math.cos(pitch) * dist) + Vector((0, 0, math.sin(pitch) * dist - droop * t * t))
            # obovate fiddle outline: narrow at the stalk, widest at ~2/3, blunt tip
            half = Wd * 0.5 * (0.0 if r == rows else (0.30, 0.78, 1.0, 0.82)[r]) if r < rows else 0.0
            fold = 0.018 * math.sin(math.pi * min(t * 1.2, 1.0))
            c = base + along
            sd = side * math.cos(roll) + Vector((0, 0, math.sin(roll)))
            grid.append([bm.verts.new(c + sd * -half - Vector((0, 0, fold))), bm.verts.new(c),
                         bm.verts.new(c + sd * half - Vector((0, 0, fold)))])
        # the tip: collapse to one vertex
        for r in range(rows):
            for cc in range(2):
                quad = [grid[r][cc], grid[r][cc + 1], grid[r + 1][cc + 1], grid[r + 1][cc]]
                uvs = [(cc * 0.5, r / rows), (cc * 0.5 + 0.5, r / rows), (cc * 0.5 + 0.5, (r + 1) / rows), (cc * 0.5, (r + 1) / rows)]
                if r == rows - 1:
                    quad, uvs = quad[:3], uvs[:3]
                    quad[2] = grid[r + 1][1]
                    uvs[2] = (0.5, 1.0)
                    if cc == 1:
                        quad = [grid[r][1], grid[r][2], grid[r + 1][1]]
                        uvs = [(0.5, r / rows), (1.0, r / rows), (0.5, 1.0)]
                fc = bm.faces.new(quad)
                for lp, uv in zip(fc.loops, uvs):
                    lp[uvl].uv = uv
        # petiole: the leaf's stalk back to the stem, as a thin flat ribbon
        a0, a1 = sp + Vector((0, 0, zb - sp.z)) * 0.0, grid[0][1].co
        pv = [bm.verts.new(Vector(a) + side * o) for a in (Vector((sp.x, sp.y, zb - 0.02)), a1) for o in (-0.004, 0.004)]
        fc = bm.faces.new((pv[0], pv[1], pv[3], pv[2]))
        for lp, uv in zip(fc.loops, ((0.5, 0.0), (0.52, 0.0), (0.52, 0.05), (0.5, 0.05))):
            lp[uvl].uv = uv
    bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts], dist=1e-6)
    lf = leaves.to_object(f"{n}_Leaves", col, leaf_m, root, smooth=True)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
