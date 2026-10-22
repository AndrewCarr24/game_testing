"""Procedural game-ready vegetation (wilderness spike): branch-growth skeletons with real taper,
bark tubes with world-scale UVs, leaf/twig cards cut from Poly Haven (CC0) scan atlases, and
per species LOD0/LOD1/LOD2 regenerated from the same skeleton (not decimated) plus a
hemi-octahedral impostor atlas (albedo + normal) baked in Blender.

  Blender -b --factory-startup --python blender/wilderness/trees.py -- [--species fir,ash,shrub,fern]
          [--no-impostor] [--no-preview] [--seed N]

Writes build/wilderness/veg/<species>.gltf (+ shared textures/), <species>_impostor_{albedo,normal}.webp,
veg.json (manifest: LOD triangle counts, textures, impostor layout), previews/<species>.png.

Prepared textures are cached in build/wilderness/veg/src_prep/: after changing a species' leaf
`tint` or source maps, delete its T_Veg_<Species>_Leaf*.png so it is regenerated.

Per-vertex data every LOD carries:
  COLOR_0 ("AO")   crown ambient occlusion: sky visibility through a leaf-density voxel grid
                   (Beer-Lambert), not vertex_ao.py's 0.3 m Cycles bake (that flattens alpha and
                   sees every card corner as buried). Same grid for every LOD, so LODs shade alike.
  _WIND (vec3)     x = branch bend weight (0 at the trunk -> 1 at the outermost tips, by path length
                   from the trunk), y = leaf flutter (0 at a card's base -> 1 at its tip, 0 on bark),
                   z = phase (0..1, per primary branch). Trunk sway comes from height in the shader.
  NORMAL           wood: analytic tube normals; cards: blended toward the crown's normal ("spherical
                   normals"), so a crown shades as one volume instead of a confetti of flat cards.
                   Cards are single double-sided quads: the engine must not flip back-face normals.
"""
import argparse
import copy
import hashlib
import json
import math
import os
import random
import sys
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER_DIR = os.path.abspath(os.path.join(HERE, ".."))
PROJECT = os.path.abspath(os.path.join(BLENDER_DIR, ".."))
sys.path.insert(0, BLENDER_DIR)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(BLENDER_DIR, "tools"))

OUT = os.path.join(PROJECT, "build", "wilderness", "veg")
PREP = os.path.join(OUT, "src_prep")
PREVIEWS = os.path.join(OUT, "previews")
UP = Vector((0, 0, 1))

# ---------------------------------------------------------------------------------------------
# Card regions in the Poly Haven atlases, in the 8x8 grid of the 1k maps (x right, y down):
# (x0, y0, x1, y1, side the stem base is on: b(ottom) / l(eft) / r(ight), base position along that side)
FIR_SPRAYS = [(2.45, 3.25, 5.15, 6.35, "b", 3.88), (5.1, 3.6, 7.65, 6.7, "b", 6.32),
              (1.5, 0.3, 3.45, 2.5, "b", 2.45), (5.25, 0.3, 7.5, 3.0, "b", 6.45),
              (3.95, 2.05, 5.0, 3.2, "b", 4.3)]
JACARANDA_FRONDS = [(1.25, 0.2, 8.0, 3.75, "l", 1.8), (0.0, 2.6, 3.45, 5.6, "l", 3.95),
                    (2.0, 4.7, 8.0, 7.95, "r", 6.45)]
WILLOW_LEAVES = [(1.4, 2.3, 2.45, 7.0, "b", 2.1), (2.6, 0.7, 3.25, 3.45, "b", 2.85),
                 (4.15, 2.55, 5.0, 6.65, "b", 4.55), (5.45, 3.25, 6.4, 6.55, "b", 5.85),
                 (6.65, 2.9, 7.55, 6.5, "b", 7.35), (5.7, 0.3, 6.3, 3.3, "b", 6.1)]
FERN_FRONDS = [(0.7, 0.85, 1.95, 7.62, "b", 1.3), (2.5, 0.2, 3.7, 6.1, "b", 3.1),
               (4.05, 0.2, 5.3, 3.98, "b", 4.85), (4.1, 4.05, 5.05, 7.78, "b", 4.6),
               (5.75, 0.85, 6.8, 7.18, "b", 6.35)]

SPECIES = {
    # Norway-spruce-like conifer: whorled, drooping-then-upturned branches, twig-spray cards
    "fir": dict(kind="conifer", title="Conifer (spruce/fir)", height=15.0, trunk_r=0.24, flare=0.55,
                crown_base=1.6, whorl_gap=0.62, branch_len=3.6, cone=0.95,
                elev_bottom=-12.0, elev_top=38.0, droop=28.0, upturn=22.0,
                twig_gap=0.27, twig_len=1.1, card_len=(0.75, 1.2), leader=1.8,
                leaf=dict(src="fir_tree_01", diff="twig_diff", alpha="twig_alpha", nor="twig_nor_gl",
                          rects=FIR_SPRAYS, tint=(0.68, 0.86, 0.6)),
                bark=dict(src="pine_bark", diff="Diffuse", nor="nor_gl", tile=(0.9, 1.4)),
                lods=[dict(trunk=9, branch=4, thin=3, seg=2, min_len=0.7, keep=1.0, csegs=2, max_level=1,
                           branch_cards=True),
                      dict(trunk=6, branch=3, thin=0, seg=3, min_len=1.4, keep=0.3, csegs=1, max_level=1,
                           branch_cards=True),
                      dict(trunk=5, branch=0, thin=0, seg=6, min_len=99, keep=0.0, csegs=1, max_level=0,
                           branch_cards=True)],
                lod_dist=[0, 22, 50, 95]),
    # ash/jacaranda-like broadleaf: decurrent crown in an ellipsoid envelope, compound-frond cards
    "ash": dict(kind="broadleaf", title="Broadleaf (ash-like)", height=13.0, crown_base=3.2,
                envelope=((0, 0, 8.4), (5.4, 5.0, 4.9)), r_tip=0.0068, pipe=2.0, flare=0.45,
                levels=[dict(len=9.6, seg=0.55, tropism=0.04, wobble=0.10, kids=11, start=0.3, angle=58, ratio=0.72, gravity=0.0),
                        dict(seg=0.45, tropism=0.07, wobble=0.16, kids=8, start=0.15, angle=46, ratio=0.55, gravity=0.06),
                        dict(seg=0.35, tropism=0.06, wobble=0.22, kids=6, start=0.2, angle=50, ratio=0.45, gravity=0.06),
                        dict(seg=0.2, tropism=0.05, wobble=0.25, kids=0, start=0.0, angle=0, ratio=0.0, gravity=0.0)],
                twig_len=(0.3, 0.55), card_len=(0.55, 0.85), fronds_per_twig=3, bend=0.16,
                leaf=dict(src="jacaranda_tree", diff="leaves_diff", alpha="leaves_alpha", nor=None,
                          rects=JACARANDA_FRONDS, tint=(0.78, 0.92, 0.66)),
                bark=dict(src="bark_brown_02", diff="Diffuse", nor="nor_gl", tile=(0.7, 1.2)),
                lods=[dict(trunk=10, branch=5, thin=3, seg=1, min_len=0.0, keep=1.0, csegs=2, max_level=2),
                      dict(trunk=7, branch=4, thin=0, seg=2, min_len=0.9, keep=0.36, csegs=1, max_level=2),
                      dict(trunk=5, branch=3, thin=0, seg=4, min_len=2.2, keep=0.10, csegs=1, max_level=1)],
                lod_dist=[0, 20, 45, 85]),
    # multi-stem deciduous shrub with single willow-leaf cards
    "shrub": dict(kind="shrub", title="Shrub (willow-leaf)", height=1.5, stems=7,
                  envelope=((0, 0, 0.78), (0.95, 0.9, 0.78)), r_tip=0.0022, pipe=2.0, flare=0.0,
                  levels=[dict(len=1.25, seg=0.16, tropism=0.05, wobble=0.12, kids=8, start=0.25, angle=44, ratio=0.55, gravity=0.04),
                          dict(seg=0.1, tropism=0.08, wobble=0.2, kids=5, start=0.15, angle=48, ratio=0.5, gravity=0.04),
                          dict(seg=0.06, tropism=0.05, wobble=0.25, kids=0, start=0.0, angle=0, ratio=0.0, gravity=0.0)],
                  twig_len=(0.14, 0.24), card_len=(0.12, 0.18), leaves_per_twig=5, bend=0.12,
                  leaf=dict(src="shrub_02", diff="Diffuse", alpha="Alpha", nor="nor_gl",
                            rects=WILLOW_LEAVES, tint=(0.95, 1.0, 0.92)),
                  bark=dict(src="bark_brown_02", diff="Diffuse", nor=None, tile=(0.25, 0.5)),
                  lods=[dict(trunk=5, branch=4, thin=3, seg=1, min_len=0.0, keep=1.0, csegs=1, max_level=1),
                        dict(trunk=3, branch=3, thin=0, seg=2, min_len=0.25, keep=0.3, csegs=1, max_level=0),
                        dict(trunk=3, branch=0, thin=0, seg=4, min_len=99, keep=0.1, csegs=1, max_level=0)],
                  lod_dist=[0, 10, 22, 40]),
    # ground-cover clump: bent fern fronds radiating from a crown, no wood
    "fern": dict(kind="clump", title="Ground cover (fern clump)", height=0.75, fronds=16,
                 frond_len=(0.5, 0.85), elev=(48, 80), bend=0.32,
                 leaf=dict(src="fern_02", diff="Diffuse", alpha="Alpha", nor="nor_gl",
                           rects=FERN_FRONDS, tint=(1.0, 1.0, 1.0)),
                 bark=None,
                 lods=[dict(fronds=16, csegs=3), dict(fronds=8, csegs=2), dict(fronds=5, csegs=1)],
                 lod_dist=[0, 8, 18, 30]),
}

TEX_SIZES = dict(leaf=1024, leaf_nor=512, bark=512, bark_nor=512, impostor=2048, impostor_ship=1024)
IMPOSTOR_FRAMES = 8


def node_name(sid):
    """glTF root node of species `sid`: Veg_ + the id with its first letter upper-cased (the runtime's
    `Veg_${name[0].toUpperCase() + name.slice(1)}` rule; .title() differs for ids with underscores)."""
    return "Veg_" + sid[0].upper() + sid[1:]


def kits():
    """Species kits under blender/wilderness/species/ (kit name -> {species id: params})."""
    from species import blue_ridge
    return {"blue_ridge": blue_ridge.KIT}


def all_species():
    out = dict(SPECIES)
    for kit in kits().values():
        out.update(kit)
    return out


_ATLAS = {}


def leaf_atlas(atlas_id):
    """Shared twig-card atlas (leafcards.py) -> its info (rects, real card sizes, mean colours, tiles)."""
    if atlas_id not in _ATLAS:
        import leafcards
        from species import blue_ridge_cards
        _ATLAS[atlas_id] = leafcards.build_atlas(atlas_id, blue_ridge_cards.ATLASES[atlas_id])
    return _ATLAS[atlas_id]


# =============================================================================================
# textures
def _load(path):
    im = bpy.data.images.load(path, check_existing=False)
    w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, im.channels)
    bpy.data.images.remove(im)
    if a.shape[2] == 1:
        a = np.repeat(a, 4, 2)
    return a


