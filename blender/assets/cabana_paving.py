"""Limestone terrace for the pool house forecourt and outdoor kitchen: one 28 x 11.2 m slab
12 cm above the lawn, cut into 1.5 m cells so shadows (pergola, pavilion) show in the baked
lighting, with a darker bronze edge reveal along the front. Origin: centre of the slab at lawn
level."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cabana_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common

NAME = "CabanaPaving"

P = dict(name=NAME, size=(27.7, 11.1), height=0.12)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    m = cc.M()
    W, D = p["size"]
    cc.box(f"{n}_Slab", (-W / 2, -D / 2, 0.0), (W / 2, D / 2, p["height"]), m["stone"], col, root, step=1.5, drop=("-z",))
    return cc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
