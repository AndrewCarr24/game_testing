"""Guest armchair: a deep, low sage lounge chair. Tailored upholstered body (arms
with a welted front panel, an outer back) on a slim pale-oak apron and four tapered
oak legs with brass caps; a loose piped seat cushion and a loose piped back cushion
sit between the arms with a soft shadow gap; a linen lumbar cushion leans on the back.
Faces -Y; origin is the floor centre."""
import importlib
import math
import os
import sys

from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bed  # noqa: E402
import guest_mats  # noqa: E402
import guest_wardrobe  # noqa: E402

importlib.reload(guest_mats)
importlib.reload(guest_wardrobe)
importlib.reload(bed)
common = guest_mats.common

NAME = "GuestArmchair"

P = dict(name=NAME, width=0.84, depth=0.88, leg_h=0.16, seat_h=0.42, arm_h=0.62, back_h=0.92)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    oak, brass = guest_mats.oak(), guest_mats.brass()
    sage, linen = guest_mats.sage_light(), guest_mats.linen()
    own = (col, root, n)
    A = guest_mats.add
    W, D, LH, SH, AH, BH = p["width"], p["depth"], p["leg_h"], p["seat_h"], p["arm_h"], p["back_h"]

    def cushion(name, size, centre, mat, cuts=3, edge=0.03, crown=None, tilt=0.0, pivot=None, piping=None):
        """Subdivided cushion at `centre`, optionally tilted about X (top toward +Y for
        tilt > 0) around `pivot`; piping = [(axis, which, radius)] welts round faces."""
        M = Matrix.Translation(centre)
        if tilt:
            pv = Vector(pivot)
            M = Matrix.Translation(pv) @ Matrix.Rotation(-tilt, 4, "X") @ Matrix.Translation(-pv) @ M
        bm = common.cushion_bmesh(size, cuts=cuts, edge=edge, crown=crown)
        bm.transform(M)
        ob = common.mesh_object(f"{n}_{name}", bm, col, mat, root)
        common.add_subsurf(ob)
        common.box_uv(ob, 0.25)
        for axis, which, rad in piping or ():
            loops = common.piping_loop(size, axis, edge / 6, edge * 0.9)
            pts = [M @ Vector(q) for q in loops[which]]
            pipe = common.tube_object(f"{n}_{name}_Piping{axis}{which}", pts, rad, col, mat, root,
                                      closed=True, profile_res=0)
            common.box_uv(pipe, 0.25)
        return ob

    # ---- legs: tapered oak, brass toe caps
    lx, ly = W / 2 - 0.085, D / 2 - 0.095
    for fx, fy, nm in ((-1, -1, "FL"), (1, -1, "FR"), (-1, 1, "BL"), (1, 1, "BR")):
        A(own, f"Leg_{nm}", guest_mats.taper_bmesh(0.046, 0.028, LH - 0.012), oak,
          (fx * lx, fy * ly, 0.012 + (LH - 0.012) / 2), 0.002)
        A(own, f"Cap_{nm}", guest_mats.cyl_bmesh(0.0155, 0.012, r2=0.0165, seg=12), brass,
          (fx * lx, fy * ly, 0.006), 0)

    # ---- pale oak apron the body sits on (eased edges; the legs are screwed under it)
    ap_h = 0.045
    A(own, "Apron", common.box_bmesh((W - 0.05, D - 0.05, ap_h)), oak, (0, 0, LH + ap_h / 2), 0.004)
    z_body = LH + ap_h                                  # underside of the upholstery

    # ---- upholstered deck under the loose seat cushion
    deck_t = 0.10
    A(own, "Deck", common.box_bmesh((W - 0.01, D - 0.02, deck_t)), sage, (0, 0, z_body + deck_t / 2), 0.018,
      tile=0.25)
    z_deck = z_body + deck_t

    # ---- arms: tailored blocks, welt round the front panel
    aw = 0.155
    arm_h = AH - z_body
    for s, sx in (("L", -1), ("R", 1)):
        cushion(f"Arm_{s}", (aw, D - 0.03, arm_h), (sx * (W / 2 - aw / 2), -0.01, z_body + arm_h / 2), sage,
                edge=0.035, crown={"+z": 0.016, "-y": 0.008, "+x": 0.008, "-x": 0.008},
                piping=[("y", 1, 0.0045)])

    # ---- outer back: full width behind the arms, raked back 10 degrees
    rake = math.radians(11)
    obt = 0.13
    ob_h = BH - z_body + 0.006
    yb = D / 2 - obt / 2 - 0.035
    cushion("Back", (W - 0.005, obt, ob_h), (0, yb, z_body + ob_h / 2), sage, edge=0.04,
            crown={"+z": 0.012, "+y": 0.01, "-y": 0.006}, tilt=rake, pivot=(0, yb + obt / 2, z_body))

    # ---- loose back cushion between the arms, leaning on the outer back
    gap = 0.007
    iw = W - 2 * aw - 2 * gap
    bct = 0.12
    bc_h = BH - 0.035 - SH
    y_back_face = yb - obt / 2                         # front face of the outer back (before rake)
    ybc = y_back_face - bct / 2 + 0.005
    cushion("BackCushion", (iw, bct, bc_h), (0, ybc, SH + bc_h / 2 - 0.01), sage, edge=0.035,
            crown={"-y": 0.03, "+z": 0.012, "+x": 0.004, "-x": 0.004},
            tilt=rake + math.radians(3), pivot=(0, yb + obt / 2, z_body), piping=[("y", 1, 0.0042)])

    # ---- loose seat cushion: front just proud of the arms, piped top and bottom
    st = SH - z_deck + 0.002
    y0 = -D / 2 - 0.006
    y1 = y_back_face - 0.03
    cushion("Seat", (iw, y1 - y0, st), (0, (y0 + y1) / 2, z_deck + st / 2 - 0.002), sage, edge=0.03,
            crown={"+z": 0.024, "-y": 0.012, "+x": 0.003, "-x": 0.003},
            piping=[("z", 0, 0.0042), ("z", 1, 0.0042)])

    # ---- linen lumbar cushion, leaning on the back cushion
    bm = bed.pillow_bmesh(0.20, 0.15, 0.058, 0.04, 2.6, slump=0.015, rounding=0.26, step=0.07, dent=0.12, sag=0.15)
    bed.place(bm, math.radians(18), math.radians(5), 0.10, SH + 0.018, max_y=ybc - bct / 2 + 0.025,
              roll=math.radians(-4))
    lum = common.mesh_object(f"{n}_Cushion", bm, col, linen, root)
    common.box_uv(lum, 0.25)

    guest_wardrobe.fix_oak(root)
    parts = guest_mats.consolidate(root, max_dim=0.35)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
