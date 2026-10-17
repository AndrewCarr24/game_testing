"""Bake a level's lighting with Cycles. Run headless on the saved level file:

  /Applications/Blender.app/Contents/MacOS/Blender -b blender/levels/office.blend \
      --python blender/levels/bake.py -- office [samples]

Writes (never saves the .blend):
  assets/textures/T_<Level>_Lightmap.webp  diffuse lighting (direct + bounce, no
                                          albedo) for every shell mesh that has a
                                          "Lightmap" UV layer; sRGB-encoded, divided by `scale`
  assets/textures/T_<Level>_Env.hdr        360° radiance panorama from the room centre,
                                          sun hidden (the sun stays real-time); used for
                                          prop lighting and all reflections
  assets/levels/<level>_bake.json          what the engine needs to apply the above

Re-run after anything in the level moves (office.py rebuilds the UV atlas).
"""
import json
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, textures  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
LEVEL = args[0] if args else "office"
SAMPLES = int(args[1]) if len(args) > 1 else 512
NAME = LEVEL.capitalize()
scene = bpy.context.scene


def use_gpu():
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
        try:
            prefs.compute_device_type = kind
        except TypeError:
            continue
        prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type != "CPU"]
        if gpus:
            for d in prefs.devices:
                d.use = True
            scene.cycles.device = "GPU"
            return f"{kind}: {', '.join(d.name for d in gpus)}"
    scene.cycles.device = "CPU"
    return "CPU"


def bake_lightmap(res):
    objs = [o for o in bpy.data.collections[f"{NAME}_Shell"].all_objects
            if o.type == "MESH" and "Lightmap" in o.data.uv_layers]
    img = bpy.data.images.new(f"{NAME}_LightmapBake", res, res, alpha=False, float_buffer=True)
    added = []
    for mat in {m for o in objs for m in o.data.materials}:
        node = mat.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = img
        mat.node_tree.nodes.active = node
        added.append((mat, node))
    view_layer = bpy.context.view_layer
    for o in view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.data.uv_layers.active = o.data.uv_layers["Lightmap"]
        o.select_set(True)
    view_layer.objects.active = objs[0]

    scene.cycles.samples = SAMPLES
    scene.render.bake.margin = 4
    scene.render.bake.use_clear = True
    t = time.time()
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"DIRECT", "INDIRECT"}, target="IMAGE_TEXTURES")
    print(f"lightmap bake: {time.time() - t:.0f}s")

    for mat, node in added:
        mat.node_tree.nodes.remove(node)
    lin = np.array(img.pixels[:], dtype=np.float32).reshape(res, res, 4)[::-1, :, :3]  # top-down
    lit = lin.max(axis=2)
    # 99th percentile: the few texels hidden behind emissive strips may clip, everything visible keeps precision
    scale = float(np.percentile(lit[lit > 1e-4], 99.0)) if (lit > 1e-4).any() else 1.0
    textures._save(f"T_{NAME}_Lightmap", textures._to_srgb(lin / scale), fmt="WEBP", quality=92)
    return [o.name for o in objs], scale


def render_environment(probe, width=512):   # only feeds blurred reflections + ambient
    cam_data = bpy.data.cameras.new(f"{NAME}_EnvProbe")
    cam_data.type = "PANO"
    try:
        cam_data.panorama_type = "EQUIRECTANGULAR"
    except AttributeError:
        cam_data.cycles.panorama_type = "EQUIRECTANGULAR"
    cam = bpy.data.objects.new(f"{NAME}_EnvProbe", cam_data)
    scene.collection.objects.link(cam)
    cam.location = probe
    # image centre looks down +X and image-right is -Y, which is three.js's
    # equirect convention (+X at u=0.5, +Z to the right) after the Y-up swap
    cam.rotation_euler = (math.radians(90), 0, math.radians(-90))
    scene.camera = cam

    sun = bpy.data.objects[f"{NAME}_Sun"]
    sun.visible_camera = False      # the sun is real-time in the engine; keep it out of the probe
    sun.visible_diffuse = True
    scene.render.resolution_x, scene.render.resolution_y = width, width // 2
    scene.render.resolution_percentage = 100
    scene.cycles.samples = 256
    scene.cycles.use_denoising = True
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "HDR"
    path = os.path.join(textures.TEX_DIR, f"T_{NAME}_Env.hdr")
    scene.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"environment render: {time.time() - t:.0f}s")
    check = bpy.data.images.load(path)
    px = np.array(check.pixels[:], dtype=np.float32)
    print(f"environment max {px.max():.2f} mean {px.reshape(-1, 4)[:, :3].mean():.3f}")
    return path


if __name__ == "__main__":
    scene.render.engine = "CYCLES"
    print("device:", use_gpu())
    sys.path.insert(0, HERE)
    p = __import__(LEVEL).P   # level parameters (importing doesn't rebuild anything)

    objects, scale = bake_lightmap(p["lightmap_res"])
    probe = (0.0, 0.0, 1.3)
    render_environment(probe)

    bake = {
        "lightmap": {
            "file": f"textures/T_{NAME}_Lightmap.webp",
            "uv": 1,
            # three.js lightMap is irradiance; Cycles' diffuse bake is irradiance / pi
            "intensity": round(math.pi * scale, 4),
            "objects": objects,
        },
        "environment": {"file": f"textures/T_{NAME}_Env.hdr", "position": common.to_gltf(probe)},
        "exposure": p.get("exposure", 1.0),
        "samples": SAMPLES,
    }
    out = os.path.join(PROJECT, "assets", "levels", f"{LEVEL}_bake.json")
    with open(out, "w") as f:
        json.dump(bake, f, indent=2)
    print("wrote", out, "scale", round(scale, 4))
