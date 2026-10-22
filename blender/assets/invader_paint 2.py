"""Textures of the invader's body (blender/assets/invader.py, stage 3).

Bakes (Cycles, 1k): the LOD0 surface's position per texel (emission of the geometry's
position), tangent-space normals from the high-res field mesh (selected to active),
ambient occlusion. Then numpy: each texel's clothing zone comes from the body field at
its position (the nearest primitive's zone; the gloves from the hand fields), plus
painted details (zip, chest pockets, the balaclava's eye opening, glove palms, seams
where garment panels meet); base colour per outfit (OUTFITS) and one shared ORM map.
"""
import math
import os

import bpy
import numpy as np

import invader_body as body

# sRGB base colours per zone, per outfit. Dark work clothes; skin and gloves vary.
OUTFITS = dict(
    Charcoal=dict(jacket=(0.19, 0.19, 0.195), collar=(0.16, 0.16, 0.165), pants=(0.12, 0.12, 0.125),
                  pocket=(0.11, 0.11, 0.115), glove=(0.065, 0.065, 0.068), palm=(0.22, 0.22, 0.21),
                  boot=(0.13, 0.105, 0.088), sole=(0.05, 0.05, 0.05), mask=(0.065, 0.065, 0.07),
                  skin=(0.74, 0.56, 0.47), metal=(0.32, 0.32, 0.33)),
    Navy=dict(jacket=(0.11, 0.13, 0.19), collar=(0.1, 0.115, 0.17), pants=(0.105, 0.125, 0.18),
              pocket=(0.095, 0.115, 0.165), glove=(0.3, 0.24, 0.17), palm=(0.34, 0.28, 0.2),
              boot=(0.07, 0.07, 0.072), sole=(0.04, 0.04, 0.04), mask=(0.085, 0.09, 0.115),
              skin=(0.46, 0.32, 0.25), metal=(0.36, 0.36, 0.37)),
    Olive=dict(jacket=(0.22, 0.23, 0.16), collar=(0.19, 0.2, 0.14), pants=(0.15, 0.15, 0.15),
               pocket=(0.14, 0.14, 0.14), glove=(0.06, 0.06, 0.06), palm=(0.2, 0.2, 0.19),
               boot=(0.42, 0.32, 0.2), sole=(0.09, 0.08, 0.07), mask=(0.11, 0.11, 0.11),
               skin=(0.82, 0.64, 0.54), metal=(0.3, 0.3, 0.3)),
)
ROUGH = dict(jacket=0.86, collar=0.88, pants=0.9, pocket=0.9, glove=0.62, palm=0.7, boot=0.5, sole=0.92,
             mask=0.95, skin=0.6, eye=0.25, metal=0.4)
METAL = dict(metal=0.7)
ZONE_KEYS = ("jacket", "collar", "pants", "pocket", "glove", "palm", "boot", "sole", "mask", "skin", "eye", "metal")


def log(*a):
    print("INVADER", *a, flush=True)


# ---------------------------------------------------------------- Cycles bakes

def cycles(scene, samples):
    scene.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        scene.cycles.device = "GPU"
    except (TypeError, KeyError, AttributeError):
        pass
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False


def image(name, size, float_buffer=True, non_color=False):
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, size, size, alpha=False, float_buffer=float_buffer)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    return img


def pixels(img):
    w, h = img.size
    a = np.zeros(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(h, w, 4)[::-1, :, :3].copy()      # row 0 = top (v = 1)


def set_pixels(img, rgb):
    h, w = rgb.shape[:2]
    a = np.ones((h, w, 4), np.float32)
    a[..., :3] = rgb[::-1]
    img.pixels.foreach_set(a.ravel())
    img.update()


def _bake_material(kind, img):
    m = bpy.data.materials.new("_bake_" + kind)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    if kind == "position":
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        em = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(geo.outputs["Position"], em.inputs["Color"])
        nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.nodes.active = tex
    return m


def bake(target, img, kind, sources=(), bake_type="EMIT", margin=8, extrusion=0.012, ray=0.03, **kw):
    me = target.data
    saved = list(me.materials)
    me.materials.clear()
    me.materials.append(_bake_material(kind, img))
    vl = bpy.context.view_layer
    for o in vl.objects:
        if o.select_get():
            o.select_set(False)
    for s in sources:
        s.select_set(True)
    target.select_set(True)
    vl.objects.active = target
    bpy.ops.object.bake(type=bake_type, use_selected_to_active=bool(sources), cage_extrusion=extrusion,
                        max_ray_distance=ray, margin=margin, margin_type="EXTEND", use_clear=True,
                        target="IMAGE_TEXTURES", **kw)
    m = me.materials[0]
    me.materials.clear()
    for s in saved:
        me.materials.append(s)
    bpy.data.materials.remove(m)
    for o in vl.objects:
        if o.select_get():
            o.select_set(False)


def uv_unwrap(ob, size):
    vl = bpy.context.view_layer
    for o in vl.objects:
        if o.select_get():
            o.select_set(False)
    vl.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, margin_method="FRACTION", margin=6.0 / size)
    bpy.ops.object.mode_set(mode="OBJECT")
    ob.select_set(False)


