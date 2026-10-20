"""Shared helpers for the kitchen_* and scullery assets (not an asset itself):
the Builder (collection + root + box parts), kitchen materials and textures,
lathing, cabinet-front layout and a few cheap props (bowls, jars, stacks)."""
import importlib
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(materials)
importlib.reload(textures)

CEIL = 4.2


# ------------------------------------------------------------------ textures

def calacatta(n=1024, seed=44):
    """Bold white marble with broad grey and warm gold veins. One tile = 1.5 m."""
    name = "T_Kitchen_Calacatta_BaseColor"
    path = os.path.join(textures.TEX_DIR, name + ".png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 1, n, endpoint=False)[None, :] * np.ones((n, 1))
    y = np.linspace(0, 1, n, endpoint=False)[:, None] * np.ones((1, n))
    t1 = textures._noise(n, 1.0, 1.0, 2.7, rng)
    t2 = textures._noise(n, 1.0, 1.0, 2.5, rng)
    t3 = textures._noise(n, 1.0, 1.0, 2.9, rng)
    fine_w = textures._noise(n, 1.0, 1.0, 1.3, rng)
    v1 = np.abs(np.sin(np.pi * (1 * x + 2 * y + 0.55 * t1 + 0.035 * fine_w)))
    v2 = np.abs(np.sin(np.pi * (2 * x + 3 * y + 0.9 * t2 + 0.05 * fine_w)))
    v3 = np.abs(np.sin(np.pi * (3 * x + 5 * y + 1.0 * t3 + 0.06 * fine_w)))
    major = (1 - v1) ** 60
    minor = 0.8 * (1 - v2) ** 80
    fine = 0.5 * (1 - v3) ** 150
    halo = 0.5 * (1 - v1) ** 6
    cloud = textures._noise(n, 1.0, 1.0, 2.6, rng) * 0.5 + 0.5
    base = np.array([0.80, 0.79, 0.76]) * (0.92 + 0.08 * cloud)[..., None]
    grey = np.array([0.16, 0.16, 0.17])
    gold = np.array([0.50, 0.37, 0.20])
    lin = base * (1 - 0.30 * halo[..., None])
    lin = lin * (1 - minor[..., None]) + gold * minor[..., None]
    lin = lin * (1 - fine[..., None]) + grey * fine[..., None]
    lin = lin * (1 - major[..., None]) + grey * major[..., None]
    return textures._save(name, textures._to_srgb(lin))


def stone_floor(n=1024, seed=52):
    """Honed warm-grey limestone, large format: 2 x 2 tiles of 1.2 m per 2.4 m tile,
    with hairline grout and a faint cloudy figure. One tile = 2.4 m."""
    name = "T_Kitchen_Stone_BaseColor"
    path = os.path.join(textures.TEX_DIR, name + ".png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(seed)
    u = np.linspace(0, 1, n, endpoint=False)[None, :] * np.ones((n, 1))
    v = np.linspace(0, 1, n, endpoint=False)[:, None] * np.ones((1, n))
    tu = np.floor(u * 2).astype(int)
    tv = np.floor(v * 2).astype(int)
    tid = tu + 2 * tv
    tone = rng.uniform(-1, 1, 4)[tid]
    cloud = textures._noise(n, 1.0, 1.0, 2.2, rng) * 0.5 + 0.5
    fine = textures._noise(n, 1.0, 1.0, 0.6, rng) * 0.5 + 0.5
    vein = np.abs(np.sin(2 * np.pi * (1.3 * u + 0.7 * v + 1.2 * textures._noise(n, 1.0, 1.0, 1.8, rng))))
    vein = 0.6 * (1 - vein) ** 30
    t = np.clip(0.55 * cloud + 0.15 * fine + 0.12 * tone + 0.15, 0, 1)
    light = np.array([0.40, 0.355, 0.30])
    dark = np.array([0.29, 0.255, 0.215])
    lin = dark + (light - dark) * t[..., None]
    lin = lin * (1 - vein[..., None] * 0.5)
    fu = np.minimum((u * 2) % 1.0, 1 - (u * 2) % 1.0) * 1.2
    fv = np.minimum((v * 2) % 1.0, 1 - (v * 2) % 1.0) * 1.2
    grout = (np.minimum(fu, fv) < 0.0016)
    lin[grout] *= 0.45
    return textures._save(name, textures._to_srgb(lin))


# ----------------------------------------------------------------- materials

def calacatta_mat():
    m = common.pbr_material("M_Kitchen_Calacatta", (0.8, 0.79, 0.76), roughness=0.14, coat=0.0)
    common.set_base_color_map(m, textures.load(calacatta()))
    return m


def stone_floor_mat():
    m = common.pbr_material("M_Kitchen_Stone", (0.4, 0.36, 0.30), roughness=0.38)   # polished
    common.set_base_color_map(m, textures.load(stone_floor()))
    return m


def brushed_steel():
    return common.pbr_material("M_Steel_Brushed", (0.62, 0.62, 0.64), roughness=0.32, metallic=1.0)


def black_glass():
    return common.pbr_material("M_Appliance_Glass", (0.012, 0.012, 0.015), roughness=0.06, metallic=0.4)


def carcass():
    return common.pbr_material("M_Carcass_Black", (0.012, 0.012, 0.013), roughness=0.6)


def ceramic(name="M_Ceramic_White", colour=(0.78, 0.76, 0.72), roughness=0.22):
    return common.pbr_material(name, colour, roughness=roughness)


def dark_glaze():
    return common.pbr_material("M_Ceramic_Charcoal", (0.05, 0.05, 0.055), roughness=0.3)


def cream_fabric():
    return materials.fabric("M_Fabric_Oat", (0.42, 0.37, 0.30))


def leather_tan():
    m = common.pbr_material("M_Leather_Cognac", (0.23, 0.075, 0.025), roughness=0.62)
    common.set_normal_map(m, textures.load(textures.leather_normal(), non_color=True), 0.6)
    return m


# ------------------------------------------------------------------- builder

class Builder:
    def __init__(self, name):
        self.n = name
        self.col = common.fresh_collection(name)
        self.root = common.empty(name, self.col)

    def box(self, name, size, centre, mat, bevel=0.002, seg=1, tile=0.5, shift=None,
            world_uv=False, parent=None, smooth=None):
        ob = common.mesh_object(f"{self.n}_{name}", common.box_bmesh(size), self.col, mat,
                                parent or self.root, smooth=bool(bevel) if smooth is None else smooth)
        ob.location = centre
        if bevel:
            common.add_bevel(ob, bevel, segments=seg)
        if tile:
            if world_uv:
                world_box_uv(ob, tile)
            else:
                common.box_uv(ob, tile)
            if shift:
                shift_uv(ob, *shift)
        return ob

    def lathe(self, name, profile, mat, loc=(0, 0, 0), segs=32, sharp=40.0, uv_tile=0.5, parent=None, closed=True):
        bm = lathe(profile, segs, closed=closed, sharp=sharp)
        ob = common.mesh_object(f"{self.n}_{name}", bm, self.col, mat, parent or self.root)
        ob.location = loc
        if uv_tile:
            planar_uv(ob, uv_tile)
        return ob

    def tube(self, name, pts, r, mat, closed=False, res=4, parent=None):
        return common.tube_object(f"{self.n}_{name}", pts, r, self.col, mat, parent or self.root,
                                  closed=closed, profile_res=res)

    def finish(self):
        parts = [o for o in self.root.children_recursive if o.type == "MESH"]
        return self.root, parts


def shift_uv(ob, du, dv):
    uv = ob.data.uv_layers["UVMap"]
    for d in uv.data:
        d.uv = (d.uv[0] + du, d.uv[1] + dv)


def world_box_uv(ob, tile):
    """Box UVs from the object's position in the asset (so neighbouring slabs of one
    stone continue the same pattern), grain/veins along the longest face axis."""
    me = ob.data
    dims = [max(v.co[a] for v in me.vertices) - min(v.co[a] for v in me.vertices) for a in range(3)]
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    loc = ob.location
    for poly in me.polygons:
        n = [abs(c) for c in poly.normal]
        na = n.index(max(n))
        a, b = [i for i in range(3) if i != na]
        if dims[b] > dims[a]:
            a, b = b, a
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = ((co[a] + loc[a]) / tile, (co[b] + loc[b]) / tile)


def planar_uv(ob, tile):
    me = ob.data
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        n = [abs(c) for c in poly.normal]
        na = n.index(max(n))
        a, b = [i for i in range(3) if i != na]
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (co[a] / tile, co[b] / tile)


# --------------------------------------------------------------------- lathe

def lathe(profile, segs, closed=True, sharp=40.0):
    """Revolve [(r, z), ...] about Z. r == 0 collapses to the axis."""
    bm = bmesh.new()
    rows = []
    for r, z in profile:
        if abs(r) < 1e-9:
            rows.append([bm.verts.new((0.0, 0.0, z))] * segs)
        else:
            rows.append([bm.verts.new((r * math.cos(2 * math.pi * s / segs),
                                       r * math.sin(2 * math.pi * s / segs), z)) for s in range(segs)])
    n = len(profile)
    for i in range(n if closed else n - 1):
        a, b = rows[i], rows[(i + 1) % n]
        for s in range(segs):
            t = (s + 1) % segs
            quad = []
            for v in (a[s], a[t], b[t], b[s]):
                if v not in quad:
                    quad.append(v)
            if len(quad) >= 3:
                bm.faces.new(quad)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for i, (r, z) in enumerate(profile):
        if abs(r) < 1e-9 or (not closed and i in (0, n - 1)):
            continue
        pr, nx = profile[(i - 1) % n], profile[(i + 1) % n]
        d1, d2 = (r - pr[0], z - pr[1]), (nx[0] - r, nx[1] - z)
        ang = math.degrees(abs(math.atan2(d1[0] * d2[1] - d1[1] * d2[0], d1[0] * d2[0] + d1[1] * d2[1])))
        if ang > sharp:
            for s in range(segs):
                e = bm.edges.get((rows[i][s], rows[i][(s + 1) % segs]))
                if e is not None and e.is_valid:
                    e.smooth = False
    return bm


def catmull(pts, per=6):
    q = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(q) - 2):
        p0, p1, p2, p3 = q[i - 1], q[i], q[i + 1], q[i + 2]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t +
                                    (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 +
                                    (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(q[-2])
    dedup = []
    for pt in out:
        if not dedup or abs(pt[0] - dedup[-1][0]) + abs(pt[1] - dedup[-1][1]) > 1e-6:
            dedup.append(pt)
    return dedup


def bowl_profile(r, h, wall=0.004, foot=0.35):
    """Closed (r, z) profile of a shallow bowl, z from 0 to h."""
    outer = [(0.0, 0.0), (r * foot, 0.0), (r * 0.6, h * 0.12), (r * 0.9, h * 0.5), (r, h)]
    inner = [(r - wall, h), (r * 0.88, h * 0.5 + wall), (r * 0.58, h * 0.12 + wall), (0.0, wall)]
    return outer + inner


# ----------------------------------------------------------------- props

def fruit_bowl(b, loc, mat_bowl, mat_fruit, mat_fruit2, r=0.17):
    """Ceramic bowl heaped with lemons and limes (cheap spheres)."""
    b.lathe("Bowl", bowl_profile(r, 0.075), mat_bowl, loc=loc, segs=24, sharp=60, uv_tile=0.3)
    lemons, limes = [], []
    for i in range(9):
        a = i * 2.4
        rr = 0.085 if i < 6 else 0.03 * (i - 6)
        z = loc[2] + 0.052 + (0.0 if i < 6 else 0.05)
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.036)
        for v in bm.verts:
            v.co.x *= 1.25
        bm.transform(Matrix.Translation((loc[0] + rr * math.cos(a), loc[1] + rr * math.sin(a), z)) @
                     Matrix.Rotation(a, 4, "Z"))
        (lemons if i % 3 else limes).append(bm)
    for tag, bms, mat in (("Lemons", lemons, mat_fruit), ("Limes", limes, mat_fruit2)):
        ob = common.mesh_object(f"{b.n}_{tag}", merged(bms), b.col, mat, b.root)
        planar_uv(ob, 0.3)


def stack_plates(b, name, loc, mat, r=0.13, count=6, step=0.016, segs=12):
    """A stack of plates or bowls as one lathed solid with a notch per piece."""
    prof = [(r * 0.72, 0.0)]                 # the foot ring sits on the shelf: no underside
    for i in range(count):
        z = i * step
        prof.append((r, z + step * 0.7))
        prof.append((r * 0.84, z + step))
    prof.append((r * 0.84, count * step + 0.004))
    prof.append((0.0, count * step + 0.004))
    ob = common.mesh_object(f"{b.n}_{name}", lathe(prof, segs, closed=False, sharp=50), b.col, mat, b.root)
    ob.location = loc
    planar_uv(ob, 0.3)
    return ob


def merged(parts_bm):
    """Merge a list of bmeshes into one."""
    out = bmesh.new()
    for tmp in parts_bm:
        vmap = {}
        for v in tmp.verts:
            vmap[v] = out.verts.new(v.co)
        for f in tmp.faces:
            try:
                out.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                pass
        tmp.free()
    bmesh.ops.recalc_face_normals(out, faces=out.faces[:])
    return out


def jars(b, name, x0, y, z, count, mat_glass, mat_lid, mat_fill, gap=0.115, seed=1, segs=8):
    """A row of storage jars (glass shell, filled lower part, lid), as three merged meshes."""
    rng = np.random.default_rng(seed)
    glass_bm, lid_bm, fill_bm = [], [], []
    for i in range(count):
        r = 0.04 + 0.008 * rng.integers(0, 3)
        h = 0.14 + 0.04 * rng.integers(0, 3)
        fill = h * float(rng.uniform(0.45, 0.9))
        move = Matrix.Translation((x0 + i * gap, y, z))
        gb = lathe([(r, 0), (r, h)], segs, closed=False, sharp=60)          # its top is under the lid
        gb.transform(move)
        glass_bm.append(gb)
        lb = lathe([(r + 0.001, h - 0.002), (r + 0.001, h + 0.015), (r - 0.003, h + 0.019), (0, h + 0.019)], segs,
                   closed=False, sharp=60)
        lb.transform(move)
        lid_bm.append(lb)
        fb = lathe([(r - 0.0035, 0.004), (r - 0.0035, fill), (0, fill)], segs, closed=False, sharp=60)
        fb.transform(move)
        fill_bm.append(fb)
    out = []
    for tag, parts, mat in (("Glass", glass_bm, mat_glass), ("Lids", lid_bm, mat_lid), ("Fill", fill_bm, mat_fill)):
        ob = common.mesh_object(f"{b.n}_{name}{tag}", merged(parts), b.col, mat, b.root)
        planar_uv(ob, 0.3)
        out.append(ob)
    return out


# --------------------------------------------------------------- cabinet fronts

class Fronts:
    """Lays out cabinet fronts (slab doors/drawers with 3 mm reveals) for a run that
    faces -Y. Fronts share the grain material; pulls are slim bronze bars."""

    def __init__(self, b, mat, pull_mat, yf, t=0.02, reveal=0.003):
        self.b, self.mat, self.pull, self.yf, self.t, self.g = b, mat, pull_mat, yf, t, reveal
        self.k = 0

    def _shift(self):
        self.k += 1
        return ((self.k * 0.37) % 1.0, (self.k * 0.23) % 1.0)

    def slab(self, name, x0, x1, z0, z1, bevel=0.0015):
        g = self.g
        w = x1 - x0 - g
        h = z1 - z0 - g
        return self.b.box(name, (w, self.t, h), ((x0 + x1) / 2, self.yf + self.t / 2, (z0 + z1) / 2),
                          self.mat, bevel=bevel, seg=1, shift=self._shift())

    def vbar(self, name, x, z0, z1, r=0.0065, stand=0.028):
        """Vertical bar pull."""
        ya, yb = self.yf, self.yf - stand
        pts = [(x, ya, z0), (x, yb, z0), (x, yb, z1), (x, ya, z1)]
        return self.b.tube(name, pts, r, self.pull, closed=False, res=3)

    def lip(self, name, x0, x1, z_top, depth=0.02):
        """Horizontal edge pull along the top of a drawer front."""
        w = x1 - x0 - self.g - 0.04
        return self.b.box(name, (w, depth, 0.014), ((x0 + x1) / 2, self.yf - depth / 2 + 0.002, z_top - 0.011),
                          self.pull, bevel=0.0015, seg=1, tile=0)

    def unit(self, kind, x0, x1, z0, z1, tag):
        """kind: 'd1' one door (hinge left), 'd2' double door, 'dr2', 'dr3' drawer stacks,
        'dr1' a single deep drawer."""
        w = x1 - x0
        if kind == "d2":
            xm = (x0 + x1) / 2
            self.slab(f"{tag}_DoorL", x0, xm, z0, z1)
            self.slab(f"{tag}_DoorR", xm, x1, z0, z1)
            if z1 - z0 > 1.2:
                zc = (z0 + z1) / 2
                self.vbar(f"{tag}_PullL", xm - 0.04, zc - 0.35, zc + 0.35)
                self.vbar(f"{tag}_PullR", xm + 0.04, zc - 0.35, zc + 0.35)
            else:
                self.lip(f"{tag}_LipL", x0, xm, z1)
                self.lip(f"{tag}_LipR", xm, x1, z1)
        elif kind == "d1":
            self.slab(f"{tag}_Door", x0, x1, z0, z1)
            if z1 - z0 > 1.2:
                zc = (z0 + z1) / 2
                self.vbar(f"{tag}_Pull", x1 - 0.05, zc - 0.35, zc + 0.35)
            else:
                self.lip(f"{tag}_Lip", x0, x1, z1)
        else:
            cuts = {"dr1": [1.0], "dr2": [0.45, 0.55], "dr3": [0.26, 0.37, 0.37]}[kind]
            tot = z1 - z0
            z = z1
            for i, f in enumerate(cuts):
                h = tot * f
                self.slab(f"{tag}_Drawer{i}", x0, x1, z - h, z)
                self.lip(f"{tag}_Lip{i}", x0, x1, z)
                z -= h


def span(x_start, units):
    """[(width, kind), ...] -> [(x0, x1, kind)] starting at x_start."""
    out, x = [], x_start
    for w, kind in units:
        out.append((x, x + w, kind))
        x += w
    return out


# ------------------------------------------------------------- worktops and sinks

def slab_with_holes(b, name, x0, x1, y0, y1, zc, t, holes, mat, bevel=0.003, seg=2, tile=1.5, world_uv=True,
                    bottom=True):
    """One worktop slab from x0..x1, y0..y1 (thickness t, centred on zc) with rectangular
    cut-outs `holes` [(xa, xb, ya, yb), ...]. One mesh, so the bevel only eases the real
    outer and cut-out edges (no grooves where separate slabs would butt). The slab is
    built from a grid of the hole lines; `bottom=False` leaves out the underside where
    the slab sits on cabinets (the overhang strip outside y0+0.03..y1 is kept)."""
    import bmesh as _bm
    xs = sorted({x0, x1, *[h[0] for h in holes], *[h[1] for h in holes]})
    ys = sorted({y0, y1, *[h[2] for h in holes], *[h[3] for h in holes]})

    def solid(i, j):
        cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
        return not any(h[0] < cx < h[1] and h[2] < cy < h[3] for h in holes)

    bm = _bm.new()
    vt, vb = {}, {}
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            vt[i, j] = bm.verts.new((x, y, zc + t / 2))
            vb[i, j] = bm.verts.new((x, y, zc - t / 2))
    cells = {(i, j) for i in range(len(xs) - 1) for j in range(len(ys) - 1) if solid(i, j)}
    for i, j in cells:
        bm.faces.new((vt[i, j], vt[i + 1, j], vt[i + 1, j + 1], vt[i, j + 1]))
        bm.faces.new((vb[i, j + 1], vb[i + 1, j + 1], vb[i + 1, j], vb[i, j]))
    # side walls on every grid edge that has a solid cell on one side only
    for i, j in cells:
        for (di, dj), (a, c) in (((0, -1), ((i, j), (i + 1, j))), ((1, 0), ((i + 1, j), (i + 1, j + 1))),
                                 ((0, 1), ((i + 1, j + 1), (i, j + 1))), ((-1, 0), ((i, j + 1), (i, j)))):
            if (i + di, j + dj) not in cells:
                bm.faces.new((vb[a], vb[c], vt[c], vt[a]))
    _bm.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    # merge the coplanar grid cells back into as few faces as possible (cleaner bevel)
    _bm.ops.dissolve_limit(bm, angle_limit=0.01, verts=bm.verts[:], edges=bm.edges[:])
    _bm.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = common.mesh_object(f"{b.n}_{name}", bm, b.col, mat, b.root, smooth=True)
    if bevel:
        common.add_bevel(ob, bevel, segments=seg)
    if tile:
        (world_box_uv if world_uv else common.box_uv)(ob, tile)
    return ob


def rounded_rect(cx, cy, hx, hy, r, z, k=3):
    """Points of a rounded rectangle (corner radius r, k segments per corner), CCW from +X."""
    pts = []
    for q, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        ox, oy = cx + sx * (hx - r), cy + sy * (hy - r)
        for i in range(k + 1):
            a = math.pi / 2 * (q + i / k)
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a), z))
    return pts


