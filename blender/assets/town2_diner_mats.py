"""The diner's material palette (town2_diner*.py). Few materials on purpose: every part is merged
per material at export, so the material count is the building's draw-call count (budget <= 25).
Variation comes from the vertex tint (geo.TINT, COLOR_0 x base colour in three.js; multiplied in
for the bake through a Color Attribute node, removed again before export) and the textures.

Each material carries custom properties read by blender/town/diner/build.py:
  lm     True: lightmapped (the baked light on TEXCOORD_1), False: emissive / glass
  metal  True: baked with the glossy pass (what a metal shows is its reflections) and exported
         as a non-metal whose base colour is the metal's reflectance (the town runtime has no
         environment map: a metal would render black)
Textures are numpy-generated or Poly Haven scans (CC0, via town_textures.fetch), cached as PNG in
build/diner_tex/ and exported as WebP into assets/models/textures/T_Town2_Diner_*.
"""
import importlib
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import town_textures as tt  # noqa: E402

importlib.reload(tt)

PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE = os.path.join(PROJECT, "build", "diner_tex")
TINT = "Col"
_M = {}


# ------------------------------------------------------------------ textures

def _img(name, make, n, force=False):
    """A cached texture: build/diner_tex/<name>.png, made by make(n) -> linear rgb [n, n, 3] (row 0 = bottom)."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name + ".png")
    if force or not os.path.exists(path):
        lin = make(n)
        tt.save_png(path, np.clip(lin, 0, 1).astype(np.float32))
    img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.load(path)
        img.name = name
    img.colorspace_settings.name = "sRGB"
    return img


def _terrazzo(n):
    """Warm cream terrazzo, 1 m tile: a fine cement matrix with marble chips (white, grey, rust,
    black) of mixed size, ground flat and a little worn."""
    rng = np.random.default_rng(71)
    mat = np.ones((n, n, 3), np.float32) * np.array([0.56, 0.50, 0.41], np.float32)
    mat *= (1 + 0.05 * tt.noise(n, 1, 1, 1.4, rng))[..., None]
    out = mat.copy()
    cols = np.array([[0.80, 0.78, 0.72], [0.66, 0.64, 0.60], [0.36, 0.34, 0.32], [0.05, 0.05, 0.05],
                     [0.42, 0.16, 0.08], [0.72, 0.60, 0.44], [0.90, 0.88, 0.84]], np.float32)
    wts = np.array([0.24, 0.2, 0.14, 0.08, 0.12, 0.12, 0.10])
    yy, xx = np.mgrid[0:n, 0:n]
    for size, count in ((0.012, 2600), (0.006, 9000), (0.022, 520)):
        r = size * n
        for _ in range(count):
            cx, cy = rng.random() * n, rng.random() * n
            rr = r * (0.5 + rng.random())
            c = cols[rng.choice(len(cols), p=wts / wts.sum())] * (0.88 + 0.24 * rng.random())
            x0, x1 = int(cx - rr - 1), int(cx + rr + 2)
            y0, y1 = int(cy - rr - 1), int(cy + rr + 2)
            ys = np.arange(y0, y1) % n
            xs = np.arange(x0, x1) % n
            dy = (np.arange(y0, y1) - cy)[:, None]
            dx = (np.arange(x0, x1) - cx)[None, :]
            a = rng.random() * math.pi
            u = dx * math.cos(a) + dy * math.sin(a)
            v = -dx * math.sin(a) + dy * math.cos(a)
            asp = 0.55 + 0.45 * rng.random()
            d = np.sqrt(u * u + (v / asp) ** 2) / rr + 0.18 * np.sin(5 * np.arctan2(v, u) + a)
            m = d < 1.0
            if not m.any():
                continue
            sub = out[np.ix_(ys, xs)]
            sub[m] = c
            out[np.ix_(ys, xs)] = sub
    wear = 1 + 0.04 * tt.noise(n, 1, 1, 1.0, np.random.default_rng(5))
    return out * wear[..., None]


def _stone(n):
    """Fieldstone veneer (the plinth): a Poly Haven stone wall scan, warmed to the town's stone."""
    try:
        px = tt.scan_tile("stone_wall", 2.0, n)
        return tt.matched(px, (0.30, 0.27, 0.23), 0.15)
    except Exception as e:  # offline
        print("stone scan:", e)
        rng = np.random.default_rng(3)
        return np.ones((n, n, 3), np.float32) * 0.28 * (1 + 0.3 * tt.noise(n, 1, 1, 1.2, rng))[..., None]


