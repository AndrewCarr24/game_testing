"""Two-door wardrobe in smoked oak: thick carcass (top and sides heavier than
the doors), inset full-height doors with 3 mm reveals and vertical grain,
slim full-height bronze bar pulls at the meeting edges, a recessed black
plinth and a shadow gap under the top. Doors are static for now.

Origin is the floor centre; the doors face -Y."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "Wardrobe"

P = dict(
    name=NAME,
    size=(1.8, 0.62, 2.4),     # width, depth, height
    plinth_h=0.05,
    plinth_recess=0.05,        # front of the plinth sits this far behind the carcass front
    plinth_side_inset=0.04,
    top_t=0.045,
    top_inset=0.006,           # carcass sides/front sit this far inside the top's edge
    side_t=0.036,
    bottom_t=0.04,
    back_t=0.012,
    door_t=0.022,
    reveal=0.003,
    top_gap=0.014,             # dark shadow gap between the doors and the top
    pull_r=0.0065,
    pull_stand=0.03,          # how far the bar stands off the door face
    pull_margin=0.11,          # bar starts/ends this far from the door's top and bottom
    pull_inset=0.032,          # centre of the bar from the meeting edge
    bevel=0.0025,
)


def shift_uv(ob, du, dv):
    """Move a part's grain pattern so neighbouring panels don't repeat."""
    uv = ob.data.uv_layers["UVMap"]
    for d in uv.data:
        d.uv = (d.uv[0] + du, d.uv[1] + dv)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    oak = materials.smoked_oak()
    bronze = materials.bronze()
    black = materials.black_metal()

    W, D, H = p["size"]
    D -= p["pull_stand"] + p["pull_r"] - p["top_inset"]   # the pulls stand proud of the carcass; keep the overall depth
    wood = []

    def box(name, size, centre, mat, bevel=None, uv=True, shift=(0, 0)):
        ob = common.mesh_object(f"{n}_{name}", common.box_bmesh(size), col, mat, root)
        ob.location = centre
        if bevel is None:
            bevel = p["bevel"]
        if bevel:
            common.add_bevel(ob, bevel, segments=2)
        if uv:
            common.box_uv(ob, tile=0.5)
            shift_uv(ob, *shift)
            wood.append(ob)
        return ob

    ins = p["top_inset"]
    y_front = -D / 2 + ins                 # front plane of sides, bottom and doors
    y_back = D / 2 - ins
    cw = W - 2 * ins                       # carcass outer width
    st, bt, tt = p["side_t"], p["bottom_t"], p["top_t"]
    ph = p["plinth_h"]
    z_top = H - tt                         # underside of the top
    z_bot = ph + bt                        # top of the bottom panel

    # --- top: full footprint, heavier than the doors
    box("Top", (W, D, tt), (0, 0, H - tt / 2), oak, bevel=0.004, shift=(0.13, 0.0))

    # --- sides, bottom panel and back
    for side, sx in (("L", -1), ("R", 1)):
        box(f"Side_{side}", (st, y_back - y_front, z_top - ph), (sx * (cw - st) / 2, (y_front + y_back) / 2, (z_top + ph) / 2),
            oak, shift=(0.31 * sx, 0.07 * sx))
    box("Bottom", (cw - 2 * st, y_back - y_front, bt), (0, (y_front + y_back) / 2, ph + bt / 2), oak,
        shift=(0.2, 0.4))
    box("Back", (cw - 2 * st, p["back_t"], z_top - ph), (0, y_back - p["back_t"] / 2, (z_top + ph) / 2), oak,
        shift=(0.5, 0.2))

    # --- dark interior seen through the reveals and the top shadow gap
    dt = p["door_t"]
    iw = cw - 2 * st
    box("Interior", (iw, 0.006, z_top - z_bot), (0, y_front + dt + 0.035, (z_top + z_bot) / 2), black,
        bevel=0, uv=False)

    # --- recessed black plinth
    pw = cw - 2 * p["plinth_side_inset"]
    py0 = y_front + p["plinth_recess"]
    box("Plinth", (pw, y_back - 0.02 - py0, ph), (0, (py0 + y_back - 0.02) / 2, ph / 2), black,
        bevel=0.001, uv=False)

    # --- inset doors: full height, vertical grain
    g = p["reveal"]
    door_w = (iw - 3 * g) / 2
    z0 = z_bot + g
    z1 = z_top - p["top_gap"]
    door_h = z1 - z0
    for side, sx in (("L", -1), ("R", 1)):
        xc = sx * (g / 2 + door_w / 2)
        box(f"Door_{side}", (door_w, dt, door_h), (xc, y_front + dt / 2, (z0 + z1) / 2), oak,
            bevel=0.002, shift=(0.0 if sx < 0 else 0.37, 0.0 if sx < 0 else 0.23))

        # bar pull on the meeting edge: stand-offs plus the bar, one swept tube
        px = sx * (g / 2 + p["pull_inset"])
        ya = y_front                       # door face
        yb = ya - p["pull_stand"]
        za, zb = z0 + p["pull_margin"], z1 - p["pull_margin"]
        pts = common.fillet_polyline([(px, ya, za), (px, yb, za), (px, yb, zb), (px, ya, zb)],
                                     0.012, segments=5, closed=False)
        common.tube_object(f"{n}_Pull_{side}", pts, p["pull_r"], col, bronze, root, closed=False, profile_res=4)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
