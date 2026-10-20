"""Linear pendant for a table or an island: a slim bronze bar with softened ends and a
warm opal diffuser set into its underside, hung on two hair-thin black cables from small
bronze ceiling canopies. The room's LIGHTS put an `area` light just under the diffuser
(aimed down) and, if wanted, a weak one on top (aimed up) for the ceiling glow.

Hangs from the ceiling: origin = the ceiling point above the bar's centre (place it at
z = ceiling height); the bar's underside is `drop` below it. Long axis along X.
Units are metres.
"""
import importlib
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import table_lamp  # noqa: E402  (lathe, cylinder_between)

importlib.reload(common)
importlib.reload(materials)

NAME = "LightGPendantLinear"

P = dict(
    name=NAME,
    length=1.6,
    width=0.075,
    height=0.045,
    drop=2.5,             # ceiling to the bar's underside
    cable_in=0.18,        # cable anchor distance from each end
)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402  (react definitions, prompts/interactivity.md)

importlib.reload(ix_common)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    bronze = materials.bronze()
    black = materials.black_metal()
    glow = materials.emissive("M_LampBulb", (1.0, 0.92, 0.74), 6.0)
    L, W, H, drop = p["length"], p["width"], p["height"], p["drop"]
    zb = -drop

    # bar: a rounded-rectangle slab (corner radius = half the width at the ends)
    bm = common.rounded_slab_bmesh(L, W, H, W * 0.45, segments=4)
    bar = common.mesh_object(f"{n}_Bar", bm, col, bronze, root, smooth=False)
    bar.location = (0, 0, zb + H / 2)      # the slab is centred on its origin
    common.add_bevel(bar, 0.004, segments=2)
    common.box_uv(bar, 0.5)
    # opal diffuser: a slightly inset strip on the underside, facing down
    dif = bmesh.new()
    dl, dw = L - 0.08, W - 0.026
    vs = [dif.verts.new((x, y, zb - 0.0015)) for x, y in ((-dl / 2, -dw / 2), (-dl / 2, dw / 2), (dl / 2, dw / 2), (dl / 2, -dw / 2))]
    dif.faces.new(vs)
    common.mesh_object(f"{n}_Diffuser", dif, col, glow, root, smooth=False)
    # cables and canopies
    cab = bmesh.new()
    for sx in (-1, 1):
        x = sx * (L / 2 - p["cable_in"])
        table_lamp.cylinder_between(cab, (x, 0, zb + H), (x, 0, -0.02), 0.0016, segs=4)
        can = table_lamp.lathe([(0.0, -0.022), (0.038, -0.022), (0.04, -0.016), (0.04, 0.0), (0.0, 0.0)], 20, sharp=40)
        common.mesh_object(f"{n}_Canopy{'LR'[sx > 0]}", can, col, bronze, root).location = (x, 0, 0)
        grip = table_lamp.lathe([(0.0, 0.0), (0.006, 0.0), (0.006, 0.022), (0.0, 0.022)], 8)
        common.mesh_object(f"{n}_Grip{'LR'[sx > 0]}_Piping", grip, col, bronze, root).location = (x, 0, zb + H)
    common.mesh_object(f"{n}_Cables_Piping", cab, col, black, root, smooth=False)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    ix_common.tag_emissive(root)   # interactivity: glowing parts follow the room's light switch
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
