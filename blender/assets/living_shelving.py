"""Open smoked-oak shelving wall unit for the den: five bays, black felt back, bronze
edge lines, shelves of muted book spines (merged per colour, cheap) and a few objects.
Faces -Y (front), back at +Y; origin is the floor centre of the footprint.
"""
import importlib
import math
import os
import sys

import bmesh
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "LivingShelving"

P = dict(name=NAME, width=3.4, depth=0.36, height=2.7, bays=4, shelf_t=0.03, side_t=0.04, plinth=0.08,
         shelf_zs=(0.40, 0.88, 1.36, 1.84, 2.32), seed=3)

# small ceramic pieces (r, z) profiles: a low bowl, a tall bottle vase, a round pot
VESSELS = [
    [(0.03, 0.0), (0.075, 0.02), (0.09, 0.055), (0.082, 0.058), (0.065, 0.03), (0.0, 0.028)],
    [(0.04, 0.0), (0.055, 0.06), (0.05, 0.16), (0.022, 0.21), (0.016, 0.26), (0.02, 0.27), (0.012, 0.27), (0.0, 0.25)],
    [(0.045, 0.0), (0.07, 0.035), (0.072, 0.075), (0.05, 0.11), (0.035, 0.115), (0.03, 0.11), (0.0, 0.10)],
]

BOOKS = [("M_Book_Cream", (0.42, 0.38, 0.30)), ("M_Book_Ink", (0.025, 0.04, 0.07)), ("M_Book_Moss", (0.04, 0.07, 0.05)),
         ("M_Book_Rust", (0.20, 0.07, 0.035)), ("M_Book_Charcoal", (0.03, 0.03, 0.032)), ("M_Book_Sand", (0.30, 0.24, 0.16))]


def add_box(bm, size, centre, skip_back=False):
    """Append a box; never its underside (it stands on a shelf), nor its back when it
    stands against the felt back panel."""
    b = common.box_bmesh(size)
    vm = {v: bm.verts.new(v.co + Vector(centre)) for v in b.verts}
    for f in b.faces:
        if f.normal.z < -0.9 or (skip_back and f.normal.y > 0.9):
            continue
        bm.faces.new([vm[v] for v in f.verts])
    b.free()


