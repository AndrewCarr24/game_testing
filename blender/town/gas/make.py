"""The gas station (town2_gas): build, lightmap, bake, export. One headless Blender process:

  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
      --python blender/town/gas/make.py -- [--samples 256] [--no-bake] [--no-export] [--shots]
      [--zones ext,int,lod1] [--res ext=2048x1024,int=1024x1024,lod1=512x256]

1. builds the scene from blender/assets/town2_gas.py (geometry kit town2_gas_kit.py, materials
   town2_gas_mat.py): one mesh per (zone, material), zones ext / int / lod1 / glow;
2. gives every lit zone a second UV set "Lightmap" (smart project, islands scaled by each face's
   density weight `lmw`, packed into the zone's atlas; exported as TEXCOORD_1);
3. bakes Cycles diffuse light (direct + indirect, no albedo) per zone with the golden LOOK's sun
   and sky (blender/levels/mansion.py LOOKS) plus the station's own lamps (area lights under the
   canopy LEDs, the troffers, the coolers), denoises it (bake.py's OIDN pass) and writes
   assets/models/textures/T_Town2_Gas_<Zone>_Lightmap.webp; the reflection panoramas
   T_Town2_Gas_<Zone>_Env.webp (inside: from the middle of the store; outside: under the canopy);
4. names them in each material's extras (lightmap, lightmapIntensity = pi x scale, envMap,
   envMapIntensity) and exports assets/models/town2_gas.gltf + the sidecar town2_gas.json
   (footprint, size, colliders) that laurel_town_world.py and viewer/wild/town.js read.

Never touches the level files. Takes a "house" run slot (GPU bake).
"""
import importlib
import json
import math
import os
import sys
import time

import bpy
import bmesh
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER = os.path.abspath(os.path.join(HERE, "..", ".."))
PROJECT = os.path.abspath(os.path.join(BLENDER, ".."))
for p in (BLENDER, os.path.join(BLENDER, "assets"), os.path.join(BLENDER, "tools"), os.path.join(BLENDER, "levels")):
    sys.path.insert(0, p)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(k, d=None):
    return argv[argv.index(k) + 1] if k in argv else d


SAMPLES = int(opt("--samples", "256"))
NO_BAKE = "--no-bake" in argv
NO_EXPORT = "--no-export" in argv
SHOTS = "--shots" in argv
ZONES = opt("--zones", "ext,int,lod1").split(",")
RES = dict(ext=(1024, 1024), int=(2048, 1024), lod1=(256, 256))
for kv in (opt("--res", "") or "").split(","):
    if "=" in kv:
        k, v = kv.split("=")
        RES[k] = tuple(int(t) for t in v.split("x"))

# bake.py's helpers (denoise, dilate, sRGB encoding, cwebp writer); its argv parsing must not see ours
_saved = sys.argv
sys.argv = ["bake.py"]
import bake as B  # noqa: E402
sys.argv = _saved
from lib import common, textures  # noqa: E402
import mansion as MAN  # noqa: E402  (LOOKS)
import town2_gas  # noqa: E402

OUT_MODELS = os.path.join(PROJECT, "assets", "models")
OUT_TEX = os.path.join(OUT_MODELS, "textures")
BUILD = os.path.join(PROJECT, "build", "town", "gas")
os.makedirs(BUILD, exist_ok=True)
scene = bpy.context.scene
LOOK = MAN.LOOKS["golden"]


def log(*a):
    print("[gas]", *a, flush=True)


