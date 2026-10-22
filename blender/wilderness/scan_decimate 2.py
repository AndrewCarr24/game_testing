"""Route (b) of the vegetation spike: a Poly Haven scanned tree, collapse-decimated to game LODs.
Measures import/decimate time and triangle counts, renders original vs decimated, exports the
decimated LODs (Draco + WebP) to build/wilderness/veg/scan/.

  Blender -b --factory-startup --python blender/wilderness/scan_decimate.py -- [island_tree_02] [--targets 12000,3000]

Poly Haven's glTF leaves come as RGB JPEGs (the alpha is a separate map), so the leaf material
is re-wired with <id>_leaves_alpha before rendering.
"""
import json
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER_DIR = os.path.abspath(os.path.join(HERE, ".."))
PROJECT = os.path.abspath(os.path.join(BLENDER_DIR, ".."))
sys.path.insert(0, BLENDER_DIR)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(BLENDER_DIR, "tools"))
OUT = os.path.join(PROJECT, "build", "wilderness", "veg", "scan")


def tris(ob):
    me = ob.data
    me.calc_loop_triangles()
    per = {}
    for t in me.loop_triangles:
        m = me.materials[t.material_index].name if me.materials else "-"
        per[m] = per.get(m, 0) + 1
    return len(me.loop_triangles), per


def fix_leaf_alpha(ob, ph_id):
    import veg_sources
    for m in ob.data.materials:
        if "leaves" not in m.name and "twig" not in m.name:
            continue
        key = "leaves_alpha" if "leaves" in m.name else "twig_alpha"
        img = bpy.data.images.load(veg_sources.path(ph_id, key))
        img.colorspace_settings.name = "Non-Color"
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        uv = next((n for n in nt.nodes if n.type == "TEX_IMAGE" and n.image and "diff" in n.image.name), None)
        if uv and uv.inputs["Vector"].is_linked:
            nt.links.new(uv.inputs["Vector"].links[0].from_socket, tex.inputs["Vector"])
        gt = nt.nodes.new("ShaderNodeMath")
        gt.operation = "GREATER_THAN"
        gt.inputs[1].default_value = 0.5
        nt.links.new(tex.outputs["Color"], gt.inputs[0])
        nt.links.new(gt.outputs[0], bsdf.inputs["Alpha"])
        try:
            m.surface_render_method = "DITHERED"
        except (AttributeError, TypeError):
            pass


def render_row(objs, path, tile=512):
    import trees
    scene = bpy.context.scene
    trees._engine(scene, "BLENDER_EEVEE")
    scene.render.resolution_x = scene.render.resolution_y = tile
    scene.render.image_settings.file_format = "PNG"
    try:
        scene.eevee.taa_render_samples = 32
    except AttributeError:
        pass
    world = bpy.data.worlds.new("W")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.55, 0.65, 0.8, 1)
    bg.inputs["Strength"].default_value = 0.9
    scene.world = world
    scene.view_settings.view_transform = "AgX"
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 3.5
    sun.rotation_euler = Vector((-0.45, 0.35, -0.82)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(sun)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    lo = np.min([np.array(o.matrix_world @ Vector(c)) for o in objs for c in o.bound_box], 0)
    hi = np.max([np.array(o.matrix_world @ Vector(c)) for o in objs for c in o.bound_box], 0)
    centre = Vector(((lo + hi) / 2).tolist())
    ext = float(np.linalg.norm(hi - lo))
    tiles, tmp = [], path + ".tile.png"
    for o in objs:
        for p in objs:
            p.hide_render = p != o
        cam.location = centre + Vector((0.25, -1, 0.18)).normalized() * ext * 1.3
        cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.clip_end = ext * 20
        scene.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        tiles.append(trees._load(tmp))
    os.remove(tmp)
    trees._save(np.hstack(tiles), path, "row")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ph_id = next((a for a in argv if not a.startswith("--") and "," not in a), "island_tree_02")
    targets = [12000, 3000]
    if "--targets" in argv:
        targets = [int(x) for x in argv[argv.index("--targets") + 1].split(",")]
    import slots
    slots.acquire("asset", 4)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(OUT, exist_ok=True)
    from polyhaven_models import fetch_model
    t0 = time.time()
    path = fetch_model(ph_id)
    bpy.ops.import_scene.gltf(filepath=path)
    t_import = time.time() - t0
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    src = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    fix_leaf_alpha(src, ph_id)
    n0, per0 = tris(src)
    report = dict(id=ph_id, import_s=round(t_import, 1), tris=n0, per_material=per0, lods=[])
    print(f"SCAN {ph_id}: {n0} tris {per0}, import {t_import:.1f}s")
    objs = [src]
    for tgt in targets:
        ob = src.copy()
        ob.data = src.data.copy()
        ob.name = f"{ph_id}_{tgt // 1000}k"
        bpy.context.scene.collection.objects.link(ob)
        mod = ob.modifiers.new("dec", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = tgt / n0
        mod.use_collapse_triangulate = True
        t1 = time.time()
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier="dec")
        dt = time.time() - t1
        n, per = tris(ob)
        # export the decimated LOD alone, the way the game would ship it
        from lib import common
        gl = os.path.join(OUT, f"{ob.name}.gltf")
        for o in objs:
            o.hide_set(False)
        common.export_gltf(ob, gl)
        doc = json.load(open(gl))
        size = os.path.getsize(gl) + sum(os.path.getsize(os.path.join(OUT, b["uri"])) for b in doc["buffers"])
        tex = sum(os.path.getsize(os.path.join(OUT, i["uri"])) for i in doc.get("images", []))
        report["lods"].append(dict(name=ob.name, target=tgt, tris=n, per_material=per, decimate_s=round(dt, 1),
                                   bytes_geometry=size, bytes_textures=tex))
        print(f"SCAN {ob.name}: {n} tris {per}, decimate {dt:.1f}s, {size / 1024:.0f} KB geometry")
        objs.append(ob)
    render_row(objs, os.path.join(OUT, f"{ph_id}_decimated.png"))
    report["preview"] = f"scan/{ph_id}_decimated.png"
    json.dump(report, open(os.path.join(OUT, f"{ph_id}.json"), "w"), indent=1)
    print("DONE")


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    print("FAILED")
    sys.exit(1)
