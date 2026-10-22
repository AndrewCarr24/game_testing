"""Sourwood, N.C. (design/town/brief.md): the town on the Laurel River flats downstream of Laurel
Fork Cove, as a level config for the wilderness terrain generator plus the layout as data
(buildings by kit name, streets, the road from the estate, bridges, the heritage rail line,
exits, hiding places, the cahoots evidence, the townspeople's posts and views).

It is its own world (`viewer/wild.html?world=laurel_town`), not a continuation of laurel_fork:
the runtime's CDLOD terrain needs size / leaf = a power of two over 1025^2 samples, so a square is
1536 m, and the town lies 0.7-1.5 km past the cove square's west edge. The town square shares the
cove's y transform and 1.5 m grid (OY = 810; x offset -1500, a whole number of cells), and overlaps
the cove square by 36 m (estate x -768..-732), where its heights ARE the cove's (copied from the
cove's terrain run), so the player can walk (or drive, or wade) across the seam: the runtime
reloads into the other world at the same estate-frame point (world.json "exits").

Frames: estate (x east, y north, z = the estate lawn, the house at the origin); terrain local =
(estate x + 1500, estate y + 810); three.js = (local x, height, -local y).

  PY=/Applications/Blender.app/Contents/Resources/5.0/python/bin/python3.11
  $PY blender/wilderness/levels/laurel_town.py                 # guide + terrain + world (~2 min)
  $PY blender/wilderness/levels/laurel_town.py --steps world   # reuse the last terrain
Needs the cove's terrain run (build/wilderness/laurel_fork/terrain.npz, from laurel_fork.py).
Outputs build/wilderness/laurel_town/ (+ world/). numpy only: no Blender, no run slot.
"""
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import terrain  # noqa: E402

NAME = "laurel_town"
COVE = "laurel_fork"
CX = -1500.0                         # the square's centre, estate x
OY = 810.0                           # = laurel_fork.OFFSET_Y (estate y -810 is the centre)
SIZE, CELL = 1536.0, 1.5
HALF = SIZE / 2
SEAM_X = -768.0                      # the cove square's west edge; x >= SEAM_X: the cove's own heights
SEED = 23
LOOK_NAME = "golden"


def local(pt):
    return (pt[0] - CX, pt[1] + OY) + tuple(pt[2:])


# ------------------------------------------------------------------ the river and the valley
# The Laurel River's centreline (estate frame), continuing the cove's out of the Narrows (x -768,
# y ~-736), through the gorge, into the Sourwood basin, round the Tunnel Knob spur and out west.
RIVER = [(-725, -735), (-800, -742), (-900, -752), (-1000, -760), (-1100, -766), (-1200, -772), (-1300, -778),
         (-1400, -784), (-1500, -792), (-1585, -800), (-1700, -806), (-1850, -810), (-1950, -816), (-2050, -828),
         (-2150, -843), (-2280, -860)]
RIVER_HW = 17.0                      # half width of the water (the hydrology's 34 m clamp)
# water surface (estate z): -184.7 where it leaves the cove, a riffle at the gorge mouth, then the
# slow flats (0.15%)
WATER = [(-725, -184.7), (-1300, -186.3), (-1380, -186.9), (-1470, -188.2), (-2280, -190.4)]
# the valley floor beyond each bank (m): the gorge, then the basin opening at x -1450, the spur
# (Tunnel Knob) pinching the north side at the west end
FLOOR_X = [-725, -800, -1000, -1200, -1350, -1430, -1500, -1580, -1700, -1850, -2000, -2100, -2160, -2280]
FLOOR_N = [8, 10, 12, 14, 16, 28, 80, 150, 165, 170, 150, 110, 28, 12]
FLOOR_S = [10, 12, 14, 16, 18, 40, 115, 125, 118, 105, 70, 40, 22, 16]
BANK_H = [(-1400, 1.8), (-1500, 3.6)]           # bank top over the water: gorge -> town (a flood terrace)
# hillsides beyond the floor: slope at the foot s0, mid-slope s1 reached over B m, height Hm
WALL_X = [-725, -1350, -1480, -2120, -2180, -2280]
WALL = dict(n_s0=[0.75, 0.75, 0.26, 0.26, 0.85, 0.85], n_s1=[1.0, 1.0, 0.85, 0.85, 1.1, 1.1],
            n_B=[50, 50, 130, 130, 40, 40], n_Hm=[190, 190, 250, 250, 140, 140],
            s_s0=[0.75, 0.75, 0.22, 0.22, 0.6, 0.6], s_s1=[1.0, 1.0, 0.75, 0.75, 1.0, 1.0],
            s_B=[50, 50, 130, 130, 60, 60], s_Hm=[200, 200, 260, 260, 200, 200])
# hollows into the hillsides (estate x, y polylines from the floor's edge uphill; depth m, width m
# at each point): the Gap Branch (the Gap Road climbs it), Church Branch behind the motel, the
# Tannery Branch behind Mill Hill (the trail) and a west draw; the rest come from the erosion
HOLLOWS = [
    [(-1574, -640, 4, 60), (-1570, -520, 30, 120), (-1562, -380, 55, 170), (-1556, -200, 60, 200), (-1552, -40, 40, 200)],
    [(-1985, -660, 4, 60), (-1990, -560, 28, 110), (-2010, -420, 45, 160), (-2030, -250, 40, 180)],
    [(-1614, -950, 4, 50), (-1618, -1050, 26, 100), (-1612, -1180, 45, 150), (-1600, -1350, 45, 170), (-1595, -1560, 30, 180)],
    [(-1990, -900, 4, 60), (-2000, -1000, 30, 120), (-2025, -1150, 45, 160), (-2050, -1350, 40, 180)],
]


