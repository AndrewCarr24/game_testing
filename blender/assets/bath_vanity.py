"""Double vanity: a floating walnut cabinet (two drawer banks and a centre door) on a
recessed black plinth, a book-matched Calacatta slab top floating on a dark shadow
reveal, two low vessel basins of honed stone with brass drains, and two wall-mounted
brass spouts (rosette, tapered spout with an aerator) with lever mixers on their own
rosettes (the back of the asset is the wall plane).

Construction: the drawer and door fronts overlay a carcass that is set back behind them,
with a black recess between, so the 4 mm reveals read as real shadow lines. Brass bar
pulls stand off the fronts on two posts.

Also holds small fixture helpers shared by the bath assets (cone_between, axis_lathe,
wall_lever, aerator_tip, bar_pull).

Origin: floor centre. The front faces -Y, the wall is at +Y (depth / 2).
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import bath_common as bc  # noqa: E402

importlib.reload(common)
importlib.reload(bc)

NAME = "BathVanity"

P = dict(
    name=NAME,
    width=2.9,
    depth=0.58,
    plinth_h=0.10,
    plinth_inset=(0.06, 0.07),     # sides, front
    top_z=0.80,                    # top face of the counter
    top_t=0.04,
    gap=0.004,
    centre_w=0.46,
    basin_dx=0.76,                 # basin centres at +-basin_dx
    basin_r=0.245,
    basin_h=0.12,
)


# ------------------------------------------------------------ fixture helpers

def cone_between(bm, a, b, r1, r2, segs=12, cap=True):
    """Tapered cylinder from a (radius r1) to b (radius r2)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    rot = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    m = Matrix.Translation((a + b) / 2) @ rot
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=segs,
                          radius1=r1, radius2=r2, depth=d.length, matrix=m)


def axis_lathe(profile, segs, origin, axis, closed=False):
    """bc.lathe about Z, then turned so +Z points along `axis` and moved to `origin`."""
    bm = bc.lathe(profile, segs, closed=closed)
    rot = Vector(axis).normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(origin) @ rot, verts=bm.verts)
    return bm


def rosette(col, root, name, mat, centre, r, t=0.010, segs=28, axis=(0, -1, 0)):
    """Round wall/deck plate with an eased front edge."""
    prof = [(0.0, 0.0), (r, 0.0), (r, t * 0.55), (r - t * 0.45, t), (0.0, t)]
    return common.mesh_object(name, axis_lathe(prof, segs, centre, axis), col, mat, root)


def aerator_tip(col, root, name, mat, black, end, axis, r):
    """Short sleeve at a spout end with a dark mesh insert facing out along `axis`."""
    axis = Vector(axis).normalized()
    end = Vector(end)
    sleeve = [(0.0, -0.012), (r * 1.06, -0.012), (r * 1.06, 0.0), (r * 0.80, 0.0), (r * 0.80, -0.003), (0.0, -0.003)]
    common.mesh_object(name, axis_lathe(sleeve, 14, end, axis), col, mat, root)
    ins = [(0.0, -0.0028), (r * 0.80, -0.0028), (r * 0.80, -0.0018), (0.0, -0.0018)]
    common.mesh_object(name + "Insert", axis_lathe(ins, 10, end, axis, closed=True), col, black, root)


