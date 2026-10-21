"""Low-slung modern sofa: upholstered plinth deck with squared padded arms, loose
seat and back cushions (soft crowns, piped seams), two scatter pillows, on a recessed
black plinth. Also provides `module()` which living_sectional builds on.

Units are metres. The sofa faces -Y (backrest at +Y); the origin is the floor centre.
"""
import importlib
import math
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402  (hiding spot, prompts/interactivity.md)

importlib.reload(ix_common)

NAME = "LivingSofa"

P = dict(
    name=NAME,
    width=2.60,
    depth=1.00,
    fabric_name="M_Fabric_Oat",
    fabric=(0.50, 0.44, 0.35),
    pillow_name="M_Fabric_Ink",
    pillow=(0.020, 0.032, 0.060),
    pillows=2,
    arm_w=0.20,
    deck_z=(0.07, 0.27),      # plinth top, deck top
    seat_t=0.19,              # seat cushion thickness
    back_h=0.40,              # back cushion height
    back_t=0.21,
    back_tilt_deg=11.0,
    frame_back_top=0.64,
    arm_top=0.60,
    cuts=3,
    cuts_small=2,
    leg="black",              # recessed plinth colour: "black" or "bronze"
    throw=("M_Fabric_Cognac", (0.20, 0.085, 0.035)),   # folded throw over the right arm (None: no throw)
    hide=True,                # a hiding spot: crouched behind the back (where there's room, the engine checks)
)


def cushion(col, parent, mat, name, size, crown, loc, rot=(0, 0, 0), cuts=4, edge=0.03, uv=0.25):
    ob = common.mesh_object(name, common.cushion_bmesh(size, cuts=cuts, edge=edge, crown=crown),
                            col, mat, parent)
    ob.location = loc
    ob.rotation_euler = rot
    common.add_subsurf(ob)
    common.box_uv(ob, tile=uv)
    return ob


# ------------------------------------------------------------------ welts (piping)
# Every welt of one module goes into a single "<Asset>_Piping<tag>" mesh (no collider:
# COLLIDER_SKIP has "Piping"), swept as a slim 4-sided smooth-shaded tube that sits half
# buried in the rounded edge of the subdivided cushion, so it reads as a sewn cord.

PIPE_R = 0.0052
PIPE_SIDES = 4


def _round_rect(hx, hy, r, segs=2):
    """Closed CCW rounded rectangle (2D points), half extents hx, hy, corner radius r."""
    r = min(r, hx * 0.9, hy * 0.9)
    pts = []
    for (cx, cy), a0 in (((hx, hy), 0), ((-hx, hy), 90), ((-hx, -hy), 180), ((hx, -hy), 270)):
        ox, oy = cx - math.copysign(r, cx), cy - math.copysign(r, cy)
        for k in range(segs + 1):
            a = math.radians(a0 + 90 * k / segs)
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return pts


def tube_into(bm, pts, normal, r=PIPE_R, sides=PIPE_SIDES, closed=True):
    """Sweep a `sides`-gon of radius r along 3D `pts` (lying roughly in a plane with
    `normal`) into bm."""
    pts = [Vector(p) for p in pts]
    N = Vector(normal).normalized()
    n = len(pts)
    rings = []
    for i in range(n):
        a = pts[i - 1] if (closed or i > 0) else pts[i]
        b = pts[(i + 1) % n] if (closed or i < n - 1) else pts[i]
        t = (b - a).normalized()
        nn = (N - t * N.dot(t)).normalized()
        bb = t.cross(nn)
        rings.append([bm.verts.new(pts[i] + r * (math.cos(2 * math.pi * k / sides) * nn +
                                                  math.sin(2 * math.pi * k / sides) * bb)) for k in range(sides)])
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        for k in range(sides):
            q = (k + 1) % sides
            bm.faces.new((rings[i][k], rings[j][k], rings[j][q], rings[i][q]))


def face_welt(bm, ob, size, axis, sign, edge, inset=0.0046, corner=None):
    """Welt round the rim of one face (normal sign*axis) of a cushion object `ob`
    (centred cushion_bmesh of `size`), in its parent's space."""
    a = "xyz".index(axis)
    o1, o2 = [b for b in range(3) if b != a]
    h = [s / 2 for s in size]
    e = min(edge, min(h) * 0.45)
    loop = _round_rect(h[o1] - inset, h[o2] - inset, corner if corner is not None else e * 0.75)
    M = ob.matrix_basis
    pts = []
    for u, v in loop:
        p = [0.0, 0.0, 0.0]
        p[a] = sign * (h[a] - inset)
        p[o1], p[o2] = u, v
        pts.append(M @ Vector(p))
    nrm = [0.0, 0.0, 0.0]
    nrm[a] = sign
    tube_into(bm, pts, M.to_3x3() @ Vector(nrm))