def undermount_sink(b, name, cx, cy, w, d, depth, z_top, mat, drain_mat, corner=0.035, drain=(0.0, 0.0)):
    """An undermount basin hung under a worktop cut-out of w x d: the lip flares from the
    square cut-out into tight rounded corners, straight walls, a coved floor falling to a
    drain (offset `drain` from the centre) with a strainer basket. Inner surface only
    (the outside is hidden in the cabinet). Returns the bowl object."""
    import bmesh as _bm
    k = 3
    hx, hy = w / 2, d / 2
    zb = z_top - depth
    dx, dy = cx + drain[0], cy + drain[1]
    loops = [
        rounded_rect(cx, cy, hx + 0.002, hy + 0.002, 0.003, z_top + 0.001, k),   # under the stone edge
        rounded_rect(cx, cy, hx - 0.004, hy - 0.004, corner, z_top - 0.012, k),
        rounded_rect(cx, cy, hx - 0.004, hy - 0.004, corner, zb + 0.022, k),
        rounded_rect(cx, cy, hx - 0.018, hy - 0.018, corner * 0.8, zb + 0.004, k),
    ]
    n = len(loops[0])
    ring = [(dx + 0.045 * math.cos(2 * math.pi * i / n + math.pi / 4 * 0), dy + 0.045 * math.sin(2 * math.pi * i / n), zb)
            for i in range(n)]
    hole = [(dx + 0.034 * math.cos(2 * math.pi * i / n), dy + 0.034 * math.sin(2 * math.pi * i / n), zb - 0.006)
            for i in range(n)]
    loops += [ring, hole]
    bm = _bm.new()
    rows = [[bm.verts.new(p) for p in lp] for lp in loops]
    for a, c in zip(rows[:-1], rows[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], c[j], c[i]))
    centre = Vector((cx, cy, z_top))
    for f in bm.faces:
        if f.normal.dot(centre - f.calc_center_median()) < 0:
            f.normal_flip()
    # sharp lip, sharp drain edge; the cove and corners stay smooth
    for ri in (1, 4):
        for i in range(n):
            e = bm.edges.get((rows[ri][i], rows[ri][(i + 1) % n]))
            if e:
                e.smooth = False
    bowl = common.mesh_object(f"{b.n}_{name}_Bowl", bm, b.col, mat, b.root, smooth=True)
    planar_uv(bowl, 0.5)
    # strainer basket: a polished cup with a flat grated top
    b.lathe(f"{name}_Strainer", [(0.0, zb - 0.004), (0.031, zb - 0.004), (0.033, zb - 0.0015), (0.0, zb - 0.0015)],
            drain_mat, loc=(dx, dy, 0), segs=16, sharp=30, uv_tile=0)
    return bowl


