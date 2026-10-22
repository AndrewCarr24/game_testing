"""The fire bath's hot pool (the bathhouse): its water (3.5 x 1.2 m, fx "water", a warmer, cloudier
teal) and vapour rising off it (fx "steam": two crossing soft cards). Origin: the pool's centre at
the room's floor level."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ph_common as pc  # noqa: E402
import ph_pool_water  # noqa: E402

importlib.reload(pc)
importlib.reload(ph_pool_water)
common = pc.common

NAME = "PHHotWater"
P = dict(name=NAME, size=(3.5, 1.2), water_z=-0.08)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = pc.start(n)
    W, D = p["size"]
    ph_pool_water.surface(n, W, D, p["water_z"], pc.water("M_PH_WaterHot", (0.03, 0.05, 0.045), 0.62), col, root, cell=1.0)
    for i, (y, facing) in enumerate(((-0.25, "-y"), (0.3, "+y"))):
        pc.no_bake_light(pc.card(f"{n}_NoCollide_Steam{i}", W - 0.2, 1.5, pc.fx_material(), col, root,
                                 at=(0, y, p["water_z"] + 0.75), facing=facing, fx="steam", aspect=(W - 0.2) / 1.5,
                                 strength=0.09, seed=float(i), color=[1.0, 0.9, 0.85]))
    return pc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
