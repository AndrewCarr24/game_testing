"""Feature fireplace wall: a floor-to-gallery-rail limestone slab wall with a long
linear gas fire (black steel frame, glass front, glowing flames over a bed of glass
stones), a floating limestone hearth bench and a walnut log niche. Mounted against a
wall; the back face is at +Y (rotate -90 for an east wall). Also provides
`limestone()` (the shared large-format limestone material, 1.2 m slabs).

Units are metres. Origin: floor centre of the footprint, back at y = +depth/2.
"""
import importlib
import math
import os
import sys

import bmesh
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(materials)
importlib.reload(textures)

NAME = "LivingFireplace"

P = dict(
    name=NAME,
    width=2.94,
    wall_t=0.22,           # stone wall thickness (the firebox recess depth)
    height=4.45,
    hearth_depth=0.50,
    hearth_h=0.40,
    fire=(2.0, 0.62),      # opening width, height
    fire_z=0.78,           # opening bottom
    flame_strength=3.5,
)

TILE = 2.4                 # metres per limestone texture tile (2 x 2 slabs of 1.2 m)


def limestone_texture(n=1024, seed=41):
    path = os.path.join(textures.TEX_DIR, "T_Living_Limestone_BaseColor.png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(seed)
    big = textures._noise(n, 0.12, 1.0, 1.9, rng)           # long horizontal cloudy bands
    mid = textures._noise(n, 0.5, 1.0, 1.4, rng)
    pores = textures._noise(n, 1.0, 1.0, 0.6, rng)
    pits = (textures._noise(n, 1.0, 1.0, 0.1, rng) > 0.93) * 1.0
    u = np.linspace(0, 1, n, endpoint=False)[None, :] * np.ones((n, 1))
    v = np.linspace(0, 1, n, endpoint=False)[:, None] * np.ones((1, n))
    slab = (np.floor(u * 2).astype(int) + 2 * np.floor(v * 2).astype(int))
    tone = rng.uniform(-1, 1, 4)[slab]
    t = 0.5 + 0.30 * big + 0.12 * mid + 0.05 * pores + 0.06 * tone
    t = np.clip(t, 0, 1)
    light = np.array([0.40, 0.345, 0.265])
    dark = np.array([0.27, 0.225, 0.17])
    lin = dark + (light - dark) * t[..., None]
    lin *= (1 - 0.18 * pits)[..., None]
    # 2 mm joints between the 1.2 m slabs
    d = np.minimum((u * 2) % 1.0, 1 - (u * 2) % 1.0) * (TILE / 2)
    e = np.minimum((v * 2) % 1.0, 1 - (v * 2) % 1.0) * (TILE / 2)
    lin[(d < 0.0012) | (e < 0.0012)] *= 0.45
    return textures._save("T_Living_Limestone_BaseColor", textures._to_srgb(lin))


def limestone():
    m = common.pbr_material("M_Living_Limestone", (0.55, 0.50, 0.42), roughness=0.72)
    common.set_base_color_map(m, textures.load(limestone_texture()))
    return m


def _uv_slabs(ob):
    """World-scale planar UVs per face (u across the largest horizontal extent)."""
    me = ob.data
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    loc = ob.location
    for poly in me.polygons:
        nrm = [abs(c) for c in poly.normal]
        na = nrm.index(max(nrm))
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co + loc
            if na == 1:
                uv.data[li].uv = (co.x / TILE, co.z / TILE)
            elif na == 0:
                uv.data[li].uv = (co.y / TILE, co.z / TILE)
            else:
                uv.data[li].uv = (co.x / TILE, co.y / TILE)


def box(col, root, name, mat, size, loc, bevel=0.0, uv="slab"):
    ob = common.mesh_object(name, common.box_bmesh(size), col, mat, root, smooth=False)
    ob.location = loc
    if bevel:
        common.add_bevel(ob, bevel, segments=2)
    if uv == "slab":
        _uv_slabs(ob)
    else:
        common.box_uv(ob, 0.5)
    return ob


def flames(col, root, name, mat, x0, x1, y, z, h, seed=4):
    """Rows of tapering flame tongues (4-sided pyramids), emissive."""
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    x = x0
    while x < x1:
        w = rng.uniform(0.05, 0.11)
        fh = h * rng.uniform(0.45, 1.0)
        yy = y + rng.uniform(-0.03, 0.03)
        lean = rng.uniform(-0.03, 0.03)
        a = bm.verts.new((x - w, yy - 0.03, z))
        b = bm.verts.new((x + w, yy - 0.03, z))
        c = bm.verts.new((x + w, yy + 0.03, z))
        d = bm.verts.new((x - w, yy + 0.03, z))
        t = bm.verts.new((x + lean, yy, z + fh))
        for f in ((a, b, t), (b, c, t), (c, d, t), (d, a, t)):
            bm.faces.new(f)
        x += w * 1.5
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = common.mesh_object(name, bm, col, mat, root, smooth=False)
    ob.location = (0, 0, 0)
    return ob


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    stone = limestone()
    black = materials.black_metal()
    walnut = materials.walnut()
    glass = materials.glass("M_Glass_Fire", tint=(0.8, 0.85, 0.85), alpha=0.10)
    flame = materials.emissive("M_Living_Flame", (1.0, 0.30, 0.03), p["flame_strength"])
    ember = materials.emissive("M_Living_Ember", (0.9, 0.12, 0.02), 2.0)
    pebble = common.pbr_material("M_Living_GlassStone", (0.012, 0.012, 0.014), roughness=0.15)

    W, T, H = p["width"], p["wall_t"], p["height"]
    HD, HH = p["hearth_depth"], p["hearth_h"]
    D = T + HD
    yb = D / 2                       # back face of the slab wall
    wy = yb - T / 2                  # centre of the slab wall
    fw, fh = p["fire"]
    fz = p["fire_z"]

    # slab wall around the opening
    side = (W - fw) / 2
    box(col, root, f"{n}_WallL", stone, (side, T, H), (-(fw / 2 + side / 2), wy, H / 2), 0.004)
    box(col, root, f"{n}_WallR", stone, (side, T, H), ((fw / 2 + side / 2), wy, H / 2), 0.004)
    box(col, root, f"{n}_WallBelow", stone, (fw, T, fz), (0, wy, fz / 2), 0.004)
    box(col, root, f"{n}_WallAbove", stone, (fw, T, H - fz - fh), (0, wy, fz + fh + (H - fz - fh) / 2), 0.004)

    # firebox lining (black), recessed
    t = 0.02
    by = yb - T + 0.02              # lining inner face at the front of the recess
    lin_d = T - 0.02
    box(col, root, f"{n}_FireBack", black, (fw, 0.01, fh), (0, yb - 0.005, fz + fh / 2), uv="box")
    box(col, root, f"{n}_FireFloor", black, (fw, lin_d, t), (0, yb - lin_d / 2, fz + t / 2), uv="box")
    box(col, root, f"{n}_FireRoof", black, (fw, lin_d, t), (0, yb - lin_d / 2, fz + fh - t / 2), uv="box")
    for s, sx in (("L", -1), ("R", 1)):
        box(col, root, f"{n}_FireSide{s}", black, (t, lin_d, fh), (sx * (fw / 2 - t / 2), yb - lin_d / 2, fz + fh / 2), uv="box")
    # front steel frame (a slim black bezel) and glass
    fy = yb - T - 0.006
    bz = 0.022
    box(col, root, f"{n}_BezelTop", black, (fw + 2 * bz, 0.012, bz), (0, fy, fz + fh + bz / 2), uv="box")
    box(col, root, f"{n}_BezelBot", black, (fw + 2 * bz, 0.012, bz), (0, fy, fz - bz / 2), uv="box")
    for s, sx in (("L", -1), ("R", 1)):
        box(col, root, f"{n}_Bezel{s}", black, (bz, 0.012, fh), (sx * (fw / 2 + bz / 2), fy, fz + fh / 2), uv="box")
    pane = box(col, root, f"{n}_Glass", glass, (fw, 0.006, fh), (0, fy - 0.003, fz + fh / 2), uv="box")
    # burner bed: glass stones strip + ember glow + flames
    box(col, root, f"{n}_Stones", pebble, (fw - 0.1, 0.12, 0.05), (0, yb - 0.11, fz + 0.045), 0.02, uv="box")
    box(col, root, f"{n}_EmberBed", ember, (fw - 0.2, 0.07, 0.012), (0, yb - 0.11, fz + 0.075), uv="box")
    flames(col, root, f"{n}_Flames", flame, -fw / 2 + 0.14, fw / 2 - 0.14, yb - 0.11, fz + 0.075, fh * 0.65)

    # hearth bench: floating limestone slab on a recessed black base
    hw = W
    base_h = 0.07
    box(col, root, f"{n}_HearthBase", black, (hw - 0.16, HD - 0.08, base_h), (0, yb - T - (HD - 0.08) / 2, base_h / 2), uv="box")
    box(col, root, f"{n}_Hearth", stone, (hw, HD, HH - base_h), (0, yb - T - HD / 2, base_h + (HH - base_h) / 2), 0.006)

    # slender walnut-framed log niche set into the right wall return? -> a walnut plinth
    # strip along the top of the stone wall for a clean architectural finish
    box(col, root, f"{n}_Cap", walnut, (W + 0.03, T + 0.03, 0.04), (0, wy, H + 0.02), 0.004, uv="box")

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
