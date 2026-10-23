"""Armory gunsmith's bench: a 2.2 x 0.75 m walnut butcher-block top at 0.95 m on a graphite base (a stack
of four drawers on the right, an open knee space with a shelf on the left), a heavy gunmetal bench vise
and a padded V-block gun cradle on top, behind it a 2.2 x 1.2 m graphite french-cleat wall (from 1.10 m)
hung with screwdrivers, punches, pliers, a hammer, a torque wrench, a coil of cord, a scope box on a
shelf, and an articulated task lamp with a cold LED head. All the loose things are fixed.
Origin: floor centre. The bench stands against a wall: the BACK (the cleat wall) is at y = +0.39, the
room is -Y."""
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

NAME = "ArmoryBench"

P = dict(
    name=NAME,
    top=(2.2, 0.75),
    top_z=0.95,
)

BACK = 0.39          # wall plane (y)
PANEL_FRONT = 0.36   # front face of the cleat panel


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    TW, TD = p["top"]
    TZ = p["top_z"]

    wal, gr, st, gm = M(0.5), M(0.5), M(0.5), M(0.5)
    po, ol, fe = M(0.5), M(0.5), M(0.2)
    lamp, led = M(0.5), M(0.5)
    ytf, ytb = -0.39, 0.36                   # top: front and back edges

    # ---- the butcher-block top: 8 glued strips, each with its own grain offset -----------------------
    ns = 8
    sw = (ytb - ytf) / ns
    for k in range(ns):
        wal.box((0, ytf + sw * (k + 0.5), TZ - 0.03), (TW, sw, 0.06), shift=(0.137 * ((k * 5) % 8), 0.211 * k))

    # ---- base ----------------------------------------------------------------------------------------
    zb0, zb1 = 0.08, 0.89
    gr.rb((0, 0.02, 0.87), (2.10, 0.66, 0.04), bev=0.002)                        # top rail frame
    gr.box((0.0, 0.035, 0.04), (2.0, 0.60, 0.08))                                 # plinth
    for sx in (-1.05 + 0.01, 0.20):                                               # the two end/divider panels
        gr.rb((sx, 0.015, (zb0 + zb1) / 2 - 0.02), (0.02, 0.69, zb1 - zb0 - 0.04), bev=0.002)
    gr.rb((1.04, 0.015, (zb0 + zb1) / 2 - 0.02), (0.02, 0.69, zb1 - zb0 - 0.04), bev=0.002)
    gr.box((0.625, 0.34, (zb0 + zb1) / 2), (0.86, 0.012, zb1 - zb0))             # drawer-stack back
    gr.box((-0.425, 0.34, (zb0 + zb1) / 2), (1.26, 0.012, zb1 - zb0))             # knee-space back
    gr.rb((-0.425, 0.015, 0.30), (1.24, 0.66, 0.025), bev=0.002)                  # the low shelf
    # drawers: 4 fronts with 3 mm reveals
    dh = (zb1 - 0.02 - zb0 - 0.01 - 3 * 0.003) / 4
    for i in range(4):
        zc = zb0 + 0.01 + dh / 2 + i * (dh + 0.003)
        gr.rb((0.62, -0.335, zc), (0.82, 0.02, dh), bev=0.0025)
        st.rb((0.62, -0.356, zc + dh * 0.22), (0.46, 0.016, 0.014), bev=0.003)       # bar pulls
        for sx in (-0.21, 0.21):
            st.box((0.62 + sx, -0.346, zc + dh * 0.22), (0.014, 0.012, 0.014))
        st.box((0.62, -0.3455, zc - dh * 0.22), (0.12, 0.002, 0.03))               # label plates
    # knee-space shelf contents: two cans and a bin, fixed
    for cx, yaw in ((-0.80, 4), (-0.47, -3)):
        mk = mark(ol, st)
        ol.rb((0, 0, 0.09), (0.30, 0.15, 0.18), bev=0.004)
        ol.box((0, 0, 0.165), (0.306, 0.156, 0.016))
        st.box((0, -0.0795, 0.15), (0.036, 0.007, 0.04))
        xform(mk, Matrix.Translation((cx, -0.10, 0.3125)) @ Matrix.Rotation(math.radians(yaw), 4, "Z"))
    po.rb((-0.12, -0.05, 0.37), (0.34, 0.26, 0.11), bev=0.004)                   # a lidded black bin
    po.rb((-0.12, -0.05, 0.43), (0.356, 0.276, 0.012), bev=0.003)
    st.box((-0.12, -0.19, 0.38), (0.12, 0.006, 0.03))

    # ---- the cleat wall -------------------------------------------------------------------------------
    pz0, pz1 = 1.10, 2.30
    gr.rb((0, (PANEL_FRONT + BACK) / 2, (pz0 + pz1) / 2), (2.2, BACK - PANEL_FRONT, pz1 - pz0), bev=0.004)
    for k in range(8):
        z0 = 1.13 + 0.15 * k
        gr.prism([(PANEL_FRONT, z0), (PANEL_FRONT - 0.016, z0 + 0.010), (PANEL_FRONT - 0.016, z0 + 0.034),
                  (PANEL_FRONT, z0 + 0.034)], (-1.08, 0, 0), (0, 1, 0), (0, 0, 1), 2.16)
    yf = PANEL_FRONT - 0.016                  # the front face of the cleats: tools mount from here
    # tool holders are rails standing 0.04 off the cleats
    def rail(x0, x1, z, depth=0.04):
        gm.rb(((x0 + x1) / 2, yf - depth / 2, z), (x1 - x0, depth, 0.022), bev=0.002)
        for sx in (x0 + 0.02, x1 - 0.02):
            gm.box((sx, yf - depth / 2 + 0.003, z - 0.008), (0.02, depth - 0.004, 0.034))

    # screwdrivers (handle above the rail, shaft down through it)
    zr = 2.00
    rail(-1.02, -0.40, zr)
    ysd = yf - 0.02
    sdx = [-0.98 + 0.083 * i for i in range(7)]
    for i, x in enumerate(sdx):
        hl, hr, sl = 0.095 + 0.012 * (i % 3), 0.0135 + 0.0008 * (i % 3), 0.10 + 0.018 * ((i * 2) % 4)
        po.cyl((x, ysd, zr + 0.011), (x, ysd, zr + 0.011 + hl), hr, hr * 0.92, segs=10)
        po.cyl((x, ysd, zr + 0.011 + hl), (x, ysd, zr + 0.016 + hl), hr * 0.92, hr * 0.55, segs=10)
        gm.cyl((x, ysd, zr + 0.011), (x, ysd, zr + 0.011 + 0.018), hr * 0.62, segs=8)
        gm.cyl((x, ysd, zr + 0.011), (x, ysd, zr - sl), 0.0034, segs=6)
        gm.cyl((x, ysd, zr - sl), (x, ysd, zr - sl - 0.012), 0.0034, 0.0016, segs=6)
    # punches: head up, tapering tip down
    rail(-0.30, 0.34, zr)
    for i in range(9):
        x = -0.27 + 0.0665 * i
        L = 0.12 + 0.012 * ((i * 4) % 5)
        gm.cyl((x, ysd, zr + 0.011), (x, ysd, zr + 0.026), 0.0062, 0.0050, segs=8)
        gm.cyl((x, ysd, zr + 0.011), (x, ysd, zr - L * 0.7), 0.0046, segs=8)
        gm.cyl((x, ysd, zr - L * 0.7), (x, ysd, zr - L), 0.0046, 0.0018, segs=8)
    # hammer on two pegs: walnut handle, gunmetal head with a ball peen
    hz, hy = 1.97, yf - 0.03
    for sx in (0.50, 0.80):
        gm.cyl((sx, yf, hz - 0.03), (sx, yf - 0.05, hz - 0.03), 0.006, segs=8)
        gm.cyl((sx, yf - 0.05, hz - 0.03), (sx, yf - 0.05, hz - 0.012), 0.006, segs=8)
    wal.cyl((0.46, hy, hz), (0.90, hy, hz), 0.0125, 0.0165, segs=10)
    gm.cyl((0.90, hy, hz), (0.90 + 0.015, hy, hz), 0.0185, segs=10)
    gm.rb((0.97, hy, hz), (0.11, 0.032, 0.036), bev=0.004)
    gm.cyl((1.025, hy, hz), (1.05, hy, hz), 0.017, 0.012, segs=10)
    gm.sphere((1.058, hy, hz), 0.014, segs=10, rings=6)
    gm.cyl((0.905, hy - 0.016, hz), (0.905, hy + 0.016, hz), 0.0175, segs=10)
    # torque wrench: stainless head, gunmetal tube, polymer grip
    tz, ty = 1.70, yf - 0.032
    for sx in (-0.78, -0.50):
        gm.cyl((sx, yf, tz - 0.03), (sx, yf - 0.06, tz - 0.03), 0.006, segs=8)
        gm.cyl((sx, yf - 0.06, tz - 0.03), (sx, yf - 0.06, tz - 0.012), 0.006, segs=8)
    gm.cyl((-0.99, ty, tz), (-0.55, ty, tz), 0.0105, segs=12)
    po.cyl((-0.55, ty, tz), (-0.36, ty, tz), 0.0165, 0.0175, segs=14)
    po.cyl((-0.36, ty, tz), (-0.352, ty, tz), 0.0175, 0.0, segs=14)
    st.cyl((-0.99, ty, tz - 0.022), (-0.99, ty, tz + 0.022), 0.024, segs=14)
    gm.cyl((-0.99, ty, tz - 0.030), (-0.99, ty, tz - 0.022), 0.008, segs=8)
    st.cyl((-0.72, ty, tz), (-0.66, ty, tz), 0.0125, segs=12)                    # the scale collar
    # a second (small) torque screwdriver
    po.cyl((-0.30, ty, tz + 0.0), (-0.20, ty, tz), 0.014, segs=10)
    st.cyl((-0.20, ty, tz), (-0.185, ty, tz), 0.0135, segs=10)
    gm.cyl((-0.185, ty, tz), (-0.06, ty, tz), 0.004, segs=8)
    for sx in (-0.27, -0.10):
        gm.cyl((sx, yf, tz - 0.03), (sx, yf - 0.05, tz - 0.03), 0.006, segs=8)
        gm.cyl((sx, yf - 0.05, tz - 0.03), (sx, yf - 0.05, tz - 0.012), 0.006, segs=8)
    # pliers hung by the jaws: three, on a rail
    zp = 1.43
    rail(-1.02, -0.50, zp + 0.14)
    for i, x in enumerate((-0.92, -0.80, -0.68)):
        for sgn in (-1, 1):
            mk = mark(po, gm)
            po.cyl((0, 0, 0), (0, 0, -0.12), 0.0055, 0.0075, segs=8)
            gm.rb((0, 0, 0.012), (0.0095, 0.012, 0.05), bev=0.001)
            xform(mk, Matrix.Translation((x + sgn * 0.0085, ysd, zp + 0.14 - 0.014 + 0.0)) @ Matrix.Rotation(math.radians(-sgn * (5 + 2 * i)), 4, "Y")
)
    # shelf with the scope box and a pelican-style case
    sz = 1.43
    gr.rb((0.0, (PANEL_FRONT - 0.016) - 0.085, sz), (0.76, 0.17, 0.022), bev=0.002)
    for sx in (-0.34, 0.34):
        gr.prism([(0, 0), (0.15, 0), (0, -0.10)], (sx, yf, sz - 0.011), (0, -1, 0), (0, 0, 1), 0.02, w=(1, 0, 0))
    po.rb((-0.11, yf - 0.095, sz + 0.011 + 0.052), (0.40, 0.14, 0.104), bev=0.004)      # scope box
    po.rb((-0.11, yf - 0.095, sz + 0.011 + 0.083), (0.41, 0.15, 0.012), bev=0.003)
    for sx in (-0.26, -0.11, 0.04):
        st.rb((sx, yf - 0.171, sz + 0.011 + 0.075), (0.045, 0.012, 0.03), bev=0.002)
    po.rb((-0.11, yf - 0.095, sz + 0.011 + 0.112), (0.12, 0.045, 0.018), bev=0.003)      # carry handle
    ol.rb((0.23, yf - 0.095, sz + 0.011 + 0.04), (0.17, 0.12, 0.08), bev=0.004)          # olive utility box
    ol.rb((0.23, yf - 0.095, sz + 0.011 + 0.088), (0.176, 0.126, 0.016), bev=0.003)
    st.box((0.23, yf - 0.157, sz + 0.011 + 0.075), (0.03, 0.006, 0.03))
    # coil of olive cord on a hook
    cx, cz = 0.76, 1.50
    gm.cyl((cx, yf, cz + 0.085), (cx, yf - 0.06, cz + 0.085), 0.0075, segs=8)
    gm.cyl((cx, yf - 0.06, cz + 0.085), (cx, yf - 0.06, cz + 0.07), 0.0075, segs=8)
    for k in range(4):
        ol.torus((cx, yf - 0.03, cz - 0.003 * (k % 2) - 0.005 * k + 0.012), 0.070 + 0.002 * ((k * 3) % 5),
                 0.0058, axis=(0, 1, 0), segs=18, tsegs=5)
    st.cyl((cx - 0.075, yf - 0.04, cz + 0.0), (cx - 0.075, yf - 0.02, cz + 0.0), 0.0085, segs=10)   # the tie clip
    # combination wrenches hung by their ring ends from a rail, and a cleaning-rod tube up top
    zw = 1.335
    rail(-0.26, 0.24, zw)
    for i in range(6):
        x = -0.22 + 0.085 * i
        L = 0.15 - 0.014 * i
        rh = 0.0105 + 0.0009 * (5 - i)
        gm.box((x, ysd, zw - 0.011 - L / 2 - 0.004), (0.0125, 0.0035, L))
        gm.cyl((x, ysd - 0.0018, zw - 0.011 - L - 0.004), (x, ysd + 0.0018, zw - 0.011 - L - 0.004), rh + 0.002, segs=12)
        gm.cyl((x, ysd - 0.0018, zw - 0.002), (x, ysd + 0.0018, zw - 0.002), rh * 0.9, segs=10)
    rz = 2.19
    for sx in (0.50, 0.92):
        gm.cyl((sx, yf, rz - 0.035), (sx, yf - 0.055, rz - 0.035), 0.006, segs=8)
        gm.cyl((sx, yf - 0.055, rz - 0.035), (sx, yf - 0.055, rz - 0.018), 0.006, segs=8)
    gm.cyl((0.38, yf - 0.032, rz), (1.03, yf - 0.032, rz), 0.0215, segs=14)
    st.cyl((0.35, yf - 0.032, rz), (0.38, yf - 0.032, rz), 0.0235, segs=14)
    st.cyl((1.03, yf - 0.032, rz), (1.06, yf - 0.032, rz), 0.0235, segs=14)
    for sx in (0.62, 0.80):
        po.cyl((sx, yf - 0.032, rz), (sx + 0.03, yf - 0.032, rz), 0.0228, segs=14)
    # flashlight and calipers, low on the wall
    fz = 1.25
    for sx in (0.55, 0.78):
        gm.cyl((sx, yf, fz - 0.03), (sx, yf - 0.05, fz - 0.03), 0.006, segs=8)
        gm.cyl((sx, yf - 0.05, fz - 0.03), (sx, yf - 0.05, fz - 0.012), 0.006, segs=8)
    po.cyl((0.50, yf - 0.032, fz), (0.72, yf - 0.032, fz), 0.0165, segs=12)
    gm.cyl((0.72, yf - 0.032, fz), (0.755, yf - 0.032, fz), 0.0165, 0.0235, segs=12)
    gm.cyl((0.755, yf - 0.032, fz), (0.77, yf - 0.032, fz), 0.0235, segs=12)
    st.cyl((0.40, yf - 0.032, fz), (0.50, yf - 0.032, fz), 0.0145, segs=10)
    st.rb((0.95, yf - 0.028, 1.26), (0.032, 0.004, 0.32), bev=0.001)                       # caliper beam
    po.rb((0.95, yf - 0.032, 1.355), (0.034, 0.011, 0.07), bev=0.002)
    gm.box((0.95, yf - 0.024, 1.15), (0.034, 0.012, 0.016))
    st.box((0.95, yf - 0.021, 1.13), (0.012, 0.006, 0.06))

    # ---- on the top ------------------------------------------------------------------------------------
    # the vise at the left end: heavy gunmetal castings, jaws open along y, the handle toward the room
    vx, vy = -0.86, 0.04
    mk = mark(gm, st)
    gm.rb((0, 0.0, 0.014), (0.24, 0.34, 0.028), bev=0.004)                       # base plate
    gm.rb((0, 0.07, 0.075), (0.19, 0.20, 0.09), bev=0.005)                        # fixed body
    gm.rb((0, 0.012, 0.115), (0.17, 0.05, 0.10), bev=0.004)                       # fixed jaw
    gm.rb((0, -0.062, 0.11), (0.17, 0.05, 0.09), bev=0.004)                       # moving jaw
    gm.rb((0, -0.062, 0.062), (0.12, 0.07, 0.04), bev=0.003)                      # its slide
    gm.cyl((0, -0.02, 0.058), (0, -0.20, 0.058), 0.0125, segs=12)                 # the screw
    gm.cyl((0, -0.085, 0.058), (0, -0.115, 0.058), 0.0175, segs=12)
    gm.cyl((-0.11, -0.20, 0.058), (0.11, -0.20, 0.058), 0.0072, segs=8)            # the T bar
    gm.sphere((-0.115, -0.20, 0.058), 0.0145, segs=10, rings=6)
    gm.sphere((0.115, -0.20, 0.058), 0.0145, segs=10, rings=6)
    gm.cyl((0, -0.20, 0.058 - 0.017), (0, -0.20, 0.058 + 0.017), 0.015, segs=10)
    gm.rb((0, 0.085, 0.138), (0.12, 0.10, 0.024), bev=0.003)                      # anvil face
    for sx in (-0.095, 0.095):
        for sy in (-0.13, 0.13):
            st.cyl((sx, sy, 0.028), (sx, sy, 0.036), 0.0105, segs=6)               # bolt heads
    xform(mk, Matrix.Translation((vx, vy, TZ)))
    # padded V-block gun cradle: two graphite blocks with felt-lined V notches
    for cx_ in (-0.40, 0.14):
        v = [(-0.12, 0), (0.12, 0), (0.12, 0.12), (0.05, 0.12), (0, 0.075), (-0.05, 0.12), (-0.12, 0.12)]
        gr.prism(v, (cx_ - 0.04, 0.0, TZ + 0.012), (0, 1, 0), (0, 0, 1), 0.08, w=(1, 0, 0))
        gr.rb((cx_, 0.0, TZ + 0.006), (0.12, 0.28, 0.012), bev=0.0025)              # base plate
        for sy in (-0.09, 0.09):
            st.cyl((cx_ - 0.03, sy, TZ + 0.012), (cx_ - 0.03, sy, TZ + 0.016), 0.008, segs=6)
            st.cyl((cx_ + 0.03, sy, TZ + 0.012), (cx_ + 0.03, sy, TZ + 0.016), 0.008, segs=6)
        pad = [(-0.050, 0.120), (0, 0.075), (0.050, 0.120), (0.058, 0.137), (0, 0.092), (-0.058, 0.137)]
        fe.prism(pad, (cx_ - 0.048, 0.0, TZ + 0.012), (0, 1, 0), (0, 0, 1), 0.096, w=(1, 0, 0))
    # parts tray with a few pins
    tx, ty0 = 0.55, 0.02
    gr.rb((tx, ty0, TZ + 0.006), (0.24, 0.16, 0.012), bev=0.002)
    for sy in (-1, 1):
        gr.rb((tx, ty0 + sy * 0.0785, TZ + 0.016), (0.24, 0.007, 0.032), bev=0.0015)
    for sx in (-1, 1):
        gr.rb((tx + sx * 0.1165, ty0, TZ + 0.016), (0.007, 0.15, 0.032), bev=0.0015)
    fe.box((tx, ty0, TZ + 0.0135), (0.226, 0.146, 0.003))
    for k in range(5):
        gm.cyl((tx - 0.08 + 0.02 * k, ty0 - 0.03 + 0.012 * ((k * 3) % 5) / 2, TZ + 0.017),
               (tx - 0.075 + 0.02 * k, ty0 + 0.03, TZ + 0.017), 0.0035, segs=6)
    st.cyl((tx + 0.07, ty0 - 0.04, TZ + 0.015), (tx + 0.07, ty0 - 0.04, TZ + 0.0175), 0.012, segs=10)   # a spring washer

    # ---- the articulated task lamp (graphite arms, cold LED head) ----------------------------------------
    sh = Vector((0.80, 0.22, TZ + 0.045))         # shoulder pivot
    el = Vector((0.58, 0.14, TZ + 0.50))          # elbow
    wr = Vector((0.20, -0.05, TZ + 0.53))         # wrist (head joint)
    lamp.cyl((sh.x, sh.y, TZ), (sh.x, sh.y, TZ + 0.02), 0.10, 0.092, segs=24)     # weighted base
    lamp.cyl((sh.x, sh.y, TZ + 0.02), (sh.x, sh.y, TZ + 0.04), 0.045, 0.03, segs=14)
    for a, b in ((sh, el), (el, wr)):
        d = (b - a)
        lat = d.cross(Vector((0, 0, 1))).normalized()
        for s in (-1, 1):
            lamp.cyl(a + lat * 0.013 * s, b + lat * 0.013 * s, 0.0052, segs=8)
    d = el - sh
    lat = d.cross(Vector((0, 0, 1))).normalized()
    spr = [sh + d * (0.25 + 0.5 * i / 16) + lat * (0.0 + (0.012 if i % 2 else -0.012)) * 1 for i in range(17)]
    lamp.sweep(spr, [0.0030] * 17, segs=5, caps=True)
    for pivot in (sh, el, wr):
        d2 = (el - sh) if pivot is not wr else (wr - el)
        lt = d2.cross(Vector((0, 0, 1))).normalized()
        lamp.cyl(pivot - lt * 0.025, pivot + lt * 0.025, 0.017, segs=14)
    hd = Vector((0.10, -0.32, -1.0)).normalized()
    lamp.cyl(wr, wr + hd * 0.02, 0.014, 0.014, segs=10)
    lamp.cyl(wr + hd * 0.02, wr + hd * 0.155, 0.030, 0.082, segs=20, caps=(True, True))
    led.cyl(wr + hd * 0.155, wr + hd * 0.163, 0.068, 0.068, segs=20, caps=(True, True))
    lamp.cyl(wr + hd * 0.152, wr + hd * 0.155, 0.083, 0.083, segs=20)
    # the lamp's cable runs down the back to the wall
    cab = [Vector((sh.x + 0.07, sh.y, TZ + 0.015)), Vector((sh.x + 0.10, sh.y + 0.04, TZ + 0.008)),
           Vector((sh.x + 0.14, sh.y + 0.10, TZ + 0.006)), Vector((sh.x + 0.18, sh.y + 0.12, TZ + 0.006)),
           Vector((sh.x + 0.20, ytb + 0.0, TZ + 0.006))]
    po.sweep(cab, [0.0035] * len(cab), segs=6)

    # ---- objects ----------------------------------------------------------------------------------------
    wal.to_object(f"{n}_Walnut", col, materials.walnut(), root)
    gr.to_object(f"{n}_Graphite", col, bk.graphite(), root)
    st.to_object(f"{n}_Stainless", col, bk.stainless(), root)
    gm.to_object(f"{n}_Gunmetal", col, bk.gunmetal(), root)
    po.to_object(f"{n}_Polymer", col, bk.polymer(), root)
    ol.to_object(f"{n}_Olive", col, bk.olive(), root)
    fe.to_object(f"{n}_Felt", col, bk.felt(), root)
    lamp.to_object(f"{n}_Lamp", col, bk.graphite(), root)
    led.to_object(f"{n}_Lamp_LED", col, bk.led(), root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