def _dilate(rgb, mask, iters=24):
    """Bleed opaque texels' colour into the transparent ones (no dark halos once mipmapped)."""
    rgb = rgb.copy()
    valid = mask.copy()
    for _ in range(iters):
        acc = np.zeros_like(rgb)
        cnt = np.zeros(mask.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            v = np.roll(np.roll(valid, dy, 0), dx, 1)
            acc += np.roll(np.roll(rgb, dy, 0), dx, 1) * v[..., None]
            cnt += v
        grow = (~valid) & (cnt > 0)
        rgb[grow] = acc[grow] / cnt[grow][:, None]
        valid |= grow
        if valid.all():
            break
    if (~valid).any():
        rgb[~valid] = rgb[valid].mean(0)
    return rgb


def _save(arr, path, name, colorspace="sRGB", size=None):
    h, w = arr.shape[:2]
    im = bpy.data.images.new(name, w, h, alpha=True)
    im.colorspace_settings.name = colorspace
    im.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel())
    if size and size != w:
        im.scale(size, size)
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)


def prep_textures(sp_name, sp):
    """RGBA leaf atlas (Poly Haven diffuse + its separate alpha map, colour-dilated, tinted),
    leaf normal map, bark colour/normal at shipping size. Returns {role: (path, colorspace)}."""
    import veg_sources
    os.makedirs(PREP, exist_ok=True)
    out = {}
    lf = sp.get("leaf")
    if lf and lf.get("atlas"):                      # shared twig-card atlas (Blue Ridge kit)
        info = leaf_atlas(lf["atlas"])
        out["leaf"] = (os.path.join(PREP, info["atlas"]), "sRGB")
        out["leaf_nor"] = (os.path.join(PREP, info["normal"]), "Non-Color")
        lf = None
    sh = sp.get("shell")
    if sh:
        t = leaf_atlas(sh["atlas"])["tiles"][sh["tile"]]
        out["shell"] = (os.path.join(PREP, t["albedo"]), "sRGB")
        out["shell_nor"] = (os.path.join(PREP, t["normal"]), "Non-Color")
    p = os.path.join(PREP, f"T_Veg_{sp_name.title()}_Leaf.png")
    if lf is None:
        pass
    elif not os.path.exists(p):
        d = _load(veg_sources.path(lf["src"], lf["diff"]))[..., :3]
        a = _load(veg_sources.path(lf["src"], lf["alpha"]))[..., 0]
        rgb = _dilate(d * np.array(lf["tint"], np.float32), a > 0.5)
        _save(np.dstack([rgb, a]), p, "leaf", size=TEX_SIZES["leaf"])
    if lf is not None:
        out["leaf"] = (p, "sRGB")
    if lf is not None and lf.get("nor"):
        p = os.path.join(PREP, f"T_Veg_{sp_name.title()}_Leaf_N.png")
        if not os.path.exists(p):
            n = _load(veg_sources.path(lf["src"], lf["nor"]))
            n[..., 3] = 1
            _save(n, p, "leafn", "Non-Color", TEX_SIZES["leaf_nor"])
        out["leaf_nor"] = (p, "Non-Color")
    bk = sp.get("bark")
    if bk:
        # colour keyed by (scan, tint): species that grade one scan differently get their own map, the
        # normal map is shared per scan. tag = a short name, "_h<hash>" keeps re-tints from going stale
        grade = [bk.get("tint", (1, 1, 1)), bk.get("sat", 1.0), bk.get("gain", 1.0)]
        tag = bk.get("tag")
        suffix = f"_{tag}_{hashlib.sha1(repr(grade).encode()).hexdigest()[:4]}" if tag else ""
        p = os.path.join(PREP, f"T_Veg_{bk['src'].title().replace('_', '')}{suffix}_Bark.png")
        if not os.path.exists(p):
            d = _load(veg_sources.path(bk["src"], bk["diff"]))
            d[..., 3] = 1
            if tag:
                g = d[..., :3] @ np.array([0.3, 0.59, 0.11], np.float32)
                rgb = g[..., None] + (d[..., :3] - g[..., None]) * grade[1]
                d[..., :3] = np.clip(rgb * np.array(grade[0], np.float32) * grade[2], 0, 1)
            _save(d, p, "bark", size=TEX_SIZES["bark"])
        out["bark"] = (p, "sRGB")
        if bk.get("nor"):
            p = os.path.join(PREP, f"T_Veg_{bk['src'].title().replace('_', '')}_Bark_N.png")
            if not os.path.exists(p):
                n = _load(veg_sources.path(bk["src"], bk["nor"]))
                n[..., 3] = 1
                _save(n, p, "barkn", "Non-Color", TEX_SIZES["bark_nor"])
            out["bark_nor"] = (p, "Non-Color")
    return out


def _image(path, colorspace):
    name = os.path.splitext(os.path.basename(path))[0]
    im = bpy.data.images.get(name)
    if im is None:
        im = bpy.data.images.load(path)
        im.name = name
    im.colorspace_settings.name = colorspace
    return im


def make_materials(sp_name, sp, tex):
    """bark (opaque), leaf (alpha-tested cards: "Leaf" in the name -> MASK at export), shell (opaque leaf
    mass inside dense shrubs: early-z rejects the cards behind it, the overdraw saving)."""
    mats = {}
    for role in ("bark", "leaf", "shell"):
        if role not in tex:
            continue
        if role == "leaf":
            name = "M_" + node_name(sp_name) + "_Leaf" if sp.get("leaf", {}).get("atlas") else \
                f"M_Veg_{sp_name.title()}_Leaf"
        elif role == "shell":
            name = "M_" + node_name(sp_name) + "_Shell"
        else:
            name = f"M_Veg_{os.path.basename(tex['bark'][0])[6:-4]}"
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        img = nt.nodes.new("ShaderNodeTexImage")
        img.image = _image(*tex[role])
        img.location = (-600, 200)
        nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
        rough = dict(bark=sp.get("bark", {}).get("rough", 0.92) if sp.get("bark") else 0.92,
                     leaf=sp.get("leaf_rough", 0.62), shell=0.85)[role]
        bsdf.inputs["Roughness"].default_value = rough
        if role == "leaf":
            nt.links.new(img.outputs["Alpha"], bsdf.inputs["Alpha"])
            m.use_backface_culling = False
            try:
                m.surface_render_method = "DITHERED"
            except (AttributeError, TypeError):
                pass
        if f"{role}_nor" in tex:
            nimg = nt.nodes.new("ShaderNodeTexImage")
            nimg.image = _image(*tex[f"{role}_nor"])
            nimg.location = (-600, -200)
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.location = (-300, -200)
            nm.inputs["Strength"].default_value = 0.8
            nt.links.new(nimg.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
        mats[role] = m
    return mats


# =============================================================================================
# skeletons
class Branch:
    def __init__(self, pts, level, parent=None, at=0.0, phase=0.0):
        self.pts = pts            # list[Vector]
        self.rad = None           # list[float], filled by the species' radius rule
        self.level = level
        self.parent = parent
        self.at = at              # attachment: float index into parent.pts
        self.children = []
        self.phase = phase
        self.path0 = 0.0          # path length from the trunk to this branch's base
        self.wood = True          # False: a virtual twig (only an anchor for cards)
        self.twigs = []           # conifer: (pos, dir, length) card anchors along this branch
        if parent is not None:
            parent.children.append(self)

    def length(self):
        return sum((b - a).length for a, b in zip(self.pts, self.pts[1:]))

    def point(self, f):
        """Point and tangent at fraction f of the polyline's index range."""
        x = f * (len(self.pts) - 1)
        i = min(int(x), len(self.pts) - 2)
        t = x - i
        p = self.pts[i].lerp(self.pts[i + 1], t)
        d = (self.pts[i + 1] - self.pts[i]).normalized()
        return p, d, i + t

    def cum(self):
        out = [0.0]
        for a, b in zip(self.pts, self.pts[1:]):
            out.append(out[-1] + (b - a).length)
        return out


def all_branches(root):
    out, stack = [], [root]
    while stack:
        b = stack.pop()
        out.append(b)
        stack.extend(b.children)
    return out


def _perp(d):
    a = Vector((1, 0, 0)) if abs(d.x) < 0.9 else Vector((0, 1, 0))
    return d.cross(a).normalized()


def _rotate(v, axis, ang):
    return Matrix.Rotation(ang, 3, axis) @ v


def _rand_unit(rng):
    while True:
        v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
        if 0.01 < v.length <= 1:
            return v.normalized()


def conifer(P, rng):
    """Excurrent conifer: one leader, whorls of primary branches every whorl_gap metres whose
    length follows a cone, each drooping then upturning; card anchors ('twigs') alternate left
    and right along every primary (the spray texture already draws the secondary twigs)."""
    H, r0 = P["height"], P["trunk_r"]
    n = 30
    lean = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)) * 0.18
    w1, w2 = rng.uniform(0, 6.28), rng.uniform(0, 6.28)
    pts = []
    ld = P.get("leader_droop", 0.0)               # hemlock: the leader nods over
    ldir = Vector((math.cos(w1), math.sin(w1), 0))
    for i in range(n + 1):
        t = i / n
        wob = Vector((math.sin(t * 9 + w1), math.cos(t * 7 + w2), 0)) * P.get("trunk_wob", 0.04)
        q = Vector((0, 0, H * t)) + lean * t * t + wob * t
        if ld and H * t > H - ld:
            u = (H * t - (H - ld)) / ld
            q += ldir * (u * u * ld * 0.55) - UP * (u * u * ld * 0.3)
        pts.append(q)
    trunk = Branch(pts, 0)
    trunk.rad = [(r0 * (1 - t) ** 0.95 + 0.012) * (1 + P["flare"] * math.exp(-H * t / 0.35))
                 for t in (i / n for i in range(n + 1))]

    def trunk_at(z):
        return trunk.point(min(max(z / H, 0), 1))

    z, k = P["crown_base"], 0
    span = H - P["crown_base"]
    dead = P.get("dead", False)                  # snag: broken-off limbs, no foliage
    while z < H - 0.45:
        rel = (z - P["crown_base"]) / span
        nb = rng.choice(P.get("whorl_n", (4, 5, 5, 6)))
        az0 = k * 2.39996 + rng.uniform(0, 0.6)
        tp, _, tat = trunk_at(z)
        rt = r0 * (1 - z / H) ** 0.95 + 0.012
        if rng.random() < P.get("skip", 0.0):     # white pine: missing whorls make the tiers
            z += P["whorl_gap"] * rng.uniform(0.85, 1.15) * (1 - 0.45 * rel)
            k += 1
            continue
        for b in range(nb):
            az = az0 + b * 2 * math.pi / nb + rng.uniform(-0.25, 0.25)
            if P.get("profile") == "pine":         # long limbs well up the crown, a flat-topped crown
                L = (P["branch_len"] * (1 - rel) ** 0.45 + 0.3) * rng.uniform(0.6, 1.1)
            else:
                L = (P["branch_len"] * (1 - rel) ** P["cone"] + 0.3) * rng.uniform(0.82, 1.1)
            if dead:
                L *= rng.uniform(0.2, 0.6)
            e0 = P["elev_bottom"] + (P["elev_top"] - P["elev_bottom"]) * rel ** 0.8
            hd = Vector((math.cos(az), math.sin(az), 0))
            segs = 6
            bp = [tp.copy()]
            for s in range(1, segs + 1):
                f = s / segs
                e = math.radians(e0 + rng.uniform(-4, 4) - P["droop"] * f * (1 - 0.5 * rel)
                                 + P["upturn"] * f ** 3)
                d = (hd * math.cos(e) + UP * math.sin(e)).normalized()
                hd = _rotate(hd, UP, rng.uniform(-0.06, 0.06))
                bp.append(bp[-1] + d * (L / segs))
            br = Branch(bp, 1, trunk, tat, phase=rng.random())
            rb = min(max(rt * 0.3, 0.01), P.get("branch_r", 0.05)) * (L / max(P["branch_len"], 1e-3)) ** 0.5
            rb = max(rb, 0.01) * (1.6 if dead else 1.0)
            br.rad = [rb * (1 - s / segs) ** 0.85 + 0.0035 for s in range(segs + 1)]
            if dead:
                continue
            up = P.get("twig_up", 0.0)

            def anchors(bb, Lb, s0, gap):
                s, side = s0, 1
                while s < Lb * 0.97:
                    p, d, _ = bb.point(s / Lb)
                    side_v = d.cross(UP).normalized() if abs(d.z) < 0.95 else _perp(d)
                    ang = math.radians(rng.uniform(40, 62))
                    td = (d * math.cos(ang) + side_v * side * math.sin(ang)).normalized()
                    td.z += up - rng.uniform(0.05, 0.25)
                    remain = Lb - s
                    tl = min(P["twig_len"], 0.45 * remain + 0.32) * rng.uniform(0.85, 1.1)
                    bb.twigs.append((p, td.normalized(), tl, s))
                    s += gap * rng.uniform(0.8, 1.2)
                    side = -side
                p, d, _ = bb.point(1.0)
                dd = (d + UP * up).normalized()
                bb.twigs.append((p - d * 0.15, dd, P["card_len"][1] * 0.9, Lb))
            # twig anchors: alternate sides in the branch's (nearly horizontal) plane; the tip carries a spray
            anchors(br, L, P.get("twig_from", 0.18) * L, P["twig_gap"])
            sec = P.get("secondary")
            if sec and L > sec.get("min_len", 1.5):      # secondary limbs (laterals of the primary)
                s, side = sec.get("from", 0.25) * L, rng.choice((-1, 1))
                while s < L * 0.85:
                    p, d, idx = br.point(s / L)
                    side_v = d.cross(UP).normalized() if abs(d.z) < 0.95 else _perp(d)
                    ang = math.radians(sec.get("angle", 50) + rng.uniform(-10, 10))
                    sd = (d * math.cos(ang) + side_v * side * math.sin(ang)).normalized()
                    L2 = (L - s) * sec.get("len_k", 0.45) * rng.uniform(0.7, 1.1) + 0.3
                    sp_ = [p.copy()]
                    for q in range(1, 5):
                        e = math.radians(-sec.get("droop", 8) * q / 4 + P.get("upturn", 0) * 0.5 * (q / 4) ** 3)
                        dd = (Vector((sd.x, sd.y, 0)).normalized() * math.cos(e) + UP * math.sin(e)).normalized()
                        sp_.append(sp_[-1] + dd * (L2 / 4))
                    b2 = Branch(sp_, 2, br, idx, phase=(br.phase + rng.uniform(-0.05, 0.05)) % 1)
                    r2 = max(0.006, br.rad[min(int(idx), len(br.rad) - 1)] * 0.45)
                    b2.rad = [r2 * (1 - q / 4) ** 0.8 + 0.003 for q in range(5)]
                    anchors(b2, L2, 0.2 * L2, P["twig_gap"] * sec.get("gap_k", 1.2))
                    s += sec.get("gap", 0.9) * rng.uniform(0.8, 1.2)
                    side = -side
        z += P["whorl_gap"] * rng.uniform(0.85, 1.15) * (1 - 0.45 * rel)
        k += 1
    # a few dead stubs below the crown
    for _ in range(P.get("stubs", rng.randint(4, 7))):
        z = rng.uniform(0.9, P["crown_base"])
        tp, _, tat = trunk_at(z)
        az = rng.uniform(0, 6.28)
        d = Vector((math.cos(az), math.sin(az), rng.uniform(-0.3, 0.1))).normalized()
        L = rng.uniform(0.25, 0.7) * P.get("stub_k", 1.0)
        br = Branch([tp, tp + d * L], 1, trunk, tat, phase=rng.random())
        br.rad = [0.018 * P.get("stub_k", 1.0), 0.005 * P.get("stub_k", 1.0)]
    # leader: sprays around the top metre and a half
    trunk.twigs = []
    for i in range(0 if dead else 10):
        f = 1 - (i / 10) * (P["leader"] / H)
        p, _, _ = trunk.point(f)
        az = i * 2.39996
        d = Vector((math.cos(az) * 0.5, math.sin(az) * 0.5, 1.0)).normalized()
        trunk.twigs.append((p, d, P["card_len"][0] * (0.6 + 0.4 * i / 10), H * f))
    return trunk


