"""Builds, bakes and exports THE BAR (blender/assets/town2_bar.py) for the town runtime
(prompts/town_building.md, viewer/wild/town.js loadSites):

  1. the asset's kit -> one mesh per material under the root empty Town2Bar
  2. lightmap UVs ("Lightmap" = TEXCOORD_1): smart-projected, density-weighted per part (lmw),
     packed into two atlases: the interior's (T_Town2_Bar_LightmapIn) and the outside's
     (T_Town2_Bar_LightmapOut), each with its own range (a dark room and a sunlit lot in one
     8-bit map band badly)
  3. the light rig: the golden-hour sun and sky of blender/levels/mansion.py LOOKS (in the
     asset's frame: the site's yaw), every lamp of the kit, the neon / bulbs / screens as
     emitters; the terrain around the site (build/wilderness/laurel_town/terrain.npz) for the
     bounce and the horizon
  4. Cycles bakes the diffuse light (direct + indirect) into each atlas, Open Image Denoise,
     encodes 8-bit sRGB of light / scale (material extras: lightmap, lightmapIntensity = scale x pi:
     three.js divides by pi)
  5. two reflection panoramas (inside at the bar, outside on the lot), radiance / 3 in 8-bit
     sRGB (extras: envMap, envMapIntensity), in the world's orientation
  6. LOD1 (Town2Bar_LOD1): a low hull with the lit look baked into one small unlit texture
  7. glTF (Draco) assets/models/town2_bar.gltf + the sidecar town2_bar.json (footprint, size,
     colliders, entrances, views) for laurel_town_world.py

  Blender -b --factory-startup --python blender/town/bar/build.py -- [--samples 256] [--no-bake]
          [--draft] [--renders] [--no-export]
"""
import json
import math
import os
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJECT, "blender"))
sys.path.insert(0, os.path.join(PROJECT, "blender", "assets"))
sys.path.insert(0, os.path.join(PROJECT, "blender", "tools"))
from lib import common  # noqa: E402
import slots  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


DRAFT = "--draft" in argv
SAMPLES = int(opt("--samples", 48 if DRAFT else 384))
BAKE = "--no-bake" not in argv
EXPORT = "--no-export" not in argv
RENDERS = "--renders" in argv
ONLY_VIEWS = opt("--views", "")
LM_IN = tuple(int(v) for v in opt("--lm-in", "1024x1024").split("x"))
LM_OUT = tuple(int(v) for v in opt("--lm-out", "1024x512").split("x"))
OUT_MODELS = os.path.join(PROJECT, "assets", "models")
OUT_TEX = os.path.join(OUT_MODELS, "textures")
BUILD = os.path.join(PROJECT, "build", "town2_bar")
os.makedirs(BUILD, exist_ok=True)
ENV_CLAMP = 3.0
LM_PERCENTILE = 99.5

slots.acquire("level" if BAKE else "asset", 2 if BAKE else 4)
t_start = time.time()

import town2_bar as asset  # noqa: E402
import town2_bar_tex as tex  # noqa: E402

scene = bpy.context.scene
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)

GROUP_IN = ("Floor", "Pine", "Wood", "Vinyl", "Props")
GROUP_OUT = ("Block", "Siding", "Roof", "Deck", "Gravel", "PropsOut", "Glass")


def blueprint_rects():
    """The estate house's ground floor (blender/levels/plan.py) for the back room's blueprint."""
    sys.path.insert(0, os.path.join(PROJECT, "blender", "levels"))
    try:
        import plan
        out = []
        for r in plan.ROOMS.values():
            if r.get("level", 0) != 0:
                continue
            x0, y0, x1, y1 = r["rect"]
            out.append([round((x0 + 28) / 56, 4), round((y0 + 22) / 44, 4), round((x1 + 28) / 56, 4), round((y1 + 22) / 44, 4)])
        return out
    except Exception as e:  # (the blueprint is a detail; never fail the build for it)
        print("blueprint: no plan", e)
        return None


# ------------------------------------------------------------------ 1. geometry
t0 = time.time()
kit, P = asset.build()
mats = tex.materials(plan=blueprint_rects())
col = common.fresh_collection("Town2Bar")
root = common.empty(asset.NAME, col)
objs = kit.to_objects(col, mats, asset.NAME)
for o in objs.values():
    o.parent = root
tris = {m: kit.tris.get(m, 0) for m in objs}
GLOW = objs.get("Glow")            # the halo cards: no lightmap, out of every bake (the lamps carry the light)
if GLOW is not None:
    GLOW.hide_render = True
print(f"geometry: {sum(tris.values())} tris in {len(objs)} meshes ({time.time() - t0:.1f}s) {tris}")
print("by section:", dict(sorted(kit.sec_tris.items(), key=lambda kv: -kv[1])))


# ------------------------------------------------------------------ 2. lightmap UVs
def select_only(obs, active=None):
    for o in bpy.data.objects:
        try:
            o.select_set(False)
        except (RuntimeError, AttributeError):
            pass
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or obs[0]


