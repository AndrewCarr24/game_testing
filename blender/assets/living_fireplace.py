"""Feature fireplace wall: a floor-to-gallery-rail limestone slab wall with a long
linear gas fire (black steel frame, glass front, live flames over a heaped bed of faceted
glass stones), a floating limestone hearth bench with a stack of logs. Mounted against a
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
    flame_strength=1.2,    # the cards' glow in the bake (the engine animates them)
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
    m = common.pbr_material("M_Living_Limestone", (0.55, 0.50, 0.42), roughness=0.5)   # honed, with a soft sheen
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


def flame_card(col, root, name, mat, x0, x1, y, z0, z1, seed):
    """One layer of live fire: a flat card (UV 0..1 across and up) tagged fx="fire", which the
    engine (viewer/fire.js) draws with an animated flame shader. In Blender, and in the bake,
    it's a plain emissive panel standing in for the fire's average glow."""
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in ((x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1))]
    f = bm.faces.new(vs)
    uv = bm.loops.layers.uv.new("UVMap")
    for loop, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop[uv].uv = c
    ob = common.mesh_object(name, bm, col, mat, root, smooth=False)
    ob["fx"] = "fire"
    ob["seed"] = seed
    ob["aspect"] = round((x1 - x0) / (z1 - z0), 3)   # card width / height, so the flames aren't stretched
    return ob


def pebbles(col, root, name, mat, x0, x1, y0, y1, z, count, seed=8):
    """Burner bed of faceted glass stones: squashed random octahedra, heaped."""
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    for _ in range(count):
        c = Vector((rng.uniform(x0, x1), rng.uniform(y0, y1), 0))
        r = rng.uniform(0.012, 0.022)
        c.z = z + r * 0.35 + rng.uniform(0, 0.012)
        rot = Vector(rng.uniform(0, 6.28, 3))
        from mathutils import Euler
        m = Euler(rot).to_matrix()
        ax = [m @ Vector((r * rng.uniform(0.8, 1.2), 0, 0)), m @ Vector((0, r * rng.uniform(0.8, 1.2), 0)),
              m @ Vector((0, 0, r * rng.uniform(0.45, 0.65)))]
        v = [bm.verts.new(c + s * a) for a in ax for s in (1, -1)]
        px, nx, py, ny, pz, nz = v
        for a, b in ((px, py), (py, nx), (nx, ny), (ny, px)):
            bm.faces.new((a, b, pz))
            bm.faces.new((b, a, nz))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = common.mesh_object(name, bm, col, mat, root, smooth=False)
    common.box_uv(ob, 0.5)
    return ob


def slab_box(col, root, name, mat, x0, x1, y0, y1, z0, z1, bevel=0.004):
    """A stone box split into separate 1.2 m slabs along the painted joints (x and z
    multiples of TILE / 2), each with an eased edge, so the joints are real V-grooves."""
    J = TILE / 2
    xs = [x0] + [k * J for k in range(-5, 6) if x0 + 0.05 < k * J < x1 - 0.05] + [x1]
    zs = [z0] + [k * J for k in range(1, 6) if z0 + 0.05 < k * J < z1 - 0.05] + [z1]
    bm = bmesh.new()
    for a, b in zip(xs, xs[1:]):
        for c, d in zip(zs, zs[1:]):
            t = common.box_bmesh((b - a, y1 - y0, d - c))
            vm = {v: bm.verts.new(v.co + Vector(((a + b) / 2, (y0 + y1) / 2, (c + d) / 2))) for v in t.verts}
            for fc in t.faces:
                bm.faces.new([vm[v] for v in fc.verts])
            t.free()
    ob = common.mesh_object(name, bm, col, mat, root, smooth=False)
    if bevel:
        common.add_bevel(ob, bevel, segments=1)
    _uv_slabs(ob)
    return ob


def logs(col, root, name, mat, end_mat, x0, y, z, seed=6):
    """A small pyramid stack of logs lying front-to-back: barked, slightly irregular
    sides; the sawn ends are a separate walnut-grain mesh."""
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    em = bmesh.new()
    segs = 9
    rows = [(4, 0.0), (3, 1), (2, 2)]
    r0 = 0.052
    for count, lvl in rows:
        for k in range(count):
            r = r0 * rng.uniform(0.85, 1.08)
            cx = x0 + r0 + (k + lvl * 0.5) * 2 * r0 * 1.02
            cz = z + r0 + lvl * r0 * 1.75
            L = rng.uniform(0.36, 0.42)
            ry = y + rng.uniform(-0.02, 0.02)
            ends = []
            rr = [r * rng.uniform(0.9, 1.06) for _ in range(segs)]
            for sy in (-1, 1):
                ends.append([(cx + rr[s] * math.cos(2 * math.pi * s / segs + k),
                              ry + sy * L / 2, cz + rr[s] * math.sin(2 * math.pi * s / segs + k)) for s in range(segs)])
            vb = [[bm.verts.new(c) for c in e] for e in ends]
            for s in range(segs):
                t = (s + 1) % segs
                bm.faces.new((vb[0][s], vb[0][t], vb[1][t], vb[1][s]))
            for e, sy in zip(ends, (-1, 1)):
                fc = [em.verts.new((c[0], c[1] + sy * 0.0005, c[2])) for c in e]
                em.faces.new(fc if sy < 0 else fc[::-1])
    for b in (bm, em):
        bmesh.ops.recalc_face_normals(b, faces=b.faces[:])
    ob = common.mesh_object(name, bm, col, mat, root, smooth=True)
    common.box_uv(ob, 0.5)
    eo = common.mesh_object(name + "Ends", em, col, end_mat, root, smooth=False)
    common.box_uv(eo, 0.5)
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
    bark = common.pbr_material("M_Plant_Bark", (0.10, 0.07, 0.045), roughness=0.8)

    W, T, H = p["width"], p["wall_t"], p["height"]
    HD, HH = p["hearth_depth"], p["hearth_h"]
    D = T + HD
    yb = D / 2                       # back face of the slab wall
    fw, fh = p["fire"]
    fz = p["fire_z"]
    y0 = yb - T

    # slab wall around the opening: separate 1.2 m limestone slabs with eased edges
    slab_box(col, root, f"{n}_WallL", stone, -W / 2, -fw / 2, y0, yb, 0.0, H)
    slab_box(col, root, f"{n}_WallR", stone, fw / 2, W / 2, y0, yb, 0.0, H)
    slab_box(col, root, f"{n}_WallBelow", stone, -fw / 2, fw / 2, y0, yb, 0.0, fz)
    slab_box(col, root, f"{n}_WallAbove", stone, -fw / 2, fw / 2, y0, yb, fz + fh, H)

    # firebox lining (black), recessed
    t = 0.02
    lin_d = T - 0.02
    box(col, root, f"{n}_FireBack", black, (fw, 0.01, fh), (0, yb - 0.005, fz + fh / 2), uv="box")
    box(col, root, f"{n}_FireFloor", black, (fw, lin_d, t), (0, yb - lin_d / 2, fz + t / 2), uv="box")
    box(col, root, f"{n}_FireRoof", black, (fw, lin_d, t), (0, yb - lin_d / 2, fz + fh - t / 2), uv="box")
    for s, sx in (("L", -1), ("R", 1)):
        box(col, root, f"{n}_FireSide{s}", black, (t, lin_d, fh), (sx * (fw / 2 - t / 2), yb - lin_d / 2, fz + fh / 2), uv="box")
    # front steel frame: a slim black bezel with an eased edge, proud of the stone, and glass
    fy = y0 - 0.006
    bz = 0.022
    box(col, root, f"{n}_BezelTop", black, (fw + 2 * bz, 0.012, bz), (0, fy, fz + fh + bz / 2), 0.002, uv="box")
    box(col, root, f"{n}_BezelBot", black, (fw + 2 * bz, 0.012, bz), (0, fy, fz - bz / 2), 0.002, uv="box")
    for s, sx in (("L", -1), ("R", 1)):
        box(col, root, f"{n}_Bezel{s}", black, (bz, 0.012, fh), (sx * (fw / 2 + bz / 2), fy, fz + fh / 2), 0.002, uv="box")
    box(col, root, f"{n}_Glass", glass, (fw, 0.006, fh), (0, fy - 0.003, fz + fh / 2), uv="box")
    # burner: a steel tray with a lip, heaped with faceted black glass stones, a glowing
    # ember line between them, two layers of live flame (a taller, redder one behind)
    bed_z = fz + t
    box(col, root, f"{n}_BurnerTray", black, (fw - 0.08, 0.15, 0.03), (0, yb - 0.11, bed_z + 0.015), 0.003, uv="box")
    box(col, root, f"{n}_Stones", pebble, (fw - 0.1, 0.13, 0.02), (0, yb - 0.11, bed_z + 0.03), 0.006, uv="box")
    pebbles(col, root, f"{n}_StonesTop", pebble, -fw / 2 + 0.07, fw / 2 - 0.07, yb - 0.17, yb - 0.05, bed_z + 0.04, 150)
    box(col, root, f"{n}_EmberBed", ember, (fw - 0.24, 0.025, 0.012), (0, yb - 0.11, bed_z + 0.042), uv="box")
    top = fz + fh - 0.03
    flame_card(col, root, f"{n}_FireBack_NoCollide", flame, -fw / 2 + 0.12, fw / 2 - 0.12, yb - 0.085, bed_z + 0.035, top, 1)
    flame_card(col, root, f"{n}_FireFront_NoCollide", flame, -fw / 2 + 0.10, fw / 2 - 0.10, yb - 0.125, bed_z + 0.035, top - 0.08, 2)
    # interactivity: the fire follows signal "fire" (renamed per placement, {"signal": {"fire":
    # "fire_great_room"}}, switched by an ix_switch_fire beside it); a gas fire burns without power
    for ob in root.children:
        if ob.get("fx") == "fire":
            ob["react"] = {"signal": "fire", "on": "show", "off": "hide", "power": False}
        elif ob.name == f"{n}_EmberBed":
            ob["react"] = {"signal": "fire", "on": {"emissive": 1}, "off": {"emissive": 0}, "power": False,
                           "duration": 1.5}

    # hearth bench: a floating limestone slab (eased edges) on a recessed black base,
    # with a stack of logs at the right-hand end
    hw = W
    base_h = 0.07
    box(col, root, f"{n}_HearthBase", black, (hw - 0.16, HD - 0.08, base_h), (0, yb - T - (HD - 0.08) / 2, base_h / 2), uv="box")
    slab_box(col, root, f"{n}_Hearth", stone, -hw / 2, hw / 2, y0 - HD, y0, base_h, HH, bevel=0.006)
    logs(col, root, f"{n}_Logs", bark, walnut, fw / 2 - 0.02 + 0.03, y0 - HD / 2, HH)

    # walnut cap along the top of the stone wall for a clean architectural finish
    box(col, root, f"{n}_Cap", walnut, (W + 0.03, T + 0.03, 0.04), (0, yb - T / 2, H + 0.02), 0.004, uv="box")

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
