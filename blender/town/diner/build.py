"""The diner's build: generate (blender/assets/town2_diner.py), merge per material, lightmap UVs,
Cycles bake (golden-hour sun and sky + the diner's own lamps and neon), denoise, export.

  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
      --python blender/town/diner/build.py -- [--samples 512] [--res 2048x1024] [--no-bake]
      [--render front,inside] [--render-samples 64] [--save]

Writes assets/models/town2_diner.gltf (+ .bin, textures/T_Town2_Diner_*), the sidecar
assets/models/town2_diner.json (footprint, size, colliders, entrances) and the lightmap
assets/models/textures/T_Town2_Diner_Lightmap.webp, named in every lightmapped material's extras
(lightmap, lightmapIntensity) for viewer/wild/town.js loadSites.

The lightmap: one W x H atlas, the left half the interior, the right half the exterior (each a
square, so islands pack without aspect games). Non-metals bake DIFFUSE (direct + indirect, no
colour: the light), metals bake GLOSSY (what they show is their reflections; Cycles bakes those
seen along the normal); both are denoised (Open Image Denoise) and stored as sRGB of light /
scale; the runtime's MeshStandardMaterial does colour x lightmap x intensity / pi, so
lightmapIntensity = pi x scale.
"""
import importlib
import json
import math
import os
import shutil
import subprocess
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJECT, "blender", "assets"))
sys.path.insert(0, os.path.join(PROJECT, "blender", "tools"))
sys.path.insert(0, os.path.join(PROJECT, "blender"))

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(k, d=None):
    return argv[argv.index(k) + 1] if k in argv else d


SAMPLES = int(opt("--samples", 256))
RES = tuple(int(v) for v in opt("--res", "2048x1024").split("x"))
BAKE = "--no-bake" not in argv
RENDER = [v for v in (opt("--render", "") or "").split(",") if v]
RENDER_SAMPLES = int(opt("--render-samples", 64))
ASSET = opt("--asset", "town2_diner")
ID = "diner"
MODELS = os.path.join(PROJECT, "assets", "models")
TEXDIR = os.path.join(MODELS, "textures")
LM_NAME = "T_Town2_Diner_Lightmap"
OUT = os.path.join(PROJECT, "build", "diner")
LM_PERCENTILE = 99.5

# the golden look (blender/levels/mansion.py LOOKS["golden"], = the town world's "look"):
# light travels along sun_dir; the asset frame is the estate frame (the site's yaw is 0)
LOOK = dict(sun_dir=(0.94, 0.12, -0.32), sun_strength=6.0, sun_color=(1.0, 0.70, 0.45),
            sky=(0.42, 0.52, 0.72), sky_strength=0.85, horizon=(0.98, 0.76, 0.56))
scene = bpy.context.scene


def log(*a):
    print("[diner]", *a, flush=True)


# ------------------------------------------------------------------ scene

def clear():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


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


def setup_light(k):
    """Sun, sky (a gradient world: zenith blue, warm horizon) and a ground plane round the lot
    (grass-dark, for bounce and for what metals reflect below the horizon); the asset's lamps."""
    try:
        scene.render.engine = "CYCLES"
    except TypeError as e:
        log("engine:", e)
    w = bpy.data.worlds.new("DinerSky")
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*LOOK["horizon"], 1)
    ramp.color_ramp.elements[1].position = 0.45
    ramp.color_ramp.elements[1].color = (*LOOK["sky"], 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = LOOK["sky_strength"]
    sun = bpy.data.lights.new("DinerSun", "SUN")
    sun.energy = LOOK["sun_strength"]
    sun.color = LOOK["sun_color"]
    sun.angle = math.radians(1.2)
    so = bpy.data.objects.new("DinerSun", sun)
    scene.collection.objects.link(so)
    so.rotation_mode = "QUATERNION"
    so.rotation_quaternion = Vector(LOOK["sun_dir"]).normalized().to_track_quat("-Z", "Y")
    # the ground beyond the lot (not baked, not exported)
    me = bpy.data.meshes.new("DinerGround")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=150)
    bmesh.ops.translate(bm, vec=(0, 0, -0.03), verts=bm.verts)
    bm.to_mesh(me)
    gm = bpy.data.materials.new("DinerGroundMat")
    gm.use_nodes = True
    b = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.09, 0.10, 0.055, 1)
    b.inputs["Roughness"].default_value = 1.0
    me.materials.append(gm)
    g = bpy.data.objects.new("DinerGround", me)
    scene.collection.objects.link(g)
    for L in k.lights:
        kind = L["kind"]
        ld = bpy.data.lights.new(f"DinerLamp_{kind}", {"point": "POINT", "spot": "SPOT", "area": "AREA"}[kind])
        ld.energy = L.get("power", 50.0)
        ld.color = L.get("color", (1.0, 0.85, 0.65))
        if kind in ("point", "spot"):
            ld.shadow_soft_size = L.get("radius", 0.05)
        if kind == "spot":
            ld.spot_size = math.radians(L.get("cone", 90))
            ld.spot_blend = L.get("blend", 0.5)
        if kind == "area":
            ld.shape = "RECTANGLE"
            ld.size, ld.size_y = L.get("size", (1.0, 0.1))
        lo = bpy.data.objects.new(ld.name, ld)
        scene.collection.objects.link(lo)
        lo.location = L["loc"]
        d = L.get("dir")
        if d is not None:
            lo.rotation_mode = "QUATERNION"
            lo.rotation_quaternion = Vector(d).normalized().to_track_quat("-Z", "Y")


