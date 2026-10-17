"""Upholstered bench for the foot of the bed: a boxed, piped ink-fabric cushion
with a soft crown on a slim bronze flat-bar frame (two sled ends joined by a
stretcher).

Units are metres. The front faces -Y, the origin is the floor centre.
Run inside Blender (see blender/run.py); re-running rebuilds it.
"""
import importlib
import os
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "Bench"

P = dict(
    name=NAME,
    width=1.45,
    depth=0.42,
    height=0.46,            # top of the cushion crown
    # cushion
    cushion_t=0.115,        # box thickness before the crown
    crown=0.02,            # centre bulge of the top face
    cushion_edge=0.03,
    piping_r=0.0042,
    # frame (flat bar: bar_w in the plane of the sled, bar_t across it)
    bar_w=0.030,
    bar_t=0.016,
    end_inset=0.05,         # sled end centre line in from the cushion end
    end_half_depth=0.172,   # y of the sled's uprights (centre line)
    bend_r=0.028,
    board_t=0.010,          # hidden black ply deck between frame and cushion
    stretcher_h=0.075,      # drop of the stretcher below the rail top
    stretcher_t=0.014,
    chamfer=0.0018,
)


def sweep_bar(name, path, half_w, half_t, chamfer, x, col, mat, parent):
    """Sweep a chamfered rectangular flat-bar section along a closed polyline
    that lies in the YZ plane at `x`. half_w is across the path in that plane,
    half_t is along X. Each profile edge has its own vertices, so the surface is
    smooth along the bar and crisp across it."""
    n = len(path)
    c = chamfer
    # (x offset, in-plane offset) corners of the chamfered section
    prof = [(half_t - c, half_w), (-half_t + c, half_w), (-half_t, half_w - c),
            (-half_t, -half_w + c), (-half_t + c, -half_w), (half_t - c, -half_w),
            (half_t, -half_w + c), (half_t, half_w - c)]
    pts = [Vector(p) for p in path]
    normals = []
    for i in range(n):
        t = (pts[(i + 1) % n] - pts[i - 1]).normalized()
        normals.append(Vector((0, -t.z, t.y)))   # in-plane perpendicular
    bm = bmesh.new()
    for e in range(len(prof)):
        a, b = prof[e], prof[(e + 1) % len(prof)]
        ra = [bm.verts.new((x + a[0], *(pts[i] + normals[i] * a[1])[1:])) for i in range(n)]
        rb = [bm.verts.new((x + b[0], *(pts[i] + normals[i] * b[1])[1:])) for i in range(n)]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((ra[i], ra[j], rb[j], rb[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # make sure normals point away from the bar's centre line
    f = bm.faces[0]
    centre = Vector((x, pts[0].y, pts[0].z))
    if (f.calc_center_median() - centre).dot(f.normal) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return common.mesh_object(name, bm, col, mat, parent)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    bronze = materials.bronze()
    ink = materials.fabric("M_Fabric_Ink", (0.018, 0.024, 0.04), roughness=0.8)
    black = materials.black_metal()

    W, D, H = p["width"], p["depth"], p["height"]
    bw, bt = p["bar_w"], p["bar_t"]
    ct = p["cushion_t"]
    crown = p["crown"]

    # --- vertical stack (from the top down)
    cushion_top_box = H - crown * 0.75 - 0.004       # the crown's centre bulge survives subdivision at ~75 %
    cushion_bot = cushion_top_box - ct
    board_bot = cushion_bot - p["board_t"]
    rail_top = board_bot
    rail_z = rail_top - bw / 2               # centre line of the top rail
    floor_z = bw / 2                         # centre line of the runner

    # --- frame: two sled ends (closed flat-bar loops)
    hx = W / 2 - p["end_inset"]
    yh = p["end_half_depth"]
    corners = [(0, -yh, floor_z), (0, yh, floor_z), (0, yh, rail_z), (0, -yh, rail_z)]
    loop = common.fillet_polyline(corners,
                                  p["bend_r"], segments=8, closed=True)
    frame_parts = []
    for side, sx in (("L", -1), ("R", 1)):
        ob = sweep_bar(f"{n}_Frame_{side}", [Vector((0, v.y, v.z)) for v in loop],
                       bw / 2, bt / 2, p["chamfer"], sx * hx, col, bronze, root)
        frame_parts.append(ob)

    # --- stretcher: a flat bar on edge hanging from the top rails, mid-depth
    sh, st = p["stretcher_h"], p["stretcher_t"]
    span = 2 * hx - bt + 0.004        # runs into the inner faces of the sled ends
    stretcher = common.mesh_object(f"{n}_Stretcher", common.box_bmesh((span, st, sh)),
                                   col, bronze, root)
    stretcher.location = (0, 0, rail_top - sh / 2)
    common.add_bevel(stretcher, p["chamfer"] * 1.2, segments=2)
    frame_parts.append(stretcher)

    # --- hidden black deck the cushion rests on (slightly smaller than the cushion)
    deck = common.mesh_object(
        f"{n}_Deck", common.box_bmesh((W - 0.07, D - 0.05, p["board_t"] + 0.002)),
        col, black, root)
    deck.location = (0, 0, (board_bot + cushion_bot) / 2)
    common.add_bevel(deck, 0.002, segments=2)
    frame_parts.append(deck)

    # --- cushion with piping
    cush_size = (W - 0.008, D - 0.008, ct)   # crown + piping bring it back to W x D
    e = p["cushion_edge"]
    cushion = common.mesh_object(
        f"{n}_Cushion",
        common.cushion_bmesh(cush_size, edge=e,
                             crown={"+z": crown, "-z": 0.0, "+x": 0.004, "-x": 0.004,
                                    "+y": 0.004, "-y": 0.004}),
        col, ink, root)
    cushion.location = (0, 0, cushion_bot + ct / 2)
    common.add_subsurf(cushion)
    fabric_parts = [cushion]
    loc = cushion.location
    for i, pts in enumerate(common.piping_loop(cush_size, "z", e / 6, e * 0.9)):
        pipe = common.tube_object(f"{n}_Cushion_Piping{i}", pts, p["piping_r"], col, ink,
                                  root, closed=True, profile_res=2)
        pipe.location = loc
        fabric_parts.append(pipe)

    for ob in frame_parts:
        common.box_uv(ob, tile=0.5)
    for ob in fabric_parts:
        common.box_uv(ob, tile=0.2)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
