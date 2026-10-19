"""Counter stool for the kitchen island: cognac leather seat and low curved back
on four splayed blackened-steel legs with a bronze foot ring. Seat height 0.66 m.
Faces -Y (the back is on +Y). Origin is the floor centre."""
import importlib
import math
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitchen_lib as L  # noqa: E402

importlib.reload(L)
common, materials = L.common, L.materials

NAME = "KitchenStool"

P = dict(
    name=NAME,
    seat_h=0.66,
    seat_r=0.205,
    seat_t=0.075,
    leg_r=0.0115,
    foot_z=0.27,
    back_arc=(52, 128),      # degrees round the seat, 90 = directly behind
    back_z=(0.78, 1.00),
)


def arc_panel(r_in, r_out, a0, a1, z0, z1, segs=14, round_r=0.008):
    """Curved cushion: a ring sector prism with slightly raised mid-height."""
    bm = bmesh.new()
    rows = []
    zs = [z0, z0 + (z1 - z0) * 0.5, z1]
    for z in zs:
        bulge = 1.0 if z == zs[1] else 0.0
        ring = []
        for rad in (r_in - 0.0, r_out + 0.008 * bulge):
            for k in range(segs + 1):
                a = math.radians(a0 + (a1 - a0) * k / segs)
                ring.append(bm.verts.new((rad * math.cos(a), rad * math.sin(a), z)))
        rows.append(ring)
    n = segs + 1

    def quad(a, b, c, d):
        bm.faces.new((a, b, c, d))

    for row in range(2):
        lo, hi = rows[row], rows[row + 1]
        for k in range(segs):
            quad(lo[k], lo[k + 1], hi[k + 1], hi[k])                       # inner face
            quad(lo[n + k + 1], lo[n + k], hi[n + k], hi[n + k + 1])       # outer face
        quad(lo[0], hi[0], hi[n], lo[n])                                    # ends
        quad(lo[segs + 1 + segs], hi[segs + 1 + segs], hi[segs], lo[segs])
    for k in range(segs):
        quad(rows[0][k + 1], rows[0][k], rows[0][n + k], rows[0][n + k + 1])   # bottom
        quad(rows[2][k], rows[2][k + 1], rows[2][n + k + 1], rows[2][n + k])   # top
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def build(**overrides):
    p = {**P, **overrides}
    b = L.Builder(p["name"])
    leather = L.leather_tan()
    bronze = materials.bronze()
    dark = materials.black_metal()

    sh, sr, st = p["seat_h"], p["seat_r"], p["seat_t"]
    # seat cushion: rounded disc
    # seat cushion: a soft drum with a piped welt round the top shoulder (the profile's
    # bead), its underside on the steel plate (not modelled where covered)
    prof = [(sr - 0.032, sh - st), (sr - 0.016, sh - st + 0.002), (sr - 0.004, sh - st + 0.012), (sr, sh - st + 0.028),
            (sr, sh - 0.032), (sr - 0.0035, sh - 0.019), (sr + 0.0015, sh - 0.0145), (sr - 0.0035, sh - 0.0095),
            (sr - 0.018, sh - 0.002), (sr - 0.06, sh + 0.003), (sr * 0.45, sh + 0.0055), (0.0, sh + 0.006)]
    seat = b.lathe("Seat", prof, leather, segs=28, sharp=60, uv_tile=0.2, closed=False)
    # seat plate under the cushion
    b.lathe("Plate", [(0, sh - st - 0.012), (sr - 0.03, sh - st - 0.012), (sr - 0.03, sh - st), (0, sh - st)], dark,
            segs=24, uv_tile=0)

    # four splayed legs from under the seat to the floor
    a_leg = sr - 0.06
    for i, ang in enumerate((45, 135, 225, 315)):
        c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        top = (a_leg * c, a_leg * s, sh - st - 0.006)
        bot = (a_leg * 1.38 * c, a_leg * 1.38 * s, 0.001)
        b.tube(f"Leg{i}", [bot, top], p["leg_r"], dark, closed=False, res=3)
    # bronze foot ring through the legs
    fz = p["foot_z"]
    t = 1 - (fz - 0.001) / (sh - st - 0.012)
    rr = a_leg * (1.38 - 0.38 * (1 - t) * 0 - 0.38 * (fz - 0.001) / (sh - st - 0.012))
    ring = [(rr * math.cos(2 * math.pi * k / 28), rr * math.sin(2 * math.pi * k / 28), fz) for k in range(28)]
    b.tube("FootRing", ring, 0.0085, bronze, closed=True, res=2)

    # low curved back on two posts
    a0, a1 = p["back_arc"]
    z0, z1 = p["back_z"]
    back = common.mesh_object(f"{b.n}_Back", arc_panel(sr - 0.065, sr - 0.012, a0, a1, z0, z1), b.col, leather, b.root)
    common.add_subsurf(back, 1, 1)
    L.planar_uv(back, 0.2)
    for i, ang in enumerate((a0 + 9, a1 - 9)):
        c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        rad = sr - 0.04
        b.tube(f"Post{i}", [(rad * c, rad * s, sh - st), (rad * c, rad * s, z0 + 0.03)], 0.0085, dark,
               closed=False, res=3)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
