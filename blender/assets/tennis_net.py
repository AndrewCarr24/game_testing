"""Tennis net on two slim dark-metal posts: the post-to-post net (a faint dark veil with
a white top tape and centre strap, sagging to 0.914 m at the middle), crank boxes on
the posts. The net runs along X, origin at the net centre on the court surface, front
faces -Y. Post centres 0.914 m outside the doubles sidelines (6.4 m from the centre)."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tennis_common as tc  # noqa: E402

importlib.reload(tc)
common = tc.common

NAME = "TennisNet"

P = dict(
    name=NAME,
    post_x=6.40,
    post_h=1.07,
    post_w=0.10,
    centre_h=0.914,
    tape_h=0.07,
    segments=8,
    bottom=0.03,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = tc.standalone(n)
    b = tc.Builder(n)
    b.part("Posts", tc.mat_metal())
    b.part("Veil", tc.mat_veil())
    b.part("Tape", tc.mat_tape())

    px, w = p["post_x"], p["post_w"]
    for s in (-1, 1):
        b.box("Posts", (s * px - w / 2, -w / 2, 0), (s * px + w / 2, w / 2, p["post_h"]), "+x -x +y -y +z")
        # crank housing on the outside of the post
        b.box("Posts", (s * px + (s * w / 2) - (0 if s > 0 else 0.07), -0.045, 0.45),
              (s * px + (s * w / 2) + (0.07 if s > 0 else 0), 0.045, 0.62), "+x -x +y -y +z")

    # net: sagging top edge, 1.6 m segments
    def top(x):
        t = (abs(x) / (px - w / 2)) ** 2
        return p["centre_h"] + (p["post_h"] - 0.02 - p["centre_h"]) * t

    xa = px - w / 2
    n_seg = p["segments"]
    xs = [-xa + 2 * xa * k / n_seg for k in range(n_seg + 1)]
    zb, th, e = p["bottom"], p["tape_h"], 0.006
    for k in range(n_seg):
        x0, x1 = xs[k], xs[k + 1]
        t0, t1 = top(x0), top(x1)
        for s, nrm in ((-1, -1), (1, 1)):          # two faces so it is seen from both sides
            y = s * 0.002
            pts = [(x0, y, zb), (x1, y, zb), (x1, y, t1 - th), (x0, y, t0 - th)]
            if nrm < 0:
                b.quad("Veil", *pts)
            else:
                b.quad("Veil", *pts[::-1])
        # tape: a thin prism following the sag, folded over the cord
        hh = 0.012
        b.quad("Tape", (x0, -hh, t0 - th), (x1, -hh, t1 - th), (x1, -hh, t1), (x0, -hh, t0))        # -y
        b.quad("Tape", (x0, hh, t0 - th), (x0, hh, t0), (x1, hh, t1), (x1, hh, t1 - th))           # +y
        b.quad("Tape", (x0, -hh, t0), (x1, -hh, t1), (x1, hh, t1), (x0, hh, t0))                   # top
    # centre strap (white), both sides
    sw = 0.025
    c = p["centre_h"]
    b.quad("Tape", (-sw, -0.006, zb), (sw, -0.006, zb), (sw, -0.006, c), (-sw, -0.006, c))
    b.quad("Tape", (-sw, 0.006, zb), (-sw, 0.006, c), (sw, 0.006, c), (sw, 0.006, zb))

    parts = b.finish(col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