# ------------------------------------------------------------------ merge + lightmap UVs

def _select(objs, active=None):
    vl = bpy.context.view_layer
    vl.update()          # (thousands of new objects: the layer's object list syncs lazily)
    for o in vl.objects:
        if o is not None:
            o.select_set(False)
    for o in objs:
        o.select_set(True)
    vl.objects.active = active or (objs[0] if objs else None)


def cull_hidden(objs, dead):
    """Delete faces nobody can see (their front lies in a dead volume: under the floors, inside
    the wall cavities, above the ceilings): they'd take lightmap texels and triangles for nothing.
    dead: callables (x, y, z) -> True when the point is in a dead volume. A face goes when its
    centre and four points toward its corners, 3 cm in front of it, are all dead."""
    if not dead:
        return 0
    import bmesh
    from mathutils import Vector
    gone = 0
    for o in objs:
        me = o.data
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.normal_update()
        kill = []
        for f in bm.faces:
            c = f.calc_center_median()
            n = f.normal
            pts = [c] + [c.lerp(v.co, 0.8) for v in list(f.verts)[:4]]
            if all(any(d(*(q + n * 0.03)) for d in dead) for q in pts):
                kill.append(f)
        if kill:
            bmesh.ops.delete(bm, geom=kill, context="FACES")
            gone += len(kill)
            bm.to_mesh(me)
        bm.free()
    empty = [o for o in objs if len(o.data.polygons) == 0]
    for o in empty:
        objs.remove(o)
        bpy.data.objects.remove(o, do_unlink=True)
    log(f"culled {gone} hidden faces ({len(empty)} parts emptied)")
    return gone


