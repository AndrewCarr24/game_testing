"""The dining car's shell (town2_diner.py): a 60 x 16 ft (18.3 x 4.9 m) stainless car in the
manner of a 1939-52 Jerry O'Mahony / Kullman car (Road Island Diner, O'Mahony #1107; Mickey's
Dining Car, St. Paul), restored and set on a fieldstone plinth.

Outside: horizontal-fluted stainless skirt with two enamel pinstripes, a continuous ribbon of
windows between stainless mullions, a porcelain-enamel letter band, an eave visor and a low
barrel roof; the centre vestibule with its doors hooked open; granite steps and chrome rails.
Inside: terrazzo floor with a red band and brass strips under the stools, cream enamel wainscot
and stainless sills, an enamel ceiling vault with stainless ribs, the back wall's openings (the
restroom hall, the pass-through, the kitchen door).
"""
import math

import lib.common as common
import town2_diner_geo as G


def wall_boxes(axis, c0, c1, a0, a1, z0, z1, openings):
    """A wall slab minus rectangular openings, as boxes. axis "x": the wall runs along x
    (a = x), its thickness spans y c0..c1; axis "y": runs along y, thickness in x.
    openings: [(a0, a1, z0, z1)]. Returns [(lo, hi)]."""
    cuts = sorted({a0, a1, *[o[0] for o in openings], *[o[1] for o in openings]})
    cuts = [c for c in cuts if a0 <= c <= a1]
    out = []
    for i in range(len(cuts) - 1):
        s0, s1 = cuts[i], cuts[i + 1]
        if s1 - s0 < 1e-4:
            continue
        mid = (s0 + s1) / 2
        holes = sorted([(o[2], o[3]) for o in openings if o[0] < mid < o[1]])
        zs = z0
        for h0, h1 in holes + [(z1, z1)]:
            if h0 - zs > 1e-4:
                out.append((s0, s1, zs, h0))
            zs = max(zs, h1)
    res = []
    for s0, s1, za, zb in out:
        if axis == "x":
            res.append(((s0, c0, za), (s1, c1, zb)))
        else:
            res.append(((c0, s0, za), (c1, s1, zb)))
    return res


