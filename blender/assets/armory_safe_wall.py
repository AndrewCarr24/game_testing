"""The armory's hero: a built-in gun-safe wall, five 1.18 m bays (5.90 x 0.62 x 2.75 m). A graphite
powder-coat carcass (back, top, sides, four 0.05 mullions, a recessed 0.08 plinth) framing five
brushed-stainless doors with a 3 mm shadow gap; turn the wheel on the middle door and the doors
lift one after another, from the centre outward, like the lids of a jewel case, each bay lit
inside by cold LED lines.

Per bay: charcoal felt back and sides, a felt floor at 0.22, a stainless blank plate on the
floor's fascia, LED lines down both inner sides and across the top (`_LED`, static), a felt
shelf at 1.88. Long-gun bays (1, 2, 4, 5): two rows of felt-padded graphite U-rests (butt cradles
on the floor, barrel rests at 0.94-1.00) for three guns standing upright. The middle bay (3): a
two-drawer graphite unit, a drawer-like felt tray at 1.0 and a felt pegboard with stainless
pegs for four pistols.

Interactivity (prompts/interactivity.md), signal "armory_safe":
  <n>_Wheel          empty at the wheel's hub (a child of <n>_Door3, so it rises with it):
                     `switch`, travel 270 degrees about its own axis (glTF z = out of the wall).
  <n>_Door1..5       empties on the hinge line (top front edge of each door, z 2.6): `react`
                     rotate -95 degrees about x = the bottom swings out and up until the door is a
                     canopy over its bay (open, its top is at ~2.82 m: clear of a 3.4 m ceiling);
                     duration 2.0 (middle), 2.35 (its neighbours), 2.7 (the ends); collide, no motor.
`pose=1` builds the doors posed open (previews only; the export must stay closed: the engine
reads each empty's rest rotation at load).

Weapon slots (SLOTS, local metres): long guns standing upright at x = bay centre -0.3 / 0 / +0.3,
y +0.12, z 0.22 (bays 1, 2, 4, 5); pistols on the bay-3 pegboard at x +-0.2, y +0.2, z 1.25 / 1.65.

Origin: floor centre; front -Y; the back is against the wall at y = +0.31."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bunker_kit as bk  # noqa: E402
import library_kit as lk  # noqa: E402

importlib.reload(bk)
importlib.reload(lk)
common = bk.common
Mesh = lk.Mesh

NAME = "ArmorySafeWall"

P = dict(
    name=NAME,
    bays=5,
    pitch=1.18,               # bay rhythm (= the library's bookcases)
    depth=0.62,
    height=2.75,
    plinth=0.08,              # recessed toe-kick height
    plinth_inset=0.06,
    mullion=0.05,             # divider between bays (its front stile is 0.054: an even 3 mm gap)
    gap=0.003,                # shadow gap round each door
    door=(1.12, 2.45, 0.05),
    hinge_z=2.6,
    floor_z=0.22,             # felt bay floor
    shelf_z=1.88,             # felt top shelf (top face)
    wheel_d=0.42,
    wheel_z=1.3,
    wheel_proud=0.08,
    open_angle=-95,           # degrees about x (glTF = Blender): negative lifts the bottom outward (-Y)
    durations=(2.0, 2.35, 2.7),   # by distance from the middle bay
    signal="armory_safe",
    pose=0,                   # 1 = doors posed open (preview only)
)

Y_FRONT, Y_BACK = -0.31, 0.31
BACK_T = 0.02                 # carcass back panel
FELT_T = 0.008
Y_FELT = Y_BACK - BACK_T - FELT_T     # the felt back's face (0.282)
Y_INNER = -0.255              # interior starts just behind the closed doors (door back at -0.26)


def bay_centres(p):
    return [(i - (p["bays"] - 1) / 2) * p["pitch"] for i in range(p["bays"])]


def slots(p=P):
    """Weapon positions in the asset's local frame (Blender axes: x right, y into the wall, z up)."""
    xs = bay_centres(p)
    mid = p["bays"] // 2
    long_guns = [(round(xs[i] + dx, 3), 0.12, p["floor_z"]) for i in range(p["bays"]) if i != mid
                 for dx in (-0.3, 0.0, 0.3)]
    pistols = [(round(xs[mid] + sx * 0.2, 3), 0.2, z) for z in (1.25, 1.65) for sx in (-1, 1)]
    return {"long_guns": long_guns, "pistols": pistols}


