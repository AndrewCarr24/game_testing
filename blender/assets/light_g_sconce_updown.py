"""Up/down wall sconce: a bronze cylinder open at both ends, a warm lens recessed in each
end, held off the wall on a short arm from a round backplate. It throws two scallops of
light, one up and one down the wall: the room's LIGHTS put a `spot` just above and below
it (pos 0.13 m out from the wall, aimed straight up / down, about 50-70 degrees).

Hangs on a wall: origin = the centre of the cylinder's height on the wall plane; it stands
out toward -Y. Mount it with z about 2.25 (its bottom stays above 2.1 m). Units are metres.
"""
import importlib
import math
import os
import sys

import bmesh
import mathutils

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import table_lamp  # noqa: E402  (lathe, cylinder_between)

importlib.reload(common)
importlib.reload(materials)

NAME = "LightGSconceUpDown"

P = dict(
    name=NAME,
    radius=0.05,
    height=0.26,
    stand=0.13,           # cylinder axis distance from the wall
    lens_in=0.028,        # lens depth inside each end
    segs=16,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    bronze = materials.bronze()
    glow = materials.emissive("M_LampBulb", (1.0, 0.92, 0.74), 6.0)

    r, h, s, segs = p["radius"], p["height"], p["stand"], p["segs"]
    w, li = 0.0025, p["lens_in"]
    # body: outer wall with eased rims, turning in and running down the inside to the lenses
    prof = [(r - w, h / 2 - li), (r - w, h / 2 - 0.002), (r - 0.001, h / 2), (r, h / 2 - 0.0015),
            (r, -h / 2 + 0.0015), (r - 0.001, -h / 2), (r - w, -h / 2 + 0.002), (r - w, -h / 2 + li)]
    body = common.mesh_object(f"{n}_Body_NoCollide", table_lamp.lathe(prof, segs, closed=False, sharp=35),
                              col, bronze, root)
    body.location = (0, -s, 0)
    # a fine reeded band round the middle (where the arm joins)
    band = table_lamp.lathe([(r, -0.012), (r + 0.003, -0.01), (r + 0.003, 0.01), (r, 0.012)], segs, closed=False,
                            sharp=35)
    common.mesh_object(f"{n}_Band_NoCollide", band, col, bronze, root).location = (0, -s, 0)
    # lenses: one facing up, one facing down
    lens = bmesh.new()
    for sg in (1, -1):
        z = sg * (h / 2 - li)
        verts = [lens.verts.new((math.cos(2 * math.pi * k / segs) * (r - w), -s + math.sin(2 * math.pi * k / segs) * (r - w), z))
                 for k in range(segs)]
        f = lens.faces.new(verts if sg > 0 else verts[::-1])
    common.mesh_object(f"{n}_Lens_NoCollide", lens, col, glow, root, smooth=False)
    # arm and backplate
    arm = bmesh.new()
    table_lamp.cylinder_between(arm, (0, -0.012, 0), (0, -s + r - 0.002, 0), 0.009, segs=10)
    common.mesh_object(f"{n}_Arm_NoCollide", arm, col, bronze, root)
    plate = table_lamp.lathe([(0.0, 0.0), (0.045, 0.0), (0.045, 0.008), (0.039, 0.013), (0.0, 0.013)], 24, sharp=40)
    bmesh.ops.rotate(plate, verts=plate.verts, cent=(0, 0, 0), matrix=mathutils.Matrix.Rotation(math.radians(90), 3, "X"))
    common.mesh_object(f"{n}_Plate_NoCollide", plate, col, bronze, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
