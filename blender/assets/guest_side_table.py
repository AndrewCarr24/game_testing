"""Guest side table: a round pale-oak top with an undercut, eased edge and an inlaid
brass ring beneath, on a slim tapering oak pedestal with brass collars, standing on
a wide chamfered oak foot disc with a black glide ring. Origin is the floor centre."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402
import guest_wardrobe  # noqa: E402

importlib.reload(guest_mats)
importlib.reload(guest_wardrobe)
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
    tr, sr, fr = p["top_r"], p["stem_r"], p["foot_r"]
    # top: undercut edge (narrower underneath) with eased arrises
    A(own, "Top", guest_mats.cyl_bmesh(tr - 0.012, T, r2=tr, seg=48), oak, (0, 0, H - T / 2), 0.004)
    A(own, "Ring", guest_mats.cyl_bmesh(tr - 0.03, 0.006, seg=40), brass, (0, 0, H - T - 0.003), 0)
    # stem swelling slightly toward the foot, brass collars where it meets top and foot
    A(own, "Stem", guest_mats.cyl_bmesh(sr, H - T - FT - 0.02, r2=sr * 0.8, seg=24), oak,
      (0, 0, FT + 0.008 + (H - T - FT - 0.02) / 2), 0.002)
    A(own, "CollarTop", guest_mats.cyl_bmesh(sr * 0.8 + 0.006, 0.012, seg=24), brass, (0, 0, H - T - 0.006 - 0.006), 0)
    A(own, "CollarFoot", guest_mats.cyl_bmesh(sr + 0.006, 0.008, seg=24), brass, (0, 0, FT + 0.004), 0)
    # foot disc: chamfered top edge, black felt glide ring underneath
    A(own, "Foot", guest_mats.cyl_bmesh(fr, FT, r2=fr - 0.01, seg=40), oak, (0, 0, FT / 2 + 0.002), 0.003)
    A(own, "FootRing", guest_mats.cyl_bmesh(fr - 0.012, 0.004, seg=40), black, (0, 0, 0.002), 0)
    guest_wardrobe.fix_oak(root)
    return root, [o for o in root.children_recursive if o.type == "MESH"]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
