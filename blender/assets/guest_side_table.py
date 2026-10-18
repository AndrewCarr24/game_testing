"""Guest side table: a round pale-oak top on a slim oak pedestal and a wide, thin
brass-edged foot disc. Origin is the floor centre."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestSideTable"

P = dict(name=NAME, top_r=0.26, height=0.50, top_t=0.03, stem_r=0.045, foot_r=0.19, foot_t=0.02)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    oak, brass, black = guest_mats.oak(), guest_mats.brass(), guest_mats.black()
    own = (col, root, n)
    A = guest_mats.add
    H, T, FT = p["height"], p["top_t"], p["foot_t"]
    A(own, "Top", guest_mats.cyl_bmesh(p["top_r"], T, seg=48), oak, (0, 0, H - T / 2), 0.004)
    A(own, "Ring", guest_mats.cyl_bmesh(p["top_r"] - 0.012, 0.006, seg=48), brass, (0, 0, H - T - 0.003), 0)
    A(own, "Stem", guest_mats.cyl_bmesh(p["stem_r"], H - T - FT, r2=p["stem_r"] * 0.8, seg=24), oak,
      (0, 0, FT + (H - T - FT) / 2), 0.002)
    A(own, "Foot", guest_mats.cyl_bmesh(p["foot_r"], FT, seg=40), oak, (0, 0, FT / 2), 0.004)
    A(own, "FootRing", guest_mats.cyl_bmesh(p["foot_r"] - 0.01, 0.004, seg=40), black, (0, 0, 0.002), 0)
    return root, [o for o in root.children_recursive if o.type == "MESH"]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
