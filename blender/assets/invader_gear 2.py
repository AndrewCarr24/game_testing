"""The invader's gear: weapons (rifle, pistol, bat, knife), head attachments (mask, cap,
hood) and the gear material (one palette atlas: every part's UVs sit in its colour cell).

Weapons are modelled in their own frame: origin = the grip (where the fist closes),
-Y = forward (muzzle / the direction a gun points), +Z = up (the top of the gun; for the
bat and the knife, along the handle out of the thumb side of the fist: the tip is +Z).
glTF: -Y -> +Z, +Z -> +Y. A weapon parented to a socket with an identity local transform
is held. Markers (empties): <Weapon>_Muzzle, <Weapon>_Tip.

Head attachments are SDF shells around the body field's head (invader_body), so they fit
it; they're skinned (Head, the hood also Neck / Chest).
"""
import math

import bmesh
import bpy
import numpy as np

import invader_body as body

# palette cells (8 x 8 on the atlas): name -> (base colour sRGB, roughness, metallic)
SWATCH = dict(
    gun_black=((0.045, 0.047, 0.05), 0.55, 0.15),
    gun_polymer=((0.07, 0.07, 0.068), 0.75, 0.0),
    gun_metal=((0.1, 0.1, 0.105), 0.4, 0.85),
    optic_glass=((0.05, 0.08, 0.1), 0.1, 0.3),
    bat_wood=((0.62, 0.44, 0.27), 0.55, 0.0),
    bat_tape=((0.06, 0.06, 0.06), 0.85, 0.0),
    knife_steel=((0.62, 0.63, 0.64), 0.25, 1.0),
    knife_handle=((0.08, 0.075, 0.07), 0.7, 0.0),
    mask_white=((0.76, 0.74, 0.69), 0.45, 0.0),
    mask_inner=((0.16, 0.15, 0.14), 0.8, 0.0),
    cap_fabric=((0.075, 0.078, 0.085), 0.9, 0.0),
    cap_brim=((0.065, 0.068, 0.072), 0.85, 0.0),
    hood_fabric=((0.055, 0.056, 0.06), 0.92, 0.0),
)
NAMES = list(SWATCH)
CELLS = 8


