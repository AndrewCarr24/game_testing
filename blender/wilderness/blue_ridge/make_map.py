"""Blue Ridge concept map: vegetation-community raster from the test terrain's masks, contours,
routes/landmarks from br_features (same numbers as the brief), N-S section with line of sight."""
import base64, math, os, subprocess, sys
import numpy as np
SP = sys.argv[1]; RUN = sys.argv[2]; OUT = sys.argv[3]
sys.path.insert(0, "/Users/andrewcarr/Documents/projects/game_testing/blender/wilderness"); sys.path.insert(0, SP)
import terrain, br_features as F

TD = f"{SP}/terrain_out/{RUN}"
d = np.load(TD + "/terrain.npz")
H = d["H"].astype(float)
N = H.shape[0]; CELL = 1536.0 / (N - 1)
OY = F.OFFSET_Y

def mask(name):
    a = terrain.read_png_fast(f"{TD}/masks/{name}.png").astype(float) / 255.0
    return a[::-1]                                  # row 0 = south, like H

slope = mask("slope") * 90; wet = mask("wetness"); curv = mask("curvature"); asp = mask("aspect") * 360
riv = mask("rivers") > 0.5; lake = mask("lakes") > 0.5
water = riv | lake
X = -768 + np.arange(N) * CELL; Y = -768 + np.arange(N) * CELL - OY      # estate frame
XX, YY = np.meshgrid(X, Y)
_, _, dwc = terrain.nearest_seed(water); dw = dwc * CELL
RL = d["river_level"]
_j = int(round((-672 + OY + 768) / CELL)); _i = int(round((-155.5 + 768) / CELL))
_win = RL[_j - 8:_j + 9, _i - 8:_i + 9]
FOOTLOG_Z = float(np.nanmean(_win)) + 2.5
alt = H

# ------------------------------------------------------------------ vegetation communities
def in_poly(px, py, poly):
    inside = np.zeros(px.shape, bool); n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        c = ((y1 > py) != (y2 > py)) & (px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-12) + x1)
        inside ^= c
    return inside

MEADOW = [(-190, -42), (230, -42), (240, -95), (205, -150), (120, -172), (20, -178), (-80, -170), (-160, -140), (-200, -95)]
BALD_C, BALD_R = (466, -1068), 140.0
northish = (np.cos(np.radians(asp)) > 0.2) | ((asp > 0) & (asp < 110))         # N, NE, E faces
southish = (asp > 140) & (asp < 290)
cove = ((curv < 0.47) | (wet > 0.55)) & ~southish | ((curv < 0.44) & (wet > 0.45))
ripar = dw < 28
hell = (slope > 22) & (slope < 46) & (wet > 0.33) & northish & (dw < 220)
ridge = (curv > 0.56) & (alt > 120)
_lh = next(p for p in F.PATHS if p["name"] == "laurel_hell")
_d, _, _, _ = terrain.poly_field(terrain.Grid(-768, -768, CELL, N, N), terrain.spline([F.local(q) for q in _lh["points"]], 3.0), 60.0)
hell = hell | (np.isfinite(_d) & (_d < 45) & (slope > 12) & (alt < 170))   # the authored thicket band of route C
oak = southish | (curv > 0.54)
rock = slope > 48
_th = np.arctan2(YY - BALD_C[1], XX - BALD_C[0])
bald = np.hypot(XX - BALD_C[0], YY - BALD_C[1]) < BALD_R * (0.8 + 0.22 * np.sin(3 * _th) + 0.12 * np.sin(5 * _th + 1.0))
meadow = in_poly(XX, YY, MEADOW)
# the laurel-hell route corridor shows as a tunnel (darker line drawn later); lanes stay thicket

PAL = dict(meadow=(0.85, 0.81, 0.54), cove=(0.33, 0.56, 0.26), ripar=(0.20, 0.38, 0.31), hell=(0.13, 0.27, 0.20),
           oak=(0.55, 0.60, 0.32), ridge=(0.62, 0.57, 0.38), bald=(0.74, 0.57, 0.70), rock=(0.74, 0.72, 0.68),
           water=(0.24, 0.50, 0.78))
