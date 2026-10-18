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
    m = common.pbr_material("M_Kitchen_Stone", (0.4, 0.36, 0.30), roughness=0.5)
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

    def lathe(self, name, profile, mat, loc=(0, 0, 0), segs=32, sharp=40.0, uv_tile=0.5, parent=None):
        bm = lathe(profile, segs, sharp=sharp)
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
    prof = [(0.0, 0.0), (r * 0.72, 0.0)]
    for i in range(count):
        z = i * step
        prof.append((r, z + step * 0.7))
        prof.append((r * 0.84, z + step))
    prof.append((r * 0.84, count * step + 0.004))
    prof.append((0.0, count * step + 0.004))
    ob = common.mesh_object(f"{b.n}_{name}", lathe(prof, segs, sharp=50), b.col, mat, b.root)
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
        gb = lathe([(r, 0), (r, h), (0, h)], segs, closed=False, sharp=60)
        gb.transform(move)
        glass_bm.append(gb)
        lb = lathe([(r + 0.001, h), (r + 0.001, h + 0.018), (0, h + 0.018)], segs, closed=False, sharp=60)
        lb.transform(move)
        lid_bm.append(lb)
        fb = lathe([(0, 0.004), (r - 0.0035, 0.004), (r - 0.0035, fill), (0, fill)], segs, closed=False, sharp=60)
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