def _envelope_t(p, d, env):
    """Distance along d from p to the crown ellipsoid's surface (<= 0: p is outside)."""
    c, r = Vector(env[0]), Vector(env[1])
    q = Vector(((p - c).x / r.x, (p - c).y / r.y, (p - c).z / r.z))
    e = Vector((d.x / r.x, d.y / r.y, d.z / r.z))
    a, b, cc = e.dot(e), 2 * q.dot(e), q.dot(q) - 1
    disc = b * b - 4 * a * cc
    if disc < 0:
        return 0.0
    return (-b + math.sqrt(disc)) / (2 * a)


def deciduous(P, rng):
    """Recursive growth: each branch is a polyline that bends toward the light (tropism), wobbles
    and sags; children leave at a fixed angle with a golden-angle azimuth, their lengths clipped
    to the crown envelope (the crown shape is the envelope, the branching is the texture).
    Shrubs start several stems from the base; trees one trunk. The last level is virtual (no
    wood): card anchors."""
    levels, env = P["levels"], P["envelope"]
    maxlev = len(levels) - 1

    def grow(start, d, L, level, parent, at, phase):
        Lv = levels[level]
        segs = max(2, int(round(L / Lv["seg"])))
        pts, d = [start.copy()], d.normalized()
        for i in range(segs):
            d = (d + UP * Lv["tropism"] + _rand_unit(rng) * Lv["wobble"]).normalized()
            d.z -= Lv["gravity"] * (i / segs)
            d.normalize()
            pts.append(pts[-1] + d * (L / segs))
        br = Branch(pts, level, parent, at, phase)
        br.wood = level < maxlev
        if level >= maxlev:
            return br
        nk = max(1, int(round(levels[level]["kids"] * rng.uniform(0.8, 1.2) * (L / (levels[level].get("len") or L)) ** 0.2)))
        if parent is None and P["kind"] == "broadleaf":
            nk = levels[0]["kids"]
        ln = levels[level + 1]
        for c in range(nk):
            f = Lv["start"] + (1 - Lv["start"]) * (c + rng.uniform(0.15, 0.85)) / nk
            p, t, idx = br.point(f)
            az = c * 2.39996 + rng.uniform(-0.35, 0.35)
            ax = _rotate(_perp(t), t, az)
            cd = _rotate(t, ax, math.radians(Lv["angle"] + rng.uniform(-10, 10)))
            nominal = L * Lv["ratio"] * (1 - 0.55 * f) * rng.uniform(0.8, 1.15)
            if level + 1 == maxlev:
                nominal = rng.uniform(*P["twig_len"])
            reach = _envelope_t(p, cd, env)
            Lc = min(nominal, max(reach * 0.92, nominal * 0.35 if level + 1 == maxlev else 0.0))
            if Lc < (0.12 if P["kind"] == "broadleaf" else 0.04):
                continue
            ph = rng.random() if level == 0 else phase + rng.uniform(-0.08, 0.08)
            grow(p, cd, Lc, level + 1, br, idx, ph % 1.0)
        # the branch's own tip carries a twig too
        if level + 1 == maxlev:
            p, t, idx = br.point(1.0)
            grow(p, t, rng.uniform(*P["twig_len"]), maxlev, br, idx, phase)
        return br

    if P["kind"] in ("shrub", "thicket"):
        base = Branch([Vector((0, 0, 0)), Vector((0, 0, 0.01))], -1)   # virtual root joining the stems
        base.wood = False
        plants = P.get("plants") or [(0.0, 0.0)]
        if P["kind"] == "thicket" and not P.get("plants"):
            # jittered grid over the tile footprint (several shrubs grown into one mass)
            half, n = P["tile"] / 2, P.get("grid", 3)
            plants = [(-half + (i + rng.uniform(0.25, 0.75)) * P["tile"] / n, -half + (j + rng.uniform(0.25, 0.75)) * P["tile"] / n)
                      for i in range(n) for j in range(n)]
        tl = P.get("stem_tilt", (12, 34))
        so = P.get("stem_off", (0.02, 0.09))
        k = 0
        for px, py in plants:
            for s in range(P["stems"]):
                az = k * 2.39996 + rng.uniform(-0.3, 0.3)
                k += 1
                off = Vector((px, py, 0)) + Vector((math.cos(az), math.sin(az), 0)) * rng.uniform(*so)
                tilt = math.radians(rng.uniform(*tl))
                d = Vector((math.cos(az) * math.sin(tilt), math.sin(az) * math.sin(tilt), math.cos(tilt)))
                L = levels[0]["len"] * rng.uniform(0.7, 1.08)
                grow(off, d, L, 0, base, 0.0, rng.random())
        root = base
    else:
        lean = P.get("lean", 0.05)
        root = grow(Vector((0, 0, 0)), Vector((rng.uniform(-lean, lean), rng.uniform(-lean, lean), 1)),
                    levels[0]["len"], 0, None, 0.0, 0.0)
    if P.get("tunnel"):
        cut_tunnel(root, P["tunnel"])
    pipe_radii(root, P)
    if P.get("stubs") and P["kind"] == "broadleaf":
        H = root.pts[-1].z
        for _ in range(P["stubs"]):
            z = rng.uniform(2.5, P.get("crown_base", H * 0.5))
            p, _, idx = root.point(z / H)
            az = rng.uniform(0, 6.28)
            d = Vector((math.cos(az), math.sin(az), rng.uniform(-0.2, 0.4))).normalized()
            L = rng.uniform(0.25, 1.0)
            br = Branch([p, p + d * (L * 0.5), p + d * L], 1, root, idx, phase=rng.random())
            rs = rng.uniform(0.03, 0.08)
            br.rad = [rs, rs * 0.8, rs * 0.45]
    return root


def in_tunnel(p, T):
    """Tunnel through a thicket tile: a corridor along local x, |y - y(x)| < w/2, z < h (y(x) bends)."""
    yc = T.get("bend", 0.0) * math.sin(math.pi * (p.x / T["len"] + 0.5))
    return abs(p.y - yc) < T["w"] / 2 and p.z < T["h"] and abs(p.x) < T["len"] / 2 + 0.5


