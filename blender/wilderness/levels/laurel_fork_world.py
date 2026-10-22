"""Laurel Fork Cove: terrain run -> the runtime world (viewer/wild_proto.html?world=laurel_fork).

From the generator's heights and masks this places the forest by the brief's community rules
(Appendix C: cove / creekside / laurel hell / oak-hickory / dry crest / laurel slick / heath bald
/ rock, from wetness, curvature, aspect, slope, distance to water and height), scatters trees,
shrubs and ferns per species (Appendix B), lays logs, boulders and the authored props (footlog,
the Poplar Cove chestnut ghost, the Gap's overlook wall, lookout slabs, the Knob's summit rock),
keeps the lookouts' views to the house open (vista clearing, checked against the trees it
placed), bakes the light (terrain sun + shadow, a canopy shadow marched through the placed crowns,
sky visibility), and writes everything in the runtime's format (viewer/wild/world.js header):

  build/wilderness/<run>/world/
    world.json        size, grid, height range, species table, views, routes, estate, props, stats
    height16.png      heights (16-bit grey, Up-filtered, row 0 = north = three.js -z)
    splat.png         RGBA 1024^2: r grass, g forest floor, b rock, 1-r-g-b path / cobble, a variation
    light.png         RGBA 1024^2: r sun n.l x terrain shadow, g canopy shadow, b sky, a terrain shadow
    thicket.png       grey, vertex grid: 255 laurel hell (solid), 128 tunnel (crouch), 0 open
    water16.png       16-bit: water surface (0 = dry), range in world.json
    backdrop16.png, backdrop.png   the 4.6 km ring's heights and baked colour
    inst_<species>.bin  uint16 x 6 per instance: x, z (over the square), y (height range),
                      size x 10000, rotY / 2pi, seed (all / 65535)
    colliders.bin     float32 x 6 per box (three.js min xyz, max xyz): trunks, logs, boulders, props

  $PY blender/wilderness/levels/laurel_fork_world.py [run]
"""
import json
import subprocess
import math
import os
import shutil
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import terrain  # noqa: E402
import laurel_fork as LF  # noqa: E402
from laurel_fork_checks import Run, in_poly, los  # noqa: E402

OY = LF.OFFSET_Y
SEED = 31

# ------------------------------------------------------------------ species (Appendix B)
# kind: the runtime stand-in when the vegetation agent's model (veg.json[id]) isn't there yet;
# height / width: nominal metres (instances carry a size factor around 1); trunk: radius at
# breast height (m) at size 1 (colliders); tint: leaf colour (sRGB hex, the brief's); tier:
# tree (near/mid/impostor), shrub (LOD0 within 12 m), under (near only)
SPECIES = {
    # ids = the vegetation agent's (build/wilderness/veg/veg.json, kits.blue_ridge); kind = the
    # runtime's stand-in until (or where) that model isn't there
    "tulip_poplar":     dict(kind="broadleaf", height=44.0, width=14.0, trunk=0.70, tint="#8DB04A", tier="tree"),
    "eastern_hemlock":  dict(kind="conifer", height=33.0, width=13.0, trunk=0.50, tint="#2F4A3A", tier="tree"),
    "northern_red_oak": dict(kind="broadleaf", height=31.0, width=18.0, trunk=0.48, tint="#3F5E2A", tier="tree"),
    "white_oak":        dict(kind="broadleaf", height=26.0, width=18.0, trunk=0.45, tint="#4A6A2E", tier="tree"),
    "chestnut_oak":     dict(kind="broadleaf", height=22.0, width=13.0, trunk=0.36, tint="#6B8A36", tier="tree"),
    "shagbark_hickory": dict(kind="broadleaf", height=27.0, width=10.0, trunk=0.30, tint="#4F7230", tier="tree"),
    "sugar_maple":      dict(kind="broadleaf", height=28.0, width=12.0, trunk=0.38, tint="#4E7A2C", tier="tree"),
    "yellow_buckeye":   dict(kind="broadleaf", height=30.0, width=14.0, trunk=0.45, tint="#6E9438", tier="tree"),
    "white_pine":       dict(kind="pine", height=40.0, width=12.0, trunk=0.50, tint="#4D6E4A", tier="tree"),
    "hemlock_snag":     dict(kind="conifer", height=24.0, width=8.0, trunk=0.45, tint="#8A8A80", tier="tree", dead=True),
    # understory (Appendix B's 4%): flowering dogwood in the coves and on moist slopes, sourwood on the
    # oak slopes and crests (kit ids since the plant kit's understory pass)
    "flowering_dogwood": dict(kind="broadleaf", height=8.0, width=8.0, trunk=0.12, tint="#557B35", tier="tree"),
    "sourwood":         dict(kind="broadleaf", height=12.0, width=6.5, trunk=0.15, tint="#4C702F", tier="tree"),
    "rosebay_rhododendron": dict(kind="shrub", height=4.5, width=4.0, trunk=0.0, tint="#2E4A2C", tier="shrub", bloom=4),
    "rhodo_thicket":    dict(kind="shrub", height=4.7, width=9.0, trunk=0.0, tint="#2E4A2C", tier="shrub", tile=True),
    "rhodo_tunnel":     dict(kind="shrub", height=4.9, width=9.0, trunk=0.0, tint="#2E4A2C", tier="shrub", tile=True),
    "mountain_laurel":  dict(kind="shrub", height=3.0, width=3.0, trunk=0.0, tint="#3F5A2E", tier="shrub", bloom=2),
    "catawba_rhododendron": dict(kind="shrub", height=2.2, width=2.6, trunk=0.0, tint="#3A5530", tier="shrub", bloom=1),
    "flame_azalea":     dict(kind="shrub", height=2.5, width=2.2, trunk=0.0, tint="#5A7A34", tier="shrub", bloom=3),
    "doghobble":        dict(kind="fern", height=1.0, width=1.8, trunk=0.0, tint="#2F5430", tier="under"),
    "christmas_fern":   dict(kind="fern", height=0.6, width=1.2, trunk=0.0, tint="#2F5027", tier="under"),
    "cinnamon_fern":    dict(kind="fern", height=1.0, width=1.2, trunk=0.0, tint="#5E7A2E", tier="under"),
}
# bloom (shrub stand-ins and the runtime's flower term): 1 Catawba magenta #B65A9E, 2 laurel
# white-pink #F3D9E0, 3 flame azalea #F08A2A, 4 rosebay's first white trusses (sparse)
BLOOM = {1: "#B65A9E", 2: "#F3D9E0", 3: "#F08A2A", 4: "#F4F0E6"}
# stems >= 20 cm per hectare and the species mix of each community (Appendix C)
COMMUNITY = {
    "cove":    dict(density=250, mix=dict(tulip_poplar=42, sugar_maple=14, yellow_buckeye=10, eastern_hemlock=16, northern_red_oak=6,
                                          shagbark_hickory=4, flowering_dogwood=8)),
    "ripar":   dict(density=200, mix=dict(eastern_hemlock=58, tulip_poplar=16, sugar_maple=10, yellow_buckeye=6, flowering_dogwood=8, hemlock_snag=2)),
    "oak":     dict(density=230, mix=dict(northern_red_oak=30, white_oak=10, shagbark_hickory=16, chestnut_oak=12, white_pine=10,
                                          tulip_poplar=10, flowering_dogwood=4, sourwood=8)),
    "crest":   dict(density=170, mix=dict(chestnut_oak=50, northern_red_oak=14, white_oak=6, white_pine=14, shagbark_hickory=6, sourwood=10)),
    "slick":   dict(density=35, mix=dict(chestnut_oak=50, white_pine=30, sourwood=20), size=0.45),
    "hell":    dict(density=30, mix=dict(eastern_hemlock=66, tulip_poplar=20, yellow_buckeye=10, hemlock_snag=4)),
    "bald":    dict(density=2, mix=dict(chestnut_oak=60, white_pine=40), size=0.5),
}
NAMES = ["meadow", "cove", "ripar", "hell", "oak", "crest", "slick", "bald", "rock", "water", "estate", "clearing"]
CID = {n: i for i, n in enumerate(NAMES)}
# sight attenuation length per community (brief: notice x exp(-sum ds / lambda)); 0 = open
SIGHT_LAMBDA = dict(meadow=0, cove=35, ripar=25, hell=3, oak=60, crest=60, slick=60, bald=150, rock=0, water=0, estate=0, clearing=0)
POPLAR_COVE = dict(center=(10, -380), radius=130.0)     # the uncut old growth
ROUTE_C_BAND = (110.0, 430.0)                            # m along route C: the thicket band
FALLS_VIEW = (-121.0, -667.0)                            # the pool's west rim, looking up at the falls


def rng(seed):
    return np.random.default_rng(seed)


def srgb_hex(h):
    return [int(h[1:3], 16) / 255, int(h[3:5], 16) / 255, int(h[5:7], 16) / 255]


# ------------------------------------------------------------------ communities
def communities(R, trails_d, route_c_d, route_c_s):
    slope, wet, curv = R.mask("slope") * 90, R.mask("wetness"), R.mask("curvature")
    asp = R.mask("aspect") * 360
    H, X, Y = R.H, R.X, R.Y
    water = (R.mask("rivers") > 0.5) | (R.mask("lakes") > 0.5)
    _, _, dwc = terrain.nearest_seed(water)
    dw = dwc * R.cell
    noise = terrain.Noise(SEED)
    n1 = noise.fbm(X, Y, 90.0, 3)
    northish = (np.cos(np.radians(asp)) > 0.2) | ((asp > 0) & (asp < 110))
    southish = (asp > 140) & (asp < 290)
    cove = (((curv < 0.47) | (wet > 0.55)) & ~southish) | ((curv < 0.44) & (wet > 0.45))
    crest = (curv > 0.56) & (H > 120)
    mesic = northish & (H < 160) & ~crest
    oak = southish | (curv > 0.54)
    C = np.full(H.shape, CID["oak"], np.int8)
    C[(cove & ~oak) | mesic | (cove & oak & (wet > 0.5))] = CID["cove"]
    C[crest] = CID["crest"]
    C[dw < 28 + 6 * n1] = CID["ripar"]
    hell = (slope > 22) & (slope < 46) & (wet > 0.33) & northish & (dw < 220) & (dw > 4)
    # the authored 45 m band of route C, over the stretch where the lane drops into the cove head
    # (the brief's ~300 m of crouching; elsewhere the lane is a bear path through the forest)
    band = (route_c_d < 22.5) & (route_c_s > ROUTE_C_BAND[0]) & (route_c_s < ROUTE_C_BAND[1])
    hell |= band & (slope > 12) & (H < 170) & (dw > 4)
    # (break the mask into irregular thickets, not a carpet: a hell is a patchwork of slicks)
    hell &= (n1 + 0.25 * noise.fbm(X + 51, Y - 17, 25.0, 2) > -0.18) | band
    C[hell] = CID["hell"]
    slick = (slope > 33) & (curv > 0.5) & (H > 90)
    for c in LF.CLIFFS:                                    # talus below every cliff
        pts = terrain.spline([LF.local(q) for q in c["points"]], 3.0)
        dd, _, _, _ = terrain.poly_field(R.grid, pts, 70.0)
        slick |= np.isfinite(dd) & (slope > 28) & (R.mask("cliff") < 0.3)
    C[slick & (C != CID["ripar"])] = CID["slick"]
    rock = ((slope > 50) & (trails_d > 5) & ~(route_c_d < 5)) | (R.mask("cliff") > 0.35)   # (a trail's cut bank isn't an outcrop)
    C[rock] = CID["rock"]
    bc, br = LF.BALD["center"], LF.BALD["radius"]
    th = np.arctan2(Y - bc[1], X - bc[0])
    bald = np.hypot(X - bc[0], Y - bc[1]) < br * (0.8 + 0.22 * np.sin(3 * th) + 0.12 * np.sin(5 * th + 1.0)) * (1 + 0.08 * n1)
    C[bald & ~rock] = CID["bald"]
    C[in_poly(X, Y, LF.MEADOW)] = CID["meadow"]
    C[Y > -64] = CID["estate"]                              # the lawn strip inside the hedge line
    gp = LF.LANDMARKS["gap"]
    C[np.hypot(X - gp[0], Y - gp[1]) < 30] = CID["clearing"]
    for nm in ("raven", "knob", "painted"):                 # the lookouts' open rock
        p = LF.LOOKOUTS[nm]
        C[(np.hypot(X - p[0], Y - p[1]) < 9)] = CID["rock"]
    C[water] = CID["water"]
    return C, dw, slope


