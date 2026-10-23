"""The dining room's fixtures (town2_diner.py), the way a 16 ft car is laid out (O'Mahony's plan:
booths down the window side, the counter and its stools in the middle, the back-bar along the
back wall with the pass-through to the kitchen):
  booths     eight high-backed booths in channel-tufted red vinyl, cracked-ice laminate tables
             with ribbed aluminium edges, a chrome wall box (selector) on every table
  counter    the long counter (rounded ends, laminate top, fluted stainless apron, chrome foot
             rail) and sixteen chrome pedestal stools with red seats
  back-bar   stainless cabinets, sunburst stainless backsplash, the mug shelf, menu letterboards,
             coffee urns, a malt mixer, the revolving pie case, the toaster; the pass-through with
             its heat lamps and ticket rail; the clock
  pies       cake stands with glass domes on the counter
  stations   the coffee station at the east end (brewers, an espresso machine), the register
  jukebox    against the west end (arched, bubble tubes in neon), the bulletin board
  lights     opal-globe pendants over the counter and every booth (and their bake lights)
"""
import math

import bmesh

import lib.common as common
import town2_diner_geo as G


def build(k, M, p):
    C = p["car"]
    fz = p["fz"]
    xi0, xi1, yi0, yi1 = C["xi0"], C["xi1"], C["yi0"], C["yi1"]
    RED, CREAM, VINYL, BLACK = p["red"], p["cream"], p["vinyl"], p["black"]
    ceil = C["ceil_z"]
    vx = p["vest_w"] / 2
    L = dict(booth_y1=1.95, stool_y=2.97, top=(3.18, 3.98), body=(3.42, 3.98), cx=5.85, bar_y=4.62)
    p["fit"] = L

    # ================================================= booths
    unit = 1.86
    starts = [(-8.83, 4), (vx + 0.29, 4)]
    tables = []
    for x0, n in starts:
        bounds = [x0 + i * unit for i in range(n + 1)]
        for i, px in enumerate(bounds):
            sides = [s for s, ok in ((1, i < n), (-1, i > 0)) if ok]
            partition(k, M, p, px, yi0, L["booth_y1"], sides, VINYL)
        for i in range(n):
            ux = x0 + i * unit
            tables.append(table(k, M, p, ux + 0.58, ux + 1.28, yi0, L["booth_y1"] - 0.15))
            for side, bx in ((1, ux + 0.05), (-1, ux + unit - 0.05)):
                seat(k, M, p, bx, side, yi0, L["booth_y1"], VINYL)
    p["tables"] = tables
    for tx, ty in tables:
        wall_box(k, M, p, tx, yi0 + 0.08, fz + 0.765)

    # ================================================= the counter and stools
    t0, t1 = L["top"]
    b0, b1 = L["body"]
    cx = L["cx"]
    zt = fz + 0.98
    top = G.rounded_rect(-cx, t0, cx, t1, 0.38, 8)
    k.add("Counter_Top", G.prism(top, zt - 0.04, zt), M["laminate"], tile=0.6)
    # the ribbed aluminium edge band round the top (the back edge too)
    edge = [(x, y) for x, y in top] + [top[0]]
    k.add("Counter_Edge", G.path_sweep(edge, [(0.0, zt - 0.045), (0.006, zt - 0.04), (0.006, zt - 0.03), (0.002, zt - 0.027), (0.006, zt - 0.023),
                                              (0.006, zt - 0.013), (0.002, zt - 0.01), (0.006, zt - 0.006), (0.006, zt + 0.002), (0.0, zt + 0.004)], closed=True),
          M["chrome"], tile=0.5, uv_rot=True)
    # the apron: fluted stainless on the stool side and round the ends (an open path), a black kick
    front = [q for q in G.rrect_path(-cx + 0.15, b0, cx - 0.15, b1, 0.3, n=8, start="bw")]
    k.add("Counter_Apron", G.path_sweep(front, G.flute_profile(fz + 0.16, zt - 0.06, 0.05, 0.006)), M["steel"], tile=0.5, uv_rot=True)
    k.add("Counter_ApronCap", G.path_sweep(front, [(-0.02, zt - 0.06), (0.012, zt - 0.055), (0.012, zt - 0.045), (-0.02, zt - 0.045)]), M["chrome"], tile=0.5)
    k.add("Counter_Kick", G.path_sweep(front, [(-0.06, fz), (-0.06, fz + 0.16)]), M["paint"], tint=BLACK, tile=1.0)
    k.add("Counter_KickTop", G.path_sweep(front, [(-0.06, fz + 0.16), (0.0, fz + 0.16)]), M["paint"], tint=BLACK, tile=1.0)
    k.collider((-cx, t0, fz), (cx, t1, zt))
    # the foot rail on brackets
    ry = b0 - 0.14
    k.add("Counter_FootRail", G.tube([(-cx + 0.5, ry, fz + 0.2), (cx - 0.5, ry, fz + 0.2)], 0.02, n=10), M["chrome"], tile=0.5, smooth=True)
    for xr in [-cx + 0.6 + i * (2 * cx - 1.2) / 6 for i in range(7)]:
        k.add("Counter_RailBracket", G.tube([(xr, ry, fz + 0.2), (xr, b0, fz + 0.24)], 0.012, n=6), M["chrome"], tile=0.5)
    # the counter's back (the work side): stainless doors and open shelves under the top
    k.add("Counter_Back", G.box_lohi((-cx + 0.25, b1 - 0.02, fz + 0.12), (cx - 0.25, b1, zt - 0.06)), M["steel"], tile=0.5)
    k.add("Counter_Shelf", G.box_lohi((-cx + 0.3, b1, fz + 0.45), (cx - 0.3, t1 - 0.04, fz + 0.47)), M["steel"], tile=0.5)
    k.add("Counter_Shelf", G.box_lohi((-cx + 0.3, b1, fz + 0.12), (cx - 0.3, t1 - 0.04, fz + 0.14)), M["steel"], tile=0.5)
    # stools: chrome pedestal, flared foot, red seat with a chrome band
    n = 16
    sx0, sx1 = -cx + 0.6, cx - 0.6
    p["stools"] = []
    for i in range(n):
        x = sx0 + i * (sx1 - sx0) / (n - 1)
        stool(k, M, p, x, L["stool_y"], VINYL)
        p["stools"].append((x, L["stool_y"]))

    # ================================================= the back-bar
    by0, by1 = L["bar_y"], yi1
    xa, xb = p["rest_door"][1] + 1.45, p["kitchen_door"][0] - 0.25     # (the bulletin board's wall, the kitchen door)
    pa, pb = p["pass"]
    zw = fz + 0.88
    for (x0b, x1b) in ((xa, pa - 0.05), (pb + 0.05, xb)):
        k.add("Bar_Base", G.box_lohi((x0b, by0 + 0.06, fz), (x1b, by1, fz + 0.1)), M["paint"], tint=BLACK, tile=1.0)
        # cabinet doors (proud panels) and handles
        nd = max(1, int(round((x1b - x0b) / 0.6)))
        for j in range(nd):
            d0 = x0b + j * (x1b - x0b) / nd + 0.01
            d1 = x0b + (j + 1) * (x1b - x0b) / nd - 0.01
            k.add("Bar_Door", G.box_lohi((d0, by0, fz + 0.11), (d1, by0 + 0.03, zw - 0.02), bevel=0.004), M["steel"], tile=0.5)
            k.add("Bar_Handle", G.box_lohi((d0 + 0.06, by0 - 0.025, zw - 0.12), (d1 - 0.06, by0 - 0.01, zw - 0.1), bevel=0.004), M["chrome"], tile=0.5)
        k.add("Bar_Carcass", G.box_lohi((x0b, by0 + 0.03, fz + 0.1), (x1b, by1, zw)), M["steel"], tile=0.5)
        k.add("Bar_Top", G.box_lohi((x0b - 0.02, by0 - 0.04, zw), (x1b + 0.02, by1, zw + 0.035), bevel=0.006), M["steel"], tile=0.5)
        k.collider((x0b, by0 - 0.04, fz), (x1b, by1, zw + 0.035))
        # backsplash: stainless sunburst panels between chrome battens
        npan = max(1, int(round((x1b - x0b) / 0.95)))
        for j in range(npan):
            q0 = x0b + j * (x1b - x0b) / npan
            q1 = x0b + (j + 1) * (x1b - x0b) / npan
            sunburst(k, M, (q0 + 0.02, q1 - 0.02), by1, zw + 0.04, fz + 1.8)
            k.add("Bar_Batten", G.box_lohi((q0 - 0.015, by1 - 0.018, zw + 0.035), (q0 + 0.015, by1, fz + 1.82)), M["chrome"], tile=0.5)
        k.add("Bar_Batten", G.box_lohi((x1b - 0.015, by1 - 0.018, zw + 0.035), (x1b + 0.015, by1, fz + 1.82)), M["chrome"], tile=0.5)
        # the mug shelf with its under-light, the menu boards above
        k.add("Bar_Shelf", G.box_lohi((x0b, by1 - 0.24, fz + 1.8), (x1b, by1, fz + 1.835), bevel=0.005), M["steel"], tile=0.5)
        k.add("Bar_ShelfLight", G.box_lohi((x0b + 0.05, by1 - 0.2, fz + 1.794), (x1b - 0.05, by1 - 0.17, fz + 1.8)), M["globe"], tile=None, bake=False)
        k.light(kind="area", loc=((x0b + x1b) / 2, by1 - 0.19, fz + 1.78), size=(x1b - x0b - 0.1, 0.03), power=16.0 * (x1b - x0b), color=(1.0, 0.86, 0.66), dir=(0, 0, -1))
        for j in range(int((x1b - x0b) / 0.16)):
            mx = x0b + 0.1 + j * 0.16
            mug(k, M, p, mx, by1 - 0.12, fz + 1.835, tint=(0.75, 0.72, 0.64) if j % 7 else (0.42, 0.06, 0.04))
        # letterboards: black, framed in chrome, over the shelf
        mb0, mb1 = fz + 1.94, ceil(by1) - 0.05
        k.add("Bar_MenuFrame", G.box_lohi((x0b + 0.05, by1 - 0.04, mb0 - 0.03), (x1b - 0.05, by1, mb1 + 0.03), bevel=0.006), M["chrome"], tile=0.5)
        nb = max(1, int(round((x1b - x0b) / 1.4)))
        for j in range(nb):
            q0 = x0b + 0.08 + j * (x1b - x0b - 0.16) / nb
            q1 = x0b + 0.08 + (j + 1) * (x1b - x0b - 0.16) / nb - 0.04
            y = by1 - 0.042
            k.add("Bar_Menu", G.decal((q0, y, mb0), (q1, y, mb0), (q1, y, mb1), (q0, y, mb1), "menu"), M["decal"], tile=None)
    # under the pass: low cabinets and the pass sill (stainless, through the wall)
    k.add("Bar_PassBase", G.box_lohi((pa - 0.05, by0 + 0.03, fz), (pb + 0.05, by1, zw)), M["steel"], tile=0.5)
    k.add("Bar_PassTop", G.box_lohi((pa - 0.07, by0 - 0.04, zw), (pb + 0.07, by1, zw + 0.035), bevel=0.006), M["steel"], tile=0.5)
    k.collider((pa - 0.07, by0 - 0.04, fz), (pb + 0.07, by1, zw + 0.035))
    z0p, z1p = p["pass_z"]
    k.add("Pass_Sill", G.box_lohi((pa, by1 - 0.12, z0p - 0.03), (pb, p["car"]["yb"] + 0.5, z0p), bevel=0.006), M["steel"], tile=0.5)
    k.add("Pass_Jamb", G.box_lohi((pa - 0.05, by1 - 0.04, z0p - 0.03), (pa, p["car"]["yb"] + 0.02, z1p + 0.04)), M["steel"], tile=0.5)
    k.add("Pass_Jamb", G.box_lohi((pb, by1 - 0.04, z0p - 0.03), (pb + 0.05, p["car"]["yb"] + 0.02, z1p + 0.04)), M["steel"], tile=0.5)
    k.add("Pass_Head", G.box_lohi((pa - 0.05, by1 - 0.04, z1p), (pb + 0.05, p["car"]["yb"] + 0.02, z1p + 0.05)), M["steel"], tile=0.5)
    # the ticket rail (a chrome channel with blank order tickets) and the heat-lamp bar (kitchen side)
    k.add("Pass_TicketRail", G.box_lohi((pa + 0.05, by1 - 0.02, z1p - 0.06), (pb - 0.05, by1 + 0.02, z1p - 0.03)), M["chrome"], tile=0.5)
    for j, tx in enumerate((pa + 0.3, pa + 0.62, pa + 0.85, pb - 0.75, pb - 0.4)):
        y = by1 - 0.025
        k.add("Pass_Ticket", G.decal((tx, y, z1p - 0.2), (tx + 0.08, y, z1p - 0.2), (tx + 0.08, y, z1p - 0.05), (tx, y, z1p - 0.05), "ticket"), M["decal"], tile=None)
    yk = p["car"]["yb"] + 0.3
    k.add("Pass_HeatLamp", G.box_lohi((pa + 0.05, yk - 0.08, z1p - 0.14), (pb - 0.05, yk + 0.08, z1p - 0.06), bevel=0.01), M["steel"], tile=0.5)
    k.add("Pass_HeatGlow", G.box_lohi((pa + 0.1, yk - 0.05, z1p - 0.145), (pb - 0.1, yk + 0.05, z1p - 0.14)), M["neon_red"], tile=None, bake=False)
    k.light(kind="area", loc=(0.0, yk, z1p - 0.16), size=(pb - pa - 0.2, 0.1), power=35.0, color=(1.0, 0.45, 0.2), dir=(0, 0, -1))
    # the clock over the pass
    k.add("Bar_ClockRim", G.cyl((0.0, by1 - 0.03, fz + 2.17), 0.19, 0.05, n=24, axis="y", bevel=0.01), M["chrome"], tile=0.5, smooth=True)
    k.add("Bar_Clock", G.decal_disc((0.0, by1 - 0.056, fz + 2.17), 0.165, "clock", n=24, axis="y"), M["decal"], tile=None)

    # equipment on the back-bar
    urn(k, M, p, 3.05, by1 - 0.3, zw + 0.035)
    urn(k, M, p, 3.65, by1 - 0.3, zw + 0.035)
    mixer(k, M, p, 4.5, by1 - 0.28, zw + 0.035)
    pie_case(k, M, p, -4.7, by1 - 0.3, zw + 0.035)
    toaster(k, M, p, -3.0, by1 - 0.3, zw + 0.035)
    toaster(k, M, p, -2.55, by1 - 0.3, zw + 0.035)
    for j in range(3):
        plates(k, M, p, 2.0 + 0.32 * j, by1 - 0.3, zw + 0.035, 8 + 3 * j)
    glass_rack(k, M, p, 5.6, by1 - 0.3, zw + 0.035)
    glass_rack(k, M, p, -6.0, by1 - 0.3, zw + 0.035)

    # ================================================= pies under glass on the counter
    for x, kind in ((-3.7, "pie0"), (-1.7, "pie1"), (1.9, "pie2"), (4.1, "cake")):
        cake_stand(k, M, p, x, 3.78, zt, kind)

    # ================================================= the register and the coffee station
    register(k, M, p, cx - 0.35, 3.62, zt)
    coffee_station(k, M, p, xi1, 2.15, 3.65)

    # ================================================= the jukebox, the bulletin board
    jukebox(k, M, p, xi0, 2.95)
    bx0, bx1 = p["rest_door"][1] + 0.2, p["rest_door"][1] + 1.3
    bulletin(k, M, p, bx0, bx1, yi1, fz + 1.2, fz + 1.95)

    # ================================================= pendants
    p["pendants"] = []
    for i in range(8):
        x = -4.9 + i * 1.4
        pendant(k, M, p, x, 3.62, fz + 2.12, 0.13, 38.0)
    for tx, ty in tables:
        pendant(k, M, p, tx, 1.33, fz + 1.88, 0.11, 22.0)
    # window-side daylight is the sun's; nothing else


