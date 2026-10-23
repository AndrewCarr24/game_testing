"""Standing water on a tunnel floor: an irregular flat patch with a soft lobed edge and a few dry
islands (concrete showing through), 2 mm above the floor (islands 3.5 mm), in the mirror-glossy
near-black `bunker_kit.wet()`. 3.0 x 2.2 m; `variant="small"` is 1.2 x 0.8 m (also available as
tunnel_puddle_small). Origin: floor centre. All NoCollide: you walk through it."""
import importlib
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bunker_door  # noqa: E402

importlib.reload(bunker_door)
Geo, bk = bunker_door.Geo, bunker_door.bk
common = bk.common

NAME = "TunnelPuddle"

P = dict(
    name=NAME,
    variant="",            # "" = 3.0 x 2.2 m, "small" = 1.2 x 0.8 m
    seed=11,
    rim=150,                # points round the edge
    z=0.002,
    island_z=0.0035,
)
SIZES = {"": (3.0, 2.2, 3), "small": (1.2, 0.8, 1)}      # width, depth, islands


def lobed(rng, n, w, d, k=(2, 3, 5, 7)):
    """n points round a closed, star-shaped, lobed outline fitted to exactly w x d metres."""
    amps = [rng.uniform(0.06, 0.12) / (1 + 0.3 * i) for i in range(len(k))]
    phs = [rng.uniform(0, 2 * math.pi) for _ in k]
    pts = []
    for i in range(n):
        th = 2 * math.pi * i / n
        r = 1 + sum(a * math.sin(kk * th + ph) for a, kk, ph in zip(amps, k, phs))
        pts.append((r * math.cos(th), r * math.sin(th)))
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    sx, sy = w / (max(xs) - min(xs)), d / (max(ys) - min(ys))
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    return [((x - cx) * sx, (y - cy) * sy) for x, y in pts]


def fan(g, pts, z, centre=(0.0, 0.0), tile=6.0):
    """Triangle fan over a star-shaped outline, facing up, with world-scale UVs."""
    bm = g.bm
    c = bm.verts.new((centre[0], centre[1], z))
    vs = [bm.verts.new((x, y, z)) for x, y in pts]
    n = len(vs)
    for i in range(n):
        f = bm.faces.new([c, vs[i], vs[(i + 1) % n]])
        f.smooth = False
        for lp in f.loops:
            lp[g.uv].uv = (lp.vert.co.x / tile, lp.vert.co.y / tile)
        f.normal_update()
        if f.normal.z < 0:
            f.normal_flip()


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    w, d, nisl = SIZES[p["variant"]]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rng = random.Random(p["seed"] + (5 if p["variant"] else 0))

    g = Geo()
    outline = lobed(rng, p["rim"], w, d)
    fan(g, outline, p["z"])
    g.finish(f"{n}_Water_NoCollide", col, bk.wet(), root)

    # dry islands: small lobed patches well inside the outline (found by sampling for room)
    g = Geo(tile=6.0)
    placed = []
    tries = 0
    while len(placed) < nisl and tries < 200:
        tries += 1
        rad = rng.uniform(0.07, 0.13) * (w / 3.0) ** 0.5 * (1.6 if not p["variant"] else 1.0)
        ang = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(0.15, 0.55)
        cx, cy = math.cos(ang) * rr * w / 2, math.sin(ang) * rr * d / 2
        if any((cx - a) ** 2 + (cy - b) ** 2 < (rad + r2 + 0.12) ** 2 for a, b, r2 in placed):
            continue
        # the island (and a margin) must lie inside the outline: test against the polygon
        if not all(_inside(outline, cx + math.cos(t) * (rad + 0.08), cy + math.sin(t) * (rad + 0.08))
                   for t in [i * math.pi / 6 for i in range(12)]):
            continue
        placed.append((cx, cy, rad))
        isl = lobed(rng, 22, 2 * rad * rng.uniform(1.0, 1.5), 2 * rad, k=(2, 3))
        fan(g, [(cx + x, cy + y) for x, y in isl], p["island_z"], centre=(cx, cy))
    if placed:
        g.finish(f"{n}_Islands_NoCollide", col, bk.concrete(), root)
    else:
        g.bm.free()

    return root, [o for o in root.children_recursive if o.type == "MESH"]


def _inside(poly, x, y):
    ins = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            ins = not ins
        j = i
    return ins


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
