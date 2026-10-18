"""Stepped white-render backdrop wall behind the sculpture: an 8 m centre panel with a deep
limestone cap and two lower wings, set on a dark shadow-gap base. Runs along Y at the garden's
west end; only its east (garden) face is built. Garden frame (see garden_common)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garden_common as gc  # noqa: E402

importlib.reload(gc)
common, outdoor = gc.common, gc.outdoor

NAME = "GardenWall"

P = dict(name=NAME, x=-19.1, thick=0.4, centre_half=4.0, wing_half=8.0, centre_h=3.7, wing_h=2.5,
         cap=0.07, base=0.14)


def build(**overrides):
    p = {**P, **overrides}
    col, root = gc.new_asset(p["name"])
    b = gc.Builder()
    wall, cap, dark = gc.render(), gc.coping(), outdoor.dark_metal()
    x0, x1 = p["x"] - p["thick"] / 2, p["x"] + p["thick"] / 2
    ci, wi, base, c = p["centre_half"], p["wing_half"], p["base"], p["cap"]
    spans = [(-wi, -ci, p["wing_h"]), (-ci, ci, p["centre_h"]), (ci, wi, p["wing_h"])]
    for y0, y1, h in spans:
        # shadow-gap base (inset), render body (east face and top only matter; ends are seen
        # from the side), cap overhanging 2 cm
        b.box(dark, (x0 + 0.03, y0, 0), (x1 - 0.03, y1, base), skip=("-z", "-x", "+y", "-y"))
        b.box(wall, (x0, y0, base), (x1, y1, h - c), skip=("-x", "+z"))
        b.box(cap, (x0 - 0.02, y0 - 0.02, h - c), (x1 + 0.02, y1 + 0.02, h), skip=("-z", "-x"))
    b.finish(p["name"], col, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
