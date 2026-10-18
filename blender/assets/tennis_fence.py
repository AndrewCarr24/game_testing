"""Court enclosure: slim dark-metal posts, top, mid and bottom rails and a faint dark
mesh veil, 3.6 m high behind both baselines (and for one bay along the sidelines),
2.0 m along the sides, with a gate in bay 5 (y 2..6 m) of each long side. Rectangle
17.9 x 36.3 m (posts just inside the edge of the 18.3 x 36.6 m surround), origin the
court centre, base on the court surface. One piece so the posts and rails line up."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tennis_common as tc  # noqa: E402

importlib.reload(tc)
common = tc.common
outdoor = tc.outdoor

NAME = "TennisFence"

P = dict(
    name=NAME,
    half_w=8.95,         # post line, x
    half_l=18.15,        # post line, y
    side_bays=9,         # bays along each long side (4.03 m)
    end_bays=4,          # bays along each end (4.48 m)
    tall=3.6,
    low=2.0,
    tall_side_bays=1,    # bays at the corners of the long sides that stay tall
    post=0.09,
    rail=0.05,           # rail height; its thickness across the fence is 0.04
    gate_w=1.5,
    gate_bay=5,          # long-side bay (0 = south) holding the gate on both sides
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = tc.standalone(n)
    b = tc.Builder(n)
    b.part("Metal", tc.mat_metal())
    b.part("Veil", tc.mat_veil())
    b.part("Handle", outdoor.bronze())
    pw, rw = p["post"], p["rail"]
    T = 0.02                                         # half thickness of a rail across the fence

    def post(x, y, h, w=None):
        w = w or pw
        b.box("Metal", (x - w / 2, y - w / 2, 0), (x + w / 2, y + w / 2, h), "+x -x +y -y +z")

    def rails_for(h):
        return [0.10, 1.85, h - 0.04] if h > 3.0 else [0.10, h - 0.04]

    def run(axis, fixed, a, c, h):
        """Rails and veil from a to c along `axis` (a < c) on the line `fixed`."""
        rails = rails_for(h)
        for k, z in enumerate(rails):
            under = "" if k == 0 else " -z"          # the bottom rail's underside is never seen
            if axis == "x":
                b.box("Metal", (a, fixed - T, z - rw / 2), (c, fixed + T, z + rw / 2), "-y +y +z" + under)
            else:
                b.box("Metal", (fixed - T, a, z - rw / 2), (fixed + T, c, z + rw / 2), "-x +x +z" + under)
        for z0, z1 in zip(rails[:-1], rails[1:]):
            z0, z1 = z0 + rw / 2, z1 - rw / 2
            veil(axis, fixed, a, c, z0, z1)

    def veil(axis, fixed, a, c, z0, z1):
        for off, flip in ((-0.002, False), (0.002, True)):
            if axis == "x":
                pts = [(a, fixed + off, z0), (c, fixed + off, z0), (c, fixed + off, z1), (a, fixed + off, z1)]
            else:
                pts = [(fixed + off, a, z0), (fixed + off, c, z0), (fixed + off, c, z1), (fixed + off, a, z1)]
            if (axis == "x") != flip:
                pass
            else:
                pts = pts[::-1]
            b.quad("Veil", *pts)

    hx, hy = p["half_w"], p["half_l"]
    nb, sb = p["end_bays"], p["side_bays"]
    # ---- ends (along X): tall
    xs = [-hx + 2 * hx * k / nb for k in range(nb + 1)]
    for sy in (-1, 1):
        for k in range(nb):
            run("x", sy * hy, xs[k], xs[k + 1], p["tall"])
        for k in range(1, nb):
            post(xs[k], sy * hy, p["tall"])
    # ---- long sides (along Y)
    ys = [-hy + 2 * hy * k / sb for k in range(sb + 1)]
    gate_bay = p["gate_bay"]
    for sx in (-1, 1):
        fx = sx * hx
        for k in range(sb):
            h = p["tall"] if (k < p["tall_side_bays"] or k >= sb - p["tall_side_bays"]) else p["low"]
            y0, y1 = ys[k], ys[k + 1]
            if k != gate_bay:
                run("y", fx, y0, y1, h)
                continue
            gc = (y0 + y1) / 2
            a0, a1 = gc - p["gate_w"] / 2, gc + p["gate_w"] / 2          # leaf
            g0, g1 = a0 - 0.05, a1 + 0.05                                   # gate posts
            run("y", fx, y0, g0, h)
            run("y", fx, g1, y1, h)
            for gy in (g0, g1):
                post(fx, gy, h + 0.04, 0.10)
            for gy in (a0 + 0.02, a1 - 0.02):                               # stiles
                b.box("Metal", (fx - T, gy - 0.02, 0.06), (fx + T, gy + 0.02, h - 0.02), "-x +x +y -y")
            for z in (0.10, h * 0.5, h - 0.04):
                b.box("Metal", (fx - T, a0, z - 0.025), (fx + T, a1, z + 0.025), "-x +x -z +z")
            veil("y", fx, a0 + 0.04, a1 - 0.04, 0.10 + 0.025, h * 0.5 - 0.025)
            veil("y", fx, a0 + 0.04, a1 - 0.04, h * 0.5 + 0.025, h - 0.04 - 0.025)
            b.box("Handle", (fx - 0.045, a1 - 0.20, 0.98), (fx + 0.045, a1 - 0.07, 1.04), "+x -x +y -y +z")
        for k in range(1, sb):
            tall = k <= p["tall_side_bays"] or k >= sb - p["tall_side_bays"]
            post(fx, ys[k], p["tall"] if tall else p["low"])
    for sx in (-1, 1):
        for sy in (-1, 1):
            post(sx * hx, sy * hy, p["tall"], 0.12)

    parts = b.finish(col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