def _polyline_dist(X, Y, pts):
    """Distance from points to a polyline (n, 4: x, y, depth, width), with the depth / width
    interpolated at the nearest point."""
    P = terrain.spline(pts, 10.0)
    d = np.full(X.shape, np.inf)
    dep = np.zeros(X.shape)
    wid = np.ones(X.shape)
    for a, c in zip(P[:-1], P[1:]):
        ab = c[:2] - a[:2]
        L2 = float(ab @ ab) or 1e-9
        t = np.clip(((X - a[0]) * ab[0] + (Y - a[1]) * ab[1]) / L2, 0, 1)
        dist = np.hypot(a[0] + t * ab[0] - X, a[1] + t * ab[1] - Y)
        m = dist < d
        d = np.where(m, dist, d)
        dep = np.where(m, a[2] + t * (c[2] - a[2]), dep)
        wid = np.where(m, a[3] + t * (c[3] - a[3]), wid)
    return d, dep, wid


def river_y(x):
    rx, ry = np.array([q[0] for q in RIVER])[::-1], np.array([q[1] for q in RIVER])[::-1]
    return np.interp(x, rx, ry)


def water_z(x):
    wx, wz = np.array([q[0] for q in WATER])[::-1], np.array([q[1] for q in WATER])[::-1]
    return np.interp(x, wx, wz)


def _ix(x, xs, vs):
    return np.interp(x, np.array(xs)[::-1], np.array(vs, float)[::-1])


def valley_field(X, Y, noise):
    """The authored valley (estate frame, analytic: the square and the backdrop ring both use it):
    the river channel (flat at water + 0.25: the hydrology digs the bed), banks, the flood terrace,
    then hillsides rising from the floor's edge, cut by hollows, with noise."""
    yr = river_y(X)
    dy = Y - yr
    north = dy > 0
    e = np.abs(dy) - RIVER_HW                                # m beyond the bank line
    F = np.where(north, _ix(X, FLOOR_X, FLOOR_N), _ix(X, FLOOR_X, FLOOR_S))
    wz = water_z(X)
    bank_h = np.interp(X, [-1500, -1400], [3.6, 1.8])
    floor_z = wz + bank_h + 0.018 * np.clip(e, 0, None).clip(None, F)
    # channel and the bank's 5 m ramp
    chan = wz + 0.25 - 0.06 * np.clip(1 - np.abs(dy) / RIVER_HW, 0, 1)
    ramp = terrain.smoothstep(0.0, 5.0, e)
    z = chan + (floor_z - chan) * ramp
    # walls: the hill foot wanders (+-18 m), spurs and coves alternate along the valley (the wall's
    # height and steepness breathe on a 300-400 m wavelength), hollows cut back into them
    F = F + 18.0 * noise.fbm(X - 7, Y + 3, 220.0, 3) * terrain.smoothstep(20.0, 60.0, F)
    b = np.clip(e - F, 0, None)
    side = lambda k: np.where(north, _ix(X, WALL_X, WALL["n_" + k]), _ix(X, WALL_X, WALL["s_" + k]))
    s0, s1, B, Hm = side("s0"), side("s1"), side("B"), side("Hm")
    wx = 160.0 * noise.fbm(X * 0.5 + 77, Y, 420.0, 2)                 # (warped: spurs curve and branch)
    spur = noise.fbm(X + wx + 900, Y * 0.45 + np.where(north, 300.0, -300.0), 380.0, 3)
    Hm = Hm * np.clip(1 + 0.5 * spur + 0.35 * (noise.ridged(X + wx, Y, 650.0, 3) - 0.45), 0.35, 1.8)
    s0 = s0 * np.clip(1 + 0.45 * spur, 0.5, 1.6)
    q = (s0 * b + (s1 - s0) * (np.minimum(b, B) ** 2 / (2 * B) + np.maximum(b - B, 0))) / Hm
    rise = Hm * (1 - np.exp(-q))
    for h in HOLLOWS:
        d, dep, wid = _polyline_dist(X, Y, h)
        t = np.clip(d / (wid / 2), 0, 1)
        rise = rise - dep * (1 - t * t) ** 2 * terrain.smoothstep(0.0, 25.0, b)
    rise = np.maximum(rise, 0.0)
    det = (9.0 * noise.fbm(X, Y, 110.0, 4) + 3.0 * noise.fbm(X - 41, Y + 77, 28.0, 3)) * terrain.smoothstep(0.0, 45.0, b)
    det += 4.0 * noise.ridged(X + 13, Y, 90.0, 3) * terrain.smoothstep(20.0, 80.0, b)
    flat = 0.25 * noise.fbm(X + 5, Y - 3, 70.0, 3) * terrain.smoothstep(2.0, 12.0, e) * (1 - terrain.smoothstep(0.0, 20.0, b))
    return z + rise + det + flat


# ------------------------------------------------------------------ the road from the estate
# The mansion-landscape workstream builds the road from the estate's gate down the valley to the
# cove square's west edge. HANDOFF (estate frame): it meets this zone at ROAD_IN, on the old river
# road's grade (laurel_fork river_road), heading west; from there the town carries it: down the
# gorge's south wall at <= 3%, across the south flats, over the green truss bridge into downtown,
# and through town as Main Street, then out west as the highway past the strip.
ROAD_IN = dict(x=-768.0, y=-786.0, z=-164.8, heading_deg=265.0, lanes=2, lane_m=3.6, shoulder_m=1.5)
ROAD_GORGE = [(-770, -786), (-800, -790), (-860, -797), (-950, -806), (-1050, -812), (-1150, -817), (-1250, -821),
              (-1350, -826), (-1430, -832), (-1480, -842), (-1520, -860), (-1550, -874), (-1572, -866), (-1583, -850),
              (-1585, -842)]
