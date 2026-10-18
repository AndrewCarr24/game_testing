"""One leaf of the sliding gate (shown closed): dark steel frame with vertical slats that
alternate 3 cm in depth, hung 10 cm above the apron on two track carriages. Placed twice,
meeting in the middle of the drive. Units are metres. The front faces -Y.
Origin: the leaf's centre on the ground (in the plane of its mid-depth).
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_common as gc  # noqa: E402

importlib.reload(gc)
common, outdoor = gc.common, gc.outdoor

NAME = "GateLeaf"

P = dict(
    name=NAME,
    width=3.96,
    bottom=0.10,
    height=2.50,        # top of the leaf above the ground
    stile=0.10,
    top_rail=(0.16, 0.09),      # height, depth
    bottom_rail=(0.20, 0.09),
    slat=(0.055, 0.045),        # width, depth
    pitch=0.088,
    stagger=0.03,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    parts = gc.Parts(n, col, root)
    bm = parts.bm("Frame", outdoor.dark_metal())
    V = gc.V
    W2 = p["width"] / 2
    z0, z1 = p["bottom"], p["height"]
    th, td = p["top_rail"]
    bh, bd = p["bottom_rail"]
    s = p["stile"]
    # frame
    gc.box(bm, V(-W2, -bd / 2, z0), V(W2, bd / 2, z0 + bh), step=4.0, top=True, bottom=True)
    gc.box(bm, V(-W2, -td / 2, z1 - th), V(W2, td / 2, z1), step=4.0, top=True, bottom=False)
    for sx in (-1, 1):
        x0, x1 = (sx * W2 - s, sx * W2) if sx > 0 else (sx * W2, sx * W2 + s)
        gc.box(bm, V(x0, -td / 2, z0 + bh), V(x1, td / 2, z1 - th), step=4.0, top=False)
    # slats between the stiles, alternating in depth
    sw, sd = p["slat"]
    span = p["width"] - 2 * s
    count = int(span // p["pitch"])
    pitch = span / count
    for i in range(count):
        xc = -W2 + s + pitch * (i + 0.5)
        dy = p["stagger"] * (1 if i % 2 else -1) / 2
        gc.box(bm, V(xc - sw / 2, dy - sd / 2, z0 + bh), V(xc + sw / 2, dy + sd / 2, z1 - th),
               step=3.0, top=False, bottom=False)
    # two track carriages (sunk into the apron's steel track)
    for cx in (-W2 + 0.35, W2 - 0.35):
        gc.box(bm, V(cx - 0.12, -0.05, 0.0), V(cx + 0.12, 0.05, z0), step=2.0, top=False, bottom=False)
    return root, parts.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
