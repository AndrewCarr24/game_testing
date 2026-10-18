"""Bake a level's lighting with Cycles, room by room. Run headless on the saved level file:

  /Applications/Blender.app/Contents/MacOS/Blender -b blender/levels/mansion.blend \
      --python blender/levels/bake.py -- mansion [samples]

For every room (shell meshes carry a "room" property and a "Lightmap" UV layer),
writes (never saves the .blend):
  assets/textures/T_<Level>_<Room>_Lightmap.webp  diffuse lighting (direct + bounce, no
                                                 albedo), sRGB-encoded, divided by `scale`
  assets/textures/T_<Level>_<Room>_Env.hdr        360° radiance panorama from the room's probe
                                                 point, sun hidden (the sun stays real-time);
                                                 lights that room's props and reflections
  assets/levels/<level>_bake.json                 what the engine needs to apply the above

All rooms are present in every bake, so light passes through open doorways.
Re-run after anything in the level moves (the level script rebuilds the UV atlases).
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
LEVEL = args[0] if args else "mansion"
SAMPLES = int(args[1]) if len(args) > 1 else 512
NAME = LEVEL.capitalize()
ENV_CLAMP = 3.0      # max radiance kept in the environment panorama
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


def bake_lightmap(room, objs, res):
    img = bpy.data.images.new(f"{NAME}_{room}_LightmapBake", res, res, alpha=False, float_buffer=True)
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
    # clamp indirect light: small bright sources (lamps) otherwise leave fireflies in dim rooms
    scene.cycles.sample_clamp_indirect = 4.0
    scene.render.bake.margin = 4
    scene.render.bake.use_clear = True
    t = time.time()
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"DIRECT", "INDIRECT"}, target="IMAGE_TEXTURES")
    print(f"lightmap bake {room}: {time.time() - t:.0f}s")

    for mat, node in added:
        mat.node_tree.nodes.remove(node)
    lin = np.array(img.pixels[:], dtype=np.float32).reshape(res, res, 4)[::-1, :, :3]  # top-down
    lin = denoise(lin)
    lit = lin.max(axis=2)
    # 99th percentile: the few texels hidden behind emissive strips may clip, everything visible keeps precision
    scale = float(np.percentile(lit[lit > 1e-4], 99.0)) if (lit > 1e-4).any() else 1.0
    textures._save(f"T_{NAME}_{room.capitalize()}_Lightmap", textures._to_srgb(lin / scale), fmt="WEBP", quality=92)
    for o in objs:
        o.select_set(False)
    return [o.name for o in objs], scale


def denoise(lin, passes=2):
    """Average each texel with its lit neighbours (3x3, twice): smooths the Monte Carlo
    grain of the bake. Unlit texels (outside UV islands) don't contribute, and islands are
    padded by 4 px, so light never bleeds from one surface into another."""
    mask = (lin.max(axis=2) > 1e-5).astype(np.float32)
    out = lin.copy()
    for _ in range(passes):
        acc = np.zeros_like(out)
        wsum = np.zeros_like(mask)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                k = 2.0 if dx == dy == 0 else 1.0
                acc += k * np.roll(np.roll(out * mask[..., None], dy, 0), dx, 1)
                wsum += k * np.roll(np.roll(mask, dy, 0), dx, 1)
        out = np.where(mask[..., None] > 0, acc / np.maximum(wsum, 1e-6)[..., None], out)
    return out


def render_environment(room, probe, width=512):   # only feeds blurred reflections + ambient
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
    path = os.path.join(textures.TEX_DIR, f"T_{NAME}_{room.capitalize()}_Env.hdr")
    scene.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"environment render {room}: {time.time() - t:.0f}s")
    # cap tiny, very bright sources (the light strips): left in, they flare as
    # blotches in every glossy reflection; their light is already in the lightmap
    img = bpy.data.images.load(path)
    w, hgt = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)
    sh = sh9(px[:, :3].reshape(hgt, w, 3))       # before clamping: props need the lights' full energy
    raw_max = px[:, :3].max()
    px[:, :3] = np.minimum(px[:, :3], ENV_CLAMP)
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = path
    img.file_format = "HDR"
    img.save()
    print(f"environment max {raw_max:.2f} -> {px[:, :3].max():.2f}, mean {px[:, :3].mean():.3f}")
    return path, sh


def sh9(rad):
    """Order-2 spherical harmonics of a radiance panorama (rows bottom-up, as Blender
    stores them), in glTF / three.js axes and three.js's coefficient order, ready for
    shGetIrradianceAt(). The probe camera faces +X (Blender) at the image centre with
    -Y to the right and +Z up (see render_environment)."""
    h, w, _ = rad.shape
    lat = ((np.arange(h) + 0.5) / h - 0.5) * np.pi          # -pi/2 (bottom row) .. pi/2
    lon = ((np.arange(w) + 0.5) / w - 0.5) * 2 * np.pi       # 0 at the centre column
    lon, lat = np.meshgrid(lon, lat)
    # Blender direction, then glTF (x, z, -y)
    bx, by, bz = np.cos(lon) * np.cos(lat), -np.sin(lon) * np.cos(lat), np.sin(lat)
    x, y, z = bx, bz, -by
    d_omega = np.cos(lat) * (np.pi / h) * (2 * np.pi / w)
    basis = [0.282095 * np.ones_like(x), 0.488603 * y, 0.488603 * z, 0.488603 * x,
             1.092548 * x * y, 1.092548 * y * z, 0.315392 * (3 * z * z - 1), 1.092548 * x * z,
             0.546274 * (x * x - y * y)]
    return [[round(float((rad[..., c] * b * d_omega).sum()), 5) for c in range(3)] for b in basis]


if __name__ == "__main__":
    scene.render.engine = "CYCLES"
    print("device:", use_gpu())
    sys.path.insert(0, HERE)
    p = __import__(LEVEL).P   # level parameters (importing doesn't rebuild anything)
    with open(os.path.join(PROJECT, "assets", "levels", f"{LEVEL}.json")) as f:
        level = json.load(f)

    shell = [o for o in bpy.data.collections[f"{NAME}_Shell"].all_objects
             if o.type == "MESH" and "Lightmap" in o.data.uv_layers]
    rooms = {}
    for room, info in level["rooms"].items():
        objs = [o for o in shell if o.get("room") == room]
        if not objs:
            continue
        names, scale = bake_lightmap(room, objs, info.get("lightmap") or p["lightmap_res"])
        gx, gy, gz = info["probe"]
        probe = (gx, -gz, gy)                     # glTF -> Blender
        # the environment only lights props and blurry reflections: small rooms get a small one
        x0, z0, x1, z1 = info["rect"]
        big = (x1 - x0) * (z1 - z0) > 150 or info.get("height", 0) > 5
        _, sh = render_environment(room, probe, width=512 if big else 256)
        R = room.capitalize()
        rooms[room] = {
            "lightmap": {
                "file": f"textures/T_{NAME}_{R}_Lightmap.webp",
                "uv": 1,
                # three.js lightMap is irradiance; Cycles' diffuse bake is irradiance / pi
                "intensity": round(math.pi * scale, 4),
                "objects": names,
            },
            "environment": {"file": f"textures/T_{NAME}_{R}_Env.hdr", "position": info["probe"]},
            "sh": sh,            # diffuse light for the room's props (three.js SH order, glTF axes)
        }
    bake = {"rooms": rooms, "exposure": p.get("exposure", 1.0), "samples": SAMPLES}
    out = os.path.join(PROJECT, "assets", "levels", f"{LEVEL}_bake.json")
    with open(out, "w") as f:
        json.dump(bake, f, indent=2)
    print("wrote", out, {r: v["lightmap"]["intensity"] for r, v in rooms.items()})