# ------------------------------------------------------------------ pieces

def partition(k, M, p, px, y0, y1, sides, vinyl):
    """A booth back (shared by back-to-back booths): a cream enamel frame, channel-tufted vinyl on
    each seated side, a stainless cap and a chrome grab rail along the top, a stainless end."""
    fz = p["fz"]
    zt = fz + 1.14
    k.add("Booth_Frame", G.box_lohi((px - 0.05, y0 + 0.02, fz + 0.1), (px + 0.05, y1, zt), bevel=0.012), M["paint"], tint=p["cream"], tile=1.0)
    k.add("Booth_Cap", G.box_lohi((px - 0.06, y0 + 0.02, zt), (px + 0.06, y1 + 0.01, zt + 0.025), bevel=0.01, seg=2), M["steel"], tile=0.5)
    k.add("Booth_Grab", G.tube([(px, y1 - 0.02, zt + 0.06), (px, y1 - 0.02, zt + 0.025)], 0.012, n=6), M["chrome"], tile=0.5)
    k.add("Booth_Grab", G.tube(common.fillet_polyline([(px, y1 - 0.02, zt + 0.025), (px, y1 - 0.02, zt + 0.08), (px, y1 - 0.25, zt + 0.08), (px, y1 - 0.25, zt + 0.025)], 0.03, 4, False), 0.012, n=6),
          M["chrome"], tile=0.5, smooth=True)
    k.add("Booth_End", G.box_lohi((px - 0.06, y1 - 0.004, fz + 0.1), (px + 0.06, y1 + 0.01, zt), bevel=0.004), M["steel"], tile=0.5)
    k.add("Booth_Kick", G.box_lohi((px - 0.05, y0 + 0.02, fz), (px + 0.05, y1, fz + 0.1)), M["steel"], tile=0.5)
    k.collider((px - 0.06, y0, fz), (px + 0.06, y1 + 0.01, zt + 0.03))
    for s in sides:
        nch = 5
        for j in range(nch):
            ya = y0 + 0.06 + j * (y1 - y0 - 0.1) / nch
            yb = y0 + 0.06 + (j + 1) * (y1 - y0 - 0.1) / nch
            xa, xb = (px + 0.05, px + 0.15) if s > 0 else (px - 0.15, px - 0.05)
            k.add("Booth_Channel", G.box_lohi((xa, ya + 0.004, fz + 0.5), (xb, yb - 0.004, zt - 0.06), bevel=0.035, seg=2), M["paint"], tint=vinyl, tile=1.0, smooth=True)
        xa, xb = (px + 0.05, px + 0.07) if s > 0 else (px - 0.07, px - 0.05)
        k.add("Booth_Welt", G.box_lohi((xa, y0 + 0.04, zt - 0.07), (xb, y1 - 0.02, zt - 0.04), bevel=0.008), M["paint"], tint=vinyl, tile=1.0, smooth=True)


