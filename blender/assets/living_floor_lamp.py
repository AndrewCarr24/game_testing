"""Arc floor lamp: a weighted white-marble block, a slim bronze stem that rises and
bends out over a seating group, and a glowing linen dome shade on a bronze collar.
The shade hangs about 1.35 m in front (-Y) of the base and 1.7 m above the floor.
Origin: floor centre of the base block. Units are metres.
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import living_side_table  # noqa: E402
from lib import common, materials, textures  # noqa: E402

importlib.reload(living_side_table)
lathe = living_side_table.lathe

NAME = "LivingFloorLamp"

P = dict(
    name=NAME,
    base=(0.46, 0.28, 0.17),
    stem_r=0.012,
    rise=1.15,            # straight height before the bend
    arc_r=0.95,
    arc_deg=118.0,
    shade_r=0.25,
    shade_h=0.24,
    glow=2.5,
)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402  (react definitions, prompts/interactivity.md)

importlib.reload(ix_common)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    marble = common.pbr_material("M_Marble_White", (0.8, 0.79, 0.77), roughness=0.12)
    common.set_base_color_map(marble, textures.load(textures.marble()))
    bronze = materials.bronze()
    glow = materials.emissive("M_Living_LampGlow", (1.0, 0.78, 0.50), p["glow"])

    bx, by, bz = p["base"]
    pad = 0.006   # the block floats on a recessed black felt pad (a shadow line at the floor)
    base = common.mesh_object(f"{n}_Base", common.box_bmesh((bx, by, bz - pad)), col, marble, root, smooth=False)
    base.location = (0, 0, pad + (bz - pad) / 2)
    felt = common.mesh_object(f"{n}_Pad", common.box_bmesh((bx - 0.03, by - 0.03, pad)), col, materials.black_metal(),
                              root, smooth=False)
    felt.location = (0, 0, pad / 2)
    common.box_uv(felt, 0.5)
    common.add_bevel(base, 0.012, segments=3)
    common.box_uv(base, 1.0)

    z0 = bz - 0.01
    z1 = p["rise"]
    R = p["arc_r"]
    riser = [(0, 0, z0), (0, 0, z1)]
    pts = [(0, 0, z1)]
    steps = 28
    th_max = math.radians(p["arc_deg"])
    for i in range(1, steps + 1):
        th = th_max * i / steps
        pts.append((0, -R + R * math.cos(th), z1 + R * math.sin(th)))
    # the riser is solid, the arc / shade hang overhead and never block the player
    riser_ob = common.tube_object(f"{n}_Riser", riser, p["stem_r"], col, bronze, root, closed=False, profile_res=2)
    stem = common.tube_object(f"{n}_ArcNoCollide", pts, p["stem_r"], col, bronze, root, closed=False, profile_res=2)
    # bronze collars: where the stem leaves the marble, and at the riser/arc joint
    for k, (zc, h_, rr) in enumerate(((bz, 0.02, 0.022), (z1 - 0.03, 0.05, 0.017))):
        cl = common.mesh_object(f"{n}_Collar{k}", lathe([(0.0, zc), (rr, zc), (rr, zc + h_ - 0.004),
                                                          (rr - 0.004, zc + h_), (0.0, zc + h_)], 16),
                                col, bronze, root)
        common.box_uv(cl, 0.5)
    end = pts[-1]
    # shade hangs from the end of the arc on a short collar
    sh_top = end[2] - 0.015
    sr, sh = p["shade_r"], p["shade_h"]
    collar = common.mesh_object(
        f"{n}_CollarNoCollide", lathe([(0, sh_top + 0.04), (0.018, sh_top + 0.04), (0.02, sh_top), (0.0, sh_top)], 16),
        col, bronze, root)
    collar.location = (0, end[1], 0)
    # dome: lathe a quarter-ellipse profile, wall as one glowing closed shell
    prof = [(0.0, sh_top)]
    for k in range(1, 9):
        a = math.pi / 2 * k / 8
        prof.append((sr * math.sin(a), sh_top - sh * (1 - math.cos(a))))
    prof.append((sr - 0.004, sh_top - sh))
    prof.append((0.0, sh_top - sh))
    dome = common.mesh_object(f"{n}_ShadeNoCollide", lathe(prof, 40), col, glow, root)
    dome.location = (0, end[1], 0)
    common.box_uv(dome, 0.5)
    rim = common.mesh_object(f"{n}_RimNoCollide", lathe([(sr - 0.012, sh_top - sh - 0.004), (sr + 0.002, sh_top - sh - 0.004),
                                                (sr + 0.002, sh_top - sh + 0.006), (sr - 0.012, sh_top - sh + 0.006)], 40),
                             col, bronze, root)
    rim.location = (0, end[1], 0)
    for ob in (riser_ob, stem, collar, rim):
        common.box_uv(ob, 0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    ix_common.tag_emissive(root)   # interactivity: glowing parts follow the room's light switch
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
