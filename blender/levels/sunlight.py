"""Which rooms direct sunlight can reach (through windows, openings, the courtyard).

Rays from a grid of points in each room toward the sun, against the house shell (glass
doesn't block). A room no ray escapes from never gets direct sun, so in the engine its
props neither cast nor receive real-time sun shadows and skip direct sunlight entirely
(their light is the room's baked SH): less shadow-map work and cheaper shading, with
nothing visible lost. Called by mansion.build (written to mansion.json rooms[r]["sun"]);
or headless on a saved level:
  Blender -b blender/levels/mansion.blend --python blender/levels/sunlight.py
which patches assets/levels/mansion.json in place.
"""
import json
import os
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))


def shell_tree(shell_objects):
    bm = bmesh.new()
    for ob in shell_objects:
        if ob.type != "MESH" or not ob.data.polygons:
            continue
        if any(m is not None and m.name.startswith("M_Glass") for m in ob.data.materials):
            continue
        me = ob.data.copy()
        me.transform(ob.matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    return BVHTree.FromBMesh(bm)


def sunlit_rooms(rooms, shell_objects, sun_dir, n=10):
    """rooms: name -> ((x0, y0, x1, y1), z0, z1) interior in Blender metres.
    sun_dir: the direction sunlight travels (Blender axes)."""
    tree = shell_tree(shell_objects)
    to_sun = -Vector(sun_dir).normalized()
    out = {}
    for room, ((x0, y0, x1, y1), z0, z1) in rooms.items():
        lit = False
        for i in range(n):
            for j in range(n):
                for zf in (0.02, 0.35, 0.7):
                    p = Vector((x0 + (x1 - x0) * (i + 0.5) / n, y0 + (y1 - y0) * (j + 0.5) / n, z0 + (z1 - z0) * zf))
                    if tree.ray_cast(p + to_sun * 0.01, to_sun, 1000)[0] is None:
                        lit = True
                        break
                if lit:
                    break
            if lit:
                break
        out[room] = lit
    return out


def main():
    """Patch mansion.json from the saved level (no rebuild)."""
    sys.path.insert(0, HERE)
    sys.path.insert(0, os.path.join(HERE, ".."))
    import plan
    path = os.path.join(PROJECT, "assets", "levels", "mansion.json")
    with open(path) as f:
        level = json.load(f)
    shell = list(bpy.data.collections["Mansion_Shell"].all_objects)
    sun = next(l for l in level["lights"] if l["type"] == "sun")["direction"]
    sun_b = (sun[0], -sun[2], sun[1])                          # glTF -> Blender
    rooms = {}
    for r, info in level["rooms"].items():
        x0, z0, x1, z1 = info["rect"]
        T = plan.T
        rooms[r] = ((x0 + T, -z1 + T, x1 - T, -z0 - T), info["floor"], info["floor"] + info["height"])
    lit = sunlit_rooms(rooms, shell, sun_b)
    for r, v in lit.items():
        level["rooms"][r]["sun"] = v
    with open(path, "w") as f:
        json.dump(level, f, indent=2)
    print("SUNLIT", sorted(r for r, v in lit.items() if v))
    print("NO SUN", sorted(r for r, v in lit.items() if not v))


if __name__ == "__main__":
    main()
