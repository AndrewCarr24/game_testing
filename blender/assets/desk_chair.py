"""Desk chair: an executive swivel chair after the Eames Aluminium Group "Soft Pad"
(EA 219/437 family): black leather sling with sewn, pillowed pads (topstitched either
side of every seam), polished cast-aluminium side ribs with a real profile, cantilevered
cast arms with stitched leather arm pads, a polished bar under the seat and one behind
the back, a black tilt-swivel housing with tension knob and lift paddle, a polished gas
column and a five-star base on twin-wheel casters.

Everything hangs off one side-view curve, the SPINE (the sling's centre line, seat front
hem -> seat -> bend -> back -> top hem): the pads are an analytic offset surface over it
(pad profile x edge roll x a little irregularity), the side ribs are a profile swept along
it, the stitch rows sit on exact rows of the pad mesh.

Footprint kept to the old chair's box (x +-0.32, y -0.314..+0.345, z 0..0.951), so the
open desk drawer still clears it (rooms/office.py places it at (2.25, 3.75), 12 deg).
Origin = floor centre, front = -Y. No interactables.
"""
import bisect
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import importlib  # noqa: E402

from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)
importlib.reload(materials)

NAME = "DeskChair"

P = dict(
    name=NAME,
    leather_name="M_Leather_Black",
    leather=(0.018, 0.016, 0.015),
    # --- keys kept from the old sled-base version (placements and overrides stay valid) ---
    half_width=0.29,
    runner_front=-0.30,
    runner_back=0.30,
    front_rake=0.03,
    arm_z=0.66,             # arm tube height: the arm pads top out ~0.68 like the old caps
    low_rail_z=0.34,
    back_rail_z=0.60,       # height of the polished bar behind the back
    board_half_width=0.27,
    back_tilt_deg=15.0,     # back recline from vertical
    back_panel_h=0.58,
    cushion_half_width=0.243,   # half width of the sling between the side ribs
    seat_cushion_t=0.050,   # pad crown thickness (seat)
    back_cushion_t=0.042,   # pad crown thickness (back)
    back_cushion_h=0.50,
    arm_cap=(0.05, 0.25, 0.02),     # arm pad (width, length, thickness)
    cushion_edge=0.022,
    # --- this version ---
    seat_front=(-0.270, 0.432),     # spine: seat front corner (y, z)
    seat_rear=(0.118, 0.404),       # spine: seat-back corner
    back_top_z=0.94,               # spine: top corner height
    seat_pads=3, back_pads=4,
    rib=(0.0085, 0.013, -0.004),    # side rib half width, half depth, offset along the sling normal
    base_r=0.295,                   # hub -> caster stem
    base_y=-0.03,                   # column / base centre (under the seat, as on the real chair)
    caster_r=0.024,
    stitch_pitch=0.004,
    seed=11,
)

LEATHER_TILE = 0.2


# ----------------------------------------------------------------------------- textures

def stitch_texture(force=False):
    """Topstitch thread strip (RGBA, alpha-tested): 4 stitches along u (one tile =
    4 x stitch_pitch), the strip's width along v. Tonal: a warm charcoal thread a step
    lighter than the leather, rounded and twisted, with the needle holes dark."""
    path = os.path.join(textures.TEX_DIR, "T_DeskChair_Stitch.png")
    if os.path.exists(path) and not force:
        return path
    W, H = 256, 64
    u = (np.arange(W) + 0.5) / W * 4.0            # 4 stitches
    v = (np.arange(H) + 0.5) / H * 2.0 - 1.0      # -1..1 across the strip
    a = (u % 1.0) * 2.0 - 1.0                     # -1..1 along one stitch cell
    A, V = np.meshgrid(a, v)
    L = 0.80                                      # stitch length / pitch
    al = A / L
    half = 0.62 * np.sqrt(np.clip(1 - np.abs(al) ** 6, 0, 1))      # thread tapers into its holes
    inside = np.clip((half - np.abs(V)) / 0.08 + 0.5, 0, 1) * (np.abs(al) < 1)
    rr = np.clip(np.abs(V) / np.maximum(half, 1e-3), 0, 1)
    shade = (0.35 + 0.65 * np.sqrt(1 - rr ** 2)) * (1 - 0.55 * np.abs(al) ** 5)
    shade *= 0.82 + 0.18 * np.sin(2 * np.pi * (A * 2.2 + V * 0.9))    # twist of the ply
    thread = np.array([0.060, 0.056, 0.050])
    rgb = thread[None, None, :] * shade[..., None]
    # needle holes just beyond each end
    hole = np.clip(1 - np.hypot((np.abs(A) - (L + 0.1)) / 0.09, V / 0.22), 0, 1)
    hole = (hole > 0.0) * 1.0
    rgb = np.where(hole[..., None] > 0, np.array([0.004, 0.004, 0.004])[None, None, :], rgb)
    alpha = np.maximum(inside, hole)
    rgb = np.where(alpha[..., None] > 0.01, rgb, thread[None, None, :] * 0.6)   # no dark mip fringe
    srgb = textures._to_srgb(rgb)
    img = bpy.data.images.new("T_DeskChair_Stitch", W, H, alpha=True)
    rgba = np.concatenate([srgb, alpha[..., None]], axis=2)
    img.pixels.foreach_set(rgba[::-1].astype(np.float32).ravel())
    img.alpha_mode = "STRAIGHT"
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return path


