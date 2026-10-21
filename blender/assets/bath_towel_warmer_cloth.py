"""Terry towels for the heated towel rail (bath_towel_warmer.py); not an asset itself.

drape(): a towel laid over a round rung as an even grid sheet (front flap, a half wrap over
the bar, back flap), pinned along the crest and laid on with soft vertical folds, small
gathers over the bar, a puckered border and ruffled edges, then cloth-dropped headless (as
mud_common's garments) with the hung rung, the rungs below it (cylinders) and the wall as
colliders, gravity tipped a few degrees toward the wall so the flaps settle onto the rungs.
The settled sheet is resampled onto a grid broken at the weave changes, given a weighted thickness
(full terry pile; thinner flat-woven hem, dobby border band and selvedges, so the pile
steps down at the band like a real towel), decimated, and cached in build/garment_cache/.

Terry: a numpy-generated loop pile (base colour with shadowed gaps between the loops +
normal map), one 0.12 m tile, T_BathTowelWarmer_Terry_*; generated only when missing.
"""
import importlib
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from lib import common, textures  # noqa: E402
import mud_common as mc  # noqa: E402  (cache, decimate, depsgraph helpers)

importlib.reload(mc)

VERSION = 10             # bump to re-simulate every towel
TILE = 0.12             # metres per terry texture repeat
BC_TEX = "T_BathTowelWarmer_Terry_BaseColor"
NRM_TEX = "T_BathTowelWarmer_Terry_Normal"
IVORY = (0.55, 0.52, 0.46)          # M_Fabric_Linen_Ivory (the hem / border band material)


# ------------------------------------------------------------------ terry texture

def _terry_height(n=1024, seed=5):
    """Tileable height field of a loop pile: staggered rows of loops (elongated domes at
    random tilts, as twisted yarn loops look from above) with gaps between them."""
    rng = np.random.default_rng(seed)
    h = np.zeros((n, n), np.float32)
    nu, nv = 78, 68                     # loops per tile across / along (1.5 x 1.8 mm)
    su, sv = n / nu, n / nv
    rad = int(max(su, sv) * 1.3) + 2
    yy, xx = np.mgrid[-rad:rad + 1, -rad:rad + 1].astype(np.float32)
    for j in range(nv):
        for i in range(nu):
            cx = (i + 0.5 * (j % 2) + rng.uniform(-0.28, 0.28)) * su
            cy = (j + rng.uniform(-0.25, 0.25)) * sv
            ang = rng.normal(0.0, 0.55)                 # loops lean, mostly along the warp (v)
            a = su * rng.uniform(0.55, 0.75)            # half length
            b = su * rng.uniform(0.32, 0.42)            # half width
            ix, iy = int(cx), int(cy)
            dx, dy = xx - (cx - ix), yy - (cy - iy)
            ca, sa = math.cos(ang), math.sin(ang)
            u = (dx * sa + dy * ca) / a
            w = (dx * ca - dy * sa) / b
            d2 = u * u + w * w
            dome = np.clip(1.0 - d2, 0.0, None) ** 0.6
            # the yarn's twist: faint ridges across the loop
            dome *= 0.88 + 0.12 * np.cos(u * 5.5 + rng.uniform(0, 6.28))
            dome *= rng.uniform(0.7, 1.0)
            rows = (np.arange(iy - rad, iy + rad + 1) % n)[:, None]
            cols = (np.arange(ix - rad, ix + rad + 1) % n)[None, :]
            h[rows, cols] = np.maximum(h[rows, cols], dome)
    fibre = textures._noise(n, 1.0, 1.0, 0.9, rng)
    h = h + 0.06 * fibre          # no low-frequency term: at a distance (mipmapped) it read as stains
    return (h - h.min()) / (h.max() - h.min() + 1e-9), rng


