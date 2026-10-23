"""The bar's shell (town2_bar.py): a long, low 1950s roadhouse of painted cinder block on a
block stem wall, board-and-batten gables under a shallow corrugated roof; a deep porch along
the lot side (the front, -Y), a river deck on posts over the bank at the back (+Y) with steps
down to a landing at the water. Inside: worn floorboards, a dark wood wainscot under knotty
pine, a tobacco-dark board ceiling on exposed beams; partitions for the restroom corridor, the
restrooms and the back room.

Frame: asset metres, x along the building (+X = the west gable, the sun's end; -X the east end
toward town), y across (front -Y), z up; z = 0 is the lot's grade, the floor is at FLOOR."""
import math

from town2_bar_kit import arc_pts, place, rounded_rect

T_BLOCK = (1.0, 1.0, 1.0)
T_STEM = (0.62, 0.6, 0.56)
T_GABLE = (0.13, 0.075, 0.055)     # board-and-batten: a dark brown stain (x the Siding scan)
T_TRIM = (0.92, 0.82, 0.6)         # window / door trim, porch posts: old cream paint
T_HAINT = (0.42, 0.66, 0.72)       # the porch ceiling: haint blue
T_CEIL = (0.42, 0.36, 0.32)        # ceiling boards (x the Pine scan): smoke-darkened
T_BEAM = (0.55, 0.5, 0.46)


def openings(P):
    """Every opening as (wall, a0, a1, z0, z1, kind): wall in 'S' (front, y = -D/2), 'N' (back),
    'E' (x = -L/2), 'W' (x = +L/2), 'p_bar' (x = PX), 'p_cor' (y = PC, x < PX), 'p_rr' (y = PR);
    a = the coordinate along the wall (x for S / N, y for E / W)."""
    f = P["floor"]
    o = []
    o.append(("S", P["door_x"] - 0.55, P["door_x"] + 0.55, f, f + 2.2, "door"))
    for x in P["front_windows"]:
        o.append(("S", x - 0.75, x + 0.75, f + 1.05, f + 2.15, "window"))
    for x in P["back_windows"]:
        o.append(("N", x - 0.7, x + 0.7, f + 1.1, f + 2.15, "window"))
    o.append(("N", P["deck_door_x"] - 0.85, P["deck_door_x"] + 0.85, f, f + 2.2, "door2"))
    o.append(("E", -1.25, -0.25, f, f + 2.1, "door"))                       # the back exit (corridor)
    if P["west_window"]:
        o.append(("W", -0.45, 0.45, f + 2.55, f + 3.05, "transom"))          # a high window over the stage
    PX, PC, PR = P["px"], P["pc"], P["pr"]
    o.append(("p_bar", PR + 0.08, PC - 0.08, f, f + 2.25, "arch"))                    # the corridor's mouth
    o.append(("p_bar", P["backroom_door"][0], P["backroom_door"][1], f, f + 2.1, "door_ajar"))   # behind the bar
    o.append(("p_cor", -13.9, -12.95, f, f + 2.1, "door_closed"))            # back room from the corridor
    o.append(("p_rr", -15.3, -14.45, f, f + 2.1, "door_closed"))
    o.append(("p_rr", -12.4, -11.55, f, f + 2.1, "door_closed"))
    return o


def wall_run(k, mat, axis, c, t0, t1, a0, a1, z0, z1, holes, tint=(1, 1, 1), lmw=1.0, bevel=0.0, tile=None, uv_rot=False, skip=()):
    """A straight wall slab along `axis` ('x' or 'y') at cross-coordinate span t0..t1, from a0 to
    a1 and z0 to z1, with rectangular holes [(h0, h1, hz0, hz1)] cut out (as separate boxes)."""
    holes = sorted([h for h in holes if h[1] > a0 and h[0] < a1], key=lambda h: h[0])

    def piece(p0, p1, q0, q1):
        if p1 - p0 < 1e-3 or q1 - q0 < 1e-3:
            return
        if axis == "x":
            k.box(mat, (p0, t0, q0), (p1, t1, q1), bevel=bevel, tint=tint, lmw=lmw, tile=tile, uv_rot=uv_rot, skip=skip)
        else:
            k.box(mat, (t0, p0, q0), (t1, p1, q1), bevel=bevel, tint=tint, lmw=lmw, tile=tile, uv_rot=uv_rot, skip=skip)
    cur = a0
    for h0, h1, hz0, hz1 in holes:
        h0c, h1c = max(h0, a0), min(h1, a1)
        piece(cur, h0c, z0, z1)
        piece(h0c, h1c, z0, max(z0, hz0))
        piece(h0c, h1c, min(z1, hz1), z1)
        cur = h1c
    piece(cur, a1, z0, z1)