def add_lathe(bm, profile, centre, segs=12):
    """Append a small open-bottomed solid of revolution (bowls, vessels)."""
    c = Vector(centre)
    rows = [[bm.verts.new(c + Vector((r * math.cos(2 * math.pi * k / segs), r * math.sin(2 * math.pi * k / segs), z)))
             for k in range(segs)] if r > 1e-6 else [bm.verts.new(c + Vector((0, 0, z)))] * segs for r, z in profile]
    for a, b in zip(rows, rows[1:]):
        for k in range(segs):
            q = (k + 1) % segs
            vs = []
            for v in (a[k], a[q], b[q], b[k]):
                if v not in vs:
                    vs.append(v)
            if len(vs) >= 3:
                f = bm.faces.new(vs)
                f.smooth = True


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rng = np.random.default_rng(p["seed"])
    oak = materials.smoked_oak()
    felt = common.pbr_material("M_Felt_Black", (0.012, 0.012, 0.013), roughness=1.0)
    bronze = materials.bronze()
    book_mats = [common.pbr_material(nm, c, roughness=0.75) for nm, c in BOOKS]

    W, D, H = p["width"], p["depth"], p["height"]
    st, sdt = p["shelf_t"], p["side_t"]
    yb = D / 2
    bays = p["bays"]

    def box(name, mat, size, loc, bevel=0.003, uv=0.5):
        ob = common.mesh_object(f"{n}_{name}", common.box_bmesh(size), col, mat, root, smooth=False)
        ob.location = loc
        if bevel:
            common.add_bevel(ob, bevel, segments=2)
        common.box_uv(ob, uv)
        return ob

    pl = p["plinth"]
    box("Back", felt, (W, 0.012, H - pl), (0, yb - 0.006, pl + (H - pl) / 2), 0.0, uv=1.0)
    box("Plinth", felt, (W - 0.1, D - 0.1, pl), (0, 0, pl / 2), 0.0, uv=1.0)
    for i in range(bays + 1):
        x = -W / 2 + sdt / 2 + (W - sdt) * i / bays
        box(f"Upright{i}", oak, (sdt, D, H - pl), (x, 0, pl + (H - pl) / 2), 0.004)
    inner_w = (W - sdt) / bays - sdt
    zs = [pl + 0.0] + list(p["shelf_zs"]) + [H - st / 2]
    shelf_levels = list(p["shelf_zs"])
    for k, z in enumerate(shelf_levels + [H - st / 2]):
        box(f"Shelf{k}", oak, (W, D, st), (0, 0, z if k < len(shelf_levels) else H - st / 2), 0.004)
    box("Base", oak, (W, D, st), (0, 0, pl + st / 2), 0.004)
    # bronze line on the front edge of the top
    box("TopLine", bronze, (W, 0.006, 0.01), (0, -D / 2 - 0.002, H - 0.02), 0.001)

    # books: per shelf and bay, fill part of the width with upright books, sometimes a leaning stack
    bms = [bmesh.new() for _ in book_mats]
    objs = bmesh.new()
    levels = [pl + st] + [z + st / 2 for z in shelf_levels]
    tops = shelf_levels + [H - st]
    for lvl, top in zip(levels, tops):
        gap = top - lvl - st / 2 if lvl != pl + st else top - lvl - st / 2
        for b_i in range(bays):
            x0 = -W / 2 + sdt + (inner_w + sdt) * b_i + 0.01
            x1 = x0 + inner_w - 0.02
            mode = rng.choice(["books", "books", "stack", "object"])
            if mode == "books":
                fill = rng.uniform(0.55, 0.95)
                x = x0 if rng.random() < 0.6 else x1 - inner_w * fill
                end = x + inner_w * fill
                while x < end - 0.03:
                    t = rng.uniform(0.022, 0.05)
                    h = min(rng.uniform(0.20, 0.36), gap - 0.03)
                    d = rng.uniform(0.20, 0.27)
                    add_box(bms[int(rng.integers(len(bms)))], (t, d, h), (x + t / 2, yb - 0.012 - d / 2, lvl + h / 2),
                            skip_back=True)
                    x += t + 0.002
                if end < x1 - 0.16 and rng.random() < 0.3:  # a small vessel in the space left over
                    vx = min(x1 - 0.08, end + 0.09)
                    add_lathe(objs, VESSELS[int(rng.integers(len(VESSELS)))], (vx, yb - 0.17, lvl))
            elif mode == "stack":
                x = rng.uniform(x0 + 0.05, x1 - 0.35)
                z = lvl
                for _ in range(int(rng.integers(3, 6))):
                    t = rng.uniform(0.025, 0.045)
                    w = rng.uniform(0.22, 0.30)
                    add_box(bms[int(rng.integers(len(bms)))], (w, 0.22, t), (x + w / 2 + rng.uniform(-0.01, 0.01), yb - 0.13, z + t / 2))
                    z += t
                if rng.random() < 0.35:   # a bowl on top of the stack
                    add_lathe(objs, VESSELS[0], (x + 0.14, yb - 0.13, z))
            elif mode == "object":
                # one or two ceramic vessels, varied, off-centre; sometimes beside a short stack
                picks = rng.permutation(len(VESSELS))[:int(rng.integers(1, 3))]
                for q, vi in enumerate(picks):
                    add_lathe(objs, VESSELS[int(vi)], (x0 + inner_w * (0.3 + 0.32 * q + rng.uniform(-0.06, 0.06)),
                                                       yb - rng.uniform(0.13, 0.19), lvl))
                if len(picks) == 1:
                    z = lvl
                    for _ in range(int(rng.integers(2, 4))):
                        t = rng.uniform(0.025, 0.04)
                        w = rng.uniform(0.2, 0.26)
                        add_box(bms[int(rng.integers(len(bms)))], (w, 0.21, t), (x1 - w / 2 - 0.03, yb - 0.13, z + t / 2))
                        z += t
    for k, bm in enumerate(bms):
        ob = common.mesh_object(f"{n}_Books{k}", bm, col, book_mats[k], root, smooth=False)
        common.box_uv(ob, 0.5)
    ceramic = common.pbr_material("M_Ceramic_Glaze", (0.55, 0.52, 0.46), roughness=0.18)
    bmesh.ops.recalc_face_normals(objs, faces=objs.faces[:])
    ob = common.mesh_object(f"{n}_Objects", objs, col, ceramic, root, smooth=True)
    common.box_uv(ob, 0.5)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
