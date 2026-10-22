"""Sourwood (laurel_town): terrain run -> the runtime world (viewer/wild.html?world=laurel_town).

The same files as laurel_fork_world (viewer/wild/load_world.js's contract) plus world.json "town":
the buildings by kit name (massing boxes until the kit's glTFs exist), streets and the road with
their heights, the truss bridge and the footbridge, the heritage line's tunnel, vehicles, the
cahoots evidence, the townspeople's posts, hiding places and exits (viewer/wild/town.js draws and
wires them).

Frame: world.json positions are in the TOWN frame, x = estate x - CX (= terrain local x), y =
estate y, so level.js's prop code (three = (x, z, -(y - estate_offset[1]))) works unchanged;
estate_offset = [CX, -OY] says how to get back to the estate frame (exits, epos=).

In the overlap with the cove square (estate x >= -768) the heights and water are the cove's own,
copied node for node (the grids share their 1.5 m lattice), so the seam is exact.

  $PY blender/wilderness/levels/laurel_town_world.py [run]
"""
import json
import math
import os
import shutil
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import terrain  # noqa: E402
import laurel_town as LT  # noqa: E402
import laurel_fork_world as LFW  # noqa: E402

OY, CX = LT.OY, LT.CX
SEED = 47
PROJECT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SPECIES = LFW.SPECIES


def tx(x):
    """estate x -> town frame x (terrain local)."""
    return float(x) - CX


class TRun:
    """A terrain run in the town frame (x local, y estate), the cove's heights patched in east of
    the seam; the same attributes as laurel_fork_checks.Run, so laurel_fork_world's helpers work."""
    def __init__(self, name):
        self.dir = os.path.join(terrain.OUT_ROOT, name)
        self.stats = json.load(open(os.path.join(self.dir, "stats.json")))
        z = np.load(os.path.join(self.dir, "terrain.npz"))
        self.H = z["H"].astype(np.float64)
        self.river_level, self.lake_level = z["river_level"].astype(np.float64), z["lake_level"].astype(np.float64)
        g = self.stats["grid"]
        self.cell, self.n = g["cell"], g["nx"]
        self.grid = terrain.Grid(g["x0"], g["y0"], g["cell"], g["nx"], g["ny"])
        x = g["x0"] + np.arange(self.n) * self.cell
        self.X, self.Y = np.meshgrid(x, x - OY)
        self._m = {}
        # the seam: node-for-node the cove's heights and water (same lattice: column i here = column
        # i - 1000 there)
        zc = np.load(os.path.join(terrain.OUT_ROOT, LT.COVE, "terrain.npz"))
        k0 = int(round((LT.SEAM_X - CX - g["x0"]) / self.cell))
        self.seam_col = k0
        nk = self.n - k0
        self.seam_diff = float(np.abs(self.H[:, k0:] - zc["H"][:, :nk]).max())
        self.H[:, k0:] = zc["H"][:, :nk]
        self.river_level[:, k0:] = zc["river_level"][:, :nk]
        self.lake_level[:, k0:] = zc["lake_level"][:, :nk]

    def mask(self, k):
        if k not in self._m:
            self._m[k] = terrain.read_png_fast(os.path.join(self.dir, "masks", f"{k}.png"))[::-1].astype(np.float64) / 255
        return self._m[k]

    def h(self, x, y):
        return terrain.height_at(self.H, self.grid, np.asarray(x, float), np.asarray(y, float) + OY)

    def ij(self, x, y):
        i = np.clip(np.round((np.asarray(x) - self.grid.x0) / self.cell).astype(int), 0, self.n - 1)
        j = np.clip(np.round((np.asarray(y) + OY - self.grid.y0) / self.cell).astype(int), 0, self.n - 1)
        return j, i


def obox(cx, cy, w, d, yaw_deg):
    """Corners of a yawed rectangle (town frame)."""
    a = math.radians(yaw_deg)
    c, s = math.cos(a), math.sin(a)
    return [(cx + u * c - v * s, cy + u * s + v * c) for u, v in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2))]


def rect_mask(R, cx, cy, w, d, yaw, grow=0.0):
    a = math.radians(yaw)
    dx, dy = R.X - cx, R.Y - cy
    u = dx * math.cos(a) + dy * math.sin(a)
    v = -dx * math.sin(a) + dy * math.cos(a)
    return (np.abs(u) <= w / 2 + grow) & (np.abs(v) <= d / 2 + grow)