def _asphalt(n):
    try:
        px = tt.scan_tile("asphalt_02", 4.0, n)
        return tt.matched(px, (0.085, 0.085, 0.083), 0.6)
    except Exception as e:
        print("asphalt scan:", e)
        rng = np.random.default_rng(4)
        return np.ones((n, n, 3), np.float32) * 0.08 * (1 + 0.25 * tt.noise(n, 1, 1, 0.9, rng))[..., None]


def _concrete(n):
    try:
        px = tt.scan_tile("concrete_floor_02", 2.0, n)
        return tt.matched(px, (0.36, 0.35, 0.33), 0.5)
    except Exception as e:
        print("concrete scan:", e)
        rng = np.random.default_rng(6)
        return np.ones((n, n, 3), np.float32) * 0.35 * (1 + 0.15 * tt.noise(n, 1, 1, 1.0, rng))[..., None]


def _brushed(n):
    """Brushed stainless grain (tile 0.5 m, grain along u), around 1: a tint multiplier."""
    rng = np.random.default_rng(9)
    g = 0.035 * tt.noise(n, 0.02, 1.0, 1.0, rng) + 0.02 * tt.noise(n, 0.1, 1.0, 1.3, rng)
    return np.repeat((0.86 + g)[..., None], 3, axis=2)


def _wood(n):
    """Oiled white oak (the booth tables' edge, the bench, the annex's soffit): grain along u."""
    try:
        px = tt.scan_tile("oak_veneer_01", 1.0, n)
        return tt.matched(px, (0.32, 0.21, 0.12), 0.1)
    except Exception as e:
        print("wood scan:", e)
        rng = np.random.default_rng(8)
        g = tt.noise(n, 0.05, 1.0, 1.2, rng)
        return np.ones((n, n, 3), np.float32) * np.array([0.32, 0.21, 0.12]) * (1 + 0.2 * g)[..., None]


def _checker(n):
    """Vestibule / restroom floor: 30 cm black and white vinyl-composition tiles (tile = 0.6 m:
    2 x 2), a little wax and wear, thin grout lines."""
    u, v = tt.grid(n)
    q = ((np.floor(u * 2) + np.floor(v * 2)) % 2).astype(np.float32)
    white, black = np.array([0.74, 0.72, 0.66]), np.array([0.025, 0.025, 0.027])
    rng = np.random.default_rng(12)
    out = q[..., None] * white + (1 - q[..., None]) * black
    out *= (1 + 0.06 * tt.noise(n, 1, 1, 1.2, rng))[..., None]
    fu, fv = (u * 2) % 1, (v * 2) % 1
    seam = np.minimum(np.minimum(fu, 1 - fu), np.minimum(fv, 1 - fv)) < 0.006
    out[seam] *= 0.55
    return out


def _laminate(n):
    """The counter and table tops: 1950s "cracked ice" laminate, pale grey-white with silver-grey
    shards (tile 0.6 m)."""
    rng = np.random.default_rng(31)
    u, v = tt.grid(n)
    base = np.ones((n, n, 3), np.float32) * np.array([0.66, 0.66, 0.64], np.float32)
    acc = np.zeros((n, n), np.float32)
    # Voronoi-ish shards: the distance to the nearest of a set of periodic seeds, edges darkened
    pts = rng.random((90, 2))
    d1 = np.full((n, n), 9.0, np.float32)
    d2 = np.full((n, n), 9.0, np.float32)
    idx = np.zeros((n, n), np.int32)
    for i, (px, py) in enumerate(pts):
        dx = np.abs(u - px)
        dx = np.minimum(dx, 1 - dx)
        dy = np.abs(v - py)
        dy = np.minimum(dy, 1 - dy)
        d = np.sqrt(dx * dx + dy * dy)
        closer = d < d1
        d2 = np.where(closer, d1, np.minimum(d2, d))
        idx = np.where(closer, i, idx)
        d1 = np.where(closer, d, d1)
    edge = 1 - tt.smooth(d2 - d1, 0.0, 0.006)
    shade = rng.random(len(pts)).astype(np.float32)[idx]
    acc = 0.84 + 0.16 * shade - 0.22 * edge
    out = base * acc[..., None]
    out += 0.03 * tt.noise(n, 1, 1, 1.0, rng)[..., None]
    return out