# ------------------------------------------------------------------ 2. lightmap UVs
def lightmap_uvs(objs, W, H, pad=2):
    """The zone's "Lightmap" UVs: Blender's smart project cuts the charts; every chart is then
    measured in metres, scaled by its faces' density weight (lmw), and skyline-packed into the
    W x H atlas at the highest uniform texel density that fits (common.pack_charts' packer, on
    the charts' bounding rectangles; 90-degree turns allowed). Faces in a lightmap group (lmg:
    a shelf's goods) share one chart, projected along their axis. Returns texels per metre."""
    for o in objs:
        me = o.data
        if "Lightmap" not in me.uv_layers:
            me.uv_layers.new(name="Lightmap")
        me.uv_layers.active = me.uv_layers["Lightmap"]
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    vl.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(50), island_margin=0.0, area_weight=0.0, correct_aspect=False, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    charts = []          # (bm index, faces, {loop: (u, v) metres}, w)
    bms = []
    for o in objs:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.faces.ensure_lookup_table()
        uv = bm.loops.layers.uv["Lightmap"]
        lw = bm.faces.layers.float.get("lmw")
        lg = bm.faces.layers.int.get("lmg")
        la = bm.faces.layers.int.get("lma")
        bi = len(bms)
        bms.append((o, bm, uv))
        groups, rest = {}, []
        for f in bm.faces:
            if lg is not None and f[lg]:
                # (front and back faces of a group get separate charts: projected together, the
                # backs - against a shelf or a wall, dark - overwrote the fronts' texels)
                ax = f[la]
                groups.setdefault((f[lg], f.normal[ax] >= 0), []).append(f)
            else:
                rest.append(f)
        for gid, faces in groups.items():
            ax = faces[0][la]
            a, b2 = [i for i in range(3) if i != ax]
            loc = {l: (l.vert.co[a], l.vert.co[b2]) for f in faces for l in f.loops}
            charts.append((bi, faces, loc, max(f[lw] for f in faces) if lw else 1.0))
        for faces in uv_islands_of(rest, uv):
            a3 = sum(f.calc_area() for f in faces)
            auv = 0.0
            for f in faces:
                q = [l[uv].uv for l in f.loops]
                for k in range(1, len(q) - 1):
                    auv += abs((q[k].x - q[0].x) * (q[k + 1].y - q[0].y) - (q[k + 1].x - q[0].x) * (q[k].y - q[0].y)) / 2
            sc = math.sqrt(a3 / auv) if auv > 1e-12 and a3 > 1e-9 else 0.0
            loc = {l: (l[uv].uv.x * sc, l[uv].uv.y * sc) for f in faces for l in f.loops}
            charts.append((bi, faces, loc, max(f[lw] for f in faces) if lw else 1.0))
    # chart rectangles in metres (weighted)
    rects = []
    for bi, faces, loc, w in charts:
        us = [p[0] for p in loc.values()]
        vs = [p[1] for p in loc.values()]
        u0, v0 = min(us), min(vs)
        rects.append((u0, v0, max(max(us) - u0, 1e-3) * w, max(max(vs) - v0, 1e-3) * w, w))
    area = sum(r[2] * r[3] for r in rects)

    def attempt(k):
        R = [(max(1, int(math.ceil(r[2] * k))) + 2 * pad, max(1, int(math.ceil(r[3] * k))) + 2 * pad) for r in rects]
        return common._skyline_pack(R, W, H), R
    lo_k, hi_k = 0.5, math.sqrt(W * H / max(area, 1e-6)) * 1.1
    for _ in range(16):
        mid = (lo_k + hi_k) / 2
        ok, _ = attempt(mid)
        lo_k, hi_k = (mid, hi_k) if ok else (lo_k, mid)
    k = lo_k
    placed, R = attempt(k)
    if placed is None:
        raise RuntimeError("lightmap charts don't fit")
    for (bi, faces, loc, w), (u0, v0, su, sv, _), (px, py, turned) in zip(charts, rects, placed):
        o, bm, uv = bms[bi]
        for l, (u, v) in loc.items():
            t = ((u - u0) * w * k, (v - v0) * w * k)
            if turned:
                t = t[::-1]
            l[uv].uv = ((px + pad + t[0]) / W, (py + pad + t[1]) / H)
    for o, bm, uv in bms:
        bm.to_mesh(o.data)
        bm.free()
        o.select_set(False)
        o.data.uv_layers.active = o.data.uv_layers["UVMap"]
        o.data.uv_layers["UVMap"].active_render = True
    log(f"  {len(charts)} charts, {k:.1f} texels/m at weight 1")
    return k


