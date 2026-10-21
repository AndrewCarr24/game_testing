"""Bake a level's lighting with Cycles, room by room. Run headless on the saved level file:

  /Applications/Blender.app/Contents/MacOS/Blender -b blender/levels/mansion.blend \
      --python blender/levels/bake.py -- mansion [samples] [--rooms a,b] [--outdoor-only]
      [--state on|off|both]

--state: on (default) bakes the rooms as lit; off bakes only their lights-off state (against
the stored on state; no outdoor); both does on then off (the full bake: ~2x the time).

For every room (shell meshes carry a "room" property and a "Lightmap" UV layer),
writes (never saves the .blend):
  assets/textures/T_<Level>_<Room>_Lightmap.webp  diffuse lighting (direct + bounce, no
                                                 albedo), sRGB-encoded, divided by `scale`
  assets/textures/T_<Level>_<Room>_Env.webp       360° radiance panorama from the room's probe
                                                 point, sun hidden (the sun stays real-time),
                                                 sRGB of radiance / ENV_CLAMP; reflections only
                                                 (props' diffuse light comes from its SH)
  assets/textures/T_<Level>_<Room>_LightmapOff.webp, _EnvOff.webp   the same with the room's
                                                 own lights off (see "lights off" below)
  assets/models/<level>_outdoor.gltf             the grounds with their lighting baked into
                                                 vertex colours (bake_outdoor)
  assets/levels/<level>_bake.json                 what the engine needs to apply the above

All rooms are present in every bake, so light passes through open doorways.
Re-run after anything in the level moves (the level script rebuilds the UV atlases).

Light fixtures (prop roots tagged "fixture" by mansion.py) don't shadow their own light: the
fixtures whose bounds hold a light (chandelier
orbs, strands and rings, sconces, downlight cans, pendants) are left out of that light's
shadow rays (Cycles shadow linking), except parts named "Shade" (a lampshade shapes its
light); glowing parts next to a light (orbs, lenses, the ceiling strips) don't light the bake
(their light is the light object's) and are hidden from the reflection panorama with the
fixtures holding a light (they flared as orbs and squares in glossy floors). A LIGHTS entry
can name more props that don't block it (LIGHTS "no_shadow": [asset, ...] -> the light
object's "no_shadow" property, set by mansion.py).

Rooms joined without a wall (plan.OPEN) share one lightmap scale (a sunlit gallery and its
neighbour met with a brightness/colour break); texels over the scale clip hue-preserving.
"""
import json
import math
import os
import shutil
import subprocess
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
# options: --rooms a,b,c (bake only these rooms; the others keep their current bake),
# --outdoor-only (only the grounds' vertex lighting, ~10 s) and --state on|off|both (the
# lighting state(s) to bake, default on: see "Lights off" below); see CLAUDE.md "When to bake"
ONLY_ROOMS = set(args[args.index("--rooms") + 1].split(",")) if "--rooms" in args else None
OUTDOOR_ONLY = "--outdoor-only" in args
STATE = args[args.index("--state") + 1] if "--state" in args else "on"
if STATE not in ("on", "off", "both"):
    raise SystemExit(f"--state {STATE!r}: on, off or both")
args = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--rooms", "--state"))]
LEVEL = args[0] if args else "mansion"
SAMPLES = int(args[1]) if len(args) > 1 else 1024
NAME = LEVEL.capitalize()
ENV_CLAMP = 3.0      # max radiance kept in the environment panorama
LM_PERCENTILE = 99.0   # lightmap scale: this percentile of the lit texels (over it: hue-preserving clip;
                       # 99.5 let the hot texels behind a backlit mirror set the primary bath's scale)
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


def chart_mask(objs, W, H):
    """Texels the room's lightmap charts cover (from the Lightmap UVs; rows top-down)."""
    mask = np.zeros((H, W), bool)
    for o in objs:
        me = o.data
        uv = np.empty(len(me.loops) * 2, np.float32)
        me.uv_layers["Lightmap"].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        for poly in me.polygons:
            q = uv[poly.loop_start:poly.loop_start + poly.loop_total]
            u0, v0 = q.min(axis=0)
            u1, v1 = q.max(axis=0)
            if u1 - u0 < 1e-7 and v1 - v0 < 1e-7:
                continue                                  # collapsed (not seen)
            x0, x1 = int(math.floor(u0 * W)), int(math.ceil(u1 * W))
            y0, y1 = int(math.floor(v0 * H)), int(math.ceil(v1 * H))
            mask[max(0, y0):min(H, y1), max(0, x0):min(W, x1)] = True
    return mask[::-1]


