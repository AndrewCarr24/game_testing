"""Build the mansion headless, save blender/levels/mansion.blend, and optionally
render previews. Never touches the Blender window you have open.

  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \\
      --python blender/tools/build_level.py -- [--plan] [--room ROOM ...] [--no-export] [--size 900]

  --plan          top-down floor plans of both levels -> build/previews/plan_ground.png, plan_upper.png
  --room ROOM     interior views of ROOM from its four corners at eye height, lit by its
                  lights (EEVEE) -> build/previews/room_<ROOM>.png (2x2 sheet); repeatable
  --only-room R   dress only these rooms (faster previews while iterating one room)
  --zone ZONE     outdoor zone preview (dresses only that zone, no room furniture):
                  build/previews/zone_<ZONE>.png = overview, the view from the house's
                  nearest window, and two eye-level views from the zone's corners
"""
import argparse
import math
import os
import runpy
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
LEVELS = os.path.join(PROJECT, "blender", "levels")
PREV = os.path.join(PROJECT, "build", "previews")


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--room", action="append", default=[])
    ap.add_argument("--only-room", action="append", default=[])
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--zone", action="append", default=[])
    ap.add_argument("--size", type=int, default=900)
    return ap.parse_args(argv)


def engine(scene):
    for e in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH"):
        try:
            scene.render.engine = e
            return
        except TypeError:
            continue


def render_to(path, w, h):
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def sheet(paths, out, tile):
    tiles = []
    for p in paths:
        img = bpy.data.images.load(p)
        tiles.append(np.array(img.pixels[:], dtype=np.float32).reshape(tile[1], tile[0], 4))
        bpy.data.images.remove(img)
        os.remove(p)
    grid = np.vstack([np.hstack(tiles[2:4]), np.hstack(tiles[0:2])])   # rows are bottom-up
    im = bpy.data.images.new("Sheet", tile[0] * 2, tile[1] * 2, alpha=False)
    im.pixels.foreach_set(grid.ravel())
    im.filepath_raw = out
    im.file_format = "PNG"
    im.save()


