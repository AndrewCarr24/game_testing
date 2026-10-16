"""Low-pile charcoal wool rug. Origin is the floor centre."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)

NAME = "Rug"

P = dict(name=NAME, size=(3.0, 2.2), thickness=0.012, corner=0.03)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    wool = common.pbr_material("M_Wool_Charcoal", (0.06, 0.06, 0.065), roughness=0.95)
    common.set_base_color_map(wool, textures.load(textures.wool()))

    w, d = p["size"]
    rug = common.mesh_object(f"{n}_Body",
                             common.rounded_slab_bmesh(w, d, p["thickness"], p["corner"]),
                             col, wool, root)
    rug.location = (0, 0, p["thickness"] / 2)
    common.add_bevel(rug, 0.004, segments=2)
    common.box_uv(rug, tile=0.5)

    parts = [rug]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