def gooseneck_tap(b, name, x, y, z, mat, reach=0.20, rise=0.40, lever=1, toward=-1, segs=16):
    """Deck-mounted gooseneck: a tapered base, a tube rising `rise` and arcing over by
    `reach` toward `toward` (-1 = -Y), a pull-down spray head with a darker face and a
    side lever with a round boss."""
    b.lathe(f"{name}_Base", [(0.0, z), (0.029, z), (0.029, z + 0.004), (0.022, z + 0.016), (0.0175, z + 0.05),
                             (0.0, z + 0.05)], mat, loc=(x, y, 0), segs=segs, sharp=30, uv_tile=0)
    R = reach / 2
    pts = [(x, y, z + 0.045), (x, y, z + rise)]
    for i in range(1, 15):
        a = math.pi * i / 14
        pts.append((x, y + toward * (R - R * math.cos(a)), z + rise + R * math.sin(a) * 0.9))
    pts.append((x, y + toward * 2 * R, z + rise - 0.03))
    b.tube(f"{name}_Spout", pts, 0.0115, mat, closed=False, res=3)
    hz = z + rise - 0.03
    b.lathe(f"{name}_Head", [(0.0, hz + 0.004), (0.0135, hz + 0.004), (0.0155, hz - 0.012), (0.0155, hz - 0.058),
                             (0.0125, hz - 0.064), (0.0, hz - 0.064)], mat, loc=(x, y + toward * 2 * R, 0),
            segs=12, sharp=30, uv_tile=0)
    # lever: boss on the base's side and a slim paddle sweeping back
    bx = x + lever * 0.024
    b.lathe(f"{name}_Boss", [(0.0, -0.001), (0.011, -0.001), (0.011, 0.018), (0.0085, 0.022), (0.0, 0.022)], mat,
            loc=(bx, y, z + 0.033), segs=12, sharp=30, uv_tile=0).rotation_euler = (0, math.radians(90 * lever), 0)
    b.box(f"{name}_Lever", (0.010, 0.075, 0.007), (bx + lever * 0.02, y - toward * 0.03, z + 0.038), mat,
          bevel=0.0025, seg=1, tile=0).rotation_euler = (math.radians(-12 * toward), 0, 0)


