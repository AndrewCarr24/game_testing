"""Outdoor lounge sofa: a teak frame of four corner posts (the legs run up into the arm
and back posts) holding slatted arm and back panels, with eased edges, a front and back
seat rail and black glides under the feet; deep sand-linen seat and back cushions with
self-piped welts and a soft crown, sitting snug against each other, and knife-edge
scatter pillows piped round their seam. Also the generator behind courtyard_armchair
(same construction, one seat wide).

Front faces -Y, origin at the floor centre. Units are metres."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import courtyard_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common
rbox = cc.rbox

NAME = "CourtyardSofa"

P = dict(
    name=NAME,
    width=2.60,
    depth=0.98,
    seat_n=3,              # seat cushions across
    leg_h=0.17,
    arm_w=0.13,
    arm_h=0.62,
    back_h=0.80,
    slat_h=0.046,
    slat_gap=0.018,
    slat_t=0.034,
    seat_t=0.17,
    back_cushion_h=0.46,
    back_cushion_t=0.15,
    back_tilt_deg=13.0,
    pillows=2,
    post=0.06,             # corner post section
    edge=0.035,            # cushion edge radius (support-loop distance)
    welt_r=0.0055,         # piping radius
)


def slat_rows(z0, z1, h, gap):
    n = max(1, round((z1 - z0 + gap) / (h + gap)))
    hh = (z1 - z0 - gap * (n - 1)) / n
    return [(z0 + i * (hh + gap) + hh / 2, hh) for i in range(n)]


# ------------------------------------------------------------------ piping

def welt(name, path, outward, r, col, mat, parent, closed=True):
    """Piping cord along path: a 4-sided smooth tube whose ridge points along each
    point's outward vector (the bisector of the two faces it joins), so it reads round
    from outside at a quarter of a round tube's cost."""
    bm = bmesh.new()
    n = len(path)
    rings = []
    for i in range(n):
        a, b = path[i - 1] if (closed or i) else path[i], path[(i + 1) % n] if (closed or i < n - 1) else path[i]
        t = (b - a).normalized()
        o = (outward[i] - t * outward[i].dot(t)).normalized()
        s = t.cross(o)
        rings.append([bm.verts.new(path[i] + d * r) for d in (o, s, -o, -s)])
    for i in range(n if closed else n - 1):
        ra, rb = rings[i], rings[(i + 1) % n]
        for k in range(4):
            j = (k + 1) % 4
            bm.faces.new((ra[k], ra[j], rb[j], rb[k]))
    if not closed:
        for ring, rev in ((rings[0], True), (rings[-1], False)):
            bm.faces.new(list(reversed(ring)) if rev else ring)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = common.mesh_object(name, bm, col, mat, parent)
    common.box_uv(ob, tile=0.25)
    return ob


