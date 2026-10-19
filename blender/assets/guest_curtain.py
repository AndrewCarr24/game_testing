"""Guest curtain panel: a full-height ripple-fold linen panel (a stiffened, doubled
heading band at the top and a weighted, doubled hem that just kisses the floor)
hung by black carriers at every back crest from a slim black rod with end finials.
1.3 m wide gathered, 3.65 m drop. Faces -Y (towards the room); the rod is at the
back, origin at floor centre of the panel."""
import importlib
import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestCurtain"

P = dict(name=NAME, width=1.3, drop=3.65, folds=7, amp=0.07, thick=0.012)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    linen = guest_mats.materials.fabric("M_Fabric_Curtain", (0.60, 0.57, 0.50), roughness=0.95)
    black = guest_mats.black()
    W, Hh, F, amp, th = p["width"], p["drop"], p["folds"], p["amp"], p["thick"]
    nx = F * 6
    hem, head = 0.09, 0.075                     # doubled hem and heading band heights
    step = 0.004                                # the small ledge where a band starts
    zs = [0.0, hem, hem + step, 0.9, 1.8, 2.7, Hh - head - step, Hh - head, Hh]

    def thick(z):
        return th * (1.7 if z <= hem + 1e-6 else 1.55 if z >= Hh - head - 1e-6 else 1.0)

    def wave(u, v):
        a = amp * (0.75 + 0.35 * v) * (1 + 0.15 * math.sin(7 * u + 3 * v))
        return -a * 0.5 * (1 - math.cos(2 * math.pi * F * u + 0.4 * v))

    bm = bmesh.new()
    front, back = {}, {}
    nz = len(zs) - 1
    for i in range(nx + 1):
        u = i / nx
        for j, z in enumerate(zs):
            v = z / Hh                          # 0 at the floor
            y = wave(u, v)
            x = (u - 0.5) * W * (1 + 0.02 * math.sin(11 * v))
            t = thick(z)
            front[i, j] = bm.verts.new((x, y - t / 2, z))
            back[i, j] = bm.verts.new((x, y + t / 2, z))
    for i in range(nx):
        for j in range(nz):
            bm.faces.new([front[i, j], front[i, j + 1], front[i + 1, j + 1], front[i + 1, j]])
            bm.faces.new([back[i, j], back[i + 1, j], back[i + 1, j + 1], back[i, j + 1]])
    for j in range(nz):
        bm.faces.new([front[0, j], back[0, j], back[0, j + 1], front[0, j + 1]])
        bm.faces.new([front[nx, j], front[nx, j + 1], back[nx, j + 1], back[nx, j]])
    for i in range(nx):
        bm.faces.new([front[i, nz], front[i + 1, nz], back[i + 1, nz], back[i, nz]])
        bm.faces.new([front[i, 0], back[i, 0], back[i + 1, 0], front[i + 1, 0]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    cur = common.mesh_object(f"{n}_Panel", bm, col, linen, root)
    common.box_uv(cur, 0.5)

    # rod with end finials, a carrier from every back crest of the heading up to it
    z_rod, y_rod, r_rod = Hh + 0.04, 0.03, 0.011
    hw = W / 2 + 0.07
    rod = common.mesh_object(f"{n}_Rod", guest_mats.cyl_bmesh(r_rod, 2 * hw, seg=12, axis="x"), col, black, root)
    rod.location = (0, y_rod, z_rod)
    common.box_uv(rod, 0.5)
    hw_bits = bmesh.new()
    for sx in (-1, 1):
        for r, ln, off in ((0.015, 0.012, 0.006), (0.012, 0.018, 0.021)):
            c = guest_mats.cyl_bmesh(r, ln, seg=12, axis="x")
            bmesh.ops.translate(c, verts=c.verts, vec=(sx * (hw + off), y_rod, z_rod))
            me = __import__("bpy").data.meshes.new("tmp")
            c.to_mesh(me)
            c.free()
            hw_bits.from_mesh(me)
            __import__("bpy").data.meshes.remove(me)
    for k in range(F + 1):
        u = k / F                                # back crests of the wave (y = 0)
        x = (u - 0.5) * W * (1 + 0.02 * math.sin(11))
        c = guest_mats.cyl_bmesh(0.0035, z_rod - (Hh - 0.02), seg=6)
        bmesh.ops.translate(c, verts=c.verts, vec=(x, th, (z_rod + Hh - 0.02) / 2))
        me = __import__("bpy").data.meshes.new("tmp")
        c.to_mesh(me)
        c.free()
        hw_bits.from_mesh(me)
        __import__("bpy").data.meshes.remove(me)
    bits = common.mesh_object(f"{n}_Carriers_Piping", hw_bits, col, black, root)
    common.box_uv(bits, 0.5)
    return root, [o for o in root.children_recursive if o.type == "MESH"]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
