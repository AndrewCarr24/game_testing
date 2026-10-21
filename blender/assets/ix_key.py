"""A door / cabinet key on a steel split ring with a leather fob: a pickup (item `key_<id>`)
that opens one lock in the level (a placement's {"lock": "key_<id>"}). The base asset is
the generic key; each key in the house is a thin variant module (ix_key_office, ix_key_safe,
ix_key_cellar, ix_key_locker) with its own item id, name, metal and fob colour, so the
player tells them apart at a glance (no writing on them: the game has no text props).

Lies flat; origin at the centre of its underside. The blade points +X, the fob -X."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402

importlib.reload(ix_common)
common, materials = ix_common.common, ix_common.materials

NAME = "IX_Key"
P = dict(
    name=NAME,
    item="key", label="Key",
    metal="brass",                 # brass | steel | bronze | nickel
    fob=(0.20, 0.075, 0.03),       # leather fob colour (linear)
    fob_size=(0.050, 0.022),       # length, width
    bow=(0.026, 0.024),            # the key's head
    blade=0.036,                   # blade length past the bow
    bits=(0.004, 0.0065, 0.003, 0.0055),   # bit depths along the blade (the cut)
    double=False,                  # bits on both edges (a safe key)
    t=0.0024,                      # key thickness
)

METALS = {
    "brass": ("M_Brass", (0.78, 0.56, 0.24), 0.3),
    "steel": ("M_Steel_Satin", (0.62, 0.62, 0.63), 0.3),
    "bronze": ("M_Bronze", (0.42, 0.26, 0.13), 0.32),
    "nickel": ("M_Key_Nickel", (0.70, 0.68, 0.64), 0.22),
}


def blade_bmesh(p):
    """The key's profile (bow + shank + cut bits) extruded to its thickness, in the XY plane."""
    bw, bh = p["bow"]
    L, t = p["blade"], p["t"]
    w = 0.0075                                    # shank width
    x0 = bw / 2 - 0.002                           # where the shank leaves the bow
    # outline, counter-clockwise: the shank's lower edge (with the cut), its tip, upper edge
    pts = [(x0, -w / 2)]
    bits = p["bits"]
    n = len(bits)
    step = (L - 0.006) / n
    for i, d in enumerate(bits):
        xa = x0 + 0.004 + i * step
        pts += [(xa, -w / 2), (xa + step * 0.25, -w / 2 - d), (xa + step * 0.75, -w / 2 - d), (xa + step, -w / 2)]
    pts += [(x0 + L - 0.0015, -w / 2), (x0 + L, -w / 2 + 0.002), (x0 + L, w / 2 - 0.001)]
    if p["double"]:
        for i, d in reversed(list(enumerate(bits[::-1]))):
            xa = x0 + 0.004 + i * step
            pts += [(xa + step, w / 2), (xa + step * 0.75, w / 2 + d * 0.8), (xa + step * 0.25, w / 2 + d * 0.8), (xa, w / 2)]
    pts += [(x0, w / 2)]
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, 0)) for x, y in pts]
    f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    top = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, t * 0.8), verts=top)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    root["interact"] = ix_common.pickup(p["item"], p["label"])

    mname, mcol, mrough = METALS[p["metal"]]
    metal = common.pbr_material(mname, mcol, roughness=mrough, metallic=1.0)
    ring_m = common.pbr_material("M_Steel_Satin", (0.62, 0.62, 0.63), roughness=0.3, metallic=1.0)
    leather = common.pbr_material(f"M_KeyFob_{n.split('_')[-1]}", p["fob"], roughness=0.55, coat=0.15)
    stitch = common.pbr_material("M_KeyFob_Stitch", (0.55, 0.50, 0.42), roughness=0.8)

    t = p["t"]
    bw, bh = p["bow"]
    # the head: a rounded slab with a hole for the ring (the hole is a dark inset disc on
    # both faces: a real through-hole would cost more triangles than it's worth at 3 cm)
    bow = common.mesh_object(f"{n}_Bow", common.rounded_slab_bmesh(bw, bh, t, min(bw, bh) * 0.42, segments=5),
                             col, metal, root)
    bow.location = (0, 0, t / 2)
    common.add_bevel(bow, 0.0005, segments=1)
    shank = common.mesh_object(f"{n}_Blade", blade_bmesh(p), col, metal, root, smooth=False)
    shank.location = (0, 0, t * 0.1)
    # the ring through the bow's hole, lying flat, and the fob hanging off it
    hx = -bw / 2 + 0.0055
    rr = 0.0105
    ring = [(hx - rr + 0.0035 + rr * math.cos(a), rr * math.sin(a), t * 0.5 + 0.0002 * math.sin(3 * a))
            for a in [2 * math.pi * k / 18 for k in range(18)]]
    common.tube_object(f"{n}_Ring", ring, 0.0009, col, ring_m, root, closed=True)
    hole = bmesh.new()
    bmesh.ops.create_cone(hole, cap_ends=True, segments=10, radius1=0.0022, radius2=0.0022, depth=t + 0.0003)
    dark = common.pbr_material("M_Key_Hole", (0.01, 0.01, 0.01), roughness=0.9)
    h = common.mesh_object(f"{n}_Hole", hole, col, dark, root, smooth=False)
    h.location = (hx, 0, t / 2)
    fl, fw = p["fob_size"]
    fx = hx - 2 * rr + 0.0085 - fl / 2         # the eyelet sits on the ring
    fob = common.mesh_object(f"{n}_Fob", common.rounded_slab_bmesh(fl, fw, 0.0032, fw * 0.45, segments=5),
                             col, leather, root)
    fob.location = (fx, 0, 0.0016)
    common.add_bevel(fob, 0.0008, segments=1)
    # stitching: a thin inset loop on the fob's top face
    st = common.fillet_polyline([(fx - fl / 2 + 0.003, -fw / 2 + 0.0025, 0), (fx + fl / 2 - 0.003, -fw / 2 + 0.0025, 0),
                                 (fx + fl / 2 - 0.003, fw / 2 - 0.0025, 0), (fx - fl / 2 + 0.003, fw / 2 - 0.0025, 0)],
                                fw * 0.3, segments=3, closed=True)
    st = [(v.x, v.y, 0.0033) for v in st]
    common.tube_object(f"{n}_Stitch", st, 0.00035, col, stitch, root, closed=True)
    # the fob's eyelet, where the ring passes
    ey = bmesh.new()
    bmesh.ops.create_cone(ey, cap_ends=True, segments=10, radius1=0.0026, radius2=0.0026, depth=0.0036,
                          matrix=Matrix.Translation((fx + fl / 2 - 0.0045, 0, 0.0018)))
    common.mesh_object(f"{n}_Eyelet", ey, col, ring_m, root, smooth=False)
    for ob in root.children:
        common.box_uv(ob, 0.2) if ob.type == "MESH" else None
    return ix_common.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