def seat(k, M, p, bx, side, y0, y1, vinyl):
    """A booth seat facing +x (side 1) or -x (-1), its back against the partition at bx."""
    fz = p["fz"]
    xa, xb = sorted((bx + side * 0.1, bx + side * 0.53))
    k.add("Booth_SeatBase", G.box_lohi((xa + 0.02, y0 + 0.04, fz + 0.06), (xb - 0.02, y1 - 0.03, fz + 0.36)), M["paint"], tint=p["cream"], tile=1.0)
    k.add("Booth_SeatKick", G.box_lohi((xa + 0.04, y0 + 0.04, fz), (xb - 0.04, y1 - 0.05, fz + 0.07)), M["steel"], tile=0.5)
    k.add("Booth_SeatBand", G.box_lohi((xa, y0 + 0.03, fz + 0.33), (xb, y1 - 0.02, fz + 0.36), bevel=0.006), M["chrome"], tile=0.5)
    k.add("Booth_Seat", G.box_lohi((xa, y0 + 0.03, fz + 0.36), (xb, y1 - 0.02, fz + 0.47), bevel=0.04, seg=3), M["paint"], tint=vinyl, tile=1.0, smooth=True)
    k.collider((xa, y0, fz), (xb, y1, fz + 0.46))


def table(k, M, p, x0, x1, y0, y1):
    """A booth table: laminate top with a ribbed aluminium edge, a chrome pedestal and wall bracket."""
    fz = p["fz"]
    zt = fz + 0.765
    k.add("Table_Top", G.box_lohi((x0 + 0.02, y0 + 0.02, zt - 0.03), (x1 - 0.02, y1, zt), bevel=0.004), M["laminate"], tile=0.6)
    out = G.rounded_rect(x0 + 0.02, y0 + 0.02, x1 - 0.02, y1, 0.03, 3)
    k.add("Table_Edge", G.path_sweep(out + [out[0]], [(0.0, zt - 0.034), (0.005, zt - 0.03), (0.005, zt - 0.022), (0.002, zt - 0.019), (0.005, zt - 0.016),
                                                       (0.005, zt - 0.005), (0.0, zt + 0.002)], closed=True), M["chrome"], tile=0.5, uv_rot=True)
    cx, cy = (x0 + x1) / 2, y1 - 0.3
    k.add("Table_Leg", G.cyl((cx, cy, fz + 0.37), 0.035, 0.74, n=12), M["chrome"], tile=0.5, smooth=True)
    k.add("Table_Foot", G.lathe([(0.001, 0.0), (0.2, 0.0), (0.2, 0.012), (0.06, 0.04), (0.04, 0.07)], c=(cx, cy, fz), n=20), M["chrome"], tile=0.5, smooth=True)
    k.add("Table_Bracket", G.box_lohi((cx - 0.1, y0 + 0.0, zt - 0.09), (cx + 0.1, y0 + 0.12, zt - 0.03), bevel=0.01), M["chrome"], tile=0.5)
    k.collider((x0, y0, fz + 0.6), (x1, y1, zt))
    k.collider((cx - 0.05, cy - 0.05, fz), (cx + 0.05, cy + 0.05, zt))
    return (cx, (y0 + y1) / 2)


