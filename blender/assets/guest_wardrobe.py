"""Guest wardrobe: a fitted run of six framed, reeded pale-oak doors.

Construction (like bespoke joinery, e.g. a white-oiled oak reeded wardrobe): a 25 mm oak
carcass (sides down to the floor, top, a bottom rail) frames six inset doors with 4 mm
reveals all round and a dark interior behind them; the door faces sit 2 mm behind the
carcass edges (a shadow line). Each door is a stile-and-rail frame (eased edges, so the
joints read) around a recessed panel of real modelled reeds at ~25 mm pitch (shallow
half-rounds with a narrow fillet between them). The reeds' light and shade (the cavity into
each valley) is painted into the wardrobe's own pale-oak texture, mip-filtered, because the
room's soft probe light alone hardly separates them (see soften_normals). Meeting pairs carry
long T-bar pulls (satin black, or bronze) on round posts and roses; a recessed black plinth
between the sides. Faces -Y; origin is the floor centre.

The middle pair is a hiding spot (prompts/interactivity.md `hide`): the carcass is hollow (a black
lining at the back, partitions between the bays, a rail with a coat at either end of the middle
bay), the middle doors hang from empties on their hinge lines; E swings them open, the player
steps in and they pull to, leaving a crack at the meeting stiles to peek through."""
import importlib
import math
import os
import sys

import bmesh
import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common
textures = guest_mats.textures
import ix_common  # noqa: E402  (hiding spot, prompts/interactivity.md)

importlib.reload(ix_common)

NAME = "GuestWardrobe"

P = dict(name=NAME, width=3.6, depth=0.62, height=2.7, plinth_h=0.10, doors=6,
         slat=0.0240,          # reed width (the half-round's chord)
         slat_gap=0.0016,      # flat fillet between reeds (pitch = slat + slat_gap, ~25.6 mm)
         reed_depth=0.0055,    # reed height above the fillets
         reveal=0.004,         # gaps between doors and to the carcass
         carcass_t=0.025,      # sides / top thickness
         stile=0.052, rail_top=0.068, rail_bottom=0.085,
         pull_len=0.56, pull_r=0.008, pull_z=1.12,
         reed_normal=0.5,      # how much of the reeds' curvature their shading normals keep
         pull_finish="black",  # "black" (satin black: reads on the pale oak) or "bronze" (the suite's hardware)
         hide=(2, 3),          # the door pair that is a hiding spot (None: a solid interior)
         coats=[(-0.42, "M_Guest_Coat_Sage", (0.10, 0.13, 0.085), 1.0),
                (0.40, "M_Guest_Coat_Stone", (0.36, 0.33, 0.28), 0.9)])


# T_Guest_Oak_BaseColor is a Poly Haven oak veneer scan (blender/tools/polyhaven_textures.py),
# rotated so its grain runs along u, and whose 1024 image is meant to cover OAK_TILE metres; the
# guest_* furniture maps it through grain_uv so the grain follows each board.
OAK_TILE = 1.5
OAK_GRAIN_ON_V = False         # the oak veneer scan is rotated: grain along u
# the wardrobe's own paler, white-oiled version of that scan (grain along u as well)
# The texture is an atlas: v in [0, 1/3) holds REEDS_PER_TILE reeds' worth of grain with each
# reed's cavity (the darkening into the valleys) painted in, so the reeding reads under the
# room's soft probe light, where a normal map would do nothing (props take their diffuse light
# from the room's SH probe through the geometric normal); v in [FLAT_V0, FLAT_V1] is plain
# grain for the frames and carcass. u runs along the grain: PALE_TILE metres per tile.
PALE_TILE = 1.0
PALE_TEX = "T_GuestWardrobe_OakPale_BaseColor"
PALE_MEAN = (0.63, 0.52, 0.375)     # linear mean colour: white-oiled oak (sRGB ~ 207, 191, 165)
REEDS_PER_TILE = 8                  # reeds in the atlas's reed band
REED_V = 1.0 / 3.0                  # top of the reed band
FLAT_V0, FLAT_V1 = 0.355, 0.985     # the plain band (0.63 of a tile: the 0.62 m sides fit)


