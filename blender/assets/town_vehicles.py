"""Vehicles of the town kit (instanced, <= 1.5k triangles each). Not an asset: exported by the
thin modules town_<vehicle>.py.

A body is lofted through stations along Y: each station (y, z_sill, z_belt, z_roof, half-width
at the sill, half-width at the roof). Between the belt and the roof the side faces are glass
(dark, painted) inside the greenhouse and body colour at the pillars; the sloped roof faces at
the front and back of the greenhouse are the windscreen and the rear glass. Wheels, lights,
mirrors, bumpers. The paint is the white swatch x a tint in COLOR_0 (`tints` in the sidecar),
so one vehicle comes in several colours for free.

  car      a modern sedan (4.8 x 1.85 x 1.45)
  suv      a modern SUV (4.9 x 1.9 x 1.7)
  pickup   a full-size pickup (5.9 x 2.0 x 1.9)
  van      the invaders' van: a plain dark full-size cargo van, no markings, tinted windows
           only in the cab (5.9 x 2.1 x 2.5)
  cruiser  the sheriff's SUV: white over black, a light bar, a push bar, a star badge
           pictogram on the front doors (no lettering)
Origin: the ground centre; front -Y.
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import town_common as tc  # noqa: E402

importlib.reload(tc.tt)
importlib.reload(tc)
V = tc.V

# stations: (y, z_sill, z_belt, z_roof, half-width low, half-width high)
BODIES = {
    "car": dict(L=4.8, W=1.85, wheel_r=0.33, wheel_y=1.42, glass=(-1.16, 1.66), pillars=(0.15,), stations=[
        (-2.4, 0.32, 0.62, 0.62, 0.84, 0.78), (-2.25, 0.25, 0.78, 0.78, 0.9, 0.86), (-1.15, 0.25, 0.9, 0.93, 0.92, 0.88),
        (-0.5, 0.25, 0.93, 1.43, 0.92, 0.7), (0.9, 0.25, 0.95, 1.43, 0.92, 0.7), (1.65, 0.25, 0.97, 1.0, 0.92, 0.86),
        (2.3, 0.28, 0.95, 0.95, 0.9, 0.84), (2.4, 0.36, 0.85, 0.85, 0.84, 0.8)]),
    "suv": dict(L=4.9, W=1.9, wheel_r=0.37, wheel_y=1.45, glass=(-1.05, 2.25), pillars=(0.2, 1.4), stations=[
        (-2.45, 0.38, 0.75, 0.75, 0.88, 0.84), (-2.3, 0.32, 0.95, 0.95, 0.94, 0.9), (-1.05, 0.32, 1.05, 1.08, 0.95, 0.9),
        (-0.45, 0.32, 1.08, 1.68, 0.95, 0.78), (2.25, 0.32, 1.1, 1.66, 0.95, 0.8), (2.42, 0.38, 1.05, 1.5, 0.92, 0.82),
        (2.45, 0.45, 0.95, 1.2, 0.9, 0.85)]),
    "pickup": dict(L=5.9, W=2.0, wheel_r=0.4, wheel_y=1.85, glass=(-1.05, 0.75), pillars=(), bed=(0.85, 2.9), stations=[
        (-2.95, 0.42, 0.85, 0.85, 0.95, 0.9), (-2.8, 0.36, 1.12, 1.12, 1.0, 0.96), (-1.05, 0.36, 1.2, 1.24, 1.0, 0.95),
        (-0.45, 0.36, 1.22, 1.88, 1.0, 0.82), (0.75, 0.36, 1.24, 1.88, 1.0, 0.85), (0.85, 0.36, 1.24, 1.24, 1.0, 1.0),
        (2.9, 0.4, 1.22, 1.22, 1.0, 1.0), (2.95, 0.48, 1.15, 1.15, 0.98, 0.98)]),
    "van": dict(L=5.9, W=2.1, wheel_r=0.38, wheel_y=1.95, glass=(-1.7, -0.35), pillars=(), stations=[
        (-2.95, 0.4, 0.8, 0.8, 0.98, 0.95), (-2.75, 0.35, 1.1, 1.1, 1.03, 1.0), (-1.95, 0.35, 1.22, 1.3, 1.05, 1.0),
        (-1.3, 0.35, 1.28, 2.42, 1.05, 0.98), (2.85, 0.35, 1.28, 2.45, 1.05, 1.0), (2.95, 0.4, 1.25, 2.4, 1.03, 0.98)]),
}
BODIES["cruiser"] = dict(BODIES["suv"])


def profile(s):
    """Half cross-section of a station, bottom to top (x >= 0): sill, lower side, belt,
    roof edge (two points: the rounded shoulder), the roof centre."""
    y, z0, zb, zr, w0, w1 = s
    green = zr > zb + 0.2
    if green:
        return [(w0 * 0.9, z0), (w0, z0 + 0.14), (w0, zb), (w1, zr - 0.06), (w1 * 0.9, zr), (0.0, zr + 0.03)]
    return [(w0 * 0.9, z0), (w0, z0 + 0.14), (w0 * 0.995, zb - 0.06), (w0 * 0.97, zb - 0.01), (w0 * 0.9, zb), (0.0, zb + 0.02)]


def body(kit, spec, paint="paint_white", glass="glass_dark", lower=None, rear_glass=True):
    st = spec["stations"]
    g0, g1 = spec["glass"]
    B = kit.p("Body", paint)
    Lw = kit.p("Lower", lower) if lower else B
    G = kit.p("Glass", glass)
    prof = [profile(x) for x in st]

    def P(i, k, side):
        x, z = prof[i][k]
        return V(side * x, st[i][0], z)
    for i in range(len(st) - 1):
        a, b = st[i], st[i + 1]
        ya, yb = a[0], b[0]
        green = a[3] > a[2] + 0.2 and b[3] > b[2] + 0.2
        in_glass = g0 - 1e-3 <= ya and yb <= g1 + 1e-3
        for side in (-1, 1):
            out = V(side, 0, 0)
            for k in range(len(prof[i]) - 1):
                q = [P(i, k, side), P(i + 1, k, side), P(i + 1, k + 1, side), P(i, k + 1, side)]
                if side < 0:
                    q = q[::-1]
                nrm = V(side, 0, 0) if k < 3 else V(side * 0.5, 0, 1)
                if k == 2 and green and in_glass:            # the side glass, split at the pillars
                    cuts = [c for c in spec["pillars"] if ya < c < yb]
                    if cuts:
                        ys = [ya] + sum(([c - 0.06, c + 0.06] for c in cuts), []) + [yb]
                        for j in range(len(ys) - 1):
                            t0, t1 = (ys[j] - ya) / (yb - ya), (ys[j + 1] - ya) / (yb - ya)
                            p0, p1 = P(i, 2, side).lerp(P(i + 1, 2, side), t0), P(i, 2, side).lerp(P(i + 1, 2, side), t1)
                            r0, r1 = P(i, 3, side).lerp(P(i + 1, 3, side), t0), P(i, 3, side).lerp(P(i + 1, 3, side), t1)
                            (G if j % 2 == 0 else B).face([p0, p1, r1, r0], toward=out)
                        continue
                    G.face(q, toward=out)
                    continue
                if k == 4 and in_glass and abs(b[3] - a[3]) > 0.25 and (rear_glass or b[3] > a[3]):
                    G.face(q, toward=V(0, -1 if b[3] > a[3] else 1, 1))      # windscreen / rear glass (centre strip)
                    continue
                if k == 3 and in_glass and abs(b[3] - a[3]) > 0.25 and (rear_glass or b[3] > a[3]):
                    G.face(q, toward=nrm)
                    continue
                (Lw if k == 0 else B).face(q, toward=nrm if k else V(side, 0, -0.5))
        kit.p("Under", "rubber").face([P(i, 0, -1), P(i, 0, 1), P(i + 1, 0, 1), P(i + 1, 0, -1)], toward=(0, 0, -1))
    for i, d in ((0, -1), (len(st) - 1, 1)):                     # front and rear fascias
        ring = [P(i, k, 1) for k in range(len(prof[i]))] + [P(i, k, -1) for k in range(len(prof[i]) - 2, -1, -1)]
        B.face(ring, toward=(0, d, 0))
    return st


def arches(kit, spec, st):
    """Dark wheel-arch bands on the body sides over each wheel."""
    r, wy = spec["wheel_r"], spec["wheel_y"]
    for y in (-wy, wy):
        s = min(st, key=lambda q: abs(q[0] - y))
        for sx in (-1, 1):
            x = sx * (s[4] + 0.004)
            pts_o = [(y + (r + 0.09) * math.cos(math.pi * k / 8), r + (r + 0.09) * math.sin(math.pi * k / 8)) for k in range(9)]
            pts_i = [(y + (r + 0.02) * math.cos(math.pi * k / 8), r + (r + 0.02) * math.sin(math.pi * k / 8)) for k in range(9)]
            A = kit.p("Arches", "rubber")
            for k in range(8):
                q = [V(x, pts_i[k][0], pts_i[k][1]), V(x, pts_i[k + 1][0], pts_i[k + 1][1]), V(x, pts_o[k + 1][0], pts_o[k + 1][1]),
                     V(x, pts_o[k][0], pts_o[k][1])]
                A.face(q, toward=(sx, 0, 0))
            inner = [V(x - sx * 0.002, y + (r + 0.02) * math.cos(math.pi * k / 8), r + (r + 0.02) * math.sin(math.pi * k / 8)) for k in range(9)]
            kit.p("Arches", "shade").face(inner, toward=(sx, 0, 0))


def wheels(kit, spec, rim="metal_galv"):
    r, wy = spec["wheel_r"], spec["wheel_y"]
    hw = spec["W"] / 2 - 0.12
    for y in (-wy, wy):
        for sx in (-1, 1):
            a, b = V(sx * (hw - 0.11), y, r), V(sx * (hw + 0.11), y, r)
            kit.p("Tyres", "rubber").tube(a, b, r, sides=10)
            ring = [b + V(0, r * 0.62 * math.cos(2 * math.pi * k / 8), r * 0.62 * math.sin(2 * math.pi * k / 8)) for k in range(8)]
            kit.p("Rims", rim).face([q + V(sx * 0.005, 0, 0) for q in ring], toward=(sx, 0, 0))
            tyre = [b + V(0, r * math.cos(2 * math.pi * k / 10), r * math.sin(2 * math.pi * k / 10)) for k in range(10)]
            kit.p("Tyres", "rubber").face(tyre, toward=(sx, 0, 0))


def lights(kit, spec, st):
    f, r = st[0], st[-1]
    for sx in (-1, 1):
        x = sx * (f[4] - 0.22)
        kit.p("Headlights", "headlight").face([(x - 0.17, f[0] - 0.005, f[2] - 0.17), (x + 0.17, f[0] - 0.005, f[2] - 0.17),
                                               (x + 0.17, f[0] - 0.005, f[2] - 0.04), (x - 0.17, f[0] - 0.005, f[2] - 0.04)],
                                              toward=(0, -1, 0))
        x = sx * (r[4] - 0.15)
        kit.p("Taillights", "taillight").face([(x - 0.12, r[0] + 0.005, r[2] - 0.3), (x + 0.12, r[0] + 0.005, r[2] - 0.3),
                                               (x + 0.12, r[0] + 0.005, r[2] - 0.05), (x - 0.12, r[0] + 0.005, r[2] - 0.05)],
                                              toward=(0, 1, 0))
    kit.p("Grille", "trim_black").face([(-f[4] * 0.45, f[0] - 0.004, f[1] + 0.08), (f[4] * 0.45, f[0] - 0.004, f[1] + 0.08),
                                        (f[4] * 0.45, f[0] - 0.004, f[2] - 0.2), (-f[4] * 0.45, f[0] - 0.004, f[2] - 0.2)],
                                       toward=(0, -1, 0))
    for s, d in ((f, -1), (r, 1)):
        kit.p("Bumpers", "trim_black").box((-s[4] - 0.02, s[0] + d * 0.06 - 0.06, s[1] - 0.02), (s[4] + 0.02, s[0] + d * 0.06 + 0.06, s[1] + 0.2))
    m = next(s for s in st if s[3] > s[2] + 0.3)
    for sx in (-1, 1):
        kit.p("Mirrors", "trim_black").box((sx * (m[4] + 0.02) - 0.08, m[0] - 0.05, m[2] + 0.02), (sx * (m[4] + 0.02) + 0.08, m[0] + 0.07,
                                                                                                    m[2] + 0.18))


def build(kind, module=None, tint=(1.0, 1.0, 1.0), **overrides):
    spec = BODIES[kind]
    module = module or f"town_{kind}"
    nm = "Town" + "".join(w.capitalize() for w in module[5:].split("_"))
    col, root, kit = tc.begin(nm, module)
    kit.tints["Body"] = tint
    if kind == "cruiser":
        kit.tints["Body"] = (1, 1, 1)
        st = body(kit, spec, paint="car_white", lower="car_black")
    elif kind == "van":
        st = body(kit, spec, paint="paint_white", rear_glass=False)
    else:
        st = body(kit, spec)
    wheels(kit, spec)
    arches(kit, spec, st)
    lights(kit, spec, st)
    if kind == "pickup":                                           # the open bed: walls, liner, tailgate line
        b0, b1 = spec["bed"]
        hw = spec["W"] / 2 - 0.06
        kit.p("Bed", "tar").face([(-hw + 0.06, b0, 0.78), (hw - 0.06, b0, 0.78), (hw - 0.06, b1 - 0.05, 0.78), (-hw + 0.06, b1 - 0.05, 0.78)],
                                 toward=(0, 0, 1))
        for sx in (-1, 1):
            kit.p("Bed", "tar").face([(sx * (hw - 0.06), b0, 0.78), (sx * (hw - 0.06), b1 - 0.05, 0.78), (sx * (hw - 0.06), b1 - 0.05, 1.22),
                                      (sx * (hw - 0.06), b0, 1.22)], toward=(-sx, 0, 0))
        kit.p("Bed", "tar").face([(-hw, b0 + 0.02, 0.78), (hw, b0 + 0.02, 0.78), (hw, b0 + 0.02, 1.23), (-hw, b0 + 0.02, 1.23)], toward=(0, 1, 0))
        kit.p("Bed", "tar").face([(-hw, b1 - 0.07, 0.78), (hw, b1 - 0.07, 0.78), (hw, b1 - 0.07, 1.2), (-hw, b1 - 0.07, 1.2)], toward=(0, -1, 0))
        # (the loft's top over the bed is the bed rail: hide it under the liner by dropping it)
    if kind == "cruiser":
        roof = max(st, key=lambda s: s[3])
        lb = kit.p("LightBar", "trim_black")
        lb.box((-0.62, -0.2, roof[3] + 0.02), (0.62, 0.05, roof[3] + 0.06))
        kit.p("LightBar", "neon_red").box((-0.6, -0.18, roof[3] + 0.06), (-0.05, 0.03, roof[3] + 0.16))
        kit.p("LightBar", "neon_blue").box((0.05, -0.18, roof[3] + 0.06), (0.6, 0.03, roof[3] + 0.16))
        f = st[0]
        pb = kit.p("PushBar", "trim_black")
        for sx in (-0.45, 0.45):
            pb.box((sx - 0.04, f[0] - 0.22, f[1]), (sx + 0.04, f[0] - 0.14, f[2] + 0.05))
        pb.box((-0.55, f[0] - 0.22, f[2] - 0.05), (0.55, f[0] - 0.14, f[2] + 0.05))
        for sx in (-1, 1):                                          # the star badge on the front doors
            x = sx * (spec["stations"][2][4] + 0.004)
            q = [(x, -0.3, 0.55), (x, 0.4, 0.55), (x, 0.4, 0.9), (x, -0.3, 0.9)]
            uv = tc.sign_uv("sheriff")
            uvs = [uv[0], uv[1], uv[2], uv[3]] if sx > 0 else [uv[1], uv[0], uv[3], uv[2]]
            kit.p("Badge", "signs").face(q if sx > 0 else [q[1], q[0], q[3], q[2]], uvs=uvs if sx > 0 else uvs, toward=(sx, 0, 0))
    if kind == "van":                                               # sliding-door seam, rear door seam, no markings
        for sx in (-1, 1):
            x = sx * 1.052
            kit.p("Seams", "trim_black").face([(x, 0.0, 0.45), (x, 0.03, 0.45), (x, 0.03, 2.2), (x, 0.0, 2.2)], toward=(sx, 0, 0))
        kit.p("Seams", "trim_black").face([(-0.01, 2.952, 0.5), (0.01, 2.952, 0.5), (0.01, 2.952, 2.3), (-0.01, 2.952, 2.3)], toward=(0, 1, 0))
        kit.p("RearGlass", "glass_dark").face([(-0.9, 2.953, 1.5), (-0.1, 2.953, 1.5), (-0.1, 2.953, 2.1), (-0.9, 2.953, 2.1)], toward=(0, 1, 0))
        kit.p("RearGlass", "glass_dark").face([(0.1, 2.953, 1.5), (0.9, 2.953, 1.5), (0.9, 2.953, 2.1), (0.1, 2.953, 2.1)], toward=(0, 1, 0))
    L, W = spec["L"], spec["W"]
    top = max(s[3] for s in st)
    kit.collide((-W / 2, -L / 2, 0), (W / 2, L / 2, top))
    far = tc.Far(nm)
    far.box((-W / 2 + 0.05, -L / 2, 0.15), (W / 2 - 0.05, L / 2, max(s[2] for s in st)), "car_silver", skip="b")
    gl = [s for s in st if s[3] > s[2] + 0.2]
    if gl:
        far.box((-gl[0][5], gl[0][0], max(s[2] for s in st)), (gl[0][5], gl[-1][0], top), "glass_dark", skip="b")
    kit.info.update(walk_in=False, vehicle=kind, footprint=[-W / 2, -L / 2, W / 2, L / 2])
    parts = tc.finish(kit, col, root, far)
    return root, parts
