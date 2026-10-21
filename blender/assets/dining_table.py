"""Long dining table for 12-14: a thick walnut top with soft corners over a recessed
smoked-oak under-plate (so it appears to float), two slab trestle ends on bronze
plinths and a smoked-oak stretcher beam.

Units are metres. Faces -Y (long axis along X), origin at the floor centre.
"""
import importlib
import math
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402  (hiding spot, prompts/interactivity.md)

importlib.reload(ix_common)

NAME = "DiningTable"


def grain_along_length(ob):
    """The walnut map's grain runs along v; swap u/v so it follows the table's length."""
    uv = ob.data.uv_layers["UVMap"]
    for d in uv.data:
        pass  # the walnut scan is rotated so its grain runs along u (polyhaven_textures ROTATE): no swap

def profiled_slab_bmesh(L, W, corner, profile, segments=8):
    """Rounded-corner slab whose edge follows `profile` [(inset, z), ...] from the top
    face down to the underside (inset = how far that ring sits inside the outline).
    Rings where the profile turns sharply get hard edges; the rounded corners stay smooth."""
    bm = bmesh.new()
    rings = []
    for inset, z in profile:
        hw, hd = L / 2 - inset, W / 2 - inset
        pts = common.fillet_polyline([(-hw, -hd, 0), (hw, -hd, 0), (hw, hd, 0), (-hw, hd, 0)],
                                     max(corner - inset, 0.005), segments=segments, closed=True)
        rings.append([bm.verts.new((p.x, p.y, z)) for p in pts])
    n = len(rings[0])
    for a, c in zip(rings[:-1], rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], c[j], c[i]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for k in range(len(profile)):
        prev = profile[k - 1] if k > 0 else (profile[k][0] - 1.0, profile[k][1])       # top face: flat
        nxt = profile[k + 1] if k + 1 < len(profile) else (profile[k][0] + 1.0, profile[k][1])
        d1 = (profile[k][0] - prev[0], profile[k][1] - prev[1])
        d2 = (nxt[0] - profile[k][0], nxt[1] - profile[k][1])
        ang = math.degrees(abs(math.atan2(d1[0] * d2[1] - d1[1] * d2[0], d1[0] * d2[0] + d1[1] * d2[1])))
        if ang > 35:
            for i in range(n):
                e = bm.edges.get((rings[k][i], rings[k][(i + 1) % n]))
                if e:
                    e.smooth = False
    return bm


def trapezoid_bmesh(t, w_top, w_bot, h):
    """A slab leg (t along x) whose width along y tapers from w_top to w_bot."""
    bm = bmesh.new()
    vs = []
    for x in (-t / 2, t / 2):
        vs.append([bm.verts.new((x, -w_bot / 2, -h / 2)), bm.verts.new((x, w_bot / 2, -h / 2)),
                   bm.verts.new((x, w_top / 2, h / 2)), bm.verts.new((x, -w_top / 2, h / 2))])
    a, b = vs
    bm.faces.new(a[::-1])
    bm.faces.new(b)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


P = dict(
    name=NAME,
    length=5.2,
    width=1.3,
    height=0.76,
    top_t=0.05,
    corner=0.10,
    leg_t=0.10,            # slab thickness (along x)
    leg_w=0.92,            # slab width (along y)
    leg_inset=1.0,        # slab centre from the table end
    plinth_h=0.03,
    stretcher=(0.09, 0.11),   # width (y), height (z)
    stretcher_z=0.48,
    hide=True,                # a hiding spot under the table (out between two chairs)
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    walnut = materials.walnut()
    oak = materials.smoked_oak()
    bronze = materials.bronze()

    L, W, H, T = p["length"], p["width"], p["height"], p["top_t"]
    # top: an eased upper arris, a 22 mm square edge, then a long underside chamfer so the
    # 50 mm slab reads light from standing height
    prof = [(0.004, 0.0), (0.0008, -0.0012), (0.0, -0.004), (0.0, -0.022), (0.004, -0.026), (0.045, -T)]
    top = common.mesh_object(f"{n}_Top", profiled_slab_bmesh(L, W, p["corner"], prof), col, walnut, root)
    top.location = (0, 0, H)
    common.box_uv(top, 0.5)
    grain_along_length(top)

    under_t = 0.035
    plate = common.mesh_object(
        f"{n}_Underplate", common.rounded_slab_bmesh(L - 0.34, W - 0.34, under_t, 0.06),
        col, oak, root)
    plate.location = (0, 0, H - T - under_t / 2 + 0.002)
    common.add_bevel(plate, 0.004, 2)
    common.box_uv(plate, 0.5)

    ph = p["plinth_h"]
    leg_top = H - T - under_t + 0.004
    lh = leg_top - ph - 0.04                 # the slab stops under an oak cleat
    sw, sz = p["stretcher"]
    span = L - 2 * p["leg_inset"]
    for side, sx in (("L", -1), ("R", 1)):
        x = sx * (L / 2 - p["leg_inset"])
        # tapered slab: full width at the top, 9 cm narrower at the foot
        leg = common.mesh_object(f"{n}_Leg_{side}", trapezoid_bmesh(p["leg_t"], p["leg_w"], p["leg_w"] - 0.09, lh),
                                 col, oak, root)
        leg.location = (x, 0, ph + lh / 2)
        common.add_bevel(leg, 0.006, 2)
        common.box_uv(leg, 0.5)
        # cleat across the top of the slab, screwed up into the under-plate
        cleat = common.mesh_object(f"{n}_Cleat_{side}", common.box_bmesh((p["leg_t"] + 0.07, p["leg_w"] + 0.04, 0.04)),
                                   col, oak, root)
        cleat.location = (x, 0, leg_top - 0.02)
        common.add_bevel(cleat, 0.005, 2)
        common.box_uv(cleat, 0.5)
        # bronze shoe the slab stands in
        foot = common.mesh_object(f"{n}_Plinth_{side}",
                                  common.box_bmesh((p["leg_t"] + 0.05, p["leg_w"] - 0.09 + 0.06, ph)),
                                  col, bronze, root)
        foot.location = (x, 0, ph / 2)
        common.add_bevel(foot, 0.004, 2)
        common.box_uv(foot, 0.5)
        # through-tenon: the stretcher's end shows 25 mm proud of the slab's outer face, pinned
        # by a bronze peg
        peg = common.mesh_object(f"{n}_Peg_{side}_NoCollide",
                                 common.box_bmesh((0.016, sw + 0.02, 0.016)), col, bronze, root)
        peg.location = (x + sx * (p["leg_t"] / 2 + 0.013), 0, p["stretcher_z"])
        common.add_bevel(peg, 0.003, 1)

    bar = common.mesh_object(f"{n}_Stretcher", common.box_bmesh((span + p["leg_t"] + 0.05, sw, sz)),
                             col, oak, root)
    bar.location = (0, 0, p["stretcher_z"])
    common.add_bevel(bar, 0.005, 2)
    common.box_uv(bar, 0.5)

    if p["hide"]:
        # hiding spot (open cover): under the top on the -Y side of the stretcher, looking out
        # between the chairs (the dining room's are 0.8 m apart, a gap on the centre line)
        y_out = -W / 2 - 0.85
        ix_common.hide_spot(root, col, n, (0.0, -0.32, 0.5), [(0.0, y_out, 0.0), (0.8, y_out, 0.0), (-0.8, y_out, 0.0)],
                            "Hide under the table", "Crawl out", cover="open", pitch=-2)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