def plan_views(size):
    """Orthographic top views per level; everything above the level's walls is hidden."""
    import plan
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    cam = bpy.data.objects.new("PlanCam", bpy.data.cameras.new("PlanCam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 56
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.rotation_euler = (0, 0, 0)
    for lvl, name, cut in ((0, "ground", 4.15), (1, "upper", 8.35)):
        cam.location = (0, 0, 40)
        cam.data.clip_start, cam.data.clip_end = 0.1, 100
        for ob in bpy.data.objects:
            if ob.type == "MESH":
                top = max((ob.matrix_world @ Vector(c)).z for c in ob.bound_box)
                low = min((ob.matrix_world @ Vector(c)).z for c in ob.bound_box)
                ob.hide_render = low >= cut - 0.06          # ceilings and everything above this level
        render_to(os.path.join(PREV, f"plan_{name}.png"), size, int(size * 40 / 52))
        print(f"PREVIEW {os.path.join(PREV, f'plan_{name}.png')}")
    for ob in bpy.data.objects:
        ob.hide_render = False
    bpy.data.objects.remove(cam)


def room_views(room, size, h):
    """Four eye-height views from just inside the room's corners, looking across it."""
    scene = bpy.context.scene
    engine(scene)
    (x0, y0, x1, y1), z0, z1 = h.interior(room)
    cam = bpy.data.objects.new("RoomCam", bpy.data.cameras.new("RoomCam"))
    cam.data.lens = 16
    cam.data.clip_start = 0.05
    scene.collection.objects.link(cam)
    scene.camera = cam
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # only this room (plus a margin) renders: other rooms' lights overflow EEVEE's shadow budget
    m = 2.5
    for ob in bpy.data.objects:
        if ob.type not in ("MESH", "LIGHT"):
            continue
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box] if ob.type == "MESH" else [ob.matrix_world.translation]
        inside = (min(v.x for v in bb) < x1 + m and max(v.x for v in bb) > x0 - m and
                  min(v.y for v in bb) < y1 + m and max(v.y for v in bb) > y0 - m and
                  min(v.z for v in bb) < z1 + 0.5 and max(v.z for v in bb) > z0 - 0.5)
        ob.hide_render = not inside and ob.data.type != "SUN" if ob.type == "LIGHT" else not inside
    paths = []
    inset = 0.6
    # furniture boxes (not the shell): a corner camera that starts inside one walks toward the centre
    boxes = []
    for ob in bpy.data.objects:
        if ob.type != "MESH" or any(c.name.endswith("_Shell") for c in ob.users_collection):
            continue
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        boxes.append((min(v.x for v in bb), max(v.x for v in bb), min(v.y for v in bb), max(v.y for v in bb),
                      min(v.z for v in bb), max(v.z for v in bb)))

    def clear(x, y, z, r=0.35):
        return not any(b[0] - r < x < b[1] + r and b[2] - r < y < b[3] + r and b[4] < z < b[5] for b in boxes)

    for i, (px, py) in enumerate(((x0 + inset, y0 + inset), (x1 - inset, y0 + inset),
                                  (x0 + inset, y1 - inset), (x1 - inset, y1 - inset))):
        for k in range(20):
            f = k / 20
            qx, qy = px + (cx - px) * f, py + (cy - py) * f
            if clear(qx, qy, z0 + 1.65):
                px, py = qx, qy
                break
        cam.location = (px, py, z0 + 1.65)
        target = Vector((cx, cy, z0 + 1.0))
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        p = os.path.join(PREV, f"_room_{room}_{i}.png")
        render_to(p, size, int(size * 0.62))
        paths.append(p)
    out = os.path.join(PREV, f"room_{room}.png")
    sheet(paths, out, (size, int(size * 0.62)))
    bpy.data.objects.remove(cam)
    for ob in bpy.data.objects:
        ob.hide_render = False
    print(f"PREVIEW {out}  (corners: top-left SW, top-right SE, bottom-left NW, bottom-right NE)")


def zone_views(zone, size):
    """Overview from above, the view from the house's nearest window, two eye-level views."""
    import plan
    scene = bpy.context.scene
    engine(scene)
    x0, y0, x1, y1 = plan.GROUNDS["zones"][zone]["rect"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    z = plan.LAWN_Z
    cam = bpy.data.objects.new("ZoneCam", bpy.data.cameras.new("ZoneCam"))
    cam.data.clip_start, cam.data.clip_end = 0.05, 2000
    scene.collection.objects.link(cam)
    scene.camera = cam
    # the house's nearest facade point (just inside the glass), upper floor if the zone is big
    hx = max(-25.6, min(25.6, cx))
    hy = max(-19.6, min(19.6, cy))
    if abs(cx) > 26 and abs(cy) < 20:
        hx, hy = math.copysign(24.6, cx), hy + 0.75      # 1.4 m inside, between mullions
    elif abs(cy) > 20:
        hx, hy = hx + 0.75, math.copysign(18.6, cy)
    span = max(x1 - x0, y1 - y0)
    views = [
        ((cx - span * 0.55, cy - span * 0.75, z + span * 0.7), 24),       # overview from the south-west, above
        ((hx, hy, 6.25), 16),                                             # from the upper floor window
        ((x0 + 1.0, y0 + 1.0, z + 1.7), 18),                              # eye level, two corners
        ((x1 - 1.0, y1 - 1.0, z + 1.7), 18),
    ]
    paths = []
    for i, (loc, lens) in enumerate(views):
        cam.location = loc
        cam.data.lens = lens
        target = Vector((cx, cy, z + (0.5 if i else 0.0)))
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        p = os.path.join(PREV, f"_zone_{zone}_{i}.png")
        render_to(p, size, int(size * 0.62))
        paths.append(p)
    out = os.path.join(PREV, f"zone_{zone}.png")
    sheet(paths, out, (size, int(size * 0.62)))
    bpy.data.objects.remove(cam)
    print(f"PREVIEW {out}  (top-left overview, top-right from the house window, bottom: eye level from two corners)")


def main():
    a = args()
    t0 = time.time()
    os.makedirs(PREV, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ns = runpy.run_path(os.path.join(LEVELS, "mansion.py"))
    level, h = ns["build"](export=not a.no_export,
                           rooms_only=a.only_room or (["-"] if a.zone else None),
                           write_json=not a.no_export, zones_only=a.zone or None)
    if not a.no_save:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(LEVELS, "mansion.blend"))
    if not a.no_export:
        runpy.run_path(os.path.join(HERE, "optimize_textures.py"))
    if a.plan:
        plan_views(a.size)
    for room in a.room:
        room_views(room, a.size, h)
    for zone in a.zone:
        zone_views(zone, a.size)
    print(f"DONE in {time.time() - t0:.1f}s")


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    print("FAILED")
    sys.exit(1)
