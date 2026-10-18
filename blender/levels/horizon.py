"""Render the horizon band seen through the windows: tree belts beyond the perimeter
hedge, fields, wooded hills and a distant range, under the level's sun, fading into haze.

  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
      --python blender/levels/horizon.py -- [samples]

Writes assets/textures/T_Mansion_Horizon.webp (RGBA: alpha 0 where the sky shows; the
engine draws the sky itself, procedurally, behind it) and assets/levels/mansion_sky.json
(the band's latitude range and brightness scale, and the sky colours the haze fades to).
The band is an equirectangular strip in three.js's convention, so the engine reads it
with the same u as an equirect environment map. Everything here is at least ~80 m
away, so a single panorama works from anywhere in the house (the lawn, terrace and
hedge in front of it are real geometry, plan.GROUNDS).
"""
import json
import math
import os
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SAMPLES = int(args[0]) if args else 128
WIDTH, LAT = 4096, (-10.0, 16.0)              # 4096 px around; latitude band in degrees (the tallest
                                               # trees and the range top out ~15° up; above is sky)
EYE = 3.0                                      # camera height (between the floors)
# sky colours (linear radiance). The engine's procedural sky uses the same numbers, and
# distant land fades to HORIZON, so the band melts into the sky at the skyline.
HORIZON = (0.80, 0.86, 0.95)
ZENITH = (0.28, 0.46, 0.85)
HAZE = (0.62, 0.70, 0.84)                     # distant land fades to this (bluer, a bit darker than the sky)
SKY = (0.55, 0.68, 0.85)                       # world light (as the bake's, mansion.P["sky"])
SUN_STRENGTH = 4.0
rng = np.random.default_rng(12)


