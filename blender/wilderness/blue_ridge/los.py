import sys, math, numpy as np
SP = sys.argv[1]; RUN = sys.argv[2]
sys.path.insert(0, "/Users/andrewcarr/Documents/projects/game_testing/blender/wilderness"); sys.path.insert(0, SP)
import terrain, br_features as F
TD = f"{SP}/terrain_out/{RUN}"; d = np.load(TD + "/terrain.npz"); H = d["H"].astype(float); N = H.shape[0]; CELL = 1536 / (N - 1); OY = F.OFFSET_Y
G = terrain.Grid(-768, -768, CELL, N, N)
def m(n): return terrain.read_png_fast(f"{TD}/masks/{n}.png").astype(float)[::-1] / 255
slope = m("slope") * 90; curv = m("curvature")
X = -768 + np.arange(N) * CELL; Y = X - OY; XX, YY = np.meshgrid(X, Y)
can = np.full(H.shape, 35.0)
can[H > 120] = 25.0
can[(curv > 0.56) & (H > 120)] = 15.0
slick = (slope > 33) & (curv > 0.5) & (H > 90)
can[slick] = 4.0
can[np.hypot(XX - 466, YY + 1068) < 140] = 4.0
can[slope > 48] = 0.0
for c in F.CLIFFS:                                 # talus / heath below every cliff: scattered small trees
    pts = terrain.spline([F.local(q) for q in c["points"]], 3.0)
    dd, _, _, _ = terrain.poly_field(G, pts, 110.0)
    below = np.isfinite(dd) & (H < np.interp(0, [0], [0]) + 1e9)
    can[np.isfinite(dd) & (slope > 28)] = np.minimum(can[np.isfinite(dd) & (slope > 28)], 8.0)
def in_poly(px, py, poly):
    inside = np.zeros(px.shape, bool); n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        inside ^= ((y1 > py) != (y2 > py)) & (px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-12) + x1)
    return inside
MEADOW = [(-190, -42), (230, -42), (240, -95), (205, -150), (120, -172), (20, -178), (-80, -170), (-160, -140), (-200, -95)]
can[in_poly(XX, YY, MEADOW)] = 0.0
def hz(x, y): return terrain.height_at(d["H"], G, np.asarray(x, float), np.asarray(y, float) + OY)
def cz(x, y):
    i = np.clip(((np.asarray(x) + 768) / CELL).round().astype(int), 0, N - 1); j = np.clip(((np.asarray(y) + OY + 768) / CELL).round().astype(int), 0, N - 1)
    return can[j, i]
def los(a, b, eye=1.7, skip=22.0, canopy=True):
    ax, ay = a[:2]; az = (a[2] if len(a) > 2 else float(hz([ax], [ay])[0])) + eye
    bx, by, bz = b
    L = math.hypot(bx - ax, by - ay); n = max(2, int(L / 2))
    t = np.arange(1, n) / n; x = ax + t * (bx - ax); y = ay + t * (by - ay); z = az + t * (bz - az)
    inside = y < -45
    g = np.where(inside, hz(np.where(inside, x, 0), np.where(inside, y, -100)), 0.0)
    c = np.where(inside, cz(np.where(inside, x, 0), np.where(inside, y, -100)), 0.0) if canopy else 0
    dd = np.hypot(x - ax, y - ay); c = np.where((dd > skip) & (np.hypot(x - bx, y - by) > 8), c, 0)
    clr = z - (g + c); k = int(np.argmin(clr))
    return dict(L=round(L), clear=round(float(clr[k]), 1), at=(round(float(x[k])), round(float(y[k]))))
house = (0, 0, 7.0)
pts = {k: tuple(v) for k, v in [(a, b) for a, b in [(s.split("=")[0], eval(s.split("=")[1])) for s in sys.argv[3:]]]} if len(sys.argv) > 3 else {}
P = dict(gate_rock=(-40, -207), raven=(420, -856), knob=(384, -1060), painted=(162, -1018), gap=(-300, -1218))
P.update(pts)
for nm, pt in P.items():
    print(f"{nm:9s} z={float(hz([pt[0]],[pt[1]])[0]):6.1f} -> house", los(pt, house), " terrain-only", los(pt, house, canopy=False)["clear"])
ft = (-155, -672, -126.0)
for nm in ("raven", "knob", "painted"):
    print(f"{nm} -> footlog", los(P[nm], ft), "| -> meadow", los(P[nm], (20, -120, 1.0)))
print("gate_rock -> knob", los(P["gate_rock"], (466, -1068, float(hz([466], [-1068])[0]) + 3)), "-> gap", los(P["gate_rock"], (-300, -1218, float(hz([-300], [-1218])[0]) + 3)))
print("slick share in play area", round(float(slick[(XX > -400) & (XX < 520) & (YY < -100) & (YY > -1250)].mean()) * 100, 1), "%")
