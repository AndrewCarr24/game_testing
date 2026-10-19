"""Large square ottoman / coffee pouf: a boxed cognac-leather cushion with a soft crown and
welted edges, on a slim bronze frame band raised on four tapered black feet. Units are metres; origin is the floor centre.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

sys.path.insert(0, HERE)
import living_sofa  # noqa: E402  (welt helper)

importlib.reload(common)
importlib.reload(materials)

NAME = "LivingOttoman"

P = dict(name=NAME, size=(1.15, 1.15), height=0.42, leather_name="M_Leather_Cognac", leather=(0.23, 0.075, 0.025))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    leather = common.pbr_material(p["leather_name"], p["leather"], roughness=0.62)
    common.set_normal_map(leather, textures.load(textures.leather_normal(), non_color=True), 0.6)
    black = materials.black_metal()
    bronze = materials.bronze()
    w, d = p["size"]
    h = p["height"]
    foot = 0.06
    # four tapered black block feet set in from the corners (one mesh)
    fb = bmesh.new()
    fs = 0.07
    for sx in (-1, 1):
        for sy in (-1, 1):
            t = common.box_bmesh((fs, fs, foot))
            for v in t.verts:
                k = 0.8 if v.co.z < 0 else 1.0
                v.co.x *= k
                v.co.y *= k
            vm = {v: fb.verts.new(v.co + Vector((sx * (w / 2 - 0.11), sy * (d / 2 - 0.11), foot / 2))) for v in t.verts}
            for fc in t.faces:
                if fc.normal.z < -0.9:
                    continue
                fb.faces.new([vm[v] for v in fc.verts])
            t.free()
    base = common.mesh_object(f"{n}_Base", fb, col, black, root, smooth=False)
    common.add_bevel(base, 0.003, segments=1)
    common.box_uv(base, 0.5)
    band = common.mesh_object(f"{n}_Band", common.box_bmesh((w - 0.05, d - 0.05, 0.012)), col, bronze, root, smooth=False)
    band.location = (0, 0, foot + 0.006)
    common.add_bevel(band, 0.002, segments=2)
    common.box_uv(band, 0.5)
    ct = h - foot - 0.012
    top = common.mesh_object(f"{n}_Cushion",
                             common.cushion_bmesh((w, d, ct), cuts=4, edge=0.045, crown={"+z": 0.025}),
                             col, leather, root)
    top.location = (0, 0, foot + 0.012 + ct / 2)
    common.add_subsurf(top)
    common.box_uv(top, 0.2)
    # leather welts round the top and bottom edges of the boxed cushion
    wb = bmesh.new()
    csz = (w, d, ct)
    for sg in (1, -1):
        living_sofa.face_welt(wb, top, csz, "z", sg, 0.045)
    bmesh.ops.recalc_face_normals(wb, faces=wb.faces[:])
    pipe = common.mesh_object(f"{n}_Piping", wb, col, leather, root)
    common.box_uv(pipe, 0.2)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
