"""Walkable grounds: the collision boxes for everything outdoors (plan.GROUNDS), so the
player can leave the house and walk the estate.

  base()      the lawn and the stone terrace (ground boxes), the perimeter hedge, and an
              invisible boundary just outside it that also closes the drive gap behind the
              gate: nobody walks (or jumps) out of the world
  voxelize()  every zone's placed geometry (world-space copies, grounds.place_zones) turned
              into boxes automatically: the meshes' triangles are sampled every 10 cm, each
              sample lands in a 25 cm column and is an up-facing top (a solid starts below
              it), a down-facing underside (the solid ends) or a side; per column that gives
              the solid z intervals (a bench, a deck with its steps, a hedge ring with the
              open lawn inside it, a pergola's beams with the walkable floor under them, the
              lower trunk of a tree but not its crown). Columns with the same intervals merge
              into rectangles. Things lower than LOW (paths, paving, the court surface) are
              left to the lawn: the feet sink a few cm into them, invisibly.
  water       pools, fountains, troughs: an invisible blocker over the water (seeThrough:
              the Grimble sees across it), so nobody falls in.

Coordinates: the boxes are written in glTF (x, y up, -y) to their own compact file,
assets/levels/<level>_grounds.json (level["grounds"]["file"]), apart from level["colliders"]
(the shell's: the engine sizes the sun's shadow box and the Grimble's sight walls from those).
"""
import math

import numpy as np

from lib import common

CELL = 0.25           # column size (m); the player is 0.5 m wide
SAMPLE = 0.1          # triangle sampling step (m)
LOW = 0.1             # intervals whose top is under lawn + LOW are walked over (paths, paving)
BAND = (-0.4, 4.6)    # z band kept, relative to the lawn (nothing above is in reach)
WATER_WALL = 2.2      # blocker height over water (higher than a jump)
BOUND_H = 6.0         # the invisible boundary round the hedge

# parts that don't collide: soft or high foliage, lights and lenses, loose small things
SKIP = ("Crown", "Canopy", "Blades", "Flowers", "Bloom", "Vines", "Fruit", "Lamp", "Lens", "Light",
        "Strip", "Embers", "Coals", "Towel", "Throw", "NoCollide", "Collider", "Joint", "Lines")
SKIP_ASSETS = ("PlantShrubGrass",)          # ornamental grass: walked through
WATER = ("Water",)
TRUNK, TRUNK_H = "Trunk", 2.0   # trees: only the trunk below 2 m collides (its limbs fan out above)


def _is_water(ob):
    if any(t in ob.name for t in WATER):
        return True
    return any(m is not None and m.name.startswith("M_Water") for m in ob.data.materials)


def _skip(ob):
    return any(t in ob.name for t in SKIP) or any(t in ob.name for t in SKIP_ASSETS)


def _triangles(objs):
    """(T, 3, 3) world-space triangles of `objs`."""
    out = []
    for ob in objs:
        me = ob.data
        me.calc_loop_triangles()
        n = len(me.loop_triangles)
        if not n:
            continue
        co = np.empty(len(me.vertices) * 3, np.float64)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        mw = np.array(ob.matrix_world)
        co = co @ mw[:3, :3].T + mw[:3, 3]
        idx = np.empty(n * 3, np.int64)
        me.loop_triangles.foreach_get("vertices", idx)
        out.append(co[idx.reshape(-1, 3)])
    return np.concatenate(out) if out else np.zeros((0, 3, 3))


