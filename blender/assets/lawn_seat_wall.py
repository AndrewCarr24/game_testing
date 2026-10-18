"""Limestone retaining wall holding a raised lawn terrace, with a teak bench set against it
and a short flight of stone steps at one end. The wall is 0.6 m high with a slim overhanging
coping; the raised lawn runs back (+Y) behind it, carrying the grove. Seat on the -Y side,
facing -Y (rotate 180 to face north towards the house).

Origin: on the lawn, centre of the wall's seating face (y = 0). X runs along the wall."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lawn_common as lc  # noqa: E402

importlib.reload(lc)
common, outdoor = lc.common, lc.outdoor

NAME = "LawnSeatWall"

P = dict(
    name=NAME,
    length=15.0,         # wall incl. steps; x = -7.5 .. 7.5
    wall_t=0.40,
    wall_h=0.56,         # top of the wall under the coping
    coping=(0.07, 0.05), # (overhang, thickness)
    grass_z=0.55,        # raised lawn level
    depth=4.2,           # raised lawn depth behind the wall
    steps=(2.4, 3),      # (width, treads): steps at the +x end
    bench=(4.2, 0.52, 0.07, 0.40),   # length, depth, seat thickness, seat top height
    bench_x=-0.6,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    stone, teak, grass = outdoor.stone(), outdoor.teak(), outdoor.grass()

    L, t, H = p["length"], p["wall_t"], p["wall_h"]
    sw, ns = p["steps"]
    x0, x1 = -L / 2, L / 2
    xs = x1 - sw                      # wall runs x0..xs, steps xs..x1
    ov, ct = p["coping"]
    # wall: only the faces that show (front, ends, top is under the coping)
    lc.box(f"{n}_Wall", (x0, 0, 0), (xs, t, H), stone, col, root, uv_tile=2.0, skip=("+y", "+z"))
    lc.box(f"{n}_Coping", (x0 - ov, -ov, H), (xs + 0.02, t + ov, H + ct), stone, col, root, uv_tile=2.0)
    # returns: the raised lawn's side and back walls
    lc.box(f"{n}_Return_W", (x0, t, 0), (x0 + t, p["depth"], H), stone, col, root, uv_tile=2.0, skip=("+z", "-y"))
    lc.box(f"{n}_Return_E", (x1 - t, t, 0), (x1, p["depth"], H), stone, col, root, uv_tile=2.0, skip=("+z", "-y"))
    lc.box(f"{n}_Return_cap_W", (x0 - ov, t, H), (x0 + t + ov, p["depth"], H + ct), stone, col, root, uv_tile=2.0)
    lc.box(f"{n}_Return_cap_E", (x1 - t - ov, t, H), (x1 + ov, p["depth"], H + ct), stone, col, root, uv_tile=2.0)
    lc.box(f"{n}_Return_S", (x0, p["depth"] - t, 0), (x1, p["depth"], H), stone, col, root, step=20, uv_tile=2.0, skip=("+z", "-y"))
    lc.box(f"{n}_Return_cap_S", (x0 - ov, p["depth"] - t - ov, H), (x1 + ov, p["depth"] + ov, H + ct), stone, col, root, step=20, uv_tile=2.0)
    # raised lawn
    lc.grid_pad(f"{n}_Lawn", x0 + t, t, x1 - t, p["depth"], p["grass_z"], grass, col, root, uv_tile=3.0)
    # steps: rise to the lawn level, 0.30 m treads
    rise = p["grass_z"] / ns
    for k in range(ns):
        top = rise * (k + 1)
        y_front = -0.30 * (ns - 1 - k)
        lc.box(f"{n}_Step{k}", (xs, y_front, 0), (x1 - t * 0.0, t if k == ns - 1 else t, top), stone, col, root,
               uv_tile=2.0, skip=("+y",))
    # step cheeks: the wall returns at the step run's end (the steps end flush with the raised lawn's return)
    # bench: teak seat on two stone blocks, against the wall
    bl, bd, bt, bh = p["bench"]
    bx = p["bench_x"]
    for sx in (-1, 1):
        lc.box(f"{n}_Bench_Block{'W' if sx < 0 else 'E'}", (bx + sx * (bl / 2 - 0.55) - 0.26, -bd + 0.05, 0),
               (bx + sx * (bl / 2 - 0.55) + 0.26, 0.0, bh - bt), stone, col, root, uv_tile=2.0, skip=("+y", "+z"))
    lc.box(f"{n}_Bench_Seat", (bx - bl / 2, -bd, bh - bt), (bx + bl / 2, 0.0, bh), teak, col, root, step=1.5, uv_tile=0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
