"""A brass inlay band laid into the library's oak floor in front of the south bookcases: to anyone
it's a decorative panel, the kind fine libraries have; it is the edge of the folding floor
(design/house/secret_passage.md), and once the floor has folded down into a stair it is the brass
nosing round the opening. A 14 mm band, 1.5 mm proud, on three sides of the panel (the fourth
side is the bookcases' plinth), with small square corner blocks.

Origin: the panel's centre on the floor; the panel runs along y (`length`), `width` across x;
its open side (no band) is at -y (against the bookcases)."""
import importlib
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)

NAME = "LibraryFloorInlay"

P = dict(
    name=NAME,
    width=0.95,           # the hatch, across (x)
    length=4.05,          # the hatch, along (y)
    band=0.014,
    proud=0.0015,
    corner=0.03,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    w, L, b, h, c = p["width"], p["length"], p["band"], p["proud"], p["corner"]
    bm = bmesh.new()

    def box(cx, cy, sx, sy, sz):
        g = common.box_bmesh((sx, sy, sz))
        bmesh.ops.translate(g, vec=(cx, cy, sz / 2), verts=g.verts)
        me = __import__("bpy").data.meshes.new("_inlay_tmp")
        g.to_mesh(me)
        g.free()
        bm.from_mesh(me)
        __import__("bpy").data.meshes.remove(me)

    # the band sits just outside the panel's edge (the strips fill the panel exactly)
    box(-w / 2 - b / 2, 0, b, L, h)                    # west side
    box(w / 2 + b / 2, 0, b, L, h)                     # east side
    box(0, L / 2 + b / 2, w + 2 * b, b, h)             # the far (north) end
    for sx in (-1, 1):
        box(sx * (w / 2 + b / 2), L / 2 + b / 2, c, c, h * 1.4)     # corner blocks at the far end
    ob = common.mesh_object(f"{n}_Brass_NoCollide", bm, col, materials.bronze(), root, smooth=False)
    common.box_uv(ob, tile=0.5)
    parts = [ob]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {common.triangle_count(parts)} tris")