def _quarry(n):
    """Kitchen floor: 6 in (15 cm) red quarry tile, dark grout (tile 0.6 m = 4 x 4)."""
    rng = np.random.default_rng(14)
    u, v = tt.grid(n)
    k = 4
    cell = (np.floor(u * k) * 7 + np.floor(v * k) * 13) % 11
    base = np.array([0.30, 0.085, 0.045], np.float32)
    out = np.ones((n, n, 3), np.float32) * base * (0.85 + 0.03 * cell)[..., None]
    out *= (1 + 0.12 * tt.noise(n, 1, 1, 1.3, rng))[..., None]
    fu, fv = (u * k) % 1, (v * k) % 1
    g = np.minimum(np.minimum(fu, 1 - fu), np.minimum(fv, 1 - fv)) < 0.035
    out[g] = np.array([0.06, 0.055, 0.05])
    return out


def _subway(n):
    """Kitchen and restroom walls: white 3 x 6 in glazed subway tile, running bond (tile 0.6 m)."""
    rng = np.random.default_rng(15)
    u, v = tt.grid(n)
    rows = 8                     # 7.5 cm courses
    cols = 4                     # 15 cm long
    r = np.floor(v * rows)
    uu = (u * cols + 0.5 * (r % 2)) % 1
    fv = (v * rows) % 1
    out = np.ones((n, n, 3), np.float32) * np.array([0.78, 0.78, 0.75], np.float32)
    out *= (1 + 0.025 * tt.noise(n, 1, 1, 1.4, rng))[..., None]
    g = (np.minimum(uu, 1 - uu) < 0.015) | (np.minimum(fv, 1 - fv) < 0.03)
    out[g] = np.array([0.52, 0.51, 0.48])
    return out


def _decals(n):
    import town2_diner_decals as D
    importlib.reload(D)
    return D.make(n)


TEXTURES = {
    "T_Town2_Diner_Decals": (_decals, 512),
    "T_Town2_Diner_Checker": (_checker, 256),
    "T_Town2_Diner_Laminate": (_laminate, 512),
    "T_Town2_Diner_Quarry": (_quarry, 256),
    "T_Town2_Diner_Subway": (_subway, 256),
    "T_Town2_Diner_Terrazzo": (_terrazzo, 512),
    "T_Town2_Diner_Stone": (_stone, 256),
    "T_Town2_Diner_Asphalt": (_asphalt, 256),
    "T_Town2_Diner_Concrete": (_concrete, 256),
    "T_Town2_Diner_Brushed": (_brushed, 256),
    "T_Town2_Diner_Wood": (_wood, 256),
}


def texture(name, force=False):
    make, n = TEXTURES[name]
    return _img(name, make, n, force)


# ------------------------------------------------------------------ materials