def wall_box(k, M, p, x, y, z):
    """A tabletop jukebox selector (after a Seeburg Wall-o-Matic): chrome body, curved glass over two
    pages of title strips, the push buttons, the coin plate."""
    w = 0.26
    prof = [(0.0, 0.0), (0.13, 0.0), (0.13, 0.04), (0.1, 0.13), (0.06, 0.175), (0.02, 0.19), (0.0, 0.19)]
    prof = [(y + a, z + b) for a, b in prof]
    k.add("WallBox_Body", G.sweep(prof, x - w / 2, x + w / 2, axis="x", bevel=0.004), M["chrome"], tile=0.5)
    # the window: title strips on the sloped face, under glass
    a, b = (y + 0.128, z + 0.05), (y + 0.075, z + 0.165)
    off = 0.004
    k.add("WallBox_Titles", G.decal((x - w / 2 + 0.02, a[0] + off, a[1]), (x + w / 2 - 0.02, a[0] + off, a[1]), (x + w / 2 - 0.02, b[0] + off, b[1]), (x - w / 2 + 0.02, b[0] + off, b[1]), "wallbox"),
          M["decal"], tile=None)
    k.add("WallBox_Glass", G.quad((x - w / 2 + 0.015, a[0] + 0.009, a[1] - 0.005), (x + w / 2 - 0.015, a[0] + 0.009, a[1] - 0.005),
                                  (x + w / 2 - 0.015, b[0] + 0.009, b[1] + 0.005), (x - w / 2 + 0.015, b[0] + 0.009, b[1] + 0.005)), M["glass"], tile=None, bake=False)
    for j in range(10):
        bxx = x - 0.1 + j * 0.022
        k.add("WallBox_Key", G.box_lohi((bxx - 0.008, y + 0.13, z + 0.012), (bxx + 0.008, y + 0.142, z + 0.03)), M["paint"], tint=(0.8, 0.78, 0.7) if j % 5 else (0.5, 0.05, 0.04), tile=1.0, lm=0.3)
    k.add("WallBox_Coin", G.box_lohi((x + w / 2 - 0.01, y + 0.03, z + 0.06), (x + w / 2 + 0.006, y + 0.1, z + 0.12), bevel=0.004), M["chrome"], tile=0.5)


def stool(k, M, p, x, y, vinyl):
    fz = p["fz"]
    zs = fz + 0.74
    k.add("Stool_Foot", G.lathe([(0.001, 0.0), (0.19, 0.0), (0.19, 0.012), (0.12, 0.035), (0.06, 0.07), (0.045, 0.11)], c=(x, y, fz), n=14), M["chrome"], tile=0.5, smooth=True)
    k.add("Stool_Post", G.cyl((x, y, fz + 0.36), 0.04, 0.52, n=12, cap=False), M["chrome"], tile=0.5, smooth=True)
    k.add("Stool_Swivel", G.lathe([(0.04, 0.0), (0.1, 0.03), (0.12, 0.06), (0.04, 0.075)], c=(x, y, fz + 0.6), n=12), M["chrome"], tile=0.5, smooth=True)
    k.add("Stool_Band", G.lathe([(0.2, 0.0), (0.205, 0.005), (0.205, 0.045), (0.2, 0.05)], c=(x, y, zs - 0.09), n=16), M["chrome"], tile=0.5, smooth=True)
    k.add("Stool_Pan", G.lathe([(0.001, 0.0), (0.2, 0.0)], c=(x, y, zs - 0.09), n=16), M["chrome"], tile=0.5)
    k.add("Stool_Seat", G.lathe([(0.2, 0.0), (0.205, 0.02), (0.2, 0.05), (0.17, 0.075), (0.08, 0.088), (0.001, 0.09)], c=(x, y, zs - 0.04), n=18),
          M["paint"], tint=vinyl, tile=1.0, smooth=True)
    k.collider((x - 0.06, y - 0.06, fz), (x + 0.06, y + 0.06, zs - 0.1))
    k.collider((x - 0.2, y - 0.2, zs - 0.1), (x + 0.2, y + 0.2, zs + 0.05))


