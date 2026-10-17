"""Bedside table lamp: a weighted smoked-oak base on a recessed black foot, a slim
bronze stem with a bead and a socket, a three-arm bronze harness, a warm bulb and a
glowing linen drum shade with real wall thickness, bronze rims and open ends.

Everything round is lathed from a hand-made profile. Origin: centre of the underside
(z = 0). Front faces -Y (the lamp is rotationally symmetric). Units are metres.
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "TableLamp"

P = dict(
    name=NAME,
    segments=48,             # around the shade and rims
    base_segments=32,        # around the base
    small_segments=20,       # around stem, socket, bulb
    height=0.62,
    # shade (drum): outer radius, wall thickness, z range
    shade_r=0.1778,
    shade_wall=0.004,
    shade_z=(0.36, 0.62),
    rim_h=0.008,             # bronze rim band height
    rim_w=0.0085,            # bronze rim radial width (straddles the wall)
    # base
    foot_r=0.060, foot_h=0.006,
    base_r=0.080, base_top=0.088,
    stem_r=0.0065, stem_top=0.396,
    bulb_z=0.478, bulb_r=0.031,
    arms=3,
    emission=1.5,
)


# ------------------------------------------------------------------ geometry

def lathe(profile, segs, closed=True, sharp=40.0):
    """Revolve `profile` [(r, z), ...] about the Z axis into a bmesh.
    Points with r == 0 collapse to a single vertex on the axis. Profile corners
    turning by more than `sharp` degrees get sharp edges (so a 4-point profile
    still shades as a crisp ring while the surface round it stays smooth)."""
    bm = bmesh.new()
    rows = []
    for r, z in profile:
        if abs(r) < 1e-9:
            rows.append([bm.verts.new((0.0, 0.0, z))] * segs)
        else:
            rows.append([bm.verts.new((r * math.cos(2 * math.pi * s / segs),
                                       r * math.sin(2 * math.pi * s / segs), z))
                         for s in range(segs)])
    n = len(profile)
    for i in range(n if closed else n - 1):
        a, b = rows[i], rows[(i + 1) % n]
        for s in range(segs):
            t = (s + 1) % segs
            quad = []
            for v in (a[s], a[t], b[t], b[s]):
                if v not in quad:
                    quad.append(v)
            if len(quad) >= 3:
                bm.faces.new(quad)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for i, (r, z) in enumerate(profile):
        if abs(r) < 1e-9 or (not closed and i in (0, n - 1)):
            continue
        pr, nx = profile[(i - 1) % n], profile[(i + 1) % n]
        d1, d2 = (r - pr[0], z - pr[1]), (nx[0] - r, nx[1] - z)
        ang = math.degrees(abs(math.atan2(d1[0] * d2[1] - d1[1] * d2[0], d1[0] * d2[0] + d1[1] * d2[1])))
        if ang > sharp:
            for s in range(segs):
                e = bm.edges.get((rows[i][s], rows[i][(s + 1) % segs]))
                if e is not None and e.is_valid:
                    e.smooth = False
    return bm


def rounded_ring(r0, r1, z0, z1, radius, segments=3):
    """Rounded-rectangle cross-section (a ring of r0..r1, z0..z1) as a closed
    profile, with every corner filleted."""
    pts = [(r0, 0, z0), (r1, 0, z0), (r1, 0, z1), (r0, 0, z1)]
    out = common.fillet_polyline(pts, radius, segments=segments, closed=True)
    return [(p.x, p.z) for p in out]


def rim_profile(r0, r1, z0, z1, c=0.0016):
    """Small rim band with chamfered outer corners (reads rounded when lit)."""
    return [(r0, z0), (r1 - c, z0), (r1, z0 + c), (r1, z1 - c), (r1 - c, z1), (r0, z1)]


def catmull(pts, per=8):
    """Catmull-Rom spline through pts [(r, z)], dense polyline."""
    q = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(q) - 2):
        p0, p1, p2, p3 = q[i - 1], q[i], q[i + 1], q[i + 2]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t +
                                    (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 +
                                    (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(q[-2])
    return out


def cylinder_between(bm, a, b, radius, segs=8):
    a, b = Vector(a), Vector(b)
    d = b - a
    rot = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    m = Matrix.Translation((a + b) / 2) @ rot
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                          radius1=radius, radius2=radius, depth=d.length, matrix=m)


def cylindrical_uv(ob, circumference_tiles=1.0, tile=0.5):
    """Turned-wood UVs: u along the axis (grain runs vertically), v once round the
    circumference (seamless); flat caps use a planar projection."""
    me = ob.data
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        if abs(poly.normal.z) > 0.92:
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                uv.data[li].uv = (co.x / tile, co.y / tile)
            continue
        angs = []
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            angs.append(math.atan2(co.y, co.x))
        a0 = angs[0]
        for li, a in zip(poly.loop_indices, angs):
            d = a - a0
            d -= 2 * math.pi * round(d / (2 * math.pi))
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (co.z / tile, (a0 + d) / (2 * math.pi) * circumference_tiles)


# --------------------------------------------------------------------- build

def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    seg, sseg, bseg = p["segments"], p["small_segments"], p["base_segments"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    oak = materials.smoked_oak()
    bronze = materials.bronze()
    dark = materials.black_metal()
    shade_mat = materials.emissive("M_LampShade_Warm", (1.0, 0.78, 0.52), p["emission"])
    bulb_mat = materials.emissive("M_LampBulb", (1.0, 0.92, 0.74), 6.0)

    # ---- recessed black foot (shadow gap under the base) -------------------
    fr, fh = p["foot_r"], p["foot_h"]
    foot = common.mesh_object(f"{n}_Foot", lathe([(0, 0), (fr, 0), (fr, fh), (0, fh)], 24),
                              col, dark, root, smooth=False)

    # ---- weighted oak base: soft pebble silhouette ------------------------
    br, bt = p["base_r"], p["base_top"]
    prof = catmull([(0.0, fh), (br - 0.006, fh), (br, fh + 0.014),
                    (br, 0.046), (br - 0.007, 0.066), (br - 0.026, 0.083),
                    (0.030, bt), (0.0, bt)], per=2)
    # drop the duplicated tail points the spline adds, keep the axis ends
    dedup = []
    for pt in prof:
        if not dedup or abs(pt[0] - dedup[-1][0]) + abs(pt[1] - dedup[-1][1]) > 1e-6:
            dedup.append(pt)
    dedup[0] = (0.0, fh)
    dedup[-1] = (0.0, bt)
    base = common.mesh_object(f"{n}_Base", lathe(dedup, bseg), col, oak, root)
    cylindrical_uv(base)

    # thin bronze inlay band round the waist of the base
    common.mesh_object(f"{n}_BaseBand",
                       lathe([(br - 0.003, 0.031), (br + 0.0012, 0.031), (br + 0.0012, 0.035), (br - 0.003, 0.035)], bseg),
                       col, bronze, root)

    # ---- bronze collar and stem ----------------------------------------------
    sr = p["stem_r"]
    collar_bm = lathe([(0.0, bt - 0.003), (0.024, bt - 0.003), (0.020, bt + 0.010), (0.0, bt + 0.010)], sseg)
    bronze_stem = common.mesh_object(f"{n}_Collar", collar_bm, col, bronze, root)

    stem_pts = [(0.0, bt + 0.004), (sr, bt + 0.004), (sr, p["stem_top"]), (0.0, p["stem_top"])]
    stem = common.mesh_object(f"{n}_Stem", lathe(stem_pts, sseg), col, bronze, root)

    # a slim bead on the stem (rotationally symmetric, flattened sphere)
    bead_z, bead_r, bead_h = 0.215, 0.0185, 0.012
    bead_prof = [(0.0, bead_z - bead_h)]
    steps = 8
    for i in range(1, steps):
        a = -math.pi / 2 + math.pi * i / steps
        bead_prof.append((bead_r * math.cos(a), bead_z + bead_h * math.sin(a)))
    bead_prof.append((0.0, bead_z + bead_h))
    bead = common.mesh_object(f"{n}_Bead", lathe(bead_prof, sseg), col, bronze, root)

    # ---- socket: a bronze cup under the bulb, black insulator ring ------------
    st = p["stem_top"]
    socket = common.mesh_object(
        f"{n}_Socket",
        lathe([(0.0, st - 0.004), (0.0125, st - 0.004), (0.0165, st + 0.006),
               (0.0165, st + 0.026), (0.0135, st + 0.037), (0.0, st + 0.037)], sseg, sharp=70), col, bronze, root)
    ring = common.mesh_object(
        f"{n}_SocketRing",
        lathe([(0.0125, st + 0.020), (0.0172, st + 0.020), (0.0172, st + 0.027), (0.0125, st + 0.027)], sseg),
        col, dark, root)

    # ---- bulb: a small globe with a neck ---------------------------------------
    bz, brad = p["bulb_z"], p["bulb_r"]
    neck_z = st + 0.036
    bulb_prof = [(0.0, neck_z), (0.0115, neck_z)]
    steps = 9
    for i in range(steps + 1):
        a = -math.radians(62) + (math.pi + math.radians(62)) * i / steps
        r, z = brad * math.cos(a), bz + brad * math.sin(a)
        if i == steps:
            r = 0.0
        if r >= 0.0115 or i == steps:
            bulb_prof.append((max(r, 0.0), z))
    bulb = common.mesh_object(f"{n}_Bulb", lathe(bulb_prof, sseg), col, bulb_mat, root)

    # ---- drum shade --------------------------------------------------------------
    z0, z1 = p["shade_z"]
    ro = p["shade_r"]
    ri = ro - p["shade_wall"]
    w = p["shade_wall"]
    tuck = 0.003   # the wall ends inside the rims, so no coplanar faces
    wall_prof = [(ri, z0 + tuck), (ro, z0 + tuck), (ro, z1 - tuck), (ri, z1 - tuck)]
    shade = common.mesh_object(f"{n}_Shade", lathe(wall_prof, seg), col, shade_mat, root)

    # bronze rims straddle the wall at the open top and bottom
    rim_mid = (ri + ro) / 2
    rh = p["rim_h"]
    for tag, (a, b) in (("RimBottom", (z0, z0 + rh)), ("RimTop", (z1 - rh, z1))):
        common.mesh_object(
            f"{n}_{tag}",
            lathe(rim_profile(rim_mid - p["rim_w"] / 2, rim_mid + p["rim_w"] / 2, a, b), seg),
            col, bronze, root)

    # ---- harness: arms from the socket to the lower rim ---------------------------
    bm = bmesh.new()
    attach_r = rim_mid
    for k in range(p["arms"]):
        ang = math.pi / 2 + 2 * math.pi * k / p["arms"]
        c, s = math.cos(ang), math.sin(ang)
        a = (0.0155 * c, 0.0155 * s, st + 0.004)
        b = (attach_r * c, attach_r * s, z0 + rh * 0.5)
        cylinder_between(bm, a, b, 0.0016, segs=8)
    # small hub where the arms meet the socket
    bmesh.ops.create_cone(bm, cap_ends=True, segments=sseg, radius1=0.0185, radius2=0.0185,
                          depth=0.004, matrix=Matrix.Translation((0, 0, st + 0.004)))
    harness = common.mesh_object(f"{n}_Harness", bm, col, bronze, root)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