def wall_colliders(k, axis, t0, t1, a0, a1, z0, z1, gaps):
    gaps = sorted([g for g in gaps if g[1] > a0 and g[0] < a1])
    cur = a0
    for g0, g1 in gaps:
        if g0 - cur > 0.02:
            k.collider(*((cur, t0, z0, g0, t1, z1) if axis == "x" else (t0, cur, z0, t1, g0, z1)))
        cur = max(cur, g1)
    if a1 - cur > 0.02:
        k.collider(*((cur, t0, z0, a1, t1, z1) if axis == "x" else (t0, cur, z0, t1, a1, z1)))


def build_shell(k, P):
    L, D, W, f = P["L"], P["D"], P["wall"], P["floor"]
    x0, x1, y0, y1 = -L / 2, L / 2, -D / 2, D / 2
    ci = f + P["ceiling"]                      # the ceiling's underside
    plate = P["plate"]
    lin = 0.05                                 # interior lining (pine / wainscot) thickness
    ops = openings(P)
    by = {}
    for o in ops:
        by.setdefault(o[0], []).append(o)
    hole = lambda w: [(a0, a1, z0, z1) for (_, a0, a1, z0, z1, kind) in by.get(w, [])]

    # ---- stem wall (block, darker), slab edge, floor slab under the boards
    k.box("Block", (x0, y0, 0.0), (x1, y0 + W, f), tint=T_STEM, lmw=0.7, skip=("-z",))
    k.box("Block", (x0, y1 - W, 0.0), (x1, y1, f), tint=T_STEM, lmw=0.7, skip=("-z",))
    k.box("Block", (x0, y0 + W, 0.0), (x0 + W, y1 - W, f), tint=T_STEM, lmw=0.7, skip=("-z",))
    k.box("Block", (x1 - W, y0 + W, 0.0), (x1, y1 - W, f), tint=T_STEM, lmw=0.7, skip=("-z",))
    k.collider(x0, y0, 0.0, x1, y1, f)                                   # the floor (stand on it)

    # ---- exterior walls: block from the floor line to the plate, cut by every opening
    zf = f
    wall_run(k, "Block", "x", None, y0, y0 + W, x0, x1, zf, plate, hole("S"), lmw=0.8, skip=("+y",))
    wall_run(k, "Block", "x", None, y1 - W, y1, x0, x1, zf, plate, hole("N"), lmw=0.8, skip=("-y",))
    wall_run(k, "Block", "y", None, x0, x0 + W, y0 + W, y1 - W, zf, plate, hole("E"), lmw=0.8, skip=("+x",))
    wall_run(k, "Block", "y", None, x1 - W, x1, y0 + W, y1 - W, zf, plate, hole("W"), lmw=0.8, skip=("-x",))
    # colliders: walls split at the doorways (windows stay solid)
    dg = lambda w: [(a0, a1) for (_, a0, a1, z0, z1, kind) in by.get(w, []) if kind.startswith("door") or kind == "arch"]
    wall_colliders(k, "x", y0, y0 + W, x0, x1, f, plate, dg("S"))
    wall_colliders(k, "x", y1 - W, y1, x0, x1, f, plate, dg("N"))
    wall_colliders(k, "y", x0, x0 + W, y0, y1, f, plate, dg("E"))
    wall_colliders(k, "y", x1 - W, x1, y0, y1, f, plate, [])

    # ---- floor boards (one board field per room), ceiling boards, beams
    PX, PC, PR = P["px"], P["pc"], P["pr"]
    ix0, ix1, iy0, iy1 = x0 + W, x1 - W, y0 + W, y1 - W
    k.box("Floor", (ix0, iy0, f - 0.03), (ix1, iy1, f), skip=("-z",), lmw=1.0)
    k.box("Pine", (ix0, iy0, ci), (ix1, iy1, ci + 0.03), skip=("+z",), tint=T_CEIL, lmw=0.7)
    # exposed beams across the room (y), every 2.4 m in the bar room
    bx = PX + 1.6
    while bx < ix1 - 0.5:
        k.box("Wood", (bx - 0.09, iy0, ci - 0.24), (bx + 0.09, iy1, ci), bevel=0.012, tint=T_BEAM, lmw=0.8, skip=("+z",))
        bx += 2.4
    # a ridge-line girder along x
    k.box("Wood", (PX, -0.12, ci - 0.3), (ix1, 0.12, ci - 0.24), bevel=0.01, tint=T_BEAM, lmw=0.8, skip=("+z",))

    # ---- interior linings: dark wood wainscot (1.1 m) with a cap rail, knotty pine above
    wz = f + 1.1

    def lining(axis, t, sgn, a0, a1, holes, z_top=ci, tall_wainscot=False):
        """Lining on a wall face at cross coordinate t, facing sgn (+1: toward +axis normal)."""
        t0, t1 = (t, t + sgn * lin) if sgn > 0 else (t - lin, t)
        t0, t1 = min(t0, t1), max(t0, t1)
        wall_run(k, "Wood", axis, None, t0, t1, a0, a1, f, wz, holes, tint=(0.9, 0.9, 0.9), uv_rot=True)
        wall_run(k, "Pine", axis, None, t0, t1, a0, a1, wz, z_top, holes)
        # cap rail
        c0, c1 = (t, t + sgn * (lin + 0.035)) if sgn > 0 else (t - lin - 0.035, t)
        wall_run(k, "Wood", axis, None, min(c0, c1), max(c0, c1), a0, a1, wz - 0.03, wz + 0.035,
                 [(h0, h1, hz0, hz1) for h0, h1, hz0, hz1 in holes if hz0 < wz + 0.04], tint=(0.7, 0.7, 0.7), bevel=0.008)
        # baseboard
        b0, b1 = (t, t + sgn * (lin + 0.02)) if sgn > 0 else (t - lin - 0.02, t)
        wall_run(k, "Wood", axis, None, min(b0, b1), max(b0, b1), a0, a1, f, f + 0.14,
                 [(h0, h1, hz0, hz1) for h0, h1, hz0, hz1 in holes if hz0 < f + 0.15], tint=(0.5, 0.5, 0.5), bevel=0.005)

    # bar room (x PX..ix1): front, back, west end; the partition's west face
    lining("x", iy0, +1, PX + 0.075, ix1, hole("S"))
    lining("x", iy1, -1, PX + 0.075, ix1, hole("N"))
    lining("y", ix1, -1, iy0, iy1, hole("W"))
    # ---- partitions (framed, 0.15 thick, pine both sides): the bar room / service block line
    pt = 0.15
    hpx = [(a0, a1, z0, z1) for (w, a0, a1, z0, z1, kd) in ops if w == "p_bar"]
    wall_run(k, "Pine", "y", None, PX - pt / 2, PX + pt / 2, iy0, iy1, f, ci, hpx)
    wall_colliders(k, "y", PX - pt / 2, PX + pt / 2, iy0, iy1, f, ci, [(a0, a1) for a0, a1, _, _ in hpx])
    # wainscot on the bar-room face
    wall_run(k, "Wood", "y", None, PX + pt / 2, PX + pt / 2 + 0.02, iy0, iy1, f, wz, hpx, tint=(0.9, 0.9, 0.9), uv_rot=True)
    wall_run(k, "Wood", "y", None, PX + pt / 2, PX + pt / 2 + 0.045, iy0, iy1, wz - 0.03, wz + 0.035,
             [h for h in hpx if h[2] < wz + 0.04], tint=(0.7, 0.7, 0.7), bevel=0.008)
    # the corridor / back room line (y = PC) and the restroom line (y = PR), x0..PX
    hpc = [(a0, a1, z0, z1) for (w, a0, a1, z0, z1, kd) in ops if w == "p_cor"]
    wall_run(k, "Pine", "x", None, PC - pt / 2, PC + pt / 2, ix0, PX - pt / 2, f, ci, hpc, tint=(0.8, 0.8, 0.8))
    wall_colliders(k, "x", PC - pt / 2, PC + pt / 2, ix0, PX - pt / 2, f, ci, [(a0, a1) for a0, a1, _, _ in hpc])
    hpr = [(a0, a1, z0, z1) for (w, a0, a1, z0, z1, kd) in ops if w == "p_rr"]
    wall_run(k, "Pine", "x", None, PR - pt / 2, PR + pt / 2, ix0, PX - pt / 2, f, ci, hpr, tint=(0.8, 0.8, 0.8))
    wall_colliders(k, "x", PR - pt / 2, PR + pt / 2, ix0, PX - pt / 2, f, ci, [])
    # the restrooms' divider (closed rooms: their walls only)
    k.box("Pine", (-13.2 - pt / 2, iy0, f), (-13.2 + pt / 2, PR - pt / 2, ci), tint=(0.8, 0.8, 0.8), lmw=0.2)
    # service block linings: the corridor (painted pine, lighter), the back room (raw)
    lining("x", iy1, -1, ix0, PX - pt / 2, hole("N"))
    lining("y", ix0, +1, PC + pt / 2, iy1, [])
    lining("y", ix0, +1, PR + pt / 2, PC - pt / 2, hole("E"))

    # ---- door and window frames, glass, sills
    for (w, a0, a1, z0, z1, kind) in ops:
        if w in ("S", "N", "E", "W"):
            frame_opening(k, P, w, a0, a1, z0, z1, kind)

    # ---- the roof: shallow gable along x, corrugated metal on purlins, fascia, soffit, gables
    roof(k, P)
    porch(k, P)
    deck(k, P)


