"""Umpire's chair: a tall dark-metal frame (splayed legs, raked rear uprights, braces, side
ladder) with a teak seat, backrest, arm rests and ladder treads. Seat 1.9 m, backrest
to 2.5 m. The umpire (and the ladder) face -Y; origin the floor centre."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tennis_common as tc  # noqa: E402

importlib.reload(tc)
common = tc.common
outdoor = tc.outdoor

NAME = "TennisUmpireChair"

P = dict(name=NAME, seat_h=1.90, back_top=2.62, tube=0.05, base_w=0.95, base_d=0.95, seat_w=0.62, seat_d=0.60)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = tc.standalone(n)
    b = tc.Builder(n)
    b.part("Teak", outdoor.teak(), uv=0.5)
    b.part("Frame", tc.mat_metal())

    H, tube = p["seat_h"], p["tube"]
    bw, bd = p["base_w"] / 2, p["base_d"] / 2
    sw, sd = p["seat_w"] / 2, p["seat_d"] / 2
    st = 0.05                                    # seat thickness

    # legs: front pair to the seat front corners, rear pair continuing up as the back uprights
    fz = H - st
    for sx in (-1, 1):
        b.strut("Frame", (sx * bw, -bd, 0.006), (sx * sw, -sd + 0.02, fz), tube, tube * 0.9)
        b.strut("Frame", (sx * bw, bd, 0.006), (sx * (sw - 0.02), sd - 0.02, fz), tube, tube * 0.9)
        # rear upright above the seat
        b.strut("Frame", (sx * (sw - 0.02), sd - 0.02, fz), (sx * (sw - 0.02), sd + 0.16, p["back_top"]), tube * 0.9, tube * 0.8)

    def at(z, sx, sy, frac=None):
        """Point on the front/rear leg of side sx at height z (linear in z)."""
        t = z / fz
        y0, y1 = (-bd, -sd + 0.02) if sy < 0 else (bd, sd - 0.02)
        x1 = sw if sy < 0 else sw - 0.02
        return (sx * (bw + (x1 - bw) * t), y0 + (y1 - y0) * t, z)

    # braces: side X-pairs at mid height, front and rear cross rails
    for z in (0.55, 1.20, fz - 0.10):
        for sx in (-1, 1):
            b.strut("Frame", at(z, sx, -1), at(z, sx, 1), 0.035)
        b.strut("Frame", at(z, -1, -1), at(z, 1, -1), 0.035)
        b.strut("Frame", at(z, -1, 1), at(z, 1, 1), 0.035)
    for sx in (-1, 1):
        b.strut("Frame", at(0.55, sx, -1), at(1.20, sx, 1), 0.03)
        b.strut("Frame", at(0.55, sx, 1), at(1.20, sx, -1), 0.03)

    # seat, backrest, arm rests (teak)
    b.box("Teak", (-sw - 0.03, -sd - 0.04, fz), (sw + 0.03, sd + 0.04, H), "+x -x +y -y +z -z")
    zb = H + 0.12
    from mathutils import Matrix
    lean = 0.16 / (p["back_top"] - fz)
    import math
    ang = -math.atan(lean)
    for k, (z0, z1) in enumerate(((zb, zb + 0.20), (zb + 0.26, zb + 0.46), (zb + 0.52, zb + 0.72))):
        yc = sd + 0.02 + lean * (z0 + z1) / 2 - lean * fz - 0.0
        zc = (z0 + z1) / 2
        M = Matrix.Translation((0, yc, zc)) @ Matrix.Rotation(ang, 4, "X") @ Matrix.Translation((0, -yc, -zc))
        b.box("Teak", (-sw + 0.01, yc - 0.015, z0), (sw - 0.01, yc + 0.015, z1), "+x -x +y -y +z -z", M=M)
    for sx in (-1, 1):
        ax = sx * (sw + 0.03)
        b.box("Teak", (ax - 0.03, -sd - 0.10, H + 0.22), (ax + 0.03, sd - 0.02, H + 0.26), "+x -x +y -y +z -z")
        b.strut("Frame", (ax, -sd - 0.04, H), (ax, -sd - 0.04, H + 0.22), 0.03, caps=False)

    # ladder up the front: two stiles and teak treads
    lx = 0.30
    for sx in (-1, 1):
        b.strut("Frame", (sx * lx, -bd - 0.45, 0.006), (sx * lx, -sd - 0.03, H - 0.05), 0.04)
    for k in range(1, 5):
        z = k * (H - 0.35) / 4.3
        t = z / (H - 0.05)
        y = (-bd - 0.45) + (-sd - 0.03 + bd + 0.45) * t
        b.box("Teak", (-lx - 0.02, y - 0.12, z - 0.02), (lx + 0.02, y + 0.12, z + 0.02), "+x -x +y -y +z -z")

    parts = b.finish(col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