def lightmap_uvs(objs):
    """Smart-project a "Lightmap" UV layer on every part, islands scaled to one texel density
    (x sqrt of the part's lm weight), then packed: the interior parts into the atlas's left half,
    the exterior's into the right half."""
    for o in objs:
        me = o.data
        if "UVMap" not in me.uv_layers:
            me.uv_layers.new(name="UVMap")
        lm = me.uv_layers.get("Lightmap") or me.uv_layers.new(name="Lightmap")
        me.uv_layers["UVMap"].active_render = True
        me.uv_layers.active = lm
    scene.tool_settings.use_uv_select_sync = True
    t = time.time()
    _select(objs)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(float(opt("--angle", 66))), island_margin=0.0, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode="OBJECT")
    log(f"smart project {len(objs)} parts: {time.time() - t:.1f}s")
    # one texel density for every part (smart_project normalises each object on its own, and
    # average_islands_scale only within an object): UV area = 3D area x the part's lm weight
    for o in objs:
        me = o.data
        uv = me.uv_layers["Lightmap"]
        a = np.empty(len(uv.data) * 2, np.float32)
        uv.data.foreach_get("uv", a)
        a = a.reshape(-1, 2)
        me.calc_loop_triangles()
        tl = np.array([t.loops[:] for t in me.loop_triangles], np.int64).reshape(-1, 3)
        if not len(tl):
            continue
        p0, p1, p2 = a[tl[:, 0]], a[tl[:, 1]], a[tl[:, 2]]
        uva = float(np.abs((p1[:, 0] - p0[:, 0]) * (p2[:, 1] - p0[:, 1]) - (p2[:, 0] - p0[:, 0]) * (p1[:, 1] - p0[:, 1])).sum() / 2)
        a3 = sum(t.area for t in me.loop_triangles)
        w = float(o.get("lm", 1.0))
        f = math.sqrt(a3 * w / uva) if uva > 1e-12 else 1.0
        uv.data.foreach_set("uv", (a * f).ravel())
        ext = (a.max(axis=0) - a.min(axis=0)) * f
        o["_lmext"] = float(max(ext))
    if "--islands" in argv:
        from bpy_extras import mesh_utils
        fam = {}
        tot = 0
        for o in objs:
            o.data.uv_layers.active = o.data.uv_layers["Lightmap"]
            n = len(mesh_utils.mesh_linked_uv_islands(o.data))
            f = o.name.split(".")[0]
            fam[f] = fam.get(f, 0) + n
            tot += n
        log(f"islands {tot}: " + ", ".join(f"{k} {v}" for k, v in sorted(fam.items(), key=lambda kv: -kv[1])[:25]))
    W, H = RES
    halves = [("in", 0.0), ("out", 0.5)] if W >= 2 * H else [("in", 0.0)]
    for zone, u0 in halves:
        grp = [o for o in objs if (o.get("zone", "out") == zone) or len(halves) == 1]
        if not grp:
            continue
        t = time.time()
        _select(grp)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.select_all(action="SELECT")
        po = (opt("--pack", "CONCAVE,CLOSEST_UDIM,ADD,0.003")).split(",")
        bpy.ops.uv.pack_islands(udim_source=po[1], rotate=True, scale=True, margin_method=po[2],
                                margin=float(po[3]), shape_method=po[0])
        bpy.ops.object.mode_set(mode="OBJECT")
        sx = 0.5 if len(halves) == 2 else 1.0
        for o in grp:
            uv = o.data.uv_layers["Lightmap"]
            a = np.empty(len(uv.data) * 2, np.float32)
            uv.data.foreach_get("uv", a)
            a = a.reshape(-1, 2)
            a[:, 0] = u0 + a[:, 0] * sx
            uv.data.foreach_set("uv", a.ravel())
        area, lo, hi, big = 0.0, [9, 9], [-9, -9], []
        for o in grp:
            me = o.data
            uv = me.uv_layers["Lightmap"]
            a = np.empty(len(uv.data) * 2, np.float32)
            uv.data.foreach_get("uv", a)
            a = a.reshape(-1, 2)
            me.calc_loop_triangles()
            oa = 0.0
            for tri in me.loop_triangles:
                p0, p1, p2 = a[tri.loops[0]], a[tri.loops[1]], a[tri.loops[2]]
                oa += abs((p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (p1[1] - p0[1])) / 2
            area += oa
            big.append((oa, o.name))
            lo = np.minimum(lo, a.min(axis=0))
            hi = np.maximum(hi, a.max(axis=0))
        big.sort(reverse=True)
        log(f"pack {zone}: {len(grp)} parts, {time.time() - t:.1f}s, uv area {area:.3f} of {sx:.2f}, bbox {lo} {hi}, largest {big[:6]}")


def merge(objs, root, name):
    """Join parts per material (one mesh = one draw call). Returns the merged objects."""
    by = {}
    for o in objs:
        by.setdefault(o.data.materials[0].name if o.data.materials else "_none", []).append(o)
    out = []
    for mname, grp in sorted(by.items()):
        _select(grp, grp[0])
        if len(grp) > 1:
            bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        ob.name = ob.data.name = f"{name}_{mname.replace('M_Town2_Diner_', '')}"
        ob.parent = root
        out.append(ob)
    return out


# ------------------------------------------------------------------ bake

def bake_pass(objs, kind, W, H, margin=4):
    img = bpy.data.images.new(f"_bake_{kind}", W, H, alpha=True, float_buffer=True)
    img.generated_color = (0, 0, 0, 0)
    added = []
    for m in {m for o in objs for m in o.data.materials}:
        nd = m.node_tree.nodes.new("ShaderNodeTexImage")
        nd.image = img
        m.node_tree.nodes.active = nd
        added.append((m, nd))
    for o in objs:
        o.data.uv_layers.active = o.data.uv_layers["Lightmap"]
    _select(objs)
    scene.render.bake.margin = margin
    scene.render.bake.use_clear = True
    t = time.time()
    bpy.ops.object.bake(type=kind, pass_filter={"DIRECT", "INDIRECT"}, target="IMAGE_TEXTURES")
    log(f"bake {kind} ({len(objs)} meshes, {W}x{H}, {SAMPLES} spp): {time.time() - t:.0f}s")
    for m, nd in added:
        m.node_tree.nodes.remove(nd)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)[::-1]
    bpy.data.images.remove(img)
    return px[..., :3].copy(), px[..., 3] > 0.5


