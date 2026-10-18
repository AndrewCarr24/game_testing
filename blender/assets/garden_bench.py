"""Monolithic limestone garden bench: a thick seat slab on two slab ends with a slim backrest.
2.6 m long, front faces -Y (the sitter looks towards -Y). Origin at the floor centre."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garden_common as gc  # noqa: E402

importlib.reload(gc)
common, outdoor = gc.common, gc.outdoor

NAME = "GardenBench"

P = dict(name=NAME, length=2.6, depth=0.56, seat_z=0.45, seat_t=0.13, end_t=0.17, back_t=0.11, back_h=0.42)


def build(**overrides):
    p = {**P, **overrides}
    col, root = gc.new_asset(p["name"])
    b = gc.Builder()
    m = outdoor.stone()
    L, D, sz, st = p["length"], p["depth"], p["seat_z"], p["seat_t"]
    et = p["end_t"]
    for sx in (-1, 1):
        x0, x1 = (L / 2 - et, L / 2) if sx > 0 else (-L / 2, -L / 2 + et)
        b.box(m, (x0, -D / 2 + 0.03, 0), (x1, D / 2 - 0.03, sz - st), skip=("-z", "+z"), uv_tile=2.0)
    b.box(m, (-L / 2, -D / 2, sz - st), (L / 2, D / 2, sz), skip=("+y",) if False else (), uv_tile=2.0)
    b.box(m, (-L / 2 + 0.02, D / 2 - p["back_t"], sz), (L / 2 - 0.02, D / 2, sz + p["back_h"]), skip=("-z",), uv_tile=2.0)
    b.finish(p["name"], col, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
