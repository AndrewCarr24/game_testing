"""Bespoke smoked-oak wardrobe, built so that two side by side read as one fitted run.

Construction (front faces -Y, origin at the floor centre):
- end panels 45 mm thick run from the floor to the cornice; where two units meet, their
  panels close up into a 90 mm pilaster with a V-groove down the joint (the room places
  the units 1.85 m apart, exactly this width, so cornices, plinths and panels butt)
- a two-part cornice: a 45 mm oak slab projecting 20 mm, over a recessed brushed-bronze
  shadow band that runs the full width between the end panels
- a black toe-kick plinth recessed 50 mm between the end panels
- two inset doors with 3 mm reveals: a framed construction (75 mm stiles, a deeper bottom
  rail, the rails tenoned between the stiles so the joints show as hairlines) around a
  field of concave flutes recessed behind the frame; the pair is bookmatched
- bronze staple pulls on round roses at hand height on the meeting stiles
- smoked oak: a Poly Haven crown-cut oak veneer scan (oak_veneer_01, CC0), graded to a
  warm fumed-oak brown, with its normal map, under a satin lacquer coat
A hiding spot (prompts/interactivity.md `hide`): the carcass is hollow (a black lining at the
back and under the cornice, a bronze rail with coats hung at the ends), each door hangs from an
empty on its hinge line, and E at the wardrobe swings them open, the player steps in, and they
pull to with a crack at the meeting stiles to peek through."""
import importlib
import math
import os
import shutil
import sys
import urllib.request

import bmesh
import bpy
import numpy as np
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(materials)
sys.path.insert(0, HERE)
import ix_common  # noqa: E402  (hiding spot, prompts/interactivity.md)

importlib.reload(ix_common)

NAME = "Wardrobe"

P = dict(
    name=NAME,
    size=(1.85, 0.62, 2.4),    # width, depth (incl. pulls), height; width = the placements' spacing
    plinth_h=0.085,
    plinth_recess=0.05,        # plinth face sits this far behind the door faces
    plinth_side_inset=0.0,     # (the plinth runs between the end panels)
    top_t=0.045,               # cornice slab
    top_inset=0.02,            # cornice projection in front of the doors
    side_t=0.045,              # end panels
    bottom_t=0.02,
    back_t=0.012,
    door_t=0.024,
    reveal=0.003,
    top_gap=0.016,             # height of the recessed bronze shadow band under the cornice
    pull_r=0.0075,
    pull_stand=0.034,          # how far the bar stands off the door face
    pull_margin=0.11,          # (unused since the pulls became hand-height staples)
    pull_inset=0.0375,         # centre of the bar from the meeting edge
    bevel=0.0025,
    pull_len=0.56,
    pull_z=1.08,               # centre height of the pulls
    stile=0.075,
    rail_top=0.085,
    rail_bottom=0.125,
    flute_pitch=0.03,
    flute_depth=0.010,
    field_recess=0.007,        # flute ridges sit this far behind the frame face
    band_setback=0.010,        # bronze band behind the door faces
    oak_tile=1.2,              # metres one veneer image covers
    hide=True,                 # a hiding spot (hollow, doors on hinges)
    rail_z=1.98,
    # (x, material, linear rgb, length): pushed to the ends, the middle is the player's. The coat
    # closet's materials (same name and colour = one material at load, no extra draw calls)
    coats=[
        (-0.70, "M_Entry_Coat_Navy", (0.020, 0.028, 0.055), 1.05),
        (-0.60, "M_Entry_Coat_Camel", (0.31, 0.19, 0.085), 0.95),
        (0.58, "M_Entry_Coat_Charcoal", (0.035, 0.036, 0.04), 1.12),
        (0.69, "M_Entry_Coat_Oat", (0.30, 0.26, 0.20), 0.88),
    ],
)

PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
PH_CACHE = os.path.join(PROJECT, "build", "polyhaven")
PH_ID = "oak_veneer_01"
TEX_BASE = "T_Wardrobe_OakSmoked_BaseColor"
TEX_NORMAL = "T_Wardrobe_OakSmoked_Normal"
SMOKED = (0.150, 0.098, 0.060)  # mean linear colour: fumed oak, a warm mid-dark brown
CONTRAST = 1.15                 # figure contrast (fuming darkens the latewood more)


# --------------------------------------------------------------------------- textures