# ------------------------------------------------------------------ scatter
def jitter_grid(R, spacing, r):
    """Candidate points: one per cell of a jittered `spacing` grid over the square (estate frame)."""
    half = 768.0
    n = int(2 * half / spacing)
    gx, gy = np.meshgrid(np.arange(n), np.arange(n))
    x = -half + (gx.ravel() + r.random(n * n)) * spacing
    yl = -half + (gy.ravel() + r.random(n * n)) * spacing
    return x, yl - OY


def sample_grid(R, A, x, y):
    j, i = R.ij(x, y)
    return A[j, i]


def poisson_thin(x, y, rad, r, order=None):
    """Keep points so no two are closer than rad[k] (the larger of the pair's radii, hashed)."""
    keep = np.zeros(len(x), bool)
    cellsz = max(float(rad.max()), 1.0)
    grid = {}
    idx = order if order is not None else r.permutation(len(x))
    for k in idx:
        cx, cy = int(math.floor(x[k] / cellsz)), int(math.floor(y[k] / cellsz))
        ok = True
        for a in (cx - 1, cx, cx + 1):
            for b in (cy - 1, cy, cy + 1):
                for q in grid.get((a, b), ()):
                    if (x[q] - x[k]) ** 2 + (y[q] - y[k]) ** 2 < max(rad[q], rad[k]) ** 2:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            keep[k] = True
            grid.setdefault((cx, cy), []).append(k)
    return keep


def scatter_trees(R, C, dw, trails_d, excl, r):
    """Trees per community: density x clustering noise on a 3 m jittered grid, thinned to a
    minimum spacing (crowns), species by the community mix, sizes by age class."""
    noise = terrain.Noise(SEED + 3)
    x, y = jitter_grid(R, 3.0, r)
    c = sample_grid(R, C, x, y)
    dens = np.zeros(len(x))
    for nm, spec in COMMUNITY.items():
        dens[c == CID[nm]] = spec["density"]
    # old growth: fewer, bigger stems; gaps and clusters from low-frequency noise
    pc = POPLAR_COVE
    oldg = np.hypot(x - pc["center"][0], y - pc["center"][1]) < pc["radius"]
    dens[oldg & (c == CID["cove"])] *= 0.62
    clus = noise.fbm(x, y, 70.0, 3) + 0.4 * noise.fbm(x + 300, y, 22.0, 2)
    dens *= np.clip(0.95 + 1.6 * clus, 0.0, 1.8)
    p = dens / 1e4 * 9.0
    ok = (r.random(len(x)) < p) & ~sample_grid(R, excl, x, y) & (sample_grid(R, trails_d, x, y) > 3.2)
    x, y, c, oldg = x[ok], y[ok], c[ok], oldg[ok]
    # species
    sp = np.empty(len(x), dtype=object)
    H = sample_grid(R, R.H, x, y)
    asp = sample_grid(R, R.mask("aspect") * 360, x, y)
    for nm, spec in COMMUNITY.items():
        m = c == CID[nm]
        names = list(spec["mix"]); w = np.array([spec["mix"][k] for k in names], float); w /= w.sum()
        sp[m] = r.choice(names, size=int(m.sum()), p=w)
    # rules: buckeye only in high coves (above -40), white pine on south faces / spurs, hemlock wet
    southish = (asp > 140) & (asp < 290)
    sp[(sp == "yellow_buckeye") & (H < -40)] = "sugar_maple"
    sp[(sp == "white_pine") & ~southish & (c != CID["crest"]) & (c != CID["slick"])] = "northern_red_oak"
    sp[(sp == "eastern_hemlock") & (sample_grid(R, dw, x, y) > 160) & (c == CID["cove"])] = "tulip_poplar"
    sp[oldg & (c == CID["cove"]) & (r.random(len(x)) < 0.35)] = "tulip_poplar"
    # sizes: age classes (most mature, some young, a few giants), community / old-growth factors
    size = np.clip(0.72 + 0.34 * r.standard_normal(len(x)) * 0.5 + 0.22 * r.random(len(x)), 0.45, 1.3)
    for nm, spec in COMMUNITY.items():
        if "size" in spec:
            size[c == CID[nm]] *= spec["size"]
    young = r.random(len(x)) < 0.18
    size[young] *= 0.55
    size[oldg & (sp == "tulip_poplar")] = np.clip(size[oldg & (sp == "tulip_poplar")] * 1.2, 0.95, 1.18)
    und = np.isin(sp, ["flowering_dogwood", "sourwood"])
    size[und] = np.clip(size[und], 0.5, 1.2)
    # spacing: crowns don't overlap much (radius ~ 0.33 crown width), big trees first
    width = np.array([SPECIES[s]["width"] for s in sp]) * size
    keep = poisson_thin(x, y, 0.33 * width, r, order=np.argsort(-width))
    return dict(x=x[keep], y=y[keep], sp=sp[keep], size=size[keep], c=c[keep])


def scatter_shrubs(R, C, dw, trails_d, excl, tunnel_d, tunnels, thick, r):
    """Laurel hell: rhodo_thicket tiles (the vegetation agent's 9 m tile) on a ~6.5 m grid over
    the hell mask, rhodo_tunnel tiles chained every 8 m along the tunnels (their crawl tunnel runs
    along the tile's x); rosebay clumps at the edges and on the creek banks; mountain laurel on
    crests and slicks; Catawba on the bald; flame azalea at the bald's edge."""
    noise = terrain.Noise(SEED + 7)
    out = []
    # thicket tiles
    x, y = jitter_grid(R, 6.5, r)
    x += r.uniform(-1, 1, len(x)); y += r.uniform(-1, 1, len(y))
    c = sample_grid(R, C, x, y)
    # (placed from the thicket mask itself, so what blocks is what shows)
    m = (sample_grid(R, thick, x, y) == 255) & (sample_grid(R, tunnel_d, x, y) > 4.6) & (sample_grid(R, trails_d, x, y) > 4.0)
    out.append(dict(x=x[m], y=y[m], sp=np.full(int(m.sum()), "rhodo_thicket", object),
                    rot=(r.integers(0, 4, int(m.sum())) * math.pi / 2 + r.normal(0, 0.15, int(m.sum()))),
                    size=r.uniform(0.92, 1.08, int(m.sum()))))
    # tunnel tiles along every tunnel polyline (estate frame), inside the hell
    tx, ty, trot = [], [], []
    for P in tunnels:
        seg = np.hypot(*np.diff(P[:, :2], axis=0).T)
        s = np.concatenate([[0], np.cumsum(seg)])
        for st in np.arange(4.0, s[-1] - 3.0, 7.0):
            k = int(np.searchsorted(s, st))
            k = min(max(k, 1), len(P) - 1)
            a, b = P[k - 1, :2], P[k, :2]
            t = (st - s[k - 1]) / max(s[k] - s[k - 1], 1e-6)
            q = a + (b - a) * t
            if sample_grid(R, thick, q[0], q[1]) != 128:
                continue
            k0, k1 = int(np.searchsorted(s, st - 4)), min(int(np.searchsorted(s, st + 4)), len(P) - 1)
            d = P[k1, :2] - P[max(k0, 0), :2]
            tx.append(q[0]); ty.append(q[1]); trot.append(math.atan2(d[1], d[0]))
    out.append(dict(x=np.array(tx), y=np.array(ty), sp=np.full(len(tx), "rhodo_tunnel", object), rot=np.array(trot),
                    size=np.ones(len(tx))))
    # clumps
    x, y = jitter_grid(R, 2.4, r)
    c = sample_grid(R, C, x, y)
    d_tr = sample_grid(R, trails_d, x, y)
    d_tu = sample_grid(R, tunnel_d, x, y)
    d_w = sample_grid(R, dw, x, y)
    ex = sample_grid(R, excl, x, y)
    nz = noise.fbm(x, y, 30.0, 3)
    u = r.random(len(x))
    rule = [  # (where, probability, species chooser)
        ((c == CID["hell"]), 0.10, lambda n: np.where(r.random(n) < 0.8, "rosebay_rhododendron", "mountain_laurel")),
        ((c == CID["ripar"]) & (d_w < 12), 0.16 + 0.14 * (nz > 0), lambda n: np.full(n, "rosebay_rhododendron", object)),
        ((c == CID["ripar"]) & (d_w >= 12), 0.06, lambda n: np.full(n, "rosebay_rhododendron", object)),
        ((c == CID["crest"]), 0.30 + 0.3 * (nz > 0), lambda n: np.full(n, "mountain_laurel", object)),
        ((c == CID["slick"]), 0.55 + 0.3 * (nz > 0), lambda n: np.where(r.random(n) < 0.85, "mountain_laurel", "rosebay_rhododendron")),
        ((c == CID["bald"]), 0.40 + 0.2 * (nz > 0), lambda n: np.where(r.random(n) < 0.8, "catawba_rhododendron", "mountain_laurel")),
        ((c == CID["oak"]), 0.03 + 0.05 * (nz > 0.2), lambda n: np.full(n, "mountain_laurel", object)),
        ((c == CID["cove"]), 0.015, lambda n: np.full(n, "rosebay_rhododendron", object)),
    ]
    chosen = np.zeros(len(x), bool)
    for where, prob, pick in rule:
        m = where & ~chosen & (u < prob) & ~ex & (d_tr > 2.2) & (d_tu > 1.3) & (d_w > 1.5)
        n = int(m.sum())
        if not n:
            continue
        sp = pick(n)
        size = np.clip(0.8 + 0.25 * r.standard_normal(n), 0.5, 1.35)
        out.append(dict(x=x[m], y=y[m], sp=sp, rot=r.uniform(0, 2 * math.pi, n), size=size))
        chosen |= m
    bc, br = LF.BALD["center"], LF.BALD["radius"]
    rad = np.hypot(x - bc[0], y - bc[1])
    m = (np.abs(rad - br * 0.95) < 18) & (u > 0.97) & ~ex & (d_tr > 2.5) & ~chosen
    n = int(m.sum())
    out.append(dict(x=x[m], y=y[m], sp=np.full(n, "flame_azalea", object), rot=r.uniform(0, 2 * math.pi, n),
                    size=np.clip(0.85 + 0.2 * r.standard_normal(n), 0.6, 1.2)))
    return {k: np.concatenate([o[k] for o in out]) for k in ("x", "y", "sp", "rot", "size")}


def scatter_ground(R, C, dw, trails_d, excl, r):
    """Christmas fern on the cove floor (densest in coves and gaps), cinnamon fern in the seeps,
    doghobble arching over the creek banks, grass tufts on the bald and the Gap."""
    noise = terrain.Noise(SEED + 11)
    x, y = jitter_grid(R, 1.6, r)
    c = sample_grid(R, C, x, y)
    wet = sample_grid(R, R.mask("wetness"), x, y)
    d_w = sample_grid(R, dw, x, y)
    d_tr = sample_grid(R, trails_d, x, y)
    ex = sample_grid(R, excl, x, y)
    nz = noise.fbm(x, y, 18.0, 3)
    p = np.zeros(len(x))
    p[c == CID["cove"]] = 0.62            # (the cove floor: knee-high Christmas fern carpet)
    p[c == CID["ripar"]] = 0.30
    p[c == CID["oak"]] = 0.08 + 0.14 * (wet[c == CID["oak"]] > 0.45)
    p[c == CID["crest"]] = 0.03
    p *= np.clip(0.7 + 1.4 * nz, 0, 1.6)
    u = r.random(len(x))
    ok = ~ex & (d_tr > 1.6)
    fern = (u < p) & ok
    cinn = fern & (wet > 0.62) & (r.random(len(x)) < 0.6)
    hob = (c == CID["ripar"]) & (d_w > 1.5) & (d_w < 7) & (r.random(len(x)) < 0.22) & ok & ~fern
    # (the bald's and the Gap's grass is the runtime's grass blades, from the splat: no tuft instances)
    sp = np.full(len(x), "", object)
    sp[fern] = "christmas_fern"; sp[cinn] = "cinnamon_fern"; sp[hob] = "doghobble"
    m = sp != ""
    n = int(m.sum())
    size = np.clip(0.8 + 0.3 * r.standard_normal(n), 0.45, 1.5)
    size[sp[m] == "christmas_fern"] *= 1.35                      # knee-high (0.55 m model -> 0.6-0.9 m)
    return dict(x=x[m], y=y[m], sp=sp[m], rot=r.uniform(0, 2 * math.pi, n), size=size)