def building_parts(b):
    """The massing in the asset frame (x across, y back, z up; front at -y): boxes
    [x0, y0, z0, x1, y1, z1, colour key] and, for walk-ins, a shell with a door gap. The runtime
    draws them and the colliders come from them."""
    w, d, h, kind = b["w"], b["d"], b["h"], b["kind"]
    P = []
    below = b.get("below_m", 0.0)
    if kind == "town_water_tower":
        for sx in (-1, 1):
            for sy in (-1, 1):
                P.append([sx * 3.0 - 0.3, sy * 3.0 - 0.3, 0, sx * 3.0 + 0.3, sy * 3.0 + 0.3, h - 7.5, "steel"])
        P.append([-4.2, -4.2, h - 8.0, 4.2, 4.2, h - 2.2, "tank"])
        return P
    if kind == "town_mill_stack":
        return [[-1.6, -1.6, 0, 1.6, 1.6, h, "brick_dark"]]
    if kind == "town_gas_station":
        # the canopy over the pumps at the front, the store at the back
        P.append([-w / 2, -d / 2, 4.8, w / 2, -d / 2 + 13, 5.6, "canopy"])
        for px in (-11, 0, 11):
            P.append([px - 0.3, -d / 2 + 5.5, 0, px + 0.3, -d / 2 + 6.1, 4.8, "steel"])
            P.append([px - 1.6, -d / 2 + 6.4, 0, px + 1.6, -d / 2 + 7.2, 1.8, "pump"])
        sx0, sx1, sy0, sy1 = -13, 13, -d / 2 + 15, d / 2
        P += shell(sx0, sy0, sx1, sy1, 4.6, door=(-1.0, 1.0), col="block", glass=True)
        return P
    if b["walkin"]:
        roof_h = h if b["roof"] == "flat" else min(h, 4.2 if h < 7 else 4.6)
        P += shell(-w / 2, -d / 2, w / 2, d / 2, roof_h, door=(-0.8, 0.8) if w < 12 else (-1.2, 1.2), col=b["kind"], glass=True)
    else:
        body = h if b["roof"] == "flat" else h * (0.62 if b["roof"] in ("gable", "hip") else 0.6)
        P.append([-w / 2, -d / 2, -below - 0.3, w / 2, d / 2, body, kind])
    if kind == "town_church":
        P.append([-2.2, -d / 2 - 0.5, 0, 2.2, -d / 2 + 3.9, 14.0, "white"])      # the steeple's tower
    return P


def shell(x0, y0, x1, y1, h, door=(-0.8, 0.8), col="wall", glass=False, t=0.25):
    """Four walls with a door gap in the front (y0) wall, and a roof slab."""
    P = [[x0, y1 - t, 0, x1, y1, h, col], [x0, y0, 0, x0 + t, y1, h, col], [x1 - t, y0, 0, x1, y1, h, col],
         [x0, y0, 0, door[0], y0 + t, h, col], [door[1], y0, 0, x1, y0 + t, h, col],
         [door[0], y0, 2.3, door[1], y0 + t, h, col], [x0, y0, h, x1, y1, h + 0.3, "roof"]]
    if glass:
        P.append([x0 + 1.0, y0 - 0.02, 0.9, door[0] - 0.6, y0 + 0.02, 2.4, "glass"])
        P.append([door[1] + 0.6, y0 - 0.02, 0.9, x1 - 1.0, y0 + 0.02, 2.4, "glass"])
    return P


def roof_of(b):
    """The roof massing the runtime draws (not a collider): kind, eave and ridge heights."""
    w, d, h, r = b["w"], b["d"], b["h"], b["roof"]
    if r in ("gable", "hip", "church"):
        eave = h * 0.62 if not b["walkin"] else min(h, 4.2 if h < 7 else 4.6) + 0.3
        ridge = h if r != "church" else 11.0
        return dict(kind="hip" if r == "hip" else "gable", eave=round(eave, 2), ridge=round(max(ridge, eave + 1.5), 2))
    if r == "monitor":
        return dict(kind="gable", eave=round(h * 0.85, 2), ridge=round(h, 2))
    if r == "church":
        return dict(kind="gable", eave=7.0, ridge=11.0)
    return None


def colliders(R, trees, town):
    out = []

    def box3(xmin, xmax, ymin, ymax, zmin, zmax):
        out.append((xmin, zmin, -(ymax + OY), xmax, zmax, -(ymin + OY)))

    for x, y, sp, size in zip(trees["x"], trees["y"], trees["sp"], trees["size"]):
        t = SPECIES[sp]["trunk"] * size
        if t < 0.08:
            continue
        g = float(R.h(x, y))
        box3(x - t * 0.85, x + t * 0.85, y - t * 0.85, y + t * 0.85, g - 1.0, g + 7.0)

    def part_boxes(cx, cy, z, yaw, p):
        """An asset-frame box -> AABBs (exact for yaw 0/90/180/270, else strips along its long side)."""
        x0, y0, z0, x1, y1, z1 = p[:6]
        a = math.radians(yaw)
        c, s = math.cos(a), math.sin(a)
        q = round((yaw % 360) / 90.0)
        if abs((yaw % 360) - q * 90) < 0.5:
            pts = [(cx + u * c - v * s, cy + u * s + v * c) for u, v in ((x0, y0), (x1, y1))]
            box3(min(pts[0][0], pts[1][0]), max(pts[0][0], pts[1][0]), min(pts[0][1], pts[1][1]), max(pts[0][1], pts[1][1]), z + z0, z + z1)
            return
        long_x = (x1 - x0) >= (y1 - y0)
        n = max(1, int(max(x1 - x0, y1 - y0) / 1.0))
        for k in range(n):
            if long_x:
                ua, ub, va, vb = x0 + (x1 - x0) * k / n, x0 + (x1 - x0) * (k + 1) / n, y0, y1
            else:
                ua, ub, va, vb = x0, x1, y0 + (y1 - y0) * k / n, y0 + (y1 - y0) * (k + 1) / n
            cs = [(cx + u * c - v * s, cy + u * s + v * c) for u in (ua, ub) for v in (va, vb)]
            xs, ys = [p_[0] for p_ in cs], [p_[1] for p_ in cs]
            # (shrunk a little: the strips' corners overshoot the yawed rectangle)
            sh = 0.15 * min(max(xs) - min(xs), max(ys) - min(ys))
            box3(min(xs) + sh, max(xs) - sh, min(ys) + sh, max(ys) - sh, z + z0, z + z1)

    for b in town["buildings"]:
        for p in b["parts"]:
            if p[6] in ("glass", "canopy"):
                continue
            part_boxes(b["x"], b["y"], b["z"], b["yaw"], p)
    # bridges: the truss deck (short boxes, each a step <= 5 cm), the trusses as side walls
    for br in town["bridges"]:
        (ax, ay), (bx, by) = br["a"], br["b"]
        L = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / L, (by - ay) / L
        hw = br["width"] / 2
        n = int(L / 0.8) + 1
        for k in range(n):
            t0, t1 = k / n, (k + 1) / n
            xa, ya, xb, yb = ax + ux * L * t0, ay + uy * L * t0, ax + ux * L * t1, ay + uy * L * t1
            z = br["za"] + (br["zb"] - br["za"]) * (t0 + t1) / 2
            ex, ey = abs(uy) * hw, abs(ux) * hw
            box3(min(xa, xb) - ex, max(xa, xb) + ex, min(ya, yb) - ey, max(ya, yb) + ey, z - 0.6, z)
            for sd in (-1, 1):
                rx, ry = (xa + xb) / 2 - uy * (hw + 0.15) * sd, (ya + yb) / 2 + ux * (hw + 0.15) * sd
                box3(rx - max(abs(xb - xa) / 2, 0.15), rx + max(abs(xb - xa) / 2, 0.15),
                     ry - max(abs(yb - ya) / 2, 0.15), ry + max(abs(yb - ya) / 2, 0.15), z, z + (br["rail"]))
    for v in town["vehicles"]:
        L, W, Hh = VEH[v["kind"]]
        part_boxes(v["x"], v["y"], v["z"], v["yaw"] - 90, [-L / 2, -W / 2, 0, L / 2, W / 2, Hh])
    return np.array(out, np.float32)


