"""The cars on the diner's lot (town2_diner.py), lofted bodies ~2-3k triangles each, baked with the
building (they shadow the asphalt and the walk):
  wagon    a muted blue-grey all-wheel-drive wagon in a front stall, a kayak on its roof bars
           (a rafting town)
  pickup   the cook's crew-cab pickup, faded green, by the east side door
  van      a plain charcoal full-size cargo van, no markings, glass only in the cab, parked behind
           the annex where the highway can't see it (the invaders')

A body is lofted along its length through stations (s, sill, belt, top, half-width, roof
half-width, cabin): each section runs from the sill up the flank to the belt, then (in the
cabin) in to the roof, mirrored. The greenhouse's side faces between the belt and the roof are
glass except at the pillars; the windscreen and rear glass are the slanted top faces at the
cabin's ends.
"""
import math

import bmesh

import town2_diner_geo as G

BODIES = {
    # length 4.75: s, sill, belt, top, half width, roof half width, cabin
    "wagon": dict(wheel_r=0.33, axles=(-1.42, 1.3), track=0.79, stations=[
        (-2.37, 0.34, 0.62, 0.66, 0.78, 0.7, 0), (-2.25, 0.3, 0.78, 0.8, 0.86, 0.8, 0), (-1.7, 0.28, 0.86, 0.9, 0.9, 0.84, 0),
        (-0.95, 0.28, 0.92, 0.98, 0.91, 0.8, 0), (-0.55, 0.28, 0.94, 1.42, 0.91, 0.7, 1), (0.6, 0.28, 0.95, 1.48, 0.91, 0.72, 1),
        (1.85, 0.28, 0.96, 1.46, 0.9, 0.72, 1), (2.25, 0.3, 0.96, 1.3, 0.88, 0.7, 1), (2.38, 0.36, 0.9, 1.0, 0.84, 0.68, 0)],
        pillars=(-0.5, 0.65, 1.3, 2.2)),
    "pickup": dict(wheel_r=0.4, axles=(-1.75, 1.85), track=0.86, stations=[
        (-2.9, 0.45, 0.85, 0.9, 0.9, 0.85, 0), (-2.75, 0.42, 1.08, 1.1, 0.98, 0.95, 0), (-1.5, 0.42, 1.15, 1.2, 1.0, 0.96, 0),
        (-1.0, 0.42, 1.17, 1.25, 1.0, 0.95, 0), (-0.55, 0.42, 1.18, 1.85, 1.0, 0.8, 1), (0.9, 0.42, 1.2, 1.88, 1.0, 0.82, 1),
        (1.05, 0.42, 1.2, 1.3, 1.0, 0.95, 0), (2.85, 0.45, 1.2, 1.25, 1.0, 0.96, 0), (2.95, 0.5, 1.1, 1.15, 0.98, 0.95, 0)],
        pillars=(-0.5, 0.15, 0.85), bed=(1.1, 2.9)),
    "van": dict(wheel_r=0.38, axles=(-1.85, 1.6), track=0.86, stations=[
        (-2.95, 0.45, 0.85, 0.95, 0.94, 0.9, 0), (-2.8, 0.4, 1.05, 1.15, 1.02, 0.96, 0), (-2.2, 0.4, 1.12, 1.3, 1.04, 1.0, 0),
        (-1.65, 0.4, 1.15, 2.2, 1.04, 0.96, 1), (-0.6, 0.4, 1.15, 2.45, 1.04, 0.98, 1), (2.85, 0.4, 1.15, 2.45, 1.04, 0.98, 1),
        (2.95, 0.45, 1.1, 2.4, 1.0, 0.95, 1)],
        pillars=(-0.65,), cargo=True),
}


def build(k, M, p):
    cars = p.get("cars", [])
    for kind, x, y, yaw, colour in cars:
        car(k, M, p, kind, x, y, yaw, colour)


