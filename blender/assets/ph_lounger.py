"""A low cedar lounger for the bathhouse's rest room (after the reclining chairs of the Vals rest
rooms): close-set cedar slats over a dark bronze frame, a long flat seat and a back raised 32
degrees, a folded linen towel at its foot. 2.0 x 0.68 m, the seat at 0.3 m.
Origin: the centre of its footprint on the floor; the head is at +y."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ph_common as pc  # noqa: E402

importlib.reload(pc)
common = pc.common

NAME = "PHLounger"
P = dict(name=NAME, length=2.0, width=0.68, seat_h=0.3, back=0.72, angle=32.0, slat=(0.055, 0.02), pitch=0.072)


def slab(name, w, l, t, mat, col, parent, at, tilt=0.0, pivot_y=0.0):
    """A board w (x) by l (y) by t thick, its near end at y = pivot_y, tilted up about x by `tilt`."""
    bm = common.box_bmesh((w, l, t))
    bmesh.ops.translate(bm, vec=(0, l / 2, 0), verts=bm.verts)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(tilt), 3, "X"))
    bmesh.ops.translate(bm, vec=(at[0], at[1] + pivot_y, at[2]), verts=bm.verts)
    ob = common.mesh_object(name, bm, col, mat, parent, smooth=False)
    common.box_uv(ob, tile=0.5)
    return ob


def _join(dst, src):
    """Append bmesh src's geometry to dst (src is freed)."""
    import bpy
    me = bpy.data.meshes.new("_ph_tmp")
    src.to_mesh(me)
    src.free()
    dst.from_mesh(me)
    bpy.data.meshes.remove(me)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = pc.start(n)
    cedar, frame, linen = pc.cedar(), pc.dark_bronze(), pc.linen()
    L, W, H = p["length"], p["width"], p["seat_h"]
    sw, st = p["slat"]
    seat_len = L - p["back"] * math.cos(math.radians(p["angle"]))
    y0 = -L / 2
    # seat slats run across (x), stepping along y; the back's slats tilt with it: one mesh each
    a = math.radians(p["angle"])
    seat, back = bmesh.new(), bmesh.new()
    k = int(seat_len / p["pitch"])
    for i in range(k):
        y = y0 + 0.02 + i * p["pitch"]
        b = common.box_bmesh((W, sw, st))
        bmesh.ops.translate(b, vec=(0, y + sw / 2, H - st / 2), verts=b.verts)
        _join(seat, b)
    yb = y0 + seat_len
    kb = int(p["back"] / p["pitch"])
    for i in range(kb):
        s_ = 0.02 + i * p["pitch"]
        b = common.box_bmesh((W, sw, st))
        bmesh.ops.translate(b, vec=(0, sw / 2, 0), verts=b.verts)
        bmesh.ops.rotate(b, verts=b.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(a, 3, "X"))
        bmesh.ops.translate(b, vec=(0, yb + s_ * math.cos(a), H - st / 2 + s_ * math.sin(a)), verts=b.verts)
        _join(back, b)
    for nm, bm_ in (("Seat", seat), ("Back", back)):
        ob = common.mesh_object(f"{n}_{nm}", bm_, col, cedar, root, smooth=False)
        common.box_uv(ob, tile=0.5)
    # the frame: two flat bars under the slats along each side, a raised one under the back, legs
    for sx in (-1, 1):
        x = sx * (W / 2 - 0.05)
        pc.box(f"{n}_Rail{sx}", (x - 0.012, y0, H - st - 0.05), (x + 0.012, yb + 0.02, H - st), frame, col, root)
        slab(f"{n}_BackRail{sx}", 0.024, p["back"], 0.05, frame, col, root, (x, yb, H - st - 0.05), p["angle"])
        for y in (y0 + 0.08, yb - 0.05):
            pc.box(f"{n}_Leg{sx}_{int(y * 100)}", (x - 0.015, y - 0.015, 0), (x + 0.015, y + 0.015, H - st - 0.05), frame, col, root)
        # the back's strut down to the floor
        pc.box(f"{n}_Strut{sx}", (x - 0.012, yb + 0.42, 0), (x + 0.012, yb + 0.45, H - st + 0.42 * math.tan(a) - 0.05),
               frame, col, root)
    # a folded linen towel at the foot (a static textile)
    pc.box(f"{n}_Towel", (-0.26, y0 + 0.08, H), (0.26, y0 + 0.42, H + 0.06), linen, col, root, uv_tile=0.25, bevel=0.018, smooth=True)
    return pc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