# vehicles and evidence massing: (length along its heading, width, height)
VEH = dict(van=(5.9, 2.1, 2.5), cruiser=(5.1, 2.0, 1.8), suv=(4.9, 1.9, 1.7), car=(4.8, 1.85, 1.45), pickup=(5.9, 2.0, 1.9),
           train=(57.0, 3.1, 4.5), crates=(2.4, 1.2, 1.6), masks=(1.6, 0.4, 1.8), table=(2.4, 0.8, 0.8), crt=(4.0, 0.6, 2.4),
           model=(3.0, 2.0, 1.2))


def communities(R, town_clear, street_d):
    """A simple split for the town square: water, the cleared town (lots, streets, lawns), the
    riverbank, cove / oak / crest forest on the hills (the cove's rules, cut down), rock."""
    CID = LFW.CID
    slope, wet, curv = R.mask("slope") * 90, R.mask("wetness"), R.mask("curvature")
    asp = R.mask("aspect") * 360
    water = (R.mask("rivers") > 0.5) | (R.mask("lakes") > 0.5)
    _, _, dwc = terrain.nearest_seed(water)
    dw = dwc * R.cell
    noise = terrain.Noise(SEED)
    n1 = noise.fbm(R.X, R.Y, 90.0, 3)
    northish = (np.cos(np.radians(asp)) > 0.2)
    southish = (asp > 140) & (asp < 290)
    C = np.full(R.H.shape, CID["oak"], np.int8)
    C[((curv < 0.47) | (wet > 0.55)) & ~southish] = CID["cove"]
    C[northish & ~southish & (curv < 0.53)] = CID["cove"]
    C[(curv > 0.56) & (R.H > -60)] = CID["crest"]
    C[dw < 14 + 6 * n1] = CID["ripar"]
    C[(slope > 50)] = CID["rock"]
    C[town_clear] = CID["estate"]
    C[water] = CID["water"]
    return C, dw, slope


