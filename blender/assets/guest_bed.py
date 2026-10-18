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

importlib.reload(bed)
importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestBed"

P = dict(
    name=NAME,
    plinth_h=0.07, plinth_inset=0.09,
    platform_half_w=0.86, platform_y0=-1.02, platform_y1=0.98, platform_top=0.30,
    mattress_half_w=0.80, mattress_y0=-0.995, mattress_y1=0.965, mattress_t=0.24,
    hb_half_w=1.08, hb_bottom=0.14, hb_top=1.08, hb_depth=0.085,
    drape_r=0.07, drape_theta=1.45, drape_len=0.28,
    duvet_end_y=0.42, flap_start_y=0.10, flap_end_y=0.42,
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
    panel_h = hb1 - hb0 - 0.10
    panel = common.mesh_object(
        f"{n}_HB_Panel",
        common.cushion_bmesh((2 * hbw - 0.10, hbd, panel_h), cuts=5, edge=0.03,
                             crown={"-y": 0.018, "+y": 0.0, "+z": 0.004, "-z": 0.004, "+x": 0.004, "-x": 0.004}),
        col, sage, root)
    panel.location = (0, y1 + hbd / 2, (hb0 + hb1) / 2)
    common.add_subsurf(panel)
    soft_parts.append(panel)
    # horizontal stitch lines on the panel
    for k, zf in enumerate((-0.18, 0.18)):
        pass

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
        return conform(x, y + fcy, 0.034 + 0.0015 + 0.004 * math.sin(4.0 * x))

    def flap_H(x, y):
        t = (y + fcy - f_y0) / (f_y1 - f_y0)
        return 0.026 + 0.010 * t * t, 0.026

    soft("DuvetFlap", bed.sheet(mhw + 0.115, fhy, 0.030, flap_S, flap_H, step=0.10), linen)

    # ---- throw: two folded layers in sage across the foot
    def throw_layer(name, hxl, hyl, cxl, cyl, ang, off, half_t, r):
        ca, sa = math.cos(ang), math.sin(ang)

        def S(x, y):
            return conform(cxl + x * ca - y * sa, cyl + x * sa + y * ca, off + 0.0015 * math.sin(5 * x))

        soft(name, bed.sheet(hxl, hyl, r, S, lambda x, y: (half_t * (1 + 0.15 * math.sin(6 * x + 1)), half_t),
                             step=0.14), sage_l)

    throw_layer("Throw_A", 0.95, 0.20, 0.0, -0.62, math.radians(1.2), 0.016, 0.016, 0.014)
    throw_layer("Throw_B", 0.94, 0.15, 0.01, -0.665, math.radians(1.6), 0.016 * 2 + 0.014, 0.014, 0.012)

    # ---- pillows and cushions
    head_y = y1 - 0.004
    for name, x, hx, hy, lean, yaw, seed, slump, roll, mat in (
            ("Pillow_L", -0.40, 0.33, 0.235, 16.0, 2.5, 1.0, 0.025, 2.0, linen),
            ("Pillow_R", 0.40, 0.33, 0.235, 20.0, -3.0, 2.3, 0.035, -3.0, linen)):
        bm = bed.pillow_bmesh(hx, hy, 0.105, 0.06, seed, slump=slump, dent=0.22, step=0.09)
        bed.place(bm, math.radians(lean), math.radians(yaw), x, m_top - 0.006, max_y=head_y - 0.004, roll=math.radians(roll))
        soft(name, bm, mat)
    for name, x, hx, hy, lean, yaw, seed, slump, front_y, roll in (
            ("Cushion_L", -0.30, 0.20, 0.15, 34.0, 5.0, 3.1, 0.02, 0.52, -6.0),
            ("Cushion_R", 0.34, 0.20, 0.15, 30.0, -7.0, 4.4, 0.03, 0.50, 8.0)):
        bm = bed.pillow_bmesh(hx, hy, 0.07, 0.05, seed, slump=slump, rounding=0.22, step=0.07, dent=0.30, sag=0.25)
        bed.place(bm, math.radians(lean), math.radians(yaw), x, m_top - 0.004, min_y=front_y, roll=math.radians(roll))
        soft(name, bm, sage)

    for ob in wood + metal:
        common.box_uv(ob, tile=0.5)
    for ob in soft_parts:
        common.box_uv(ob, tile=0.25)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
