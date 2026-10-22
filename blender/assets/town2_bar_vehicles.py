"""Vehicles for the bar's lot (town2_bar_lot.py): a 1990s full-size pickup, a 1980s square-body
pickup, a windowless full-size cargo van (the invaders'). Bodies are side-profile prisms
(wheel arches cut in) with bevelled edges; wheels are lathed tyres on steel rims; glass, lights,
chrome and the grille from the props atlas. Origin: on the ground under the vehicle's centre,
the nose toward local +x."""
import math

from mathutils import Matrix, Vector

M_OUT = "PropsOut"


def _arch_outline(x0, x1, zb, arches, ztop_pts):
    """CCW side outline (x, z): bottom from x0 to x1 at zb with semicircular wheel arches
    [(cx, r)], then the upper edge `ztop_pts` from x1 back to x0."""
    pts = [(x0, zb)]
    for cx, r in sorted(arches):
        if cx - r <= x0 or cx + r >= x1:
            continue
        pts.append((cx - r, zb))
        for i in range(1, 12):
            a = math.pi - math.pi * i / 12
            pts.append((cx + r * math.cos(a), zb + r * math.sin(a) * 0.95))
        pts.append((cx + r, zb))
    pts.append((x1, zb))
    pts += ztop_pts
    return pts


def _side_prism(k, outline, y0, y1, M, cell, bevel=0.035, lmw=0.5):
    """Extrude an (x, z) outline across y0..y1 (local), placed by M."""
    S = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))       # (x, y, z) <- (a, -c, b)
    # prism draws (a, b) in its xy plane extruded along its z: map a -> x, b -> z, extrusion -> -y
    k.prism(M_OUT, outline, -y1, -y0, M=M @ S, bevel=bevel, segs=2, uv=("cell", cell), lmw=lmw)


def wheel(k, M, x, y, r=0.38, w=0.26, rim="wheel_steel", lmw=0.3):
    side = 1 if y > 0 else -1
    W = M @ Matrix.Translation((x, y, r)) @ Matrix.Rotation(-math.pi / 2 * side, 4, "X")
    prof = [(r * 0.62, -w / 2), (r * 0.9, -w / 2 - 0.005), (r * 0.98, -w / 2 + 0.03), (r, -w / 2 + 0.07), (r, w / 2 - 0.07),
            (r * 0.98, w / 2 - 0.03), (r * 0.9, w / 2 + 0.005), (r * 0.62, w / 2)]
    k.lathe(M_OUT, prof, sides=14, M=W, uv=("cell", "tire"), lmw=lmw, cap0=False, cap1=False)
    k.lathe(M_OUT, [(r * 0.63, w / 2 - 0.01), (r * 0.6, w / 2 - 0.03), (r * 0.3, w / 2 - 0.05), (r * 0.18, w / 2 - 0.02), (r * 0.08, w / 2 - 0.0), (0.0, w / 2 - 0.0)],
            sides=14, M=W, uv=("cell", rim), lmw=0.1, cap0=False)
    k.lathe(M_OUT, [(0.0, -w / 2 + 0.02), (r * 0.62, -w / 2 + 0.02)], sides=12, M=W, uv=("cell", "rubber"), lmw=0.02, cap0=False, cap1=False)