ROAD_Z0, ROAD_Z1 = -164.8, -183.6          # the bench: from the cove's grade down to the south flats
BRIDGE = dict(a=(-1585.0, -842.0), b=(-1585.0, -762.0), deck=-182.0, spans=2, width=10.0)   # the truss bridge (road)
MAIN_Y = -725.0
ROAD_TOWN = [(-1585, -762), (-1585, -748), (-1592, -731), (-1610, -725), (-1700, -725), (-1800, -725),
             (-1860, -725), (-1950, -727), (-2050, -736), (-2120, -758), (-2165, -790), (-2200, -820), (-2240, -836), (-2275, -846)]

# ------------------------------------------------------------------ buildings
# kit name -> (w, d, h, walk-in, roof): w along x, d along y in the asset frame (front faces -Y);
# the blockout's massing until the kit's glTFs exist (design/town/kit_request.md v2)
KIT = {
    "town_bar": (30, 18, 6, True, "gable"), "town_shop_a": (8, 18, 9, False, "flat"), "town_shop_b": (8, 18, 9, True, "flat"),
    "town_shop_c": (8, 18, 9, False, "flat"), "town_shop_d": (8, 18, 9, True, "flat"), "town_shop_wide": (16, 18, 9, True, "flat"),
    "town_sheriff": (18, 14, 5.5, True, "flat"), "town_depot": (32, 10, 8, True, "hip"), "town_church": (13, 26, 21, True, "church"),
    "town_church_hall": (12, 16, 5, True, "gable"), "town_gas_station": (34, 26, 6, True, "canopy"),
    "town_fastfood": (18, 14, 6, True, "flat"), "town_plaza": (64, 16, 5.5, True, "flat"), "town_inn": (20, 18, 13, True, "hip"),
    "town_motel_office": (10, 9, 4.5, True, "gable"), "town_motel_wing": (26, 10, 4, True, "gable"),
    "town_mill": (64, 24, 14, True, "monitor"), "town_mill_stack": (3.2, 3.2, 34, False, "stack"),
    "town_water_tower": (9, 9, 24, False, "tower"), "town_school": (44, 15, 10, False, "flat"),
    "town_cottage_a": (9, 11, 6, False, "hip"), "town_cottage_b": (9, 11, 6, False, "gable"), "town_cottage_c": (9, 11, 6, False, "gable"),
    "town_house_a": (11, 12, 9, False, "hip"), "town_house_b": (11, 12, 9, False, "hip"), "town_house_c": (11, 12, 7, False, "gable"),
    "town_garage": (7, 7, 3.8, False, "gable"), "town_garage_open": (7, 7, 3.8, True, "gable"), "town_shed": (3, 4, 3, False, "gable"),
}


def B(id_, kind, x, y, yaw=0.0, role=None, **kw):
    """A building: kit name, centre (estate x, y), yaw (deg, CCW: 0 = front faces -Y / south,
    180 = north), role (what it is in the town and the story)."""
    w, d, h, walk, roof = KIT[kind]
    return dict(id=id_, kind=kind, x=float(x), y=float(y), yaw=float(yaw), w=w, d=d, h=h, walkin=walk, roof=roof,
                role=role or kind.replace("town_", ""), **kw)