def frame_opening(k, P, w, a0, a1, z0, z1, kind):
    L, D, W = P["L"], P["D"], P["wall"]
    # wall plane coordinate (outer face) and the outward direction
    if w == "S":
        t_out, n = -D / 2, -1
    elif w == "N":
        t_out, n = D / 2, +1
    elif w == "E":
        t_out, n = -L / 2, -1
    else:
        t_out, n = L / 2, +1
    axis = "x" if w in ("S", "N") else "y"
    t_in = t_out - n * (W + 0.05)

    def B(mat, aa0, aa1, tt0, tt1, zz0, zz1, **kw):
        lo = [0, 0, zz0]
        hi = [0, 0, zz1]
        ai, ti = (0, 1) if axis == "x" else (1, 0)
        lo[ai], hi[ai] = min(aa0, aa1), max(aa0, aa1)
        lo[ti], hi[ti] = min(tt0, tt1), max(tt0, tt1)
        k.box(mat, tuple(lo), tuple(hi), **kw)
    tr = 0.09                                       # exterior trim width
    # exterior casing (painted trim), proud of the block by 2.5 cm
    B("Siding", a0 - tr, a0, t_out, t_out + n * 0.025, z0 - (0.0 if kind.startswith("door") else 0.06), z1 + tr, tint=T_TRIM, bevel=0.006, lmw=0.5)
    B("Siding", a1, a1 + tr, t_out, t_out + n * 0.025, z0 - (0.0 if kind.startswith("door") else 0.06), z1 + tr, tint=T_TRIM, bevel=0.006, lmw=0.5)
    B("Siding", a0 - tr, a1 + tr, t_out, t_out + n * 0.03, z1, z1 + tr + 0.02, tint=T_TRIM, bevel=0.006, lmw=0.5)
    # jambs (reveal through the wall)
    B("Wood", a0, a0 + 0.03, t_out, t_in, z0, z1, tint=(0.6, 0.6, 0.6), lmw=0.5)
    B("Wood", a1 - 0.03, a1, t_out, t_in, z0, z1, tint=(0.6, 0.6, 0.6), lmw=0.5)
    B("Wood", a0, a1, t_out, t_in, z1 - 0.03, z1, tint=(0.6, 0.6, 0.6), lmw=0.5)
    if kind in ("window", "transom"):
        # sill (outside, sloped look via a thin proud slab), stool inside
        B("Siding", a0 - 0.12, a1 + 0.12, t_out + n * 0.06, t_out - n * 0.02, z0 - 0.06, z0, tint=T_TRIM, bevel=0.01, lmw=0.5)
        B("Wood", a0 - 0.06, a1 + 0.06, t_in - n * 0.0, t_in - n * 0.05, z0 - 0.03, z0 + 0.01, tint=(0.7, 0.7, 0.7), bevel=0.006)
        B("Wood", a0, a1, t_out, t_in, z0, z0 + 0.02, tint=(0.6, 0.6, 0.6))
        # sash: a double-hung window, two sashes with a meeting rail; muntins on the upper
        tm = t_out - n * 0.09
        zm = (z0 + z1) / 2
        for (q0, q1, off) in ((z0 + 0.02, zm + 0.02, 0.0), (zm - 0.02, z1 - 0.03, 0.045)):
            ts = tm - n * off
            B("Siding", a0 + 0.03, a1 - 0.03, ts, ts - n * 0.04, q0, q0 + 0.05, tint=T_TRIM, lmw=0.6)
            B("Siding", a0 + 0.03, a1 - 0.03, ts, ts - n * 0.04, q1 - 0.05, q1, tint=T_TRIM, lmw=0.6)
            B("Siding", a0 + 0.03, a0 + 0.08, ts, ts - n * 0.04, q0, q1, tint=T_TRIM, lmw=0.6)
            B("Siding", a1 - 0.08, a1 - 0.03, ts, ts - n * 0.04, q0, q1, tint=T_TRIM, lmw=0.6)
            B("Glass", a0 + 0.08, a1 - 0.08, ts - n * 0.018, ts - n * 0.022, q0 + 0.05, q1 - 0.05, lmw=0.2)
    elif kind in ("door", "door2"):
        B("Wood", a0, a1, t_out, t_in, z0, z0 + 0.025, tint=(0.4, 0.4, 0.4))     # threshold
    elif kind == "arch":
        pass