def module(p, col, root, mat, pmat, n, x0, x1, y0, y1, back=True, arms=None, tag="", seat_w=0.95, split_y=None):
    """One upholstered module occupying plan rect x0..x1, y0..y1 (back at y1).
    arms: {"L": (ya, yb) | None, "R": ...} y extent of each side arm.
    split_y: also split the seat cushions front/back at this y (a chaise's long seat)."""
    arms = arms or {}
    z0, z1 = p["deck_z"]
    aw = p["arm_w"]
    parts = []
    welts = bmesh.new()
    # deck (structure the cushions sit on), full footprint; its front rail shows below the seats
    ax0 = x0 + (aw if arms.get("L") else 0)
    ax1 = x1 - (aw if arms.get("R") else 0)
    deck = common.mesh_object(f"{n}_Deck{tag}", common.box_bmesh((x1 - x0, y1 - y0, z1 - z0)), col, mat, root)
    deck.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    common.add_bevel(deck, 0.014, segments=2)
    common.box_uv(deck, 0.25)
    parts.append(deck)
    # recessed plinth (a shadow line under the upholstery), its top edge eased
    inset = 0.07
    plinth = common.mesh_object(f"{n}_Plinth{tag}",
                                common.box_bmesh((x1 - x0 - 2 * inset, y1 - y0 - 2 * inset, z0)),
                                col, materials.black_metal() if p["leg"] == "black" else materials.bronze(), root,
                                smooth=False)
    plinth.location = ((x0 + x1) / 2, (y0 + y1) / 2, z0 / 2)
    common.add_bevel(plinth, 0.003, segments=1)
    parts.append(plinth)
    # back rail frame: an upholstered rail the back cushions lean on, welted along its top
    bt = 0.16
    if back:
        rs = (ax1 - ax0, bt, p["frame_back_top"] - z1 + 0.04)
        rail = cushion(col, root, mat, f"{n}_BackFrame{tag}", rs,
                       {"+z": 0.010, "-y": 0.006}, ((ax0 + ax1) / 2, y1 - bt / 2, (z1 - 0.04 + p["frame_back_top"]) / 2),
                       cuts=p["cuts_small"], edge=0.035)
        parts.append(rail)
    # arms: padded track arms, welted round both side panels (top and front edges)
    for side, sx in (("L", x0 + aw / 2), ("R", x1 - aw / 2)):
        ext = arms.get(side)
        if not ext:
            continue
        ya, yb = ext
        asz = (aw, yb - ya, p["arm_top"] - z0)
        arm = cushion(col, root, mat, f"{n}_Arm{side}{tag}", asz,
                      {"+z": 0.018, "+x": 0.008, "-x": 0.008, "-y": 0.012}, (sx, (ya + yb) / 2, (z0 + p["arm_top"]) / 2),
                      cuts=p["cuts_small"], edge=0.04)
        for sg in (1, -1):
            face_welt(welts, arm, asz, "x", sg, 0.04)
        parts.append(arm)
    # seat cushions: boxed, welted top and bottom, crowned, the fronts proud of the deck
    seat_y1 = y1 - (bt if back else 0.0) - 0.005
    sw_total = ax1 - ax0
    k = max(1, round(sw_total / seat_w))
    sw = sw_total / k
    st = p["seat_t"]
    spans = [(y0 - 0.015, seat_y1)] if split_y is None else [(y0 - 0.015, split_y - 0.006), (split_y + 0.006, seat_y1)]
    for i in range(k):
        cx = ax0 + sw * (i + 0.5)
        for si, (sa, sb) in enumerate(spans):
            ssz = (sw - 0.012, sb - sa, st)
            seat = cushion(col, root, mat, f"{n}_Seat{tag}{i}" + ("" if si == 0 else f"_{si}"), ssz,
                           {"+z": 0.032, "-y": 0.020, "+y": 0.0 if si == len(spans) - 1 else 0.012,
                            "+x": 0.008, "-x": 0.008},
                           (cx, (sa + sb) / 2, z1 + st / 2 - 0.005),
                           cuts=p["cuts"], edge=0.03)
            for sg in (1, -1):
                face_welt(welts, seat, ssz, "z", sg, 0.03)
            parts.append(seat)
    # back cushions: loose, plump at the front, leaning on the rail and sunk into the seat
    if back:
        bh, bth = p["back_h"], p["back_t"]
        tilt = math.radians(p["back_tilt_deg"])
        for i in range(k):
            cx = ax0 + sw * (i + 0.5)
            zc = z1 + st + bh / 2 * math.cos(tilt) - 0.018
            yc = y1 - bt - bth / 2 * math.cos(tilt) - 0.002
            bsz = (sw - 0.014, bth, bh)
            bc = cushion(col, root, mat, f"{n}_BackCushion{tag}{i}", bsz,
                         {"-y": 0.045, "+y": 0.004, "+z": 0.026, "+x": 0.010, "-x": 0.010},
                         (cx, yc, zc), rot=(-tilt, 0, 0), cuts=p["cuts"], edge=0.035)
            face_welt(welts, bc, bsz, "y", -1, 0.035)
            parts.append(bc)
    bmesh.ops.recalc_face_normals(welts, faces=welts.faces[:])
    pipe = common.mesh_object(f"{n}_Piping{tag}", welts, col, mat, root)
    common.box_uv(pipe, 0.25)
    parts.append(pipe)
    return parts