def layout_buildings():
    out = []
    front_n = MAIN_Y + 9.0          # north-side fronts: carriageway 7.2, angle parking, sidewalk
    front_s = MAIN_Y - 9.0
    # downtown, north side: ten shopfronts shoulder to shoulder from the bridge corner west
    shops = ["a", "b", "c", "a", "d", "c", "a", "b", "c", "a"]
    roles = ["outdoor gear", "coffee", "sweets", "boutique", "bank", "gallery", "boutique", "bakery", "books", "pharmacy"]
    for k, (v, r) in enumerate(zip(shops, roles)):
        out.append(B(f"shop_n{k}", f"town_shop_{v}", -1612 - 8 * k, front_n + 9, 0, r))
    out.append(B("church", "town_church", -1707, front_n + 6 + 13, 0, "church (white steeple; the fellowship hall: the phones)"))
    out.append(B("church_hall", "town_church_hall", -1726, front_n + 8 + 8, 0, "fellowship hall: the table of phones"))
    out.append(B("outfitter", "town_shop_wide", -1748, front_n + 9, 0, "rafting outfitter / fly shop"))
    out.append(B("realty", "town_shop_wide", -1766, front_n + 9, 0, "real estate: estates for sale in the window"))
    out.append(B("inn", "town_inn", -1810, front_n + 6 + 9, 0, "the boutique inn"))
    # downtown, south side (backs to the river walk)
    out.append(B("sheriff", "town_sheriff", -1612, front_s - 7, 180, "sheriff's office: his window watches the bridge"))
    for k, (v, r) in enumerate(zip(["b", "c", "a", "b"], ["diner", "ice cream", "antiques", "wine bar"])):
        out.append(B(f"shop_s{k}", f"town_shop_{v}", -1656 - 8 * k, front_s - 9, 180, r))
    out.append(B("depot", "town_depot", -1735, front_s - 5, 180, "the depot: railroad and history museum (the estate model)"))
    out.append(B("shop_s4", "town_shop_wide", -1775, front_s - 9, 180, "tasting room"))
    # the highway end of town (north side): gas station, drive-through, the strip plaza, the motel
    out.append(B("gas", "town_gas_station", -1880, -727 + 6 + 13, 0, "gas station + convenience store (CB radio; a van in the back lot)"))
    out.append(B("fastfood", "town_fastfood", -1926, -727.5 + 10 + 7, 0, "burger drive-through"))
    out.append(B("plaza", "town_plaza", -1990, -731 + 9 + 8, 0, "strip plaza: video store (the monitor room), laundromat, pharmacy, vacant"))
    out.append(B("motel_office", "town_motel_office", -2040, -737 + 9 + 4.5, 0, "motor lodge office"))
    out.append(B("motel_a", "town_motel_wing", -2066, -737 + 13 + 5 + 10, 0, "motel, the vans' back lot behind"))
    out.append(B("motel_b", "town_motel_wing", -2084, -737 + 8 + 13, -90, "motel"))
    # the roadhouse: the last building before the highway leaves town, on the river by the spur
    out.append(B("bar", "town_bar", -2112, -807, 180, "THE BAR (the roadhouse): the turn"))
    # Church Street (y -662) and the hill behind: houses, garages, the school
    cs = -662.0
    xs_n = [-1612, -1634, -1656, -1678, -1700, -1745, -1767, -1789, -1830, -1852]
    for k, x in enumerate(xs_n):
        out.append(B(f"house_n{k}", f"town_house_{'abc'[k % 3]}", x, cs + 5 + 3 + 6, 0, "house"))
    xs_s = [-1618, -1640, -1662, -1684, -1760, -1782, -1830, -1852]
    for k, x in enumerate(xs_s):
        out.append(B(f"house_s{k}", f"town_house_{'bca'[k % 3]}", x, cs - 5 - 3 - 6, 180, "house"))
    out.append(B("garage_loot", "town_garage_open", -1606, cs + 5 + 3 + 12 + 8, 90, "the garage: the estate's stolen goods"))
    for k, x in enumerate([-1656, -1700, -1767]):
        out.append(B(f"garage{k}", "town_garage", x + 3, cs + 5 + 3 + 12 + 8, 0, "garage"))
    out.append(B("school", "town_school", -1880, -606, 0, "school"))
    # south bank: the mill (brewery + lofts), its stack, the water tower, Mill Hill's rentals
    out.append(B("mill", "town_mill", -1700, -868, 180, "the mill: brewery taproom + lofts (the vans' depot behind)"))
    out.append(B("stack", "town_mill_stack", -1742, -886, 0, "mill stack"))
    out.append(B("water_tower", "town_water_tower", -1640, -905, 0, "water tower"))
    rows = [-940.0, -968.0, -996.0]
    for r_, ry in enumerate(rows):
        for k in range(10):
            x = -1668 - 20 * k
            out.append(B(f"cottage_{r_}_{k}", f"town_cottage_{'abc'[(k + r_) % 3]}", x, ry - 3 - 3 - 5.5, 180,
                         "vacation rental (every one booked; a lockbox on every door)", row=r_))
    return out


# ------------------------------------------------------------------ streets, trails, the rail
STREETS = [
    # (name, points, width, kind) — the road from the estate is "road" (painted lanes)
    ("road_gorge", ROAD_GORGE, 10.0, "road"),
    ("main_street", ROAD_TOWN, 10.0, "road"),
    ("church_street", [(-1592, -731), (-1594, -700), (-1600, -662), (-1700, -662), (-1800, -662), (-1880, -664)], 7.0, "street"),
    ("depot_street", [(-1782, -725), (-1782, -662), (-1786, -630)], 6.5, "street"),
    # the county road north up the Gap Branch: it climbs the hollow at 12% and bends out of sight
    # (the exit; the gap itself is beyond the square)
    ("gap_road", [(-1596, -662), (-1586, -620), (-1576, -560), (-1570, -500), (-1566, -440)], 6.5, "street"),
    ("mill_road", [(-1552, -872), (-1600, -888), (-1650, -912), (-1700, -914), (-1780, -912), (-1870, -912)], 6.5, "street"),
    ("mill_row_0", [(-1655, -940), (-1760, -940), (-1860, -940)], 6.0, "street"),
    ("mill_row_1", [(-1655, -968), (-1760, -968), (-1860, -968)], 6.0, "street"),
    ("mill_row_2", [(-1655, -996), (-1760, -996), (-1860, -996)], 6.0, "street"),
    ("mill_stair_e", [(-1650, -912), (-1652, -940), (-1652, -968), (-1652, -996)], 3.0, "walk"),
    ("mill_stair_w", [(-1870, -912), (-1866, -940), (-1866, -968), (-1866, -996)], 3.0, "walk"),
    # the river walk (greenway) along the north bank, and the fishermen's path up the gorge
    ("river_walk", [(-1600, -778), (-1700, -783), (-1800, -786), (-1900, -790), (-2000, -800)], 3.0, "walk"),
    ("gorge_path", [(-745, -712), (-800, -720), (-900, -731), (-1000, -740), (-1100, -746), (-1200, -752),
                    (-1300, -757), (-1400, -763), (-1480, -770), (-1550, -776), (-1600, -778)], 1.8, "trail"),
    # the Tannery Branch trail behind Mill Hill, up the hollow to the south ridge
    ("tannery_trail", [(-1652, -996), (-1630, -1060), (-1615, -1150), (-1608, -1260), (-1600, -1380), (-1595, -1500), (-1592, -1570)], 1.8, "trail"),
]
# the heritage excursion line: from the depot west along the river, a level crossing over the
# highway, into the Tunnel Knob's portal
RAIL = [(-1705, -752), (-1800, -754), (-1900, -757), (-2000, -763), (-2060, -768), (-2110, -770),
        (-2150, -768), (-2172, -764)]