def roof(k, P):
    L, D, plate = P["L"], P["D"], P["plate"]
    ov, ovg = P["overhang"], P["gable_overhang"]
    pitch = P["pitch"]
    ridge = plate + (D / 2) * pitch
    x0, x1 = -L / 2 - ovg, L / 2 + ovg
    ye = D / 2 + ov
    ze = plate - ov * pitch
    th = 0.03
    for s in (-1, 1):
        # the metal: one slope, its top face (UV along x: the corrugations run down the slope)
        p0 = (x0, 0.0, ridge + 0.02)
        k.quad("Roof", [(x0, s * ye, ze), (x1, s * ye, ze), (x1, 0.0, ridge), (x0, 0.0, ridge)][:: (1 if s < 0 else -1)],
               lmw=0.35, uv=lambda co, nn: (co.x / 1.8, math.hypot(co.y, co.z - ridge) / 1.8))
        # underside (the soffit boards over the overhang only; the attic is closed by the ceiling)
        k.quad("Siding", [(x0, s * ye, ze - th), (x0, s * (D / 2), plate - th), (x1, s * (D / 2), plate - th), (x1, s * ye, ze - th)][:: (1 if s < 0 else -1)],
               tint=T_GABLE, lmw=0.35)
        # the corrugated eave edge: a wavy strip (what the eye sees of the profile)
        n = int((x1 - x0) / 0.076)
        pts = []
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            pts.append((x, s * ye, ze + 0.009 * math.sin(i * math.pi)))
        bot = [(p[0], p[1], ze - 0.012) for p in pts]
        for i in range(n):
            q = [bot[i], bot[i + 1], pts[i + 1], pts[i]]
            if s > 0:
                q = q[::-1]
            k.quad("Roof", q, lmw=0.1)
        # fascia board under the eave edge
        k.box("Siding", (x0, s * ye - (0.025 if s > 0 else 0), ze - 0.22), (x1, s * ye + (0.0 if s > 0 else 0.025), ze - 0.012),
              tint=T_GABLE, lmw=0.4)
        # gutter (half round) on the front only
        if s < 0:
            k.lathe("PropsOut", [(0.06, 0), (0.06, x1 - x0)], sides=10, M=place(x0, s * ye - 0.06, ze - 0.06) @
                    __import__("mathutils").Matrix.Rotation(math.pi / 2, 4, "Y"), uv=("cell", "galvanized"), a0=-math.pi / 2, a1=math.pi / 2,
                    cap0=False, cap1=False, lmw=0.3)
    # ridge cap
    k.box("Roof", (x0, -0.16, ridge - 0.02), (x1, 0.16, ridge + 0.04), lmw=0.2, skip=("-z",))
    # gables: board-and-batten triangles at both ends, battens every 0.4 m
    for gx, s in ((-L / 2, -1), (L / 2, 1)):
        tri = [(-D / 2 - 0.0, plate), (D / 2, plate), (0.0, ridge)]
        # the triangle (a thin prism in y-z, at the wall face)
        k.prism("Siding", [(y, z) for y, z in tri], 0.0, 0.03, M=_yz_plane(gx + s * 0.0, s), tint=T_GABLE, lmw=0.7,
                uv=lambda co, nn: (co.y / 1.6, co.z / 1.6))
        y = -D / 2 + 0.2
        while y < D / 2 - 0.1:
            zt = plate + (D / 2 - abs(y)) * pitch
            k.box("Siding", (gx + s * 0.03, y - 0.035, plate), (gx + s * 0.055, y + 0.035, zt - 0.02), tint=T_GABLE, lmw=0.4,
                  M=None)
            y += 0.4
        # rake boards
        for sy in (-1, 1):
            a = (gx + s * 0.06, sy * (D / 2 + ov), ze)
            b = (gx + s * 0.06, 0.0, ridge)
            _beam(k, "Siding", a, b, 0.05, 0.2, tint=T_GABLE, lmw=0.4)
    # the attic's plate band (block top to the soffit)
    L2 = L / 2
    for s in (-1, 1):
        k.box("Siding", (-L2, s * (D / 2) - (0.0 if s > 0 else 0.03), plate - 0.25), (L2, s * (D / 2) + (0.03 if s > 0 else 0.0), plate),
              tint=T_GABLE, lmw=0.5)
    k.collider(-L / 2 - ovg, -D / 2 - ov, plate, L / 2 + ovg, D / 2 + ov, ridge)