def sunburst(k, M, xr, y, z0, z1):
    """A stainless sunburst panel: rays fanning up from the bottom centre, each a shallow ridge."""
    x0, x1 = xr
    cx, cz = (x0 + x1) / 2, z0
    k.add("Bar_Splash", G.box_lohi((x0, y - 0.012, z0), (x1, y, z1)), M["steel"], tile=0.5)
    nr = 15
    for i in range(nr):
        a0 = math.pi * (i + 0.15) / nr
        a1 = math.pi * (i + 0.85) / nr
        am = (a0 + a1) / 2
        R = 2.0
        def hit(a):
            dx, dz = math.cos(a), math.sin(a)
            ts = []
            if abs(dx) > 1e-6:
                ts.append(((x1 if dx > 0 else x0) - cx) / dx)
            if dz > 1e-6:
                ts.append((z1 - cz) / dz)
            t = min(t for t in ts if t > 0)
            return (cx + dx * t, cz + dz * t)
        pa, pb, pm = hit(a0), hit(a1), hit(am)
        bm = bmesh.new()
        c0 = bm.verts.new((cx, y - 0.013, cz))
        va = bm.verts.new((pa[0], y - 0.013, pa[1]))
        vm = bm.verts.new((pm[0], y - 0.019, pm[1]))
        vb = bm.verts.new((pb[0], y - 0.013, pb[1]))
        bm.faces.new([c0, vm, va])
        bm.faces.new([c0, vb, vm])
        k.add("Bar_Ray", bm, M["steel"], tile=0.5, lm=0.6)
    k.add("Bar_RayHub", G.cyl((cx, y - 0.015, cz + 0.005), 0.06, 0.02, n=12, axis="y"), M["chrome"], tile=0.5)


def mug(k, M, p, x, y, z, tint):
    k.add("Mug", G.lathe([(0.001, 0.0), (0.038, 0.0), (0.042, 0.085), (0.034, 0.088), (0.001, 0.07)], c=(x, y, z), n=7),
          M["paint"], tint=tint, tile=1.0, smooth=True, lm=0.25)


def urn(k, M, p, x, y, z):
    """A twin-tank coffee urn (a tall chrome cylinder on legs, a gauge glass, a spigot)."""
    k.add("Urn_Body", G.lathe([(0.001, 0.12), (0.15, 0.12), (0.17, 0.14), (0.17, 0.62), (0.16, 0.66), (0.09, 0.7), (0.05, 0.7), (0.05, 0.74), (0.001, 0.75)],
                             c=(x, y, z), n=24), M["chrome"], tile=0.5, smooth=True)
    for a in (0.6, 2.7, 4.8):
        k.add("Urn_Leg", G.cyl((x + 0.13 * math.cos(a), y + 0.13 * math.sin(a), z + 0.06), 0.018, 0.12, n=8), M["chrome"], tile=0.5)
    k.add("Urn_Gauge", G.cyl((x + 0.08, y - 0.16, z + 0.4), 0.012, 0.42, n=8), M["glass"], tile=None, bake=False)
    k.add("Urn_Coffee", G.cyl((x + 0.08, y - 0.16, z + 0.32), 0.009, 0.26, n=6), M["paint"], tint=(0.06, 0.025, 0.01), tile=1.0, lm=0.2)
    k.add("Urn_Spigot", G.tube([(x, y - 0.16, z + 0.2), (x, y - 0.24, z + 0.2), (x, y - 0.24, z + 0.15)], 0.018, n=8), M["chrome"], tile=0.5, smooth=True)
    k.add("Urn_Handle", G.box_lohi((x - 0.012, y - 0.26, z + 0.2), (x + 0.012, y - 0.22, z + 0.29), bevel=0.005), M["paint"], tint=(0.02, 0.02, 0.02), tile=1.0, lm=0.2)


def mixer(k, M, p, x, y, z):
    """A three-spindle malt mixer in jade enamel, with stainless cups."""
    k.add("Mixer_Base", G.box_lohi((x - 0.2, y - 0.12, z), (x + 0.2, y + 0.1, z + 0.06), bevel=0.02, seg=2), M["paint"], tint=(0.25, 0.45, 0.35), tile=1.0)
    k.add("Mixer_Column", G.box_lohi((x - 0.06, y + 0.0, z + 0.06), (x + 0.06, y + 0.1, z + 0.4), bevel=0.03, seg=2), M["paint"], tint=(0.25, 0.45, 0.35), tile=1.0)
    k.add("Mixer_Head", G.box_lohi((x - 0.19, y - 0.1, z + 0.38), (x + 0.19, y + 0.1, z + 0.5), bevel=0.04, seg=3), M["paint"], tint=(0.25, 0.45, 0.35), tile=1.0, smooth=True)
    for dx in (-0.12, 0.0, 0.12):
        k.add("Mixer_Cup", G.lathe([(0.001, 0.0), (0.035, 0.0), (0.045, 0.18), (0.042, 0.18), (0.001, 0.005)], c=(x + dx, y - 0.06, z + 0.07), n=12), M["chrome"], tile=0.5, smooth=True)
        k.add("Mixer_Spindle", G.cyl((x + dx, y - 0.06, z + 0.32), 0.005, 0.12, n=6), M["chrome"], tile=0.5)


def pie_case(k, M, p, x, y, z):
    """The revolving pie case: a glass cylinder on a chrome base with three shelves of pies."""
    h = 0.62
    k.add("PieCase_Base", G.lathe([(0.001, 0.0), (0.24, 0.0), (0.24, 0.08), (0.22, 0.09), (0.001, 0.09)], c=(x, y, z), n=24), M["chrome"], tile=0.5, smooth=True)
    k.add("PieCase_Top", G.lathe([(0.001, h + 0.12), (0.22, h + 0.12), (0.24, h + 0.08), (0.24, h + 0.06), (0.001, h + 0.06)], c=(x, y, z), n=24), M["chrome"], tile=0.5, smooth=True)
    k.add("PieCase_Glass", G.cyl((x, y, z + 0.09 + (h - 0.03) / 2), 0.23, h - 0.03, n=24, cap=False), M["glass"], tile=None, bake=False)
    k.add("PieCase_Post", G.cyl((x, y, z + 0.09 + h / 2), 0.012, h, n=8), M["chrome"], tile=0.5)
    for j, kind in enumerate(("pie0", "pie2", "pie1")):
        zz = z + 0.1 + j * 0.2
        k.add("PieCase_Shelf", G.cyl((x, y, zz), 0.21, 0.008, n=24), M["glass"], tile=None, bake=False)
        k.add("PieCase_PieSide", G.cyl((x, y, zz + 0.025), 0.12, 0.04, n=16, cap=False), M["paint"], tint=(0.55, 0.35, 0.15), tile=1.0, lm=0.3)
        k.add("PieCase_Pie", G.decal_disc((x, y, zz + 0.046), 0.125, kind, n=16), M["decal"], tile=None, lm=0.3)
    k.light(kind="point", loc=(x, y, z + h + 0.03), power=4.0, color=(1.0, 0.9, 0.75), radius=0.02)


