"""Den media wall, 8.4 m wide: a smoked-oak slat feature wall with a 3.1 m glowing
screen (emissive cinematic still), a floating smoked-oak credenza with bronze finger
pulls and a warm under-glow, two slim floor-standing speakers, and moss-green
acoustic-fabric panels either side. Back face at +Y (rotate 180 against a south wall).

Units are metres. Origin: floor centre of the footprint, back at y = +depth/2.
"""
import importlib
import math
import os
import sys

import bmesh
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(materials)
importlib.reload(textures)

NAME = "LivingMediaWall"

P = dict(
    name=NAME,
    width=8.4,
    depth=0.52,
    slat_zone=4.9,          # width of the oak slat wall behind the screen
    wall_h=3.75,
    screen=(3.1, 1.74),     # visible picture size
    screen_z=0.95,          # bottom of the screen above the floor
    credenza=(4.9, 0.46, 0.40),
    credenza_z=0.14,
    panel_w=1.55,
    panel_h=2.9,
    glow=1.1,
)


def screen_texture(w=1024, h=576, seed=7):
    path = os.path.join(textures.TEX_DIR, "T_Living_Screen_BaseColor.png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(seed)
    y = np.linspace(0, 1, h)[:, None] * np.ones((1, w))      # 0 top .. 1 bottom
    x = np.linspace(0, 1, w)[None, :] * np.ones((h, 1))
    horizon = 0.62
    sky_top = np.array([0.020, 0.075, 0.150])
    sky_low = np.array([0.95, 0.40, 0.10])
    k = np.clip(y / horizon, 0, 1) ** 2.2
    lin = sky_top + (sky_low - sky_top) * k[..., None]
    sun = np.exp(-(((x - 0.62) * 2.6) ** 2 + ((y - 0.52) * 3.0) ** 2) * 6.0)
    lin += sun[..., None] * np.array([1.0, 0.75, 0.35])
    # mountain ridge silhouette (periodic fractal noise along x)
    n = np.zeros(w)
    for o, a in ((2, 0.12), (5, 0.06), (13, 0.03), (31, 0.012)):
        n += a * np.sin(2 * np.pi * (np.arange(w) / w * o + rng.random()))
    ridge = horizon + 0.02 + n
    ground = y > ridge[None, :]
    lin = np.where(ground[..., None], np.array([0.012, 0.010, 0.012]) + 0.05 * np.clip(1 - (y - ridge[None, :]) * 6, 0, 1)[..., None] * np.array([0.8, 0.3, 0.1]), lin)
    return textures._save("T_Living_Screen_BaseColor", textures._to_srgb(np.clip(lin, 0, 1)))


def screen_material(strength):
    m = common.pbr_material("M_Living_Screen", (0, 0, 0), roughness=0.25)
    bsdf = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    img = textures.load(screen_texture())
    tex = m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = strength
    return m


def box(col, root, name, mat, size, loc, bevel=0.0, uv=0.5):
    ob = common.mesh_object(name, common.box_bmesh(size), col, mat, root, smooth=False)
    ob.location = loc
    if bevel:
        common.add_bevel(ob, bevel, segments=2)
    common.box_uv(ob, uv)
    return ob


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    oak = materials.smoked_oak()
    black = materials.black_metal()
    bronze = materials.bronze()
    felt = common.pbr_material("M_Felt_Black", (0.012, 0.012, 0.013), roughness=1.0)
    moss = materials.fabric("M_Fabric_Moss", (0.030, 0.050, 0.035))

    W, D = p["width"], p["depth"]
    yb = D / 2

    # --- oak slat wall (backing + slats)
    sz = p["slat_zone"]
    wh = p["wall_h"]
    box(col, root, f"{n}_SlatBacking", felt, (sz, 0.02, wh), (0, yb - 0.01, wh / 2), uv=1.0)
    slat_w, pitch, slat_d = 0.045, 0.075, 0.045
    count = int(sz / pitch)
    bm = bmesh.new()
    for i in range(count):
        x = -sz / 2 + pitch * (i + 0.5) + (sz - count * pitch) / 2
        b = common.box_bmesh((slat_w, slat_d, wh))
        for v in b.verts:
            v.co.x += x
            v.co.y += yb - 0.02 - slat_d / 2
            v.co.z += wh / 2
        mesh_tmp = bpy_mesh = None
        # merge into one bmesh
        vmap = {}
        for v in b.verts:
            vmap[v] = bm.verts.new(v.co)
        for f in b.faces:
            bm.faces.new([vmap[v] for v in f.verts])
        b.free()
    slats = common.mesh_object(f"{n}_Slats", bm, col, oak, root, smooth=False)
    common.box_uv(slats, 0.5)

    # --- screen: black bezel box + emissive picture
    sw, sh = p["screen"]
    sz0 = p["screen_z"]
    sy = yb - 0.02 - slat_d - 0.01
    bez = 0.012
    box(col, root, f"{n}_TVBody", black, (sw + 2 * bez, 0.045, sh + 2 * bez), (0, sy - 0.0225 + 0.0, sz0 + sh / 2), 0.004)
    fy = sy - 0.045 - 0.0008
    ob_bm = bmesh.new()
    vs = [ob_bm.verts.new(c) for c in ((-sw / 2, fy, sz0), (sw / 2, fy, sz0), (sw / 2, fy, sz0 + sh), (-sw / 2, fy, sz0 + sh))]
    ob_bm.faces.new(vs)
    pic = common.mesh_object(f"{n}_Screen", ob_bm, col, screen_material(p["glow"]), root, smooth=False)
    uvl = pic.data.uv_layers.new(name="UVMap")
    for li, uvc in zip(pic.data.polygons[0].loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))):
        uvl.data[li].uv = uvc

    # --- credenza
    cw, cd, ch = p["credenza"]
    cz = p["credenza_z"]
    cy = yb - cd / 2
    box(col, root, f"{n}_Credenza", oak, (cw, cd, ch), (0, cy, cz + ch / 2), 0.006)
    # door fronts: shadow gaps cut as thin black reveal strips, bronze finger pulls on 4 doors
    doors = 4
    dw = cw / doors
    for i in range(1, doors):
        box(col, root, f"{n}_Reveal{i}", felt, (0.006, 0.004, ch - 0.02), (-cw / 2 + dw * i, cy - cd / 2 - 0.0005, cz + ch / 2), uv=1.0)
    for i in range(doors):
        x = -cw / 2 + dw * (i + 0.5)
        box(col, root, f"{n}_Pull{i}", bronze, (0.30, 0.012, 0.012), (x, cy - cd / 2 - 0.006, cz + ch - 0.045), 0.003)
    # under-glow strip and a dark plinth recess
    glow = materials.emissive("M_Living_WarmGlow", (1.0, 0.62, 0.30), 2.2)
    box(col, root, f"{n}_UnderGlow", glow, (cw - 0.1, 0.03, 0.012), (0, cy - cd / 2 + 0.07, cz - 0.006), uv=1.0)
    box(col, root, f"{n}_Plinth", felt, (cw - 0.3, cd - 0.12, 0.02), (0, cy, 0.012 + 0.0), uv=1.0)
    # wall-hung bronze reveal line above the picture and a slim cap on the slat wall
    box(col, root, f"{n}_SlatCap", bronze, (sz, 0.06, 0.012), (0, yb - 0.04, wh + 0.006), 0.002)

    # --- speakers (slim floor columns)
    for s, sx in (("L", -1), ("R", 1)):
        x = sx * (cw / 2 + 0.45)
        box(col, root, f"{n}_Speaker{s}", black, (0.26, 0.30, 1.15), (x, yb - 0.18, 0.575), 0.012)
        box(col, root, f"{n}_Grille{s}", felt, (0.22, 0.012, 1.05), (x, yb - 0.18 - 0.152, 0.575), uv=1.0)
        for k, zz in enumerate((0.95, 0.60)):
            r = common.mesh_object(f"{n}_Driver{s}{k}", _ring(0.065 - 0.012 * k, 0.012), col, bronze, root)
            r.location = (x, yb - 0.18 - 0.16, zz)
            r.rotation_euler = (math.pi / 2, 0, 0)
            common.box_uv(r, 0.5)

    # --- acoustic fabric panels either side of the slat wall (2 per side, with gaps)
    pw, ph = p["panel_w"], p["panel_h"]
    for s, sx in (("L", -1), ("R", 1)):
        for k in range(2):
            x0 = sz / 2 + 0.03 + k * (pw / 2 + 0.03)
            w = pw / 2 - 0.02
            ob = common.mesh_object(
                f"{n}_Panel{s}{k}", common.cushion_bmesh((w, 0.06, ph), cuts=3, edge=0.02, crown={"-y": 0.006}),
                col, moss, root)
            ob.location = (sx * (x0 + w / 2), yb - 0.04, 0.12 + ph / 2)
            common.add_subsurf(ob)
            common.box_uv(ob, 0.25)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


def _ring(r, t, segs=20):
    bm = bmesh.new()
    rows = []
    for rr, z in ((r, 0), (r, t), (r * 0.6, t), (r * 0.6, 0)):
        rows.append([bm.verts.new((rr * math.cos(2 * math.pi * i / segs), rr * math.sin(2 * math.pi * i / segs), z))
                     for i in range(segs)])
    for a in range(4):
        b = (a + 1) % 4
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((rows[a][i], rows[a][j], rows[b][j], rows[b][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
