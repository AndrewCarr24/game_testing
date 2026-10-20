"""Battery: a rechargeable 21700 cell for the flashlight (21 x 70 mm), a deep teal wrap
with a thin white band, a steel positive cap and a flat steel base. A pickup (item
"battery"; refills the flashlight). Lies on its side along X; origin at the centre of its underside."""
import importlib
import os
import sys

from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402

importlib.reload(ix_common)
common, materials = ix_common.common, ix_common.materials

NAME = "IX_Battery"
P = dict(name=NAME, length=0.070, r=0.0105, segments=18)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    root["interact"] = ix_common.pickup("battery", "Battery")

    wrap = common.pbr_material("M_Battery_Wrap", (0.01, 0.12, 0.13), roughness=0.35, coat=0.5)
    band = common.pbr_material("M_Battery_Band", (0.72, 0.72, 0.70), roughness=0.4, coat=0.5)
    steel = materials.steel()
    L, r, seg = p["length"], p["r"], p["segments"]
    common.mesh_object(f"{n}_Wrap", ix_common.lathe_bmesh(
        [(r - 0.0012, 0.0005), (r, 0.0018), (r, L - 0.0018), (r - 0.0012, L - 0.0006)], seg, axis="x"), col, wrap, root)
    common.mesh_object(f"{n}_Band", ix_common.lathe_bmesh(
        [(r + 0.0001, 0.050), (r + 0.0001, 0.054)], seg, axis="x"), col, band, root)
    common.mesh_object(f"{n}_Base", ix_common.lathe_bmesh(
        [(0, 0.0), (r - 0.0012, 0.0), (r - 0.0012, 0.0006)], seg, axis="x"), col, steel, root)
    common.mesh_object(f"{n}_Cap", ix_common.lathe_bmesh(
        [(r - 0.0012, L - 0.0006), (0.0045, L - 0.0004), (0.0042, L + 0.0012), (0, L + 0.0012)], seg, axis="x"),
        col, steel, root)
    for ob in root.children:
        ob.location = Vector(ob.location) + Vector((-L / 2, 0, r))
    return ix_common.finish(root)