def toaster(k, M, p, x, y, z):
    k.add("Toaster", G.box_lohi((x - 0.17, y - 0.12, z), (x + 0.17, y + 0.12, z + 0.24), bevel=0.04, seg=3), M["chrome"], tile=0.5, smooth=True)
    for dx in (-0.08, 0.0, 0.08):
        k.add("Toaster_Slot", G.box_lohi((x + dx - 0.012, y - 0.08, z + 0.236), (x + dx + 0.012, y + 0.08, z + 0.242)), M["paint"], tint=(0.01, 0.01, 0.01), tile=1.0, lm=0.2)
    k.add("Toaster_Lever", G.box_lohi((x + 0.17, y - 0.02, z + 0.12), (x + 0.2, y + 0.02, z + 0.14)), M["paint"], tint=(0.02, 0.02, 0.02), tile=1.0, lm=0.2)


def plates(k, M, p, x, y, z, n):
    k.add("Plates", G.lathe([(0.001, 0.0), (0.1, 0.0), (0.125, n * 0.012), (0.001, n * 0.012)], c=(x, y, z), n=20), M["paint"], tint=(0.78, 0.76, 0.7), tile=1.0, smooth=True, lm=0.4)


def glass_rack(k, M, p, x, y, z):
    k.add("GlassRack", G.box_lohi((x - 0.24, y - 0.24, z), (x + 0.24, y + 0.24, z + 0.1)), M["paint"], tint=(0.08, 0.09, 0.1), tile=1.0, lm=0.4)
    for i in range(4):
        for j in range(4):
            gx, gy = x - 0.18 + i * 0.12, y - 0.18 + j * 0.12
            k.add("Glass", G.cyl((gx, gy, z + 0.16), 0.035, 0.12, n=8, cap=False), M["glass"], tile=None, bake=False)


def cake_stand(k, M, p, x, y, zt, kind):
    k.add("Stand_Foot", G.lathe([(0.001, 0.0), (0.09, 0.0), (0.09, 0.01), (0.025, 0.04), (0.02, 0.14), (0.15, 0.15), (0.15, 0.16), (0.001, 0.16)], c=(x, y, zt), n=20),
          M["chrome"], tile=0.5, smooth=True)
    k.add("Stand_PieSide", G.cyl((x, y, zt + 0.185), 0.13, 0.045, n=20, cap=False), M["paint"], tint=(0.55, 0.35, 0.15) if kind != "cake" else (0.75, 0.7, 0.62), tile=1.0, lm=0.3)
    if kind == "cake":
        k.add("Stand_PieSide", G.cyl((x, y, zt + 0.23), 0.13, 0.1, n=20, cap=False), M["paint"], tint=(0.72, 0.68, 0.6), tile=1.0, lm=0.3)
    k.add("Stand_Pie", G.decal_disc((x, y, zt + (0.208 if kind != "cake" else 0.281)), 0.132, kind, n=20), M["decal"], tile=None, lm=0.3)
    k.add("Stand_Dome", G.lathe([(0.155, 0.0), (0.155, 0.1), (0.145, 0.2), (0.11, 0.27), (0.05, 0.3), (0.001, 0.305)], c=(x, y, zt + 0.16), n=20), M["glass"], tile=None, bake=False, smooth=True)
    k.add("Stand_Knob", G.lathe([(0.001, 0.0), (0.02, 0.005), (0.02, 0.03), (0.001, 0.04)], c=(x, y, zt + 0.46), n=10), M["chrome"], tile=0.5, smooth=True)


def register(k, M, p, x, y, zt):
    """A brass-and-chrome register (kept from the old car) and the modern card reader beside it."""
    k.add("Register_Body", G.sweep([(y - 0.18, zt), (y + 0.18, zt), (y + 0.18, zt + 0.32), (y + 0.05, zt + 0.36), (y - 0.1, zt + 0.22), (y - 0.18, zt + 0.12)], x - 0.2, x + 0.2,
                                   axis="x", bevel=0.01), M["chrome"], tint=p["brass"], tile=0.5)
    for i in range(4):
        for j in range(3):
            k.add("Register_Key", G.cyl((x - 0.12 + i * 0.08, y - 0.13 + j * 0.035, zt + 0.15 + j * 0.03), 0.013, 0.02, n=8), M["paint"], tint=(0.8, 0.78, 0.7), tile=1.0, lm=0.2)
    k.add("Register_Drawer", G.box_lohi((x - 0.19, y - 0.2, zt), (x + 0.19, y - 0.17, zt + 0.08), bevel=0.005), M["chrome"], tint=p["brass"], tile=0.5)
    k.add("Reader", G.box_lohi((x - 0.38, y - 0.08, zt), (x - 0.28, y + 0.06, zt + 0.03), bevel=0.008), M["paint"], tint=(0.02, 0.02, 0.022), tile=1.0, lm=0.3)
    k.add("Reader_Screen", G.box_lohi((x - 0.37, y - 0.06, zt + 0.03), (x - 0.29, y + 0.04, zt + 0.032)), M["neon_blue"], tile=None, bake=False)


