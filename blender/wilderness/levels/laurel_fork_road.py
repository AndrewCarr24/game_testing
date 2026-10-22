"""The county road: the estate's drive leaves the gate as a two-lane concrete road and winds down
the cove's north wall to the Laurel River, then follows the river's north bank west, out of the
square and down the valley to the town (blockout.md: town zone x -2300..-1450, y -1150..-480; the
town's main street continues it). design/wilderness/estate_link.md has the write-up.

Engineered like a real mountain road: 7.0 m of concrete (two 3.35 m lanes + 0.15 m edge lines),
1.2 m gravel shoulders, grade <= 10 % (the terrain generator's grade cap), hairpins of 16-18 m
centreline radius on the steep lower wall (laid as fillet arcs, not the trail router's lattice
V's), cut / fill banks from the corridor (bank 30 deg fill, 45 deg cut), culverts where side
streams pass under the fill (the corridor is ford=False), guardrails where the fill side drops.

  PY=/Applications/Blender.app/Contents/Resources/5.0/python/bin/python3.11
  $PY blender/wilderness/levels/laurel_fork_road.py --plan      # profile of ROAD on the last terrain
  $PY blender/wilderness/levels/laurel_fork_road.py             # road.json from the last build

laurel_fork.py takes the corridor (PATHS "county_road" = path()) and runs this module's run() as
its "road" step, after "world": it writes build/wilderness/<name>/world/road.json (three.js frame,
read by viewer/wild/road.js): the centreline with its surface heights, the guardrail runs, the
culverts, and the ring continuation (beyond the square's west edge, on the backdrop's held-open
river corridor) to the town zone's edge.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import terrain  # noqa: E402

NAME = "laurel_fork"
OFFSET_Y = 810.0
PAVED = 7.0                  # concrete, edge line to edge line + the lines
SHOULDER = 1.2               # gravel each side
WIDTH = PAVED + 2 * SHOULDER # the corridor's flat core (terrain.corridor: width = core x 2)
MAX_GRADE = 0.10
TOWN_EDGE_X = -1450.0        # the town zone's east edge (blockout.md)

# The alignment (estate frame). Legs between control points; ("arc", r) after a point rounds the
# corner there with a fillet of radius r (hairpins and bends a car can take). Leg by leg:
#   the gate apron -> a bend west onto the bench, nearly level along the meadow's north edge
#   -> down the plateau's west end -> four hairpins on the cove's north wall (on its gentler
#   spurs) -> the north bank above the Narrows, west to the square's edge at the river.
ROAD = [
    (19.75, -64.0), (19.75, -84.0, ("arc", 24.0)), (-20.0, -118.0, ("arc", 60.0)),
    (-160.0, -132.0, ("arc", 150.0)), (-300.0, -170.0, ("arc", 120.0)),
    # four hairpins on the cove's north wall (circle centres, 17 m centreline radius)
    (-735.0, -395.0, ("pin", 17.0)),            # west
    (-300.0, -560.0, ("pin", 17.0)),            # east
    (-728.0, -603.0, ("pin", 17.0)),            # west
    (-275.0, -641.0, ("pin", 17.0)),            # east, above Laurel Fork (west of the creek trail)
    (-520.0, -679.0, ("arc", 150.0)), (-690.0, -697.0, ("arc", 150.0)),
    (-767.0, -703.0),
]


def _pins(pts):
    """Hairpins: a control point ("pin", r) is the CENTRE of the turn's circle; the legs either side
    become tangents to it (tangent from the neighbouring anchor, which is itself the tangent point
    when the neighbour is a pin too: iterated). Returns the control list with each pin replaced by
    its arc's points (plain vertices: the fillet pass leaves them alone)."""
    pins = [k for k, p in enumerate(pts) if len(p) > 2 and p[2][0] == "pin"]
    if not pins:
        return pts
    C = {k: np.array(pts[k][:2], float) for k in pins}
    R = {k: pts[k][2][1] for k in pins}
    # turn direction: the sign of the turn at the centre between its neighbours
    def sgn(k):
        a, b, c = (np.array(pts[k - 1][:2], float), C[k], np.array(pts[k + 1][:2], float))
        u, v = b - a, c - b
        return 1.0 if u[0] * v[1] - u[1] * v[0] > 0 else -1.0
    S = {k: sgn(k) for k in pins}
    T_in = {k: None for k in pins}
    T_out = {k: None for k in pins}

    def tangent(c, r, s, anchor, arriving):
        v = anchor - c
        D = max(np.linalg.norm(v), r + 1e-3)
        a = math.atan2(v[1], v[0])
        best = None
        for b in (a + math.acos(r / D), a - math.acos(r / D)):
            T = c + r * np.array([math.cos(b), math.sin(b)])
            tdir = s * np.array([-math.sin(b), math.cos(b)])         # travel direction there
            ok = (tdir @ (T - anchor) > 0) if arriving else (tdir @ (anchor - T) > 0)
            if ok:
                best = (T, b)
        return best
    for _ in range(8):
        for k in pins:
            prev = T_out.get(k - 1) if (k - 1) in C and T_out.get(k - 1) is not None else None
            nxt = T_in.get(k + 1) if (k + 1) in C and T_in.get(k + 1) is not None else None
            pa = prev[0] if prev is not None else np.array(pts[k - 1][:2], float)
            na = nxt[0] if nxt is not None else np.array(pts[k + 1][:2], float)
            T_in[k] = tangent(C[k], R[k], S[k], pa, True)
            T_out[k] = tangent(C[k], R[k], S[k], na, False)
    out = []
    for k, p in enumerate(pts):
        if k not in C:
            out.append(p)
            continue
        (_, b0), (_, b1) = T_in[k], T_out[k]
        da = (b1 - b0) % (2 * math.pi) if S[k] > 0 else -((b0 - b1) % (2 * math.pi))
        n = max(3, int(abs(da) * R[k] / 2.0))
        for i in range(n + 1):
            b = b0 + da * i / n
            q = C[k] + R[k] * np.array([math.cos(b), math.sin(b)])
            out.append((float(q[0]), float(q[1])))
    return out


