"""The grounds around the house (plan.GROUNDS): lawn, stone terrace, perimeter hedge, and
the outdoor zones dressed by blender/levels/outdoor/<zone>.py.

Everything outdoors ends up in a few merged meshes in the "<Name>_Outdoor" collection,
exported to assets/models/<name>_outdoor.gltf (separately from the shell):
  <Name>_Outdoor_Flat        every untextured material; bake.py bakes colour x light into
                             its vertex colours and collapses it to one material
  <Name>_Outdoor_<Material>  one per textured palette material (stone, teak, foliage,
                             grass, gravel); vertex colours = baked light
  <Name>_Outdoor_Water / _Glass
Their lighting is baked into vertex colours (bake.py), so the engine draws them unlit
(one texture fetch at most): no real-time light, no shadow lookups. Big flat surfaces are
generated as grids so the vertex lighting has the resolution to show the house's shadow.
They are in the bake scene, so the lawn's bounce light reaches the rooms too.
"""
import importlib
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

from lib import common, outdoor, textures

import ground_colliders

HERE = os.path.dirname(os.path.abspath(__file__))
importlib.reload(ground_colliders)
if os.path.join(HERE, "outdoor") not in sys.path:
    sys.path.insert(0, os.path.join(HERE, "outdoor"))


# ------------------------------------------------------------------ base surfaces
def _axis_coords(lo, hi, near, fine, coarse):
    """Grid lines from lo to hi: `fine` spacing inside the `near` band, `coarse` outside."""
    out, x = [], lo
    while x < hi - 1e-6:
        out.append(x)
        x = min(hi, x + (fine if near[0] - 1e-6 <= x < near[1] else coarse))
        if x > near[0] and out[-1] < near[0]:
            x = near[0]
    out.append(hi)
    return sorted(set(round(v, 4) for v in out))


def grid_mesh(name, xs, ys, z, col, mat, uv_tile, skip=None):
    """Flat upward-facing grid at height z with vertices at xs x ys; quads for which
    skip(cx, cy) is true are left out (the lawn under the house)."""
    bm = bmesh.new()
    vid = {}
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            vid[i, j] = bm.verts.new((x, y, z))
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if skip and skip(cx, cy):
                continue
            bm.faces.new((vid[i, j], vid[i + 1, j], vid[i + 1, j + 1], vid[i, j + 1]))
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            lp[uv].uv = (lp.vert.co.x / uv_tile, lp.vert.co.y / uv_tile)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


def segmented_box(name, lo, hi, step, col, mat, uv_tile):
    """Box whose long horizontal axis is cut every `step` metres (for vertex lighting)."""
    axis = 0 if hi[0] - lo[0] >= hi[1] - lo[1] else 1
    n = max(1, round((hi[axis] - lo[axis]) / step))
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=[hi[i] - lo[i] for i in range(3)], verts=bm.verts)
    bmesh.ops.translate(bm, vec=[(hi[i] + lo[i]) / 2 for i in range(3)], verts=bm.verts)
    for k in range(1, n):
        c = lo[axis] + (hi[axis] - lo[axis]) * k / n
        no = [0, 0, 0]
        no[axis] = 1
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=[c if i == axis else 0 for i in range(3)], plane_no=no)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    common.box_uv(ob, tile=uv_tile)
    return ob