def run(name=LT.NAME):
    t0 = time.time()
    R = TRun(name)
    out_dir = os.path.join(R.dir, "world")
    os.makedirs(out_dir, exist_ok=True)
    r = np.random.default_rng(SEED)
    st = R.stats
    routed = {k: [(x, y - OY) for x, y in v] for k, v in st["routed_paths"].items()}   # local x, estate y
    kinds = {s[0]: (s[2], s[3]) for s in LT.STREETS}
    kinds["rail"] = (4.0, "rail")
    # ---- the town's data in the town frame
    bl = json.load(open(os.path.join(R.dir, "buildings.json")))
    kit_avail = sorted({b["kind"] for b in bl} | {"town_truss_span", "town_bridge_pier", "town_footbridge", "town_tunnel_portal"})
    kit_avail = [k for k in kit_avail if os.path.exists(os.path.join(PROJECT, "assets", "models", f"{k}.gltf"))]
    buildings = []
    for b in bl:
        x, y = tx(b["x"]), b["y"]
        # the pad as built (the final surface's median over the footprint; the piers' cottages: the front)
        m = rect_mask(R, x, y, b["w"], b["d"], b["yaw"])
        z = float(np.median(R.H[m])) if m.any() else float(R.h(x, y))
        if b["kind"].startswith("town_cottage"):
            z = b["z"]
            b["below_m"] = round(max(0.0, z - float(R.H[m].min())) if m.any() else 0.0, 2)
        bb = dict(b, x=round(x, 2), y=round(y, 2), z=round(z, 2))
        bb["parts"] = [[round(v, 3) if isinstance(v, float) else v for v in p] for p in building_parts(bb)]
        bb["roof_shape"] = roof_of(bb)
        bb["kit"] = b["kind"] in kit_avail
        buildings.append(bb)
    # streets: the routed polylines with their final heights (the runtime lays asphalt / lanes on them)
    streets = []
    for nm, pts in routed.items():
        w, kind = kinds.get(nm, (4.0, "street"))
        if kind in ("trail",):
            continue
        P = terrain.spline([(x, y) for x, y in pts], 2.0)[:, :2]
        z = R.h(P[:, 0], P[:, 1])
        streets.append(dict(name=nm, kind=kind, width=w, pts=[[round(float(a), 2), round(float(c), 2), round(float(e), 3)] for a, c, e in zip(P[:, 0], P[:, 1], z)]))
    # the truss bridge (road) and the footbridge: deck ends on the ground at each abutment
    def bridge(kind, a, b_, width, rail, spans=1):
        a = (tx(a[0]), a[1]); b_ = (tx(b_[0]), b_[1])
        za, zb = float(R.h(*a)) + 0.05, float(R.h(*b_)) + 0.05
        wl = R.river_level
        mid = ((a[0] + b_[0]) / 2, (a[1] + b_[1]) / 2)
        j, i = R.ij(*mid)
        water = float(np.nanmedian(wl[max(0, j - 6):j + 7, max(0, i - 6):i + 7])) if np.isfinite(wl[max(0, j - 6):j + 7, max(0, i - 6):i + 7]).any() else za - 5
        return dict(kind=kind, a=[round(a[0], 2), round(a[1], 2)], b=[round(b_[0], 2), round(b_[1], 2)], za=round(za, 2), zb=round(zb, 2),
                    width=width, rail=rail, spans=spans, water=round(water, 2), kit="town_truss_span" in kit_avail if kind == "truss" else False)
    bridges = [bridge("truss", LT.BRIDGE["a"], LT.BRIDGE["b"], LT.BRIDGE["width"], 1.3, LT.BRIDGE["spans"]),
               bridge("foot", LT.FOOTBRIDGE["a"], LT.FOOTBRIDGE["b"], 2.5, 1.1)]
    vehicles = []
    for kind, x, y, yaw in LT.VEHICLES:
        vehicles.append(dict(kind=kind, x=round(tx(x), 2), y=y, z=round(float(R.h(tx(x), y)), 2), yaw=yaw, role="townspeople" if kind != "cruiser" else "sheriff"))
    evidence = []
    for ev in LT.EVIDENCE:
        for (x, y) in ev["pts"]:
            k = ev["kind"]
            rec = dict(name=ev["name"], kind=k, x=round(tx(x), 2), y=y, z=round(float(R.h(tx(x), y)), 2), yaw=ev.get("yaw", 0) + 90, note=ev["note"])
            evidence.append(rec)
            if k == "van":
                vehicles.append(dict(rec, role="invaders"))
    # inside a building, evidence stands on its floor (the pad), not the terrain under it
    for ev in evidence:
        for b in buildings:
            if rect_mask_pt(ev["x"], ev["y"], b):
                ev["z"] = b["z"]
                ev["in"] = b["id"]
    people = [dict(p, x=round(tx(p["x"]), 2), z=round(float(R.h(tx(p["x"]), p["y"])), 2)) for p in LT.PEOPLE]
    for p in people:
        for b in buildings:
            if rect_mask_pt(p["x"], p["y"], b):
                p["z"] = b["z"]
    hides = [dict(h, x=round(tx(h["x"]), 2), z=round(float(R.h(tx(h["x"]), h["y"])), 2)) for h in LT.HIDES]
    tun = LT.TUNNEL
    town = dict(name="Sourwood", frame="town: x = estate x - %.0f, y = estate y" % CX, buildings=buildings, streets=streets,
                bridges=bridges, vehicles=vehicles, evidence=evidence, people=people, hides=hides,
                tunnel=dict(x=round(tx(tun["x"]), 2), y=tun["y"], z=round(float(R.h(tx(tun["x"]), tun["y"])), 2), yaw=tun["yaw"]),
                exits=LT.EXITS, road_in=LT.ROAD_IN, kit=kit_avail)
    # ---- clearings, communities, trees
    clear = np.zeros(R.H.shape, bool)
    street_d = np.full(R.H.shape, np.inf)
    for s in streets:
        P = np.array([[q[0], q[1] + OY] for q in s["pts"]])
        d, _, _, _ = terrain.poly_field(R.grid, P, 30.0)
        street_d = np.minimum(street_d, np.where(np.isfinite(d), d - s["width"] / 2, np.inf))
    trail_d = np.full(R.H.shape, np.inf)
    for nm, pts in routed.items():
        if kinds.get(nm, ("", ""))[1] == "trail":
            d, _, _, _ = terrain.poly_field(R.grid, np.array([[x, y + OY] for x, y in pts]), 20.0)
            trail_d = np.minimum(trail_d, d)
    lots = np.zeros(R.H.shape, bool)
    for b in buildings:
        lots |= rect_mask(R, b["x"], b["y"], b["w"], b["d"], b["yaw"], grow=4.0)
    for br in bridges:
        (ax, ay), (bx, by) = br["a"], br["b"]
        d, _, _, _ = terrain.poly_field(R.grid, np.array([[ax, ay + OY], [bx, by + OY]]), 20.0)
        lots |= np.isfinite(d) & (d < br["width"] / 2 + 3)
    # the town's cleared ground: the valley floor in town (lawns, lots, fields) + lots and streets
    # anywhere, and Mill Hill's slope among the cottages
    Xe = R.X + CX
    yr = LT.river_y(Xe)
    e = np.abs(R.Y - yr) - LT.RIVER_HW
    F = np.where(R.Y > yr, LT._ix(Xe, LT.FLOOR_X, LT.FLOOR_N), LT._ix(Xe, LT.FLOOR_X, LT.FLOOR_S))
    floor = (e < F + 6) & (Xe < -1440) & (e > 3)
    millhill = (Xe < -1640) & (Xe > -1880) & (R.Y < -900) & (R.Y > -1012)
    town_clear = floor | lots | (street_d < 5) | millhill
    C, dw, slope = communities(R, town_clear, street_d)
    excl = (C == LFW.CID["water"]) | (C == LFW.CID["rock"]) | (C == LFW.CID["estate"]) | (dw < 3) | (street_d < 6) | (trail_d < 2.5)
    trees = LFW.scatter_trees(R, C, dw, np.where(np.isfinite(trail_d), trail_d, 1e9), excl, r)
    # (the town's views look across open flats at whole hillsides, where the cove's look into a
    # closed forest: the forest's impostors were most of a SwiftShader frame. Beyond 60 m of the
    # valley floor the stand is thinned to 55%: the canopy shell (terrain.js) fills the far slopes)
    xe_t = trees["x"] + CX
    e_t = np.abs(trees["y"] - LT.river_y(xe_t)) - LT.RIVER_HW
    F_t = np.where(trees["y"] > LT.river_y(xe_t), LT._ix(xe_t, LT.FLOOR_X, LT.FLOOR_N), LT._ix(xe_t, LT.FLOOR_X, LT.FLOOR_S))
    thin = (e_t > F_t + 60) & (r.random(len(xe_t)) > 0.55)
    trees = {k: v[~thin] for k, v in trees.items()}
    # yard and street trees in town: maples, oaks, dogwoods, a few hemlocks, off the lots and streets
    yx, yy = LFW.jitter_grid(R, 9.0, r)
    keep = LFW.sample_grid(R, town_clear & ~lots & (street_d > 4.5) & (dw > 6), yx, yy) & (r.random(len(yx)) < 0.22)
    yx, yy = yx[keep], yy[keep]
    ysp = r.choice(["sugar_maple", "white_oak", "flowering_dogwood", "eastern_hemlock", "northern_red_oak"], size=len(yx), p=[0.34, 0.16, 0.3, 0.1, 0.1])
    ysz = np.clip(0.75 + 0.2 * r.standard_normal(len(yx)), 0.45, 1.05)
    trees = {k: np.concatenate([trees[k], v]) for k, v in dict(x=yx, y=yy, sp=ysp, size=ysz, c=np.full(len(yx), LFW.CID["estate"])).items()}
    trees["rot"] = r.uniform(0, 2 * math.pi, len(trees["x"]))
    # shrubs: rosebay on the banks and in the hollows, mountain laurel on the oak slopes
    sx, sy = LFW.jitter_grid(R, 6.0, r)
    cc = LFW.sample_grid(R, C, sx, sy)
    ex_s = LFW.sample_grid(R, excl, sx, sy)
    pr = np.where(cc == LFW.CID["ripar"], 0.35, np.where(cc == LFW.CID["cove"], 0.06, np.where(cc == LFW.CID["oak"], 0.05, 0.0)))
    keep = (r.random(len(sx)) < pr) & ~ex_s
    sx, sy, cc = sx[keep], sy[keep], cc[keep]
    ssp = np.where(cc == LFW.CID["oak"], "mountain_laurel", "rosebay_rhododendron")
    shrubs = dict(x=sx, y=sy, sp=ssp, size=np.clip(0.8 + 0.2 * r.standard_normal(len(sx)), 0.5, 1.2), rot=r.uniform(0, 2 * math.pi, len(sx)))
    # ---- light: terrain + canopy + the buildings' shadows
    top, base = LFW.canopy_volume(R, trees, shrubs)
    L = LFW.light_bake(R, top, base, st["look"])
    occ = np.full(R.H.shape, -1e9)
    for b in buildings:
        m = rect_mask(R, b["x"], b["y"], b["w"], b["d"], b["yaw"])
        hh = b["h"] if b["kind"] not in ("town_water_tower",) else 6.0
        occ[m] = np.maximum(occ[m], b["z"] + hh * (0.8 if b["roof"] in ("gable", "hip") else 1.0))
    L["g"] = L["g"] * building_shadow(R, occ, st["look"])
    # ---- splat: grass (lawns, the floor), forest floor, rock, path (streets, lots, the bed)
    noise = terrain.Noise(SEED + 3)
    nz = noise.fbm(R.X, R.Y, 7.0, 3)
    grass = (town_clear & ~lots).astype(float)
    grass = np.maximum(grass, 0.25 * (C == LFW.CID["ripar"]))
    rock = np.clip((slope - 44) / 10, 0, 1)
    path = np.clip(1.6 - np.where(np.isfinite(street_d), street_d, 99) / 1.5, 0, 1)
    path = np.maximum(path, np.clip(1.3 - np.where(np.isfinite(trail_d), trail_d, 99) / 1.2 - 0.4 * nz, 0, 1))
    path = np.maximum(path, lots.astype(float) * 0.85)
    bed = (R.mask("rivers") > 0.3) | (R.mask("lakes") > 0.3)
    path = np.maximum(path, bed.astype(float) * 0.9)
    path = np.clip(path, 0, 1)
    rock *= 1 - path
    grass *= (1 - path) * (1 - rock)
    floor_ = np.clip(1 - grass - rock - path, 0, 1)
    var = 0.5 + 0.45 * noise.fbm(R.X - 33, R.Y + 71, 40.0, 3)
    u8, texels = LFW.u8, LFW.texels
    files = {}
    files["splat.png"] = terrain.write_png(os.path.join(out_dir, "splat.png"), np.dstack([u8(texels(grass)), u8(texels(floor_)), u8(texels(rock)), u8(texels(var))]))
    files["light.png"] = terrain.write_png(os.path.join(out_dir, "light.png"), np.dstack([u8(texels(L[k])) for k in "rgba"]))
    files["thicket.png"] = terrain.write_png(os.path.join(out_dir, "thicket.png"), np.zeros(R.H.shape, np.uint8))
    hlo, hhi = float(R.H.min()), float(R.H.max())
    files["height16.png"] = terrain.write_png(os.path.join(out_dir, "height16.png"), np.round((R.H - hlo) / (hhi - hlo) * 65535).astype(np.uint16))
    wl = np.where(np.isfinite(R.lake_level) & (R.H < R.lake_level), R.lake_level, R.river_level)
    wm = np.isfinite(wl)
    wlo, whi = float(np.nanmin(wl)) - 1, float(np.nanmax(wl)) + 1
    wq = np.where(wm, np.round((np.where(wm, wl, wlo) - wlo) / (whi - wlo) * 65534) + 1, 0).astype(np.uint16)
    files["water16.png"] = terrain.write_png(os.path.join(out_dir, "water16.png"), wq)
    # ---- the backdrop ring: the cove where it is, the valley function elsewhere
    Hb, gb, bake_b = ring(R, st)
    blo, bhi = float(Hb.min()), float(Hb.max())
    files["backdrop16.png"] = terrain.write_png(os.path.join(out_dir, "backdrop16.png"), np.round((Hb - blo) / (bhi - blo) * 65535).astype(np.uint16))
    files["backdrop.png"] = terrain.write_png(os.path.join(out_dir, "backdrop.png"), u8(bake_b))
    # ---- instances
    counts = {}
    allp = {k: np.concatenate([trees[k], shrubs[k]]) for k in ("x", "y", "sp", "size", "rot")}
    for sp_name in SPECIES:
        m = allp["sp"] == sp_name
        n = int(m.sum())
        x, y, s, rot = allp["x"][m], allp["y"][m], allp["size"][m], allp["rot"][m]
        zz = R.h(x, y) - (0.15 if SPECIES[sp_name]["tier"] == "tree" else 0.05)
        q = LFW.quantise_instances(x, y, zz, s, rot, r.random(n), LT.SIZE, hlo, hhi)
        if SPECIES[sp_name]["tier"] == "under":
            q = np.stack([q[:, 0], q[:, 1], (np.clip(np.round(s * 100), 0, 255).astype(np.uint16) << 8)
                          | np.clip(np.round((rot % (2 * math.pi)) / (2 * math.pi) * 256) % 256, 0, 255).astype(np.uint16), q[:, 5]], axis=1)
        fn = f"inst_{sp_name}.bin"
        with open(os.path.join(out_dir, fn), "wb") as fh:
            fh.write(q.astype("<u2").tobytes())
        files[fn] = int(q.size * 2)
        counts[sp_name] = n
    # ---- props (level.js): the heritage line, river rocks
    rail = routed.get("rail")
    authored = []
    if rail:
        P = terrain.spline([(x, y) for x, y in rail], 2.0)
        z = R.h(P[:, 0], P[:, 1])
        authored.append(dict(kind="rail", pts=[[round(float(a), 2), round(float(c), 2), round(float(e) + 0.05, 2)] for a, c, e in zip(P[:, 0], P[:, 1], z)]))
    boulders = []
    rx, ry = LFW.jitter_grid(R, 5.0, r)
    cb = LFW.sample_grid(R, (R.mask("rivers") > 0.5) & (R.X + CX < -1300) | ((C == LFW.CID["ripar"]) & ~town_clear), rx, ry)
    keep = cb & (r.random(len(rx)) < 0.05)
    for x, y in zip(rx[keep], ry[keep]):
        rr = float(r.uniform(0.5, 1.6))
        boulders.append(dict(x=float(x), y=float(y), z=float(R.h(x, y)) - rr * 0.35, r=rr, sq=float(r.uniform(0.55, 0.8)),
                             yaw=float(r.uniform(0, 3.14)), seed=float(r.random())))
    cols = np.concatenate([colliders(R, trees, town), LFW.colliders(R, dict(x=[], y=[], sp=[], size=[]), [], boulders, [])]) \
        if boulders else colliders(R, trees, town)
    c_lo = cols.reshape(-1, 2, 3).min(axis=(0, 1)) - 0.01
    c_hi = cols.reshape(-1, 2, 3).max(axis=(0, 1)) + 0.01
    sc = 65535.0 / (c_hi - c_lo)
    cq = np.concatenate([np.floor((cols[:, :3] - c_lo) * sc), np.ceil((cols[:, 3:] - c_lo) * sc)], axis=1)
    with open(os.path.join(out_dir, "colliders16.bin"), "wb") as fh:
        fh.write(np.clip(cq, 0, 65535).astype("<u2").tobytes())
    with open(os.path.join(out_dir, "colliders.bin"), "wb") as fh:
        fh.write(cols.astype("<f4").tobytes())
    files["colliders16.bin"] = int(cq.size * 2)
    try:
        subprocess.run(["cwebp", "-quiet", "-q", "88", "-alpha_q", "100", "-exact", "-m", "6",
                        os.path.join(out_dir, "light.png"), "-o", os.path.join(out_dir, "light.webp")], check=True)
        files["light.webp"] = os.path.getsize(os.path.join(out_dir, "light.webp"))
    except Exception as e_:
        print("  light.webp not written:", e_)
    # ---- views, routes, the river out west
    vw = make_views(R)
    rts = routes(R, routed, bridges)
    river_out = []
    for xe in np.arange(-2268.0, -3780.0, -24.0):
        river_out.append([round(tx(xe), 1), round(float(LT.river_y(xe)), 1), round(float(LT.water_z(xe)) - 0.02 * (-2268 - xe) * 0.01, 2), 34.0])
    meta = dict(
        name=name, title="Sourwood", frame=f"three.js, terrain local: x = estate x - ({CX:.0f}), z = -(estate y + {OY:.0f}); "
                                           "world.json positions: x = estate x - CX, y = estate y",
        estate_offset=[CX, -OY], size=LT.SIZE, res=R.n, spacing=R.cell, mapRes=R.n - 1,
        height=dict(min=hlo, max=hhi), water=dict(min=wlo, max=whi),
        backdrop=dict(extent=4608.0, cell=12.0, samples=[gb.nx, gb.ny], inner=[128, 257], min=blo, max=bhi),
        look=st["look"], light_scale=st["light_scale"],
        haze=dict(visual_range_m=32000.0, extinction=3.912 / 32000.0, away="#8FA6C4", sun="#E6C49A"),
        species={k: dict(v, count=counts.get(k, 0), file=f"inst_{k}.bin", tint_rgb=LFW.srgb_hex(v["tint"]), veg_ids=[k],
                         **({"fmt": "xz4"} if v["tier"] == "under" else {})) for k, v in SPECIES.items()},
        bloom={k: LFW.srgb_hex(v) for k, v in LFW.BLOOM.items()},
        communities=dict(names=LFW.NAMES, sight_lambda=LFW.SIGHT_LAMBDA),
        views=vw, routes=rts, props=LFW.rounded(dict(logs=[], boulders=boulders, authored=authored), 3),
        estate=None, colliders=int(len(cols)), colliders_q=dict(file="colliders16.bin", lo=[round(float(v), 4) for v in c_lo], hi=[round(float(v), 4) for v in c_hi]),
        river=dict(name="Laurel River", out=river_out), town=LFW.rounded(town, 3),
        light_file="light.webp" if os.path.exists(os.path.join(out_dir, "light.webp")) else "light.png",
        spawn=vw["spawn"],
        # the runtime: the town's lawns are mown (short blades, not the cove's hay), keys 1-0 jump between views
        grass=dict(floor=0.05, height=0.3, tint=[0.78, 1.0, 0.55], hay=False),
        keys={f"Digit{(k + 1) % 10}": v for k, v in enumerate(["spawn", "gorge_mouth", "bridge_approach", "main_street", "river_walk",
                                                                "strip", "motel_lot", "bar_lot", "mill_hill", "steeple"])},
        checks=dict(seam_max_diff_m=round(R.seam_diff, 3)),
        stats=dict(trees=int(len(trees["x"])), shrubs=int(len(shrubs["x"])), buildings=len(buildings), files_bytes=files,
                   timings_s=dict(total=round(time.time() - t0, 1))),
    )
    with open(os.path.join(out_dir, "world.json"), "w") as fh:
        json.dump(meta, fh, separators=(",", ":"))
    print(f"world {name}: {len(trees['x'])} trees, {len(shrubs['x'])} shrubs, {len(buildings)} buildings, {len(cols)} colliders, "
          f"seam: the run differed from the cove by up to {R.seam_diff:.2f} m before the patch")
    print("  species", {k: v for k, v in counts.items() if v})
    print("  files", files)
    return meta