VLIT = 0.25          # parts at or under this lightmap weight are lit per vertex (see vertex_light)
WHITE = 4            # texels of the atlas' corner held at 1.0: the vertex-lit faces' lightmap UVs point there


def face_arrays(me):
    """(lightmap weight, vertex-lit, loop totals) per face."""
    w = np.empty(len(me.polygons), np.float32)
    me.attributes["lmw"].data.foreach_get("value", w)
    v = np.empty(len(me.polygons), np.int8)
    me.attributes["vlit"].data.foreach_get("value", v)
    lt = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("loop_total", lt)
    return w, v.astype(bool), lt


def small_faces_vertex_lit(obs, min_area=0.02, min_width=0.05):
    """Faces too small or thin for a chart of their own (box edges, bevels, slats: thousands of
    islands, each with its margin) take their light per vertex too."""
    n_all = n_v = 0
    for o in obs:
        me = o.data
        co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lv)
        ls = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get("loop_start", ls)
        lt = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get("loop_total", lt)
        ar = np.empty(len(me.polygons), np.float32); me.polygons.foreach_get("area", ar)
        nxt = np.arange(len(me.loops)) + 1
        last = ls + lt - 1
        nxt[last] = ls
        el = np.linalg.norm(co[lv[nxt]] - co[lv], axis=1)
        per = np.add.reduceat(el, ls)
        width = 2 * ar / np.maximum(per, 1e-6)
        v = np.empty(len(me.polygons), np.int8); me.attributes["vlit"].data.foreach_get("value", v)
        small = (ar < min_area) | (width < min_width)
        v2 = (v.astype(bool) | small).astype(np.int8)
        me.attributes["vlit"].data.foreach_set("value", v2)
        n_all += len(v2); n_v += int(v2.sum())
    print(f"vertex-lit faces: {n_v} of {n_all}")