def car(k, M, p, kind, x, y, yaw, colour):
    B = BODIES[kind]
    lz = p["lot_z"]
    st = B["stations"]
    # (the stations run along the car's local x; front = -x; it is placed with yaw about z)
    def sec(s):
        sx, zs, zb, zt, w, wr, cab = s
        pts = [(0.0, zs - 0.02), (w * 0.9, zs), (w, zs + 0.12), (w, zb - 0.06), (w * 0.985, zb)]
        if cab:
            pts += [(wr + (w - wr) * 0.1, zb + 0.04), (wr, zt - 0.06), (wr * 0.85, zt), (0.0, zt + 0.02)]
        else:
            pts += [(w * 0.95, zb + 0.015), (w * 0.88, zt - 0.01), (w * 0.6, zt), (0.0, zt + 0.005)]
        return [(sx, a, b) for a, b in pts]
    secs = [sec(s) for s in st]
    body, glass = bmesh.new(), bmesh.new()
    n = len(secs[0])

    def full(sc):        # mirrored: right side (-y) bottom to top, then the left (+y) top to bottom
        right = [(px, -py, pz) for px, py, pz in sc]
        left = [(px, py, pz) for px, py, pz in sc[::-1]][1:-1]
        return right + left
    rings = [full(sc) for sc in secs]
    m = len(rings[0])
    pil = B["pillars"]
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        cab = st[i][6] and st[i + 1][6]
        for j in range(m):
            jn = (j + 1) % m
            quad = [a[j], b[j], b[jn], a[jn]]
            # greenhouse side faces: index 5..6 on the right (belt+ -> roof), mirrored on the left
            side = j in (5, 6) or j in (m - 7, m - 6)
            xs = (st[i][0] + st[i + 1][0]) / 2
            is_glass = cab and side and j in (5, m - 7) and not any(abs(xs - q) < 0.07 for q in pil)
            if B.get("cargo") and xs > -0.6:
                is_glass = False
            dst = glass if is_glass else body
            vs = [dst.verts.new(q) for q in quad]
            dst.faces.new(vs)
    # end caps (nose and tail)
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        vs = [body.verts.new(q) for q in ring]
        try:
            body.faces.new(vs[::-1] if rev else vs)
        except ValueError:
            pass
    # windscreen and rear glass: the cabin's first and last top faces (front glass slab)
    ci = [i for i, s in enumerate(st) if s[6]]
    if ci and not B.get("cargo"):
        pass
    bmesh.ops.remove_doubles(body, verts=body.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(body, faces=body.faces[:])
    mat = place_matrix(x, y, yaw, lz)
    for bm_ in (body, glass):
        bmesh.ops.transform(bm_, matrix=mat, verts=bm_.verts)
    k.add(f"Car_{kind}_Body", body, M["paint"], tint=colour, tile=1.0, smooth=40, lm=0.5, zone="out")
    if glass.faces:
        bmesh.ops.recalc_face_normals(glass, faces=glass.faces[:])
        k.add(f"Car_{kind}_Glass", glass, M["paint"], tint=(0.012, 0.014, 0.016), tile=1.0, lm=0.4, zone="out")
    else:
        glass.free()
    # the windscreen: a dark panel on the slanted face at the cabin's front
    if ci:
        i0 = ci[0]
        s0, s1 = st[i0 - 1], st[i0]
        wr = s1[5] * 0.92
        ws = G.quad((s0[0] + 0.05, -s0[4] * 0.88, s0[2] + 0.06), (s0[0] + 0.05, s0[4] * 0.88, s0[2] + 0.06), (s1[0] + 0.02, wr, s1[3] - 0.07), (s1[0] + 0.02, -wr, s1[3] - 0.07))
        bmesh.ops.transform(ws, matrix=mat, verts=ws.verts)
        k.add(f"Car_{kind}_Screen", ws, M["paint"], tint=(0.015, 0.017, 0.02), tile=1.0, lm=0.3, zone="out")
    # wheels: tyre, rim, a dark arch liner on the flank
    r = B["wheel_r"]
    for ax in B["axles"]:
        for sgn in (-1, 1):
            wy = sgn * (B["track"])
            tyre = G.lathe([(r * 0.62, -0.11), (r * 0.95, -0.12), (r, -0.08), (r, 0.08), (r * 0.95, 0.12), (r * 0.62, 0.11)], c=(0, 0, 0), n=16)
            G.xform(tyre, rx=math.pi / 2)
            G.xform(tyre, loc=(ax, wy, r))
            bmesh.ops.transform(tyre, matrix=mat, verts=tyre.verts)
            k.add(f"Car_{kind}_Tyre", tyre, M["paint"], tint=(0.018, 0.018, 0.02), tile=1.0, smooth=40, lm=0.3, zone="out")
            rim = G.cyl((ax, wy + sgn * 0.1, r), r * 0.62, 0.02, n=14, axis="y")
            bmesh.ops.transform(rim, matrix=mat, verts=rim.verts)
            k.add(f"Car_{kind}_Rim", rim, M["steel"], tile=0.5, lm=0.3, zone="out")
            hub = G.cyl((ax, wy + sgn * 0.115, r), r * 0.2, 0.02, n=8, axis="y")
            bmesh.ops.transform(hub, matrix=mat, verts=hub.verts)
            k.add(f"Car_{kind}_Hub", hub, M["paint"], tint=(0.05, 0.05, 0.05), tile=1.0, lm=0.2, zone="out")
    # lamps: head (pale) and tail (red) blocks at the ends, bumpers, mirrors, handles
    s0, s1 = st[0], st[-1]
    for sgn in (-1, 1):
        for bm_, tint in ((G.box_lohi((s0[0] - 0.01, sgn * s0[4] * 0.62 - 0.14, s0[2] - 0.1), (s0[0] + 0.12, sgn * s0[4] * 0.62 + 0.14, s0[2] - 0.02)), (0.7, 0.7, 0.66)),
                          (G.box_lohi((s1[0] - 0.12, sgn * s1[4] * 0.8 - 0.1, s1[2] - 0.2), (s1[0] + 0.01, sgn * s1[4] * 0.8 + 0.1, s1[2] - 0.04)), (0.4, 0.02, 0.02))):
            bmesh.ops.transform(bm_, matrix=mat, verts=bm_.verts)
            k.add(f"Car_{kind}_Lamp", bm_, M["paint"], tint=tint, tile=1.0, lm=0.3, zone="out")
        mir = G.box_lohi((st[2][0] + 0.6 if not B.get("cargo") else -1.6, sgn * (st[3][4] + 0.12) - 0.07, st[3][2] + 0.02), ((st[2][0] + 0.75) if not B.get("cargo") else -1.45, sgn * (st[3][4] + 0.12) + 0.07, st[3][2] + 0.17), bevel=0.02)
        bmesh.ops.transform(mir, matrix=mat, verts=mir.verts)
        k.add(f"Car_{kind}_Mirror", mir, M["paint"], tint=colour, tile=1.0, lm=0.3, zone="out")
    for s_, sgn in ((s0, -1), (s1, 1)):
        bump = G.box_lohi((s_[0] - 0.06 * -sgn - (0.06 if sgn < 0 else 0), -s_[4] * 0.95, s_[1] - 0.05), (s_[0] + (0.06 if sgn > 0 else 0.0) + (0.0 if sgn > 0 else 0.06), s_[4] * 0.95, s_[1] + 0.16), bevel=0.03)
        bmesh.ops.transform(bump, matrix=mat, verts=bump.verts)
        k.add(f"Car_{kind}_Bumper", bump, M["paint"], tint=(0.03, 0.03, 0.033), tile=1.0, lm=0.3, zone="out")
    # extras: the pickup's bed (an open box), the wagon's roof bars and kayak
    if "bed" in B:
        # the open bed, seen from above: a black liner sunk into the body's top between the bed
        # rails, the tailgate's top edge, a toolbox across the front of the bed
        b0, b1 = B["bed"]
        w = st[-2][4] - 0.09
        zt = st[-2][3] + 0.006
        for bm_, tint in ((G.box_lohi((b0 + 0.08, -w, zt - 0.01), (b1 - 0.08, w, zt)), (0.012, 0.012, 0.013)),
                          (G.box_lohi((b0 + 0.1, -w + 0.02, zt), (b0 + 0.42, w - 0.02, zt + 0.22), bevel=0.02), (0.55, 0.56, 0.57))):
            bmesh.ops.transform(bm_, matrix=mat, verts=bm_.verts)
            k.add(f"Car_{kind}_Bed", bm_, M["paint"], tint=tint, tile=1.0, lm=0.3, zone="out")
    if kind == "wagon":
        zr = st[5][3] + 0.04
        for bx in (-0.3, 1.2):
            bar = G.box_lohi((bx - 0.03, -0.72, zr), (bx + 0.03, 0.72, zr + 0.05))
            bmesh.ops.transform(bar, matrix=mat, verts=bar.verts)
            k.add("Car_wagon_Bar", bar, M["paint"], tint=(0.02, 0.02, 0.02), tile=1.0, lm=0.3, zone="out")
        prof = [(-1.9, 0.0), (-1.5, 0.11), (0.0, 0.17), (1.5, 0.12), (2.0, 0.0)]
        kay = bmesh.new()
        ringsk = []
        for sx_, hw in prof:
            ringsk.append([kay.verts.new((sx_ + 0.45, hw * math.cos(a) * 1.0, zr + 0.18 + hw * 0.7 * math.sin(a))) for a in [2 * math.pi * t / 8 for t in range(8)]])
        for i in range(len(ringsk) - 1):
            for j in range(8):
                kay.faces.new([ringsk[i][j], ringsk[i][(j + 1) % 8], ringsk[i + 1][(j + 1) % 8], ringsk[i + 1][j]])
        bmesh.ops.remove_doubles(kay, verts=kay.verts, dist=1e-4)
        bmesh.ops.transform(kay, matrix=mat, verts=kay.verts)
        k.add("Car_wagon_Kayak", kay, M["paint"], tint=(0.75, 0.32, 0.04), tile=1.0, smooth=50, lm=0.4, zone="out")
    # a collider: the body's box
    L0, L1 = st[0][0], st[-1][0]
    W_ = max(s[4] for s in st)
    zt = max(s[3] for s in st)
    corners = [(L0, -W_), (L1, -W_), (L1, W_), (L0, W_)]
    pts = [mat @ __import__("mathutils").Vector((cx, cy, 0)) for cx, cy in corners]
    k.collider((min(q.x for q in pts), min(q.y for q in pts), 0.0), (max(q.x for q in pts), max(q.y for q in pts), lz + zt))


def place_matrix(x, y, yaw, z):
    from mathutils import Matrix
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(yaw), 4, "Z")