def rect_mask_pt(x, y, b):
    a = math.radians(b["yaw"])
    dx, dy = x - b["x"], y - b["y"]
    u = dx * math.cos(a) + dy * math.sin(a)
    v = -dx * math.sin(a) + dy * math.cos(a)
    return abs(u) <= b["w"] / 2 and abs(v) <= b["d"] / 2


def building_shadow(R, occ, look):
    """Sun shadow of the buildings' boxes on the ground (marched toward the sun over `occ`, their
    tops): 1 lit, 0 shadowed (softened)."""
    sd = np.asarray(look["sun_dir"], float)
    Lv = -sd / np.linalg.norm(sd)
    hor = math.hypot(Lv[0], Lv[1])
    tanE, lx, ly = Lv[2] / hor, Lv[0] / hor, Lv[1] / hor
    ny, nx = R.H.shape
    jj, ii = np.mgrid[0:ny, 0:nx].astype(np.float64)
    sh = np.zeros(R.H.shape, bool)
    for k in range(1, 60):
        t = k * 1.5
        iu = np.clip(np.round(ii + lx * t / R.cell).astype(np.int64), 0, nx - 1)
        jv = np.clip(np.round(jj + ly * t / R.cell).astype(np.int64), 0, ny - 1)
        sh |= (R.H + 0.3 + t * tanE) < occ[jv, iu]
        if t * tanE > 40:
            break
    return np.clip(terrain.blur(1.0 - sh.astype(float), 0.8), 0.0, 1.0)