def bake_lightmap(room, objs, res):
    """Bakes the room's lightmap; returns the names of the room's lightmapped meshes (rugs and
    wall art included: they borrow the floor's / wall's texels, so they're hidden from the
    bake rather than baked), the denoised linear lightmap (rows top-down) and its chart mask."""
    W, H = (res, res) if isinstance(res, int) else tuple(res)
    names = [o.name for o in objs]
    rugs = [o for o in objs if o.get("lm_borrow")]
    objs = [o for o in objs if not o.get("lm_borrow")]
    # the borrowed wall art's black frames and backings (one roomless mesh): hidden too, or
    # they shadow the very wall texels the art takes its light from
    rugs += [o for o in bpy.data.collections[f"{NAME}_Shell"].all_objects if o.get("art_frame")]
    for o in rugs:
        o.hide_render = True
    img = bpy.data.images.new(f"{NAME}_{room}_LightmapBake", W, H, alpha=False, float_buffer=True)
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
    lin = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)[::-1, :, :3]  # top-down
    bpy.data.images.remove(img)
    mask = chart_mask(objs, W, H)
    lin = denoise(lin, mask)
    for o in objs:
        o.select_set(False)
    for o in rugs:
        o.hide_render = False
    return names, lin, mask


def room_scale(lin, mask):
    lit = lin.max(axis=2)[mask]
    lit = lit[lit > 1e-4]
    return float(np.percentile(lit, LM_PERCENTILE)) if lit.size else 1.0


def open_groups(plan):
    """Rooms joined without a wall (plan.OPEN), as connected groups: room -> set of rooms."""
    group = {r: {r} for r in plan.ROOMS}
    for a, b in plan.OPEN:
        g = group[a] | group[b]
        for r in g:
            group[r] = g
    return group


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


def denoise(lin, mask=None):
    """Intel Open Image Denoise (Blender's compositor Denoise node) on the baked lightmap:
    removes the Monte Carlo grain while keeping contact shadows and corners sharp. The
    charts (mask: the texels the UV charts cover, so dark texels inside a chart count too and
    small islands are treated like big ones) are dilated first so the filter never sees the
    black gaps between them."""
    if mask is None:
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


def render_environment(room, probe, width=512, hide=(), save=True, tag=""):
    """The room's panorama twice: everything visible for the SH (props need the lights' full
    energy), then with `hide` (glowing fixtures and the fixtures holding a light) invisible to
    the camera for the reflection map (they flared as orbs and squares in glossy floors).
    Returns (path or None, sh, rgb): rgb = the reflection map's radiance / ENV_CLAMP, rows
    top-down; save=False leaves writing it to the caller."""
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
    scene.cycles.use_denoising = True
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "HDR"
    os.makedirs(os.path.join(PROJECT, "build", "env"), exist_ok=True)

    def render(path, samples):
        scene.cycles.samples = samples
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(path)
        w, hgt = img.size
        px = np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)
        bpy.data.images.remove(img)
        return px, w, hgt

    t = time.time()
    full, w, hgt = render(os.path.join(PROJECT, "build", "env", f"T_{NAME}_{room.capitalize()}_EnvFull{tag}.hdr"), 128)
    sh = sh9(full[:, :3].reshape(hgt, w, 3))       # unclamped, fixtures in: props need the lights' full energy
    raw_max = full[:, :3].max()
    for o in hide:
        o.visible_camera = False
    px, w, hgt = render(os.path.join(PROJECT, "build", "env", f"T_{NAME}_{room.capitalize()}_Env{tag}.hdr"), 256)
    for o in hide:
        o.visible_camera = True
    print(f"environment render {room}: {time.time() - t:.0f}s ({len(hide)} fixtures hidden from the reflections)")
    # cap tiny, very bright sources (the light strips): left in, they flare as
    # blotches in every glossy reflection; their light is already in the lightmap
    px[:, :3] = np.minimum(px[:, :3], ENV_CLAMP)
    # 8-bit sRGB of radiance / ENV_CLAMP: a fraction of the .hdr's size, and it only feeds
    # blurred reflections (the engine scales it back up before prefiltering)
    rgb = px[:, :3].reshape(hgt, w, 3)[::-1] / ENV_CLAMP
    out = textures._save(f"T_{NAME}_{room.capitalize()}_Env", textures._to_srgb(rgb), fmt="WEBP", quality=90) if save else None
    print(f"environment max {raw_max:.2f} -> {px[:, :3].max():.2f}, mean {px[:, :3].mean():.3f}")
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(cam_data)
    return out, sh, rgb


