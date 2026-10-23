"""Folded linen on a cedar shelf (the bathhouse): a cantilevered board on the wall with three stacks
of folded towels (static textiles, not pickups). 1.6 m long, the board at 0.9 m.
Origin: the shelf's back centre on the wall surface, floor level; it faces -y."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ph_common as pc  # noqa: E402

importlib.reload(pc)
common = pc.common

NAME = "PHTowels"
P = dict(name=NAME, length=1.6, depth=0.4, z=0.9, t=0.05)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = pc.start(n)
    L, D, z, t = p["length"], p["depth"], p["z"], p["t"]
    pc.box(f"{n}_Shelf", (-L / 2, -D, z - t), (L / 2, 0, z), pc.cedar(), col, root, uv_tile=0.5, bevel=0.003)
    linen = pc.linen()
    for i, (x, k) in enumerate(((-0.5, 4), (0.0, 3), (0.48, 5))):
        for j in range(k):
            dx = 0.012 * ((i + j) % 3 - 1)
            pc.box(f"{n}_Towel{i}_{j}", (x - 0.2 + dx, -D + 0.05, z + j * 0.055), (x + 0.2 + dx, -0.04, z + (j + 1) * 0.055 - 0.004),
                   linen, col, root, uv_tile=0.25, bevel=0.016, smooth=True)
    return pc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