def pack_islands_texels(obs, W, H, pad):
    """Our own packer for the charts (Blender's left most of the atlas empty with ~1000 islands):
    the islands (faces joined where they share a vertex at the same UV), their bounding boxes
    skyline-packed (lib/common._skyline_pack, 90 degree turns allowed) at the highest uniform
    texel density that fits, `pad` texels around each, clear of the white corner."""
    isl = []
    for oi, o in enumerate(obs):
        me = o.data
        uv = np.empty(len(me.loops) * 2, np.float32)
        me.uv_layers["Lightmap"].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lv)
        w, vl, lt = face_arrays(me)
        ls = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get("loop_start", ls)
        parent = list(range(len(me.polygons)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        q = np.round(uv * 1e5).astype(np.int64)
        seen = {}
        for fi in np.where(~vl)[0]:
            for li in range(ls[fi], ls[fi] + lt[fi]):
                key = (int(lv[li]), int(q[li, 0]), int(q[li, 1]))
                g = seen.get(key)
                if g is None:
                    seen[key] = fi
                else:
                    a_, b_ = find(fi), find(g)
                    if a_ != b_:
                        parent[a_] = b_
        groups = {}
        for fi in np.where(~vl)[0]:
            groups.setdefault(find(fi), []).append(fi)
        for fs in groups.values():
            loops = np.concatenate([np.arange(ls[f_], ls[f_] + lt[f_]) for f_ in fs])
            lo, hi = uv[loops].min(axis=0), uv[loops].max(axis=0)
            isl.append((oi, loops, lo, np.maximum(hi - lo, 1e-6)))
    Hp = H - (WHITE + 2)
    rects_at = lambda k: [(int(math.ceil(sz[0] * k)) + 2 * pad, int(math.ceil(sz[1] * k)) + 2 * pad) for _, _, _, sz in isl]
    lo_k, hi_k = 0.5, 4096.0
    if common._skyline_pack(rects_at(lo_k), W, Hp) is None:
        raise RuntimeError("lightmap charts don't fit")
    for _ in range(22):
        mid = math.sqrt(lo_k * hi_k)
        if common._skyline_pack(rects_at(mid), W, Hp) is not None:
            lo_k = mid
        else:
            hi_k = mid
    k = lo_k
    placed = common._skyline_pack(rects_at(k), W, Hp)
    uvs = []
    for o in obs:
        u = np.empty(len(o.data.loops) * 2, np.float32)
        o.data.uv_layers["Lightmap"].data.foreach_get("uv", u)
        uvs.append(u.reshape(-1, 2))
    covered = 0.0
    for (oi, loops, lo, sz), (px, py, turned) in zip(isl, placed):
        t = (uvs[oi][loops] - lo) * k
        if turned:
            t = t[:, ::-1]
        uvs[oi][loops, 0] = (px + pad + t[:, 0]) / W
        uvs[oi][loops, 1] = (py + pad + (WHITE + 2) + t[:, 1]) / H
        covered += sz[0] * sz[1] * k * k
    for o, u in zip(obs, uvs):
        o.data.uv_layers["Lightmap"].data.foreach_set("uv", u.ravel())
    return k, covered / (W * H)


def lightmap_uvs(obs, size, pad=3):
    """Charts for the faces that take a lightmap (lmw > VLIT): smart-projected, scaled by
    sqrt(lmw), the atlas' aspect, packed. The small parts (lmw <= VLIT: bottles, hardware, wires,
    neon) get no chart: their lightmap UV is the white corner and their light goes into COLOR_0
    (vertex_light): thousands of tiny islands, each with its margin, had shrunk the atlas to 1%."""
    W, H = size
    for o in obs:
        me = o.data
        lm = me.uv_layers.get("Lightmap") or me.uv_layers.new(name="Lightmap")
        me.uv_layers.active = lm
        w, vl, lt = face_arrays(me)
        me.polygons.foreach_set("select", ~vl)
        me.update()
    select_only(obs)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60.0), island_margin=0.0, area_weight=0.0, correct_aspect=False, scale_to_bounds=False)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode="OBJECT")
    # one density across the objects (average_islands_scale evens the islands within an object
    # only), then the part's weight (sqrt(lmw): lmw scales the texel count) and the aspect
    for o in obs:
        me = o.data
        lm = me.uv_layers["Lightmap"]
        uv = np.empty(len(me.loops) * 2, np.float32)
        lm.data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        w, vl, lt = face_arrays(me)
        me.calc_loop_triangles()
        tri = np.empty(len(me.loop_triangles) * 3, np.int32)
        me.loop_triangles.foreach_get("loops", tri)
        tp = np.empty(len(me.loop_triangles), np.int32)
        me.loop_triangles.foreach_get("polygon_index", tp)
        keep = ~vl[tp]
        t3 = uv[tri].reshape(-1, 3, 2)[keep]
        a_uv = float(np.abs(np.cross(t3[:, 1] - t3[:, 0], t3[:, 2] - t3[:, 0])).sum() / 2)
        co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        lvx = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lvx)
        p3 = co[lvx[tri]].reshape(-1, 3, 3)[keep]
        a_3d = float(np.linalg.norm(np.cross(p3[:, 1] - p3[:, 0], p3[:, 2] - p3[:, 0]), axis=1).sum() / 2)
        f = math.sqrt(a_3d / a_uv) if a_uv > 1e-12 else 1.0
        uv *= f * np.sqrt(np.repeat(np.maximum(w, 0.02), lt))[:, None]
        lm.data.foreach_set("uv", uv.ravel())
    t = time.time()
    k, fill = pack_islands_texels(obs, W, H, pad)
    print(f"lightmap pack {W}x{H}: {time.time() - t:.1f}s, {k:.1f} texels/m at lmw 1, charts cover {fill:.2f} of the atlas")
    for o in obs:
        me = o.data
        lm = me.uv_layers["Lightmap"]
        uv = np.empty(len(me.loops) * 2, np.float32)
        lm.data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        w, vl, lt = face_arrays(me)
        uv[np.repeat(vl, lt)] = (WHITE / 2 / W, WHITE / 2 / H)
        lm.data.foreach_set("uv", uv.ravel())
        me.uv_layers.active = me.uv_layers["UVMap"]
        me.uv_layers["UVMap"].active_render = True
        me.polygons.foreach_set("select", np.ones(len(me.polygons), bool))


groups = {"In": [objs[m] for m in GROUP_IN if m in objs], "Out": [objs[m] for m in GROUP_OUT if m in objs]}
sizes = {"In": LM_IN, "Out": LM_OUT}
t0 = time.time()
for g, obs in groups.items():
    small_faces_vertex_lit(obs)
    lightmap_uvs(obs, sizes[g])
print(f"lightmap UVs: {time.time() - t0:.1f}s")


# ------------------------------------------------------------------ 3. light rig + context
def look():
    sys.path.insert(0, os.path.join(PROJECT, "blender", "levels"))
    src = open(os.path.join(PROJECT, "blender", "levels", "mansion.py")).read()
    a = src.index("LOOKS = {")
    b = src.index("\n}\n", a) + 2
    ns = {}
    exec(src[a:b], {"dict": dict}, ns)
    return ns["LOOKS"][P["look"]]


LK = look()
yaw = math.radians(P["world"]["yaw"])
Rz = Matrix.Rotation(-yaw, 3, "Z")            # estate -> asset frame