def stitch_material():
    m = common.pbr_material("M_DeskChair_Stitch", (0.06, 0.056, 0.05), roughness=0.55)
    img = textures.load(stitch_texture())
    img.alpha_mode = "STRAIGHT"
    nodes, links = m.node_tree.nodes, m.node_tree.links
    bsdf = next(nd for nd in nodes if nd.type == "BSDF_PRINCIPLED")
    if not any(nd.type == "TEX_IMAGE" for nd in nodes):
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.location = (bsdf.location.x - 700, bsdf.location.y)
        rnd = nodes.new("ShaderNodeMath")
        rnd.operation = "ROUND"
        rnd.location = (bsdf.location.x - 350, bsdf.location.y - 250)
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(tex.outputs["Alpha"], rnd.inputs[0])
        links.new(rnd.outputs[0], bsdf.inputs["Alpha"])
    m.use_backface_culling = True
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "DITHERED"
    return m


# ----------------------------------------------------------------------------- geometry helpers

def fillet(pts, radii, seg=20):
    """Open polyline (Vectors) with corner i rounded by radii[i] (ends ignored)."""
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        u, v = (a - b).normalized(), (c - b).normalized()
        th = u.angle(v)
        r = radii[i]
        if r <= 0 or th > math.pi - 1e-4:
            out.append(b)
            continue
        t = r / math.tan(th / 2)
        t = min(t, 0.48 * (a - b).length, 0.48 * (c - b).length)
        r = t * math.tan(th / 2)
        t1, t2 = b + u * t, b + v * t
        ctr = b + (u + v).normalized() * (r / math.sin(th / 2))
        d1, d2 = t1 - ctr, t2 - ctr
        for k in range(seg + 1):
            out.append(ctr + d1.slerp(d2, k / seg).normalized() * r)
    out.append(pts[-1])
    return out


class Curve:
    """Dense polyline with arc length; eval(s) -> point, unit tangent."""

    def __init__(self, pts, step=0.003):
        dense = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            n = max(1, int(math.ceil((b - a).length / step)))
            for k in range(1, n + 1):
                dense.append(a.lerp(b, k / n))
        self.p = dense
        self.s = [0.0]
        for a, b in zip(dense[:-1], dense[1:]):
            self.s.append(self.s[-1] + (b - a).length)
        self.length = self.s[-1]

    def _seg(self, s):
        s = max(0.0, min(self.length, s))
        i = max(0, min(len(self.s) - 2, bisect.bisect_right(self.s, s) - 1))
        f = (s - self.s[i]) / max(self.s[i + 1] - self.s[i], 1e-9)
        return i, f

    def point(self, s):
        i, f = self._seg(s)
        return self.p[i].lerp(self.p[i + 1], f)

    def tangent(self, s, d=0.004):
        return (self.point(s + d) - self.point(s - d)).normalized()

    def adaptive(self, s0, s1, max_deg=5.0, max_len=0.15):
        """Sample positions between s0 and s1: dense in bends, sparse on straights."""
        out = [s0]
        last_t = self.tangent(s0)
        s = s0
        while s < s1:
            s = min(s1, s + 0.004)
            t = self.tangent(s)
            if s >= s1 or math.degrees(last_t.angle(t)) >= max_deg or s - out[-1] >= max_len:
                out.append(s)
                last_t = t
        return out


def ring_pts(c, au, av, a, b, n, power=2.0, ridge=0.0, start=0.0):
    """Superellipse ring around c in the (au, av) plane (half axes a, b)."""
    out = []
    for k in range(n):
        t = 2 * math.pi * k / n + start
        ct, st = math.cos(t), math.sin(t)
        x = a * math.copysign(abs(ct) ** (2 / power), ct)
        y = b * math.copysign(abs(st) ** (2 / power), st)
        if ridge and ct > 0:                    # a soft spine down the outer face
            x *= 1 + ridge * ct ** 6
        out.append(c + au * x + av * y)
    return out


