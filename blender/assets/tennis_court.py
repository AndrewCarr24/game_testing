"""Hard tennis court: a 36.6 x 18.3 m dark-green surround with the 23.77 x 10.97 m
blue-grey playing area and the white lines (ITF dimensions), as a low concrete slab.
Long axis along Y (the net line is along X at y = 0), origin the court centre at lawn
level, the court surface 5 cm above it. The surfaces are cut into cells of ~1.5 m so
the baked vertex lighting can show shadows (house, fence, pavilion) across them."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tennis_common as tc  # noqa: E402

importlib.reload(tc)
common, outdoor = tc.common, tc.outdoor

NAME = "TennisCourt"

P = dict(
    name=NAME,
    width=18.3,          # surround, across the net (x)
    length=36.6,         # surround, baseline to baseline run-off included (y)
    play_w=10.97,        # doubles width
    play_l=23.77,
    single_w=8.23,
    service=6.40,        # service line to the net
    top=tc.COURT_TOP,
    line_w=0.05,
    base_w=0.10,
    line_h=0.004,        # lines proud of the surface (a hair over the 3 mm brief: no z-fighting at 60 m)
)


def _axis(lo, hi, n):
    return [lo + (hi - lo) * k / n for k in range(n + 1)]


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = tc.standalone(n)
    b = tc.Builder(n)
    b.part("Surround", tc.mat_surround())
    b.part("Play", tc.mat_play())
    b.part("Lines", tc.mat_line())
    b.part("Edge", outdoor.concrete())

    W, L, pw, pl = p["width"], p["length"], p["play_w"], p["play_l"]
    z = p["top"]
    hw, hl, hpw, hpl = W / 2, L / 2, pw / 2, pl / 2

    # --- surfaces: grid lines fall on the playing-area edge so the two colours meet cleanly
    xs = _axis(-hw, -hpw, 2)[:-1] + _axis(-hpw, hpw, 8) + _axis(hpw, hw, 2)[1:]
    ys = _axis(-hl, -hpl, 4)[:-1] + _axis(-hpl, hpl, 16) + _axis(hpl, hl, 4)[1:]
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            inside = (abs((xs[i] + xs[i + 1]) / 2) < hpw) and (abs((ys[j] + ys[j + 1]) / 2) < hpl)
            b.grid("Play" if inside else "Surround", 2, 1, z, [xs[i], xs[i + 1]], [ys[j], ys[j + 1]])

    # --- slab edge (concrete), cut every ~3.6 m (barely shaded)
    for sx in (-1, 1):
        b.grid("Edge", 0, sx, sx * hw, _axis(-hl, hl, 10), [0.0, z])
    for sy in (-1, 1):
        b.grid("Edge", 1, sy, sy * hl, [0.0, z], _axis(-hw, hw, 5))

    # --- lines: single quads a hair above the surface, cut every ~2.4 m
    zl = z + p["line_h"]
    lw, bw = p["line_w"], p["base_w"]

    def strip(x0, y0, x1, y1):
        nx = max(1, int(round((x1 - x0) / 2.4)))
        ny = max(1, int(round((y1 - y0) / 2.4)))
        b.grid("Lines", 2, 1, zl, _axis(x0, x1, nx), _axis(y0, y1, ny))

    sw2 = p["single_w"] / 2
    for sx in (-1, 1):
        # doubles and singles sidelines (outer edge of the line on the court boundary)
        x_out = sx * hpw
        x_in = x_out - sx * lw
        strip(min(x_out, x_in), -hpl, max(x_out, x_in), hpl)
        xs0 = sx * sw2
        strip(xs0 - lw / 2, -hpl, xs0 + lw / 2, hpl)
    for sy in (-1, 1):
        y_out = sy * hpl
        y_in = y_out - sy * bw
        strip(-hpw, min(y_out, y_in), hpw, max(y_out, y_in))
        # service line and centre mark
        ys0 = sy * p["service"]
        strip(-sw2, ys0 - lw / 2, sw2, ys0 + lw / 2)
        b.grid("Lines", 2, 1, zl, [-lw / 2, lw / 2], sorted([y_in, y_in - sy * 0.10]))
    strip(-lw / 2, -p["service"], lw / 2, p["service"])      # centre service line

    parts = b.finish(col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
