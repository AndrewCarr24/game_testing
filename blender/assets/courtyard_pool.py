"""Raised reflecting pool in honed limestone, built like the real thing: walls clad in
1.07 m panels standing on a recessed shadow-gap plinth, separate coping stones (eased
edges, 4 mm joints) that overhang the cladding outside and the water inside, a still
dark water surface just below the coping, and a head wall at the north end with a
recessed dark niche, a bronze spout lip and a thin sheet of water that leaves the lip
and curves down into the pool. Long axis along Y, head wall at +Y.

Also hosts `stone` / `slab_uv`, the limestone helpers the other courtyard stone pieces use.

Origin: floor centre of the footprint. Units are metres."""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import courtyard_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common
materials = cc.materials

NAME = "CourtyardPool"

P = dict(
    name=NAME,
    length=8.6,
    width=2.8,          # outer
    coping=0.30,
    height=0.42,        # rim height
    water_z=0.345,
    head_wall_t=0.50,
    head_wall_h=1.30,
    lip_z=1.02,         # spout lip height
    sheet_w=1.7,
    seed=11,
)


# ------------------------------------------------------------------ limestone pieces

# One stone of the shared limestone texture: its joints sit at u = 0.096 + 0.2i,
# v = 0.2j (UV units; 0.5 UV per metre at the native 2 m tile).
WIN = 0.176          # usable window inside a stone, UV units
NATIVE = 0.30        # UV per metre (0.5 is the paving's scale; a little larger reads as one big stone)


def tri(x):
    return 1 - abs((x % 2) - 1)


