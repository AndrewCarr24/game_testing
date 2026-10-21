"""Shared bits for the interactive props (prompts/interactivity.md): the `react` / `interact`
definitions every asset writes the same way, the wall-switch builder, and `wire()`, which
room modules call to put their light fixtures on the room's light switch.

Conventions used here (the engine is viewer/interactables.js):
- `react` / `travel` axes are letter strings in glTF space ("y" = up); new `interact`
  rotate/slide axes are glTF vectors (common.to_gltf), like the existing doors and drawers.
- Glowing parts of light fixtures react to signal "lights" by default (the engine treats a
  never-set signal as off, so the level renames it per placement with
  {"signal": {"lights": "lights_<room>"}} via wire(), and the room's switch starts on).
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)


# ------------------------------------------------------------------ react definitions

def glow(signal="lights"):
    """Emissive on/off: a lamp shade, a bulb, an LED strip, a screen."""
    return {"signal": signal, "on": {"emissive": 1}, "off": {"emissive": 0}}


def tag_glow(root, mats, signal="lights"):
    """Give every mesh under `root` that uses one of `mats` (materials or names) a glow react.
    Returns the tagged objects."""
    names = {m if isinstance(m, str) else m.name for m in mats if m is not None}
    out = []
    for ob in [root] + list(root.children_recursive):
        if ob.type != "MESH":
            continue
        if any(m is not None and m.name in names for m in ob.data.materials):
            ob["react"] = glow(signal)
            out.append(ob)
    return out


def emits(mat):
    """Does this material glow (non-black emission colour, strength > 0)?"""
    if mat is None or not mat.node_tree:
        return False
    b = next((nd for nd in mat.node_tree.nodes if nd.type == "BSDF_PRINCIPLED"), None)
    if b is None:
        return False
    c = b.inputs["Emission Color"].default_value
    return b.inputs["Emission Strength"].default_value > 0 and max(c[0], c[1], c[2]) > 0


def tag_emissive(root, signal="lights", names=None):
    """Glow react on every glowing mesh under `root` (only those whose name contains one of
    `names`, if given). Returns the tagged objects."""
    out = []
    for ob in [root] + list(root.children_recursive):
        if ob.type != "MESH" or (names and not any(k in ob.name for k in names)):
            continue
        if any(emits(m) for m in ob.data.materials):
            ob["react"] = glow(signal)
            out.append(ob)
    return out


# the fixture assets whose glow tag_emissive() puts on "lights" (wire() renames it per room;
# the engine batches reactors sharing a signal and material, so the many ceiling cans are cheap)
FIXTURES = {
    "light_g_downlight", "light_u_downlight",
    "bath_mirror", "bath_pendant", "bath_sconce",
    "dining_chandelier", "dining_pendants",
    "entry_chandelier", "entry_mirror", "entry_mirror_tall", "entry_sconce",
    "guest_floor_lamp",
    "kitchen_pendant",
    "library_floorlamp", "library_lamp",
    "light_g_cove", "light_g_cove_down",
    "light_g_pendant_linear", "light_g_sconce_updown", "light_u_halo", "light_u_linear_pendant",
    "living_chandelier", "living_floor_lamp", "living_table_lamp",
    "table_lamp",
    # built-in LED strips that light the room (shelves, under-cabinet, hood, closet, cases)
    "kitchen_wall_run", "kitchen_range_wall", "kitchen_island", "kitchen_pantry", "kitchen_scullery_run",
    "kitchen_coffee_station", "entry_coat_closet", "dining_climate_wall",
    "garage_cabinets", "garage_slatwall", "garage_vitrine", "living_media_wall",
    # outdoor: the courtyard's festoon strings (its candles aren't electric: LIGHTS signal=None)
    "courtyard_festoon",
}


def wire(placements, room, fixtures=None, state=None):
    """Room modules: every placement of a fixture asset gets {"signal": {"lights": "lights_<room>"}}
    (merged into its options), so it follows the room's light switch. `state` (rooms without a
    switch, e.g. the galleries): the signal's initial value, set from the fixtures themselves.
    Accepts a list or tuple, returns a list."""
    fixtures = FIXTURES if fixtures is None else fixtures
    out = []
    for entry in placements:
        asset, loc, rot, *rest = entry
        if asset not in fixtures:
            out.append(entry)
            continue
        opts = dict(rest[0]) if rest else {}
        sig = opts.get("signal")
        sig = dict(sig) if isinstance(sig, dict) else ({} if sig is None else {"lights": sig})
        sig.setdefault("lights", f"lights_{room}")
        opts["signal"] = sig
        if state is not None:
            opts.setdefault("state", state)
        out.append((asset, loc, rot, opts))
    return out


# ------------------------------------------------------------------ wall switch

def plate_bmesh(w, h, t, corner, segments=3):
    """A flat plate, back at y = 0, front face at y = -t (rounded in plan, so the z extent is h)."""
    bm = common.rounded_slab_bmesh(w, h, t, corner, segments=segments)   # x by y by z
    # rounded_slab is w (x) by h (y) by t (z, from 0 up): turn it to stand on the wall
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                     matrix=Matrix.Rotation(math.radians(90), 3, "X"))
    bmesh.ops.translate(bm, vec=(0, -t / 2, 0), verts=bm.verts)
    return bm


def _marks(bm, marks, y):
    """Raised marks on a face at depth y: (x, z, w, h[, angle]) thin boxes; angle (degrees)
    turns a mark about the face normal (two turned bars make a chevron)."""
    for g in marks:
        gx, gz, gw, gh = g[:4]
        m = Matrix.Translation((gx, y, gz))
        if len(g) > 4 and g[4]:
            m = m @ Matrix.Rotation(math.radians(g[4]), 4, "Y")
        bmesh.ops.create_cube(bm, size=1.0, matrix=m @ Matrix.Diagonal((gw, 0.0008, gh, 1.0)))
    return bm


def _disc(r, depth, y, segments=24):
    """A cylinder facing -Y (its axis along y), centred at depth y."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=r, radius2=r, depth=depth,
                          matrix=Matrix.Translation((0, y, 0)) @ Matrix.Rotation(math.radians(90), 4, "X"))
    return bm


