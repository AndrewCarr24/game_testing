"""Shared helpers for asset generator scripts.

Every asset script rebuilds its collection from scratch, so re-running a script
with new parameters is always safe.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector


# ---------------------------------------------------------------- scene / data

def fresh_collection(name):
    """Return collection `name`, emptied of objects (created if missing)."""
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    datas = [ob.data for ob in col.all_objects if ob.data is not None]
    for ob in list(col.all_objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for data in datas:
        try:  # Blender may already have freed orphaned data
            if data.users == 0:
                getattr(bpy.data, {"Mesh": "meshes", "Curve": "curves"}[data.bl_rna.identifier]).remove(data)
        except (ReferenceError, KeyError):
            pass
    return col


def link(ob, col, parent=None):
    col.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    return ob


def empty(name, col, location=(0, 0, 0)):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_type = "PLAIN_AXES"
    ob.empty_display_size = 0.2
    ob.location = location
    return link(ob, col)


def mesh_object(name, bm, col, mat=None, parent=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    if mat is not None:
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    return link(ob, col, parent)


# ------------------------------------------------------------------ materials

def pbr_material(name, color, roughness=0.5, metallic=0.0, coat=0.0):
    """Principled BSDF only, so it survives glTF export unchanged."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat
    mat.diffuse_color = (*color, 1.0)
    mat.roughness = roughness
    mat.metallic = metallic
    return mat


def _image_node(mat, image, location):
    nodes = mat.node_tree.nodes
    tex = next((n for n in nodes if n.type == "TEX_IMAGE" and n.image == image), None)
    if tex is None:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = image
    tex.location = location
    return tex


def set_base_color_map(mat, image):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    tex = _image_node(mat, image, (bsdf.location.x - 400, bsdf.location.y))
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])


def set_normal_map(mat, image, strength=1.0):
    nodes = mat.node_tree.nodes
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    tex = _image_node(mat, image, (bsdf.location.x - 600, bsdf.location.y - 350))
    nm = next((n for n in nodes if n.type == "NORMAL_MAP"), None) or nodes.new("ShaderNodeNormalMap")
    nm.location = (bsdf.location.x - 250, bsdf.location.y - 350)
    nm.inputs["Strength"].default_value = strength
    mat.node_tree.links.new(tex.outputs["Color"], nm.inputs["Color"])
    mat.node_tree.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])


# ----------------------------------------------------------------- primitives

def _remap(t, h, e, n):
    """Map a uniform grid coordinate t in [-1, 1] (n segments) to [-h, h],
    putting a support loop at distance e from each face so subdivision gives a
    tight, controlled edge radius."""
    i = round((t + 1) / 2 * n)
    inner = [(-h + e) + (2 * (h - e)) * k / (n - 2) for k in range(n - 1)]
    pos = [-h] + inner + [h]
    return pos[i]


def cushion_bmesh(size, cuts=6, edge=0.025, crown=None):
    """Box with support loops and a soft crown on each face.

    size: (x, y, z) full dimensions, centred on the origin.
    crown: dict of face -> bulge in metres, keys '+x' '-x' '+y' '-y' '+z' '-z'.
    Meant to be used with a Subdivision Surface modifier.
    """
    crown = crown or {}
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    n = cuts + 1
    half = [s / 2 for s in size]
    for v in bm.verts:
        t = [max(-1.0, min(1.0, c)) for c in v.co]
        p = [_remap(t[a], half[a], min(edge, half[a] * 0.45), n) for a in range(3)]
        u = [p[a] / half[a] for a in range(3)]
        for a, axis in enumerate("xyz"):
            o1, o2 = [b for b in range(3) if b != a]
            amp = crown.get(("+" if u[a] >= 0 else "-") + axis, 0.0)
            p[a] += amp * u[a] * (1 - u[o1] ** 2) * (1 - u[o2] ** 2)
        v.co = Vector(p)
    return bm


def box_bmesh(size):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    return bm


