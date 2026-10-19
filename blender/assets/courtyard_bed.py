"""Raised planting bed for the courtyard's edges: limestone walls (separate stones, eased
edges, no paving joints) at sitting height, with a coping on the front wall, holding
layered garden planting in drifts, tallest at the back (against the glass) and spilling
over the front:

  back   tall golden grass and loose silver-leaved shrubs (olive-sprig cards)
  middle arching ferns, clipped boxwood mounds, more shrubs
  front  blue-green sedge tufts, star jasmine trailing over the coping and down the wall

All leaves are alpha-tested cards from the shared courtyard foliage atlas (one material),
with normals bent outward so each plant shades as a volume. Long axis along X, the front
(walkway side) faces -Y, origin at the floor centre. Units are metres.

Collision: walls, coping and soil are solid; the leaf cards are NoCollide (fronds and
trailers reach past the walls), the boxwood mounds sit inside the walls."""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import courtyard_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common

NAME = "CourtyardBed"

P = dict(
    name=NAME,
    length=6.0,
    depth=1.20,
    height=0.48,
    wall=0.10,
    coping=(0.28, 0.045),       # front coping width (overhangs the front by 2 cm), thickness
    soil_down=0.07,             # soil surface below the wall top
    seed=1,
    density=1.0,                # planting density multiplier
    box_every=4.6,              # one boxwood mound per this many metres
    trail_every=0.95,           # mean pitch of the jasmine clumps along the front
    clear=(),                   # x ranges (lo, hi) kept free of back-row planting (a tree, a mast)
)


class Planting:
    def __init__(self, rng):
        self.rng = rng
        self.bm = bmesh.new()
        self.uvl = self.bm.loops.layers.uv.new("UVMap")
        self.normals = {}

    def _norm(self, verts, n):
        for v in verts:
            self.normals[v] = n

    def card(self, centre, right, up, cell, normal, flip=None):
        f = cc.add_card(self.bm, self.uvl, centre, right, up, cell,
                        flip=self.rng.random() < 0.5 if flip is None else flip)
        self._norm(f.verts, normal)

    def strip(self, pts, hw, cell, normals, widths=None):
        rows = cc.add_strip(self.bm, self.uvl, pts, hw, cell, flip=self.rng.random() < 0.5, widths=widths)
        for (a, b), nn in zip(rows, normals):
            self.normals[a] = nn
            self.normals[b] = nn

    def finish(self, name, col, mat, root, limit=None):
        """limit (xmax, ymax): leaves pressed inside the bed's back wall and end walls (the
        glass is right behind them), so nothing pokes through into the galleries."""
        if limit:
            for v in self.bm.verts:
                v.co.x = max(-limit[0], min(limit[0], v.co.x))
                v.co.y = min(limit[1], v.co.y)
        order = list(self.bm.verts)
        ns = [self.normals.get(v, Vector((0, 0, 1))) for v in order]
        ob = common.mesh_object(name, self.bm, col, mat, root, smooth=True)
        cc.set_vertex_normals(ob.data, ns)
        return ob


def grass(pl, base, size, cell="grassA", n=5):
    rng = pl.rng
    a0 = rng.uniform(0, math.pi)
    for j in range(n):
        ang = a0 + j * math.pi / n
        right = Vector((math.cos(ang), math.sin(ang), 0)) * size * 0.5
        tilt = Vector((rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), 1)).normalized()
        pl.card(base + tilt * size * 0.5, right, tilt * size * 0.5, cell,
                Vector((math.cos(ang + 1.57) * 0.3, math.sin(ang + 1.57) * 0.3, 1)).normalized())


def shrub(pl, centre, r, cards):
    """Loose rounded shrub of sprig cards: each card's base inside, tip outward."""
    rng = pl.rng
    for _ in range(cards):
        while True:
            d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.4, 1)))
            if 0.2 < d.length <= 1.0:
                break
        d.normalize()
        pos = centre + Vector((d.x * r, d.y * r, d.z * r * 0.8)) * rng.uniform(0.25, 0.65)
        up = (d * 0.8 + Vector((0, 0, 0.5)) + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)) * 0.3).normalized()
        right = up.cross(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))).normalized()
        s = r * rng.uniform(0.85, 1.15)
        nn = ((pos - centre).normalized() * 0.7 + Vector((0, 0, 0.5))).normalized()
        pl.card(pos + up * s * 0.4, right * s * 0.5, up * s * 0.5, "sprigA" if rng.random() < 0.5 else "sprigB", nn)


