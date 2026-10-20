"""Fuse: a main cartridge fuse for the breaker panel (14 x 51 mm), a white ceramic body
with a red trip indicator, brass end caps with a ferrule ring. A pickup (item "fuse"; used
at the garage breaker panel to restore power). Lies along X; origin at the centre of its underside."""
import importlib
import os
import sys

from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402

importlib.reload(ix_common)
common, materials = ix_common.common, ix_common.materials

NAME = "IX_Fuse"
P = dict(name=NAME, length=0.051, r=0.007, cap=0.011, segments=16)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    root["interact"] = ix_common.pickup("fuse", "Fuse")

    ceramic = common.pbr_material("M_Fuse_Ceramic", (0.80, 0.78, 0.73), roughness=0.55)
    brass = common.pbr_material("M_Brass", (0.78, 0.56, 0.24), roughness=0.3, metallic=1.0)
    red = common.pbr_material("M_Fuse_Indicator", (0.55, 0.03, 0.02), roughness=0.4)
    L, r, c, seg = p["length"], p["r"], p["cap"], p["segments"]
    common.mesh_object(f"{n}_Body", ix_common.lathe_bmesh([(r - 0.0004, c - 0.001), (r - 0.0004, L - c + 0.001)], seg,
                                                         axis="x"), col, ceramic, root)
    for k, (a, b) in enumerate(((0.0, c), (L - c, L))):
        sgn = 1 if k == 0 else -1
        prof = [(0, a if k == 0 else b), (r - 0.0008, a if k == 0 else b)]
        prof = [(0, 0.0), (r - 0.0009, 0.0), (r, 0.0008), (r, c - 0.0028), (r + 0.0004, c - 0.0024),
                (r + 0.0004, c - 0.0008), (r - 0.0004, c - 0.0004), (r - 0.0004, c)]
        bm = ix_common.lathe_bmesh(prof, seg, axis="x", sharp=[3, 5])
        ob = common.mesh_object(f"{n}_Cap{k}", bm, col, brass, root)
        if k == 1:
            ob.scale = (-1, 1, 1)
            ob.location = (L, 0, 0)
    dot = common.mesh_object(f"{n}_Indicator", common.box_bmesh((0.004, 0.003, 0.0006)), col, red, root, smooth=False)
    dot.location = (L / 2, 0, r - 0.0002)
    for ob in root.children:
        ob.location = Vector(ob.location) + Vector((-L / 2, 0, r + 0.0004))
    return ix_common.finish(root)