def uv_islands_of(faces, uv):
    """Faces grouped by UV connectivity (shared vertex with the same UV)."""
    idx = {f: i for i, f in enumerate(faces)}
    parent = list(range(len(faces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    seen = set()
    for f in faces:
        for l in f.loops:
            v = l.vert
            if v in seen:
                continue
            seen.add(v)
            by = {}
            for l2 in v.link_loops:
                if l2.face not in idx:
                    continue
                key = (round(l2[uv].uv.x, 5), round(l2[uv].uv.y, 5))
                if key in by:
                    a, b = find(by[key]), find(idx[l2.face])
                    parent[a] = b
                else:
                    by[key] = idx[l2.face]
    groups = {}
    for i, f in enumerate(faces):
        groups.setdefault(find(i), []).append(f)
    return list(groups.values())


def uv_islands(bm, uv):
    """Faces grouped by UV connectivity (shared vertex with the same UV)."""
    parent = {f.index: f.index for f in bm.faces}
    bm.faces.index_update()

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for v in bm.verts:
        by = {}
        for l in v.link_loops:
            key = (round(l[uv].uv.x, 5), round(l[uv].uv.y, 5))
            if key in by:
                a, b = find(by[key]), find(l.face.index)
                parent[a] = b
            else:
                by[key] = l.face.index
    groups = {}
    faces = list(bm.faces)
    for f in faces:
        groups.setdefault(find(f.index), []).append(f)
    return list(groups.values())


# ------------------------------------------------------------------ 3. the bake world
def setup_world(kit, col):
    sd = bpy.data.lights.new("Town2Gas_Sun", "SUN")
    sd.energy = LOOK["sun_strength"]
    sd.color = LOOK["sun_color"]
    sd.angle = math.radians(1.2)
    sun = bpy.data.objects.new("Town2Gas_Sun", sd)
    sun.rotation_euler = Vector(LOOK["sun_dir"]).to_track_quat("-Z", "Y").to_euler()
    col.objects.link(sun)
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    nt = world.node_tree
    bg = next(nd for nd in nt.nodes if nd.type == "BACKGROUND")
    # a sky that is brighter and warmer at the horizon, deeper overhead (the LOOK's dome colours),
    # normalised to the LOOK's sky light
    geo = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(geo.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    # (the LOOK's colours a third of the way to grey: the full-blue sky turned the shaded lot and
    # the back of the store blue next to the town's own ground)
    def grey(c):
        return Vector(c) * 0.5 + Vector((1, 1, 1)) * (sum(c) / 3) * 0.5
    sky = grey(LOOK["sky"])
    hz, zn = grey(LOOK["sky_horizon"]), grey(LOOK["sky_zenith"])
    k = sky.length / ((hz + zn) / 2).length
    e0, e1 = ramp.color_ramp.elements[0], ramp.color_ramp.elements[1]
    e0.position, e1.position = 0.0, 0.7
    e0.color = (*(hz * k * 0.9), 1)
    e1.color = (*(zn * k * 1.1), 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    # (x 1.5: the wilderness runtime lights its ground with more sky than the house bake; at the
    # LOOK's own strength the lot's shade read near-black next to the town)
    bg.inputs["Strength"].default_value = LOOK["sky_strength"] * 1.5
    # the ground round the lot (the town's mown grass and road), for bounce and the sky's horizon
    me = bpy.data.meshes.new("Town2Gas_Surround")
    bm = bmesh.new()
    R = 160.0
    vs = [bm.verts.new(p) for p in ((-R, -R, -0.03), (R, -R, -0.03), (R, R, -0.03), (-R, R, -0.03))]
    bm.faces.new(vs)
    bm.to_mesh(me)
    bm.free()
    # (the town round the lot: mown grass in sun, the road; it bounces warm light into the shade)
    m = common.pbr_material("M_Town2Gas_BakeGround", (0.2, 0.18, 0.12), roughness=1.0)
    me.materials.append(m)
    g = bpy.data.objects.new("Town2Gas_Surround", me)
    col.objects.link(g)
    # the station's own lamps
    for i, L in enumerate(kit.lights):
        kind = L["kind"].upper()
        ld = bpy.data.lights.new(f"Town2Gas_L{i}", kind)
        ld.energy = L["energy"]
        ld.color = L["color"]
        if kind == "AREA":
            ld.shape = "RECTANGLE"
            ld.size, ld.size_y = L["size"]
            if "spread" in L:
                ld.spread = math.radians(L["spread"])
        elif kind == "SPOT":
            ld.spot_size = math.radians(L.get("angle", 60))
            ld.spot_blend = L.get("blend", 0.5)
            ld.shadow_soft_size = L.get("radius", 0.05)
        else:
            ld.shadow_soft_size = L.get("radius", 0.05)
        ob = bpy.data.objects.new(ld.name, ld)
        ob.location = L["loc"]
        rx, ry, rz = L["rot"]
        ob.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz) + L["zrot"])
        if "aim" in L:
            ob.rotation_euler = (Vector(L["aim"]) - Vector(L["loc"])).to_track_quat("-Z", "Y").to_euler()
        col.objects.link(ob)
    return sun


def use_gpu():
    return B.use_gpu()


# ------------------------------------------------------------------ 4. bake one zone
def bake_zone(zone, objs, W, H, hide):
    for o in hide:
        o.hide_render = True
    img = bpy.data.images.new(f"Town2Gas_{zone}_Bake", W, H, alpha=False, float_buffer=True)
    added = []
    for mat in {m for o in objs for m in o.data.materials}:
        node = mat.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = img
        mat.node_tree.nodes.active = node
        added.append((mat, node))
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(False)
    for o in objs:
        o.data.uv_layers.active = o.data.uv_layers["Lightmap"]
        o.select_set(True)
    vl.objects.active = objs[0]
    scene.render.engine = "CYCLES"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = False
    scene.cycles.sample_clamp_indirect = 6.0
    scene.cycles.max_bounces = 6
    scene.render.bake.margin = 6
    scene.render.bake.use_clear = True
    t = time.time()
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"DIRECT", "INDIRECT"}, target="IMAGE_TEXTURES")
    log(f"bake {zone} {W}x{H}: {time.time() - t:.0f}s")
    for mat, node in added:
        mat.node_tree.nodes.remove(node)
    lin = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)[::-1, :, :3]
    bpy.data.images.remove(img)
    for o in objs:
        o.select_set(False)
        o.data.uv_layers.active = o.data.uv_layers["UVMap"]
    for o in hide:
        o.hide_render = False
    mask = chart_mask(objs, W, H)
    lin = B.denoise(lin, mask)
    return lin, mask


