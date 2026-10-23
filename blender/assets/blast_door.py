"""The armory's blast door: a 0.28 m graphite steel leaf with a stainless edge band, in a steel
frame that stands 0.1 m proud of the wall on both faces, big external hinge knuckles, a spoked
handwheel on each face (fixed to the leaf), three locking bolts on the latch edge and a
safety-yellow kick plate on the sill and the frame feet.

For `plan.CUTS` like door.py: origin = bottom centre of the opening on the wall's centre plane;
the room it swings into is +Y (the hinges and the leaf's open position are on that side), hinge
at the -X jamb, 90 degrees. The hinge empty carries the rotate `interact`; the level decides
whether it is locked. Geometry helpers (Geo) live in bunker_door.py.
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bunker_door  # noqa: E402

importlib.reload(bunker_door)
Geo, bk = bunker_door.Geo, bunker_door.bk
common = bk.common

NAME = "BlastDoor"

P = dict(
    name=NAME,
    opening=(2.0, 2.2),
    wall_t=0.3,
    leaf_t=0.28,
    gap=0.01,
    sill_h=0.02,
    liner=0.05,              # frame reveal lining inside the opening
    surround=0.22,           # width of the frame's face band
    proud=0.10,              # how far the frame stands off each wall face
    wheel_r=0.30,
    wheel_z=1.12,
    duration=3.2,
)


def wheel(g, cx, cz, y0, d, r=0.30, spokes=6):
    """Handwheel on a face: y0 = the face plane, d = +1 (faces +Y) or -1 (faces -Y). The axle
    stands out of a base plate; everything is relative to the face."""
    def y(off):
        return y0 + d * off
    g.cyl((cx, y(0.040), cz), 0.028, 0.10, "y", segs=10)                       # axle
    g.cyl((cx, y(0.090), cz), 0.060, 0.045, "y", segs=16)                      # hub
    g.cyl((cx, y(0.115), cz), 0.034, 0.012, "y", segs=12)                      # hub cap
    t = 0.018
    R = r - t
    g.torus((cx, y(0.090), cz), R, t, "y", segs=32, tsegs=6)                  # rim
    for i in range(spokes):
        a = 2 * math.pi * i / spokes + math.pi / 6
        rm = (R + 0.05) / 2
        g.box((cx + rm * math.cos(a), y(0.090), cz + rm * math.sin(a)), (R - 0.05, 0.034, 0.030),
              rot=(-a, "y"))
        g.cyl((cx + R * math.cos(a), y(0.090), cz + R * math.sin(a)), 0.026, 0.05, "y", segs=8)   # grip boss


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    graphite, stainless, yellow = bk.graphite(), bk.stainless(), bk.safety_yellow()

    w, h = p["opening"]
    wt, lt, g, lin, sh_ = p["wall_t"], p["leaf_t"], p["gap"], p["liner"], p["sill_h"]
    sur, pr = p["surround"], p["proud"]
    clear_w = w - 2 * lin
    sw = clear_w - 2 * g
    zb = sh_ + 0.01
    zt = h - lin - g
    sht = zt - zb
    face_y = wt / 2 + pr / 2           # centre y of the frame's face band
    hx = -clear_w / 2 + g              # the hinge axis (leaf edge, room-side face)
    hy = lt / 2

    # ---- frame (static; jambs and head are separate meshes so none spans the doorway) ----
    def jamb(sign):
        m = Geo()
        m.box((sign * (w / 2 - lin / 2), 0, (h - lin) / 2), (lin, wt, h - lin))
        for f in (-1, 1):
            m.box((sign * (w / 2 + sur / 2), f * face_y, (h + sur) / 2), (sur, pr, h + sur))
        m.finish(f"{n}_Frame_{'R' if sign > 0 else 'L'}", col, graphite, root, bevel=0.004)

    jamb(-1), jamb(1)
    m = Geo()
    m.box((0, 0, h - lin / 2), (clear_w, wt, lin))
    for f in (-1, 1):
        m.box((0, f * face_y, h + sur / 2), (w + 2 * sur, pr, sur))
    m.finish(f"{n}_Frame_Head", col, graphite, root, bevel=0.004)

    m = Geo()                                                                  # the threshold
    m.box((0, 0, sh_ / 2), (clear_w, wt + 2 * pr, sh_))
    m.finish(f"{n}_Sill", col, graphite, root, bevel=0.003)

    m = Geo()                                                                  # yellow on the sill ...
    for f in (-1, 1):
        m.box((0, f * (wt / 2 + pr - 0.04), sh_ + 0.0007), (clear_w - 0.02, 0.07, 0.0015))
    m.finish(f"{n}_Kick_Sill", col, yellow, root)
    for sign in (-1, 1):                                                       # ... and on the frame feet
        m = Geo()
        for f in (-1, 1):
            m.box((sign * (w / 2 + sur / 2), f * (wt / 2 + pr + 0.002), 0.17), (sur - 0.03, 0.004, 0.34))
        m.finish(f"{n}_Kick_{'R' if sign > 0 else 'L'}", col, yellow, root)

    # static hinge knuckles between the leaf's (on the axis, room side), with pin caps
    kz = [0.40, 1.12, 1.84]
    kh = 0.24
    kr = 0.058
    m = Geo()
    ax, ay = hx, hy
    edges = [sh_ + 0.012] + [z for k in kz for z in (k - kh / 2 - 0.012, k + kh / 2 + 0.012)] + [zt - 0.012]
    for z0, z1 in zip(edges[0::2], edges[1::2]):
        m.cyl((ax, ay, (z0 + z1) / 2), kr, z1 - z0, "z", segs=14)
    for z0, z1 in zip(edges[0::2], edges[1::2]):                               # a lug into the frame
        m.box((ax - 0.07, ay + 0.012, (z0 + z1) / 2), (0.1, 0.07, z1 - z0 - 0.01))
    m.finish(f"{n}_Knuckles_NoCollide", col, graphite, root, bevel=0.003)

    # ---- the leaf ---------------------------------------------------------------------------
    hinge = common.empty(f"{n}_Hinge", col, (hx, hy, 0))
    hinge.parent = root
    hinge["interact"] = {
        "type": "rotate",
        "axis": common.to_gltf((0, 0, 1)),
        "angle": 90,
        "duration": p["duration"],
        "range": 2.4,
        "side": "both",
        "collide": True,
        "prompt": "Open door",
        "promptActive": "Close door",
        "lockedPrompt": "Locked · keycard required",
        "unlockPrompt": "Unlock with keycard",
    }
    cz = (zb + zt) / 2
    ly = -lt / 2
    leaf = Geo()
    leaf.box((sw / 2, ly, cz), (sw, lt, sht))
    pin = 0.15                                          # raised face panels
    pw, ph = sw - 2 * pin, sht - 2 * pin
    pcx = sw / 2
    for f in (-1, 1):
        fy = (0 if f > 0 else -lt) + f * 0.009
        leaf.box((pcx, fy, cz), (pw, 0.018, ph))
        wy = (0 if f > 0 else -lt) + f * 0.018
        leaf.cyl((pcx + 0.05, wy + f * 0.01, p["wheel_z"]), 0.11, 0.02, "y", segs=20)    # wheel base plate
    # hinge straps (leaf side) on the room face, at each leaf knuckle
    for z in kz:
        leaf.cyl((0, 0, z), kr, kh, "z", segs=14)
        leaf.box((0.27, 0.014, z), (0.54, 0.028, 0.14))
        leaf.box((0.54, 0.014, z), (0.03, 0.036, 0.16))
    leaf.finish(f"{n}_Leaf", col, graphite, hinge, bevel=0.004)

    hw = Geo()
    wx = pcx + 0.05
    for f in (-1, 1):
        wy0 = (0 if f > 0 else -lt) + f * 0.018 + f * 0.02
        wheel(hw, wx, p["wheel_z"], wy0, f, r=p["wheel_r"])
        fy = (0 if f > 0 else -lt)
        # edge band: a stainless frame round each face
        bw, bt = 0.04, 0.005
        by = fy + f * (0.018 + bt / 2 - 0.0)
        for (bx, bz, sx, sz) in ((sw / 2, zt - bw / 2, sw, bw), (sw / 2, zb + bw / 2, sw, bw),
                                 (bw / 2, cz, bw, sht - 2 * bw), (sw - bw / 2, cz, bw, sht - 2 * bw)):
            hw.box((bx, fy + f * (bt / 2), bz), (sx, bt, sz))
        # four heavy bolt-heads at the corners of the raised panel
        for ux in (-1, 1):
            for uz in (-1, 1):
                bxp = pcx + ux * (pw / 2 - 0.05)
                bzp = cz + uz * (ph / 2 - 0.05)
                hw.cyl((bxp, fy + f * (0.018 + 0.004), bzp), 0.046, 0.008, "y", segs=12)
                hw.cyl((bxp, fy + f * (0.018 + 0.016), bzp), 0.034, 0.016, "y", segs=6)
        # rivets round the panel's border, and a plain rating plate beside the wheel
        rx0, rx1 = pcx - pw / 2 + 0.03, pcx + pw / 2 - 0.03
        rz0, rz1 = cz - ph / 2 + 0.03, cz + ph / 2 - 0.03
        pts = [(rx0 + (rx1 - rx0) * i / 8, rz0) for i in range(1, 8)] + [(rx0 + (rx1 - rx0) * i / 8, rz1) for i in range(1, 8)]
        pts += [(rx0, rz0 + (rz1 - rz0) * i / 10) for i in range(1, 10)] + [(rx1, rz0 + (rz1 - rz0) * i / 10) for i in range(1, 10)]
        for rx, rz in pts:
            hw.cyl((rx, fy + f * (0.018 + 0.003), rz), 0.011, 0.006, "y", segs=6)
        hw.box((pcx - 0.42, fy + f * (0.018 + 0.002), p["wheel_z"] + 0.35), (0.20, 0.004, 0.11))
    for z in (0.55, 1.12, 1.69):                                               # locking bolts, latch edge
        hw.cyl((sw + 0.0, ly, z), 0.032, 0.09, "x", segs=12)
        hw.cyl((sw - 0.002, ly, z), 0.046, 0.016, "x", segs=12)
    for z in kz:                                                                # pin caps
        hw.cyl((0, 0, z + kh / 2 + 0.003), 0.03, 0.006, "z", segs=10)
    hw.finish(f"{n}_Hardware", col, stainless, hinge)

    return root, [o for o in root.children_recursive if o.type == "MESH"]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