def _fillet(pts, step=2.0):
    """Polyline with rounded corners: each control point with ("arc", r) is replaced by a circular
    arc tangent to both legs (r clamped so the arc fits half of each leg); ("pin", r) points are
    hairpin circles (_pins)."""
    pts = _pins(pts)
    P = [np.array(p[:2], float) for p in pts]
    R = [p[2][1] if len(p) > 2 else 0.0 for p in pts]
    out = [P[0]]
    for k in range(1, len(P) - 1):
        a, b, c = P[k - 1], P[k], P[k + 1]
        r = R[k]
        u, v = (a - b), (c - b)
        lu, lv = np.linalg.norm(u), np.linalg.norm(v)
        u, v = u / lu, v / lv
        cos = float(np.clip(u @ v, -1, 1))
        th = math.acos(cos)                         # interior angle at b
        if r <= 0 or th > math.pi - 1e-3:
            out.append(b)
            continue
        t = r / math.tan(th / 2)                    # tangent length
        t = min(t, 0.5 * lu, 0.5 * lv)
        r = t * math.tan(th / 2)
        p0, p1 = b + u * t, b + v * t
        bis = (u + v) / np.linalg.norm(u + v)
        centre = b + bis * (r / math.sin(th / 2))
        a0 = math.atan2(*(p0 - centre)[::-1])
        a1 = math.atan2(*(p1 - centre)[::-1])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        n = max(2, int(abs(da) * r / step))
        for i in range(n + 1):
            ang = a0 + da * i / n
            out.append(centre + r * np.array([math.cos(ang), math.sin(ang)]))
    out.append(P[-1])
    # resample evenly (Catmull-Rom in the corridor then passes through these without overshoot)
    Q = np.array(out)
    seg = np.hypot(*np.diff(Q, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    keep = np.concatenate([[True], seg > 0.05])
    Q, s = Q[keep], s[keep]
    ss = np.linspace(0, s[-1], max(2, int(s[-1] / step) + 1))
    return np.column_stack([np.interp(ss, s, Q[:, 0]), np.interp(ss, s, Q[:, 1])])


def points(step=4.0):
    """The centreline in the estate frame, every ~step m (for laurel_fork.PATHS)."""
    return [(round(float(x), 2), round(float(y), 2)) for x, y in _fillet(ROAD, step)]


def path():
    """The corridor for terrain.build (laurel_fork.PATHS): graded to MAX_GRADE, flat across the
    paved width + shoulders, fill banks 30 deg, cuts 45 deg; no fords (culverts: the side streams
    pass under the fill); not painted as trail dirt (the road mesh covers it)."""
    return dict(name="county_road", width=WIDTH, shoulder=4.0, max_grade=MAX_GRADE, smooth=30.0, ford=False,
                bank_deg=30.0, cut_deg=45.0, reach=30.0, road=True, county=True, culverts=True, points=points())


def _grid(st):
    g = st["grid"]
    return terrain.Grid(g["x0"], g["y0"], g["cell"], g["nx"], g["ny"])


def plan(name=NAME):
    """Profile of ROAD over the last built terrain (terrain.npz H): length, grade, cut/fill, as the
    corridor would be laid now (the terrain already carries the last road, so after a build this
    shows ~0 cut / fill)."""
    D = os.path.join(terrain.OUT_ROOT, name)
    H = np.load(os.path.join(D, "terrain.npz"))["H"].astype(np.float64)
    st = json.load(open(os.path.join(D, "stats.json")))
    grid = _grid(st)
    p = path()
    pts = [(x, y + OFFSET_Y) for x, y in p["points"]]
    P, seg, s, h, hs, hp = terrain.path_profile(H, grid, pts, p)
    gr = np.abs(np.diff(hp)) / np.maximum(seg, 1e-6)
    dz = hp - h
    print(f"length {s[-1]:.0f} m, z {hp[0]:.1f} -> {hp[-1]:.1f}, grade max {gr.max():.3f} p95 {np.percentile(gr, 95):.3f}")
    print(f"cut max {-dz.min():.1f} m, fill max {dz.max():.1f} m, |dz| p95 {np.percentile(np.abs(dz), 95):.1f} m")
    # clearance to the water (a fill bank must not reach a channel): distance to the nearest river
    # cell (the hydrology's rivers mask) against the fill's toe (core + fill height / tan 30)
    rv = terrain.read_png_fast(os.path.join(D, "masks", "rivers.png"))[::-1] > 127
    jj, ii = np.nonzero(rv)
    W = np.column_stack([grid.x0 + ii * grid.cell, grid.y0 + jj * grid.cell])
    from bisect import bisect_left  # noqa: F401
    dw = np.array([np.min(np.hypot(W[:, 0] - x, W[:, 1] - y)) if len(W) else 1e9 for x, y in P[:, :2][::2]])
    toe = (p["width"] / 2 + np.maximum(dz[::2], 0) / math.tan(math.radians(30)) + 3)
    bad = np.nonzero(dw < toe)[0]
    print(f"water: nearest {dw.min():.0f} m; {len(bad)} samples where the fill toe reaches a channel")
    for k in bad[::5]:
        q = P[::2][k]
        print(f"   ({q[0]:.0f}, {q[1] - OFFSET_Y:.0f}) water {dw[k]:.0f} m, toe {toe[k]:.0f} m")
    for k in range(0, len(s), max(1, len(s) // 40)):
        print(f"  s {s[k]:6.0f}  ({P[k, 0]:7.1f}, {P[k, 1] - OFFSET_Y:7.1f})  ground {h[k]:7.1f}  road {hp[k]:7.1f}  dz {dz[k]:+6.1f}")


# ------------------------------------------------------------------ road.json for the runtime
def run(name=NAME):
    D = os.path.join(terrain.OUT_ROOT, name)
    z = np.load(os.path.join(D, "terrain.npz"))
    H = z["H"].astype(np.float64)
    st = json.load(open(os.path.join(D, "stats.json")))
    grid = _grid(st)
    routed = st["routed_paths"].get("county_road")
    if not routed:
        print("road: no county_road in this terrain's paths")
        return None
    P = terrain.spline([tuple(q) for q in routed], 1.0)[:, :2]
    seg = np.hypot(*np.diff(P, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    # (evenly by arc length: the spline's spacing varies per segment, and smoothing by index over
    # uneven spacing steepens the grade)
    su = np.linspace(0, s[-1], int(s[-1] / 1.0) + 1)
    P = np.column_stack([np.interp(su, s, P[:, 0]), np.interp(su, s, P[:, 1])])
    seg = np.hypot(*np.diff(P, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    # the surface: the corridor's flat core (the final terrain on the centreline), lightly smoothed
    # (the 1.5 m grid's bilinear facets), grade re-capped
    hz = terrain.sample(H, grid, P[:, 0], P[:, 1])
    k = 4
    pad = np.pad(hz, k, mode="edge")
    c = np.cumsum(np.concatenate([[0], pad]))
    hz = (c[2 * k + 1:] - c[:-2 * k - 1]) / (2 * k + 1)
    # direction, normal (right of travel), per point
    d = np.gradient(P, axis=0)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    nrm = np.column_stack([d[:, 1], -d[:, 0]])
    # guardrails: where the ground 2.5-6 m beyond the shoulder falls away more than 1.5 m (fill
    # banks and drop-offs), per side; runs merged over gaps < 12 m and kept when >= 16 m
    rails = []
    for side in (1, -1):
        off = WIDTH / 2 + np.array([2.5, 4.0, 6.0])
        drop = np.max([hz - terrain.sample(H, grid, P[:, 0] + side * nrm[:, 0] * o, P[:, 1] + side * nrm[:, 1] * o)
                       for o in off], axis=0)
        need = drop > 1.5
        runs, i = [], 0
        while i < len(need):
            if need[i]:
                j = i
                while j + 1 < len(need) and need[j + 1]:
                    j += 1
                runs.append([i, j])
                i = j + 1
            else:
                i += 1
        merged = []
        for r in runs:
            if merged and s[r[0]] - s[merged[-1][1]] < 12.0:
                merged[-1][1] = r[1]
            else:
                merged.append(r)
        for a, b in merged:
            a, b = max(0, a - 4), min(len(s) - 1, b + 4)          # (flared in a little before and after)
            if s[b] - s[a] >= 16.0:
                rails.append(dict(side=side, s=[round(float(s[a]), 1), round(float(s[b]), 1)]))
    # culverts: under the road wherever water gathers to cross it: the stream channels (the
    # hydrology's rivers mask) and the hollows it fills across (peaks of the flow-accumulation mask
    # along the road, >= 60 m apart); the pipe runs square across the fill, its length to where the
    # fill's toe meets the ground (each side)
    rv = terrain.read_png_fast(os.path.join(D, "masks", "rivers.png"))[::-1] > 127
    fl = terrain.read_png_fast(os.path.join(D, "masks", "flow.png"))[::-1].astype(np.float64)
    on = terrain.sample(rv.astype(float), grid, P[:, 0], P[:, 1]) > 0.5
    f = terrain.sample(fl, grid, P[:, 0], P[:, 1]) + 40.0 * on
    culverts = []
    for m in np.argsort(-f):
        if f[m] < 50.0:
            break
        if s[m] < 60.0 or any(abs(s[m] - c["s"]) < 60.0 for c in culverts):
            continue
        gh = lambda o: float(terrain.sample(H, grid, P[m, 0] + nrm[m, 0] * o, P[m, 1] + nrm[m, 1] * o))   # o > 0: right
        down = 1 if gh(10.0) < gh(-10.0) else -1
        L = {}
        o = WIDTH / 2 + 1.0                       # outlet: the fill's toe (the slope eases off the bank)
        while o < 30.0 and (gh(down * (o + 1.0)) - gh(down * o)) < -0.45:
            o += 1.0
        L[down] = o
        o = WIDTH / 2 + 1.0                       # inlet: where the hollow's floor comes up to the pipe
        while o < 20.0 and gh(-down * o) < hz[m] - 1.2:
            o += 1.0
        L[-down] = o
        culverts.append(dict(s=round(float(s[m]), 1), right=round(L[1], 1), left=round(L[-1], 1),
                             out=down, drop=round(hz[m] - gh(down * L[down]), 1)))
    culverts.sort(key=lambda c: c["s"])
    # the ring continuation: from the square's west edge down the held-open river corridor (the
    # backdrop's flat at -188.5 north of the river) to the town zone's edge
    wb = json.load(open(os.path.join(D, "world", "world.json")))
    bd = wb["backdrop"]
    bh = terrain.read_png_fast(os.path.join(D, "world", "backdrop16.png")).astype(np.float64)
    bh = bh / 65535.0 * (bd["max"] - bd["min"]) + bd["min"]          # image rows north first (three z asc)
    B = bd["extent"] / 2

    def ring_h(xe, ye):
        X, Z = xe, -(ye + OFFSET_Y)
        u, v = (X + B) / bd["cell"], (Z + B) / bd["cell"]
        i0, j0 = int(np.floor(u)), int(np.floor(v))
        fu, fv = u - i0, v - j0
        q = bh[j0:j0 + 2, i0:i0 + 2]
        return float(q[0, 0] * (1 - fu) * (1 - fv) + q[0, 1] * fu * (1 - fv) + q[1, 0] * (1 - fu) * fv + q[1, 1] * fu * fv)
    end = (float(P[-1, 0]), float(P[-1, 1] - OFFSET_Y), float(hz[-1]))
    out = [tuple(q) for q in (wb.get("river", {}).get("out") or [])]
    ring = []
    if out:
        # 24 m north of the river ribbon's centre, graded gently down to the corridor's flat
        xs = np.arange(end[0] - 8.0, TOWN_EDGE_X - 1.0, -8.0)
        oy = np.interp(-xs, [-q[0] for q in out], [q[1] for q in out])
        ys = oy + np.array([q[3] for q in out]).max() / 2 + 14.0
        ys = np.where(xs > -900, np.maximum(ys, end[1] + (xs - end[0]) * 0.0), ys)
        # blend the first stretch from the square's exit point onto that line
        t = np.clip((end[0] - xs) / 140.0, 0, 1)
        t = t * t * (3 - 2 * t)
        ys = end[1] * (1 - t) + ys * t
        zg = np.array([ring_h(x, y) for x, y in zip(xs, ys)])
        zr = np.minimum(end[2] - 0.0, -186.8) * np.ones_like(xs)          # the embankment over the flood plain
        zr = end[2] * (1 - t) + zr * t
        zr = np.maximum(zr, zg + 0.4)
        ring = [[round(float(x), 2), round(float(zz), 2), round(float(-(y + OFFSET_Y)), 2)] for x, y, zz in zip(xs, ys, zr)]
    pts3 = [[round(float(x), 2), round(float(zz), 2), round(float(-y), 2)] for (x, y), zz in zip(P, hz)]
    data = dict(name="county_road", frame="three.js, terrain local (as world.json)", paved=PAVED,
                shoulder=SHOULDER, lanes=2, lane=3.35, centre_line="double yellow", edge_line="white",
                joint=4.5, grade_max=MAX_GRADE, length_m=round(float(s[-1]), 1),
                ring_length_m=round(float(len(ring) * 8.0), 1), points=pts3, ring=ring, rails=rails, culverts=culverts,
                town_edge_x=TOWN_EDGE_X)
    gr = np.abs(np.diff(hz)) / np.maximum(seg, 1e-6)
    data["grade_p95"] = round(float(np.percentile(gr, 95)), 3)
    data["grade_measured_max"] = round(float(gr.max()), 3)
    path_ = os.path.join(D, "world", "road.json")
    with open(path_, "w") as fh:
        json.dump(data, fh, separators=(",", ":"))
    print(f"road: {data['length_m']} m in the square (+{data['ring_length_m']} m in the ring), grade max {data['grade_measured_max']} "
          f"p95 {data['grade_p95']}, {len(rails)} guardrail runs, {len(culverts)} culverts -> {path_}")
    return data


if __name__ == "__main__":
    if "--plan" in sys.argv:
        plan(sys.argv[sys.argv.index("--plan") + 1] if len(sys.argv) > sys.argv.index("--plan") + 1 else NAME)
    else:
        run(sys.argv[1] if len(sys.argv) > 1 else NAME)
