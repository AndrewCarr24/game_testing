"""Wine bottle: a full Bordeaux bottle (300 mm), dark green glass with a punt, a plain cream
label (no markings) and a deep claret foil capsule. A throwable pickup (item "wine_bottle",
noise 1.2): it shatters where it lands. Standing; origin at the centre of its underside."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402

importlib.reload(ix_common)
common, materials = ix_common.common, ix_common.materials

NAME = "IX_WineBottle"
P = dict(name=NAME, segments=20, label="M_Bottle_Label_Cream", label_color=(0.62, 0.57, 0.46))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    root["interact"] = ix_common.pickup("wine_bottle", "Wine bottle", throwable=True, noise=1.2, shatter=True)
    glass = materials.glass("M_Glass_Bottle_Green", tint=(0.025, 0.07, 0.035), alpha=0.88, roughness=0.05)
    label = common.pbr_material(p["label"], p["label_color"], roughness=0.85)
    foil = common.pbr_material("M_Bottle_Foil", (0.17, 0.015, 0.03), roughness=0.3, metallic=0.8)
    seg = p["segments"]
    r = 0.037
    prof = [(0, 0.016), (0.012, 0.012), (0.026, 0.003), (r - 0.003, 0.0), (r, 0.004), (r, 0.205), (r - 0.003, 0.222),
            (0.026, 0.240), (0.017, 0.255), (0.0145, 0.268), (0.0145, 0.292), (0.0158, 0.294), (0.0158, 0.30),
            (0, 0.30)]
    # glass first: the engine shatters a thrown item in its first mesh's material
    common.mesh_object(f"{n}_Glass", ix_common.lathe_bmesh(prof, seg, sharp=[4]), col, glass, root)
    common.mesh_object(f"{n}_Label", ix_common.lathe_bmesh([(r + 0.0004, 0.075), (r + 0.0004, 0.165)], seg), col,
                       label, root)
    common.mesh_object(f"{n}_Capsule", ix_common.lathe_bmesh(
        [(0.0150, 0.262), (0.0150, 0.292), (0.0163, 0.2935), (0.0163, 0.3005), (0, 0.3005)], seg, sharp=[2]),
        col, foil, root)
    return ix_common.finish(root)