def ring(R, st):
    """The 4.6 km backdrop around the town square (12 m): the town's own heights inside its square,
    the cove's fine terrain inside the cove's, the cove's backdrop ring elsewhere (its town and
    corridor holes replaced by the valley function), the valley function + framing hills beyond
    the cove's ring (west). Baked colour: forest, pastures on the valley floor, rock."""
    ext, cell = 4608.0, 12.0
    n = int(ext / cell) + 1
    gb = terrain.Grid(-ext / 2, -ext / 2, cell, n, n)                 # town local
    Xl, Yl = gb.xy()
    Xe, Ye = Xl + CX, Yl - OY
    noise = terrain.Noise(LT.SEED)
    V = LT.valley_field(Xe, Ye, noise)
    zc, stc = LT.cove_data()
    bst = stc["backdrop"]
    gbc = terrain.Grid(-bst["extent"] / 2, -bst["extent"] / 2, bst["cell"], bst["samples"][0], bst["samples"][1])
    Hbc = zc["Hb"].astype(np.float64)
    in_cove_ring = (np.abs(Xe) < bst["extent"] / 2 - cell) & (np.abs(Yl) < bst["extent"] / 2 - cell)
    hbc = terrain.sample(Hbc, gbc, Xe, Yl)
    # the cove's holes -> the valley function, by the hole weight
    w = np.zeros_like(Xe)
    for x0, y0, x1, y1, hh, bl in LT.cove_holes():
        ex = np.maximum(np.maximum(x0 - Xe, Xe - x1), 0)
        ey = np.maximum(np.maximum(y0 - Yl, Yl - y1), 0)
        w = np.maximum(w, 1 - terrain.smoothstep(0, bl, np.hypot(ex, ey)))
    cove_part = hbc + (V - hbc) * w
    frame = terrain.smoothstep(ext / 2 * 0.3, ext / 2 * 0.9, np.maximum(np.abs(Xl), np.abs(Yl)))
    west = V + 110.0 * frame * (0.55 + 0.45 * noise.ridged(Xe, Ye, 1100.0, 5))
    fade = terrain.smoothstep(-bst["extent"] / 2 + 12, -bst["extent"] / 2 + 260, Xe)        # into the cove ring from the west
    Hb = np.where(in_cove_ring, cove_part * fade + west * (1 - fade), west)
    # the cove's fine square, then the town's own
    in_cove = (np.abs(Xe) <= 768) & (np.abs(Yl) <= 768)
    Hc = zc["H"].astype(np.float64)
    gc = terrain.Grid(-768, -768, 1.5, Hc.shape[1], Hc.shape[0])
    Hb = np.where(in_cove, terrain.sample(Hc, gc, Xe, Yl), Hb)
    k0 = int(round((-LT.HALF - gb.x0) / cell))
    step = int(round(cell / R.cell))
    k1 = k0 + (R.n - 1) // step + 1
    Hb[k0:k1, k0:k1] = R.H[::step, ::step]
    # colour: forest with a mottle, pastures on low flat ground beyond the town, rock on steep
    rgb_b, vis_b, sky_b = terrain.light(Hb, cell, st["look"])
    nb, _, _ = terrain.normals(Hb, cell)
    sl = np.degrees(np.arccos(nb[..., 2]))
    forest_c = np.array([0.030, 0.052, 0.020]) * (0.85 + 0.3 * noise.fbm(Xe + 9, Ye, 90.0, 3))[..., None]
    field = ((sl < 6) & (Hb < -150) & (noise.fbm(Xe, Ye, 260.0, 3) > -0.2)).astype(float)[..., None]
    alb = forest_c * (1 - field) + np.array([0.06, 0.09, 0.03]) * field
    rk = np.clip((sl - 46) / 10, 0, 1)[..., None]
    alb = alb * (1 - rk) + np.array([0.18, 0.18, 0.16]) * rk
    look = st["look"]
    lb = (np.asarray(look["sun_color"]) * look["sun_strength"] / math.pi
          * (np.clip((nb * (-np.asarray(look["sun_dir"]) / np.linalg.norm(look["sun_dir"]))).sum(axis=2), 0, 1) * vis_b)[..., None]
          + np.asarray(look["sky"]) * look["sky_strength"] * sky_b[..., None])
    bake = np.clip(alb * lb / st["light_scale"], 0, 1)
    srgb = np.where(bake <= 0.0031308, bake * 12.92, 1.055 * np.clip(bake, 0, None) ** (1 / 2.4) - 0.055)
    return Hb, gb, srgb