def dilate(lin, mask, steps=10):
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


def denoise(lin, mask):
    """Open Image Denoise through the compositor (as blender/levels/bake.py)."""
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
        o = tree.nodes.new("NodeGroupOutput")
        tree.links.new(n_img.outputs["Image"], n_dn.inputs["Image"])
        tree.links.new(n_dn.outputs["Image"], o.inputs[0])
    sc.compositing_node_group = tree
    next(n for n in tree.nodes if n.bl_idname == "CompositorNodeImage").image = src
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.render.use_compositing = True
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.image_settings.file_format = "OPEN_EXR"
    bpy.ops.render.render(scene=sc.name)
    path = os.path.join(OUT, "_denoised.exr")
    os.makedirs(OUT, exist_ok=True)
    bpy.data.images["Render Result"].save_render(path, scene=sc)
    res = bpy.data.images.load(path)
    out = np.array(res.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]
    bpy.data.images.remove(res)
    bpy.data.images.remove(src)
    return np.maximum(out, 0)


def to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def write_png(path, img8):
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


def write_lightmap(lin, scale):
    """sRGB of lin / scale (over 1: scaled down as a whole, hue kept), dithered, as WebP."""
    x = lin / scale
    peak = x.max(axis=2, keepdims=True)
    x = np.where(peak > 1.0, x / np.maximum(peak, 1e-9), x)
    s = to_srgb(x)
    rng = np.random.default_rng(1)
    s = s + (rng.random(s.shape[:2] + (1,)) - rng.random(s.shape[:2] + (1,))) * (0.5 / 255)
    img8 = np.round(np.clip(s, 0, 1) * 255).astype(np.uint8)
    png = os.path.join(OUT, LM_NAME + ".png")
    write_png(png, img8)
    os.makedirs(TEXDIR, exist_ok=True)
    out = os.path.join(TEXDIR, LM_NAME + ".webp")
    cwebp = shutil.which("cwebp") or "/opt/homebrew/bin/cwebp"
    subprocess.run([cwebp, "-quiet", "-q", "92", "-sharp_yuv", "-m", "6", "-mt", png, "-o", out], check=True)
    return out


def bake(merged):
    W, H = RES
    lm_objs = [o for o in merged if o.data.materials and o.data.materials[0].get("lm")]
    metal = [o for o in lm_objs if o.data.materials[0].get("metal")]
    scene.cycles.samples = SAMPLES
    scene.cycles.sample_clamp_indirect = 6.0
    scene.cycles.use_denoising = False
    A, mA = bake_pass(lm_objs, "DIFFUSE", W, H)
    lin = denoise(A, mA)
    if metal:
        B, mB = bake_pass(metal, "GLOSSY", W, H)
        linB = denoise(B, mB)
        lin = np.where(mB[..., None], linB, lin)
    lit = lin.max(axis=2)[mA]
    lit = lit[lit > 1e-4]
    scale = float(np.percentile(lit, LM_PERCENTILE)) if lit.size else 1.0
    np.save(os.path.join(OUT, "lightmap_linear.npy"), lin.astype(np.float16))
    path = write_lightmap(lin, scale)
    log(f"lightmap {path}: scale {scale:.3f} (p{LM_PERCENTILE} of lit texels)")
    return scale


# ------------------------------------------------------------------ export

def for_export(mats, scale):
    """Materials as the runtime reads them: no tint node (COLOR_0 does that), metals as
    non-metals, the lightmap in the extras."""
    for m in mats:
        nt = m.node_tree
        b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        mix = nt.nodes.get("DinerTintMix")
        if mix is not None:
            src = mix.inputs["A"].links[0].from_socket if mix.inputs["A"].links else None
            col = tuple(mix.inputs["A"].default_value)
            nt.nodes.remove(mix)
            nt.nodes.remove(nt.nodes["DinerTint"])
            if src is not None:
                nt.links.new(src, b.inputs["Base Color"])
            else:
                b.inputs["Base Color"].default_value = col
        if m.get("metal"):
            b.inputs["Metallic"].default_value = 0.0
        for k in ("lm", "metal", "tex", "bake_hide"):
            if k in m:
                lmflag = m.get("lm")
                del m[k]
                if k == "lm":
                    m["_lm"] = bool(lmflag)
        if m.get("_lm"):
            m["lightmap"] = f"textures/{LM_NAME}.webp"
            m["lightmapIntensity"] = round(math.pi * scale, 4)
        if "_lm" in m:
            del m["_lm"]