def base(plan, col):
    G, z = plan.GROUNDS, plan.LAWN_Z
    lx0, ly0, lx1, ly1 = G["lawn"]
    # 1.5 m cells within ~12 m of the house (its shadow, the terrace edge), 6 m beyond
    xs = _axis_coords(lx0, lx1, (-38, 38), 1.5, 6.0)
    ys = _axis_coords(ly0, ly1, (-32, 32), 1.5, 6.0)
    # (the bathhouse: grid lines on its footprint, no lawn under it: plan.LAWN_HOLES)
    holes = getattr(plan, "LAWN_HOLES", [])
    xs = sorted(set(xs) | {h[i] for h in holes for i in (0, 2)})
    ys = sorted(set(ys) | {h[i] for h in holes for i in (1, 3)})
    house = lambda cx, cy: (abs(cx) < 26 and abs(cy) < 20) or any(h[0] < cx < h[2] and h[1] < cy < h[3] for h in holes)
    objs = [grid_mesh("Lawn", xs, ys, z, col, outdoor.grass(), 3.0, skip=house)]
    for i, (x0, y0, x1, y1) in enumerate(G["terrace"]):
        gx = _axis_coords(x0, x1, (x0, x1), 1.5, 1.5)
        gy = _axis_coords(y0, y1, (y0, y1), 1.5, 1.5)
        objs.append(grid_mesh(f"Terrace_{i}", gx, gy, z + 0.06, col, outdoor.stone(), 2.0))
    hd = G["hedge"]
    x0, y0, x1, y1 = hd["rect"]
    t, ht = hd["thick"], hd["height"]
    sides = {"s": ("x", y0, x0, x1), "n": ("x", y1, x0, x1), "w": ("y", x0, y0, y1), "e": ("y", x1, y0, y1)}
    for side, (axis, line, a0, a1) in sides.items():
        spans = [(a0, a1)]
        for gs, g0, g1 in hd["gaps"]:
            if gs == side:
                spans = [s for (b0, b1) in spans for s in ((b0, min(b1, g0)), (max(b0, g1), b1)) if s[1] - s[0] > 0.1]
        for j, (b0, b1) in enumerate(spans):
            lo, hi = ((b0, line - t / 2, z), (b1, line + t / 2, z + ht)) if axis == "x" else \
                     ((line - t / 2, b0, z), (line + t / 2, b1, z + ht))
            objs.append(segmented_box(f"Hedge_{side}{j}", lo, hi, 3.0, col, outdoor.foliage(), 1.5))
    return objs


