"""Clipped yew hedge walls that close the garden on either side of the olive allée, frame the
view down the pool and return at the west end to meet the backdrop wall. Garden frame (see
garden_common): origin at the pool's centre, long walls parallel to the pool at +-13.2 m."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garden_common as gc  # noqa: E402

importlib.reload(gc)
common, outdoor = gc.common, gc.outdoor

NAME = "GardenHedges"

P = dict(name=NAME, u0=-19.0, u1=15.5, v=13.2, thick=0.9, height=1.9, return_from=8.0)


def build(**overrides):
    p = {**P, **overrides}
    col, root = gc.new_asset(p["name"])
    b = gc.Builder()
    leaf = outdoor.foliage()
    t, h = p["thick"], p["height"]
    for sy in (-1, 1):
        v = sy * p["v"]
        b.box(leaf, (p["u0"] - t / 2, v - t / 2, 0), (p["u1"], v + t / 2, h), skip=("-z",), step=3.0, uv_tile=1.5)
        # return along the west end, from the wall's wing out to the long hedge
        y0, y1 = sorted((sy * p["return_from"], sy * (p["v"] - t / 2)))
        b.box(leaf, (p["u0"] - t / 2, y0, 0), (p["u0"] + t / 2, y1, h), skip=("-z", "+y", "-y"), step=3.0, uv_tile=1.5)
    b.finish(p["name"], col, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
