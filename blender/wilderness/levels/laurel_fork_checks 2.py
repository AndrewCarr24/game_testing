"""Laurel Fork checks on a terrain run (re-run after every terrain change; the brief's margins
were 1-5 m): sight lines from the three lookouts to the house over terrain + the brief's canopy
model (Appendix A), what each lookout can't see (footlog, pool, meadow, the Gap, each other), the
creek / falls / plunge pool / footlog layout, trail grades and cross-slopes, and route C's slopes
against the 40 deg walking limit. Writes build/wilderness/<run>/checks.json.

  $PY blender/wilderness/levels/laurel_fork_checks.py [run]
The world step (laurel_fork_world.py) re-checks the views against the trees it actually placed.
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
import laurel_fork as LF  # noqa: E402

OY = LF.OFFSET_Y


class Run:
    """A terrain run in the estate frame: heights, masks, grid."""
    def __init__(self, name):
        self.dir = os.path.join(terrain.OUT_ROOT, name)
        self.stats = json.load(open(os.path.join(self.dir, "stats.json")))
        z = np.load(os.path.join(self.dir, "terrain.npz"))
        self.H = z["H"].astype(np.float64)
        self.river_level, self.lake_level = z["river_level"], z["lake_level"]
        g = self.stats["grid"]
        self.cell, self.n = g["cell"], g["nx"]
        self.grid = terrain.Grid(g["x0"], g["y0"], g["cell"], g["nx"], g["ny"])
        x = g["x0"] + np.arange(self.n) * self.cell
        self.X, self.Y = np.meshgrid(x, x - OY)            # estate frame
        self._m = {}

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


def in_poly(px, py, poly):
    inside = np.zeros(np.shape(px), bool)
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        inside ^= ((y1 > py) != (y2 > py)) & (px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-12) + x1)
    return inside


def brief_canopy(R):
    """Appendix A's canopy model (m above ground): 35 in coves, 25 above +120, 15 on dry crests,
    4 on laurel slicks and the bald, <= 8 on talus within 110 m of a cliff, 0 on rock, meadow."""
    H, slope, curv = R.H, R.mask("slope") * 90, R.mask("curvature")
    can = np.full(H.shape, 35.0)
    can[H > 120] = 25.0
    can[(curv > 0.56) & (H > 120)] = 15.0
    can[(slope > 33) & (curv > 0.5) & (H > 90)] = 4.0
    can[np.hypot(R.X - LF.BALD["center"][0], R.Y - LF.BALD["center"][1]) < LF.BALD["radius"]] = 4.0
    can[slope > 48] = 0.0
    for c in LF.CLIFFS:
        pts = terrain.spline([LF.local(q) for q in c["points"]], 3.0)
        dd, _, _, _ = terrain.poly_field(R.grid, pts, 110.0)
        m = np.isfinite(dd) & (slope > 28)
        can[m] = np.minimum(can[m], 8.0)
    can[in_poly(R.X, R.Y, LF.MEADOW)] = 0.0
    return can


def los(R, can, a, b, eye=1.7, skip=22.0, skip_target=8.0, step=2.0):
    """Clearance (m) of the sight line from a (x, y[, z]) at eye height to b (x, y, z) over
    terrain + canopy; the canopy is ignored within `skip` m of the observer (the open outcrop)
    and skip_target m of the target. Returns dict(L, clear, at)."""
    ax, ay = a[0], a[1]
    az = (a[2] if len(a) > 2 else float(R.h(ax, ay))) + eye
    bx, by, bz = b
    L = math.hypot(bx - ax, by - ay)
    n = max(2, int(L / step))
    t = np.arange(1, n) / n
    x, y, z = ax + t * (bx - ax), ay + t * (by - ay), az + t * (bz - az)
    inside = y < -45                                         # (north of it: the estate, no forest)
    g = np.where(inside, R.h(np.where(inside, x, 0), np.where(inside, y, -100)), LF.LAWN_Z)
    if can is not None:
        j, i = R.ij(x, np.where(inside, y, -100))
        c = np.where(inside, can[j, i], 0.0)
        d0, d1 = np.hypot(x - ax, y - ay), np.hypot(x - bx, y - by)
        c = np.where((d0 > skip) & (d1 > skip_target), c, 0.0)
    else:
        c = 0.0
    clr = z - (g + c)
    k = int(np.argmin(clr))
    return dict(L=round(L), clear=round(float(clr[k]), 2), at=[round(float(x[k])), round(float(y[k]))])


def views(R, can):
    """Lookouts -> the house's upper floor, and what each lookout must NOT see."""
    out = {}
    house = LF.HOUSE_EYE
    for nm, pt in LF.LOOKOUTS.items():
        r = los(R, can, pt, house)
        r["terrain_only"] = los(R, None, pt, house)["clear"]
        r["z"] = round(float(R.h(*pt)), 1)
        hidden = {}
        for tn, tp in dict(footlog=LF.LANDMARKS["footlog"], pool=LF.LANDMARKS["plunge_pool"],
                           meadow=(20, -120), gap=LF.LANDMARKS["gap"]).items():
            tz = float(R.h(*tp)) + 1.5
            hidden[tn] = los(R, can, pt, (tp[0], tp[1], tz))["clear"]
        for on, op in LF.LOOKOUTS.items():
            if on != nm:
                hidden[on] = los(R, can, pt, (op[0], op[1], float(R.h(*op)) + 1.7))["clear"]
        r["others_clear_m"] = hidden          # < 0 = hidden (as the brief wants)
        out[nm] = r
    g = LF.LANDMARKS["gate_rock"]
    out["gate_rock_sees"] = {k: los(R, can, g, (p[0], p[1], float(R.h(*p)) + 3))["clear"]
                             for k, p in dict(knob=LF.LANDMARKS["knob"], gap=LF.LANDMARKS["gap"]).items()}
    return out


