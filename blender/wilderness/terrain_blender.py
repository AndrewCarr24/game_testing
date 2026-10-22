"""Blender phase of the wilderness terrain (terrain.py writes build/wilderness/<name>/terrain.npz):
chunked LOD meshes with skirts, water and backdrop meshes, Draco glTF export with a "Bake"
vertex colour, an import check against the collider sampler, and renders.

  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
      --python blender/wilderness/terrain_blender.py -- <name> [--no-export] [--no-render] [--res 1600x900]

Writes build/wilderness/<name>/
  models/terrain_L<k>.gltf (+ .bin)   one file per LOD, one node per chunk: Wild_Terrain_<cx>_<cy>_L<k>
  models/water.gltf, models/backdrop.gltf
  manifest.json                       chunks, LOD steps, skirt depths, triangles, file sizes, import check, timings
  render_*.png                        Eevee renders (mask-driven material) + the unlit engine look
Takes a "level" run slot (blender/tools/slots.py): it builds ~3M triangles and renders on the GPU.
"""
import argparse
import json
import math
import os
import sys
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [HERE, os.path.join(PROJECT, "blender"), os.path.join(PROJECT, "blender", "tools")]
import terrain  # noqa: E402
import slots  # noqa: E402
from lib import common  # noqa: E402


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?", default="demo")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--res", default="1600x900")
    ap.add_argument("--samples", type=int, default=32)
    return ap.parse_args(argv)


# --------------------------------------------------------------------------------- meshes
def tris_grid(ny, nx):
    """Two triangles per cell, split along (j, i)-(j+1, i+1) like terrain.height_at."""
    j, i = np.mgrid[0:ny - 1, 0:nx - 1]
    a = (j * nx + i).ravel()
    b, c, d = a + 1, a + nx + 1, a + nx
    return np.concatenate([np.stack([a, b, c], 1), np.stack([a, c, d], 1)])


def perimeter(ny, nx):
    """Border vertex indices of an ny x nx grid, counter-clockwise from the south-west corner."""
    s = [i for i in range(nx)]
    e = [j * nx + nx - 1 for j in range(1, ny)]
    n = [(ny - 1) * nx + i for i in range(nx - 2, -1, -1)]
    w = [j * nx for j in range(ny - 2, 0, -1)]
    return np.array(s + e + n + w)


def make_mesh(name, co, tris, col, mat, normals=None, colors=None, uv=None, props=None, extra=None):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(co))
    me.vertices.foreach_set("co", co.astype(np.float32).ravel())
    me.loops.add(tris.size)
    me.loops.foreach_set("vertex_index", tris.astype(np.int32).ravel())
    me.polygons.add(len(tris))
    me.polygons.foreach_set("loop_start", np.arange(0, tris.size, 3, dtype=np.int32))
    me.update()
    if uv is not None:
        lay = me.uv_layers.new(name="UVMap")
        lay.data.foreach_set("uv", uv[tris.ravel()].astype(np.float32).ravel())
    if colors is not None:
        attr = me.color_attributes.new("Bake", "FLOAT_COLOR", "POINT")
        rgba = np.concatenate([colors, np.ones((len(colors), 1))], 1).astype(np.float32)
        attr.data.foreach_set("color", rgba.ravel())
        me.color_attributes.active_color = attr
    for nm, c in (extra or {}).items():       # render-only attributes (export writes "Bake" only)
        at = me.color_attributes.new(nm, "FLOAT_COLOR", "POINT")
        at.data.foreach_set("color", np.concatenate([c, np.ones((len(c), 1))], 1).astype(np.float32).ravel())
    me.shade_smooth()
    if normals is not None:
        me.normals_split_custom_set_from_vertices(normals.astype(np.float32))
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    for k, v in (props or {}).items():
        ob[k] = v
    return ob