# ------------------------------------------------------------------ vista clearing
def vista_clear(R, trees, margin=2.5, reach=1400.0):
    """Real overlooks are kept open: within `reach` m of each lookout, any tree whose crown top
    would come within `margin` m of the sight line to the house's upper floor is cut (or, past
    60 m, topped to a shrub-height crown). Returns the cut mask."""
    cut = np.zeros(len(trees["x"]), bool)
    hgt = np.array([SPECIES[s]["height"] for s in trees["sp"]]) * trees["size"]
    gz = R.h(trees["x"], trees["y"])
    hx, hy, hz = LF.HOUSE_EYE
    for nm, (ax, ay) in LF.LOOKOUTS.items():
        az = float(R.h(ax, ay)) + 1.7
        L = math.hypot(hx - ax, hy - ay)
        ux, uy = (hx - ax) / L, (hy - ay) / L
        rx, ry = trees["x"] - ax, trees["y"] - ay
        t = rx * ux + ry * uy
        lat = np.abs(-rx * uy + ry * ux)
        # (estate_link: + the crown's half-width: a broad crown standing just outside the band still
        # reached over the line; a re-scatter put a red oak's into the Knob's view, -17 m)
        crown = np.array([SPECIES[s]["width"] for s in trees["sp"]]) * trees["size"] * 0.5
        near = (t > 0) & (t < reach) & (lat < 6 + 0.06 * t + crown)
        line_z = az + (t / L) * (hz - az)
        cut |= near & (gz + hgt > line_z - margin)
    return cut


# ------------------------------------------------------------------ canopy + light
def canopy_volume(R, trees, shrubs):
    """Crown top / base heights (absolute) and leaf density per cell from the placed plants."""
    top = np.full(R.H.shape, -1e9)
    base = np.full(R.H.shape, 1e9)
    cell = R.cell
    for x, y, sp, size in zip(trees["x"], trees["y"], trees["sp"], trees["size"]):
        s = SPECIES[sp]
        h, w = s["height"] * size, s["width"] * size * 0.5
        cb = {"broadleaf": 0.45, "conifer": 0.18, "pine": 0.55}[s["kind"]] * h
        g = float(R.h(x, y))
        i0, i1 = int((x - w + 768) / cell), int((x + w + 768) / cell) + 1
        j0, j1 = int((y + OY - w + 768) / cell), int((y + OY + w + 768) / cell) + 1
        if i1 < 0 or j1 < 0 or i0 >= R.n or j0 >= R.n:
            continue
        i0, j0, i1, j1 = max(i0, 0), max(j0, 0), min(i1, R.n), min(j1, R.n)
        xx = -768 + np.arange(i0, i1) * cell - x
        yy = -768 + np.arange(j0, j1) * cell - (y + OY)
        d2 = (xx[None, :] ** 2 + yy[:, None] ** 2) / (w * w)
        inside = d2 < 1
        prof = np.sqrt(np.clip(1 - d2, 0, 1))
        if s["kind"] == "conifer":                    # a cone: top at the centre, wide low
            t_ = g + cb + (h - cb) * (1 - np.sqrt(np.clip(d2, 0, 1)))
            b_ = np.full(d2.shape, g + cb)
        else:
            mid, hr = g + (cb + h) / 2, (h - cb) / 2
            t_, b_ = mid + hr * prof, mid - hr * prof
        sl = (slice(j0, j1), slice(i0, i1))
        top[sl] = np.where(inside, np.maximum(top[sl], t_), top[sl])
        base[sl] = np.where(inside, np.minimum(base[sl], b_), base[sl])
    # shrubs / thickets: a low dense layer
    for x, y, sp, size in zip(shrubs["x"], shrubs["y"], shrubs["sp"], shrubs["size"]):
        s = SPECIES[sp]
        h, w = s["height"] * size, s["width"] * size * 0.5
        g = float(R.h(x, y))
        j, i = int(round((y + OY + 768) / cell)), int(round((x + 768) / cell))
        k = max(1, int(w / cell))
        sl = (slice(max(j - k, 0), j + k + 1), slice(max(i - k, 0), i + k + 1))
        top[sl] = np.maximum(top[sl], g + h)
        base[sl] = np.minimum(base[sl], g + 0.4)
    return top, base


def light_bake(R, top, base, look):
    """r: sun n.l x terrain shadow; g: canopy transmittance toward the sun (sunflecks through
    the gaps); b: sky visibility (terrain horizon x canopy cover); a: terrain shadow."""
    rgb, vis, sky = terrain.light(R.H, R.cell, look)
    n, _, _ = terrain.normals(R.H, R.cell)
    sd = np.asarray(look["sun_dir"], float)
    Lv = -sd / np.linalg.norm(sd)
    ndl = np.clip((n * Lv).sum(axis=2), 0, 1)
    hor = math.hypot(Lv[0], Lv[1])
    tanE = Lv[2] / hor
    lx, ly = Lv[0] / hor, Lv[1] / hor
    has = top > -1e8
    zt = np.where(has, top, -1e9)
    zb = np.where(has, base, 1e9)
    ny, nx = R.H.shape
    jj, ii = np.mgrid[0:ny, 0:nx].astype(np.float64)
    g1 = terrain.Grid(0, 0, 1, nx, ny)
    tau = np.zeros(R.H.shape)
    sigma = 0.09                                            # leaf density (1/m inside a crown)
    step = 2.0
    for k in range(1, 90):
        t = k * step
        u, v = ii + lx * t / R.cell, jj + ly * t / R.cell
        z = R.H + 1.2 + t * tanE
        iu = np.clip(np.round(u).astype(np.int64), 0, nx - 1)
        jv = np.clip(np.round(v).astype(np.int64), 0, ny - 1)
        inside = (z > zb[jv, iu]) & (z < zt[jv, iu])
        tau += sigma * step * inside
        if t * tanE > 60:
            break
    canopy = np.exp(-tau)
    cover = terrain.blur(((zt - R.H) > 4).astype(float), 10 / R.cell)
    skyc = sky * (1 - 0.72 * cover)
    thick = terrain.blur(((zt - R.H) > 1.0) & ((zt - R.H) < 7), 1.0)
    skyc *= 1 - 0.5 * thick                                 # under a thicket
    return dict(r=ndl * vis, g=canopy, b=np.clip(skyc / max(np.percentile(skyc, 99.5), 1e-3), 0, 1), a=vis,
                stats=dict(canopy_mean_cove=None))


# ------------------------------------------------------------------ props
def place_logs(R, C, trails_d, excl, r, n_ghost=420, n_blow=160):
    """Chestnut ghosts (silver, barkless, upper slopes c > 0.5) and blowdowns with root wads
    (coves, c < 0.5). Each log rests on the ground along its length."""
    curv = R.mask("curvature")
    logs = []
    tries = 0
    while len([l for l in logs if l["kind"] == "ghost"]) < n_ghost and tries < 20000:
        tries += 1
        x, y = r.uniform(-640, 560), r.uniform(-1290, -190)
        j, i = R.ij(x, y)
        c = C[j, i]
        if c not in (CID["oak"], CID["crest"], CID["slick"]) or curv[j, i] < 0.5 or excl[j, i]:
            continue
        logs.append(dict(kind="ghost", x=x, y=y, L=r.uniform(12, 24), d=r.uniform(0.5, 1.2)))
    tries = 0
    while len([l for l in logs if l["kind"] == "blow"]) < n_blow and tries < 20000:
        tries += 1
        x, y = r.uniform(-640, 560), r.uniform(-1290, -190)
        j, i = R.ij(x, y)
        if C[j, i] not in (CID["cove"], CID["ripar"]) or curv[j, i] > 0.5 or excl[j, i]:
            continue
        logs.append(dict(kind="blow", x=x, y=y, L=r.uniform(14, 26), d=r.uniform(0.5, 1.4)))
    out = []
    gy, gx = np.gradient(terrain.blur(R.H, 3.0), R.cell)
    for lg in logs:
        j, i = R.ij(lg["x"], lg["y"])
        down = math.atan2(-gy[j, i], -gx[j, i])            # fall line: logs lie across or down it
        yaw = down + (r.choice([0.0, math.pi / 2]) + r.normal(0, 0.35))
        dx, dy = math.cos(yaw), math.sin(yaw)
        ts = np.linspace(-lg["L"] / 2, lg["L"] / 2, int(lg["L"]) + 1)
        px, py = lg["x"] + ts * dx, lg["y"] + ts * dy
        gz = R.h(px, py)
        if (sample_grid(R, trails_d, px, py) < 2.5 + lg["d"]).any() or sample_grid(R, excl, px, py).any():
            continue
        if (sample_grid(R, C, px, py) == CID["water"]).any():
            continue
        r_ = lg["d"] / 2
        # the axis line resting on the ground: lowest line above every ground point, through 2
        z0, z1 = gz[0] + r_ * 0.8, gz[-1] + r_ * 0.8
        line = z0 + (z1 - z0) * (ts - ts[0]) / (ts[-1] - ts[0])
        lift = float(np.max(gz + r_ * 0.8 - line))
        line = line + max(lift, 0)
        gap = line - r_ - gz
        if gap.max() > 2.5:                                 # spanning a gully: skip (looks floating)
            continue
        out.append(dict(kind=lg["kind"], x0=float(px[0]), y0=float(py[0]), z0=float(line[0]),
                        x1=float(px[-1]), y1=float(py[-1]), z1=float(line[-1]), r=r_,
                        wad=lg["kind"] == "blow"))
    return out


def place_boulders(R, C, trails_d, excl, r):
    """Cove boulder fields (high sediment, concave), creek boulders, the Narrows' 3-5 m chute."""
    sed, curv = R.mask("sediment"), R.mask("curvature")
    water = C == CID["water"]
    _, _, dwc = terrain.nearest_seed(water)
    dw = dwc * R.cell
    x, y = jitter_grid(R, 4.0, r)
    j, i = R.ij(x, y)
    c = C[j, i]
    p = np.zeros(len(x))
    p[(c == CID["cove"]) & (curv[j, i] < 0.48)] = 0.05
    p[(c == CID["cove"]) & (sed[j, i] > 0.3)] = 0.12
    p[(dw[j, i] < 7) & (c != CID["water"])] = 0.18             # creek banks
    p[(c == CID["slick"])] = 0.06                               # talus
    narrows = (x < -540) & (dw[j, i] < 14)
    p[narrows] = 0.5
    ok = (r.random(len(x)) < p) & ~excl[j, i] & (trails_d[j, i] > 3.0)
    x, y = x[ok], y[ok]
    rad = np.where(narrows[ok], r.uniform(1.4, 2.6, ok.sum()), np.clip(r.lognormal(-0.3, 0.45, ok.sum()), 0.3, 2.0))
    keep = poisson_thin(x, y, rad * 1.1, r, order=np.argsort(-rad))
    x, y, rad = x[keep], y[keep], rad[keep]
    z = R.h(x, y)
    return [dict(x=float(a), y=float(b), z=float(zz) - 0.35 * float(rr), r=float(rr), sq=float(r.uniform(0.55, 0.85)),
                 yaw=float(r.uniform(0, 6.283)), seed=float(r.random())) for a, b, zz, rr in zip(x, y, z, rad)]


def trail_frame(points, near):
    """Nearest point on a routed trail (estate frame) to `near`, and the unit direction there."""
    P = terrain.spline(points, 0.5)
    k = int(np.argmin(np.hypot(P[:, 0] - near[0], P[:, 1] - near[1])))
    a, b = P[max(k - 4, 0)], P[min(k + 4, len(P) - 1)]
    d = np.array([b[0] - a[0], b[1] - a[1]]); d /= np.hypot(*d)
    return P[k][:2], d


def river_fit(R):
    p = os.path.join(R.dir, "river_fit.json")
    return json.load(open(p)) if os.path.exists(p) else None