col = np.ones(H.shape + (3,)) * np.array(PAL["oak"])
mesic = northish & (alt < 160) & ~ridge
col[(cove & ~oak) | mesic] = PAL["cove"]; col[cove & oak & (wet > 0.5)] = PAL["cove"]
col[ridge] = PAL["ridge"]; col[ripar] = PAL["ripar"]; col[hell] = PAL["hell"]
col[rock] = PAL["rock"]; col[bald] = PAL["bald"]; col[meadow] = PAL["meadow"]; col[water] = PAL["water"]
share = {k: float(v.mean()) for k, v in dict(cove=((cove & ~oak) | mesic) & ~ripar & ~hell, ripar=ripar & ~water, hell=hell & ~ripar,
                                              oak=~(cove & ~oak) & ~mesic & ~ripar & ~hell & ~ridge & ~rock, ridge=ridge & ~rock, rock=rock).items()}
gy, gx = np.gradient(H, CELL)
Lv = np.array([-0.55, 0.55, 0.63]); Lv /= np.linalg.norm(Lv)
nrm = np.dstack([-gx, -gy, np.ones_like(H)]); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
shade = np.clip(np.einsum("ijk,k->ij", nrm, Lv), 0, 1)
col = col * (0.55 + 0.6 * shade[..., None])
step = 2                                            # 3 m per pixel at 1.5 m cells
img = (np.clip(col[::step, ::step], 0, 1) * 255).astype(np.uint8)
png = f"{SP}/veg_raster.png"; jpg = f"{SP}/veg_raster.jpg"
terrain.write_png(png, img)                         # flips: north at top
subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "82", png, "--out", jpg], check=True, capture_output=True)
b64 = base64.b64encode(open(jpg, "rb").read()).decode()

# ------------------------------------------------------------------ contours (6 m grid)
cs = 4
Hc = H[::cs, ::cs]; Xc = X[::cs]; Yc = Y[::cs]
def contours(Z, level):
    ny, nx = Z.shape
    above = Z > level
    a, b, c, dd = above[:-1, :-1], above[:-1, 1:], above[1:, 1:], above[1:, :-1]
    case = a * 1 + b * 2 + c * 4 + dd * 8
    js, is_ = np.nonzero((case > 0) & (case < 15))
    def pt(e):
        kind, j, i = e
        if kind == "h":
            z0, z1 = Z[j, i], Z[j, i + 1]; t = (level - z0) / (z1 - z0); return (Xc[i] + t * (Xc[i + 1] - Xc[i]), Yc[j])
        z0, z1 = Z[j, i], Z[j + 1, i]; t = (level - z0) / (z1 - z0); return (Xc[i], Yc[j] + t * (Yc[j + 1] - Yc[j]))
    TAB = {1: [("B", "L")], 2: [("B", "R")], 3: [("L", "R")], 4: [("R", "T")], 5: [("B", "R"), ("L", "T")], 6: [("B", "T")],
           7: [("L", "T")], 8: [("L", "T")], 9: [("B", "T")], 10: [("B", "L"), ("R", "T")], 11: [("R", "T")], 12: [("L", "R")],
           13: [("B", "R")], 14: [("B", "L")]}
    adj = {}; segs = []
    for j, i in zip(js, is_):
        E = dict(B=("h", j, i), T=("h", j + 1, i), L=("v", j, i), R=("v", j, i + 1))
        for e0, e1 in TAB[int(case[j, i])]:
            k = len(segs); segs.append((E[e0], E[e1]))
            adj.setdefault(E[e0], []).append(k); adj.setdefault(E[e1], []).append(k)
    used = [False] * len(segs); lines = []
    for k0 in range(len(segs)):
        if used[k0]:
            continue
        used[k0] = True; chain = [segs[k0][0], segs[k0][1]]
        for direction in (1, 0):
            while True:
                end = chain[-1] if direction else chain[0]
                nxt = [k for k in adj.get(end, []) if not used[k]]
                if not nxt:
                    break
                k = nxt[0]; used[k] = True
                e = segs[k][1] if segs[k][0] == end else segs[k][0]
                if direction: chain.append(e)
                else: chain.insert(0, e)
        lines.append([pt(e) for e in chain])
    return lines

