"""Armory emergency power and air wall: three white wall-hung battery units (each with a cold LED line),
a graphite transfer-switch cabinet with a big red rotary handle, grey conduit running over the batteries
and up into the ceiling, and an NBC air-filtration unit (white steel cabinet, two gauges, hand crank,
a ribbed flexible duct up to a ceiling blast valve). Fixed set dressing, about 3.65 wide x 0.55 deep x
3.4 tall. Origin: floor centre; the BACK is the wall plane at y = +0.275, the room is -Y (the hand
crank is the deepest part, to y = -0.275). Anything reaches 3.4 m at most (the ceiling)."""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bunker_kit as bk  # noqa: E402
import library_kit  # noqa: E402
from library_kit import Mesh, common, materials  # noqa: E402

importlib.reload(bk)
importlib.reload(library_kit)
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402


def _ortho(d):
    """Two unit vectors perpendicular to d (and each other): u x v = d."""
    d = Vector(d).normalized()
    a = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
    u = d.cross(a).normalized()
    v = d.cross(u).normalized()
    return u, v


class M(Mesh):
    """library_kit.Mesh plus beveled boxes, cylinders/cones, spheres, tori, sweeps, prisms."""

    def _new_faces(self, before):
        return [f for f in self.bm.faces if f not in before]

    def _uv(self, faces, tile=None):
        self._set_uv_box(faces, (1, 1, 1), (0, 0), tile or self.tile)

    def rb(self, centre, size, bev=0.003, **kw):
        """Box with chamfered edges (one segment): catches a highlight on every edge."""
        before = set(self.bm.faces)
        verts = self.box(centre, size, **kw)
        edges = list({e for v in verts for e in v.link_edges})
        bmesh.ops.bevel(self.bm, geom=list(verts) + edges, offset=min(bev, min(size) * 0.45),
                        segments=1, affect="EDGES")
        self._uv(self._new_faces(before), kw.get("tile"))

    def cyl(self, a, b, r, r2=None, segs=16, caps=(True, True), smooth=True, tile=None, start=0.0):
        """Cylinder / cone from point a (radius r) to point b (radius r2); caps flat, sides smooth."""
        a, b = Vector(a), Vector(b)
        r2 = r if r2 is None else r2
        u, v = _ortho(b - a)
        bm = self.bm
        before = set(bm.faces)
        ang = [start + 2 * math.pi * i / segs for i in range(segs)]

        def ring(p, rad):
            return [bm.verts.new(p + rad * (math.cos(t) * u + math.sin(t) * v)) for t in ang]

        r0, r1 = ring(a, r), ring(b, r2)
        for i in range(segs):
            j = (i + 1) % segs
            f = bm.faces.new([r0[i], r0[j], r1[j], r1[i]])
            f.smooth = smooth
        if caps[0] and r > 1e-6:
            bm.faces.new(list(reversed(ring(a, r))))
        if caps[1] and r2 > 1e-6:
            bm.faces.new(ring(b, r2))
        self._uv(self._new_faces(before), tile)

    def sphere(self, c, r, segs=12, rings=8, squash=1.0):
        before = set(self.bm.faces)
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=segs, v_segments=rings, radius=r)
        bmesh.ops.scale(self.bm, vec=(1, 1, squash), verts=res["verts"])
        bmesh.ops.translate(self.bm, vec=Vector(c), verts=res["verts"])
        fs = self._new_faces(before)
        for f in fs:
            f.smooth = True
        self._uv(fs)

    def sweep(self, pts, radii, segs=10, caps=True, frame0=None, scale_v=1.0):
        """Tube through points `pts` with a radius per point (parallel-transport frames).
        scale_v flattens the cross-section (an oval cable)."""
        bm = self.bm
        before = set(bm.faces)
        pts = [Vector(p) for p in pts]
        n = len(pts)
        if not hasattr(radii, "__len__"):
            radii = [radii] * n
        rings, prev_u = [], None
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
            if prev_u is None:
                u = _ortho(t)[0] if frame0 is None else Vector(frame0)
                u = (u - t * u.dot(t)).normalized()
            else:
                u = (prev_u - t * prev_u.dot(t)).normalized()
            prev_u = u
            v = t.cross(u).normalized()
            rings.append((p, u, v))
        ang = [2 * math.pi * k / segs for k in range(segs)]

        def verts_of(i):
            p, u, v = rings[i]
            return [bm.verts.new(p + radii[i] * (math.cos(a) * u + math.sin(a) * v * scale_v)) for a in ang]

        vs = [verts_of(i) for i in range(n)]
        for i in range(n - 1):
            for k in range(segs):
                k2 = (k + 1) % segs
                f = bm.faces.new([vs[i][k], vs[i][k2], vs[i + 1][k2], vs[i + 1][k]])
                f.smooth = True
        if caps:
            bm.faces.new(list(reversed(verts_of(0))))
            bm.faces.new(verts_of(n - 1))
        fs = self._new_faces(before)
        bmesh.ops.recalc_face_normals(bm, faces=fs)
        self._uv(fs)

    def torus(self, c, R, r, axis=(0, 1, 0), segs=24, tsegs=8):
        bm = self.bm
        before = set(bm.faces)
        u, v = _ortho(axis)
        ax = Vector(axis).normalized()
        c = Vector(c)
        rows = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            dirv = math.cos(a) * u + math.sin(a) * v
            ctr = c + R * dirv
            rows.append([bm.verts.new(ctr + r * (math.cos(t) * dirv + math.sin(t) * ax))
                         for t in [2 * math.pi * k / tsegs for k in range(tsegs)]])
        for i in range(segs):
            i2 = (i + 1) % segs
            for k in range(tsegs):
                k2 = (k + 1) % tsegs
                f = bm.faces.new([rows[i][k], rows[i2][k], rows[i2][k2], rows[i][k2]])
                f.smooth = True
        fs = self._new_faces(before)
        bmesh.ops.recalc_face_normals(bm, faces=fs)
        self._uv(fs)

    def prism(self, pts, origin, u, v, depth, w=None):
        """Polygon `pts` (a, b) in the plane origin + a*u + b*v, extruded `depth` along w
        (default u x v)."""
        bm = self.bm
        u, v = Vector(u), Vector(v)
        w = (Vector(w) if w is not None else u.cross(v)).normalized()
        before = set(bm.faces)
        vs = [bm.verts.new(Vector(origin) + a * u + b * v) for a, b in pts]
        f = bm.faces.new(vs)
        res = bmesh.ops.extrude_face_region(bm, geom=[f])
        nv = [e for e in res["geom"] if isinstance(e, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, vec=w * depth, verts=nv)
        fs = self._new_faces(before)
        bmesh.ops.recalc_face_normals(bm, faces=fs)
        self._uv(fs)


def mark(*meshes):
    return [(m, set(m.bm.verts)) for m in meshes]


def xform(marks, matrix):
    """Rigidly move everything the meshes gained since mark() (a hinged lid, a tilted tool)."""
    for m, before in marks:
        bmesh.ops.transform(m.bm, matrix=matrix, verts=[v for v in m.bm.verts if v not in before])


def rot_about(point, axis, angle):
    p = Vector(point)
    return Matrix.Translation(p) @ Matrix.Rotation(angle, 4, axis) @ Matrix.Translation(-p)

NAME = "ArmoryPower"

P = dict(
    name=NAME,
    ceiling=3.4,
    battery=(1.15, 0.15, 0.75),
    battery_z=1.45,
    pitch=1.25,
)

WALL = 0.275


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    CE = p["ceiling"]
    BW, BD, BH = p["battery"]
    BZ, PITCH = p["battery_z"], p["pitch"]

    wh, gr, st, gm, po = M(0.5), M(0.5), M(0.5), M(0.5), M(0.5)
    rd, led, pvc, gv = M(0.5), M(0.5), M(0.5), M(0.5)

    # ---- three wall-hung battery units ------------------------------------------------------------------
    bxs = [-PITCH, 0.0, PITCH]
    by = WALL - BD / 2
    yf = WALL - BD
    for bx in bxs:
        wh.rb((bx, by, BZ + BH / 2), (BW, BD, BH), bev=0.012)
        wh.rb((bx, yf - 0.0015, BZ + BH / 2), (BW - 0.08, 0.004, BH - 0.08), bev=0.002)       # raised face panel
        gr.box((bx, WALL - 0.008, BZ + BH - 0.05), (BW - 0.3, 0.012, 0.05))                    # hanging rail (shows as a shadow gap)
        for k in range(7):                                                                      # intake slots
            gr.box((bx - 0.30, yf - 0.0035, BZ + 0.10 + 0.032 * k), (0.34, 0.002, 0.012))
        gr.rb((bx - 0.26, yf - 0.0035, BZ + BH - 0.15), (0.26, 0.003, 0.09), bev=0.002)        # display window
        po.box((bx - 0.26, yf - 0.0052, BZ + BH - 0.15), (0.23, 0.001, 0.065))
        st.rb((bx + 0.25, yf - 0.0035, BZ + BH - 0.15), (0.10, 0.003, 0.016), bev=0.001)         # nameless plate
        led.box((bx + 0.40, yf - 0.0045, BZ + BH / 2 + 0.02), (0.012, 0.0015, 0.52))           # the cold LED line
        for gx in (-0.36, -0.24, 0.24, 0.36):                                                   # cable glands
            po.cyl((bx + gx, by, BZ - 0.002), (bx + gx, by, BZ - 0.045), 0.014, 0.012, segs=8)
        for sx in (-1, 1):
            st.rb((bx + sx * (BW / 2 - 0.004), by, BZ + BH * 0.55), (0.008, 0.07, 0.12), bev=0.002)   # side handles

    # ---- conduit over the batteries and up into the ceiling ----------------------------------------------
    cy = WALL - 0.034
    zc = BZ + BH + 0.10                                    # 2.30
    gap_x = PITCH / 2                                      # centre of the gap between batteries 2 and 3
    pvc.cyl((-1.80, cy, zc), (gap_x + 0.02, cy, zc), 0.0145, segs=10)
    for bx in bxs:                                         # stubs down into each unit
        pvc.cyl((bx + 0.12, cy, zc), (bx + 0.12, cy, BZ + BH - 0.01), 0.0145, segs=10)
        gv.rb((bx + 0.12, cy, zc - 0.045), (0.034, 0.012, 0.012), bev=0.001, rot=(math.radians(90), "z"))
    for dx in (-0.024, 0.024):                             # two runs from the cabinet to the ceiling
        pvc.cyl((gap_x + dx, cy, 0.95), (gap_x + dx, cy, CE), 0.0145, segs=10)
    pvc.rb((gap_x, cy + 0.0, 1.20), (0.14, 0.05, 0.14), bev=0.004)                # junction box
    gr.box((gap_x, cy - 0.027, 1.20), (0.12, 0.004, 0.12))
    for sx in (-0.05, 0.05):
        for sz in (-0.05, 0.05):
            st.cyl((gap_x + sx, cy - 0.030, 1.20 + sz), (gap_x + sx, cy - 0.032, 1.20 + sz), 0.006, segs=6)
    for zz in (1.75, 2.62, 3.10, 3.34):                                            # strut clamps
        gv.rb((gap_x, cy + 0.016, zz), (0.082, 0.012, 0.022), bev=0.002)
        for dx in (-0.034, 0.034):
            gv.cyl((gap_x + dx, cy + 0.02, zz), (gap_x + dx, cy + 0.012, zz), 0.006, segs=6)
    for xx in (-1.60, -0.80, 0.80, 1.60):
        gv.rb((xx, cy + 0.016, zc), (0.022, 0.012, 0.082), bev=0.002)
    # conduit end-caps where the horizontal run enters the first unit and joins the vertical
    pvc.sphere((-1.80, cy, zc), 0.0148, segs=8, rings=5)
    pvc.rb((gap_x, cy, zc), (0.09, 0.040, 0.050), bev=0.004)                       # the tee box

    # ---- the transfer-switch cabinet -------------------------------------------------------------------
    tx, ty = gap_x, WALL - 0.15
    tz0 = 0.05
    gr.rb((tx, ty, tz0 + 0.45), (0.60, 0.30, 0.90), bev=0.006)
    gr.box((tx, WALL - 0.30 - 0.0015, tz0 + 0.45), (0.003, 0.003, 0.86))               # door seam (a groove)
    for sx in (-0.26, 0.26):
        for sz in (0.08, 0.82):
            st.rb((tx + sx, WALL - 0.304, tz0 + sz), (0.034, 0.012, 0.10), bev=0.002)          # hinges / hasps
    po.cyl((tx - 0.27, ty, 0.0), (tx - 0.27, ty, tz0), 0.025, segs=8)
    po.cyl((tx + 0.27, ty, 0.0), (tx + 0.27, ty, tz0), 0.025, segs=8)
    for k in range(6):                                                                      # lower louvres
        gr.rb((tx, WALL - 0.3 - 0.004, tz0 + 0.10 + 0.018 * k), (0.30, 0.010, 0.008), bev=0.001, rot=(math.radians(-14), "x"))
    st.rb((tx, WALL - 0.3 - 0.004, tz0 + 0.74), (0.30, 0.004, 0.09), bev=0.002)             # warning panel (no text)
    rd.box((tx, WALL - 0.3 - 0.0065, tz0 + 0.74), (0.26, 0.002, 0.05))
    for k, sx in enumerate((-0.10, 0.10)):                                                  # two status lights
        po.cyl((tx + sx, WALL - 0.3, tz0 + 0.60), (tx + sx, WALL - 0.3 - 0.012, tz0 + 0.60), 0.019, segs=12)
        led.cyl((tx + sx, WALL - 0.3 - 0.012, tz0 + 0.60), (tx + sx, WALL - 0.3 - 0.016, tz0 + 0.60), 0.0125, segs=12)
    # the big rotary handle (red), on a stainless escutcheon
    hz = tz0 + 0.37
    hy = WALL - 0.30
    st.cyl((tx, hy, hz), (tx, hy - 0.008, hz), 0.115, segs=24)
    gr.cyl((tx, hy - 0.008, hz), (tx, hy - 0.012, hz), 0.092, segs=24)
    for a in (-55, 0, 55):                                                                  # position marks
        pa = math.radians(a)
        st.box((tx + 0.100 * math.sin(pa), hy - 0.0125, hz + 0.100 * math.cos(pa)), (0.012, 0.002, 0.012), rot=(-pa, "y"))
    rd.cyl((tx, hy - 0.012, hz), (tx, hy - 0.060, hz), 0.032, 0.028, segs=18)               # the hub
    mk = mark(rd)
    rd.rb((0, -0.05, 0.0), (0.040, 0.030, 0.25), bev=0.008, taper=(1.0, 1.0))                # the lever, along local z
    rd.cyl((0, -0.05, 0.095), (0, -0.05, 0.125), 0.027, 0.024, segs=12)
    rd.cyl((0, -0.05, -0.095), (0, -0.05, -0.125), 0.027, 0.024, segs=12)
    xform(mk, Matrix.Translation((tx, hy, hz)) @ Matrix.Rotation(math.radians(-35), 4, "Y"))
    st.cyl((tx + 0.19, hy, hz + 0.03), (tx + 0.19, hy - 0.022, hz + 0.03), 0.014, segs=10)     # a padlock hasp pin

    # ---- the NBC air-filtration unit -------------------------------------------------------------------
    nx, nbw, nbd, nbh = -PITCH, 0.70, 0.50, 1.30
    nz0 = 0.05
    ny = WALL - nbd / 2
    wh.rb((nx, ny, nz0 + nbh / 2), (nbw, nbd, nbh), bev=0.012)
    gr.box((nx, ny, 0.025), (nbw - 0.06, nbd - 0.06, 0.05))                               # plinth
    nyf = WALL - nbd                                                                       # front face
    gr.rb((nx, nyf - 0.004, nz0 + 0.34), (0.54, 0.010, 0.38), bev=0.003)                    # intake grille frame
    for k in range(11):
        gr.rb((nx, nyf - 0.0115, nz0 + 0.19 + 0.030 * k), (0.50, 0.012, 0.014), bev=0.002, rot=(math.radians(-22), "x"))
    wh.rb((nx, nyf - 0.003, nz0 + 0.74), (0.60, 0.006, 0.16), bev=0.002)                    # gauge plate
    gr.rb((nx, nyf - 0.0065, nz0 + 0.74), (0.60, 0.002, 0.16), bev=0.002)
    for sx in (-0.15, 0.15):                                                                # two round gauges
        st.cyl((nx + sx, nyf - 0.006, nz0 + 0.74), (nx + sx, nyf - 0.030, nz0 + 0.74), 0.062, 0.058, segs=24)
        po.cyl((nx + sx, nyf - 0.030, nz0 + 0.74), (nx + sx, nyf - 0.032, nz0 + 0.74), 0.052, segs=24)
        wh.cyl((nx + sx, nyf - 0.032, nz0 + 0.74), (nx + sx, nyf - 0.0325, nz0 + 0.74), 0.048, segs=24)  # the dial
        for a in range(-120, 121, 30):                                                      # tick marks
            pa = math.radians(a)
            po.box((nx + sx + 0.040 * math.sin(pa), nyf - 0.0335, nz0 + 0.74 + 0.040 * math.cos(pa)),
                   (0.003, 0.001, 0.008), rot=(-pa, "y"))
        pa = math.radians(35 if sx < 0 else -20)
        rd.box((nx + sx + 0.016 * math.sin(pa), nyf - 0.0342, nz0 + 0.74 + 0.016 * math.cos(pa)),
               (0.003, 0.0012, 0.034), rot=(-pa, "y"))                                      # needle
        gm.cyl((nx + sx, nyf - 0.0335, nz0 + 0.74), (nx + sx, nyf - 0.036, nz0 + 0.74), 0.005, segs=8)
    for sx in (-0.30, 0.30):                                                               # door latches
        st.rb((nx + sx, nyf - 0.006, nz0 + 1.12), (0.04, 0.012, 0.07), bev=0.002)
        st.rb((nx + sx, nyf - 0.006, nz0 + 0.45), (0.04, 0.012, 0.07), bev=0.002)
    st.rb((nx, nyf - 0.003, nz0 + 1.15), (0.14, 0.004, 0.045), bev=0.001)                   # data plate
    # hand crank on the right side
    sx_ = nx + nbw / 2
    cz = nz0 + 0.62
    gm.cyl((sx_, ny - 0.03, cz), (sx_ + 0.075, ny - 0.03, cz), 0.013, segs=10)               # shaft
    st.cyl((sx_, ny - 0.03, cz), (sx_ + 0.012, ny - 0.03, cz), 0.04, segs=14)                # boss
    gm.rb((sx_ + 0.062, ny - 0.03, cz - 0.07), (0.016, 0.026, 0.15), bev=0.003)              # the arm, hanging down
    po.cyl((sx_ + 0.062, ny - 0.03, cz - 0.145), (sx_ + 0.062 + 0.09, ny - 0.03, cz - 0.145), 0.0155, segs=10)   # handle
    gm.cyl((sx_ + 0.062 - 0.012, ny - 0.03, cz - 0.145), (sx_ + 0.062 + 0.0, ny - 0.03, cz - 0.145), 0.01, segs=8)
    # the flange on top and the ribbed flexible duct up to the ceiling valve
    topz = nz0 + nbh
    gr.cyl((nx, ny, topz), (nx, ny, topz + 0.04), 0.115, 0.1, segs=20)
    vx, vy = nx, WALL - 0.215
    steps = 56
    path, rad = [], []
    z0, z1 = topz + 0.04, CE - 0.24
    for i in range(steps + 1):
        t = i / steps
        z = z0 + (z1 - z0) * t
        x = nx + 0.10 * math.sin(2 * math.pi * t * 0.9) * (1 - t * 0.5)
        y = ny + (vy - ny) * (t ** 1.4) - 0.07 * math.sin(math.pi * min(1.0, t * 1.3))
        path.append(Vector((x, y, z)))
        rad.append(0.075 if i % 2 == 0 else 0.0675)
    st.sweep(path, rad, segs=10)
    end = path[-1]
    for pt in (path[0], end):                                                              # clamp bands
        gv.cyl(pt + Vector((0, 0, -0.012)), pt + Vector((0, 0, 0.012)), 0.0795, segs=12)
    # wall straps along the duct
    for i in (14, 28, 42):
        pt = path[i]
        st.cyl(pt + Vector((0, 0, -0.008)), pt + Vector((0, 0, 0.008)), 0.0765, segs=12)
        gv.rb((pt.x, (pt.y + WALL) / 2 + 0.01, pt.z), (0.022, WALL - pt.y - 0.062, 0.014), bev=0.002)
    # the ceiling blast valve
    vz = CE
    gm.cyl((end.x, end.y, end.z), (end.x, end.y, vz - 0.04), 0.12, 0.115, segs=22)
    gm.cyl((end.x, end.y, vz - 0.04), (end.x, end.y, vz), 0.17, segs=22)
    st.cyl((end.x, end.y, end.z + 0.012), (end.x, end.y, end.z + 0.03), 0.128, segs=22)
    for k in range(8):
        a = math.radians(45 * k)
        st.cyl((end.x + 0.145 * math.cos(a), end.y + 0.145 * math.sin(a), vz - 0.04),
               (end.x + 0.145 * math.cos(a), end.y + 0.145 * math.sin(a), vz - 0.05), 0.0095, segs=6)
    gm.cyl((end.x, end.y, end.z + 0.08), (end.x + 0.20, end.y, end.z + 0.08), 0.011, segs=8)     # the lever shaft
    rd.cyl((end.x + 0.20, end.y, end.z + 0.08), (end.x + 0.30, end.y, end.z + 0.08), 0.015, segs=10)
    rd.sphere((end.x + 0.305, end.y, end.z + 0.08), 0.022, segs=10, rings=6)
    gm.cyl((end.x - 0.02, end.y, end.z + 0.08), (end.x + 0.0, end.y, end.z + 0.08), 0.02, segs=10)
    st.cyl((end.x, end.y - 0.12, end.z + 0.06), (end.x, end.y - 0.17, end.z + 0.06), 0.011, segs=8)   # a test port

    # ---- objects -----------------------------------------------------------------------------------------------
    wh.to_object(f"{n}_White", col, bk.white(), root)
    gr.to_object(f"{n}_Graphite", col, bk.graphite(), root)
    st.to_object(f"{n}_Stainless", col, bk.stainless(), root)
    gm.to_object(f"{n}_Gunmetal", col, bk.gunmetal(), root)
    po.to_object(f"{n}_Polymer", col, bk.polymer(), root)
    rd.to_object(f"{n}_Red", col, bk.red(), root)
    pvc.to_object(f"{n}_Conduit", col, bk.pvc(), root)
    gv.to_object(f"{n}_Galvanised", col, bk.galvanised(), root)
    led.to_object(f"{n}_LED", col, bk.led(), root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