TUNNEL = dict(x=-2176.0, y=-764.0, yaw=90.0)       # portal face at the end of the cut, facing east
FOOTBRIDGE = dict(a=(-1795.0, -786.0), b=(-1795.0, -830.0))

# ------------------------------------------------------------------ gameplay: exits, hiding, evidence, people
# exits (estate frame rects x0, y0, x1, y1): the runtime reloads into `to` at the same point;
# `to: None` = a later level (marked, not wired). The east one is the seam with the cove.
EXITS = [
    dict(name="cove", to=COVE, rect=[-750.0, -1578.0, -700.0, -42.0], spawn_dx=2.0,
         note="back up the gorge: road, river, path (the cove's own trigger is x < -762)"),
    dict(name="highway_west", to=None, rect=[-2300.0, -870.0, -2255.0, -800.0], note="the highway out west (the roadblock)"),
    dict(name="tunnel", to=None, rect=[-2190.0, -770.0, -2172.0, -758.0], note="the heritage line's tunnel under Tunnel Knob"),
    dict(name="river_down", to=None, rect=[-2300.0, -900.0, -2255.0, -846.0], note="downstream: a raft, or wading"),
    dict(name="gap_road", to=None, rect=[-1600.0, -450.0, -1535.0, -420.0], note="the county road north up the Gap Branch to the gap"),
    dict(name="tannery_trail", to=None, rect=[-1640.0, -1590.0, -1560.0, -1560.0], note="the trail south to the ridge"),
]
HIDES = [
    dict(name="under_depot_platform", x=-1735, y=-743, kind="crawl", note="1.15 m under the freight platform"),
    dict(name="under_bridge_south", x=-1592, y=-826, kind="bank", note="the river bank under the truss's south span"),
    dict(name="under_bridge_north", x=-1578, y=-776, kind="bank", note="under the north span, by the pier"),
    dict(name="bar_deck_underside", x=-2112, y=-819, kind="crawl", note="under the bar's river deck, on the gravel"),
    dict(name="motel_ice_alcove", x=-2060, y=-715, kind="alcove", note="the ice-machine alcove"),
    dict(name="church_tower", x=-1707, y=-716, kind="climb", note="the steeple's bell deck (sees the whole town)"),
    dict(name="raft_racks", x=-1748, y=-780, kind="cover", note="the outfitter's raft racks on the river walk"),
    dict(name="cottage_crawl", x=-1760, y=-930, kind="crawl", note="under a downhill cottage's deck"),
    dict(name="tunnel_mouth", x=-2170, y=-764, kind="dark", note="the tunnel's dark: invaders won't follow far"),
    dict(name="laurel_thicket", x=-1620, y=-1080, kind="thicket", note="rhododendron in the Tannery Branch hollow"),
]
# the cahoots, told by the environment only (brief: "The turn"); vans etc. are massing boxes here
EVIDENCE = [
    dict(name="vans_motel", kind="van", pts=[(-2050, -682), (-2058, -682), (-2066, -682), (-2074, -682), (-2082, -682), (-2090, -682)],
         yaw=0, note="six identical dark vans in the motel's back lot, nose out"),
    dict(name="van_gas", kind="van", pts=[(-1866, -700)], yaw=90, note="a van in the gas station's back lot, doors open"),
    dict(name="vans_bar", kind="van", pts=[(-2128, -790), (-2096, -790)], yaw=0, note="two at the bar"),
    dict(name="vans_mill", kind="van", pts=[(-1672, -890), (-1680, -890)], yaw=90, note="behind the brewery"),
    dict(name="loot", kind="crates", pts=[(-1606, -630), (-1604, -634), (-1608, -626)], yaw=0,
         note="the estate's own furniture in the open garage (the mansion's glTFs: a dining chair, the office lamp, the great room's art)"),
    dict(name="masks", kind="masks", pts=[(-1724, -985)], yaw=0, note="the invaders' masks drying on a cottage's clothesline"),
    dict(name="phones", kind="table", pts=[(-1726, -700)], yaw=0, note="the fellowship hall: every phone on one table"),
    dict(name="monitors", kind="crt", pts=[(-1962, -694)], yaw=0, note="the video store's back room: the estate's camera feeds"),
    dict(name="estate_model", kind="model", pts=[(-1738, -742)], yaw=0, note="the museum's vitrine: a scale model of the estate"),
    dict(name="back_room", kind="masks", pts=[(-2122, -800)], yaw=0, note="the bar's back room: masks on hooks"),
]
VEHICLES = [   # (kind, x, y, yaw deg): townspeople's cars, the cruiser, the heritage train
    ("cruiser", -1598, -735, 90), ("suv", -1640, -717, 0), ("car", -1660, -717, 0), ("pickup", -1690, -717, 0),
    ("suv", -1720, -717, 0), ("car", -1760, -717, 0), ("car", -1668, -733, 180), ("suv", -1700, -733, 180),
    ("pickup", -1890, -712, 0), ("car", -1930, -718, 90), ("suv", -2004, -712, 0), ("car", -2020, -712, 0),
    ("pickup", -2112, -790, 0), ("train", -1745, -752, 90),
]
PEOPLE = [   # the townspeople's posts (stand-ins): role, where, facing (estate deg, 0 = north)
    dict(role="sheriff", x=-1612, y=-733, face=180, note="on the bench outside his office, watching the bridge"),
    dict(role="barista", x=-1620, y=-713, face=180), dict(role="museum docent", x=-1730, y=-741, face=0),
    dict(role="outfitter", x=-1750, y=-780, face=180, note="at the raft racks"),
    dict(role="gas attendant", x=-1880, y=-713, face=180), dict(role="drive-through", x=-1926, y=-704, face=90),
    dict(role="video clerk", x=-1962, y=-702, face=180), dict(role="motel manager", x=-2040, y=-718, face=180),
    dict(role="bartender", x=-2105, y=-806, face=0), dict(role="man on a porch", x=-1678, y=-647, face=180),
    dict(role="woman watering baskets", x=-1650, y=-716, face=180), dict(role="jogger", x=-1700, y=-783, face=90),
]
SPAWN = dict(pos=(-760.0, -786.5), look=(-860.0, -797.0))      # the road at the seam, looking down the gorge