SLOTS = slots(P)


# ------------------------------------------------------------------ round things (into a Mesh's bmesh)

def _basis(axis):
    axis = axis.normalized()
    ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    u = axis.cross(ref).normalized()
    return u, axis.cross(u).normalized()


def cyl(m, a, b, r1, r2=None, segs=12, caps=True):
    """A (tapered) cylinder from point a to point b, smooth sides, flat caps."""
    bm = m.bm
    a, b = Vector(a), Vector(b)
    r2 = r1 if r2 is None else r2
    u, v = _basis(b - a)
    rings = []
    for c, r in ((a, r1), (b, r2)):
        rings.append([bm.verts.new(c + r * (math.cos(2 * math.pi * k / segs) * u + math.sin(2 * math.pi * k / segs) * v))
                      for k in range(segs)])
    faces = []
    for k in range(segs):
        j = (k + 1) % segs
        f = bm.faces.new((rings[0][k], rings[0][j], rings[1][j], rings[1][k]))
        f.smooth = True
        faces.append(f)
    if caps:
        for ring in rings:
            f = bm.faces.new(ring)
            f.smooth = False
            faces.append(f)
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    return faces


def lathe_y(m, profile, centre, segs=24):
    """Solid of revolution about the -Y axis through `centre`: profile [(r, d)], d = distance out
    of the wall (toward -Y). Smooth sides; rings where the profile turns sharply stay crisp."""
    bm = m.bm
    cx, cy, cz = centre
    rows = []
    for r, d in profile:
        if r < 1e-7:
            rows.append([bm.verts.new((cx, cy - d, cz))] * segs)
        else:
            rows.append([bm.verts.new((cx + r * math.cos(2 * math.pi * k / segs), cy - d,
                                       cz + r * math.sin(2 * math.pi * k / segs))) for k in range(segs)])
    faces = []
    for i in range(len(rows) - 1):
        (r0, d0), (r1, d1) = profile[i], profile[i + 1]
        flat = abs(d1 - d0) < 1e-6          # a face lying in the wheel's plane (a step): flat shaded
        for k in range(segs):
            j = (k + 1) % segs
            quad = []
            for vv in (rows[i][k], rows[i][j], rows[i + 1][j], rows[i + 1][k]):
                if vv not in quad:
                    quad.append(vv)
            if len(quad) >= 3:
                f = bm.faces.new(quad)
                f.smooth = not flat
                faces.append(f)
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    return faces


def knurled_torus(m, centre, R, r, segs=72, minor=10, knurl=0.0016):
    """A handwheel rim lying in the XZ plane (its axis along y): every other major ring is swollen
    on the outer and front faces, so the grip reads as knurled ridges in the light."""
    bm = m.bm
    cx, cy, cz = centre
    rows = []
    for k in range(segs):
        th = 2 * math.pi * k / segs
        ring = []
        for q in range(minor):
            ph = 2 * math.pi * q / minor
            rr = r
            if k % 2 == 0:
                # swell where the hand grips: the outer edge and the face toward the player
                rr += knurl * max(0.0, math.cos(ph)) + 0.6 * knurl * max(0.0, -math.sin(ph))
            rad = R + rr * math.cos(ph)
            ring.append(bm.verts.new((cx + rad * math.cos(th), cy + rr * math.sin(ph), cz + rad * math.sin(th))))
        rows.append(ring)
    faces = []
    for k in range(segs):
        kk = (k + 1) % segs
        for q in range(minor):
            qq = (q + 1) % minor
            f = bm.faces.new((rows[k][q], rows[kk][q], rows[kk][qq], rows[k][qq]))
            f.smooth = True
            faces.append(f)
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    return faces


def _u_contour(sx, a, rc, yf, yb, segs=4):
    """Inner contour of a U notch opening toward -Y: from the left tip (sx - a, yf) back to the
    bottom line y = yb (its corners rounded with radius rc), across it, and out to the right tip."""
    rc = min(rc, a)
    pts = [(sx - a, yf)]
    for ccx, t0 in ((sx - a + rc, math.pi), (sx + a - rc, 0.5 * math.pi)):
        for k in range(segs + 1):
            t = t0 - 0.5 * math.pi * k / segs
            pts.append((ccx + rc * math.cos(t), yb - rc + rc * math.sin(t)))
    pts.append((sx + a, yf))
    clean = [pts[0]]
    for q in pts[1:]:
        if abs(q[0] - clean[-1][0]) + abs(q[1] - clean[-1][1]) > 1e-6:
            clean.append(q)
    return clean