def add_subsurf(ob, levels=1, render_levels=2):
    m = ob.modifiers.new("Subdivision", "SUBSURF")
    m.levels = levels
    m.render_levels = render_levels
    return m


def add_bevel(ob, width, segments=3):
    m = ob.modifiers.new("Bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    m.harden_normals = True
    return m


# ---------------------------------------------------------------------- tubes

def fillet_polyline(points, radius, segments=8, closed=True):
    """Round every corner of a 3D polyline with an arc of `radius`
    (bent-tube look). Returns a new list of points."""
    pts = [Vector(p) for p in points]
    count = len(pts)
    out = []
    for i in range(count):
        b = pts[i]
        if not closed and (i == 0 or i == count - 1):
            out.append(b)
            continue
        a, c = pts[i - 1], pts[(i + 1) % count]
        u, v = (a - b).normalized(), (c - b).normalized()
        theta = u.angle(v)
        if theta > math.pi - 1e-4:
            out.append(b)
            continue
        r = min(radius, 0.45 * min((a - b).length, (c - b).length) * math.tan(theta / 2))
        t = r / math.tan(theta / 2)
        t1, t2 = b + u * t, b + v * t
        centre = b + (u + v).normalized() * (r / math.sin(theta / 2))
        d1, d2 = t1 - centre, t2 - centre
        for k in range(segments + 1):
            f = k / segments
            # mathutils' slerp returns a unit vector, so rescale to the radius
            out.append(centre + d1.slerp(d2, f).normalized() * r)
    return out


def tube_object(name, points, radius, col, mat=None, parent=None, closed=True,
                profile_res=3):
    """Sweep a round profile along `points` and return a real mesh object."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_mode = "ROUND"
    cu.bevel_depth = radius
    cu.bevel_resolution = profile_res
    cu.use_fill_caps = not closed
    sp = cu.splines.new("POLY")
    sp.points.add(len(points) - 1)
    for p, co in zip(sp.points, points):
        p.co = (*co, 1.0)
    sp.use_cyclic_u = closed
    tmp = bpy.data.objects.new(name + "_tmp", cu)
    col.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.curves.remove(cu)
    me.name = name
    for p in me.polygons:
        p.use_smooth = True
    if mat is not None:
        me.materials.clear()
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    return link(ob, col, parent)


def piping_loop(size, axis, inset, corner):
    """Points of a rounded-rectangle loop running round the edge of the face
    of a cushion of `size` whose normal is +/-`axis` (returns both loops)."""
    a = "xyz".index(axis)
    o1, o2 = [b for b in range(3) if b != a]
    h = [s / 2 - inset for s in size]
    loops = []
    for sign in (1, -1):
        rect = []
        for c1, c2 in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            p = [0.0, 0.0, 0.0]
            p[a] = sign * h[a]
            p[o1] = c1 * h[o1]
            p[o2] = c2 * h[o2]
            rect.append(p)
        loops.append(fillet_polyline(rect, corner, segments=6, closed=True))
    return loops


# ------------------------------------------------------------------- finishing

def box_uv(ob, tile=1.0):
    """World-scale box projection: 1 UV unit = `tile` metres, and on every
    face u runs along the object's longest axis available (wood grain)."""
    me = ob.data
    dims = [max(v.co[a] for v in me.vertices) - min(v.co[a] for v in me.vertices) for a in range(3)]
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        n = [abs(c) for c in poly.normal]
        na = n.index(max(n))
        a, b = [i for i in range(3) if i != na]
        if dims[b] > dims[a]:
            a, b = b, a
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (co[a] / tile, co[b] / tile)


def smart_uv(objects, angle=66.0, margin=0.02):
    """Give each mesh its own UV layout (needed later for baked textures)."""
    view_layer = bpy.context.view_layer
    for ob in objects:
        if ob.type != "MESH":
            continue
        for o in view_layer.objects.selected:
            o.select_set(False)
        view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin)
        bpy.ops.object.mode_set(mode="OBJECT")
        ob.select_set(False)


