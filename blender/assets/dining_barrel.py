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

    # body: one flat stave per lathe segment (hard joints between staves, smooth along each
    # stave's bulge), the staves running up past the sunk head as the chime
    rows = [(barrel_r(H * i / 8, H, re_, rm), H * i / 8) for i in range(9)]
    chime = 0.018
    prof = rows + [(re_ - 0.016, H), (re_ - 0.016, H - chime), (0.0, H - chime)]
    body_bm = lathe(prof, segs)
    for f in body_bm.faces:
        f.smooth = True
    for e in body_bm.edges:
        a, b = e.verts
        vertical = abs(a.co.z - b.co.z) > 1e-4 and abs(a.co.x * b.co.y - a.co.y * b.co.x) < 1e-6
        if vertical or abs(a.co.z - b.co.z) < 1e-6 and min(a.co.z, b.co.z) > H - chime - 1e-4 and \
                (a.co.xy.length > re_ - 0.03):
            e.smooth = False
    body = common.mesh_object(f"{n}_Body", body_bm, col, oak, root, smooth=True)
    me = body.data
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            a = math.atan2(co.y, co.x)
            uv.data[li].uv = (co.z / 0.5, a / (2 * math.pi) * 1.0 * 2.0) if abs(poly.normal.z) < 0.9 else (co.x / 0.5, co.y / 0.5)

    # blackened steel hoops: flat bands standing just proud of the staves
    hoops = bmesh.new()
    for z in (0.09, 0.27, H - 0.27, H - 0.09):
        r = barrel_r(z, H, re_, rm)
        h = lathe([(r - 0.001, z - 0.021), (r + 0.004, z - 0.02), (r + 0.004, z + 0.02), (r - 0.001, z + 0.021)], segs)
        hoops.from_mesh(bpy_mesh(h))
    hp = common.mesh_object(f"{n}_Hoops", hoops, col, steel, root, smooth=False)
    common.box_uv(hp, 0.5)
    # bung: a dark oak plug in the belly stave
    bung = common.mesh_object(f"{n}_Bung_NoCollide", lathe([(0.0, 0.006), (0.019, 0.006), (0.022, 0.0)], 10),
                              col, oak, root, smooth=True)
    bung.location = (0.0, -(rm - 0.004), H / 2)
    bung.rotation_euler = (math.radians(90), 0, 0)
    common.box_uv(bung, 0.5)
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