def chart_mask(objs, W, H):
    """Texels the zone's lightmap charts cover (rasterised triangles; rows top-down)."""
    mask = np.zeros((H, W), bool)
    for o in objs:
        me = o.data
        me.calc_loop_triangles()
        uv = np.empty(len(me.loops) * 2, np.float32)
        me.uv_layers["Lightmap"].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2) * (W, H)
        for tri in me.loop_triangles:
            p = uv[list(tri.loops)]
            x0, y0 = np.floor(p.min(axis=0)).astype(int)
            x1, y1 = np.ceil(p.max(axis=0)).astype(int)
            x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
            if x1 <= x0 or y1 <= y0:
                continue
            mask[y0:y1, x0:x1] = True        # (bounding boxes: generous, which the dilation wants anyway)
    return mask[::-1]


def env_panorama(name, probe, width=256):
    """A 360-degree radiance panorama (reflections only) -> T_Town2_Gas_<name>_Env.webp; returns
    (file, clamp)."""
    cam_data = bpy.data.cameras.new(f"Town2Gas_Env_{name}")
    cam_data.type = "PANO"
    try:
        cam_data.panorama_type = "EQUIRECTANGULAR"
    except AttributeError:
        cam_data.cycles.panorama_type = "EQUIRECTANGULAR"
    cam = bpy.data.objects.new(cam_data.name, cam_data)
    scene.collection.objects.link(cam)
    cam.location = probe
    cam.rotation_euler = (math.radians(90), 0, math.radians(-90))
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = width, width // 2
    scene.render.resolution_percentage = 100
    scene.cycles.samples = min(SAMPLES, 128)
    scene.cycles.use_denoising = True
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "HDR"
    path = os.path.join(BUILD, f"env_{name}.hdr")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]
    bpy.data.images.remove(img)
    clamp = 3.0
    px = np.minimum(px, clamp) / clamp
    fname = f"T_Town2_Gas_{name.capitalize()}_Env"
    B.write_webp(fname, textures._to_srgb(px), quality=88)
    src = os.path.join(textures.TEX_DIR, fname + ".webp")
    os.replace(src, os.path.join(OUT_TEX, fname + ".webp"))
    bpy.data.objects.remove(cam, do_unlink=True)
    return f"textures/{fname}.webp", clamp


