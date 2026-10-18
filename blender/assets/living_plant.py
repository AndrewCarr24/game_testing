"""Statement plant in a tall plaster planter: a fiddle-leaf fig (large cupped leaves
on a leaning trunk) or, with kind="olive", a multi-stem olive with silvery lance
leaves. Leaves are hand-built low-poly shapes in three greens (no textures).

Units are metres. Origin: floor centre of the planter. Faces -Y (irrelevant).
"""
import importlib
import math
import os
import sys

import bmesh
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import living_side_table  # noqa: E402
from lib import common  # noqa: E402

importlib.reload(living_side_table)
lathe = living_side_table.lathe

NAME = "LivingPlant"

P = dict(
    name=NAME,
    kind="fig",
    seed=12,
    planter_r=0.30,
    planter_h=0.62,
    trunk_h=1.95,
    leaf_count=110,
    leaf_len=0.38,
    leaf_w=0.25,
)


def leaf_bmesh(bm, origin, d, length, width, roll, shape="fig", cup=0.02):
    """Append a leaf starting at `origin`, pointing along d."""
    d = Vector(d).normalized()
    up = Vector((0, 0, 1))
    x = d.cross(up)
    if x.length < 1e-3:
        x = Vector((1, 0, 0))
    x.normalize()
    z = x.cross(d).normalized()
    # roll about d
    c, s = math.cos(roll), math.sin(roll)
    x, z = x * c + z * s, z * c - x * s
    if shape == "fig":
        prof = [(0.0, 0.0), (0.30, 0.12), (0.5, 0.45), (0.38, 0.78), (0.0, 1.0)]
    else:
        prof = [(0.0, 0.0), (0.5, 0.35), (0.38, 0.75), (0.0, 1.0)]
    left, right = [], []
    for i, (hw, t) in enumerate(prof):
        zc = cup * (1 - abs(hw / 0.5 - 0.0)) if False else 0
        lift = cup * (hw * 2) if 0 < i < len(prof) - 1 else 0.0
        # cup: sides rise a little; droop along the length
        droop = -0.10 * length * t * t
        base = origin + d * (t * length) + z * (droop)
        left.append(bm.verts.new(base - x * (hw * width) + z * lift))
        right.append(bm.verts.new(base + x * (hw * width) + z * lift))
    # centre line vertex to make a midrib fold
    faces = []
    n = len(prof)
    for i in range(n - 1):
        a, b, c2, d2 = left[i], right[i], right[i + 1], left[i + 1]
        quad = []
        for v in (a, b, c2, d2):
            if v not in quad and all((v.co - q.co).length > 1e-6 for q in quad):
                quad.append(v)
        if len(quad) >= 3:
            faces.append(bm.faces.new(quad))
    return faces


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rng = np.random.default_rng(p["seed"])
    fig = p["kind"] == "fig"

    plaster = common.pbr_material("M_Plaster_Planter", (0.26, 0.235, 0.20), roughness=0.9)
    soil = common.pbr_material("M_Soil_Dark", (0.012, 0.009, 0.007), roughness=1.0)
    bark = common.pbr_material("M_Bark_Grey" if not fig else "M_Bark_Fig", (0.10, 0.075, 0.05) if fig else (0.13, 0.115, 0.10),
                               roughness=0.85)
    greens = ([common.pbr_material(f"M_Leaf_Fig{i}", c, roughness=0.32) for i, c in
               enumerate(((0.020, 0.075, 0.018), (0.030, 0.100, 0.025), (0.016, 0.060, 0.016)))] if fig else
              [common.pbr_material(f"M_Leaf_Olive{i}", c, roughness=0.5) for i, c in
               enumerate(((0.10, 0.14, 0.07), (0.075, 0.115, 0.06), (0.13, 0.16, 0.09)))])

    pr, ph = p["planter_r"], p["planter_h"]
    prof = [(0.0, 0.0), (pr * 0.82, 0.0), (pr * 0.86, 0.02), (pr, 0.10), (pr * 1.02, ph - 0.03), (pr, ph), (pr * 0.9, ph),
            (pr * 0.9, ph - 0.06), (0.0, ph - 0.06)]
    pot = common.mesh_object(f"{n}_Planter", lathe(prof, 40), col, plaster, root)
    common.box_uv(pot, 0.5)
    dirt = common.mesh_object(f"{n}_Soil", lathe([(0.0, ph - 0.05), (pr * 0.88, ph - 0.05), (pr * 0.88, ph - 0.035),
                                                   (0.0, ph - 0.035)], 24), col, soil, root)
    common.box_uv(dirt, 0.5)

    bm = [bmesh.new() for _ in greens]

    def add_leaf(origin, d, L, W, roll):
        k = int(rng.integers(len(greens)))
        leaf_bmesh(bm[k], origin, d, L, W, roll, "fig" if fig else "olive", cup=0.03 if fig else 0.005)

    top = ph - 0.05
    if fig:
        # one leaning trunk with a slight S curve, leaves spiralling up the top 65 %
        H = p["trunk_h"]
        lean = Vector((0.10, 0.06, 0))
        pts = []
        for i in range(11):
            t = i / 10
            pts.append(Vector((lean.x * t * t + 0.02 * math.sin(t * 5), lean.y * t * t, top + (H - top) * t)))
        common.tube_object(f"{n}_Trunk", pts, 0.022, col, bark, root, closed=False, profile_res=2)
        count = p["leaf_count"]
        for i in range(count):
            t = 0.33 + 0.67 * (i / count) ** 0.85
            idx = t * 10
            a = pts[int(min(9, idx))]
            b = pts[int(min(10, idx + 1))]
            base = a.lerp(b, idx - int(idx))
            ang = i * 2.399963 + rng.uniform(-0.3, 0.3)       # golden-angle spiral
            outward = Vector((math.cos(ang), math.sin(ang), 0))
            tilt = rng.uniform(0.05, 0.55) * (1.1 - t * 0.6)  # up-turned near the crown
            d = outward * math.cos(tilt * 0.6) + Vector((0, 0, math.sin(tilt) * 0.7 - 0.12 + (0.5 if t > 0.92 else 0)))
            L = p["leaf_len"] * rng.uniform(0.75, 1.15) * (1.0 - 0.25 * (1 - t))
            add_leaf(base + outward * 0.02, d, L, p["leaf_w"] * L / p["leaf_len"], rng.uniform(-0.5, 0.5))
    else:
        stems = 3
        crown = []
        for s in range(stems):
            ang = s * 2.1 + 0.4
            h = p["trunk_h"] * rng.uniform(0.7, 0.9)
            spread = Vector((math.cos(ang), math.sin(ang), 0)) * 0.28
            pts = []
            for i in range(9):
                t = i / 8
                wob = Vector((0.04 * math.sin(t * 9 + s), 0.04 * math.cos(t * 7 + s), 0))
                pts.append(Vector((0, 0, top + (h - top) * t)) + spread * (t ** 1.3) + wob)
            common.tube_object(f"{n}_Trunk{s}", pts, 0.034 - s * 0.003, col, bark, root, closed=False, profile_res=2)
            # branches from the upper half
            for b in range(4):
                t0 = 0.45 + 0.13 * b
                a = pts[int(t0 * 8)]
                bang = ang + rng.uniform(-1.6, 1.6)
                bd = Vector((math.cos(bang) * 0.55, math.sin(bang) * 0.55, 0.65))
                bl = rng.uniform(0.35, 0.6)
                bp = [a + bd * (bl * k / 4) + Vector((0, 0, -0.03 * k)) for k in range(5)]
                common.tube_object(f"{n}_Branch{s}_{b}", bp, 0.011, col, bark, root, closed=False, profile_res=2)
                crown.extend(bp[1:] * 2)
            crown.extend(pts[5:] * 2)
        for i in range(p["leaf_count"]):
            c = crown[int(rng.integers(len(crown)))]
            o = c + Vector(rng.normal(0, 0.10, 3)) * Vector((1, 1, 0.8))
            d = Vector(rng.normal(0, 1, 3)); d.z = abs(d.z) * 0.5 + 0.1
            add_leaf(o, d, p["leaf_len"], p["leaf_w"], rng.uniform(0, 6.28))

    for k, b in enumerate(bm):
        bmesh.ops.recalc_face_normals(b, faces=b.faces[:])
        ob = common.mesh_object(f"{n}_LeavesNoCollide{k}", b, col, greens[k], root, smooth=False)
        common.box_uv(ob, 0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