def rig():
    lc = common.fresh_collection("Town2Bar_Lights")
    sd = Rz @ Vector(LK["sun_dir"])
    ld = bpy.data.lights.new("Town2Bar_Sun", "SUN")
    ld.energy, ld.color, ld.angle = LK["sun_strength"], LK["sun_color"], math.radians(1.5)
    sun = bpy.data.objects.new("Town2Bar_Sun", ld)
    sun.rotation_euler = sd.to_track_quat("-Z", "Y").to_euler()
    lc.objects.link(sun)
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = next(nd for nd in world.node_tree.nodes if nd.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*LK["sky"], 1)
    bg.inputs["Strength"].default_value = LK["sky_strength"]
    for i, L in enumerate(kit.lights):
        if L["power"] <= 0:
            continue
        kind = L["kind"]
        d = bpy.data.lights.new(f"Town2Bar_L{i}", kind)
        d.energy, d.color = L["power"], L["color"]
        if kind in ("POINT", "SPOT"):
            d.shadow_soft_size = L.get("radius", 0.05)
        if kind == "SPOT":
            d.spot_size, d.spot_blend = math.radians(L.get("angle", 60.0)), L.get("blend", 0.3)
        if kind == "AREA":
            d.shape = "RECTANGLE"
            d.size, d.size_y = L["size"]
        ob = bpy.data.objects.new(f"Town2Bar_L{i}", d)
        ob.location = L["pos"]
        if "aim" in L:
            ob.rotation_euler = (Vector(L["aim"]) - Vector(L["pos"])).to_track_quat("-Z", "Y").to_euler()
        lc.objects.link(ob)
    return sun