# ------------------------------------------------------------------- appliances

def hinge(b, tag, parts, pivot, interact):
    """Interactivity: hang an appliance door's meshes (`<n>_<tag>_<part>`) under an empty at its
    hinge line, carrying the `interact`; the geometry and the closed pose are unchanged."""
    e = common.empty(f"{b.n}_{tag}_Hinge", b.col, pivot)
    e.parent = b.root
    for ob in list(b.root.children):
        if ob.type == "MESH" and any(ob.name == f"{b.n}_{tag}_{k}" for k in parts):
            ob.parent = e
            ob.location = ob.location - e.location
    e["interact"] = interact
    return e


def oven_hinge(b, tag, xm, y_front, z_bottom, parts=("Door", "Window", "Band", "Display_NoCollide", "Handle")):
    """A built-in oven door (oven_door's parts) that drops open on its bottom front edge."""
    return hinge(b, tag, parts, (xm, y_front, z_bottom), {
        "type": "rotate", "axis": common.to_gltf((1, 0, 0)), "angle": 85, "duration": 0.7, "range": 1.5,
        "side": "both", "collide": True, "prompt": "Open oven", "promptActive": "Close oven"})


def bottle_profile(kind):
    """(r, z) lathe profiles: a wine bottle, a squat water bottle, a milk bottle."""
    return {
        "wine": [(0.0, 0.0), (0.036, 0.0), (0.037, 0.008), (0.037, 0.2), (0.03, 0.235), (0.014, 0.262),
                 (0.013, 0.30), (0.015, 0.305), (0.0, 0.305)],
        "water": [(0.0, 0.0), (0.04, 0.0), (0.041, 0.008), (0.041, 0.17), (0.03, 0.205), (0.016, 0.22),
                  (0.016, 0.24), (0.0, 0.24)],
        "milk": [(0.0, 0.0), (0.042, 0.0), (0.043, 0.008), (0.043, 0.15), (0.03, 0.185), (0.022, 0.2),
                 (0.022, 0.215), (0.0, 0.215)],
    }[kind]


