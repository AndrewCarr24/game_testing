"""Floor-to-ceiling walnut bookcase for the library (and, lower, the office).

A walnut carcass: black plinth, a closed cabinet with two doors below, open
shelves above filled with individually modelled books (cheap: only the faces a
reader can see: spine, top and the exposed side of a taller book), leaning
stacks, flat stacks and the odd bronze object, a cornice, and a slim bronze
ladder rail on standoffs. All books share one spine atlas, T_Library_Spines.

`seed` changes the arrangement; library_bookcase_a / _b wrap it so neighbouring
bays on a wall are not identical. Origin: floor centre, the open front faces -Y.
"""
import importlib
import math
import os
import random
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)
importlib.reload(materials)

NAME = "LibraryBookcase"

P = dict(
    name=NAME,
    seed=1,
    width=1.18,              # one bay
    bays=2,                  # bays per unit (one mesh set per unit keeps draw calls down)
    depth=0.36,
    height=3.74,
    plinth_h=0.08,
    plinth_recess=0.03,
    cabinet_h=0.84,          # top of the closed cabinet (counter)
    side_t=0.025,
    shelf_t=0.022,
    back_t=0.012,
    cornice_h=0.085,
    rows=7,
    doors=True,
    rail=True,
    rail_z=3.2,
    books=True,
    shelf_h=None,            # compartment heights (list); default tapers upward
    book_recess=0.035,
)

# ------------------------------------------------------------- spine atlas

ATLAS_COLS, ATLAS_ROWS = 16, 3        # spine cells, each 64 x 256 px
CELL_W, CELL_H = 64, 256
PAPER_Y0 = ATLAS_ROWS * CELL_H        # image row where the cream paper strip starts

# linear-RGB base colours: leather and cloth, mostly deep and a little worn
SPINE_COLOURS = [
    (0.115, 0.012, 0.012), (0.075, 0.010, 0.010), (0.014, 0.060, 0.030), (0.010, 0.040, 0.025),
    (0.010, 0.018, 0.065), (0.015, 0.025, 0.090), (0.19, 0.085, 0.030), (0.12, 0.055, 0.020),
    (0.020, 0.018, 0.016), (0.040, 0.030, 0.022), (0.30, 0.22, 0.12), (0.22, 0.16, 0.09),
    (0.34, 0.075, 0.025), (0.23, 0.17, 0.045), (0.045, 0.12, 0.13), (0.07, 0.07, 0.08),
    (0.40, 0.35, 0.26), (0.060, 0.075, 0.12), (0.20, 0.03, 0.04), (0.08, 0.10, 0.05),
]
GOLD = np.array([0.55, 0.36, 0.075])