def terrain_context():
    """The terrain around the site in the asset frame (bounce, horizon, the bank under the deck)."""
    D = os.path.join(PROJECT, "build", "wilderness", "laurel_town")
    try:
        z = np.load(os.path.join(D, "terrain.npz"))
        st = json.load(open(os.path.join(D, "stats.json")))
        wj = json.load(open(os.path.join(D, "world", "world.json")))
    except Exception as e:
        print("terrain context: none", e)
        return None
    H, WL = z["H"], z["river_level"]
    g = st["grid"]
    x0, y0, c = g["x0"], g["y0"], g["cell"]
    bar = next((b for b in wj["town"]["buildings"] if b["id"] == "bar"), None)
    pad = float(bar["z"]) if bar else float(np.median(H))
    oy = wj["estate_offset"][1]
    ex, ey = P["world"]["x"] + 1500.0, P["world"]["y"]        # the asset origin in the town frame (x local, y estate)
    R = 140.0
    step = 2
    i0 = int((ex - R - x0) / c); i1 = int((ex + R - x0) / c)
    j0 = int((ey - oy - R - y0) / c); j1 = int((ey - oy + R - y0) / c)
    step = 2
    i1 = i0 + step * ((i1 - i0) // step)
    j1 = j0 + step * ((j1 - j0) // step)
    bm = bmesh.new()
    cols = []
    V = {}
    for j in range(j0, j1 + 1, step):
        for i in range(i0, i1 + 1, step):
            X, Y = x0 + i * c, y0 + j * c + oy
            dxe, dye = X - ex, Y - ey
            ax, ay = -dxe, -dye                       # yaw 180: asset = -(estate - origin)
            a = math.radians(P["world"]["yaw"] - 180.0)
            ax, ay = ax * math.cos(a) - ay * math.sin(a), ax * math.sin(a) + ay * math.cos(a)
            V[(i, j)] = bm.verts.new((ax, ay, float(H[j, i]) - pad))
    water = set()
    for j in range(j0, j1, step):
        for i in range(i0, i1, step):
            q = [V[(i, j)], V[(i + step, j)], V[(i + step, j + step)], V[(i, j + step)]]
            try:
                f = bm.faces.new(q)
            except ValueError:
                continue
            if f.normal.z < 0:
                f.normal_flip()
            wl = WL[j, i]
            if np.isfinite(wl) and wl > H[j, i] + 0.05:
                water.add(f.index)
    bm.faces.index_update()
    me = bpy.data.meshes.new("Town2Bar_Terrain")
    bm.to_mesh(me)
    bm.free()
    ca = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
    for p in me.polygons:
        c_ = (0.03, 0.035, 0.035, 1) if p.index in water else (0.09, 0.1, 0.05, 1)
        for li in p.loop_indices:
            ca.data[li].color = c_
    m = bpy.data.materials.new("Town2Bar_TerrainMat")
    m.use_nodes = True
    bs = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    vc = m.node_tree.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Col"
    m.node_tree.links.new(vc.outputs["Color"], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.95
    me.materials.append(m)
    ob = bpy.data.objects.new("Town2Bar_Terrain", me)
    cc = common.fresh_collection("Town2Bar_Context")
    cc.objects.link(ob)
    # the river's surface (a flat plane at the water level, darker: bounce only)
    wl = WL[j0:j1, i0:i1]
    lvl = float(np.nanmedian(wl[np.isfinite(wl)])) - pad if np.isfinite(wl).any() else -4.0
    print(f"terrain context: pad z {pad:.2f}, water {lvl:.2f}, {len(me.polygons)} faces")
    P["_water"] = lvl
    P["_pad"] = pad
    return ob


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
            return kind
    scene.cycles.device = "CPU"
    return "CPU"


scene.render.engine = "CYCLES"
print("cycles:", use_gpu())
sun = rig()
terrain = terrain_context()


# ------------------------------------------------------------------ 4. bake
def chart_mask(obs, W, H):
    mask = np.zeros((H, W), bool)
    for o in obs:
        me = o.data
        uv = np.empty(len(me.loops) * 2, np.float32)
        me.uv_layers["Lightmap"].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        ls = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get("loop_start", ls)
        lt = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get("loop_total", lt)
        for s, t in zip(ls, lt):
            q = uv[s:s + t]
            u0, v0 = q.min(axis=0)
            u1, v1 = q.max(axis=0)
            if u1 - u0 < 1e-7 and v1 - v0 < 1e-7:
                continue
            mask[max(0, int(v0 * H)):min(H, int(math.ceil(v1 * H))), max(0, int(u0 * W)):min(W, int(math.ceil(u1 * W)))] = True
    return mask[::-1]


def dilate(lin, mask, steps=10):
    out, m = lin.copy(), mask.astype(np.float32)
    for _ in range(steps):
        acc = np.zeros_like(out)
        ws = np.zeros_like(m)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            acc += np.roll(np.roll(out * m[..., None], dy, 0), dx, 1)
            ws += np.roll(np.roll(m, dy, 0), dx, 1)
        grow = (m == 0) & (ws > 0)
        out[grow] = acc[grow] / ws[grow][..., None]
        m = np.maximum(m, grow.astype(np.float32))
    return out


def denoise(lin, mask):
    lin = dilate(lin, mask)
    h, w, _ = lin.shape
    src = bpy.data.images.new("_LMNoisy", w, h, alpha=False, float_buffer=True)
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
    path = os.path.join(BUILD, "_denoised.exr")
    bpy.data.images["Render Result"].save_render(path, scene=sc)
    res = bpy.data.images.load(path)
    out = np.array(res.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]
    bpy.data.images.remove(res)
    bpy.data.images.remove(src)
    return np.maximum(out, 0)


def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def save_image(name, srgb, fmt="WEBP", quality=92, folder=OUT_TEX):
    os.makedirs(folder, exist_ok=True)
    h, w, _ = srgb.shape
    img = bpy.data.images.new("_save_" + name, w, h, alpha=False)
    img.pixels.foreach_set(np.concatenate([srgb[::-1], np.ones((h, w, 1), np.float32)], axis=2).astype(np.float32).ravel())
    path = os.path.join(folder, name + (".webp" if fmt == "WEBP" else ".png"))
    img.filepath_raw = path
    img.file_format = fmt
    img.save(quality=quality) if fmt == "WEBP" else img.save()
    bpy.data.images.remove(img)
    return path


def bake_group(g, obs, size):
    W, H = size
    img = bpy.data.images.new(f"Town2Bar_{g}_Bake", W, H, alpha=False, float_buffer=True)
    added = []
    for o in obs:
        for m in o.data.materials:
            nd = m.node_tree.nodes.new("ShaderNodeTexImage")
            nd.image = img
            m.node_tree.nodes.active = nd
            added.append((m, nd))
        o.data.uv_layers.active = o.data.uv_layers["Lightmap"]
    select_only(obs)
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = False
    scene.cycles.sample_clamp_indirect = 6.0
    scene.cycles.max_bounces = 6
    scene.cycles.diffuse_bounces = 4
    scene.render.bake.margin = 6
    scene.render.bake.use_clear = True
    t = time.time()
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"DIRECT", "INDIRECT"}, target="IMAGE_TEXTURES", margin=6)
    print(f"bake {g} {W}x{H} @ {SAMPLES}: {time.time() - t:.0f}s")
    for m, nd in added:
        m.node_tree.nodes.remove(nd)
    for o in obs:
        o.data.uv_layers.active = o.data.uv_layers["UVMap"]
    lin = np.array(img.pixels[:], np.float32).reshape(H, W, 4)[::-1, :, :3]
    bpy.data.images.remove(img)
    mask = chart_mask(obs, W, H)
    np.save(os.path.join(BUILD, f"lm_{g}_raw.npy"), lin.astype(np.float16))
    lin = denoise(lin, mask)
    mask[-WHITE - 2:, :WHITE + 2] = False
    lit = lin.max(axis=2)[mask]
    lit = lit[lit > 1e-5]
    scale = float(np.percentile(lit, LM_PERCENTILE)) if lit.size else 1.0
    x = lin / scale
    peak = x.max(axis=2, keepdims=True)
    x = np.where(peak > 1, x / np.maximum(peak, 1e-6), x)       # hue-preserving clip
    x[-WHITE:, :WHITE] = 1.0              # the white corner (rows top-down: uv (0, 0) is the last row)
    name = f"T_Town2_Bar_Lightmap{g}"
    save_image(name, to_srgb(x), quality=94)
    save_image(name, to_srgb(x), fmt="PNG", folder=BUILD)
    print(f"lightmap {g}: scale {scale:.3f}, mean {float(lin[mask].mean()):.4f}")
    return name, scale


def vertex_bake(g, obs):
    """The vertex-lit faces' light (lmw <= VLIT): Cycles' diffuse light baked into a "Light"
    colour attribute (corner domain); apply_vertex_light folds it into Tint at export."""
    for o in obs:
        me = o.data
        la = me.color_attributes.get("Light") or me.color_attributes.new("Light", "FLOAT_COLOR", "CORNER")
        me.color_attributes.active_color = la
    select_only(obs)
    scene.cycles.samples = max(64, SAMPLES // 2)
    t = time.time()
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"DIRECT", "INDIRECT"}, target="VERTEX_COLORS")
    print(f"vertex bake {g}: {time.time() - t:.0f}s")
    for o in obs:
        o.data.color_attributes.active_color = o.data.color_attributes["Tint"]