def views():
    """Named eye-height views (estate frame): pos (x, y[, z over ground]), look (x, y, z abs or None)."""
    return dict(
        spawn=dict(pos=SPAWN["pos"], look=(*SPAWN["look"], None)),
        seam_road=dict(pos=(-760, -786.5), look=(-860, -797, -166.5)),
        seam_river=dict(pos=(-758, -718), look=(-900, -735, None)),
        gorge_mouth=dict(pos=(-1405, -828), look=(-1700, -760, -175.0)),
        gorge_mouth_river=dict(pos=(-1420, -766), look=(-1700, -760, -178.0)),
        bridge_approach=dict(pos=(-1572, -872), look=(-1585, -760, -176.0)),
        bridge_deck=dict(pos=(-1585, -830, 1.65), look=(-1600, -700, -178.0)),
        main_street=dict(pos=(-1605, -726), look=(-1800, -724, -180.0)),
        church_street=dict(pos=(-1605, -662), look=(-1800, -664, -178.0)),
        river_walk=dict(pos=(-1610, -779), look=(-1800, -786, -183.0)),
        strip=dict(pos=(-1850, -727), look=(-2050, -720, -180.0)),
        motel_lot=dict(pos=(-2040, -672), look=(-2070, -684, -184.0)),
        bar_lot=dict(pos=(-2100, -768), look=(-2112, -800, -181.0)),
        mill_hill=dict(pos=(-1760, -996), look=(-1700, -800, -182.0)),
        steeple=dict(pos=(-1707, -720, 17.0), look=(-1900, -760, -186.0)),
    )


# ------------------------------------------------------------------ the guide (the macro terrain)
def cove_data():
    D = os.path.join(terrain.OUT_ROOT, COVE)
    z = np.load(os.path.join(D, "terrain.npz"))
    st = json.load(open(os.path.join(D, "stats.json")))
    return z, st


def cove_holes():
    """The cove backdrop's flat holes over the corridor and the town (laurel_fork terrain_overrides):
    (x0, y0, x1, y1, h, blend) in estate x / local y."""
    import laurel_fork as LF
    ov = LF.terrain_overrides(1.5)
    return ov["backdrop"]["holes"][1:]


def cove_natural(Hb, gb, Xl_e, Yl):
    """The cove's backdrop at (estate x, local y) with its corridor / town holes undone where they
    are weak (Hb = nat + (h - nat) w  ->  nat), and a confidence weight (1 - w)."""
    hb = terrain.sample(Hb, gb, Xl_e, Yl)
    conf = np.ones_like(hb)
    holes = cove_holes()
    nat = hb
    for x0, y0, x1, y1, hh, bl in holes[::-1]:
        ex = np.maximum(np.maximum(x0 - Xl_e, Xl_e - x1), 0)
        ey = np.maximum(np.maximum(y0 - Yl, Yl - y1), 0)
        w = 1 - terrain.smoothstep(0, bl, np.hypot(ex, ey))
        nat = np.where(w < 0.8, (nat - hh * w) / np.maximum(1 - w, 0.2), nat)
        conf *= 1 - w
    return nat, conf


