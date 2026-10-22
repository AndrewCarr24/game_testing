"""Baked interior light for the town kit's walk-in buildings (town_bar, ...). Not an asset.

The wild runtime has no real-time lights, so a walk-in's lamps and glowing surfaces are
baked (Cycles, diffuse direct + indirect, no albedo) into the "AO" colour attribute, which
the export writes as COLOR_0 and the runtime multiplies into the base colour. It keeps the
light's colour (a pink wash under the neon, warm pools under the shades), normalised so the
brightest lit surfaces read 1; vertices outside the inner boxes (the exterior), the glow meshes
and the LOD1 stay 1. Faces inside are split finer while the interior is built (kit.sub) so the
pools resolve. Cached by geometry in build/town_light/.
"""
import hashlib
import math
import os

import bpy
import numpy as np
from mathutils import Vector

import town_common as tc

CACHE = os.path.join(tc.PROJECT, "build", "town_light")


def _key(kit, meshes, inner_boxes, params):
    h = hashlib.sha1(repr((kit.lights, sorted(kit.tints.items()), inner_boxes, params, "v3")).encode())
    for o in sorted(meshes, key=lambda o: o.name):
        co = np.zeros(3 * len(o.data.vertices), np.float32)
        o.data.vertices.foreach_get("co", co)
        h.update(o.name.encode())
        h.update(np.round(co, 3).tobytes())
    return h.hexdigest()


def bake(kit, root, meshes, inner_boxes, samples=96, glow_boost=6.0, floor=0.10, ambient=0.012):
    meshes = [o for o in meshes if o.type == "MESH" and o.data.polygons and not o.hide_render]
    key = _key(kit, meshes, inner_boxes, (samples, glow_boost, floor, ambient))
    path = os.path.join(CACHE, f"{root.name}.npz")
    for o in meshes:
        me = o.data
        attr = me.color_attributes.get("AO") or me.color_attributes.new("AO", "FLOAT_COLOR", "POINT")
        me.color_attributes.active_color = attr
    if os.path.exists(path):
        try:
            z = np.load(path)
            if str(z["key"]) == key:
                for o in meshes:
                    o.data.color_attributes["AO"].data.foreach_set("color", z[o.name].ravel())
                print(f"TOWN LIGHT {root.name}: cached")
                return
        except Exception:
            pass
    pre = {}
    for o in meshes:                          # what's there (tints) stays outside the rooms
        v = np.zeros(4 * len(o.data.vertices), np.float32)
        o.data.color_attributes["AO"].data.foreach_get("color", v)
        pre[o] = v.reshape(-1, 4)[:, :3].copy()
    tmp = bpy.data.scenes.new("_TownLight")
    coll = bpy.data.collections.new("_TownLightObjects")
    tmp.collection.children.link(coll)
    for o in [root] + list(root.children_recursive):
        coll.objects.link(o)
    tmp.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        tmp.cycles.device = "GPU"
    except (TypeError, KeyError):
        pass
    tmp.cycles.samples = samples
    w = bpy.data.worlds.new("_TownLightWorld")
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (1, 1, 1, 1)
    bg.inputs["Strength"].default_value = ambient
    tmp.world = w
    lamps = []
    for i, L in enumerate(kit.lights):
        kind = {"SPOT": "SPOT", "AREA": "AREA"}.get(L["kind"], "POINT")
        ld = bpy.data.lights.new(f"_tl{i}", kind)
        ld.energy = L["power"]
        ld.color = L["colour"]
        if kind == "AREA":
            ld.size = L["radius"]
        else:
            ld.shadow_soft_size = L["radius"]
        if kind == "SPOT":
            ld.spot_size = math.radians(120)
            ld.spot_blend = 0.7
        lo = bpy.data.objects.new(f"_tl{i}", ld)
        lo.location = L["pos"]
        if kind in ("SPOT", "AREA"):
            lo.rotation_euler = Vector(L.get("dir") or (0, 0, -1)).to_track_quat("-Z", "Y").to_euler()
        coll.objects.link(lo)
        lamps.append(lo)
    gm = tc._mats.get("glow")
    bsdf = old = None
    if gm is not None:
        bsdf = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        old = bsdf.inputs["Emission Strength"].default_value
        bsdf.inputs["Emission Strength"].default_value = old * glow_boost
    vl = tmp.view_layers[0]
    for o in [o for o in bpy.context.view_layer.objects if o.select_get()]:
        o.select_set(False)
    for o in vl.objects:
        o.select_set(o in meshes, view_layer=vl)
    vl.objects.active = meshes[0]
    try:
        with bpy.context.temp_override(scene=tmp, view_layer=vl, active_object=meshes[0], object=meshes[0],
                                       selected_objects=meshes, selected_editable_objects=meshes):
            bpy.ops.object.bake(type="DIFFUSE", pass_filter={"DIRECT", "INDIRECT"}, target="VERTEX_COLORS")
    finally:
        if bsdf is not None:
            bsdf.inputs["Emission Strength"].default_value = old
        for o in [root] + list(root.children_recursive):
            coll.objects.unlink(o)
        for lo in lamps:
            bpy.data.objects.remove(lo)
        bpy.data.collections.remove(coll)
        bpy.data.scenes.remove(tmp)
    raw, inside = {}, {}
    for o in meshes:
        me = o.data
        v = np.zeros(4 * len(me.vertices), np.float32)
        me.color_attributes["AO"].data.foreach_get("color", v)
        raw[o] = v.reshape(-1, 4)
        co = np.zeros(3 * len(me.vertices), np.float32)
        me.vertices.foreach_get("co", co)
        M = np.array(o.matrix_world)
        co = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
        m = np.zeros(len(co), bool)
        for (a0, b0, c0, a1, b1, c1) in inner_boxes:
            e = 0.03
            m |= ((co[:, 0] > a0 - e) & (co[:, 0] < a1 + e) & (co[:, 1] > b0 - e) & (co[:, 1] < b1 + e)
                  & (co[:, 2] > c0 - e) & (co[:, 2] < c1 + e))
        glow = any(mt is not None and mt.name == "M_Town_Glow" for mt in me.materials)
        inside[o] = m & (not glow)
    lums = [(r[:, :3] @ np.array([0.2126, 0.7152, 0.0722]))[inside[o]] for o, r in raw.items()]
    lum = np.concatenate(lums) if lums else np.ones(1)
    ref = max(float(np.percentile(lum, 97)) if lum.size else 1.0, 1e-4)
    arrays = {}
    for o, r in raw.items():
        c = np.clip(r[:, :3] / ref, 0, 1.0)
        c = floor + (1 - floor) * c
        c = np.round(c * 32) / 32
        c[~inside[o]] = pre[o][~inside[o]]
        r[:, :3] = c
        r[:, 3] = 1
        o.data.color_attributes["AO"].data.foreach_set("color", r.ravel())
        arrays[o.name] = r.copy()
    os.makedirs(CACHE, exist_ok=True)
    tmpf = f"{path}.{os.getpid()}.tmp.npz"
    np.savez_compressed(tmpf, key=np.array(key), **arrays)
    os.replace(tmpf, path)
    print(f"TOWN LIGHT {root.name}: baked {len(kit.lights)} lamps, ref {ref:.4f}")


def fill(objs, value=1.0):
    """A constant "AO" attribute (LOD1s, exterior-only assets) so merged meshes match."""
    for o in objs:
        me = o.data
        attr = me.color_attributes.get("AO") or me.color_attributes.new("AO", "FLOAT_COLOR", "POINT")
        attr.data.foreach_set("color", np.full(4 * len(attr.data), value, np.float32))