def apply_vertex_light(obs, scale):
    """COLOR_0 of a vertex-lit face = tint x light / scale; its lightmap UV reads the white
    texel (1.0 x scale x pi in three.js) -> albedo x tint x light, as the lightmap gives the rest."""
    for o in obs:
        me = o.data
        if "Light" not in me.color_attributes:
            continue
        n = len(me.loops)
        tc = np.empty(n * 4, np.float32); me.color_attributes["Tint"].data.foreach_get("color", tc)
        lc = np.empty(n * 4, np.float32); me.color_attributes["Light"].data.foreach_get("color", lc)
        tc, lc = tc.reshape(-1, 4), lc.reshape(-1, 4)
        w, vl, lt = face_arrays(me)
        vl = np.repeat(vl, lt)
        v = lc[:, :3] / scale
        peak = v.max(axis=1, keepdims=True)
        v = np.where(peak > 1, v / np.maximum(peak, 1e-6), v)
        tc[vl, :3] = tc[vl, :3] * v[vl]
        me.color_attributes["Tint"].data.foreach_set("color", tc.ravel())
        me.color_attributes.remove(me.color_attributes["Light"])
        me.color_attributes.active_color = me.color_attributes["Tint"]


def render_env(name, pos, width=512, samples=128):
    cam_d = bpy.data.cameras.new(name)
    cam_d.type = "PANO"
    try:
        cam_d.panorama_type = "EQUIRECTANGULAR"
    except AttributeError:
        cam_d.cycles.panorama_type = "EQUIRECTANGULAR"
    cam = bpy.data.objects.new(name, cam_d)
    scene.collection.objects.link(cam)
    cam.location = pos
    # image centre = the world's +X (three.js), image right = three.js +Z; the asset sits at the
    # site's yaw, so rotate bake.py's camera (90, 0, -90) by it
    cam.rotation_euler = (math.radians(90), 0, math.radians(-90) - yaw)
    scene.camera = cam
    sun.visible_camera = False
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = width, width // 2, 100
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = "OPEN_EXR"
    path = os.path.join(BUILD, name + ".exr")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(path)
    w, h = im.size
    px = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, :3]
    bpy.data.images.remove(im)
    bpy.data.objects.remove(cam, do_unlink=True)
    px = np.minimum(px, ENV_CLAMP) / ENV_CLAMP
    out = save_image(name, to_srgb(px), quality=90)
    print(f"env {name}: mean {float(px.mean() * ENV_CLAMP):.3f}")
    return name


baked = {}
envs = {}
if BAKE:
    for g, obs in groups.items():
        baked[g] = bake_group(g, obs, sizes[g])
        vertex_bake(g, obs)
    f = P["floor"]
    envs["In"] = render_env("T_Town2_Bar_EnvIn", (-2.0, 1.2, f + 1.5), samples=64 if DRAFT else 160)
    envs["Out"] = render_env("T_Town2_Bar_EnvOut", (2.0, -15.0, 1.6), samples=64 if DRAFT else 160)
else:
    for g in groups:
        p = os.path.join(BUILD, f"T_Town2_Bar_Lightmap{g}.png")
        meta = os.path.join(BUILD, "bake.json")
        if os.path.exists(meta):
            baked[g] = (f"T_Town2_Bar_Lightmap{g}", json.load(open(meta))["scale"][g])
    envs = {"In": "T_Town2_Bar_EnvIn", "Out": "T_Town2_Bar_EnvOut"}
if BAKE:
    json.dump({"scale": {g: v[1] for g, v in baked.items()}, "samples": SAMPLES}, open(os.path.join(BUILD, "bake.json"), "w"))