def fridge_interior(b, tag, xa, xb, za, zb, y0, depth, contents, seed=1):
    """The inside of a fridge column seen with the door open: an open white liner box (inner
    faces) from y0 back by `depth`, a glowing back panel, glass shelves with steel front trims,
    a frosted crisper drawer at the bottom, and a few bottles, jars and containers on the
    shelves (`contents`: one list per shelf of (kind, x offset from the left wall)). Everything
    but the liner is NoCollide. Returns the shelf heights."""
    rng = np.random.default_rng(seed)
    liner = common.pbr_material("M_Fridge_Liner", (0.80, 0.81, 0.82), roughness=0.3)
    light = materials.emissive("M_Fridge_Light", (0.90, 0.95, 1.0), 0.9)
    shelf = materials.glass("M_Glass_Shelf", (0.85, 0.93, 0.92), 0.22, roughness=0.05)
    frost = materials.glass("M_Glass_Frosted", (0.88, 0.92, 0.92), 0.55, roughness=0.35)
    trim = materials.steel()
    oven_cavity(b, tag, xa, xb, za, zb, y0, depth, liner, trim, racks=0)
    w, xm, yb = xb - xa, (xa + xb) / 2, y0 + depth
    b.box(f"{tag}_FridgeLight_NoCollide", (w - 0.16, 0.004, zb - za - 0.5), (xm, yb - 0.003, (za + zb) / 2 + 0.1),
          light, bevel=0, tile=0)
    # crisper drawer: frosted front and lid over the bottom 0.34 m
    zc = za + 0.34
    b.box(f"{tag}_Crisper_NoCollide", (w - 0.02, 0.01, 0.30), (xm, y0 + 0.03, za + 0.16), frost, bevel=0.002, tile=0)
    b.box(f"{tag}_CrisperLid_NoCollide", (w - 0.01, depth - 0.05, 0.006), (xm, y0 + 0.025 + (depth - 0.05) / 2, zc),
          shelf, bevel=0, tile=0)
    levels = [zc + (zb - 0.1 - zc) * (k + 1) / (len(contents)) for k in range(len(contents) - 1)]
    shelf_z = [zc] + levels
    for k, z in enumerate(levels):
        b.box(f"{tag}_Shelf{k}_NoCollide", (w - 0.01, depth - 0.07, 0.006), (xm, y0 + 0.05 + (depth - 0.07) / 2, z),
              shelf, bevel=0, tile=0)
        b.box(f"{tag}_ShelfTrim{k}_NoCollide", (w - 0.01, 0.01, 0.022), (xm, y0 + 0.05, z - 0.004), trim, bevel=0.002,
              tile=0)
    green = materials.glass("M_Glass_Olive", (0.2, 0.28, 0.1), 0.55)
    clear = materials.glass("M_Glass_Jar", (0.9, 0.95, 0.92), 0.25)
    milk = common.pbr_material("M_Fridge_Milk", (0.82, 0.82, 0.80), roughness=0.4)
    tub = common.pbr_material("M_Fridge_Tub", (0.72, 0.70, 0.64), roughness=0.5)
    lid = common.pbr_material("M_Fridge_Lid", (0.10, 0.22, 0.32), roughness=0.5)
    fills = [common.pbr_material("M_Fridge_Juice", (0.70, 0.32, 0.03), roughness=0.3),
             common.pbr_material("M_Fridge_Jam", (0.32, 0.03, 0.04), roughness=0.3)]
    groups = {}
    for k, row in enumerate(contents):
        z = shelf_z[k] + 0.003
        for kind, dx in row:
            x, y = xa + dx, y0 + 0.16 + float(rng.uniform(-0.04, 0.06))
            if kind in ("wine", "water", "milk"):
                bm = lathe(bottle_profile(kind), 12, closed=False, sharp=50)
                bmesh.ops.translate(bm, vec=(x, y, z), verts=bm.verts)
                groups.setdefault({"wine": green, "water": clear, "milk": milk}[kind], []).append(bm)
            elif kind == "tub":                    # a lidded food container
                for mat, (h0, h1, r) in ((tub, (0.0, 0.09, 0.0)), (lid, (0.09, 0.105, 0.004))):
                    bm = common.box_bmesh((0.17 + r, 0.12 + r, h1 - h0))
                    bmesh.ops.translate(bm, vec=(x, y + 0.05, z + (h0 + h1) / 2), verts=bm.verts)
                    groups.setdefault(mat, []).append(bm)
            elif kind == "jars":
                jars(b, f"{tag}_Jars{k}_NoCollide_", x, y, z, 3, clear, trim, fills[k % 2], gap=0.1, seed=seed + k)
    for i, (mat, bms) in enumerate(groups.items()):
        ob = common.mesh_object(f"{b.n}_{tag}_Contents{i}_NoCollide", merged(bms), b.col, mat, b.root)
        planar_uv(ob, 0.3)
    return shelf_z


