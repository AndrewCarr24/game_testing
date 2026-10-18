"""Thick oat linen bath mat with a ribbed texture (the shared fabric weave) and a
softly rounded edge. Origin: floor centre; the front faces -Y.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import bath_common as bc  # noqa: E402

importlib.reload(common)
importlib.reload(bc)

NAME = "BathMat"

P = dict(name=NAME, size=(1.3, 0.62), thickness=0.022, corner=0.07)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    oat = materials.fabric("M_Fabric_Oat", (0.42, 0.37, 0.30))
    w, d = p["size"]
    t = p["thickness"]
    bm = common.rounded_slab_bmesh(w, d, t, p["corner"], segments=6)
    ob = common.mesh_object(f"{n}_Mat", bm, col, oat, root)
    ob.location = (0, 0, t / 2)
    common.add_bevel(ob, 0.008, segments=2)
    common.box_uv(ob, tile=0.25)
    return root, bc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