# ------------------------------------------------------------------ 6. LOD1
def lod1():
    """A low hull: walls, roof, the porch roof, the lot, the deck, the sign, boxes for the
    vehicles; its look (albedo x light + glow) baked into a 256 px unlit texture."""
    L, D, plate = P["L"], P["D"], P["plate"]
    ridge = plate + D / 2 * P["pitch"]
    bm = bmesh.new()

    def box(lo, hi):
        b2 = bmesh.new()
        bmesh.ops.create_cube(b2, size=1.0)
        bmesh.ops.scale(b2, vec=[hi[i] - lo[i] for i in range(3)], verts=b2.verts)
        bmesh.ops.translate(b2, vec=[(hi[i] + lo[i]) / 2 for i in range(3)], verts=b2.verts)
        me = bpy.data.meshes.new("_t"); b2.to_mesh(me); b2.free()
        bm.from_mesh(me); bpy.data.meshes.remove(me)
    box((-L / 2, -D / 2, 0.0), (L / 2, D / 2, plate))
    ov = P["overhang"]
    vs = [bm.verts.new(p) for p in ((-L / 2 - 0.35, -D / 2 - ov, plate - ov * P["pitch"]), (L / 2 + 0.35, -D / 2 - ov, plate - ov * P["pitch"]),
                                     (L / 2 + 0.35, 0, ridge), (-L / 2 - 0.35, 0, ridge), (-L / 2 - 0.35, D / 2 + ov, plate - ov * P["pitch"]),
                                     (L / 2 + 0.35, D / 2 + ov, plate - ov * P["pitch"]))]
    bm.faces.new([vs[0], vs[1], vs[2], vs[3]])
    bm.faces.new([vs[5], vs[4], vs[3], vs[2]])
    bm.faces.new([bm.verts.new((-L / 2, -D / 2, plate)), bm.verts.new((-L / 2, 0, ridge)), bm.verts.new((-L / 2, D / 2, plate))][::-1])
    bm.faces.new([bm.verts.new((L / 2, -D / 2, plate)), bm.verts.new((L / 2, 0, ridge)), bm.verts.new((L / 2, D / 2, plate))])
    pd = P["porch_depth"]
    box((P["porch_x0"], -D / 2 - pd, 0.0), (P["porch_x1"], -D / 2, P["floor"]))
    box((P["porch_x0"], -D / 2 - pd - 0.3, P["porch_beam"]), (P["porch_x1"], -D / 2, P["porch_beam"] + 0.5))
    box((P["deck_x0"], D / 2, -1.0), (P["deck_x1"], P["deck_y1"], P["floor"]))
    x0, y0, x1, y1 = P["footprint"]
    q = [bm.verts.new(p) for p in ((x0, y0, 0.01), (x1, y0, 0.01), (x1, y1, 0.01), (x0, y1, 0.01))]
    bm.faces.new(q)
    for (cx, cy, w, d, h) in ((-4.1, -14.0, 2.0, 6.0, 2.05), (-1.35, -14.0, 2.0, 6.0, 2.05), (3.4, -13.8, 2.0, 5.4, 1.85)):
        box((cx - w / 2, cy - d / 2, 0.0), (cx + w / 2, cy + d / 2, h))
    me = bpy.data.meshes.new("Town2Bar_LOD1")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("Town2Bar_LOD1", me)
    col.objects.link(ob)
    ob.parent = root
    me.uv_layers.new(name="UVMap")
    select_only([ob])
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


