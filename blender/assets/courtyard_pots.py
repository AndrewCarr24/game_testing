"""A cluster of hand-thrown terracotta pots of different sizes and shapes (rolled-rim
pots, a tall long-tom, a wide low bowl), grouped the way a gardener would, each planted:
a fern, a clipped boxwood ball, a silver-leaved shrub, golden grass, sedge, and star jasmine
spilling over the rims. Variants:

  door   flanking the doorway: a tall long-tom with a shrub, a rolled-rim pot of grass, a
         low bowl of jasmine
  mast   round a festoon mast's foot: a big low pot centred on the mast (jasmine trailing,
         sedge) and a fern pot beside it
  corner three pots, fern / grass / boxwood

Collision: each pot is its own mesh; plants are NoCollide (boxwood balls sit inside the
pot's box). Origin: the cluster's main pot centre on the floor. Units are metres."""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import courtyard_common as cc  # noqa: E402
import courtyard_bed as bed  # noqa: E402
import courtyard_olive_tree as olive  # noqa: E402

importlib.reload(cc)
importlib.reload(bed)
importlib.reload(olive)
common = cc.common

NAME = "CourtyardPots"

P = dict(
    name=NAME,
    variant="corner",
    seed=2,
)

# (x, y, shape, scale, plant)
VARIANTS = {
    "door": [(0.0, 0.0, "tom", 1.0, "shrub"), (0.48, -0.30, "roll", 0.85, "grass"),
             (-0.30, -0.42, "bowl", 0.8, "jasmine")],
    "mast": [(0.0, 0.0, "low", 1.0, "mast"), (0.62, -0.38, "roll", 0.75, "fern")],
    "corner": [(0.0, 0.0, "roll", 1.15, "fern"), (0.58, -0.22, "tom", 0.8, "grass"),
               (0.20, -0.62, "roll", 0.6, "box")],
}

# profiles (r, z) for scale 1, outer surface up and over the rim, down the inside to the soil;
# the last entry is the soil height
SHAPES = {
    "roll": ([(0.17, 0.0), (0.175, 0.012), (0.24, 0.30), (0.262, 0.43), (0.272, 0.445), (0.29, 0.455),
              (0.298, 0.49), (0.29, 0.525), (0.255, 0.53), (0.245, 0.50)], 0.48),
    "tom": ([(0.16, 0.0), (0.165, 0.012), (0.24, 0.66), (0.262, 0.68), (0.275, 0.72), (0.266, 0.745),
             (0.235, 0.748), (0.228, 0.71)], 0.69),
    "bowl": ([(0.14, 0.0), (0.15, 0.012), (0.30, 0.13), (0.37, 0.22), (0.385, 0.25), (0.37, 0.262),
              (0.34, 0.25), (0.33, 0.22)], 0.21),
    "low": ([(0.30, 0.0), (0.31, 0.012), (0.41, 0.30), (0.435, 0.40), (0.452, 0.415), (0.455, 0.45),
             (0.44, 0.465), (0.40, 0.46), (0.395, 0.43)], 0.41),
}


def pot(name, shape, scale, loc, col, mat, soil, root, rng):
    prof, zs = SHAPES[shape]
    prof = [(r * scale, z * scale) for r, z in prof]
    segs = 18 if prof[0][0] > 0.22 else 16
    bm = bmesh.new()
    rot = Matrix.Rotation(rng.uniform(0, 6.28), 4, "Z")
    cc.lathe_bm(bm, prof, segs, rot)        # traced up the outside and down the inside: normals face out
    ob = common.mesh_object(name, bm, col, mat, root, smooth=True)
    ob.location = loc
    sb = bmesh.new()
    rin = prof[-1][0] * 1.01
    cc.lathe_bm(sb, [(0.0, zs * scale + 0.01), (rin * 0.6, zs * scale + 0.005), (rin, zs * scale - 0.01)], segs)
    for f in sb.faces:
        f.normal_update()
        if f.normal.z < 0:
            f.normal_flip()
    so = common.mesh_object(name + "Soil", sb, col, soil, root, smooth=True)
    so.location = loc
    return zs * scale, prof[-3][0], max(z for r, z in prof)