def oven_glass():
    """Smoked oven-door glass: dark, but the lit cavity and racks read through it."""
    return materials.glass("M_Glass_Oven", tint=(0.03, 0.03, 0.035), alpha=0.6, roughness=0.04)


def panel_with_holes(b, name, x0, x1, z0, z1, y_front, t, holes, mat, bevel=0.002, seg=1):
    """A vertical panel in the XZ plane (front face at y_front, t deep toward +Y) with
    rectangular openings `holes` [(xa, xb, za, zb)]: slab_with_holes stood up."""
    ob = slab_with_holes(b, name, x0, x1, z0, z1, -(y_front + t / 2), t, holes, mat, bevel=bevel, seg=seg, tile=0)
    ob.rotation_euler = (math.pi / 2, 0, 0)
    return ob


def oven_cavity(b, tag, xa, xb, za, zb, y0, depth, mat, rack_mat, racks=2):
    """The inside of an oven seen through its door: an open enamel box (inner faces only)
    from y0 back by `depth`, with wire shelves on side runners."""
    import bmesh as _bm
    bm = _bm.new()
    y1 = y0 + depth
    c = [bm.verts.new(v) for v in ((xa, y0, za), (xb, y0, za), (xb, y1, za), (xa, y1, za),
                                    (xa, y0, zb), (xb, y0, zb), (xb, y1, zb), (xa, y1, zb))]
    for q in ((0, 1, 2, 3), (7, 6, 5, 4), (3, 2, 6, 7), (0, 3, 7, 4), (2, 1, 5, 6)):
        bm.faces.new([c[i] for i in q])
    centre = Vector(((xa + xb) / 2, (y0 + y1) / 2, (za + zb) / 2))
    for f in bm.faces:
        if f.normal.dot(centre - f.calc_center_median()) < 0:
            f.normal_flip()
    ob = common.mesh_object(f"{b.n}_{tag}_Cavity", bm, b.col, mat, b.root, smooth=False)
    planar_uv(ob, 0.5)
    w, h = xb - xa, zb - za
    for r in range(racks):
        z = za + h * (r + 1) / (racks + 1)
        b.box(f"{tag}_Rack{r}_NoCollide", (w - 0.01, 0.006, 0.006), ((xa + xb) / 2, y0 + 0.03, z), rack_mat, bevel=0, tile=0)
        for k in range(4):
            x = xa + 0.02 + k * (w - 0.04) / 3
            b.box(f"{tag}_Rack{r}_{k}_NoCollide", (0.005, depth - 0.06, 0.005), (x, y0 + depth / 2, z), rack_mat,
                  bevel=0, tile=0)
    return ob