def terry_textures():
    """(base colour path, normal path), generated once."""
    bc_path = os.path.join(textures.TEX_DIR, BC_TEX + ".png")
    nrm_path = os.path.join(textures.TEX_DIR, NRM_TEX + ".png")
    if os.path.exists(bc_path) and os.path.exists(nrm_path):
        return bc_path, nrm_path
    n = 1024
    h, rng = _terry_height(n)
    # colour: lit loop tops, shadowed (slightly warmer) gaps, a little per-area variation
    shade = 0.62 + 0.38 * h ** 0.85
    lin = np.stack([shade, shade * (0.985 + 0.015 * h), shade * (0.95 + 0.05 * h)], axis=-1)
    target = np.array(IVORY) * 0.97
    lin = lin * (target / lin.reshape(-1, 3).mean(axis=0))
    textures._save(BC_TEX, textures._to_srgb(np.clip(lin, 0, 1)))
    strength = 3.2
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    nrm = np.stack([-dx, dy, np.ones_like(h)], axis=-1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    textures._save(NRM_TEX, nrm * 0.5 + 0.5, non_color=True)
    return bc_path, nrm_path


def terry_material():
    m = common.pbr_material("M_BathTowelWarmer_Terry", (1, 1, 1), roughness=0.96)
    if not any(nd.type == "TEX_IMAGE" for nd in m.node_tree.nodes):
        bcp, nrp = terry_textures()
        common.set_base_color_map(m, textures.load(bcp))
        common.set_normal_map(m, textures.load(nrp, non_color=True), 1.0)
    return m


# ------------------------------------------------------------------ the sheet

def _breaks(total, step, marks, min_gap=0.0012):
    vals = sorted(set([0.0, total] + [k * total / max(1, round(total / step)) for k in range(round(total / step) + 1)]
                      + [m for m in marks if 0.0 < m < total]))
    out = [vals[0]]
    for v in vals[1:]:
        if v - out[-1] >= min_gap:
            out.append(v)
        elif v == total:
            out[-1] = total
    return out


def drape(tag, y_r, z_r, rr, width, front, back, t, lower=(), wall=0.0, x_off=0.0, skew=0.0,
          gather=0.006, folds=0.012, splay=0.0, tilt=0.0, seed=0, tris=1200, frames=60, bend=1.6, mass=0.4):
    """A folded towel hung over a rung whose axis runs along X at (y_r, z_r), radius rr.
    front / back: flap lengths below the rung axis; t: thickness; lower: z of rungs below
    (colliders the flaps rest on); wall: y of the wall face; skew: hem tilt (m: the towel
    was put on the bar a touch askew); gather: ripples over the bar; folds: depth of the
    soft vertical folds in the flaps (m).
    Returns a bmesh in asset coordinates: material 0 terry pile, 1 flat weave (hems,
    border bands, selvedges), UVs in TILE units."""
    params = dict(v=VERSION, y_r=y_r, z_r=z_r, rr=rr, width=width, front=front, back=back, t=t,
                  lower=list(lower), wall=wall, x_off=x_off, skew=skew, gather=gather, folds=folds, splay=splay, tilt=tilt, seed=seed,
                  tris=tris, frames=frames, bend=bend, mass=mass)
    path_npz = os.path.join(mc.CACHE, f"bathtw_{tag}_{mc._key('bathtw_' + tag, params)}.npz")
    if os.path.exists(path_npz):
        return mc._load_cache(path_npz)

    R = rr + t / 2 + 0.0025                       # the sheet's mid-surface radius over the bar
    arc = math.pi * R
    L = front + arc + back

    def centre(a):
        """Mid-surface point (y, z) and outward normal at arc length a from the front hem."""
        if a <= front:                # a thick fold may stand off the bar a little before it hangs
            d = front - a
            return Vector((y_r - R - splay * (1 - math.exp(-d / 0.07)), z_r - d)), Vector((-1.0, 0.0))
        if a <= front + arc:
            th = math.pi - (a - front) / R          # pi (front) -> 0 (back) over the top
            return Vector((y_r + R * math.cos(th), z_r + R * math.sin(th))), Vector((math.cos(th), math.sin(th)))
        d = a - front - arc
        return Vector((y_r + R + 0.5 * splay * (1 - math.exp(-d / 0.07)), z_r - d)), Vector((1.0, 0.0))

    # rows (along the towel) and columns (across); breakpoints where the weave changes
    HEM, GAP, BAND, SEL, EPS = 0.011, 0.030, 0.042, 0.007, 0.0015
    ends = []
    for e in (HEM, HEM + GAP, HEM + GAP + BAND):
        ends += [e - EPS, e + EPS]
    marks = ends + [L - e for e in ends] + [front + arc * k / 8 for k in range(9)]
    rows = _breaks(L, 0.022, marks)
    cols = _breaks(width, 0.022, [SEL - EPS, SEL + EPS, width - SEL - EPS, width - SEL + EPS])

    def weave(a, s):
        """(flat weave?, thickness weight) at towel coords a (along), s (across from one side)."""
        e = min(a, L - a)
        edge = min(s, width - s)
        if e < HEM:
            return True, 0.62
        if HEM + GAP < e < HEM + GAP + BAND:
            return True, 0.5
        if edge < SEL:                  # selvedge: flat edge, same terry material
            return False, 0.6
        return False, 1.0

    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 2 * math.pi, 6)
    crest_a = front + arc / 2

    def ripple(a, s):
        """Normal offset (away from the bar) of the sheet as it is laid on: soft vertical
        folds that open up below the crest and slant a little, small gathers over the bar,
        the woven border puckering (it is tighter than the pile), the hem corners flaring."""
        dc = abs(a - crest_a)
        e = min(a, L - a)
        edge = min(s, width - s)
        x = s / width
        side = 1.0 if a < crest_a else -1.0
        flap = mc.smoothstep(0.0, 0.42, dc) ** 0.8          # taut under the bar, fluting toward the hem
        # broad ridges, narrow valleys (hanging cloth folds), slanting slightly down the flap
        off = folds * flap * abs(math.sin(math.pi * x * 2.3 + ph[0] + side * 2.5 * dc)) ** 0.7
        off += 0.35 * folds * flap * abs(math.sin(math.pi * x * 4.1 + ph[1] - side * 4.0 * dc)) ** 0.7
        off += gather * max(0.0, 1.0 - dc / 0.09) * (0.5 + 0.5 * math.sin(2 * math.pi * x * width / 0.075 + ph[2]))
        if e < HEM + GAP + BAND + 0.012:
            off += 0.0045 * (0.5 + 0.5 * math.sin(2 * math.pi * s / 0.047 + ph[3] + 9.0 * e))
        off += 0.018 * max(0.0, 1 - e / 0.10) ** 1.5 * max(0.0, 1 - edge / 0.07)          # corners kick out
        # the side hems are tighter than the pile, so the edges ruffle a little
        off += (0.002 + 0.005 * flap) * max(0.0, 1 - edge / 0.05) ** 2 * \
            (0.5 + 0.5 * math.sin(2 * math.pi * dc / 0.075 + ph[4] + (0.0 if s < width / 2 else 2.0)))
        return off

    # the simulated sheet: an even grid (cloth solvers dislike the hem's thin rows)
    nA, nS = max(8, round(L / 0.018)), max(6, round(width / 0.022))
    A = [L * k / nA for k in range(nA + 1)]
    S = [width * k / nS for k in range(nS + 1)]
    bm = bmesh.new()
    for a in A:
        offs = []
        for s in S:
            a2 = min(L, max(0.0, a + skew * (s / width - 0.5) * 2))     # askew on the bar
            p, nrm = centre(a2)
            offs.append((p, nrm, ripple(a, s)))
        # gather each row so its length across stays the towel's width
        wav = [o[2] for o in offs]
        length = sum(math.hypot(S[i + 1] - S[i], wav[i + 1] - wav[i]) for i in range(len(S) - 1))
        g = width / length
        for i, s in enumerate(S):
            p, nrm, w = offs[i]
            bm.verts.new(Vector((x_off + (s - width / 2) * g, p.x + nrm.x * w, p.y + nrm.y * w)))
    bm.verts.ensure_lookup_table()
    m1 = nS + 1
    for j in range(nA):
        for i in range(nS):
            bm.faces.new((bm.verts[j * m1 + i], bm.verts[j * m1 + i + 1], bm.verts[(j + 1) * m1 + i + 1],
                          bm.verts[(j + 1) * m1 + i]))
    crest_a = front + arc / 2
    pins = [1.0 if abs(a - crest_a) < arc * 0.30 else 0.0 for a in A for s in S]

    scene = bpy.data.scenes.new("BathTWClothSim")
    scene.frame_start, scene.frame_end = 1, frames
    # gravity tipped a few degrees toward the wall: the flaps settle onto the rungs below
    g = 9.81
    scene.gravity = (0.0, g * math.sin(tilt), -g * math.cos(tilt))
    me = bpy.data.meshes.new("BathTWCloth")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("BathTWCloth", me)
    scene.collection.objects.link(ob)
    temp = [ob]
    vg = ob.vertex_groups.new(name="pin")
    for k, w in enumerate(pins):
        if w:
            vg.add([k], w, "REPLACE")

    def collider(name, bmc):
        cm = bpy.data.meshes.new(name)
        bmc.to_mesh(cm)
        bmc.free()
        co_ob = bpy.data.objects.new(name, cm)
        scene.collection.objects.link(co_ob)
        co_ob.modifiers.new("Collision", "COLLISION")
        co_ob.collision.thickness_outer = 0.001
        co_ob.collision.cloth_friction = 10.0
        temp.append(co_ob)

    import bath_common as bcm
    span = (x_off - width / 2 - 0.05, x_off + width / 2 + 0.05)
    for k, zr in enumerate([z_r] + list(lower)):
        bmc = bmesh.new()
        bcm.cylinder_between(bmc, (span[0], y_r, zr), (span[1], y_r, zr), rr + t / 2 + 0.0008, 24)
        collider(f"BathTWRung{k}", bmc)
    bmc = common.box_bmesh((width + 0.2, 0.05, 2.0))
    bmesh.ops.translate(bmc, verts=bmc.verts, vec=(x_off, wall + 0.025 - t / 2 - 0.0015, z_r))
    collider("BathTWWall", bmc)

    cmod = ob.modifiers.new("Cloth", "CLOTH")
    st = cmod.settings
    st.quality = 10
    st.mass = mass
    st.tension_stiffness = st.compression_stiffness = 22.0
    st.shear_stiffness = 8.0
    st.bending_stiffness = bend
    st.air_damping = 1.5
    st.tension_damping = st.compression_damping = 6.0
    st.bending_damping = 0.6
    st.vertex_group_mass = "pin"
    st.pin_stiffness = 1.0
    cs = cmod.collision_settings
    cs.use_collision = True
    cs.collision_quality = 4
    cs.distance_min = 0.0015
    cs.use_self_collision = True
    cs.self_distance_min = 0.002
    cs.self_friction = 5.0
    cmod.point_cache.frame_start, cmod.point_cache.frame_end = 1, frames
    mc._dg(scene)
    for f in range(1, frames + 1):
        scene.frame_set(f)
    dg = mc._dg(scene)
    out = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    for o in temp:
        d = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if d is not None and d.users == 0:
            bpy.data.meshes.remove(d)
    bpy.data.scenes.remove(scene)

    co = np.zeros(3 * len(out.vertices), np.float32)
    out.vertices.foreach_get("co", co)
    bpy.data.meshes.remove(out)
    co = co.reshape(nA + 1, nS + 1, 3)

    def at(a, s):
        fa, fs = min(a / L * nA, nA - 1e-6), min(s / width * nS, nS - 1e-6)
        j, i = int(fa), int(fs)
        u, v = fa - j, fs - i
        q = (co[j, i] * (1 - u) * (1 - v) + co[j + 1, i] * u * (1 - v) + co[j, i + 1] * (1 - u) * v +
             co[j + 1, i + 1] * u * v)
        return Vector(map(float, q))

    # the finished sheet: rows and columns broken where the weave changes, UVs, materials
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    grid = [[bm.verts.new(at(a, s)) for s in cols] for a in rows]
    for j in range(len(rows) - 1):
        for i in range(len(cols) - 1):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            am, sm = (rows[j] + rows[j + 1]) / 2, (cols[i] + cols[i + 1]) / 2
            f.material_index = 1 if weave(am, sm)[0] else 0
            for lp, (jj, ii) in zip(f.loops, ((j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i))):
                lp[uv].uv = (cols[ii] / TILE, rows[jj] / TILE)
    weights = [weave(a, s)[1] for a in rows for s in cols]
    out = bpy.data.meshes.new("BathTWSheet")
    bm.to_mesh(out)
    bm.free()
    out = _thicken(out, t, weights)
    bm = bmesh.new()
    bm.from_mesh(out)
    bpy.data.meshes.remove(out)
    mc._decimate(bm, tris)
    _rim_uvs(bm, t, width, L)
    tmp = bpy.data.meshes.new("BathTWTmp")
    bm.to_mesh(tmp)
    mc._save_cache(path_npz, tmp)
    bpy.data.meshes.remove(tmp)
    return bm