def chunk_mesh(name, H, N, B, x0, y0, cell, j0, i0, size, step, skirt, col, mat, extent):
    """Chunk covering samples [j0, j0+size] x [i0, i0+size] at `step`."""
    js = np.arange(j0, j0 + size + 1, step)
    is_ = np.arange(i0, i0 + size + 1, step)
    J, I = np.meshgrid(js, is_, indexing="ij")
    ny, nx = J.shape
    co = np.stack([x0 + I * cell, y0 + J * cell, H[J, I]], -1).reshape(-1, 3)
    nrm = N[J, I].reshape(-1, 3)
    rgb = B[J, I].reshape(-1, 3)
    uv = np.stack([(co[:, 0] - x0) / extent, (co[:, 1] - y0) / extent], 1)
    tris = tris_grid(ny, nx)
    if skirt > 0:   # border ring copied `skirt` m down; quads face outward
        ring = perimeter(ny, nx)
        base = len(co)
        low = co[ring].copy()
        low[:, 2] -= skirt
        co = np.vstack([co, low])
        nrm = np.vstack([nrm, nrm[ring]])
        rgb = np.vstack([rgb, rgb[ring]])
        uv = np.vstack([uv, uv[ring]])
        p, q = ring, np.roll(ring, -1)
        pl, ql = base + np.arange(len(ring)), base + np.roll(np.arange(len(ring)), -1)
        tris = np.vstack([tris, np.stack([p, pl, ql], 1), np.stack([p, ql, q], 1)])
    return make_mesh(name, co, tris, col, mat, nrm, rgb, uv)


def border_error(H, j0, i0, size, step):
    """Max height difference along the chunk border between this LOD (linear between its
    samples) and the full-resolution border: the crack a neighbour at LOD0 could show."""
    if step == 1:
        return 0.0
    err = 0.0
    for line in (H[j0, i0:i0 + size + 1], H[j0 + size, i0:i0 + size + 1],
                 H[j0:j0 + size + 1, i0], H[j0:j0 + size + 1, i0 + size]):
        x = np.arange(len(line))
        approx = np.interp(x, x[::step], line[::step])
        err = max(err, float(np.abs(line - approx).max()))
    return err


def water_mesh(name, level, x0, y0, cell, step, col, mat):
    L = level[::step, ::step]
    ny, nx = L.shape
    ok = np.isfinite(L)
    J, I = np.mgrid[0:ny, 0:nx]
    cellok = ok[:-1, :-1] & ok[1:, :-1] & ok[:-1, 1:] & ok[1:, 1:]
    tris = tris_grid(ny, nx).reshape(2, ny - 1, nx - 1, 3)[:, cellok].reshape(-1, 3)
    used = np.unique(tris)
    remap = np.full(ny * nx, -1)
    remap[used] = np.arange(len(used))
    co = np.stack([x0 + I.ravel()[used] * cell * step, y0 + J.ravel()[used] * cell * step,
                   np.nan_to_num(L.ravel()[used])], -1)
    nrm = np.tile([0.0, 0.0, 1.0], (len(used), 1))
    return make_mesh(name, co, remap[tris], col, mat, nrm, None, None, dict(outdoor="water"))


def backdrop_mesh(name, Hb, Bb, gb, inner, Hfine_edge_err, col, mat, Ab=None):
    k0, k1 = inner
    n = Hb.shape[0]
    J, I = np.mgrid[0:n, 0:n]
    co = np.stack([gb["x0"] + I * gb["cell"], gb["y0"] + J * gb["cell"], Hb], -1).reshape(-1, 3)
    N, _, _ = terrain.normals(Hb, gb["cell"])
    inside = np.zeros((n - 1, n - 1), bool)
    inside[k0:k1 - 1, k0:k1 - 1] = True
    tris = tris_grid(n, n).reshape(2, n - 1, n - 1, 3)[:, ~inside].reshape(-1, 3)
    # inner skirt (faces the play area) hides the slivers between the coarse and fine edges
    ring = []
    m = k1 - k0
    for t in range(m - 1):
        ring.append((k0, k0 + t))
    for t in range(m - 1):
        ring.append((k0 + t, k1 - 1))
    for t in range(m - 1):
        ring.append((k1 - 1, k1 - 1 - t))
    for t in range(m - 1):
        ring.append((k1 - 1 - t, k0))
    ring = np.array([j * n + i for j, i in ring])
    base = len(co)
    low = co[ring].copy()
    low[:, 2] -= Hfine_edge_err + 1.0
    co = np.vstack([co, low])
    nrm = np.vstack([N.reshape(-1, 3), N.reshape(-1, 3)[ring]])
    rgb = np.vstack([Bb.reshape(-1, 3), Bb.reshape(-1, 3)[ring]])
    p, q = ring, np.roll(ring, -1)
    pl, ql = base + np.arange(len(ring)), base + np.roll(np.arange(len(ring)), -1)
    tris = np.vstack([tris, np.stack([p, ql, pl], 1), np.stack([p, q, ql], 1)])
    extra = None
    if Ab is not None:
        extra = dict(Albedo=np.vstack([Ab.reshape(-1, 3), Ab.reshape(-1, 3)[ring]]))
    return make_mesh(name, co, tris, col, mat, nrm, rgb, None, dict(outdoor="flat"), extra)


