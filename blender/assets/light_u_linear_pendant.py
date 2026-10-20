"""Linear pendant for the library's reading table: a long, slim bronze bar with softened
edges, an opal diffuser strip along its underside (light down onto the table) and a narrower
one along its top (uplight that washes the ceiling), hung on two fine bronze cables from two
small round ceiling canopies.

Origin: the centre of the diffuser's underside (z = 0); long axis along X. `ceiling` is the
distance from the origin up to the ceiling: place it at z = ceiling height - P["ceiling"]
(library: 3.8 - 2.15 -> z = 1.65, 0.89 m above the 0.76 m table). The room module puts an
`area` light just under it (down) and one just over it (up). Units are metres.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitchen_lib as L  # noqa: E402

importlib.reload(L)
common, materials = L.common, L.materials

NAME = "LightULinearPendant"

P = dict(
    name=NAME,
    length=2.4,
    width=0.10,          # bar depth (y)
    height=0.055,        # bar height (z), above the diffuser
    lens=0.006,          # diffuser strip thickness (stands proud of the bar's underside)
    up_lens=0.004,
    ceiling=2.15,        # origin -> ceiling
    cable_x=0.85,        # cables at +-cable_x
    emission=5.0,
)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402  (react definitions, prompts/interactivity.md)

importlib.reload(ix_common)


def build(**overrides):
    p = {**P, **overrides}
    b = L.Builder(p["name"])
    bronze = materials.bronze()
    glow = materials.emissive("M_LightU_Opal", (1.0, 0.84, 0.64), p["emission"])
    Lb, W, H, t, tu = p["length"], p["width"], p["height"], p["lens"], p["up_lens"]

    # the bar: a softly bevelled bronze extrusion sitting on the diffuser
    b.box("Bar_NoCollide", (Lb, W, H), (0, 0, t + H / 2), bronze, bevel=0.012, seg=2, tile=0.3)
    # opal diffuser underneath (inset from the ends and sides), uplight lens on top
    b.box("Diffuser_NoCollide", (Lb - 0.05, W - 0.026, t + 0.004), (0, 0, (t + 0.004) / 2), glow, bevel=0.0015, tile=0)
    zt = t + H
    b.box("Uplight_NoCollide", (Lb - 0.08, W * 0.36, tu + 0.004), (0, 0, zt - 0.002 + (tu + 0.004) / 2), glow, bevel=0.0, tile=0)

    # cables and canopies
    top = p["ceiling"]
    for i, x in enumerate((-p["cable_x"], p["cable_x"])):
        b.tube(f"Cable{i}_Piping", [(x, 0, zt + tu), (x, 0, top - 0.02)], 0.0022, bronze, closed=False, res=1)
        b.lathe(f"Canopy{i}", [(0.0, top - 0.024), (0.034, top - 0.024), (0.04, top - 0.016), (0.04, top + 0.002),
                               (0.0, top + 0.002)], bronze, loc=(x, 0, 0), segs=16, sharp=30, uv_tile=0.3)
        # the cable's grip on the bar
        b.lathe(f"Grip{i}_Piping", [(0.0, zt + tu - 0.002), (0.008, zt + tu - 0.002), (0.008, zt + tu + 0.018),
                                    (0.004, zt + tu + 0.024), (0.0, zt + tu + 0.024)], bronze, loc=(x, 0, 0), segs=10,
                uv_tile=0.3)
    ix_common.tag_emissive(b.root)   # interactivity: glowing parts follow the room's light switch
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
