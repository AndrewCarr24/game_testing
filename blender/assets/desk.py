"""Executive desk: walnut top and modesty panel on two polished steel sled
frames (same family as the lounge chair). Visitor side faces -Y; the person
sitting at the desk is on +Y. Origin is the floor centre."""
import importlib
import math
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)
importlib.reload(materials)
sys.path.insert(0, HERE)
import ix_common  # noqa: E402  (hiding spot, prompts/interactivity.md)

importlib.reload(ix_common)

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
    # cable management (sitter's side of the modesty panel) and a leather desk pad
    grommet=(0.62, -0.25),
    tray_x=(-0.62, 0.66),
    pad=(0.86, 0.44, 0.003),
    pad_y=0.17,
    hide=True,                 # a hiding spot in the knee space (out on the sitter's side)
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


def grain_uv(ob):
    """box_uv puts u along a part's longest axis, but the walnut map's grain runs
    along v: swap them so the grain follows the length of every board."""
    for d in ob.data.uv_layers["UVMap"].data:
        pass  # the walnut scan is rotated so its grain runs along u (polyhaven_textures ROTATE): no swap


def knife_slab_bmesh(w, d, t, corner, ease=0.003, band=0.02, chamfer=0.012, segments=8):
    """Desk top: rounded corners in plan, a 3 mm eased top edge, a vertical edge band
    and below it an undercut chamfer, so the 45 mm top reads as a thin, crisp edge."""
    def ring(inset, z):
        hw, hd = w / 2 - inset, d / 2 - inset
        pts = common.fillet_polyline([(-hw, -hd, 0), (hw, -hd, 0), (hw, hd, 0), (-hw, hd, 0)],
                                     max(corner - inset, 0.004), segments=segments, closed=True)
        return [bm.verts.new((p.x, p.y, z)) for p in pts]

    bm = bmesh.new()
    zt, zb = t / 2, -t / 2
    r0, r1, r2 = ring(ease, zt), ring(0.0, zt - ease), ring(0.0, zt - band)
    r2b, r3 = ring(0.0, zt - band), ring(chamfer, zb)     # split ring: hard crease
    faces = []
    for a, b in ((r0, r1), (r1, r2), (r2b, r3)):
        k = len(a)
        for i in range(k):
            j = (i + 1) % k
            f = bm.faces.new((a[i], a[j], b[j], b[i]))
            f.smooth = True
            faces.append(f)
    top = bm.faces.new(r0[::-1])
    bot = bm.faces.new(r3)
    top.smooth = bot.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def lathe_bmesh(profile, segs, centre=(0, 0, 0)):
    """Closed solid of revolution about Z from [(r, z), ...] (r = 0 closes on the axis)."""
    bm = bmesh.new()
    rows = []
    for r, z in profile:
        if r < 1e-9:
            rows.append([bm.verts.new((centre[0], centre[1], centre[2] + z))])
        else:
            rows.append([bm.verts.new((centre[0] + r * math.cos(2 * math.pi * s / segs),
                                       centre[1] + r * math.sin(2 * math.pi * s / segs), centre[2] + z))
                         for s in range(segs)])
    for a, b in zip(rows, rows[1:]):
        for s in range(segs):
            s2 = (s + 1) % segs
            q = [a[s % len(a)], a[s2 % len(a)], b[s2 % len(b)], b[s % len(b)]]
            u = []
            for v in q:
                if v not in u:
                    u.append(v)
            if len(u) >= 3:
                try:
                    bm.faces.new(u)
                except ValueError:
                    pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.smooth = True
    return bm


