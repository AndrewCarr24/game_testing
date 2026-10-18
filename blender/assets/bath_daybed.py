"""Spa daybed: a honed-stone plinth base with a thick oat linen mattress, a rolled
bolster at the head and two scatter cushions (ink and ivory).
The head (bolster) is at the +X end. Origin: floor centre, front -Y.
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import bath_common as bc  # noqa: E402

importlib.reload(common)
importlib.reload(bc)

NAME = "BathDaybed"

P = dict(name=NAME, size=(2.0, 0.82), seat_h=0.44, base_h=0.24, base_inset=0.05)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    stone, black = bc.stone(), materials.black_metal()
    oat = materials.fabric("M_Fabric_Oat", (0.42, 0.37, 0.30))
    ivory = materials.fabric("M_Fabric_Linen_Ivory", (0.55, 0.52, 0.46))
    ink = materials.fabric("M_Fabric_Ink", (0.02, 0.03, 0.06))

    W, D = p["size"]
    H, bh, ins = p["seat_h"], p["base_h"], p["base_inset"]
    # stone plinth (a slab, recessed from the mattress edge) on a dark shadow foot
    bc.box(col, root, f"{n}_Foot", (W - 0.30, D - 0.24, 0.05), (0, 0, 0.025), black, bevel=0.002)
    bc.box(col, root, f"{n}_Base", (W - 0.04, D - 0.04, bh - 0.05), (0, 0, 0.05 + (bh - 0.05) / 2), stone, bevel=0.012, uv_tile=1.0)
    # mattress
    mt = H - bh
    mat = common.mesh_object(f"{n}_Mattress", common.cushion_bmesh((W, D, mt), edge=0.035, crown={"+z": 0.02}), col, oat, root)
    mat.location = (0, 0, bh + mt / 2)
    common.box_uv(mat, tile=0.25)
    common.add_subsurf(mat)
    # bolster at the head (+X end)
    br = 0.115
    bol = bmesh.new()
    bc.cylinder_between(bol, (W / 2 - 0.22, -D / 2 + 0.14, H + br - 0.01), (W / 2 - 0.22, D / 2 - 0.14, H + br - 0.01), br, 24)
    common.box_uv(common.mesh_object(f"{n}_Bolster", bol, col, ivory, root), tile=0.25)
    # two scatter cushions leaning on the bolster
    for i, (mat_, y, sz) in enumerate(((ink, -0.17, (0.12, 0.46, 0.42)), (ivory, 0.19, (0.11, 0.40, 0.38)))):
        c = common.mesh_object(f"{n}_Pillow_{i}", common.cushion_bmesh(sz, cuts=4, edge=0.04, crown={"+x": 0.03, "-x": 0.03}),
                               col, mat_, root)
        common.box_uv(c, tile=0.25)
        common.add_subsurf(c)
        c.rotation_euler = (0, math.radians(17 + 3 * i), math.radians(4 - 8 * i))
        c.location = (W / 2 - 0.22 - br - 0.065 - 0.01 * i, y, H + sz[2] / 2 + 0.005)
    return root, bc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
