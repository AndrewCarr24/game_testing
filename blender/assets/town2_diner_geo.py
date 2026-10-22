"""Geometry kit for the diner (town2_diner*.py): bmesh primitives built straight in the asset
frame (metres, z up, origin at the lot's floor centre, front -Y) and a Parts registry that turns
them into mesh objects with world-scale UVs, a linear vertex tint ("Col", multiplied into the
material's base colour by the engine as COLOR_0), a lightmap density weight and collider tags.

Every part is merged per material at export (blender/town/diner/build.py), so a part costs no
draw call of its own: tint and UV scale are how one material covers many surfaces.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

TINT = "Col"


# ------------------------------------------------------------------ primitives (bmesh)

def _bevel(bm, width, segments=1, edges=None):
    if width <= 0:
        return bm
    es = edges if edges is not None else bm.edges[:]
    bmesh.ops.bevel(bm, geom=es, offset=width, offset_type="OFFSET", segments=segments,
                    profile=0.5, affect="EDGES", clamp_overlap=True)
    return bm


def box(c, size, bevel=0.0, seg=1):
    """Axis-aligned box centred at c with full size (sx, sy, sz); optional bevel on every edge."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(c), verts=bm.verts)
    b = min(bevel, min(size) * 0.45)
    return _bevel(bm, b, seg)


def box_lohi(lo, hi, bevel=0.0, seg=1):
    c = [(a + b) / 2 for a, b in zip(lo, hi)]
    s = [abs(b - a) for a, b in zip(lo, hi)]
    return box(c, s, bevel, seg)