def river_rocks(R, C, trails_d, r):
    """The Laurel River's boulders: big blocks on its rapids (the shoals, the ledge at the head of the
    Narrows, the Narrows cascade), scattered rocks breaking the surface mid-channel, cobble-bar
    rocks; the Nantahala / Linville look (the river is the main stem west of x -480)."""
    water = C == CID["water"]
    bars = R.mask("bars") > 0.5
    x, y = jitter_grid(R, 2.6, r)
    j, i = R.ij(x, y)
    main = (x < -480) & ((y < -752) | (x < -560))
    _, _, dwc = terrain.nearest_seed(water)
    dw = dwc[j, i] * R.cell
    p = np.zeros(len(x))
    p[water[j, i] & main] = 0.035
    p[bars[j, i] & main & ~water[j, i]] = 0.03
    rapid = np.zeros(len(x), bool)
    for cx, cy, rad in RAPIDS:
        m = (np.hypot(x - cx, y - cy) < rad) & main & (dw < 8)
        rapid |= m
    p[rapid] = 0.32
    ok = (r.random(len(x)) < p) & (trails_d[j, i] > 3.5)
    x, y, rapid = x[ok], y[ok], rapid[ok]
    n = len(x)
    rad = np.where(rapid, r.uniform(1.0, 3.2, n), np.clip(r.lognormal(-0.1, 0.5, n), 0.4, 2.2))
    keep = poisson_thin(x, y, rad * 1.05, r, order=np.argsort(-rad))
    x, y, rad = x[keep], y[keep], rad[keep]
    z = R.h(x, y)
    # (in the channel a rock sits on the bed but breaks the surface: its top 0.3-0.5 r over the water)
    wl = np.where(np.isfinite(R.lake_level) & (R.H < R.lake_level), R.lake_level, R.river_level)
    jj, ii = R.ij(x, y)
    w = wl[jj, ii]
    zc = np.where(np.isfinite(w), np.maximum(z - 0.3 * rad, w - 0.15 * rad), z - 0.3 * rad)
    return [dict(x=float(a), y=float(b), z=float(zz), r=float(rr), sq=float(r.uniform(0.5, 0.8)),
                 yaw=float(r.uniform(0, 6.283)), seed=float(r.random())) for a, b, zz, rr in zip(x, y, zc, rad)]


# the rapids (estate frame: centre, radius): the shoals, the ledge at the Narrows' head, the cascade
RAPIDS = [(-585.0, -1055.0, 34.0), (-575.0, -792.0, 34.0), (-600.0, -762.0, 26.0), (-640.0, -748.0, 30.0)]


def river_props(R, routed, gb=None, Hb=None):
    """The swinging bridge over the Laurel River (on the fitted crossing, river_fit.json) and the
    old rail line on the river road (two rails on ties, along the routed road at its graded height)."""
    out = []
    fit = river_fit(R)
    if fit:
        b = fit["bridge"]
        (ax, ay), (bx, by) = b["a"], b["b"]
        za, zb = float(R.h(ax, ay)) + 0.15, float(R.h(bx, by)) + 0.15
        wl = np.where(np.isfinite(R.lake_level) & (R.H < R.lake_level), R.lake_level, R.river_level)
        mx, my = (ax + bx) / 2, (ay + by) / 2
        m = np.hypot(R.X - mx, R.Y - my) < 10
        water = float(np.nanmedian(wl[m])) if np.isfinite(wl[m]).any() else float(R.h(mx, my))
        # the deck sags 0.9 m at mid-span and hangs ~4.5 m over the water: where the banks are lower it
        # stands on timber cribs with steps up from the trail (0.25 m risers); towers of 4.2 m at the
        # ends carry the two cable handrails
        lift = 4.5 + 0.9
        # (each end walks out along the axis to where the bank is high enough: high bank to high bank)
        L0 = math.hypot(bx - ax, by - ay); ux0, uy0 = (bx - ax) / L0, (by - ay) / L0
        for _ in range(40):
            if float(R.h(ax, ay)) >= water + 3.8:
                break
            ax, ay = ax - ux0 * 0.75, ay - uy0 * 0.75
        for _ in range(40):
            if float(R.h(bx, by)) >= water + 3.8:
                break
            bx, by = bx + ux0 * 0.75, by + uy0 * 0.75
        za, zb = float(R.h(ax, ay)) + 0.15, float(R.h(bx, by)) + 0.15
        zd_a, zd_b = max(za, water + lift), max(zb, water + lift)
        # the steps: outward from each deck end, one riser per tread, until they reach the ground
        L = math.hypot(bx - ax, by - ay); ux, uy = (bx - ax) / L, (by - ay) / L
        def steps(ex, ey, zt, sgn):
            st = []
            for i in range(1, 60):
                sx, sy = ex + sgn * ux * 0.3 * i, ey + sgn * uy * 0.3 * i
                top = zt - 0.16 * i
                g = float(R.h(sx, sy))
                if top <= g + 0.05:
                    break
                st.append([round(sx, 2), round(sy, 2), round(top, 2), round(g, 2)])
            return st
        out.append(dict(kind="swing_bridge", x0=ax, y0=ay, z0=zd_a, x1=bx, y1=by, z1=zd_b, sag=0.9, width=b.get("width", 1.2),
                        tower=4.2, water=round(water, 2), ground0=za, ground1=zb, riser=0.16, tread=0.3,
                        steps0=steps(ax, ay, zd_a, -1), steps1=steps(bx, by, zd_b, 1)))
    road = routed.get("river_road")
    if road:
        P = terrain.spline([(x, y) for x, y in road], 2.0)
        z = R.h(P[:, 0], P[:, 1])
        pts = [[round(float(px), 2), round(float(py), 2), round(float(pz) + 0.05, 2)] for px, py, pz in zip(P[:, 0], P[:, 1], z)]
        # beyond the square the line runs on down the valley to the town (drawn on the ring): it
        # eases down at 3% on a gravel embankment to the valley floor, then along the south bank to
        # the town's truss bridge (4th value: the ground under it, for the embankment)
        if gb is not None:
            x0, y0, z0 = pts[-1]
            zc = z0
            for xe in np.arange(x0 - 12.0, -1575.0, -12.0):
                ye = float(np.interp(xe, [-1600, -1300, -900, -770], [-835, -817, -796, -786]))
                g = float(backdrop_height(gb, Hb, np.array([xe]), np.array([ye]))[0])
                zc = max(g + 0.6, zc - 0.03 * 12.0)
                pts.append([round(float(xe), 2), round(ye, 2), round(zc, 2), round(g, 2)])
        out.append(dict(kind="rail", pts=pts))
    return out


def authored_props(R, routed, r):
    props = []
    # the footlog: 16 m sawn log with a handrail over the creek at the ford
    fl = LF.LANDMARKS["footlog"]
    (cx, cy), d = trail_frame(routed["creek_trail"], fl)
    a = np.array([cx, cy]) - 8 * d
    b = np.array([cx, cy]) + 8 * d
    ze = max(float(R.h(*a)), float(R.h(*b))) + 0.12
    props.append(dict(kind="footlog", x0=float(a[0]), y0=float(a[1]), x1=float(b[0]), y1=float(b[1]), z=ze, r=0.45,
                      rail_side=1))
    # the Poplar Cove chestnut ghost across the creek trail, one end propped on a boulder:
    # 1.2 m thick, its underside 1.25 m over the trail (crawl under: crouch is 1.1 m)
    pc = LF.LANDMARKS["poplar_cove"]
    (tx, ty), d = trail_frame(routed["creek_trail"], pc)
    nrm = np.array([-d[1], d[0]])
    p0 = np.array([tx, ty]) - nrm * 7.0
    p1 = np.array([tx, ty]) + nrm * 11.0
    gz_t = float(R.h(tx, ty))
    z_axis_t = gz_t + 1.25 + 0.6
    g0, g1 = float(R.h(*p0)), float(R.h(*p1))
    # rests on the ground at p0's end (the root end), on a 2 m boulder at p1's
    z0 = g0 + 0.6
    z1 = z0 + (z_axis_t - z0) * (np.hypot(*(p1 - p0)) / np.hypot(*(np.array([tx, ty]) - p0)))
    props.append(dict(kind="hero_ghost", x0=float(p0[0]), y0=float(p0[1]), z0=z0, x1=float(p1[0]), y1=float(p1[1]),
                      z1=float(z1), r=0.6, wad=True))
    props.append(dict(kind="boulder", x=float(p1[0] - nrm[0] * 0.8), y=float(p1[1] - nrm[1] * 0.8),
                      z=float(min(g1, z1 - 0.6 - 1.1)), r=max(1.2, (z1 - 0.6 - g1) * 0.62), sq=0.9, yaw=0.3, seed=0.4))
    # the Gap: the overlook's stone wall along the north side of the pad, the parkway's edge
    gp = LF.LANDMARKS["gap"]
    gz = float(R.h(*gp))
    for k, (x0, x1) in enumerate([(-326, -306), (-294, -274)]):     # a gap in the middle for the trail
        props.append(dict(kind="wall", x0=x0, y0=gp[1] + 16, x1=x1, y1=gp[1] + 16, z=gz, h=0.9, t=0.6))
    # lookout slabs: flat gneiss slabs at each lookout, and the Knob's summit rock (climbable
    # steps of <= 0.9 m: the jump clears ~1 m)
    for nm, (x, y) in LF.LOOKOUTS.items():
        # (behind and beside the lookout: the view to the house stays open)
        toh = math.atan2(LF.HOUSE_EYE[1] - y, LF.HOUSE_EYE[0] - x)
        for k in range(4):
            a_ = toh + math.pi + r.uniform(-1.6, 1.6)
            sx, sy = x + math.cos(a_) * r.uniform(2.5, 6), y + math.sin(a_) * r.uniform(2.5, 6)
            props.append(dict(kind="slab", x=float(sx), y=float(sy), z=float(R.h(sx, sy)) - 0.15, w=float(r.uniform(2.5, 4.5)),
                              dd=float(r.uniform(1.8, 3.2)), h=float(r.uniform(0.25, 0.45)), yaw=float(r.uniform(0, 3.14))))
    # the falls sheet: from the lip's water to the pool
    lip = LF.LANDMARKS["falls_lip"]
    wl = np.where(np.isfinite(R.lake_level) & (R.H < R.lake_level), R.lake_level, R.river_level)
    def lvl(x, y, rr=6.0):
        m = np.hypot(R.X - x, R.Y - y) < rr
        v = wl[m][np.isfinite(wl[m])]
        return float(np.median(v)) if len(v) else float(R.h(x, y))
    # (fitted to where the water actually drops: the steepest water cells near the lip, the drop's
    # line along their mean gradient; erosion decides the creek's exact crossing)
    gy, gx = np.gradient(np.where(np.isfinite(wl), wl, np.nan), R.cell)
    gmag = np.hypot(gx, gy)
    near = (np.hypot(R.X - lip[0], R.Y - lip[1]) < 28) & np.isfinite(gmag) & (gmag > 0.6)
    if near.sum() >= 4:
        cx, cy = float(R.X[near].mean()), float(R.Y[near].mean())
        dx, dy = float(-gx[near].mean()), float(-gy[near].mean())        # downhill (estate frame: rows run north)
        L = math.hypot(dx, dy) or 1.0
        dx, dy = dx / L, dy / L
        ext = float(np.sqrt(((R.X[near] - cx) * -dy + (R.Y[near] - cy) * dx).var()) * 3.0)
        top, bot = (cx - dx * 4.5, cy - dy * 4.5), (cx + dx * 4.5, cy + dy * 4.5)
        props.append(dict(kind="falls", x0=top[0], y0=top[1], z0=lvl(top[0] - dx * 3, top[1] - dy * 3) + 0.1,
                          x1=bot[0], y1=bot[1], z1=lvl(*LF.LANDMARKS["plunge_pool"]) + 0.05, width=float(np.clip(ext, 5.0, 9.0))))
    else:
        props.append(dict(kind="falls", x0=lip[0] + 5.0, y0=lip[1] + 0.5, z0=lvl(lip[0] + 9, lip[1]) + 0.1,
                          x1=lip[0] - 4.0, y1=lip[1] - 2.0, z1=lvl(*LF.LANDMARKS["plunge_pool"]) + 0.05, width=6.5))
    kx, ky = LF.LANDMARKS["knob"]
    g = float(R.h(kx, ky))
    for k, (dx, dy, w, h) in enumerate([(3.0, -1.0, 5.0, 0.9), (1.5, -0.5, 3.8, 1.8), (0.4, 0.0, 2.8, 2.7), (-0.4, 0.3, 2.0, 3.6), (-0.9, 0.5, 1.4, 4.4)]):
        props.append(dict(kind="slab", x=kx + dx, y=ky + dy, z=g - 0.3, w=w, dd=w * 0.8, h=h + 0.3, yaw=0.4))
    # snags: a few grey dead hemlocks near the creek (the adelgid; honest detail)
    return props


