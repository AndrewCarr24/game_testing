"""Guest curtain panel: a full-height pleated linen panel (wave fold, ripple-fold
heading) hanging from a slim black rod. 1.3 m wide gathered, 3.65 m drop. Faces -Y
(towards the room); the rod is at the back, origin at floor centre of the panel."""
import importlib
import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestCurtain"

P = dict(name=NAME, width=1.3, drop=3.65, folds=7, amp=0.07, thick=0.012)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    linen = guest_mats.materials.fabric("M_Fabric_Curtain", (0.60, 0.57, 0.50), roughness=0.95)
    black = guest_mats.black()
    W, Hh, F, amp, th = p["width"], p["drop"], p["folds"], p["amp"], p["thick"]
    nx, nz = F * 8, 6
    bm = bmesh.new()
    front, back = {}, {}
    for i in range(nx + 1):
        u = i / nx
        for j in range(nz + 1):
            v = j / nz                         # 0 at the floor
            a = amp * (0.75 + 0.35 * v) * (1 + 0.15 * math.sin(7 * u + 3 * v))
            y = -a * 0.5 * (1 - math.cos(2 * math.pi * F * u + 0.4 * v))
            x = (u - 0.5) * W * (1 + 0.02 * math.sin(11 * v))
            z = v * Hh
            front[i, j] = bm.verts.new((x, y - th / 2, z))
            back[i, j] = bm.verts.new((x, y + th / 2, z))
    for i in range(nx):
        for j in range(nz):
            bm.faces.new([front[i, j], front[i, j + 1], front[i + 1, j + 1], front[i + 1, j]])
            bm.faces.new([back[i, j], back[i + 1, j], back[i + 1, j + 1], back[i, j + 1]])
    for j in range(nz):
        bm.faces.new([front[0, j], back[0, j], back[0, j + 1], front[0, j + 1]])
        bm.faces.new([front[nx, j], front[nx, j + 1], back[nx, j + 1], back[nx, j]])
    for i in range(nx):
        bm.faces.new([front[i, nz], front[i + 1, nz], back[i + 1, nz], back[i, nz]])
        bm.faces.new([front[i, 0], back[i, 0], back[i + 1, 0], front[i + 1, 0]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    cur = common.mesh_object(f"{n}_Panel", bm, col, linen, root)
    common.box_uv(cur, 0.5)
    rod = common.mesh_object(f"{n}_Rod", guest_mats.cyl_bmesh(0.011, W + 0.2, seg=12, axis="x"), col, black, root)
    rod.location = (0, 0.03, Hh + 0.04)
    return root, [o for o in root.children_recursive if o.type == "MESH"]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
