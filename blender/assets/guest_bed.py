"""Guest bed (queen): low light-oak platform on a recessed black plinth, a wide
sage-linen upholstered headboard on an oak backboard, white linen duvet with a
turned-back flap, two linen pillows, two sage lumbar cushions and a sage throw
folded across the foot. Soft goods reuse bed.py's inflated-sheet builders.

Units are metres. The foot faces -Y, the headboard is at +Y, origin at the floor
centre of the platform."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bed  # noqa: E402
import guest_mats  # noqa: E402
import guest_wardrobe  # noqa: E402

importlib.reload(bed)
importlib.reload(guest_mats)
importlib.reload(guest_wardrobe)
common = guest_mats.common

NAME = "GuestBed"

P = dict(
    name=NAME,
    plinth_h=0.07, plinth_inset=0.09,
    platform_half_w=0.86, platform_y0=-1.02, platform_y1=0.98, platform_top=0.30,
    mattress_half_w=0.80, mattress_y0=-0.995, mattress_y1=0.965, mattress_t=0.24,
    hb_half_w=1.08, hb_bottom=0.14, hb_top=1.08, hb_depth=0.085,
    drape_r=0.07, drape_theta=1.45, drape_len=0.28,
    duvet_end_y=0.30, flap_start_y=0.0, flap_end_y=0.32,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    oak, black = guest_mats.oak(), guest_mats.black()
    linen, sage, sage_l = guest_mats.linen(), guest_mats.sage(), guest_mats.sage_light()
    wood, soft_parts, metal = [], [], []

    def box(name, size, centre, mat, bevel=0.004, bucket=wood):
        ob = common.mesh_object(f"{n}_{name}", common.box_bmesh(size), col, mat, root)
        ob.location = centre
        if bevel:
            common.add_bevel(ob, bevel, segments=2)
        bucket.append(ob)
        return ob

    def soft(name, bm, mat):
        ob = common.mesh_object(f"{n}_{name}", bm, col, mat, root)
        soft_parts.append(ob)
        return ob

    ph, ins = p["plinth_h"], p["plinth_inset"]
    hw, y0, y1, ptop = p["platform_half_w"], p["platform_y0"], p["platform_y1"], p["platform_top"]
    cy = (y0 + y1) / 2
    box("Plinth", (2 * (hw - ins), (y1 - y0) - 2 * ins, ph + 0.01), (0, cy, (ph + 0.01) / 2), black, 0, metal)
    box("Platform", (2 * hw, y1 - y0, ptop - ph), (0, cy, (ph + ptop) / 2), oak, 0.006)
    # slim oak edge board proud of the platform: a shadow line under the mattress
    box("PlatformCap", (2 * hw + 0.016, y1 - y0 + 0.008, 0.016), (0, cy, ptop - 0.008), oak, 0.003)

    # ---- headboard: oak backboard + sage linen cushion panel
    hbw, hb0, hb1, hbd = p["hb_half_w"], p["hb_bottom"], p["hb_top"], p["hb_depth"]
    box("HB_Back", (2 * hbw, 0.04, hb1 - hb0), (0, y1 + hbd + 0.02, (hb0 + hb1) / 2), oak, 0.005)
    # sage linen panel: four horizontal channels stitched into the board, the edge
    # rolling back onto the oak (an open-backed soft sheet lying on the board face)
    y_pb = y1 + hbd                                  # front face of the oak backboard
    php, pzc = (hb1 - hb0 - 0.10) / 2, (hb0 + hb1) / 2
    phx = hbw - 0.05
    nch, r_hem = 4, 0.035
    chh = 2 * php / nch
    cap = [r_hem * (1 - math.cos(math.pi / 2 * k / 4)) for k in range(5)]
    rows = {round(-php + c, 5) for c in cap} | {round(php - c, 5) for c in cap}
    for c in range(nch):
        for f in (0.0, 0.07, 0.18, 0.33, 0.5, 0.67, 0.82, 0.93):
            rows.add(round(-php + (c + f) * chh, 5))
    rows = sorted(r for r in rows if -php <= r <= php)

    def hb_S(x, v):
        return Vector((x, y_pb, pzc + v))

    def hb_H(x, v):
        s = ((v + php) / chh) % 1.0
        ch = math.sin(math.pi * s) ** 0.6
        u = x / phx
        return (0.052 + 0.032 * ch) * (1 + 0.04 * (1 - u * u)), 0.0

    panel = soft("HB_Panel", bed.sheet(phx, php, r_hem, hb_S, hb_H, step=0.13, ys=rows, back=False), sage)

    # ---- mattress
    mhw, my0, my1, mt = p["mattress_half_w"], p["mattress_y0"], p["mattress_y1"], p["mattress_t"]
    m_top = ptop + mt
    msize = (2 * mhw, my1 - my0, mt)
    mloc = (0, (my0 + my1) / 2, ptop + mt / 2)
    mattress = soft("Mattress", common.cushion_bmesh(
        msize, cuts=3, edge=0.05, crown={"+z": 0.012, "-z": 0.0, "+x": 0.004, "-x": 0.004, "+y": 0.004, "-y": 0.004}), linen)
    mattress.location = mloc
    common.add_subsurf(mattress)

    # ---- duvet (same drape as bed.py)
    R, TH, DL = p["drape_r"], p["drape_theta"], p["drape_len"]
    yfoot = my0
    zn = m_top + 0.040 + 0.002

    def bend(s):
        if s <= R * TH:
            a = s / R
            return R * math.sin(a), R * (1 - math.cos(a))
        s2 = s - R * TH
        return (R * math.sin(TH) + s2 * math.cos(TH), R * (1 - math.cos(TH)) + s2 * math.sin(TH))

    def wrinkle(x, y):
        return (0.006 * math.sin(3.1 * x + 0.7 * y + 1.0) * math.sin(2.3 * y - 0.4)
                + 0.004 * math.sin(7.3 * x - 2.9 * y + 0.5)
                + 0.005 * math.exp(-((x + 0.2) ** 2 + (y + 0.1) ** 2) / 0.12) * math.sin(5.0 * y + 3.0 * x))

    def duvet_S(px, py):
        sx = max(abs(px) - mhw, 0.0)
        sy = max(yfoot - py, 0.0)
        s = math.hypot(sx, sy)
        X, Y, drop = px, py, 0.0
        if s > 0:
            ux, uy = sx / s, sy / s
            s_eff = s * (1 + 0.08 * math.sin(5.3 * py * ux + 4.1 * px * uy + 0.8))
            lat, drop = bend(s_eff)
            if sx > 0:
                X = math.copysign(mhw + lat * ux, px)
            if sy > 0:
                Y = yfoot - lat * uy
        fade = math.exp(-s / 0.04)
        crown = 0.016 * max(0.0, 1 - (px / 1.0) ** 2) * math.exp(-max(0.0, (-0.2 - py)) / 0.8)
        return Vector((X, Y, zn - drop + (wrinkle(px, py) + crown) * fade))

    def duvet_H(px, py):
        lump = (0.5 + 0.5 * math.sin(2.7 * px + 0.4) * math.sin(3.4 * py + 1.2)) * (0.6 + 0.4 * math.sin(6.1 * px - 4.1 * py))
        return 0.040 + 0.014 * lump, 0.040

    def conform(px, py, off):
        s = duvet_S(px, py)
        nrm = bed.surface_normal(duvet_S, px, py)
        return s + nrm * (duvet_H(px, py)[0] + off)

    d_y0, d_y1 = yfoot - DL, p["duvet_end_y"]
    dcy, dhy = (d_y0 + d_y1) / 2, (d_y1 - d_y0) / 2
    soft("Duvet", bed.sheet(mhw + DL, dhy, 0.040, lambda x, y: duvet_S(x, y + dcy),
                            lambda x, y: duvet_H(x, y + dcy), step=0.11, rounding=0.45), linen)
    f_y0, f_y1 = p["flap_start_y"], p["flap_end_y"]
    fcy, fhy = (f_y0 + f_y1) / 2, (f_y1 - f_y0) / 2

    def flap_S(x, y):
        return conform(x, y + fcy, 0.019 + 0.001 + 0.003 * math.sin(4.0 * x))

    def flap_H(x, y):
        t = (y + fcy - f_y0) / (f_y1 - f_y0)
        return 0.019 + 0.009 * t * t, 0.019

    soft("DuvetFlap", bed.sheet(mhw + 0.19, fhy, 0.028, flap_S, flap_H, step=0.10), linen)

    # ---- throw: two folded layers in sage across the foot
    def throw_layer(name, hxl, hyl, cxl, cyl, ang, off, half_t, r):
        ca, sa = math.cos(ang), math.sin(ang)

        def S(x, y):
            return conform(cxl + x * ca - y * sa, cyl + x * sa + y * ca, off + 0.0015 * math.sin(5 * x))

        soft(name, bed.sheet(hxl, hyl, r, S, lambda x, y: (half_t * (1 + 0.15 * math.sin(6 * x + 1)), half_t),
                             step=0.14), sage_l)

    throw_layer("Throw_A", 0.95, 0.20, 0.0, -0.62, math.radians(1.2), 0.016, 0.016, 0.014)
    throw_layer("Throw_B", 0.94, 0.15, 0.01, -0.665, math.radians(1.6), 0.016 * 2 + 0.014, 0.014, 0.012)

    # ---- pillows: sage euro shams on the headboard, linen sleeping pillows, sage
    # cushions and a linen lumbar piped in sage
    head_y = y_pb - 0.085                            # crest of the headboard channels
    pipes = []

    def pillow(name, mat, x, hx, hy, thick, lean, yaw, seed, slump, roll, piping=0.0, pipe_mat=None,
               rounding=0.30, step=0.09, dent=0.22, sag=1.0, max_y=None, min_y=None, lift=0.006):
        bm = bed.pillow_bmesh(hx, hy, thick, min(0.06, 0.3 * min(hx, hy)), seed, slump=slump,
                              rounding=rounding, step=step, dent=dent, sag=sag)
        M = bed.place(bm, math.radians(lean), math.radians(yaw), x, m_top - lift, max_y=max_y, min_y=min_y,
                      roll=math.radians(roll))
        soft(name, bm, mat)
        if piping:
            S = bed.pillow_surface(hx, hy, seed, slump, sag)
            pts = [M @ q for q in bed.border_loop(hx, hy, S, rounding)]
            pipes.append(common.tube_object(f"{n}_{name}_Piping", pts, piping, col, pipe_mat or mat, root,
                                            closed=True, profile_res=0))

    pillow("Sham_L", sage_l, -0.40, 0.28, 0.27, 0.09, 8.0, 2.0, 5.7, 0.02, 1.5, 0.004, rounding=0.26,
           step=0.095, dent=0.12, max_y=head_y - 0.004, lift=0.008)
    pillow("Sham_R", sage_l, 0.40, 0.28, 0.27, 0.09, 10.0, -2.0, 6.4, 0.03, -1.0, 0.004, rounding=0.26,
           step=0.095, dent=0.12, max_y=head_y - 0.004, lift=0.008)
    pillow("Pillow_L", linen, -0.38, 0.33, 0.21, 0.10, 23.0, 2.5, 1.0, 0.025, 2.0, max_y=head_y - 0.175)
    pillow("Pillow_R", linen, 0.39, 0.33, 0.21, 0.10, 29.0, -3.0, 2.3, 0.035, -3.0, max_y=head_y - 0.145)
    pillow("Cushion_L", sage, -0.27, 0.20, 0.17, 0.066, 28.0, 5.0, 3.1, 0.02, -6.0, 0.005, rounding=0.34,
           step=0.075, dent=0.18, sag=0.2, min_y=0.42, lift=0.004)
    pillow("Cushion_R", sage, 0.31, 0.20, 0.17, 0.066, 26.0, -7.0, 4.4, 0.03, 8.0, 0.005, rounding=0.34,
           step=0.075, dent=0.18, sag=0.2, min_y=0.42, lift=0.004)
    pillow("Lumbar", linen, 0.02, 0.27, 0.14, 0.06, 18.0, -3.0, 8.3, 0.01, -1.0, 0.0045, pipe_mat=sage,
           rounding=0.2, step=0.075, dent=0.18, sag=0.2, min_y=0.335, lift=0.004)
    soft_parts.extend(pipes)

    for ob in wood + metal:
        common.box_uv(ob, tile=0.5)
    for ob in soft_parts:
        common.box_uv(ob, tile=0.25)
    guest_wardrobe.fix_oak(root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
