"""Access keycard: credit-card sized, pearl white with a blue band, gold chip
and a small black emblem. A pickup (item id "keycard").

Lies flat; origin at the centre of its underside."""
import importlib
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common  # noqa: E402

importlib.reload(common)

NAME = "Keycard"

P = dict(
    name=NAME,
    size=(0.0856, 0.054),     # ISO card
    thickness=0.0015,         # a bit thicker than a real card so it reads in-game
    corner=0.0032,
    band=0.02,                # blue band across one end
    item="keycard",
    label="Keycard",
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    root["interact"] = {"type": "pickup", "item": p["item"], "name": p["label"],
                        "prompt": f"Take {p['label'].lower()}", "range": 1.4}

    white = common.pbr_material("M_Card_Pearl", (0.82, 0.82, 0.8), roughness=0.3, coat=0.6)
    blue = common.pbr_material("M_Card_Blue", (0.01, 0.07, 0.42), roughness=0.3, coat=0.6)
    gold = common.pbr_material("M_Card_Chip", (1.0, 0.76, 0.33), roughness=0.25, metallic=1.0)
    ink = common.pbr_material("M_Card_Ink", (0.01, 0.01, 0.012), roughness=0.4)

    w, d = p["size"]
    t = p["thickness"]
    body = common.mesh_object(f"{n}_Body", common.rounded_slab_bmesh(w, d, t, p["corner"], segments=4),
                              col, white, root)
    body.location = (0, 0, t / 2)

    # decals sit 0.1 mm proud of the top face
    top = t + 0.00005
    band = common.mesh_object(f"{n}_Band", common.box_bmesh((p["band"], d - 0.001, 0.0001)), col, blue, root,
                              smooth=False)
    band.location = (w / 2 - p["band"] / 2 - 0.0005, 0, top)
    chip = common.mesh_object(f"{n}_Chip", common.box_bmesh((0.011, 0.009, 0.0002)), col, gold, root, smooth=False)
    chip.location = (-w / 2 + 0.017, 0.006, top)

    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.006, radius2=0.006, depth=0.0001)
    emblem = common.mesh_object(f"{n}_Emblem", bm, col, ink, root, smooth=False)
    emblem.location = (w / 2 - p["band"] - 0.012, -0.012, top)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
