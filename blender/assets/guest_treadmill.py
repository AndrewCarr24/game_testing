"""Treadmill: a low graphite deck with a black running belt between rubber-topped step
rails and a rounded rear roller cover; a sloping motor cowl at the front; two raked
oval uprights carrying a slim tablet console (dark screen facing the runner) wrapped
by a bent handlebar, with short rubber-gripped side rails. The runner faces -Y
(console end at -Y); origin is the floor centre. Runs for 1.95 m, 0.80 m wide,
1.37 m tall."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestTreadmill"

P = dict(name=NAME, width=0.86, length=1.95, deck_z=0.12, deck_t=0.08)


def prism_x(profile, x0, x1):
    """Closed (y, z) profile extruded along x from x0 to x1."""
    bm = bmesh.new()
    a = [bm.verts.new((x0, y, z)) for y, z in profile]
    b = [bm.verts.new((x1, y, z)) for y, z in profile]
    m = len(profile)
    for k in range(m):
        bm.faces.new((a[k], a[(k + 1) % m], b[(k + 1) % m], b[k]))
    bm.faces.new(a)
    bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def bar_between(a, b, w, d):
    """Rectangular bar (w along x, d across) from a to b, both in a plane x = const."""
    a, b = Vector(a), Vector(b)
    L = (b - a).length
    bm = common.box_bmesh((w, d, L))
    ang = math.atan2(-(b - a).y, (b - a).z)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(ang, 3, "X"))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(a + b) / 2)
    return bm


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    gr, rub = guest_mats.graphite(), guest_mats.rubber()
    own = (col, root, n)
    A = guest_mats.add
    W, L = p["width"] - 0.06, p["length"] - 0.01
    y0, y1 = -L / 2, L / 2
    hood_len = 0.50
    hy = y0 + hood_len                    # where the cowl meets the belt
    rail_top = p["deck_z"] + p["deck_t"] + 0.005      # top of the step rails (the belt just below)
    belt_w = W - 0.26

    # ---- rubber feet under the deck corners
    for sx in (-1, 1):
        for tag, y in (("F", hy + 0.12), ("B", y1 - 0.14)):
            A(own, f"Foot_{tag}{sx}", common.box_bmesh((0.07, 0.12, 0.05)), rub, (sx * (W / 2 - 0.09), y, 0.025), 0.004)

    # ---- deck, belt, step rails
    A(own, "Deck", common.box_bmesh((W - 0.12, y1 - hy - 0.03, 0.10)), gr, (0, (hy + y1 - 0.03) / 2, 0.05 + 0.10 / 2),
      0.012)
    A(own, "Belt", common.box_bmesh((belt_w, y1 - hy - 0.06, 0.012)), rub, (0, (hy + y1 - 0.06) / 2, rail_top - 0.012),
      0.003)
    for sx in (-1, 1):
        x = sx * (W / 2 - 0.065)
        A(own, f"Rail{sx}", common.box_bmesh((0.11, y1 - hy - 0.04, 0.05)), gr, (x, (hy + y1 - 0.04) / 2, rail_top - 0.025),
          0.012)
        A(own, f"Tread{sx}", common.box_bmesh((0.075, y1 - hy - 0.16, 0.005)), rub,
          (x + sx * 0.004, (hy + y1 - 0.04) / 2, rail_top + 0.0015), 0.0015)
    # rear roller cover: a rounded nose over the belt's end
    rc = A(own, "RollerRear", guest_mats.cyl_bmesh(0.055, W - 0.02, seg=18, axis="x"), gr, (0, y1 - 0.06, 0.15), 0)
    common.add_bevel(rc, 0.006, segments=2)
    A(own, "RollerBelt", guest_mats.cyl_bmesh(0.035, belt_w, seg=14, axis="x"), rub, (0, y1 - 0.075, rail_top - 0.035), 0)

    # ---- motor cowl: a sloping wedge across the front, every edge well rounded
    prof = [(y0, 0.035), (y0 + 0.015, 0.27), (y0 + 0.10, 0.31), (hy + 0.02, 0.225), (hy + 0.02, 0.035)]
    hood = common.mesh_object(f"{n}_Hood", prism_x(prof, -W / 2, W / 2), col, gr, root, smooth=True)
    common.add_bevel(hood, 0.035, segments=4)
    common.box_uv(hood, 0.5)
    # a dark shadow-gap kick plate under the cowl and a slim LED status line on its slope
    A(own, "Kick", common.box_bmesh((W - 0.08, hood_len - 0.04, 0.035)), rub, (0, y0 + hood_len / 2 + 0.02, 0.0175), 0)

    # ---- raked oval uprights from the cowl's flanks to the console
    top_y, top_z = y0 + 0.17, 1.10
    ups = []
    for sx in (-1, 1):
        x = sx * (W / 2 - 0.055)
        up = common.mesh_object(f"{n}_Upright{sx}", bar_between((x, y0 + 0.30, 0.22), (x * 0.94, top_y, top_z), 0.045, 0.075),
                                col, gr, root, smooth=True)
        common.add_bevel(up, 0.016, segments=3)
        common.box_uv(up, 0.5)
        ups.append(up)

    # ---- console: a slim tablet tipped back toward the runner, screen inset on its face
    tilt = math.radians(22)
    c = Vector((0, top_y + 0.01, 1.185))
    cons = common.mesh_object(f"{n}_Console", common.box_bmesh((W - 0.12, 0.045, 0.37)), col, gr, root, smooth=True)
    cons.rotation_euler = (-tilt, 0, 0)
    cons.location = c
    common.add_bevel(cons, 0.014, segments=3)
    common.box_uv(cons, 0.5)
    nrm = Vector((0, math.cos(tilt), math.sin(tilt)))     # screen normal (toward the runner, up)
    scr = common.mesh_object(f"{n}_Screen", common.box_bmesh((W - 0.20, 0.004, 0.29)), col, guest_mats.screen(), root)
    scr.rotation_euler = (-tilt, 0, 0)
    scr.location = c + nrm * 0.0235
    # a tray lip under the screen
    lip = common.mesh_object(f"{n}_ConsoleLip", common.box_bmesh((W - 0.24, 0.05, 0.018)), col, rub, root, smooth=True)
    lip.rotation_euler = (-tilt, 0, 0)
    lip.location = c + nrm * 0.03 - Vector((0, -math.sin(tilt), math.cos(tilt))) * 0.185
    common.add_bevel(lip, 0.005, segments=2)
    common.box_uv(lip, 0.5)

    # ---- handlebar: bent tube wrapping the console's front, then short side rails
    rr = 0.017
    xb = W / 2 - 0.055
    yb = top_y + 0.13
    bar = common.fillet_polyline([(-xb, top_y + 0.05, 1.03), (-xb, yb, 1.02), (xb, yb, 1.02), (xb, top_y + 0.05, 1.03)],
                                 0.07, 6, closed=False)
    t = common.tube_object(f"{n}_Handlebar", bar, rr, col, gr, root, closed=False, profile_res=2)
    common.box_uv(t, 0.5)
    for sx in (-1, 1):
        x = sx * xb
        pts = common.fillet_polyline([(x, top_y + 0.02, 1.04), (x, top_y + 0.12, 1.0), (x, y0 + 0.95, 0.99)], 0.08, 5,
                                     closed=False)
        t = common.tube_object(f"{n}_Handrail{sx}", pts, rr, col, gr, root, closed=False, profile_res=2)
        common.box_uv(t, 0.5)
        sl = common.tube_object(f"{n}_Grip{sx}", [(x, y0 + 0.40, 0.995), (x, y0 + 0.90, 0.99)], 0.022, col, rub, root,
                                closed=False, profile_res=2)
        common.box_uv(sl, 0.5)
    sl = common.tube_object(f"{n}_GripFront", [(-0.18, yb, 1.02), (0.18, yb, 1.02)], 0.022, col, rub, root,
                            closed=False, profile_res=2)
    common.box_uv(sl, 0.5)
    parts = guest_mats.consolidate(root, max_dim=0.35)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