# ------------------------------------------------------------------ the security monitor's feeds
def render_feeds(kit, w=256, h=128):
    """The four cameras the monitors show (pumps, door, register, the back lot with the van),
    rendered in the station's own light and made to look like a cheap DVR's quad view: washed,
    greenish, vignetted, scan lines, a white time bar. Returns a (2h, 2w, 3) linear image."""
    out = np.zeros((2 * h, 2 * w, 3), np.float32)
    cam_data = bpy.data.cameras.new("Town2Gas_CCTV")
    cam_data.lens = 14.0
    cam = bpy.data.objects.new("Town2Gas_CCTV", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.engine = "CYCLES"
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = w, h, 100
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = "HDR"
    rng = np.random.default_rng(3)
    for i, key in enumerate(("cam_pumps", "cam_door", "cam_register", "cam_back")):
        if key not in kit.marks:
            continue
        cam.location = kit.marks[key]
        cam.rotation_euler = (Vector(kit.marks[key + "_at"]) - Vector(kit.marks[key])).to_track_quat("-Z", "Y").to_euler()
        path = os.path.join(BUILD, f"feed_{key}.hdr")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(path)
        px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]
        bpy.data.images.remove(img)
        px = px / (1.0 + px) * 1.6                                  # a soft roll-off (auto exposure)
        lum = px @ np.array([0.3, 0.59, 0.11], np.float32)
        px = lum[..., None] * np.array([0.82, 1.0, 0.86], np.float32) * 0.8 + px * 0.2
        yy, xx = np.mgrid[0:h, 0:w]
        vig = 1 - 0.45 * (((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        px *= np.clip(vig, 0.3, 1)[..., None]
        px *= (0.9 + 0.1 * (yy % 2))[..., None]
        px += rng.normal(0, 0.012, px.shape).astype(np.float32)
        px[4:12, 6:70] = px[4:12, 6:70] * 0.3 + 0.55               # the time bar (blank: no text)
        r, c = divmod(i, 2)
        out[r * h:(r + 1) * h, c * w:(c + 1) * w] = np.clip(px, 0, 1)
    out[h - 1:h + 1, :] = 0.0
    out[:, w - 1:w + 1] = 0.0
    bpy.data.objects.remove(cam, do_unlink=True)
    return out


# ------------------------------------------------------------------ main
def main():
    t0 = time.time()
    if not NO_BAKE:
        import slots
        slots.acquire("house", 2)
    # factory scene: clear it
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    col = bpy.data.collections.new("Town2Gas")
    scene.collection.children.link(col)
    kit, info = town2_gas.build(col)
    objs = {k: o for k, o in kit.objects.items()}
    by_zone = {}
    for (zone, mat), o in objs.items():
        by_zone.setdefault(zone, []).append(o)
    tris = {z: common.triangle_count(v) for z, v in by_zone.items()}
    log("triangles", tris, "objects", {z: len(v) for z, v in by_zone.items()})
    dens = {}
    for zone in ("ext", "int", "lod1"):
        if zone in by_zone:
            dens[zone] = round(lightmap_uvs(by_zone[zone], *RES[zone]), 1)
    log("lightmap texels/m", dens)
    bake_col = bpy.data.collections.new("Town2Gas_Bake")
    scene.collection.children.link(bake_col)
    setup_world(kit, bake_col)
    meta = dict(triangles=tris, texels_per_m=dens, zones={})
    if not NO_BAKE:
        log("cycles:", use_gpu())
        # the monitors' feeds, rendered from the station itself, into the sign atlas
        import town2_gas_tex as TX
        feeds = render_feeds(kit)
        TX.signs(feeds)
        bpy.data.images["T_Town2_Gas_Signs"].reload()
        log("cctv feeds rendered")
        glow = [o for z, v in by_zone.items() if z.endswith("_g") for o in v]
        lod0 = [o for z, v in by_zone.items() if not z.startswith("lod1") for o in v]
        for zone in ZONES:
            if zone not in by_zone:
                continue
            W, H = RES[zone]
            hide = glow + (lod0 if zone == "lod1" else by_zone.get("lod1", []))
            hide = list({o.name: o for o in hide}.values())
            lin, mask = bake_zone(zone, by_zone[zone], W, H, hide)
            scale = B.room_scale(lin, mask)
            srgb = B.lightmap_srgb(lin, scale)
            fname = f"T_Town2_Gas_{zone.capitalize()}_Lightmap"
            B.write_webp(fname, srgb, quality=92)
            os.replace(os.path.join(textures.TEX_DIR, fname + ".webp"), os.path.join(OUT_TEX, fname + ".webp"))
            meta["zones"][zone] = dict(file=f"textures/{fname}.webp", intensity=round(math.pi * scale, 4), size=[W, H])
            log(zone, "scale", round(scale, 3))
        # reflections: the store from its middle, the forecourt from under the canopy
        for z, v in by_zone.items():
            if z.startswith("lod1"):
                for o in v:
                    o.hide_render = True
        for name, key in (("int", "probe_int"), ("ext", "probe_ext")):
            if key in kit.marks:
                f, clamp = env_panorama(name, kit.marks[key])
                meta["zones"].setdefault(name, {})["env"] = f
                meta["zones"][name]["env_clamp"] = clamp
        json.dump(meta, open(os.path.join(BUILD, "bake.json"), "w"), indent=1)
    else:
        old = os.path.join(BUILD, "bake.json")
        if os.path.exists(old):
            meta["zones"] = json.load(open(old)).get("zones", {})
    # material extras
    for (zone, mat), o in objs.items():
        z = meta["zones"].get(zone)
        for m in o.data.materials:
            if z and "file" in z:
                m["lightmap"] = z["file"]
                m["lightmapIntensity"] = z["intensity"]
            base = zone.split("_")[0]
            ez = meta["zones"].get("int" if base == "int" else "ext") or {}
            if "env" in ez and kit.mats[mat].get("reflect", 0) > 0:
                m["envMap"] = ez["env"]
                m["envMapIntensity"] = round(kit.mats[mat]["reflect"] * ez["env_clamp"], 3)
    if not NO_EXPORT:
        export(kit, info, objs)
    if SHOTS:
        town2_gas.shots(kit, objs, BUILD)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BUILD, "gas.blend"))
    log(f"done in {time.time() - t0:.0f}s")


def export(kit, info, objs):
    root = bpy.data.objects.new("Town2Gas", None)
    lod0 = bpy.data.objects.new("Town2Gas_LOD0", None)
    lod1 = bpy.data.objects.new("Town2Gas_LOD1", None)
    for e in (root, lod0, lod1):
        bpy.context.scene.collection.objects.link(e)
    lod0.parent = root
    lod1.parent = root
    lod1["lodDistance"] = info.get("lod_distance", 140)
    for (zone, mat), o in objs.items():
        o.parent = lod1 if zone.startswith("lod1") else lod0
        # (the lightmap is the second UV set)
        me = o.data
        if "Lightmap" in me.uv_layers and me.uv_layers[0].name != "UVMap":
            raise RuntimeError(f"{o.name}: UVMap must be the first UV layer")
        if "Lightmap" not in me.uv_layers and not zone.endswith("_g"):
            log("WARN no lightmap UVs on", o.name)
        for a in list(me.attributes):
            if a.name in ("lmw", "lmg", "lma"):
                me.attributes.remove(a)
    path = os.path.join(OUT_MODELS, "town2_gas.gltf")
    common.export_gltf(root, path, quality=88)
    x0, y0, x1, y1 = info["footprint"]
    side = dict(footprint=[x0, y0, x1, y1], size=[round(x1 - x0, 2), round(y1 - y0, 2), info["height"]],
                walk_in=True, colliders=kit.colliders, marks=kit.marks,
                lod=dict(node="Town2Gas_LOD1", distance=info.get("lod_distance", 140)),
                note="town2_gas (blender/assets/town2_gas.py, blender/town/gas/make.py): asset frame = Blender, origin at the lot's floor centre, front -Y")
    json.dump(side, open(os.path.join(OUT_MODELS, "town2_gas.json"), "w"), separators=(",", ":"))
    log("exported", path, os.path.getsize(path.replace(".gltf", ".bin")) // 1024, "KB bin,", len(kit.colliders), "colliders")


main()