def loft(bm, rings, caps=(True, True), closed=True):
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(rings[0])
    m = n if closed else n - 1
    for r0, r1 in zip(vs[:-1], vs[1:]):
        for k in range(m):
            bm.faces.new((r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k]))
    for cap, rv, flip in ((caps[0], vs[0], True), (caps[1], vs[-1], False)):
        if cap:
            ctr = bm.verts.new(sum((v.co for v in rv), Vector()) / n)
            for k in range(n):
                f = (rv[k], rv[(k + 1) % n], ctr)
                bm.faces.new(f[::-1] if flip else f)
    return vs


def domed_rings(rings, axis_out, depth, steps=3):
    """Extra rings shrinking towards a rounded end beyond the last ring."""
    last = rings[-1]
    ctr = sum(last, Vector()) / len(last)
    out = []
    for k in range(1, steps + 1):
        th = (math.pi / 2) * k / (steps + 0.6)
        sc, off = math.cos(th), math.sin(th) * depth
        out.append([ctr + (p - ctr) * sc + axis_out * off for p in last])
    return out


def sweep(bm, curve, samples, section, cap_dome=(0.0, 0.0)):
    """Loft section(s, centre, tangent) rings along curve samples; dome the ends."""
    rings = []
    for s in samples:
        rings.append(section(s, curve.point(s), curve.tangent(s)))
    if cap_dome[1] > 0:
        rings += domed_rings(rings, curve.tangent(samples[-1]), cap_dome[1])
    if cap_dome[0] > 0:
        rings = domed_rings(rings[::-1], -curve.tangent(samples[0]), cap_dome[0])[::-1] + rings
    loft(bm, rings)