def wall_lever(col, root, name, mat, centre, length=0.080, angle=-14.0, r_hub=0.015):
    """Wall-mounted mixer lever: a rosette, a short round hub out of the wall and a
    tapered lever pointing forward (-Y), tilted down by `angle` degrees."""
    c = Vector(centre)
    rosette(col, root, name + "Rosette", mat, c, 0.034, t=0.008)
    bm = bmesh.new()
    hub_end = c + Vector((0, -0.044, 0))
    cone_between(bm, c + Vector((0, -0.006, 0)), hub_end, r_hub, r_hub * 0.9, 16)
    cone_between(bm, hub_end, hub_end + Vector((0, -0.004, 0)), r_hub * 0.9, r_hub * 0.7, 16)
    a = math.radians(angle)
    start = hub_end + Vector((0, 0.016, 0.0))
    tip = start + Vector((0, -length * math.cos(a), length * math.sin(a)))
    cone_between(bm, start, tip, 0.0078, 0.0056, 10)
    end = tip + (tip - start).normalized() * 0.004
    cone_between(bm, tip, end, 0.0056, 0.0040, 10)
    lever = common.mesh_object(name, bm, col, mat, root)
    # flatten the lever a little (wider than it is tall) about its own axis
    for v in lever.data.vertices:
        if (v.co - c).y < -0.0495:
            v.co.z = start.z + (v.co.z - start.z - (v.co.y - start.y) * math.tan(-a)) * 0.7 + (v.co.y - start.y) * math.tan(-a)


def bar_pull(col, root, name, mat, centre, length, vertical=False, r=0.0055, stand=0.024, post_r=0.0045):
    """Round bar pull on two posts, standing off a front whose face is at centre.y."""
    c = Vector(centre)
    bm = bmesh.new()
    d = Vector((0, 0, 1)) if vertical else Vector((1, 0, 0))
    out = Vector((0, -stand, 0))
    a, b = c + out - d * length / 2, c + out + d * length / 2
    cone_between(bm, a, b, r, r, 10)
    inset = min(0.035, length * 0.18)
    for p in (a + d * inset, b - d * inset):
        cone_between(bm, p - out + Vector((0, 0.001, 0)), p, post_r * 1.25, post_r, 8)
    return common.mesh_object(name, bm, col, mat, root)


def soft_extrude(outline, x0, x1, ease=0.006, inset=0.004):
    """Closed (y, z) counter-clockwise outline extruded along X from x0 to x1. The end
    slices are pulled `ease` metres in and shrunk `inset` metres along the outline's inward
    normals, so the ends read soft (folded or bound cloth) instead of cut. Capped ends."""
    m = len(outline)
    area = sum(outline[i][0] * outline[(i + 1) % m][1] - outline[(i + 1) % m][0] * outline[i][1] for i in range(m))
    sgn = 1.0 if area > 0 else -1.0
    shrunk = []
    for i in range(m):
        (ay, az), (by, bz) = outline[i - 1], outline[(i + 1) % m]
        dy, dz = by - ay, bz - az
        ln = math.hypot(dy, dz) or 1.0
        ny, nz = -dz / ln * sgn, dy / ln * sgn          # inward normal for a CCW outline
        shrunk.append((outline[i][0] + ny * inset, outline[i][1] + nz * inset))
    slices = [(x0, shrunk), (x0 + ease, outline), (x1 - ease, outline), (x1, shrunk)]
    bm = bmesh.new()
    rows = [[bm.verts.new((x, y, z)) for y, z in ol] for x, ol in slices]
    for ra, rb in zip(rows, rows[1:]):
        for i in range(m):
            j = (i + 1) % m
            bm.faces.new((ra[i], ra[j], rb[j], rb[i]))
    bm.faces.new(rows[0][::-1])
    bm.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def round_outline(y0, y1, z0, z1, r_front, r_back, segs=4):
    """(y, z) outline of a folded-cloth section: the -Y side rounded by r_front (a fold),
    the +Y side by r_back (a hem). Counter-clockwise."""
    pts = []
    for (cy_, cz_, r, a0) in ((y1 - r_back, z0 + r_back, r_back, -90), (y1 - r_back, z1 - r_back, r_back, 0),
                              (y0 + r_front, z1 - r_front, r_front, 90), (y0 + r_front, z0 + r_front, r_front, 180)):
        for k in range(segs + 1):
            a = math.radians(a0 + 90 * k / segs)
            pts.append((cy_ + r * math.cos(a), cz_ + r * math.sin(a)))
    out = []
    for q in pts:
        if not out or abs(q[0] - out[-1][0]) + abs(q[1] - out[-1][1]) > 1e-6:
            out.append(q)
    if abs(out[0][0] - out[-1][0]) + abs(out[0][1] - out[-1][1]) < 1e-6:
        out.pop()
    return out


