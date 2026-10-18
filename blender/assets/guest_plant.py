"""Potted olive tree for the guest suite: a tapered oat-ceramic pot, a bent trunk,
a handful of branches and ~300 narrow two-tone silver-green leaves (one merged mesh
per tone, so only a few draw calls). Origin is the floor centre; about 1.9 m tall."""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestPlant"

P = dict(name=NAME, seed=7, leaves=640, crown_r=0.55, crown_z=1.35)


def leaf(bm, pos, direction, size, curl=0.25):
    """A narrow folded leaf: base at pos, pointing along direction, six triangles."""
    d = Vector(direction).normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    side = d.cross(up).normalized()
    nrm = side.cross(d).normalized()
    L, w = size, size * 0.26
    p0 = Vector(pos)
    mid = p0 + d * L * 0.5
    pts = [p0, mid + side * w + nrm * (curl * w), mid - side * w + nrm * (curl * w),
           p0 + d * L + nrm * (curl * w * 1.4), mid + nrm * (-curl * w * 0.3)]
    v = [bm.verts.new(p) for p in pts]
    for tri in ((0, 1, 4), (0, 4, 2), (1, 3, 4), (4, 3, 2)):
        bm.faces.new([v[i] for i in tri])


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    pot_m = common.pbr_material("M_Ceramic_Oat", (0.55, 0.51, 0.43), roughness=0.55)
    soil_m = common.pbr_material("M_Soil_Dark", (0.02, 0.015, 0.012), roughness=1.0)
    bark_m = common.pbr_material("M_Bark_Olive", (0.14, 0.11, 0.08), roughness=0.9)
    leaf_a = common.pbr_material("M_Leaf_Olive_A", (0.10, 0.17, 0.075), roughness=0.55)
    leaf_b = common.pbr_material("M_Leaf_Olive_B", (0.19, 0.25, 0.14), roughness=0.55)
    for m in (leaf_a, leaf_b):
        m.use_backface_culling = False
    own = (col, root, n)
    A = guest_mats.add

    pot_h, r0, r1 = 0.46, 0.17, 0.235
    A(own, "Pot", guest_mats.cyl_bmesh(r0, pot_h, r2=r1, seg=40), pot_m, (0, 0, pot_h / 2), 0.004)
    A(own, "Rim", guest_mats.cyl_bmesh(r1 + 0.008, 0.02, seg=40), pot_m, (0, 0, pot_h - 0.01), 0.002)
    A(own, "Soil", guest_mats.cyl_bmesh(r1 - 0.01, 0.01, seg=32), soil_m, (0, 0, pot_h - 0.025), 0)

    # trunk: a gentle S curve; branches fork off its upper part
    trunk = [(0.0, 0.0, pot_h - 0.02), (0.02, 0.01, 0.7), (-0.02, 0.0, 0.95), (0.02, -0.02, 1.2), (0.0, 0.0, 1.4)]
    tr = common.tube_object(f"{n}_Trunk", trunk, 0.028, col, bark_m, root, closed=False, profile_res=2)
    common.box_uv(tr, 0.5)
    cz, cr = p["crown_z"], p["crown_r"]
    tips, branches = [], []
    for k in range(11):
        a = k / 11 * 2 * math.pi + rnd.uniform(-0.3, 0.3)
        h = rnd.uniform(0.95, 1.35)
        out = rnd.uniform(0.25, 0.42)
        tip = (math.cos(a) * out, math.sin(a) * out, cz + rnd.uniform(-0.25, 0.35))
        mid = (math.cos(a) * out * 0.35, math.sin(a) * out * 0.35, h + 0.2)
        br = common.tube_object(f"{n}_Branch{k}", [(0.0, 0.0, h), mid, tip], 0.009, col, bark_m, root,
                                closed=False, profile_res=1)
        branches.append(((0.0, 0.0, h), mid, tip))
        common.box_uv(br, 0.5)
        tips.append(Vector(tip))
    tips.append(Vector((0.0, 0.0, 1.62)))

    bms = [bmesh.new(), bmesh.new()]
    for i in range(p["leaves"]):
        p0, p1, p2 = [Vector(q) for q in rnd.choice(branches)]
        t = rnd.uniform(0.35, 1.0)
        pos = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t * t * p2
        pos += Vector((rnd.gauss(0, 0.05), rnd.gauss(0, 0.05), rnd.gauss(0, 0.05)))
        out = Vector((pos.x, pos.y, 0.4 * (pos.z - cz))).normalized()
        d = (out + Vector((rnd.gauss(0, 0.55), rnd.gauss(0, 0.55), rnd.gauss(0, 0.45)))).normalized()
        leaf(bms[i % 2], pos, d, rnd.uniform(0.12, 0.2))
    for k, (bm, m) in enumerate(zip(bms, (leaf_a, leaf_b))):
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        ob = common.mesh_object(f"{n}_Leaves{k}", bm, col, m, root)
    parts = guest_mats.consolidate(root, max_dim=0.7)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