def _bsdf(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def material(name, color=(0.8, 0.8, 0.8), roughness=0.6, metallic=0.0, tex=None, lm=True, metal=False,
             emission=None, strength=0.0, alpha=None, tint=True):
    """A palette material (created once per build)."""
    if name in _M and _M[name].name in bpy.data.materials:
        return _M[name]
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    b = _bsdf(m)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    nt = m.node_tree
    src = None
    if tex:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = texture(tex)
        t.location = (-700, 300)
        src = t.outputs["Color"]
    if tint:
        # vertex tint x (texture or colour): for the bake only (build.py removes it for export)
        ca = nt.nodes.new("ShaderNodeVertexColor")
        ca.layer_name = TINT
        ca.name = "DinerTint"
        ca.location = (-700, 0)
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.name = "DinerTintMix"
        mix.inputs["Factor"].default_value = 1.0
        mix.location = (-400, 150)
        if src is not None:
            nt.links.new(src, mix.inputs["A"])
        else:
            mix.inputs["A"].default_value = (*color, 1)
        nt.links.new(ca.outputs["Color"], mix.inputs["B"])
        nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    elif src is not None:
        nt.links.new(src, b.inputs["Base Color"])
    if emission is not None:
        b.inputs["Emission Color"].default_value = (*emission, 1)
        b.inputs["Emission Strength"].default_value = strength
    if alpha is not None:
        b.inputs["Alpha"].default_value = alpha
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "BLENDED"
        else:
            m.blend_method = "BLEND"
    m.use_backface_culling = True       # (single-sided in glTF; glass turns it off)
    m["lm"] = bool(lm)
    m["metal"] = bool(metal)
    m["tex"] = tex or ""
    m.diffuse_color = (*color, 1)
    _M[name] = m
    return m


def palette():
    """The diner's materials by role."""
    _M.clear()
    M = {}
    # painted / plastic / vinyl / laminate / enamel / rubber: white x tint
    M["paint"] = material("M_Town2_Diner_Paint", (1, 1, 1), 0.55)
    # stainless (fluted skin, back-bar, trim, kitchen): brushed grain x tint; glossy-baked
    M["steel"] = material("M_Town2_Diner_Steel", (0.62, 0.62, 0.64), 0.28, 1.0, tex="T_Town2_Diner_Brushed", metal=True)
    # polished chrome (stools, rails, napkin dispensers, the jukebox's trim)
    M["chrome"] = material("M_Town2_Diner_Chrome", (0.85, 0.85, 0.87), 0.08, 1.0, metal=True)
    M["terrazzo"] = material("M_Town2_Diner_Terrazzo", (1, 1, 1), 0.35, tex="T_Town2_Diner_Terrazzo")
    M["stone"] = material("M_Town2_Diner_Stone", (1, 1, 1), 0.9, tex="T_Town2_Diner_Stone")
    M["asphalt"] = material("M_Town2_Diner_Asphalt", (1, 1, 1), 0.9, tex="T_Town2_Diner_Asphalt")
    M["concrete"] = material("M_Town2_Diner_Concrete", (1, 1, 1), 0.85, tex="T_Town2_Diner_Concrete")
    M["checker"] = material("M_Town2_Diner_Checker", (1, 1, 1), 0.3, tex="T_Town2_Diner_Checker")
    M["laminate"] = material("M_Town2_Diner_Laminate", (1, 1, 1), 0.3, tex="T_Town2_Diner_Laminate")
    M["quarry"] = material("M_Town2_Diner_Quarry", (1, 1, 1), 0.6, tex="T_Town2_Diner_Quarry")
    M["subway"] = material("M_Town2_Diner_Subway", (1, 1, 1), 0.15, tex="T_Town2_Diner_Subway")
    M["decal"] = material("M_Town2_Diner_Decal", (1, 1, 1), 0.5, tex="T_Town2_Diner_Decals")
    M["wood"] = material("M_Town2_Diner_Wood", (1, 1, 1), 0.5, tex="T_Town2_Diner_Wood")
    # glass: alpha-blended, a faint sky sheen as emission (no environment in the runtime)
    M["glass"] = material("M_Town2_Diner_Glass", (0.6, 0.66, 0.68), 0.05, alpha=0.22, lm=False, tint=False,
                          emission=(0.55, 0.62, 0.70), strength=0.06)
    M["glass"].use_backface_culling = False
    M["glass"]["bake_hide"] = True
    # light: neon tubes, lamp globes, the sign's faces (emissive, unlit)
    M["neon_red"] = material("M_Town2_Diner_NeonRed", (1.0, 0.12, 0.08), 0.4, lm=False, tint=False,
                             emission=(1.0, 0.10, 0.06), strength=12.0)
    M["neon_blue"] = material("M_Town2_Diner_NeonBlue", (0.3, 0.7, 1.0), 0.4, lm=False, tint=False,
                              emission=(0.25, 0.75, 1.0), strength=10.0)
    M["globe"] = material("M_Town2_Diner_Globe", (1.0, 0.92, 0.80), 0.4, lm=False, tint=False,
                          emission=(1.0, 0.86, 0.66), strength=6.0)
    M["globe_cool"] = material("M_Town2_Diner_LampCool", (1.0, 0.97, 0.92), 0.4, lm=False, tint=False,
                               emission=(1.0, 0.96, 0.90), strength=5.0)
    # the far version's one material: black, its look baked into an emission map (build.py)
    M["far"] = material("M_Town2_Diner_Far", (0.0, 0.0, 0.0), 0.9, lm=False, tint=False)
    M["far"]["far"] = True
    M["steel"]["gmix"] = 0.35        # brushed: mostly its diffuse light, a sheen of reflection
    M["chrome"]["gmix"] = 0.75       # polished: mostly reflection
    M["globe"]["bake_hide"] = True
    M["globe_cool"]["bake_hide"] = True
    return M