def cyl(c, r, h, n=16, axis="z", bevel=0.0, seg=1, cap=True, r2=None):
    """Cylinder (or cone frustum with r2) centred at c along axis."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=n, radius1=r,
                          radius2=r if r2 is None else r2, depth=h)
    if bevel > 0:
        rings = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-6]
        _bevel(bm, min(bevel, h * 0.45, r * 0.45), seg, rings)
    rot = {"z": Matrix(), "x": Matrix.Rotation(math.pi / 2, 4, "Y"), "y": Matrix.Rotation(math.pi / 2, 4, "X")}[axis]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ rot, verts=bm.verts)
    return bm


def lathe(profile, c=(0, 0, 0), n=24, cap_bottom=False, cap_top=False, angle=2 * math.pi):
    """Surface of revolution about the z axis through c: profile = [(r, z), ...] bottom to top."""
    bm = bmesh.new()
    full = abs(angle - 2 * math.pi) < 1e-6
    steps = n if full else n + 1
    rings = []
    for k in range(steps):
        a = angle * k / n
        ca, sa = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((c[0] + r * ca, c[1] + r * sa, c[2] + z)) for r, z in profile])
    for k in range(n):
        r0, r1 = rings[k], rings[(k + 1) % steps]
        for i in range(len(profile) - 1):
            quad = [r0[i], r1[i], r1[i + 1], r0[i + 1]]
            if profile[i][0] < 1e-6 and profile[i + 1][0] < 1e-6:
                continue
            try:
                bm.faces.new(quad)
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    if full:
        if cap_bottom and profile[0][0] > 1e-6:
            ring = [rr[0] for rr in rings]
            bm.faces.new(ring[::-1])
        if cap_top and profile[-1][0] > 1e-6:
            ring = [rr[-1] for rr in rings]
            bm.faces.new(ring)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def prism(poly, z0, z1, bevel=0.0, seg=1):
    """A vertical prism: polygon [(x, y), ...] (CCW) extruded from z0 to z1."""
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, z0)) for x, y in poly]
    f = bm.faces.new(vs[::-1])
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    top = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, z1 - z0), verts=top)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if bevel > 0:
        _bevel(bm, bevel, seg)
    return bm


def sweep(profile, x0, x1, axis="x", bevel=0.0, seg=1, cap=True):
    """A profile [(u, v), ...] (closed polygon in the plane across `axis`) swept from x0 to x1.
    axis x: profile is (y, z); axis y: (x, z); axis z: (x, y)."""
    bm = bmesh.new()

    def P(u, v, t):
        return {"x": (t, u, v), "y": (u, t, v), "z": (u, v, t)}[axis]
    a = [bm.verts.new(P(u, v, x0)) for u, v in profile]
    b = [bm.verts.new(P(u, v, x1)) for u, v in profile]
    n = len(profile)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([a[i], a[j], b[j], b[i]])
    if cap:
        bm.faces.new(a[::-1])
        bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if bevel > 0:
        _bevel(bm, bevel, seg)
    return bm


def open_sweep(profile, x0, x1, axis="x"):
    """An open polyline profile swept (a strip surface, e.g. a vault)."""
    bm = bmesh.new()

    def P(u, v, t):
        return {"x": (t, u, v), "y": (u, t, v), "z": (u, v, t)}[axis]
    a = [bm.verts.new(P(u, v, x0)) for u, v in profile]
    b = [bm.verts.new(P(u, v, x1)) for u, v in profile]
    for i in range(len(profile) - 1):
        bm.faces.new([a[i], a[i + 1], b[i + 1], b[i]])
    return bm


def quad(p0, p1, p2, p3):
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(p) for p in (p0, p1, p2, p3)])
    return bm


def tube(points, r, n=8, closed=False, cap=True):
    """A round tube along a polyline (parallel-transport frames)."""
    pts = [Vector(p) for p in points]
    bm = bmesh.new()
    rings = []
    m = len(pts)
    prev_n = None
    for i in range(m):
        if closed:
            t = (pts[(i + 1) % m] - pts[i - 1]).normalized()
        else:
            t = (pts[min(i + 1, m - 1)] - pts[max(i - 1, 0)]).normalized()
        if prev_n is None:
            ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            nrm = t.cross(ref).normalized()
        else:
            nrm = (prev_n - t * prev_n.dot(t)).normalized()
        prev_n = nrm
        bi = t.cross(nrm)
        rings.append([bm.verts.new(pts[i] + (nrm * math.cos(2 * math.pi * k / n) + bi * math.sin(2 * math.pi * k / n)) * r)
                      for k in range(n)])
    segs = m if closed else m - 1
    for i in range(segs):
        a, b = rings[i], rings[(i + 1) % m]
        for k in range(n):
            bm.faces.new([a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]])
    if cap and not closed:
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def arc_pts(c, r, a0, a1, n, z=None, plane="xy"):
    out = []
    for k in range(n + 1):
        a = a0 + (a1 - a0) * k / n
        if plane == "xy":
            out.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a), c[2] if z is None else z))
        elif plane == "xz":
            out.append((c[0] + r * math.cos(a), c[1], c[2] + r * math.sin(a)))
        else:
            out.append((c[0], c[1] + r * math.cos(a), c[2] + r * math.sin(a)))
    return out


def rounded_rect(x0, y0, x1, y1, r, n=6):
    """CCW outline of a rounded rectangle."""
    r = min(r, (x1 - x0) / 2 - 1e-4, (y1 - y0) / 2 - 1e-4)
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, math.pi / 2), (x0 + r, y0 + r, math.pi)):
        for k in range(n + 1):
            a = a0 + (math.pi / 2) * k / n
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def text(s, size, depth, c=(0, 0, 0), rot=(math.pi / 2, 0, 0), align="CENTER", font=None, bevel=0.0, spacing=1.0):
    """Block letters: a Blender text object converted to a bmesh (Bfont unless font)."""
    cu = bpy.data.curves.new("_txt", "FONT")
    cu.body = s
    cu.size = size
    cu.extrude = depth / 2
    cu.bevel_depth = bevel
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.space_character = spacing
    if font:
        cu.font = font
    ob = bpy.data.objects.new("_txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.curves.remove(cu)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y") @ Matrix.Rotation(rot[0], 4, "X"),
                        verts=bm.verts)
    return bm


def xform(bm, loc=(0, 0, 0), rz=0.0, rx=0.0, ry=0.0, scale=None):
    """Transform a bmesh in place: scale, rotate (x, y, then z) and move. Returns bm."""
    M = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(rz, 4, "Z") @ Matrix.Rotation(ry, 4, "Y") @ Matrix.Rotation(rx, 4, "X")
    if scale is not None:
        s = scale if isinstance(scale, (tuple, list)) else (scale,) * 3
        M = M @ Matrix.Diagonal((*s, 1.0))
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    return bm


def join(*bms):
    """Concatenate bmeshes into the first (the others are freed)."""
    out = bms[0]
    for b in bms[1:]:
        me = bpy.data.meshes.new("_j")
        b.to_mesh(me)
        out.from_mesh(me)
        bpy.data.meshes.remove(me)
        b.free()
    return out


def mirror_x(bm, x=0.0, keep=True):
    """Mirror across the plane x = x (a copy added when keep)."""
    me = bpy.data.meshes.new("_m")
    bm.to_mesh(me)
    b2 = bmesh.new()
    b2.from_mesh(me)
    bpy.data.meshes.remove(me)
    bmesh.ops.transform(b2, matrix=Matrix.Translation((x, 0, 0)) @ Matrix.Diagonal((-1, 1, 1, 1)) @ Matrix.Translation((-x, 0, 0)), verts=b2.verts)
    bmesh.ops.reverse_faces(b2, faces=b2.faces[:])
    if keep:
        return join(bm, b2)
    bm.free()
    return b2


# ------------------------------------------------------------------ parts registry

class Parts:
    """Mesh parts of the asset. add() makes an object from a bmesh (already in the asset
    frame), with:
      tint     linear RGB vertex tint (COLOR_0 x the material's base colour), default white
      tile     metres per UV unit for the box-projected material UVs (None: leave bm's UVs)
      lm       lightmap texel-density weight (1 = the building's norm; 0.4 = far, flat exterior)
      collide  True: its world AABB becomes a collider (or pass a list of boxes explicitly
               with collider())
      smooth   shade smooth (curved parts) with an auto-smooth angle
      bake     False: hidden in the bake (glass, the bulbs' shades), not lightmapped
      zone     "in" / "out": which half of the lightmap atlas (default: by the interior boxes)
    """

    def __init__(self, col, root):
        self.col, self.root = col, root
        self.objects = []
        self.colliders = []          # (x0, y0, z0, x1, y1, z1) in the asset frame
        self.lights = []             # bake lights: dict(kind, loc, ...)
        self.entrances = []
        self.inside = []             # interior volumes (lo, hi): parts centred in them bake into the interior half
        self.cameras = {}            # preview cameras: name -> (location, look-at, lens mm)
        self.count = {}

    def add(self, name, bm, mat, tint=None, tile=1.0, lm=1.0, collide=False, smooth=False, bake=True, lod=0, uv_rot=False,
            zone=None):
        k = self.count.get(name, 0)
        self.count[name] = k + 1
        nm = name if k == 0 else f"{name}.{k:03d}"
        bm.normal_update()
        if tile is not None or not bm.loops.layers.uv:
            _box_uv(bm, tile or 1.0, uv_rot)
        if smooth:
            # smooth shading, hard edges over the angle (a float: 30 deg default)
            lim = math.radians(55 if smooth is True else smooth)
            for f in bm.faces:
                f.smooth = True
            for e in bm.edges:
                if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
                    e.smooth = False
        me = bpy.data.meshes.new(nm)
        bm.to_mesh(me)
        bm.free()
        if mat is not None:
            me.materials.append(mat)
        attr = me.color_attributes.new(TINT, "FLOAT_COLOR", "CORNER")
        t = tuple(tint) if tint is not None else (1.0, 1.0, 1.0)
        rgba = (*t[:3], 1.0)
        attr.data.foreach_set("color", rgba * len(me.loops))
        ob = bpy.data.objects.new(nm, me)
        self.col.objects.link(ob)
        ob.parent = self.root
        ob["lm"] = float(lm)
        ob["bake"] = bool(bake)
        ob["lod"] = int(lod)
        if zone is None:
            # inside (the interior's lightmap half) when the part's centre is in an interior box
            cx = sum(v.co.x for v in me.vertices) / max(1, len(me.vertices))
            cy = sum(v.co.y for v in me.vertices) / max(1, len(me.vertices))
            cz = sum(v.co.z for v in me.vertices) / max(1, len(me.vertices))
            zone = "in" if any(a[0] <= cx <= b[0] and a[1] <= cy <= b[1] and a[2] <= cz <= b[2] for a, b in self.inside) else "out"
        ob["zone"] = zone
        if collide:
            self.collider_of(me)
        self.objects.append(ob)
        return ob

    def collider_of(self, me):
        xs = [v.co.x for v in me.vertices]
        ys = [v.co.y for v in me.vertices]
        zs = [v.co.z for v in me.vertices]
        self.colliders.append((min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)))

    def collider(self, lo, hi):
        self.colliders.append((min(lo[0], hi[0]), min(lo[1], hi[1]), min(lo[2], hi[2]),
                               max(lo[0], hi[0]), max(lo[1], hi[1]), max(lo[2], hi[2])))

    def light(self, **kw):
        self.lights.append(kw)


def _box_uv(bm, tile, rot=False):
    """World-scale box projection on every face (1 UV unit = tile metres)."""
    uv = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        n = f.normal
        an = [abs(n.x), abs(n.y), abs(n.z)]
        na = an.index(max(an))
        a, b = [(1, 2), (0, 2), (0, 1)][na]
        if rot:
            a, b = b, a
        for l in f.loops:
            co = l.vert.co
            l[uv].uv = (co[a] / tile, co[b] / tile)


# ------------------------------------------------------------------ plan paths

def rrect_path(x0, y0, x1, y1, r, n=6, start="bw", closed=False):
    """A rounded rectangle's outline as a CCW path of (x, y). start "bw": open, from the back
    (y1) west end round the west side, the front (y0) and the east side to the back east end
    (the diner car's skin: its back is under the annex); "loop": the closed outline."""
    pts = []

    def corner(cx, cy, a0):
        for k in range(n + 1):
            a = a0 + (math.pi / 2) * k / n
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    if start == "bw":
        corner(x0 + r, y1 - r, math.pi / 2)        # NW: from north to west
        corner(x0 + r, y0 + r, math.pi)            # SW
        corner(x1 - r, y0 + r, -math.pi / 2)       # SE
        corner(x1 - r, y1 - r, 0.0)                # NE: from east to north
        return pts
    corner(x1 - r, y0 + r, -math.pi / 2)
    corner(x1 - r, y1 - r, 0.0)
    corner(x0 + r, y1 - r, math.pi / 2)
    corner(x0 + r, y0 + r, math.pi)
    return pts


def path_normals(path, closed):
    """Outward normals (to the right of travel for a CCW path) at each path point (averaged)."""
    out = []
    m = len(path)
    for i in range(m):
        if closed:
            a, b = path[i - 1], path[(i + 1) % m]
        else:
            a, b = path[max(i - 1, 0)], path[min(i + 1, m - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(tx, ty) or 1.0
        out.append((ty / ln, -tx / ln))
    return out


def path_sweep(path, profile, closed=False, z0=0.0, cap=False):
    """A profile [(offset outward, z), ...] (bottom to top) swept along a plan path: mouldings,
    flutes, bands round the car. Faces point outward when the profile runs upward."""
    bm = bmesh.new()
    ns = path_normals(path, closed)
    grid = []
    for (x, y), (nx, ny) in zip(path, ns):
        grid.append([bm.verts.new((x + nx * o, y + ny * o, z0 + z)) for o, z in profile])
    segs = len(path) if closed else len(path) - 1
    for i in range(segs):
        a, b = grid[i], grid[(i + 1) % len(path)]
        for j in range(len(profile) - 1):
            bm.faces.new([a[j], b[j], b[j + 1], a[j + 1]])
    if cap and not closed:
        for g, rev in ((grid[0], True), (grid[-1], False)):
            if len(g) > 2:
                try:
                    bm.faces.new(g[::-1] if rev else g)
                except ValueError:
                    pass
    return bm


def flute_profile(z0, z1, pitch=0.045, depth=0.008, base=0.0):
    """Horizontal flutes (the stainless skirt): rounded ridges every `pitch` from z0 to z1."""
    n = max(1, int(round((z1 - z0) / pitch)))
    pr = []
    for k in range(n):
        za = z0 + (z1 - z0) * k / n
        zb = z0 + (z1 - z0) * (k + 1) / n
        for t in (0.0, 0.2, 0.5, 0.8):
            z = za + (zb - za) * t
            pr.append((base + depth * math.sin(math.pi * t) ** 0.7, z))
    pr.append((base, z1))
    return pr


def path_point(path, s):
    """Point and unit tangent at arc length s along an open path."""
    acc = 0.0
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        ln = math.hypot(b[0] - a[0], b[1] - a[1])
        if acc + ln >= s or i == len(path) - 2:
            t = min(1.0, max(0.0, (s - acc) / (ln or 1)))
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), ((b[0] - a[0]) / (ln or 1), (b[1] - a[1]) / (ln or 1))
        acc += ln
    return path[-1], (1.0, 0.0)


def path_length(path):
    return sum(math.hypot(path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1]) for i in range(len(path) - 1))


def neon_text(s, size, tube, c=(0, 0, 0), rot=(math.pi / 2, 0, 0), align="CENTER", font=None, spacing=1.0):
    """Outline neon: a tube along every glyph outline (a text curve with no fill, bevelled)."""
    cu = bpy.data.curves.new("_neon", "FONT")
    cu.body = s
    cu.size = size
    cu.fill_mode = "NONE"
    cu.bevel_depth = tube
    cu.bevel_resolution = 1
    cu.resolution_u = 4
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.space_character = spacing
    if font:
        cu.font = font
    ob = bpy.data.objects.new("_neon", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.curves.remove(cu)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y") @ Matrix.Rotation(rot[0], 4, "X"),
                        verts=bm.verts)
    return bm


def decal(p0, p1, p2, p3, region, uvs=((0, 0), (1, 0), (1, 1), (0, 1))):
    """A quad (bottom-left, bottom-right, top-right, top-left) mapped onto a decal atlas region."""
    import town2_diner_decals as D
    bm = bmesh.new()
    f = bm.faces.new([bm.verts.new(p) for p in (p0, p1, p2, p3)])
    lay = bm.loops.layers.uv.new("UVMap")
    for l, (u, v) in zip(f.loops, uvs):
        l[lay].uv = D.uv(region, u, v)
    return bm


def decal_disc(c, r, region, n=20, axis="z", flip=False):
    """A disc facing +axis (or -axis with flip) mapped onto a round decal region (pies, clocks)."""
    import town2_diner_decals as D
    bm = bmesh.new()
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        ca, sa = math.cos(a), math.sin(a)
        if axis == "z":
            pts.append(((c[0] + r * ca, c[1] + r * sa, c[2]), (0.5 + 0.5 * ca, 0.5 + 0.5 * sa)))
        elif axis == "y":       # facing -y (a wall clock seen from -y): u along +x
            pts.append(((c[0] + r * ca, c[1], c[2] + r * sa), (0.5 + 0.5 * ca, 0.5 + 0.5 * sa)))
        else:                   # facing +x: u along -y... (seen from +x, u to the viewer's right = -y)
            pts.append(((c[0], c[1] - r * ca, c[2] + r * sa), (0.5 + 0.5 * ca, 0.5 + 0.5 * sa)))
    vs = [bm.verts.new(p) for p, _ in pts]
    if flip:
        vs, pts = vs[::-1], pts[::-1]
    f = bm.faces.new(vs)
    lay = bm.loops.layers.uv.new("UVMap")
    for l, (_, (u, v)) in zip(f.loops, pts):
        l[lay].uv = D.uv(region, u, v)
    return bm
