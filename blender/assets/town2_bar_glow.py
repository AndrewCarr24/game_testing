"""Glow cards for the bar (town2_bar.py): the runtime has no bloom, so neon, bulbs and lamp cones
get soft halos drawn as alpha-blended emissive cards (material "Glow": one RGBA texture used as
both base colour and emission, alpha from the texture; no lightmap, no lights: emission x alpha
over what's behind). One draw call for every halo of the building. Hidden from the bakes: the
light itself comes from the lamps and the emitters.

The glow atlas (256 px, 4 x 4 cells of 64):
  row 0-1: radial halos (one per neon colour, warm bulb, white)
  row 2:   tube halos (a soft band across v: ribbons along neon strokes)
  row 3:   cone (bright at the top, fading down and to the sides), sun shaft"""
import math

import bmesh
import numpy as np
from mathutils import Vector

GLOW_N = 4
COLOURS = {"pink": (1.0, 0.16, 0.45), "green": (0.22, 1.0, 0.3), "blue": (0.16, 0.36, 1.0), "red": (1.0, 0.1, 0.05),
           "amber": (1.0, 0.5, 0.12), "white": (1.0, 0.86, 0.74), "purple": (0.6, 0.15, 1.0), "warm": (1.0, 0.66, 0.36)}
ORDER = ["pink", "green", "blue", "red", "amber", "white", "purple", "warm"]
CELLS = {}
for i, c in enumerate(ORDER):
    CELLS["halo_" + c] = (i % 4, i // 4)
for i, c in enumerate(["pink", "green", "blue", "red"]):
    CELLS["tube_" + c] = (i, 2)
CELLS["tube_amber"] = (0, 3)
CELLS["tube_white"] = (1, 3)
CELLS["cone_warm"] = (2, 3)
CELLS["cone_green"] = (3, 3)


def rect(cell, inset=0.06):
    c, r = cell
    d = 1.0 / GLOW_N
    return ((c + inset) * d, 1 - (r + 1 - inset) * d, (c + 1 - inset) * d, 1 - (r + inset) * d)


def texture(size=256):
    """RGBA (linear colour premultiplied by nothing: colour x intensity, alpha = the falloff)."""
    cs = size // GLOW_N
    out = np.zeros((size, size, 4), np.float32)
    yy, xx = np.mgrid[0:cs, 0:cs].astype(np.float32)
    u, v = (xx + 0.5) / cs, 1 - (yy + 0.5) / cs
    for name, (c, r) in CELLS.items():
        kind, col = name.split("_")
        rgb = np.array(COLOURS[col], np.float32)
        if kind == "halo":
            d = np.hypot(u - 0.5, v - 0.5) * 2
            a = np.clip(1 - d, 0, 1) ** 2.2
        elif kind == "tube":
            d = np.abs(v - 0.5) * 2
            a = np.clip(1 - d, 0, 1) ** 2.0
        else:   # cone: v = 1 top .. 0 bottom, u across; faint (smoke catching the light)
            a = 0.16 * np.clip(1 - np.abs(u - 0.5) * 2, 0, 1) ** 2.0 * (v ** 1.4) * np.clip((1 - v) * 8, 0, 1)
        cell = np.zeros((cs, cs, 4), np.float32)
        cell[..., :3] = rgb
        cell[..., 3] = a
        out[r * cs:(r + 1) * cs, c * cs:(c + 1) * cs] = cell
    return out


def _uvmap(cell, t_across_fn, t_along_fn=None):
    r = rect(CELLS[cell])

    def f(co, n):
        ta = t_across_fn(co)
        tl = 0.5 if t_along_fn is None else t_along_fn(co)
        return (r[0] + (r[2] - r[0]) * tl, r[1] + (r[3] - r[1]) * ta)
    return f


def ribbon(k, pts, normal, width, colour, closed=False):
    """A flat soft band along a stroke (in the plane facing `normal`), `width` across."""
    P = [Vector(p) for p in pts]
    if closed:
        P = P + [P[0]]
    if len(P) < 2:
        return
    nrm = Vector(normal).normalized()
    bm = bmesh.new()
    rows = []
    uvs = []
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)])
        if t.length < 1e-9:
            t = Vector((1, 0, 0))
        side = t.normalized().cross(nrm).normalized() * (width / 2)
        rows.append((bm.verts.new(p - side), bm.verts.new(p + side)))
    faces = []
    for i in range(len(rows) - 1):
        a0, a1 = rows[i]
        b0, b1 = rows[i + 1]
        try:
            faces.append(bm.faces.new([a0, b0, b1, a1]))
        except ValueError:
            pass
    r = rect(CELLS[f"tube_{colour}" if f"tube_{colour}" in CELLS else "tube_white"])
    # UV: across the band = 0 .. 1 in v (the falloff), u at the cell's middle
    lay = bm.loops.layers.uv.new("UVMap")
    left = {v for pair in rows for v in pair[:1]}
    for f in faces:
        for lp in f.loops:
            lp[lay].uv = ((r[0] + r[2]) / 2, r[1] if lp.vert in left else r[3])
    _add_uv_bm(k, bm, lay)


