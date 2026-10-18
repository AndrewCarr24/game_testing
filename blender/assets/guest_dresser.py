"""Guest dresser: a long low pale-oak chest on a recessed black plinth, six flat
drawer fronts split by reveal gaps, with slim brass pulls. Faces -Y, origin is the
floor centre. Drawers are fixed (closed)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestDresser"

P = dict(name=NAME, size=(1.6, 0.46, 0.80), plinth_h=0.10, gap=0.005, cols=3, rows=2)


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
    A(own, "Plinth", common.box_bmesh((W - 0.12, D - 0.10, ph + 0.01)), black, (0, 0.01, (ph + 0.01) / 2), 0)
    top_t = 0.035
    A(own, "Top", common.box_bmesh((W, D, top_t)), oak, (0, 0, H - top_t / 2), 0.004)
    body_h = H - top_t - ph
    A(own, "Carcass", common.box_bmesh((W - 0.03, D - 0.03, body_h)), oak, (0, 0.0, ph + body_h / 2), 0.003)
    cols, rows = p["cols"], p["rows"]
    fw = (W - 0.03 - g * (cols + 1)) / cols
    fh = (body_h - 0.01 - g * (rows + 1)) / rows
    y = -D / 2 + 0.015 - 0.01
    for r in range(rows):
        for c in range(cols):
            x = -(W - 0.03) / 2 + g + fw / 2 + c * (fw + g)
            z = ph + 0.005 + g + fh / 2 + r * (fh + g)
            A(own, f"Front_{r}{c}", common.box_bmesh((fw, 0.02, fh)), oak, (x, y - 0.0, z), 0.002)
            if r == rows - 1:
                pz = z + fh / 2 - 0.05
            else:
                pz = z + fh / 2 - 0.05
            pull = common.mesh_object(f"{n}_Pull_{r}{c}", common.box_bmesh((0.16, 0.012, 0.012)), col, brass, root)
            pull.location = (x, y - 0.014, pz)
            common.add_bevel(pull, 0.003, segments=2)
    parts = guest_mats.consolidate(root, max_dim=0.6)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