def dp(points, tol):
    if len(points) < 3:
        return points
    P = np.array(points); a, b = P[0], P[-1]; ab = b - a; L = np.hypot(*ab)
    dist = np.abs(np.cross(ab, P - a)) / L if L > 1e-9 else np.hypot(*(P - a).T)
    i = int(np.argmax(dist))
    if dist[i] > tol:
        return dp(points[:i + 1], tol)[:-1] + dp(points[i:], tol)
    return [points[0], points[-1]]

# ------------------------------------------------------------------ SVG frame
K = 0.66                                            # px per metre
XMIN, XMAX, YMIN, YMAX = -770.0, 770.0, -1580.0, 95.0
PX, PY = 40, 96
W = 1640
def sx(x): return PX + (x - XMIN) * K
def sy(y): return PY + (YMAX - y) * K
PH = (YMAX - YMIN) * K
out = []
A = out.append
A(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="1560" viewBox="0 0 {W} 1560" font-family="Helvetica, Arial, sans-serif">')
A('<defs><clipPath id="plan"><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"/></clipPath>' % (PX, PY, (XMAX - XMIN) * K, PH))
A('<marker id="arr" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#8b1a1a"/></marker>')
A('<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="#0d2318" stroke-width="2"/></pattern></defs>')
A(f'<rect width="{W}" height="1560" fill="#f3efe6"/>')
A('<text x="40" y="38" font-size="25" font-weight="bold" fill="#1d2a1d">Laurel Fork Cove  (slug: blue_ridge)</text>')
A('<text x="40" y="60" font-size="13" fill="#444">Plan, north up, 1 px = 1.52 m. Estate frame: x east, y north, z = estate lawn (0). Terrain = blender/wilderness/terrain.py (+ proposed knicks hook) test run at 1.5 m '
  '(terrain local = estate + (0, 810)).</text>')
A('<text x="40" y="78" font-size="13" fill="#444">Colours = vegetation communities placed by the masks (rules in brief.md). Contours every 20 m, bold every 100 m. Mid-June, golden hour.</text>')
A('<g clip-path="url(#plan)">')
A(f'<rect x="{PX}" y="{PY}" width="{(XMAX-XMIN)*K:.1f}" height="{PH:.1f}" fill="#cfd8b8"/>')
x0, y0 = sx(-768), sy(-768 - OY + 1536)
A(f'<image x="{x0:.1f}" y="{y0:.1f}" width="{1536*K:.1f}" height="{1536*K:.1f}" preserveAspectRatio="none" xlink:href="data:image/jpeg;base64,{b64}"/>')
# contours
for lev in range(-160, 261, 20):
    bold = lev % 100 == 0
    for ln in contours(Hc, lev):
        pts = dp([(sx(x), sy(y)) for x, y in ln], 1.2)
        if len(pts) < 2:
            continue
        dstr = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        A(f'<path d="{dstr}" fill="none" stroke="#2a2a20" stroke-opacity="{0.55 if bold else 0.22}" stroke-width="{1.3 if bold else 0.6}"/>')
# estate (north of the terrain square)
A(f'<rect x="{sx(-90):.1f}" y="{sy(80):.1f}" width="{180*K:.1f}" height="{160*K:.1f}" fill="#9cc46a" stroke="none"/>')
A(f'<rect x="{sx(-70):.1f}" y="{sy(62):.1f}" width="{140*K:.1f}" height="{124*K:.1f}" fill="none" stroke="#1f4d1f" stroke-width="{1.4*K*2:.1f}"/>')
A(f'<rect x="{sx(14):.1f}" y="{sy(-60.5):.1f}" width="{11.5*K:.1f}" height="{3*K:.1f}" fill="#9cc46a"/>')
A(f'<rect x="{sx(-26):.1f}" y="{sy(20):.1f}" width="{52*K:.1f}" height="{40*K:.1f}" fill="#f4f1ea" stroke="#333" stroke-width="1"/>')
A(f'<rect x="{sx(-4):.1f}" y="{sy(33):.1f}" width="{25*K:.1f}" height="{6*K:.1f}" fill="#5aa8d8"/>')
A(f'<path d="M{sx(19.75):.1f},{sy(-25):.1f} L{sx(19.75):.1f},{sy(-62):.1f}" stroke="#d8cfb8" stroke-width="{7*K:.1f}"/>')
# meadow outline
A('<path d="M' + " L".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in MEADOW) + ' Z" fill="none" stroke="#8a7a30" stroke-width="1" stroke-dasharray="4 3"/>')
# estate road: gate -> east along the bench, down the far side of the spur
ROAD = [(20, -62), (24, -100), (90, -118), (200, -120), (330, -150), (470, -215), (600, -300), (700, -330), (790, -360)]
A('<path d="M' + " L".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in ROAD) + f'" fill="none" stroke="#efe6cc" stroke-width="5"/>')
A('<path d="M' + " L".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in ROAD) + f'" fill="none" stroke="#6f6248" stroke-width="1.2" stroke-dasharray="7 4"/>')
# parkway on the south flank, through the Gap
PKWY = [(-790, -1290), (-560, -1285), (-400, -1262), (-300, -1240), (-180, -1262), (40, -1290), (300, -1250), (560, -1240), (790, -1270)]
A('<path d="M' + " L".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in PKWY) + f'" fill="none" stroke="#555" stroke-width="5"/>')
A('<path d="M' + " L".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in PKWY) + f'" fill="none" stroke="#e9e4d4" stroke-width="1" stroke-dasharray="8 6"/>')
# cliffs
for c in F.CLIFFS:
    pts = terrain.spline(c["points"], 3.0)
    A('<path d="M' + " L".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in pts[:, :2]) + '" fill="none" stroke="#3a3530" stroke-width="3.2"/>')
    # ticks on the low side
    for k in range(2, len(pts) - 2, 4):
        (xa, ya), (xb, yb) = pts[k - 1, :2], pts[k + 1, :2]
        tx, ty = xb - xa, yb - ya; L = math.hypot(tx, ty)
        nx_, ny_ = ty / L, -tx / L                  # right of travel
        sgn = -c["side"]                            # low side
        x1, y1 = pts[k, :2]
        A(f'<line x1="{sx(x1):.1f}" y1="{sy(y1):.1f}" x2="{sx(x1 + sgn*nx_*7):.1f}" y2="{sy(y1 + sgn*ny_*7):.1f}" stroke="#3a3530" stroke-width="1.2"/>')
