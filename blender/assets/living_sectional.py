"""Deep media-room sectional: a long run with a chaise on the right, built from the
living_sofa upholstery modules in a warm mushroom velvet, with a left arm, scatter
pillows and a recessed black plinth. Faces -Y; origin is the floor centre of the
bounding rectangle (run width x run + chaise depth).
"""
import importlib
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import living_sofa  # noqa: E402

importlib.reload(living_sofa)
common, materials = living_sofa.common, living_sofa.materials

NAME = "LivingSectional"

P = dict(
    living_sofa.P,
    name=NAME,
    width=4.60,            # run length
    depth=1.12,            # run depth
    chaise_w=1.05,
    chaise_len=1.15,       # how far the chaise projects forward of the run
    fabric_name="M_Fabric_Mushroom",
    fabric=(0.17, 0.13, 0.10),
    pillow_name="M_Fabric_Moss",
    pillow=(0.030, 0.050, 0.035),
    seat_t=0.21,
    deck_z=(0.07, 0.25),
    back_h=0.46,
    frame_back_top=0.62,
    arm_top=0.58,
    arm_w=0.22,
    back_tilt_deg=13.0,
    cuts=3,
    cuts_small=2,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    mat = materials.fabric(p["fabric_name"], p["fabric"])
    pmat = materials.fabric(p["pillow_name"], p["pillow"])
    w, d, cw, cl = p["width"], p["depth"], p["chaise_w"], p["chaise_len"]
    total_d = d + cl
    # local frame: back wall at +total_d/2; run occupies the back strip
    y_back = total_d / 2
    run_y0 = y_back - d
    x0, x1 = -w / 2, w / 2
    living_sofa.module(p, col, root, mat, pmat, n, x0, x1 - cw, run_y0, y_back, back=True,
                       arms={"L": (run_y0, y_back)}, tag="Run", seat_w=1.15)
    # chaise: low, no back, with the right arm running the full depth
    living_sofa.module(p, col, root, mat, pmat, n, x1 - cw, x1, -total_d / 2, y_back, back=True,
                       arms={"R": (-total_d / 2, y_back)}, tag="Chaise", seat_w=1.4)
    z_seat = p["deck_z"][1] + p["seat_t"]
    for i, (px, rz) in enumerate(((x0 + p["arm_w"] + 0.32, -8), (x0 + p["arm_w"] + 0.95, 6),
                                  (x1 - cw - 0.38, -5))):
        living_sofa.pillow(col, root, pmat if i != 1 else materials.fabric("M_Fabric_Cognac", (0.20, 0.085, 0.035)),
                           f"{n}_Pillow{i}", (px, run_y0 + d / 2 - 0.14, z_seat + 0.21),
                           (-math.radians(12), 0, math.radians(rz)), size=0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
