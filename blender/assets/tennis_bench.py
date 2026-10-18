"""Courtside / pavilion bench: teak slat seat and back on slim dark-metal side frames.
1.9 m wide, 0.5 m deep, seat 0.46 m, back to 0.85 m. The front faces -Y, origin the
floor centre."""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tennis_common as tc  # noqa: E402

importlib.reload(tc)
common = tc.common
outdoor = tc.outdoor

NAME = "TennisBench"

P = dict(name=NAME, width=1.9, depth=0.50, seat_h=0.46, back_h=0.85, slat_w=0.095, slat_t=0.035, gap=0.012, leg=0.04)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = tc.standalone(n)
    b = tc.Builder(n)
    b.part("Slats", outdoor.teak(), uv=0.5)
    b.part("Frame", tc.mat_metal())

    W, D, H, t, sw, gap = p["width"], p["depth"], p["seat_h"], p["slat_t"], p["slat_w"], p["gap"]
    hw = W / 2 - 0.05
    # seat slats along X
    y = -D / 2 + 0.02
    while y + sw <= D / 2 - 0.10:
        b.box("Slats", (-hw, y, H - t), (hw, y + sw, H), "+x -x +y -y +z -z")
        y += sw + gap
    # rear member: one raked strut from the floor to the top of the back
    from mathutils import Matrix
    y0, top_z, lean = D / 2 - 0.12, H + 0.52, 0.20
    ang = -math.atan2(lean, top_z)
    ym = lambda z: y0 + lean * z / top_z
    for k in range(3):
        zc = H + 0.16 + k * (sw + gap) + sw / 2
        yc = ym(zc) - 0.015 - t / 2
        M = Matrix.Translation((0, yc, zc)) @ Matrix.Rotation(ang, 4, "X") @ Matrix.Translation((0, -yc, -zc))
        b.box("Slats", (-hw, yc - t / 2, zc - sw / 2), (hw, yc + t / 2, zc + sw / 2), "+x -x +y -y +z -z", M=M)
    # frames: front leg and raked rear member at each end, joined by a seat rail
    for s in (-1, 1):
        x = s * (hw - 0.04)
        b.box("Frame", (x - 0.015, -D / 2 + 0.03, H - t - 0.04), (x + 0.015, D / 2 - 0.10, H - t), "+x -x +y -y -z")
        b.box("Frame", (x - 0.015, -D / 2 + 0.05, 0), (x + 0.015, -D / 2 + 0.05 + p["leg"], H - t - 0.04), "+x -x +y -y")
        b.strut("Frame", (x, y0, 0.004), (x, ym(top_z), top_z), 0.03, 0.03, caps=True)
    parts = b.finish(col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