def emits(mat):
    if mat is None or not mat.use_nodes:
        return False
    for n in mat.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            st = n.inputs["Emission Strength"].default_value
            col = n.inputs["Emission Color"].default_value
            if st > 0 and max(col[:3]) > 0:
                return True
        elif n.type == "EMISSION" and n.inputs["Strength"].default_value > 0:
            return True
    return False


def setup_fixtures():
    """Shadow linking and ray visibility for light fixtures (see the module docstring).
    Returns the objects to hide from the reflection panorama."""
    lights = [o for o in bpy.data.collections[f"{NAME}_PreviewLights"].objects
              if o.type == "LIGHT" and o.data.type != "SUN"]
    skip = {f"{NAME}_Shell", f"{NAME}_Outdoor", f"{NAME}_PreviewLights"}
    roots, dark, extra = {}, 0, {}
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.data.polygons:
            continue
        if any(c.name in skip for c in o.users_collection):
            # the ceiling strips: their light is the area light under each one
            if any(m is not None and m.name.startswith("M_LightStrip") for m in o.data.materials):
                o.visible_diffuse = o.visible_glossy = o.visible_shadow = False
                dark += 1
            continue
        r = o
        while r.parent is not None:
            r = r.parent
        if r.get("fixture"):          # light fixtures only (mansion.py tags their roots)
            roots.setdefault(r.name, []).append(o)
        elif r.name not in extra:
            extra[r.name] = r
    boxes = {name: common.world_aabb(obs) for name, obs in roots.items()}
    hide, linked = set(), 0
    for i, L in enumerate(lights):
        p = L.matrix_world.translation
        own = [n for n, (lo, hi) in boxes.items() if all(lo[k] - 0.12 <= p[k] <= hi[k] + 0.12 for k in range(3))]
        blockers = [o for n in own for o in roots[n] if "Shade" not in o.name]
        hide.update(o for n in own for o in roots[n])
        for n in L.get("no_shadow", []):           # LIGHTS no_shadow: not hidden from the reflections
            if n in extra:
                blockers += [o for o in [extra[n]] + list(extra[n].children_recursive) if o.type == "MESH"]
        if blockers:
            col = bpy.data.collections.get(f"_NoShadow_{i}") or bpy.data.collections.new(f"_NoShadow_{i}")
            for o in blockers:
                if o.name not in col.objects:
                    col.objects.link(o)
            for co in col.collection_objects:
                co.light_linking.link_state = "EXCLUDE"
            L.light_linking.blocker_collection = col
            linked += 1
        # glowing parts next to the light: their light is the light object's
        for n, (lo, hi) in boxes.items():
            if all(lo[k] - 0.3 <= p[k] <= hi[k] + 0.3 for k in range(3)):
                for o in roots[n]:
                    if o.visible_diffuse and any(emits(m) for m in o.data.materials):
                        o.visible_diffuse = o.visible_glossy = o.visible_shadow = False
                        hide.add(o)
                        dark += 1
    print(f"fixtures: {linked} lights skip their own fixture's shadow, {dark} glowing parts out of the bake, "
          f"{len(hide)} meshes hidden from the reflections")
    return list(hide)


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