def basin_profile(r, h, wall=0.014):
    """(r, z) of a shallow bowl: foot, belly, rounded flat rim, sloping inside to a
    sunken drain seat."""
    pts = [(0.0, 0.0), (r * 0.52, 0.0), (r * 0.70, 0.006), (r * 0.90, 0.045), (r, 0.092), (r, h - 0.012),
           (r - 0.004, h - 0.004), (r - wall / 2, h), (r - wall + 0.002, h - 0.004), (r - wall, h - 0.012),
           (r - wall - 0.004, h - 0.045), (r * 0.62, 0.034), (r * 0.30, 0.024), (0.034, 0.020), (0.030, 0.014),
           (0.0, 0.014)]
    return pts


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    walnut, black, brass = materials.walnut(), materials.black_metal(), bc.brass()
    marble, stone = bc.marble_wall(), bc.stone()

    W, D, ph = p["width"], p["depth"], p["plinth_h"]
    zt, tt, gap = p["top_z"], p["top_t"], p["gap"]
    yb, yf = D / 2, -D / 2                      # back (wall) and front of the cabinet
    top_front_over = 0.02
    reveal_h = 0.010                            # dark shadow line between cabinet and slab

    # ---- recessed plinth
    pis, pif = p["plinth_inset"]
    bc.box(col, root, f"{n}_Plinth", (W - 2 * pis, D - pif - 0.02, ph), (0, (yf + pif + yb - 0.02) / 2, ph / 2),
           black, bevel=0.003)

    # ---- carcass (set back behind the fronts), black recess behind the reveals, fronts
    z0, z1 = ph, zt - tt - reveal_h
    cw = W - 0.04
    ft = 0.022
    yfront = yf + ft / 2                        # centre of the fronts (their face is at yf)
    set_back = 0.014                            # fronts stand this far proud of the carcass face
    cy0 = yf + ft + set_back                    # carcass front face
    gt = 0.018                                  # end gables run forward to the back of the fronts
    bc.box(col, root, f"{n}_Carcass", (cw - 2 * gt, yb - cy0, z1 - z0), (0, (yb + cy0) / 2, (z0 + z1) / 2),
           walnut, bevel=0.002, uv_tile=0.5)
    for sx in (-1, 1):
        bc.box(col, root, f"{n}_CarcassGable_{sx}", (gt, yb - (yf + ft), z1 - z0),
               (sx * (cw / 2 - gt / 2), (yb + yf + ft) / 2, (z0 + z1) / 2), walnut, bevel=0.002, uv_tile=0.5)
    bc.box(col, root, f"{n}_RecessShadow", (cw - 2 * gt, set_back + 0.002, z1 - z0 - 0.004),
           (0, yf + ft + set_back / 2, (z0 + z1) / 2), black, bevel=0.0)
    # dark reveal under the slab, set back from the front
    bc.box(col, root, f"{n}_TopReveal", (cw - 0.02, D - 0.06, reveal_h + 0.002), (0, yb - (D - 0.06) / 2, z1 + reveal_h / 2),
           black, bevel=0.0)
    bank_w = (cw - p["centre_w"] - 4 * gap) / 2
    xs = [(-cw / 2 + gap + bank_w / 2, bank_w, "L"), (0.0, p["centre_w"], "C"), (cw / 2 - gap - bank_w / 2, bank_w, "R")]
    fz0, fz1 = z0 + gap, z1 - gap
    for xc, w, tag in xs:
        if tag == "C":
            panels = [("Door", fz0, fz1)]
        else:
            split = fz0 + (fz1 - fz0) * 0.60
            panels = [("DrawerLow", fz0, split - gap / 2), ("DrawerTop", split + gap / 2, fz1)]
        for nm, a, b in panels:
            bc.box(col, root, f"{n}_Front_{tag}_{nm}", (w, ft, b - a), (xc, yfront, (a + b) / 2), walnut,
                   bevel=0.0018, uv_tile=0.5)
            if tag == "C":
                bar_pull(col, root, f"{n}_Pull_{tag}", brass, (xc + w / 2 - 0.05, yf, (a + b) / 2 + 0.06), 0.30,
                         vertical=True)
            else:
                pw = min(w - 0.16, 0.36)
                bar_pull(col, root, f"{n}_Pull_{tag}_{nm}", brass, (xc, yf, b - 0.045), pw)

    # ---- marble top, slightly proud at the front, eased edges
    tw, td = W + 0.0, D + top_front_over
    bc.box(col, root, f"{n}_Top", (tw, td, tt), (0, yb - td / 2, zt - tt / 2), marble, bevel=0.0045, uv_tile=1.0)

    # ---- basins, drains, wall spouts and lever mixers
    for sgn, tag in ((-1, "L"), (1, "R")):
        cx = sgn * p["basin_dx"]
        cy = (yf + yb) / 2 + 0.01
        b = common.mesh_object(f"{n}_Basin_{tag}", bc.lathe(basin_profile(p["basin_r"], p["basin_h"]), 48), col, stone, root)
        b.location = (cx, cy, zt)
        bc.cylindrical_uv(b, tile=1.0)
        # brass drain cap sitting in the sunken seat, with a thin dark ring round it
        drain = bc.lathe([(0.0, 0.0175), (0.026, 0.0175), (0.028, 0.0155), (0.028, 0.0140), (0.0, 0.0140)], 24)
        common.mesh_object(f"{n}_Drain_{tag}", drain, col, brass, root).location = (cx, cy, zt)
        # wall spout: rosette, tapered spout with a slight drop, aerator
        sz = zt + 0.30
        rosette(col, root, f"{n}_SpoutRosette_{tag}", brass, (cx, yb, sz), 0.045, t=0.010)
        tip_y = cy + 0.06
        sp = bmesh.new()
        cone_between(sp, (cx, yb - 0.008, sz), (cx, tip_y + 0.004, sz - 0.004), 0.0125, 0.0100, 14, cap=False)
        common.mesh_object(f"{n}_Spout_{tag}", sp, col, brass, root)
        tipb = bmesh.new()
        cone_between(tipb, (cx, tip_y + 0.006, sz - 0.004), (cx, tip_y - 0.004, sz - 0.006), 0.0100, 0.0100, 14, cap=False)
        common.mesh_object(f"{n}_SpoutEnd_{tag}", tipb, col, brass, root)
        # aerator facing down at the end of the spout
        aerator_tip(col, root, f"{n}_Aerator_{tag}", brass, black, (cx, tip_y - 0.002, sz - 0.0145), (0, 0, -1), 0.0105)
        cap = bmesh.new()
        cone_between(cap, (cx, tip_y - 0.004, sz - 0.006), (cx, tip_y - 0.012, sz - 0.006), 0.0100, 0.0094, 14)
        common.mesh_object(f"{n}_SpoutCap_{tag}", cap, col, brass, root)
        # lever mixer to the outer side of the spout
        wall_lever(col, root, f"{n}_Lever_{tag}", brass, (cx + sgn * 0.15, yb, sz - 0.01))

    bc.merge(root, bc.children(root, "_Carcass", "_Front_"), f"{n}_Cabinet")
    bc.merge(root, bc.children(root, "_RecessShadow", "_TopReveal", "Insert"), f"{n}_PipingShadow")
    bc.merge(root, bc.by_material(root, brass), f"{n}_PipingBrass")
    bc.merge(root, bc.children(root, "_Basin_"), f"{n}_Basins")
    return root, bc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
