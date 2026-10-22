"""The secret stair's window into the pool (the bathhouse; viewer/water_fx.js fx "underwater"): one
card on the water's side of the glass in the pool's east end, facing the stair. The engine follows
every view ray through it into the pool (its box: userData.box, glTF, the pool's inside up to the
surface) and shows what it meets: the stone floor and walls under moving light, the surface's
silver underside, the light above inside Snell's window, all fogged teal by the distance. 5.2 x
1.14 m (the window, bathhouse_plan.POOL_WINDOW). Origin: the card's centre."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ph_common as pc  # noqa: E402

importlib.reload(pc)
common = pc.common

NAME = "PHPoolWindow"
# the pool's inside in glTF (x, y up, z = -Blender y): x 27.15..38.37, y -1.4..-0.08, Blender y 34.9..40.9
P = dict(name=NAME, size=(5.2, 1.14), box=[27.15, -1.4, -40.9, 38.37, -0.08, -34.9])


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = pc.start(n)
    w, h = p["size"]
    pc.no_bake_light(pc.card(f"{n}_NoCollide_Water", w, h, pc.fx_material("M_PH_FX_Water"), col, root, facing="+x",
                             fx="underwater", box=p["box"], stone=[0.075, 0.1, 0.092], deep=[0.004, 0.045, 0.055],
                             above=[0.95, 0.78, 0.55], sun=[0.7, 0.85, 0.72]))
    return pc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