def creek(R):
    st = R.stats
    rl, ll = R.river_level, R.lake_level
    # the falls: water level just upstream of the lip and the pool below
    lip = LF.LANDMARKS["falls_lip"]
    def level_near(x, y, r=8.0):
        m = (np.hypot(R.X - x, R.Y - y) < r)
        v = np.concatenate([rl[m][np.isfinite(rl[m])], ll[m][np.isfinite(ll[m])]])
        return float(np.nanmedian(v)) if len(v) else None
    up = level_near(lip[0] + 14, lip[1])
    pool = level_near(*LF.LANDMARKS["plunge_pool"])
    lakes = st["hydrology"]["lakes"]
    fl = LF.LANDMARKS["footlog"]
    ford = min(st["fords"], key=lambda f: math.hypot(f["x"] - fl[0], f["y"] - OY - fl[1])) if st["fords"] else None
    # footlog: water level and the ground 8 m either side of the creek along the trail
    w = level_near(*fl, r=6.0)
    trail = st["routed_paths"]["creek_trail"]
    P = terrain.spline(trail, 1.0)
    k = int(np.argmin(np.hypot(P[:, 0] - fl[0], P[:, 1] - OY - fl[1])))
    ends = []
    for dk in (-8, 8):
        q = P[min(max(k + dk, 0), len(P) - 1)]
        ends.append(round(float(R.h(q[0], q[1] - OY)), 2))
    return dict(falls_drop_m=round(up - pool, 1) if up is not None and pool is not None else None,
                water_above_lip=round(up, 2) if up else None, pool_level=round(pool, 2) if pool else None,
                lakes=[dict(level=lk["level"], area_m2=round(lk["cells"] * R.cell ** 2)) for lk in lakes],
                river_length_m=st["hydrology"]["river_length_m"], max_width_m=st["hydrology"]["max_width"],
                fords=[dict(x=f["x"], y=round(f["y"] - OY, 1), width_m=f["width_m"]) for f in st["fords"]],
                footlog=dict(ford=ford and dict(x=ford["x"], y=round(ford["y"] - OY, 1), width_m=ford["width_m"]),
                             water=round(w, 2) if w else None, bank_ends=ends,
                             deck_over_water_m=round(max(ends) - w, 2) if w else None))


def slope_along(R, pts, step=1.0):
    P = terrain.spline([(x, y + OY) for x, y in pts], step)
    s = R.mask("slope") * 90
    j = np.clip(np.round((P[:, 1] - R.grid.y0) / R.cell).astype(int), 0, R.n - 1)
    i = np.clip(np.round((P[:, 0] - R.grid.x0) / R.cell).astype(int), 0, R.n - 1)
    v = s[j, i]
    return dict(length_m=round(float(np.hypot(*np.diff(P[:, :2], axis=0).T).sum())),
                slope_p50=round(float(np.percentile(v, 50)), 1), slope_p95=round(float(np.percentile(v, 95)), 1),
                over_40deg_m=round(float((v > 40).sum() * step)), max=round(float(v.max()), 1))


def run(name=LF.NAME):
    R = Run(name)
    can = brief_canopy(R)
    out = dict(run=name, views=views(R, can), creek=creek(R))
    out["trails"] = {p["name"]: dict(length_m=p["length_m"], max_cut_fill_m=p["max_cut_fill_m"],
                                     cut_fill_p95_m=p["cut_fill_p95_m"], rise_m=p["rise_m"],
                                     switchbacks=len(p.get("switchbacks", [])))
                     for p in R.stats["paths"]}
    for w in R.stats["walk"]["paths"]:
        out["trails"][w["name"]].update(grade_p50=w["grade_p50"], grade_p99=w["grade_p99"], cross_deg_p99=w["cross_deg_p99"])
    routed = {k: [(x, y - OY) for x, y in v] for k, v in R.stats["routed_paths"].items()}
    out["slopes"] = {k: slope_along(R, v) for k, v in routed.items()}
    out["slopes"]["route_c_lane"] = slope_along(R, LF.ROUTE_C)
    out["terrain"] = dict(height=R.stats["height"], slope_p50=R.stats["walk"]["slope_deg_p50"],
                          slope_p90=R.stats["walk"]["slope_deg_p90"],
                          play_area_over_40deg_pct=round(float(((R.mask("slope") * 90 > 40)
                                                                 [(R.X > -700) & (R.X < 600) & (R.Y < -62) & (R.Y > -1300)]).mean() * 100), 1))
    with open(os.path.join(R.dir, "checks.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    v = out["views"]
    print("views to the house (clearance m; terrain only):")
    for nm in LF.LOOKOUTS:
        print(f"  {nm:8s} z {v[nm]['z']:6.1f}  L {v[nm]['L']} m  clear {v[nm]['clear']:6.2f} at {v[nm]['at']}  "
              f"(terrain {v[nm]['terrain_only']})  others {v[nm]['others_clear_m']}")
    print("  gate rock ->", v["gate_rock_sees"])
    c = out["creek"]
    print(f"creek: falls drop {c['falls_drop_m']} m ({c['water_above_lip']} -> {c['pool_level']}), lakes {c['lakes']}, fords {c['fords']}")
    print(f"  footlog {c['footlog']}")
    for k, t in out["trails"].items():
        print(f"  trail {k:12s} {t}")
    for k, sl in out["slopes"].items():
        print(f"  slope {k:12s} {sl}")
    print("  terrain", out["terrain"])
    return out


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else LF.NAME)