def rim_trailers(pl, centre, r_in, r_out, z_rim, n, rng, drop=(0.18, 0.35)):
    """Jasmine strands from the soil over the rim and down the pot's side."""
    a0 = rng.uniform(0, 6.28)
    for k in range(n):
        a = a0 + k * 2 * math.pi / n + rng.uniform(-0.4, 0.4)
        d = Vector((math.cos(a), math.sin(a), 0))
        dz = min(rng.uniform(*drop), z_rim - 0.03)
        c0 = Vector((centre.x, centre.y, 0))
        pts = [c0 + d * r_in * 0.5 + Vector((0, 0, z_rim - 0.05)), c0 + d * (r_out + 0.01) + Vector((0, 0, z_rim + 0.025)),
               c0 + d * (r_out + 0.05) + Vector((0, 0, z_rim - 0.07)),
               c0 + d * (r_out + 0.06) + Vector((0, 0, z_rim - dz))]
        side = d.cross(Vector((0, 0, 1))) * 0.12
        pl.strip(pts, side, "jasmine", [Vector((0, 0, 1)), (d + Vector((0, 0, 0.6))).normalized(), d, d],
                 widths=[0.7, 1.0, 1.0, 0.8])


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rng = random.Random(p["seed"])
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    terra, soil, leaf, box = cc.terracotta_mat(), cc.soil_mat(), cc.foliage_mat(), cc.boxwood_mat()
    pl = bed.Planting(rng)
    bmb = bmesh.new()
    stems = bmesh.new()
    for i, (x, y, shape, s, plant) in enumerate(VARIANTS[p["variant"]]):
        zs, r_rim, z_top = pot(f"{n}_Pot{i}", shape, s, (x, y, 0), col, terra, soil, root, rng)
        c = Vector((x, y, zs))
        if plant == "fern":
            bed.fern(pl, c, 0.62 * s + 0.2, 9)
        elif plant == "grass":
            bed.grass(pl, c, 0.95 * s + 0.25)
            bed.grass(pl, c + Vector((0.06, -0.05, 0)), 0.75 * s + 0.2, "grassA", 4)
        elif plant == "shrub":
            # a little multi-stemmed standard: three bare stems, then the leafy head
            r = 0.40 * s
            head = c + Vector((0, 0, 0.42 + r * 0.6))
            for k in range(3):
                a = k * 2.1 + rng.uniform(-0.3, 0.3)
                top = head + Vector((math.cos(a) * r * 0.25, math.sin(a) * r * 0.25, -r * 0.2))
                pts = [c + Vector((math.cos(a) * 0.03, math.sin(a) * 0.03, -0.02)), c.lerp(top, 0.5) +
                       Vector((rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03), 0)), top]
                rings, tang = olive.rings_along(pts, [0.016, 0.012, 0.007], 5)
                olive.emit(stems, rings, 0, 2, cap_tip=pts[-1] + tang[-1] * 0.01)
            bed.shrub(pl, head, r, 26)
        elif plant == "box":
            r = 0.21 * s + 0.07
            bed.boxwood(bmb, c + Vector((0, 0, r * 0.62)), r, rng)
        elif plant == "jasmine":
            for k in range(3):
                bed.grass(pl, c + Vector((rng.uniform(-0.1, 0.1), rng.uniform(-0.1, 0.1), 0)), 0.35, "grassB", 3)
            rim_trailers(pl, c, r_rim, r_rim + 0.02, z_top, 8, rng, (0.12, 0.22))
        elif plant == "mast":
            # a ring of sedge round the mast and jasmine spilling over the rim
            for k in range(5):
                a = k * 2 * math.pi / 5 + rng.uniform(-0.3, 0.3)
                bed.grass(pl, c + Vector((math.cos(a) * 0.22 * s, math.sin(a) * 0.22 * s, 0)), 0.45, "grassB", 3)
            rim_trailers(pl, c, r_rim, r_rim + 0.02, z_top, 9, rng, (0.2, 0.36))
        if plant in ("fern", "grass", "shrub", "box") and shape != "tom":
            rim_trailers(pl, c, r_rim, r_rim + 0.02, z_top, 3, rng, (0.1, 0.25))
    pl.finish(f"{n}_PlantsNoCollide", col, leaf, root)
    if bmb.verts:
        common.mesh_object(f"{n}_Boxwood", bmb, col, box, root, smooth=True)
    else:
        bmb.free()
    if stems.verts:
        common.mesh_object(f"{n}_Stems", stems, col, cc.bark_mat(), root, smooth=True)
    else:
        stems.free()
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