def cut_tunnel(root, T):
    """Remove every branch (and what grows from it) whose polyline runs through the tunnel; stems are
    cut at their first point inside, so the corridor is clear wood and the canopy above stays."""
    def walk(b):
        for i, p in enumerate(b.pts):
            if b.level >= 0 and in_tunnel(p, T):
                if i < 2:
                    if b.parent is not None:
                        b.parent.children.remove(b)
                    return
                b.pts = b.pts[:i]
                b.children = [c for c in b.children if c.at < i - 1]
                break
        for c in list(b.children):
            walk(c)
    walk(root)


def pipe_radii(root, P):
    """Pipe model: a node's cross-section carries every tip downstream of it,
    r = r_tip * n_tips^(1/p) (p = 2: da Vinci's rule, area preserved at forks)."""
    def tips(b):
        n = len(b.pts)
        flow = [0.0] * n
        flow[n - 1] += 1.0
        for c in b.children:
            ft = tips(c)
            flow[min(int(math.ceil(c.at)), n - 1)] += ft
        acc = 0.0
        for i in range(n - 1, -1, -1):
            acc += flow[i]
            flow[i] = acc
        b.rad = [P["r_tip"] * f ** (1 / P["pipe"]) for f in flow]
        k = P.get("rad_k")
        if k and 0 <= b.level < len(k):
            b.rad = [r * k[b.level] for r in b.rad]
        if b.level == 0 and P.get("trunk_r") and P["kind"] == "broadleaf":
            H = max(p.z for p in b.pts) or 1.0
            b.rad = [max(r, P["trunk_r"] * (1 - P.get("trunk_taper", 0.72) * (p.z / H) ** 1.15))
                     for r, p in zip(b.rad, b.pts)]
        if b.level == 0 and P.get("flare"):
            fz = P.get("flare_z", 0.3)
            b.rad = [r * (1 + P["flare"] * math.exp(-p.z / fz)) for r, p in zip(b.rad, b.pts)]
        return flow[0]
    tips(root)


def set_paths(root):
    """path0: path length from the trunk to each branch's base (the wind bend weight's input)."""
    for b in all_branches(root):
        if b.parent is None or b.level <= 0:
            b.path0 = 0.0
            continue
        par = b.parent
        if par.level <= 0:
            b.path0 = 0.0
        else:
            cum = par.cum()
            i = min(int(b.at), len(cum) - 2)
            t = b.at - i
            b.path0 = par.path0 + cum[i] + (cum[i + 1] - cum[i]) * t


# =============================================================================================
# cards
def card_rects(rects):
    """Atlas rects -> (base_uv, along_uv, across_uv, along_extent, across_lo, across_hi), UVs with
    v up (Blender/glTF-after-flip convention), extents in UV units."""
    out = []
    for x0, y0, x1, y1, side, b in rects:
        u0, u1, v0, v1 = x0 / 8, x1 / 8, 1 - y1 / 8, 1 - y0 / 8
        if side == "b":
            base, al, ac = (b / 8, v0), (0, 1), (1, 0)
            ext, lo, hi = v1 - v0, u0 - b / 8, u1 - b / 8
        elif side == "l":
            bv = 1 - b / 8
            base, al, ac = (u0, bv), (1, 0), (0, 1)
            ext, lo, hi = u1 - u0, v0 - bv, v1 - bv
        else:
            bv = 1 - b / 8
            base, al, ac = (u1, bv), (-1, 0), (0, -1)
            ext, lo, hi = u1 - u0, -(v1 - bv), -(v0 - bv)
        out.append((base, al, ac, ext, lo, hi))
    return out


def conifer_cards(trunk, P, rng):
    cards = []
    for b in all_branches(trunk):
        for (p, d, tl, s) in b.twigs:
            L = min(max(tl, P["card_len"][0]), P["card_len"][1]) * rng.uniform(0.9, 1.1)
            if b.level == 0:
                across = _perp(d)
                roll = rng.uniform(0, 6.28)
            else:
                across = d.cross(UP).normalized() if abs(d.z) < 0.97 else _perp(d)
                roll = math.radians(rng.uniform(-P.get("spray_roll", 28), P.get("spray_roll", 28)))
            across = _rotate(across, d, roll)
            if P.get("_rect_w"):
                rect = rng.choices(range(len(P["_rect_w"])), P["_rect_w"])[0]
            else:
                rect = rng.choice((0, 1, 3)) if L > 0.7 else rng.randrange(len(P["leaf"]["rects"]))
            path = (b.path0 + s) if b.level > 0 else 0.0
            cards.append(dict(base=p.copy(), along=d.copy(), across=across, L=L, rect=rect,
                              bend=rng.uniform(0.08, 0.2), path=path, phase=b.phase,
                              key=rng.random(), level=b.level))
            if rng.random() < P.get("spray2", 0.35):   # a steeper second spray: volume seen from the side
                ac2 = _rotate(across, d, math.radians(rng.choice((-1, 1)) * rng.uniform(55, 80)))
                cards.append(dict(base=p.copy(), along=d.copy(), across=ac2, L=L * 0.85,
                                  rect=rect if P.get("_rect_w") else rng.randrange(len(P["leaf"]["rects"])),
                                  bend=rng.uniform(0.05, 0.15),
                                  path=path, phase=b.phase, key=rng.random(), level=b.level))
    return cards


def conifer_branch_cards(trunk, P):
    """Far LOD: one pair of big sprays per primary branch (rolled +-40 deg so the crown still reads
    from the side), base at the trunk, along the branch's chord."""
    rng = random.Random(99)
    cards = []
    for b in trunk.children:
        L = b.length()
        if L < 0.6:
            continue
        p0, p1 = b.pts[0], b.pts[-1]
        d = (p1 - p0).normalized()
        across = d.cross(UP).normalized() if abs(d.z) < 0.97 else _perp(d)
        for sgn in (-1, 1):
            ac = _rotate(across, d, math.radians(sgn * rng.uniform(30, 45)))
            cards.append(dict(base=p0 + d * 0.1, along=d, across=ac, L=L * 1.2,
                              rect=rng.choice(P.get("base_rects", (0, 1))),
                              bend=0.12, path=0.0, phase=b.phase, key=rng.random(), level=1, outer=1))
    for i in range(4):
        az = i * 1.5708
        d = Vector((math.cos(az) * 0.35, math.sin(az) * 0.35, 1)).normalized()
        top = trunk.pts[-1] - UP * P["leader"] * 1.1
        cards.append(dict(base=top, along=d, across=Vector((-math.sin(az), math.cos(az), 0)),
                          L=P["leader"] * 1.15, rect=P.get("base_rects", (0,))[0], bend=0.0, path=0.0, phase=0.0, key=0.5,
                          level=0, outer=1))
    return cards


def deciduous_cards(root, P, rng):
    cards = []
    env_c = Vector(P["envelope"][0])
    for b in all_branches(root):
        if b.wood:
            continue
        L_tw = b.length()
        n = P.get("fronds_per_twig") or P.get("leaves_per_twig")
        for j in range(n):
            f = 1.0 if j == 0 else rng.uniform(0.25, 0.95)
            p, d, _ = b.point(f)
            out = (p - env_c)
            out.z *= 0.5
            out = out.normalized() if out.length > 1e-4 else UP
            if j == 0:
                ad = (d + out * 0.3 + UP * 0.15).normalized()
            else:
                side = _rotate(_perp(d), d, rng.uniform(0, 6.28))
                ad = (d * 0.55 + side * 0.65 + out * 0.3 + UP * 0.1).normalized()
            if P.get("card_flat"):                 # rosette cards (rhododendron whorls) face the sky
                ad.z *= 1 - P["card_flat"]
                ad.normalize()
            across = ad.cross(UP) if abs(ad.z) < 0.95 else _perp(ad)
            cr = P.get("card_roll", 35)
            across = _rotate(across.normalized(), ad, math.radians(rng.uniform(-cr, cr)))
            if P.get("_rect_w"):
                rect = rng.choices(range(len(P["_rect_w"])), P["_rect_w"])[0]
                L = P["_rect_len"][rect] * P.get("card_scale", 1.0) * rng.uniform(0.85, 1.15)
            else:
                rect = rng.randrange(len(P["leaf"]["rects"]))
                L = rng.uniform(*P["card_len"])
            cards.append(dict(base=p.copy(), along=ad, across=across, L=L,
                              rect=rect, bend=P["bend"] * rng.uniform(0.6, 1.4),
                              path=b.path0 + f * L_tw, phase=b.phase, key=rng.random(), level=b.level))
    return cards


# =============================================================================================
# mesh building
class MeshData:
    def __init__(self):
        self.co, self.nrm, self.wind, self.faces, self.uvs, self.mat = [], [], [], [], [], []

    def vert(self, co, n, wind):
        self.co.append(tuple(co))
        self.nrm.append(tuple(n))
        self.wind.append(tuple(wind))
        return len(self.co) - 1

    def face(self, idx, uvs, mat):
        self.faces.append(tuple(idx))
        self.uvs.extend(uvs)
        self.mat.append(mat)

    def tris(self):
        return sum(len(f) - 2 for f in self.faces)


def tube(md, b, sides, step, bark_tile, wmax, mat=0, cap=True):
    """A tapered generalised cylinder along b.pts (every `step`-th point) with parallel-transport
    frames. UVs: u wraps an integer number of bark tiles around, v = metres / tile along."""
    idx = list(range(0, len(b.pts), step))
    if idx[-1] != len(b.pts) - 1:
        idx.append(len(b.pts) - 1)
    pts = [b.pts[i].copy() for i in idx]
    rad = [b.rad[i] for i in idx]
    cum0 = b.cum()
    cum = [cum0[i] for i in idx]
    if b.parent is not None and b.level > 0 and len(pts) > 1:
        d0 = (pts[1] - pts[0]).normalized()
        pts[0] = pts[0] - d0 * min(rad[0] * 1.5, 0.3 * (pts[1] - pts[0]).length)  # sink into the parent
    n = len(pts)
    tang = []
    for i in range(n):
        a, c = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        tang.append((c - a).normalized())
    nrm = _perp(tang[0])
    urep = max(1, round(2 * math.pi * rad[0] / bark_tile[0]))
    rings = []
    for i in range(n):
        if i > 0:
            nrm = (nrm - tang[i] * nrm.dot(tang[i])).normalized()
        bin_ = tang[i].cross(nrm)
        w = 0.0 if b.level <= 0 else min(1.0, (b.path0 + cum[i]) / wmax)
        ring = []
        for j in range(sides + 1):
            a = 2 * math.pi * j / sides
            dirv = nrm * math.cos(a) + bin_ * math.sin(a)
            co = pts[i] + dirv * rad[i]
            ring.append((md.vert(co, dirv, (w, 0.0, b.phase)), (urep * j / sides, cum[i] / bark_tile[1])))
        rings.append(ring)
    for i in range(n - 1):
        for j in range(sides):
            a, bq, c, d = rings[i][j], rings[i][j + 1], rings[i + 1][j + 1], rings[i + 1][j]
            md.face((a[0], bq[0], c[0], d[0]), (a[1], bq[1], c[1], d[1]), mat)
    if cap and rad[-1] > 0.006:
        tipco = pts[-1] + tang[-1] * rad[-1]
        w = 0.0 if b.level <= 0 else min(1.0, (b.path0 + cum[-1]) / wmax)
        tip = md.vert(tipco, tang[-1], (w, 0.0, b.phase))
        for j in range(sides):
            a, bq = rings[-1][j], rings[-1][j + 1]
            md.face((a[0], bq[0], tip), (a[1], bq[1], (a[1][0], a[1][1] + 0.05)), mat)