def chevron(x, z, up=True, size=0.011, bar=0.0018, spread=40):
    """Two glyph bars making a ^ (up) or a v (down), centred on (x, z)."""
    c, s = math.cos(math.radians(spread)), math.sin(math.radians(spread))
    a = 1 if up else -1
    # the bars meet at the tip, half the chevron's height above (below) the centre, so each
    # bar's own centre is level with it
    return [(x - c * size / 2, z, size, bar, -a * spread),
            (x + c * size / 2, z, size, bar, a * spread)]


# a control's kind reads from across the room: plate shape and finish, the moving part, its light
PLATES = {
    "graphite": lambda: common.pbr_material("M_Switch_Plate_Graphite", (0.035, 0.034, 0.033), roughness=0.42,
                                            metallic=0.6),
    "bronze": lambda: materials.bronze(),
}


def switch(n, col, root, p):
    """A single-gang wall control. Origin: the plate's back centre (on the wall surface); the
    front faces -Y. The moving part is its own empty (`<n>_Rocker`) carrying the `switch`
    interact; a locator LED (`<n>_Locator`) is the switch's indicator.

    p: plate_size (w, h, t), plate ("graphite" | "bronze"), plate_shape ("rect" | "round"),
    part ("paddle": a rocker that tips | "knob": turns a quarter | "button": pushes in),
    rocker_size (the moving part's w, h, t; a knob's / button's diameter is w),
    glyphs (raised marks on the paddle / button), paddle ((name, colour) of the moving part's
    material), plate_marks (marks printed on the plate: their own static mesh, material
    marks = (name, colour)), led ((name, colour, strength)), led_at ((x, z) on the plate,
    static; default: under the paddle, moving with it), ring (radius of a lit ring round a
    button, the indicator), travel (overrides the part's)."""
    plate_m = PLATES[p.get("plate", "graphite")]()
    pname, pcol = p.get("paddle", ("M_Switch_Rocker", (0.012, 0.012, 0.013)))
    rocker_m = common.pbr_material(pname, pcol, roughness=0.3, coat=0.4)
    lname, lcol, lstr = p.get("led", ("M_Switch_Locator", (1.0, 0.62, 0.28), 2.0))
    led_m = materials.emissive(lname, lcol, lstr)
    part = p.get("part", "paddle")

    pw, ph, pt = p["plate_size"]
    round_ = p.get("plate_shape") == "round"
    plate = common.mesh_object(f"{n}_Plate", plate_bmesh(pw, ph, pt, pw / 2 - 1e-4 if round_ else 0.004,
                                                         segments=8 if round_ else 3), col, plate_m, root)
    common.add_bevel(plate, 0.0012, segments=1)
    if p.get("plate_marks"):
        mname, mcol = p["marks"]
        marks_m = common.pbr_material(mname, mcol, roughness=0.5)
        common.mesh_object(f"{n}_Plate_Marks", _marks(bmesh.new(), p["plate_marks"], -pt - 0.0003), col,
                           marks_m, root, smooth=False)

    rw, rh, rt = p["rocker_size"]
    pivot = common.empty(f"{n}_Rocker", col, (0, -pt, 0))
    pivot.parent = root
    travel = p.get("travel") or {"paddle": {"axis": "x", "angle": 12}, "knob": {"axis": "z", "angle": 90},
                                 "button": {"axis": "-z", "distance": 0.003}}[part]
    pivot["interact"] = {
        "type": "switch", "signal": p["signal"], "state": bool(p["state"]),
        "prompt": p["prompt"], "promptActive": p["promptActive"],
        "range": 1.3, "duration": 0.3 if part == "knob" else 0.15,
        "travel": travel,
        "indicator": f"{n}_Locator",
    }
    if part == "paddle":
        # the rocker: a slightly crowned paddle standing proud of the plate
        # one mesh (one draw call: the rocker moves, so it isn't batched): the paddle, bevelled
        # here rather than by a modifier, plus its raised marks (a split line, the glyphs)
        y0 = -rt / 2 + 0.001
        bm = common.box_bmesh((rw, rt, rh))
        bmesh.ops.translate(bm, vec=(0, y0, 0), verts=bm.verts)
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.0015, segments=2, affect="EDGES", profile=0.5)
        _marks(bm, [(0, 0, rw * 0.86, 0.0010)] + list(p.get("glyphs", [])), y0 - rt / 2 - 0.0003)
        common.mesh_object(f"{n}_Rocker_Paddle", bm, col, rocker_m, pivot, smooth=False)
    elif part == "knob":
        # a gas-valve knob: a round skirt with a grip bar across it, turned a quarter when on
        r, d = rw / 2, rt
        bm = _disc(r, d, -d / 2)
        grip = common.box_bmesh((0.0065, 0.006, r * 1.9))
        bmesh.ops.translate(grip, vec=(0, -d - 0.0025, 0), verts=grip.verts)
        bmesh.ops.bevel(grip, geom=list(grip.edges), offset=0.0012, segments=2, affect="EDGES", profile=0.5)
        _append(bm, grip)
        common.mesh_object(f"{n}_Rocker_Knob", bm, col, rocker_m, pivot, smooth=False)
    else:
        # a round push button, in 3 mm while on
        r, d = rw / 2, rt
        bm = _disc(r, d, -d / 2, segments=28)
        _marks(bm, list(p.get("glyphs", [])), -d - 0.0003)
        common.mesh_object(f"{n}_Rocker_Button", bm, col, rocker_m, pivot, smooth=False)

    if p.get("ring"):
        # a lit ring round the button, on the plate (static: the button moves inside it)
        common.mesh_object(f"{n}_Locator", _disc(p["ring"], 0.0016, -pt - 0.0008, segments=28), col, led_m,
                           root, smooth=False)
    elif p.get("led_at"):
        lx, lz = p["led_at"]
        led = common.mesh_object(f"{n}_Locator", _disc(0.0019, 0.0008, 0.0, segments=10), col, led_m, root,
                                 smooth=False)
        led.location = (lx, -pt - 0.0004, lz)
    else:
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.0016, radius2=0.0016, depth=0.0008,
                              matrix=Matrix.Rotation(math.radians(90), 4, "X"))
        led = common.mesh_object(f"{n}_Locator", bm, col, led_m, pivot, smooth=False)
        led.location = (0, -0.0006, -rh / 2 - 0.0065)
    return pivot


