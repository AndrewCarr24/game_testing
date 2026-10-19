"""Which rooms can see into which (a potentially-visible set, PVS): from a grid of eye-height
points in room A, is any point of room B reachable in a straight line past the house shell
(doorways, openings, interior glass and the courtyard count as open)? The engine's furniture
culler shows a room's furniture far away only when the player's room can see it (and it's in
view); without this, a flat distance rule either drew rooms behind walls or let rooms seen
through a doorway pop in late. Called by mansion.build (mansion.json rooms[r]["sees"]); or
headless on a saved level, patching mansion.json in place:
  Blender -b blender/levels/mansion.blend --python blender/levels/visibility.py
"""
import json
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import sunlight  # noqa: E402  (shell BVH without glass)


def _grid(rect, z, n):
    x0, y0, x1, y1 = rect
    return [Vector((x0 + (x1 - x0) * (i + 0.5) / n, y0 + (y1 - y0) * (j + 0.5) / n, z))
            for i in range(n) for j in range(n)]


def blockers(plan, doors=True):
    """Solid quads for exterior glazing (you see out of a window, but a sight line that leaves
    the house mustn't count as reaching another room through its window across the lawn) and
    for doorways with doors. Interior glass (courtyard, into the great room) and open
    doorways stay see-through."""
    import bmesh
    bm = bmesh.new()
    xs, ys = (-26, 26), (-20, 20)
    for c in plan.CUTS:
        L, (a0, a1), (z0, z1) = c["line"], c["span"], c["z"]
        facade = (c["axis"] == "x" and any(abs(L - y) < 1e-6 for y in ys)) or \
                 (c["axis"] == "y" and any(abs(L - x) < 1e-6 for x in xs))
        door = doors and c["kind"] == "opening" and c.get("door")
        # doors count as closed (that's how they start; a room behind a door you've opened is
        # normally within the culler's close range anyway)
        if not ((c["kind"] == "window" and facade) or door):
            continue
        if c["axis"] == "x":
            q = [(a0, L, z0), (a1, L, z0), (a1, L, z1), (a0, L, z1)]
        else:
            q = [(L, a0, z0), (L, a1, z0), (L, a1, z1), (L, a0, z1)]
        bm.faces.new([bm.verts.new(v) for v in q])
    return bm


def room_visibility(rooms, shell_objects, plan=None, n_from=5, n_to=4, doors_closed=True):
    """rooms: name -> ((x0, y0, x1, y1), z0, z1) interior, Blender metres.
    Returns name -> sorted list of rooms it can see (itself included)."""
    from mathutils.bvhtree import BVHTree
    tree = sunlight.shell_tree(shell_objects)
    outside = BVHTree.FromBMesh(blockers(plan, doors=doors_closed)) if plan else None
    eyes = {r: _grid(rect, z0 + 1.65 if z1 - z0 > 1.8 else (z0 + z1) / 2, n_from) for r, (rect, z0, z1) in rooms.items()}
    targets = {r: _grid(rect, z0 + 1.0, n_to) + _grid(rect, min(z0 + 2.2, z1 - 0.3), 2)
               for r, (rect, z0, z1) in rooms.items()}
    sees = {r: {r} for r in rooms}
    names = sorted(rooms)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if b in sees[a]:
                continue
            visible = False
            for e in eyes[a]:
                for t in targets[b]:
                    d = t - e
                    dist = d.length
                    if tree.ray_cast(e, d.normalized(), dist - 0.05)[0] is None and \
                            (outside is None or outside.ray_cast(e, d.normalized(), dist - 0.05)[0] is None):
                        visible = True
                        break
                if visible:
                    break
            if visible:
                sees[a].add(b)
                sees[b].add(a)
    return {r: sorted(v) for r, v in sees.items()}


def main():
    sys.path.insert(0, os.path.join(HERE, ".."))
    import plan
    path = os.path.join(PROJECT, "assets", "levels", "mansion.json")
    with open(path) as f:
        level = json.load(f)
    shell = list(bpy.data.collections["Mansion_Shell"].all_objects)
    rooms = {}
    for r, info in level["rooms"].items():
        x0, z0, x1, z1 = info["rect"]
        T = plan.T
        rooms[r] = ((x0 + T, -z1 + T, x1 - T, -z0 - T), info["floor"], info["floor"] + info["height"])
    sees = room_visibility(rooms, shell, plan)
    sees_open = room_visibility(rooms, shell, plan, doors_closed=False)
    for r in sees:
        level["rooms"][r]["sees"] = sees[r]
        level["rooms"][r]["seesOpen"] = sees_open[r]
    with open(path, "w") as f:
        json.dump(level, f, indent=2)
    for r in ("dining", "entry", "office"):
        print("SEES", r, sees[r])
        print("OPEN", r, sees_open[r])


if __name__ == "__main__":
    main()