def triangle_count(objects):
    dg = bpy.context.evaluated_depsgraph_get()
    total = 0
    for ob in objects:
        if ob.type != "MESH":
            continue
        me = ob.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        total += len(me.loop_triangles)
        ob.evaluated_get(dg).to_mesh_clear()
    return total


def export_gltf(root, filepath, texture_dir="textures", image_format="WEBP", quality=88):
    """Export `root` and its children for the web: .gltf + .bin, with images
    converted to WebP in a texture folder shared by every asset (relative to the
    .gltf), so a texture used by several assets downloads once."""
    _export(root, filepath, export_format="GLTF_SEPARATE", export_texture_dir=texture_dir,
            export_image_format=image_format, export_image_quality=quality,
            # Draco-compressed geometry: several times smaller downloads (three.js DRACOLoader)
            export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
            export_draco_position_quantization=14, export_draco_normal_quantization=10,
            export_draco_texcoord_quantization=12)


def export_glb(root, filepath):
    """Export `root` and its children as a single self-contained .glb."""
    _export(root, filepath, export_format="GLB")


def _export(root, filepath, **opts):
    view_layer = bpy.context.view_layer
    for o in view_layer.objects.selected:
        o.select_set(False)
    root.select_set(True)
    for ob in root.children_recursive:
        ob.select_set(True)
    view_layer.objects.active = root
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        **opts,
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_extras=True,   # custom properties (e.g. "interact") -> node extras
    )
    for o in view_layer.objects.selected:
        o.select_set(False)


def rounded_slab_bmesh(width, depth, thickness, corner, segments=8):
    """Slab with rounded corners in plan, centred on the origin."""
    hw, hd, ht = width / 2, depth / 2, thickness / 2
    outline = fillet_polyline([(-hw, -hd, 0), (hw, -hd, 0), (hw, hd, 0), (-hw, hd, 0)],
                              corner, segments=segments, closed=True)
    bm = bmesh.new()
    verts = [bm.verts.new((p.x, p.y, -ht)) for p in outline]
    face = bm.faces.new(verts)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    top = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, thickness), verts=top)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def sled_loop(x, y_front, y_back, z_top, radius, bend, rake=0.0, segments=8):
    """Closed side loop in the YZ plane at `x`: floor runner, rear upright,
    top rail, front upright (optionally raked back by `rake`)."""
    corners = [(x, y_front, radius), (x, y_back, radius),
               (x, y_back, z_top), (x, y_front + rake, z_top)]
    return fillet_polyline(corners, bend, segments=segments, closed=True)


def duplicate_hierarchy(root, col, suffix):
    """Linked copy of `root` and its children (meshes shared, like an instance)."""
    mapping = {}
    for ob in [root] + list(root.children_recursive):
        c = ob.copy()
        c.name = ob.name + suffix
        col.objects.link(c)
        mapping[ob] = c
    for ob, c in mapping.items():
        if ob.parent in mapping:
            c.parent = mapping[ob.parent]
    return mapping[root]


# --------------------------------------------------------- Blender -> glTF

def to_gltf(v):
    """Blender (Z-up) point -> glTF (Y-up): (x, y, z) -> (x, z, -y)."""
    return [round(v[0], 4), round(v[2], 4), round(-v[1], 4)]


def world_aabb(objects):
    dg = bpy.context.evaluated_depsgraph_get()
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for ob in objects:
        if ob.type != "MESH":
            continue
        ev = ob.evaluated_get(dg)
        for c in ev.bound_box:
            w = ev.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def aabb_gltf(lo, hi):
    a, b = to_gltf(lo), to_gltf(hi)
    return {"min": [min(a[i], b[i]) for i in range(3)], "max": [max(a[i], b[i]) for i in range(3)]}


# ------------------------------------------------------------ baked lighting

