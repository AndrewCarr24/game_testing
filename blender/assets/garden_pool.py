"""The west garden's reflecting pool: a long, raised, rectangular basin in honed limestone
with a crisp coping and the water a few millimetres below the rim. Long axis along X,
origin at the pool's centre on the lawn (garden frame, see garden_common)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garden_common as gc  # noqa: E402

importlib.reload(gc)
common, outdoor = gc.common, gc.outdoor

NAME = "GardenPool"

P = dict(name=NAME, length=27.0, width=4.6, coping=0.40, height=0.30, water_drop=0.03, floor_z=0.06)


def build(**overrides):
    p = {**P, **overrides}
    col, root = gc.new_asset(p["name"])
    L, W, H, t = p["length"], p["width"], p["height"], p["coping"]
    b = gc.Builder()
    cop = gc.coping()
    # two long bars and two end bars: rim top, outer face, inner face
    for sy in (-1, 1):
        y0, y1 = (W / 2 - t, W / 2) if sy > 0 else (-W / 2, -W / 2 + t)
        b.box(cop, (-L / 2, y0, 0), (L / 2, y1, H), skip=("-z",))
    for sx in (-1, 1):
        x0, x1 = (L / 2 - t, L / 2) if sx > 0 else (-L / 2, -L / 2 + t)
        b.box(cop, (x0, -W / 2 + t, 0), (x1, W / 2 - t, H), skip=("-z", "+y", "-y"))
    # basin floor
    b.grid(gc.pool_floor(), (-L / 2 + t, -W / 2 + t, p["floor_z"]), (L - 2 * t, 0, 0), (0, W - 2 * t, 0), step=99)
    # water
    zw = H - p["water_drop"]
    b.grid(outdoor.water(), (-L / 2 + t, -W / 2 + t, zw), (L - 2 * t, 0, 0), (0, W - 2 * t, 0), step=99)
    b.finish(p["name"], col, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