def card_mesh(md, c, rects, segs, scale, wmax, crown_n, mat=1):
    base_uv, al, ac, ext, lo, hi = rects[c["rect"]]
    L = c["L"] * scale
    k = L / ext                                   # metres per UV unit
    A, C = c["along"], c["across"]
    N = A.cross(C).normalized()
    if N.z < 0:
        N = -N
    base = c["base"]
    if scale != 1.0:                              # grow thinned cards about their centre (half-way)
        centre = c["base"] + A * (c["L"] * 0.5)
        base = (centre - A * (L * 0.5)).lerp(c["base"], 0.5)
    rows = []
    bdir = c.get("bend_dir", -UP)
    for s_i in range(segs + 1):
        s = s_i / segs
        droop = c["bend"] * L * s * s
        row = []
        for a in (lo, hi):
            co = base + A * (s * L) + C * (a * k) + bdir * droop
            cn = c["normal"] if "normal" in c else crown_n(co)
            n = (N * (0.35 if N.dot(cn) >= 0 else -0.35) + cn * 0.65).normalized()
            w = min(1.0, (c["path"] + s * L) / wmax)
            uv = (base_uv[0] + al[0] * s * ext + ac[0] * a, base_uv[1] + al[1] * s * ext + ac[1] * a)
            row.append((md.vert(co, n, (w, s, (c["phase"] + 0.13 * c["key"]) % 1.0)), uv))
        rows.append(row)
    for s_i in range(segs):
        a, b = rows[s_i][0], rows[s_i][1]
        cc, d = rows[s_i + 1][1], rows[s_i + 1][0]
        md.face((a[0], b[0], cc[0], d[0]), (a[1], b[1], cc[1], d[1]), mat)


def crown_normal_fn(sp, root):
    if sp["kind"] == "conifer":
        H = sp["height"]

        def fn(p):
            r = Vector((p.x, p.y, 0))
            r = r.normalized() if r.length > 1e-4 else Vector((1, 0, 0))
            slope = sp["branch_len"] / (H - sp["crown_base"])          # cone: normal tilts up
            return (r + UP * slope * 1.2 + UP * 0.25).normalized()
        return fn
    if sp["kind"] in ("clump", "mat"):
        def fn(p):
            r = Vector((p.x, p.y, 0))
            r = r.normalized() if r.length > 1e-4 else Vector((1, 0, 0))
            return (r * 0.6 + UP).normalized()
        return fn
    c, r = Vector(sp["envelope"][0]), Vector(sp["envelope"][1])

    def fn(p):
        q = p - c
        g = Vector((q.x / (r.x * r.x), q.y / (r.y * r.y), q.z / (r.z * r.z)))
        return g.normalized() if g.length > 1e-6 else UP
    return fn


def fern_cards(P, lod, rng):
    cards = []
    n = lod["fronds"]
    sterile = P.get("frond_rects") or list(range(len(P["leaf"]["rects"])))
    for i in range(n):
        rr = random.Random(1000 + i + 7919 * P.get("_variant", 0))   # the same frond i in every LOD
        az = i * 2.39996 + rr.uniform(-0.2, 0.2)
        e = math.radians(rr.uniform(*P["elev"]))
        d = Vector((math.cos(az) * math.cos(e), math.sin(az) * math.cos(e), math.sin(e)))
        rect = sterile[rr.randrange(len(sterile))]
        if P.get("_rect_len"):
            L = P["_rect_len"][rect] * P.get("card_scale", 1.0) * rr.uniform(0.75, 1.1)
        else:
            L = rr.uniform(*P["frond_len"])
        across = Vector((-math.sin(az), math.cos(az), 0))
        across = _rotate(across, d, math.radians(rr.uniform(-20, 20)))
        base = Vector((math.cos(az), math.sin(az), 0)) * P.get("crown_r", 0.03) * rr.uniform(0.3, 1.0) + Vector((0, 0, 0.02))
        cards.append(dict(base=base, along=d, across=across, L=L, rect=rect,
                          bend=P["bend"] * rr.uniform(0.7, 1.2), path=0.0, phase=rr.random(), key=rr.random(), level=9))
    fert = P.get("fertile")
    if fert and lod.get("fertile", True):            # cinnamon fern: the withered fertile fronds, upright, central
        for i in range(fert["n"]):
            rr = random.Random(5000 + i)
            az = rr.uniform(0, 6.28)
            e = math.radians(rr.uniform(*fert["elev"]))
            d = Vector((math.cos(az) * math.cos(e), math.sin(az) * math.cos(e), math.sin(e)))
            L = P["_rect_len"][fert["rect"]] * rr.uniform(0.8, 1.05)
            across = Vector((-math.sin(az), math.cos(az), 0))
            cards.append(dict(base=Vector((0, 0, 0.02)), along=d, across=across, L=L, rect=fert["rect"], bend=0.05,
                              path=0.0, phase=rr.random(), key=rr.random(), level=9))
    # fewer fronds in lower LODs: widen them so the clump keeps its coverage
    return cards, (P["fronds"] / n) ** 0.5 if n < P["fronds"] else 1.0


def build_lod(sp_name, sp, root, cards, lod, li, mats, rng):
    md = MeshData()
    roles = sp.get("_roles") or (["leaf"] if sp["kind"] == "clump" else ["bark", "leaf"])
    mi = {r: i for i, r in enumerate(roles)}
    rects = card_rects(sp["leaf"]["rects"]) if sp.get("leaf") else []
    crown_n = crown_normal_fn(sp, root)
    if sp["kind"] == "clump":
        cards_l, scale = fern_cards(sp, lod, rng)
        for c in cards_l:
            c["path"] = 0.0
            card_mesh(md, c, rects, lod["csegs"], scale ** 0.5, 1.0, crown_n, mat=mi["leaf"])
            # flutter on fern fronds is the whole frond: bend weight = s
        for i, w in enumerate(md.wind):
            md.wind[i] = (w[1], w[1], w[2])
        return md, roles
    if sp["kind"] == "mat":
        moss_mat(md, sp, lod, rects, mi, crown_n)
        return md, roles
    wmax = max(1e-3, max([b.path0 + b.length() for b in all_branches(root) if b.level >= 1] + [c["path"] + c["L"] for c in cards] + [1.0]))
    bt = sp["bark"]["tile"]
    for b in all_branches(root):
        if not b.wood or b.level < 0 or b.level > lod["max_level"] or len(b.pts) < 2:
            continue
        L = b.length()
        if b.level >= 1 and L < lod["min_len"]:
            continue
        r0 = b.rad[0]
        sides = lod["trunk"] if b.level == 0 else (lod["branch"] if r0 > lod.get("thick_r", 0.02) or (sp["kind"] == "shrub" and b.level == 0) else lod["thin"])
        if sp["kind"] == "thicket" and b.level == 0:
            sides = lod["branch"]
        if sides < 3:
            continue
        tube(md, b, sides, lod["seg"], bt, wmax, mat=mi["bark"], cap=b.level > 0)
    if lod.get("branch_cards") and "leaf" in mi:    # conifer base layer: a spray pair per primary branch
        for c in conifer_branch_cards(root, sp):
            card_mesh(md, c, rects, lod["csegs"], 1.0, wmax, crown_n, mat=mi["leaf"])
    if lod.get("bark_cards") and sp.get("_bark_cards"):  # shagbark strips (LOD0 only)
        for c in sp["_bark_cards"]:
            card_mesh(md, c, rects, 1, 1.0, wmax, crown_n, mat=mi["leaf"])
    if lod.get("shell") and "shell" in mi:
        add_shell(md, sp["_shells"][lod["shell"]], mi["shell"], sp)
    keep = lod["keep"]
    if keep <= 0 or not cards:
        return md, roles
    # thinning: keep a deterministic subset, outer cards first (they make the silhouette); grow the
    # survivors so the crown keeps its leaf area
    kept = [c for c in cards if c["key"] * (1.25 - 0.5 * c.get("outer", 0.5)) < keep]
    scale = min(lod.get("max_grow", 2.8), (len(cards) / max(1, len(kept))) ** 0.5) if keep < 1 else 1.0
    for c in kept:
        card_mesh(md, c, rects, lod["csegs"], scale, wmax, crown_n, mat=mi["leaf"])
    return md, roles


def bark_strip_cards(root, P, rng):
    """Shagbark: long plates attached at the top, hanging down the bole and curling out at the foot."""
    bc = P["bark_cards"]
    out = []
    H = root.pts[-1].z
    for i in range(bc["n"]):
        z = rng.uniform(*bc["z"])
        p, t, idx = root.point(min(z / H, 1))
        r = root.rad[min(int(round(idx)), len(root.rad) - 1)]
        az = rng.uniform(0, 6.28)
        radial = Vector((math.cos(az), math.sin(az), 0))
        tang = Vector((-math.sin(az), math.cos(az), 0))
        L = rng.uniform(*bc["len"])
        out.append(dict(base=p + radial * (r * 0.98), along=(-UP + radial * 0.04).normalized(), across=tang, L=L,
                        rect=bc["rect"], bend=rng.uniform(0.12, 0.3), bend_dir=radial, normal=radial,
                        path=0.0, phase=0.0, key=0.0, level=0, outer=1))
    return out


