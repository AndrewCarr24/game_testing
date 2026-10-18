"""Focal sculpture at the west end of the garden: a tall bronze ribbon, twisted through 270
degrees and tapering as it climbs, with a shorter counter-twisted companion, on a honed
limestone plinth. About 5.3 m overall. Garden frame (see garden_common): placed on the pool
axis, seen from the east (the house)."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garden_common as gc  # noqa: E402

importlib.reload(gc)
common, outdoor = gc.common, gc.outdoor

NAME = "GardenSculpture"

P = dict(
    name=NAME,
    x=-15.9,             # on the pool axis, in the end court
    plinth=2.6,
    plinth_h=0.38,
    height=4.9,          # ribbon height above the plinth
    segments=30,
)


def ribbon(bm, base, height, w0, w1, thick, twist, lean, sway, phase, segments, bend=0.0):
    """Twisted tapering ribbon; centre line leans and sways gently."""
    rings = []
    for i in range(segments + 1):
        t = i / segments
        z = base.z + height * t
        # centre line: slight lean plus an S-curve, zero offset at the foot
        cx = base.x + lean * t * t + sway * math.sin(2 * math.pi * t + phase) * t
        cy = base.y + bend * math.sin(math.pi * t)
        a = (w0 + (w1 - w0) * t) / 2
        th = twist * (t ** 1.15) + phase
        d = Vector((math.cos(th), math.sin(th), 0))
        n = Vector((-math.sin(th), math.cos(th), 0)) * (thick / 2)
        c = Vector((cx, cy, z))
        rings.append([bm.verts.new(c + d * a + n), bm.verts.new(c - d * a + n),
                      bm.verts.new(c - d * a - n), bm.verts.new(c + d * a - n)])
    for i in range(segments):
        for k in range(4):
            j = (k + 1) % 4
            bm.faces.new((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]))
    bm.faces.new(rings[0])
    bm.faces.new(reversed(rings[-1]))


def build(**overrides):
    p = {**P, **overrides}
    col, root = gc.new_asset(p["name"])
    b = gc.Builder()
    plinth = gc.coping()
    s, ph = p["plinth"], p["plinth_h"]
    x = p["x"]
    b.box(plinth, (x - s / 2, -s / 2, 0), (x + s / 2, s / 2, ph), skip=("-z",))
    # sculpture
    bm = bmesh.new()
    base = Vector((x, 0, ph))
    ribbon(bm, base, p["height"], 2.0, 0.55, 0.16, math.radians(300), 0.0, 0.25, 0.0, p["segments"])
    ribbon(bm, base + Vector((0.0, 0.0, 0)), p["height"] * 0.66, 1.2, 0.4, 0.12, math.radians(-240), 0.0, -0.2,
           math.radians(90), 20)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # smooth along the twist, crisp along the ribbon's edges
    for e in bm.edges:
        d = e.verts[1].co - e.verts[0].co
        e.smooth = abs(d.z) < 1e-6 or (d.xy.length > 1.5 * abs(d.z))
    for f in bm.faces:
        f.smooth = True
    common.mesh_object(f"{p['name']}_Bronze", bm, col, gc.bronze(), root, smooth=False)
    b.finish(p["name"], col, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