def pickup(k, x, y, yaw, paint="truck_red", style="90s", rust=True, extras=()):
    M = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Translation((-2.7, 0, 0))
    hw = 0.99
    zb = 0.46
    fa, ra, r = 0.88, 4.2, 0.5
    if style == "90s":
        top = [(3.02, 1.12), (3.0, 1.82), (2.2, 1.84), (1.62, 1.18), (0.25, 1.08), (0.12, 0.98), (0.12, zb)]
    else:   # the square-body: flat hood, upright glass
        top = [(3.02, 1.12), (3.0, 1.84), (2.28, 1.85), (1.86, 1.2), (0.22, 1.12), (0.12, 1.08), (0.12, zb)]
    cab = _arch_outline(0.12, 3.02, zb, [(fa, r)], top)
    _side_prism(k, cab, -hw, hw, M, paint)
    # the bed: two side walls (arched), the front wall, the tailgate, the floor (bedliner)
    bx0, bx1, bz = 3.07, 5.36, 1.12
    for s in (-1, 1):
        wall = _arch_outline(bx0, bx1, zb + 0.06, [(ra, r)], [(bx1, bz), (bx0, bz)])
        _side_prism(k, wall, s * hw - (0.06 if s > 0 else 0), s * hw + (0.0 if s > 0 else 0.06), M, paint, bevel=0.02)
        k.box(M_OUT, (bx0, s * hw - (0.08 if s > 0 else 0), bz - 0.005), (bx1, s * hw + (0.0 if s > 0 else 0.08), bz + 0.025), M=M, bevel=0.01, uv=("cell", paint), lmw=0.2)
    k.box(M_OUT, (bx0, -hw + 0.06, 0.62), (bx0 + 0.06, hw - 0.06, bz), M=M, uv=("cell", paint), lmw=0.2)
    k.box(M_OUT, (bx1 - 0.06, -hw + 0.04, 0.6), (bx1, hw - 0.04, bz), M=M, bevel=0.015, uv=("cell", paint), lmw=0.3)
    k.box(M_OUT, (bx0 + 0.06, -hw + 0.06, 0.6), (bx1 - 0.06, hw - 0.06, 0.64), M=M, uv=("cell", "bedliner"), lmw=0.3)
    k.box(M_OUT, (bx0, -0.8, zb - 0.04), (bx1, 0.8, 0.6), M=M, uv=("cell", "iron_black"), lmw=0.05, skip=("-z",))     # frame under the bed
    # glass: windshield, side windows, the back light
    wz0, wz1 = (1.2, 1.8) if style == "90s" else (1.22, 1.8)
    wx0, wx1 = (1.66, 2.18) if style == "90s" else (1.9, 2.27)
    for s in (-1, 1):
        q = [(wx1 + 0.08, s * (hw + 0.004), 1.25), (2.92, s * (hw + 0.004), 1.25), (2.92, s * (hw + 0.004), 1.74), (wx1 + 0.12, s * (hw + 0.004), 1.74)]
        k.quad(M_OUT, [tuple(M @ Vector(p)) for p in (q if s < 0 else q[::-1])], uv=("cell", "glass_dark"), lmw=0.1)
    n = Vector((-(wz1 - wz0), 0, -(wx1 - wx0))).normalized() * -0.006
    ws = [Vector((wx0 + 0.04, -hw + 0.1, wz0 + 0.04)), Vector((wx0 + 0.04, hw - 0.1, wz0 + 0.04)), Vector((wx1 - 0.02, hw - 0.12, wz1 - 0.03)), Vector((wx1 - 0.02, -hw + 0.12, wz1 - 0.03))]
    off = Vector((-0.01, 0, 0.006))
    k.quad(M_OUT, [tuple(M @ (p + off)) for p in ws], uv=("cell", "glass_dark"), lmw=0.1)
    k.quad(M_OUT, [tuple(M @ Vector(p)) for p in [(3.025, 0.75, 1.3), (3.025, -0.75, 1.3), (3.025, -0.7, 1.72), (3.025, 0.7, 1.72)]], uv=("cell", "glass_dark"), lmw=0.1)
    # front: grille, headlights, a chrome bumper; rear: tail lights, a step bumper; mirrors, handles
    k.box(M_OUT, (0.09, -0.62, 0.68), (0.13, 0.62, 0.98), M=M, uv=("cell", "grille"), lmw=0.1)
    for s in (-1, 1):
        k.box(M_OUT, (0.095, s * 0.8 - 0.15, 0.74), (0.13, s * 0.8 + 0.15, 0.94), M=M, uv=("cell", "headlight"), lmw=0.05)
        k.box(M_OUT, (0.1, s * 0.92 - 0.04, 0.6), (0.14, s * 0.92 + 0.04, 0.68), M=M, uv=("cell", "turn_amber"), lmw=0.02)
        k.box(M_OUT, (bx1 - 0.01, s * (hw - 0.08) - 0.07, 0.75), (bx1 + 0.02, s * (hw - 0.08) + 0.07, 1.05), M=M, uv=("cell", "taillight"), lmw=0.02)
        k.box(M_OUT, (2.05, s * (hw + 0.02) - (0.1 if s < 0 else 0.0), 1.22), (2.25, s * (hw + 0.02) + (0.1 if s > 0 else 0.0), 1.38), M=M, bevel=0.01, uv=("cell", "chrome"), lmw=0.02)
        k.box(M_OUT, (2.7, s * (hw + 0.003) - 0.01, 1.05), (2.86, s * (hw + 0.003) + 0.01, 1.08), M=M, uv=("cell", "chrome"), lmw=0.0)
        wheel(k, M, fa, s * (hw - 0.14), r=0.38)
        wheel(k, M, ra, s * (hw - 0.14), r=0.38)
        if rust:
            k.box(M_OUT, (1.38, s * (hw + 0.002) - 0.004, zb), (3.0, s * (hw + 0.002) + 0.004, zb + 0.16), M=M, uv=("cell", "rust"), lmw=0.02)
            k.box(M_OUT, (4.72, s * (hw + 0.002) - 0.004, zb + 0.06), (5.34, s * (hw + 0.002) + 0.004, zb + 0.24), M=M, uv=("cell", "rust"), lmw=0.02)
        k.box(M_OUT, (4.75, s * 0.86 - 0.12, 0.2), (4.8, s * 0.86 + 0.12, 0.5), M=M, uv=("cell", "mudflap"), lmw=0.01)
    k.box(M_OUT, (-0.06, -hw + 0.02, 0.4), (0.12, hw - 0.02, 0.62), M=M, bevel=0.03, uv=("cell", "chrome"), lmw=0.2)
    k.box(M_OUT, (bx1, -hw + 0.06, 0.38), (bx1 + 0.16, hw - 0.06, 0.56), M=M, bevel=0.02, uv=("cell", "chrome" if style == "80s" else "iron_black"), lmw=0.2)
    k.box(M_OUT, (0.4, -0.75, 0.25), (bx1 - 0.2, 0.75, zb), M=M, uv=("cell", "iron_black"), lmw=0.05, skip=("-z",))
    if "toolbox" in extras:
        k.box(M_OUT, (bx0 + 0.07, -hw, bz), (bx0 + 0.55, hw, bz + 0.34), M=M, bevel=0.02, uv=("cell", "aluminium"), lmw=0.2)
    if "cargo" in extras:
        k.box(M_OUT, (4.2, -0.6, 0.64), (4.9, 0.1, 0.94), M=M, bevel=0.02, uv=("cell", "cooler_red"), lmw=0.1)
        k.box(M_OUT, (3.3, 0.1, 0.64), (4.0, 0.8, 0.74), M=M, uv=("cell", "wood_light"), lmw=0.05)
    c = M @ Vector((2.74, 0, 0))
    a = math.radians(yaw)
    ext = (abs(math.cos(a)) * 2.75 + abs(math.sin(a)) * 1.0, abs(math.sin(a)) * 2.75 + abs(math.cos(a)) * 1.0)
    k.collider(c.x - ext[0], c.y - ext[1], 0.0, c.x + ext[0], c.y + ext[1], 1.85)