def _samples(tris, step):
    """Points on every triangle about `step` apart, with each point's kind:
    1 = up-facing, -1 = down-facing, 0 = side. Returns (P (N, 3), kind (N,))."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    n = np.cross(b - a, c - a)
    ln = np.linalg.norm(n, axis=1)
    ok = ln > 1e-10
    a, b, c, n, ln = a[ok], b[ok], c[ok], n[ok], ln[ok]
    nz = n[:, 2] / ln
    kind = np.where(nz > 0.3, 1, np.where(nz < -0.3, -1, 0)).astype(np.int8)
    edge = np.maximum.reduce([np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1),
                              np.linalg.norm(a - c, axis=1)])
    k = np.clip(np.ceil(edge / step).astype(np.int64), 1, 600)
    pts, kinds = [], []
    for kk in np.unique(k):
        sel = np.nonzero(k == kk)[0]
        i, j = np.meshgrid(np.arange(kk + 1), np.arange(kk + 1), indexing="ij")
        m = (i + j) <= kk
        u, v = i[m] / kk, j[m] / kk                       # (M,)
        chunk = max(1, int(2_000_000 // len(u)))
        for s in range(0, len(sel), chunk):
            t = sel[s:s + chunk]
            P = (a[t, None, :] + (b - a)[t, None, :] * u[None, :, None] + (c - a)[t, None, :] * v[None, :, None])
            pts.append(P.reshape(-1, 3))
            kinds.append(np.repeat(kind[t], len(u)))
    if not pts:
        return np.zeros((0, 3)), np.zeros(0, np.int8)
    return np.concatenate(pts), np.concatenate(kinds)


def _column_intervals(zs, ks, zlo, step):
    """Solid z intervals of one column from its samples (sorted top down, undersides before
    tops at the same height)."""
    out, top = [], None
    for z, k in zip(zs, ks):
        if k == 1:
            if top is None:
                top = z
        elif k == -1:
            if top is not None:
                out.append((z, top))
                top = None
            else:
                out.append((z - 0.03, z))         # a thin underside on its own (a soffit)
        else:
            out.append((z - step, z))             # (samples are <= step apart up the face; the
                                                  # top one is its top edge: no lip over a deck's edge)
    if top is not None:
        out.append((zlo, top))
    return out


def _union(iv, gap=0.06):
    iv = sorted(iv)
    out = []
    for z0, z1 in iv:
        if out and z0 <= out[-1][1] + gap:
            out[-1] = (out[-1][0], max(out[-1][1], z1))
        else:
            out.append((z0, z1))
    return out


def _rectangles(cells):
    """Greedy cover of a set of (ix, iy) cells by rectangles [(ix0, iy0, ix1, iy1)] (exclusive)."""
    left = set(cells)
    out = []
    for ix, iy in sorted(cells, key=lambda c: (c[1], c[0])):
        if (ix, iy) not in left:
            continue
        x1 = ix + 1
        while (x1, iy) in left:
            x1 += 1
        y1 = iy + 1
        while all((x, y1) in left for x in range(ix, x1)):
            y1 += 1
        for y in range(iy, y1):
            for x in range(ix, x1):
                left.discard((x, y))
        out.append((ix, iy, x1, y1))
    return out


def voxelize(objs, lawn, cell=CELL, step=SAMPLE):
    """Boxes (Blender (lo, hi)) for the solid parts of `objs` in the reachable band."""
    zlo, zhi = lawn + BAND[0], lawn + BAND[1]
    Ps, Ks = [], []
    for low in (False, True):
        tris = _triangles([ob for ob in objs if (TRUNK in ob.name) == low])
        if not len(tris):
            continue
        P, K = _samples(tris, step)
        # (everything above stays: a tall block's top says it's solid below; a tree's limbs
        # above TRUNK_H go: the trunk is what's in the way, not the branches overhead)
        keep = (P[:, 2] >= zlo - 1.0) & ((P[:, 2] <= lawn + TRUNK_H) if low else True)
        Ps.append(P[keep])
        Ks.append(K[keep])
    if not Ps:
        return []
    P, K = np.concatenate(Ps), np.concatenate(Ks)
    x0, y0 = math.floor(P[:, 0].min() / cell) * cell - cell, math.floor(P[:, 1].min() / cell) * cell - cell
    ix = np.floor((P[:, 0] - x0) / cell).astype(np.int64)
    iy = np.floor((P[:, 1] - y0) / cell).astype(np.int64)
    W = int(ix.max()) + 2
    col = iy * W + ix
    zr = np.round(P[:, 2], 3)
    # per column, top down; at the same height an underside before a top (a seat on its base)
    order = np.lexsort((np.where(K == -1, 0, np.where(K == 0, 1, 2)), -zr, col))
    col, zr, K = col[order], zr[order], K[order]
    # drop exact repeats (several samples of one flat face in a column)
    rep = np.ones(len(col), bool)
    rep[1:] = (col[1:] != col[:-1]) | (zr[1:] != zr[:-1]) | (K[1:] != K[:-1])
    col, zr, K = col[rep], zr[rep], K[rep]
    starts = np.flatnonzero(np.r_[True, col[1:] != col[:-1]])
    ends = np.r_[starts[1:], len(col)]
    groups = {}

    def snap(z0, z1):
        """Fewer distinct columns (fewer, bigger boxes): anything starting near the lawn starts
        at the band's bottom; walkable tops keep 2 cm, tops out of a jump's reach (over 1.4 m)
        round up to 25 cm, undersides overhead to 10 cm."""
        z0 = zlo if z0 < lawn + 0.15 else math.floor(z0 / 0.1) * 0.1
        q = 0.25 if z1 > lawn + 1.4 else 0.02
        return round(z0, 3), round(math.ceil((z1 - lawn) / q) * q + lawn, 3)

    for s, e in zip(starts, ends):
        iv = _union(_column_intervals(zr[s:e].tolist(), K[s:e].tolist(), zlo, step))
        key = []
        for z0, z1 in iv:
            z0, z1 = max(z0, zlo), min(z1, zhi)
            if z1 - z0 < 0.01 or z1 < lawn + LOW:
                continue
            key.append(snap(z0, z1))
        key = _union(key, gap=0.0)
        if key:
            c = int(col[s])
            groups.setdefault(tuple(key), []).append((c % W, c // W))
    boxes = []
    for key, cells in groups.items():
        for a0, b0, a1, b1 in _rectangles(cells):
            for z0, z1 in key:
                boxes.append(((x0 + a0 * cell, y0 + b0 * cell, round(z0, 3)),
                              (x0 + a1 * cell, y0 + b1 * cell, round(z1, 3))))
    return boxes


def water_blockers(objs, lawn, inset=0.05):
    out = []
    for ob in objs:
        lo, hi = common.world_aabb([ob])
        if hi.x - lo.x < 0.3 or hi.y - lo.y < 0.3:
            continue
        out.append(((lo.x + inset, lo.y + inset, lawn + BAND[0]), (hi.x - inset, hi.y - inset, hi.z + WATER_WALL)))
    return out


def base(plan):
    """Lawn and terrace ground boxes, the perimeter hedge, the world boundary. Blender boxes,
    each (lo, hi, tag)."""
    G, z = plan.GROUNDS, plan.LAWN_Z
    out = []
    lx0, ly0, lx1, ly1 = G["lawn"]
    out.append(((lx0, ly0, z - 1.0), (lx1, ly1, z), "ground"))
    for x0, y0, x1, y1 in G["terrace"]:
        out.append(((x0, y0, z - 0.5), (x1, y1, z + 0.06), "ground"))
    hd = G["hedge"]
    x0, y0, x1, y1 = hd["rect"]
    t, ht = hd["thick"], hd["height"]
    sides = {"s": ("x", y0, x0, x1), "n": ("x", y1, x0, x1), "w": ("y", x0, y0, y1), "e": ("y", x1, y0, y1)}
    for side, (axis, line, a0, a1) in sides.items():
        spans = [(a0 - t / 2, a1 + t / 2)]
        for gs, g0, g1 in hd["gaps"]:
            if gs == side:
                spans = [s for (b0, b1) in spans for s in ((b0, min(b1, g0)), (max(b0, g1), b1)) if s[1] - s[0] > 0.1]
        for b0, b1 in spans:
            lo, hi = ((b0, line - t / 2, z), (b1, line + t / 2, z + ht)) if axis == "x" else \
                     ((line - t / 2, b0, z), (line + t / 2, b1, z + ht))
            out.append((lo, hi, "hedge"))
    # the boundary: just outside the hedge's outer face, all the way round (closes the gap)
    o, w = t / 2 + 0.6, 0.3
    bx0, by0, bx1, by1 = x0 - o, y0 - o, x1 + o, y1 + o
    for lo, hi in (((bx0 - w, by0 - w, z), (bx1 + w, by0, z + BOUND_H)), ((bx0 - w, by1, z), (bx1 + w, by1 + w, z + BOUND_H)),
                   ((bx0 - w, by0, z), (bx0, by1, z + BOUND_H)), ((bx1, by0, z), (bx1 + w, by1, z + BOUND_H))):
        out.append((lo, hi, "bound"))
    return out


def _flat(lo, hi):
    a = common.aabb_gltf(lo, hi)
    return [round(v, 3) for v in a["min"] + a["max"]]


def build(plan, placed, doors=()):
    """The walkable outdoors: (meta, boxes). meta goes into the level file's "grounds" (what
    the engine and the Grimble need to know: the lawn's height, the walkable bounds, the
    house's footprint, the exterior doors); boxes is the compact collider file (glTF
    [x0, y0, z0, x1, y1, z1] per box) by kind: "ground" (lawn, terrace), "hedge", "bound"
    (invisible, seeThrough), "water" (invisible blockers, seeThrough), "solid" (the zones'
    geometry). placed: the zones' world-space mesh copies."""
    lawn = plan.LAWN_Z
    solid = [ob for ob in placed if ob.type == "MESH" and ob.data.polygons and not _skip(ob) and not _is_water(ob)]
    water = [ob for ob in placed if ob.type == "MESH" and ob.data.polygons and _is_water(ob)]
    boxes = {"ground": [], "hedge": [], "bound": [], "water": [], "solid": []}
    for lo, hi, tag in base(plan):
        boxes[tag].append(_flat(lo, hi))
    boxes["solid"] = [_flat(lo, hi) for lo, hi in voxelize(solid, lawn)]
    boxes["water"] = [_flat(lo, hi) for lo, hi in water_blockers(water, lawn)]
    G = plan.GROUNDS
    hx0, hy0, hx1, hy1 = G["hedge"]["rect"]
    t = G["hedge"]["thick"]
    inner = (hx0 + t / 2, hy0 + t / 2, hx1 - t / 2, hy1 - t / 2)
    rects = [r["rect"] for r in plan.ROOMS.values()]
    house = (min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects))
    g = lambda r: [r[0], -r[3], r[2], -r[1]]          # Blender rect -> glTF x0, z0, x1, z1
    print("GROUNDS colliders: " + ", ".join(f"{k} {len(v)}" for k, v in boxes.items()))
    meta = {
        "lawn": round(lawn, 3),                       # glTF y of the lawn
        "terrace": round(lawn + 0.06, 3),             # ... of the stone terrace ringing the house
        "bounds": g(inner),                           # walkable: inside the perimeter hedge
        "house": g(house),                            # the house's footprint (its own floors/colliders)
        "terraces": [g(r) for r in G["terrace"]],
        "zones": {z: g(i["rect"]) for z, i in G["zones"].items()},
        "doors": list(doors),                         # exterior doors: [{asset, position, rotationY, room}]
        "seeThrough": ["bound", "water"],             # kinds a sight line passes
    }
    return meta, boxes