# ------------------------------------------------------------------ lights off
# A second lighting state per room: the room's own lights off (its LIGHTS, its ceiling strips,
# its fixtures' glow); the sun, the sky and the neighbours' lights still on. Written next to the
# on state as T_<Level>_<Room>_LightmapOff.webp (same atlas and encoding: lin / the room's
# scale) and T_<Level>_<Room>_EnvOff.webp, plus the off SH and a tint in the bake JSON's
# rooms[r].off. The engine (viewer/baked.js) fades each room between the two from its light
# signal (lights_<room>, or the group's, e.g. lights_galleries) and `power`. It packs the off
# lightmap into the on lightmap's alpha as a luminance ratio (no second GPU texture: a ratio in
# the WebP's own alpha cost 4x the download, lossless alpha of a noisy map), and the light that's
# left keeps the room's tint (sky / sun bounce, bluer or redder than the lamps):
#   off = on x ratio x mix(tint, 1, ratio)      (the bake logs how close that comes)
LUM = np.array([0.2126, 0.7152, 0.0722], np.float32)
OFF_QUALITY = 90        # the off maps are dim: q90 is ~60% of q95's size with no visible difference


def to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lightmap_srgb(lin, scale, dither=True):
    """sRGB of lin / scale, over 1 scaled down as a whole (hue kept: a per-channel clip turned
    clipped sun patches green), lightly dithered (half a level: hides banding in dark gradients)."""
    x = lin / scale
    peak = x.max(axis=2, keepdims=True)
    x = np.where(peak > 1.0, x / np.maximum(peak, 1e-9), x)
    srgb = textures._to_srgb(x)
    if dither:
        rng = np.random.default_rng(1)
        srgb = srgb + (rng.random(srgb.shape[:2] + (1,)) - rng.random(srgb.shape[:2] + (1,))) * (0.5 / 255)
    return np.clip(srgb, 0, 1)


def write_png(path, img8):
    """8-bit RGB / RGBA PNG (rows top-down), written directly (no colour management)."""
    import struct
    import zlib
    h, w, c = img8.shape
    raw = b"".join(b"\x00" + img8[y].tobytes() for y in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6 if c == 4 else 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def write_webp(name, srgb, quality=95):
    """srgb (h, w, 3) in 0..1 -> assets/textures/<name>.webp with cwebp (lossy, sharp RGB->YUV,
    best method: the q92 default made blocky patches on dark ceilings and bled colour across
    charts), else Blender's writer."""
    cwebp = shutil.which("cwebp") or ("/opt/homebrew/bin/cwebp" if os.path.exists("/opt/homebrew/bin/cwebp") else None)
    if cwebp is None:
        return textures._save(name, srgb, fmt="WEBP", quality=quality)
    png = os.path.join(PROJECT, "build", "lightmaps", name + ".png")
    write_png(png, np.round(np.clip(srgb, 0, 1) * 255).astype(np.uint8))
    out = os.path.join(textures.TEX_DIR, name + ".webp")
    subprocess.run([cwebp, "-quiet", "-q", str(quality), "-sharp_yuv", "-m", "6", "-mt", png, "-o", out], check=True)
    return out


def decode(path):
    """A stored 8-bit texture's values (sRGB-encoded, 0..1, rows top-down, RGB)."""
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, -1)[::-1, :, :3]
    bpy.data.images.remove(img)
    return px


def off_ratio(on, off, valid):
    """on, off: linear (h, w, 3) in the same units; valid: texels that count. Returns the
    luminance ratio (h, w) in 0..1, the tint (lum 1) of the light that's left, and the mean
    relative error of the ratio-only and the ratio + tint reconstruction (for the log)."""
    lon, loff = on @ LUM, off @ LUM
    r = np.where(lon > 1e-5, np.clip(loff / np.maximum(lon, 1e-9), 0, 1), 1.0).astype(np.float32)
    v = valid & (lon > 1e-4)
    est = on * r[..., None]
    w = v & (r < 0.6)
    tint = np.ones(3, np.float32)
    if w.sum() > 16:
        k = (1 - r[w])[:, None]
        tint = (off[w] * k).sum(0) / np.maximum((est[w] * k).sum(0), 1e-9)
        tint = np.clip(tint / max(float(tint @ LUM), 1e-6), 0.3, 3.0)
    est2 = est * (tint * (1 - r[..., None]) + r[..., None])
    scale = max(float(off[v].mean()), 1e-9) if v.any() else 1.0
    err = [float(np.abs(e[v] - off[v]).mean() / scale) if v.any() else 0.0 for e in (est, est2)]
    return r, tint, err