def _add_uv_bm(k, bm, lay):
    """Append a bmesh whose UVs are already set (loop layer `lay`) to the Glow bucket."""
    store = [[tuple(lp[lay].uv) for lp in f.loops] for f in bm.faces]
    counter = {"i": 0, "j": 0}

    def uvf(co, n):
        f = store[counter["i"]]
        val = f[counter["j"]]
        counter["j"] += 1
        if counter["j"] >= len(f):
            counter["j"] = 0
            counter["i"] += 1
        return val
    k.add(bm, "Glow", uv=uvf, lmw=0.0, vlit=True)


def halo(k, centre, size, colour, normal=None, crossed=3):
    """A soft round halo: one card facing `normal`, or `crossed` cards around z (seen from anywhere)."""
    c = Vector(centre)
    cell = f"halo_{colour}" if f"halo_{colour}" in CELLS else "halo_warm"
    r = rect(CELLS[cell])
    dirs = []
    if normal is not None:
        dirs = [Vector(normal).normalized()]
    else:
        dirs = [Vector((math.cos(math.pi * i / crossed), math.sin(math.pi * i / crossed), 0)) for i in range(crossed)]
        dirs.append(Vector((0, 0, 1)))
    for n in dirs:
        up = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))
        a = n.cross(up).normalized() * (size / 2)
        b = a.cross(n).normalized() * (size / 2)
        bm = bmesh.new()
        q = [bm.verts.new(c - a - b), bm.verts.new(c + a - b), bm.verts.new(c + a + b), bm.verts.new(c - a + b)]
        f = bm.faces.new(q)
        lay = bm.loops.layers.uv.new("UVMap")
        for lp, (uu, vv) in zip(f.loops, ((r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3]))):
            lp[lay].uv = (uu, vv)
        _add_uv_bm(k, bm, lay)


def cone(k, apex, height, r_top, r_bottom, colour="warm", planes=4):
    """A lamp's light cone as crossed vertical trapezoids (bright under the shade, fading down)."""
    a = Vector(apex)
    cell = f"cone_{colour}" if f"cone_{colour}" in CELLS else "cone_warm"
    r = rect(CELLS[cell])
    for i in range(planes):
        ang = math.pi * i / planes
        d = Vector((math.cos(ang), math.sin(ang), 0))
        bm = bmesh.new()
        q = [bm.verts.new(a - d * r_bottom - Vector((0, 0, height))), bm.verts.new(a + d * r_bottom - Vector((0, 0, height))),
             bm.verts.new(a + d * r_top), bm.verts.new(a - d * r_top)]
        f = bm.faces.new(q)
        lay = bm.loops.layers.uv.new("UVMap")
        for lp, (uu, vv) in zip(f.loops, ((r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3]))):
            lp[lay].uv = (uu, vv)
        _add_uv_bm(k, bm, lay)