def build(k, M, p):
    C = p["car"]
    x0, x1, yf, yb, r, fz = C["x0"], C["x1"], C["yf"], C["yb"], C["r"], p["fz"]
    RED, CREAM, SS = p["red"], p["cream"], p["ss"]
    zs0, zs1 = fz - 0.10, fz + 0.84        # the fluted skirt
    zw0, zw1 = fz + 0.90, fz + 2.02         # the window band (glass)
    zb0, zb1 = fz + 2.08, fz + 2.58         # the enamel letter band
    ze = fz + 2.62                          # eave
    xi0, xi1, yi0, yi1 = x0 + 0.22, x1 - 0.22, yf + 0.22, yb - 0.22   # interior faces
    C.update(xi0=xi0, xi1=xi1, yi0=yi0, yi1=yi1, zw0=zw0, zw1=zw1, ze=ze)
    vx = p["vest_w"] / 2
    path = G.rrect_path(x0, yf, x1, yb, r, n=8, start="bw")

    # ------------------------------------------------ outside: skirt, stripes, sill, head, band
    k.add("Car_Skirt", G.path_sweep(path, G.flute_profile(zs0, zs1 - 0.2, 0.045, 0.007)), M["steel"], tile=0.5, uv_rot=True)
    # the enamel pinstripes (two) and the stainless between them, at the top of the skirt
    k.add("Car_SkirtTop", G.path_sweep(path, [(0, zs1 - 0.2), (0.004, zs1 - 0.19), (0.004, zs1 - 0.13), (0, zs1 - 0.12),
                                              (0, zs1 - 0.09), (0.004, zs1 - 0.08), (0.004, zs1 - 0.02), (0, zs1)]), M["steel"], tile=0.5, uv_rot=True)
    for za, zb in ((zs1 - 0.19, zs1 - 0.13), (zs1 - 0.08, zs1 - 0.02)):
        k.add("Car_Stripe", G.path_sweep(path, [(0.005, za), (0.006, za + 0.005), (0.006, zb - 0.005), (0.005, zb)]), M["paint"], tint=RED)
    # the sill: a rounded stainless nosing
    k.add("Car_Sill", G.path_sweep(path, [(0, zs1), (0.045, zs1 + 0.005), (0.055, zs1 + 0.02), (0.05, zw0 - 0.02),
                                          (0.02, zw0), (-0.03, zw0)]), M["steel"], tile=0.5, uv_rot=True)
    # the head and the enamel letter band with its stainless beads
    k.add("Car_Head", G.path_sweep(path, [(-0.03, zw1), (0.02, zw1), (0.03, zw1 + 0.02), (0.03, zb0)]), M["steel"], tile=0.5, uv_rot=True)
    k.add("Car_Band", G.path_sweep(path, [(0.012, zb0 + 0.03), (0.016, (zb0 + zb1) / 2), (0.012, zb1 - 0.03)]), M["paint"], tint=RED)
    for zc in (zb0 + 0.015, zb1 - 0.015):
        k.add("Car_Bead", G.path_sweep(path, [(0.0, zc - 0.016), (0.03, zc - 0.01), (0.036, zc), (0.03, zc + 0.01), (0.0, zc + 0.016)]),
              M["chrome"], tile=0.5, uv_rot=True)
    # the eave visor: a stainless drip edge round the roof
    k.add("Car_Visor", G.path_sweep(path, [(0.0, zb1), (0.12, ze - 0.03), (0.2, ze - 0.02), (0.22, ze), (0.2, ze + 0.03), (0.0, ze + 0.05)]),
          M["steel"], tile=0.5, uv_rot=True)
    # the plinth: fieldstone, inset under the skirt, with a cast stone cap
    ppath = G.rrect_path(x0 + 0.03, yf + 0.03, x1 - 0.03, yb - 0.03, r, n=6, start="bw")
    k.add("Car_Plinth", G.path_sweep(ppath, [(0.02, 0.0), (0.02, zs0 + 0.02)]), M["stone"], tile=2.0)
    k.add("Car_PlinthCap", G.path_sweep(ppath, [(0.0, zs0), (0.04, zs0 + 0.005), (0.04, zs0 + 0.03), (-0.05, zs0 + 0.03)]), M["concrete"], tile=1.0)

    # ------------------------------------------------ the window ribbon: mullions, glass, corners
    runs = []      # (start (x, y), dir (dx, dy), length, n bays, outward normal)
    runs.append(((x0 + r, yf), (1, 0), (-vx - 0.05) - (x0 + r), 8, (0, -1)))
    runs.append(((vx + 0.05, yf), (1, 0), (x1 - r) - (vx + 0.05), 8, (0, -1)))
    runs.append(((x1, yf + r), (0, 1), (yb - r) - (yf + r) - 0.0, 4, (1, 0)))
    runs.append(((x0, yb - r), (0, -1), (yb - r) - (yf + r), 4, (-1, 0)))
    mw = 0.1
    win = []       # window panes (centre, half width, dir, normal) for the lining's reveals
    for (sx, sy), (dx, dy), ln, n, (nx, ny) in runs:
        pitch = ln / n
        for i in range(n + 1):
            s = i * pitch
            cx, cy = sx + dx * s, sy + dy * s
            w = mw if 0 < i < n else mw / 2
            off = 0 if 0 < i < n else (w / 2 if i == 0 else -w / 2)
            cx, cy = cx + dx * off, cy + dy * off
            # a mullion through the wall's depth (from the skin, 2 cm proud, to the lining)
            if dx:
                (xa, xb), (ya, yb_) = (cx - w / 2, cx + w / 2), sorted((cy + ny * 0.02, cy - ny * 0.22))
            else:
                (xa, xb), (ya, yb_) = sorted((cx + nx * 0.02, cx - nx * 0.22)), (cy - w / 2, cy + w / 2)
            lo, hi = (xa, ya, zw0 - 0.01), (xb, yb_, zw1 + 0.01)
            k.add("Car_Mullion", G.box_lohi(lo, hi, bevel=0.008), M["steel"], tile=0.5)
        for i in range(n):
            s0, s1 = i * pitch + mw / 2, (i + 1) * pitch - mw / 2
            if i == 0:
                s0 = mw / 2
            if i == n - 1:
                s1 = ln - mw / 2
            a = (sx + dx * s0 - nx * 0.03, sy + dy * s0 - ny * 0.03)
            b = (sx + dx * s1 - nx * 0.03, sy + dy * s1 - ny * 0.03)
            # (a -> b along the CCW run, upward: the face points outward)
            k.add("Car_Glass", G.quad((a[0], a[1], zw0), (b[0], b[1], zw0), (b[0], b[1], zw1), (a[0], a[1], zw1)),
                  M["glass"], tile=None, bake=False)
            win.append(((sx + dx * (s0 + s1) / 2, sy + dy * (s0 + s1) / 2), (s1 - s0) / 2, (dx, dy), (nx, ny)))
    C["windows"] = win
    # the corners: curved stainless panels through the window band, inside and out
    for cx, cy, a0 in ((x0 + r, yf + r, math.pi), (x1 - r, yf + r, -math.pi / 2), (x1 - r, yb - r, 0.0), (x0 + r, yb - r, math.pi / 2)):
        arc = [(cx + r * math.cos(a0 + math.pi / 2 * t / 8), cy + r * math.sin(a0 + math.pi / 2 * t / 8)) for t in range(9)]
        k.add("Car_Corner", G.path_sweep(arc, [(0.0, zw0 - 0.02), (0.006, zw0), (0.006, zw1), (0.0, zw1 + 0.02)]), M["steel"], tile=0.5, uv_rot=True)
    # (the back run between the corners is under the annex: the skin stops at the back corners)

    # ------------------------------------------------ the barrel roof
    span0, span1 = yf - 0.12, yb + 0.12
    crown = fz + 3.12
    prof = []
    nseg = 16
    for i in range(nseg + 1):
        t = i / nseg
        y = span0 + (span1 - span0) * t
        z = ze + 0.03 + (crown - ze - 0.03) * math.sin(math.pi * t) ** 0.85
        prof.append((y, z))
    C["roof_z"] = lambda y: ze + 0.03 + (crown - ze - 0.03) * math.sin(math.pi * min(1.0, max(0.0, (y - span0) / (span1 - span0)))) ** 0.85
    rx0, rx1 = x0 + 0.05, x1 - 0.05
    bm = G.open_sweep(prof, rx1, rx0, axis="x")     # (reversed so the faces point up)
    k.add("Car_Roof", bm, M["paint"], tint=p["roof"], tile=1.0, lm=0.6)
    # roof seams (standing ribs across the barrel, every 0.9 m) and the end caps
    for i in range(1, int((rx1 - rx0) / 0.9)):
        xr = rx0 + i * (rx1 - rx0) / int((rx1 - rx0) / 0.9)
        rib = [(xr, y, z + 0.012) for y, z in prof]
        k.add("Car_RoofRib", G.tube(rib[::2] if len(rib) % 2 else rib[::2] + [rib[-1]], 0.012, n=3), M["paint"], tint=p["roof"], tile=1.0, lm=0.3)
    gable = prof + [(span1, ze), (span0, ze)]
    for xa, xb in ((rx0 - 0.03, rx0 + 0.01), (rx1 - 0.01, rx1 + 0.03)):
        k.add("Car_RoofEnd", G.sweep(gable, xa, xb, axis="x"), M["paint"], tint=RED, tile=1.0, lm=0.6)

    # ------------------------------------------------ the vestibule (centre front)
    vy0 = yf - p["vest_d"]
    k.entrances.append(dict(name="front", at=[0.0, round(vy0, 3)], facing=[0, -1], note="the vestibule's doors, hooked open"))
    vpath = [(-vx, yf), (-vx, vy0 + 0.25)] + G.arc_pts((-vx + 0.25, vy0 + 0.25, 0), 0.25, math.pi, 1.5 * math.pi, 5)[1:] \
        + G.arc_pts((vx - 0.25, vy0 + 0.25, 0), 0.25, 1.5 * math.pi, 2 * math.pi, 5) + [(vx, yf)]
    vpath = [(q[0], q[1]) for q in vpath]
    k.add("Vest_Skirt", G.path_sweep(vpath, G.flute_profile(zs0, zs1, 0.045, 0.007)), M["steel"], tile=0.5, uv_rot=True)
    zvh = fz + 2.30
    # glass-block sides and the door head: the sides are glass block (a tinted paint grid), the
    # front is the door opening (1.5 m) under a stainless head
    dw = p["door_w"] / 2
    for s in (-1, 1):
        # side panels (x = +/- vx) from the car to the rounded corner
        lo, hi = (s * vx - 0.06, vy0 + 0.25, zs1), (s * vx + 0.06, yf, zvh)
        k.add("Vest_GlassBlock", G.box_lohi(lo, hi, bevel=0.01), M["paint"], tint=(0.55, 0.62, 0.62), tile=0.2, collide=True)
        # front piers beside the doors, round the corners
        corner = G.arc_pts((s * (vx - 0.25), vy0 + 0.25, 0), 0.25, (1.5 * math.pi if s > 0 else math.pi), (2 * math.pi if s > 0 else 1.5 * math.pi), 5)
        cpts = [(q[0], q[1]) for q in corner]
        k.add("Vest_Corner", G.path_sweep(cpts, [(0.0, zs1), (0.006, zs1 + 0.02), (0.006, zvh - 0.02), (0.0, zvh)]), M["steel"], tile=0.5, uv_rot=True)
        px0, px1 = (dw, vx - 0.25) if s > 0 else (-vx + 0.25, -dw)
        k.add("Vest_Pier", G.box_lohi((px0, vy0 - 0.005, zs1), (px1, vy0 + 0.12, zvh), bevel=0.01), M["steel"], tile=0.5, collide=True)
    k.add("Vest_Head", G.box_lohi((-vx + 0.25, vy0 - 0.01, fz + 2.12), (vx - 0.25, vy0 + 0.12, zvh)), M["paint"], tint=RED, tile=0.5)
    k.add("Vest_HeadBead", G.box_lohi((-vx + 0.2, vy0 - 0.02, fz + 2.10), (vx - 0.2, vy0 + 0.02, fz + 2.13), bevel=0.008), M["chrome"], tile=0.5)
    k.add("Vest_Roof", G.prism([(q[0], q[1]) for q in G.rounded_rect(-vx - 0.12, vy0 - 0.12, vx + 0.12, yf + 0.05, 0.3, 5)], zvh, zvh + 0.12, bevel=0.02),
          M["steel"], tile=0.5, lm=0.7)
    k.add("Vest_Floor", G.box_lohi((-vx + 0.06, vy0 + 0.06, fz - 0.06), (vx - 0.06, yi0, fz)), M["checker"], tile=0.6)
    k.add("Vest_Ceiling", G.box_lohi((-vx + 0.06, vy0 + 0.12, zvh - 0.06), (vx - 0.06, yf, zvh - 0.03)), M["paint"], tint=CREAM, tile=1.0)
    k.add("Vest_Lining", G.box_lohi((-vx + 0.06, vy0 + 0.12, zs0), (-vx + 0.08, yf, zvh)), M["paint"], tint=CREAM, tile=1.0)
    k.add("Vest_Lining", G.box_lohi((vx - 0.08, vy0 + 0.12, zs0), (vx - 0.06, yf, zvh)), M["paint"], tint=CREAM, tile=1.0)
    # the doors: stainless-framed glass, hooked open flat against the vestibule's front piers
    for s in (-1, 1):
        hx = s * dw                                    # hinge at the opening's edge
        leaf = dw - 0.02
        x_a, x_b = sorted((hx, hx + s * 0.05))
        yd0, yd1 = vy0 - 0.06 - leaf, vy0 - 0.02
        # (swung 90 deg outward: the leaf stands along -y from the hinge)
        frame = [((x_a, yd0, fz + 0.02), (x_b, yd1, fz + 0.12)), ((x_a, yd0, fz + 1.98), (x_b, yd1, fz + 2.08)),
                 ((x_a, yd0, fz + 0.02), (x_b, yd0 + 0.09, fz + 2.08)), ((x_a, yd1 - 0.09, fz + 0.02), (x_b, yd1, fz + 2.08)),
                 ((x_a, yd0, fz + 0.12), (x_b, yd1, fz + 0.36))]
        for lo, hi in frame:
            k.add("Vest_Door", G.box_lohi(lo, hi, bevel=0.006), M["steel"], tile=0.5)
        k.add("Vest_DoorGlass", G.box_lohi(((x_a + x_b) / 2 - 0.004, yd0 + 0.09, fz + 0.36), ((x_a + x_b) / 2 + 0.004, yd1 - 0.09, fz + 1.98)),
              M["glass"], tile=None, bake=False)
        xp = x_a - 0.045 if s > 0 else x_b + 0.045
        k.add("Vest_DoorPull", G.tube([(xp, yd0 + 0.16, fz + 0.85), (xp, yd0 + 0.16, fz + 1.35)], 0.014, n=8), M["chrome"], tile=0.5, smooth=True)
        for zz in (fz + 0.9, fz + 1.3):
            k.add("Vest_DoorPullPost", G.tube([(xp, yd0 + 0.16, zz), ((x_a if s > 0 else x_b), yd0 + 0.16, zz)], 0.008, n=6), M["chrome"], tile=0.5)
        k.collider((x_a, yd0, fz), (x_b, yd1, fz + 2.1))
    # the threshold, the granite steps and the chrome rails
    k.add("Vest_Sill", G.box_lohi((-dw, vy0 - 0.04, fz - 0.02), (dw, vy0 + 0.08, fz + 0.005), bevel=0.005), M["chrome"], tile=0.5)
    sz = p["walk_z"]
    st = (fz - sz) / 2
    for i, (ya, yb_, top) in enumerate(((vy0 - 0.66, vy0 - 0.33, sz + st), (vy0 - 0.33, vy0 + 0.02, fz - 0.005))):
        k.add("Vest_Step", G.box_lohi((-p["step_w"] / 2, ya, 0.0), (p["step_w"] / 2, yb_, top), bevel=0.012, seg=2), M["concrete"], tint=(0.62, 0.62, 0.64), tile=1.0, collide=True)
    for s in (-1, 1):
        xr = s * (p["step_w"] / 2 - 0.06)
        rail = [(xr, vy0 - 1.05, sz), (xr, vy0 - 1.05, sz + 0.92), (xr, vy0 - 0.72, sz + 0.92), (xr, vy0 - 0.05, fz + 0.92), (xr, vy0 - 0.05, fz - 0.02)]
        k.add("Vest_Rail", G.tube(common.fillet_polyline(rail, 0.07, segments=5, closed=False), 0.022, n=10), M["chrome"], tile=0.5, smooth=True)
        k.add("Vest_RailPost", G.tube([(xr, vy0 - 0.5, sz + st), (xr, vy0 - 0.5, sz + 0.92 + (fz - sz) * 0.4)], 0.018, n=8), M["chrome"], tile=0.5, smooth=True)

    # ------------------------------------------------ colliders: floor, walls (split at the vestibule)
    k.collider((x0, yf, 0.0), (x1, yb, fz))
    k.collider((-vx, vy0, 0.0), (vx, yf, fz))
    for lo, hi in wall_boxes("x", yf - 0.02, yi0, x0, x1, 0.0, ze, [(-dw, dw, 0.0, fz + 2.1)]):
        k.collider(lo, hi)
    for xa in (x0, xi1):
        k.collider((xa, yf, 0.0), (xa + 0.22, yb, ze))
    k.collider((-vx - 0.06, vy0 + 0.25, 0), (-vx + 0.06, yf, zvh))
    k.collider((vx - 0.06, vy0 + 0.25, 0), (vx + 0.06, yf, zvh))

    # ------------------------------------------------ inside: floor
    bw = p["band"]            # the red terrazzo band under the stools (y range)
    k.add("Car_Floor", G.box_lohi((xi0, yi0, fz - 0.05), (xi1, bw[0], fz)), M["terrazzo"], tile=1.0)
    k.add("Car_Floor", G.box_lohi((xi0, bw[1], fz - 0.05), (xi1, yi1, fz)), M["terrazzo"], tile=1.0)
    k.add("Car_FloorBand", G.box_lohi((xi0, bw[0], fz - 0.05), (xi1, bw[1], fz)), M["terrazzo"], tint=(0.95, 0.42, 0.34), tile=1.0)
    for yy in bw:
        k.add("Car_FloorStrip", G.box_lohi((xi0, yy - 0.004, fz - 0.002), (xi1, yy + 0.004, fz + 0.0015)), M["chrome"], tint=p["brass"], tile=0.5, lm=0.3)
    # brass divider strips across the floor every 1.8 m, and a border inset
    for xs in [xi0 + 0.25 + 1.8 * i for i in range(int((xi1 - xi0) / 1.8) + 1)]:
        if xs < xi1 - 0.2:
            for ya, yb2 in ((yi0 + 0.25, bw[0]), (bw[1], yi1 - 0.25)):
                k.add("Car_FloorStrip", G.box_lohi((xs - 0.004, ya, fz - 0.002), (xs + 0.004, yb2, fz + 0.0015)), M["chrome"], tint=p["brass"], tile=0.5, lm=0.3)
    for ya in (yi0 + 0.25, yi1 - 0.25):
        k.add("Car_FloorStrip", G.box_lohi((xi0 + 0.25, ya - 0.004, fz - 0.002), (xi1 - 0.25, ya + 0.004, fz + 0.0015)), M["chrome"], tint=p["brass"], tile=0.5, lm=0.3)

    # ------------------------------------------------ inside: walls (front + ends), sills, bands
    # wainscot: cream enamel panels with a stainless base and a stainless cap/sill
    for (ax, c0, c1, a0, a1) in (("x", yi0 - 0.02, yi0, xi0, -vx), ("x", yi0 - 0.02, yi0, vx, xi1),
                                ("y", xi0 - 0.02, xi0, yi0, yi1), ("y", xi1, xi1 + 0.02, yi0, yi1)):
        sign_in = 1 if (ax == "x" or c1 == xi0) else -1
        for lo, hi in wall_boxes(ax, c0, c1, a0, a1, fz, zw0 - 0.02, []):
            k.add("Car_Wainscot", G.box_lohi(lo, hi), M["paint"], tint=CREAM, tile=1.0)
        # base: a 10 cm stainless kick
        if ax == "x":
            k.add("Car_Kick", G.box_lohi((a0, c1 - 0.0, fz), (a1, c1 + 0.012, fz + 0.1)), M["steel"], tile=0.5)
            k.add("Car_InSill", G.box_lohi((a0, c0 - 0.2, zw0 - 0.03), (a1, c1 + 0.04, zw0 - 0.0), bevel=0.006), M["steel"], tile=0.5)
            k.add("Car_InHead", G.box_lohi((a0, c0 - 0.2, zw1), (a1, c1 + 0.01, zw1 + 0.04)), M["steel"], tile=0.5)
            k.add("Car_InBand", G.box_lohi((a0, c0 - 0.2, zw1 + 0.04), (a1, c1, ze - 0.2)), M["paint"], tint=CREAM, tile=1.0)
        else:
            d = 1 if c1 == xi0 else -1
            xa, xb = (c1, c1 + 0.012) if d > 0 else (c0 - 0.012, c0)
            k.add("Car_Kick", G.box_lohi((xa, a0, fz), (xb, a1, fz + 0.1)), M["steel"], tile=0.5)
            sa, sb = (c0 - 0.2, c1 + 0.04) if d > 0 else (c0 - 0.04, c1 + 0.2)
            k.add("Car_InSill", G.box_lohi((sa, a0, zw0 - 0.03), (sb, a1, zw0)), M["steel"], tile=0.5)
            ha, hb = (c0 - 0.2, c1 + 0.01) if d > 0 else (c0 - 0.01, c1 + 0.2)
            k.add("Car_InHead", G.box_lohi((ha, a0, zw1), (hb, a1, zw1 + 0.04)), M["steel"], tile=0.5)
            k.add("Car_InBand", G.box_lohi((ha, a0, zw1 + 0.04), (hb, a1, ze - 0.2)), M["paint"], tint=CREAM, tile=1.0)
    # the vestibule's inner opening: cream returns
    for s in (-1, 1):
        k.add("Car_VestReturn", G.box_lohi((s * vx - 0.03, yf - 0.02, fz), (s * vx + 0.03, yi0, zw1 + 0.2)), M["steel"], tile=0.5)
    k.add("Car_VestHeadIn", G.box_lohi((-vx, yf - 0.02, fz + 2.22), (vx, yi0 + 0.01, ze - 0.2)), M["paint"], tint=CREAM, tile=1.0)

    # the back wall (dining side cream above the back-bar; its annex face is the annex's lining)
    ops = [(p["rest_door"][0], p["rest_door"][1], fz - 0.01, fz + 2.12), (p["kitchen_door"][0], p["kitchen_door"][1], fz - 0.01, fz + 2.12),
           (p["pass"][0], p["pass"][1], p["pass_z"][0], p["pass_z"][1])]
    for lo, hi in wall_boxes("x", yi1, yb, xi0, xi1, fz, ze - 0.2, ops):
        k.add("Car_BackWall", G.box_lohi(lo, hi), M["paint"], tint=CREAM, tile=1.0)
    for lo, hi in wall_boxes("x", yi1, yb, xi0, xi1, 0.0, ze, ops[:2]):
        k.collider(lo, hi)
    # stainless door casings
    for a0, a1 in (p["rest_door"], p["kitchen_door"]):
        for xa in (a0 - 0.06, a1):
            k.add("Car_Casing", G.box_lohi((xa, yi1 - 0.02, fz), (xa + 0.06, yb + 0.01, fz + 2.18)), M["steel"], tile=0.5)
        k.add("Car_Casing", G.box_lohi((a0 - 0.06, yi1 - 0.02, fz + 2.12), (a1 + 0.06, yb + 0.01, fz + 2.18)), M["steel"], tile=0.5)
        k.add("Car_DoorSill", G.box_lohi((a0, yi1, fz - 0.01), (a1, yb, fz + 0.004)), M["chrome"], tile=0.5, lm=0.3)

    # ------------------------------------------------ inside: the vaulted ceiling
    cz0, ccrown = ze - 0.2, fz + 2.98
    C["ceil_z"] = lambda y: cz0 + (ccrown - cz0) * math.sin(math.pi * min(1.0, max(0.0, (y - yi0) / (yi1 - yi0)))) ** 0.8
    prof = []
    for i in range(nseg + 1):
        t = i / nseg
        y = yi0 + (yi1 - yi0) * t
        prof.append((y, cz0 + (ccrown - cz0) * math.sin(math.pi * t) ** 0.8))
    k.add("Car_Ceiling", G.open_sweep(prof, xi0, xi1, axis="x"), M["paint"], tint=CREAM, tile=1.0)
    # stainless ribs along the vault and a cove trim at the walls
    for t in (0.0, 0.27, 0.5, 0.73, 1.0):
        y = yi0 + (yi1 - yi0) * t
        z = cz0 + (ccrown - cz0) * math.sin(math.pi * t) ** 0.8 - 0.012
        k.add("Car_CeilRib", G.box_lohi((xi0, y - 0.03, z - 0.012), (xi1, y + 0.03, z + 0.012)), M["steel"], tile=0.5, lm=0.5)
    # end walls' lunettes inside (cream) and the gable ends' cavity
    for xa, xb in ((xi0 - 0.02, xi0), (xi1, xi1 + 0.02)):
        k.add("Car_Lunette", G.sweep(prof, xa, xb, axis="x"), M["paint"], tint=CREAM, tile=1.0)
    return C