def lightmap_uv(objects, solids, air, resolution=1024, padding=4, name="Lightmap"):
    """Second UV layer for baked lighting (exported as TEXCOORD_1).

    Every face that can be seen from the air inside `bounds` gets its own
    rectangle in one shared atlas at a uniform texel density; faces buried in
    another solid or facing out of the bounds collapse to a corner so they
    don't waste space. Meant for axis-aligned architecture (box faces).
    solids: list of (lo, hi) boxes; air: list of (lo, hi) boxes the player can be in.
    A face counts as visible if any of five sample points on it borders air.
    Returns texels per metre."""

    def in_air(p):
        inside = any(all(lo[i] - 1e-6 <= p[i] <= hi[i] + 1e-6 for i in range(3)) for lo, hi in air)
        buried = any(all(s_lo[i] < p[i] < s_hi[i] for i in range(3)) for s_lo, s_hi in solids)
        return inside and not buried

    faces = []   # (ob, poly, axes, mins, size)
    for ob in objects:
        me = ob.data
        if name not in me.uv_layers:
            me.uv_layers.new(name=name)
        me.uv_layers.active_index = 0
        off = Vector(ob.location)
        for poly in me.polygons:
            n = [abs(c) for c in poly.normal]
            na = n.index(max(n))
            axes = [i for i in range(3) if i != na]
            cos = [off + me.vertices[vi].co for vi in poly.vertices]
            mins = [min(c[a] for c in cos) for a in axes]
            size = [max(c[a] for c in cos) - mins[k] for k, a in enumerate(axes)]
            centre = off + poly.center + poly.normal * 0.05
            samples = [centre]
            for f0, f1 in ((0.1, 0.1), (0.9, 0.1), (0.1, 0.9), (0.9, 0.9)):
                q = centre.copy()
                q[axes[0]] = mins[0] + f0 * size[0]
                q[axes[1]] = mins[1] + f1 * size[1]
                samples.append(q)
            if not any(in_air(q) for q in samples):
                continue
            faces.append((ob, poly, axes, mins, size))

    def pack(k):
        """Shelf-pack all rectangles at k texels/metre; return placements or None."""
        order = sorted(range(len(faces)), key=lambda i: -faces[i][4][1])
        x = y = shelf = 0
        out = {}
        for i in order:
            w = faces[i][4][0] * k + 2 * padding
            h = faces[i][4][1] * k + 2 * padding
            if x + w > resolution:
                x, y, shelf = 0, y + shelf, 0
            if w > resolution or y + h > resolution:
                return None
            out[i] = (x + padding, y + padding)
            x += w
            shelf = max(shelf, h)
        return out

    lo_k, hi_k = 1.0, float(resolution)
    for _ in range(40):
        mid = (lo_k + hi_k) / 2
        lo_k, hi_k = (mid, hi_k) if pack(mid) else (lo_k, mid)
    k = int(lo_k * 0.995)
    placed = pack(k)

    for ob in objects:
        layer = ob.data.uv_layers[name]
        for d in layer.data:
            d.uv = (0.0, 0.0)
    for i, (ob, poly, axes, mins, size) in enumerate(faces):
        px, py = placed[i]
        layer = ob.data.uv_layers[name]
        off = Vector(ob.location)
        for li in poly.loop_indices:
            co = off + ob.data.vertices[ob.data.loops[li].vertex_index].co
            u = px + (co[axes[0]] - mins[0]) * k
            v = py + (co[axes[1]] - mins[1]) * k
            layer.data[li].uv = (u / resolution, v / resolution)
    return k


# ------------------------------------------------------------------ collision

# trim and small wall fixtures that never block the player (standing on a 1 cm
# keycard reader is not a thing)
COLLIDER_SKIP = ("Piping", "Reader", "Canopy", "NoCollide")


def part_colliders(parts, skip=COLLIDER_SKIP):
    """One box per mesh part (asset at the origin), in glTF coords, so the
    player can stand on a seat or a desktop instead of on the asset's overall
    bounding box. Parts under an interactable (anything with an "interact"
    property) move, so the engine gives them their own dynamic collider."""
    def moves(ob):
        while ob is not None:
            if "interact" in ob.keys():
                return True
            ob = ob.parent
        return False
    return [aabb_gltf(*world_aabb([ob])) for ob in parts
            if ob.type == "MESH" and not moves(ob) and not any(s in ob.name for s in skip)]
