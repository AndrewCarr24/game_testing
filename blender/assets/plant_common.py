"""Shared building blocks for the plant_* assets (not an asset itself): lumpy foliage
blobs, tapered limbs, small mesh helpers. Outdoor materials come from lib/outdoor.py."""
import importlib
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, outdoor  # noqa: E402

importlib.reload(common)
importlib.reload(outdoor)


# ------------------------------------------------------------------ noise
class Lump:
    """Smooth 3D pseudo-noise in [-1, 1] (a few random sines), deterministic per seed."""

    def __init__(self, rng, freq=1.0):
        self.w = [(rng.uniform(0.6, 1.6) * freq * rng.choice((-1, 1)),
                   rng.uniform(0.6, 1.6) * freq * rng.choice((-1, 1)),
                   rng.uniform(0.6, 1.6) * freq * rng.choice((-1, 1)),
                   rng.uniform(0, 6.28)) for _ in range(4)]

    def __call__(self, x, y, z):
        return sum(math.sin(a * x + b * y + c * z + ph) for a, b, c, ph in self.w) / 4.0 * 1.35


# ------------------------------------------------------------------ blobs
def blob(bm, centre, radii, rng, subdiv=2, lump=0.18, jitter=0.07, flat_bottom=0.6, tilt=None,
         freq=1.3, mat_index=0):
    """A lumpy ellipsoid (foliage mass). flat_bottom < 1 squashes the lower half so
    crowns have a flatter underside and read as layers. Returns the new faces."""
    geom = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    verts = [v for v in geom["verts"]]
    noise = Lump(rng, freq)
    rot = Matrix.Identity(3)
    if tilt:
        rot = Matrix.Rotation(tilt[0], 3, "X") @ Matrix.Rotation(tilt[1], 3, "Y")
    for v in verts:
        d = v.co.normalized()
        f = 1.0 + lump * noise(d.x * 2, d.y * 2, d.z * 2) + jitter * rng.uniform(-1, 1)
        x, y, z = d.x * f, d.y * f, d.z * f
        if z < 0:
            z *= flat_bottom
        p = rot @ Vector((x * radii[0], y * radii[1], z * radii[2]))
        v.co = p + Vector(centre)
    faces = list({f for v in verts for f in v.link_faces})
    for f in faces:
        f.material_index = mat_index
        f.smooth = True
    return faces


def cluster(bm, centre, radii, rng, sats=10, sat_size=(0.3, 0.45), lump=0.22, jitter=0.10,
            flat_bottom=0.55, subdiv=2, up_bias=0.35, sat_lump=0.2):
    """A foliage mass: one lumpy main body plus `sats` smaller lobes budding off its
    surface (mostly on top and the sides), so the silhouette is cauliflower-like leaf
    clusters rather than one smooth pillow."""
    c = Vector(centre)
    faces = blob(bm, c, radii, rng, subdiv=subdiv, lump=lump, jitter=jitter, flat_bottom=flat_bottom)
    surf = list({v for f in faces for v in f.verts})        # the displaced surface, so lobes stay attached
    mean = sum(radii) / 3
    for _ in range(sats):
        for _try in range(20):
            v = rng.choice(surf)
            rel = v.co - c
            if rel.z / max(radii[2], 1e-6) > -0.35:
                break
        pos = c.lerp(v.co, rng.uniform(0.85, 1.0))
        pos.z += up_bias * 0.25 * mean * 0.3
        k = rng.uniform(*sat_size)
        blob(bm, pos, (mean * k * rng.uniform(0.9, 1.15), mean * k * rng.uniform(0.9, 1.15), mean * k),
             rng, subdiv=1, lump=sat_lump, jitter=0.12, flat_bottom=0.6)


# ------------------------------------------------------------------ limbs
def spline(pts, per=4):
    """Catmull-Rom through pts."""
    q = [Vector(pts[0])] + [Vector(p) for p in pts] + [Vector(pts[-1])]
    out = []
    for i in range(1, len(q) - 2):
        p0, p1, p2, p3 = q[i - 1], q[i], q[i + 1], q[i + 2]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(Vector(pts[-1]))
    return out


def sweep(bm, pts, radii, sides=6, lobe=0.0, lobes=3, twist=0.0, noise=0.0, rng=None,
          tip=True, mat_index=0):
    """Tapered (optionally fluted / twisted) tube along pts; the end closes to a point."""
    n = len(pts)
    tang = [(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(n)]
    ref = Vector((1, 0, 0)) if abs(tang[0].x) < 0.9 else Vector((0, 1, 0))
    nrm = (ref - tang[0] * ref.dot(tang[0])).normalized()
    rings = []
    for i in range(n):
        t = tang[i]
        nrm = (nrm - t * nrm.dot(t)).normalized()
        bi = t.cross(nrm)
        s = i / max(n - 1, 1)
        ring = []
        for k in range(sides):
            th = 2 * math.pi * k / sides
            f = 1 + lobe * math.sin(lobes * th + twist * s * 6.283)
            if noise and rng:
                f += noise * (rng.random() - 0.5)
            ring.append(bm.verts.new(pts[i] + (nrm * math.cos(th) + bi * math.sin(th)) * radii[i] * f))
        rings.append(ring)
    faces = []
    for i in range(n - 1):
        for k in range(sides):
            j = (k + 1) % sides
            faces.append(bm.faces.new((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k])))
    if tip:
        tv = bm.verts.new(pts[-1] + tang[-1] * radii[-1] * 1.2)
        for k in range(sides):
            faces.append(bm.faces.new((rings[-1][k], rings[-1][(k + 1) % sides], tv)))
    for f in faces:
        f.material_index = mat_index
        f.smooth = True
    return rings


def taper(n, r0, r1, flare=0.0, flare_len=0.2):
    out = []
    for i in range(n):
        t = i / max(n - 1, 1)
        out.append(r0 + (r1 - r0) * t ** 0.85 + flare * math.exp(-t / flare_len))
    return out


# ------------------------------------------------------------------ misc
def new_asset(name):
    col = common.fresh_collection(name)
    root = common.empty(name, col)
    return col, root


def finish(ob, tile=None):
    if tile:
        common.box_uv(ob, tile=tile)
    return ob


def parts_of(root):
    return [o for o in root.children_recursive if o.type == "MESH"]


def rng_for(seed):
    return random.Random(seed)