def oven_door(b, tag, x0, x1, z0, z1, yf, frame_mat, glass_mat, band_mat, display_mat, handle_mat,
              band=0.075, side=0.05, bottom=0.05, t=0.022, handle=True, cavity_mat=None, rack_mat=None,
              depth=0.40, display=True):
    """A built-in oven/steam-oven door (front face at yf, t deep): a steel frame round a
    smoked window, a black-glass control band with a small warm display along the top, a
    steel bar handle on standoffs and (with cavity_mat) the lit cavity behind the window."""
    xa, xb, za, zb = x0 + side, x1 - side, z0 + bottom, z1 - band
    panel_with_holes(b, f"{tag}_Door", x0, x1, z0, z1, yf, t, [(xa, xb, za, zb)], frame_mat, bevel=0.0025, seg=1)
    b.box(f"{tag}_Window", (xb - xa + 0.012, 0.005, zb - za + 0.012), ((xa + xb) / 2, yf + 0.008, (za + zb) / 2),
          glass_mat, bevel=0, tile=0)
    b.box(f"{tag}_Band", (x1 - x0 - 0.024, 0.004, band - 0.022), ((x0 + x1) / 2, yf - 0.0015, z1 - band / 2 - 0.004),
          band_mat, bevel=0.001, tile=0)
    if display:
        b.box(f"{tag}_Display_NoCollide", (0.07, 0.002, 0.016), ((x0 + x1) / 2, yf - 0.0035, z1 - band / 2 - 0.004),
              display_mat, bevel=0, tile=0)
    if handle:
        zh = z1 - band - 0.035
        hx0, hx1 = x0 + 0.06, x1 - 0.06
        pts = [(hx0, yf, zh), (hx0, yf - 0.045, zh), (hx1, yf - 0.045, zh), (hx1, yf, zh)]
        b.tube(f"{tag}_Handle", common.fillet_polyline(pts, 0.012, segments=3, closed=False), 0.008, handle_mat,
               closed=False, res=2)
    if cavity_mat is not None:
        oven_cavity(b, tag, xa - 0.004, xb + 0.004, za - 0.004, zb + 0.004, yf + t, depth, cavity_mat, rack_mat)
    return xa, xb, za, zb