def spines(n=1024, seed=5, force=False):
    """Atlas of 48 book spines (64 x 256 px cells, 16 x 3) plus a cream paper strip."""
    path = os.path.join(textures.TEX_DIR, "T_Library_Spines.png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    img = np.zeros((n, n, 3))
    grain = textures._noise(n, 1.0, 1.0, 0.9, rng) * 0.5 + 0.5      # leather mottling
    streak = textures._noise(n, 0.3, 1.0, 0.7, rng) * 0.5 + 0.5

    yy, xx = np.mgrid[0:CELL_H, 0:CELL_W]
    for r in range(ATLAS_ROWS):
        for c in range(ATLAS_COLS):
            idx = r * ATLAS_COLS + c
            base = np.array(SPINE_COLOURS[rng.integers(len(SPINE_COLOURS))])
            style = rng.choice(["classic", "classic", "bands", "label", "cloth", "twotone", "plain"])
            gx, gy = c * CELL_W, r * CELL_H
            g = grain[gy:gy + CELL_H, gx:gx + CELL_W, None]
            s = streak[gy:gy + CELL_H, gx:gx + CELL_W, None]
            cell = base * (0.78 + 0.34 * g) * (0.92 + 0.16 * s)
            gold = GOLD * rng.uniform(0.85, 1.15)
            dark_label = np.array(SPINE_COLOURS[rng.integers(len(SPINE_COLOURS))]) * 0.6 + 0.01

            if style in ("classic", "bands", "label"):
                for y in (14, 20, CELL_H - 22, CELL_H - 16):                  # gilt rules top and bottom
                    cell[y:y + 2] = gold
                # raised bands (hubs): light line, dark shadow below
                nb = 4 if style != "label" else 3
                pos = np.linspace(48, CELL_H - 52, nb).astype(int)
                for p in pos:
                    cell[p - 2:p + 3] *= 1.28
                    cell[p + 3:p + 6] *= 0.62
                    cell[p - 5:p - 2] *= 0.8
                # title panels between bands
                lab_a = (pos[0] + 8, pos[1] - 8)
                cell[lab_a[0]:lab_a[1], 8:CELL_W - 8] = dark_label
                for k in range(rng.integers(2, 4)):
                    yy0 = lab_a[0] + 8 + k * 11
                    if yy0 + 3 < lab_a[1] - 6:
                        w = rng.integers(14, CELL_W - 22)
                        x0 = (CELL_W - w) // 2
                        cell[yy0:yy0 + 3, x0:x0 + w] = gold
                if style == "label" and len(pos) > 2:
                    cell[pos[1] + 8:pos[2] - 8, 10:CELL_W - 10] = np.array([0.45, 0.39, 0.27])
                    cell[pos[1] + 14:pos[1] + 17, 16:CELL_W - 16] = 0.02
            elif style == "cloth":
                cell[0:int(CELL_H * 0.22)] = cell[0:int(CELL_H * 0.22)] * 0.3 + base[None, None, ::-1] * 0.7
                cell[int(CELL_H * 0.22):int(CELL_H * 0.22) + 3] = gold
                for k in range(rng.integers(3, 6)):
                    y0 = int(CELL_H * (0.35 + 0.1 * k))
                    w = rng.integers(16, CELL_W - 14)
                    x0 = (CELL_W - w) // 2
                    cell[y0:y0 + 4, x0:x0 + w] = np.array([0.6, 0.57, 0.5])
                cell[CELL_H - 30:CELL_H - 12, 18:CELL_W - 18] = np.array([0.6, 0.57, 0.5])
            elif style == "twotone":
                split = int(CELL_H * rng.uniform(0.62, 0.78))
                other = np.array(SPINE_COLOURS[rng.integers(len(SPINE_COLOURS))])
                cell[split:] = other * (0.78 + 0.34 * g[split:])
                cell[split:split + 3] = gold
                cell[28:44, 14:CELL_W - 14] = dark_label
                for k in range(2):
                    cell[34 + k * 4:36 + k * 4, 20:CELL_W - 20] = gold
            else:                                                            # plain with one tiny label
                cell[40:100, 14:CELL_W - 14] = np.array([0.5, 0.44, 0.31])
                cell[56:60, 20:CELL_W - 20] = 0.02
                cell[68:71, 24:CELL_W - 24] = 0.02
                cell[CELL_H - 26:CELL_H - 23] = gold

            # shading between neighbours: dark edges, a soft round of the spine
            edge = np.minimum(xx, CELL_W - 1 - xx)[..., None]
            cell *= np.clip(0.55 + edge / 10.0, 0, 1)
            cell[:, 0:2] = base * 0.35       # leftmost two px double as the side colour
            # top and bottom of the spine: slightly darker (cover boards, dust)
            cell *= np.clip(0.6 + np.minimum(yy, CELL_H - 1 - yy)[..., None] / 14.0, 0, 1)
            img[gy:gy + CELL_H, gx:gx + CELL_W] = cell

    # cream paper strip (top faces of books: page blocks with fine lines)
    h = n - PAPER_Y0
    y = np.arange(h)[:, None] * np.ones((1, n))
    lines = 0.5 + 0.5 * np.sin(y * 2 * np.pi / 3.0)
    tone = textures._noise(n, 1.0, 1.0, 1.6, rng)[PAPER_Y0:] * 0.5 + 0.5
    paper = np.array([0.62, 0.53, 0.36])[None, None, :] * (0.78 + 0.1 * lines[..., None] + 0.12 * tone[..., None])
    img[PAPER_Y0:] = paper
    return textures._save("T_Library_Spines", textures._to_srgb(np.clip(img, 0, 1)))


def books_material():
    m = common.pbr_material("M_Library_Spines", (1, 1, 1), roughness=0.62)
    common.set_base_color_map(m, textures.load(spines()))
    return m


# ------------------------------------------------------------------ helpers

TILE = 0.5   # wood tile (m)


class Mesh:
    """Accumulates boxes and quads into one bmesh with its own UV layer."""

    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def box(self, centre, size, shift=(0.0, 0.0), skip=()):
        """World-scale wood UVs (grain along the longer in-plane axis)."""
        bm = self.bm
        res = bmesh.ops.create_cube(bm, size=1.0)
        verts = res["verts"]
        bmesh.ops.scale(bm, vec=Vector(size), verts=verts)
        bmesh.ops.translate(bm, vec=Vector(centre), verts=verts)
        faces = {f for v in verts for f in v.link_faces}
        for f in faces:
            n = [abs(c) for c in f.normal]
            na = n.index(max(n))
            a, b = [i for i in range(3) if i != na]
            if size[b] > size[a]:
                a, b = b, a
            for lp in f.loops:
                co = lp.vert.co
                # u along the board's length (the walnut scan's grain runs along u)
                lp[self.uv].uv = (co[a] / TILE + shift[0], co[b] / TILE + shift[1])
        return faces

    def to_object(self, name, col, mat, parent):
        for f in self.bm.faces:
            f.smooth = False
        return common.mesh_object(name, self.bm, col, mat, parent, smooth=False)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rnd = random.Random(p["seed"] * 7919 + 13)
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    walnut = materials.walnut()
    bronze = materials.bronze()

    W1, D, H = p["width"], p["depth"], p["height"]
    nb = p["bays"]
    W = W1 * nb
    st, sh, bt = p["side_t"], p["shelf_t"], p["back_t"]
    iw = W1 - st                           # clear width of a bay
    y0, y1 = -D / 2, D / 2                 # front, back
    z_cab = p["cabinet_h"]
    ch = p["cornice_h"]
    z_top = H - ch                         # underside of the cornice
    ph = p["plinth_h"]
    wood = Mesh()
    sx, sy = rnd.uniform(0, 3), rnd.uniform(0, 3)   # per-bay grain offset

    def box(c, s_, shift=(0.0, 0.0)):
        wood.box(c, s_, shift=(sx + shift[0], sy + shift[1]))

    # whole-case parts: end sides and dividers, counter, recessed plinth, cornice
    for k in range(nb + 1):
        x = -W / 2 + k * W1
        x = min(max(x, -W / 2 + st / 2), W / 2 - st / 2)
        box((x, 0, (z_top + ph) / 2), (st, D - 0.002, z_top - ph), shift=(0.11 * k, 0.0))
    box((0, 0, z_cab - sh / 2 - 0.004), (W, D, sh + 0.008))
    box((0, -p["plinth_recess"] / 2, ph / 2), (W - 0.004, D - p["plinth_recess"] - 0.002, ph), shift=(0.5, 0.5))
    box((0, -0.004, H - ch / 2), (W, D + 0.012, ch))
    box((0, -0.012, H - ch - 0.01), (W - 0.04, D + 0.004, 0.02))

    br = Mesh()
    comps = []                       # per bay: list of (x_centre, z_floor, height)
    heights = p["shelf_h"]
    rows = p["rows"]
    avail = z_top - sh - z_cab
    if heights is None:
        heights = [0.44 - 0.015 * i for i in range(rows)]
        tot = sum(heights)
        heights = [h * (avail - (rows - 1) * sh) / tot for h in heights]
    for k in range(nb):
        xc = -W / 2 + (k + 0.5) * W1
        box((xc, 0, z_top - sh / 2), (iw, D - 0.002, sh), shift=(0.3 * k, 0.1))
        box((xc, y1 - bt / 2, (z_top + z_cab) / 2), (iw, bt, z_top - z_cab), shift=(0.2 * k, 0.3))
        box((xc, 0, ph + sh / 2), (iw, D - 0.04, sh))
        box((xc, y1 - bt / 2, (z_cab + ph) / 2), (iw, bt, z_cab - ph))
        if p["doors"]:
            g = 0.003
            dw = (iw - 3 * g) / 2
            dz0, dz1 = ph + sh + g, z_cab - sh - 0.01 - g
            dt = 0.02
            for d_ in (-1, 1):
                xd = xc + d_ * (g / 2 + dw / 2)
                box((xd, y0 + dt / 2 + 0.002, (dz0 + dz1) / 2), (dw, dt, dz1 - dz0),
                    shift=(0.37 * (d_ + 1) + k, 0.2 * (d_ + 1)))
                # slim vertical bronze pull on the meeting edge, in the door's upper part: its top
                # 6 cm below the door's top edge (it used to run 9 cm past the door into the shelf)
                pz = dz1 - 0.06 - 0.15
                br.box((xc + d_ * 0.045, y0 - 0.012, pz), (0.012, 0.012, 0.30))
                for zz in (0.13, -0.13):
                    br.box((xc + d_ * 0.045, y0 - 0.001, pz + zz), (0.01, 0.018, 0.012))
        z = z_cab
        bay = []
        for i, h in enumerate(heights):
            bay.append((xc, z, h))
            z += h
            if i < rows - 1:
                box((xc, 0.0, z + sh / 2), (iw, D - 0.002, sh), shift=(0.17 * i, 0.4 * k))
                z += sh
        comps.append(bay)

    if p["rail"]:
        rz, standoff = p["rail_z"], 0.075
        for k in (-1, 1):
            br.box((k * (W / 2 - 0.05), y0 - standoff / 2, rz), (0.012, standoff, 0.045))
        br.box((0, y0 - standoff, rz), (W, 0.016, 0.016))

    # ---------------------------------------------------------------- books
    if p["books"]:
        bk = Mesh()
        deco_bm = br.bm                    # bronze objects share the rail's mesh
        ncells = ATLAS_COLS * ATLAS_ROWS

        def add_face(pts, uvs):
            f = bk.bm.faces.new([bk.bm.verts.new(q) for q in pts])
            for lp, uv in zip(f.loops, uvs):
                lp[bk.uv].uv = uv

        def spine(pts, cell, lying=False):
            """pts: bl, br, tr, tl of a quad facing -Y."""
            px, py = (cell % ATLAS_COLS) * CELL_W, (cell // ATLAS_COLS) * CELL_H
            u0, u1 = (px + 2) / 1024.0, (px + CELL_W - 2) / 1024.0
            vb, vt = 1 - (py + CELL_H - 2) / 1024.0, 1 - (py + 2) / 1024.0
            uvs = [(u0, vb), (u1, vb), (u1, vt), (u0, vt)] if not lying else [(u0, vb), (u0, vt), (u1, vt), (u1, vb)]
            add_face(pts, uvs)

        def top(pts):
            """Page block: pts front-left, front-right, back-right, back-left, facing +Z."""
            u = rnd.uniform(0.0, 0.85)
            v = 1 - (PAPER_Y0 + 24 + rnd.uniform(0, 140)) / 1024.0
            add_face(pts, [(u, v), (u + 0.04, v), (u + 0.04, v - 0.1), (u, v - 0.1)])

        SIDE_U = 1.0 / 1024.0

        def side(x, za, zb, yf, yb, facing):
            """Vertical quad in the plane x from za to zb; facing = -1 (-X) or +1 (+X)."""
            pts = [(x, yf, zb), (x, yb, zb), (x, yb, za), (x, yf, za)]       # normal -X
            if facing > 0:
                pts = pts[::-1]
            add_face(pts, [(SIDE_U, 0.5)] * 4)

        def flat_stack(xa, xb, zf, yf, show_top=True):
            """Lying books, spines out. Returns the z of the stack's top."""
            zz = zf
            for _ in range(rnd.randint(2, 4)):
                bw = (xb - xa) * rnd.uniform(0.82, 0.98)
                bx = xa + ((xb - xa) - bw) / 2 + rnd.uniform(-0.008, 0.008)
                th, dd = rnd.uniform(0.028, 0.055), rnd.uniform(0.2, 0.26)
                spine([(bx, yf, zz), (bx + bw, yf, zz), (bx + bw, yf, zz + th), (bx, yf, zz + th)],
                      rnd.randrange(ncells), lying=True)
                if show_top:
                    top([(bx, yf, zz + th), (bx + bw, yf, zz + th), (bx + bw, yf + dd, zz + th), (bx, yf + dd, zz + th)])
                side(bx, zz, zz + th, yf, yf + dd, -1)
                side(bx + bw, zz, zz + th, yf, yf + dd, +1)
                zz += th
            return zz

        for bay in comps:
          for ri, (xc, zf, hc) in enumerate(bay):
            mode = rnd.choices(["full", "gap", "sparse", "stack"], [0.58, 0.16, 0.12, 0.14])[0]
            yfront = y0 + p["book_recess"] + rnd.uniform(0.0, 0.012)
            dmax = D - p["book_recess"] - bt - 0.02
            lo, hi = xc - iw / 2 + 0.004, xc + iw / 2 - 0.004
            deco, left = None, rnd.random() < 0.5
            if mode in ("gap", "stack"):
                reserve = rnd.uniform(0.22, 0.34) if mode == "gap" else rnd.uniform(0.18, 0.28)
                deco = "stack" if mode == "stack" else rnd.choice(["sphere", "vase", "stack", "bowl", "box"])
                xa, xb = (lo, lo + reserve) if left else (hi - reserve, hi)
                if left:
                    lo += reserve + 0.01
                else:
                    hi -= reserve + 0.01
            visible_top = zf + 0.62 * hc < 1.75   # nobody sees the top of a book above eye height
            books = []
            cx, base_h, run = lo, rnd.uniform(0.62, 0.8) * hc, rnd.randint(3, 9)
            run_y = rnd.uniform(0.0, 0.02)       # books in a run line up at the front
            lean = None
            while cx < hi - 0.02:
                w = rnd.choice([0.022, 0.026, 0.03, 0.034, 0.038, 0.044, 0.05, 0.058, 0.07])
                w = min(w, hi - cx)
                if w < 0.016:
                    break
                if run <= 0:
                    base_h, run = rnd.uniform(0.6, 0.88) * hc, rnd.randint(3, 9)
                    run_y = rnd.uniform(0.0, 0.025) if rnd.random() < 0.6 else 0.0
                run -= 1
                h = min(hc - 0.03, max(0.17, base_h * rnd.uniform(0.9, 1.08)))
                if w >= 0.058:
                    h = min(hc - 0.03, h * 1.07)
                d = min(dmax, rnd.uniform(0.17, 0.26))
                if mode == "sparse" and len(books) > 4 and rnd.random() < 0.08:
                    lean = (w, h, d)
                    break
                books.append((cx, w, h, yfront + run_y, d))
                cx += w
            for k, (bx, w, h, yf, d) in enumerate(books):
                spine([(bx, yf, zf), (bx + w, yf, zf), (bx + w, yf, zf + h), (bx, yf, zf + h)], rnd.randrange(ncells))
                if visible_top:
                    top([(bx, yf, zf + h), (bx + w, yf, zf + h), (bx + w, yf + d, zf + h), (bx, yf + d, zf + h)])
                if k > 0:    # the side of the taller neighbour that rises above the shorter one
                    pbx, pw, ph, pyf, pd = books[k - 1]
                    if h > ph:
                        side(bx, zf + ph, zf + h, yf, yf + d, -1)
                    elif ph > h:
                        side(bx, zf + h, zf + ph, pyf, pyf + pd, +1)
                    # where one run stands proud of the next, the side of the proud book
                    hm = zf + min(h, ph)
                    if yf < pyf - 0.001:
                        side(bx, zf, hm, yf, pyf, -1)
                    elif pyf < yf - 0.001:
                        side(bx, zf, hm, pyf, yf, +1)
            if books and (deco or lean):      # exposed end of the row of upright books
                bx, w, h, yf, d = books[0] if (deco and left) else books[-1]
                if deco and left:
                    side(bx, zf, zf + h, yf, yf + d, -1)
                elif deco:
                    side(bx + w, zf, zf + h, yf, yf + d, +1)
            if lean and books:
                w, h, d = lean
                lb, lw, lh, lyf, ld = books[-1]
                ang = math.radians(rnd.uniform(9, 15))
                xr = lb + lw + h * math.sin(ang) + w * math.cos(ang) * 0.0
                x0 = lb + lw + h * math.sin(ang)          # bottom-left; the top-left leans on the last book
                c, s_ = math.cos(ang), math.sin(ang)
                px, pz = x0 + w, zf
                def rot(x, z):
                    dx, dz = x - px, z - pz
                    return (px + dx * c - dz * s_, pz + dx * s_ + dz * c)
                bl, br2, tr2, tl2 = rot(x0, zf), rot(x0 + w, zf), rot(x0 + w, zf + h), rot(x0, zf + h)
                yf = yfront
                spine([(bl[0], yf, bl[1]), (br2[0], yf, br2[1]), (tr2[0], yf, tr2[1]), (tl2[0], yf, tl2[1])],
                      rnd.randrange(ncells))
                if visible_top:
                    top([(tl2[0], yf, tl2[1]), (tr2[0], yf, tr2[1]), (tr2[0], yf + d, tr2[1]), (tl2[0], yf + d, tl2[1])])
                # exposed side (the left face leans over the neighbour, +X face looks into the gap)
                f = [(br2[0], yf, br2[1]), (br2[0], yf + d, br2[1]), (tr2[0], yf + d, tr2[1]), (tr2[0], yf, tr2[1])]
                add_face(f, [(SIDE_U, 0.5)] * 4)
            if deco:
                zz = flat_stack(xa, xb, zf, yfront + 0.01, visible_top)
                cxm, cym = (xa + xb) / 2, yfront + 0.13
                if deco == "sphere":
                    bmesh.ops.create_uvsphere(deco_bm, u_segments=12, v_segments=7, radius=0.062,
                                              matrix=Matrix.Translation((cxm, cym, zz + 0.062)))
                elif deco == "vase":
                    bmesh.ops.create_cone(deco_bm, cap_ends=True, segments=12, radius1=0.045, radius2=0.024,
                                          depth=0.2, matrix=Matrix.Translation((cxm, cym, zz + 0.1)))
                elif deco == "bowl":            # a shallow bronze bowl on the stack
                    rows = [(0.03, 0.0), (0.055, 0.012), (0.075, 0.035), (0.071, 0.037), (0.05, 0.016), (0.014, 0.01)]
                    ring = []
                    for r_, z_ in rows:
                        ring.append([deco_bm.verts.new((cxm + r_ * math.cos(2 * math.pi * k / 12),
                                                        cym + r_ * math.sin(2 * math.pi * k / 12), zz + z_))
                                     for k in range(12)])
                    bowl = [deco_bm.faces.new(ring[0][::-1]), deco_bm.faces.new(ring[-1])]
                    for ra, rb in zip(ring, ring[1:]):
                        for k in range(12):
                            bowl.append(deco_bm.faces.new((ra[k], ra[(k + 1) % 12], rb[(k + 1) % 12], rb[k])))
                    bmesh.ops.recalc_face_normals(deco_bm, faces=bowl)
                else:                           # "box": a lidded walnut keepsake box
                    bw_, bd_, bh_ = min(0.2, xb - xa - 0.02), 0.13, 0.075
                    wood.box((cxm, cym, zz + bh_ / 2), (bw_, bd_, bh_), shift=(0.3, 0.2))
                    wood.box((cxm, cym, zz + bh_ + 0.006), (bw_ + 0.006, bd_ + 0.006, 0.012), shift=(0.1, 0.6))
        books_obj = common.mesh_object(f"{n}_Books", bk.bm, col, books_material(), root, smooth=False)

    common.mesh_object(f"{n}_Carcass", wood.bm, col, walnut, root, smooth=False)
    br_obj = common.mesh_object(f"{n}_Bronze", br.bm, col, bronze, root, smooth=False)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
