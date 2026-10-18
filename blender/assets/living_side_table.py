"""Drum side table: a marble-topped disc on a bronze pedestal with a stepped foot
(also the base for living_coffee_round). Units are metres; origin is the floor centre.
Also provides `lathe()` and `disc_profile()` for the other living_ assets.
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "LivingSideTable"

P = dict(
    name=NAME,
    segments=48,
    top_r=0.27,
    top_t=0.035,
    height=0.55,
    top="marble",            # "marble" or "oak"
    foot_r=0.19,
    neck_r=0.075,
    skirt=0.0,               # >0: oak/marble drum skirt below the top (radius = top_r - skirt)
)


def lathe(profile, segs, closed=True, sharp=40.0):
    """Revolve `profile` [(r, z), ...] about the Z axis into a bmesh.
    Points with r == 0 collapse to a single vertex on the axis. Profile corners
    turning by more than `sharp` degrees get sharp edges (so a 4-point profile
    still shades as a crisp ring while the surface round it stays smooth)."""
    bm = bmesh.new()
    rows = []
    for r, z in profile:
        if abs(r) < 1e-9:
            rows.append([bm.verts.new((0.0, 0.0, z))] * segs)
        else:
            rows.append([bm.verts.new((r * math.cos(2 * math.pi * s / segs),
                                       r * math.sin(2 * math.pi * s / segs), z))
                         for s in range(segs)])
    n = len(profile)
    for i in range(n if closed else n - 1):
        a, b = rows[i], rows[(i + 1) % n]
        for s in range(segs):
            t = (s + 1) % segs
            quad = []
            for v in (a[s], a[t], b[t], b[s]):
                if v not in quad:
                    quad.append(v)
            if len(quad) >= 3:
                bm.faces.new(quad)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for i, (r, z) in enumerate(profile):
        if abs(r) < 1e-9 or (not closed and i in (0, n - 1)):
            continue
        pr, nx = profile[(i - 1) % n], profile[(i + 1) % n]
        d1, d2 = (r - pr[0], z - pr[1]), (nx[0] - r, nx[1] - z)
        ang = math.degrees(abs(math.atan2(d1[0] * d2[1] - d1[1] * d2[0], d1[0] * d2[0] + d1[1] * d2[1])))
        if ang > sharp:
            for s in range(segs):
                e = bm.edges.get((rows[i][s], rows[i][(s + 1) % segs]))
                if e is not None and e.is_valid:
                    e.smooth = False
    return bm

def disc_profile(r, z0, z1, round_r=0.008):
    """Closed (r, z) profile of a disc with softly chamfered edges."""
    c = min(round_r, (z1 - z0) / 2.5)
    return [(0.0, z0), (r - c, z0), (r, z0 + c), (r, z1 - c), (r - c, z1), (0.0, z1)]


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    bronze = materials.bronze()
    if p["top"] == "marble":
        top_mat = common.pbr_material("M_Marble_White", (0.8, 0.79, 0.77), roughness=0.12, coat=0.0)
        common.set_base_color_map(top_mat, textures.load(textures.marble()))
        uvs = 1.0
    else:
        top_mat = materials.smoked_oak()
        uvs = 0.5
    seg = p["segments"]
    H, tt = p["height"], p["top_t"]
    r = p["top_r"]
    top = common.mesh_object(f"{n}_Top", lathe(disc_profile(r, H - tt, H), seg), col, top_mat, root)
    common.box_uv(top, uvs)
    fr, nr = p["foot_r"], p["neck_r"]
    ped = [(0.0, 0.0), (fr, 0.0), (fr, 0.012), (fr * 0.92, 0.02), (nr * 1.25, 0.05), (nr, 0.10),
           (nr, H - tt - 0.04), (nr * 1.5, H - tt - 0.012), (nr * 1.7, H - tt), (0.0, H - tt)]
    pedestal = common.mesh_object(f"{n}_Pedestal", lathe(ped, p["small_segments"] if "small_segments" in p else 32),
                                  col, bronze, root)
    common.box_uv(pedestal, 0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
