"""Kettlebell stand: a low pale-oak stand on a black plinth holding a graduated set
of six cast-iron kettlebells (8-24 kg) on two tiers. 1.3 m wide, 0.40 deep, 0.92
high; faces -Y. Origin is the floor centre."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestKettlebells"

P = dict(name=NAME, width=1.3, depth=0.40)


def kettlebell(bm_body, bm_handle, x, y, z, r):
    """Cast ball (flattened bottom) + a squared handle loop, centred at (x, y, z = floor of the bell)."""
    bmesh.ops.create_uvsphere(bm_body, u_segments=20, v_segments=12, radius=r,
                              matrix=Matrix.Translation((x, y, z + r * 0.96)) @ Matrix.Diagonal((1, 1, 0.96, 1)))
    return None


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    oak, black, iron = guest_mats.oak(), guest_mats.black(), guest_mats.graphite()
    own = (col, root, n)
    A = guest_mats.add
    W, D = p["width"], p["depth"]
    plinth, post_h = 0.06, 0.92
    A(own, "Plinth", common.box_bmesh((W - 0.08, D - 0.06, plinth)), black, (0, 0, plinth / 2), 0)
    for sx in (-1, 1):
        A(own, f"End{sx}", common.box_bmesh((0.03, D, post_h - plinth)), oak, (sx * (W / 2 - 0.015), 0, plinth + (post_h - plinth) / 2), 0.003)
    A(own, "Back", common.box_bmesh((W - 0.06, 0.02, post_h - plinth)), oak, (0, D / 2 - 0.01, plinth + (post_h - plinth) / 2), 0.003)
    shelf_t = 0.03
    shelf_z = (plinth + shelf_t, 0.56, post_h)
    for k, z in enumerate(shelf_z):
        A(own, f"Shelf{k}", common.box_bmesh((W - 0.06, D - 0.02, shelf_t)), oak, (0, -0.005, z - shelf_t / 2), 0.003)
    body = bmesh.new()
    bells = []   # (x, shelf z, radius)
    for k, x in enumerate((-0.42, 0.0, 0.42)):
        bells.append((x, shelf_z[0], 0.125 - 0.0 * k + 0.006 * k))
        bells.append((x, shelf_z[1], 0.085 + 0.008 * k))
    for x, zz, rr in bells:
        # cast ball with the flat base a real bell stands on (cut 0.1 r below the equator... at 0.9 r)
        ret = bmesh.ops.create_uvsphere(body, u_segments=16, v_segments=10, radius=rr,
                                        matrix=Matrix.Translation((x, -0.01, zz + rr * 0.9)))
        for v in ret["verts"]:
            v.co.z = max(v.co.z, zz)
    A(own, "Bells", body, iron, (0, 0, 0), 0)
    for i, (x, zz, rr) in enumerate(bells):
        top = zz + rr * 1.9
        hr = 0.011 + 0.05 * rr          # handle thickness grows with the bell (16 mm .. 17 mm radius)
        # the horns rise out of the shoulders, flare out, and the grip runs across the top
        pts = [(x - rr * 0.42, -0.01, zz + rr * 1.45), (x - rr * 0.62, -0.01, top + rr * 0.30),
               (x - rr * 0.45, -0.01, top + rr * 0.58), (x + rr * 0.45, -0.01, top + rr * 0.58),
               (x + rr * 0.62, -0.01, top + rr * 0.30), (x + rr * 0.42, -0.01, zz + rr * 1.45)]
        pts = common.fillet_polyline(pts, rr * 0.22, segments=3, closed=False)
        t = common.tube_object(f"{n}_Handle{i}", pts, hr, col, iron, root, closed=False, profile_res=1)
        common.box_uv(t, 0.5)
    parts = guest_mats.consolidate(root, max_dim=0.35)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