def material(name, color_node_fn):
    """Principled material whose base colour comes from color_node_fn(nodes, links), mixed
    toward the horizon haze by distance from the camera."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 0.95
    links.new(color_node_fn(nodes, links), bsdf.inputs["Base Color"])
    cam = nodes.new("ShaderNodeCameraData")
    # haze = 1 - exp(-d / 3500 m)
    div = nodes.new("ShaderNodeMath"); div.operation = "DIVIDE"; div.inputs[1].default_value = -3500.0
    links.new(cam.outputs["View Distance"], div.inputs[0])
    ex = nodes.new("ShaderNodeMath"); ex.operation = "EXPONENT"
    links.new(div.outputs[0], ex.inputs[0])
    inv = nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    links.new(ex.outputs[0], inv.inputs[1])
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*HAZE, 1)
    mix = nodes.new("ShaderNodeMixShader")
    links.new(inv.outputs[0], mix.inputs["Fac"])
    links.new(bsdf.outputs[0], mix.inputs[1])
    links.new(emit.outputs[0], mix.inputs[2])
    out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
    links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def ramp_by(nodes, links, fac_socket, stops):
    r = nodes.new("ShaderNodeValToRGB")
    els = r.color_ramp.elements
    while len(els) > len(stops):
        els.remove(els[-1])
    while len(els) < len(stops):
        els.new(0.5)
    for el, (pos, col) in zip(els, stops):
        el.position, el.color = pos, (*col, 1)
    links.new(fac_socket, r.inputs["Fac"])
    return r.outputs["Color"]


def land_color(nodes, links):
    """Fields: lawn green near, a patchwork of greens and straw farther, darker woods on hills."""
    geo = nodes.new("ShaderNodeNewGeometry")
    vor = nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 0.004
    links.new(geo.outputs["Position"], vor.inputs["Vector"])
    fields = ramp_by(nodes, links, vor.outputs["Color"], [
        (0.0, (0.05, 0.10, 0.025)), (0.35, (0.08, 0.13, 0.03)), (0.6, (0.13, 0.14, 0.05)), (0.85, (0.035, 0.07, 0.02))])
    noise = nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 0.01
    links.new(geo.outputs["Position"], noise.inputs["Vector"])
    woods = ramp_by(nodes, links, noise.outputs["Fac"], [(0.35, (0.02, 0.045, 0.015)), (0.65, (0.04, 0.07, 0.025))])
    # woods on the slopes: blend by height
    sep = nodes.new("ShaderNodeSeparateXYZ"); links.new(geo.outputs["Position"], sep.inputs[0])
    h = nodes.new("ShaderNodeMapRange"); h.inputs["From Min"].default_value = 15; h.inputs["From Max"].default_value = 70
    links.new(sep.outputs["Z"], h.inputs["Value"])
    mix = nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    links.new(h.outputs["Result"], mix.inputs["Factor"])
    links.new(fields, mix.inputs["A"]); links.new(woods, mix.inputs["B"])
    return mix.outputs["Result"]


def leaf_color(nodes, links):
    # leafy surface: a fine noise bump on the crowns (light breaks up into clumps)
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    tex = nodes.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = 3.0
    tex.inputs["Detail"].default_value = 6.0
    bump = nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.9
    bump.inputs["Distance"].default_value = 0.4
    links.new(tex.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    info = nodes.new("ShaderNodeObjectInfo")
    return ramp_by(nodes, links, info.outputs["Random"], [
        (0.0, (0.020, 0.045, 0.012)), (0.5, (0.035, 0.070, 0.018)), (1.0, (0.055, 0.085, 0.022))])


def flat_color(col):
    def fn(nodes, links):
        rgb = nodes.new("ShaderNodeRGB"); rgb.outputs[0].default_value = (*col, 1)
        return rgb.outputs[0]
    return fn


def mesh(name, bm, mat, col):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def terrain(col, mat):
    """Flat out to 300 m, then rolling wooded hills, rising to a range in the east-north-east."""
    rings = np.concatenate([[0.0], np.geomspace(120, 9000, 70)])
    segs = 512
    th = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    k = np.arange(1, 24)
    pa, pb = rng.uniform(0, 2 * np.pi, (2, k.size))
    amp = 1.0 / k ** 1.2

    def height(r, t):
        n1 = (amp[:, None] * np.sin(k[:, None] * t[None, :] + pa[:, None])).sum(0)
        n2 = (amp[:, None] * np.sin(k[:, None] * t[None, :] * 2 + pb[:, None] + r / 900)).sum(0)
        rise = np.clip((r - 300) / 900, 0, 1) ** 2
        hills = rise * (35 + 30 * n1 + 15 * n2)
        # the range: strongest towards +x+y (east-north-east), from 3 km out
        rng_dir = np.clip(np.cos(t - 0.45), 0, 1) ** 2
        rng_h = np.clip((r - 3000) / 3000, 0, 1) * rng_dir * (380 + 160 * n2)
        return np.maximum(hills + rng_h, 0)

    bm = bmesh.new()
    verts = []
    for r in rings:
        if r == 0:
            verts.append([bm.verts.new((0, 0, 0))])
            continue
        z = height(r, th)
        verts.append([bm.verts.new((r * math.cos(a), r * math.sin(a), zz)) for a, zz in zip(th, z)])
    for i in range(segs):
        bm.faces.new((verts[0][0], verts[1][i], verts[1][(i + 1) % segs]))
    for ri in range(1, len(verts) - 1):
        a, b = verts[ri], verts[ri + 1]
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((a[i], b[i], b[j], a[j]))
    return mesh("Terrain", bm, mat, col), height


def tree_meshes(col, leaf, bark):
    """A few tree shapes (round, oval, conifer); instances share these meshes."""
    protos = []
    lib = bpy.data.collections.new("TreeProtos")
    for kind in ("round", "round2", "oval", "conifer"):
        bm = bmesh.new()
        if kind == "conifer":
            for i, (z, r) in enumerate([(1.5, 2.2), (4.0, 1.8), (6.3, 1.3), (8.3, 0.8), (9.8, 0.35)]):
                bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=r, radius2=0.05, depth=3.2,
                                      matrix=__import__("mathutils").Matrix.Translation((0, 0, z + 1.2)))
        else:
            blobs = 7 if kind != "oval" else 5
            for i in range(blobs):
                ret = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
                r = rng.uniform(2.0, 3.2) if kind != "oval" else rng.uniform(1.5, 2.1)
                off = Vector((rng.uniform(-1.8, 1.8), rng.uniform(-1.8, 1.8),
                              rng.uniform(3.2, 7.0) if kind != "oval" else rng.uniform(3.0, 9.0)))
                for v in ret["verts"]:
                    jitter = (1 + 0.16 * math.sin(v.co.x * 7 + i) * math.sin(v.co.y * 5) * math.sin(v.co.z * 6 + i)
                              + 0.07 * math.sin(v.co.x * 23 + 2 * i) * math.sin(v.co.y * 19) * math.sin(v.co.z * 21))
                    v.co = v.co * r * jitter + off
                    if kind == "oval":
                        v.co.z = off.z + (v.co.z - off.z) * 1.5
        leaf_ob = mesh(f"Tree_{kind}", bm, leaf, lib)
        bmt = bmesh.new()
        bmesh.ops.create_cone(bmt, cap_ends=True, segments=6, radius1=0.25, radius2=0.15, depth=5.0,
                              matrix=__import__("mathutils").Matrix.Translation((0, 0, 2.5)))
        trunk = mesh(f"Trunk_{kind}", bmt, bark, lib)
        trunk.parent = leaf_ob
        protos.append(leaf_ob)
    return protos


def scatter_trees(col, protos, height):
    """Belts and copses beyond the hedge (80-320 m), denser in clumps, with gaps that
    open views to the hills; sparse copses farther out on the hillsides."""
    pts = []
    centres = []
    for _ in range(170):
        r = rng.uniform(85, 320)
        a = rng.uniform(0, 2 * np.pi)
        centres.append((r, a, rng.uniform(10, 35), rng.integers(8, 30)))
    for r, a, spread, n in centres:
        c = np.array([r * math.cos(a), r * math.sin(a)])
        for _ in range(n):
            p = c + rng.normal(0, spread, 2)
            if np.hypot(*p) < 80:
                continue
            pts.append(p)
    for _ in range(260):                        # far copses
        r = rng.uniform(400, 1600)
        a = rng.uniform(0, 2 * np.pi)
        pts.append(np.array([r * math.cos(a), r * math.sin(a)]))
    for i, (x, y) in enumerate(pts):
        proto = protos[rng.integers(len(protos))]
        r, t = np.hypot(x, y), np.arctan2(y, x)
        z = float(height(np.array([r]), np.array([t]))[0]) if r > 300 else 0.0
        for src in (proto, proto.children[0]):
            ob = bpy.data.objects.new(f"{src.name}.{i}", src.data)
            col.objects.link(ob)
            s = rng.uniform(1.0, 1.8) * (1.4 if r > 400 else 1.0)
            ob.scale = (s, s, s * rng.uniform(0.9, 1.25))
            ob.rotation_euler = (0, 0, rng.uniform(0, 2 * np.pi))
            ob.location = (x, y, z - 0.3)
    return len(pts)


def main():
    scene = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    col = scene.collection
    with open(os.path.join(PROJECT, "assets", "levels", "mansion.json")) as f:
        level = json.load(f)
    sun_gl = next(l for l in level["lights"] if l["type"] == "sun")
    gx, gy, gz = sun_gl["direction"]
    sun_dir = Vector((gx, -gz, gy)).normalized()            # glTF -> Blender, direction light travels

    land = material("M_Land", land_color)
    leaf = material("M_Leaves", leaf_color)
    bark = material("M_Bark", flat_color((0.03, 0.022, 0.015)))
    _, height = terrain(col, land)
    protos = tree_meshes(col, leaf, bark)
    n = scatter_trees(col, protos, height)
    print("trees:", n)

    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = SUN_STRENGTH
    sun_data.angle = math.radians(0.6)
    sun = bpy.data.objects.new("Sun", sun_data)
    col.objects.link(sun)
    sun.rotation_euler = Vector((0, 0, -1)).rotation_difference(sun_dir).to_euler()
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = next(nd for nd in world.node_tree.nodes if nd.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*SKY, 1)
    scene.world = world

    cam_data = bpy.data.cameras.new("Horizon")
    cam_data.type = "PANO"
    cam_data.panorama_type = "EQUIRECTANGULAR"
    cam_data.latitude_min, cam_data.latitude_max = map(math.radians, LAT)
    cam_data.clip_end = 20000
    cam = bpy.data.objects.new("Horizon", cam_data)
    col.objects.link(cam)
    cam.location = (0, 0, EYE)
    cam.rotation_euler = (math.radians(90), 0, math.radians(-90))   # three.js equirect convention (bake.py)
    scene.camera = cam

    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = "GPU"
    except TypeError:
        pass
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = round(WIDTH * (LAT[1] - LAT[0]) / 360)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_mode = "RGBA"
    raw = os.path.join(PROJECT, "build", "horizon.exr")
    os.makedirs(os.path.dirname(raw), exist_ok=True)
    scene.render.filepath = raw
    bpy.ops.render.render(write_still=True)

    img = bpy.data.images.load(raw)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    a = px[..., 3:4]
    rgb = np.where(a > 1e-4, px[..., :3] / np.maximum(a, 1e-4), 0)     # EXR is premultiplied
    scale = float(np.percentile(rgb[a[..., 0] > 0.5].max(axis=1), 99.5))
    srgb = common_to_srgb(np.clip(rgb / scale, 0, 1))
    out = bpy.data.images.new("T_Mansion_Horizon", w, h, alpha=True)
    out.pixels.foreach_set(np.concatenate([srgb, a], axis=2).astype(np.float32).ravel())
    path = os.path.join(PROJECT, "assets", "textures", "T_Mansion_Horizon.webp")
    out.filepath_raw = path
    out.file_format = "WEBP"
    out.save(quality=88)
    meta = {"file": "textures/T_Mansion_Horizon.webp", "scale": round(scale, 4), "latitude": list(LAT),
            "horizon": list(HORIZON), "zenith": list(ZENITH),
            "sun": [round(-c, 4) for c in (gx, gy, gz)]}         # towards the sun, glTF axes
    with open(os.path.join(PROJECT, "assets", "levels", "mansion_sky.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print("wrote", path, meta)


def common_to_srgb(lin):
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)


main()
