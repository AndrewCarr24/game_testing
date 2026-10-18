"""Wall sconce: a tall opal-glass tube held off the wall between two polished-bronze caps,
carried on a short bronze arm from a round backplate. The tube glows warm.

Hangs on a wall: origin = the centre of the tube's height on the wall plane; the tube
stands 0.09 m off the wall toward -Y. Units are metres.
"""
import importlib
import math
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import table_lamp  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "EntrySconce"

P = dict(
    name=NAME,
    length=0.46,          # glass tube length
    r=0.038,              # tube radius
    stand=0.095,          # tube axis distance from the wall
    emission=2.4,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    bronze = common.pbr_material("M_Entry_Bronze_Polished", (0.50, 0.30, 0.14), roughness=0.2, metallic=1.0)
    glow = materials.emissive("M_Entry_Sconce_Glow", (1.0, 0.80, 0.55), p["emission"])

    L, r, s = p["length"], p["r"], p["stand"]
    segs = 28

    def lathe_z(name, prof, mat, y=-s, z=0.0):
        bm = table_lamp.lathe(prof, segs, sharp=45)
        ob = common.mesh_object(f"{n}_{name}", bm, col, mat, root)
        ob.location = (0, y, z)
        return ob

    # tube: axis vertical (z) at y = -stand
    lathe_z("Tube", [(r, -L / 2 + 0.004), (r, L / 2 - 0.004)] + [(r - 0.003, L / 2 - 0.004), (r - 0.003, -L / 2 + 0.004)],
            glow)
    # caps: stepped discs top and bottom
    for tag, sg in (("CapTop", 1), ("CapBottom", -1)):
        z0 = sg * L / 2
        prof = [(0.0, z0 - sg * 0.014), (r + 0.006, z0 - sg * 0.014), (r + 0.006, z0 + sg * 0.012),
                (r - 0.012, z0 + sg * 0.018), (0.0, z0 + sg * 0.018)]
        lathe_z(tag, prof if sg > 0 else prof, bronze)
    # arm and backplate
    arm = bmesh.new()
    table_lamp.cylinder_between(arm, (0, 0.0, 0.0), (0, -s + 0.002, 0.0), 0.008, segs=12)
    common.mesh_object(f"{n}_Arm", arm, col, bronze, root)
    plate = table_lamp.lathe([(0.0, 0.0), (0.05, 0.0), (0.05, 0.008), (0.044, 0.016), (0.0, 0.016)], 36, sharp=40)
    import mathutils
    bmesh.ops.rotate(plate, verts=plate.verts, cent=(0, 0, 0), matrix=mathutils.Matrix.Rotation(math.radians(90), 3, "X"))
    common.mesh_object(f"{n}_Plate", plate, col, bronze, root)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
