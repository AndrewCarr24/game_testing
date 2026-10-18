"""Walnut credenza: a long low cabinet with four doors with vertical grain and slim
bronze pulls, on a recessed black plinth, with a solid top that overhangs a little.
Origin: floor centre; the doors face -Y. 2.4 x 0.5 x 0.78 m."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import library_kit as kit  # noqa: E402
from library_kit import Mesh, common, materials  # noqa: E402

importlib.reload(kit)

NAME = "LibraryCredenza"

P = dict(name=NAME, size=(2.4, 0.5, 0.78), doors=4, top_t=0.04, plinth_h=0.09)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    walnut, bronze, black = materials.walnut(), materials.bronze(), materials.black_metal()
    W, D, H = p["size"]
    tt, ph, nd = p["top_t"], p["plinth_h"], p["doors"]
    wood, brz, blk = Mesh(0.5), Mesh(0.5), Mesh(0.5)
    ins = 0.012
    cw = W - 2 * ins
    wood.box((0, 0, H - tt / 2), (W, D, tt), shift=(0.1, 0.2))
    side_t = 0.03
    ch = H - tt - ph
    for sx in (-1, 1):
        wood.box((sx * (cw - side_t) / 2, 0, ph + ch / 2), (side_t, D - 2 * ins, ch), shift=(0.3 * sx, 0.1))
    wood.box((0, 0, ph + 0.015), (cw, D - 2 * ins, 0.03), shift=(0.5, 0.3))
    wood.box((0, D / 2 - ins - 0.006, ph + ch / 2), (cw, 0.012, ch), shift=(0.2, 0.7))
    # dividers between pairs of doors
    for k in range(1, nd):
        x = -cw / 2 + k * cw / nd
        if k == nd // 2:
            wood.box((x, 0, ph + ch / 2), (0.03, D - 2 * ins - 0.01, ch), shift=(0.1 * k, 0.6))
    blk.box((0, -0.02, ph / 2), (cw - 0.06, D - 2 * ins - 0.06, ph))
    # dark interior seen through the reveals
    blk.box((0, -D / 2 + 0.04, ph + ch / 2), (cw - 2 * side_t, 0.004, ch - 0.01))
    dt, g = 0.02, 0.003
    dw = (cw - 2 * side_t - 0.03 - (nd + 1) * g) / nd if nd % 2 == 0 else (cw - 2 * side_t - (nd + 1) * g) / nd
    x0 = -cw / 2 + side_t + g
    for k in range(nd):
        x = x0 + k * (dw + g) + (0.03 + g if k >= nd // 2 and nd % 2 == 0 else 0) + dw / 2
        wood.box((x, -D / 2 + ins + dt / 2, ph + ch / 2), (dw, dt, ch - 2 * g - 0.002), shift=(0.37 * k, 0.17 * k))
        side = 1 if k % 2 == 0 else -1          # pull on the inner edge of each pair
        px = x + side * (dw / 2 - 0.04)
        brz.box((px, -D / 2 + ins - 0.008, ph + ch / 2), (0.011, 0.014, 0.26))
    w = wood.to_object(f"{n}_Wood", col, walnut, root)
    common.add_bevel(w, 0.003, segments=2)
    brz.to_object(f"{n}_Pulls", col, bronze, root)
    blk.to_object(f"{n}_Plinth", col, black, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
