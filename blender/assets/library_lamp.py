"""Banker's lamp: a bronze foot and stem carrying a half-cylinder green glass shade
that glows warm. Origin: centre of the underside (z = 0), the shade's long side faces -Y.
About 0.36 x 0.17 x 0.42 m. Put a point light at z = 0.30."""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import library_kit as kit  # noqa: E402
from library_kit import Mesh, common, materials  # noqa: E402

importlib.reload(kit)

NAME = "LibraryLamp"

P = dict(name=NAME, shade_len=0.36, shade_r=0.085, shade_z=0.335, stem_r=0.011)


def flat_caps(ob):
    """Flat discs and ledges shade flat; only the turned, curved faces stay smooth."""
    for poly in ob.data.polygons:
        if abs(poly.normal.z) > 0.999:
            poly.use_smooth = False
    return ob


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402  (react definitions, prompts/interactivity.md)

importlib.reload(ix_common)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    bronze = materials.bronze()
    glow = materials.emissive("M_Library_BankerGlass", (0.05, 0.30, 0.10), 1.0)

    brz = Mesh(0.5)
    # foot (stepped dome) and stem
    brz.lathe([(0, 0.0), (0.105, 0.0), (0.105, 0.012), (0.092, 0.03), (0.05, 0.05), (0.022, 0.06), (0.0, 0.06)], segs=28)
    brz.lathe([(0, 0.05), (p["stem_r"], 0.05), (p["stem_r"], 0.27), (0.017, 0.28), (0.017, 0.30), (0, 0.30)], segs=14)
    brz.lathe([(0, 0.145), (0.024, 0.145), (0.024, 0.156), (0, 0.156)], segs=12)      # collar
    # shade yoke
    z0 = p["shade_z"]
    brz.box((0, 0, z0 - 0.015), (0.04, 0.05, 0.02))
    brz.box((0, 0, 0.30 + (z0 - 0.30) / 2 - 0.005), (0.02, 0.02, max(z0 - 0.30 - 0.01, 0.01)))
    L, R = p["shade_len"], p["shade_r"]
    segs = 14
    prof = [(R * math.cos(math.pi * i / segs), z0 + R * 0.78 * math.sin(math.pi * i / segs) - 0.015) for i in range(segs + 1)]
    for sx in (-1, 1):
        x = sx * (L / 2 + 0.003)
        for i in range(segs):
            (ya, za), (yb, zb) = prof[i], prof[i + 1]
            pts = [(x, ya, za), (x, yb, zb), (x, 0.0, z0 - 0.015)]
            brz.quad(pts if sx > 0 else pts[::-1], [(0, 0)] * 3)
    flat_caps(brz.to_object(f"{n}_Bronze", col, bronze, root, smooth=True))

    # shade: a cased-glass shell along X (outer + inner surface, 4 mm thick, closed lower
    # edges), with rolled bronze rims on the lower edges and a pull chain under it
    sh = Mesh(0.5)
    L, R = p["shade_len"], p["shade_r"]
    segs = 14
    T = 0.004
    def arc(r):
        return [(r * math.cos(math.pi * i / segs), z0 + r * 0.78 * math.sin(math.pi * i / segs) - 0.015) for i in range(segs + 1)]
    out_, in_ = arc(R), arc(R - T)
    for i in range(segs):
        (ya, za), (yb, zb) = out_[i], out_[i + 1]
        sh.quad([(-L / 2, ya, za), (L / 2, ya, za), (L / 2, yb, zb), (-L / 2, yb, zb)], [(0, 0)] * 4)
        (ya, za), (yb, zb) = in_[i], in_[i + 1]
        sh.quad([(-L / 2, yb, zb), (L / 2, yb, zb), (L / 2, ya, za), (-L / 2, ya, za)], [(0, 0)] * 4)
    for (yo, zo), (yi, zi) in ((out_[0], in_[0]), (out_[-1], in_[-1])):
        q = [(-L / 2, yo, zo), (-L / 2, yi, zi), (L / 2, yi, zi), (L / 2, yo, zo)]
        sh.quad(q if yo > 0 else q[::-1], [(0, 0)] * 4)
    flat_caps(sh.to_object(f"{n}_Shade", col, glow, root, smooth=True))
    rim = Mesh(0.5)
    for (yo, zo) in (out_[0], out_[-1]):
        rim.box((0, yo + (0.0015 if yo > 0 else -0.0015), zo + 0.002), (L + 0.008, 0.0065, 0.0065))
    # pull chain with a bead, hanging from under the shade's crown
    rim.box((0.07, 0.0, z0 - 0.06), (0.0018, 0.0018, 0.085))
    rim.box((0.07, 0.0, z0 - 0.106), (0.008, 0.008, 0.008))
    rim.to_object(f"{n}_Rims", col, bronze, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    ix_common.tag_emissive(root)   # interactivity: glowing parts follow the room's light switch
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
