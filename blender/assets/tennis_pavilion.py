"""Viewing pavilion: an open-fronted shelter on a low limestone plinth, a white render
back wall, a thin flat white roof with a teak soffit and warm downlights, four slim
dark-metal posts, and a teak-topped drinks counter on a render base. Stone forecourt
in front. 6.0 m wide x 3.0 m deep (plus 2.2 m forecourt), 2.9 m high. The open side
faces -Y; origin the centre of the plinth at ground level. Benches are placed separately
(tennis_bench)."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tennis_common as tc  # noqa: E402

importlib.reload(tc)
common = tc.common
outdoor = tc.outdoor

NAME = "TennisPavilion"

P = dict(
    name=NAME,
    width=6.4,          # plinth
    depth=3.0,
    plinth_h=0.15,
    apron_d=2.2,        # forecourt in front, at court level (0.05)
    apron_h=0.05,
    roof_z=2.72,
    roof_t=0.18,
    overhang=0.30,
    wall_t=0.25,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = tc.standalone(n)
    b = tc.Builder(n)
    b.part("Stone", outdoor.stone(), uv=2.0)
    b.part("Render", tc.mat_render())
    b.part("Soffit", outdoor.teak(), uv=0.5)
    b.part("Metal", tc.mat_metal())
    b.part("Counter", outdoor.teak(), uv=0.5)
    b.part("Lamp", outdoor.lamp("Warm"))
    b.part("Fridge", outdoor.flat("M_Out_Tennis_Fridge", (0.05, 0.05, 0.055)))

    W, D, ph = p["width"], p["depth"], p["plinth_h"]
    hw, hd = W / 2, D / 2
    # plinth and forecourt
    b.box("Stone", (-hw, -hd, 0), (hw, hd, ph), "+x -x +y -y +z", cell=1.55)
    b.box("Stone", (-hw, -hd - p["apron_d"], 0), (hw, -hd, p["apron_h"]), "+x -x -y +z", cell=1.55)
    # back wall
    wt, wz = p["wall_t"], p["roof_z"]
    wx = hw - 0.20
    yb = hd - 0.15
    b.box("Render", (-wx, yb - wt, ph), (wx, yb, wz), "+x -x +y -y", cell=1.5)
    # roof: soffit (teak) under a white slab
    ov, rz, rt = p["overhang"], p["roof_z"], p["roof_t"]
    rx0, rx1 = -wx - ov + 0.2, wx + ov - 0.2
    ry0, ry1 = -hd - 0.35, yb + 0.05
    b.box("Render", (rx0, ry0, rz), (rx1, ry1, rz + rt), "+x -x +y -y +z", cell=1.65)
    b.grid("Soffit", 2, -1, rz, _ax(rx0, rx1, 1.65), _ax(ry0, ry1, 1.5))
    # posts at the front edge
    py = ry0 + 0.20
    xs = [-wx + 0.15 + k * (2 * wx - 0.3) / 3 for k in range(4)]
    for x in xs:
        b.box("Metal", (x - 0.05, py - 0.05, ph), (x + 0.05, py + 0.05, rz), "+x -x +y -y")
    # downlights
    for x in (-1.9, 0.0, 1.9):
        b.box("Lamp", (x - 0.08, -0.55, rz - 0.003), (x + 0.08, -0.39, rz - 0.003), "-z")
        b.box("Lamp", (x - 0.08, 0.40, rz - 0.003), (x + 0.08, 0.56, rz - 0.003), "-z")
    # drinks counter at the east end against the back wall
    cx0, cx1 = wx - 1.75, wx - 0.2
    cy1 = yb - wt
    cy0 = cy1 - 0.55
    b.box("Render", (cx0, cy0, ph), (cx1, cy1, ph + 0.82), "+x -x -y +y", cell=1.5)
    b.box("Fridge", (cx0 + 0.12, cy0 - 0.004, ph + 0.08), (cx0 + 0.72, cy0 - 0.004, ph + 0.62), "-y")
    b.box("Counter", (cx0 - 0.03, cy0 - 0.04, ph + 0.82), (cx1 + 0.03, cy1, ph + 0.86), "+x -x +y -y +z -z")

    parts = b.finish(col, root)
    return root, parts


def _ax(lo, hi, cell):
    return tc._cells(lo, hi, cell)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