def rounded_rect(hx, hy, rad, seg=3):
    """Closed rounded rectangle in its own (x, y) plane: points and outward normals."""
    pts, nrm = [], []
    for cx, cy, a0 in ((hx - rad, -hy + rad, -90), (hx - rad, hy - rad, 0),
                       (-hx + rad, hy - rad, 90), (-hx + rad, -hy + rad, 180)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            nrm.append(Vector((math.cos(a), math.sin(a), 0)))
            pts.append(Vector((cx + rad * math.cos(a), cy + rad * math.sin(a), 0)))
    return pts, nrm


def face_welt(name, size, axis, sign, edge, r, col, mat, parent, loc, rot=None):
    """Welt round one face of a subdivided cushion (`axis` 'z' = top, 'y' = front/back).
    Catmull-Clark pulls a box edge in by edge/6 on each axis, so the cord sits there."""
    a = "xyz".index(axis)
    o1, o2 = [b for b in range(3) if b != a]
    ins = edge / 6
    pts, nrm = rounded_rect(size[o1] / 2 - ins, size[o2] / 2 - ins, edge * 0.9)
    path, out = [], []
    for p2, n2 in zip(pts, nrm):
        v, w = [0.0] * 3, [0.0] * 3
        v[a], v[o1], v[o2] = sign * (size[a] / 2 - ins), p2.x, p2.y
        w[a], w[o1], w[o2] = sign * 1.0, n2.x, n2.y
        path.append(Vector(v))
        out.append(Vector(w).normalized())
    ob = welt(name, path, out, r, col, mat, parent)
    ob.location = loc
    if rot:
        ob.rotation_euler = rot
    return ob


def seam_ring(ob):
    """Closed ring of the evaluated (subdivided) mesh's vertices on its local y = 0
    plane, sorted round the centre, with in-plane outward normals."""
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    ring = [v.co.copy() for v in me.vertices if abs(v.co.y) < 1e-4]
    ev.to_mesh_clear()
    # keep only the outline: the farthest vertex in each direction from the centre
    best = {}
    for q in ring:
        key = round(math.atan2(q.z, q.x), 2)
        if key not in best or q.length > best[key].length:
            best[key] = q
    pts = [best[k] for k in sorted(best)]
    keep = []
    for i, q in enumerate(pts):          # drop interior grid points that slipped in
        a, b = pts[i - 1], pts[(i + 1) % len(pts)]
        if q.length >= min(a.length, b.length) * 0.97:
            keep.append(q)
    out = []
    for i, q in enumerate(keep):
        t = (keep[(i + 1) % len(keep)] - keep[i - 1])
        nv = Vector((t.z, 0, -t.x)).normalized()
        if nv.dot(q) < 0:
            nv = -nv
        out.append(nv)
    return keep, out


def cushion(name, size, crown, col, mat, parent, loc, rot=None, edge=0.035, hide=None):
    """hide: the face that is never seen ("-z" under a seat cushion on the deck, "+y" behind
    a back cushion against the slats): its flat part is left out (the subsurf keeps the
    rounded edge round it)."""
    bm = common.cushion_bmesh(size, cuts=3, edge=edge, crown=crown)
    if hide:
        ax = "xyz".index(hide[1])
        sg = 1 if hide[0] == "+" else -1
        bm.normal_update()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal[ax] * sg > 0.9], context="FACES")
    ob = common.mesh_object(name, bm, col, mat, parent)
    ob.location = loc
    if rot:
        ob.rotation_euler = rot
    common.add_subsurf(ob)
    common.box_uv(ob, tile=0.25)
    return ob


# ------------------------------------------------------------------ build

