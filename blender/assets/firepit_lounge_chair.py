"""Deep outdoor lounge chair: sand cushions in a chunky teak frame (solid side arms, raked
back panel) on a recessed black plinth. Front faces -Y. Origin: floor centre. Metres."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import firepit_common as fc  # noqa: E402

importlib.reload(fc)
common, outdoor = fc.common, fc.outdoor

NAME = "FirepitLoungeChair"
P = dict(
    name=NAME,
    width=0.84,
    depth=0.86,
    arm_t=0.07,
    arm_h=0.56,
    seat_top=0.42,
    back_tilt=-17.0,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = fc.new_asset(n)
    W, D, at, ah = p["width"], p["depth"], p["arm_t"], p["arm_h"]
    teak, dark, sand = outdoor.teak(), outdoor.dark_metal(), fc.sand_cushion()
    tilt = p["back_tilt"]

    # black recessed plinth: reads as a shadow gap under the seat
    fc.box(f"{n}_Plinth", (W - 2 * at - 0.02, D - 0.14, 0.16), (0, 0.0, 0.08), dark, col, root)
    # teak side arms (solid panels, set 4 cm up on the plinth line)
    fc.merge_boxes(f"{n}_Arms",
                   [((at, D, ah - 0.04), (sx * (W / 2 - at / 2), 0, 0.04 + (ah - 0.04) / 2), (0, 0, 0), 0)
                    for sx in (-1, 1)], teak, col, root, uv_tile=0.5)
    # raked back panel between the arms
    fc.box(f"{n}_BackPanel", (W - 2 * at - 0.01, 0.04, 0.58), (0, D / 2 - 0.10, 0.50), teak, col, root,
           rot=(tilt, 0, 0), uv_tile=0.5)
    # cushions
    sw = W - 2 * at - 0.02
    fc.box(f"{n}_Seat", (sw, D - 0.30, 0.16), (0, -0.07, p["seat_top"] - 0.08), sand, col, root, bevel=0.03)
    fc.box(f"{n}_BackCushion", (sw, 0.15, 0.46), (0, D / 2 - 0.20, 0.64 - 0.02), sand, col, root,
           rot=(tilt, 0, 0), bevel=0.03)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts
