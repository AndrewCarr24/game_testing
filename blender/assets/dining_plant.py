"""Sculptural olive tree in a honed limestone planter: three twisting grey-brown stems,
a loose airy canopy of ~950 narrow silver-green leaves (flat double-sided cards in two
tones) and a skim of dark soil with pale pebbles.

Units are metres. Origin: floor centre, symmetric. About 2.7 m tall.
"""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "DiningPlant"

P = dict(name=NAME, pot_r=0.30, pot_h=0.58, leaves=1100, seed=5, height=2.7)


def lathe(profile, segs):
    bm = bmesh.new()
    rows = []
    for r, z in profile:
        if r < 1e-9:
            rows.append([bm.verts.new((0, 0, z))] * segs)
        else:
            rows.append([bm.verts.new((r * math.cos(2 * math.pi * k / segs), r * math.sin(2 * math.pi * k / segs), z))
                         for k in range(segs)])
    for a, b in zip(rows[:-1], rows[1:]):
        for k in range(segs):
            t = (k + 1) % segs
            quad = []
            for v in (a[k], a[t], b[t], b[k]):
                if v not in quad:
                    quad.append(v)
            if len(quad) >= 3:
                bm.faces.new(quad)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])

    stone = common.pbr_material("M_Limestone_Planter", (0.46, 0.42, 0.35), roughness=0.85)
    soil = common.pbr_material("M_Soil_Dark", (0.02, 0.014, 0.01), roughness=1.0)
    pebble = common.pbr_material("M_Pebbles", (0.34, 0.31, 0.27), roughness=0.9)
    bark = common.pbr_material("M_Bark_Olive", (0.13, 0.105, 0.08), roughness=0.9)
    leaf_a = common.pbr_material("M_Leaf_Olive", (0.085, 0.13, 0.055), roughness=0.55)
    leaf_b = common.pbr_material("M_Leaf_Olive_Silver", (0.17, 0.22, 0.13), roughness=0.5)

    R, H = p["pot_r"], p["pot_h"]
    prof = [(0.0, 0.0), (R * 0.78, 0.0), (R * 0.95, 0.04), (R, 0.22), (R * 0.97, H * 0.8), (R * 0.9, H - 0.025),
            (R * 0.93, H - 0.01), (R * 0.93, H), (R * 0.82, H), (R * 0.82, H - 0.06), (0.0, H - 0.06)]
    pot = common.mesh_object(f"{n}_Planter", lathe(prof, 36), col, stone, root)
    common.box_uv(pot, 0.5)
    sb = lathe([(0.0, H - 0.055), (R * 0.82, H - 0.055), (R * 0.8, H - 0.045), (0.0, H - 0.045)], 24)
    common.box_uv(common.mesh_object(f"{n}_Soil", sb, col, soil, root), 0.5)
    pb = bmesh.new()
    for _ in range(26):
        a, d = rnd.uniform(0, 6.28), R * 0.75 * math.sqrt(rnd.random())
        bmesh.ops.create_uvsphere(pb, u_segments=6, v_segments=4, radius=rnd.uniform(0.018, 0.03),
                                  matrix=Matrix.Translation((d * math.cos(a), d * math.sin(a), H - 0.045)) @
                                  Matrix.Diagonal((1, 1, 0.6, 1)))
    common.box_uv(common.mesh_object(f"{n}_Pebbles", pb, col, pebble, root), 0.5)

    # stems: three twisting curves from the soil, each ending in a few branch tips
    Ht = p["height"]
    tips = []
    z0 = H - 0.05
    for si in range(3):
        a0 = si * 2.1 + 0.4
        pts = []
        top = Ht * rnd.uniform(0.62, 0.8)
        for k in range(8):
            t = k / 7
            z = z0 + t * (top - z0)
            ang = a0 + t * 1.6
            rad = (0.05 + 0.20 * math.sin(t * 2.2)) * (0.6 + t)
            pts.append((rad * math.cos(ang), rad * math.sin(ang), z))
        rr = 0.034 - si * 0.004
        common.tube_object(f"{n}_Stem{si}", pts, rr, col, bark, root, closed=False, profile_res=2)
        base = Vector(pts[-1])
        tips.append(base)
        # three branches off the upper third of each stem
        for bi in range(4):
            q = Vector(pts[4 + bi % 3])
            d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0.5, 1.0)))
            d.normalize()
            end = q + d * rnd.uniform(0.3, 0.6)
            end.z = min(end.z, Ht - 0.15)
            mid = (q + end) / 2 + Vector((0, 0, 0.05))
            common.tube_object(f"{n}_Branch{si}{bi}", [tuple(q), tuple(mid), tuple(end)], 0.012, col, bark, root,
                               closed=False, profile_res=2)
            tips.append(end)

    # leaves: narrow diamond cards (4 tris), scattered around branch tips
    la, lb = bmesh.new(), bmesh.new()
    for i in range(p["leaves"]):
        c = rnd.choice(tips)
        pos = c + Vector((rnd.gauss(0, 0.14), rnd.gauss(0, 0.14), rnd.gauss(0, 0.13)))
        pos.z = max(pos.z, 1.0)
        yaw = rnd.uniform(0, 6.28)
        pitch = rnd.uniform(-0.9, 0.5)
        m = Matrix.Translation(pos) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(pitch, 4, "X")
        ln, lw = rnd.uniform(0.08, 0.13), rnd.uniform(0.018, 0.027)
        bm_ = la if rnd.random() < 0.55 else lb
        vs = [bm_.verts.new(m @ Vector(v)) for v in ((0, 0, 0), (lw, ln * 0.5, 0.004), (0, ln, 0), (-lw, ln * 0.5, 0.004))]
        bm_.faces.new(vs)
    for nm, bm_, mat in (("LeavesA", la, leaf_a), ("LeavesB", lb, leaf_b)):
        ob = common.mesh_object(f"{n}_{nm}", bm_, col, mat, root, smooth=False)
        common.box_uv(ob, 0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    for o in parts:
        if not o.data.uv_layers:
            common.box_uv(o, 0.5)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
