"""Guest bench for the foot of the bed: a long piped linen box cushion with a soft
crown on a pale-oak frame: four tapered legs joined by aprons (set back from the
leg faces), a deck board under the cushion and a low stretcher. Long axis along X,
front faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402
import guest_wardrobe  # noqa: E402

importlib.reload(guest_mats)
importlib.reload(guest_wardrobe)
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
    crown = 0.016
    ztop = H - ct - crown * 0.7                   # top of the frame = underside of the cushion
    lw = 0.046                                    # leg section at the top
    lx, ly = W / 2 - 0.04 - lw / 2, D / 2 - 0.03 - lw / 2
    for fx, fy, nm in ((-1, -1, "FL"), (1, -1, "FR"), (-1, 1, "BL"), (1, 1, "BR")):
        A(own, f"Leg_{nm}", guest_mats.taper_bmesh(lw, 0.03, ztop), oak, (fx * lx, fy * ly, ztop / 2), 0.002)
    ah, at, aset = 0.07, 0.022, 0.006             # apron height, thickness, set-back from the leg face
    for nm, size, loc in (
            ("Apron_F", (2 * lx - lw, at, ah), (0, -ly - lw / 2 + aset + at / 2, ztop - ah / 2)),
            ("Apron_B", (2 * lx - lw, at, ah), (0, ly + lw / 2 - aset - at / 2, ztop - ah / 2)),
            ("Apron_L", (at, 2 * ly - lw, ah), (-lx - lw / 2 + aset + at / 2, 0, ztop - ah / 2)),
            ("Apron_R", (at, 2 * ly - lw, ah), (lx + lw / 2 - aset - at / 2, 0, ztop - ah / 2))):
        A(own, nm, common.box_bmesh(size), oak, loc, 0.0015)
    A(own, "Deck", common.box_bmesh((2 * lx + lw - 0.004, 2 * ly + lw - 0.004, 0.012)), oak,
      (0, 0, ztop - 0.006), 0.002)
    A(own, "Stretcher", common.box_bmesh((2 * lx - 0.03, 0.028, 0.022)), oak, (0, 0, 0.12), 0.002)
    for s, sx in (("L", -1), ("R", 1)):
        A(own, f"Rung_{s}", common.box_bmesh((0.022, 2 * ly - 0.03, 0.022)), oak, (sx * lx, 0, 0.12), 0.002)

    size = (W - 0.006, D - 0.006, ct)
    e = 0.03
    cu = common.mesh_object(f"{n}_Cushion", common.cushion_bmesh(size, cuts=4, edge=e,
                            crown={"+z": crown, "+x": 0.004, "-x": 0.004, "+y": 0.003, "-y": 0.003}),
                            col, linen, root)
    cu.location = (0, 0, ztop + ct / 2)
    common.add_subsurf(cu)
    common.box_uv(cu, 0.25)
    for i, pts in enumerate(common.piping_loop(size, "z", e / 6, e * 0.9)):
        pipe = common.tube_object(f"{n}_Cushion_Piping{i}", pts, 0.004, col, linen, cu, closed=True, profile_res=1)
        common.box_uv(pipe, 0.25)
    guest_wardrobe.fix_oak(root)
    return root, [o for o in root.children_recursive if o.type == "MESH"]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
