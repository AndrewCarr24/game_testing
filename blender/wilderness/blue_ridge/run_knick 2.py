"""Test of a proposed `knicks` hook (post-erosion, pre-cliffs): lower a river reach below a lip."""
import sys, json, math, numpy as np
SP = sys.argv[1]; cell = float(sys.argv[2]); name = sys.argv[3]
sys.path.insert(0, "/Users/andrewcarr/Documents/projects/game_testing/blender/wilderness"); sys.path.insert(0, SP)
import terrain, br_features as F
terrain.OUT_ROOT = SP + "/terrain_out"
_orig = terrain.apply_cliffs
def knicks(H, grid, p, noise):
    X, Y = grid.xy()
    for k in F.KNICKS:
        pts = terrain.spline([F.local(q) for q in k["points"]], 3.0)
        d, at, s, side = terrain.poly_field(grid, pts, k["width"] / 2)
        fin = np.isfinite(d)
        t = np.clip(np.where(fin, d, 1e9) / (k["width"] / 2), 0, 1)
        across = (1 - t * t) ** 2
        total = np.hypot(*(pts[1:, :2] - pts[:-1, :2]).T).sum()
        along = terrain.smoothstep(0, k["lip"], s) * (1 - terrain.smoothstep(total - k["fade"], total, s))
        H = H - k["height"] * across * along * fin
    return H
def pools(H, grid, p, noise):
    X, Y = grid.xy()
    for k in F.KNICKS:
        if k.get("pool"):
            c = F.local(k["pool"]["center"]); r = k["pool"]["radius"]
            tt = np.clip(np.hypot(X - c[0], Y - c[1]) / r, 0, 1)
            H = H - k["pool"]["depth"] * (1 - tt * tt) ** 2
    return H
def patched(H, grid, p, noise):
    H2, info = _orig(knicks(H, grid, p, noise), grid, p, noise)
    return pools(H2, grid, p, noise), info
terrain.apply_cliffs = patched
ov = F.terrain_overrides(); ov["cell"] = cell; ov["name"] = name
ov["shapes"] = [s for s in ov["shapes"] if s["name"] != "plunge_pool"]
st = terrain.build(**ov)