def cell_uv(name):
    i = NAMES.index(name)
    return ((i % CELLS) + 0.5) / CELLS, 1.0 - ((i // CELLS) + 0.5) / CELLS


def atlas(size=256):
    """(albedo sRGB, ORM) float arrays (size, size, 3), row 0 = top (v = 1)."""
    A = np.zeros((size, size, 3), np.float32)
    O = np.zeros((size, size, 3), np.float32)
    cs = size // CELLS
    yy, xx = np.mgrid[0:cs, 0:cs]
    rng = np.random.default_rng(5)
    for i, n in enumerate(NAMES):
        col, rough, metal = SWATCH[n]
        r, c = i // CELLS, i % CELLS
        noise = 1.0 + 0.04 * (rng.random((cs, cs)) - 0.5)
        A[r * cs:(r + 1) * cs, c * cs:(c + 1) * cs] = np.array(col)[None, None] * noise[..., None]
        O[r * cs:(r + 1) * cs, c * cs:(c + 1) * cs] = (1.0, rough, metal)
    return A, O


# ---------------------------------------------------------------- mesh builders

class Mesh:
    def __init__(self):
        self.v, self.f, self.s = [], [], []

    def add(self, verts, faces, swatch):
        o = len(self.v)
        self.v += [tuple(map(float, p)) for p in verts]
        self.f += [tuple(i + o for i in fc) for fc in faces]
        self.s += [swatch] * len(faces)
        return self

    def box(self, c, size, swatch, rot=None, taper=(1.0, 1.0)):
        """Box centred at c; taper scales the +y end's x and z."""
        hx, hy, hz = (np.asarray(size) / 2)
        pts = []
        for z in (-hz, hz):
            for y in (-hy, hy):
                for x in (-hx, hx):
                    k = taper if y > 0 else (1.0, 1.0)
                    pts.append((x * k[0], y, z * k[1]))
        pts = np.array(pts)
        if rot is not None:
            pts = pts @ np.asarray(rot).T
        pts += np.asarray(c)
        F = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
        return self.add(pts, F, swatch)

    def tube(self, a, b, ra, rb, swatch, sides=10, caps=True, rot0=0.0):
        a, b = np.asarray(a, float), np.asarray(b, float)
        ax = b - a
        ax /= np.linalg.norm(ax)
        u = np.cross(ax, [0, 0, 1] if abs(ax[2]) < 0.9 else [1, 0, 0])
        u /= np.linalg.norm(u)
        w = np.cross(ax, u)
        pts = []
        for c, r in ((a, ra), (b, rb)):
            for i in range(sides):
                t = 2 * math.pi * i / sides + rot0
                pts.append(c + r * (math.cos(t) * u + math.sin(t) * w))
        F = [(i, (i + 1) % sides, sides + (i + 1) % sides, sides + i) for i in range(sides)]
        if caps:
            F += [tuple(range(sides))[::-1], tuple(range(sides, 2 * sides))]
        return self.add(pts, F, swatch)

    def lathe(self, profile, swatch, sides=12, axis=2):
        """profile: [(along, radius)] along the local axis (2 = z)."""
        pts = []
        for h, r in profile:
            for i in range(sides):
                t = 2 * math.pi * i / sides
                p = [r * math.cos(t), r * math.sin(t)]
                q = [0.0, 0.0, 0.0]
                q[axis] = h
                others = [k for k in range(3) if k != axis]
                q[others[0]], q[others[1]] = p
                pts.append(q)
        n = len(profile)
        F = []
        for j in range(n - 1):
            for i in range(sides):
                a, b = j * sides + i, j * sides + (i + 1) % sides
                F.append((a, b, b + sides, a + sides))
        F.append(tuple(range(sides))[::-1])
        F.append(tuple(range((n - 1) * sides, n * sides)))
        return self.add(pts, F, swatch)


def rx(deg):
    return body.rot_x(deg)


def rifle():
    """A plain carbine, ~0.92 m. Bore at z = 0.075; the butt at y = +0.33."""
    m = Mesh()
    bz = 0.075
    m.box((0, -0.01, bz), (0.036, 0.22, 0.07), "gun_black")                       # receiver
    m.box((0, -0.27, bz), (0.05, 0.3, 0.05), "gun_polymer", taper=(1.0, 1.0))     # handguard
    m.tube((0, -0.42, bz), (0, -0.56, bz), 0.009, 0.009, "gun_metal", sides=8)   # barrel
    m.tube((0, -0.56, bz), (0, -0.6, bz), 0.012, 0.012, "gun_metal", sides=8)    # muzzle device
    m.box((0, -0.08, 0.118), (0.022, 0.3, 0.012), "gun_black")                    # top rail
    m.tube((0, -0.03, 0.15), (0, 0.06, 0.15), 0.016, 0.018, "gun_black", sides=10)   # optic
    m.box((0, -0.035, 0.13), (0.02, 0.03, 0.03), "gun_black")
    m.tube((0, -0.03, 0.15), (0, -0.031, 0.15), 0.013, 0.013, "optic_glass", sides=10)
    m.tube((0, 0.10, 0.088), (0, 0.24, 0.088), 0.016, 0.016, "gun_black", sides=8)    # buffer tube
    m.box((0, 0.27, 0.07), (0.04, 0.12, 0.085), "gun_polymer", taper=(1.0, 1.25))  # stock
    m.box((0, 0.335, 0.07), (0.044, 0.012, 0.11), "gun_polymer")                  # butt pad
    m.box((0, 0.012, -0.005), (0.03, 0.036, 0.1), "gun_polymer", rot=rx(-18))      # pistol grip
    m.box((0, -0.075, -0.02), (0.024, 0.065, 0.14), "gun_black", rot=rx(10))       # magazine
    m.box((0, -0.02, 0.03), (0.006, 0.05, 0.03), "gun_black")                     # trigger guard
    m.box((0, -0.385, 0.112), (0.006, 0.012, 0.03), "gun_black")                  # front sight
    return m, dict(muzzle=(0, -0.6, bz), foregrip=(0, -0.29, bz), butt=(0, 0.34, 0.07), sight=(0, -0.03, 0.15))


def pistol():
    m = Mesh()
    m.box((0, -0.065, 0.06), (0.028, 0.19, 0.034), "gun_black")                   # slide
    m.box((0, -0.06, 0.034), (0.026, 0.16, 0.02), "gun_polymer")                  # frame
    m.box((0, 0.005, -0.012), (0.03, 0.045, 0.1), "gun_polymer", rot=rx(-16))      # grip
    m.box((0, -0.04, 0.012), (0.006, 0.045, 0.022), "gun_polymer")                # trigger guard
    m.tube((0, -0.16, 0.06), (0, -0.162, 0.06), 0.005, 0.005, "gun_metal", sides=6)
    return m, dict(muzzle=(0, -0.162, 0.06), sight=(0, -0.06, 0.08))


def bat():
    m = Mesh()
    prof = [(-0.095, 0.0), (-0.094, 0.018), (-0.085, 0.024), (-0.075, 0.016), (-0.06, 0.0135), (0.15, 0.0135),
            (0.3, 0.018), (0.45, 0.027), (0.58, 0.032), (0.72, 0.033), (0.745, 0.028), (0.752, 0.0)]
    m.lathe(prof, "bat_wood", sides=12)
    # grip tape over the handle (a slightly wider sleeve)
    m.lathe([(-0.074, 0.0), (-0.073, 0.0148), (0.12, 0.0148), (0.121, 0.0)], "bat_tape", sides=12)
    return m, dict(tip=(0, 0, 0.74))


def knife():
    m = Mesh()
    m.box((0, 0, -0.005), (0.022, 0.03, 0.115), "knife_handle")
    m.box((0, 0, 0.058), (0.026, 0.045, 0.008), "knife_steel")                    # guard
    # blade: a flat wedge along +z, edge toward -y
    pts = [(-0.002, 0.012, 0.062), (0.002, 0.012, 0.062), (-0.002, -0.016, 0.062), (0.002, -0.016, 0.062),
           (-0.0015, 0.01, 0.2), (0.0015, 0.01, 0.2), (0.0, -0.004, 0.235)]
    F = [(0, 2, 3, 1), (0, 1, 5, 4), (2, 6, 3), (0, 4, 6, 2), (1, 3, 6, 5), (4, 5, 6)]
    m.add(pts, F, "knife_steel")
    return m, dict(tip=(0, -0.004, 0.235))


WEAPONS = dict(Rifle=rifle, Pistol=pistol, Bat=bat, Knife=knife)


def mesh_object(name, m, col, mat, parent=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(m.v, [], m.f)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    me.materials.append(mat)
    uv = me.uv_layers.new(name="UVMap")
    data = np.zeros(len(me.loops) * 2)
    for poly, sw in zip(me.polygons, m.s):
        u, v = cell_uv(sw)
        for li in poly.loop_indices:
            data[2 * li], data[2 * li + 1] = u, v
    uv.data.foreach_set("uv", data)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = False
    return ob


# ---------------------------------------------------------------- head attachments (SDF shells)

def _head_field(L, p):
    prims = [q for q in body.body_prims(L, p) if q["bone"] in ("Head", "Neck") and q.get("op", "u") == "u"]
    return prims


def _shell_mesh(fn, lo, hi, h):
    """Isosurface of fn(points) on a grid -> (verts, quads)."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    n = np.ceil((hi - lo) / h).astype(int) + 1
    ax = [lo[i] + h * np.arange(n[i]) for i in range(3)]
    X, Y, Z = np.meshgrid(*ax, indexing="ij")
    P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    d = fn(P).reshape(X.shape).astype(np.float32)
    return body.mesh_grid(d, lo, h)


def head_attachments(L, p):
    """{name: (verts, quads, swatch)} in the model frame."""
    prims = _head_field(L, p)

    def head_d(P):
        d, _ = body.eval_points(prims, P)
        return d

    out = {}
    lo, hi = (-0.13, -0.17, 1.5), (0.13, 0.15, 1.86)
    eyes = [L["eye_L"], L["eye_R"]]

    # the mask: a 4 mm shell 6 mm off the face, front only, eye holes, a few breathing holes
    def mask(P):
        d = head_d(P)
        shell = np.maximum(d - 0.0095, -(d - 0.0055))
        y, z = P[:, 1], P[:, 2]
        front = np.maximum(y + 0.03, -(np.minimum(z - 1.565, 1.775 - z)))   # y < -0.03, z in range
        # oval outline
        oval = np.sqrt((P[:, 0] / 0.078) ** 2 + ((z - 1.668) / 0.115) ** 2) - 1.0
        m = np.maximum(shell, np.maximum(front, oval * 0.05))
        for e in eyes:
            q = (P - e) / np.array([0.017, 0.05, 0.0105])
            m = np.maximum(m, -(np.linalg.norm(q, axis=1) - 1.0) * 0.01)
        return m
    v, f = _shell_mesh(mask, lo, hi, 0.002)
    out["Mask"] = (v, f, "mask_white")

    # the cap: crown shell above the brow line + a brim
    def cap(P):
        d = head_d(P)
        shell = np.maximum(d - 0.012, -(d - 0.004))
        z, y = P[:, 2], P[:, 1]
        cut = 1.722 - z - 0.012 * (y + 0.1) / 0.2      # the band dips a little toward the back
        crown = np.maximum(shell, cut)
        b = body.ell((0, -0.105, 1.722), (0.085, 0.075, 0.006))
        brim = body._sd(P, b)
        brim = np.maximum(brim, y + 0.06)               # only in front
        return np.minimum(crown, brim)
    v, f = _shell_mesh(cap, lo, (0.13, 0.15, 1.87), 0.0025)
    out["Cap"] = (v, f, "cap_fabric")

    # the hood: a loose shell over head and neck with a face opening, ending on the shoulders
    def hood(P):
        d = head_d(P)
        shell = np.maximum(d - 0.024, -(d - 0.01))
        z, y = P[:, 2], P[:, 1]
        opening = np.sqrt((P[:, 0] / 0.07) ** 2 + ((z - 1.655) / 0.095) ** 2) - 1.0
        face = np.maximum(opening * 0.05, y + 0.02)        # the opening in front (negative inside)
        bottom = 1.5 - z
        return np.maximum(np.maximum(shell, -face), bottom)
    v, f = _shell_mesh(hood, (-0.15, -0.17, 1.45), (0.15, 0.17, 1.86), 0.003)
    out["Hood"] = (v, f, "hood_fabric")
    return out
