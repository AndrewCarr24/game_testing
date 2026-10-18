"""Counter stool: a round cognac-leather seat pad with a welted edge on four splayed
bronze legs joined by a ring foot rest. Seat height 0.68 m.

Units are metres, origin at the floor centre, faces -Y (symmetric).
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(materials)
importlib.reload(textures)

NAME = "DiningStool"

P = dict(name=NAME, seat_h=0.68, seat_r=0.20, pad_t=0.075, legs_top_r=0.15, legs_bot_r=0.25, ring_z=0.28)


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

    bronze = materials.bronze()
    leather = common.pbr_material("M_Leather_Cognac", (0.23, 0.075, 0.025), roughness=0.62)
    common.set_normal_map(leather, textures.load(textures.leather_normal(), non_color=True), 0.6)

    sh, r, t = p["seat_h"], p["seat_r"], p["pad_t"]
    z0 = sh - t
    prof = [(0.0, z0), (r - 0.012, z0), (r - 0.003, z0 + 0.007), (r, z0 + 0.02), (r, z0 + t - 0.022),
            (r - 0.012, z0 + t - 0.007), (r - 0.04, z0 + t - 0.001), (r * 0.5, z0 + t + 0.004), (0.0, z0 + t + 0.006)]
    pad = common.mesh_object(f"{n}_Pad", lathe(prof, 32), col, leather, root)
    common.box_uv(pad, 0.2)

    # bronze plate under the pad and the four splayed legs
    plate = common.mesh_object(f"{n}_Plate", lathe([(0, z0 - 0.012), (r - 0.04, z0 - 0.012), (r - 0.04, z0), (0, z0)], 24),
                               col, bronze, root)
    bm = bmesh.new()
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        top = Vector((p["legs_top_r"] * math.cos(a), p["legs_top_r"] * math.sin(a), z0 - 0.008))
        bot = Vector((p["legs_bot_r"] * math.cos(a), p["legs_bot_r"] * math.sin(a), 0.0))
        d = top - bot
        m = Matrix.Translation((top + bot) / 2) @ d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=8, radius1=0.011, radius2=0.015,
                              depth=d.length, matrix=m)
    legs = common.mesh_object(f"{n}_Legs", bm, col, bronze, root)

    # foot ring at ring_z: radius of the splayed legs at that height
    rz = p["ring_z"]
    rr = p["legs_bot_r"] + (p["legs_top_r"] - p["legs_bot_r"]) * rz / (z0 - 0.008)
    ring = []
    for k in range(25):
        a = 2 * math.pi * k / 24
        ring.append((rr * math.cos(a), rr * math.sin(a), rz))
    common.tube_object(f"{n}_Ring", ring, 0.009, col, bronze, root, closed=True, profile_res=2)
    for ob in (plate, legs):
        common.box_uv(ob, 0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
