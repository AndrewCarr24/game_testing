"""Pool house daybed: a deep teak platform with a sand mattress, four cream and clay pillows and
a folded charcoal throw. Head toward +Y, foot side (open) toward -Y. 2.3 x 2.1 m. Origin: floor
centre."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cabana_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common

NAME = "CabanaDaybed"

P = dict(name=NAME, w=2.3, d=2.1)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    m = cc.M()
    box = cc.box
    W, D = p["w"], p["d"]
    box(f"{n}_Plinth", (-W / 2 + 0.08, -D / 2 + 0.08, 0.0), (W / 2 - 0.08, D / 2 - 0.08, 0.12), m["dark"], col, root, drop=("-z", "+z"))
    box(f"{n}_Platform", (-W / 2, -D / 2, 0.12), (W / 2, D / 2, 0.32), m["teak"], col, root, drop=("-z",), bevel=0.01)
    box(f"{n}_Mattress", (-W / 2 + 0.03, -D / 2 + 0.03, 0.32), (W / 2 - 0.03, D / 2 - 0.03, 0.55), m["sand"], col, root,
        drop=("-z",), bevel=0.05)
    box(f"{n}_Headboard", (-W / 2, D / 2 - 0.10, 0.32), (W / 2, D / 2, 0.92), m["teak"], col, root, drop=("-z",), bevel=0.01)
    for i, (x, mat) in enumerate(((-0.78, "cream"), (-0.26, "clay"), (0.26, "cream"), (0.78, "cream"))):
        box(f"{n}_Pillow{i}", (x - 0.24, D / 2 - 0.50, 0.55), (x + 0.24, D / 2 - 0.12, 0.84), m[mat], col, root,
            drop=("-z",), bevel=0.04)
    box(f"{n}_Throw", (-W / 2 + 0.2, -D / 2 + 0.03, 0.55), (W / 2 - 0.2, -D / 2 + 0.50, 0.575), m["charcoal"], col, root,
        drop=("-z",), bevel=0.01)
    return cc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
