"""Executive desk: walnut top and modesty panel on two polished steel sled
frames (same family as the lounge chair). Visitor side faces -Y; the person
sitting at the desk is on +Y. Origin is the floor centre."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)

NAME = "Desk"

P = dict(
    name=NAME,
    top=(2.0, 0.9, 0.045),     # width, depth, thickness
    height=0.74,               # top surface
    corner=0.02,               # plan-view corner radius of the top
    tube_r=0.014,
    bend_r=0.07,
    frame_inset=0.14,          # frames sit this far in from the top's ends
    frame_depth_inset=0.08,
    modesty=(1.5, 0.018, 0.36),
    modesty_y=-0.32,
    # pencil drawer under the top, opening toward the sitter (+Y)
    drawer_case=(0.66, 0.55, 0.085),   # outer width, depth, height
    drawer_case_t=0.015,
    drawer_front_inset=0.02,           # case opening sits this far behind the top's edge
    drawer_travel=0.30,
    pull_width=0.24,
)


def drawer(p, n, col, root, walnut, steel):
    """Drawer case (fixed) plus the drawer itself under an empty, `<n>_Drawer`.
    The empty carries an `interact` custom property, exported as glTF extras,
    which tells the game how the drawer moves. Returns the wooden parts."""
    w, d, t = p["top"]
    z_under = p["height"] - t
    cw, cd, ch = p["drawer_case"]
    ct = p["drawer_case_t"]
    y_open = d / 2 - p["drawer_front_inset"]       # case opening (front plane)
    y_back = y_open - cd
    wood = []

    def part(name, size, centre, parent, offset=(0, 0, 0)):
        ob = common.mesh_object(f"{n}_{name}", common.box_bmesh(size), col, walnut, parent)
        ob.location = [centre[i] - offset[i] for i in range(3)]
        common.add_bevel(ob, 0.002, segments=2)
        wood.append(ob)
        return ob

    # case: sides, bottom and back hang from the underside of the top
    for side, sx in (("L", -1), ("R", 1)):
        part(f"DrawerCase_{side}", (ct, cd, ch), (sx * (cw - ct) / 2, y_open - cd / 2, z_under - ch / 2), root)
    part("DrawerCase_Bottom", (cw, cd, ct), (0, y_open - cd / 2, z_under - ch + ct / 2), root)
    part("DrawerCase_Back", (cw - 2 * ct, ct, ch - ct), (0, y_back + ct / 2, z_under - (ch - ct) / 2), root)

    # the moving drawer: everything below is parented to this empty
    origin = (0, y_open, z_under - ch / 2)
    dr = common.empty(f"{n}_Drawer", col, origin)
    dr.parent = root
    dr["interact"] = {
        "type": "slide",
        "axis": common.to_gltf((0, 1, 0)),           # in the desk's local space
        "distance": p["drawer_travel"],
        "duration": 0.45,
        "range": 1.6,                                 # metres from the drawer front
        "prompt": "Open drawer",
        "promptActive": "Close drawer",
    }

    gap = 0.003
    ft = 0.018
    part("Drawer_Front", (cw - 2 * gap, ft, ch - gap), (0, y_open + ft / 2, z_under - ch / 2 - gap / 2), dr, origin)
    bt = 0.01
    iw = cw - 2 * ct - 2 * gap
    bd = cd - ct - 0.02
    bh = ch - ct - 0.012
    bz = z_under - ch + ct + gap
    for side, sx in (("L", -1), ("R", 1)):
        part(f"Drawer_Side_{side}", (bt, bd, bh), (sx * (iw - bt) / 2, y_open - bd / 2, bz + bh / 2), dr, origin)
    part("Drawer_Back", (iw - 2 * bt, bt, bh), (0, y_open - bd + bt / 2, bz + bh / 2), dr, origin)
    part("Drawer_Bottom", (iw - 2 * bt, bd - bt, 0.006), (0, y_open - (bd - bt) / 2, bz + 0.003), dr, origin)

    # bent steel bar pull, same tube language as the frames
    pw, zc, y0 = p["pull_width"] / 2, z_under - ch / 2, y_open + ft
    pts = common.fillet_polyline([(-pw, y0, zc), (-pw, y0 + 0.028, zc), (pw, y0 + 0.028, zc), (pw, y0, zc)],
                                 0.008, segments=6, closed=False)
    pts = [(x - origin[0], y - origin[1], z - origin[2]) for x, y, z in pts]
    common.tube_object(f"{n}_Drawer_Pull", pts, 0.005, col, steel, dr, closed=False)
    return wood


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    walnut = common.pbr_material("M_Walnut", (0.105, 0.042, 0.016), roughness=0.5, coat=0.25)
    common.set_base_color_map(walnut, textures.load(textures.walnut()))
    steel = common.pbr_material("M_Steel_Polished", (0.85, 0.85, 0.86), roughness=0.18, metallic=1.0)

    w, d, t = p["top"]
    top = common.mesh_object(f"{n}_Top", common.rounded_slab_bmesh(w, d, t, p["corner"]),
                             col, walnut, root)
    top.location = (0, 0, p["height"] - t / 2)
    common.add_bevel(top, 0.005)

    r = p["tube_r"]
    z_rail = p["height"] - t - r
    hd = d / 2 - p["frame_depth_inset"]
    for side, sx in (("L", -1), ("R", 1)):
        x = sx * (w / 2 - p["frame_inset"])
        pts = common.sled_loop(x, -hd, hd, z_rail, r, p["bend_r"])
        common.tube_object(f"{n}_Frame_{side}", pts, r, col, steel, root)

    mw, mt, mh = p["modesty"]
    panel = common.mesh_object(f"{n}_ModestyPanel", common.box_bmesh((mw, mt, mh)), col, walnut, root)
    panel.location = (0, p["modesty_y"], p["height"] - t - mh / 2)
    common.add_bevel(panel, 0.003)

    wood = [top, panel] + drawer(p, n, col, root, walnut, steel)
    for ob in wood:
        common.box_uv(ob, tile=0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
