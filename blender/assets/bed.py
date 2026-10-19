"""King platform bed: smoked oak platform floating on a recessed black plinth,
channel-tufted ink headboard in an oak frame, oat linen mattress / duvet /
pillows, ink cushions, a folded stone throw across the foot.

Units are metres. The foot of the bed faces -Y, the headboard is at +Y, the
origin is the floor centre. Run inside Blender (see blender/run.py).

Soft goods are not boxes: each is an "inflated sheet" (a neutral surface plus a
thickness field and a rounded hem), so the duvet can drape over the mattress
edge, the flap and the throw can sit on the duvet's surface, and pillows get
crowns, a pinched seam and a little slump.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import importlib  # noqa: E402

from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)
importlib.reload(materials)

NAME = "Bed"

P = dict(
    name=NAME,
    # platform
    plinth_h=0.08,
    plinth_inset=0.10,
    platform_half_w=0.975,
    platform_y0=-1.02,
    platform_y1=0.955,
    platform_top=0.38,
    # mattress
    mattress_half_w=0.93,
    mattress_y0=-0.985,
    mattress_y1=0.945,
    mattress_t=0.25,
    # headboard
    hb_half_w=1.05,
    hb_h=1.15,
    hb_channels=8,
    hb_bulge=0.055,
    # duvet drape
    drape_r=0.07,
    drape_theta=1.45,
    drape_len=0.30,
    duvet_end_y=0.30,
    flap_start_y=0.02,
    flap_end_y=0.32,
)


# ---------------------------------------------------------------- soft goods

def _coords(half, r, step, m=4):
    """Grid lines from -half to +half: m segments of a quarter circle of
    radius r at each end (so the hem is a round profile), uniform between."""
    cap = [r * (1 - math.cos(math.pi / 2 * k / m)) for k in range(m + 1)]
    span = 2 * (half - r)
    n = max(1, round(span / step))
    mid = [-half + r + span * k / n for k in range(1, n)]
    return [-half + c for c in cap] + mid + [half - c for c in reversed(cap)]


def surface_normal(S, x, y, e=1e-3):
    su = S(x + e, y) - S(x - e, y)
    sv = S(x, y + e) - S(x, y - e)
    n = su.cross(sv)
    n.normalize()
    return n


def sheet(hx, hy, r, S, H, step=0.1, m=4, rounding=0.0, step_y=None, ys=None, back=True):
    """Closed, soft slab. S(x, y) -> neutral surface point, H(x, y) -> (top,
    bottom) half-thickness; thickness falls to zero at the border through a
    quarter circle of radius r, so the hem is round. rounding > 0 pulls the
    corners in (pillows). step_y / ys: a different spacing (or explicit grid
    lines) along y; back=False leaves out the bottom faces (a panel against a
    board). Returns a bmesh."""
    xs = _coords(hx, r, step, m)
    ys = ys if ys is not None else _coords(hy, r, step_y or step, m)
    bm = bmesh.new()
    top, bot = {}, {}
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            u, v = x / hx, y / hy
            if rounding:
                nrm = math.hypot(u, v)
                if nrm > 1e-9:
                    f = 1 - rounding + rounding * max(abs(u), abs(v)) / nrm
                    u, v = u * f, v * f
            X, Y = u * hx, v * hy
            d = min(hx - abs(x), hy - abs(y))
            cap = 1.0 if d >= r else math.sqrt(max(0.0, 1 - (1 - d / r) ** 2))
            ht, hb = H(X, Y)
            s = S(X, Y)
            n = surface_normal(S, X, Y)
            top[i, j] = bm.verts.new(s + n * (ht * cap))
            bot[i, j] = bm.verts.new(s - n * (hb * cap))
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            bm.faces.new([top[i, j], top[i + 1, j], top[i + 1, j + 1], top[i, j + 1]])
            if back:
                bm.faces.new([bot[i, j + 1], bot[i + 1, j + 1], bot[i + 1, j], bot[i, j]])
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    if not back:
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    else:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def place(bm, lean, yaw, x, min_z, max_y=None, min_y=None, roll=0.0):
    """Rotate a pillow-local bmesh (face toward -Y, standing along Z) by `lean`
    radians (top toward +Y) and `yaw`, then set its x, lowest z and a y limit.
    Returns the matrix so trim can follow."""
    M = Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(-lean, 4, "X") @ Matrix.Rotation(roll, 4, "Y")
    bm.transform(M)
    zs = [v.co.z for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    dz = min_z - min(zs)
    dy = (max_y - max(ys)) if max_y is not None else (min_y - min(ys))
    T = Matrix.Translation((x, dy, dz))
    bm.transform(T)
    return T @ M


def pillow_surface(hx, hy, seed, slump, sag=1.0):
    """Neutral surface of a standing pillow: slightly bellied, top edge sagging
    toward the middle, sides barrelled, a few soft undulations."""
    ph = seed * 1.7

    def S(x, v):
        u, w = x / hx, v / hy
        off = (0.012 * math.sin(2.6 * u + ph) * (1 - 0.5 * abs(w))
               + 0.010 * math.sin(3.3 * w + 1.3 * ph + 0.5 * u)
               + slump * w * w * (0.5 + 0.5 * w)
               + 0.016 * (1 - u * u))                      # belly
        top = max(0.0, w) ** 2
        xx = x * (1 + 0.035 * (1 - w * w) - 0.03 * top) + 0.035 * sag * w * math.sin(ph)
        zz = (v - 0.028 * sag * top * (1 - u * u) + 0.014 * math.sin(2.2 * u + ph) * max(0.0, w)
              - 0.016 * sag * top * u * math.cos(ph))
        return Vector((xx, off, zz))

    return S


def pillow_bmesh(hx, hy, thick, r, seed, slump=0.0, rounding=0.30, step=0.075, dent=0.0, sag=1.0):
    """Standing pillow in its own frame: width along X, height along Z, front
    face toward -Y."""
    ph = seed * 1.7

    S = pillow_surface(hx, hy, seed, slump, sag)

    def H(x, v):
        u, w = x / hx, v / hy
        crown = (max(1e-4, 1 - u * u) ** 0.9) * (max(1e-4, 1 - w * w) ** 0.9)
        t = thick * (0.12 + 0.88 * crown)
        t *= 1 + 0.07 * math.sin(3.7 * u + 2.1 * w + ph)
        # stuffing creases running in from the corners, and a centre dent
        for k, (cu, cw_) in enumerate(((0.9, 0.8), (-0.85, -0.7))):
            dd = ((u * cw_ - w * cu) / math.hypot(cu, cw_))
            reach = min(1.0, max(0.0, (abs(u * cu + w * cw_) - 0.25) / 0.35))   # fades in, no step
            t *= 1 - 0.20 * math.exp(-(dd / 0.10) ** 2) * reach * reach * (3 - 2 * reach)
        t *= 1 - dent * math.exp(-(u / 0.28) ** 2) * (0.4 + 0.6 * max(0.0, w))
        return t, t

    return sheet(hx, hy, r, S, H, step=step, rounding=rounding)


def border_loop(hx, hy, S, rounding, n=9):
    """Points round the border of a pillow sheet, following its corner
    rounding (used for piping)."""
    pts = []
    for side in range(4):
        for k in range(n):
            f = -1 + 2 * k / n
            u, v = [(f, -1), (1, f), (-f, 1), (-1, -f)][side]
            nrm = math.hypot(u, v)
            fct = 1 - rounding + rounding * max(abs(u), abs(v)) / nrm
            pts.append(S(u * fct * hx, v * fct * hy))
    return pts


# --------------------------------------------------------------------- build

def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    oak = materials.smoked_oak()
    black = materials.black_metal()
    ink = materials.fabric("M_Fabric_Ink", (0.018, 0.024, 0.04), roughness=0.8)
    oat = materials.fabric("M_Fabric_Oat", (0.42, 0.37, 0.30))
    stone = materials.fabric("M_Fabric_Stone", (0.16, 0.15, 0.135))

    wood_parts, fabric_parts, metal_parts = [], [], []

    def box(name, size, centre, mat, bevel=0.004, bucket=wood_parts):
        ob = common.mesh_object(f"{n}_{name}", common.box_bmesh(size), col, mat, root)
        ob.location = centre
        if bevel:
            common.add_bevel(ob, bevel, segments=2)
        bucket.append(ob)
        return ob

    def soft(name, bm, mat, location=(0, 0, 0)):
        ob = common.mesh_object(f"{n}_{name}", bm, col, mat, root)
        ob.location = location
        fabric_parts.append(ob)
        return ob

    # ---- plinth, platform ---------------------------------------------------
    ph, ins = p["plinth_h"], p["plinth_inset"]
    hw, y0, y1 = p["platform_half_w"], p["platform_y0"], p["platform_y1"]
    ptop = p["platform_top"]
    box("Plinth", (2 * (hw - ins), (y1 - y0) - 2 * ins, ph + 0.01),
        (0, (y0 + y1) / 2, (ph + 0.01) / 2), black, bevel=0, bucket=metal_parts)
    mid_z = 0.195
    box("PlatformLower", (2 * hw, y1 - y0, mid_z - 0.006 - ph),
        (0, (y0 + y1) / 2, (ph + mid_z - 0.006) / 2), oak)
    box("PlatformReveal", (2 * hw - 0.05, (y1 - y0) - 0.05, 0.02),
        (0, (y0 + y1) / 2, mid_z), black, bevel=0, bucket=metal_parts)
    box("PlatformUpper", (2 * hw, y1 - y0, ptop - mid_z - 0.006),
        (0, (y0 + y1) / 2, (mid_z + 0.006 + ptop) / 2), oak)

    # ---- headboard -----------------------------------------------------------
    hbw, hbh = p["hb_half_w"], p["hb_h"]
    y_back = y1 + 0.12                 # back of the headboard (= overall bed length)
    box("HB_Back", (2 * hbw, 0.03, hbh - ph), (0, y_back - 0.015, (hbh + ph) / 2), oak)
    post_w = 0.05
    for s, sx in (("L", -1), ("R", 1)):
        box(f"HB_Post_{s}", (post_w, 0.12, hbh - ph), (sx * (hbw - post_w / 2), y_back - 0.06, (hbh + ph) / 2), oak)
        box(f"HB_Foot_{s}", (0.22, 0.10, ph + 0.01), (sx * 0.80, y_back - 0.06, (ph + 0.01) / 2),
            black, bevel=0, bucket=metal_parts)
    box("HB_Top", (2 * hbw, 0.12, 0.055), (0, y_back - 0.06, hbh - 0.0275), oak)
    box("HB_Bottom", (2 * hbw, 0.12, 0.05), (0, y_back - 0.06, ph + 0.025), oak)

    # channel-tufted ink panel (heightfield, seen only from the front)
    nch = p["hb_channels"]
    px0, pw = -(hbw - post_w), 2 * (hbw - post_w)
    cw = pw / nch
    zlo, zhi = ph + 0.05, hbh - 0.055
    base_y = y_back - 0.03 - 0.0   # face of the oak back board
    bulge = p["hb_bulge"]
    s_list = [0, 0.06, 0.17, 0.32, 0.5, 0.68, 0.83, 0.94]
    xs = [px0 + (c + s) * cw for c in range(nch) for s in s_list] + [px0 + pw]
    end_offs = [0, 0.008, 0.02, 0.04, 0.065, 0.1]
    span = zhi - zlo
    nmid = max(1, round((span - 0.2) / 0.19))
    zs = ([zlo + e for e in end_offs]
          + [zlo + 0.1 + (span - 0.2) * k / nmid for k in range(1, nmid)]
          + [zhi - e for e in reversed(end_offs)])

    def panel_y(x, z):
        c = (x - px0) / cw
        s = c - math.floor(c)
        if c >= nch:
            s = 0.0
        ch = math.sin(math.pi * s) ** 0.62
        e = min(z - zlo, zhi - z)
        f = min(1.0, e / 0.11)
        f = (f * f * (3 - 2 * f)) ** 0.8
        crown = 1 + 0.08 * math.sin(math.pi * (z - zlo) / span)
        return base_y - 0.004 - bulge * ch * f * crown

    bm = bmesh.new()
    grid = [[bm.verts.new((x, panel_y(x, z), z)) for z in zs] for x in xs]
    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            bm.faces.new([grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:           # all face -Y
        if f.normal.y > 0:
            f.normal_flip()
    panel = common.mesh_object(f"{n}_HB_Panel", bm, col, ink, root)
    fabric_parts.append(panel)

    # ---- mattress ----------------------------------------------------------
    mhw, my0, my1, mt = p["mattress_half_w"], p["mattress_y0"], p["mattress_y1"], p["mattress_t"]
    m_top = ptop + mt
    msize = (2 * mhw, my1 - my0, mt)
    mloc = (0, (my0 + my1) / 2, ptop + mt / 2)
    mat_bm = common.cushion_bmesh(msize, cuts=3, edge=0.05,
                                  crown={"+z": 0.012, "-z": 0.0, "+x": 0.004, "-x": 0.004,
                                         "+y": 0.004, "-y": 0.004})
    mattress = soft("Mattress", mat_bm, oat, mloc)      # in a fitted sheet: no piping
    common.add_subsurf(mattress)

    # ---- duvet (draped over the mattress) ------------------------------------
    R, TH, DL = p["drape_r"], p["drape_theta"], p["drape_len"]
    yfoot = my0
    zn = m_top + 0.040 + 0.002               # neutral surface of the duvet

    def bend(s):
        if s <= R * TH:
            a = s / R
            return R * math.sin(a), R * (1 - math.cos(a))
        s2 = s - R * TH
        return (R * math.sin(TH) + s2 * math.cos(TH),
                R * (1 - math.cos(TH)) + s2 * math.sin(TH))

    def wrinkle(x, y):
        return (0.006 * math.sin(3.1 * x + 0.7 * y + 1.0) * math.sin(2.3 * y - 0.4)
                + 0.004 * math.sin(7.3 * x - 2.9 * y + 0.5)
                + 0.005 * math.exp(-((x - 0.25) ** 2 + (y + 0.15) ** 2) / 0.12) * math.sin(5.0 * y + 3.0 * x))

    def duvet_S(px, py):
        sx = max(abs(px) - mhw, 0.0)
        sy = max(yfoot - py, 0.0)
        s = math.hypot(sx, sy)
        X, Y, drop = px, py, 0.0
        if s > 0:
            ux, uy = sx / s, sy / s
            s_eff = s * (1 + 0.08 * math.sin(5.3 * py * ux + 4.1 * px * uy + 0.8))   # soft folds in the skirt
            lat, drop = bend(s_eff)
            if sx > 0:
                X = math.copysign(mhw + lat * ux, px)
            if sy > 0:
                Y = yfoot - lat * uy
        fade = math.exp(-s / 0.04)
        crown = 0.016 * max(0.0, 1 - (px / 1.0) ** 2) * math.exp(-max(0.0, (-0.2 - py)) / 0.8)
        return Vector((X, Y, zn - drop + (wrinkle(px, py) + crown) * fade))

    def duvet_H(px, py):
        lump = (0.5 + 0.5 * math.sin(2.7 * px + 0.4) * math.sin(3.4 * py + 1.2)) \
            * (0.6 + 0.4 * math.sin(6.1 * px - 4.1 * py))
        return 0.040 + 0.014 * lump, 0.040

    def conform(px, py, off):
        s = duvet_S(px, py)
        nrm = surface_normal(duvet_S, px, py)
        return s + nrm * (duvet_H(px, py)[0] + off)

    dx_half = mhw + DL
    d_y0 = yfoot - DL
    d_y1 = p["duvet_end_y"]
    cy = (d_y0 + d_y1) / 2
    hy = (d_y1 - d_y0) / 2
    duvet_bm = sheet(dx_half, hy, 0.040,
                     lambda x, y: duvet_S(x, y + cy),
                     lambda x, y: duvet_H(x, y + cy), step=0.11, rounding=0.45)
    soft("Duvet", duvet_bm, oat)

    # turned-back flap: the head end of the duvet folded over itself
    f_y0, f_y1 = p["flap_start_y"], p["flap_end_y"]
    fcy, fhy = (f_y0 + f_y1) / 2, (f_y1 - f_y0) / 2

    def flap_S(x, y):
        return conform(x, y + fcy, 0.019 + 0.001 + 0.003 * math.sin(4.0 * x))

    def flap_H(x, y):
        t = (y + fcy - f_y0) / (f_y1 - f_y0)       # 0 at the free edge, 1 at the fold
        return 0.019 + 0.009 * t * t, 0.019

    soft("DuvetFlap", sheet(mhw + 0.19, fhy, 0.028, flap_S, flap_H, step=0.10), oat)

    # ---- throw: folded once (fold toward the foot), laid a little off-centre and
    # askew so it hangs further over one side; the top layer stops short of the
    # bottom one's open edge
    def throw_layer(name, hxl, hyl, cxl, cyl, ang, off, half_t, r):
        ca, sa = math.cos(ang), math.sin(ang)

        def S(x, y):
            return conform(cxl + x * ca - y * sa, cyl + x * sa + y * ca,
                           off + 0.002 * math.sin(5 * x + 0.6) + 0.0015 * math.sin(11 * x - 3 * y))

        soft(name, sheet(hxl, hyl, r, S, lambda x, y: (half_t * (1 + 0.18 * math.sin(6 * x + 1)), half_t),
                         step=0.16), stone)

    t_ang, t_cx = math.radians(3.0), 0.10
    hyA, hyB, cyA = 0.235, 0.205, -0.63
    throw_layer("Throw_A", 1.05, hyA, t_cx, cyA, t_ang, 0.015, 0.015, 0.014)
    throw_layer("Throw_B", 1.04, hyB, t_cx + 0.012, cyA - hyA + hyB + 0.004, t_ang + math.radians(0.5),
                0.015 * 2 + 0.013, 0.013, 0.013)

    # ---- pillows: euro shams against the headboard, sleeping pillows leaning on
    # them, two ink cushions and a lumbar in front ------------------------------
    head_y = y_back - 0.034 - p["hb_bulge"] * 1.08   # crest of the headboard channels
    pil_info = []

    def pillow(name, mat, x, hx, hy_p, thick, lean, yaw, seed, slump, roll, piping, rounding=0.30,
               step=0.085, dent=0.22, sag=1.0, max_y=None, min_y=None, lift=0.006):
        bm = pillow_bmesh(hx, hy_p, thick, min(0.06, 0.3 * min(hx, hy_p)), seed, slump=slump,
                          rounding=rounding, step=step, dent=dent, sag=sag)
        M = place(bm, math.radians(lean), math.radians(yaw), x, m_top - lift, max_y=max_y, min_y=min_y,
                  roll=math.radians(roll))
        soft(name, bm, mat)
        if piping:
            pil_info.append((name, hx, hy_p, seed, slump, M, piping, mat, rounding, sag))

    # euro shams (square, stone, piped), nearly upright
    pillow("Sham_L", stone, -0.475, 0.29, 0.275, 0.095, 9.0, 2.0, 5.2, 0.02, 1.5, 0.004, rounding=0.26,
           step=0.095, dent=0.12, max_y=head_y - 0.004, lift=0.008)
    pillow("Sham_R", stone, 0.475, 0.29, 0.275, 0.095, 11.0, -2.5, 6.1, 0.03, -1.0, 0.004, rounding=0.26,
           step=0.095, dent=0.12, max_y=head_y - 0.004, lift=0.008)
    # sleeping pillows (oat, plain edge), leaning on the shams
    pillow("Pillow_L", oat, -0.45, 0.34, 0.215, 0.100, 24.0, 3.0, 1.0, 0.025, 2.0, 0.0,
           max_y=head_y - 0.19)
    pillow("Pillow_R", oat, 0.46, 0.34, 0.215, 0.100, 27.0, -4.0, 2.3, 0.035, -3.0, 0.0,
           max_y=head_y - 0.16)
    # ink cushions, leaning on the pillows
    pillow("Cushion_L", ink, -0.31, 0.20, 0.19, 0.068, 30.0, 7.0, 3.1, 0.02, -7.0, 0.0055, rounding=0.34,
           step=0.075, dent=0.18, sag=0.2, min_y=0.42, lift=0.004)
    pillow("Cushion_R", ink, 0.38, 0.20, 0.19, 0.068, 27.0, -9.0, 4.4, 0.03, 9.0, 0.0055, rounding=0.34,
           step=0.075, dent=0.18, sag=0.2, min_y=0.42, lift=0.004)
    # lumbar in front, centred
    pillow("Lumbar", stone, 0.03, 0.29, 0.15, 0.064, 18.0, 3.0, 7.7, 0.01, 1.0, 0.0045, rounding=0.2,
           step=0.085, dent=0.18, sag=0.2, min_y=0.335, lift=0.004)

    for name, hx, hy_p, seed, slump, M, rad, mat, rounding, sag in pil_info:
        S = pillow_surface(hx, hy_p, seed, slump, sag)
        pts = [M @ q for q in border_loop(hx, hy_p, S, rounding)]
        pipe = common.tube_object(f"{n}_{name}_Piping", pts, rad, col, mat, root, closed=True, profile_res=0)
        fabric_parts.append(pipe)

    # ---- finishing -------------------------------------------------------------
    for ob in wood_parts:
        common.box_uv(ob, tile=0.5)
    for ob in fabric_parts:
        common.box_uv(ob, tile=0.25)
    for ob in metal_parts:
        common.box_uv(ob, tile=0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