def bake_lod1(ob, size=256):
    """Bake the full-detail look onto the hull (selected-to-active: diffuse colour x light +
    emission), then give it an unlit material."""
    img = bpy.data.images.new("Town2Bar_LOD1_Bake", size, size, alpha=False, float_buffer=True)
    m = bpy.data.materials.new("M_Town2_Bar_LOD1")
    m.use_nodes = True
    nt = m.node_tree
    nd = nt.nodes.new("ShaderNodeTexImage")
    nd.image = img
    nt.nodes.active = nd
    ob.data.materials.append(m)
    srcs = [o for o in objs.values() if o.name != ob.name and o.data.materials[0].name not in ("M_Town2_Bar_Glass", "M_Town2_Bar_Glow")]
    select_only(srcs + [ob], active=ob)
    scene.cycles.samples = 32 if DRAFT else 96
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = 0.6
    scene.render.bake.max_ray_distance = 2.0
    scene.render.bake.margin = 4
    bpy.ops.object.bake(type="COMBINED", pass_filter={"DIRECT", "INDIRECT", "COLOR", "DIFFUSE", "EMIT"}, target="IMAGE_TEXTURES",
                        use_selected_to_active=True, cage_extrusion=0.6, max_ray_distance=2.0, margin=4)
    scene.render.bake.use_selected_to_active = False
    lin = np.array(img.pixels[:], np.float32).reshape(size, size, 4)[::-1, :, :3]
    bpy.data.images.remove(img)
    path = save_image("T_Town2_Bar_LOD1", to_srgb(lin * 0.95), fmt="PNG", folder=BUILD)
    nt.nodes.clear()
    it = nt.nodes.new("ShaderNodeTexImage")
    it.image = bpy.data.images.load(path)
    bg = nt.nodes.new("ShaderNodeBackground")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(it.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


lod = lod1()
if BAKE:
    t0 = time.time()
    bake_lod1(lod)
    print(f"LOD1 bake: {time.time() - t0:.0f}s")


# ------------------------------------------------------------------ previews (Cycles, the full look)
VIEWS = {
    # name: (eye, target, lens mm) in the asset frame
    "lot_low": ((-21.0, -27.0, 0.45), (2.0, -6.0, 2.4), 24),
    "porch": ((-12.4, -8.6, 2.05), (8.0, -9.4, 2.0), 22),
    "down_bar": ((-9.2, 1.6, 2.05), (3.5, 4.6, 1.5), 50),
    "pool_top": ((-2.6, -1.05, 3.35), (-2.6, -1.0, 0.0), 26),
    "jukebox": ((4.4, 4.2, 1.35), (5.55, 6.3, 1.2), 32),
    "backroom": ((-8.3, 4.6, 1.7), (-15.7, 4.6, 1.5), 35),
    "room_stage": ((-6.5, -4.5, 2.1), (14.0, 1.5, 1.3), 24),
    "deck": ((15.0, 16.0, -1.8), (6.0, 7.0, 1.8), 24),
    "stage": ((8.0, -2.8, 2.0), (15.0, 0.6, 1.4), 28),
}


def renders():
    cam_d = bpy.data.cameras.new("Town2Bar_Cam")
    cam = bpy.data.objects.new("Town2Bar_Cam", cam_d)
    scene.collection.objects.link(cam)
    scene.camera = cam
    sun.visible_camera = True
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.cycles.samples = 48 if DRAFT else 128
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items] else "Standard"
    scene.render.image_settings.file_format = "PNG"
    lod.hide_render = True
    if GLOW is not None:
        GLOW.hide_render = False
    out = []
    for nm, (eye, tgt, lens) in VIEWS.items():
        if ONLY_VIEWS and nm not in ONLY_VIEWS.split(","):
            continue
        cam.location = eye
        cam.rotation_euler = (Vector(tgt) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
        cam_d.lens = lens
        cam_d.clip_start = 0.05
        p = os.path.join(BUILD, "renders", nm + ".png")
        scene.render.filepath = p
        bpy.ops.render.render(write_still=True)
        out.append(p)
    lod.hide_render = False
    print("renders:", " ".join(out))


if RENDERS:
    renders()


# ------------------------------------------------------------------ 7. export
def sidecar():
    x0, y0, x1, y1 = P["footprint"]
    lo, hi = common.world_aabb([o for o in objs.values()])
    cols = [[round(v, 3) for v in c] for c in kit.colliders]
    S = dict(asset="town2_bar", root=asset.NAME, footprint=[x0, y0, x1, y1], size=[round(x1 - x0, 2), round(y1 - y0, 2), round(hi[2], 2)],
             bounds=[[round(v, 2) for v in lo], [round(v, 2) for v in hi]], walk_in=True, below_m=0.0, floor=P["floor"],
             tris_lod0=int(sum(tris.values())), tris_lod1=len(lod.data.polygons) * 2,
             materials=sorted(m.name for m in mats.values()), colliders=cols,
             entrances=[dict(pos=[P["door_x"], -P["D"] / 2 - P["porch_depth"] - 0.9, 0.0], facing="-Y", width=1.0, kind="door", note="the front door, open, up the porch steps"),
                        dict(pos=[P["deck_door_x"], P["D"] / 2 + 1.0, P["floor"]], facing="+Y", width=1.6, kind="door", note="to the river deck"),
                        dict(pos=[P["stair_x"], P["deck_y1"] + P["stair_steps"] * 0.28, P["landing_z"]], facing="+Y", width=1.3, kind="stair", note="the landing at the water")],
             world=P["world"], lightmaps={g: dict(file=f"textures/{v[0]}.webp", intensity=round(v[1] * math.pi, 4)) for g, v in baked.items()})
    json.dump(S, open(os.path.join(OUT_MODELS, "town2_bar.json"), "w"), separators=(",", ":"))
    return S


if EXPORT:
    for g, obs in groups.items():
        if g in baked:
            apply_vertex_light(obs, baked[g][1])
        for o in obs:
            m = o.data.materials[0]
            tex.export_prep(m)
            if g in baked:
                m["lightmap"] = f"textures/{baked[g][0]}.webp"
                # (the interior a stop brighter than physical: the runtime has no eye adaptation, and
                # a room lit like a real bar at dusk reads black after the golden-hour lot)
                m["lightmapIntensity"] = round(baked[g][1] * math.pi * (P["interior_exposure"] if g == "In" else 1.0), 5)
            if envs.get(g if m.name != "M_Town2_Bar_Glass" else "Out"):
                m["envMap"] = f"textures/{envs[g if m.name != 'M_Town2_Bar_Glass' else 'Out']}.webp"
                m["envMapIntensity"] = ENV_CLAMP
    if GLOW is not None:
        GLOW.hide_render = False
        tex.export_prep(GLOW.data.materials[0])
    # (the bake's helpers out of the export: the root's hierarchy only)
    path = os.path.join(OUT_MODELS, "town2_bar.gltf")
    common.export_gltf(root, path, export_vertex_color="NAME", export_vertex_color_name="Tint",
                       export_draco_texcoord_quantization=14)
    S = sidecar()
    sz = sum(os.path.getsize(os.path.join(OUT_MODELS, f)) for f in os.listdir(OUT_MODELS) if f.startswith("town2_bar"))
    print(f"exported {path}: {S['tris_lod0']} tris LOD0, {S['tris_lod1']} LOD1, {len(S['colliders'])} colliders, model files {sz / 1e6:.2f} MB")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BUILD, "town2_bar.blend"))
print(f"done in {time.time() - t_start:.0f}s")