def lot_pads(H, grid, buildings, streets_z=None):
    """Flatten each building's footprint (+1.5 m) to its pad height, banks at 33 deg fill / 45 cut
    within 14 m. Cottages (hill lots, on piers): the pad is the street side's ground (the back
    hangs over the slope: `below_m`)."""
    X, Y = grid.xy()
    t33, t45 = math.tan(math.radians(33)), math.tan(math.radians(45))
    for b in buildings:
        cx, cy = local((b["x"], b["y"]))
        a = math.radians(b["yaw"])
        hx, hy = b["w"] / 2 + 1.5, b["d"] / 2 + 1.5
        R = math.hypot(hx, hy) + 16
        i0, i1 = max(0, int((cx - R - grid.x0) / grid.cell)), min(grid.nx, int((cx + R - grid.x0) / grid.cell) + 2)
        j0, j1 = max(0, int((cy - R - grid.y0) / grid.cell)), min(grid.ny, int((cy + R - grid.y0) / grid.cell) + 2)
        if i0 >= i1 or j0 >= j1:
            continue
        sl = (slice(j0, j1), slice(i0, i1))
        dx, dy = X[sl] - cx, Y[sl] - cy
        u = dx * math.cos(a) + dy * math.sin(a)
        v = -dx * math.sin(a) + dy * math.cos(a)
        e = np.hypot(np.maximum(np.abs(u) - hx, 0), np.maximum(np.abs(v) - hy, 0))
        inside = e <= 0
        Hs = H[sl]
        if b["kind"].startswith("town_cottage"):
            # a hill lot: the pad is the street (front) edge's ground; only the front half is cut
            # level (the porch, the piers' footings), the back keeps the slope under the piers
            front = inside & (v < -b["d"] / 2 + 2.5)
            z = float(np.median(Hs[front])) if front.any() else float(np.median(Hs[inside]))
            e2 = np.hypot(np.maximum(np.abs(u) - hx, 0), np.maximum(-hy - v, 0) + np.maximum(v, 0))
            clamped = np.clip(Hs, z - e2 * t33, z + e2 * t45)
            Hs = Hs + (clamped - Hs) * (1 - terrain.smoothstep(8.0, 14.0, e2))
            b["below_m"] = round(max(0.0, float(z - Hs[inside].min())), 2)
        else:
            z = b.get("pad")
            if z is None:
                z = float(np.median(Hs[inside]))
            b["below_m"] = 0.0
            clamped = np.clip(Hs, z - e * t33, z + e * t45)
            wgt = 1 - terrain.smoothstep(10.0, 16.0, e)
            Hs = Hs + (clamped - Hs) * wgt
        b["z"] = round(z, 2)
        H[sl] = Hs
    return H


def bench(H, grid, pts_e, z0, z1, core, reach=28.0, flat_after=None):
    """A graded bench (the road down the gorge): the line's heights fall linearly by arc length
    from z0 to z1 (then hold), the corridor cut and filled into the slope."""
    P = terrain.spline([local(q) for q in pts_e], 1.5)
    s = np.concatenate([[0], np.cumsum(np.hypot(*(P[1:, :2] - P[:-1, :2]).T))])
    L = s[-1] if flat_after is None else flat_after
    hp = z0 + (z1 - z0) * np.clip(s / L, 0, 1)
    return H + terrain.corridor(H, grid, P[:, :2], hp, core, 34.0, reach, 3.0, 50.0), P, hp


def build_guide(cell=CELL, buildings=None, erode=True):
    """The macro terrain for terrain.build (as a .npy guide, guide_height 1, no shapes, no detail,
    no erosion): the valley field, blended into the cove's own heights at the seam and the cove's
    backdrop at the square's north / south edges; the road's bench down the gorge; the lots."""
    n = int(round(SIZE / cell)) + 1
    grid = terrain.Grid(-HALF, -HALF, cell, n, n)
    Xl, Yl = grid.xy()
    Xe, Ye = Xl + CX, Yl - OY
    noise = terrain.Noise(SEED)
    H = valley_field(Xe, Ye, noise)
    # stream-power erosion on the hillsides only (dendritic hollows; the floor and lots untouched)
    if erode:
        dH = terrain.fluvial(H, cell, dict(on=True, factor=4, iters=60, k=0.05, m=0.5, diffusion=0.6))
        yr = river_y(Xe)
        e = np.abs(Ye - yr) - RIVER_HW
        F = np.where(Ye > yr, _ix(Xe, FLOOR_X, FLOOR_N), _ix(Xe, FLOOR_X, FLOOR_S))
        H = H + dH * terrain.smoothstep(F + 15.0, F + 60.0, e)
    zc, st = cove_data()
    bst = st["backdrop"]
    gb = terrain.Grid(-bst["extent"] / 2, -bst["extent"] / 2, bst["cell"], bst["samples"][0], bst["samples"][1])
    Hb = zc["Hb"].astype(np.float64)
    nat, conf = cove_natural(Hb, gb, Xe, Yl)
    # north / south edges: the cove's (natural) backdrop, over 160 m
    dn = np.minimum(HALF - Yl, Yl + HALF)
    w_edge = (1 - terrain.smoothstep(0.0, 160.0, dn)) * np.clip(conf * 3, 0, 1)
    H = H + (nat - H) * w_edge
    # the seam: the cove's fine heights east of SEAM_X; west of it the cove's continuation (its
    # backdrop + the fine field's edge offset, decaying over 30 m) blends into the valley over 55 m
    Hc = zc["H"].astype(np.float64)
    gc = terrain.Grid(st["grid"]["x0"], st["grid"]["y0"], st["grid"]["cell"], st["grid"]["nx"], st["grid"]["ny"])
    rl = zc["river_level"].astype(np.float64)
    Hc_fill = np.where(np.isfinite(rl), np.maximum(Hc, rl + 0.25), Hc)        # the cove's channel, filled to water + 0.25
    edge_y = Yl[:, 0]
    fine_edge = terrain.sample(Hc_fill, gc, np.full_like(edge_y, SEAM_X + 0.01), edge_y)
    nat_edge, _ = cove_natural(Hb, gb, np.full_like(edge_y, SEAM_X - 0.01), edge_y)
    off = (fine_edge - nat_edge)[:, None]
    dxs = np.clip(SEAM_X - Xe, 0, None)
    cont = nat + off * (1 - terrain.smoothstep(0.0, 30.0, dxs))
    w_c = terrain.smoothstep(SEAM_X - 62.0, SEAM_X - 7.0, Xe) * np.clip(conf * 2.5, 0, 1)
    H = H + (cont - H) * w_c
    # the river's channel stays open through the blend (the cove's continuation would dam it): its
    # bed line at water + 0.25, banks no steeper than 31 deg, falling west from the cove's water
    dyr = np.abs(Ye - river_y(Xe)) - RIVER_HW
    chan = water_z(Xe) + 0.25 + np.clip(dyr, 0, None) * 1.0
    H = np.where((Xe < SEAM_X) & (dyr < 14), np.minimum(H, chan), H)
    inside = Xe >= SEAM_X
    fine = terrain.sample(Hc_fill, gc, np.where(inside, Xe, SEAM_X), Yl)
    H = np.where(inside, fine, H)
    # no pits (the hill foot's incision would hold ponds): fill to drain, before the road's fills
    # and the lots, whose small dams the hydrology routes over
    H = terrain.priority_flood(H, 1e-3)
    H = np.where(inside, fine, H)
    # the road's bench down the gorge (west of the seam), then the south flats to the bridge
    H, P, hp = bench(H, grid, ROAD_GORGE[1:], ROAD_Z0 - 0.4, ROAD_Z1, 6.0, flat_after=None)
    keep = Xe >= SEAM_X - 3
    H = np.where(keep, np.where(inside, fine, H), H)
    if buildings:
        H = lot_pads(H, grid, buildings)
    # the seam exact: whatever the fills and the bench left at the seam column is ramped out over
    # 40 m west of it (the run east of the seam is the cove's, patched in node for node)
    k = int(round((SEAM_X - CX + HALF) / cell))
    off = (H[:, k] - H[:, k - 1])[:, None]
    H = np.where(Xe < SEAM_X, H + off * (1 - terrain.smoothstep(0.0, 40.0, SEAM_X - Xe)), H)
    return H, grid