def make_shells(sp, cards, targets):
    """Opaque leaf-mass hull: a metaball union of the foliage clumps, decimated per LOD, pulled inside
    the card layer by `inset`. Returns {target_tris: (co, faces, normals)}."""
    sh = sp["shell"]
    pts = [c["base"] + c["along"] * (c["L"] * 0.45) for c in cards]
    if sh.get("zmin") is not None:
        pts = [p for p in pts if p.z >= sh["zmin"]]
    T = sp.get("tunnel")
    if T:
        pts = [p for p in pts if not in_tunnel(p - UP * (sh["radius"] * 0.8), T)]
    # voxel-average the clump centres (fewer, bigger balls: a smoother hull than one ball per card)
    vc = sh.get("voxel", sh["radius"] * 0.9)
    cells = {}
    for p in pts:
        cells.setdefault((int(p.x // vc), int(p.y // vc), int(p.z // vc)), []).append(p)
    pts = [sum(v, Vector()) / len(v) for v in cells.values()]
    rr = random.Random(5)
    if len(pts) > sh.get("max_balls", 900):
        pts = rr.sample(pts, sh.get("max_balls", 900))
    scene = bpy.context.scene
    mb = bpy.data.metaballs.new("ShellMB")
    mb.resolution = mb.render_resolution = sh.get("res", 0.2)
    mb.threshold = sh.get("threshold", 0.6)
    for p in pts:
        e = mb.elements.new()
        e.co = p
        e.radius = sh["radius"] * sh.get("ball_k", 1.35) * (1 - 0.9 * min(0.5, sh.get("inset", 0.15)))
    ob = bpy.data.objects.new("ShellMB", mb)
    scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    base = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.metaballs.remove(mb)
    out = {}
    n0 = sum(len(p.vertices) - 2 for p in base.polygons)
    for tgt in targets:
        tmp = bpy.data.objects.new("ShellTmp", base.copy())
        scene.collection.objects.link(tmp)
        sm = tmp.modifiers.new("smooth", "SMOOTH")
        sm.factor, sm.iterations = 0.9, 8
        mod = tmp.modifiers.new("dec", "DECIMATE")
        mod.ratio = min(1.0, tgt / max(1, n0))
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
        me.calc_loop_triangles()
        co = np.zeros(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        nr = np.zeros(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("normal", nr)
        co, nr = co.reshape(-1, 3), nr.reshape(-1, 3)
        co = co - nr * min(sh.get("inset", 0.15), 0.06)          # deeper insets fold concave hulls
        tris = [tuple(t.vertices) for t in me.loop_triangles]
        out[tgt] = (co, tris, nr)
        me2 = tmp.data
        bpy.data.objects.remove(tmp)
        bpy.data.meshes.remove(me2)
        bpy.data.meshes.remove(me)
    bpy.data.meshes.remove(base)
    return out


def add_shell(md, shell, mat, sp):
    """Shell triangles into the LOD mesh: box-projected world-scale UVs on the repeating tile, smooth
    outward normals, a little branch-bend wind (it moves with the foliage)."""
    co, tris, nr = shell
    tile = sp["shell"].get("tile_m", 0.9)
    H = max(sp.get("height", 3.0), 0.5)
    base = len(md.co)
    for p, n in zip(co, nr):
        md.vert(Vector(p.tolist()), Vector(n.tolist()), (0.35 * min(1.0, max(0.0, p[2] / H)), 0.0, 0.0))
    # box projection per face, world scale: the leaf tile is random, so the seams between faces don't read
    for t in tris:
        a, b, c = (co[i] for i in t)
        fn = np.cross(b - a, c - a)
        ax = int(np.argmax(np.abs(fn)))
        uv = []
        for i in t:
            q = co[i]
            u, v = [(q[1], q[2]), (q[0], q[2]), (q[0], q[1])][ax]
            uv.append((float(u) / tile, float(v) / tile))
        md.face(tuple(base + i for i in t), uv, mat)


def moss_mat(md, sp, lod, rects, mi, crown_n):
    """Moss cushion: a low lumpy dome (opaque moss tile) + a fringe of scanned moss sprigs round the rim."""
    rr = random.Random(sp.get("_seed", 7))
    R, Hm = sp["radius"], sp["height"]
    rings, segs = lod["rings"], lod["segs"]
    tile = sp["shell"].get("tile_m", 0.25)
    ph = [rr.uniform(0, 6.28) for _ in range(4)]

    def h(x, y):
        r = math.hypot(x / R, y / (R * sp.get("oval", 0.8)))
        if r >= 1:
            return 0.0
        n = 1 + 0.25 * math.sin(3 * x + ph[0]) * math.cos(2.5 * y + ph[1]) + 0.15 * math.sin(7 * x + ph[2])
        return Hm * (1 - r * r) ** 0.6 * n
    idx = {}
    for i in range(rings + 1):
        rf = i / rings
        for j in range(segs if i else 1):
            a = 2 * math.pi * j / segs
            wob = 1 + 0.12 * math.sin(3 * a + ph[3]) if i == rings else 1.0
            x, y = math.cos(a) * R * rf * wob, math.sin(a) * R * sp.get("oval", 0.8) * rf * wob
            z = h(x, y) if i < rings else -0.01
            nrm = Vector((x * 0.6, y * 0.6, R)).normalized()
            idx[(i, j)] = md.vert(Vector((x, y, z)), nrm, (0.05 * rf, 0.0, 0.0))
    for i in range(rings):
        for j in range(segs):
            j2 = (j + 1) % segs
            if i == 0:
                vs = (idx[(0, 0)], idx[(1, j)], idx[(1, j2)])
            else:
                vs = (idx[(i, j)], idx[(i + 1, j)], idx[(i + 1, j2)], idx[(i, j2)])
            uv = [(md.co[v][0] / tile, md.co[v][1] / tile) for v in vs]
            md.face(vs, uv, mi["shell"])
    n = lod.get("fringe", 0)
    for k in range(n):
        a = 2 * math.pi * (k + rr.uniform(-0.3, 0.3)) / n
        rad = Vector((math.cos(a), math.sin(a) * sp.get("oval", 0.8), 0))
        base = rad * (R * 0.88)
        base.z = 0.0
        out = Vector((math.cos(a), math.sin(a), 0))
        c = dict(base=base, along=(out * 0.55 + UP).normalized(), across=Vector((-math.sin(a), math.cos(a), 0)),
                 L=sp["_rect_len"][0] * rr.uniform(0.8, 1.3), rect=0, bend=0.1, path=0.0, phase=rr.random(),
                 key=rr.random(), level=9)
        card_mesh(md, c, rects, 1, lod.get("fringe_scale", 1.0), 1.0, crown_n, mat=mi["leaf"])


def to_object(name, md, mats, roles, col):
    me = bpy.data.meshes.new(name)
    me.from_pydata(md.co, [], md.faces)
    me.uv_layers.new(name="UVMap")
    uv = np.array(md.uvs, np.float32).ravel()
    me.uv_layers[0].data.foreach_set("uv", uv)
    for r in roles:
        me.materials.append(mats[r])
    me.polygons.foreach_set("material_index", md.mat)
    me.polygons.foreach_set("use_smooth", [True] * len(md.faces))
    me.update()
    me.normals_split_custom_set_from_vertices(md.nrm)
    wa = me.attributes.new("_wind", "FLOAT_VECTOR", "POINT")
    wa.data.foreach_set("vector", np.array(md.wind, np.float32).ravel())
    na = me.attributes.new("bake_n", "FLOAT_VECTOR", "POINT")           # for the impostor bake only
    na.data.foreach_set("vector", np.array(md.nrm, np.float32).ravel())
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


# =============================================================================================
# ambient occlusion through the crown
def crown_ao(objects, leaf_mat_index=1, cell=None, strength=0.72, floor_k=0.35, weights=None):
    """Sky visibility per vertex through a voxel grid of leaf area (from the LOD0 cards, shared by
    every LOD): 16 rays per vertex, Beer-Lambert transmittance exp(-0.5 * LAD * coverage * ds),
    the ground occluding downward rays. Written as the "AO" colour attribute (exported COLOR_0)."""
    lod0 = objects[0]
    me = lod0.data
    co = np.zeros(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    lo, hi = co.min(0) - 0.2, co.max(0) + 0.2
    ext = hi - lo
    cell = cell or float(ext.max() / 30)
    dims = np.maximum(1, np.ceil(ext / cell).astype(int))
    grid = np.zeros(dims, np.float32)
    # leaf area per cell: every leaf face's area * alpha coverage, at its centre
    coverage = 0.4
    weights = weights or {leaf_mat_index: coverage}
    for poly in me.polygons:
        w = weights.get(poly.material_index)
        if w is None and len(me.materials) > 1:
            continue
        c = np.array(poly.center)
        ijk = np.clip(((c - lo) / cell).astype(int), 0, dims - 1)
        grid[tuple(ijk)] += poly.area * (coverage if w is None else w)
    lad = grid / cell ** 3                         # m2 leaf / m3
    sigma = 0.5 * lad
    # 16 directions, Fibonacci sphere, mostly upward
    n = 16
    dirs = []
    for i in range(n):
        z = 1 - (i + 0.5) / n * 1.3                # z from ~1 to -0.3
        r = math.sqrt(max(0, 1 - z * z))
        a = i * 2.39996
        dirs.append((r * math.cos(a), r * math.sin(a), z))
    dirs = np.array(dirs, np.float32)
    wts = 0.55 + 0.45 * dirs[:, 2]                 # the sky above is brighter than the horizon
    wts /= wts.sum()
    steps = int(np.ceil(ext.max() / cell)) + 2
    for ob in objects:
        me = ob.data
        v = np.zeros(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", v)
        v = v.reshape(-1, 3)
        vis = np.zeros(len(v), np.float32)
        for d, wt in zip(dirs, wts):
            tau = np.zeros(len(v), np.float32)
            t = np.arange(steps, dtype=np.float32)[:, None] * cell + cell * 0.75
            pos = v[None, :, :] + t[:, :, None] * d[None, None, :]
            ijk = ((pos - lo) / cell).astype(int)
            inside = np.all((ijk >= 0) & (ijk < dims), axis=2)
            ijk = np.clip(ijk, 0, dims - 1)
            s = sigma[ijk[..., 0], ijk[..., 1], ijk[..., 2]] * inside
            tau = s.sum(0) * cell
            T = np.exp(-tau)
            if d[2] < 0:                            # downward: the ground is there eventually
                T *= floor_k
            vis += wt * T
        ao = 1 - strength * (1 - np.clip(vis / max(vis.max(), 1e-3) * 1.1, 0, 1))
        # contact darkening at the base of trunks/stems
        ao *= 1 - 0.35 * np.exp(-np.maximum(v[:, 2], 0) / 0.5)
        ao = np.round(ao * 16) / 16
        attr = me.color_attributes.get("AO") or me.color_attributes.new("AO", "FLOAT_COLOR", "POINT")
        rgba = np.stack([ao, ao, ao, np.ones_like(ao)], 1).astype(np.float32)
        attr.data.foreach_set("color", rgba.ravel())
        me.color_attributes.active_color = attr
    return float(cell)


# =============================================================================================
# export
def export(sp_name, root_ob):
    from lib import common
    path = os.path.join(OUT, f"{sp_name}.gltf")
    common.export_gltf(root_ob, path, export_attributes=True)
    with open(path) as fh:
        doc = json.load(fh)
    for m in doc.get("materials", []):           # leaf cards: alpha test, both sides, no specular ext noise
        if "Leaf" in m.get("name", ""):
            m["alphaMode"] = "MASK"
            m["alphaCutoff"] = 0.5
            m["doubleSided"] = True
        m.pop("extensions", None)
    doc["extensionsUsed"] = [e for e in doc.get("extensionsUsed", []) if not e.startswith("KHR_materials_")]
    with open(path, "w") as fh:
        json.dump(doc, fh, separators=(",", ":"))
    size = os.path.getsize(path) + sum(os.path.getsize(os.path.join(OUT, b["uri"])) for b in doc.get("buffers", []))
    size_tex = sum(os.path.getsize(os.path.join(OUT, i["uri"])) for i in doc.get("images", []))
    return path, (size, size_tex), doc


# =============================================================================================
# impostor: hemi-octahedral N x N frames, albedo (x AO) and object-space normal, emission renders
def hemi_oct_dir(u, v):
    px, py = u * 2 - 1, v * 2 - 1
    x, y = (px + py) / 2, (px - py) / 2
    z = 1 - abs(x) - abs(y)
    return Vector((x, y, z)).normalized()


def _engine(scene, name):
    try:
        scene.render.engine = name
        return True
    except TypeError:
        return False


def _bake_material(src, mode):
    """Copy of src whose surface is emission (albedo x AO, or the stored normal) cut out by the
    same alpha (hard 0.5 threshold = the engine's alpha test)."""
    m = bpy.data.materials.new(f"{src.name}__{mode}")
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    sbsdf = next(n for n in src.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    img_src = sbsdf.inputs["Base Color"].links[0].from_node if sbsdf.inputs["Base Color"].is_linked else None
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = img_src.image if img_src else None
    img.interpolation = "Cubic"
    if mode == "albedo":
        ao = nt.nodes.new("ShaderNodeAttribute")
        ao.attribute_name = "AO"
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs["Factor"].default_value = 1.0
        nt.links.new(img.outputs["Color"], mul.inputs[6])
        nt.links.new(ao.outputs["Color"], mul.inputs[7])
        nt.links.new(mul.outputs[2], em.inputs["Color"])
    else:
        at = nt.nodes.new("ShaderNodeAttribute")
        at.attribute_name = "bake_n"
        vm = nt.nodes.new("ShaderNodeVectorMath")
        vm.operation = "MULTIPLY_ADD"
        vm.inputs[1].default_value = (0.5, 0.5, 0.5)
        vm.inputs[2].default_value = (0.5, 0.5, 0.5)
        nt.links.new(at.outputs["Vector"], vm.inputs[0])
        nt.links.new(vm.outputs[0], em.inputs["Color"])
    if sbsdf.inputs["Alpha"].is_linked:
        gt = nt.nodes.new("ShaderNodeMath")
        gt.operation = "GREATER_THAN"
        gt.inputs[1].default_value = 0.5
        nt.links.new(img.outputs["Alpha"], gt.inputs[0])
        nt.links.new(gt.outputs[0], mix.inputs[0])
    else:
        mix.inputs[0].default_value = 1.0
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    try:
        m.surface_render_method = "DITHERED"
    except (AttributeError, TypeError):
        pass
    m.use_backface_culling = False
    return m


def bake_impostor(sp_name, ob, frames=IMPOSTOR_FRAMES, px=None, ship=None):
    """ship: (albedo px, normal px) of the shipped WebP atlases (the 2k bake is kept as PNG)."""
    ship = ship or (TEX_SIZES["impostor_ship"], TEX_SIZES["impostor_ship"])
    px = px or TEX_SIZES["impostor"] // frames
    scene = bpy.context.scene
    _engine(scene, "BLENDER_EEVEE") or _engine(scene, "BLENDER_EEVEE_NEXT")
    scene.render.resolution_x = scene.render.resolution_y = px
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    try:
        scene.eevee.taa_render_samples = 16
    except AttributeError:
        pass
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.color_mode = "RGBA"
    world = bpy.data.worlds.new("ImpWorld")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Strength"].default_value = 0.0
    scene.world = world
    # bounding sphere around the bbox centre
    co = np.zeros(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    c = (co.min(0) + co.max(0)) / 2
    R = float(np.linalg.norm(co - c, axis=1).max()) * 1.02
    C = Vector(c.tolist())
    cam = bpy.data.objects.new("ImpCam", bpy.data.cameras.new("ImpCam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 2 * R
    cam.data.clip_start = 0.01
    cam.data.clip_end = 6 * R
    scene.collection.objects.link(cam)
    scene.camera = cam
    others = [o for o in scene.objects if o.type == "MESH" and o != ob]
    hidden = [(o, o.hide_render) for o in others]
    for o in others:
        o.hide_render = True
    orig = list(ob.data.materials)
    variants = {mode: [_bake_material(m, mode) for m in orig] for mode in ("albedo", "normal")}
    tmp = os.path.join(OUT, "_imp_tmp.exr")
    atlas = {mode: np.zeros((frames * px, frames * px, 4), np.float32) for mode in variants}
    for j in range(frames):
        for i in range(frames):
            d = hemi_oct_dir(i / (frames - 1), j / (frames - 1))
            right = UP.cross(d)
            right = right.normalized() if right.length > 1e-4 else Vector((1, 0, 0))
            upv = d.cross(right)
            cam.matrix_world = Matrix.Translation(C + d * 3 * R) @ Matrix((
                (right.x, upv.x, d.x, 0), (right.y, upv.y, d.y, 0), (right.z, upv.z, d.z, 0), (0, 0, 0, 1)))
            for mode, mlist in variants.items():
                for k, m in enumerate(mlist):
                    ob.data.materials[k] = m
                scene.render.filepath = tmp
                bpy.ops.render.render(write_still=True)
                atlas[mode][j * px:(j + 1) * px, i * px:(i + 1) * px] = _load(tmp)
    os.remove(tmp)
    for k, m in enumerate(orig):
        ob.data.materials[k] = m
    for o, h in hidden:
        o.hide_render = h
    for mlist in variants.values():
        for m in mlist:
            bpy.data.materials.remove(m)
    bpy.data.objects.remove(cam)
    # un-premultiply, dilate colour under the transparent texels, encode
    res = {}
    for mode, a in atlas.items():
        alpha = a[..., 3]
        rgb = np.where(alpha[..., None] > 1e-3, a[..., :3] / np.maximum(alpha[..., None], 1e-3), 0)
        rgb = _dilate(rgb, alpha > 0.5, iters=8)
        if mode == "albedo":
            rgb = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(np.clip(rgb, 0, None), 1 / 2.4) - 0.055)
        res[mode] = np.dstack([np.clip(rgb, 0, 1), alpha])
    out = {}
    for mode, a in res.items():
        for size, tag in ((TEX_SIZES["impostor"], "2k"), (ship[0] if mode == "albedo" else ship[1], "")):
            name = f"{sp_name}_impostor_{mode}{'_' + tag if tag else ''}"
            h = a.shape[0]
            im = bpy.data.images.new(name, h, h, alpha=True)
            im.colorspace_settings.name = "sRGB" if mode == "albedo" else "Non-Color"
            im.pixels.foreach_set(np.ascontiguousarray(a, np.float32).ravel())
            if size != h:
                im.scale(size, size)
            fmt, ext = ("PNG", "png") if tag else ("WEBP", "webp")
            im.filepath_raw = os.path.join(OUT, f"{name}.{ext}")
            im.file_format = fmt
            try:
                im.save(quality=90)
            except TypeError:
                im.save()
            bpy.data.images.remove(im)
        out[mode] = f"{sp_name}_impostor_{mode}.webp"
    # Blender (x, y, z) -> glTF/three (x, z, -y)
    return dict(frames=frames, frame_px=ship[0] // frames, atlas_px=ship[0], normal_px=ship[1],
                center=[float(c[0]), float(c[2]), float(-c[1])], radius=R, mapping="hemi-octahedral",
                albedo=out["albedo"], normal=out["normal"],
                normal_space="object, Blender Z-up: n_three = (x, z, -y)", baked_px=TEX_SIZES["impostor"])


# =============================================================================================
# previews
def preview_sheet(sp_name, objects, path, tile=512):
    scene = bpy.context.scene
    _engine(scene, "BLENDER_EEVEE") or _engine(scene, "BLENDER_EEVEE_NEXT")
    scene.render.resolution_x = scene.render.resolution_y = tile
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    try:
        scene.eevee.taa_render_samples = 32
    except AttributeError:
        pass
    world = bpy.data.worlds.new("PrevWorld")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.55, 0.65, 0.8, 1)
    bg.inputs["Strength"].default_value = 0.9
    scene.world = world
    try:
        scene.view_settings.view_transform = "AgX"
    except TypeError:
        pass
    sun = bpy.data.objects.new("PrevSun", bpy.data.lights.new("PrevSun", "SUN"))
    sun.data.energy = 3.5
    sun.data.angle = 0.05
    sun.rotation_euler = Vector((-0.45, 0.35, -0.82)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(sun)
    fm = bpy.data.meshes.new("PrevFloor")
    s = 200
    fm.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    floor = bpy.data.objects.new("PrevFloor", fm)
    mat = bpy.data.materials.new("PrevFloor")
    mat.use_nodes = True
    next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.16, 0.2, 0.1, 1)
    fm.materials.append(mat)
    scene.collection.objects.link(floor)
    # AO into the preview materials (exported already; three.js multiplies COLOR_0 itself)
    for m in {m for o in objects for m in o.data.materials}:
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        if not bsdf.inputs["Base Color"].is_linked:
            continue
        src = bsdf.inputs["Base Color"].links[0].from_socket
        at = nt.nodes.new("ShaderNodeAttribute")
        at.attribute_name = "AO"
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs["Factor"].default_value = 1.0
        nt.links.new(src, mul.inputs[6])
        nt.links.new(at.outputs["Color"], mul.inputs[7])
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        if bsdf.inputs["Alpha"].is_linked:          # hard cut-out like the engine's alphaTest 0.5
            asrc = bsdf.inputs["Alpha"].links[0].from_socket
            gt = nt.nodes.new("ShaderNodeMath")
            gt.operation = "GREATER_THAN"
            gt.inputs[1].default_value = 0.5
            nt.links.new(asrc, gt.inputs[0])
            nt.links.new(gt.outputs[0], bsdf.inputs["Alpha"])
    cam = bpy.data.objects.new("PrevCam", bpy.data.cameras.new("PrevCam"))
    cam.data.lens = 50
    scene.collection.objects.link(cam)
    scene.camera = cam
    co = np.zeros(len(objects[0].data.vertices) * 3, np.float32)
    objects[0].data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    lo, hi = co.min(0), co.max(0)
    centre = Vector(((lo + hi) / 2).tolist())
    extent = float(np.linalg.norm(hi - lo))
    tiles = []
    tmp = path + ".tile.png"
    views = [(o, (0.25, -1, 0.18), 1.4) for o in objects] + [(objects[0], (0.6, -1, 0.05), 0.4)]
    for ob_show, d, dist_k in views:
        for o in objects:
            o.hide_render = o != ob_show
        d = Vector(d).normalized()
        look = centre if dist_k >= 1 else centre + Vector((0, 0, (hi[2] - lo[2]) * 0.1))
        cam.location = look + d * extent * dist_k
        cam.rotation_euler = (look - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.clip_end = extent * 20
        scene.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        tiles.append(_load(tmp))
    os.remove(tmp)
    for o in objects:
        o.hide_render = False
    row = np.hstack(tiles)
    _save(row, path, "sheet")
    for o in (sun, floor, cam):
        bpy.data.objects.remove(o)


# =============================================================================================
def variant_params(sp, v, rng):
    """Variant v (1 = the base) of a kit species: same species, its own skeleton (seed) and a jittered
    crown envelope; height stays within ~4% of the base so the base's impostor still fits."""
    P = copy.deepcopy(sp)
    P["_variant"] = v
    if P.get("variant_dims"):
        P["radius"], P["height"] = P["variant_dims"][(v - 1) % len(P["variant_dims"])]
    if v == 1 or "envelope" not in P:
        return P
    (cx, cy, cz), (rx, ry, rz) = P["envelope"]
    j = sp.get("variant_jitter", 0.1)
    P["envelope"] = ((cx + rng.uniform(-0.06, 0.06) * rx, cy + rng.uniform(-0.06, 0.06) * ry, cz * rng.uniform(0.97, 1.02)),
                     (rx * rng.uniform(1 - j, 1 + j), ry * rng.uniform(1 - j, 1 + j), rz * rng.uniform(1 - j * 0.5, 1 + j * 0.3)))
    if P.get("levels"):
        P["levels"][0]["kids"] = max(3, int(round(P["levels"][0]["kids"] * rng.uniform(0.85, 1.15))))
    return P


def collider_info(sp, root, objs):
    """Collision hints for the runtime, three.js frame (y up), metres."""
    k = sp["kind"]
    co = np.zeros(len(objs[0].data.vertices) * 3, np.float32)
    objs[0].data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    if k in ("broadleaf", "conifer"):
        r = root.rad[0] if root is not None else 0.3
        if root is not None:                      # radius at breast height (1.3 m)
            H = root.pts[-1].z
            i = min(len(root.rad) - 1, int(round(1.3 / max(H, 1e-3) * (len(root.rad) - 1))))
            r = root.rad[i]
        return dict(type="capsule", radius=round(float(r), 3), height=round(float(min(6.0, sp.get("crown_base", 4.0))), 2),
                    dbh_m=round(float(2 * r), 2))
    if k in ("shrub", "thicket"):
        lo, hi = co.min(0), co.max(0)
        box = dict(type="box", min=[round(float(lo[0]) * 0.8, 2), 0.0, round(float(-hi[1]) * 0.8, 2)],
                   max=[round(float(hi[0]) * 0.8, 2), round(float(hi[2]) * 0.9, 2), round(float(-lo[1]) * 0.8, 2)],
                   soft=True, note="thicket rule: blocks movement, sight lambda from the community map")
        if sp.get("tunnel"):
            T = sp["tunnel"]
            box["tunnel"] = dict(axis="x", width=T["w"], height=T["h"], bend=T.get("bend", 0.0), length=T["len"],
                                 note="corridor centre z_three = -bend*sin(pi*(x/len + 0.5)); crouch height")
        return box
    return None


def build_species(sp_name, seed, impostor=True, preview=True, base_info=None):
    from lib import common
    t0 = time.time()
    ALL = all_species()
    base_id, v = sp_name, 1
    if sp_name not in ALL and "_" in sp_name and sp_name.rsplit("_", 1)[1].isdigit():
        base_id, v = sp_name.rsplit("_", 1)[0], int(sp_name.rsplit("_", 1)[1])
    sp0 = ALL[base_id]
    if sp0["kind"] in ("log", "stump", "rock"):
        import deadwood
        return deadwood.build(sp_name, base_id, v, sp0, seed, preview)
    seed = seed + 101 * (v - 1) + sp0.get("seed_off", 0)
    rng = random.Random(seed)
    sp = variant_params(sp0, v, random.Random(seed + 1))
    sp["_seed"] = seed
    col = bpy.data.collections.new(node_name(sp_name))
    bpy.context.scene.collection.children.link(col)
    tex = prep_textures(base_id, sp)
    mats = make_materials(base_id, sp, tex)
    leaf_meta = None
    if sp.get("leaf", {}).get("atlas"):             # atlas rects, real card sizes, mean colours
        info_a = leaf_atlas(sp["leaf"]["atlas"])
        names = sp["leaf"]["cards"]
        sp["leaf"]["rects"] = [info_a["rects"][n] for n in names]
        sp["_rect_len"] = [info_a["cards"][n]["size_m"][1] for n in names]
        sp["_rect_w"] = sp["leaf"].get("weights") or [1.0] * len(names)
        if sp.get("bark_cards"):
            sp["bark_cards"]["rect"] = names.index(sp["bark_cards"]["card"])
        leaf_meta = {n: info_a["cards"][n]["mean_srgb"] for n in names}
    sp["_roles"] = [r for r in ("bark", "leaf", "shell") if r in mats]
    root = None
    cards = []
    if sp["kind"] == "conifer":
        root = conifer(sp, rng)
        set_paths(root)
        cards = conifer_cards(root, sp, rng) if sp.get("leaf") else []
    elif sp["kind"] in ("broadleaf", "shrub", "thicket"):
        root = deciduous(sp, rng)
        set_paths(root)
        cards = deciduous_cards(root, sp, rng)
    if cards:                                       # 'outer': how far out in the crown (thinning keeps these)
        if sp["kind"] == "conifer":
            for c in cards:
                p = c["base"]
                rmax = sp["branch_len"] * (1 - max(0, (p.z - sp["crown_base"])) / (sp["height"] - sp["crown_base"])) + 0.4
                c["outer"] = min(1, Vector((p.x, p.y, 0)).length / max(rmax, 0.3))
        else:
            cc, rr = Vector(sp["envelope"][0]), Vector(sp["envelope"][1])
            for c in cards:
                q = c["base"] - cc
                c["outer"] = min(1, math.sqrt((q.x / rr.x) ** 2 + (q.y / rr.y) ** 2 + (q.z / rr.z) ** 2))
    if sp.get("bark_cards") and root is not None:
        sp["_bark_cards"] = bark_strip_cards(root, sp, random.Random(seed + 3))
    if sp.get("shell") and sp["kind"] != "mat":
        sp["_shells"] = make_shells(sp, cards, sorted({l["shell"] for l in sp["lods"] if l.get("shell")}))
    root_ob = bpy.data.objects.new(node_name(sp_name), None)
    col.objects.link(root_ob)
    objs, lod_info = [], []
    for li, lod in enumerate(sp["lods"]):
        md, roles = build_lod(base_id, sp, root, cards, lod, li, mats, rng)
        ob = to_object(f"{node_name(sp_name)}_LOD{li}", md, mats, roles, col)
        ob.parent = root_ob
        objs.append(ob)
        by = {r: sum(len(f) - 2 for f, m in zip(md.faces, md.mat) if m == i) for i, r in enumerate(roles)}
        lod_info.append(dict(name=ob.name, tris=md.tris(), verts=len(md.co), wood_tris=by.get("bark", 0),
                             leaf_tris=by.get("leaf", 0), shell_tris=by.get("shell", 0),
                             draw_calls=sum(1 for r in roles if by.get(r))))
    mi = {r: i for i, r in enumerate(sp["_roles"])}
    w = {mi["leaf"]: 0.4} if "leaf" in mi else {}
    if "shell" in mi:
        w[mi["shell"]] = sp["shell"].get("ao_k", 1.2)
    cell = crown_ao(objs, leaf_mat_index=mi.get("leaf", 0), weights=w or None, strength=sp.get("ao_strength", 0.72))
    path, (size, size_tex), doc = export(sp_name, root_ob)
    info = dict(title=sp["title"], gltf=os.path.basename(path), bytes_geometry=size, bytes_textures=size_tex, lods=lod_info,
                lod_dist=sp["lod_dist"], cards=len(cards), seed=seed, ao_cell_m=round(cell, 3),
                height_m=round(max(v_.co.z for v_ in objs[0].data.vertices), 2),
                textures={k: [os.path.basename(p_[0]), bpy.data.images[os.path.splitext(os.path.basename(p_[0]))[0]].size[0]]
                          for k, p_ in tex.items()})
    for k in ("kind", "group", "latin", "community", "reference", "palette", "notes"):
        if k in sp0:
            info[k] = sp0[k]
    info["species"] = base_id
    info["variant"] = v
    info["variants"] = sp0.get("variants", 1)
    if leaf_meta:
        info["leaf_mean_srgb"] = leaf_meta
    col_i = collider_info(sp, root, objs)
    if col_i:
        info["collider"] = col_i
    info["sources"] = sources_of(sp)
    print(f"VEG {sp_name}: " + "  ".join(f"LOD{i} {l['tris']} tris" for i, l in enumerate(lod_info)) + f"  {size / 1024:.0f} KB")
    if impostor and sp.get("impostor", sp["kind"] not in ("clump", "mat")):
        if v > 1 and base_info and base_info.get("impostor"):
            info["impostor"] = dict(base_info["impostor"], shared_from=base_id)
        else:
            t1 = time.time()
            info["impostor"] = bake_impostor(sp_name, objs[0], ship=sp.get("impostor_px", (1024, 512)))
            info["impostor"]["bake_s"] = round(time.time() - t1, 1)
    if preview:
        os.makedirs(PREVIEWS, exist_ok=True)
        preview_sheet(sp_name, objs, os.path.join(PREVIEWS, f"{sp_name}.png"))
        info["preview"] = f"previews/{sp_name}.png"
    info["build_s"] = round(time.time() - t0, 1)
    return info


def sources_of(sp):
    """Poly Haven (CC0) scans a species uses (credits)."""
    out = []
    if sp.get("bark"):
        out.append(sp["bark"]["src"])
    lf = sp.get("leaf") or {}
    if lf.get("atlas"):
        out.append("island_tree_02 (leaf grain)")
        if lf["atlas"] == "br_ground":
            out.append("moss_01")
    elif lf.get("src"):
        out.append(lf["src"])
    if sp.get("shell", {}).get("tile") == "moss_tile":
        out.append("moss_01")
    return sorted(set(out))


def write_manifest(man_path, manifest):
    manifest["generated"] = time.strftime("%Y-%m-%d %H:%M")
    with open(man_path + ".part", "w") as fh:
        json.dump(manifest, fh, indent=1)
    os.replace(man_path + ".part", man_path)         # atomic: the runtime may be reading it


def expand(ids):
    """Species ids -> build list with every variant (tulip_poplar -> tulip_poplar, _2, _3)."""
    ALL = all_species()
    out = []
    for sid in ids:
        sp = ALL.get(sid)
        if sp is None:
            out.append(sid)                     # an explicit variant id
            continue
        out.append(sid)
        out += [f"{sid}_{v}" for v in range(2, sp.get("variants", 1) + 1)]
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--species", default=None, help="comma list (spike: fir,ash,shrub,fern; kit ids; variant ids)")
    ap.add_argument("--kit", default=None, help="build every species of a kit (blue_ridge)")
    ap.add_argument("--no-variants", action="store_true")
    ap.add_argument("--no-impostor", action="store_true")
    ap.add_argument("--no-preview", action="store_true")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args(argv)
    import slots
    slots.acquire("asset", 4)
    os.makedirs(OUT, exist_ok=True)
    if a.kit:
        ids = list(kits()[a.kit])
        if a.species:
            ids = [i for i in ids if i in a.species.split(",")]
    else:
        ids = (a.species or ",".join(SPECIES)).split(",")
    if not a.no_variants:
        ids = expand(ids)
    man_path = os.path.join(OUT, "veg.json")
    manifest = json.load(open(man_path)) if os.path.exists(man_path) else {"species": {}}
    failed = []
    for name in ids:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        _ATLAS.clear()
        base = name.rsplit("_", 1)[0] if name not in all_species() else None
        try:
            info = build_species(name, a.seed, not a.no_impostor, not a.no_preview,
                                 base_info=manifest["species"].get(base) if base else None)
        except Exception:
            import traceback
            traceback.print_exc()
            failed.append(name)
            continue
        manifest["species"][name] = info
        if a.kit or info.get("group"):
            update_kit(manifest, a.kit or "blue_ridge")
        write_manifest(man_path, manifest)
    print("DONE", man_path, "FAILED " + ",".join(failed) if failed else "")


def update_kit(manifest, kit):
    """Top-level "kits" section: per kit, species -> its variant ids and the shared texture sets."""
    K = kits()[kit]
    ent = manifest.setdefault("kits", {}).setdefault(kit, {})
    ent["species"] = {sid: [k for k in [sid] + [f"{sid}_{v}" for v in range(2, sp.get("variants", 1) + 1)]
                            if k in manifest["species"]] for sid, sp in K.items()}
    ent["groups"] = {}
    for sid, sp in K.items():
        ent["groups"].setdefault(sp.get("group", "other"), []).append(sid)
    ent["doc"] = "design/wilderness/blue_ridge/plants.md"


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        print("FAILED")
        sys.exit(1)
