"""Round entry rug: a 3.1 m low-pile charcoal wool disc with a fine oat-linen border band
set in from the edge, to ground the centre table under the chandelier.

Origin: floor centre. Units are metres.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials, textures  # noqa: E402
import table_lamp  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "EntryRugRound"

P = dict(name=NAME, radius=1.55, thickness=0.014, band=(1.30, 1.36), segments=80)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    wool = common.pbr_material("M_Wool_Charcoal", (0.06, 0.06, 0.065), roughness=0.95)
    common.set_base_color_map(wool, textures.load(textures.wool()))
    oat = materials.fabric("M_Fabric_Oat", (0.42, 0.37, 0.30))
    R, t, seg = p["radius"], p["thickness"], p["segments"]
    disc = common.mesh_object(f"{n}_Body", table_lamp.lathe(
        [(0.0, 0.0), (R - 0.004, 0.0), (R, 0.004), (R, t - 0.004), (R - 0.004, t), (0.0, t)], seg, sharp=40), col, wool, root)
    common.box_uv(disc, tile=0.5)
    r0, r1 = p["band"]
    band = common.mesh_object(f"{n}_Band", table_lamp.lathe(
        [(r0, t - 0.002), (r1, t - 0.002), (r1, t + 0.003), (r0, t + 0.003)], seg, sharp=40), col, oat, root)
    common.box_uv(band, tile=0.25)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