def terrain_overrides(cell=CELL, guide_path=None):
    def path(name, pts, width, kind):
        road = kind in ("road", "street")
        return dict(name=name, width=width, shoulder=3.0 if road else 2.0, max_grade=0.06 if kind == "road" else 0.12 if road else 0.30,
                    smooth=30.0 if road else 12.0, ford=not road, bank_deg=33.0, cut_deg=48.0,
                    reach=18.0 if road else 10.0, road=road, trail=kind in ("trail", "walk"),
                    points=[local(q) for q in pts],
                    **({"switchbacks": dict(half_width=45.0)} if name in ("gap_road", "tannery_trail") else {}))
    paths = [path(*s) for s in STREETS]
    paths.append(dict(name="rail", width=4.0, shoulder=2.5, max_grade=0.015, smooth=40.0, ford=True, bank_deg=33.0,
                      cut_deg=55.0, reach=14.0, road=False, points=[local(q) for q in RAIL]))
    return dict(
        name=NAME, seed=SEED, size=SIZE, cell=cell, base=0.0, tilt=(0.0, 0.0), shapes=[], shape_jitter=0.0,
        guide=guide_path, guide_height=1.0,
        detail=dict(warp=0.0, warp_wavelength=600.0, low_amp=0.0, low_wavelength=280.0, high_amp=0.0, high_wavelength=320.0,
                    mountain=(0.1, 0.7)),
        erosion=dict(fluvial=dict(on=False), droplets=dict(on=False), thermal=dict(on=False)),
        hydro=dict(river_area=8.0e5, width_k=8.0, width=(2.5, 34.0), depth_k=0.07, depth0=0.6, bank_drop=0.25, bank_w=5.0,
                   inflows=[dict(name="laurel_river", x=local((-800.0, -742.0))[0], y=local((-800.0, -742.0))[1], r=8.0, area=3.4e8)],
                   bank_deg=18.0, lake_min_area=300.0, lake_min_depth=6.0, freeboard=0.2, beach_w=3.0, beach_deg=12.0),
        knicks=[], cliffs=[], pads=[], paths=paths,
        masks=dict(rock_deg=(48.0, 58.0), cliff_rock=1.0),
        palette=dict(grass=(0.045, 0.075, 0.025), dry=(0.13, 0.085, 0.045), alpine=(0.05, 0.07, 0.035),
                     rock=(0.20, 0.20, 0.18), scree=(0.11, 0.12, 0.08), dirt=(0.10, 0.07, 0.04),
                     gravel=(0.22, 0.19, 0.14), mud=(0.12, 0.09, 0.05), forest=(0.035, 0.06, 0.025)),
        backdrop=dict(holes=[], rock_deg=(44.0, 56.0), frame_height=0.0, frame_wavelength=1100.0),
    )


def build_terrain(cell=CELL, name=NAME):
    bl = layout_buildings()
    H, grid = build_guide(cell, bl)
    D = os.path.join(terrain.OUT_ROOT, name)
    os.makedirs(D, exist_ok=True)
    gp = os.path.join(D, "guide.npy")
    np.save(gp, H.astype(np.float64))
    with open(os.path.join(D, "buildings.json"), "w") as fh:
        json.dump(bl, fh, indent=0)
    ov = terrain_overrides(cell, gp)
    ov["name"] = name
    return terrain.build(**ov)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", default="terrain,world")
    ap.add_argument("--name", default=NAME)
    a = ap.parse_args()
    t0 = time.time()
    if "terrain" in a.steps:
        st = build_terrain(CELL, a.name)
        for pth in st["paths"]:
            print(f"  path {pth['name']:14s} {pth['length_m']:7.1f} m  grade {pth['max_grade']}  cut/fill max {pth['max_cut_fill_m']} m "
                  f"at {pth['max_cut_fill_at']}")
    if "world" in a.steps:
        import laurel_town_world
        laurel_town_world.run(a.name)
    print(f"done in {time.time() - t0:.0f} s")