# ---------------------------------------------------------------- zones

def zones_at(P, N, p, L):
    """Zone name index (into ZONE_KEYS) and helper values for texel positions P (n, 3)."""
    prims = [q for q in body.body_prims(L, p) if q.get("op", "u") == "u"]
    _, per = body.eval_points(prims, P)
    bd = per.min(1)
    arg = per.argmin(1)
    zone = np.array([prims[i]["zone"] for i in range(len(prims))])[arg]
    # the hands
    hd = np.full(len(P), 1.0)
    palm = np.zeros(len(P), bool)
    for s in "LR":
        M = body.hand_frame(L, s)
        loc = (P - M[:3, 3]) @ M[:3, :3]
        hp = [q for q in body.hand_prims(p, s) if q.get("op", "u") == "u"]
        near = np.linalg.norm(P - M[:3, 3], axis=1) < 0.26
        if not near.any():
            continue
        _, hper = body.eval_points(hp, loc[near])
        d = hper.min(1)
        idx = np.nonzero(near)[0]
        better = d < hd[idx]
        hd[idx[better]] = d[better]
        # the palm side of the glove (and the inner fingers)
        ln = loc[near]
        pz = (ln[:, 2] < -0.012) & (ln[:, 1] > 0.0) & (ln[:, 1] < 0.105)     # the palm (not the fingers)
        palm[idx[better & pz]] = True
    on_hand = hd < bd
    zone = np.where(on_hand, np.where(palm, "palm", "glove"), zone)
    # seams: where the nearest primitive changes (garment panels), not on the knit mask
    return zone, arg, on_hand


