"""Standing oak wine barrel used as a high table: bulged oak staves (lathed, with stave
grooves), a flat head, four black steel hoops. Origin: floor centre. 0.62 m across,
0.92 m tall (a standing-height table). Units are metres; symmetric about Z.
"""
import importlib
import math
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "DiningBarrel"

P = dict(name=NAME, height=0.92, r_end=0.265, r_mid=0.315, staves=20)


def lathe(profile, segs, cyl_uv=True):
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


def barrel_r(z, H, r_end, r_mid):
    t = z / H * 2 - 1
    return r_end + (r_mid - r_end) * (1 - t * t)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    oak = materials.smoked_oak()
    steel = common.pbr_material("M_Hoop_Steel", (0.025, 0.025, 0.028), roughness=0.4, metallic=0.9)
    H, re_, rm, segs = p["height"], p["r_end"], p["r_mid"], p["staves"]

    # body: a 40-sided prism approximating staves would be heavy; use 24 sides, flat shaded alternate faces
    prof = [(0.0, 0.0)] + [(barrel_r(H * i / 8, H, re_, rm), H * i / 8) for i in range(9)] + [(0.0, H)]
    body_bm = lathe(prof, segs)
    for f in body_bm.faces:
        f.smooth = False
    body = common.mesh_object(f"{n}_Body", body_bm, col, oak, root, smooth=False)
    # staves read as flat facets; the lathe's flat faces give the hexadecagon-barrel look
    me = body.data
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            a = math.atan2(co.y, co.x)
            uv.data[li].uv = (co.z / 0.5, a / (2 * math.pi) * 1.0 * 2.0) if abs(poly.normal.z) < 0.9 else (co.x / 0.5, co.y / 0.5)

    hoops = bmesh.new()
    for z in (0.09, 0.27, H - 0.27, H - 0.09):
        r = barrel_r(z, H, re_, rm) + 0.004
        lathe_prof = [(r - 0.004, z - 0.02), (r + 0.006, z - 0.02), (r + 0.006, z + 0.02), (r - 0.004, z + 0.02)]
        h = lathe(lathe_prof + [lathe_prof[0]], segs)
        hoops.from_mesh(bpy_mesh(h))
    hp = common.mesh_object(f"{n}_Hoops", hoops, col, steel, root, smooth=False)
    common.box_uv(hp, 0.5)

    # head: a slightly proud lid disc
    lid = common.mesh_object(f"{n}_Head", lathe([(0.0, H), (re_ - 0.01, H), (re_ - 0.01, H + 0.004)] if False else
                                                [(0.0, H + 0.008), (re_ - 0.012, H + 0.008), (re_ - 0.012, H - 0.002), (0.0, H - 0.002)], segs),
                             col, oak, root, smooth=False)
    common.box_uv(lid, 0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


def bpy_mesh(bm):
    import bpy
    me = bpy.data.meshes.new("tmp_hoop")
    bm.to_mesh(me)
    bm.free()
    return me


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
