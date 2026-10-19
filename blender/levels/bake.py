"""Bake a level's lighting with Cycles, room by room. Run headless on the saved level file:

  /Applications/Blender.app/Contents/MacOS/Blender -b blender/levels/mansion.blend \
      --python blender/levels/bake.py -- mansion [samples] [--rooms a,b] [--outdoor-only]

For every room (shell meshes carry a "room" property and a "Lightmap" UV layer),
writes (never saves the .blend):
  assets/textures/T_<Level>_<Room>_Lightmap.webp  diffuse lighting (direct + bounce, no
                                                 albedo), sRGB-encoded, divided by `scale`
  assets/textures/T_<Level>_<Room>_Env.webp       360° radiance panorama from the room's probe
                                                 point, sun hidden (the sun stays real-time),
                                                 sRGB of radiance / ENV_CLAMP; reflections only
                                                 (props' diffuse light comes from its SH)
  assets/models/<level>_outdoor.gltf             the grounds with their lighting baked into
                                                 vertex colours (bake_outdoor)
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
# options: --rooms a,b,c (bake only these rooms; the others keep their current bake) and
# --outdoor-only (only the grounds' vertex lighting, ~10 s); see CLAUDE.md "When to bake"
ONLY_ROOMS = set(args[args.index("--rooms") + 1].split(",")) if "--rooms" in args else None
OUTDOOR_ONLY = "--outdoor-only" in args
args = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--rooms")]
LEVEL = args[0] if args else "mansion"
SAMPLES = int(args[1]) if len(args) > 1 else 1024
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
    """Returns the names of the room's lightmapped meshes (rugs included: they borrow the
    floor's texels, so they're hidden from the bake rather than baked) and the scale."""
    names = [o.name for o in objs]
    rugs = [o for o in objs if o.get("lm_borrow")]
    objs = [o for o in objs if not o.get("lm_borrow")]
    for o in rugs:
        o.hide_render = True
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
    for o in rugs:
        o.hide_render = False
    return names, scale


def dilate(lin, mask, steps=12):
    """Grow each UV island's edge texels outward into the empty space between islands, so
    neither the denoiser nor texture filtering pulls black into the islands' borders."""
    out, m = lin.copy(), mask.astype(np.float32)
    for _ in range(steps):
        acc = np.zeros_like(out)
        wsum = np.zeros_like(m)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            acc += np.roll(np.roll(out * m[..., None], dy, 0), dx, 1)
            wsum += np.roll(np.roll(m, dy, 0), dx, 1)
        grow = (m == 0) & (wsum > 0)
        out[grow] = acc[grow] / wsum[grow][..., None]
        m = np.maximum(m, grow.astype(np.float32))
    return out


def denoise(lin):
    """Intel Open Image Denoise (Blender's compositor Denoise node) on the baked lightmap:
    removes the Monte Carlo grain while keeping contact shadows and corners sharp. The
    islands are dilated first so the filter never sees the black gaps between them."""
    mask = lin.max(axis=2) > 1e-5
    lin = dilate(lin, mask)
    h, w, _ = lin.shape
    src = bpy.data.images.new("_LightmapNoisy", w, h, alpha=False, float_buffer=True)
    src.pixels.foreach_set(np.concatenate([lin[::-1], np.ones((h, w, 1), np.float32)], axis=2).ravel())
    sc = bpy.data.scenes.get("_Denoise") or bpy.data.scenes.new("_Denoise")
    tree = bpy.data.node_groups.get("_DenoiseTree")
    if tree is None:
        tree = bpy.data.node_groups.new("_DenoiseTree", "CompositorNodeTree")
        tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        n_img = tree.nodes.new("CompositorNodeImage")
        n_dn = tree.nodes.new("CompositorNodeDenoise")
        n_dn.inputs["HDR"].default_value = True
        out = tree.nodes.new("NodeGroupOutput")
        tree.links.new(n_img.outputs["Image"], n_dn.inputs["Image"])
        tree.links.new(n_dn.outputs["Image"], out.inputs[0])
    sc.compositing_node_group = tree
    next(n for n in tree.nodes if n.bl_idname == "CompositorNodeImage").image = src
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.render.use_compositing = True
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.image_settings.file_format = "OPEN_EXR"
    bpy.ops.render.render(scene=sc.name)
    path = os.path.join(PROJECT, "build", "_denoised.exr")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.data.images["Render Result"].save_render(path, scene=sc)
    res = bpy.data.images.load(path)
    out = np.array(res.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]
    bpy.data.images.remove(res)
    bpy.data.images.remove(src)
    return np.maximum(out, 0)


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
    path = os.path.join(PROJECT, "build", "env", f"T_{NAME}_{room.capitalize()}_Env.hdr")
    os.makedirs(os.path.dirname(path), exist_ok=True)
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
    # 8-bit sRGB of radiance / ENV_CLAMP: a fraction of the .hdr's size, and it only feeds
    # blurred reflections (the engine scales it back up before prefiltering)
    rgb = px[:, :3].reshape(hgt, w, 3)[::-1] / ENV_CLAMP
    out = textures._save(f"T_{NAME}_{room.capitalize()}_Env", textures._to_srgb(rgb), fmt="WEBP", quality=90)
    print(f"environment max {raw_max:.2f} -> {px[:, :3].max():.2f}, mean {px[:, :3].mean():.3f}")
    return out, sh


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


