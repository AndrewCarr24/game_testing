"""Exercise mats: a sage yoga mat and an oat mat laid slightly offset (flat), a
rolled mat, a foam roller and a folded towel on top. Mats are 1.85 x 0.62 m; the
whole set occupies about 1.9 x 1.3 m. Origin is the floor centre."""
import importlib
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestMat"

P = dict(name=NAME)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rub = guest_mats.rubber()
    sage = common.pbr_material("M_Mat_Sage", (0.17, 0.25, 0.15), roughness=0.75)
    oat = common.pbr_material("M_Mat_Oat", (0.50, 0.45, 0.37), roughness=0.75)
    towel = guest_mats.linen()
    own = (col, root, n)
    A = guest_mats.add
    t = 0.012
    A(own, "MatA", common.rounded_slab_bmesh(1.85, 0.62, t, 0.02), sage, (0.0, -0.32, t / 2), 0.003, tile=0.5)
    A(own, "MatB", common.rounded_slab_bmesh(1.85, 0.62, t, 0.02), oat, (0.06, 0.34, t / 2), 0.003, tile=0.5)
    # rolled mat leaning at one end: a spiral of two cylinders (core + roll)
    roll = common.mesh_object(f"{n}_Roll", guest_mats.cyl_bmesh(0.085, 0.62, seg=28, axis="y"), col, sage, root)
    roll.location = (0.72, -0.32, 0.012 + 0.085)
    common.box_uv(roll, 0.5)
    core = common.mesh_object(f"{n}_RollCore", guest_mats.cyl_bmesh(0.03, 0.625, seg=12, axis="y"), col, oat, root)
    core.location = roll.location
    common.box_uv(core, 0.5)
    # foam roller
    fr = common.mesh_object(f"{n}_FoamRoller", guest_mats.cyl_bmesh(0.075, 0.45, seg=28, axis="x"), col, rub, root)
    fr.location = (-0.5, 0.35, t + 0.075)
    common.box_uv(fr, 0.5)
    parts = guest_mats.consolidate(root, max_dim=0.2)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