def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    teak = cc.teak_mat()
    sand, sage, clay = cc.sand_fabric(), cc.sage_fabric(), cc.clay_fabric()
    from lib import materials
    black = materials.black_metal()

    W, D = p["width"], p["depth"]
    t = p["slat_t"]
    aw = p["arm_w"]
    lh = p["leg_h"]
    ps = p["post"]
    rail_z0, rail_h = lh, 0.075
    glide = 0.008

    # corner posts: legs that carry on up into the arm (front) and back (rear) frames
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        top = p["arm_h"] if sy < 0 else p["back_h"]
        x, y = sx * (W / 2 - ps / 2), sy * (D / 2 - ps / 2)
        rbox(f"{n}_Leg{i}", (ps, ps, top - glide), (x, y, glide + (top - glide) / 2), teak, col, root,
             bevel=0.005, seg=1)
        rbox(f"{n}_Glide{i}", (ps - 0.012, ps - 0.012, glide + 0.002), (x, y, (glide + 0.002) / 2), black, col, root,
             bevel=0, uv_tile=0)

    # seat rails between the posts and a plain deck the cushions sit on
    span_x = W - 2 * ps + 0.004
    rbox(f"{n}_RailFront", (span_x, 0.04, rail_h), (0, -D / 2 + 0.03, rail_z0 + rail_h / 2), teak, col, root,
         bevel=0.004, seg=1)
    rbox(f"{n}_RailBack", (span_x, 0.04, rail_h), (0, D / 2 - 0.03, rail_z0 + rail_h / 2), teak, col, root,
         bevel=0.004, seg=1)
    deck_top = rail_z0 + rail_h
    rbox(f"{n}_Deck", (W - 2 * ps, D - 0.10, 0.025), (0, 0, deck_top - 0.0125), teak, col, root, bevel=0, uv_tile=0.5)

    # slatted arm panels between the arm posts, back panel between the rear posts
    for side, sx in (("L", -1), ("R", 1)):
        for k, (zc, hh) in enumerate(slat_rows(rail_z0, p["arm_h"], p["slat_h"], p["slat_gap"])):
            rbox(f"{n}_ArmSlat{side}{k}", (t, D - 2 * ps + 0.004, hh), (sx * (W / 2 - ps / 2), 0, zc), teak, col, root,
                 bevel=0.003, seg=1)
        rbox(f"{n}_ArmCap{side}", (aw, D, 0.032), (sx * (W / 2 - aw / 2), 0, p["arm_h"] + 0.016), teak, col, root,
             bevel=0.006, seg=2)
    for k, (zc, hh) in enumerate(slat_rows(rail_z0, p["back_h"], p["slat_h"], p["slat_gap"])):
        rbox(f"{n}_BackSlat{k}", (span_x, t, hh), (0, D / 2 - ps / 2, zc), teak, col, root, bevel=0.003, seg=1)
    rbox(f"{n}_BackCap", (W, 0.09, 0.03), (0, D / 2 - 0.045, p["back_h"] + 0.015), teak, col, root, bevel=0.006, seg=2)

    # seat cushions: snug side by side between the posts, a soft crown, welts top and bottom
    e, wr = p["edge"], p["welt_r"]
    inner = W - 2 * ps
    ns = p["seat_n"]
    cw = inner / ns
    seat_front = -D / 2 + 0.010
    slat_face = D / 2 - ps / 2 - t / 2
    seat_back = slat_face - 0.004
    sd = seat_back - seat_front
    st = p["seat_t"]
    seat_z0 = deck_top
    for i in range(ns):
        cx = -inner / 2 + cw * (i + 0.5)
        size = (cw + 0.004, sd, st)
        loc = (cx, (seat_front + seat_back) / 2, seat_z0 + st / 2)
        cushion(f"{n}_SeatCushion{i}", size, {"+z": 0.024, "+x": 0.008, "-x": 0.008, "-y": 0.012}, col, sand, root,
                loc, edge=e, hide="-z")
        face_welt(f"{n}_SeatCushion{i}_PipingTop", size, "z", 1, e, wr, col, sand, root, loc)
        face_welt(f"{n}_SeatCushion{i}_PipingBottom", size, "z", -1, e, wr, col, sand, root, loc)

    # back cushions lean on the back slats: bottom on the seat, top edge touching the slats
    bh, bt = p["back_cushion_h"], p["back_cushion_t"]
    tilt = math.radians(p["back_tilt_deg"])
    ct, sn = math.cos(tilt), math.sin(tilt)
    seat_top = seat_z0 + st
    by = slat_face - 0.002 - (bt / 2 * ct + bh / 2 * sn)
    bz = seat_top - 0.002 + (bt / 2 * sn + bh / 2 * ct)
    back_rot = (-tilt, 0, 0)
    for i in range(ns):
        cx = -inner / 2 + cw * (i + 0.5)
        size = (cw + 0.004, bt, bh)
        cushion(f"{n}_BackCushion{i}", size, {"-y": 0.024, "+y": 0.006, "+z": 0.008, "+x": 0.008, "-x": 0.008},
                col, sand, root, (cx, by, bz), back_rot, edge=e, hide="+y")
        face_welt(f"{n}_BackCushion{i}_PipingFront", size, "y", -1, e, wr, col, sand, root, (cx, by, bz), back_rot)

    # knife-edge scatter pillows leaning on the back cushions, piped round the seam
    mats = [clay, sage]
    pw, pt, ph = 0.46, 0.036, 0.44
    m_back = Matrix.Translation((0, by, bz)) @ Matrix.Rotation(-tilt, 4, "X")
    for k in range(p["pillows"]):
        sx = -1 if k % 2 == 0 else 1
        px = sx * (inner / 2 - 0.36) if ns > 1 else 0.0
        local = Vector((px, -bt / 2 - 0.05 - pt / 2, -bh / 2 + ph / 2 - 0.004))
        loc = m_back @ local
        rot = (-tilt - math.radians(6), 0, math.radians(7 * sx))
        ob = common.mesh_object(f"{n}_Pillow{k}",
                                common.cushion_bmesh((pw, pt, ph), cuts=2, edge=0.10,   # wide grid: a smooth dome
                                                     crown={"+y": 0.06, "-y": 0.06, "+z": -0.03, "-z": -0.015,
                                                            "+x": -0.028, "-x": -0.028}),
                                col, mats[k % 2], root)
        ob.location = loc
        ob.rotation_euler = rot
        common.add_subsurf(ob)
        common.box_uv(ob, tile=0.25)
        # the seam: the subdivided pillow's own mid-plane edge ring (exact fit)
        path, out = seam_ring(ob)
        pipe = welt(f"{n}_Pillow{k}_Piping", path, out, 0.0045, col, mats[k % 2], root)
        pipe.location = loc
        pipe.rotation_euler = rot

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
