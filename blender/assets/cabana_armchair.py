"""Outdoor lounge armchair for the pavilion's covered terrace: slim teak frame, deep sand seat and
back cushions, a clay pillow. Faces -Y. 0.85 x 0.85 x 0.78 m. Origin: floor centre."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cabana_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common

NAME = "CabanaArmchair"

P = dict(name=NAME)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    m = cc.M()
    box = cc.box
    for sx in (-1, 1):
        box(f"{n}_Side{sx}", (sx * 0.38 - 0.045, -0.40, 0.14), (sx * 0.38 + 0.045, 0.40, 0.56), m["teak"], col, root, drop=("-z",))
        for ly in (-0.34, 0.34):
            box(f"{n}_Leg{sx}{ly}", (sx * 0.38 - 0.025, ly - 0.025, 0.0), (sx * 0.38 + 0.025, ly + 0.025, 0.14), m["dark"], col, root,
                drop=("-z", "+z"))
    box(f"{n}_Base", (-0.34, -0.38, 0.16), (0.34, 0.40, 0.26), m["warm_dark"], col, root, drop=("-z",))
    box(f"{n}_Seat", (-0.335, -0.40, 0.26), (0.335, 0.30, 0.42), m["sand"], col, root, drop=("-z",), bevel=0.035)
    box(f"{n}_Back", (-0.335, 0.28, 0.32), (0.335, 0.42, 0.80), m["sand"], col, root, drop=("-z",))
    box(f"{n}_Pillow", (-0.18, 0.10, 0.42), (0.18, 0.24, 0.68), m["clay"], col, root, drop=("-z",))
    return cc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
