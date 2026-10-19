"""Entry centre table: a 1.5 m round honed white-marble top with a softly eased edge
on a sculptural walnut pedestal (a flared drum on a bronze plinth, with a recessed
shadow gap under the top). Rotationally symmetric. Origin: floor centre.
Units are metres.
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials, textures  # noqa: E402
import table_lamp  # noqa: E402  (lathe, catmull, cylindrical_uv)

importlib.reload(common)
importlib.reload(materials)

NAME = "EntryRoundTable"

P = dict(
    name=NAME,
    top_r=0.75,
    top_t=0.055,
    height=0.80,
    segments=72,
    plinth_r=0.40, plinth_h=0.04,
    stem_r_low=0.255, stem_r_waist=0.145, stem_r_high=0.225,
    gap=0.035,              # dark shadow gap between stem and top
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    seg = p["segments"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    walnut = materials.walnut()
    bronze = materials.bronze()
    black = materials.black_metal()
    marble = common.pbr_material("M_Marble_White", (0.8, 0.79, 0.77), roughness=0.12)
    common.set_base_color_map(marble, textures.load(textures.marble()))

    H, tt, R = p["height"], p["top_t"], p["top_r"]
    z_top0 = H - tt

    # marble top with a eased lower edge and a crisp top edge
    e = 0.012
    top_prof = [(0.0, z_top0), (R - e, z_top0), (R, z_top0 + 0.006), (R, H - 0.004), (R - 0.004, H),
                (0.0, H)]
    top = common.mesh_object(f"{n}_Top", table_lamp.lathe(top_prof, seg, sharp=35), col, marble, root)
    common.box_uv(top, tile=1.0)

    # black recessed collar (shadow gap)
    g = p["gap"]
    collar = common.mesh_object(f"{n}_Collar", table_lamp.lathe(
        [(0.0, z_top0 - g), (p["stem_r_high"] - 0.02, z_top0 - g), (p["stem_r_high"] - 0.02, z_top0), (0.0, z_top0)], 48),
        col, black, root)

    # walnut stem: flared at the foot, pinched waist, swelling under the top
    z0 = p["plinth_h"]
    z1 = z_top0 - g
    pts = [(p["stem_r_low"], z0), (p["stem_r_low"] - 0.02, z0 + 0.10), (p["stem_r_waist"] + 0.01, z0 + 0.26),
           (p["stem_r_waist"], (z0 + z1) / 2 - 0.02), (p["stem_r_waist"] + 0.02, z1 - 0.15), (p["stem_r_high"], z1)]
    dense = table_lamp.catmull([(r, z) for r, z in pts], per=3)
    prof = [(0.0, z0)] + dense + [(0.0, z1)]
    stem = common.mesh_object(f"{n}_Stem", table_lamp.lathe(prof, 56, sharp=60), col, walnut, root)
    table_lamp.cylindrical_uv(stem, circumference_tiles=1.6, tile=0.5)

    # bronze plinth disc with a chamfer
    pr, ph = p["plinth_r"], p["plinth_h"]
    plinth = common.mesh_object(f"{n}_Plinth", table_lamp.lathe(
        [(0.0, 0.0), (pr - 0.008, 0.0), (pr, 0.008), (pr, ph - 0.006), (pr - 0.01, ph), (0.0, ph)], 56, sharp=35),
        col, bronze, root)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
