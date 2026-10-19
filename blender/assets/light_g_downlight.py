"""Ceiling downlight: a slim surface-mounted cylinder can in black anodised aluminium,
eased lower rim, a deep black baffle and a small warm lens set well up inside it (glare-free:
from eye height you see the dark baffle and a bright dot, not a glowing slot). The light
itself is a `spot` in the room's LIGHTS just under the lens.

Hangs from the ceiling: origin = the centre of the can's top on the ceiling plane (place it
at z = ceiling height); everything is below it. Units are metres.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import table_lamp  # noqa: E402  (lathe)

importlib.reload(common)
importlib.reload(materials)

NAME = "LightGDownlight"

P = dict(
    name=NAME,
    radius=0.045,
    height=0.11,          # can length below the ceiling
    lens_up=0.035,        # lens height above the rim (inside the baffle)
    segs=14,
)


def lamp_bulb():
    """The shared warm bulb/lens glow (same definition as table_lamp's)."""
    return materials.emissive("M_LampBulb", (1.0, 0.92, 0.74), 6.0)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    black = materials.black_metal()
    glow = lamp_bulb()

    r, h, s = p["radius"], p["height"], p["segs"]
    w = 0.003                              # wall thickness
    zl = -h + p["lens_up"]
    # can: a chamfered ceiling rose, outer wall, eased rim, inner baffle up to the lens (open profile)
    prof = [(r + 0.004, 0.0), (r, -0.005), (r, -h + 0.003), (r - w, -h), (r - w - 0.006, zl)]
    can = table_lamp.lathe(prof, s, closed=False, sharp=35)
    common.mesh_object(f"{n}_Can_NoCollide", can, col, black, root)
    lens = table_lamp.lathe([(r - w - 0.006, zl), (0.0, zl)], s, closed=False)
    ob = common.mesh_object(f"{n}_Lens_NoCollide", lens, col, glow, root)
    for poly in ob.data.polygons:          # faces down, into the room
        if poly.normal.z > 0:
            poly.flip()
    ob.data.update()
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
