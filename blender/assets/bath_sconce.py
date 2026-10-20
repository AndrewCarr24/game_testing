"""Wall sconce: a slim brass backplate and a vertical alabaster light bar (emissive,
rounded ends in brass caps). Origin: centre of the sconce on the wall plane; the back
is at y = 0 and it stands out toward -Y. Hang it with a z in PLACEMENTS (about 1.65).
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import bath_common as bc  # noqa: E402

importlib.reload(common)
importlib.reload(bc)

NAME = "BathSconce"

P = dict(name=NAME, height=0.34, radius=0.026, stand_off=0.05, plate=(0.05, 0.40, 0.010), emission=2.6)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402  (react definitions, prompts/interactivity.md)

importlib.reload(ix_common)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    brass = bc.brass()
    shade = materials.emissive("M_Bath_Alabaster", (1.0, 0.84, 0.62), p["emission"])

    h, r, so = p["height"], p["radius"], p["stand_off"]
    pw, ph, pd = p["plate"]
    bc.box(col, root, f"{n}_Plate", (pw, pd, ph), (0, -pd / 2, 0), brass, bevel=0.0035)
    # light bar: lathed about Z, rotated upright in place (axis is Z already)
    cy = -so - r * 0.2
    prof = [(0.0, -h / 2), (r * 0.9, -h / 2), (r, -h / 2 + 0.012), (r, h / 2 - 0.012), (r * 0.9, h / 2), (0.0, h / 2)]
    bar = common.mesh_object(f"{n}_Light", bc.lathe(prof, 24), col, shade, root)
    bar.location = (0, cy, 0)
    # brass caps and two short arms from the plate to the bar
    for sgn, tag in ((1, "Top"), (-1, "Bottom")):
        cap = bc.lathe([(0.0, 0.0), (r * 1.04, 0.0), (r * 1.04, 0.012), (r * 0.8, 0.016), (0.0, 0.016)], 24)
        c = common.mesh_object(f"{n}_Cap{tag}", cap, col, brass, root)
        if sgn > 0:
            c.location = (0, cy, h / 2 - 0.004)
        else:
            c.rotation_euler = (math.pi, 0, 0)
            c.location = (0, cy, -h / 2 + 0.004)
        import bmesh
        arm = bmesh.new()
        bc.cylinder_between(arm, (0, -pd, sgn * (h / 2 - 0.03)), (0, cy, sgn * (h / 2 - 0.03)), 0.006, 10)
        common.mesh_object(f"{n}_Arm{tag}", arm, col, brass, root)
    bc.merge(root, bc.by_material(root, brass), f"{n}_PipingBrass")
    ix_common.tag_emissive(root)   # interactivity: glowing parts follow the room's light switch
    return root, bc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
