"""Court floodlight mast: a tapered dark-metal pole with a base plate, a cross-arm and two
LED heads aimed down and toward -Y (rotate the placement to aim at the court). 6.5 m.
Origin the floor centre; the lenses glow (baked emission)."""
import importlib
import math
import os
import sys

from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tennis_common as tc  # noqa: E402

importlib.reload(tc)
common = tc.common
outdoor = tc.outdoor

NAME = "TennisFloodlight"

P = dict(name=NAME, height=6.5, base_w=0.20, top_w=0.11, head_tilt=28.0)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = tc.standalone(n)
    b = tc.Builder(n)
    b.part("Metal", tc.mat_metal())
    b.part("Lens", outdoor.lamp("Flood"))

    H = p["height"]
    b.box("Metal", (-0.18, -0.18, 0), (0.18, 0.18, 0.025), "+x -x +y -y +z")
    b.strut("Metal", (0, 0, 0.025), (0, 0, H), p["base_w"], p["top_w"], caps=False)
    b.box("Metal", (-0.075, -0.075, H - 0.01), (0.075, 0.075, H + 0.03), "+x -x +y -y +z")
    # cross-arm and heads (heads face -Y, tilted down)
    b.box("Metal", (-0.55, -0.04, H - 0.10), (0.55, 0.04, H - 0.04), "+x -x +y -y +z -z")
    tilt = math.radians(p["head_tilt"])
    for sx in (-0.38, 0.38):
        pivot = (sx, -0.04, H - 0.12)
        M = Matrix.Translation(pivot) @ Matrix.Rotation(tilt, 4, "X") @ Matrix.Translation((-pivot[0], -pivot[1], -pivot[2]))
        b.box("Metal", (sx - 0.22, -0.30, H - 0.20), (sx + 0.22, -0.06, H - 0.04), "+x -x +y +z -z", M=M)
        b.box("Metal", (sx - 0.22, -0.30, H - 0.20), (sx + 0.22, -0.06, H - 0.04), "-y", M=M)
        b.box("Lens", (sx - 0.19, -0.306, H - 0.18), (sx + 0.19, -0.306, H - 0.06), "-y", M=M)
    parts = b.finish(col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
