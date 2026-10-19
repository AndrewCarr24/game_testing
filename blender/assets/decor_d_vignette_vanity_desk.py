"""Writing desk / dressing table vignette (primary bedroom, guest_desk 1.45 x 0.68 at
0.74 m, placed at the desk's centre with the desk's rotation; its lamp stands at local
(+0.55, +0.05)): a bronze tray of three perfume bottles at the back left, an ink notebook
with a pen in front of the chair, and two books under the lamp with a small bud vase."""
import importlib
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_d_kit as kit  # noqa: E402

importlib.reload(kit)

NAME = "DecorD_Vignette_VanityDesk"
P = dict(name=NAME, seed=11, palette="ink")


def build(**overrides):
    p = {**P, **overrides}
    rng = random.Random(p["seed"])
    pal = kit.PALETTES[p["palette"]]
    B = kit.Builder(p["name"])
    # tray of scent bottles, back left
    tx, ty = -0.40, 0.13
    b = kit.tray(B, kit.at(tx, ty, 0.0, 3), pal["metal"], w=0.30, d=0.17, h=0.022, r=0.025, wall=0.004, base=0.004)
    kit.perfume(B, kit.at(tx - 0.08, ty + 0.025, b, 3), w=0.055, d=0.04, h=0.10, cap="bronze", cap_h=0.032)
    kit.perfume(B, kit.at(tx + 0.0, ty + 0.03, b, 10), w=0.045, d=0.032, h=0.07, cap="bronze", cap_h=0.026)
    kit.perfume(B, kit.at(tx + 0.075, ty - 0.02, b, -6), w=0.06, d=0.03, h=0.055, cap="charcoal", cap_h=0.02)
    # notebook and pen in front of the chair
    kit.notebook(B, kit.at(-0.02, -0.12, 0.0, 84), w=0.15, d=0.21, t=0.014, cover="ink")
    kit.pen(B, kit.at(0.13, -0.13, 0.0, 78), pal["metal"])
    # two books beside the lamp, a bud vase on them
    z = kit.book_stack(B, kit.at(0.22, 0.10, 0.0, -6), rng, 2, ["oat", "stone_fabric"],
                       sizes=[(0.24, 0.30), (0.21, 0.27)], thick=(0.026, 0.036), spin=3, fixed=True)
    h = kit.vessel(B, kit.at(0.20, 0.12, z), "marble", "bud", h=0.13, r=0.036, segs=14)
    kit.stem_sprig(B, kit.at(0.20, 0.12, z + h), rng, h=0.22, leaves=7)
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(NAME, kit.common.triangle_count(parts))