def van(k, x, y, yaw, paint="van_black"):
    """A windowless full-size cargo van, nose toward local +x."""
    M = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Translation((-2.95, 0, 0))
    hw = 1.0
    zb = 0.42
    fa, ra, r = 0.98, 4.45, 0.48
    top = [(5.9, 0.5), (5.9, 1.98), (5.85, 2.06), (1.7, 2.06), (1.12, 1.32), (0.28, 1.12), (0.12, 1.02), (0.12, zb)]
    body = _arch_outline(0.12, 5.9, zb, [(fa, r), (ra, r)], top[1:])
    body = [(x_, z_) for x_, z_ in body]
    _side_prism(k, body, -hw, hw, M, paint, bevel=0.05)
    # glass: windshield, the front doors' windows only
    ws = [Vector((1.14, -hw + 0.1, 1.36)), Vector((1.14, hw - 0.1, 1.36)), Vector((1.66, hw - 0.12, 1.98)), Vector((1.66, -hw + 0.12, 1.98))]
    k.quad(M_OUT, [tuple(M @ (p + Vector((-0.012, 0, 0.008)))) for p in ws], uv=("cell", "glass_dark"), lmw=0.1)
    for s in (-1, 1):
        q = [(1.72, s * (hw + 0.004), 1.4), (2.55, s * (hw + 0.004), 1.4), (2.55, s * (hw + 0.004), 1.9), (1.82, s * (hw + 0.004), 1.9)]
        k.quad(M_OUT, [tuple(M @ Vector(p)) for p in (q if s < 0 else q[::-1])], uv=("cell", "glass_dark"), lmw=0.1)
        # door seams (the slider), a handle, mirrors
        for sx in (2.62, 3.95):
            k.box(M_OUT, (sx - 0.006, s * (hw + 0.002) - 0.003, 0.5), (sx + 0.006, s * (hw + 0.002) + 0.003, 1.95), M=M, uv=("cell", "plastic_black"), lmw=0.0)
        k.box(M_OUT, (2.4, s * (hw + 0.004) - 0.008, 1.12), (2.52, s * (hw + 0.004) + 0.008, 1.15), M=M, uv=("cell", "plastic_black"), lmw=0.0)
        k.box(M_OUT, (1.62, s * (hw + 0.05) - (0.12 if s < 0 else 0.0), 1.45), (1.74, s * (hw + 0.05) + (0.12 if s > 0 else 0.0), 1.75), M=M, bevel=0.01, uv=("cell", "plastic_black"), lmw=0.02)
        k.box(M_OUT, (0.1, s * 0.78 - 0.14, 0.78), (0.14, s * 0.78 + 0.14, 0.96), M=M, uv=("cell", "headlight"), lmw=0.02)
        k.box(M_OUT, (5.89, s * (hw - 0.08) - 0.06, 1.0), (5.92, s * (hw - 0.08) + 0.06, 1.4), M=M, uv=("cell", "taillight"), lmw=0.02)
        wheel(k, M, fa, s * (hw - 0.15), r=0.37, rim="steel_dark")
        wheel(k, M, ra, s * (hw - 0.15), r=0.37, rim="steel_dark")
    k.box(M_OUT, (5.905, -0.004, 0.5), (5.915, 0.004, 1.95), M=M, uv=("cell", "plastic_black"), lmw=0.0)        # the rear doors' seam
    k.box(M_OUT, (0.08, -0.6, 0.66), (0.13, 0.6, 0.98), M=M, uv=("cell", "grille"), lmw=0.05)
    k.box(M_OUT, (-0.06, -hw + 0.03, 0.38), (0.14, hw - 0.03, 0.62), M=M, bevel=0.03, uv=("cell", "plastic_black"), lmw=0.1)
    k.box(M_OUT, (5.85, -hw + 0.05, 0.35), (6.02, hw - 0.05, 0.55), M=M, bevel=0.02, uv=("cell", "plastic_black"), lmw=0.1)
    k.box(M_OUT, (0.4, -0.8, 0.22), (5.6, 0.8, zb), M=M, uv=("cell", "iron_black"), lmw=0.05, skip=("-z",))
    c = M @ Vector((2.95, 0, 0))
    a = math.radians(yaw)
    ext = (abs(math.cos(a)) * 3.0 + abs(math.sin(a)) * 1.02, abs(math.sin(a)) * 3.0 + abs(math.cos(a)) * 1.02)
    k.collider(c.x - ext[0], c.y - ext[1], 0.0, c.x + ext[0], c.y + ext[1], 2.06)


