"""Guest floor lamp: weighted black disc, slim brass stem, glowing linen drum shade.
Origin is the floor centre; shade centre at z = 1.42 (put a point light there)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestFloorLamp"

P = dict(name=NAME, height=1.55, shade_r=0.21, shade_h=0.34)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    black, brass = guest_mats.black(), guest_mats.brass()
    shade_mat = guest_mats.materials.emissive("M_Lampshade_Linen", (0.95, 0.82, 0.62), 0.9)
    own = (col, root, n)
    A = guest_mats.add
    H, sr, sh = p["height"], p["shade_r"], p["shade_h"]
    A(own, "Base", guest_mats.cyl_bmesh(0.15, 0.025, r2=0.14, seg=40), black, (0, 0, 0.0125), 0.002)
    A(own, "Stem", guest_mats.cyl_bmesh(0.008, H - sh / 2 - 0.02, seg=12), brass, (0, 0, 0.025 + (H - sh / 2 - 0.045) / 2), 0)
    A(own, "Collar", guest_mats.cyl_bmesh(0.02, 0.03, seg=16), brass, (0, 0, H - sh / 2 - 0.03), 0)
    A(own, "Shade", guest_mats.cyl_bmesh(sr, sh, seg=40), shade_mat, (0, 0, H - sh / 2), 0, tile=0.25)
    A(own, "RimTop", guest_mats.cyl_bmesh(sr + 0.003, 0.008, seg=40), brass, (0, 0, H - 0.004), 0)
    A(own, "RimBottom", guest_mats.cyl_bmesh(sr + 0.003, 0.008, seg=40), brass, (0, 0, H - sh + 0.004), 0)
    parts = guest_mats.consolidate(root, max_dim=0.2)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