def _yz_plane(x, s):
    """Matrix taking a prism drawn in (y, z) with depth along +local z to the gable at x."""
    from mathutils import Matrix
    M = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    return Matrix.Translation((x if s > 0 else x - 0.03, 0, 0)) @ M


def _beam(k, mat, a, b, w, h, **kw):
    """A rectangular beam w (horizontal) x h from a to b."""
    from mathutils import Matrix, Vector
    a, b = Vector(a), Vector(b)
    d = b - a
    Lb = d.length
    q = d.to_track_quat("X", "Z")
    M = Matrix.Translation(a) @ q.to_matrix().to_4x4()
    k.box(mat, (0, -w / 2, -h / 2), (Lb, w / 2, h / 2), M=M, **kw)


def porch(k, P):
    D, f = P["D"], P["floor"]
    px0, px1, pd = P["porch_x0"], P["porch_x1"], P["porch_depth"]
    y0 = -D / 2 - pd
    yw = -D / 2
    # deck boards on joists, a skirt of lattice-ish boards to grade
    k.box("Deck", (px0, y0, f - 0.04), (px1, yw, f), skip=("-z",), lmw=0.8, uv_rot=True)
    k.box("Siding", (px0, y0, 0.0), (px1, y0 + 0.03, f - 0.04), tint=(0.25, 0.25, 0.24), lmw=0.4, skip=("-z",))
    for x in (px0, px1):
        k.box("Siding", (x - 0.015, y0, 0.0), (x + 0.015, yw, f - 0.04), tint=(0.25, 0.25, 0.24), lmw=0.3, skip=("-z",))
    k.box("Deck", (px0, y0 - 0.02, f - 0.06), (px1, y0 + 0.03, f), tint=(0.8, 0.8, 0.8), bevel=0.01, lmw=0.6)   # nosing
    k.collider(px0, y0, 0.0, px1, yw, f)
    # steps: in front of the door and at the east end
    dx = P["door_x"]
    for i in range(3):
        zt = f - (i + 1) * f / 3
        k.box("Deck", (dx - 1.1, y0 - 0.3 * (i + 1), max(0.0, zt - 0.04)), (dx + 1.1, y0 - 0.3 * i, zt), bevel=0.008, lmw=0.6,
              skip=("-z",), uv_rot=True)
        k.box("Siding", (dx - 1.1, y0 - 0.3 * (i + 1) + 0.02, 0.0), (dx + 1.1, y0 - 0.3 * (i + 1) + 0.04, max(0.0, zt - 0.04)),
              tint=(0.25, 0.25, 0.24), lmw=0.3, skip=("-z",))
        k.collider(dx - 1.1, y0 - 0.3 * (i + 1), 0.0, dx + 1.1, y0 - 0.3 * i, zt)
    for i in range(3):
        zt = f - (i + 1) * f / 3
        k.box("Deck", (px0 - 0.3 * (i + 1), y0 + 0.2, max(0.0, zt - 0.04)), (px0 - 0.3 * i, y0 + 1.8, zt), bevel=0.008, lmw=0.5,
              skip=("-z",))
        k.collider(px0 - 0.3 * (i + 1), y0 + 0.2, 0.0, px0 - 0.3 * i, y0 + 1.8, zt)
    # posts (6x6, painted trim green) on the porch edge, a doubled beam, rafters, a shed roof
    zb = P["porch_beam"]
    zw = P["plate"] - 0.25
    xs = [px0 + 0.15 + i * (px1 - px0 - 0.3) / (P["porch_posts"] - 1) for i in range(P["porch_posts"])]
    # (no post in front of the door's steps)
    xs = [x for x in xs if abs(x - dx) > 1.3]
    for x in xs:
        k.box("Siding", (x - 0.075, y0 + 0.08, f), (x + 0.075, y0 + 0.23, zb), bevel=0.012, tint=T_TRIM, lmw=0.6)
        k.box("Siding", (x - 0.1, y0 + 0.055, f), (x + 0.1, y0 + 0.255, f + 0.08), bevel=0.01, tint=T_TRIM, lmw=0.5)
        k.collider(x - 0.08, y0 + 0.08, f, x + 0.08, y0 + 0.23, zb)
    k.box("Siding", (px0, y0 + 0.06, zb), (px1, y0 + 0.25, zb + 0.24), bevel=0.01, tint=T_GABLE, lmw=0.6)
    # ceiling boards (haint blue) following the roof slope, rafters showing
    zr0 = zb + 0.24
    k.quad("Siding", [(px0, y0 + 0.06, zr0), (px0, yw, zw), (px1, yw, zw), (px1, y0 + 0.06, zr0)], tint=T_HAINT, lmw=0.8,
           uv=lambda co, nn: (co.x / 1.6, co.y / 1.6), uv_rot=False)
    x = px0 + 0.3
    while x < px1 - 0.2:
        _beam(k, "Siding", (x, y0 + 0.06, zr0 - 0.12), (x, yw, zw - 0.12), 0.05, 0.14, tint=T_HAINT, lmw=0.4)
        x += 0.8
    # the shed roof's metal over it, overhanging the beam
    zr1 = zw + 0.12
    yo = y0 - 0.35
    zo = zr1 - (yw - yo) * (zr1 - (zr0 + 0.14)) / (yw - (y0 + 0.06))
    k.quad("Roof", [(px0 - 0.3, yo, zo), (px1 + 0.3, yo, zo), (px1 + 0.3, yw, zr1), (px0 - 0.3, yw, zr1)], lmw=0.3,
           uv=lambda co, nn: (co.x / 1.8, co.y / 1.8))
    k.box("Siding", (px0 - 0.3, yo - 0.025, zo - 0.18), (px1 + 0.3, yo, zo), tint=T_GABLE, lmw=0.4)
    k.quad("Siding", [(px0 - 0.3, yo, zo - 0.18), (px0 - 0.3, y0 + 0.06, zr0), (px1 + 0.3, y0 + 0.06, zr0), (px1 + 0.3, yo, zo - 0.18)][::-1],
           tint=T_HAINT, lmw=0.3)
    for xe in (px0 - 0.3, px1 + 0.3):
        k.quad("Siding", [(xe, yo, zo - 0.18), (xe, yw, zr1 - 0.18), (xe, yw, zr1), (xe, yo, zo)][:: (1 if xe < 0 else -1)], tint=T_GABLE, lmw=0.3)


