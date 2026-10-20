"""Built-in walnut coat closet, 2.4 m wide: the left half is a pair of full-height closed
doors, the right half an open bay with a bronze hanging rail and five coats hung edge-on on slim
hangers (cloth-simulated, so they drape and fold; see mud_common.hanger_coat), an LED-lit hat shelf above and two shoe drawers below; a row of upper cupboard
doors runs across the whole width. Walnut throughout, a recessed black plinth, bronze
bar pulls.

Origin: floor centre. The doors face -Y (the wall is on +Y). Units are metres.
"""
import importlib
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import table_lamp  # noqa: E402
import mud_common as mc  # noqa: E402

importlib.reload(common)
importlib.reload(materials)
importlib.reload(mc)

NAME = "EntryCoatCloset"

P = dict(
    name=NAME,
    size=(2.29, 0.62, 3.0),     # two fill the cloakroom's 5.2 m north wall up to the east run's front (4.58 m)
    plinth_h=0.07,
    side_t=0.036, top_t=0.045, back_t=0.012, door_t=0.022,
    reveal=0.003,
    upper_h=0.58,
    rail_z=2.02,
    shelf_z=2.30,
    coats=[  # (colour name, rgb, length, x offset)
        ("M_Entry_Coat_Navy", (0.020, 0.028, 0.055), 1.22, -0.46),
        ("M_Entry_Coat_Camel", (0.31, 0.19, 0.085), 1.10, -0.23),
        ("M_Entry_Coat_Charcoal", (0.035, 0.036, 0.04), 1.28, 0.0),
        ("M_Entry_Coat_Oat", (0.30, 0.26, 0.20), 0.98, 0.23),
        ("M_Entry_Coat_Olive", (0.07, 0.085, 0.04), 1.15, 0.46),
    ],
)