def bake_outdoor(samples=256):
    """The grounds (grounds.py): bake lighting into each merged outdoor mesh's "Bake" vertex
    colours (flat materials: colour x light; textured: light only, the texture multiplies in
    the engine), normalise, collapse the flat mesh to one material, export
    assets/models/<level>_outdoor.gltf. Returns {kind: scale} for the bake JSON."""
    col = bpy.data.collections.get(f"{NAME}_Outdoor")
    if col is None:
        return None
    view_layer = bpy.context.view_layer
    scales = {}
    for kind, passes in (("flat", {"DIRECT", "INDIRECT", "COLOR"}), ("textured", {"DIRECT", "INDIRECT"})):
        group = [o for o in col.all_objects if o.type == "MESH" and o.get("outdoor") == kind]
        if not group:
            continue
        for o in view_layer.objects:
            o.select_set(False)
        for o in group:
            o.data.color_attributes.active_color = o.data.color_attributes["Bake"]
            o.select_set(True)
        view_layer.objects.active = group[0]
        scene.cycles.samples = samples
        t = time.time()
        bpy.ops.object.bake(type="DIFFUSE", pass_filter=passes, target="VERTEX_COLORS")
        cols = {o: np.array([c.color[:] for c in o.data.color_attributes["Bake"].data], np.float32) for o in group}
        lit = np.concatenate([c[:, :3].max(axis=1) for c in cols.values()])
        scale = float(np.percentile(lit, 99.5)) or 1.0
        for o, c in cols.items():
            c[:, :3] = np.clip(c[:, :3] / scale, 0, 1)
            c[:, 3] = 1
            o.data.color_attributes["Bake"].data.foreach_set("color", c.ravel())
        scales[kind] = round(scale, 5)
        print(f"outdoor bake {kind}: {len(group)} meshes, {sum(len(c) for c in cols.values())} corners, "
              f"scale {scale:.4f}, {time.time() - t:.0f}s")
    # the flat mesh's colours now include each material's colour: one material for all
    flat_mat = bpy.data.materials.get("M_Outdoor_Flat") or common.pbr_material("M_Outdoor_Flat", (1, 1, 1), roughness=1)
    for o in col.all_objects:
        if o.type == "MESH" and o.get("outdoor") == "flat":
            o.data.materials.clear()
            o.data.materials.append(flat_mat)
            for poly in o.data.polygons:
                poly.material_index = 0
    root = bpy.data.objects[f"{NAME}_Outdoor"]
    common._export(root, os.path.join(PROJECT, "assets", "models", f"{LEVEL}_outdoor.gltf"),
                   export_format="GLTF_SEPARATE", export_texture_dir="textures", export_image_format="WEBP",
                   export_image_quality=85, export_vertex_color="NAME", export_vertex_color_name="Bake",
                   export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=10,
                   export_draco_position_quantization=14, export_draco_normal_quantization=10,
                   export_draco_texcoord_quantization=12, export_draco_color_quantization=10)
    # the export rewrote shared textures at full size; shrink prop textures again (as build_level does)
    import runpy
    runpy.run_path(os.path.join(PROJECT, "blender", "tools", "optimize_textures.py"))
    return scales


if __name__ == "__main__":
    scene.render.engine = "CYCLES"
    print("device:", use_gpu())
    sys.path.insert(0, HERE)
    p = __import__(LEVEL).P   # level parameters (importing doesn't rebuild anything)
    with open(os.path.join(PROJECT, "assets", "levels", f"{LEVEL}.json")) as f:
        level = json.load(f)

    shell = [o for o in bpy.data.collections[f"{NAME}_Shell"].all_objects
             if o.type == "MESH" and "Lightmap" in o.data.uv_layers]
    out = os.path.join(PROJECT, "assets", "levels", f"{LEVEL}_bake.json")
    partial = ONLY_ROOMS is not None or OUTDOOR_ONLY
    previous = json.load(open(out)) if partial and os.path.exists(out) else {}
    rooms = dict(previous.get("rooms", {})) if partial else {}
    for room, info in level["rooms"].items():
        if OUTDOOR_ONLY or (ONLY_ROOMS is not None and room not in ONLY_ROOMS):
            continue
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
            "environment": {"file": f"textures/T_{NAME}_{R}_Env.webp", "scale": ENV_CLAMP, "position": info["probe"]},
            "sh": sh,            # diffuse light for the room's props (three.js SH order, glTF axes)
        }
    outdoor = bake_outdoor() if (ONLY_ROOMS is None or OUTDOOR_ONLY) else previous.get("outdoor")
    bake = {"rooms": rooms, "exposure": p.get("exposure", 1.0), "samples": SAMPLES if not partial else previous.get("samples", SAMPLES)}
    if partial:
        bake["partial"] = {"rooms": sorted(ONLY_ROOMS or []), "outdoor": OUTDOOR_ONLY, "samples": SAMPLES}
    if outdoor:
        bake["outdoor"] = outdoor      # vertex-colour scale per kind (flat: colour x light, textured: light)
    with open(out, "w") as f:
        json.dump(bake, f, indent=2)
    print("wrote", out, {r: v["lightmap"]["intensity"] for r, v in rooms.items()})