def grain_uv(ob, tile=OAK_TILE, along=None, grain_on_v=OAK_GRAIN_ON_V, offset=(0.0, 0.0)):
    """Box projection with the grain along `along` ("x"/"y"/"z") wherever that axis lies
    in the face's plane, else along the mesh's longest axis available on the face (like
    common.box_uv). grain_on_v puts the grain on v (for textures scanned that way)."""
    me = ob.data
    dims = [max(v.co[a] for v in me.vertices) - min(v.co[a] for v in me.vertices) for a in range(3)]
    ga = "xyz".index(along) if along else None
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        n = [abs(c) for c in poly.normal]
        na = n.index(max(n))
        a, b = [i for i in range(3) if i != na]      # a = grain axis
        if b == ga or (ga not in (a, b) and dims[b] > dims[a]):
            a, b = b, a
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            g, c = co[a] / tile + offset[0], co[b] / tile + offset[1]
            uv.data[li].uv = (c, g) if grain_on_v else (g, c)


def fix_oak(root, skip=()):
    """grain_uv on every pale-oak mesh under `root` (names in `skip` keep their UVs)."""
    for ob in root.children_recursive:
        if (ob.type == "MESH" and ob.data.materials and ob.data.materials[0] is not None
                and ob.data.materials[0].name == "M_Oak_Light" and ob.name not in skip):
            grain_uv(ob)


# ------------------------------------------------------------------ material
def _pale_texture():
    """The guest oak scan, re-toned to a paler, less orange white-oiled oak (kept the figure,
    softened the contrast a touch). Made once; regenerated only when the file is missing."""
    path = os.path.join(textures.TEX_DIR, PALE_TEX + ".png")
    if os.path.exists(path):
        return path
    src = bpy.data.images.load(os.path.join(textures.TEX_DIR, "T_Guest_Oak_BaseColor.png"))
    w, h = src.size
    px = np.zeros(w * h * 4, np.float32)
    src.pixels.foreach_get(px)
    bpy.data.images.remove(src)
    s = px.reshape(h, w, 4)[::-1, :, :3].astype(np.float64)        # top-down, sRGB values
    lin = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722])
    mean_lin = lin.reshape(-1, 3).mean(0)
    mean_lum = lum.mean()
    # figure (light/dark) at 65% contrast (a white oil mutes it); local hue variation halved
    fig = (lum / mean_lum) ** 0.65
    hue = ((lin / lum[..., None]) / (mean_lin / mean_lum)) ** 0.5
    out = np.array(PALE_MEAN) * fig[..., None] * hue
    # reed band (image rows are top-down: v = 1 - (row + 0.5) / h): the cavity falling into each
    # valley. A smooth, nearly sinusoidal profile (a raised cosine squared: the fundamental plus a
    # quarter-strength 2nd harmonic): a crisp dark valley line has strong high harmonics, which
    # mip-mapping keeps until the reeds are ~4 px apart on screen and which then beat against the
    # pixel grid into moire arcs across the doors
    v = 1.0 - (np.arange(h) + 0.5) / h
    t = (v / REED_V) * REEDS_PER_TILE
    cav = 1.0 - 0.34 * ((1.0 + np.cos(2 * np.pi * t)) / 2) ** 2
    band = v < REED_V + 0.006
    shade = np.where(band, cav, 1.0)
    out = out * shade[:, None, None]
    textures._save(PALE_TEX, textures._to_srgb(out))
    return path


def oak_pale():
    """Pale white-oiled oak, matte (no coat: stays a plain MeshStandardMaterial)."""
    m = common.pbr_material("M_GuestWardrobe_OakPale", PALE_MEAN, roughness=0.62)
    common.set_base_color_map(m, textures.load(_pale_texture()))
    return m