def grid_box_bmesh(size, counts, skip=()):
    """Box centred on the origin whose faces are split into counts = (nx, ny, nz)
    equal strips per axis (needed so mirrored UVs fold exactly on vertices)."""
    bm = bmesh.new()
    h = [s / 2 for s in size]
    for a in range(3):
        b, c = [k for k in range(3) if k != a]
        for sign in (-1, 1):
            if ("+" if sign > 0 else "-") + "xyz"[a] in skip:
                continue                       # face against the floor / another stone
            nb, nc = counts[b], counts[c]
            vs = []
            for i in range(nb + 1):
                row = []
                for j in range(nc + 1):
                    co = [0.0, 0.0, 0.0]
                    co[a] = sign * h[a]
                    co[b] = -h[b] + size[b] * i / nb
                    co[c] = -h[c] + size[c] * j / nc
                    row.append(bm.verts.new(co))
                vs.append(row)
            for i in range(nb):
                for j in range(nc):
                    q = [vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]]
                    bm.faces.new(q if sign > 0 else q[::-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def stone_counts(size, scale=None):
    return [max(1, round(s * (scale or NATIVE) / WIN)) for s in size]


def slab_uv(ob, rng, counts):
    """Limestone UVs that never cross a paving joint of the shared texture: each axis
    runs at (almost exactly) native scale, mirrored back and forth inside one stone of
    the texture, folding on the grid lines of the piece; each piece picks its own stone
    (tone variety)."""
    me = ob.data
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    lo = [min(v.co[a] for v in me.vertices) for a in range(3)]
    hi = [max(v.co[a] for v in me.vertices) for a in range(3)]
    dims = [max(hi[a] - lo[a], 1e-6) for a in range(3)]
    i, j = rng.randrange(5), rng.randrange(5)
    u0, v0 = 0.096 + 0.2 * i + 0.012, 0.2 * j + 0.012
    for poly in me.polygons:
        nn = [abs(c) for c in poly.normal]
        na = nn.index(max(nn))
        a, b = [k for k in range(3) if k != na]
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            fa = (co[a] - lo[a]) / dims[a] * counts[a]
            fb = (co[b] - lo[b]) / dims[b] * counts[b]
            uv.data[li].uv = (u0 + WIN * tri(fa), v0 + WIN * tri(fb))


def stone(name, size, loc, mat, col, parent, rng, bevel=0.004, seg=1, skip=("-z",)):
    """A limestone piece: grid box, mirrored single-stone UVs, eased edges."""
    counts = stone_counts(size)
    ob = common.mesh_object(name, grid_box_bmesh(size, counts, skip), col, mat, parent, smooth=False)
    ob.location = loc
    slab_uv(ob, rng, counts)
    if bevel:
        common.add_bevel(ob, bevel, segments=seg)
    return ob


def runs(total, target):
    """Split a length into equal pieces close to `target` long."""
    k = max(1, round(total / target))
    return [total / k] * k


# ------------------------------------------------------------------ build

def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rng = random.Random(p["seed"])
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    lime, water = cc.limestone_mat(), cc.water_mat()
    bronze = materials.bronze()
    dark = cc.soil_mat()
    glass = materials.glass("M_Courtyard_WaterSheet", tint=(0.80, 0.93, 0.95), alpha=0.42, roughness=0.05)

    L, W, c, H = p["length"], p["width"], p["coping"], p["height"]
    ht, hh = p["head_wall_t"], p["head_wall_h"]
    ct = 0.06                       # coping thickness
    ov_out, ov_in = 0.02, 0.03      # coping overhang outside / over the water
    gap = 0.004                     # stone joints
    toe = 0.035                     # recessed plinth height
    wall_t = c - ov_in              # cladding wall thickness under the coping
    y_s = -L / 2                    # south (outer) face
    y_h = L / 2 - ht                # head wall's water face
    zc = H - ct                     # coping underside

    # recessed plinth (shadow gap) under the cladding, all round the U of walls
    for side, sx in (("W", -1), ("E", 1)):
        stone(f"{n}_Plinth_{side}", (wall_t - 0.04, y_h - y_s - 0.02, toe),
              (sx * (W / 2 - ov_out - wall_t / 2), (y_s + y_h) / 2 + 0.01, toe / 2), lime, col, root, rng, bevel=0,
              skip=("-z", "+z"))
    stone(f"{n}_Plinth_S", (W - 2 * ov_out - 0.04, wall_t - 0.04, toe), (0, y_s + ov_out + wall_t / 2, toe / 2),
          lime, col, root, rng, bevel=0, skip=("-z", "+z"))

    # cladding panels and coping stones along the two long sides
    side_len = y_h - y_s
    for side, sx in (("W", -1), ("E", 1)):
        x_w = sx * (W / 2 - ov_out - wall_t / 2)
        x_c = sx * (W / 2 - c / 2)
        y = y_s
        for k, ln in enumerate(runs(side_len, 1.07)):
            stone(f"{n}_Clad_{side}{k}", (wall_t, ln - gap, zc - toe), (x_w, y + ln / 2, toe + (zc - toe) / 2),
                  lime, col, root, rng, bevel=0.003, skip=("-z", "+z"))
            stone(f"{n}_Coping_{side}{k}", (c, ln - gap, ct), (x_c, y + ln / 2, zc + ct / 2), lime, col, root, rng,
                  bevel=0.008, seg=2)
            y += ln
    # south end: cladding and coping between the side copings
    inner_w = W - 2 * c
    x = -inner_w / 2
    for k, ln in enumerate(runs(inner_w, 1.07)):
        stone(f"{n}_Clad_S{k}", (ln - gap, wall_t, zc - toe), (x + ln / 2, y_s + ov_out + wall_t / 2, toe + (zc - toe) / 2),
              lime, col, root, rng, bevel=0.003, skip=("-z", "+z"))
        stone(f"{n}_Coping_S{k}", (ln - gap, c, ct), (x + ln / 2, y_s + c / 2, zc + ct / 2), lime, col, root, rng,
              bevel=0.008, seg=1)
        x += ln

    # water surface (the slab stops light leaking) and the basin floor under it
    wx = W - 2 * (ov_out + wall_t)
    wy0, wy1 = y_s + ov_out + wall_t, y_h
    wz = p["water_z"]
    cc.rbox(f"{n}_Water", (wx + 0.002, wy1 - wy0, 0.05), (0, (wy0 + wy1) / 2, wz - 0.025), water, col, root,
            bevel=0, uv_tile=0)
    cc.rbox(f"{n}_Basin", (wx + 0.002, wy1 - wy0, 0.05), (0, (wy0 + wy1) / 2, 0.025), dark, col, root,
            bevel=0, uv_tile=0)

    # head wall: a solid block clad in three panels, a capping stone, and a recessed
    # dark niche behind the falling sheet
    sw = p["sheet_w"]
    niche_w, niche_d = sw + 0.20, 0.06
    niche_z0 = wz - 0.01
    niche_z1 = p["lip_z"] + 0.10
    stone(f"{n}_HeadWall", (W, ht - niche_d, hh - 0.05), (0, y_h + niche_d + (ht - niche_d) / 2, (hh - 0.05) / 2),
          lime, col, root, rng, bevel=0.006)
    # face frame round the niche: two jambs and a head over it
    jamb_w = (W - niche_w) / 2
    for side, sx in (("W", -1), ("E", 1)):
        stone(f"{n}_HeadJamb_{side}", (jamb_w - gap, niche_d, hh - 0.05),
              (sx * (niche_w / 2 + jamb_w / 2), y_h + niche_d / 2, (hh - 0.05) / 2), lime, col, root, rng, bevel=0.006)
    stone(f"{n}_HeadLintel", (niche_w + 0.002, niche_d, hh - 0.05 - niche_z1),
          (0, y_h + niche_d / 2, niche_z1 + (hh - 0.05 - niche_z1) / 2), lime, col, root, rng, bevel=0.006,
          skip=())
    stone(f"{n}_HeadSill", (niche_w + 0.002, niche_d, niche_z0), (0, y_h + niche_d / 2, niche_z0 / 2),
          lime, col, root, rng, bevel=0.004)
    cc.rbox(f"{n}_Niche", (niche_w, 0.01, niche_z1 - niche_z0), (0, y_h + niche_d - 0.005, (niche_z0 + niche_z1) / 2),
            dark, col, root, bevel=0, uv_tile=0)
    x = -(W + 0.06) / 2
    for k, ln in enumerate(runs(W + 0.06, 1.0)):
        stone(f"{n}_HeadCap{k}", (ln - gap, ht + 0.06, 0.05), (x + ln / 2, L / 2 - ht / 2 + 0.01, hh - 0.025), lime, col,
              root, rng, bevel=0.008, seg=1)
        x += ln

    # bronze spout: a lip projecting from the niche back and its slot
    lz = p["lip_z"]
    ly = y_h + niche_d
    cc.rbox(f"{n}_SpoutLip", (sw + 0.06, 0.09, 0.025), (0, ly - 0.045, lz), bronze, col, root, bevel=0.003, seg=1,
            uv_tile=0.5)
    cc.rbox(f"{n}_SpoutSlot", (sw + 0.06, 0.012, 0.08), (0, ly - 0.006, lz + 0.05), bronze, col, root,
            bevel=0.002, seg=1, uv_tile=0.5)

    # the falling sheet: leaves the lip horizontally, then falls on a parabola
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rows = []
    v0, g = 0.55, 9.81                 # exit speed (m/s), gravity
    drop = lz - 0.0125 - wz
    t_end = math.sqrt(2 * drop / g)
    for k in range(7):
        t = t_end * (k / 6) ** 0.8
        yy = ly - 0.09 - v0 * t
        zz = lz - 0.0125 - 0.5 * g * t * t
        rows.append([bm.verts.new((sx * sw / 2, yy, zz)) for sx in (-1, 1)])
    for k in range(6):
        f = bm.faces.new((rows[k][0], rows[k][1], rows[k + 1][1], rows[k + 1][0]))
        for loop, (uu, vv) in zip(f.loops, ((0, k / 6), (1, k / 6), (1, (k + 1) / 6), (0, (k + 1) / 6))):
            loop[uvl].uv = (uu, vv)
    sheet = common.mesh_object(f"{n}_Sheet", bm, col, glass, root)
    sheet.data.materials[0].use_backface_culling = False
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