def folded_stack(b, name, x, y, z, w, d, n, t, mat, tile=0.25):
    """A stack of n folded cloths (each t thick, w along x, d deep) as one extruded profile:
    each fold bulges round at the front (-Y) with a tucked crease between folds, the back
    is flat against the shelf's back. One mesh, ~4n + 8 triangles per side."""
    import bmesh as _bm
    prof = [(y + d / 2, z), (y - d / 2 + t * 0.5, z)]          # (y, z) round the section, start back-bottom
    for i in range(n):
        z0 = z + i * t
        prof += [(y - d / 2 + t * 0.12, z0 + t * 0.18), (y - d / 2, z0 + t * 0.5),
                 (y - d / 2 + t * 0.12, z0 + t * 0.82), (y - d / 2 + t * 0.45, z0 + t)]
    prof[-1] = (y - d / 2 + t * 0.5, z + n * t)
    prof.append((y + d / 2, z + n * t))
    bm = _bm.new()
    l = [bm.verts.new((x - w / 2, py, pz)) for py, pz in prof]
    r = [bm.verts.new((x + w / 2, py, pz)) for py, pz in prof]
    m = len(prof)
    for i in range(m):
        j = (i + 1) % m
        f = bm.faces.new((l[i], l[j], r[j], r[i]))
    bm.faces.new(l[::-1])
    bm.faces.new(r)
    _bm.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for e in bm.edges:            # hard edges round the flat ends and the back; folds stay soft
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(50):
            e.smooth = False
    ob = common.mesh_object(f"{b.n}_{name}", bm, b.col, mat, b.root, smooth=True)
    common.box_uv(ob, tile)
    return ob


def cylindrical_uv(ob, tile, cx=0.0, cy=0.0):
    """UVs for a lathed solid: u round the circumference (in metres, so the tile scale is
    true), v up the axis. No seams twisting across faces the way a box projection does
    on a round surface; flat caps get a planar projection."""
    me = ob.data
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        if abs(poly.normal.z) > 0.95:
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                uv.data[li].uv = ((co.x - cx) / tile, (co.y - cy) / tile)
            continue
        angs = [math.atan2(me.vertices[me.loops[li].vertex_index].co.y - cy,
                           me.vertices[me.loops[li].vertex_index].co.x - cx) for li in poly.loop_indices]
        a0 = angs[0]
        for li, a in zip(poly.loop_indices, angs):
            d = a - a0
            d -= 2 * math.pi * round(d / (2 * math.pi))
            co = me.vertices[me.loops[li].vertex_index].co
            r = math.hypot(co.x - cx, co.y - cy)
            uv.data[li].uv = ((a0 + d) * max(r, 0.05) / tile, co.z / tile)


def cushion_welt(b, name, size, loc, inset=0.0042, corner=0.03, radius=0.0042, mat=None, face="+z"):
    """Piped welt round the top (or bottom, face='-z') edge of a subdivided cushion of
    `size` centred at `loc`: a thin closed 4-sided tube (reads round when smooth-shaded)."""
    sgn = 1 if face[0] == "+" else -1
    hx, hy = size[0] / 2 - inset, size[1] / 2 - inset
    z = sgn * (size[2] / 2 - inset)
    rect = [(-hx, -hy, z), (hx, -hy, z), (hx, hy, z), (-hx, hy, z)]
    pts = common.fillet_polyline(rect, corner, segments=3, closed=True)
    ob = b.tube(name, [tuple(p) for p in pts], radius, mat, closed=True, res=1)
    ob.location = loc
    return ob