def colliders(R, trees, logs, boulders, props):
    """AABBs in three.js coords (min x, y, z, max x, y, z)."""
    out = []
    def box3(xmin, xmax, ymin, ymax, zmin, zmax):      # estate x/y, height z -> three
        out.append((xmin, zmin, -(ymax + OY), xmax, zmax, -(ymin + OY)))
    for x, y, sp, size in zip(trees["x"], trees["y"], trees["sp"], trees["size"]):
        t = SPECIES[sp]["trunk"] * size
        if t < 0.08:
            continue
        g = float(R.h(x, y))
        box3(x - t * 0.85, x + t * 0.85, y - t * 0.85, y + t * 0.85, g - 1.0, g + 7.0)
    def capsule(x0, y0, z0, x1, y1, z1, r_, to_ground=True, k_=0.9):
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(2, int(L / 0.7))
        for t in np.linspace(0, 1, n):
            x, y, z = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z0 + (z1 - z0) * t
            g = float(R.h(x, y))
            lo = g - 0.5 if to_ground and z - r_ - g < 0.6 else z - r_
            box3(x - r_ * k_, x + r_ * k_, y - r_ * k_, y + r_ * k_, lo, z + r_ * 0.92)
    for lg in logs:
        capsule(lg["x0"], lg["y0"], lg["z0"], lg["x1"], lg["y1"], lg["z1"], lg["r"])
    for b in boulders:
        rr = b["r"] * 0.8
        box3(b["x"] - rr, b["x"] + rr, b["y"] - rr, b["y"] + rr, b["z"] - b["r"], b["z"] + b["r"] * b["sq"] * 0.95)
    for p in props:
        if p["kind"] == "footlog":
            x0, y0, x1, y1, z = p["x0"], p["y0"], p["x1"], p["y1"], p["z"]
            L = math.hypot(x1 - x0, y1 - y0); ux, uy = (x1 - x0) / L, (y1 - y0) / L
            for t in np.linspace(0, 1, int(L / 0.5) + 1):
                x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                box3(x - 0.33, x + 0.33, y - 0.33, y + 0.33, z - 0.9, z)             # the deck (walk on it)
                rx, ry = x - uy * 0.55 * p["rail_side"], y + ux * 0.55 * p["rail_side"]
                box3(rx - 0.08, rx + 0.08, ry - 0.08, ry + 0.08, z, z + 1.05)         # the handrail
        elif p["kind"] == "swing_bridge":
            x0, y0, x1, y1 = p["x0"], p["y0"], p["x1"], p["y1"]
            L = math.hypot(x1 - x0, y1 - y0); ux, uy = (x1 - x0) / L, (y1 - y0) / L
            hw = p["width"] / 2
            # the steps up onto each crib (outward from the ends, down to the ground)
            for sx, sy, top, g in p["steps0"] + p["steps1"]:
                box3(sx - 0.16, sx + 0.16, sy - 0.62, sy + 0.62, g - 0.5, top) if abs(ux) > abs(uy) else \
                    box3(sx - 0.62, sx + 0.62, sy - 0.16, sy + 0.16, g - 0.5, top)
            for t in np.linspace(0, 1, int(L / 0.4) + 1):
                x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                z = p["z0"] + (p["z1"] - p["z0"]) * t - p["sag"] * 4 * t * (1 - t)
                dw = hw + 0.02                                                        # the plank deck, full width
                box3(x - max(abs(uy) * dw, 0.22), x + max(abs(uy) * dw, 0.22), y - max(abs(ux) * dw, 0.22), y + max(abs(ux) * dw, 0.22), z - 0.25, z)
                for sd in (-1, 1):                                                    # the cable sides
                    rx, ry = x - uy * (hw + 0.05) * sd, y + ux * (hw + 0.05) * sd
                    box3(rx - 0.06, rx + 0.06, ry - 0.06, ry + 0.06, z, z + 1.15)
        elif p["kind"] == "hero_ghost":
            capsule(p["x0"], p["y0"], p["z0"], p["x1"], p["y1"], p["z1"], p["r"], to_ground=False)
        elif p["kind"] == "boulder":
            rr = p["r"] * 0.8
            box3(p["x"] - rr, p["x"] + rr, p["y"] - rr, p["y"] + rr, p["z"] - p["r"], p["z"] + p["r"] * p["sq"] * 0.95)
        elif p["kind"] == "wall":
            box3(min(p["x0"], p["x1"]), max(p["x0"], p["x1"]), min(p["y0"], p["y1"]) - p["t"] / 2, max(p["y0"], p["y1"]) + p["t"] / 2,
                 p["z"] - 1.0, p["z"] + p["h"])
        elif p["kind"] == "slab":
            hw = min(p["w"], p["dd"]) * 0.45
            box3(p["x"] - hw, p["x"] + hw, p["y"] - hw, p["y"] + hw, p["z"] - 1.0, p["z"] + p["h"])
    return np.array(out, np.float32)


# ------------------------------------------------------------------ helpers: rasters, output
def texels(a):
    """Vertex grid (n x n) -> texel centres ((n-1) x (n-1)): 2x2 mean."""
    return 0.25 * (a[:-1, :-1] + a[1:, :-1] + a[:-1, 1:] + a[1:, 1:])


def u8(a):
    return np.round(np.clip(a, 0, 1) * 255).astype(np.uint8)


def north_valley(Hb, gb, noise):
    """The view back (brief, signature moment 5): beyond the house the land falls away. North of
    the estate the ring is reshaped into a valley, a low wooded ridge at ~1 km behind the house
    and a second one at the ring's edge, all below the lookouts' eye (+174..+255), so from Raven,
    the Knob and Painted Rock the house sits above its treeline with ridge after ridge behind it
    (the far ones are the sky's ridgelines, sky_wild.js, which now show over these)."""
    Xb, Yb = gb.xy()
    ye = Yb - OY                                            # estate y (north +)
    wob = 90.0 * noise.fbm(Xb + 1234.0, np.zeros_like(Xb), 700.0, 3)
    t = ye + wob
    prof_t = [80, 300, 620, 960, 1230, 1600]
    prof_h = [0.0, -55.0, -120.0, 25.0, -75.0, 95.0]
    target = np.interp(t, prof_t, prof_h)
    target += 45.0 * noise.fbm(Xb - 77.0, Yb + 5.0, 900.0, 3) * np.clip((ye - 300) / 600, 0, 1)
    detail = Hb - terrain.blur(Hb, 6)
    w = terrain.smoothstep(80.0, 300.0, ye)
    return Hb * (1 - w) + (target + 0.6 * detail) * w


def backdrop_height(gb, Hb, x, y, step=2):
    """Heights of the runtime's backdrop mesh (every `step`-th sample, triangles a-d-b / b-d-e as
    level.js buildBackdrop): trees placed in the ring sit on what is drawn."""
    c = gb.cell * step
    u = (np.asarray(x) - gb.x0) / c
    v = (np.asarray(y) + OY - gb.y0) / c
    m = (gb.nx - 1) // step
    i = np.clip(np.floor(u).astype(int), 0, m - 1); j = np.clip(np.floor(v).astype(int), 0, m - 1)
    fu, fv = u - i, v - j
    H2 = Hb[::step, ::step]
    a, b, d, e = H2[j, i], H2[j, i + 1], H2[j + 1, i], H2[j + 1, i + 1]
    # (a, d, b) when fu + fv <= 1, else (b, d, e)
    lower = fu + fv <= 1
    return np.where(lower, a + (b - a) * fu + (d - a) * fv, e + (d - e) * (1 - fu) + (b - e) * (1 - fv))


def town_line(routed):
    """The view down the valley to the town from the river road's end (kept open: vista clearing)."""
    rd = routed.get("river_road")
    if not rd:
        return None
    P = terrain.spline([(x, y) for x, y in rd], 1.0)[:, :2]
    return P[-24], np.array([-1700.0, -800.0])


def town_vista(x, y, routed, half=9.0, reach=420.0):
    line = town_line(routed)
    if line is None:
        return np.zeros(len(x), bool)
    a, b = line
    d = (b - a) / np.linalg.norm(b - a)
    rx, ry = x - a[0], y - a[1]
    along = rx * d[0] + ry * d[1]
    across = np.abs(rx * -d[1] + ry * d[0])
    return (along > -2) & (along < reach) & (across < half + along * 0.02)


def ring_forest(gb, Hb, r, routed=None):
    """The river valley's walls beyond the square (the ring, x < -768, toward the town) were bare
    green: forest on them, as instances of the cove's own species (impostors from 105 m), off the
    river, the road and the town's flats."""
    x, y = np.meshgrid(np.arange(-1500.0, -770.0, 9.0), np.arange(-1150.0, -440.0, 9.0))
    x = (x + r.uniform(-3.5, 3.5, x.shape)).ravel(); y = (y + r.uniform(-3.5, 3.5, y.shape)).ravel()
    h = backdrop_height(gb, Hb, x, y)
    hx = backdrop_height(gb, Hb, x + 6, y) - backdrop_height(gb, Hb, x - 6, y)
    hy = backdrop_height(gb, Hb, x, y + 6) - backdrop_height(gb, Hb, x, y - 6)
    slope = np.degrees(np.arctan(np.hypot(hx, hy) / 12.0))
    yc = np.interp(x, [-2500, -1800, -1300, -900, -700], [-820, -800, -780, -762, -752])
    off = np.abs(y - yc)
    ok = (slope > 7) & (off > 34) & (r.random(len(x)) < 0.8) & ~town_vista(x, y, routed or {})
    x, y, h, off = x[ok], y[ok], h[ok], off[ok]
    u = r.random(len(x))
    low = h < -150
    sp = np.where(low & (u < 0.35), "eastern_hemlock", np.where(u < 0.45, "tulip_poplar",
                  np.where(u < 0.7, "northern_red_oak", np.where(u < 0.82, "white_pine", np.where(u < 0.92, "chestnut_oak", "sugar_maple")))))
    size = np.clip(0.8 + 0.2 * r.standard_normal(len(x)), 0.55, 1.15)
    return dict(x=x, y=y, z=h - 0.4, sp=sp, size=size, rot=r.uniform(0, 2 * math.pi, len(x)))


def river_out(gb, Hb, x0=-768.0, x1=-2300.0):
    """The Laurel River beyond the square (estate frame): the valley floor of the ring west to the
    town, as a polyline [x, y, z, width] for the runtime's water ribbon."""
    Xb, Yb = gb.xy()
    vp = next(v for v in LF.VALLEYS if v["name"] == "laurel_river_lower")["points"]
    vx, vy = np.array([q[0] for q in vp])[::-1], np.array([q[1] for q in vp])[::-1]
    out = []
    for xe in np.arange(x0, x1 - 1, -24.0):
        i = int(round((xe - gb.x0) / gb.cell))
        col = Hb[:, i]
        ys = Yb[:, i] - OY
        yc = float(np.interp(xe, vx, vy))
        m = np.abs(ys - yc) < 40
        k = np.argmin(np.where(m, col, np.inf))
        out.append([round(float(xe), 1), round(yc, 1), round(float(col[k]) + 0.35, 2), 30.0 if xe > -1450 else 38.0])
    # smooth the line and keep the level falling
    a = np.array(out)
    for _ in range(3):
        a[1:-1, 1] = (a[:-2, 1] + 2 * a[1:-1, 1] + a[2:, 1]) / 4
    a[:, 2] = np.minimum.accumulate(a[:, 2])
    return a.round(2).tolist()


def river_meta(R, gb, Hb):
    fit = river_fit(R) or {}
    return dict(name="Laurel River", catchment_km2=round(LF.RIVER_INFLOW["area"] / 1e6), inflow=LF.LANDMARKS["river_inflow"],
                confluence=LF.LANDMARKS["confluence"], cascade=LF.LANDMARKS["narrows_cascade"],
                bridge=fit.get("bridge"), rapids=[list(q) for q in RAPIDS], out=river_out(gb, Hb))


