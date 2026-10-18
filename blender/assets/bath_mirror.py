"""Wall mirror for the primary bath: a tall rounded-top-and-bottom pill (stadium) mirror
with a slim brushed-brass frame and a warm halo glow behind it (emissive strip,
so the mirror seems to float off the marble).

Origin: centre of the mirror on the wall plane. The back is at y = 0, the glass faces
-Y; the mirror spans +-width/2 in X and +-height/2 in Z. Hang it with a z in PLACEMENTS.
"""
import importlib
import math
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import bath_common as bc  # noqa: E402

importlib.reload(common)
importlib.reload(bc)

NAME = "BathMirror"

P = dict(
    name=NAME,
    width=0.90, height=1.25,
    corner=0.45,          # corner radius (= width / 2 makes a stadium)
    frame_w=0.016,        # visible width of the brass frame
    frame_d=0.034,        # depth of the frame from the wall
    glass_d=0.026,        # the glass face stands this far from the wall
    halo_d=0.012,
    halo_w=0.012,         # glow ring outside the frame
    segs=12,
)


def outline(w, h, r, segs):
    """Rounded-rectangle outline (counter-clockwise) in the XZ plane."""
    r = min(r, w / 2 - 1e-4, h / 2 - 1e-4)
    pts = []
    for cx, cz, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(segs + 1):
            a = math.radians(a0 + 90 * k / segs)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def prism(pts, y0, y1):
    """Extrude a closed XZ outline between y0 and y1 (no bevel): a flat plate."""
    bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for x, z in pts]
    b = [bm.verts.new((x, y1, z)) for x, z in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(a[::-1])
    bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def ring_plate(outer, inner, y0, y1):
    """Closed frame: region between two same-count outlines, extruded y0..y1."""
    bm = bmesh.new()
    n = len(outer)
    vo0 = [bm.verts.new((x, y0, z)) for x, z in outer]
    vo1 = [bm.verts.new((x, y1, z)) for x, z in outer]
    vi0 = [bm.verts.new((x, y0, z)) for x, z in inner]
    vi1 = [bm.verts.new((x, y1, z)) for x, z in inner]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((vo0[i], vo0[j], vo1[j], vo1[i]))      # outer side
        bm.faces.new((vi1[i], vi1[j], vi0[j], vi0[i]))      # inner side
        bm.faces.new((vo1[i], vo1[j], vi1[j], vi1[i]))      # front
        bm.faces.new((vo0[j], vo0[i], vi0[i], vi0[j]))      # back
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    brass, mirror = bc.brass(), bc.mirror()
    glow = materials.emissive("M_Bath_MirrorHalo", (1.0, 0.80, 0.55), 3.0)

    w, h, r, segs = p["width"], p["height"], p["corner"], p["segs"]
    fw = p["frame_w"]
    gw, gh = w - 2 * fw, h - 2 * fw
    gr = max(r - fw, 0.01)
    # glass
    g = common.mesh_object(f"{n}_Glass", prism(outline(gw, gh, gr, segs), -p["glass_d"], -p["glass_d"] + 0.004), col, mirror,
                           root, smooth=False)
    # brass frame (a ring around the glass, standing proud of the glass)
    fr = common.mesh_object(f"{n}_Frame",
                            ring_plate(outline(w, h, r, segs), outline(gw, gh, gr, segs), -p["frame_d"], -0.004),
                            col, brass, root, smooth=False)
    # halo: a glowing ring just outside the frame, set behind it
    hw = p["halo_w"]
    halo = common.mesh_object(
        f"{n}_Halo",
        ring_plate(outline(w + 2 * hw, h + 2 * hw, r + hw, segs), outline(w - 0.004, h - 0.004, r, segs),
                   -p["halo_d"], -0.002), col, glow, root, smooth=False)
    return root, bc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