def light_signals(level):
    """room -> the signal its lights follow: mansion.json rooms[r].lights (mansion.py writes it;
    "" = none), else the lights signal most of the room's fixtures were wired to
    (ix_common.wire), else lights_<room>."""
    counts = {}
    for p in level["props"]:
        s = p.get("signal")
        s = s.get("lights") if isinstance(s, dict) else (s if isinstance(s, str) and s.startswith("lights_") else None)
        if s:
            c = counts.setdefault(p["room"], {})
            c[s] = c.get(s, 0) + 1
    out = {}
    for r, info in level["rooms"].items():
        if "lights" in info:
            out[r] = info["lights"]
        elif r in counts:
            out[r] = max(counts[r], key=counts[r].get)
        else:
            out[r] = f"lights_{r}"
    return out


def room_at(level, pt):
    """The (smallest) room whose box holds the Blender point pt."""
    gx, gy, gz = pt[0], pt[2], -pt[1]
    best = None
    for r, info in level["rooms"].items():
        x0, z0, x1, z1 = info["rect"]
        if x0 - 0.05 <= gx <= x1 + 0.05 and z0 - 0.05 <= gz <= z1 + 0.05 and \
                info["floor"] - 0.05 <= gy <= info["floor"] + info["height"] + 0.3:
            a = (x1 - x0) * (z1 - z0)
            if best is None or a < best[0]:
                best = (a, r)
    return best[1] if best else None


def react_signals(ob):
    """The signals an object's `react` custom property (one or a list) follows."""
    r = ob.get("react")
    if r is None:
        return set()
    items = [r] if hasattr(r, "keys") else list(r)
    return {it.get("signal") for it in items if hasattr(it, "keys") and it.get("signal")}


class LightsOff:
    """Context: everything that follows light signal `sig` off for the bake: its light
    objects (custom property "signal" from mansion.py, else by the room they're in), the
    ceiling strips of its rooms (hidden) and the glowing parts of the fixtures wired to it
    (react on "lights"; emission 0 through object-level material copies)."""
    _dark = {}

    def __init__(self, sig, level, room_sig):
        self.sig, self.level, self.room_sig = sig, level, room_sig

    def light_signal(self, L):
        if "signal" in L.keys():
            return L["signal"]
        room = L.get("room") or room_at(self.level, L.matrix_world.translation)
        return self.room_sig.get(room)

    @classmethod
    def dark(cls, m):
        if m.name not in cls._dark:
            d = m.copy()
            d.name = m.name + "_LightsOff"
            for n in d.node_tree.nodes if d.node_tree is not None else []:
                if n.type == "BSDF_PRINCIPLED":
                    n.inputs["Emission Strength"].default_value = 0
                elif n.type == "EMISSION":
                    n.inputs["Strength"].default_value = 0
            cls._dark[m.name] = d
        return cls._dark[m.name]

    def prop_roots(self):
        """(root, lights signal) of every placed prop: the root's "lights" property (mansion.py),
        else matched by position to mansion.json's props."""
        want = []
        for p in self.level["props"]:
            s = p.get("signal")
            s = s.get("lights") if isinstance(s, dict) else None
            if s and not p.get("attach"):
                want.append((p["position"], s))
        skip = {f"{NAME}_Shell", f"{NAME}_Outdoor", f"{NAME}_PreviewLights"}
        out = []
        for o in bpy.data.objects:
            if o.parent is not None or o.type not in ("EMPTY", "MESH") or any(c.name in skip for c in o.users_collection):
                continue
            if "lights" in o.keys():
                if o["lights"]:
                    out.append((o, o["lights"]))
                continue
            x, y, z = o.location
            for (px, py, pz), s in want:
                if abs(px - x) < 0.003 and abs(py - z) < 0.003 and abs(pz + y) < 0.003:
                    out.append((o, s))
                    break
        return out

    def __enter__(self):
        sig = self.sig
        lights = [o for o in bpy.data.collections[f"{NAME}_PreviewLights"].objects
                  if o.type == "LIGHT" and o.data.type != "SUN"]
        self.lights = [L for L in lights if self.light_signal(L) == sig and not L.hide_render]
        for L in self.lights:
            L.hide_render = True
        self.strips = [o for o in bpy.data.collections[f"{NAME}_Shell"].all_objects
                       if o.type == "MESH" and self.room_sig.get(o.get("room")) == sig and not o.hide_render
                       and any(m is not None and m.name.startswith("M_LightStrip") for m in o.data.materials)]
        for o in self.strips:
            o.hide_render = True
        self.slots, roots = [], self.prop_roots()
        for root, s in roots:
            if s != sig:
                continue
            for o in [root] + list(root.children_recursive):
                if o.type != "MESH" or "lights" not in react_signals(o):
                    continue
                for slot in o.material_slots:
                    m = slot.material
                    if m is None:
                        continue
                    self.slots.append((slot, slot.link))
                    slot.link = "OBJECT"
                    slot.material = self.dark(m)
        print(f"lights off {sig}: {len(self.lights)} lights, {len(self.strips)} strip meshes, "
              f"{len(self.slots)} glowing material slots ({sum(1 for _, s in roots if s == sig)} fixtures)")
        return self

    def __exit__(self, *exc):
        for L in self.lights:
            L.hide_render = False
        for o in self.strips:
            o.hide_render = False
        for slot, link in self.slots:
            slot.link = link
        return False


