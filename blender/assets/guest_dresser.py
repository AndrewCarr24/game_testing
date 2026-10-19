"""Guest dresser: a long low pale-oak chest on a recessed black plinth. A solid top
with eased edges overhangs a carcass of thick sides; six drawer fronts sit flush
inset between them with 3 mm reveals (a dark backer behind the gaps), each with a
slim brass bar pull on round stand-offs. Faces -Y, origin is the floor centre.
Drawers are fixed (closed)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402
import guest_wardrobe  # noqa: E402

importlib.reload(guest_mats)
importlib.reload(guest_wardrobe)
common = guest_mats.common

NAME = "GuestDresser"

P = dict(name=NAME, size=(1.6, 0.46, 0.80), plinth_h=0.10, gap=0.003, cols=3, rows=2)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    oak, brass, black = guest_mats.oak(), guest_mats.brass(), guest_mats.black()
    own = (col, root, n)
    A = guest_mats.add
    W, D, H = p["size"]
    ph, g = p["plinth_h"], p["gap"]
    oh, top_t, st, bt = 0.012, 0.032, 0.024, 0.022     # top overhang, top, side and bottom thickness
    cw = W - 2 * oh
    y_f = -D / 2 + oh                                   # carcass / drawer front plane
    y_b = D / 2 - 0.004
    cd = y_b - y_f

    A(own, "Plinth", common.box_bmesh((W - 0.12, D - 0.10, ph + 0.01)), black, (0, 0.01, (ph + 0.01) / 2), 0)
    A(own, "Top", common.box_bmesh((W, D, top_t)), oak, (0, 0, H - top_t / 2), 0.005)
    z_top = H - top_t
    for s, sx in (("L", -1), ("R", 1)):
        A(own, f"Side_{s}", common.box_bmesh((st, cd, z_top - ph)), oak, (sx * (cw - st) / 2, y_f + cd / 2,
                                                                          (ph + z_top) / 2), 0.002)
    A(own, "Bottom", common.box_bmesh((cw - 2 * st, cd, bt)), oak, (0, y_f + cd / 2, ph + bt / 2), 0.002)
    A(own, "Back", common.box_bmesh((cw - 2 * st, 0.012, z_top - ph - bt)), oak,
      (0, y_b - 0.006, (ph + bt + z_top) / 2), 0)
    # dark backer seen through the reveals
    ox0, ox1 = -cw / 2 + st, cw / 2 - st
    oz0, oz1 = ph + bt, z_top
    A(own, "Backer", common.box_bmesh((ox1 - ox0, 0.004, oz1 - oz0)), black, (0, y_f + 0.024, (oz0 + oz1) / 2), 0)

    cols, rows = p["cols"], p["rows"]
    fw = (ox1 - ox0 - g * (cols + 1)) / cols
    fh = (oz1 - oz0 - g * (rows + 1)) / rows
    ft = 0.02
    pr, stand, pw = 0.0048, 0.024, 0.16
    for r in range(rows):
        for c in range(cols):
            x = ox0 + g + fw / 2 + c * (fw + g)
            z = oz0 + g + fh / 2 + r * (fh + g)
            A(own, f"Front_{r}{c}", common.box_bmesh((fw, ft, fh)), oak, (x, y_f + ft / 2, z), 0.002)
            pz = z + fh / 2 - 0.055
            pts = common.fillet_polyline([(x - pw / 2, y_f, pz), (x - pw / 2, y_f - stand, pz),
                                          (x + pw / 2, y_f - stand, pz), (x + pw / 2, y_f, pz)],
                                         0.010, segments=4, closed=False)
            common.tube_object(f"{n}_Pull_{r}{c}", pts, pr, col, brass, root, closed=False, profile_res=2)
    guest_wardrobe.fix_oak(root)
    parts = guest_mats.consolidate(root, max_dim=0.6)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
