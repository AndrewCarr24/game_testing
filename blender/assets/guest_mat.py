"""Exercise mats: a sage yoga mat and an oat mat laid slightly offset (flat), a
rolled mat, a foam roller and a folded towel on top. Mats are 1.85 x 0.62 m; the
whole set occupies about 1.9 x 1.3 m. Origin is the floor centre."""
import importlib
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestMat"

P = dict(name=NAME)


def spiral_roll(r0, r1, t, turns, length, per_turn=22):
    """A mat of thickness t rolled from radius r0 to r1: the spiral section (outer edge out,
    inner edge back) extruded along y over `length`; the curved faces are smoothed."""
    import math
    import bmesh
    N = int(per_turn * turns)
    outer, inner = [], []
    for k in range(N + 1):
        th = 2 * math.pi * turns * k / N
        r = r0 + (r1 - r0 - t / 2) * k / N
        outer.append(((r + t / 2) * math.cos(th), (r + t / 2) * math.sin(th)))
        inner.append(((r - t / 2) * math.cos(th), (r - t / 2) * math.sin(th)))
    prof = outer + inner[::-1]
    bm = bmesh.new()
    a = [bm.verts.new((x, -length / 2, z)) for x, z in prof]
    b = [bm.verts.new((x, length / 2, z)) for x, z in prof]
    m = len(prof)
    for k in range(m):
        f = bm.faces.new((a[k], a[(k + 1) % m], b[(k + 1) % m], b[k]))
        f.smooth = k not in (N, m - 1)          # the two strip ends stay crisp
    bm.faces.new(a[::-1])
    bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rub = guest_mats.rubber()
    sage = common.pbr_material("M_Mat_Sage", (0.17, 0.25, 0.15), roughness=0.75)
    oat = common.pbr_material("M_Mat_Oat", (0.50, 0.45, 0.37), roughness=0.75)
    towel = guest_mats.linen()
    own = (col, root, n)
    A = guest_mats.add
    t = 0.012
    A(own, "MatA", common.rounded_slab_bmesh(1.85, 0.62, t, 0.02), sage, (0.0, -0.32, t / 2), 0.003, tile=0.5)
    A(own, "MatB", common.rounded_slab_bmesh(1.85, 0.62, t, 0.02), oat, (0.06, 0.34, t / 2), 0.003, tile=0.5)
    # rolled mat at one end: the mat itself wound up (a thick spiral strip), so its end
    # shows the turns
    roll = common.mesh_object(f"{n}_Roll", spiral_roll(0.022, 0.104, t, 3.0, 0.62), col, sage, root, smooth=False)
    roll.location = (0.72, -0.32, 0.012 + 0.085)
    common.box_uv(roll, 0.5)
    # foam roller
    fr = common.mesh_object(f"{n}_FoamRoller", guest_mats.cyl_bmesh(0.075, 0.45, seg=28, axis="x"), col, rub, root)
    fr.location = (-0.5, 0.35, t + 0.075)
    common.box_uv(fr, 0.5)
    parts = guest_mats.consolidate(root, max_dim=0.2)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
