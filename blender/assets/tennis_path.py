"""Limestone path from the lawn to the court gate: 1.8 m wide, 10.35 m long, laid flat at
court level (5 cm above the lawn) with cut cells for vertex lighting. Long axis along X,
origin the centre at lawn level."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tennis_common as tc  # noqa: E402

importlib.reload(tc)
common = tc.common
outdoor = tc.outdoor

NAME = "TennisPath"

P = dict(name=NAME, length=10.35, width=1.8, top=tc.COURT_TOP)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = tc.standalone(n)
    b = tc.Builder(n)
    b.part("Stone", outdoor.stone(), uv=2.0)
    L, W, z = p["length"] / 2, p["width"] / 2, p["top"]
    xs = tc._cells(-L, L, 1.5)
    b.grid("Stone", 2, 1, z, xs, tc._cells(-W, W, 1.5))
    for sy in (-1, 1):
        b.grid("Stone", 1, sy, sy * W, [0.0, z], xs)
    parts = b.finish(col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