def town_meta(gb, Hb):
    """The town downstream (not built yet: a later level; brief note in blockout.md). What the
    ring shows of it from the river corridor: a water tower, a white steeple, the steel truss bridge
    where the river road crosses into town, a scatter of houses on the flats."""
    T = LF.TOWN
    hb = lambda x, y: float(terrain.sample(Hb, gb, np.array([x]), np.array([y + OY]))[0])
    glimpses = [dict(kind="water_tower", x=-1640.0, y=-905.0, h=24.0),
                dict(kind="steeple", x=-1720.0, y=-690.0, h=21.0),
                dict(kind="truss_bridge", x0=-1585.0, y0=-765.0, x1=-1585.0, y1=-835.0, h=6.0),
                dict(kind="tipple", x=-1540.0, y=-870.0, h=12.0)]
    rr = np.random.default_rng(SEED + 41)
    for _ in range(38):
        x, y = rr.uniform(-2250, -1600), rr.uniform(-1080, -560)
        if abs(y + 795) < 45:
            continue
        glimpses.append(dict(kind="house", x=float(round(x, 1)), y=float(round(y, 1)), w=float(rr.uniform(7, 12)),
                             d=float(rr.uniform(6, 9)), h=float(rr.uniform(4.5, 7)), yaw=float(rr.uniform(-0.3, 0.3)),
                             roof=int(rr.integers(0, 3))))
    for g in glimpses:
        if "x" in g:
            g["z"] = round(hb(g["x"], g["y"]), 2)
        else:
            g["z"] = round(min(hb(g["x0"], g["y0"]), hb(g["x1"], g["y1"])), 2)
    return dict(T, glimpses=glimpses)


def blur_mask(m, sigma):
    return np.clip(terrain.blur(m.astype(float), sigma), 0, 1)