def fern(pl, base, L, fronds):
    """Arching fern: fronds radiate from the crown, rise, then bow outward and down."""
    rng = pl.rng
    a0 = rng.uniform(0, 2 * math.pi)
    for j in range(fronds):
        a = a0 + j * 2 * math.pi / fronds + rng.uniform(-0.25, 0.25)
        d = Vector((math.cos(a), math.sin(a), 0))
        l = L * rng.uniform(0.75, 1.1)
        rise = rng.uniform(0.35, 0.55)
        pts = [base + Vector((0, 0, 0.02)), base + d * l * 0.32 + Vector((0, 0, l * rise)),
               base + d * l * 0.70 + Vector((0, 0, l * rise * 1.05)), base + d * l * 0.98 + Vector((0, 0, l * rise * 0.55))]
        side = d.cross(Vector((0, 0, 1)))
        hw = side * l * 0.21
        nn = (d * 0.4 + Vector((0, 0, 1))).normalized()
        pl.strip(pts, hw, "fern", [nn] * 4, widths=[0.35, 1.0, 0.9, 0.55])


def spill(pl, x, y_in, y_face, z_top, rng, strands=None):
    """A clump of star jasmine spilling over the coping: three to five strands fanned out
    from one point, each angled off the wall plane (so the clump has depth), arching over
    the lip and hanging free of the stone, longer and shorter."""
    n = strands or rng.randint(3, 5)
    for j in range(n):
        dx = rng.uniform(-0.12, 0.12)
        drop = rng.uniform(0.18, z_top - 0.06)
        out = rng.uniform(0.05, 0.13)
        phi = rng.uniform(-0.75, 0.75)
        w = 0.12 * rng.uniform(0.85, 1.2)
        hw = Vector((w * math.cos(phi), -w * abs(math.sin(phi)) * 0.6, w * math.sin(phi) * 0.4))
        pts = [Vector((x + dx * 0.3, y_in, z_top - 0.05)),
               Vector((x + dx * 0.6, y_face + 0.03, z_top + 0.035)),
               Vector((x + dx, y_face - out * 0.6, z_top - 0.07)),
               Vector((x + dx * 1.2, y_face - out, z_top - drop * 0.6)),
               Vector((x + dx * 1.3 + rng.uniform(-0.04, 0.04), y_face - out * 0.9, z_top - drop))]
        nn = Vector((0, -1, 0.25)).normalized()
        pl.strip(pts, hw, "jasmine", [Vector((0, -0.2, 1)).normalized(), Vector((0, -0.7, 0.7)).normalized(), nn, nn,
                                      nn], widths=[0.6, 1.0, 1.0, 0.85, 0.6])


def boxwood(bm, centre, r, rng):
    tmp = bmesh.new()
    bmesh.ops.create_icosphere(tmp, subdivisions=3, radius=r)
    ph = [rng.uniform(0, 6.28) for _ in range(6)]
    for v in tmp.verts:
        d = v.co.normalized()
        f = 1 + 0.075 * math.sin(5.0 * d.x + ph[0]) * math.sin(4.0 * d.y + ph[1]) * math.sin(4.5 * d.z + ph[2])
        f += 0.035 * math.sin(11.0 * d.x + ph[3]) * math.sin(9.0 * d.y + ph[4]) * math.sin(10.0 * d.z + ph[5])
        v.co = d * r * f
        v.co.z *= 0.85
    # drop the buried underside
    bmesh.ops.delete(tmp, geom=[f for f in tmp.faces if all(v.co.z < -r * 0.45 for v in f.verts)], context="FACES")
    vm = {v: bm.verts.new(v.co + centre) for v in tmp.verts}
    for f in tmp.faces:
        bm.faces.new([vm[v] for v in f.verts])
    tmp.free()