# --------------------------------------------------------------------------------- materials
HAZE = (400.0, 7000.0, 0.55)          # view distance (m) from, to, max haze
HAZE_COLOR = (0.62, 0.62, 0.66, 1.0)
def engine_material():
    """What the glTF carries: white, rough; the engine multiplies the "Bake" colour (like the
    grounds' M_Outdoor_Flat)."""
    return common.pbr_material("M_Wild_Terrain", (1, 1, 1), roughness=1.0)


def water_material():
    m = common.pbr_material("M_Wild_Water", (0.03, 0.08, 0.09), roughness=0.04)
    return m


def node(nt, kind, loc, **inputs):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def render_material(out_dir, p):
    """Cheap mask-driven terrain material for the renders: splat (slope, wetness, curvature,
    sediment) + path + rivers/lakes masks -> grass / dry / rock / scree / dirt / gravel, a
    procedural noise for breakup and distance haze. The engine version is the same recipe."""
    m = bpy.data.materials.new("M_Wild_Render")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = node(nt, "ShaderNodeOutputMaterial", (1400, 0))
    bsdf = node(nt, "ShaderNodeBsdfPrincipled", (1100, 0))
    bsdf.inputs["Roughness"].default_value = 0.95
    links = nt.links
    links.new(bsdf.outputs[0], out.inputs[0])
    uv = node(nt, "ShaderNodeUVMap", (-1200, 0))
    uv.uv_map = "UVMap"

    def tex(fname, y):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.location = (-950, y)
        t.image = bpy.data.images.load(os.path.join(out_dir, "masks", fname))
        t.image.colorspace_settings.name = "Non-Color"
        t.extension = "EXTEND"
        links.new(uv.outputs[0], t.inputs[0])
        return t
    splat = tex("splat_rgba.png", 300)
    splat.image.alpha_mode = "CHANNEL_PACKED"     # alpha = sediment, not transparency
    path = tex("path.png", 0)
    riv = tex("rivers.png", -300)
    lak = tex("lakes.png", -600)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    sep.location = (-650, 300)
    links.new(splat.outputs["Color"], sep.inputs[0])
    noise = node(nt, "ShaderNodeTexNoise", (-950, 650), Scale=0.08, Detail=6.0)
    geo_pos = nt.nodes.new("ShaderNodeNewGeometry")
    geo_pos.location = (-1200, 650)
    links.new(geo_pos.outputs["Position"], noise.inputs["Vector"])
    pal = {k: tuple(v) + (1.0,) for k, v in p["palette"].items()}

    def mix(a, b, fac, y):
        mx = nt.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.location = (y, 0)
        for sock, v in ((6, a), (7, b)):
            if isinstance(v, tuple):
                mx.inputs[sock].default_value = v
            else:
                links.new(v, mx.inputs[sock])
        links.new(fac, mx.inputs[0])
        return mx.outputs[2]

    def ramp(src, lo, hi, x, y, noise_amt=0.0):
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.location = (x, y)
        mr.interpolation_type = "SMOOTHSTEP"
        mr.inputs["From Min"].default_value = lo
        mr.inputs["From Max"].default_value = hi
        if noise_amt:
            add = nt.nodes.new("ShaderNodeMath")
            add.operation = "MULTIPLY_ADD"
            add.location = (x - 180, y)
            links.new(noise.outputs["Fac"], add.inputs[0])
            add.inputs[1].default_value = noise_amt
            links.new(src, add.inputs[2])
            add.inputs[2].default_value = 0
            links.new(add.outputs[0], mr.inputs["Value"])
            sub = nt.nodes.new("ShaderNodeMath")
            sub.operation = "SUBTRACT"
            sub.location = (x - 90, y - 120)
            links.new(add.outputs[0], sub.inputs[0])
            sub.inputs[1].default_value = noise_amt * 0.5
            links.new(sub.outputs[0], mr.inputs["Value"])
        else:
            links.new(src, mr.inputs["Value"])
        return mr.outputs["Result"]
    wet = ramp(sep.outputs[1], 0.15, 0.75, -400, 500, 0.4)
    c = mix(pal["dry"], pal["grass"], wet, -200)
    scree = ramp(splat.outputs["Alpha"], 0.15, 0.6, -400, 200)
    c = mix(c, pal["scree"], scree, 0)
    rock = ramp(sep.outputs[0], 36 / 90, 48 / 90, -400, -100, 0.12)
    c = mix(c, pal["rock"], rock, 200)
    water = nt.nodes.new("ShaderNodeMath")
    water.operation = "MAXIMUM"
    water.location = (-650, -450)
    links.new(riv.outputs["Color"], water.inputs[0])
    links.new(lak.outputs["Color"], water.inputs[1])
    c = mix(c, pal["mud"], water.outputs[0], 400)
    pth = ramp(path.outputs["Color"], 0.05, 0.02, -400, -300)
    c = mix(c, pal["dirt"], pth, 600)
    # distance haze (aerial perspective) - cheap, also what the engine's fog does
    cam = nt.nodes.new("ShaderNodeCameraData")
    cam.location = (500, -400)
    hz = nt.nodes.new("ShaderNodeMapRange")
    hz.location = (700, -400)
    hz.inputs["From Min"].default_value = HAZE[0]
    hz.inputs["From Max"].default_value = HAZE[1]
    hz.inputs["To Max"].default_value = HAZE[2]
    links.new(cam.outputs["View Distance"], hz.inputs["Value"])
    c = mix(c, HAZE_COLOR, hz.outputs["Result"], 850)
    links.new(c, bsdf.inputs["Base Color"])
    return m


