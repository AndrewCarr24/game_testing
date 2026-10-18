"""West garden paving: the landing that continues the house terrace, the two long walks that
flank the reflecting pool, and the end court around the sculpture. Large-format limestone
slabs with thin dark joints (cross joints run the full width, leading the eye down the
garden). Garden frame (see garden_common): origin at the pool's centre."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garden_common as gc  # noqa: E402

importlib.reload(gc)
common, outdoor = gc.common, gc.outdoor

NAME = "GardenPaving"

P = dict(
    name=NAME,
    pool_half=13.5,          # half the pool length
    pool_half_w=2.3,
    walk_w=2.5,
    landing=2.0,             # between the terrace edge and the pool head
    court=5.3,               # end court depth beyond the pool foot
    half_w=8.4,              # landing / court half width
    gap=0.025,               # joint width
)


def build(**overrides):
    p = {**P, **overrides}
    col, root = gc.new_asset(p["name"])
    ph, hw, ww = p["pool_half"], p["half_w"], p["walk_w"]
    pw = p["pool_half_w"]
    b = gc.Builder()
    stone, joint = outdoor.stone(), gc.joint()
    rects = []
    for sy in (-1, 1):
        y0, y1 = sorted((sy * pw, sy * (pw + ww)))
        rects.append(("walk", -ph, y0, ph, y1, 1.8, ww))
    rects.append(("landing", ph, -hw, ph + p["landing"], hw, 2.0, 2.8))
    rects.append(("court", -ph - p["court"], -hw, -ph, hw, p["court"] / 2, 2.8))
    g = p["gap"] / 2
    for kind, x0, y0, x1, y1, su, sv in rects:
        b.grid(joint, (x0, y0, gc.JOINT_Z), (x1 - x0, 0, 0), (0, y1 - y0, 0), step=99)
        for sx0, sy0, sx1, sy1 in gc.tile_rect(x0, y0, x1, y1, su, sv):
            b.grid(stone, (sx0 + g, sy0 + g, gc.PAVE_Z), (sx1 - sx0 - 2 * g, 0, 0), (0, sy1 - sy0 - 2 * g, 0),
                   uv_tile=2.0)
        if kind == "landing":
            b.box(stone, (x0, y0, 0), (x1, y1, gc.PAVE_Z), only=("+y", "-y"), uv_tile=2.0)
        elif kind == "court":
            b.box(stone, (x0, y0, 0), (x1, y1, gc.PAVE_Z), only=("+y", "-y", "-x"), uv_tile=2.0)
    b.finish(p["name"], col, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
