"""Scullery prep table: a 2.2 x 0.9 m end-grain walnut butcher block on a blackened
steel frame with a brushed-steel lower shelf (baskets, folded towels), set with a
chopping board, a bowl of lemons and a knife block. Long axis along X, 0.92 m high.
Origin is the floor centre."""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitchen_lib as L  # noqa: E402

importlib.reload(L)
common, materials = L.common, L.materials

NAME = "KitchenPrepTable"

P = dict(
    name=NAME,
    size=(1.8, 0.9),
    height=0.92,
    top_t=0.075,
    leg=0.05,
    shelf_z=0.24,
)


def build(**overrides):
    p = {**P, **overrides}
    b = L.Builder(p["name"])
    walnut = materials.walnut()
    dark = materials.black_metal()
    steel = L.brushed_steel()
    oak = materials.smoked_oak()
    linen = L.cream_fabric()
    linen2 = materials.fabric("M_Fabric_Stone", (0.16, 0.15, 0.14))
    wicker = common.pbr_material("M_Wicker", (0.30, 0.21, 0.12), roughness=0.95)
    cer = L.ceramic()
    lemon = common.pbr_material("M_Lemon", (0.75, 0.55, 0.03), roughness=0.5)
    lime = common.pbr_material("M_Lime", (0.12, 0.30, 0.03), roughness=0.5)

    W, D = p["size"]
    h, tt, lg = p["height"], p["top_t"], p["leg"]
    # block top: three glued-up strips so the grain direction changes slightly
    strip = D / 3
    for i in range(3):
        b.box(f"Top{i}", (W, strip - 0.002, tt), (0, -D / 2 + strip * (i + 0.5), h - tt / 2), walnut, bevel=0.003, seg=1,
              tile=0.5, shift=(0.21 * i, 0.37 * i))
    # frame: legs, aprons under the top, lower shelf rails
    lx, ly = W / 2 - 0.1, D / 2 - 0.08
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        b.box(f"Leg{i}", (lg, lg, h - tt), (sx * lx, sy * ly, (h - tt) / 2), dark, bevel=0.003, tile=0)
    for tag, size, c in (("ApronF", (2 * lx, 0.03, 0.06), (0, -ly, h - tt - 0.03)),
                         ("ApronB", (2 * lx, 0.03, 0.06), (0, ly, h - tt - 0.03)),
                         ("ApronL", (0.03, 2 * ly, 0.06), (-lx, 0, h - tt - 0.03)),
                         ("ApronR", (0.03, 2 * ly, 0.06), (lx, 0, h - tt - 0.03))):
        b.box(tag, size, c, dark, bevel=0.002, tile=0)
    sz = p["shelf_z"]
    b.box("Shelf", (2 * lx, 2 * ly, 0.02), (0, 0, sz), steel, bevel=0.003, tile=0)
    for tag, size, c in (("RailF", (2 * lx, 0.025, 0.04), (0, -ly, sz - 0.02)),
                         ("RailB", (2 * lx, 0.025, 0.04), (0, ly, sz - 0.02)),
                         ("RailL", (0.025, 2 * ly, 0.04), (-lx, 0, sz - 0.02)),
                         ("RailR", (0.025, 2 * ly, 0.04), (lx, 0, sz - 0.02))):
        b.box(tag, size, c, dark, bevel=0.002, tile=0)

    # lower shelf (x within +-lx = 0.8, between the legs): baskets and towels
    for i, bx in enumerate((-0.6, -0.25)):
        br = 0.15
        prof = [(0.0, 0.0), (br * 0.85, 0.0), (br, 0.18), (br - 0.006, 0.18), (br * 0.85 - 0.006, 0.01), (0.0, 0.01)]
        b.lathe(f"Basket{i}", prof, wicker, loc=(bx, 0.0, sz + 0.01), segs=14, sharp=70, uv_tile=0.3)
    for k, (tx, ty) in enumerate(((0.12, 0.0), (0.55, 0.0))):
        L.folded_stack(b, f"Towels{k}", tx, ty, sz + 0.01, 0.36, 0.26, 6, 0.036, linen if k == 0 else linen2)

    # on the block
    zt = h
    b.box("Board", (0.55, 0.32, 0.03), (-0.55, -0.12, zt + 0.015), oak, bevel=0.006, seg=2, tile=0.5, shift=(0.5, 0.2))
    L.fruit_bowl(b, (0.55, 0.12, zt), cer, lemon, lime, r=0.19)
    # knife block
    b.box("KnifeBlock", (0.12, 0.1, 0.24), (0.0, 0.28, zt + 0.12), oak, bevel=0.004, seg=1, tile=0.5)
    for k in range(3):
        b.box(f"Knife{k}", (0.02, 0.022, 0.07), (-0.035 + k * 0.035, 0.28, zt + 0.275), dark, bevel=0.002, tile=0)
    # a salt cellar and an oil bottle
    b.lathe("Oil", [(0, 0), (0.035, 0), (0.035, 0.2), (0.012, 0.25), (0.012, 0.31), (0, 0.31)],
            materials.glass("M_Glass_Olive", (0.2, 0.28, 0.1), 0.55), loc=(0.2, 0.3, zt), segs=14, uv_tile=0)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