def vertex_color_material():
    """The engine look: unlit, colour = the "Bake" vertex colour (MeshBasicMaterial)."""
    m = bpy.data.materials.new("M_Wild_EngineLook")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = node(nt, "ShaderNodeOutputMaterial", (400, 0))
    em = node(nt, "ShaderNodeEmission", (200, 0))
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Bake"
    nt.links.new(attr.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


# --------------------------------------------------------------------------------- render
def setup_render(p, res, samples):
    scene = bpy.context.scene
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    w, h = (int(v) for v in res.split("x"))
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    try:
        scene.eevee.taa_render_samples = samples
    except AttributeError:
        pass
    world = bpy.data.worlds.new("W_Wild")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = tuple(p["look"]["sky"]) + (1,)
    bg.inputs["Strength"].default_value = p["look"]["sky_strength"]
    scene.world = world
    sd = np.asarray(p["look"]["sun_dir"], float)
    sd = sd / np.linalg.norm(sd)
    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = p["look"]["sun_strength"]
    sun_data.color = p["look"]["sun_color"]
    sun_data.angle = math.radians(1.0)
    sun = bpy.data.objects.new("Sun", sun_data)
    scene.collection.objects.link(sun)
    # point the light's -Z along sun_dir
    from mathutils import Vector
    sun.rotation_euler = Vector(sd).to_track_quat("-Z", "Y").to_euler()
    scene.view_settings.exposure = -0.9
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    return scene


def camera(name, loc, target, lens):
    from mathutils import Vector
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_start, cd.clip_end = 0.5, 12000
    cam = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam


# --------------------------------------------------------------------------------- main
def main():
    a = args()
    slots.acquire("level", 2)
    T0 = time.perf_counter()
    times = {}
    out_dir = os.path.join(terrain.OUT_ROOT, a.name)
    stats = json.load(open(os.path.join(out_dir, "stats.json")))
    p = terrain.merged(terrain.P, dict(name=a.name, cell=stats["cell_m"], size=stats["size_m"]))
    p["look"], p["chunks"], p["lods"] = stats["look"], stats["chunks"], stats["lods"]
    data = np.load(os.path.join(out_dir, "terrain.npz"))
    H = data["H"].astype(np.float64)
    B = data["bake"].astype(np.float32) / 65535
    g = stats["grid"]
    x0, y0, cell, n = g["x0"], g["y0"], g["cell"], g["nx"]
    extent = (n - 1) * cell
    N, _, _ = terrain.normals(H, cell)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    col = bpy.data.collections.new("Wild")
    bpy.context.scene.collection.children.link(col)
    mat = engine_material()
    C = p["chunks"]
    size = (n - 1) // C
    manifest = dict(name=a.name, chunks=C, chunk_size_m=size * cell, cell_m=cell, origin=[x0, y0],
                    lods=[], files={}, coords="Blender z-up metres; glTF/three.js: x = x, y = z, z = -y")
    t = time.perf_counter()
    roots = {}
    for li, step in enumerate(p["lods"]):
        root = bpy.data.objects.new(f"Wild_Terrain_L{li}", None)
        col.objects.link(root)
        roots[li] = root
        tri_surface, tri_total, skirts = 0, 0, []
        for cy in range(C):
            for cx in range(C):
                j0, i0 = cy * size, cx * size
                err = border_error(H, j0, i0, size, step)
                skirt = round(err + 0.5, 2)
                skirts.append(skirt)
                ob = chunk_mesh(f"Wild_Terrain_{cx}_{cy}_L{li}", H, N, B, x0, y0, cell, j0, i0, size, step,
                                skirt, col, mat, extent)
                ob.parent = root
                ob["chunk"] = [cx, cy]
                ob["lod"] = li
                ob["step_m"] = step * cell
                ob["outdoor"] = "flat"
                ntri = len(ob.data.polygons)
                tri_total += ntri
                tri_surface += 2 * (size // step) ** 2
        manifest["lods"].append(dict(lod=li, step_cells=step, step_m=step * cell,
                                     tris_per_chunk=2 * (size // step) ** 2,
                                     tris_surface=tri_surface, tris_with_skirts=tri_total,
                                     skirt_m_max=max(skirts), skirt_m_mean=round(float(np.mean(skirts)), 2)))
        print(f"LOD{li}: step {step * cell} m, {tri_surface} tris (+skirts {tri_total - tri_surface})", flush=True)
    times["chunks"] = round(time.perf_counter() - t, 1)
    t = time.perf_counter()
    wmat = water_material()
    wroot = bpy.data.objects.new("Wild_Water", None)
    col.objects.link(wroot)
    lake = water_mesh("Wild_Water_Lakes", data["lake_level"].astype(np.float64), x0, y0, cell, 2, col, wmat)
    river = water_mesh("Wild_Water_Rivers", data["river_level"].astype(np.float64), x0, y0, cell, 1, col, wmat)
    lake.parent = river.parent = wroot
    bd = stats["backdrop"]
    Hb = data["Hb"].astype(np.float64)
    Bb = data["bake_b"].astype(np.float32) / 65535
    gb = dict(x0=-bd["extent"] / 2, y0=-bd["extent"] / 2, cell=bd["cell"])
    st = int(round(bd["cell"] / cell))
    edge_err = max(border_error(H, 0, 0, n - 1, st), 0.5)
    broot = bpy.data.objects.new("Wild_Backdrop", None)
    col.objects.link(broot)
    Ab = data["albedo_b"].astype(np.float32) / 65535 if "albedo_b" in data else None
    back = backdrop_mesh("Wild_Backdrop_Ring", Hb, Bb, gb, bd["inner"], edge_err, col, mat)
    back.parent = broot
    times["water_backdrop"] = round(time.perf_counter() - t, 1)
    manifest["water"] = dict(lakes_tris=len(lake.data.polygons), rivers_tris=len(river.data.polygons))
    manifest["backdrop"] = dict(tris=len(back.data.polygons), cell_m=bd["cell"], extent_m=bd["extent"])

    # ------------------------------------------------------------------ export + check
    if not a.no_export:
        t = time.perf_counter()
        mdir = os.path.join(out_dir, "models")
        os.makedirs(mdir, exist_ok=True)
        opts = dict(export_vertex_color_name="Bake", export_draco_color_quantization=10)
        targets = [(roots[li], f"terrain_L{li}.gltf") for li in roots] + [(wroot, "water.gltf"), (broot, "backdrop.gltf")]
        # lean variant (measurement): no normals / UVs; an unlit engine derives both from position
        lean = dict(opts, export_normals=False, export_texcoords=False)
        targets += [(roots[li], f"lean/terrain_L{li}_lean.gltf") for li in roots]
        os.makedirs(os.path.join(mdir, "lean"), exist_ok=True)
        for root, fname in targets:
            path = os.path.join(mdir, fname)
            common.export_gltf(root, path, **(lean if "lean" in fname else opts))
            binf = path[:-5] + ".bin"
            manifest["files"][fname] = dict(gltf=os.path.getsize(path),
                                            bin=os.path.getsize(binf) if os.path.exists(binf) else 0)
            print(f"export {fname}: {sum(manifest['files'][fname].values()) / 1e6:.2f} MB", flush=True)
        times["export"] = round(time.perf_counter() - t, 1)
        t = time.perf_counter()
        manifest["check"] = import_check(os.path.join(mdir, "terrain_L0.gltf"), H, stats, out_dir)
        times["import_check"] = round(time.perf_counter() - t, 1)
        print("check", manifest["check"], flush=True)

    # ------------------------------------------------------------------ renders
    if not a.no_render:
        t = time.perf_counter()
        scene = setup_render(p, a.res, a.samples)
        rmat = render_material(out_dir, p)
        for li, root in roots.items():
            for ch in root.children:
                ch.hide_render = li != 0
                if li == 0:
                    ch.data.materials[0] = rmat
        if Ab is not None:     # render-only albedo, added after the export (it would be COLOR_1)
            n_b = Ab.shape[0]
            ring_n = len(back.data.vertices) - n_b * n_b
            at = back.data.color_attributes.new("Albedo", "FLOAT_COLOR", "POINT")
            flat = Ab.reshape(-1, 3)
            ring_src = np.array([v.co for v in back.data.vertices][n_b * n_b:]) if ring_n else np.zeros((0, 3))
            ii = np.clip(np.round((ring_src[:, 0] - gb["x0"]) / gb["cell"]).astype(int), 0, n_b - 1)
            jj = np.clip(np.round((ring_src[:, 1] - gb["y0"]) / gb["cell"]).astype(int), 0, n_b - 1)
            allc = np.vstack([flat, flat[jj * n_b + ii]])
            at.data.foreach_set("color", np.concatenate([allc, np.ones((len(allc), 1))], 1).astype(np.float32).ravel())
        back.data.materials[0] = rmat_back(p)
        zc = lambda x, y: float(terrain.height_at(H, terrain.Grid(x0, y0, cell, n, n), x, y))
        shots = [
            ("aerial", (-1350, -1550, 950), (40, 40, 60), 32),
            ("gate", (20, -790, zc(20, -748) + 22), (-40, 150, zc(-40, 150) + 30), 26),
            ("camp", (70, 150, zc(70, 150) + 2.0), (-215, -110, zc(-215, -110) - 2), 24),
            ("mesa", (60, -430, zc(60, -430) + 6), (230, -380, zc(230, -380) + 12), 30),
            ("ford", (-35, -650, zc(-35, -650) + 4), (-80, -585, zc(-80, -585)), 30),
        ]
        for nm, loc, tgt, lens in shots:
            scene.camera = camera(f"Cam_{nm}", loc, tgt, lens)
            scene.render.filepath = os.path.join(out_dir, f"render_{nm}.png")
            bpy.ops.render.render(write_still=True)
            print("render", nm, flush=True)
        # engine look: unlit vertex colours (what three.js MeshBasicMaterial draws)
        vmat = vertex_color_material()
        for ch in roots[0].children:
            ch.data.materials[0] = vmat
        back.data.materials[0] = vmat
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.exposure = 0
        scene.camera = bpy.data.objects["Cam_aerial"]
        scene.render.filepath = os.path.join(out_dir, "render_aerial_engine.png")
        bpy.ops.render.render(write_still=True)
        times["render"] = round(time.perf_counter() - t, 1)
    times["total"] = round(time.perf_counter() - T0, 1)
    manifest["timings_s"] = times
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    print(json.dumps(manifest["lods"], indent=0))
    print("times", times)


def rmat_back(p):
    """Backdrop in the renders: its "Albedo" attribute, lit by the same sun, + the same haze."""
    m = bpy.data.materials.new("M_Wild_BackdropRender")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 1.0
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Albedo"
    cam = nt.nodes.new("ShaderNodeCameraData")
    hz = nt.nodes.new("ShaderNodeMapRange")
    hz.inputs["From Min"].default_value = HAZE[0]
    hz.inputs["From Max"].default_value = HAZE[1]
    hz.inputs["To Max"].default_value = HAZE[2]
    nt.links.new(cam.outputs["View Distance"], hz.inputs["Value"])
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    nt.links.new(attr.outputs["Color"], mx.inputs[6])
    mx.inputs[7].default_value = HAZE_COLOR
    nt.links.new(hz.outputs["Result"], mx.inputs[0])
    nt.links.new(mx.outputs[2], bsdf.inputs["Base Color"])
    return m


def import_check(path, H, stats, out_dir):
    """Re-import LOD0 and compare its surface with terrain.height_at (= the collider) at random
    points, and the 16-bit collider file with the float heights."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    g = stats["grid"]
    grid = terrain.Grid(g["x0"], g["y0"], g["cell"], g["nx"], g["ny"])
    rng = np.random.default_rng(1)
    pts = rng.uniform(g["x0"] + 1, g["x0"] + (g["nx"] - 1) * g["cell"] - 1, (3000, 2))
    dg = bpy.context.evaluated_depsgraph_get()
    trees = []
    for o in new:
        bm_tree = BVHTree.FromObject(o, dg)
        mw = o.matrix_world
        trees.append((bm_tree, mw, mw.inverted()))
    errs = []
    for x, y in pts:
        hit = None
        for tree, mw, inv in trees:
            org = inv @ Vector((x, y, 2000.0))
            dirn = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
            loc, _, _, _ = tree.ray_cast(org, dirn)
            if loc is not None:
                z = (mw @ loc).z
                hit = z if hit is None else max(hit, z)
        if hit is not None:
            errs.append(hit - float(terrain.height_at(H, grid, x, y)))
    errs = np.abs(np.array(errs))
    me = new[0].data
    colnames = [a.name for a in me.color_attributes]
    q = np.frombuffer(open(os.path.join(out_dir, "collider_u16.bin"), "rb").read(), "<u2").reshape(g["ny"], g["nx"])
    c = stats["collider"]
    Hc = q[::-1].astype(np.float64) * c["scale"] + c["height_min"]
    res = dict(objects=len(new), hits=int(len(errs)), mesh_vs_collider_max_m=round(float(errs.max()), 4),
               mesh_vs_collider_mean_m=round(float(errs.mean()), 4), color_attributes=colnames,
               collider_quantisation_max_m=round(float(np.abs(Hc - H).max()), 4),
               verts_first_chunk=len(me.vertices))
    for o in new:
        bpy.data.objects.remove(o)
    return res


if __name__ == "__main__":
    main()