# ------------------------------------------------------------------ the house's outside
def plane_grid(name, origin, du, dv, step, col, mat, uv_tile=2.0):
    """A flat grid from `origin` spanning vectors du, dv (its normal is du x dv), cut about
    every `step` metres both ways (vertex lighting)."""
    o, du, dv = Vector(origin), Vector(du), Vector(dv)
    nu, nv = max(1, round(du.length / step)), max(1, round(dv.length / step))
    bm = bmesh.new()
    vs = [[bm.verts.new(o + du * (i / nu) + dv * (j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
    uv = bm.loops.layers.uv.new("UVMap")
    ua, va = du.normalized(), dv.normalized()
    for f in bm.faces:
        for lp in f.loops:
            lp[uv].uv = (lp.vert.co.dot(ua) / uv_tile, lp.vert.co.dot(va) / uv_tile)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


def _subtract(spans, a0, a1):
    """1D: spans [(s0, s1)] minus (a0, a1)."""
    out = []
    for s0, s1 in spans:
        for b0, b1 in ((s0, min(s1, a0)), (max(s0, a1), s1)):
            if b1 - b0 > 1e-4:
                out.append((b0, b1))
    return out


def house_exterior(h, plan, col, off=0.01, coping=(0.3, 0.25)):
    """The outside of the house shell, outdoor-baked like the grounds (it was unlit black
    through the upper windows): the facades (white render, 1 cm proud of the shell's outer
    faces, around every window and door), the roofs (a sedum mat on the low roofs over the
    cloakroom and garage, gravel on the main roof) and a stone coping round each roof edge
    where nothing rises beyond it."""
    objs = []
    render = outdoor.render_white()
    # (the bathhouse: its rooms name their facade, "stone": the same coursed stone as inside)
    facade = {"stone": outdoor.coursed_stone()}
    lawn = plan.LAWN_Z + 0.06                       # the terrace surface
    for k, (axis, line, sign, a0, a1, z0, z1, room) in enumerate(h.exterior_walls(with_room=True)):
        mat = facade.get(plan.ROOMS[room].get("facade"), render)
        z0 = max(z0, lawn - 0.02 if not plan.ROOMS[room].get("building") else plan.LAWN_Z - 0.02)
        if z1 - z0 < 1e-3:
            continue
        L = line + sign * off
        if axis == "x":         # wall along x at y = L, normal (0, sign, 0)
            o, du, dv = ((a0, L, z0), (a1 - a0, 0, 0), (0, 0, z1 - z0)) if sign < 0 else \
                        ((a1, L, z0), (a0 - a1, 0, 0), (0, 0, z1 - z0))
        else:                   # wall along y at x = L, normal (sign, 0, 0)
            o, du, dv = ((L, a1, z0), (0, a0 - a1, 0), (0, 0, z1 - z0)) if sign < 0 else \
                        ((L, a0, z0), (0, a1 - a0, 0), (0, 0, z1 - z0))
        objs.append(plane_grid(f"Facade_{k}", o, du, dv, 1.5, col, mat))
    tops = {r: h.outer_z(r)[1] for r in plan.ROOMS}
    sedum, gravel, stone = outdoor.sedum(), outdoor.gravel(), outdoor.stone()
    cw, chh = coping
    for k, (room, (x0, y0, x1, y1), top) in enumerate(h.roofs()):
        if top < plan.LAWN_Z:
            continue                                # (underground: the secret passage's rooms)
        low = top < plan.TOP
        objs.append(plane_grid(f"Roof_{k}", (x0, y0, top + off), (x1 - x0, 0, 0), (0, y1 - y0, 0),
                               1.0 if low else 3.0, col, sedum if low else gravel))
        # coping along the edges nothing rises beyond (the facade, the courtyard)
        for side, line, b0, b1 in (("S", y0, x0, x1), ("N", y1, x0, x1), ("W", x0, y0, y1), ("E", x1, y0, y1)):
            spans = [(b0, b1)]
            for o, q in plan.ROOMS.items():
                if o == room or q.get("kind") == "courtyard" or tops[o] < top - 1e-6:
                    continue
                qx0, qy0, qx1, qy1 = q["rect"]
                near = {"S": qy1, "N": qy0, "W": qx1, "E": qx0}[side]
                if abs(near - line) > 1e-6:
                    continue
                c0, c1 = (qx0, qx1) if side in "SN" else (qy0, qy1)
                spans = _subtract(spans, c0, c1)
            for j, (s0, s1) in enumerate(spans):
                if side == "S":
                    lo, hi = (s0, y0, top), (s1, y0 + cw, top + chh)
                elif side == "N":
                    lo, hi = (s0, y1 - cw, top), (s1, y1, top + chh)
                elif side == "W":
                    lo, hi = (x0, s0, top), (x0 + cw, s1, top + chh)
                else:
                    lo, hi = (x1 - cw, s0, top), (x1, s1, top + chh)
                objs.append(segmented_box(f"Coping_{k}_{side}{j}", lo, hi, 1.5, col, stone, 2.0))
    return objs


# ------------------------------------------------------------------ zones
def zone_module(name):
    try:
        mod = importlib.import_module(name)
    except ModuleNotFoundError:
        print(f"SKIP zone {name}: no blender/levels/outdoor/{name}.py yet")
        return None
    importlib.reload(mod)
    return mod


def place_zones(plan, col, roots, zones_only=None):
    """Instantiate every zone's PLACEMENTS as world-space copies in `col`. roots: assets
    already built for the rooms (reused: rebuilding an asset would wipe its collection)."""
    built, temp, placed, report = dict(roots), [], [], {}
    for zone, info in plan.GROUNDS["zones"].items():
        if zones_only and zone not in zones_only:
            continue
        mod = zone_module(zone)
        if mod is None:
            continue
        x0, y0, x1, y1 = info["rect"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        tris = 0
        for entry in getattr(mod, "PLACEMENTS", []):
            asset, pos, rot = entry[:3]
            if asset not in built or built[asset] is None:
                try:
                    amod = importlib.import_module(asset)
                except ModuleNotFoundError:
                    print(f"SKIP {asset}: no blender/assets/{asset}.py yet")
                    built[asset] = None
                    continue
                importlib.reload(amod)
                built[asset], _ = amod.build()
                temp.append(built[asset])
            src = built[asset]
            if src is None:
                continue
            x, y = pos[0], pos[1]
            z = pos[2] if len(pos) > 2 else 0.0
            world = Matrix.Translation((cx + x, cy + y, plan.LAWN_Z + z)) @ Matrix.Rotation(math.radians(rot), 4, "Z")
            # the source's own transform is ignored: assets are modelled at the origin
            src_inv = src.matrix_world.inverted()
            for ob in [src] + list(src.children_recursive):
                if ob.type != "MESH" or not ob.data.polygons:
                    continue
                if any(t in ob.name for t in ("Collider", "NoBake")):
                    continue
                me = ob.data.copy()
                me.transform(world @ src_inv @ ob.matrix_world)
                me.update()
                cp = bpy.data.objects.new(f"{zone}_{ob.name}", me)
                col.objects.link(cp)
                placed.append(cp)
                tris += sum(len(p.vertices) - 2 for p in me.polygons)
        budget = info.get("tris")
        report[zone] = tris
        print(f"ZONE {zone}: {tris} triangles (budget {budget}){'  WARN over budget' if budget and tris > budget else ''}")
    # remove the hierarchies built only for the grounds (they sit at the origin, inside the house)
    for root in temp:
        cols = set(root.users_collection)
        for ob in [root] + list(root.children_recursive):
            bpy.data.objects.remove(ob, do_unlink=True)
        for c in cols:
            if c.name != "Scene Collection" and not c.objects and not c.children:
                bpy.data.collections.remove(c)
    return placed, report


# ------------------------------------------------------------------ merging
def kind_of(mat):
    if mat is None:
        return "flat"
    if mat.name.startswith("M_Water"):
        return "water"
    if mat.name == "M_Out_Glass":
        return "glass"
    textured = mat.use_nodes and any(n.type == "TEX_IMAGE" and n.image for n in mat.node_tree.nodes)
    return "textured" if textured else "flat"


def split_by_material(ob, col):
    """One object per material of `ob` (world space already)."""
    me = ob.data
    used = sorted({p.material_index for p in me.polygons})
    if len(used) <= 1:
        mat = me.materials[used[0]] if me.materials and used else None
        if len(me.materials) > 1 and mat is not None:
            me.materials.clear()
            me.materials.append(mat)
            for p in me.polygons:
                p.material_index = 0
        return [ob]
    out = []
    for mi in used:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != mi], context="FACES")
        for f in bm.faces:
            f.material_index = 0
        m2 = bpy.data.meshes.new(f"{me.name}_{mi}")
        bm.to_mesh(m2)
        bm.free()
        m2.materials.append(me.materials[mi])
        o2 = bpy.data.objects.new(f"{ob.name}_{mi}", m2)
        col.objects.link(o2)
        out.append(o2)
    bpy.data.objects.remove(ob, do_unlink=True)
    return out


def merge(objs, col, name, root):
    groups = {}
    for ob in objs:
        for part in split_by_material(ob, col):
            mat = part.data.materials[0] if part.data.materials else None
            kind = kind_of(mat)
            key = ("Flat" if kind == "flat" else "Water" if kind == "water" else "Glass" if kind == "glass"
                   else mat.name.replace("M_Grounds_", "").replace("M_Out_", ""))
            groups.setdefault((key, kind), []).append(part)
    merged = []
    for (key, kind), parts in groups.items():
        if len(parts) > 1:
            with bpy.context.temp_override(active_object=parts[0], selected_editable_objects=parts,
                                           selected_objects=parts, object=parts[0]):
                bpy.ops.object.join()
        ob = parts[0]
        ob.name = ob.data.name = f"{name}_Outdoor_{key}"
        ob["outdoor"] = kind
        ob.parent = root
        attr = ob.data.color_attributes.get("Bake") or ob.data.color_attributes.new("Bake", "FLOAT_COLOR", "CORNER")
        ob.data.color_attributes.active_color = attr
        attr.data.foreach_set("color", [1.0] * (4 * len(attr.data)))
        merged.append(ob)
        print(f"OUTDOOR {ob.name}: {sum(len(p.vertices) - 2 for p in ob.data.polygons)} triangles, "
              f"{len(ob.data.materials)} material(s)")
    return merged


def build(h, plan, roots, zones_only=None, doors=()):
    """roots: asset -> root already built for the rooms. Returns (outdoor root, objects, report,
    walkable) with walkable = ground_colliders.build's (meta, boxes): the colliders that make
    the grounds walkable, from the zones' placed geometry before it's merged."""
    col = common.fresh_collection(f"{h.name}_Outdoor")
    root = common.empty(f"{h.name}_Outdoor", col)
    objs = base(plan, col) + house_exterior(h, plan, col)
    placed, report = place_zones(plan, col, roots, zones_only)
    walkable = ground_colliders.build(plan, placed, doors)
    merged = merge(objs + placed, col, h.name, root)
    return root, merged, report, walkable
