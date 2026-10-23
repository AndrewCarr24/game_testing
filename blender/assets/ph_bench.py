"""A monolithic stone bench (the bathhouse): one honed slab of the floor's stone, 0.44 m high, on a
plinth set back 6 cm so it floats on a line of shadow (Zumthor's benches at Vals are blocks of the
walls' stone). Long and low: crouched behind one in the bath hall, a player is out of sight of
the lawn. Origin: the centre of its footprint on the floor; the long side runs along x, the front
faces -y."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ph_common as pc  # noqa: E402

importlib.reload(pc)
common = pc.common

NAME = "PHBench"
P = dict(name=NAME, length=3.6, depth=0.5, height=0.44, top=0.1, inset=0.06)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = pc.start(n)
    L, D, H, t, k = p["length"], p["depth"], p["height"], p["top"], p["inset"]
    stone = pc.slab()
    pc.box(f"{n}_Top", (-L / 2, -D / 2, H - t), (L / 2, D / 2, H), stone, col, root, uv_tile=2.4, bevel=0.004)
    pc.box(f"{n}_Plinth", (-L / 2 + k, -D / 2 + k, 0), (L / 2 - k, D / 2 - k, H - t), pc.stone(), col, root, uv_tile=2.0)
    return pc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
