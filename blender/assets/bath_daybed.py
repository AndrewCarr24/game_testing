"""Spa daybed: a honed-stone plinth base with a thick oat linen mattress (piped welts
round its top and bottom edges), a rolled bolster at the head with piped ends, two
scatter cushions (ink and ivory) and a folded ink throw draped over the front at the foot.
The head (bolster) is at the +X end. Origin: floor centre, front -Y.
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import bath_common as bc  # noqa: E402

importlib.reload(common)
importlib.reload(bc)

NAME = "BathDaybed"

P = dict(name=NAME, size=(2.0, 0.82), seat_h=0.44, base_h=0.24, base_inset=0.05)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    stone, black = bc.stone(), materials.black_metal()
    oat = materials.fabric("M_Fabric_Oat", (0.42, 0.37, 0.30))
    ivory = materials.fabric("M_Fabric_Linen_Ivory", (0.55, 0.52, 0.46))
    ink = materials.fabric("M_Fabric_Ink", (0.02, 0.03, 0.06))

    W, D = p["size"]
    H, bh, ins = p["seat_h"], p["base_h"], p["base_inset"]
    # stone plinth (a slab, recessed from the mattress edge) on a dark shadow foot
    bc.box(col, root, f"{n}_Foot", (W - 0.30, D - 0.24, 0.05), (0, 0, 0.025), black, bevel=0.002)
    bc.box(col, root, f"{n}_Base", (W - 0.04, D - 0.04, bh - 0.05), (0, 0, 0.05 + (bh - 0.05) / 2), stone, bevel=0.012, uv_tile=1.0)
    # mattress
    mt = H - bh
    mat = common.mesh_object(f"{n}_Mattress", common.cushion_bmesh((W, D, mt), edge=0.035, crown={"+z": 0.02}), col, oat, root)
    mat.location = (0, 0, bh + mt / 2)
    common.box_uv(mat, tile=0.25)
    common.add_subsurf(mat)
    # piped welts round the mattress's top and bottom edges
    for k, loop in enumerate(common.piping_loop((W, D, mt), "z", 0.0075, 0.03)):
        pts = [(v.x, v.y, v.z + bh + mt / 2) for v in loop]
        common.box_uv(common.tube_object(f"{n}_PipingWelt_{k}", pts, 0.0055, col, oat, root, closed=True, profile_res=1),
                      tile=0.25)
    # bolster at the head (+X end): a soft roll with piped, slightly domed ends
    br = 0.115
    bx, bz = W / 2 - 0.22, H + br - 0.01
    by0, by1 = -D / 2 + 0.14, D / 2 - 0.14
    prof = [(0.0, by0 - 0.012), (br * 0.55, by0 - 0.009), (br * 0.92, by0 - 0.003), (br, by0 + 0.006)]
    prof += [(br, by1 - 0.006), (br * 0.92, by1 + 0.003), (br * 0.55, by1 + 0.009), (0.0, by1 + 0.012)]
    bol = bc.lathe(prof, 24)
    bmesh.ops.rotate(bol, verts=bol.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(-90), 3, "X"))
    bmesh.ops.rotate(bol, verts=bol.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(180), 3, "Z"))
    bmesh.ops.translate(bol, vec=(bx, 0, bz), verts=bol.verts)
    common.box_uv(common.mesh_object(f"{n}_Bolster", bol, col, ivory, root), tile=0.25)
    for k, yy in enumerate((by0 + 0.004, by1 - 0.004)):
        ring = [(bx + (br + 0.002) * math.cos(2 * math.pi * i / 20), yy, bz + (br + 0.002) * math.sin(2 * math.pi * i / 20))
                for i in range(20)]
        common.box_uv(common.tube_object(f"{n}_PipingBolster_{k}", ring, 0.005, col, ivory, root, closed=True,
                                         profile_res=1), tile=0.25)
    # two scatter cushions leaning on the bolster
    for i, (mat_, y, sz) in enumerate(((ink, -0.17, (0.12, 0.46, 0.42)), (ivory, 0.19, (0.11, 0.40, 0.38)))):
        c = common.mesh_object(f"{n}_Pillow_{i}", common.cushion_bmesh(sz, cuts=3, edge=0.04, crown={"+x": 0.03, "-x": 0.03}),
                               col, mat_, root)
        common.box_uv(c, tile=0.25)
        common.add_subsurf(c)
        c.rotation_euler = (0, math.radians(17 + 3 * i), math.radians(4 - 8 * i))
        c.location = (W / 2 - 0.22 - br - 0.065 - 0.01 * i, y, H + sz[2] / 2 + 0.005)
    # folded throw over the foot end: lies across the top (following the crown) and drapes
    # over the front edge. The path is the throw's underside; it rounds the edge on a tight
    # radius about a centre near the corner so it clears the welt without standing far off.
    tt = 0.016                      # folded: two layers
    c_, g_ = 0.017, 0.002
    path = []
    for k in range(9):
        y = D / 2 - 0.07 - (D - 0.07 - c_) * k / 8
        uy = y / (D / 2)
        path.append((y, H + 0.004 + 0.02 * 0.86 * max(0.0, 1 - uy * uy)))
    zc = path[-1][1] - (c_ + g_)
    for k in range(1, 7):
        a = math.pi / 2 + (math.pi / 2) * k / 6
        path.append((-D / 2 + c_ + (c_ + g_) * math.cos(a), zc + (c_ + g_) * math.sin(a)))
    path += [(-D / 2 - 0.0015, H - 0.10), (-D / 2 + 0.0005, H - 0.165)]
    throw = _strip(path, tt, -W / 2 + 0.10, -W / 2 + 0.62)
    t_ob = common.mesh_object(f"{n}_PipingThrow", throw, col, ink, root)
    common.box_uv(t_ob, tile=0.25)
    return root, bc.parts_of(root)


def _strip(path, t, x0, x1):
    """Extrude a thick strip along X: `path` is the (y, z) centre-line of its underside;
    the top is offset by t along the path's right-hand normal. Ends are capped."""
    import bmesh as _bm
    from mathutils import Vector as V
    pts = [V(p) for p in path]
    under, over = [], []
    for i, pt in enumerate(pts):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        d = (b - a).normalized()
        nrm = V((d.y, -d.x))          # right of travel: up on the top run, outward on the drape
        under.append(pt)
        over.append(pt + nrm * t)
    outline = under + over[::-1]
    bm = _bm.new()
    left = [bm.verts.new((x0, q.x, q.y)) for q in outline]
    right = [bm.verts.new((x1, q.x, q.y)) for q in outline]
    m = len(outline)
    for i in range(m):
        j = (i + 1) % m
        bm.faces.new((left[i], left[j], right[j], right[i]))
    bm.faces.new(left[::-1])
    bm.faces.new(right)
    _bm.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # sharp at the cut ends, smooth along the folds
    for e_ in bm.edges:
        if abs(e_.verts[0].co.x - e_.verts[1].co.x) < 1e-6:
            e_.smooth = False
    return bm


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