def paint(pos, nrm_unused, ao, p, L, size):
    """-> {outfit: albedo (size, size, 3) sRGB}, orm (size, size, 3)"""
    P = pos.reshape(-1, 3).astype(float)
    zone, arg, on_hand = zones_at(P, None, p, L)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    # painted details ------------------------------------------------------
    jacket = zone == "jacket"
    zone = np.where(jacket & (np.abs(x) < 0.0045) & (y < -0.05) & (z > p["hem_z"]) & (z < 1.49), "metal", zone)
    # the balaclava's eye opening: skin, and the eyes in it
    head = (zone == "mask") & (y < -0.055)
    slit = head & (((x / 0.06) ** 2 + ((z - 1.685) / 0.0185) ** 2) < 1.0)
    zone = np.where(slit, "skin", zone)
    eye = np.zeros(len(P), bool)
    iris = np.zeros(len(P), bool)
    for sx in (1, -1):
        e = L["eye_L"] * np.array([sx, 1, 1])
        r = ((x - e[0]) / 0.0125) ** 2 + ((z - 1.684) / 0.0072) ** 2
        eye |= slit & (r < 1.0)
        iris |= slit & (np.hypot(x - e[0] - 0.0, (z - 1.684)) < 0.0052)
    zone = np.where(eye, "eye", zone)
    zk = {k: i for i, k in enumerate(ZONE_KEYS)}
    zi = np.array([zk.get(str(zz), zk["jacket"]) for zz in zone])
    # seams: neighbour texels on another primitive (same garment), drawn 1-2 texels wide
    img_arg = arg.reshape(size, size)
    img_z = zi.reshape(size, size)
    seam = np.zeros((size, size), bool)
    for sh in ((0, 1), (1, 0)):
        a2 = np.roll(img_arg, sh, axis=(0, 1))
        z2 = np.roll(img_z, sh, axis=(0, 1))
        seam |= (a2 != img_arg) & (z2 == img_z)
    seam &= ~np.isin(img_z, [zk["mask"], zk["skin"], zk["eye"], zk["glove"], zk["palm"]])
    seam = seam.ravel()
    # chest pockets (outline + flap line), drawn on the jacket front
    pk = np.zeros(len(P), bool)
    for sx in (1, -1):
        cx = 0.078 * sx
        inside = (np.abs(x - cx) < 0.05) & (z > 1.27) & (z < 1.39) & (y < -0.06)
        edge = inside & ((np.abs(np.abs(x - cx) - 0.05) < 0.0025) | (np.abs(z - 1.27) < 0.0025) | (np.abs(z - 1.355) < 0.002))
        pk |= edge & (zi == zk["jacket"])
    # cargo pocket flap line
    flap = (zi == zk["pocket"]) & (np.abs(z - (0.915 + (0.505 - 0.915) * 0.52 + 0.05)) < 0.003)
    # colour --------------------------------------------------------------
    n1 = body.vnoise(P, 900, 11) * 0.5 + body.vnoise(P, 2400, 12) * 0.5     # weave grain
    n2 = body.vnoise(P, 14, 13)                                             # broad wear / dirt
    knit = np.sin((x * 900 + body.vnoise(P, 60, 14) * 2.0)) * 0.5 + 0.5     # balaclava ribs
    aof = ao.reshape(-1)
    out = {}
    for name, pal in OUTFITS.items():
        base = np.zeros((len(P), 3))
        for k, i in zk.items():
            m = zi == i
            if not m.any():
                continue
            if k == "eye":
                c = np.where(iris[m, None], np.array([0.09, 0.06, 0.045]), np.array([0.62, 0.58, 0.53]))
            else:
                c = np.array(pal.get(k, pal["jacket"]))[None].repeat(m.sum(), 0)
            base[m] = c
        g = 1.0 + 0.06 * n1 + 0.07 * n2
        g = np.where(zi == zk["mask"], g * (0.92 + 0.12 * knit), g)
        g = np.where(np.isin(zi, [zk["boot"], zk["sole"]]), 1.0 + 0.05 * n1 + 0.12 * n2, g)
        g = np.where(np.isin(zi, [zk["skin"], zk["eye"]]), 1.0 + 0.02 * n1, g)
        col = base * g[:, None]
        col = np.where(seam[:, None], col * 0.72, col)
        col = np.where((pk | flap)[:, None], col * 0.68, col)
        # dust on the boots and the trouser hems, a bit on the knees
        dust = np.clip((p["boot_z"] + 0.08 - z) / 0.25, 0, 1) * (0.5 + 0.5 * n2) * 0.25
        dust *= ~np.isin(zi, [zk["glove"], zk["palm"]])
        col = col * (1 - dust[:, None]) + np.array([0.33, 0.29, 0.24]) * dust[:, None]
        # occlusion into the colour (direct light has no AO in the engine)
        col *= (0.55 + 0.45 * aof)[:, None]
        out[name] = np.clip(col, 0, 1).reshape(size, size, 3).astype(np.float32)
    rough = np.array([ROUGH.get(k, 0.85) for k in ZONE_KEYS])[zi] + 0.05 * n1 - 0.04 * n2
    metal = np.array([METAL.get(k, 0.0) for k in ZONE_KEYS])[zi]
    orm = np.stack([aof, np.clip(rough, 0.05, 1.0), metal], 1).reshape(size, size, 3).astype(np.float32)
    stats = {k: float((zi == i).mean()) for k, i in zk.items()}
    return out, orm, stats


def save_webp(img_np, path, name, non_color=False):
    """Write an sRGB / data image as WebP (variants not referenced by the glTF)."""
    h, w = img_np.shape[:2]
    img = bpy.data.images.new(name + "_save", w, h, alpha=False, float_buffer=False)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    set_pixels(img, img_np)
    img.filepath_raw = path
    img.file_format = "WEBP"
    sc = bpy.context.scene
    sc.render.image_settings.file_format = "WEBP"
    sc.render.image_settings.quality = 85
    img.save_render(path, scene=sc)
    bpy.data.images.remove(img)