def recalc(bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def mark_sharp(bm, deg=40.0):
    lim = math.radians(deg)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
            e.smooth = False


def obj(name, bm, col, mat, parent, sharp=None, recalc_normals=True):
    if recalc_normals:
        recalc(bm)
    if sharp is not None:
        mark_sharp(bm, sharp)
    return common.mesh_object(name, bm, col, mat, parent, smooth=True)


def strip_faces(bm, rows_a, rows_b, uv_layer=None, uvs=None):
    """Quads between two vertex rows (same length)."""
    for k in range(len(rows_a) - 1):
        f = bm.faces.new((rows_a[k], rows_a[k + 1], rows_b[k + 1], rows_b[k]))
        if uv_layer is not None:
            for loop, uv in zip(f.loops, (uvs[0][k], uvs[0][k + 1], uvs[1][k + 1], uvs[1][k])):
                loop[uv_layer].uv = uv


# ----------------------------------------------------------------------------- the chair

def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rng = np.random.default_rng(p["seed"])

    leather = common.pbr_material(p["leather_name"], p["leather"], roughness=0.62)
    common.set_normal_map(leather, textures.load(textures.leather_normal(), non_color=True), 0.6)
    alu = materials.steel()             # M_Steel_Polished: polished cast aluminium
    black = materials.black_metal()     # M_Aluminium_Black: housing, knob, casters
    stitch = stitch_material()

    W = p["cushion_half_width"]

    # ---------------------------------------------------------------- spine (x = 0 plane)
    fy, fz = p["seat_front"]
    ry, rz = p["seat_rear"]
    tilt = math.radians(p["back_tilt_deg"])
    tz = p["back_top_z"]
    ty = ry + (tz - rz) * math.tan(tilt)
    ctrl = [Vector((0, fy + 0.034, fz - 0.056)),        # front hem, rolled back under the seat front
            Vector((0, fy, fz)),                         # seat front corner (waterfall roll)
            Vector((0, ry, rz)),                         # seat-back bend
            Vector((0, ty, tz)),                         # top corner (roll over)
            Vector((0, ty + 0.022, tz - 0.034))]         # top hem, behind
    spine = Curve(fillet(ctrl, [0, 0.042, 0.10, 0.028, 0], seg=28))

    def frame_at(s):
        c = spine.point(s)
        t = spine.tangent(s)
        nrm = Vector((0, -t.z, t.y))                    # sling normal: up on the seat, forward on the back
        return c, t, nrm

    def s_near(y=None, z=None):
        best, bs = 1e9, 0.0
        for s, q in zip(spine.s, spine.p):
            d = abs(q.y - y) if y is not None else abs(q.z - z)
            if d < best and (z is None or q.y > ry - 0.05):
                best, bs = d, s
        return bs

    def corner_s(i):
        # arc-length position closest to control point i (fillet midpoint)
        q = ctrl[i]
        return min(zip(spine.s, spine.p), key=lambda sp: (sp[1] - q).length)[0]

    s_cf, s_bend, s_tc = corner_s(1), corner_s(2), corner_s(3)
    s_end = spine.length

    # pad boundaries (seams) along the spine
    seat_n, back_n = p["seat_pads"], p["back_pads"]
    s1 = s_cf + 0.085
    seat_b = [0.0, s1] + [s1 + (s_bend - s1) * k / (seat_n - 1) for k in range(1, seat_n)]
    back_len = (s_tc + 0.035) - s_bend
    back_b = [s_bend + back_len * k / back_n for k in range(back_n)] + [s_end]
    bounds = seat_b[:-1] + back_b                    # all boundaries, s_bend once
    seat_t, back_t = p["seat_cushion_t"], p["back_cushion_t"]
    thick = ([seat_t * 0.82] + [seat_t] * (seat_n - 1)
             + [back_t * 1.08] + [back_t] * (back_n - 2) + [back_t * 0.78])
    H_HEM, H_SEAM, H_JOIN, H_FLOOR = 0.003, 0.011, 0.008, 0.0015
    end_h = [H_HEM] + [H_SEAM] * (len(bounds) - 2) + [H_HEM]
    end_h[seat_n] = H_JOIN
    phase = rng.uniform(0, 2 * math.pi, (len(thick), 4))

    def pad_index(s):
        return max(0, min(len(thick) - 1, bisect.bisect_right(bounds, s) - 1))

    def pad_h(s, x, i=None):
        i = pad_index(s) if i is None else i
        a, b = bounds[i], bounds[i + 1]
        u = max(0.0, min(1.0, (s - a) / (b - a)))
        f = max(0.0, 1 - abs(2 * u - 1) ** 2.4) ** 0.5
        base = end_h[i] * (1 - u) + end_h[i + 1] * u
        ph = phase[i]
        xn = x / W
        wob = (0.05 * math.sin(2.1 * xn * math.pi + ph[0]) * math.sin(math.pi * u + ph[1])
               + 0.03 * math.sin(4.3 * xn * math.pi + ph[2]) + 0.025 * math.sin(3 * math.pi * u + ph[3]))
        hc = thick[i] * (1 + wob) * (1 - 0.07 * xn * xn)     # fuller in the middle than at the sides
        if 1 <= i <= seat_n - 1:                     # sat-in: the seat pads a touch lower in the middle
            hc -= 0.0045 * math.exp(-(x / 0.13) ** 2) * math.sin(math.pi * u)
        if i == seat_n:                              # lumbar pad: fuller in the middle
            hc += 0.003 * math.exp(-(x / 0.16) ** 2)
        hs = base + (hc - base) * f
        gx = max(0.0, 1 - min(1.0, abs(xn)) ** 4) ** 0.33
        return H_FLOOR + (hs - H_FLOOR) * gx

    seam_ph = rng.uniform(0, 2 * math.pi, (len(bounds), 2))

    def seam_wave(s, x):
        """Sewn seams aren't ruler-straight: rows near a seam drift +-1 mm along the spine."""
        j = min(range(1, len(bounds) - 1), key=lambda k: abs(s - bounds[k]))
        d = s - bounds[j]
        ph = seam_ph[j]
        w = 0.0011 * math.sin(x * 2 * math.pi / 0.13 + ph[0]) + 0.0005 * math.sin(x * 2 * math.pi / 0.05 + ph[1])
        return w * math.exp(-(d / 0.022) ** 2)

    def pad_pt(s, x, i=None, lift=0.0):
        s = s + seam_wave(s, x)
        c, t, nrm = frame_at(s)
        return Vector((x, c.y, c.z)) + nrm * (pad_h(s, x, i) + lift)

    # x samples across the pads (dense into the side rolls) and the s samples per pad
    xf = [0.0, 0.2, 0.4, 0.56, 0.69, 0.79, 0.865, 0.92, 0.955, 0.98, 1.0]
    xs = sorted({round(sg * W * k, 5) for k in xf for sg in (-1, 1)})
    sx = W - 0.014                                    # stitch rows stop short of the side rolls
    xs = sorted(set(xs) | {-sx, sx})
    ST = 0.009                                        # topstitch offset from each seam

    def pad_samples(i):
        a, b = bounds[i], bounds[i + 1]
        ss = {a, b}
        L = b - a
        near = [0.0035, ST, 0.016, 0.028]
        for k, o in enumerate(near):
            if o < 0.4 * L:
                if i > 0 or True:
                    ss.add(a + o)
                ss.add(b - o)
        lo, hi = a + 0.028, b - 0.028
        m = max(1, int(round((hi - lo) / 0.03)))
        for k in range(1, m):
            ss.add(lo + (hi - lo) * k / m)
        return sorted(ss)

    def pad_mesh(name, pads):
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        rows, uvs = [], []
        prev = None
        for i in pads:
            for s in pad_samples(i):
                if prev is not None and abs(s - prev) < 1e-6:
                    continue
                rows.append([bm.verts.new(pad_pt(s, x, i if s < bounds[i + 1] - 1e-6 else min(i, len(thick) - 1)))
                             for x in xs])
                uvs.append([(x / LEATHER_TILE, s / LEATHER_TILE) for x in xs])
                prev = s
        for k in range(len(rows) - 1):
            strip_faces(bm, rows[k], rows[k + 1], uvl, (uvs[k], uvs[k + 1]))
        ob = common.mesh_object(name, bm, col, leather, root)   # winding already outward
        return ob

    pad_mesh(f"{n}_SeatPads", range(0, seat_n))
    pad_mesh(f"{n}_BackPads", range(seat_n, len(thick)))

    # ---- topstitching: two rows either side of every seam, on exact pad-mesh rows
    sbm = bmesh.new()
    suv = sbm.loops.layers.uv.new("UVMap")
    tile = 4 * p["stitch_pitch"]
    half_w = 0.0008

    def stitch_row(pts_fn, n_fn, along, length_param):
        """pts_fn(k) surface points, n_fn(k) normals, along(k) row direction; strip across."""
        a_row, b_row, ua, ub = [], [], [], []
        for k in range(len(length_param)):
            q, nn, d = pts_fn(k), n_fn(k), along(k)
            w = nn.cross(d).normalized() * half_w
            a_row.append(sbm.verts.new(q + nn * 0.0005 - w))
            b_row.append(sbm.verts.new(q + nn * 0.0005 + w))
            ua.append((length_param[k] / tile, 0.0))
            ub.append((length_param[k] / tile, 1.0))
        strip_faces(sbm, a_row, b_row, suv, (ua, ub))

    def surf_normal(s, x, i):
        e = 0.0015
        dx = pad_pt(s, x + e, i) - pad_pt(s, x - e, i)
        ds = pad_pt(s + e, x, i) - pad_pt(s - e, x, i)
        return dx.cross(ds).normalized()

    row_x = [x for x in xs if abs(x) <= sx + 1e-6]
    for j in range(1, len(bounds) - 1):
        for side in (-1, 1):
            s = bounds[j] + side * ST
            i = j if side > 0 else j - 1
            stitch_row(lambda k, s=s, i=i: pad_pt(s, row_x[k], i),
                       lambda k, s=s, i=i: surf_normal(s, row_x[k], i),
                       lambda k: Vector((1, 0, 0)), [x - row_x[0] for x in row_x])

    # ---------------------------------------------------------------- sling backing + hems
    # the leather sling the pads are sewn to: visible from behind and below, its edges run
    # into the ribs' slots; shallow sewn-through grooves behind every seam
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    mx = [-W - 0.006, -W + 0.03, -0.12, 0.0, 0.12, W - 0.03, W + 0.006]
    s_list = sorted(set(spine.adaptive(0.0, s_end, max_deg=6, max_len=0.05))
                    | {b + o for b in bounds[1:-1] for o in (-0.006, 0.0, 0.006)})

    def back_pt(s, x):
        c, t, nrm = frame_at(s)
        sag = 0.004 * (1 - (x / (W + 0.006)) ** 2)
        groove = sum(0.0018 * math.exp(-((s - b) / 0.004) ** 2) for b in bounds[1:-1]) * (1 - (x / (W + 0.006)) ** 8)
        return Vector((x, c.y, c.z)) - nrm * (0.003 + sag - groove)

    bm.free()
    # two meshes (seat, back), split at the bend, so each gets its own collider box
    for tag, part in (("Seat", [q for q in s_list if q <= s_bend + 1e-9]),
                      ("Back", [q for q in s_list if q >= s_bend - 1e-9])):
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        rows = [[bm.verts.new(back_pt(s, x)) for x in mx] for s in part]
        uvs = [[(x / LEATHER_TILE, s / LEATHER_TILE) for x in mx] for s in part]
        for k in range(len(rows) - 1):      # reversed winding: faces point away from the sitter
            strip_faces(bm, rows[k + 1], rows[k], uvl, (uvs[k + 1], uvs[k]))
        common.mesh_object(f"{n}_Sling_{tag}", bm, col, leather, root)

    # rear stitch rows (one per seam, sewn through)
    rx = [x for x in mx if abs(x) < W]
    for b in bounds[1:-1]:
        stitch_row(lambda k, b=b: back_pt(b, rx[k]) + (back_pt(b, rx[k]) - Vector((rx[k], spine.point(b).y, spine.point(b).z))).normalized() * 0.0001,
                   lambda k, b=b: -frame_at(b)[2],
                   lambda k: Vector((-1, 0, 0)), [x - rx[0] for x in rx])

    # hems: the sling's rolled ends at the seat front and the back top
    for tag, s in (("Front", 0.0), ("Top", s_end)):
        hb = bmesh.new()
        c, t, nrm = frame_at(s)
        rings = []
        for x in [-W - 0.004, -W * 0.6, 0.0, W * 0.6, W + 0.004]:
            ctr = Vector((x, c.y, c.z)) + nrm * 0.0002
            rings.append(ring_pts(ctr, nrm, t, 0.0048, 0.0052, 10))
        loft(hb, rings)
        common.box_uv(common.mesh_object(f"{n}_Hem{tag}_Piping", hb, col, leather, root), LEATHER_TILE)

    # ---------------------------------------------------------------- side ribs (polished)
    ra, rb, roff = p["rib"]
    s_rib0, s_rib1 = s_cf - 0.034, s_tc - 0.012
    rib_s = spine.adaptive(s_rib0, s_rib1, max_deg=7.0, max_len=0.14)
    for side, sg in (("L", -1), ("R", 1)):
        xr = sg * (W + ra)

        def section(s, c, t, sg=sg, xr=xr):
            nrm = Vector((0, -t.z, t.y))
            ctr = Vector((xr, c.y, c.z)) + nrm * roff
            return ring_pts(ctr, Vector((sg, 0, 0)), nrm, ra, rb, 14, power=2.6, ridge=0.12)

        bm = bmesh.new()
        sweep(bm, spine, rib_s, section, cap_dome=(0.012, 0.012))
        obj(f"{n}_Rib_{side}", bm, col, alu, root)

    # ---------------------------------------------------------------- bar behind the back
    s_bb = s_near(z=p["back_rail_z"])
    c, t, nrm = frame_at(s_bb)
    xe = W + ra
    pts = [Vector((-xe + 0.002, c.y, c.z)) + nrm * (roff - 0.004),
           Vector((-W + 0.02, c.y, c.z)) - nrm * 0.024,
           Vector((0, c.y, c.z)) - nrm * 0.034,
           Vector((W - 0.02, c.y, c.z)) - nrm * 0.024,
           Vector((xe - 0.002, c.y, c.z)) + nrm * (roff - 0.004)]
    bar = Curve(fillet(pts, [0, 0.03, 0.4, 0.03, 0], seg=10))

    def bar_sec(s, q, tt, nrm=nrm):
        v = nrm.cross(tt).normalized()
        return ring_pts(q, v, tt.cross(v).normalized(), 0.012, 0.0075, 12, power=2.4)

    bm = bmesh.new()
    sweep(bm, bar, bar.adaptive(0, bar.length, 9, 0.12), bar_sec)
    obj(f"{n}_BackBar", bm, col, alu, root)

    # ---------------------------------------------------------------- under the seat
    by = p["base_y"]
    s_ub = s_near(y=by)
    c, t, nrm = frame_at(s_ub)
    rib_bottom = c.z + roff - rb + 0.004                 # z where the bar meets the ribs
    mech_top = rib_bottom - 0.028
    pts = [Vector((-xe, by, rib_bottom)), Vector((-0.12, by, mech_top + 0.004)),
           Vector((0.12, by, mech_top + 0.004)), Vector((xe, by, rib_bottom))]
    sbar = Curve(fillet(pts, [0, 0.06, 0.06, 0], seg=8))

    def sbar_sec(s, q, tt):
        k = abs(q.x) / xe
        return ring_pts(q, Vector((0, 1, 0)), Vector((0, 1, 0)).cross(tt).normalized() * -1,
                        0.030 - 0.008 * k, 0.008, 14, power=2.8)

    bm = bmesh.new()
    sweep(bm, sbar, sbar.adaptive(0, sbar.length, 6, 0.1), sbar_sec)
    obj(f"{n}_SeatBar", bm, col, alu, root)

    # tilt-swivel housing: a rounded black box with a tension knob and a lift paddle
    hw_, hd_, hh_ = 0.075, 0.105, 0.034
    hz = mech_top - hh_ / 2
    bm = rounded_box((2 * hw_, 2 * hd_, hh_), 0.010)
    bmesh.ops.translate(bm, vec=(0, by - 0.005, hz), verts=bm.verts)
    obj(f"{n}_Mechanism", bm, col, black, root)
    bm = bmesh.new()
    kr = ring_pts(Vector((0, by - 0.085, hz - hh_ / 2)), Vector((1, 0, 0)), Vector((0, 1, 0)), 0.022, 0.022, 20)
    rings = [kr, [q + Vector((0, 0, -0.016)) for q in kr],
             [Vector((0, by - 0.085, hz - hh_ / 2 - 0.02)) + (q - Vector((0, by - 0.085, hz - hh_ / 2))) * 0.85
              for q in kr]]
    loft(bm, rings, caps=(False, True))
    obj(f"{n}_Knob_NoCollide", bm, col, black, root, sharp=50)
    lever = Curve([Vector((hw_ - 0.01, by + 0.03, hz)), Vector((0.15, by + 0.01, hz - 0.012)),
                   Vector((0.19, by - 0.02, hz - 0.016))])

    def lev_sec(s, q, tt):
        k = s / lever.length
        return ring_pts(q, Vector((0, 0, 1)).cross(tt).normalized(), Vector((0, 0, 1)),
                        0.004 + 0.008 * max(0, k - 0.6) / 0.4, 0.0035, 8)

    bm = bmesh.new()
    sweep(bm, lever, [0, lever.length * 0.55, lever.length * 0.8, lever.length], lev_sec, cap_dome=(0, 0.006))
    obj(f"{n}_Lever_NoCollide", bm, col, alu, root)

    # ---------------------------------------------------------------- column + base
    hub_top = 0.128
    col_top = hz - hh_ / 2
    bm = bmesh.new()
    cz = Vector((0, 0, 1))
    C = Vector((0, by, 0))
    prof = [(0.0262, hub_top - 0.01), (0.0262, 0.232), (0.0245, 0.240), (0.0215, 0.243),
            (0.0215, 0.252), (0.0172, 0.256), (0.0172, col_top + 0.004)]
    rings = [ring_pts(C + cz * z, Vector((1, 0, 0)), Vector((0, 1, 0)), r, r, 24) for r, z in prof]
    loft(bm, rings, caps=(False, False))
    obj(f"{n}_Column", bm, col, alu, root, sharp=35)

    # five-star base: crowned, tapering legs with a foot at each tip, polished
    bm = bmesh.new()
    hub = [(0.040, 0.058), (0.056, 0.063), (0.059, 0.100), (0.052, 0.122), (0.036, hub_top + 0.004),
           (0.0, hub_top + 0.006)]
    rings = [ring_pts(C + cz * z, Vector((1, 0, 0)), Vector((0, 1, 0)), max(r, 1e-4), max(r, 1e-4), 25)
             for r, z in hub]
    loft(bm, rings[:-1], caps=(True, True))
    R = p["base_r"]
    leg_angles = [-90 + 36 + 72 * k for k in range(5)]        # two legs forward, one straight back
    tips = []
    for ang in leg_angles:
        d = Vector((math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0))
        side = cz.cross(d).normalized()
        lrings = []
        for r in [0.035, 0.07, 0.14, 0.21, 0.255, R]:
            k = (r - 0.035) / (R - 0.035)
            top = 0.124 - 0.046 * k ** 0.8
            bot = 0.064 - 0.010 * k
            hw = 0.030 - 0.012 * k ** 0.8
            hh = (top - bot) / 2
            ctr = C + d * r + cz * ((top + bot) / 2)
            ring = []
            for q in range(14):
                th = 2 * math.pi * q / 14
                ct, st = math.cos(th), math.sin(th)
                x = hw * math.copysign(abs(ct) ** (2 / 2.4), ct)
                y = hh * math.copysign(abs(st) ** (2 / (2.2 if st > 0 else 5.0)), st)
                ring.append(ctr + side * x + cz * y)
            lrings.append(ring)
        lrings += domed_rings(lrings, d, 0.014, steps=3)
        loft(bm, lrings, caps=(False, True))
        tips.append(C + d * R)
    obj(f"{n}_Base", bm, col, alu, root)

    # twin-wheel casters, each turned its own way (trailing inwards, as left after a roll)
    cr = p["caster_r"]
    cb = bmesh.new()
    wb = bmesh.new()
    for k, tip in enumerate(tips):
        out = (tip - C).normalized()
        yaw = math.atan2(-out.y, -out.x) + rng.uniform(-0.9, 0.9)
        trail = Vector((math.cos(yaw), math.sin(yaw), 0))
        axle = cz.cross(trail).normalized()
        wc = tip + trail * 0.016 + cz * cr
        # stem + hood (black housing between the wheels, rounded over the top)
        hood = []
        for z, rr in ((0.062, 0.006), (0.050, 0.006), (0.046, 0.011)):
            hood.append(ring_pts(Vector((tip.x, tip.y, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), rr, rr, 8))
        loft(cb, hood, caps=(False, False))
        hs = []
        for a_ in (-0.0075, 0.0075):
            hs.append(ring_pts(wc + axle * a_ + cz * 0.004, trail, cz, cr * 0.95, cr * 0.95, 10, start=math.pi / 10))
        loft(cb, hs)
        # two wheels
        for side_ in (-1, 1):
            w0 = wc + axle * side_ * 0.0075
            prof_w = [(cr - 0.006, 0.0005), (cr - 0.0015, 0.0025), (cr, 0.0065), (cr - 0.0015, 0.0105),
                      (cr - 0.006, 0.0125)]
            wr = [ring_pts(w0 + axle * side_ * o, trail, cz, r_, r_, 10, start=math.pi / 10) for r_, o in prof_w]
            loft(wb, wr, caps=(True, True))
    obj(f"{n}_CasterHoods_NoCollide", cb, col, black, root, sharp=60)
    obj(f"{n}_CasterWheels_NoCollide", wb, col, black, root, sharp=50)

    # ---------------------------------------------------------------- arms (cantilevered from the ribs)
    ax0 = W + 2 * ra + 0.0085                 # strut against the rib's outer face
    ax1 = ax0 + 0.014                         # horizontal arm a little further out
    ap_w, ap_l, ap_t = p["arm_cap"]
    az = p["arm_z"] - 0.012
    s_am = s_near(y=0.0)
    cam = spine.point(s_am)
    arm_front = -0.172
    for side, sg in (("L", -1), ("R", 1)):
        pts = [Vector((sg * ax0, -0.02, cam.z + roff - 0.002)),
               Vector((sg * ax0, 0.088, cam.z + 0.012)),
               Vector((sg * ax1, 0.092, az)),
               Vector((sg * ax1, arm_front, az + 0.002))]
        arm = Curve(fillet(pts, [0, 0.07, 0.075, 0], seg=12))
        L = arm.length

        def arm_sec(s, q, tt, L=L, sg=sg):
            k = s / L
            g = min(1.0, max(0.0, (k - 0.35) / 0.3))
            a = 0.0085 + (0.015 - 0.0085) * g
            b = 0.0135 - (0.0135 - 0.0068) * g
            v = tt.cross(Vector((sg, 0, 0))).normalized() * sg
            return ring_pts(q, Vector((sg, 0, 0)), v, a, b, 12, power=2.4)

        bm = bmesh.new()
        sweep(bm, arm, arm.adaptive(0, L, 9, 0.08), arm_sec, cap_dome=(0.008, 0.012))
        obj(f"{n}_Arm_{side}", bm, col, alu, root)

        # arm pad: crowned leather pad on the straight run, stitched round its top edge
        y0, y1 = arm_front - 0.012, arm_front - 0.012 + ap_l
        zb = az + 0.0068 - 0.002
        bm = bmesh.new()
        hwp, ht = ap_w / 2, ap_t

        def pad_ring(y, sc=1.0, lift=0.0):
            ctr = Vector((sg * ax1, y, zb + ht * 0.45 + lift))
            out = []
            for q in range(16):
                th = 2 * math.pi * q / 16
                ct, st = math.cos(th), math.sin(th)
                x = hwp * sc * math.copysign(abs(ct) ** (2 / 2.8), ct)
                zz = (ht * 0.55 if st > 0 else ht * 0.45) * sc ** 0.5 * math.copysign(abs(st) ** (2 / (2.2 if st > 0 else 4)), st)
                out.append(ctr + Vector((x, 0, zz)))
            return out

        ys = [y0 + 0.03, y0 + 0.08, (y0 + y1) / 2, y1 - 0.08, y1 - 0.03]
        prs = [pad_ring(y) for y in ys]
        ends = []
        for k in range(1, 4):
            th = (math.pi / 2) * k / 4.4
            ends.append((math.cos(th), math.sin(th) * 0.03))
        front = [pad_ring(y0 + 0.03 - o, sc) for sc, o in ends][::-1]
        back = [pad_ring(y1 - 0.03 + o, sc) for sc, o in ends]
        loft(bm, front + prs + back)
        apo = obj(f"{n}_ArmPad_{side}", bm, col, leather, root)
        common.box_uv(apo, LEATHER_TILE)
        # stitch rows along both long top edges
        for e in (-1, 1):
            xx = e * (hwp - 0.006)
            th_x = math.acos(min(1.0, (abs(xx) / hwp) ** (2.8 / 2)))
            zt = ht * 0.55 * math.sin(th_x) ** (2 / 2.2)
            ysl = np.linspace(y0 + 0.022, y1 - 0.022, 9)
            nrm_s = Vector((e * 0.45, 0, 1)).normalized()
            stitch_row(lambda k, ysl=ysl, xx=xx, zt=zt: Vector((sg * ax1 + xx, ysl[k], zb + ht * 0.45 + zt)),
                       lambda k, nrm_s=nrm_s: nrm_s,
                       lambda k: Vector((0, 1, 0)), list(ysl - ysl[0]))

    common.mesh_object(f"{n}_Stitching_NoCollide", sbm, col, stitch, root, smooth=True)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


def rounded_box(size, r, cuts=3):
    """Soft box: a subdivided cube whose edge band is projected onto a radius-r rounding."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    h = [s / 2 for s in size]
    nseg = cuts + 1
    for v in bm.verts:
        p = []
        for a in range(3):
            t = max(-1.0, min(1.0, v.co[a]))
            i = round((t + 1) / 2 * nseg)
            inner = [(-h[a] + r) + (2 * (h[a] - r)) * k / (nseg - 2) for k in range(nseg - 1)]
            p.append(([-h[a]] + inner + [h[a]])[i])
        q = Vector(p)
        c = Vector([max(-(h[a] - r), min(h[a] - r, q[a])) for a in range(3)])
        d = q - c
        if d.length > 1e-9:
            q = c + d.normalized() * r
        v.co = q
    return bm


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