def make_views(R):
    def three(x, y, z):
        return [round(float(x), 2), round(float(z), 2), round(float(-(y + OY)), 2)]
    out = {}
    for nm, v in LT.views().items():
        p, l = v["pos"], v["look"]
        x, y = tx(p[0]), p[1]
        dz = p[2] if len(p) > 2 else 1.65
        g = float(R.h(x, y))
        lx, ly = tx(l[0]), l[1]
        lz = l[2] if l[2] is not None else float(R.h(lx, ly)) + 1.5
        out[nm] = dict(pos=three(x, y, g + dz), look=three(lx, ly, lz))
    return out


def routes(R, routed, bridges):
    """Walker polylines (three.js x, z): arriving by the road (the seam -> the gorge -> the truss
    bridge -> Main Street -> the bar) and by the river (the fishermen's path -> the river walk)."""
    pl = lambda nm: terrain.spline([(x, y) for x, y in routed[nm]], 2.0)[:, :2]
    to = lambda P: [[round(float(x), 2), round(float(-(y + OY)), 2)] for x, y in P]
    tr = next(b for b in bridges if b["kind"] == "truss")
    span = np.linspace(tr["a"], tr["b"], 30)
    road = np.vstack([pl("road_gorge"), span, pl("main_street")])
    # (Main Street to the bar's lot: stop where the highway passes the lot)
    bar = next(b for b in LT.layout_buildings() if b["id"] == "bar")
    k = int(np.argmin(np.hypot(road[:, 0] - tx(bar["x"]), road[:, 1] - (bar["y"] + 30))))
    river = np.vstack([pl("gorge_path"), pl("river_walk")])
    return dict(road=to(road[:k + 1]), river=to(river))


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else LT.NAME)