def write_off(room, lm_srgb, mask, off):
    """Write a room's lights-off lightmap + panorama (off: lightmap = off lightmap / the room's
    scale, env = off panorama / ENV_CLAMP, both linear; sh, signal) next to its on state
    (lm_srgb: the on lightmap as stored). Returns the bake JSON's rooms[room].off entry."""
    R = room.capitalize()
    lm_off = lightmap_srgb(off["lightmap"], 1.0)
    # the engine rebuilds off as on x ratio x mix(tint, 1, ratio): fit the tint, log the error
    r, tint, err = off_ratio(to_linear(lm_srgb), to_linear(lm_off), mask)
    print(f"lights off {room}: mean ratio {r[mask].mean():.3f}, tint {np.round(tint, 3).tolist()}, "
          f"rebuild error {err[0]:.3f} (ratio only) / {err[1]:.3f} (with tint)")
    write_webp(f"T_{NAME}_{R}_LightmapOff", lm_off, quality=OFF_QUALITY)
    write_webp(f"T_{NAME}_{R}_EnvOff", textures._to_srgb(off["env"]), quality=OFF_QUALITY)
    return {"signal": off["signal"],
            "lightmap": f"textures/T_{NAME}_{R}_LightmapOff.webp",
            "environment": f"textures/T_{NAME}_{R}_EnvOff.webp",
            "sh": off["sh"],              # the props' diffuse light with the room's lights off
            "tint": [round(float(t), 4) for t in tint],
            "ratio": round(float(r[mask].mean()), 4), "samples": SAMPLES, "date": time.strftime("%Y-%m-%d %H:%M")}


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(PROJECT, "blender", "tools"))
    import slots  # noqa: E402
    slots.acquire("level", 2)            # a bake loads the whole house and renders on the GPU, like a house build
    scene.render.engine = "CYCLES"
    print("device:", use_gpu())
    sys.path.insert(0, HERE)
    p = __import__(LEVEL).P   # level parameters (importing doesn't rebuild anything)
    with open(os.path.join(PROJECT, "assets", "levels", f"{LEVEL}.json")) as f:
        level = json.load(f)

    shell = [o for o in bpy.data.collections[f"{NAME}_Shell"].all_objects
             if o.type == "MESH" and "Lightmap" in o.data.uv_layers]
    out = os.path.join(PROJECT, "assets", "levels", f"{LEVEL}_bake.json")
    partial = ONLY_ROOMS is not None or OUTDOOR_ONLY or STATE == "off"
    stored = json.load(open(out)) if os.path.exists(out) else {}
    previous = stored if partial else {}
    rooms = dict(previous.get("rooms", {})) if partial else {}
    hide = setup_fixtures() if not OUTDOOR_ONLY else []
    room_sig = light_signals(level)

    def todo():
        for room, info in level["rooms"].items():
            if OUTDOOR_ONLY or (ONLY_ROOMS is not None and room not in ONLY_ROOMS):
                continue
            objs = [o for o in shell if o.get("room") == room]
            if objs:
                gx, gy, gz = info["probe"]
                x0, z0, x1, z1 = info["rect"]
                # the environment only lights props and blurry reflections: small rooms get a small one
                big = (x1 - x0) * (z1 - z0) > 150 or info.get("height", 0) > 5
                yield room, info, objs, (gx, -gz, gy), 512 if big else 256      # (probe: glTF -> Blender)

    baked, written = {}, {}
    if STATE in ("on", "both"):
        for room, info, objs, probe, env_w in todo():
            names, lin, mask = bake_lightmap(room, objs, info.get("lightmap") or p["lightmap_res"])
            _, sh, env_rgb = render_environment(room, probe, width=env_w, hide=hide, save=False)
            baked[room] = (names, lin, mask, sh, env_rgb)
        # one scale per open group (rooms joined without a wall): the group's brightest room's
        # scale (rooms of the group not baked now keep theirs, so the new ones match them)
        import plan  # noqa: E402
        groups = open_groups(plan)
        own = {room: room_scale(b[1], b[2]) for room, b in baked.items()}
        for room, (names, lin, mask, sh, env_rgb) in baked.items():
            scale = max([own[r] for r in groups.get(room, {room}) if r in own] +
                        [rooms[r]["lightmap"]["intensity"] / math.pi for r in groups.get(room, {room})
                         if r not in own and r in rooms])
            if scale != own[room]:
                print(f"lightmap {room}: scale {own[room]:.3f} -> {scale:.3f} (shared with {sorted(groups[room] - {room})})")
            R = room.capitalize()
            lm_srgb = lightmap_srgb(lin, scale)
            write_webp(f"T_{NAME}_{R}_Lightmap", lm_srgb)
            write_webp(f"T_{NAME}_{R}_Env", textures._to_srgb(env_rgb), quality=90)
            written[room] = (lm_srgb, mask, scale)
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
            # an on-only re-bake keeps the room's lights-off state (stale if the room's light changed)
            old_off = stored.get("rooms", {}).get(room, {}).get("off")
            if STATE == "on" and old_off:
                rooms[room]["off"] = old_off
                print(f"WARN {room}: kept the lights-off state of {old_off.get('date')}; re-bake it "
                      f"(--state off --rooms {room}) if this room's light changed")
    if STATE in ("off", "both"):
        # one pass per light signal: its lights, strips and glows off, its rooms baked
        by_sig = {}
        for item in todo():
            if room_sig.get(item[0]):
                by_sig.setdefault(room_sig[item[0]], []).append(item)
        for sig, items in by_sig.items():
            with LightsOff(sig, level, room_sig):
                for room, info, objs, probe, env_w in items:
                    R = room.capitalize()
                    if room in written:
                        lm_srgb, mask, scale = written[room]
                    elif room in rooms:
                        # off only: against the stored on state, as the engine shows it
                        scale = rooms[room]["lightmap"]["intensity"] / math.pi
                        lm_srgb = decode(os.path.join(textures.TEX_DIR, f"T_{NAME}_{R}_Lightmap.webp"))
                        mask = None
                    else:
                        print(f"WARN {room}: no on state to go with the off one (bake it with --state both)")
                        continue
                    names, lin, mask_off = bake_lightmap(room, objs, info.get("lightmap") or p["lightmap_res"])
                    mask = mask_off if mask is None else mask
                    _, sh_off, env_off = render_environment(room, probe, width=env_w, hide=hide, save=False, tag="_Off")
                    rooms[room]["off"] = write_off(room, lm_srgb, mask, dict(lightmap=lin / scale, env=env_off,
                                                                             sh=sh_off, signal=sig))
    outdoor = bake_outdoor() if (ONLY_ROOMS is None or OUTDOOR_ONLY) and STATE != "off" else previous.get("outdoor")
    bake = {"rooms": rooms, "exposure": p.get("exposure", 1.0), "samples": SAMPLES if not partial else previous.get("samples", SAMPLES)}
    if partial:
        bake["partial"] = {"rooms": sorted(ONLY_ROOMS or []), "outdoor": OUTDOOR_ONLY, "samples": SAMPLES, "state": STATE}
    if outdoor:
        bake["outdoor"] = outdoor      # vertex-colour scale per kind (flat: colour x light, textured: light)
    with open(out, "w") as f:
        json.dump(bake, f, indent=2)
    print("wrote", out, {r: v["lightmap"]["intensity"] for r, v in rooms.items()})
    print("lights off (mean ratio):", {r: v["off"]["ratio"] for r, v in rooms.items() if v.get("off")})
    missing = sorted(r for r in level["rooms"] if room_sig.get(r) and r in rooms and not rooms[r].get("off"))
    if missing:
        print("no lights-off state yet:", ",".join(missing))