def _append(a, b):
    """Copy bmesh b's geometry into a (b is freed)."""
    import bpy
    me = bpy.data.meshes.new("_ix_tmp")
    b.to_mesh(me)
    b.free()
    a.from_mesh(me)
    bpy.data.meshes.remove(me)
    return a


# ------------------------------------------------------------------ small-prop helpers

def lathe_bmesh(profile, segments=24, axis="z", sharp=None):
    """Spin a profile [(r, h), ...] (bottom to top, r = 0 closes a pole) around `axis`
    ("z" up, or "x" lying along x). `sharp`: profile indices whose ring is a hard edge."""
    bm = bmesh.new()
    rings = []
    for r, h in profile:
        if r < 1e-7:
            rings.append([bm.verts.new((0, 0, h))] * segments)
            continue
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / segments),
                                    r * math.sin(2 * math.pi * k / segments), h)) for k in range(segments)])
    for a, b in zip(rings, rings[1:]):
        for k in range(segments):
            j = (k + 1) % segments
            quad = []
            for v in (a[k], a[j], b[j], b[k]):
                if v not in quad:
                    quad.append(v)
            if len(quad) >= 3:
                bm.faces.new(quad)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for i in (sharp or []):
        ring = set(rings[i])
        for e in bm.edges:
            if e.verts[0] in ring and e.verts[1] in ring:
                e.smooth = False
    if axis == "x":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
    return bm