def throw_bmesh(x_in, x_out, za, y0, y1, t=0.012, drop_in=0.13, drop_out=0.30, seed=3):
    """A folded throw draped over a track arm (plan x_in..x_out, top za), y0..y1 wide:
    a slab of thickness t following the arm's section, its hanging ends rippled."""
    import random
    rnd = random.Random(seed)
    g = t / 2 + 0.002
    rc = 0.035
    sec = [(x_in - g, za - drop_in), (x_in - g, za - drop_in * 0.5), (x_in - g, za - rc)]
    for k in range(1, 3):
        a = math.pi / 2 * k / 3
        sec.append((x_in + rc - (rc + g) * math.cos(a), za - rc + (rc + g) * math.sin(a)))
    sec += [(x_in + rc, za + g), ((x_in + x_out) / 2, za + g + 0.012), (x_out - rc, za + g)]
    for k in range(1, 3):
        a = math.pi / 2 * k / 3
        sec.append((x_out - rc + (rc + g) * math.sin(a), za - rc + (rc + g) * math.cos(a)))
    sec += [(x_out + g, za - rc), (x_out + g, za - drop_out * 0.5), (x_out + g, za - drop_out)]
    m = 5
    bm = bmesh.new()
    ns = len(sec)
    # outward normals of the section (2D) for the thickness
    nrm = []
    for i in range(ns):
        a, b = sec[max(i - 1, 0)], sec[min(i + 1, ns - 1)]
        tx, tz = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(tx, tz)
        nrm.append((tz / ln, -tx / ln))
    ph = [rnd.uniform(0, 6.28) for _ in range(2)]
    grid = {}
    for side, off in (("o", t / 2), ("i", -t / 2)):
        for i, ((x, z), (nx, nz)) in enumerate(zip(sec, nrm)):
            hang = max(0.0, (za - rc - z) / 0.3)            # 0 on the arm, 1 at the hem
            for j in range(m + 1):
                v = j / m
                y = y0 + (y1 - y0) * v
                ripple = -0.006 * hang * (0.5 + 0.5 * math.sin(v * math.pi * 3 + ph[0 if x < x_in + 0.05 else 1]))
                grid[(side, i, j)] = bm.verts.new((x + (off + ripple) * nx,
                                                   y + 0.02 * hang * math.sin(v * 2.2 + ph[1]),
                                                   z + (off + ripple) * nz))
    def q(a, b, c, d):
        bm.faces.new((grid[a], grid[b], grid[c], grid[d]))
    for i in range(ns - 1):
        for j in range(m):
            q(("o", i, j), ("o", i + 1, j), ("o", i + 1, j + 1), ("o", i, j + 1))
            q(("i", i, j + 1), ("i", i + 1, j + 1), ("i", i + 1, j), ("i", i, j))
    for i in range(ns - 1):       # selvedges along y0 / y1
        q(("o", i, 0), ("i", i, 0), ("i", i + 1, 0), ("o", i + 1, 0))
        q(("o", i + 1, m), ("i", i + 1, m), ("i", i, m), ("o", i, m))
    for i in (0, ns - 1):         # hems
        for j in range(m):
            q(("o", i, j), ("o", i, j + 1), ("i", i, j + 1), ("i", i, j))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def pillow_bmesh(w, h, t, grid=4, pinch=0.07):
    """Knife-edge scatter pillow in the XZ plane, thickness along Y: two stuffed faces
    sewn together at a seam ring (creased), the side midpoints pulled in so the
    corners stand out as soft "ears". Returns (bm, seam points) for a welt."""
    bm = bmesh.new()
    crease = bm.edges.layers.float.get("crease_edge") or bm.edges.layers.float.new("crease_edge")
    g = grid
    vs = {}

    def pos(i, j, s):
        u, v = -1 + 2 * i / g, -1 + 2 * j / g
        x = u * w / 2 * (1 - pinch * (1 - v * v))
        z = v * h / 2 * (1 - pinch * (1 - u * u))
        fill = ((1 - u * u) * (1 - v * v)) ** 0.55
        return Vector((x, s * t / 2 * fill, z))

    for s in (-1, 1):
        for i in range(g + 1):
            for j in range(g + 1):
                edge = i in (0, g) or j in (0, g)
                key = (i, j, 0 if edge else s)
                if key not in vs:
                    vs[key] = bm.verts.new(pos(i, j, s if not edge else 0))
    for s in (-1, 1):
        def V(i, j):
            return vs[(i, j, 0 if (i in (0, g) or j in (0, g)) else s)]
        for i in range(g):
            for j in range(g):
                q = (V(i, j), V(i + 1, j), V(i + 1, j + 1), V(i, j + 1))
                bm.faces.new(q if s > 0 else q[::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ring = []
    for i in range(g):
        ring.append((i, 0))
    for j in range(g):
        ring.append((g, j))
    for i in range(g, 0, -1):
        ring.append((i, g))
    for j in range(g, 0, -1):
        ring.append((0, j))
    for e in bm.edges:
        a, b = e.verts
        if abs(a.co.y) < 1e-9 and abs(b.co.y) < 1e-9:
            e[crease] = 0.75
    seam = [vs[(i, j, 0)].co.copy() for i, j in ring]
    return bm, seam


def pillow(col, root, mat, name, loc, rot, size=0.46, cuts=2, aspect=0.92, thick=0.17):
    w, h, t = size, size * aspect, thick
    bm, seam = pillow_bmesh(w, h, t)
    ob = common.mesh_object(name, bm, col, mat, root)
    ob.location = loc
    ob.rotation_euler = rot
    common.add_subsurf(ob)
    common.box_uv(ob, tile=0.25)
    # welt along the seam (subdivision pulls the seam in a little at the corners)
    wb = bmesh.new()
    sm = [Vector((p.x * 0.985, 0.0, p.z * 0.985)) for p in seam]
    tube_into(wb, sm, (0, 1, 0), r=0.0045)
    bmesh.ops.recalc_face_normals(wb, faces=wb.faces[:])
    pw = common.mesh_object(f"{name}Piping", wb, col, mat, ob)
    common.box_uv(pw, 0.25)
    return ob


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    mat = materials.fabric(p["fabric_name"], p["fabric"])
    pmat = materials.fabric(p["pillow_name"], p["pillow"])
    w, d = p["width"], p["depth"]
    module(p, col, root, mat, pmat, n, -w / 2, w / 2, -d / 2, d / 2,
           arms={"L": (-d / 2, d / 2), "R": (-d / 2, d / 2)})
    z_seat = p["deck_z"][1] + p["seat_t"]
    if p.get("throw"):
        tname, tcol = p["throw"]
        x_out = w / 2
        th = common.mesh_object(f"{n}_ThrowNoCollide",
                                throw_bmesh(x_out - p["arm_w"], x_out, p["arm_top"] + 0.012, -d / 2 + 0.16, -d / 2 + 0.62),
                                col, materials.fabric(tname, tcol), root)
        common.box_uv(th, 0.25)
    if p["pillows"] == 1:
        # a single lumbar pillow, centred, leaning into the back cushion
        bt = 0.16
        yb = d / 2 - bt - p["back_t"] * 0.9 - 0.04
        pillow(col, root, pmat, f"{n}_Pillow0", (0.0, yb, z_seat + 0.15), (-math.radians(16), 0, math.radians(3)),
               size=min(0.56, w - 2 * p["arm_w"] - 0.12), aspect=0.55, thick=0.15)
    for i in range(p["pillows"] if p["pillows"] != 1 else 0):
        sx = -1 if i == 0 else 1
        pillow(col, root, pmat, f"{n}_Pillow{i}",
               (sx * (w / 2 - p["arm_w"] - 0.27), 0.0, z_seat + 0.20),
               (-math.radians(12), 0, math.radians(-8 if i == 0 else 7)))
    if p.get("hide") and w >= 1.8:
        # hiding spot (open cover; sofas, not the armchairs built from this): crouched a hand behind the back, peeking over it; out behind it
        ix_common.hide_spot(root, col, n, (0.0, d / 2 + 0.3, 0.74), [(0.0, d / 2 + 0.85, 0.0), (0.6, d / 2 + 0.85, 0.0),
                                                                   (-0.6, d / 2 + 0.85, 0.0)],
                            "Hide behind the sofa", "Stand up", cover="open", facing=(0, -1, 0), pitch=8,
                            look={"yaw": 55, "pitch": 22})
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
