"""Guest wardrobe: a floor-to-near-ceiling run of six reeded pale-oak doors over a
sage linen-wrapped carcass. Each door is a flat oak leaf with a plain border and a
field of half-round reeds; the doors overlay the carcass with 3 mm reveals (dark
interior behind them), meeting pairs carry slim brass bar pulls on stand-offs, and
the run floats on a recessed black plinth. Faces -Y; origin is the floor centre."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestWardrobe"

P = dict(name=NAME, width=3.6, depth=0.62, height=2.7, plinth_h=0.09, doors=6, slat=0.032, slat_gap=0.008)


# T_Guest_Oak_BaseColor is a Poly Haven oak veneer scan (blender/tools/polyhaven_textures.py),
# rotated so its grain runs along u, and whose 1024 image is meant to cover OAK_TILE metres; the
# guest_* furniture maps it through grain_uv so the grain follows each board.
OAK_TILE = 1.5
OAK_GRAIN_ON_V = False         # the oak veneer scan is rotated: grain along u


def grain_uv(ob, tile=OAK_TILE, along=None, grain_on_v=OAK_GRAIN_ON_V):
    """Box projection with the grain along `along` ("x"/"y"/"z") wherever that axis lies
    in the face's plane, else along the mesh's longest axis available on the face (like
    common.box_uv). grain_on_v puts the grain on v (for textures scanned that way)."""
    me = ob.data
    dims = [max(v.co[a] for v in me.vertices) - min(v.co[a] for v in me.vertices) for a in range(3)]
    ga = "xyz".index(along) if along else None
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        n = [abs(c) for c in poly.normal]
        na = n.index(max(n))
        a, b = [i for i in range(3) if i != na]      # a = grain axis
        if b == ga or (ga not in (a, b) and dims[b] > dims[a]):
            a, b = b, a
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            g, c = co[a] / tile, co[b] / tile
            uv.data[li].uv = (c, g) if grain_on_v else (g, c)


def fix_oak(root, skip=()):
    """grain_uv on every pale-oak mesh under `root` (names in `skip` keep their UVs)."""
    for ob in root.children_recursive:
        if (ob.type == "MESH" and ob.data.materials and ob.data.materials[0] is not None
                and ob.data.materials[0].name == "M_Oak_Light" and ob.name not in skip):
            grain_uv(ob)


def reeds(bm, x0, x1, z0, z1, y_face, pitch, proud, seg=4):
    """Half-round reeds across [x0, x1] standing `proud` off the face plane y_face
    (toward -Y), running from z0 to z1, with end caps: one strip of quads."""
    n = max(1, round((x1 - x0) / pitch))
    w = (x1 - x0) / n
    prof = []
    for k in range(n):
        for j in range(seg):
            t = j / seg
            prof.append((x0 + (k + t) * w, -proud * math.sin(math.pi * t) ** 0.6))
    prof.append((x1, 0.0))
    lo = [bm.verts.new((x, y_face + dy, z0)) for x, dy in prof]
    hi = [bm.verts.new((x, y_face + dy, z1)) for x, dy in prof]
    for i in range(len(prof) - 1):
        bm.faces.new((lo[i], lo[i + 1], hi[i + 1], hi[i]))
    # end caps (the reeds' profile at the top and bottom of the field)
    for k in range(n):
        idx = list(range(k * seg, k * seg + seg + 1))
        bm.faces.new([hi[i] for i in idx])
        bm.faces.new([lo[i] for i in reversed(idx)])


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    oak, brass, black, sage = guest_mats.oak(), guest_mats.brass(), guest_mats.black(), guest_mats.sage()
    own = (col, root, n)
    A = guest_mats.add
    W, D, H, ph = p["width"], p["depth"], p["height"], p["plinth_h"]
    nd = p["doors"]
    g = 0.003                                   # reveal between doors
    dt = 0.020                                  # door leaf thickness
    pitch = p["slat"] + p["slat_gap"] * 0.25    # reed pitch (~34 mm)
    y_front = -D / 2 + 0.012 + dt               # carcass front plane (doors overlay it)

    # ---- recessed black plinth, sage carcass (sides, top), dark interior behind the reveals
    A(own, "Plinth", common.box_bmesh((W - 0.10, D - 0.08, ph + 0.01)), black, (0, 0.02, (ph + 0.01) / 2), 0)
    cd = D / 2 - y_front
    A(own, "Carcass", common.box_bmesh((W, cd, H - ph)), sage, (0, y_front + cd / 2, ph + (H - ph) / 2),
      0.003, tile=0.25)
    A(own, "Interior", common.box_bmesh((W - 0.02, 0.004, H - ph - 0.02)), black,
      (0, y_front - 0.002, ph + (H - ph) / 2), 0)

    # ---- doors: oak leaves (one mesh) and their reed fields (one mesh)
    dw = (W - (nd - 1) * g) / nd
    z0, z1 = ph + g, H - g
    leaves = bmesh.new()
    field = bmesh.new()
    stile, rail = 0.034, 0.055
    y_leaf = y_front - dt                       # door face plane
    for d in range(nd):
        xa = -W / 2 + d * (dw + g)
        xc = xa + dw / 2
        bmesh.ops.create_cube(leaves, size=1.0, matrix=Matrix.Translation((xc, y_front - dt / 2, (z0 + z1) / 2))
                              @ Matrix.Diagonal((dw, dt, z1 - z0, 1.0)))
        reeds(field, xa + stile, xa + dw - stile, z0 + rail, z1 - rail, y_leaf, pitch, 0.012)
    lv = common.mesh_object(f"{n}_Doors", leaves, col, oak, root)
    common.add_bevel(lv, 0.0025, segments=2)
    grain_uv(lv, along="z")
    fl = common.mesh_object(f"{n}_Reeds", field, col, oak, root)
    grain_uv(fl, along="z")

    # ---- brass bar pulls on the stiles at each meeting pair, on round stand-offs
    pr, stand = 0.0065, 0.032
    zc, half = 1.12, 0.30
    pulls = []
    for d in range(nd):
        xa = -W / 2 + d * (dw + g)
        meet = xa + dw if d % 2 == 0 else xa          # meeting edge of the pair
        sx = -1 if d % 2 == 0 else 1
        px = meet + sx * (stile / 2 + 0.002)
        ya, yb = y_leaf, y_leaf - stand
        pts = common.fillet_polyline([(px, ya, zc - half), (px, yb, zc - half), (px, yb, zc + half),
                                      (px, ya, zc + half)], 0.014, segments=4, closed=False)
        pulls.append(common.tube_object(f"{n}_Pull_{d}", pts, pr, col, brass, root, closed=False, profile_res=2))
    for pl in pulls:
        common.box_uv(pl, 0.5)
    parts = guest_mats.consolidate(root, max_dim=0.7)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