# routes
RC = dict(creek_trail="#c0392b", ridge_trail="#e67e22", painted_spur="#e67e22", laurel_hell="#7d3c98")
for p in F.PATHS:
    pts = terrain.spline([(q[0], q[1]) for q in p["points"]], 4.0)
    dstr = "M" + " L".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in pts)
    if p["name"] == "laurel_hell":
        A(f'<path d="{dstr}" fill="none" stroke="#f3efe6" stroke-width="4.5" stroke-opacity="0.7"/>')
        A(f'<path d="{dstr}" fill="none" stroke="{RC[p["name"]]}" stroke-width="2.6" stroke-dasharray="3 3"/>')
    else:
        A(f'<path d="{dstr}" fill="none" stroke="#fff" stroke-width="5" stroke-opacity="0.75"/>')
        A(f'<path d="{dstr}" fill="none" stroke="{RC[p["name"]]}" stroke-width="2.6"/>')
# pursuers
for (xa, ya), (xb, yb), lab in [((20, 30), (25, -120), ""), ((760, -380), (560, -560), "wave 2 by road (from ~4 min)"),
                                 ((560, -560), (440, -840), ""), ((560, -560), (490, -1020), "")]:
    A(f'<line x1="{sx(xa):.1f}" y1="{sy(ya):.1f}" x2="{sx(xb):.1f}" y2="{sy(yb):.1f}" stroke="#8b1a1a" stroke-width="2.2" stroke-dasharray="7 4" marker-end="url(#arr)"/>')
    if lab:
        A(f'<text x="{sx(xa)-6:.1f}" y="{sy(ya)-6:.1f}" font-size="12" fill="#8b1a1a" text-anchor="end" font-weight="bold">{lab}</text>')