# ------------------------------------------------------------------ geometry
def _box(bm, lo, hi):
    """Axis-aligned box from corner lo to corner hi into bm."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    v = [bm.verts.new(c) for c in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                   (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([v[i] for i in f])


def _part(owner, name, boxes, mat, along, bevel=0.0018, segments=1, tile=PALE_TILE, seed=0):
    """One mesh object of several boxes with real (modelled) eased edges, flat shaded, grain
    along `along`. The bevel is geometry rather than a modifier so the vertex AO has vertices
    on each face: with only a box's 8 corners, a door frame's AO came from where it touches its
    neighbours and darkened every face. UVs: each box is mapped on its own into the atlas's
    plain band (grain along u, from a random start, so neighbouring boards differ)."""
    col, root, n = owner
    rng = np.random.default_rng(seed)
    ga = "xyz".index(along)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    for lo, hi in boxes:
        one = bmesh.new()
        _box(one, lo, hi)
        if bevel:
            bmesh.ops.bevel(one, geom=list(one.edges) + list(one.verts), offset=bevel, offset_type="OFFSET",
                            segments=segments, profile=0.5, affect="EDGES", clamp_overlap=True)
        ext = [hi[i] - lo[i] for i in range(3)]
        du = rng.uniform(0, 1)
        luv = one.loops.layers.uv.verify()
        for f in one.faces:
            nrm = [abs(c) for c in f.normal]
            na = nrm.index(max(nrm))
            a, b = [i for i in range(3) if i != na]
            if b == ga or (ga not in (a, b) and ext[b] > ext[a]):
                a, b = b, a                               # a = along the grain
            room = max(0.0, (FLAT_V1 - FLAT_V0) - ext[b] / tile)
            dv = FLAT_V0 + rng.uniform(0, room)
            for lp in f.loops:
                co = lp.vert.co
                lp[luv].uv = ((co[a] - lo[a]) / tile + du, dv + min(ext[b], (FLAT_V1 - FLAT_V0) * tile) / tile
                              * ((co[b] - lo[b]) / max(ext[b], 1e-6)))
        me = bpy.data.meshes.new("_tmp")
        one.to_mesh(me)
        one.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    ob = common.mesh_object(f"{n}_{name}", bm, col, mat, root, smooth=False)
    return ob


def reed_field(bm, x0, x1, z0, z1, y_crown, pitch_target, gap, depth, seg=5, band=0.045, uoff=0.0,
               tile=PALE_TILE):
    """Reeds running vertically across [x0, x1] (their crowns at y_crown, toward -Y), from z0 to
    z1: shallow circular half-rounds separated by flat fillets `depth` behind the crowns, cut
    into three rows so the contact shadow at the rails stays within `band` of them. UVs: grain
    along z (u); across, each reed spans one reed of the atlas's reed band (its cavity)."""
    n = max(1, round((x1 - x0) / pitch_target))
    pitch = (x1 - x0) / n
    c = pitch - gap                                   # reed chord
    R = (c * c / 4 + depth * depth) / (2 * depth)     # arc radius
    half = math.asin(min(1.0, (c / 2) / R))
    y_fil = y_crown + depth
    zs = [z0, z0 + band, z1 - band, z1]
    uv = bm.loops.layers.uv.verify()
    per = REEDS_PER_TILE
    vstep = REED_V / per

    # a block of `per` reeds is one board: its grain runs on across them (each block of a door
    # starts at its own place along the grain); between blocks the UVs jump (a seam in a valley)
    def uo_of(k):
        return uoff + 0.29 * (k // per)

    # one continuous strip across the field (welded valleys: a valley vertex's normal faces out,
    # not into the next reed, so its baked AO stays open); columns carry the UV they take as
    # the right edge of the face to their left (vl, ul) and as the left edge of the next (vr, ur)
    cols = [(x0 - 0.002, y_fil, 0.0, 0.0, uo_of(0), uo_of(0))]       # tucked under the stile
    v_prev, u_prev = 0.0, uo_of(0)
    for k in range(n):
        xm = x0 + (k + 0.5) * pitch
        j0 = (k % per) * vstep
        for j in range(seg + 1):
            a = -half + 2 * half * j / seg
            x, y = xm + R * math.sin(a), y_fil - (R * math.cos(a) - (R - depth))
            v = j0 + vstep * (0.5 + 0.5 * math.sin(a) / math.sin(half))
            if j == 0:
                cols.append((x, y, v_prev, v, u_prev, uo_of(k)))
            else:
                cols.append((x, y, v, v, uo_of(k), uo_of(k)))
        v_prev, u_prev = j0 + vstep, uo_of(k)
    cols.append((x1 + 0.002, y_fil, v_prev, v_prev, u_prev, u_prev))
    grid = [[bm.verts.new((x, y, z)) for z in zs] for x, y, *_ in cols]
    for i in range(len(cols) - 1):
        _, _, _, vr, _, ur = cols[i]
        _, _, vl, _, ul, _ = cols[i + 1]
        for r in range(len(zs) - 1):
            f = bm.faces.new((grid[i][r], grid[i + 1][r], grid[i + 1][r + 1], grid[i][r + 1]))
            for lp, (vv, uu, zi) in zip(f.loops, ((vr, ur, r), (vl, ul, r), (vl, ul, r + 1), (vr, ur, r + 1))):
                lp[uv].uv = (zs[zi] / tile + uu, vv)


def soften_normals(ob, keep):
    """Custom normals between the reeds' true normals (keep = 1) and the panel's -Y (keep = 0).
    At full curvature every reed alternated light and dark from the probe light and, worse,
    from the vertex AO (a valley vertex's tilted normal faces the next reed, so it bakes dark):
    at 3-4 px per reed (4 m away) that per-vertex stripe aliased into broad moire arcs. The
    reeding's light and shade is in the mip-mapped texture instead; the geometry keeps the
    real relief (silhouettes, parallax) and a gentle share of the curvature."""
    from mathutils import Vector
    me = ob.data
    flat = Vector((0.0, -1.0, 0.0))
    nrm = []
    for loop in me.loops:
        v = me.vertices[loop.vertex_index].normal
        nrm.append(tuple((v * keep + flat * (1.0 - keep)).normalized()))
    me.normals_split_custom_set(nrm)


def lathe(bm, sections, seg, axis, centre, inner):
    """Revolve profile sections [(r, h), ...] around `axis` ("y" or "z") through `centre`.
    Each section is its own smooth strip (a crisp crease between sections); r = 0 points
    close the strip with a fan. Faces are wound to face away from the solid's core, the axis
    between h = inner[0] and inner[1]."""
    from mathutils import Vector
    cx, cy, cz = centre
    ax = Vector((0, 0, 1)) if axis == "z" else Vector((0, 1, 0))
    c0 = Vector(centre)
    for prof in sections:
        rings = []
        for r, h in prof:
            ring = []
            for i in range(1 if r < 1e-9 else seg):
                a = 2 * math.pi * i / seg
                u, w = r * math.cos(a), r * math.sin(a)
                co = (cx + u, cy + w, cz + h) if axis == "z" else (cx + u, cy + h, cz + w)
                ring.append(bm.verts.new(co))
            rings.append(ring)
        for ra, rb in zip(rings, rings[1:]):
            for i in range(seg):
                j = (i + 1) % seg
                if len(ra) == 1:
                    q = (ra[0], rb[i], rb[j])
                elif len(rb) == 1:
                    q = (ra[i], rb[0], ra[j])
                else:
                    q = (ra[i], rb[i], rb[j], ra[j])
                try:
                    f = bm.faces.new(q)
                except ValueError:
                    continue
                f.normal_update()
                fc = f.calc_center_median()
                h = min(max((fc - c0).dot(ax), min(inner)), max(inner))
                if f.normal.dot(fc - (c0 + ax * h)) < 0:
                    f.normal_flip()


def _dome(r, h0, h1, k=3):
    """Quarter-round end of radius r from the barrel (at h0) toward h1 (the tip)."""
    sgn = 1 if h1 > h0 else -1
    return [(r * math.cos(0.5 * math.pi * i / k), h0 + sgn * r * math.sin(0.5 * math.pi * i / k)) for i in range(k + 1)]


def pull_bmesh(px, yface, zc, L, r, span, proj):
    """A T-bar pull: a round bar with domed ends on two posts, each seated on a rose with an
    eased edge. Bar along z at x = px, `proj` in front of the door face yface (toward -Y)."""
    bm = bmesh.new()
    yb = yface - proj
    lo, hi = zc - L / 2 + r, zc + L / 2 - r
    bar = list(reversed(_dome(r, 0.0, -r)))[:-1] + [(r, 0.0), (r, hi - lo)] + _dome(r, hi - lo, hi - lo + r)[1:]
    # (sections: dome-barrel-dome as one smooth strip: the dome meets the barrel tangentially)
    lathe(bm, [bar], 14, "z", (px, yb, lo), (0.0, hi - lo))
    for s in (-1, 1):
        z = zc + s * span / 2
        # post from the rose to the bar (its ends are buried in both)
        lathe(bm, [[(0.0052, 0.0), (0.0052, -(proj - r * 0.5))]], 10, "y", (px, yface - 0.003, z), (0.0, -proj))
        # rose: a 3.5 mm disc, eased front edge, front face fan
        rr = 0.0110
        lathe(bm, [[(rr, 0.0), (rr, -0.0025)], [(rr, -0.0025), (rr - 0.0012, -0.0037)],
                   [(rr - 0.0012, -0.0037), (0.0, -0.0037)]], 14, "y", (px, yface + 0.0005, z), (-0.0018, -0.0018))
    return bm


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    oak, brass, black = oak_pale(), guest_mats.brass(), guest_mats.black()
    own = (col, root, n)
    W, D, H, ph = p["width"], p["depth"], p["height"], p["plinth_h"]
    nd, g, t = p["doors"], p["reveal"], p["carcass_t"]
    y0, y1 = -D / 2, D / 2                          # carcass front / back
    dt = 0.022                                      # door thickness
    yf = y0 + 0.002                                 # door face plane (2 mm behind the carcass edge)
    yb = yf + dt                                    # door back
    zb = ph + 0.022                                 # top of the bottom rail

    # ---- carcass: sides to the floor, top, bottom rail; oak, grain up the sides
    if p["hide"]:
        # (one part per side: a part is one collider box, and one round both would fill the hollow)
        _part(own, "SideL", [((-W / 2, y0, 0), (-W / 2 + t, y1, H - t))], oak, "z", bevel=0.0022, segments=2)
        _part(own, "SideR", [((W / 2 - t, y0, 0), (W / 2, y1, H - t))], oak, "z", bevel=0.0022, segments=2, seed=7)
    else:
        _part(own, "Sides", [((-W / 2, y0, 0), (-W / 2 + t, y1, H - t)),
                             ((W / 2 - t, y0, 0), (W / 2, y1, H - t))], oak, "z", bevel=0.0022, segments=2)
    _part(own, "Top", [((-W / 2, y0, H - t), (W / 2, y1, H))], oak, "x", bevel=0.0022, segments=2)
    _part(own, "BottomRail", [((-W / 2 + t, y0, ph), (W / 2 - t, y1 - 0.02, zb))], oak, "x", bevel=0.0015)
    # recessed black plinth between the sides, dark interior behind the reveals, a back
    _part(own, "Plinth", [((-W / 2 + t, y0 + 0.045, 0), (W / 2 - t, y1 - 0.03, ph))], black, "x", bevel=0.001)
    hide = p["hide"]
    if hide:
        _part(own, "Interior", [((-W / 2 + t, y1 - 0.014, zb), (W / 2 - t, y1 - 0.004, H - t))], black, "x", bevel=0.0008)
    else:
        _part(own, "Interior", [((-W / 2 + t, yb + 0.003, zb), (W / 2 - t, yb + 0.008, H - t))], black, "x", bevel=0.0008)

    # ---- doors: stile-and-rail frames around reeded panels
    xi0, xi1 = -W / 2 + t + g, W / 2 - t - g
    zd0, zd1 = zb + g, H - t - g
    dw = (xi1 - xi0 - (nd - 1) * g) / nd
    sw, rt, rb = p["stile"], p["rail_top"], p["rail_bottom"]
    stiles, rails = [], []
    reeds = bmesh.new()
    pitch = p["slat"] + p["slat_gap"]
    for d in range(nd):
        xa = xi0 + d * (dw + g)
        xb = xa + dw
        st_ = [((xa, yf, zd0), (xa + sw, yb, zd1)), ((xb - sw, yf, zd0), (xb, yb, zd1))]
        ra_ = [((xa + sw, yf, zd0), (xb - sw, yb, zd0 + rb)), ((xa + sw, yf, zd1 - rt), (xb - sw, yb, zd1))]
        if hide and d in hide:
            # a door that swings: its own frame and reeds (hung from its hinge below)
            _part(own, f"Door{d}_Stiles", st_, oak, "z", bevel=0.002, segments=1, seed=1 + d)
            _part(own, f"Door{d}_Rails", ra_, oak, "x", bevel=0.002, segments=1, seed=2 + d)
            rb_ = bmesh.new()
            reed_field(rb_, xa + sw, xb - sw, zd0 + rb, zd1 - rt, yf + 0.003, pitch, p["slat_gap"],
                       p["reed_depth"], uoff=0.37 * d)
            soften_normals(common.mesh_object(f"{n}_Door{d}_Reeds", rb_, col, oak, root), p["reed_normal"])
            continue
        stiles += st_
        rails += ra_
        # panel: reed crowns 3 mm behind the frame face
        reed_field(reeds, xa + sw, xb - sw, zd0 + rb, zd1 - rt, yf + 0.003, pitch, p["slat_gap"],
                   p["reed_depth"], uoff=0.37 * d)
    _part(own, "DoorStiles", stiles, oak, "z", bevel=0.002, segments=1, seed=1)
    _part(own, "DoorRails", rails, oak, "x", bevel=0.002, segments=1, seed=2)
    rd = common.mesh_object(f"{n}_DoorReeds", reeds, col, oak, root)
    soften_normals(rd, p["reed_normal"])

    # ---- T-bar pulls on the meeting stiles of each pair: a bar on two posts with roses
    L, pr, zc = p["pull_len"], p["pull_r"], p["pull_z"]
    proj = 0.040                                    # bar centre in front of the door face
    span = L - 0.07                                 # post centres
    for d in range(nd):
        xa = xi0 + d * (dw + g)
        px = (xa + dw - sw / 2) if d % 2 == 0 else (xa + sw / 2)
        ob = common.mesh_object(f"{n}_Pull_{d}", pull_bmesh(px, yf, zc, L, pr, span, proj), col, black if p["pull_finish"] == "black" else brass, root)
        common.box_uv(ob, 0.5)
    if hide:
        hiding(p, n, col, root, oak, black, brass, dict(xi0=xi0, dw=dw, g=g, yf=yf, yb=yb, y1=y1, zb=zb, H=H, t=t, W=W, D=D))
    parts = guest_mats.consolidate(root, max_dim=0.7)
    return root, parts


def hiding(p, n, col, root, oak, black, brass, k):
    """The middle pair as a hiding spot: partitions closing its bay, a rail with a coat at either
    end, the two doors (frame, reeds, pull) hung from empties on their outer hinge lines, merged
    per material; the eye a hand behind the doors, the exit in front."""
    a, b = p["hide"]
    xi0, dw, g = k["xi0"], k["dw"], k["g"]
    xa = xi0 + a * (dw + g)                 # the bay: the left door's outer edge ..
    xb = xi0 + b * (dw + g) + dw            # .. the right door's
    xc = (xa + xb) / 2
    y_in, y_bk, zb, ztop = k["yb"] + 0.004, k["y1"] - 0.014, k["zb"], k["H"] - k["t"]
    # (two parts: one part = one collider box, and one round both would fill the bay)
    _part((col, root, n), "BayWallL", [((xa - g - 0.012, y_in, zb), (xa - g, y_bk, ztop))], black, "z", bevel=0.0008)
    _part((col, root, n), "BayWallR", [((xb + g, y_in, zb), (xb + g + 0.012, y_bk, ztop))], black, "z", bevel=0.0008)
    coats = [(xc + dx, m, rgb, ln) for dx, m, rgb, ln in p["coats"]]
    ix_common.closet_rail(root, col, f"{n}_Bay", xa + 0.03, xb - 0.03, (y_in + y_bk) / 2 + 0.02, 1.98, coats, brass)
    doors = []
    for d, hx, sx in ((a, xa, -1), (b, xb, 1)):
        parts = [o for o in root.children if o.name.startswith(f"{n}_Door{d}_") or o.name == f"{n}_Pull_{d}"]
        pv = ix_common.pivot(root, col, f"{n}_Door{d}", (hx, k["yf"], 0.0), parts)
        ix_common.merge_parts(pv, {oak.name: "Leaf", black.name: "Pull", brass.name: "Pull"})
        doors.append((pv, sx * 100, sx * ix_common.crack(dw)))
    D = k["D"]
    ix_common.hide_spot(root, col, n, (xc, k["yb"] + 0.15, 1.6), [(xc, -D / 2 - 0.55, 0.0), (xc + 0.7, -D / 2 - 0.55, 0.0),
                                                                   (xc - 0.7, -D / 2 - 0.55, 0.0)],
                        "Hide in the wardrobe", "Leave the wardrobe", doors=doors, pitch=-4)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