def _thicken(me, t, weights):
    """Solidify the settled sheet about its mid-surface, thickness t x per-vertex weight."""
    scene = bpy.data.scenes.new("BathTWSolidify")
    for _ in range(4):                 # material slots, else solidify clamps the rim's index offset
        me.materials.append(None)
    ob = bpy.data.objects.new("BathTWSolid", me)
    scene.collection.objects.link(ob)
    vg = ob.vertex_groups.new(name="thick")
    for k, w in enumerate(weights):
        vg.add([k], w, "REPLACE")
    ob.vertex_groups.new(name="shell")             # index 1: the new shell's verts (for _rim_uvs)
    m = ob.modifiers.new("Solidify", "SOLIDIFY")
    m.thickness = t
    m.offset = 0.0
    m.use_even_offset = True
    m.use_rim = True
    m.vertex_group = "thick"
    m.thickness_vertex_group = 0.0
    m.shell_vertex_group = "shell"
    m.material_offset_rim = 2          # rim faces: material + 2 until _rim_uvs fixes their UVs
    new = bpy.data.meshes.new_from_object(ob.evaluated_get(mc._dg(scene)))
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    bpy.data.scenes.remove(scene)
    return new


def _rim_uvs(bm, t, width, length):
    """Solidify copies the edge's UVs onto both edges of a rim face (zero width: the pile's
    normal map smeared into streaks and flipped ticks along the edges). Open every rim face
    across the thickness, always toward the outside of the towel's UV rectangle (so the
    tangent frames agree from face to face), and give it back its material. Runs after the
    decimation (rim faces still carry material + 2; new-shell verts the "shell" weight)."""
    uv = bm.loops.layers.uv.active
    dl = bm.verts.layers.deform.active
    W, H = width / TILE, length / TILE
    d = t / TILE
    for f in bm.faces:
        if f.material_index < 2:
            continue
        f.material_index -= 2
        for lp in f.loops:
            if dl is None or lp.vert[dl].get(1, 0.0) < 0.5:
                continue
            u, v = lp[uv].uv
            side = min((u, (-d, 0.0)), (W - u, (d, 0.0)), (v, (0.0, -d)), (H - v, (0.0, d)))[1]
            lp[uv].uv = (u + side[0], v + side[1])
