"""Guest floor lamp: weighted black disc base with a chamfered edge and a brass foot
switch, a slim brass stem with a collar, and an open glowing linen drum shade (a
real wall with thickness, brass-wire rims top and bottom) hung on a three-arm brass
spider over a socket and bulb. Origin is the floor centre; shade centre at
z = height - shade_h / 2 (put a point light there)."""
import importlib
import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestFloorLamp"

P = dict(name=NAME, height=1.55, shade_r=0.21, shade_h=0.34)


def drum(r_out, r_in, h, seg):
    """Open tube (outer and inner wall, annular lips top and bottom), centred on the
    origin, axis z."""
    bm = bmesh.new()
    rings = []
    for r, z in ((r_out, -h / 2), (r_out, h / 2), (r_in, h / 2), (r_in, -h / 2)):
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg), z))
                      for k in range(seg)])
    for a in range(4):
        ra, rb = rings[a], rings[(a + 1) % 4]
        for k in range(seg):
            k1 = (k + 1) % seg
            bm.faces.new((ra[k], ra[k1], rb[k1], rb[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def circle(r, z, seg=40):
    return [(r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg), z) for k in range(seg)]


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402  (react definitions, prompts/interactivity.md)

importlib.reload(ix_common)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    black, brass = guest_mats.black(), guest_mats.brass()
    shade_mat = guest_mats.materials.emissive("M_Lampshade_Linen", (0.95, 0.82, 0.62), 0.9)
    bulb_mat = guest_mats.materials.emissive("M_LampBulb", (1.0, 0.92, 0.74), 6.0)
    own = (col, root, n)
    A = guest_mats.add
    H, sr, sh = p["height"], p["shade_r"], p["shade_h"]
    zs0, zs1 = H - sh, H                                 # shade bottom, top

    # base: weighted disc, chamfered top edge, brass collar and a foot switch
    A(own, "Base", guest_mats.cyl_bmesh(0.15, 0.025, r2=0.142, seg=32), black, (0, 0, 0.0125), 0.003)
    A(own, "BaseCollar", guest_mats.cyl_bmesh(0.016, 0.014, r2=0.012, seg=16), brass, (0, 0, 0.032), 0)
    A(own, "Switch", guest_mats.cyl_bmesh(0.011, 0.008, seg=12), brass, (0.095, 0.0, 0.0285), 0)

    # stem up to the socket, collar under the shade
    z_sock = zs1 - 0.16                                  # socket top (bulb sits above it)
    A(own, "Stem", guest_mats.cyl_bmesh(0.008, z_sock - 0.06 - 0.039, seg=12), brass,
      (0, 0, 0.039 + (z_sock - 0.06 - 0.039) / 2), 0)
    A(own, "Collar", guest_mats.cyl_bmesh(0.013, 0.02, seg=16), brass, (0, 0, zs0 - 0.03), 0)
    A(own, "Socket", guest_mats.cyl_bmesh(0.017, 0.06, r2=0.015, seg=16), brass, (0, 0, z_sock - 0.03), 0)
    # bulb: a small globe on its neck
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.03)
    for v in bm.verts:
        if v.co.z < 0:
            v.co.x *= 0.75 + 0.25 * (1 + v.co.z / 0.03)
            v.co.y *= 0.75 + 0.25 * (1 + v.co.z / 0.03)
    A(own, "Bulb", bm, bulb_mat, (0, 0, z_sock + 0.032), 0)

    # spider: hub on the socket, three arms up to the top ring
    hub_z = z_sock - 0.012
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5
        pts = [(0.019 * math.cos(a), 0.019 * math.sin(a), hub_z),
               ((sr - 0.004) * math.cos(a), (sr - 0.004) * math.sin(a), zs1 - 0.006)]
        common.tube_object(f"{n}_Spider_Piping{k}", pts, 0.0022, col, brass, root, closed=False, profile_res=0)
    A(own, "Hub", guest_mats.cyl_bmesh(0.022, 0.008, seg=16), brass, (0, 0, hub_z), 0)

    # shade: open drum with wall thickness, brass wire rims
    shade = common.mesh_object(f"{n}_Shade", drum(sr, sr - 0.003, sh - 0.006, 40), col, shade_mat, root)
    shade.location = (0, 0, H - sh / 2)
    common.box_uv(shade, 0.25)
    for nm, z in (("RimTop", zs1 - 0.004), ("RimBottom", zs0 + 0.004)):
        common.tube_object(f"{n}_{nm}_Piping", circle(sr + 0.0005, z, 32), 0.0032, col, brass, root, closed=True,
                           profile_res=0)
    for ob in root.children:
        if ob.type == "MESH" and not ob.data.uv_layers:
            common.box_uv(ob, 0.5)
    parts = guest_mats.consolidate(root, max_dim=0.2)
    ix_common.tag_emissive(root)   # interactivity: glowing parts follow the room's light switch
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