def _scan(kind):
    """Poly Haven 2k map of the veneer (cached in build/polyhaven/), or None offline."""
    path = os.path.join(PH_CACHE, f"{PH_ID}_{kind}_2k.jpg")
    if not os.path.exists(path):
        url = f"https://dl.polyhaven.org/file/ph-assets/Textures/jpg/2k/{PH_ID}/{PH_ID}_{kind}_2k.jpg"
        try:
            os.makedirs(PH_CACHE, exist_ok=True)
            req = urllib.request.Request(url, headers={"User-Agent": "game_testing-wardrobe/1.0 (CC0)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                open(path + ".tmp", "wb").write(r.read())
            shutil.move(path + ".tmp", path)
        except Exception as e:  # offline
            print(f"wardrobe: {PH_ID} {kind} unavailable ({e})")
            return None
    return path


def _read(path, n):
    img = bpy.data.images.load(path)
    img.scale(n, n)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(n, n, 4)[..., :3]   # as stored
    bpy.data.images.remove(img)
    return px


def _write(name, px):
    n = px.shape[0]
    path = os.path.join(textures.TEX_DIR, name + ".png")
    img = bpy.data.images.new("_" + name, n, n, alpha=False)
    img.pixels.foreach_set(np.concatenate([px, np.ones((n, n, 1), np.float32)], axis=2).ravel())
    img.filepath_raw = path + ".tmp.png"
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    os.replace(path + ".tmp.png", path)
    return path


def _textures(n=1024):
    """(base colour path, normal path or None); generated once (other agents run builds too)."""
    base = os.path.join(textures.TEX_DIR, TEX_BASE + ".png")
    nor = os.path.join(textures.TEX_DIR, TEX_NORMAL + ".png")
    if not os.path.exists(base):
        src = _scan("diff")
        if src is None:
            return None, None
        s = np.clip(_read(src, n), 0, 1)
        lin = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
        lum = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        r = lum / float(lum.mean())
        detail = np.clip(1 + CONTRAST * (r - 1), 0.25, 2.5)
        # latewood (dark) slightly cooler, earlywood flecks slightly warmer: the smoked look
        tint = np.stack([detail ** 1.05, detail, detail ** 0.92], axis=-1)
        out = np.array(SMOKED, np.float32)[None, None, :] * tint
        out = np.clip(out, 0, 1)
        srgb = np.where(out <= 0.0031308, out * 12.92, 1.055 * out ** (1 / 2.4) - 0.055)
        _write(TEX_BASE, srgb.astype(np.float32))
    if not os.path.exists(nor):
        src = _scan("nor_gl")
        if src is not None:
            _write(TEX_NORMAL, _read(src, n))
    return base, (nor if os.path.exists(nor) else None)


def wardrobe_oak():
    m = common.pbr_material("M_Wardrobe_OakSmoked", SMOKED, roughness=0.52)
    if not any(nd.type == "TEX_IMAGE" for nd in m.node_tree.nodes):
        base, nor = _textures()
        if base:
            common.set_base_color_map(m, textures.load(base))
        if nor:
            common.set_normal_map(m, textures.load(nor, non_color=True), 0.6)
    return m


# --------------------------------------------------------------------------- helpers

def grain_uv(ob, tile, along="z", mirror=False, shift=(0.0, 0.0)):
    """World-scale box projection with the grain (the scan's v) along `along` wherever that
    axis lies in the face plane, else along the longer of the face's axes. mirror flips u
    (a bookmatched leaf)."""
    me = ob.data
    dims = [max(v.co[a] for v in me.vertices) - min(v.co[a] for v in me.vertices) for a in range(3)]
    ga = "xyz".index(along)
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    loc = ob.location
    for poly in me.polygons:
        nrm = [abs(c) for c in poly.normal]
        na = nrm.index(max(nrm))
        a, b = [i for i in range(3) if i != na]      # b = grain axis
        if a == ga or (ga not in (a, b) and dims[a] > dims[b]):
            a, b = b, a
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            u = (co[a] + loc[a]) / tile
            uv.data[li].uv = ((-u if mirror else u) + shift[0], (co[b] + loc[b]) / tile + shift[1])


def flute_strip(x0, x1, z0, z1, y_ridge, pitch, depth, seg=5, land=0.12):
    """Concave flutes across [x0, x1] running z0..z1: narrow flat lands at y_ridge between
    round-bottomed grooves cut `depth` into the face (+Y = into the door).
    Returns a bmesh (a single sheet; its edges meet the frame's inner faces)."""
    bm = bmesh.new()
    k = max(1, round((x1 - x0) / pitch))
    w = (x1 - x0) / k
    prof = []                                       # (x, dy, flat_segment_follows)
    for i in range(k):
        xa = x0 + i * w
        prof.append((xa, 0.0, True))
        xl = xa + land * w
        for j in range(seg):
            t = j / seg
            prof.append((xl + t * (w - land * w), depth * math.sin(math.pi * t), False))
    prof.append((x1, 0.0, False))
    # two rows (ends on the rails' faces plus a middle row), so the baked vertex AO has
    # vertices out in the open field: with only end vertices tucked under the rails the whole
    # field came out evenly dark and the grooves didn't read
    zs = [z0, (z0 + z1) / 2, z1]
    rows = [[bm.verts.new((x, y_ridge + dy, z)) for x, dy, _ in prof] for z in zs]
    for lo, hi in zip(rows, rows[1:]):
        for i in range(len(prof) - 1):
            f = bm.faces.new((lo[i], lo[i + 1], hi[i + 1], hi[i]))
            f.smooth = not prof[i][2]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # face -Y (toward the room)
    if sum(f.normal.y for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return bm


def disc_bmesh(r, t, seg=16):
    """A cylinder along Y (a pull rose): r radius, t thick, centred at the origin."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=t)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                     matrix=Matrix.Rotation(math.pi / 2, 3, "X"))
    return bm


# --------------------------------------------------------------------------- build

def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    oak = wardrobe_oak()
    bronze = materials.bronze()
    # matte black for what is seen through the reveals and the toe kick (a metal there
    # reflected the bright ceiling and lit every reveal up as a white line)
    black = common.pbr_material("M_Felt_Black", (0.012, 0.012, 0.013), roughness=1.0)
    tile = p["oak_tile"]

    W, D, H = p["size"]
    y_wall = D / 2 - 0.005                                # 5 mm off the wall
    y_f = -D / 2 + p["pull_stand"] + 2 * p["pull_r"]     # door faces (the pulls take the rest of the depth)
    et, dt, g = p["side_t"], p["door_t"], p["reveal"]
    ph, tt = p["plinth_h"], p["top_t"]
    z_slab = H - tt                                        # underside of the cornice slab
    z_band = z_slab - p["top_gap"]                         # underside of the bronze band
    xi = W / 2 - et                                        # inner face of the end panels

    def box(name, lo, hi, mat, bevel=None, seg=2, along="z", mirror=False, shift=(0, 0)):
        size = [h - l for l, h in zip(lo, hi)]
        ob = common.mesh_object(f"{n}_{name}", common.box_bmesh(size), col, mat, root)
        ob.location = [(l + h) / 2 for l, h in zip(lo, hi)]
        bevel = p["bevel"] if bevel is None else bevel
        if bevel:
            common.add_bevel(ob, bevel, segments=seg)
        if mat is oak:
            grain_uv(ob, tile, along, mirror, shift)
        else:
            common.box_uv(ob, 0.5)
        return ob

    # --- cornice slab: full width, projecting, eased front edge, horizontal grain
    box("Cornice", (-W / 2, y_f - p["top_inset"], z_slab), (W / 2, y_wall, H), oak, bevel=0.004, seg=3,
        along="x", shift=(0.21, 0.37))
    # --- recessed bronze shadow band under it, between the end panels
    box("Band", (-xi, y_f + p["band_setback"], z_band), (xi, y_f + p["band_setback"] + 0.03, z_slab), bronze,
        bevel=0.0008, seg=1)

    # --- end panels: floor to cornice, flush with the door faces
    for side, sx in (("L", -1), ("R", 1)):
        x0, x1 = sorted((sx * W / 2, sx * xi))
        box(f"End_{side}", (x0, y_f, 0.0), (x1, y_wall, z_slab), oak, bevel=0.004,
            shift=(0.43 if sx > 0 else 0.0, 0.11 if sx > 0 else 0.0))

    # --- dark interior behind the reveals, recessed toe-kick plinth (a hiding spot is hollow: the
    #     lining sits at the back and under the cornice, the plinth's top is its floor)
    if p["hide"]:
        box("Interior", (-xi, y_wall - 0.018, ph), (xi, y_wall - 0.006, z_slab), black, bevel=0)
        box("InteriorTop", (-xi, y_f + dt + 0.004, z_band - 0.014), (xi, y_wall - 0.018, z_band - 0.002), black, bevel=0)
    else:
        box("Interior", (-xi, y_f + dt + 0.012, ph), (xi, y_f + dt + 0.018, z_slab), black, bevel=0)
    box("Plinth", (-xi, y_f + p["plinth_recess"], 0.0), (xi, y_wall - 0.03, ph), black, bevel=0.001, seg=1)

    # --- doors: framed, fluted fields, bookmatched pair
    door_w = (2 * xi - 3 * g) / 2
    z0, z1 = ph + 0.002, z_band - g
    st, rt, rb = p["stile"], p["rail_top"], p["rail_bottom"]
    yb = y_f + dt
    for side, sx in (("L", -1), ("R", 1)):
        xa, xb = sorted((sx * (g / 2), sx * (g / 2 + door_w)))       # door's x extent
        mir = sx > 0
        sh = (0.0, 0.0) if sx < 0 else (0.0, 0.05)
        # stiles full height, rails between them (hairline joints)
        box(f"Door_{side}_StileA", (xa, y_f, z0), (xa + st, yb, z1), oak, bevel=0.0035, mirror=mir, shift=sh)
        box(f"Door_{side}_StileB", (xb - st, y_f, z0), (xb, yb, z1), oak, bevel=0.0035, mirror=mir, shift=sh)
        box(f"Door_{side}_RailTop", (xa + st, y_f, z1 - rt), (xb - st, yb, z1), oak, bevel=0.0035,
            along="x", mirror=mir, shift=(0.3, 0.6))
        box(f"Door_{side}_RailBottom", (xa + st, y_f, z0), (xb - st, yb, z0 + rb), oak, bevel=0.0035,
            along="x", mirror=mir, shift=(0.1, 0.2))
        # fluted field, its edges on the frame's inner faces
        fb = flute_strip(xa + st, xb - st, z0 + rb, z1 - rt,
                         y_f + p["field_recess"], p["flute_pitch"], p["flute_depth"])
        me = bpy.data.meshes.new(f"{n}_Door_{side}_Field")
        fb.to_mesh(me)
        fb.free()
        me.materials.append(oak)
        fo = bpy.data.objects.new(me.name, me)
        common.link(fo, col, root)
        grain_uv(fo, tile, "z", mir, sh)

        # bronze staple pull on the meeting stile, on two roses
        meet = xa if sx > 0 else xb
        px = meet + sx * st / 2
        za, zb = p["pull_z"] - p["pull_len"] / 2, p["pull_z"] + p["pull_len"] / 2
        ya, yo = y_f + 0.002, y_f - p["pull_stand"] - p["pull_r"]
        pts = common.fillet_polyline([(px, ya, za), (px, yo, za), (px, yo, zb), (px, ya, zb)],
                                     0.016, segments=6, closed=False)
        pl = common.tube_object(f"{n}_Pull_{side}", pts, p["pull_r"], col, bronze, root, closed=False,
                                profile_res=3)
        common.box_uv(pl, 0.5)
        for k, z in (("A", za), ("B", zb)):
            ro = common.mesh_object(f"{n}_Pull_{side}_Rose{k}", disc_bmesh(0.0125, 0.004, seg=16), col, bronze, root)
            ro.location = (px, y_f - 0.002, z)
            common.add_bevel(ro, 0.0012, segments=1)
            common.box_uv(ro, 0.5)

    if p["hide"]:
        hiding(p, n, col, root, bronze, door_w, y_f, dt, y_wall, xi)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


def hiding(p, n, col, root, bronze, door_w, y_f, dt, y_wall, xi):
    """Hang each door (its frame, field, pull and roses) from an empty on its outer hinge line,
    merged into one mesh per material (moving parts aren't batched), and make the wardrobe a hiding
    spot: the eye between the coats a hand behind the doors, the exit in front."""
    W, D, H = p["size"]
    g = p["reveal"]
    doors = []
    for side, sx in (("L", -1), ("R", 1)):
        parts = [o for o in root.children if o.name.startswith((f"{n}_Door_{side}_", f"{n}_Pull_{side}"))]
        pv = ix_common.pivot(root, col, f"{n}_Door{side}", (sx * (g / 2 + door_w), y_f, 0.0), parts)
        ix_common.merge_parts(pv, {"M_Wardrobe_OakSmoked": "Leaf", "M_Bronze": "Pull"})
        doors.append((pv, sx * 100, sx * ix_common.crack(door_w)))   # R opens counter-clockwise; a crack at the meeting stiles
    yb = y_f + dt
    ix_common.closet_rail(root, col, n, -xi + 0.03, xi - 0.03, (yb + y_wall) / 2 + 0.02, p["rail_z"], p["coats"], bronze)
    ix_common.hide_spot(root, col, n, (0.0, yb + 0.15, 1.6), [(0.0, -D / 2 - 0.55, 0.0), (0.0, -D / 2 - 0.85, 0.0)],
                        "Hide in the wardrobe", "Leave the wardrobe", doors=doors, pitch=-4)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