def pickup(item, name, prompt=None, **extra):
    d = {"type": "pickup", "item": item, "name": name, "prompt": prompt or f"Take {name.lower()}", "range": 1.4}
    d.update(extra)
    return d


def finish(root):
    return root, [o for o in root.children_recursive if o.type == "MESH"]


def home_screen_texture(w=512, h=320):
    """The smart-home UI (no words): a dark navy panel, a thermostat ring on the left, six
    room tiles with amber 'on' dots on the right. Shared by the tablet and the wall panel."""
    import numpy as np
    from lib import textures
    path = os.path.join(textures.TEX_DIR, "T_IX_HomeScreen_BaseColor.png")
    if os.path.exists(path):
        return path
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    lin = np.zeros((h, w, 3), np.float32)
    lin[:] = np.array([0.006, 0.010, 0.020])
    lin += (1 - y / h)[..., None] * np.array([0.010, 0.016, 0.030])
    # thermostat ring
    cx, cy, r = 0.24 * w, 0.52 * h, 0.30 * h
    d = np.hypot(x - cx, y - cy)
    ang = (np.degrees(np.arctan2(y - cy, x - cx)) + 360 + 90) % 360
    ring = np.clip(1 - np.abs(d - r) / 3.0, 0, 1)
    lin += ring[..., None] * np.array([0.05, 0.07, 0.10])
    arc = ring * (ang < 230)
    lin += arc[..., None] * np.array([0.55, 0.30, 0.08])
    dot = np.clip(1 - np.hypot(x - cx, y - cy) / (0.06 * h), 0, 1) ** 0.5
    lin += dot[..., None] * np.array([0.10, 0.12, 0.16])

    def rrect(x0, y0, x1, y1, rad):
        qx = np.maximum(np.maximum(x0 + rad - x, x - (x1 - rad)), 0)
        qy = np.maximum(np.maximum(y0 + rad - y, y - (y1 - rad)), 0)
        return np.clip(rad + 1 - np.hypot(qx, qy), 0, 1) * ((x > x0 - 1) & (x < x1 + 1) & (y > y0 - 1) & (y < y1 + 1))

    on = [1, 0, 1, 1, 0, 0]
    for i in range(6):
        c, rw = i % 3, i // 3
        x0, y0 = 0.48 * w + c * 0.17 * w, 0.18 * h + rw * 0.36 * h
        tile = rrect(x0, y0, x0 + 0.15 * w, y0 + 0.30 * h, 8)
        lin += tile[..., None] * np.array([0.020, 0.028, 0.045])
        bar = rrect(x0 + 10, y0 + 0.30 * h - 18, x0 + 0.15 * w - 30, y0 + 0.30 * h - 13, 2)
        lin += bar[..., None] * np.array([0.06, 0.07, 0.09])
        led = np.clip(1 - np.hypot(x - (x0 + 0.15 * w - 14), y - (y0 + 14)) / 5.0, 0, 1)
        lin += led[..., None] * (np.array([0.9, 0.45, 0.10]) if on[i] else np.array([0.06, 0.07, 0.09]))
    top = rrect(0.04 * w, 0.05 * h, 0.30 * w, 0.075 * h, 3)
    lin += top[..., None] * np.array([0.05, 0.06, 0.08])
    return textures._save("T_IX_HomeScreen_BaseColor", textures._to_srgb(np.clip(lin, 0, 1)))


def screen_material(name="M_IX_HomeScreen", strength=1.6):
    """Glass-black screen showing the home UI, emissive (the glow react dims it)."""
    from lib import textures
    m = common.pbr_material(name, (0.0, 0.0, 0.0), roughness=0.12)
    b = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    if not b.inputs["Emission Color"].is_linked:
        tex = m.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = textures.load(home_screen_texture())
        m.node_tree.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = strength
    return m