def groundcover(bm, x0, x1, y0, y1, z, rng, pitch=0.34):
    """Low mounded undergrowth over the soil (the dark mass under the leaf cards, so the
    bed reads full rather than as cards on bare earth); tucked under at its edges."""
    nx = max(2, round((x1 - x0) / pitch))
    ny = max(2, round((y1 - y0) / pitch))
    ph = [rng.uniform(0, 6.28) for _ in range(4)]
    grid = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            y = y0 + (y1 - y0) * j / ny
            edge = i in (0, nx) or j in (0, ny)
            h = 0.06 + 0.05 * math.sin(x * 2.3 + ph[0]) * math.sin(y * 3.1 + ph[1]) + \
                0.03 * math.sin(x * 5.7 + ph[2] + y * 2.0) + rng.uniform(-0.015, 0.015)
            row.append(bm.verts.new((x, y, z - 0.02 if edge else z + max(h, 0.01))))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rng = random.Random(p["seed"])
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    stone, soil, leaf, box = cc.limestone_mat(), cc.soil_mat(), cc.foliage_mat(), cc.boxwood_mat()

    srng = random.Random(p["seed"] + 100)
    L, D, H, t = p["length"], p["depth"], p["height"], p["wall"]
    cw, ct = p["coping"]

    def block(name, size, loc, bevel):
        """One long limestone piece; its UVs put the shared limestone map's slab courses
        (1.0 x 0.5 m, running bond, joints at v = 0.25 UV steps) on the faces as the
        wall's block joints: every face's v range is shifted to sit inside one course."""
        ob = cc.rbox(name, size, loc, stone, col, root, bevel=bevel, uv_tile=2.0, seg=1)
        uv = ob.data.uv_layers["UVMap"]
        du = srng.uniform(0, 1)
        for d in uv.data:
            d.uv = (d.uv.x + du, d.uv.y + 0.125)
        return ob

    # walls: front (under the coping), back and two ends; the coping is a ledge to sit
    # on that overhangs the front face by 2 cm
    wh = H - ct
    block(f"{n}_WallFront", (L, t, wh), (0, -D / 2 + t / 2, wh / 2), 0.006)
    block(f"{n}_WallBack", (L, t, H), (0, D / 2 - t / 2, H / 2), 0.008)
    block(f"{n}_Coping", (L, cw, ct), (0, -D / 2 - 0.02 + cw / 2, H - ct / 2), 0.010)
    ye = D - t - cw + 0.02 - 0.004
    for side, sx in (("W", -1), ("E", 1)):
        block(f"{n}_End{side}", (t, ye, H), (sx * (L / 2 - t / 2), (cw - 0.02 - t) / 2, H / 2), 0.008)
    zs = H - p["soil_down"]
    y0, y1 = -D / 2 + cw - 0.02, D / 2 - t          # planting strip (behind the coping)
    cc.rbox(f"{n}_Soil", (L - 2 * t, y1 - y0, 0.05), (0, (y0 + y1) / 2, zs - 0.025), soil, col, root, bevel=0,
            uv_tile=0)

    pl = Planting(rng)
    dens = p["density"]
    xin = L / 2 - t - 0.08

    def free(x):
        return all(not (lo <= x <= hi) for lo, hi in p["clear"])

    # back row: drifts of tall grass alternating with loose shrubs
    x = -xin + rng.uniform(0, 0.2)
    while x < xin:
        kind = rng.random()
        if free(x):
            yb = y1 - rng.uniform(0.18, 0.30)
            if kind < 0.5:
                for _ in range(rng.randint(2, 3)):
                    grass(pl, Vector((x + rng.uniform(-0.12, 0.12), yb + rng.uniform(-0.08, 0.08), zs - 0.02)),
                          rng.uniform(1.10, 1.50))
                    x += rng.uniform(0.28, 0.40) / dens
            else:
                r = rng.uniform(0.48, 0.66)
                shrub(pl, Vector((x, yb - 0.06, zs + r * 0.8)), r, int(22 * dens))
                x += r * 1.35 / dens
        else:
            x += 0.3
    # middle: ferns with the odd boxwood mound and small shrub
    bmb = bmesh.new()
    nbox = max(1, round(L / p["box_every"]))
    box_x = [(-L / 2 + L * (i + 0.5) / nbox) + rng.uniform(-0.3, 0.3) for i in range(nbox)]
    box_x = [bx for bx in box_x if free(bx) and free(bx - 0.35) and free(bx + 0.35)]
    for bx in box_x:
        r = rng.uniform(0.30, 0.38)
        boxwood(bmb, Vector((bx, (y0 + y1) / 2 - 0.05, zs + r * 0.55)), r, rng)
    x = -xin + rng.uniform(0.1, 0.3)
    ym = (y0 + y1) / 2 + 0.02
    while x < xin:
        if all(abs(x - bx) > 0.42 for bx in box_x):
            if rng.random() < 0.72:
                fern(pl, Vector((x, ym + rng.uniform(-0.08, 0.08), zs - 0.01)), rng.uniform(0.70, 0.95),
                     rng.randint(7, 9))
            else:
                r = rng.uniform(0.28, 0.36)
                shrub(pl, Vector((x, ym, zs + r * 0.7)), r, int(10 * dens))
        x += rng.uniform(0.50, 0.68) / dens
    # front: sedge tufts behind the coping
    x = -xin + rng.uniform(0, 0.2)
    while x < xin:
        grass(pl, Vector((x, y0 + 0.14 + rng.uniform(-0.04, 0.04), zs - 0.01)), rng.uniform(0.42, 0.58), "grassB", 3)
        x += rng.uniform(0.45, 0.7) / dens
    leafy = pl.finish(f"{n}_PlantingNoCollide", col, leaf, root, limit=(L / 2 - 0.03, D / 2 - 0.03))

    # jasmine spilling over the coping in clumps, with gaps of bare stone between
    tr = Planting(rng)
    x = -L / 2 + 0.25 + rng.uniform(0, 0.4)
    while x < L / 2 - 0.25:
        spill(tr, x, y0 + 0.1, -D / 2 - 0.02, H, rng)
        x += p["trail_every"] * rng.uniform(0.7, 1.7)
    tr.finish(f"{n}_TrailingNoCollide", col, leaf, root, limit=(L / 2 - 0.03, D / 2 - 0.03))
    groundcover(bmb, -L / 2 + t, L / 2 - t, y0, y1, zs, rng)
    common.mesh_object(f"{n}_Boxwood", bmb, col, box, root, smooth=True)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
