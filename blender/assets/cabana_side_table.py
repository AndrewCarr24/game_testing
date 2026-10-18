"""Limestone drum side table with a bronze tray, 0.5 m across, 0.45 m high. Origin: floor centre."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cabana_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common

NAME = "CabanaSideTable"

P = dict(name=NAME, size=0.5, height=0.45)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    m = cc.M()
    s, h = p["size"] / 2, p["height"]
    cc.box(f"{n}_Block", (-s, -s, 0.0), (s, s, h), m["stone"], col, root, drop=("-z",))
    cc.box(f"{n}_Tray", (-0.14, -0.14, h), (0.14, 0.14, h + 0.025), m["bronze"], col, root, drop=("-z",), bevel=0.008)
    return cc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
