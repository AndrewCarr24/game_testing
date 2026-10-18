"""Guest wardrobe: a floor-to-near-ceiling run of reeded pale-oak doors (narrow
vertical slats over a sage carcass) with slim brass pull bars at the door joints and
a recessed black plinth. Faces -Y; origin is the floor centre."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestWardrobe"

P = dict(name=NAME, width=3.6, depth=0.62, height=2.7, plinth_h=0.09, doors=6, slat=0.032, slat_gap=0.008)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    oak, brass, black, sage = guest_mats.oak(), guest_mats.brass(), guest_mats.black(), guest_mats.sage()
    own = (col, root, n)
    A = guest_mats.add
    W, D, H, ph = p["width"], p["depth"], p["height"], p["plinth_h"]
    A(own, "Plinth", common.box_bmesh((W - 0.10, D - 0.08, ph + 0.01)), black, (0, 0.02, (ph + 0.01) / 2), 0)
    A(own, "Carcass", common.box_bmesh((W, D - 0.03, H - ph)), sage, (0, 0.015, ph + (H - ph) / 2), 0.003, tile=0.25)
    # reeded door faces: slats of a continuous grid, one door per bay, a gap between bays
    nd = p["doors"]
    bay = W / nd
    sl, sg = p["slat"], p["slat_gap"]
    pitch = sl + sg
    nslat = int((bay - 0.012) // pitch)
    fh = H - ph - 0.012
    y = -D / 2 + 0.0075
    import bmesh
    from mathutils import Matrix
    bm = bmesh.new()
    for d in range(nd):
        x0 = -W / 2 + d * bay + (bay - nslat * pitch + sg) / 2
        for s in range(nslat):
            x = x0 + s * pitch + sl / 2
            bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((x, y, ph + 0.006 + fh / 2))
                                  @ Matrix.Diagonal((sl, 0.022, fh, 1.0)))
    A(own, "Slats", bm, oak, (0, 0, 0), 0)
    # brass pull bars at the joints
    for d in range(nd):
        side = -1 if d % 2 == 0 else 1
        x = -W / 2 + d * bay + bay / 2 + side * (bay / 2 - 0.07)
        pull = common.mesh_object(f"{n}_Pull_{d}", common.box_bmesh((0.014, 0.014, 0.5)), col, brass, root)
        pull.location = (x, -D / 2 - 0.012, 1.15)
        common.add_bevel(pull, 0.004, segments=2)
    return root, [o for o in root.children_recursive if o.type == "MESH"]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
