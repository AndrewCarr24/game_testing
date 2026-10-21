"""Low outdoor coffee table: a stepped honed-limestone plinth (recessed foot, block, and an
overhanging top slab, each a single stone with eased edges) styled with a wide ceramic
bowl of sedge and a pair of cloth-bound books (covers, spine, page block; throwable pickups)
on a rimmed teak tray.

Origin: floor centre. Long axis along X. Units are metres."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import courtyard_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common
rbox = cc.rbox

NAME = "CourtyardCoffeeTable"

P = dict(
    name=NAME,
    size=(1.30, 0.78),
    height=0.36,
    top_t=0.06,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    stone, teak, cer = cc.limestone_mat(), cc.teak_mat(), cc.ceramic_mat()
    sand, clay, sage = cc.sand_fabric(), cc.clay_fabric(), cc.sage_fabric()
    leaf = cc.foliage_mat()

    import random
    import courtyard_pool as pool
    importlib.reload(pool)
    rng = random.Random(5)
    w, d = p["size"]
    h, t = p["height"], p["top_t"]
    # plinth: a recessed foot (shadow gap), the block, and an overhanging top slab;
    # each is one stone (no paving joints), with eased edges
    pool.stone(f"{n}_Foot", (w - 0.30, d - 0.20, 0.07), (0, 0, 0.035), stone, col, root, rng, bevel=0.004,
               skip=("-z", "+z"))
    pool.stone(f"{n}_Plinth", (w - 0.18, d - 0.12, h - t - 0.07), (0, 0, 0.07 + (h - t - 0.07) / 2), stone, col, root,
               rng, bevel=0.006, skip=("+z",))
    pool.stone(f"{n}_Top", (w, d, t), (0, 0, h - t / 2), stone, col, root, rng, bevel=0.012, seg=2, skip=())

    # teak tray (base and four rails) with two books: covers over an inset page block
    tz = h
    tw, td, tb = 0.46, 0.30, 0.012
    tx, ty = 0.30, 0.04
    rbox(f"{n}_Tray", (tw, td, tb), (tx, ty, tz + tb / 2), teak, col, root, bevel=0.002, seg=1)
    for k, (sx, sy, lx, ly) in enumerate(((0, -1, tw, 0.014), (0, 1, tw, 0.014), (-1, 0, 0.014, td - 0.028),
                                          (1, 0, 0.014, td - 0.028))):
        rbox(f"{n}_TrayRim{k}", (lx, ly, 0.03), (tx + sx * (tw / 2 - 0.007), ty + sy * (td / 2 - 0.007), tz + 0.015),
             teak, col, root, bevel=0.003, seg=1)

    def book(name, size, loc, rz, cover):
        bw_, bd_, bh_ = size
        ct = 0.003
        parts = []
        for k, z in enumerate((-bh_ / 2 + ct / 2, bh_ / 2 - ct / 2)):
            parts.append(rbox(f"{name}_Cover{k}", (bw_, bd_, ct), (0, 0, z), cover, col, root, bevel=0.001, seg=1,
                              uv_tile=0.25))
        parts.append(rbox(f"{name}_Spine", (ct, bd_, bh_), (-bw_ / 2 + ct / 2, 0, 0), cover, col, root, bevel=0.001,
                          seg=1, uv_tile=0.25))
        parts.append(rbox(f"{name}_Pages", (bw_ - 0.008, bd_ - 0.008, bh_ - 2 * ct), (0.002, 0, 0), cer, col, root,
                          bevel=0, uv_tile=0))
        from mathutils import Matrix, Vector
        m = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(rz, 4, "Z")
        for ob in parts:
            ob.matrix_world = m @ Matrix.Translation(ob.location)
        return parts

    # each book is a throwable pickup (lib/pickups.py); the tray and the bowl of sedge stay
    from lib import pickups
    importlib.reload(pickups)
    for nm, size, loc, rz, cover in (("BookA", (0.28, 0.21, 0.035), (tx, ty, tz + tb + 0.0175), -3, sand),
                                     ("BookB", (0.24, 0.18, 0.028), (tx + 0.01, ty + 0.005, tz + tb + 0.035 + 0.014),
                                      11, clay)):
        obs = book(f"{n}_{nm}", size, loc, math.radians(rz), cover)
        pickups.adopt(f"{n}_{nm}_Pickup", col, root, "book", obs, (loc[0], loc[1], loc[2] - size[2] / 2),
                      math.radians(rz))
    # wide ceramic bowl
    prof = [(0.0, 0.0), (0.07, 0.0), (0.075, 0.006), (0.12, 0.04), (0.16, 0.085), (0.165, 0.095), (0.158, 0.098),
            (0.15, 0.094), (0.115, 0.05), (0.0, 0.02)]
    bowl = cc.lathe([(r, z) for r, z in prof], 28, f"{n}_Bowl", col, cer, root, sharp=45)
    bowl.location = (-0.30, -0.05, tz)
    # sedge tuft in the bowl
    cb = bmesh.new()
    uvl = cb.loops.layers.uv.new("UVMap")
    for j in range(6):
        ang = j * math.pi / 6 + 0.3
        right = Vector((math.cos(ang), math.sin(ang), 0)) * 0.17
        cc.add_card(cb, uvl, Vector((-0.30, -0.05, tz + 0.03 + 0.15)), right, Vector((0, 0, 0.15)), "grassB")
    common.mesh_object(f"{n}_Sedge", cb, col, leaf, root, smooth=False)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