def export(root, merged, k, scale):
    import lib.common as common
    path = os.path.join(MODELS, f"town2_{ID}.gltf")
    common.export_gltf(root, path, export_vertex_color="NAME", export_vertex_color_name="Col",
                       export_all_vertex_colors=False, export_image_quality=88)
    tris = 0
    for o in merged:
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
    sx, sy = k.site
    side = dict(asset=f"town2_{ID}", root=root.name,
                footprint=[-sx / 2, -sy / 2, sx / 2, sy / 2], size=[sx, sy, round(k.height, 2)],
                colliders=[[round(v, 3) for v in c] for c in k.colliders],
                entrances=k.entrances, walk_in=True, tris_lod0=tris,
                materials=sorted({o.data.materials[0].name for o in merged if o.data.materials}),
                lightmap=f"textures/{LM_NAME}.webp", lightmap_scale=round(scale, 4))
    json.dump(side, open(os.path.join(MODELS, f"town2_{ID}.json"), "w"), indent=1)
    log(f"export {path}: {tris} tris, {len(merged)} meshes, {len(k.colliders)} colliders")


# ------------------------------------------------------------------ preview renders

def render(k, names):
    scene.cycles.samples = RENDER_SAMPLES
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1600, 900
    scene.view_settings.view_transform = "AgX" if "AgX" in [v.identifier for v in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    for n in names:
        if n not in k.cameras:
            log("no camera", n)
            continue
        loc, at, lens = k.cameras[n]
        cd = bpy.data.cameras.new("DinerCam")
        cd.lens = lens
        cam = bpy.data.objects.new("DinerCam", cd)
        scene.collection.objects.link(cam)
        cam.location = loc
        cam.rotation_mode = "QUATERNION"
        cam.rotation_quaternion = (Vector(at) - Vector(loc)).to_track_quat("-Z", "Y")
        scene.camera = cam
        scene.render.filepath = os.path.join(OUT, "renders", f"{n}.png")
        bpy.ops.render.render(write_still=True)
        log("render", scene.render.filepath)


def report(objs):
    """Triangles by part family (the name before the first underscore-separated detail)."""
    by = {}
    for o in objs:
        me = o.data
        me.calc_loop_triangles()
        fam = o.name.split(".")[0]
        by[fam] = by.get(fam, 0) + len(me.loop_triangles)
    tot = sum(by.values())
    top = sorted(by.items(), key=lambda kv: -kv[1])[:30]
    log(f"triangles {tot}: " + ", ".join(f"{k} {v}" for k, v in top))


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    import slots
    slots.acquire("house", 2) if BAKE else slots.acquire("asset", 4)
    clear()
    log("device", use_gpu())
    A = importlib.import_module(ASSET)
    root, k = A.build()
    log(f"built {len(k.objects)} parts in {time.time() - t0:.1f}s")
    setup_light(k)
    if RENDER:
        render(k, RENDER)
    lod0 = [o for o in k.objects if o.get("lod", 0) == 0]
    cull_hidden(lod0, getattr(k, "dead", []))
    report(lod0)
    lm_parts = [o for o in lod0 if o.data.materials and o.data.materials[0].get("lm")]
    lightmap_uvs(lm_parts)
    merged = merge(lod0, root, A.NAME)
    # hidden in the bake: glass (the sun comes in) and the lamp shades (their bulbs are bake
    # lights inside them); neon stays visible: it lights what's round it
    for o in merged:
        m = o.data.materials[0] if o.data.materials else None
        if m is not None and m.get("bake_hide"):
            o.hide_render = True
    json.dump({n: dict(loc=list(c[0]), at=list(c[1]), lens=c[2]) for n, c in k.cameras.items()}, open(os.path.join(OUT, "cams.json"), "w"), indent=1)
    scale = bake(merged) if BAKE else 1.0
    for o in merged:
        o.hide_render = False
    mats = sorted({m for o in merged for m in o.data.materials}, key=lambda m: m.name)
    for_export(mats, scale)
    export(root, merged, k, scale)
    if "--save" in argv:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "town2_diner.blend"))
    log(f"done in {time.time() - t0:.0f}s")


main()