def cable_management(p, n, col, root, black, steel):
    """Grommet in the top, a cable tray under it behind the modesty panel, and a
    cable spine dropping from the tray to the floor beside the right-hand frame."""
    w, d, t = p["top"]
    H = p["height"]
    z_under = H - t
    gx, gy = p["grommet"]
    # grommet: steel collar flush in the top, black brush insert slightly sunk
    ring = lathe_bmesh([(0.026, H - 0.004), (0.031, H - 0.004), (0.031, H + 0.0012), (0.029, H + 0.0022),
                        (0.024, H + 0.0022), (0.0225, H + 0.0006), (0.0, H + 0.0006)], 20, (gx, gy, 0))
    common.mesh_object(f"{n}_Grommet_NoCollide", ring, col, steel, root)
    # tray: a black steel U channel hung from the underside on two brackets
    x0, x1 = p["tray_x"]
    ty, tw, th = gy, 0.11, 0.075
    bm = bmesh.new()
    def box(c, s):
        r = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=s, verts=r["verts"])
        bmesh.ops.translate(bm, vec=c, verts=r["verts"])
    zt = z_under - 0.02                    # tray hangs 2 cm below the top
    box((0.5 * (x0 + x1), ty, zt - th + 0.0015), (x1 - x0, tw, 0.003))
    for sy in (-1, 1):
        box((0.5 * (x0 + x1), ty + sy * (tw / 2 - 0.0015), zt - th / 2), (x1 - x0, 0.003, th))
    for x in (x0 + 0.06, x1 - 0.06):          # hangers
        box((x, ty, z_under - 0.012), (0.03, tw + 0.006, 0.004))
        for sy in (-1, 1):
            box((x, ty + sy * (tw / 2 + 0.001), z_under - 0.012 - 0.012), (0.03, 0.003, 0.024))
    # power strip resting in the tray, cables bundled to it
    box((x1 - 0.2, ty + 0.012, zt - th + 0.02), (0.32, 0.05, 0.035))
    tray = common.mesh_object(f"{n}_CableTray", bm, col, black, root, smooth=False)
    common.add_bevel(tray, 0.0012, segments=1)
    # cable spine: from the tray's end down to the floor, a short run along it
    sx = x1 - 0.03
    pts = [(sx, ty, zt - th + 0.01), (sx, ty, 0.2), (sx + 0.02, ty + 0.03, 0.012), (sx + 0.06, ty + 0.25, 0.012)]
    pts = common.fillet_polyline(pts, 0.12, segments=5, closed=False)
    common.tube_object(f"{n}_CableSpine_NoCollide", pts, 0.011, col, black, root, closed=False, profile_res=1)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    walnut = common.pbr_material("M_Walnut", (0.105, 0.042, 0.016), roughness=0.5, coat=0.25)
    common.set_base_color_map(walnut, textures.load(textures.walnut()))
    steel = common.pbr_material("M_Steel_Polished", (0.85, 0.85, 0.86), roughness=0.08, metallic=1.0)

    w, d, t = p["top"]
    top = common.mesh_object(f"{n}_Top", knife_slab_bmesh(w, d, t, p["corner"]), col, walnut, root,
                             smooth=False)
    top.location = (0, 0, p["height"] - t / 2)

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

    # leather writing pad on the sitter's side, a little in from the edge
    leather = common.pbr_material("M_Leather_Black", (0.018, 0.016, 0.015), roughness=0.62)
    common.set_normal_map(leather, textures.load(textures.leather_normal(), non_color=True), 0.6)
    pw_, pd_, pt_ = p["pad"]
    pad = common.mesh_object(f"{n}_DeskPad", common.rounded_slab_bmesh(pw_, pd_, pt_, 0.012, segments=3),
                             col, leather, root, smooth=False)
    pad.location = (0, p["pad_y"], p["height"] + pt_ / 2)
    common.add_bevel(pad, 0.001, segments=1)
    common.box_uv(pad, tile=0.2)

    black = materials.black_metal()
    cable_management(p, n, col, root, black, steel)

    wood = [top, panel] + drawer(p, n, col, root, walnut, steel)
    for ob in wood:
        common.box_uv(ob, tile=0.5)
        grain_uv(ob)
    if p["hide"]:
        # hiding spot (open cover): curled up in the knee space behind the modesty panel, under the
        # drawer, looking out on the sitter's side (beside the chair)
        d = p["top"][1]
        ix_common.hide_spot(root, col, n, (0.32, -0.06, 0.48), [(0.42, d / 2 + 0.75, 0.0), (-0.42, d / 2 + 0.75, 0.0)],
                            "Hide under the desk", "Crawl out", cover="open", pitch=-2)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