def facades(h, plan):
    """Each room's see-through openings in the outer walls (windows, doorways; not the garage
    door), for the engine's culler outdoors: a room's furniture is drawn from outside only
    while one of these faces the eye. Returns {room: [[x0, z0, x1, z1, nx, nz], ...]} in glTF
    (the opening's extent on the facade line and its outward normal)."""
    out = {}
    for c in plan.CUTS:
        if c["kind"] not in ("window", "opening"):
            continue
        sign = h.exterior_side(c)
        if sign is None:
            continue
        a0, a1 = c["span"]
        for room, r in plan.ROOMS.items():
            z0, z1 = h.z_range_of(r)
            if z0 > c["z"][0] + 1e-6 or z1 < c["z"][1] - 1e-6:
                continue
            x0, y0, x1, y1 = r["rect"]
            lo, hi, b0, b1 = (y0, y1, x0, x1) if c["axis"] == "x" else (x0, x1, y0, y1)
            edge = lo if sign > 0 else hi
            if abs(edge - c["line"]) > 1e-6 or b0 >= a1 - 1e-6 or b1 <= a0 + 1e-6:
                continue
            if c["axis"] == "x":        # wall along x at y = line; outward = -sign along y
                seg = [a0, -c["line"], a1, -c["line"], 0.0, float(sign)]
            else:                       # wall along y at x = line; outward = -sign along x
                seg = [c["line"], -a1, c["line"], -a0, float(-sign), 0.0]
            out.setdefault(room, []).append([round(v, 3) for v in seg])
    return out