def deck(k, P):
    D, f = P["D"], P["floor"]
    dx0, dx1, dy1 = P["deck_x0"], P["deck_x1"], P["deck_y1"]
    y0 = D / 2
    k.box("Deck", (dx0, y0, f - 0.04), (dx1, dy1, f), lmw=0.7, uv_rot=True)
    k.collider(dx0, y0, f - 0.3, dx1, dy1, f)
    # rim joists and joists below (seen from the bank / the crawl space)
    gz = P["deck_ground"]
    k.box("Deck", (dx0, dy1 - 0.05, f - 0.3), (dx1, dy1, f - 0.04), tint=(0.6, 0.6, 0.6), lmw=0.4)
    k.box("Deck", (dx0, y0, f - 0.3), (dx0 + 0.05, dy1, f - 0.04), tint=(0.6, 0.6, 0.6), lmw=0.3)
    k.box("Deck", (dx1 - 0.05, y0, f - 0.3), (dx1, dy1, f - 0.04), tint=(0.6, 0.6, 0.6), lmw=0.3)
    x = dx0 + 0.4
    while x < dx1 - 0.1:
        k.box("Deck", (x - 0.025, y0, f - 0.28), (x + 0.025, dy1 - 0.05, f - 0.04), tint=(0.5, 0.5, 0.5), lmw=0.15, skip=("+z",))
        x += 0.4
    # posts down into the bank (their feet run under the terrain), cross bracing
    for x in [dx0 + 0.1 + i * (dx1 - dx0 - 0.2) / 6 for i in range(7)]:
        for yy, zb in ((y0 + 0.4, gz[0]), (dy1 - 0.15, gz[1])):
            k.box("Deck", (x - 0.07, yy - 0.07, zb - 1.0), (x + 0.07, yy + 0.07, f - 0.3), tint=(0.55, 0.55, 0.55), lmw=0.25)
        _beam(k, "Deck", (x, y0 + 0.4, gz[0] + 0.2), (x, dy1 - 0.15, f - 0.35), 0.04, 0.12, tint=(0.5, 0.5, 0.5), lmw=0.15)
    # railing: posts, top rail, balusters (2x2), on three sides with a gap for the stair (west end)
    st0, st1 = P["stair_x"] - 0.65, P["stair_x"] + 0.65
    rh = f + 1.0

    def rail(a, b, gap=None):
        ax, ay = a
        bx, by = b
        Lr = math.hypot(bx - ax, by - ay)
        n = int(Lr / 0.13)
        for i in range(n + 1):
            t = i / n
            px, py = ax + (bx - ax) * t, ay + (by - ay) * t
            if gap and gap[0] < (px if ay == by else py) < gap[1]:
                continue
            k.box("Deck", (px - 0.02, py - 0.02, f), (px + 0.02, py + 0.02, rh - 0.06), tint=(0.85, 0.85, 0.85), lmw=0.12)
        segs = [(a, b)] if not gap else ([(a, (gap[0], ay) if ay == by else (ax, gap[0])), ((gap[1], ay) if ay == by else (ax, gap[1]), b)])
        for (sa, sb) in segs:
            x0_, x1_ = sorted((sa[0], sb[0]))
            y0_, y1_ = sorted((sa[1], sb[1]))
            k.box("Deck", (x0_ - 0.06, y0_ - 0.06, rh - 0.06), (x1_ + 0.06, y1_ + 0.06, rh), bevel=0.01, lmw=0.3)
            k.box("Deck", (x0_ - 0.02, y0_ - 0.02, f + 0.1), (x1_ + 0.02, y1_ + 0.02, f + 0.16), lmw=0.15)
            k.collider(x0_ - 0.06, y0_ - 0.06, f, x1_ + 0.06, y1_ + 0.06, rh + 0.1)
    rail((dx0, dy1 - 0.04), (dx1, dy1 - 0.04), gap=(st0, st1))
    rail((dx0 + 0.04, y0 + 0.05), (dx0 + 0.04, dy1 - 0.04))
    rail((dx1 - 0.04, y0 + 0.05), (dx1 - 0.04, dy1 - 0.04))
    for x in (dx0 + 0.04, dx1 - 0.04, st0, st1):
        k.box("Deck", (x - 0.06, dy1 - 0.1, f), (x + 0.06, dy1 + 0.02, rh + 0.1), bevel=0.01, lmw=0.3)
    # the stair down the bank to the landing: stringers, treads (each a collider step)
    n = P["stair_steps"]
    zt0, zb = f, P["landing_z"]
    rise = (zt0 - zb) / n
    run = 0.28
    for i in range(n):
        z = zt0 - (i + 1) * rise
        y_a, y_b = dy1 + i * run, dy1 + (i + 1) * run
        k.box("Deck", (st0, y_a, z - 0.04), (st1, y_b + 0.03, z), bevel=0.006, lmw=0.3, uv_rot=True)
        k.collider(st0, y_a, z - 0.25, st1, y_b, z)
    ylen = n * run
    for x in (st0 - 0.05, st1 + 0.05):
        _beam(k, "Deck", (x, dy1, zt0 - 0.15), (x, dy1 + ylen, zb - 0.15), 0.05, 0.28, tint=(0.6, 0.6, 0.6), lmw=0.2)
        # handrail
        _beam(k, "Deck", (x, dy1, zt0 + 0.9), (x, dy1 + ylen, zb + 0.9), 0.06, 0.06, lmw=0.2)
        for i in range(0, n + 1, 4):
            yy = dy1 + i * run
            zz = zt0 - i * rise
            k.box("Deck", (x - 0.04, yy - 0.04, zz - 0.2), (x + 0.04, yy + 0.04, zz + 0.9), lmw=0.15)
    # the landing at the water: a small dock on piles
    ly0, ly1 = dy1 + ylen, dy1 + ylen + 2.4
    lx0, lx1 = st0 - 1.0, st1 + 2.2
    k.box("Deck", (lx0, ly0, zb - 0.05), (lx1, ly1, zb), lmw=0.4, uv_rot=True)
    k.collider(lx0, ly0, zb - 0.4, lx1, ly1, zb)
    for (x, y) in ((lx0 + 0.1, ly0 + 0.1), (lx1 - 0.1, ly0 + 0.1), (lx0 + 0.1, ly1 - 0.1), (lx1 - 0.1, ly1 - 0.1)):
        k.cyl("Deck", (x, y, zb - 2.0), (x, y, zb + 0.35), 0.1, sides=8, tint=(0.5, 0.48, 0.45), lmw=0.2)
    P["_landing"] = (lx0, ly0, lx1, ly1, zb)
