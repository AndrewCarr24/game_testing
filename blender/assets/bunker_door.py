"""The armory's door: a graphite steel leaf in a steel frame, one narrow vision slot of ballistic
glass, a stainless lever on both sides. For `plan.CUTS` like door.py: origin = bottom centre of
the opening on the wall's centre plane, the room it swings into is +Y (the hall side is -Y), it
swings 90 degrees about a hinge at the -X jamb. The hinge empty carries the rotate `interact`;
whether it is locked is the level's business.

Also hosts `Geo`, the small bmesh toolkit (boxes, cylinders, tori) the other bunker/tunnel assets
import (tunnel_*, pump_station, blast_door): library_kit's Mesh plus round things.
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import bunker_kit as bk  # noqa: E402
import library_kit as lk  # noqa: E402

importlib.reload(bk)
importlib.reload(lk)
common = bk.common


class Geo(lk.Mesh):
    """library_kit.Mesh (boxes with world-scale UVs) plus cylinders, cones, tori and ellipse
    shells. Round parts are smooth-shaded with crisp rims (cap edges are marked sharp)."""

    AXES = {"z": Matrix.Identity(4), "y": Matrix.Rotation(-math.pi / 2, 4, "X"),
            "x": Matrix.Rotation(math.pi / 2, 4, "Y")}

    def cyl(self, centre, r, length, axis="z", segs=16, r2=None, caps=True, smooth=True):
        """Cylinder / cone along `axis` (r at -length/2, r2 at +length/2)."""
        m = Matrix.Translation(Vector(centre)) @ self.AXES[axis]
        res = bmesh.ops.create_cone(self.bm, cap_ends=caps, cap_tris=False, segments=segs, radius1=r,
                                    radius2=r if r2 is None else r2, depth=length, matrix=m)
        faces = {f for v in res["verts"] for f in v.link_faces}
        for f in faces:
            if len(f.verts) == segs and segs != 4:
                f.smooth = False
                for e in f.edges:
                    e.smooth = False
            else:
                f.smooth = smooth
        return res["verts"]

    def torus(self, centre, R, t, axis="y", segs=32, tsegs=8):
        """Ring of tube radius t on a circle of radius R lying in the plane normal to `axis`."""
        m = Matrix.Translation(Vector(centre)) @ self.AXES[axis]
        rows = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            ring = []
            for j in range(tsegs):
                b = 2 * math.pi * j / tsegs
                rr = R + t * math.cos(b)
                ring.append(self.bm.verts.new(m @ Vector((rr * math.cos(a), rr * math.sin(a), t * math.sin(b)))))
            rows.append(ring)
        faces = []
        for i in range(segs):
            for j in range(tsegs):
                f = self.bm.faces.new([rows[i][j], rows[(i + 1) % segs][j],
                                       rows[(i + 1) % segs][(j + 1) % tsegs], rows[i][(j + 1) % tsegs]])
                f.smooth = True
                faces.append(f)
        bmesh.ops.recalc_face_normals(self.bm, faces=faces)

    def oval_lathe(self, profile, a, b, segs=28, centre=(0, 0, 0), sharp=40.0, closed=False):
        """Solid of revolution about the -Y axis (a wall fitting that stands out toward -Y) with an
        elliptical section: profile = [(r, depth), ...] (r 0..1 scales the half-width a along x and
        the half-height b along z; depth is metres toward -Y; r = 0 collapses to the axis).
        Corners turning more than `sharp` degrees get crisp edges, the rest shades smooth."""
        bm = self.bm
        rows = []
        for r, d in profile:
            if abs(r) < 1e-9:
                rows.append([bm.verts.new((centre[0], centre[1] - d, centre[2]))] * segs)
            else:
                rows.append([bm.verts.new((centre[0] + a * r * math.cos(2 * math.pi * s / segs), centre[1] - d,
                                           centre[2] + b * r * math.sin(2 * math.pi * s / segs)))
                             for s in range(segs)])
        n = len(profile)
        faces = []
        for i in range(n if closed else n - 1):
            ra, rb = rows[i], rows[(i + 1) % n]
            for s in range(segs):
                t = (s + 1) % segs
                quad = []
                for v in (ra[s], ra[t], rb[t], rb[s]):
                    if v not in quad:
                        quad.append(v)
                if len(quad) >= 3:
                    try:
                        faces.append(bm.faces.new(quad))
                    except ValueError:
                        pass
        bmesh.ops.recalc_face_normals(bm, faces=faces)
        for f in faces:
            f.smooth = True
        for i, (r, d) in enumerate(profile):
            if abs(r) < 1e-9 or i in (0, n - 1) and not closed:
                continue
            pr, nx = profile[(i - 1) % n], profile[(i + 1) % n]
            d1, d2 = (r - pr[0], d - pr[1]), (nx[0] - r, nx[1] - d)
            ang = math.degrees(abs(math.atan2(d1[0] * d2[1] - d1[1] * d2[0], d1[0] * d2[0] + d1[1] * d2[1])))
            if ang > sharp:
                for s in range(segs):
                    e = bm.edges.get((rows[i][s], rows[i][(s + 1) % segs]))
                    if e is not None:
                        e.smooth = False
        return faces

    def beam(self, a, b, size, up=(0, 0, 1)):
        """Rectangular bar from point a to point b with cross-section size = (w, h) (w along
        `up`'s perpendicular)."""
        a, b = Vector(a), Vector(b)
        d = b - a
        z = d.normalized()
        x = Vector(up).cross(z)
        if x.length < 1e-6:
            x = Vector((1, 0, 0)).cross(z)
        x.normalize()
        y = z.cross(x)
        rot = Matrix((x, y, z)).transposed().to_4x4()
        res = bmesh.ops.create_cube(self.bm, size=1.0)
        verts = res["verts"]
        bmesh.ops.scale(self.bm, vec=Vector((size[0], size[1], d.length)), verts=verts)
        bmesh.ops.transform(self.bm, matrix=Matrix.Translation((a + b) / 2) @ rot, verts=verts)
        faces = list({f for v in verts for f in v.link_faces})
        bmesh.ops.recalc_face_normals(self.bm, faces=faces)
        return verts

    def strap(self, a, b, w, t, up=(0, 0, 1)):
        """Open 4-sided flat bar from a to b (w wide along the cross product of `up` and the run,
        t thick): 8 triangles, for wire and strap work seen from outside (no end caps)."""
        a, b = Vector(a), Vector(b)
        z = (b - a).normalized()
        x = Vector(up).cross(z)
        if x.length < 1e-6:
            x = Vector((1, 0, 0)).cross(z)
        x.normalize()
        y = z.cross(x)
        vs = [[self.bm.verts.new(pt + x * (sx * w / 2) + y * (sy * t / 2)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
              for pt in (a, b)]
        for i in range(4):
            j = (i + 1) % 4
            self.bm.faces.new([vs[0][i], vs[0][j], vs[1][j], vs[1][i]])
        return vs

    def finish(self, name, col, mat, parent, bevel=None, location=None):
        ob = self.to_object(name, col, mat, parent)
        if bevel:
            common.add_bevel(ob, bevel, segments=1)
        if location is not None:
            ob.location = location
        return ob


NAME = "BunkerDoor"

P = dict(
    name=NAME,
    opening=(1.2, 2.15),     # width, height
    wall_t=0.3,
    leaf_t=0.06,
    gap=0.004,
    floor_gap=0.012,
    liner=0.03,              # the frame's reveal lining inside the opening
    trim_w=0.075,            # the frame's flat trim on both wall faces
    trim_t=0.014,
    slot=(0.085, 0.52),      # vision slot width, height
    slot_z=1.62,
    handle_z=1.02,
    duration=0.9,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    graphite, stainless, glass = bk.graphite(), bk.stainless(), bk.ballistic_glass()

    w, h = p["opening"]
    wt, lt, g, lin = p["wall_t"], p["leaf_t"], p["gap"], p["liner"]
    tw, tt = p["trim_w"], p["trim_t"]
    clear_w = w - 2 * lin
    sw = clear_w - 2 * g                       # leaf width
    z0 = p["floor_gap"]
    sh = h - lin - g - z0                      # leaf height
    hx = -clear_w / 2 + g                      # hinge axis x (leaf's hinge edge)
    hy = lt / 2                                # on the room-side face, like door.py

    # ---- the frame: static, one mesh per jamb/head so no single collider spans the doorway ----
    def jamb(sign):
        m = Geo()
        x_in = sign * (w / 2 - lin / 2)
        m.box((x_in, 0, (h - lin) / 2), (lin, wt, h - lin))                           # reveal lining
        # stop lip behind the leaf on the hall (-Y) side
        m.box((sign * (clear_w / 2 - 0.01), -lt / 2 - 0.012, (h - lin) / 2), (0.02, 0.024, h - lin))
        for face in (-1, 1):                                                          # flat trim, both faces
            m.box((sign * (w / 2 + tw / 2), face * (wt / 2 + tt / 2), (h + tw) / 2), (tw, tt, h + tw))
        return m.finish(f"{n}_Frame_{'R' if sign > 0 else 'L'}", col, graphite, root, bevel=0.0015)

    jamb(-1), jamb(1)
    m = Geo()
    m.box((0, 0, h - lin / 2), (clear_w, wt, lin))
    for face in (-1, 1):
        m.box((0, face * (wt / 2 + tt / 2), h + tw / 2), (w + 2 * tw, tt, tw))
    m.finish(f"{n}_Frame_Head", col, graphite, root, bevel=0.0015)

    # ---- the leaf (rotates with the hinge empty) ------------------------------------------
    hinge = common.empty(f"{n}_Hinge", col, (hx, hy, 0))
    hinge.parent = root
    hinge["interact"] = {
        "type": "rotate",
        "axis": common.to_gltf((0, 0, 1)),
        "angle": 90,
        "duration": p["duration"],
        "range": 1.8,
        "side": "both",
        "collide": True,
        "prompt": "Open door",
        "promptActive": "Close door",
        "lockedPrompt": "Locked · keycard required",
        "unlockPrompt": "Unlock with keycard",
    }

    sx, sz = p["slot"]
    scz = p["slot_z"]
    cx = sw / 2                                 # slot centred on the leaf (hinge space: leaf spans 0..sw)
    ly = -lt / 2                                # leaf centre y in hinge space
    leaf = Geo()
    zb, zt = z0 + 0, z0 + sh
    sb, st = scz - sz / 2, scz + sz / 2
    leaf.box((sw / 2, ly, (zb + sb) / 2), (sw, lt, sb - zb))                       # below the slot
    leaf.box((sw / 2, ly, (st + zt) / 2), (sw, lt, zt - st))                       # above
    leaf.box(((cx - sx / 2) / 2, ly, scz), (cx - sx / 2, lt, sz))                      # hinge-side strip
    leaf.box(((cx + sx / 2 + sw) / 2, ly, scz), (sw - cx - sx / 2, lt, sz))            # latch-side strip
    # pressed panel lines: two shallow raised rails down each face, a fold along the latch edge
    for face in (-1, 1):
        fy = ly + face * (lt / 2 + 0.0015)
        leaf.box((0.06, fy, (zb + zt) / 2), (0.012, 0.003, sh - 0.12))
        leaf.box((sw - 0.06, fy, (zb + zt) / 2), (0.012, 0.003, sh - 0.12))
        leaf.box((sw / 2, fy, zb + 0.06), (sw - 0.108, 0.003, 0.012))
        leaf.box((sw / 2, fy, zt - 0.06), (sw - 0.108, 0.003, 0.012))
    leaf.finish(f"{n}_Leaf", col, graphite, hinge, bevel=0.0018)

    # stainless: slot surround, kick plates, latch-edge strip, hinge knuckles, levers
    ss = Geo()
    for face in (-1, 1):
        fy = ly + face * (lt / 2 + 0.002)
        ss.box((cx - sx / 2 - 0.007, fy, scz), (0.014, 0.004, sz + 0.028))
        ss.box((cx + sx / 2 + 0.007, fy, scz), (0.014, 0.004, sz + 0.028))
        ss.box((cx, fy, sb - 0.007), (sx, 0.004, 0.014))
        ss.box((cx, fy, st + 0.007), (sx, 0.004, 0.014))
        ss.box((sw / 2, fy, zb + 0.095), (sw - 0.04, 0.004, 0.19))                  # kick plate
    ss.box((sw - 0.0015, ly, (zb + zt) / 2), (0.003, lt + 0.004, sh - 0.01))           # latch-edge strip
    for hz in (0.28, h / 2, h - 0.34):                                            # three hinge knuckles
        ss.cyl((0, 0, hz), 0.0155, 0.12, "z", segs=12)
    for face in (-1, 1):                                                          # levers
        fy = ly + face * (lt / 2)
        lx = sw - 0.085
        hz = p["handle_z"]
        ss.cyl((lx, fy + face * 0.003, hz), 0.032, 0.006, "y", segs=16)           # rose
        ss.cyl((lx, fy + face * 0.025, hz), 0.0085, 0.05, "y", segs=8)           # spindle
        ss.box((lx - 0.055, fy + face * 0.047, hz), (0.15, 0.015, 0.02))          # lever (points to hinge)
        ss.cyl((lx - 0.13, fy + face * 0.047, hz), 0.0105, 0.015, "y", segs=10)
    ss.finish(f"{n}_Hardware", col, stainless, hinge)
    glass_m = Geo()
    glass_m.box((cx, ly, scz), (sx + 0.004, lt - 0.012, sz + 0.004))
    glass_m.finish(f"{n}_Glass", col, glass, hinge)

    return root, [o for o in root.children_recursive if o.type == "MESH"]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