def coffee_station(k, M, p, xw, y0, y1):
    """At the east end wall: a stainless cabinet, a two-warmer brewer with its pots, a matte black
    espresso machine (the restoration's one modern thing), cups and lids."""
    fz = p["fz"]
    d = 0.62
    zt = fz + 0.9
    k.add("Coffee_Cab", G.box_lohi((xw - d, y0, fz + 0.1), (xw, y1, zt)), M["steel"], tile=0.5)
    k.add("Coffee_Kick", G.box_lohi((xw - d + 0.05, y0, fz), (xw, y1, fz + 0.1)), M["paint"], tint=p["black"], tile=1.0)
    k.add("Coffee_Top", G.box_lohi((xw - d - 0.02, y0 - 0.02, zt), (xw, y1 + 0.02, zt + 0.035), bevel=0.006), M["steel"], tile=0.5)
    for j in range(2):
        ya, yb = y0 + 0.02 + j * (y1 - y0) / 2, y0 + (j + 1) * (y1 - y0) / 2 - 0.02
        k.add("Coffee_Door", G.box_lohi((xw - d - 0.015, ya, fz + 0.12), (xw - d, yb, zt - 0.03), bevel=0.004), M["steel"], tile=0.5)
        k.add("Coffee_Handle", G.box_lohi((xw - d - 0.035, ya + 0.08, zt - 0.14), (xw - d - 0.015, yb - 0.08, zt - 0.12), bevel=0.004), M["chrome"], tile=0.5)
    k.collider((xw - d - 0.02, y0, fz), (xw, y1, zt + 0.035))
    z = zt + 0.035
    # the brewer
    bx = xw - 0.3
    by = y0 + 0.4
    k.add("Brewer_Body", G.box_lohi((bx - 0.2, by - 0.25, z), (bx + 0.2, by + 0.25, z + 0.06)), M["steel"], tile=0.5)
    k.add("Brewer_Tower", G.box_lohi((bx + 0.05, by - 0.25, z + 0.06), (bx + 0.2, by + 0.25, z + 0.55), bevel=0.01), M["steel"], tile=0.5)
    k.add("Brewer_Head", G.box_lohi((bx - 0.2, by - 0.25, z + 0.45), (bx + 0.2, by + 0.25, z + 0.55), bevel=0.01), M["steel"], tile=0.5)
    k.add("Brewer_Panel", G.box_lohi((bx - 0.205, by - 0.2, z + 0.47), (bx - 0.2, by + 0.2, z + 0.53)), M["paint"], tint=(0.02, 0.02, 0.02), tile=1.0, lm=0.3)
    for dy in (-0.12, 0.12):
        k.add("Brewer_Basket", G.box_lohi((bx - 0.12, by + dy - 0.08, z + 0.38), (bx + 0.05, by + dy + 0.08, z + 0.44), bevel=0.01), M["paint"], tint=(0.03, 0.03, 0.03), tile=1.0, lm=0.3)
        pot(k, M, bx - 0.05, by + dy, z + 0.06)
    for dy, zz in ((-0.12, z + 0.55), (0.12, z + 0.55)):
        pot(k, M, bx - 0.05, by + dy, zz, warmer=True)
    # the espresso machine: matte black, chrome group heads, a wood steam knob
    ex, ey = xw - 0.32, y1 - 0.38
    k.add("Espresso_Body", G.box_lohi((ex - 0.25, ey - 0.3, z), (ex + 0.25, ey + 0.3, z + 0.42), bevel=0.02, seg=2), M["paint"], tint=(0.018, 0.018, 0.02), tile=1.0)
    k.add("Espresso_Drip", G.box_lohi((ex - 0.3, ey - 0.26, z), (ex - 0.22, ey + 0.26, z + 0.03)), M["steel"], tile=0.5)
    k.add("Espresso_Top", G.box_lohi((ex - 0.24, ey - 0.29, z + 0.42), (ex + 0.24, ey + 0.29, z + 0.44)), M["steel"], tile=0.5)
    for dy in (-0.13, 0.13):
        k.add("Espresso_Group", G.cyl((ex - 0.27, ey + dy, z + 0.25), 0.045, 0.06, n=12), M["chrome"], tile=0.5, smooth=True)
        k.add("Espresso_Handle", G.tube([(ex - 0.29, ey + dy, z + 0.21), (ex - 0.42, ey + dy - 0.03, z + 0.2)], 0.012, n=6), M["paint"], tint=(0.15, 0.08, 0.04), tile=1.0, lm=0.3)
    for j in range(6):
        k.add("Cup", G.lathe([(0.001, 0.0), (0.03, 0.0), (0.04, 0.055), (0.001, 0.055)], c=(ex + 0.05 - (j % 3) * 0.08, ey - 0.15 + (j // 3) * 0.3, z + 0.44), n=10),
              M["paint"], tint=(0.78, 0.76, 0.7), tile=1.0, lm=0.3)
    # to-go cups and lids, the sugar caddy
    for j in range(3):
        k.add("ToGo", G.lathe([(0.001, 0.0), (0.03, 0.0), (0.042, 0.4), (0.001, 0.4)], c=(xw - 0.52 + j * 0.08 * 0, y0 + 0.9 + j * 0.1, z), n=10), M["paint"], tint=(0.75, 0.72, 0.64), tile=1.0, lm=0.3)
    # the shelf above with mugs
    k.add("Coffee_Shelf", G.box_lohi((xw - 0.28, y0, fz + 1.95), (xw, y1, fz + 1.98), bevel=0.005), M["steel"], tile=0.5)
    for j in range(10):
        mug(k, M, p, xw - 0.14, y0 + 0.1 + j * 0.13, fz + 1.98, (0.75, 0.72, 0.64))


def pot(k, M, x, y, z, warmer=False):
    k.add("Pot_Glass", G.lathe([(0.001, 0.0), (0.06, 0.0), (0.085, 0.06), (0.08, 0.12), (0.05, 0.16), (0.045, 0.18)], c=(x, y, z), n=14), M["glass"], tile=None, bake=False, smooth=True)
    k.add("Pot_Coffee", G.lathe([(0.001, 0.003), (0.058, 0.003), (0.08, 0.06), (0.078, 0.08), (0.001, 0.08)], c=(x, y, z), n=12), M["paint"], tint=(0.05, 0.02, 0.008), tile=1.0, lm=0.3)
    k.add("Pot_Collar", G.lathe([(0.05, 0.16), (0.055, 0.165), (0.055, 0.2), (0.048, 0.205)], c=(x, y, z), n=12), M["paint"], tint=(0.35, 0.04, 0.03) if not warmer else (0.6, 0.35, 0.05), tile=1.0, lm=0.3)
    k.add("Pot_Handle", G.tube([(x, y + 0.05, z + 0.17), (x, y + 0.11, z + 0.15), (x, y + 0.1, z + 0.05)], 0.01, n=6), M["paint"], tint=(0.02, 0.02, 0.02), tile=1.0, lm=0.2)


def jukebox(k, M, p, xw, yc):
    """After a Wurlitzer 1015: an arched walnut cabinet, bubble-tube pilasters lit in amber, red and
    blue, the selection panel glowing behind its glass, the grille below; chrome trim."""
    fz = p["fz"]
    w, d, h = 0.95, 0.66, 1.52
    y0, y1 = yc - w / 2, yc + w / 2
    x0, x1 = xw, xw + d
    # the cabinet's front outline (y, z): straight sides, a round arch on top
    arc = [(yc + (w / 2) * math.cos(math.pi * t / 16), fz + h - w / 2 + (w / 2) * math.sin(math.pi * t / 16)) for t in range(17)]
    outline = [(y1, fz)] + arc + [(y0, fz)]
    k.add("Juke_Cabinet", G.sweep(outline, x0, x1 - 0.06, axis="x"), M["wood"], tint=(0.75, 0.6, 0.5), tile=0.5)
    k.collider((x0, y0, fz), (x1, y1, fz + h))
    # the bubble tubes: two arches of neon (outer amber-red, inner blue), the pilasters' tubes
    def arch(r, z0, xoff):
        pts = [(x1 - xoff, yc + r * math.cos(math.pi * t / 16), fz + h - w / 2 + r * math.sin(math.pi * t / 16)) for t in range(17)]
        return [(pts[0][0], pts[0][1], z0)] + pts + [(pts[-1][0], pts[-1][1], z0)]
    k.add("Juke_TubeOuter", G.tube(arch(w / 2 - 0.05, fz + 0.12, 0.02), 0.026, n=8), M["neon_red"], tile=None, bake=True)
    k.add("Juke_TubeInner", G.tube(arch(w / 2 - 0.13, fz + 0.52, 0.03), 0.018, n=8), M["neon_blue"], tile=None, bake=True)
    # chrome trim round the arch
    k.add("Juke_Trim", G.tube(arch(w / 2 - 0.005, fz + 0.02, 0.05), 0.014, n=6), M["chrome"], tile=0.5, smooth=True)
    # the face: grille (lower), selection panel (upper, sloped), the dome glass
    xf = x1 - 0.062
    k.add("Juke_Grille", G.decal((xf, y1 - 0.2, fz + 0.15), (xf, y0 + 0.2, fz + 0.15), (xf, y0 + 0.2, fz + 0.55), (xf, y1 - 0.2, fz + 0.55), "grille"), M["decal"], tile=None)
    k.add("Juke_PanelBox", G.box_lohi((x1 - 0.2, y0 + 0.2, fz + 0.62), (x1 - 0.06, y1 - 0.2, fz + 0.98), bevel=0.01), M["chrome"], tile=0.5)
    xp = x1 - 0.059
    k.add("Juke_Panel", G.decal((xp, y1 - 0.24, fz + 0.66), (xp, y0 + 0.24, fz + 0.66), (xp, y0 + 0.24, fz + 0.94), (xp, y1 - 0.24, fz + 0.94), "juke"), M["decal"], tile=None)
    k.add("Juke_Dome", G.lathe([(0.001, 0.0), (0.3, 0.0), (0.28, 0.12), (0.18, 0.22), (0.001, 0.26)], c=(x1 - 0.25, yc, fz + 1.0), n=16), M["glass"], tile=None, bake=False, smooth=True)
    k.add("Juke_Record", G.cyl((x1 - 0.25, yc, fz + 1.05), 0.14, 0.006, n=20), M["paint"], tint=(0.01, 0.01, 0.01), tile=1.0, lm=0.3)
    k.add("Juke_Plinth", G.box_lohi((x0, y0 - 0.02, fz), (x1 + 0.01, y1 + 0.02, fz + 0.08), bevel=0.01), M["chrome"], tile=0.5)
    k.light(kind="area", loc=(x1 + 0.05, yc, fz + 0.9), size=(0.8, 0.9), power=10.0, color=(1.0, 0.5, 0.25), dir=(1, 0, 0))


def bulletin(k, M, p, x0, x1, y, z0, z1):
    """A cork board in an oak frame (a lost dog, a yard sale, a church supper: nothing readable)."""
    k.add("Board_Frame", G.box_lohi((x0 - 0.04, y - 0.03, z0 - 0.04), (x1 + 0.04, y, z1 + 0.04), bevel=0.008), M["wood"], tile=0.5)
    yy = y - 0.031
    k.add("Board_Cork", G.decal((x0, yy, z0), (x1, yy, z0), (x1, yy, z1), (x0, yy, z1), "cork"), M["decal"], tile=None)
    notes = [(0.08, 0.45, 0.21, 0.28, "paper0", 3), (0.32, 0.5, 0.18, 0.23, "paper1", -4), (0.52, 0.42, 0.2, 0.27, "flyer", 2), (0.75, 0.48, 0.16, 0.2, "paper2", -6),
             (0.12, 0.08, 0.19, 0.24, "paper3", 5), (0.36, 0.1, 0.17, 0.2, "photo", -2), (0.58, 0.06, 0.2, 0.26, "paper0", 1), (0.8, 0.1, 0.15, 0.2, "paper1", 7)]
    W, H = x1 - x0, z1 - z0
    for u, v, w, h, reg, rot in notes:
        cx, cz = x0 + (u + w / 2) * W, z0 + (v + h / 2) * H
        hw, hh = w * W / 2, h * H / 2
        a = math.radians(rot)
        pts = [(cx + dx * math.cos(a) - dz * math.sin(a), yy - 0.002, cz + dx * math.sin(a) + dz * math.cos(a)) for dx, dz in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
        k.add("Board_Note", G.decal(*pts, reg), M["decal"], tile=None, lm=0.4)
        k.add("Board_Pin", G.cyl((cx, yy - 0.006, cz + hh * 0.8), 0.006, 0.01, n=6, axis="y"), M["paint"], tint=(0.6, 0.05, 0.04), tile=1.0, lm=0.2)


def pendant(k, M, p, x, y, zg, r, power):
    """An opal schoolhouse globe on a chrome stem from a canopy on the vault."""
    zc = p["car"]["ceil_z"](y)
    k.add("Pendant_Canopy", G.lathe([(0.001, 0.0), (0.06, 0.0), (0.05, -0.03), (0.001, -0.035)], c=(x, y, zc - 0.005), n=12), M["chrome"], tile=0.5, smooth=True)
    k.add("Pendant_Stem", G.cyl((x, y, (zc + zg + r * 1.6) / 2), 0.007, zc - zg - r * 1.6, n=6, cap=False), M["chrome"], tile=0.5, lm=0.2)
    k.add("Pendant_Fitter", G.lathe([(0.012, 0.09), (0.035, 0.085), (0.06, 0.03), (0.062, 0.0), (0.012, 0.0)], c=(x, y, zg + r * 1.5), n=14), M["chrome"], tile=0.5, smooth=True)
    k.add("Pendant_Globe", G.lathe([(0.055, r * 1.52), (r * 0.82, r * 1.3), (r, r * 0.75), (r * 0.95, r * 0.3), (r * 0.6, r * 0.02), (0.001, 0.0)], c=(x, y, zg), n=16),
          M["globe"], tile=None, bake=False, smooth=True)
    k.light(kind="point", loc=(x, y, zg + r * 0.8), power=power, color=(1.0, 0.80, 0.58), radius=r * 0.6)
    p.setdefault("pendants", []).append((x, y, zg))
