"""Library reading armchair: a deep, low club chair in navy wool. A walnut plinth on
slim bronze-capped tapered legs carries the upholstered body: a tight outside back,
track arms with a welted outer panel, loose back cushions that lean into the back and
a firm welted seat cushion. The sofas are the same generator with `seats` = 3.
Origin: floor centre; faces -Y. About 0.89 x 0.91 x 0.94 m."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import library_kit as kit  # noqa: E402
from library_kit import Mesh, common, materials  # noqa: E402

importlib.reload(kit)

NAME = "LibraryArmchair"

P = dict(
    name=NAME,
    fabric="navy",           # "navy" | "oat" | "cognac" | "green"
    width=0.88,
    depth=0.9,
    leg_h=0.13,
    seat_h=0.44,             # top of the seat cushion
    arm_h=0.62,
    arm_w=0.17,
    back_h=0.93,
    cuts=3,
    seats=1,                 # seat / back cushions across (a sofa has 2-3)
)

PLINTH_T = 0.04              # walnut plinth between the legs and the upholstery
WELT_R = 0.005


def grain_uv(ob):
    """The walnut map's grain runs along v; kit.Mesh puts u along a part's length."""
    for d in ob.data.uv_layers["UVMap"].data:
        pass  # the walnut scan is rotated so its grain runs along u (polyhaven_textures ROTATE): no swap


def cushion_bm(size, cuts=(3, 3, 3), edge=0.03, crown=None, drop=(), taper=0.0, channels=None):
    """Like common.cushion_bmesh but with per-axis cuts (flat faces need fewer) and
    faces nobody sees removed (`drop`, e.g. ("-z",)). taper pulls the front (-y)
    face back toward the top, so a back cushion reads as a pillow, not a slab."""
    crown = crown or {}
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    for a, c in enumerate(cuts):
        no = [0, 0, 0]
        no[a] = 1
        for k in range(1, c + 1):
            t = -1 + 2 * k / (c + 1)
            co = [0, 0, 0]
            co[a] = t
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no)
    half = [s / 2 for s in size]
    segs = [c + 1 for c in cuts]
    for v in bm.verts:
        t = [max(-1.0, min(1.0, c)) for c in v.co]
        p = [common._remap(t[a], half[a], min(edge, half[a] * 0.45), segs[a]) for a in range(3)]
        u = [p[a] / half[a] for a in range(3)]
        for a, axis in enumerate("xyz"):
            o1, o2 = [b for b in range(3) if b != a]
            amp = crown.get(("+" if u[a] >= 0 else "-") + axis, 0.0)
            p[a] += amp * u[a] * (1 - u[o1] ** 2) * (1 - u[o2] ** 2)
        if taper and u[1] < 0:
            p[1] += taper * (u[2] + 1) / 2 * (-u[1])
        if channels:
            face, ax, depth, rows = channels
            fa, ca = "xyz".index(face[1]), "xyz".index(ax)
            sign = 1 if face[0] == "+" else -1
            other = 3 - fa - ca
            ic = round((t[ca] + 1) / 2 * segs[ca])
            io = round((t[other] + 1) / 2 * segs[other])
            if abs(t[fa] - sign) < 1e-6 and ic in rows and 1 <= io <= segs[other] - 1:
                k = 0.5 if io in (1, segs[other] - 1) else 1.0
                p[fa] -= sign * depth * k
        v.co = Vector(p)
    bm.normal_update()
    kill = []
    for f in bm.faces:
        for key in drop:
            a = "xyz".index(key[1])
            if f.normal[a] * (1 if key[0] == "+" else -1) > 0.95:
                kill.append(f)
                break
    if kill:
        bmesh.ops.delete(bm, geom=kill, context="FACES")
    return bm


def welt_points(size, face, edge, corner=None, segments=3):
    """Rounded-rectangle loop on the edge of `face` ('+z', '-y', ...) of a cushion
    whose subdivided corners are pulled in by edge / 8: the welt sits on the corner."""
    a = "xyz".index(face[1])
    sign = 1 if face[0] == "+" else -1
    o1, o2 = [b for b in range(3) if b != a]
    ins = edge / 8                 # one subsurf level pulls a corner in by edge / 8
    h = [s / 2 - ins for s in size]
    rect = []
    for c1, c2 in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        q = [0.0, 0.0, 0.0]
        q[a] = sign * h[a]
        q[o1] = c1 * h[o1]
        q[o2] = c2 * h[o2]
        rect.append(q)
    return common.fillet_polyline(rect, corner or edge * 0.9, segments=segments, closed=True)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    walnut, bronze = materials.walnut(), materials.bronze()
    fab = {"navy": kit.linen_navy, "oat": kit.linen_oat, "cognac": kit.leather_cognac,
           "green": kit.leather_green}[p["fabric"]]()
    W, D, lh = p["width"], p["depth"], p["leg_h"]
    aw = p["arm_w"]
    tile = 0.2 if p["fabric"] in ("cognac", "green") else 0.25
    c = p["cuts"]
    ns = p["seats"]
    z0 = lh + PLINTH_T                       # underside of the upholstery
    upholstery = []

    def piece(name, size, centre, cuts, edge, crown=None, drop=(), tilt=0.0, taper=0.0, welts=()):
        rot = Matrix.Rotation(tilt, 4, "X")
        ob = common.mesh_object(name, cushion_bm(size, cuts, edge, crown, drop, taper), col, fab, root)
        ob.location = centre
        ob.rotation_euler = (tilt, 0, 0)
        common.add_subsurf(ob, levels=1, render_levels=1)
        common.box_uv(ob, tile=tile)
        upholstery.append(ob)
        for i, face in enumerate(welts):
            pts = welt_points(size, face, edge)
            if taper and face == "-y":
                pts = [Vector((q.x, q.y + taper * (q.z / (size[2] / 2) + 1) / 2, q.z)) for q in pts]
            w = common.tube_object(f"{name}_Welt{i}", pts, WELT_R, col, fab, root, closed=True, profile_res=1)
            w.location = centre
            w.rotation_euler = (tilt, 0, 0)
            common.box_uv(w, tile=tile)
            upholstery.append(w)
        return ob

    # ------------------------------------------------------------ body
    yf_arm, yb_arm = -D / 2 + 0.006, D / 2 - 0.002
    ya = (yf_arm + yb_arm) / 2
    inner = W - 2 * aw
    # track arms: welt round the outer panel; a soft crown on top
    for sx in (-1, 1):
        piece(f"{n}_Arm_{'L' if sx < 0 else 'R'}", (aw, yb_arm - yf_arm, p["arm_h"] - z0),
              (sx * (W - aw) / 2, ya, z0 + (p["arm_h"] - z0) / 2), (2, 3, 3), 0.035,
              {"+z": 0.022, "+x" if sx > 0 else "-x": 0.008, "-y": 0.01}, ("-z",),
              welts=("+x" if sx > 0 else "-x",))
    # outside back: a tight panel between the arms, lower than the loose cushions
    bf = 0.13
    yb_back = D / 2 + 0.004
    back_top = p["back_h"] - 0.13
    piece(f"{n}_OutsideBack", (inner + 0.03, bf, back_top - z0), (0, yb_back - bf / 2, z0 + (back_top - z0) / 2),
          (max(2, 2 * ns - 1), 2, 2), 0.035, {"+z": 0.012, "+y": 0.006}, ("-z", "-y"), welts=("+y",))
    # deck: the platform under the seat cushions, its front band shows below them
    base_top = 0.30
    deck_front = yf_arm + 0.022
    deck_d = (yb_back - bf) - deck_front + 0.02
    piece(f"{n}_Deck", (inner + 0.03, deck_d, base_top - z0), (0, deck_front + deck_d / 2, z0 + (base_top - z0) / 2),
          (max(2, 2 * ns - 1), 2, 2), 0.025, {"-y": 0.008}, ("-z", "+z"))

    # loose back cushions, raked, leaning on the outside back
    tilt = math.radians(-9)
    ct, st_ = math.cos(-tilt), math.sin(-tilt)
    bd = 0.18
    zc_lo = 0.27
    hb = (p["back_h"] + 0.005 - zc_lo - bd / 2 * st_) / ct           # top-rear corner at back_h
    zc = zc_lo + hb / 2 * ct
    y_lean = yb_back - bf + 0.012                                      # where the top-rear corner rests
    yc = y_lean - bd / 2 * ct - hb / 2 * st_
    seat_rear = yc - bd / 2 * ct - (hb / 2) * st_ * 0.15 + 0.03       # seat tucks under the cushion
    gap = 0.008
    cw = (inner - 0.008 - (ns - 1) * gap) / ns
    seat_front = yf_arm + 0.01
    sd_ = seat_rear - seat_front
    for i in range(ns):
        xc = -inner / 2 + 0.004 + cw / 2 + i * (cw + gap)
        tag = "" if ns == 1 else f"_{i}"
        piece(f"{n}_Back{tag}", (cw + 0.004, bd, hb), (xc, yc, zc), (3, 2, 3), 0.045,
              {"-y": 0.03, "+z": 0.016, "+x": 0.006, "-x": 0.006}, ("+y",), tilt=tilt, taper=0.035,
              welts=("-y",))
        piece(f"{n}_Seat{tag}", (cw, sd_, p["seat_h"] - base_top), (xc, seat_front + sd_ / 2, base_top + (p["seat_h"] - base_top) / 2),
              (3, 3, 2), 0.03, {"+z": 0.026, "-y": 0.012, "+x": 0.006, "-x": 0.006}, ("-z",),
              welts=("+z", "-z"))

    kit.merge_objects(upholstery, f"{n}_Upholstery", col, root)

    # ------------------------------------------- walnut plinth, tapered legs, bronze shoes
    wood, brz = Mesh(0.5), Mesh(0.5)
    wood.box((0, 0.0, lh + PLINTH_T / 2), (W - 0.024, D - 0.064, PLINTH_T), shift=(0.4, 0.1))
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (W / 2 - 0.08), sy * (D / 2 - 0.1)
            wood.box((x, y, lh / 2 + 0.01), (0.04, 0.04, lh - 0.02), taper=(1.35, 1.35), shift=(sx * 0.3, sy * 0.2))
            brz.box((x, y, 0.0085), (0.038, 0.038, 0.017), taper=(1.04, 1.04))
    w = wood.to_object(f"{n}_Legs", col, walnut, root)
    grain_uv(w)
    common.add_bevel(w, 0.003, segments=1)
    b = brz.to_object(f"{n}_Caps", col, bronze, root)
    common.add_bevel(b, 0.0015, segments=1)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
