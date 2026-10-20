"""Car key: the EVs' key fob, a glossy black pebble (72 x 34 x 12 mm) with a satin steel
band round its waist, three flush buttons (no markings) and a steel key ring through one end.
A pickup (item "car_key"). Lies flat; origin at the centre of its underside."""
import importlib
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402

importlib.reload(ix_common)
common, materials = ix_common.common, ix_common.materials

NAME = "IX_CarKey"
P = dict(name=NAME, size=(0.072, 0.034, 0.012))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    root["interact"] = ix_common.pickup("car_key", "Car key")

    gloss = common.pbr_material("M_KeyFob_Black", (0.012, 0.012, 0.014), roughness=0.18, coat=0.8)
    satin = common.pbr_material("M_Steel_Satin", (0.62, 0.62, 0.63), roughness=0.3, metallic=1.0)
    btn = common.pbr_material("M_KeyFob_Button", (0.05, 0.05, 0.055), roughness=0.5)
    w, d, t = p["size"]
    shell = common.mesh_object(f"{n}_Shell", common.rounded_slab_bmesh(w, d, t, d * 0.45, segments=6), col, gloss, root)
    shell.location = (0, 0, t / 2)
    common.add_bevel(shell, 0.0035, segments=2)
    band = common.mesh_object(f"{n}_Band", common.rounded_slab_bmesh(w + 0.0008, d + 0.0008, 0.0025, d * 0.45 + 0.0004,
                                                                      segments=6), col, satin, root)
    band.location = (0, 0, t / 2)
    for k, x in enumerate((-0.016, 0.0, 0.016)):
        b = common.mesh_object(f"{n}_Button{k}", common.rounded_slab_bmesh(0.011, 0.011, 0.0008, 0.005, segments=3),
                               col, btn, root)
        b.location = (x - 0.004, 0, t + 0.0001)
    ring = [(w / 2 + 0.003 + 0.009 * math.cos(a), 0.009 * math.sin(a), 0.0016)
            for a in [2 * math.pi * k / 16 for k in range(16)]]
    common.tube_object(f"{n}_Ring", ring, 0.0012, col, satin, root, closed=True)
    return ix_common.finish(root)
