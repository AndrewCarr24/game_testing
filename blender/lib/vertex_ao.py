"""Bake an asset's own ambient occlusion into a per-vertex colour attribute ("AO"; per vertex,
not per face corner, so the export doesn't split vertices), exported as
glTF COLOR_0. three.js multiplies vertex colours into the base colour, so creases, the
undersides of tables and seats and the backs of shelves darken at no runtime cost; the
floor's contact shadow is already in the room's lightmap, so the asset is baked alone
(in a scene of its own), away from the floor.

Shared mesh data means every placement of the asset gets the same AO (it's the asset's
own occlusion, which doesn't depend on where it stands)."""
import os

import bpy

ATTR = "AO"


CACHE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "build", "ao_cache"))


def _key(meshes, params):
    import hashlib
    import numpy as np
    h = hashlib.sha1(repr(params).encode())
    for o in sorted(meshes, key=lambda o: o.name):
        me = o.data
        co = np.zeros(3 * len(me.vertices), np.float32)
        me.vertices.foreach_get("co", co)
        lv = np.zeros(len(me.loops), np.int32)
        me.loops.foreach_get("vertex_index", lv)
        h.update(o.name.encode()); h.update(np.round(co, 4).tobytes()); h.update(lv.tobytes())
        h.update(np.array(o.matrix_local, np.float32).round(4).tobytes())
    return h.hexdigest()


def bake(root, distance=0.3, samples=24, strength=0.6, max_face_area=0.25):
    """Bake (or reuse from build/ao_cache/ when the geometry is unchanged)."""
    import numpy as np
    meshes = [o for o in [root] + list(root.children_recursive) if o.type == "MESH" and o.data.polygons]
    if not meshes:
        return 0
    key = _key(meshes, (distance, samples, strength, max_face_area, "point", 16))
    path = os.path.join(CACHE, f"{root.name}.npz")
    if os.path.exists(path):
        z = np.load(path)
        if str(z["key"]) == key:
            for o in meshes:
                me = o.data
                attr = me.color_attributes.get(ATTR) or me.color_attributes.new(ATTR, "FLOAT_COLOR", "POINT")
                me.color_attributes.active_color = attr
                attr.data.foreach_set("color", z[o.name].ravel())
            return 0
    corners = _bake(root, meshes, distance, samples, strength, max_face_area)
    os.makedirs(CACHE, exist_ok=True)
    arrays = {}
    for o in meshes:
        v = np.zeros(4 * len(o.data.vertices), np.float32)
        o.data.color_attributes[ATTR].data.foreach_get("color", v)
        arrays[o.name] = v
    np.savez_compressed(path, key=np.array(key), **arrays)
    return corners


def _bake(root, meshes, distance, samples, strength, max_face_area):
    tmp = bpy.data.scenes.new("_AOBake")
    coll = bpy.data.collections.new("_AOBakeObjects")
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
    tmp.world = bpy.data.worlds.get("_AOWorld") or bpy.data.worlds.new("_AOWorld")
    tmp.world.light_settings.distance = distance
    for o in meshes:
        me = o.data
        attr = me.color_attributes.get(ATTR)
        if attr is not None and attr.domain != "POINT":
            me.color_attributes.remove(attr)
            attr = None
        attr = attr or me.color_attributes.new(ATTR, "FLOAT_COLOR", "POINT")
        me.color_attributes.active_color = attr
    vl = tmp.view_layers[0]
    # the bake works on the context's selection: make it exactly these meshes, in this scene
    main_sel = [o for o in bpy.context.view_layer.objects if o.select_get()]
    for o in main_sel:
        o.select_set(False)
    for o in vl.objects:
        o.select_set(o in meshes, view_layer=vl)
    vl.objects.active = meshes[0]
    with bpy.context.temp_override(scene=tmp, view_layer=vl, active_object=meshes[0], object=meshes[0],
                                   selected_objects=meshes, selected_editable_objects=meshes):
        bpy.ops.object.bake(type="AO", target="VERTEX_COLORS")
    # normalise to the asset's open surfaces (its 90th percentile reads as unoccluded; raw AO
    # is low on the many corners buried where parts intersect), then soften
    # Large faces are left unoccluded: a big panel has only a few corners, mostly where it
    # meets other parts, so their AO would smear across the whole face; small faces
    # (cushions, legs, mouldings, shelves' insides) are where self-occlusion shows anyway.
    import numpy as np
    datas = list({o.data: o for o in meshes})
    raw, small = {}, {}
    for me in datas:
        attr = me.color_attributes[ATTR]
        v = np.zeros(4 * len(attr.data), np.float32)
        attr.data.foreach_get("color", v)
        raw[me] = v.reshape(-1, 4)
        mask = np.zeros(len(attr.data), bool)            # per vertex: on any small face
        for poly in me.polygons:
            if poly.area < max_face_area:
                mask[list(poly.vertices)] = True
        small[me] = mask
    sel = np.concatenate([r[small[me], 0] for me, r in raw.items()])
    top = max(float(np.percentile(sel, 90)), 1e-3) if sel.size else 1.0
    corners = 0
    for me, r in raw.items():
        a = np.where(small[me], np.clip(r[:, 0] / top, 0, 1), 1.0)
        v = 1.0 - strength * (1.0 - a)
        # 16 levels: invisible on soft shading, and the exporter stores colours at 16 bits
        # regardless of the Draco setting, so few distinct values is what keeps them small
        v = np.round(v * 16) / 16
        r[:, 0] = r[:, 1] = r[:, 2] = v
        r[:, 3] = 1
        me.color_attributes[ATTR].data.foreach_set("color", r.ravel())
        corners += len(r)
    for o in [root] + list(root.children_recursive):
        coll.objects.unlink(o)
    bpy.data.collections.remove(coll)
    bpy.data.scenes.remove(tmp)
    return corners