# views back to the house (checked: terrain + canopy model, see brief)
for (xa, ya), lab in [((384, -880), "0.96 km"), ((384, -1060), "1.13 km"), ((162, -1018), "1.03 km")]:
    A(f'<line x1="{sx(xa):.1f}" y1="{sy(ya):.1f}" x2="{sx(0):.1f}" y2="{sy(0):.1f}" stroke="#1a4f8b" stroke-width="1.3" stroke-dasharray="2 4"/>')
A('</g>')
A(f'<rect x="{PX}" y="{PY}" width="{(XMAX-XMIN)*K:.1f}" height="{PH:.1f}" fill="none" stroke="#333" stroke-width="1"/>')

def hz(x, y):
    return float(terrain.height_at(d["H"], terrain.Grid(-768, -768, CELL, N, N), np.array([x]), np.array([y + OY]))[0])

def label(x, y, text, dx=8, dy=-6, size=13, anchor="start", bold=True, color="#111", z=True, marker="circle"):
    if marker == "circle":
        A(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="4.5" fill="#fff" stroke="#111" stroke-width="1.6"/>')
    elif marker == "tri":
        A(f'<path d="M{sx(x):.1f},{sy(y)-7:.1f} l6,11 l-12,0 z" fill="#fff" stroke="#111" stroke-width="1.5"/>')
    zt = f"  {hz(x, y):+.0f}" if z and -768 <= y + OY <= 768 else ""
    w = "bold" if bold else "normal"
    A(f'<text x="{sx(x)+dx:.1f}" y="{sy(y)+dy:.1f}" font-size="{size}" font-weight="{w}" fill="{color}" text-anchor="{anchor}" '
      f'stroke="#f3efe6" stroke-width="3" paint-order="stroke">{text}{zt}</text>')

A(f'<text x="{sx(-60):.1f}" y="{sy(48):.1f}" font-size="12" fill="#1f4d1f" text-anchor="end" font-weight="bold" stroke="#f3efe6" stroke-width="3" paint-order="stroke">THE ESTATE (hedge 140 x 124 m)</text>')
label(19.75, -62, "GATE  0", dx=10, dy=4, z=False, marker="tri")
A(f'<text x="{sx(-185):.1f}" y="{sy(-120):.1f}" font-size="12" fill="#6b5a10" font-style="italic" stroke="#f3efe6" stroke-width="3" paint-order="stroke">hay meadow (cleared bench), 110-130 m to the forest edge</text>')
A(f'<text x="{sx(520):.1f}" y="{sy(-205):.1f}" font-size="11" fill="#4a3f2a" font-style="italic" stroke="#f3efe6" stroke-width="3" paint-order="stroke">estate road (to the valley, east)</text>')
label(-40, -196, "Gate Rock (the step down)", dx=-8, anchor="end")
label(10, -380, "Poplar Cove (old growth)", dx=10)
label(95, -612, "confluence", dx=10, dy=14, bold=False, size=12)
label(-92, -658, "Laurel Fork Falls (16 m drop, lip -116)", dx=-10, dy=-10, anchor="end", z=False)
label(-155.5, -672, "footlog 16 m", dx=-10, dy=16, anchor="end", z=False)
label(-260, -900, "Hemlock Hollow", dx=-10, anchor="end", bold=False)
label(384, -880, "Raven Rock (lookout)", dx=-10, dy=-8, anchor="end")
label(466, -1068, "The Knob (heath bald)", dx=10, dy=4)
label(384, -1060, "Knob west rock (lookout)", dx=-10, dy=-8, anchor="end")
label(162, -1018, "Painted Rock (lookout)", dx=-10, dy=-10, anchor="end")
label(-300, -1218, "THE GAP (overlook, exit)", dx=10, dy=18)
label(300, -560, "laurel hell (crawl)", dx=10, dy=-4, bold=False, marker="none", z=False, color="#4a1f5e")
label(-640, -735, "the Narrows (edge)", dx=0, dy=-12, bold=False, anchor="middle", marker="none", z=False)
A(f'<text x="{sx(-560):.1f}" y="{sy(-1305):.1f}" font-size="12" fill="#333" font-style="italic" stroke="#f3efe6" stroke-width="3" paint-order="stroke">parkway (south edge)</text>')
A(f'<text x="{sx(-700):.1f}" y="{sy(-450):.1f}" font-size="12" fill="#2b3b1b" font-style="italic" stroke="#f3efe6" stroke-width="3" paint-order="stroke">Laurel Fork creek flows west</text>')
# spot heights
for x, y in [(-460, -712), (-600, -730), (200, -450), (-450, -1180), (300, -1130), (-400, -300), (600, -900)]:
    A(f'<text x="{sx(x):.1f}" y="{sy(y):.1f}" font-size="10" fill="#222" stroke="#f3efe6" stroke-width="2.5" paint-order="stroke">{hz(x, y):+.0f}</text>')
# north arrow + scale bar
nx0, ny0 = sx(700), sy(40)
A(f'<path d="M{nx0:.1f},{ny0-26:.1f} l9,24 l-9,-6 l-9,6 z" fill="#222"/><text x="{nx0:.1f}" y="{ny0+12:.1f}" font-size="13" text-anchor="middle" font-weight="bold">N</text>')
bx, by = sx(-740), sy(-1545)
A(f'<rect x="{bx-6:.1f}" y="{by-18:.1f}" width="{500*K+40:.1f}" height="30" fill="#f3efe6" fill-opacity="0.85"/>')
for k in range(5):
    A(f'<rect x="{bx + k*100*K:.1f}" y="{by:.1f}" width="{100*K:.1f}" height="6" fill="{"#222" if k % 2 == 0 else "#fff"}" stroke="#222" stroke-width="0.8"/>')
A(f'<text x="{bx:.1f}" y="{by-5:.1f}" font-size="11">0</text><text x="{bx+500*K:.1f}" y="{by-5:.1f}" font-size="11" text-anchor="middle">500 m</text>')

# ------------------------------------------------------------------ legend (right column)
LX = PX + (XMAX - XMIN) * K + 30; ly = PY + 10
A(f'<text x="{LX}" y="{ly}" font-size="15" font-weight="bold">Vegetation (mask-placed)</text>'); ly += 10
for key, name in [("meadow", "hay meadow: the estate's cleared bench"), ("cove", "cove forest: tulip poplar, buckeye, sugar maple, hemlock"),
                  ("ripar", "creekside: hemlock, rosebay, doghobble"), ("hell", "laurel hell: rhododendron thicket (blocks)"),
                  ("oak", "oak-hickory: red oak, hickory, white pine"), ("ridge", "ridge: chestnut oak, pine, mountain laurel"),
                  ("bald", "heath bald: Catawba rhododendron, laurel"), ("rock", "rock (cliffs, outcrops, > 48 deg)"), ("water", "creek and plunge pool")]:
    r, g, b = (int(255 * v) for v in PAL[key])
    A(f'<rect x="{LX}" y="{ly+6}" width="22" height="14" fill="rgb({r},{g},{b})" stroke="#444" stroke-width="0.6"/>')
    A(f'<text x="{LX+30}" y="{ly+18}" font-size="12">{name}</text>'); ly += 22
ly += 30
A(f'<text x="{LX}" y="{ly}" font-size="15" font-weight="bold">Routes, gate to the Gap</text>'); ly += 8
for key, name, sub in [("creek_trail", "A  Down the creek", "1.76 km: down 133 m, up 220 m"), ("ridge_trail", "B  Along the ridge", "1.92 km: up 243 m, crest walk west"),
                       ("laurel_hell", "C  Through the laurel hell", "0.81 km off-trail, ends at Painted Rock")]:
    dash = 'stroke-dasharray="3 3"' if key == "laurel_hell" else ""
    A(f'<line x1="{LX}" y1="{ly+14}" x2="{LX+26}" y2="{ly+14}" stroke="{RC[key]}" stroke-width="3" {dash}/>')
    A(f'<text x="{LX+34}" y="{ly+18}" font-size="12.5" font-weight="bold">{name}</text>')
    A(f'<text x="{LX+34}" y="{ly+33}" font-size="11.5" fill="#444">{sub}</text>'); ly += 40
A(f'<line x1="{LX}" y1="{ly+12}" x2="{LX+26}" y2="{ly+12}" stroke="#8b1a1a" stroke-width="2.2" stroke-dasharray="7 4"/>')
A(f'<text x="{LX+34}" y="{ly+16}" font-size="12">pursuers (wave 1 from the gate)</text>'); ly += 22
A(f'<line x1="{LX}" y1="{ly+12}" x2="{LX+26}" y2="{ly+12}" stroke="#3a3530" stroke-width="3.2"/>')
A(f'<text x="{LX+34}" y="{ly+16}" font-size="12">cliff (ticks on the low side)</text>'); ly += 22
A(f'<line x1="{LX}" y1="{ly+12}" x2="{LX+26}" y2="{ly+12}" stroke="#1a4f8b" stroke-width="1.3" stroke-dasharray="2 4"/>')
A(f'<text x="{LX+34}" y="{ly+16}" font-size="12">checked view back to the house (upper floor)</text>'); ly += 44
A(f'<text x="{LX}" y="{ly}" font-size="15" font-weight="bold">Heights (z vs lawn; asl if gate = 1,040 m)</text>'); ly += 6
for name, (x, y) in [("Gate", (20, -95)), ("Gate Rock", (-40, -196)), ("Poplar Cove", (10, -380)), ("Falls lip", (-85, -655)),
                     ("Plunge pool", (-115, -655)), ("Footlog", (-155, -672)), ("Creek, west edge", (-760, -745)),
                     ("Raven Rock", (384, -880)), ("The Knob", (466, -1068)), ("Knob west rock", (384, -1060)), ("Painted Rock", (162, -1018)), ("The Gap", (-300, -1218))]:
    z = hz(x, y)
    if name == "Footlog":
        z = FOOTLOG_Z
    A(f'<text x="{LX}" y="{ly+16}" font-size="12">{name}</text><text x="{LX+150}" y="{ly+16}" font-size="12" text-anchor="end">{z:+.0f} m</text>'
      f'<text x="{LX+230}" y="{ly+16}" font-size="12" text-anchor="end" fill="#555">{1040 + z:,.0f} m</text>'); ly += 18
ly += 30
A(f'<text x="{LX}" y="{ly}" font-size="15" font-weight="bold">Edges</text>'); ly += 4
for t in ["N: the hedge and the meadow (the estate)", "W: the Narrows, a boulder-choked chute", "E: Raven Spur falls to the estate road",
          "S: the parkway below the crest", "everywhere: laurel hells and slopes > 40 deg", "playable ~1.3 x 1.25 km; backdrop to 4.6 km"]:
    A(f'<text x="{LX}" y="{ly+16}" font-size="12">{t}</text>'); ly += 18

# ------------------------------------------------------------------ section along the view line
NS = {}
exec(open(SP + "/los.py").read().split("house = (0, 0, 7.0)")[0].replace("SP = sys.argv[1]; RUN = sys.argv[2]", f"SP = {SP!r}; RUN = {RUN!r}"), NS)
CAN = NS["can"]
SXo, SYo = PX, PY + PH + 70
ZMAX, ZMIN = 290.0, -110.0
A0, A1 = (0.0, 40.0), (182.0, -1146.0)          # house -> Painted Rock -> the crest
LTOT = math.hypot(A1[0] - A0[0], A1[1] - A0[1])
def qx(s_): return SXo + s_ * K
def qz(z): return SYo + (ZMAX - z) * K
A(f'<text x="{SXo}" y="{SYo-36}" font-size="15" font-weight="bold">Section along the view line: house - meadow - Poplar Cove - Laurel Fork - Painted Rock - crest (true scale)</text>')
A(f'<text x="{SXo}" y="{SYo-18}" font-size="12" fill="#444">Green = canopy model used for the sight checks (35 m cove trees, 25 m upper slopes, 15 m dry crests, 4-8 m laurel slick / talus). Blue dashed: Painted Rock sees the upper floor over the treetops.</text>')
ss = np.arange(0, LTOT, 3.0)
px_ = A0[0] + ss / LTOT * (A1[0] - A0[0]); py_ = A0[1] + ss / LTOT * (A1[1] - A0[1])
zs = np.array([hz(x, y) if y < -45 else 0.0 for x, y in zip(px_, py_)])
def canz(x, y):
    if y > -45: return 0.0
    return float(CAN[int(round((y + OY + 768) / CELL)), int(round((x + 768) / CELL))])
cz_ = np.array([canz(x, y) for x, y in zip(px_, py_)])
ground = " L".join(f"{qx(a):.1f},{qz(z):.1f}" for a, z in zip(ss, zs))
top = " L".join(f"{qx(a):.1f},{qz(z + c):.1f}" for a, z, c in zip(ss[::-1], zs[::-1], cz_[::-1]))
A(f'<path d="M{ground} L{top} Z" fill="#5f9a4a" fill-opacity="0.6"/>')
A(f'<path d="M{ground} L{qx(ss[-1]):.1f},{qz(ZMIN):.1f} L{qx(0):.1f},{qz(ZMIN):.1f} Z" fill="#b9a88a" stroke="#3b3222" stroke-width="1.2"/>')
for z in (-100, 0, 100, 200):
    A(f'<line x1="{qx(0):.1f}" y1="{qz(z):.1f}" x2="{qx(LTOT):.1f}" y2="{qz(z):.1f}" stroke="#777" stroke-width="0.5" stroke-dasharray="2 4"/>')
    A(f'<text x="{qx(LTOT)+6:.1f}" y="{qz(z)+4:.1f}" font-size="10" fill="#555">{z:+d}</text>')
A(f'<rect x="{qx(20):.1f}" y="{qz(8.4):.1f}" width="{40*K:.1f}" height="{8.4*K:.1f}" fill="#f4f1ea" stroke="#333"/>')
sp_ = math.hypot(162 - A0[0], -1018 - A0[1])
A(f'<line x1="{qx(sp_):.1f}" y1="{qz(hz(162, -1018) + 1.7):.1f}" x2="{qx(40):.1f}" y2="{qz(7):.1f}" stroke="#1a4f8b" stroke-width="1.5" stroke-dasharray="6 4"/>')
for name, (x, y) in [("house", (0, 0)), ("meadow", (8, -140)), ("Poplar Cove", (40, -330)), ("Laurel Fork", (95, -640)),
                     ("laurel slick", (140, -900)), ("Painted Rock", (162, -1018)), ("crest trail", (180, -1140))]:
    sx_ = math.hypot(x - A0[0], y - A0[1]); z = hz(x, y) if y < -45 else 0
    A(f'<text x="{qx(sx_):.1f}" y="{qz(max(z, 0) + 70):.1f}" font-size="11" text-anchor="middle" fill="#222">{name}</text>')
    A(f'<line x1="{qx(sx_):.1f}" y1="{qz(max(z, 0) + 66):.1f}" x2="{qx(sx_):.1f}" y2="{qz(z + 3):.1f}" stroke="#555" stroke-width="0.6"/>')
A('</svg>')
svg = "\n".join(out)
open(OUT, "w").write(svg)
print("svg bytes", len(svg), "raster jpg", os.path.getsize(jpg))
print("community share", {k: round(v * 100, 1) for k, v in share.items()})


for p in F.PATHS:
    pts = terrain.spline([(q[0], q[1]) for q in p["points"]], 2.0)
    z = np.array([hz(x, y) for x, y in pts]); dz = np.diff(z)
    L = float(np.hypot(*np.diff(pts, axis=0).T).sum())
    print(p["name"], "length", round(L), "up", round(float(dz[dz > 0].sum())), "down", round(float(-dz[dz < 0].sum())), "start", round(z[0]), "end", round(z[-1]))
print("footlog z", round(FOOTLOG_Z, 1))