def quad_uv(ob):
    """UV 0..1 over the first face (a screen quad)."""
    uv = ob.data.uv_layers.get("UVMap") or ob.data.uv_layers.new(name="UVMap")
    for li, c in zip(ob.data.polygons[0].loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[li].uv = c


def screen_quad(name, col, mat, parent, w, h, y):
    """A w x h quad in the XZ plane at depth y, facing -Y, UV 0..1."""
    bm = bmesh.new()
    vs = [bm.verts.new(c) for c in ((-w / 2, y, -h / 2), (w / 2, y, -h / 2), (w / 2, y, h / 2), (-w / 2, y, h / 2))]
    bm.faces.new(vs)
    ob = common.mesh_object(name, bm, col, mat, parent, smooth=False)
    quad_uv(ob)
    return ob


# ------------------------------------------------------------------ fewer draw calls

def merge_by_material(parent, col, prefix):
    """Join the meshes directly under `parent` (in its space) into one mesh per material, named
    `<prefix>_<n>`: a moving part (a door, a pickup) isn't batched, so each mesh is a draw call.
    Modifiers (bevels) are applied first. Returns the new objects. (Locks, keys and caches.)"""
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    groups = {}
    for ob in [c for c in parent.children if c.type == "MESH" and not c.children]:
        mat = ob.data.materials[0] if ob.data.materials else None
        groups.setdefault(mat.name if mat else "", (mat, []))[1].append(ob)
    out = []
    for k, (name, (mat, obs)) in enumerate(sorted(groups.items())):
        if len(obs) < 2:
            continue
        bm = bmesh.new()
        for ob in obs:
            me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
            me.transform(ob.matrix_parent_inverse @ ob.matrix_basis)
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
        for ob in obs:
            bpy.data.objects.remove(ob)
        new = common.mesh_object(f"{prefix}_{k}", bm, col, mat, parent, smooth=False)   # (keeps each face's shading)
        out.append(new)
    return out


# ------------------------------------------------------------------ hiding spots

def pivot(root, col, name, at, parts):
    """Hang `parts` (objects, children of `root`) under a new empty at `at` (a door's hinge line),
    keeping their place. Not an interactable: the parts keep their static colliders (a shut door
    stays solid); a `hide` spot swings the empty (viewer/hiding.js)."""
    e = common.empty(name, col, at)
    e.parent = root
    for ob in parts:
        ob.parent = e
        ob.location = ob.location - e.location
    return e


def merge_parts(parent, names=None):
    """Apply the modifiers of `parent`'s mesh children and join them into one mesh per material.
    Moving parts are drawn unbatched, so a door hung from many parts would cost a draw call per
    part; merged it's one per material. `names`: material name -> suffix of the merged object
    (default: the material's last word). Returns the merged objects."""
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    kids = [o for o in parent.children if o.type == "MESH"]
    for ob in kids:
        if ob.modifiers:
            me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
            old = ob.data
            ob.modifiers.clear()
            ob.data = me
            if old.users == 0:
                bpy.data.meshes.remove(old)
    groups = {}
    for ob in kids:
        groups.setdefault(ob.data.materials[0].name if ob.data.materials else "", []).append(ob)
    out = []
    for i, (mname, obs) in enumerate(groups.items()):
        head = obs[0]
        if len(obs) > 1:
            with bpy.context.temp_override(active_object=head, object=head, selected_objects=obs,
                                           selected_editable_objects=obs):
                bpy.ops.object.join()
        tag = (names or {}).get(mname) or mname.split("_")[-1] or str(i)
        head.name = f"{parent.name}_{tag}"
        head.data.name = head.name
        out.append(head)
    return out


def closet_rail(root, col, n, x0, x1, y, z, coats, rail_mat, tris=420):
    """Inside a wardrobe: a hanging rail from x0 to x1 at (y, z) on two end brackets, and coats on
    hangers hung edge-on along it (cloth-simulated, mud_common.hanger_coat), pushed to the ends so
    a player can stand in the middle. `coats`: [(x, material name, rgb, length)]. The coats are
    _NoCollide (no colliders: the doors and carcass already close the wardrobe)."""
    import bpy
    import mud_common as mc
    import table_lamp
    rb = bmesh.new()
    table_lamp.cylinder_between(rb, (x0, y, z), (x1, y, z), 0.011, segs=12)
    for x in (x0, x1):
        table_lamp.cylinder_between(rb, (x, y, z + 0.035), (x, y, z), 0.016, segs=10)
    common.mesh_object(f"{n}_Rail_NoCollide", rb, col, rail_mat, root)
    hang = bmesh.new()
    by_mat = {}
    for k, (x, mname, rgb, length) in enumerate(coats):
        top = z + 0.03
        cb = mc.hanger_coat(length=length, width=0.2, depth=0.03, sleeve=0.55, tris=tris,
                            stiff=0.7 + 0.1 * (k % 3), pockets="flap" if k % 2 == 0 else None, seed=k % 3)
        bmesh.ops.transform(cb, matrix=Matrix.Translation((x, y, top)) @ Matrix.Rotation(math.pi / 2, 4, "Z"),
                            verts=cb.verts)
        me = bpy.data.meshes.new("tmp_coat")
        cb.to_mesh(me)
        cb.free()
        by_mat.setdefault(mname, (rgb, bmesh.new()))[1].from_mesh(me)
        bpy.data.meshes.remove(me)
        neck = (x, y, top - 0.12)
        table_lamp.cylinder_between(hang, (x, y + 0.02, z + 0.016), (x, y + 0.004, z + 0.028), 0.0025, segs=5)
        table_lamp.cylinder_between(hang, (x, y + 0.004, z + 0.028), neck, 0.0025, segs=5)
        for sy in (-1, 1):
            table_lamp.cylinder_between(hang, neck, (x, y + sy * 0.18, top - 0.12 - 0.06), 0.0035, segs=5)
    for mname, (rgb, bm) in by_mat.items():
        for f in bm.faces:
            f.material_index = 0
        ob = common.mesh_object(f"{n}_{mname[2:]}_NoCollide", bm, col, materials.fabric(mname, rgb, roughness=0.95), root)
        common.box_uv(ob, tile=0.25)
        ob.data.set_sharp_from_angle(angle=1.2)
    common.mesh_object(f"{n}_Hangers_NoCollide", hang, col, rail_mat, root)


def crack(door_w, gap=0.14):
    """The angle (deg) a door of width `door_w` is left ajar so its free edge stands `gap` m
    proud: the crack a hidden player peeks through is about the same on a wide or a narrow door."""
    return math.degrees(math.asin(min(1.0, gap / door_w)))


def hide_spot(root, col, n, eye, exit, prompt, leave, cover="closed", doors=(), facing=None, pitch=0.0,
              look=None, tag="Hide", **extra):
    """A hiding spot (interact type `hide`, viewer/hiding.js; prompts/interactivity.md): empties
    `<n>_<tag>` (the interactable), `<n>_<tag>Eye` (the camera inside) and `<n>_<tag>Exit[i]` (the
    feet outside; with a list of points the first clear one wins), in the asset's own Blender
    coords (the root at the origin). `doors`: [(pivot empty, angle, ajar)] swung about the vertical
    through the pivot (degrees, + = counter-clockwise seen from above): open to `angle` while the
    player climbs in or out, left at `ajar` (the crack to peek through) while inside.
    `facing`: the direction the view faces inside (default: from the eye toward the exit);
    `pitch`: its tilt (deg, + up); `look`: {yaw, pitch} how far it may turn (deg); `cover`:
    "closed" (shut in) or "open" (under a table, behind a sofa)."""
    spot = common.empty(f"{n}_{tag}", col, eye)
    spot.parent = root
    e = common.empty(f"{n}_{tag}Eye", col, eye)
    e.parent = root
    exits = list(exit) if isinstance(exit[0], (list, tuple)) else [exit]
    names = []
    for i, x in enumerate(exits):
        o = common.empty(f"{n}_{tag}Exit{i if i else ''}", col, x)
        o.parent = root
        names.append(o.name)
    d = {"type": "hide", "prompt": prompt, "promptActive": leave, "eye": e.name,
         "exit": names if len(names) > 1 else names[0], "cover": cover, "range": 1.4, "pitch": pitch}
    if doors:
        d["doors"] = [{"node": pv.name, "axis": common.to_gltf((0, 0, 1)), "angle": a, "ajar": j}
                      for pv, a, j in doors]
    if facing is None and doors:
        facing = (0, -1, 0)          # shut in: out through the doors (the asset's front), whichever exit is used
    if facing is not None:
        d["facing"] = common.to_gltf(facing)
    if look:
        d["look"] = look
    d.update(extra)
    spot["interact"] = d
    return spot
