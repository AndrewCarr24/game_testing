"""Bedroom nightstand: smoked oak case on a recessed black plinth so it seems
to float, one drawer (real drawer box) over an open shelf with a visible back
panel, and a slim recessed bronze pull. The front (drawer side) faces -Y;
origin is the floor centre."""
import importlib
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "Nightstand"

P = dict(
    name=NAME,
    size=(0.55, 0.42, 0.55),      # width, depth, height
    plinth_h=0.07,
    plinth_inset=(0.045, 0.05, 0.04),   # sides, front, back (recess under the case)
    top_t=0.03,
    overhang=0.008,               # top overhangs the carcass on three sides
    side_t=0.018,
    bottom_t=0.02,
    divider_t=0.018,
    divider_z=0.30,               # underside of the divider (shelf height above the floor)
    back_t=0.012,
    back_recess=0.032,            # back panel's rear face sits this far in from the rear edge
    drawer_gap=0.003,
    drawer_travel=0.25,
    drawer_open=0.0,              # 0..1, preview only (the shipped model is closed)
    pull_w=0.20,
    pull_h=0.03,
    pull_depth=0.012,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    oak = materials.smoked_oak()
    bronze = materials.bronze()
    black = materials.black_metal()

    W, D, H = p["size"]
    ph, top_t, oh = p["plinth_h"], p["top_t"], p["overhang"]
    st, bt, dvt, kt = p["side_t"], p["bottom_t"], p["divider_t"], p["back_t"]
    gap = p["drawer_gap"]
    wood = []

    def box(name, size, centre, mat=oak, parent=root, offset=(0, 0, 0), bevel=0.002, uv=True):
        ob = common.mesh_object(f"{n}_{name}", common.box_bmesh(size), col, mat, parent)
        ob.location = [centre[i] - offset[i] for i in range(3)]
        if bevel:
            common.add_bevel(ob, bevel, segments=2)
        if uv:
            wood.append(ob)
        return ob

    # ---- recessed plinth (black), so the case seems to float
    pi_s, pi_f, pi_b = p["plinth_inset"]
    y0, y1 = -D / 2 + pi_f, D / 2 - pi_b
    box("Plinth", (W - 2 * pi_s, y1 - y0, ph), (0, (y0 + y1) / 2, ph / 2), black, bevel=0.003, uv=False)

    # ---- case
    cw = W - 2 * oh                       # carcass outer width
    y_front = -D / 2 + oh                 # carcass / drawer front plane
    y_rear = D / 2 - oh
    cd = y_rear - y_front
    z_top = H - top_t                     # underside of the top
    z_bot = ph + bt                       # top face of the bottom board
    z_div = p["divider_z"]
    z_div_top = z_div + dvt

    top = box("Top", (W, D, top_t), (0, 0, H - top_t / 2), bevel=0.004)
    box("Bottom", (cw, cd, bt), (0, (y_front + y_rear) / 2, ph + bt / 2))
    for side, sx in (("L", -1), ("R", 1)):
        box(f"Side_{side}", (st, cd, z_top - ph - bt), (sx * (cw - st) / 2, (y_front + y_rear) / 2,
                                                        (ph + bt + z_top) / 2))
    iw = cw - 2 * st                      # clear width between the sides
    box("Divider", (iw, cd - kt - p["back_recess"] + oh, dvt),
        (0, y_front + (cd - kt - p["back_recess"] + oh) / 2, z_div + dvt / 2))
    # back panel: slim, set into the case and visible in the open shelf
    back_rear = D / 2 - p["back_recess"]
    box("Back", (iw + 0.006, kt, z_top - z_bot), (0, back_rear - kt / 2, (z_bot + z_top) / 2), bevel=0.0015)

    # fixed drawer runners (black), on the inner faces of the sides
    z_open_lo, z_open_hi = z_div_top, z_top
    run_w, run_h = 0.006, 0.016
    run_y0, run_y1 = y_front + 0.01, back_rear - kt
    z_run = (z_open_lo + z_open_hi) / 2 - 0.01
    for side, sx in (("L", -1), ("R", 1)):
        box(f"Runner_{side}", (run_w, run_y1 - run_y0, run_h),
            (sx * (iw / 2 - run_w / 2), (run_y0 + run_y1) / 2, z_run), black, bevel=0.001, uv=False)

    # ---- the drawer: everything below hangs from the empty `<n>_Drawer`
    oh_z = z_open_hi - z_open_lo                         # opening height
    origin = (0, y_front, (z_open_lo + z_open_hi) / 2)
    dr = common.empty(f"{n}_Drawer", col, origin)
    dr.parent = root
    dr["interact"] = {
        "type": "slide",
        "axis": common.to_gltf((0, -1, 0)),              # opens toward the front, in local space
        "distance": p["drawer_travel"],
        "duration": 0.4,
        "range": 1.4,
        "prompt": "Open drawer",
        "promptActive": "Close drawer",
    }
    dr.location.y -= p["drawer_open"] * p["drawer_travel"]

    ft = 0.02
    fw, fh = iw - 2 * gap, oh_z - 2 * gap
    fz = origin[2]
    # drawer front: one mesh, with a pocket in the upper part for the pull
    pw, ph_, pd = p["pull_w"], p["pull_h"], p["pull_depth"]
    pz = fz + fh / 2 - 0.045                             # pocket centre height
    bm = common.box_bmesh((fw, ft, fh))
    for co, no in (((-pw / 2, 0, 0), (1, 0, 0)), ((pw / 2, 0, 0), (1, 0, 0)),
                   ((0, 0, pz - fz - ph_ / 2), (0, 0, 1)), ((0, 0, pz - fz + ph_ / 2), (0, 0, 1))):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                               plane_co=co, plane_no=no)
    bm.normal_update()
    pocket = [f for f in bm.faces if f.normal.y < -0.9 and abs(f.calc_center_median().x) < pw / 2 - 1e-4
              and abs(f.calc_center_median().z - (pz - fz)) < ph_ / 2 - 1e-4]
    ext = bmesh.ops.extrude_face_region(bm, geom=pocket)
    bmesh.ops.translate(bm, vec=(0, pd, 0), verts=[g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)])
    bmesh.ops.delete(bm, geom=pocket, context="FACES_ONLY")   # the old face would still cap the pocket
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    front = common.mesh_object(f"{n}_Drawer_Front", bm, col, oak, dr)
    front.location = (0, ft / 2, 0)
    common.add_bevel(front, 0.0015, segments=2)
    wood.append(front)

    # drawer box behind the front
    bw = iw - 2 * run_w - 2 * gap - 0.002
    bdepth = run_y1 - y_front - ft - 0.02
    bh = oh_z - 0.065
    bz0 = z_open_lo + 0.012
    sw = 0.01
    yc = y_front + ft + bdepth / 2
    def dpart(name, size, centre):
        return box(name, size, centre, parent=dr, offset=origin, bevel=0.001)
    for side, sx in (("L", -1), ("R", 1)):
        dpart(f"Drawer_Side_{side}", (sw, bdepth, bh), (sx * (bw - sw) / 2, yc, bz0 + bh / 2))
    dpart("Drawer_Back", (bw - 2 * sw, sw, bh), (0, y_front + ft + bdepth - sw / 2, bz0 + bh / 2))
    dpart("Drawer_Bottom", (bw - 2 * sw, bdepth, 0.008), (0, yc, bz0 + 0.004 + 0.008))

    # slim bronze pull, resting in the pocket
    # the pocket's back face is at y_front + pd; the bar sits against it
    box("Drawer_Pull", (pw - 0.012, 0.010, 0.010), (0, y_front + pd - 0.005, pz - 0.004), bronze,
        parent=dr, offset=origin, bevel=0.0035, uv=False)

    for ob in wood:
        common.box_uv(ob, tile=0.5)
        if "_Side_" in ob.name and "Drawer" not in ob.name:
            # case sides: grain runs front to back, like the top, not up the panel
            for d in ob.data.uv_layers["UVMap"].data:
                d.uv = (d.uv[1], d.uv[0])
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
