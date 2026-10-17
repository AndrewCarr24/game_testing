"""Build one asset headless, export it, and render a preview sheet.

  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
      --python blender/tools/build_asset.py -- <asset> [--no-export] [--size 512] [--set key=value ...]

Each call is its own Blender process with an empty scene, so several can run in
parallel without touching each other or the Blender window you have open.

Writes
  assets/models/<asset>.gltf (+ .bin, shared textures/)   unless --no-export
  build/previews/<asset>.png   2x2 sheet: front, three-quarter, side, top
and prints a report (size, triangles, grounding, materials, textures,
interactables) with WARN lines for anything outside the project's budget.
"""
import argparse
import importlib
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
sys.path.insert(0, os.path.join(BLENDER_DIR, "assets"))

MAX_TRIS = 15000          # per prop; hero pieces may justify more, say so in the spec
MAX_TEXTURE = 1024


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("asset")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--size", type=int, default=512, help="pixels per preview tile")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override a build() parameter, e.g. --set variant=geometric_a (repeatable)")
    return ap.parse_args(argv)


def overrides(pairs):
    out = {}
    for pair in pairs:
        k, v = pair.split("=", 1)
        for cast in (int, float):
            try:
                v = cast(v)
                break
            except ValueError:
                pass
        out[k] = v
    return out


def report(root, parts, common):
    lo, hi = common.world_aabb(parts)
    size = hi - lo
    tris = common.triangle_count(parts)
    warns = []
    print(f"REPORT {root.name}")
    print(f"  size      {size.x:.3f} x {size.y:.3f} x {size.z:.3f} m (x, y, z)")
    print(f"  bottom    z = {lo.z:.4f} m" + ("" if abs(lo.z) < 0.002 else "   <- not on the ground"))
    if abs(lo.z) >= 0.002 and root.parent is None:
        warns.append(f"lowest point is z={lo.z:.4f}; props should sit on z=0")
    print(f"  meshes    {len(parts)}   triangles {tris}")
    if tris > MAX_TRIS:
        warns.append(f"{tris} triangles > {MAX_TRIS} budget")
    mats = sorted({m.name for o in parts for m in o.data.materials if m})
    print(f"  materials {', '.join(mats)}")
    images = {}
    for m in {m for o in parts for m in o.data.materials if m}:
        for nd in m.node_tree.nodes:
            if nd.type == "TEX_IMAGE" and nd.image:
                images[nd.image.name] = tuple(nd.image.size)
    for name, (w, h) in sorted(images.items()):
        print(f"  texture   {name} {w}x{h}")
        if max(w, h) > MAX_TEXTURE:
            warns.append(f"texture {name} is {w}x{h}; default max is {MAX_TEXTURE}")
    for ob in [root] + list(root.children_recursive):
        if "interact" in ob.keys():
            print(f"  interact  {ob.name}: {dict(ob['interact'])}")
    for o in parts:
        textured = any(nd.type == "TEX_IMAGE" for m in o.data.materials if m for nd in m.node_tree.nodes)
        if textured and not o.data.uv_layers:
            warns.append(f"{o.name} uses an image texture but has no UV map (use common.box_uv)")
    for w in warns:
        print(f"WARN {w}")
    return lo, hi


def preview(lo, hi, path, tile):
    scene = bpy.context.scene
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x = scene.render.resolution_y = tile
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"

    world = scene.world or bpy.data.worlds.new("PreviewWorld")
    scene.world = world
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.42, 0.44, 0.47, 1)
    bg.inputs["Strength"].default_value = 1.0

    centre = (lo + hi) / 2
    extent = max((hi - lo).length, 0.05)
    sun = bpy.data.objects.new("PreviewSun", bpy.data.lights.new("PreviewSun", "SUN"))
    sun.data.energy = 3.0
    sun.data.angle = 0.2
    sun.rotation_euler = Vector((-0.5, 0.6, -0.8)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(sun)
    floor_me = bpy.data.meshes.new("PreviewFloor")
    s = extent * 4
    floor_me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    floor = bpy.data.objects.new("PreviewFloor", floor_me)
    floor.location = (centre.x, centre.y, lo.z)
    fm = bpy.data.materials.new("PreviewFloor")
    try:
        fm.use_nodes = True
    except AttributeError:
        pass
    next(n for n in fm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1)
    floor_me.materials.append(fm)
    scene.collection.objects.link(floor)

    cam = bpy.data.objects.new("PreviewCam", bpy.data.cameras.new("PreviewCam"))
    cam.data.lens = 50
    cam.data.clip_start = extent * 0.01
    cam.data.clip_end = extent * 50
    scene.collection.objects.link(cam)
    scene.camera = cam
    dist = extent * 1.45
    views = [("front", (0, -1, 0.25)), ("three_quarter", (0.9, -1, 0.65)),
             ("side", (1, 0, 0.25)), ("top", (0.001, -0.25, 1))]
    tiles = []
    tmp = path + ".tile.png"
    for name, d in views:
        cam.location = centre + Vector(d).normalized() * dist
        cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(tmp)
        tiles.append(np.array(img.pixels[:], dtype=np.float32).reshape(tile, tile, 4))
        bpy.data.images.remove(img)
    os.remove(tmp)
    # Blender rows are bottom-up: bottom row of the sheet = side, top; top row = front, three-quarter
    sheet = np.vstack([np.hstack([tiles[2], tiles[3]]), np.hstack([tiles[0], tiles[1]])])
    out = bpy.data.images.new("PreviewSheet", tile * 2, tile * 2, alpha=False)
    out.pixels.foreach_set(sheet.ravel())
    out.filepath_raw = path
    out.file_format = "PNG"
    out.save()
    print(f"PREVIEW {path}  (top-left front, top-right three-quarter, bottom-left side, bottom-right top)")


def main():
    a = args()
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    from lib import common
    mod = importlib.import_module(a.asset)
    kw = overrides(a.set)
    root, parts = mod.build(**kw)
    lo, hi = report(root, parts, common)
    if not a.no_export:
        out = os.path.join(PROJECT, "assets", "models", f"{a.asset}.gltf")
        common.export_gltf(root, out)
        print(f"EXPORT {out}")
    prev_dir = os.path.join(PROJECT, "build", "previews")
    os.makedirs(prev_dir, exist_ok=True)
    tag = "".join(f"_{v}" for v in kw.values())
    preview(lo, hi, os.path.join(prev_dir, f"{a.asset}{tag}.png"), a.size)
    print(f"DONE {a.asset} in {time.time() - t0:.1f}s")


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    print("FAILED")
    sys.exit(1)