def cube(bm, size, loc, rot=(0, 0, 0), bevel=0.02, seg=2):
    m = Matrix.Translation(loc) @ Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y") @ \
        Matrix.Rotation(rot[0], 4, "X") @ Matrix.Diagonal((*size, 1.0))
    ret = bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    verts = ret["verts"]
    if bevel:
        edges = list({e for v in verts for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=seg, affect="EDGES")


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402  (react definitions, prompts/interactivity.md)

importlib.reload(ix_common)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    walnut = materials.walnut()
    bronze = materials.bronze()
    black = materials.black_metal()
    glow = materials.emissive("M_Entry_LED_Warm", (1.0, 0.82, 0.58), 4.0)
    oat = materials.fabric("M_Fabric_Oat", (0.42, 0.37, 0.30))

    W, D, H = p["size"]
    ph, st, tt, bk, dt, g = p["plinth_h"], p["side_t"], p["top_t"], p["back_t"], p["door_t"], p["reveal"]
    wood = []

    def box(name, size, centre, mat=None, bevel=0.0025, uv=True, shift=(0, 0), seg=2):
        ob = common.mesh_object(f"{n}_{name}", common.box_bmesh(size), col, mat or walnut, root, smooth=False)
        ob.location = centre
        if bevel:
            common.add_bevel(ob, bevel, segments=seg)
        if uv and (mat is None or mat is walnut):
            common.box_uv(ob, tile=0.5)
            u = ob.data.uv_layers["UVMap"]
            for d in u.data:
                d.uv = (d.uv[0] + shift[0], d.uv[1] + shift[1])
        return ob

    ins = 0.006
    y_front = -D / 2 + ins
    y_back = D / 2 - ins
    cw = W - 2 * ins
    z_top = H - tt
    z_in0, z_in1 = ph, z_top

    # ---- carcass
    box("Top", (W, D, tt), (0, 0, H - tt / 2), bevel=0.004, shift=(0.1, 0.0))
    for side, sx in (("L", -1), ("R", 1)):
        box(f"Side_{side}", (st, y_back - y_front, z_top - ph), (sx * (cw - st) / 2, (y_front + y_back) / 2, (z_top + ph) / 2),
            shift=(0.3 * sx, 0.1))
    box("Back", (cw - 2 * st, bk, z_top - ph), (0, y_back - bk / 2, (z_top + ph) / 2), bevel=0, shift=(0.5, 0.2))
    box("Floor", (cw - 2 * st, y_back - y_front - dt, 0.03), (0, (y_front + dt + y_back) / 2, ph + 0.015), shift=(0.2, 0.4))
    box("Divider", (0.03, y_back - y_front - dt, z_top - ph), (0, (y_front + dt + y_back) / 2, (z_top + ph) / 2), shift=(0.7, 0.3))
    box("Plinth", (cw - 0.08, y_back - 0.02 - (y_front + 0.05), ph), (0, ((y_front + 0.05) + y_back - 0.02) / 2, ph / 2), black,
        bevel=0)
    # shadow gap above the doors: a dark recess behind them
    box("Interior", ((cw - 2 * st) / 2 - 0.015, 0.006, z_top - ph), (-(cw - 2 * st) / 4 - 0.0075, y_front + dt + 0.03, (z_top + ph) / 2), black, bevel=0, uv=False)

    iw = cw - 2 * st
    half = iw / 2 - 0.015
    uh = p["upper_h"]
    low_top = z_top - uh - g
    # ---- closed lower doors (left bay)
    dw = (half - 3 * g) / 2
    for i in range(2):
        xc = -(0.015 + g + dw / 2 + i * (dw + g))
        box(f"Door_L{i}", (dw, dt, low_top - ph - g), (xc, y_front + dt / 2, (low_top + ph + g) / 2), bevel=0.002,
            shift=(0.17 * i, 0.29 * i))
    # ---- upper doors across the width (4)
    uw = (iw - 5 * g) / 4
    for i in range(4):
        xc = -iw / 2 + g + uw / 2 + i * (uw + g)
        box(f"Upper_{i}", (uw, dt, uh - g), (xc, y_front + dt / 2, z_top - uh / 2 - g / 2), bevel=0.002,
            shift=(0.11 * i, 0.43))
        pull = box(f"UpperPull_{i}", (0.22, 0.012, 0.012), (xc, y_front - 0.003, z_top - uh + 0.05), bronze, bevel=0.002, uv=False, seg=1)
    # ---- vertical bar pulls on the closed doors, at the meeting edge
    for i, xe in enumerate((-0.015 - g / 2 - 0.035, -0.015 - g / 2 - dw - g - 0.0 + 0.035 + 0.0)):
        pass
    pxs = [-(0.015 + g + dw + g / 2) - 0.0]      # meeting edge between the two left doors
    for i, px in enumerate(pxs):
        for sx in (-1, 1):
            box(f"Pull_{i}_{'a' if sx < 0 else 'b'}", (0.012, 0.016, 0.55), (px + sx * 0.04, y_front - 0.003, 1.15), bronze,
                bevel=0.003, uv=False, seg=1)

    # ---- open bay (right): rail, shelf, LED, coat hangers, drawers
    bx0, bx1 = 0.015, iw / 2
    bw = bx1 - bx0
    bcx = (bx0 + bx1) / 2
    rail_z, shelf_z = p["rail_z"], p["shelf_z"]
    box("Shelf", (bw, y_back - y_front - dt - 0.02, 0.03), (bcx, (y_front + dt + y_back) / 2 + 0.0, shelf_z + 0.015),
        shift=(0.4, 0.6))
    box("LED", (bw - 0.1, 0.014, 0.008), (bcx, y_front + dt + 0.05, shelf_z - 0.004), glow, bevel=0, uv=False)
    rb = bmesh.new()
    table_lamp.cylinder_between(rb, (bx0 + 0.02, 0.02, rail_z), (bx1 - 0.02, 0.02, rail_z), 0.0125, segs=16)
    common.mesh_object(f"{n}_Rail", rb, col, bronze, root)
    for sx, x in ((-1, bx0 + 0.02), (1, bx1 - 0.02)):
        bra = bmesh.new()
        table_lamp.cylinder_between(bra, (x, 0.02, rail_z + 0.04), (x, 0.02, rail_z), 0.02, segs=14)
        common.mesh_object(f"{n}_RailBracket_{'a' if sx < 0 else 'b'}", bra, col, bronze, root)
    # hat shelf: three linen boxes
    boxes = bmesh.new()
    for i, (bw_, bh_) in enumerate(((0.34, 0.22), (0.30, 0.18), (0.26, 0.24))):
        cube(boxes, (bw_, 0.30, bh_), (bx0 + 0.25 + i * 0.36, 0.0, shelf_z + 0.03 + bh_ / 2), bevel=0.012)
    bo = common.mesh_object(f"{n}_Boxes", boxes, col, oat, root, smooth=False)
    common.box_uv(bo, tile=0.25)
    # drawers (two shoe drawers)
    dh = 0.26
    for i in range(2):
        zc = ph + 0.03 + g + dh / 2 + i * (dh + g)
        box(f"Drawer_{i}", (bw - 2 * g, dt, dh), (bcx, y_front + dt / 2, zc), bevel=0.002, shift=(0.2 * i, 0.5))
        box(f"DrawerPull_{i}", (bw * 0.5, 0.012, 0.012), (bcx, y_front - 0.003, zc + dh / 2 - 0.035), bronze, bevel=0.002, uv=False, seg=1)

    # ---- coats and hangers: hung edge-on along the rail (shoulders run front to back). Each coat
    # is cloth-simulated on its hanger (mud_common.hanger_coat: shoulders carried by the bar,
    # sleeves and hem falling free), so they hang and fold like fabric.
    hang = bmesh.new()
    coat_bms = {}
    for k, (cname, rgb, length, dx) in enumerate(p["coats"]):
        x = bcx + dx * 0.55
        top = rail_z + 0.03                        # the hanger's hook point, over the rail
        cb = mc.hanger_coat(length=length * 0.78, width=0.215, depth=0.03, sleeve=0.56, tris=650,
                            stiff=0.7 + 0.15 * (k % 3), pockets="flap" if k % 2 == 0 else None, seed=k % 3)
        bmesh.ops.transform(cb, matrix=Matrix.Translation((x, 0.0, top)) @ Matrix.Rotation(math.pi / 2, 4, "Z"),
                            verts=cb.verts)
        rgb_bm = coat_bms.setdefault(cname, (rgb, bmesh.new()))[1]
        me = bpy.data.meshes.new("tmp_coat")
        cb.to_mesh(me)
        cb.free()
        rgb_bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        # hanger: a hook over the rail, the neck, and the bar sloping into each shoulder
        neck = (x, 0.0, top - 0.12)
        table_lamp.cylinder_between(hang, (x, 0.02, rail_z + 0.016), (x, 0.004, rail_z + 0.028), 0.0025, segs=5)
        table_lamp.cylinder_between(hang, (x, 0.004, rail_z + 0.028), neck, 0.0025, segs=5)
        for sy in (-1, 1):
            table_lamp.cylinder_between(hang, neck, (x, sy * 0.19, top - 0.12 - 0.066), 0.0035, segs=5)
    for cname, (rgb, bm) in coat_bms.items():
        for f in bm.faces:
            f.material_index = 0
        mat = materials.fabric(cname, rgb, roughness=0.95)
        ob = common.mesh_object(f"{n}_{cname[2:]}_NoCollide", bm, col, mat, root, smooth=True)
        common.box_uv(ob, tile=0.25)
        ob.data.set_sharp_from_angle(angle=1.2)
    common.mesh_object(f"{n}_Hangers", hang, col, bronze, root)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    ix_common.tag_emissive(root)   # interactivity: glowing parts follow the room's light switch
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
