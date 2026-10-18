"""Guest bench for the foot of the bed: a long linen-upholstered cushion on a slim
pale-oak frame with four tapered legs. Long axis along X, front faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestBench"

P = dict(name=NAME, width=1.35, depth=0.42, height=0.44, cushion_t=0.10)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    oak, linen = guest_mats.oak(), guest_mats.linen()
    own = (col, root, n)
    A = guest_mats.add
    W, D, H, ct = p["width"], p["depth"], p["height"], p["cushion_t"]
    fh = 0.07
    ztop = H - ct
    A(own, "Frame", common.box_bmesh((W - 0.04, D - 0.04, fh)), oak, (0, 0, ztop - fh / 2), 0.004)
    for fx, fy, nm in ((-1, -1, "FL"), (1, -1, "FR"), (-1, 1, "BL"), (1, 1, "BR")):
        A(own, f"Leg_{nm}", guest_mats.taper_bmesh(0.045, 0.028, ztop - fh), oak,
          (fx * (W / 2 - 0.06), fy * (D / 2 - 0.06), (ztop - fh) / 2), 0.002)
    cu = common.mesh_object(f"{n}_Cushion", common.cushion_bmesh((W, D, ct), cuts=5, edge=0.03,
                            crown={"+z": 0.018, "+x": 0.004, "-x": 0.004}), col, linen, root)
    cu.location = (0, 0, ztop + ct / 2)
    common.add_subsurf(cu)
    common.box_uv(cu, 0.25)
    return root, [o for o in root.children_recursive if o.type == "MESH"]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