def extrude_polygon(m, pts, z0, z1, tile=None):
    """A prism: the closed polygon pts [(x, y)] (counter-clockwise from above) from z0 to z1."""
    bm = m.bm
    lo = [bm.verts.new((x, y, z0)) for x, y in pts]
    hi = [bm.verts.new((x, y, z1)) for x, y in pts]
    faces = [bm.faces.new(list(reversed(lo))), bm.faces.new(hi)]
    nn = len(pts)
    for k in range(nn):
        j = (k + 1) % nn
        faces.append(bm.faces.new((lo[k], lo[j], hi[j], hi[k])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    m._set_uv_box(faces, (1, 1, 1), (0.0, 0.0), tile or m.tile)
    return faces


def u_rest(gr, fe, sx, a, rc, yf, ys, z0, z1, pad=0.005, arm=0.022, wall=0.014):
    """A padded U-rest for one gun: a graphite yoke (two arms and a back, its back face at ys)
    lined with felt `pad` thick; the gun sits in the notch (half-width a) and its back on the
    felt at ys - wall."""
    yb = ys - wall
    lining_out = _u_contour(sx, a + pad, rc + pad, yf, yb + pad)
    lining_in = _u_contour(sx, a, rc, yf + 0.002, yb)
    A = a + pad + arm
    yoke = [(sx - A, yf), (sx - A, ys), (sx + A, ys), (sx + A, yf)] + list(reversed(lining_out))
    extrude_polygon(gr, yoke, z0, z1)
    extrude_polygon(fe, lining_out + list(reversed(lining_in)), z0 + 0.001, z1 + 0.002)


def door_bmesh(w, h, t, top_gap, channel):
    """One door in its hinge empty's frame: front face at y = 0, back at y = t, top edge at
    z = -top_gap, bottom at z = -top_gap - h. `channel` = (x0, x1, z0, z1, depth): a recessed pull
    channel in the front face (z in the empty's frame). Built as one closed solid (no overlapping
    boxes), so a bevel modifier only rounds real edges."""
    bm = bmesh.new()
    x0, x1 = -w / 2, w / 2
    zt, zb = -top_gap, -top_gap - h
    cx0, cx1, cz0, cz1, cd = channel
    V = bm.verts.new
    # front outer ring (y=0) and channel rim (y=0), channel floor (y=cd)
    fo = [V((x0, 0, zb)), V((x1, 0, zb)), V((x1, 0, zt)), V((x0, 0, zt))]
    fc = [V((cx0, 0, cz0)), V((cx1, 0, cz0)), V((cx1, 0, cz1)), V((cx0, 0, cz1))]
    ff = [V((cx0, cd, cz0)), V((cx1, cd, cz0)), V((cx1, cd, cz1)), V((cx0, cd, cz1))]
    bo = [V((x0, t, zb)), V((x1, t, zb)), V((x1, t, zt)), V((x0, t, zt))]
    F = bm.faces.new
    for i in range(4):                       # front face: four quads between the outer ring and the channel rim
        j = (i + 1) % 4
        F((fo[i], fo[j], fc[j], fc[i]))
    for i in range(4):                       # channel walls
        j = (i + 1) % 4
        F((fc[i], fc[j], ff[j], ff[i]))
    F(ff)                                    # channel floor
    F(list(reversed(bo)))                    # back
    for i in range(4):                       # edges of the slab
        j = (i + 1) % 4
        F((fo[i], bo[i], bo[j], fo[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


# ------------------------------------------------------------------ build

def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    graphite, stainless, felt, led = bk.graphite(), bk.stainless(), bk.felt(), bk.led()

    W, H = p["pitch"] * p["bays"], p["height"]
    xs = bay_centres(p)
    mid = p["bays"] // 2
    dw, dh, dt = p["door"]
    g = p["gap"]
    hz = p["hinge_z"]
    door_bot = hz - g - dh                       # 0.147
    side_t = W / 2 - (xs[-1] + dw / 2 + g)       # end stiles (0.027)
    mw = p["mullion"]
    stile = p["pitch"] - dw - 2 * g              # front face of a mullion (0.054): a 3 mm gap all round
    fz = p["floor_z"]
    pl = p["plinth"]

    gr, fe, st, le, bl = Mesh(0.5), Mesh(0.25), Mesh(0.5), Mesh(0.5), Mesh(0.5)

    # ---- carcass ---------------------------------------------------------------------------
    D = Y_BACK - Y_FRONT
    gr.box((0, Y_BACK - BACK_T / 2, (pl + H) / 2), (W, BACK_T, H - pl))                     # back
    gr.box((0, 0, (hz + H) / 2), (W, D, H - hz))                                               # top (front band 2.6-2.75)
    for s in (-1, 1):
        gr.box((s * (W / 2 - side_t / 2), 0, (pl + hz) / 2), (side_t, D, hz - pl))            # sides
    gr.box((0, Y_FRONT + 0.0275, (pl + door_bot - g) / 2), (W, 0.055, door_bot - g - pl))     # bottom rail under the doors
    gr.box((0, (Y_INNER + Y_BACK - BACK_T) / 2, (pl + fz - 0.01) / 2),
           (W - 2 * side_t, Y_BACK - BACK_T - Y_INNER, fz - 0.01 - pl))                        # bay floor block (fascia)
    gr.box((0, (Y_FRONT + p["plinth_inset"] + Y_BACK) / 2, pl / 2),
           (W - 0.06, D - p["plinth_inset"], pl))                                              # recessed plinth
    mullions = [(xs[i] + xs[i + 1]) / 2 for i in range(p["bays"] - 1)]
    for mx in mullions:
        gr.box((mx, (Y_INNER + Y_BACK - BACK_T) / 2, (fz + hz) / 2), (mw, Y_BACK - BACK_T - Y_INNER, hz - fz))
        gr.box((mx, (Y_FRONT + Y_INNER) / 2, (pl + hz) / 2), (stile, Y_INNER - Y_FRONT, hz - pl))   # front stile

    # ---- per bay ---------------------------------------------------------------------------
    for i, xc in enumerate(xs):
        left = -W / 2 + side_t if i == 0 else mullions[i - 1] + mw / 2
        right = W / 2 - side_t if i == p["bays"] - 1 else mullions[i] - mw / 2
        bw = right - left
        cx = (left + right) / 2
        il, ir = left + FELT_T, right - FELT_T        # felt faces
        iw = ir - il
        ylen = Y_FELT - Y_INNER
        # felt: back, sides, floor
        bl.box((cx, Y_FELT + FELT_T / 2, (fz + hz) / 2), (bw, FELT_T, hz - fz), shift=(0.13 * i, 0.0))
        for xx in (left + FELT_T / 2, right - FELT_T / 2):
            fe.box((xx, (Y_INNER + Y_FELT) / 2, (fz + hz) / 2), (FELT_T, ylen, hz - fz), shift=(0.07 * i, 0.3))
        fe.box((cx, (Y_INNER + Y_FELT) / 2, fz - 0.005), (iw, ylen, 0.01), shift=(0.21 * i, 0.5))
        # blank stainless plate on the floor's fascia, and a fine stainless nosing on the floor's edge
        st.box((cx, Y_INNER - 0.001, fz - 0.045), (0.10, 0.002, 0.032))
        st.box((cx, Y_INNER + 0.003, fz - 0.004), (iw, 0.006, 0.008))
        # cold LED lines in slim graphite channels: down both sides near the front, across the top
        ly = Y_INNER + 0.024
        for xx, sgn in ((il, 1), (ir, -1)):
            gr.box((xx + sgn * 0.004, ly, (fz + hz) / 2), (0.008, 0.018, hz - fz - 0.012))
            le.box((xx + sgn * 0.0085, ly, (fz + hz) / 2), (0.002, 0.008, hz - fz - 0.03))
        gr.box((cx, ly, hz - 0.005), (iw, 0.018, 0.010))
        le.box((cx, ly, hz - 0.0105), (iw - 0.03, 0.008, 0.002))
        # felt top shelf on a graphite tray, stainless front lip
        sz = p["shelf_z"]
        sy0 = Y_INNER + 0.05                          # behind the LED lines
        gr.box((cx, (sy0 + Y_FELT) / 2, sz - 0.014), (iw, Y_FELT - sy0, 0.022))
        fe.box((cx, (sy0 + Y_FELT) / 2, sz - 0.002), (iw - 0.004, Y_FELT - sy0, 0.004), shift=(0.3 * i, 0.1))
        st.box((cx, sy0 - 0.003, sz - 0.012), (iw, 0.006, 0.03))

        if i != mid:
            # two rows of padded U-rests: graphite yokes lined with felt on a graphite rail
            # (butt cradles on the floor, barrel rests at 0.94-1.00), one per gun slot
            ys = 0.158                                # yokes' back = the rail's front
            # the notches sit off the slot line toward -x, where the guns hang below their bore
            # (the slot x is the bore line: armory_rifle / armory_shotgun stand on it)
            for z0, z1, a, rc, yf, off in ((fz, fz + 0.075, 0.105, 0.022, 0.065, -0.055),
                                           (0.94, 1.00, 0.047, 0.03, 0.072, -0.008)):
                gr.box((cx, (ys + Y_FELT) / 2, (z0 + z1) / 2), (iw, Y_FELT - ys, z1 - z0 - 0.01))
                for dx in (-0.3, 0.0, 0.3):
                    u_rest(gr, fe, xc + dx + off, a, rc, yf, ys, z0, z1)
        else:
            # bay 3: a two-drawer graphite unit, a drawer-like felt tray at 1.0, the pistol pegboard
            uy0 = Y_INNER + 0.05
            gr.box((cx, (uy0 + Y_FELT) / 2, (fz + 0.955) / 2), (iw - 0.01, Y_FELT - uy0, 0.955 - fz))
            dh2 = (0.955 - fz - 0.009) / 2
            for k in range(2):
                z0 = fz + 0.003 + k * (dh2 + 0.003)
                gr.box((cx, uy0 - 0.009, z0 + dh2 / 2), (iw - 0.016, 0.018, dh2))
                st.box((cx, uy0 - 0.024, z0 + dh2 * 0.72), (0.36, 0.012, 0.014))          # bar pull
                for sx in (-1, 1):
                    st.box((cx + sx * 0.17, uy0 - 0.0225, z0 + dh2 * 0.72), (0.014, 0.015, 0.014))
            # the tray: graphite pan, felt bed at 1.0, low side rails, stainless lip with a finger pull
            gr.box((cx, (uy0 + Y_FELT) / 2, 0.97), (iw - 0.01, Y_FELT - uy0, 0.022))
            fe.box((cx, (uy0 + Y_FELT) / 2, 0.9845), (iw - 0.04, Y_FELT - uy0 - 0.02, 0.007), shift=(0.4, 0.2))
            for sx in (-1, 1):
                gr.box((cx + sx * (iw / 2 - 0.012), (uy0 + Y_FELT) / 2, 0.996), (0.012, Y_FELT - uy0, 0.03))
            lw = iw / 2 - 0.065                       # the lip, split round a 0.12 finger notch
            for sx in (-1, 1):
                st.box((cx + sx * (0.06 + lw / 2), uy0 - 0.004, 0.99), (lw, 0.008, 0.05))
            st.box((cx, uy0 - 0.004, 0.973), (0.12, 0.008, 0.016))                         # under the finger notch
            # pegboard: graphite frame, felt face, a pair of stainless pegs under each pistol
            pz0, pz1, px = 1.06, 1.84, 0.5
            yb = 0.208                                # felt face at y 0.200: a pistol's underside (origin) at the slot's y
            gr.box((cx, (yb + Y_FELT) / 2, (pz0 + pz1) / 2), (2 * px, Y_FELT - yb, pz1 - pz0))
            fe.box((cx, yb - 0.004, (pz0 + pz1) / 2), (2 * px - 0.03, 0.008, pz1 - pz0 - 0.03), shift=(0.6, 0.3))
            yface = yb - 0.008
            pegs = []
            for sx in (-1, 1):
                for z in (1.25, 1.65):
                    for dx in (-0.06, 0.06):
                        pegs.append((cx + sx * 0.2 + dx, z - 0.078))
            for x, z in pegs:
                cyl(st, (x, yface, z), (x, 0.164, z + 0.008), 0.0035, 0.0032, segs=8)
                cyl(st, (x, 0.164, z + 0.008), (x, 0.160, z + 0.016), 0.0032, 0.0032, segs=8)  # up-turned tip

    gro = gr.to_object(f"{n}_Carcass", col, graphite, root)
    common.add_bevel(gro, 0.0015, segments=1)
    fe.to_object(f"{n}_Felt", col, felt, root)
    sto = st.to_object(f"{n}_Trim", col, stainless, root)
    common.add_bevel(sto, 0.0008, segments=1).angle_limit = math.radians(60)   # boxes only, not the pegs
    le.to_object(f"{n}_LED", col, led, root)
    # (orchestrator) the bays' backs are backlit diffusers (a soft cold light box behind the guns:
    # a jewel case's vitrine; free: an emissive surface, no light)
    bl.to_object(f"{n}_Backlight_LED", col, bk.backlight(), root)

    # ---- doors -----------------------------------------------------------------------------
    cw, cz0, cz1, cd = 0.042, 0.30, 0.95, 0.02        # pull channel (heights from the floor)
    doors = []
    for i, xc in enumerate(xs):
        k = abs(i - mid)
        dur = p["durations"][min(k, len(p["durations"]) - 1)]
        door = common.empty(f"{n}_Door{i + 1}", col, (xc, Y_FRONT, hz))
        door.parent = root
        door["react"] = {"signal": p["signal"], "on": {"rotate": {"axis": "x", "angle": p["open_angle"]}},
                         "duration": dur, "collide": True, "motor": False}
        bm = door_bmesh(dw, dh, dt, g, (-cw / 2, cw / 2, cz0 - hz, cz1 - hz, cd))
        ob = common.mesh_object(f"{n}_Door{i + 1}_Leaf", bm, col, stainless, door, smooth=False)
        common.add_bevel(ob, 0.002, segments=2)
        doors.append(door)

    # ---- the wheel (on the middle door) ----------------------------------------------------
    d3 = doors[mid]
    wz = p["wheel_z"] - hz
    # escutcheon ring on the door face (moves with the door, not with the wheel)
    esc = Mesh(0.5)
    lathe_y(esc, [(0.0, 0.0), (0.072, 0.0), (0.072, 0.004), (0.066, 0.008), (0.0, 0.008)], (0, 0, wz), segs=32)
    common.mesh_object(f"{n}_Door{mid + 1}_Escutcheon", esc.bm, col, stainless, d3, smooth=False)
    wheel = common.empty(f"{n}_Wheel", col, (0, 0, wz))
    wheel.parent = d3
    wheel["interact"] = {
        "type": "switch", "signal": p["signal"], "state": False,
        "prompt": "Turn the wheel", "promptActive": "Close the safe",
        "range": 1.4, "duration": 1.1,
        "travel": {"axis": "z", "angle": 270},
    }
    R = p["wheel_d"] / 2
    rr = 0.017
    Rm = R - rr                                       # rim centre line
    yd = p["wheel_proud"]                             # rim plane out from the door face
    rim = Mesh(0.5)
    knurled_torus(rim, (0, -yd, 0), Rm, rr, segs=72, minor=10)
    for s in range(5):
        a = math.pi / 2 + 2 * math.pi * s / 5
        ca, sa = math.cos(a), math.sin(a)
        cyl(rim, (0.036 * ca, -yd + 0.012, 0.036 * sa), ((Rm - 0.004) * ca, -yd, (Rm - 0.004) * sa),
            0.0115, 0.0085, segs=10)
    common.mesh_object(f"{n}_Wheel_Rim", rim.bm, col, stainless, wheel, smooth=False)
    hub = Mesh(0.5)
    lathe_y(hub, [(0.0, 0.0), (0.058, 0.0), (0.058, 0.010), (0.046, 0.016), (0.044, yd + 0.006),
                  (0.040, yd + 0.016), (0.030, yd + 0.020), (0.0, yd + 0.020)], (0, 0, 0), segs=28)
    common.mesh_object(f"{n}_Wheel_Hub", hub.bm, col, graphite, wheel, smooth=False)
    cap = Mesh(0.5)
    lathe_y(cap, [(0.0, yd + 0.0215), (0.022, yd + 0.0215), (0.022, yd + 0.019), (0.0, yd + 0.019)],
            (0, 0, 0), segs=24)
    common.mesh_object(f"{n}_Wheel_Cap", cap.bm, col, stainless, wheel, smooth=False)

    if p["pose"]:
        for door in doors:
            door.rotation_euler.x = math.radians(p["open_angle"])

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
    for k, v in SLOTS.items():
        print(k, v)