def rounded(o, nd):
    """JSON-bound data with floats rounded (world.json's prop lists were most of its 0.55 MB)."""
    if isinstance(o, float):
        return round(o, nd)
    if isinstance(o, dict):
        return {k: rounded(v, nd) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [rounded(v, nd) for v in o]
    return o


def quantise_instances(x, y, z, size, rot, seed, size_m, hlo, hhi):
    half = size_m / 2
    q = np.zeros((len(x), 6), np.uint16)
    q[:, 0] = np.clip(np.round((x + half) / size_m * 65535), 0, 65535)
    q[:, 1] = np.clip(np.round((-(y + OY) + half) / size_m * 65535), 0, 65535)    # three z
    q[:, 2] = np.clip(np.round((z - hlo) / (hhi - hlo) * 65535), 0, 65535)
    q[:, 3] = np.clip(np.round(size * 10000), 0, 65535)
    q[:, 4] = np.clip(np.round((rot % (2 * math.pi)) / (2 * math.pi) * 65535), 0, 65535)
    q[:, 5] = np.clip(np.round(seed * 65535), 0, 65535)
    return q


def to3(x, y, z):
    return [round(float(x), 2), round(float(z), 2), round(float(-(y + OY)), 2)]


def make_views(R, thick=None, routed=None, props=None):
    """Named eye-height views (three.js coords): the brief's moments + the bench's four names."""
    def eye(x, y, dz=1.65):
        return [float(x), float(R.h(x, y)) + dz, float(-(y + OY))]
    def look_at(p, x, y, z=None):
        return [float(x), float(R.h(x, y) + 1.0 if z is None else z), float(-(y + OY))]
    hx, hy, hz = LF.HOUSE_EYE
    v = {}
    g = LF.GATE
    v["gate"] = dict(pos=eye(g[0], g[1] - 3), look=look_at(None, g[0], g[1] - 120))
    v["meadow_edge"] = dict(pos=eye(-20, -150), look=look_at(None, -50, -230))
    v["poplar_cove"] = dict(pos=eye(-6, -392), look=look_at(None, 30, -380, float(R.h(30, -380)) + 12))
    v["falls"] = dict(pos=eye(*FALLS_VIEW), look=look_at(None, -88, -659, -121.0))
    v["footlog"] = dict(pos=eye(-150, -655), look=look_at(None, -158, -690))
    v["laurel_hell"] = dict(pos=eye(300, -462, 0.95), look=look_at(None, 305, -480))
    if thick is not None and routed is not None:          # crouched in route C's tunnel, looking along it
        P = terrain.spline(routed["route_c"], 1.0)[:, :2]
        for k in range(len(P) // 4, len(P) - 10):
            j, i = R.ij(P[k, 0], P[k, 1])
            j2, i2 = R.ij(P[k + 6, 0], P[k + 6, 1])
            if thick[j, i] == 128 and thick[j2, i2] == 128:
                v["laurel_hell"] = dict(pos=eye(P[k, 0], P[k, 1], 0.95), look=look_at(None, P[k + 8, 0], P[k + 8, 1], float(R.h(*P[k + 8])) + 0.9))
                break
    for nm, (x, y) in LF.LOOKOUTS.items():
        v[nm] = dict(pos=eye(x, y), look=[hx, hz, -(hy + OY)])
    v["gap"] = dict(pos=eye(-300, -1205), look=look_at(None, -300, -1260))
    fa = next((p for p in props or [] if p["kind"] == "falls"), None)
    if fa:                                                 # (the falls view looks at the fitted sheet)
        v["falls"] = dict(pos=eye(*FALLS_VIEW), look=[float(fa["x0"]), float((fa["z0"] + fa["z1"]) / 2), float(-(fa["y0"] + OY))])
    # the Laurel River: on the swinging bridge looking downstream at the cascade into the Narrows;
    # the gorge from the river road; the road at the square's west edge looking down the valley to
    # the town
    sb = next((p for p in props or [] if p["kind"] == "swing_bridge"), None)
    if sb:
        mx, my, mz = (sb["x0"] + sb["x1"]) / 2, (sb["y0"] + sb["y1"]) / 2, (sb["z0"] + sb["z1"]) / 2 - sb["sag"]
        v["bridge"] = dict(pos=[float(mx), float(mz) + 1.65, float(-(my + OY))], look=look_at(None, -585, -770, float(sb["water"]) - 4.0))
    rd = (routed or {}).get("river_road")
    if rd:
        P = terrain.spline([(x, y) for x, y in rd], 1.0)[:, :2]
        k = int(np.argmin(np.hypot(P[:, 0] + 640, P[:, 1] + 1180)))
        v["river_gorge"] = dict(pos=eye(P[k, 0], P[k, 1]), look=look_at(None, -560, -1000, float(R.h(P[k, 0], P[k, 1])) - 2.0))
        e = P[-24]
        v["river_road"] = dict(pos=eye(e[0], e[1], 2.4), look=[-1700.0, -180.0, float(-(-800 + OY))])
    # the cascade from below: the lowest dry spot (1-4 m over the water) 30-60 m north-east of it
    wl = np.where(np.isfinite(R.lake_level) & (R.H < R.lake_level), R.lake_level, R.river_level)
    cx, cy = LF.LANDMARKS["narrows_cascade"]
    best = None
    for rad in (34, 42, 52, 62):
        for a in np.linspace(-0.2, 1.8, 18):                 # (east through north)
            px, py = cx + rad * math.cos(a), cy + rad * math.sin(a)
            j, i = R.ij(px, py)
            if np.isfinite(wl[j, i]) or (thick is not None and thick[j, i]):
                continue
            m = np.hypot(R.X - px, R.Y - py) < 14
            w = wl[m][np.isfinite(wl[m])]
            if not len(w):
                continue
            above = float(R.h(px, py)) - float(w.min())
            if 1.0 < above < 4.5 and (best is None or above < best[0]):
                best = (above, px, py)
    if best:
        v["cascade"] = dict(pos=eye(best[1], best[2], 1.7), look=look_at(None, cx, cy, -166.0))
    # wild_bench's four (open, forest, ridge, spawn)
    v["open"] = v["meadow_edge"]; v["forest"] = v["poplar_cove"]; v["ridge"] = v["painted"]; v["spawn"] = v["gate"]
    return v


def routes(routed, fit=None, props=None):
    """Walker polylines (three.js x, z) for routes A, B, C: gate -> the Gap."""
    def pl(pts, rev=False):
        P = terrain.spline([(x, y) for x, y in pts], 2.0)[:, :2]
        return P[::-1] if rev else P
    rid = pl(routed["ridge_trail"])
    def cut(P, near, after=True):
        k = int(np.argmin(np.hypot(P[:, 0] - near[0], P[:, 1] - near[1])))
        return P[k:] if after else P[:k + 1]
    gate = np.array([[LF.GATE[0], LF.GATE[1] - 4.0]])
    A = np.vstack([gate, pl(routed["creek_trail"])])
    B = np.vstack([gate, rid])
    rc = pl(routed["route_c"])
    sp = pl(routed["painted_spur"], rev=True)              # Painted Rock -> the crest
    C = np.vstack([gate, cut(rid, rc[0], after=False), rc, sp, cut(rid, sp[-1])])
    to = lambda P: [[round(float(x), 2), round(float(-(y + OY)), 2)] for x, y in P]
    out = dict(A=to(A), B=to(B), C=to(C))
    # D, toward the town: the creek trail to the footlog, the river trail to the swinging bridge,
    # across it, down the river road out of the square (west)
    if "river_trail" in routed and "river_road" in routed and fit:
        crk = pl(routed["creek_trail"])
        rt = pl(routed["river_trail"])
        road = pl(routed["river_road"])
        (ax, ay), (bx, by) = fit["bridge"]["a"], fit["bridge"]["b"]
        sb = next((p for p in props or [] if p["kind"] == "swing_bridge"), None)
        if sb:
            (ax, ay), (bx, by) = (sb["x0"], sb["y0"]), (sb["x1"], sb["y1"])
        L = math.hypot(bx - ax, by - ay); ux, uy = (bx - ax) / L, (by - ay) / L
        # (up the steps along the bridge's axis, across, down the far steps)
        span = np.linspace([ax - ux * 6, ay - uy * 6], [bx + ux * 6, by + uy * 6], 40)
        k = int(np.argmin(np.hypot(road[:, 0] - bx, road[:, 1] - by)))
        D = np.vstack([gate, cut(crk, rt[0], after=False), rt, span, road[k:]])
        out["D"] = to(D)
    return out


def estate(R):
    """The estate stand-in (estate frame, z up; the runtime converts): lawn, terrace, house
    massing (two floors, the courtyard open), hedge with the gate gap, pool, cypresses."""
    cyp = [[61.2, 37.0], [61.2, 32.5], [61.2, 28.0], [43.0, 52.5], [-20.3, 54.3], [-15.7, 54.3], [-63.5, 9.6], [-63.5, -9.6],
           [-58.5, 9.6], [-58.5, -9.6], [14.6, -47.0], [24.9, -47.0], [14.6, -51.0], [24.9, -51.0], [14.6, -55.0], [24.9, -55.0],
           [14.6, -59.0], [24.9, -59.0], [-58.6, -58.3], [-51.6, -58.7], [-45.0, -58.1], [63.7, -1.0], [63.7, 8.0], [-46.5, 60.3],
           [-43.6, 59.5], [-27.8, 60.4], [-1.3, 60.4], [1.2, 60.9], [12.5, 60.6], [29.5, 60.2], [32.6, 59.6], [59.8, 59.5],
           [-65.0, 56.5], [-68.3, -7.4], [-68.0, 11.8], [-67.2, 20.2], [-13.0, -59.0], [11.0, -58.9], [40.0, -60.7],
           [68.9, -10.0], [68.9, 11.5]]          # blender/levels/outdoor/*.py PLACEMENTS (plant_tree_cypress)
    return dict(
        lawn=dict(rect=[-90, -80, 90, 80], z=LF.LAWN_Z),
        terrace=dict(rect=[-31, -25, 31, 25], z=0.0),
        house=[dict(rect=[-26, -20, 26, 20], z0=0.0, z1=8.8, hole=[-10, -7, 10, 7]),
               dict(rect=[-26, -10.5, -13.5, 10.5], z0=0.0, z1=8.8, glass="w"),          # great room's glass wall
               dict(rect=[-8, -20, 8, -10.5], z0=0.0, z1=8.8, glass="s")],               # the entry
        glass_bands=[dict(face="s", x=[-26, 26], z=[5.0, 7.9]), dict(face="n", x=[-10, 8], z=[0.4, 3.9]),
                     dict(face="w", y=[-10.5, 10.5], z=[0.3, 8.1]), dict(face="s", x=[-8, 8], z=[0.3, 8.1])],
        hedge=dict(rect=[-70, -62, 70, 62], thick=1.4, height=2.8, gap=[14.0, 25.5]),
        gate=dict(x=[14.0, 25.5], y=-62.0, pier=1.0, height=3.2),
        pool=dict(rect=[-4.5, 37.5, 20.5, 43.5], z=-0.1),
        pool_house=dict(rect=[38, 34, 52, 46], z1=4.2),
        cypress=cyp, cypress_height=11.0, cypress_r=0.9)


def run(name=LF.NAME):
    t0 = time.time()
    R = Run(name)
    out_dir = os.path.join(R.dir, "world")
    os.makedirs(out_dir, exist_ok=True)
    r = rng(SEED)
    st = R.stats
    routed = {k: [(x, y - OY) for x, y in v] for k, v in st["routed_paths"].items()}
    pmeta = {p["name"]: p for p in LF.PATHS}
    # distances to the walked trails (estate road included) and to route C's lane
    trails_d = np.full(R.H.shape, np.inf)
    road_d = np.full(R.H.shape, np.inf)
    for nm, pts in routed.items():
        P = terrain.spline([LF.local(q) for q in pts], 1.5)
        d, _, _, _ = terrain.poly_field(R.grid, P, 60.0)
        if nm == "route_c":
            route_c_d, _, route_c_s, _ = terrain.poly_field(R.grid, P, 60.0)
        elif pmeta[nm].get("road"):
            # (estate_link: a wide road (the county road) keeps its trees, rocks and thickets off
            # its whole width plus 2 m: road_d < 4 means within half its width + 2 m)
            road_d = np.minimum(road_d, d - max(0.0, pmeta[nm]["width"] / 2 + 2.0 - 4.0))
            trails_d = np.minimum(trails_d, d - 1.0)
        else:
            trails_d = np.minimum(trails_d, d)
    # the swinging bridge's line counts as trail (no thicket, trunk or rock on it or its approaches)
    fit = river_fit(R)
    if fit:
        (ax, ay), (bx, by) = fit["bridge"]["a"], fit["bridge"]["b"]
        L = math.hypot(bx - ax, by - ay); ux, uy = (bx - ax) / L, (by - ay) / L
        seg = np.array([[ax - ux * 16, ay - uy * 16 + OY], [bx + ux * 16, by + uy * 16 + OY]])
        d, _, _, _ = terrain.poly_field(R.grid, terrain.spline(seg.tolist(), 1.0), 20.0)
        trails_d = np.minimum(trails_d, np.where(np.isfinite(d), d, 1e9))
    C, dw, slope = communities(R, trails_d, route_c_d, route_c_s)
    t1 = time.time()
    # exclusions: water + banks, rock, the estate, pads, the Gap, lookouts
    excl = (C == CID["water"]) | (C == CID["rock"]) | (C == CID["estate"]) | (C == CID["meadow"]) | (dw < 1.5)
    excl |= (C == CID["clearing"]) | (road_d < 4.0)
    excl |= np.hypot(R.X - FALLS_VIEW[0], R.Y - FALLS_VIEW[1]) < 9           # the pool's gravel beach (the falls view)
    # tunnels through the laurel hell: route C's lane + a few dead-end side tunnels
    tunnel = np.isfinite(route_c_d) & (route_c_d < 1.6)         # (>= 2 cells: diagonal stretches don't pinch)
    side_pts = []
    rc = terrain.spline([LF.local(q) for q in routed["route_c"]], 2.0)
    for k in range(6):
        p = rc[int(r.integers(20, len(rc) - 20))][:2].copy()
        a = r.uniform(0, 2 * math.pi)
        pts = [p.copy()]
        for _ in range(int(r.integers(14, 30))):
            a += r.normal(0, 0.45)
            p = p + 2.0 * np.array([math.cos(a), math.sin(a)])
            pts.append(p.copy())
        side_pts.append(np.array(pts))
        d, _, _, _ = terrain.poly_field(R.grid, np.array(pts), 3.0)
        tunnel |= np.isfinite(d) & (d < 1.2)
    hell0 = C == CID["hell"]
    lane = terrain.spline([q for q in routed["route_c"]], 2.0)[:, :2]
    tunnels = [lane] + [np.column_stack([q[:, 0], q[:, 1] - OY]) for q in side_pts]
    tunnel_d = np.minimum(np.where(np.isfinite(route_c_d), route_c_d, 99), 99)
    for sp_ in side_pts:
        d, _, _, _ = terrain.poly_field(R.grid, sp_, 6.0)
        tunnel_d = np.minimum(tunnel_d, np.where(np.isfinite(d), d, 99))
    on_c = np.isfinite(route_c_d) & (route_c_d < 2.6)              # route C's lane: no trunk, log or boulder on it
    bars = R.mask("bars") > 0.5                                   # the Laurel River's cobble bars stay open
    excl |= bars
    trees = scatter_trees(R, C, dw, trails_d, excl | (dw < 6.5) | on_c, r)
    cut = vista_clear(R, trees)
    cut |= town_vista(trees["x"], trees["y"], routed)
    trees = {k: v[~cut] for k, v in trees.items()}
    trees["rot"] = r.uniform(0, 2 * math.pi, len(trees["x"]))
    hell = (C == CID["hell"]) & (trails_d > 2.0) & ~excl
    thick = np.zeros(R.H.shape, np.uint8)
    thick[hell] = 255
    thick[hell & tunnel] = 128
    shrubs = scatter_shrubs(R, C, dw, trails_d, excl, tunnel_d, tunnels, thick, r)
    ground = scatter_ground(R, C, dw, trails_d, excl | (C == CID["hell"]), r)
    t2 = time.time()
    logs = place_logs(R, C, trails_d, excl | on_c, r)
    boulders = place_boulders(R, C, trails_d, excl | on_c, r)
    boulders += river_rocks(R, C, trails_d, r)
    z_b = np.load(os.path.join(R.dir, "terrain.npz"))
    bst0 = st["backdrop"]
    gb0 = terrain.Grid(-bst0["extent"] / 2, -bst0["extent"] / 2, bst0["cell"], bst0["samples"][0], bst0["samples"][1])
    Hb0 = north_valley(z_b["Hb"].astype(np.float64), gb0, terrain.Noise(SEED + 19))
    props = authored_props(R, routed, r) + river_props(R, routed, gb0, Hb0)
    # canopy + light
    top, base = canopy_volume(R, trees, shrubs)
    L = light_bake(R, top, base, st["look"])
    t3 = time.time()
    # sight checks again, over the trees actually placed (the canopy raster) + thickets
    can = np.where(top > -1e8, np.maximum(top - R.H, 0), 0)
    view_chk = {}
    for nm, p in LF.LOOKOUTS.items():
        view_chk[nm] = los(R, can, p, LF.HOUSE_EYE, skip=4.0)
        view_chk[nm]["terrain_only"] = los(R, None, p, LF.HOUSE_EYE)["clear"]
    hidden = {}
    for nm, p in LF.LOOKOUTS.items():
        hidden[nm] = {k: los(R, can, p, (q[0], q[1], float(R.h(*q)) + 1.5), skip=4.0)["clear"]
                      for k, q in dict(footlog=LF.LANDMARKS["footlog"], pool=LF.LANDMARKS["plunge_pool"],
                                       meadow=(20, -120), gap=LF.LANDMARKS["gap"]).items()}
    # splat (texel grid)
    noise = terrain.Noise(SEED + 19)
    nz = noise.fbm(R.X, R.Y, 7.0, 3)
    wet = R.mask("wetness")
    asp = R.mask("aspect") * 360
    grass = np.isin(C, [CID["meadow"], CID["estate"], CID["clearing"]]).astype(float)
    # (estate_link: no hay inside the hedge: the house's own grounds are drawn there, viewer/wild/estate.js)
    grass = np.where((np.abs(R.X) < 70.0) & (R.Y > -61.6), 0.0, grass)
    grass = np.maximum(grass, 0.55 * (C == CID["bald"]))
    northwet = np.clip((wet - 0.35) * 2, 0, 1) * (np.cos(np.radians(asp)) > 0.1)
    grass = np.maximum(grass, 0.14 * northwet * np.isin(C, [CID["cove"], CID["ripar"]]) * (nz > -0.1))  # moss
    rock = np.clip((slope - 44) / 10, 0, 1)
    rock = np.maximum(rock, np.clip(R.mask("cliff") * 1.5, 0, 1))
    for nm, p in LF.LOOKOUTS.items():
        rock = np.maximum(rock, np.clip(1.4 - np.hypot(R.X - p[0], R.Y - p[1]) / 10, 0, 1))
    path = np.clip(1.3 - trails_d / 1.2 - 0.4 * nz, 0, 1)                    # trail dirt, worn edges
    path = np.maximum(path, np.clip(3.0 - road_d / 1.6, 0, 1))
    bed = (R.mask("rivers") > 0.3) | (R.mask("lakes") > 0.3)
    path = np.maximum(path, bed.astype(float) * 0.9)
    path = np.maximum(path, 0.85 * blur_mask(R.mask("bars"), 1.0))                # cobble bars, the floodplain's gravel
    path = np.maximum(path, 0.5 * np.clip(R.mask("sediment") - 0.4, 0, 1) * (slope > 28))   # talus
    path = np.clip(path, 0, 1)
    rock *= 1 - path
    grass *= (1 - path) * (1 - rock)
    floor = np.clip(1 - grass - rock - path, 0, 1)
    var = 0.5 + 0.45 * noise.fbm(R.X - 33, R.Y + 71, 40.0, 3)
    splat = np.dstack([u8(texels(grass)), u8(texels(floor)), u8(texels(rock)), u8(texels(var))])
    light = np.dstack([u8(texels(L["r"])), u8(texels(L["g"])), u8(texels(L["b"])), u8(texels(L["a"]))])
    files = {}
    files["splat.png"] = terrain.write_png(os.path.join(out_dir, "splat.png"), splat)
    files["light.png"] = terrain.write_png(os.path.join(out_dir, "light.png"), light)
    files["thicket.png"] = terrain.write_png(os.path.join(out_dir, "thicket.png"), thick)
    shutil.copyfile(os.path.join(R.dir, "height16.png"), os.path.join(out_dir, "height16.png"))
    files["height16.png"] = os.path.getsize(os.path.join(out_dir, "height16.png"))
    # water surface
    wl = np.where(np.isfinite(R.lake_level) & (R.H < R.lake_level), R.lake_level, R.river_level).astype(np.float64)
    wm = np.isfinite(wl)
    wlo, whi = float(np.nanmin(wl)) - 1, float(np.nanmax(wl)) + 1
    wq = np.where(wm, np.round((np.where(wm, wl, wlo) - wlo) / (whi - wlo) * 65534) + 1, 0).astype(np.uint16)
    files["water16.png"] = terrain.write_png(os.path.join(out_dir, "water16.png"), wq)
    # backdrop: heights + a baked colour (forested hills, a few cleared valley floors, rock)
    z = np.load(os.path.join(R.dir, "terrain.npz"))
    Hb = z["Hb"].astype(np.float64)
    bst = st["backdrop"]
    gb = terrain.Grid(-bst["extent"] / 2, -bst["extent"] / 2, bst["cell"], bst["samples"][0], bst["samples"][1])
    Hb = north_valley(Hb, gb, noise)
    rgb_b, vis_b, sky_b = terrain.light(Hb, gb.cell, st["look"])
    nb, _, _ = terrain.normals(Hb, gb.cell)
    sl_b = np.degrees(np.arccos(nb[..., 2]))
    Xb, Yb = gb.xy()
    nzb = noise.fbm(Xb, Yb, 260.0, 4)
    forest_c = np.array([0.030, 0.052, 0.020]) * (0.85 + 0.3 * noise.fbm(Xb + 9, Yb, 90.0, 3))[..., None]
    field = ((sl_b < 7) & (nzb > 0.35) & (Hb < 40)).astype(float)[..., None]     # a few pastures on valley floors
    alb = forest_c * (1 - field) + np.array([0.06, 0.09, 0.03]) * field
    rk = np.clip((sl_b - 46) / 10, 0, 1)[..., None]
    alb = alb * (1 - rk) + np.array([0.18, 0.18, 0.16]) * rk
    lb = (np.asarray(st["look"]["sun_color"]) * st["look"]["sun_strength"] / math.pi * (np.clip((nb * (-np.asarray(st["look"]["sun_dir"]) / np.linalg.norm(st["look"]["sun_dir"]))).sum(axis=2), 0, 1) * vis_b)[..., None]
          + np.asarray(st["look"]["sky"]) * st["look"]["sky_strength"] * sky_b[..., None])
    bake = np.clip(alb * lb / st["light_scale"], 0, 1)
    srgb = lambda c: np.where(c <= 0.0031308, c * 12.92, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - 0.055)
    blo, bhi = float(Hb.min()), float(Hb.max())
    files["backdrop16.png"] = terrain.write_png(os.path.join(out_dir, "backdrop16.png"),
                                                np.round((Hb - blo) / (bhi - blo) * 65535).astype(np.uint16))
    files["backdrop.png"] = terrain.write_png(os.path.join(out_dir, "backdrop.png"), u8(srgb(bake)))
    # instances
    hlo, hhi = st["collider"]["height_min"], st["collider"]["height_max"]
    counts = {}
    allp = {k: np.concatenate([trees[k], shrubs[k], ground[k]]) for k in ("x", "y", "sp", "size", "rot")}
    for sp_name in SPECIES:
        m = allp["sp"] == sp_name
        n = int(m.sum())
        x, y, s, rot = allp["x"][m], allp["y"][m], allp["size"][m], allp["rot"][m]
        zz = R.h(x, y) - (0.15 if SPECIES[sp_name]["tier"] == "tree" else 0.05)
        if SPECIES[sp_name].get("tile"):                      # tiles on a slope: sink by the fall over their half-width
            sl = np.tan(np.radians(np.clip(sample_grid(R, slope, x, y), 0, 50)))
            zz = zz - 0.35 * sl * SPECIES[sp_name]["width"] * 0.5
        q = quantise_instances(x, y, zz, s, rot, r.random(n), 1536.0, hlo, hhi)
        if SPECIES[sp_name]["tier"] == "under":
            # ground cover ("xz4"): x, z, size (x100) << 8 | rot (/256 turn), seed; y = the
            # heightfield at load (-0.05): a third smaller (most instances are ferns)
            q = np.stack([q[:, 0], q[:, 1], (np.clip(np.round(s * 100), 0, 255).astype(np.uint16) << 8)
                          | np.clip(np.round((rot % (2 * math.pi)) / (2 * math.pi) * 256) % 256, 0, 255).astype(np.uint16),
                          q[:, 5]], axis=1)
        fn = f"inst_{sp_name}.bin"
        with open(os.path.join(out_dir, fn), "wb") as fh:
            fh.write(q.astype("<u2").tobytes())
        files[fn] = int(q.size * 2)
        counts[sp_name] = n
    # the ring's forest (outside the square: its own bounds in the species table, three.js frame)
    ring = ring_forest(gb, Hb, r, routed)
    ring_species = {}
    if len(ring["x"]):
        bx0, bx1 = float(ring["x"].min()) - 1, float(ring["x"].max()) + 1
        bz0, bz1 = float(-(ring["y"].max() + OY)) - 1, float(-(ring["y"].min() + OY)) + 1
        rlo, rhi = float(ring["z"].min()) - 1, float(ring["z"].max()) + 1
        for sp_name in sorted(set(ring["sp"])):
            m = ring["sp"] == sp_name
            n = int(m.sum())
            X3, Z3 = ring["x"][m], -(ring["y"][m] + OY)
            q = np.zeros((n, 6), np.uint16)
            q[:, 0] = np.clip(np.round((X3 - bx0) / (bx1 - bx0) * 65535), 0, 65535)
            q[:, 1] = np.clip(np.round((Z3 - bz0) / (bz1 - bz0) * 65535), 0, 65535)
            q[:, 2] = np.clip(np.round((ring["z"][m] - rlo) / (rhi - rlo) * 65535), 0, 65535)
            q[:, 3] = np.clip(np.round(ring["size"][m] * 10000), 0, 65535)
            q[:, 4] = np.clip(np.round(ring["rot"][m] / (2 * math.pi) * 65535), 0, 65535)
            q[:, 5] = np.clip(np.round(r.random(n) * 65535), 0, 65535)
            fn = f"inst_ring_{sp_name}.bin"
            with open(os.path.join(out_dir, fn), "wb") as fh:
                fh.write(q.astype("<u2").tobytes())
            files[fn] = n * 12
            ring_species[f"ring_{sp_name}"] = dict(SPECIES[sp_name], count=n, file=fn, tint_rgb=srgb_hex(SPECIES[sp_name]["tint"]),
                                                   veg_ids=[sp_name], bounds=dict(x=[bx0, bx1], z=[bz0, bz1], h=[rlo, rhi]), ring=True)
    cols = colliders(R, trees, logs, boulders, props)
    with open(os.path.join(out_dir, "colliders.bin"), "wb") as fh:
        fh.write(cols.astype("<f4").tobytes())
    # the shipped form: uint16 per coordinate over the boxes' own range, mins rounded down and
    # maxes up (a box only ever grows, by < 2.4 cm in x / z)
    c_lo = cols.reshape(-1, 2, 3).min(axis=(0, 1)) - 0.01
    c_hi = cols.reshape(-1, 2, 3).max(axis=(0, 1)) + 0.01
    sc = 65535.0 / (c_hi - c_lo)
    cq = np.concatenate([np.floor((cols[:, :3] - c_lo) * sc), np.ceil((cols[:, 3:] - c_lo) * sc)], axis=1)
    with open(os.path.join(out_dir, "colliders16.bin"), "wb") as fh:
        fh.write(np.clip(cq, 0, 65535).astype("<u2").tobytes())
    files["colliders16.bin"] = int(cq.size * 2)
    colliders_q = dict(file="colliders16.bin", lo=[round(float(v), 4) for v in c_lo], hi=[round(float(v), 4) for v in c_hi])
    # the light map ships as WebP (lossy colour, lossless alpha = the terrain shadow): it is GPU-only
    try:
        subprocess.run(["cwebp", "-quiet", "-q", "88", "-alpha_q", "100", "-exact", "-m", "6",
                        os.path.join(out_dir, "light.png"), "-o", os.path.join(out_dir, "light.webp")], check=True)
        files["light.webp"] = os.path.getsize(os.path.join(out_dir, "light.webp"))
    except Exception as e:                                # (no cwebp: the runtime reads light.png)
        print("  light.webp not written:", e)
    # stats: community shares in the play area, canopy light in the cove, etc.
    play = (R.X > -700) & (R.X < 600) & (R.Y < -62) & (R.Y > -1300)
    share = {n: round(float((C[play] == CID[n]).mean() * 100), 1) for n in NAMES}
    area_ha = play.sum() * R.cell ** 2 / 1e4
    forest_ha = float(np.isin(C[play], [CID[k] for k in ("cove", "ripar", "hell", "oak", "crest", "slick")]).sum() * R.cell ** 2 / 1e4)
    lt = dict(cove_canopy_mean=round(float(L["g"][(C == CID["cove"]) & play].mean()), 3),
              cove_floor_light=round(float((L["r"] * L["g"] * 0.85 + L["b"] * 0.15)[(C == CID["cove"]) & play].mean()
                                           / max((L["r"] * 0.85 + 0.15)[(C == CID["meadow"])].mean(), 1e-3)), 3),
              creek_canopy_mean=round(float(L["g"][bed].mean()), 3), meadow_canopy_mean=round(float(L["g"][C == CID["meadow"]].mean()), 3))
    meta = dict(
        name=name, title="Laurel Fork Cove", frame="three.js, terrain local: x = estate x, z = -(estate y + %.0f)" % OY,
        estate_offset=[0.0, -OY], size=1536.0, res=R.n, spacing=R.cell, mapRes=R.n - 1,
        height=dict(min=hlo, max=hhi), water=dict(min=wlo, max=whi),
        backdrop=dict(extent=bst["extent"], cell=bst["cell"], samples=bst["samples"], inner=bst["inner"], min=blo, max=bhi),
        look=st["look"], light_scale=st["light_scale"],
        haze=dict(visual_range_m=32000.0, extinction=3.912 / 32000.0, away="#8FA6C4", sun="#E6C49A"),
        species={k: dict(v, count=counts[k], file=f"inst_{k}.bin", tint_rgb=srgb_hex(v["tint"]),
                         veg_ids=[k], **({"fmt": "xz4"} if v["tier"] == "under" else {}))
                 for k, v in SPECIES.items()} | ring_species,
        bloom={k: srgb_hex(v) for k, v in BLOOM.items()},
        communities=dict(names=NAMES, share_pct=share, sight_lambda=SIGHT_LAMBDA),
        views=make_views(R, thick, routed, props), routes=routes(routed, river_fit(R), props),
        props=rounded(dict(logs=logs, boulders=boulders, authored=props), 3),
        estate=estate(R), colliders=int(len(cols)), colliders_q=colliders_q, lawn_z=LF.LAWN_Z,
        river=river_meta(R, gb, Hb), town=town_meta(gb, Hb),
        light_file="light.webp" if os.path.exists(os.path.join(out_dir, "light.webp")) else "light.png",
        spawn=make_views(R)["gate"],
        checks=dict(views=view_chk, hidden_from_lookouts=hidden, vista_cut=int(cut.sum()), light=lt),
        stats=dict(trees=int(len(trees["x"])), shrubs=int(len(shrubs["x"])), ground=int(len(ground["x"])),
                   logs=len(logs), boulders=len(boulders), play_area_ha=round(float(area_ha), 1), forest_ha=round(forest_ha, 1),
                   stems_per_forest_ha=round(len(trees["x"]) / max(forest_ha, 1), 0),
                   thicket_m2=round(float((thick == 255).sum() * R.cell ** 2)), tunnel_m2=round(float((thick == 128).sum() * R.cell ** 2)),
                   files_bytes=files, timings_s=dict(communities=round(t1 - t0, 1), scatter=round(t2 - t1, 1),
                                                    light=round(t3 - t2, 1), total=round(time.time() - t0, 1))),
    )
    with open(os.path.join(out_dir, "world.json"), "w") as fh:
        json.dump(meta, fh, separators=(",", ":"))
    # a plan of the communities + routes for the docs
    pal = dict(meadow=(0.85, 0.81, 0.54), cove=(0.33, 0.56, 0.26), ripar=(0.20, 0.38, 0.31), hell=(0.13, 0.27, 0.20),
               oak=(0.55, 0.60, 0.32), crest=(0.62, 0.57, 0.38), slick=(0.55, 0.50, 0.40), bald=(0.74, 0.57, 0.70),
               rock=(0.74, 0.72, 0.68), water=(0.24, 0.50, 0.78), estate=(0.45, 0.70, 0.30), clearing=(0.8, 0.8, 0.6))
    img = np.zeros(R.H.shape + (3,))
    for n_ in NAMES:
        img[C == CID[n_]] = pal[n_]
    nrm, _, _ = terrain.normals(R.H, R.cell)
    Lv = np.array([-0.55, 0.55, 0.63]); Lv /= np.linalg.norm(Lv)
    img *= (0.55 + 0.6 * np.clip((nrm * Lv).sum(axis=2), 0, 1))[..., None]
    img[(thick == 128)] = (0.9, 0.4, 0.9)
    img[trails_d < 1.5] = (0.85, 0.25, 0.15)
    img[np.isfinite(route_c_d) & (route_c_d < 1.0) & (thick != 128)] = (0.6, 0.2, 0.7)
    terrain.write_png(os.path.join(out_dir, "communities.png"), u8(img[::2, ::2]))
    print(f"world {name}: {meta['stats']['trees']} trees ({meta['stats']['stems_per_forest_ha']}/ha of forest), "
          f"{meta['stats']['shrubs']} shrubs, {meta['stats']['ground']} ferns/tufts, {len(logs)} logs, {len(boulders)} boulders, "
          f"{len(cols)} colliders, vista cut {int(cut.sum())}")
    print("  shares %", share)
    print("  species", counts)
    print("  light", lt)
    print("  views over the placed trees:", {k: (v["clear"], v["at"]) for k, v in view_chk.items()})
    print("  hidden from lookouts (clear < 0 = hidden):", hidden)
    print("  timings", meta["stats"]["timings_s"], "files", {k: v for k, v in files.items()})
    return meta


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else LF.NAME)