def jon_boat(k, x, y, z, yaw):
    """A small aluminium jon boat tied at the landing."""
    M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(yaw), 4, "Z")
    L, W, H = 3.6, 1.3, 0.42
    outline = [(-L / 2, -W / 2 + 0.05), (L / 2 - 0.4, -W / 2), (L / 2, -W / 2 + 0.15), (L / 2, W / 2 - 0.15), (L / 2 - 0.4, W / 2), (-L / 2, W / 2 - 0.05)]
    k.prism(M_OUT, outline, -0.05, H, M=M, uv=("cell", "aluminium"), bevel=0.02, lmw=0.3, caps=(True, False))
    inner = [(a * 0.96, b * 0.9) for a, b in outline]
    k.prism(M_OUT, inner[::-1], 0.03, H - 0.01, M=M, uv=("cell", "galvanized"), lmw=0.2, caps=(False, False))
    k.prism(M_OUT, inner, 0.03, 0.035, M=M, uv=("cell", "galvanized"), lmw=0.2, caps=(False, True))
    for bx in (-0.9, 0.3):
        k.box(M_OUT, (bx - 0.14, -W / 2 + 0.06, H - 0.12), (bx + 0.14, W / 2 - 0.06, H - 0.08), M=M, uv=("cell", "aluminium"), lmw=0.05)
