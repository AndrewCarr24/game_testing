"""Floor-to-ceiling wine racking for the cellar: a black plinth and smoked-oak storage
cabinet with an oak worktop, a grid of individual bottle cells (cheap low-poly bottles:
mostly bottom-out, some neck-out with bronze foil), and a fluted smoked-oak crown that
runs up to the ceiling. `bays` bays of `bay_w` metres side by side.

Units are metres. The front faces -Y (the back goes against a wall), origin at the floor
centre of the whole run; the run is centred on x = 0. Height = `height` (the ceiling).
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "DiningWineRack"

P = dict(
    name=NAME,
    bays=4,
    bay_w=1.0,
    depth=0.40,            # racking depth
    height=4.2,            # floor to ceiling
    plinth_h=0.08,
    cabinet_top=0.90,      # worktop underside
    top_t=0.035,
    cabinet_depth=0.48,
    rack_top=2.60,
    cols=8,                # bottle cells per bay
    rows=12,
    divider=0.010,
    bottle_r=0.042,
    bottle_len=0.08,
    neck_out=0.06,         # share of cells showing a neck-out bottle
    empty=0.07,            # share of cells left empty
    seed=3,
    bottle_segs=8,         # sides per bottle (the 6-bay run uses 7 to stay in the prop budget)
)


# ------------------------------------------------------------------- bottles

def _rand(i, j, k):
    return (math.sin(i * 12.9898 + j * 78.233 + k * 37.719) * 43758.5453) % 1.0


def bottle_bottom_out(bm, x, y_front, z, r, length, segs=8, spin=0.0):
    """The base of a bottle lying neck-in: a short open glass tube and a conical punt
    pushed into the base, on its own ring of verts so the heel reads as a crisp rim. Axis along +Y, front end at y_front. 3 * segs triangles."""
    ring_f, ring_b, heel = [], [], []
    for k in range(segs):
        a = spin + 2 * math.pi * k / segs
        c, s_ = math.cos(a), math.sin(a)
        ring_f.append(bm.verts.new((x + r * c, y_front, z + r * s_)))
        ring_b.append(bm.verts.new((x + r * c, y_front + length, z + r * s_)))
        heel.append(bm.verts.new((x + r * c, y_front, z + r * s_)))
    tube, punt = [], []
    for k in range(segs):
        t = (k + 1) % segs
        tube.append(bm.faces.new((ring_f[k], ring_f[t], ring_b[t], ring_b[k])))
    # punt: its own copy of the rim ring (a hard edge), the centre pushed 9 mm in
    centre = bm.verts.new((x, y_front + 0.009, z))
    for k in range(segs):
        t = (k + 1) % segs
        punt.append(bm.faces.new((heel[t], heel[k], centre)))
    # explicit facing (single-sided in the engine): the glass faces out of the bottle,
    # the punt faces the room
    for f in tube:
        f.normal_update()
        c = f.calc_center_median()
        if f.normal.dot(Vector((c.x - x, 0.0, c.z - z))) < 0:
            f.normal_flip()
    for f in punt:
        f.normal_update()
        if f.normal.y > 0:
            f.normal_flip()


def _lathe_y(bm, x, y0, z, prof, segs, spin=0.0, cap=False):
    """Revolve [(r, dy)] about the line through (x, ., z) parallel to Y (open ends;
    `cap` closes the last ring with a fan)."""
    rows = []
    for r, dy in prof:
        rows.append([bm.verts.new((x + r * math.cos(spin + 2 * math.pi * k / segs), y0 + dy,
                                   z + r * math.sin(spin + 2 * math.pi * k / segs))) for k in range(segs)])
    for a, b in zip(rows[:-1], rows[1:]):
        for k in range(segs):
            t = (k + 1) % segs
            bm.faces.new((a[k], a[t], b[t], b[k]))
    if cap:
        c = bm.verts.new((x, y0 + prof[-1][1], z))
        last = rows[-1]
        for k in range(segs):
            bm.faces.new((last[k], last[(k + 1) % segs], c))


def bottle_neck_out(bm, foil, x, y_front, z, r, segs=8, spin=0.0):
    """Neck facing the viewer: the body running back into the cell, a rounded shoulder,
    the neck and a foil capsule with a domed end."""
    _lathe_y(bm, x, y_front, z, [(r, 0.11), (r * 0.80, 0.066), (0.017, 0.050), (0.0125, 0.036),
                                (0.0125, 0.030)], segs, spin)
    _lathe_y(foil, x, y_front, z, [(0.0145, 0.034), (0.0145, 0.004), (0.011, 0.0)], segs, spin, cap=True)


def reeded_panel(bm, x0, x1, y_back, depth, z0, z1, pitch, segs=3, top_cap=False):
    """A run of half-round reeds standing on the plane y = y_back, bulging toward -Y by
    `depth`, from z0 to z1: one strip of quads per reed facet plus a bottom cap (the top
    meets the ceiling). Smooth-shaded it reads as turned oak flutes."""
    k = max(1, int(round((x1 - x0) / pitch)))
    w = (x1 - x0) / k
    prof = []
    for i in range(k):
        for s_ in range(segs + 1):
            if i > 0 and s_ == 0:
                continue
            a = math.pi * s_ / segs
            prof.append((x0 + i * w + w / 2 - math.cos(a) * w / 2, y_back - math.sin(a) * depth))
    lo = [bm.verts.new((px, py, z0)) for px, py in prof]
    hi = [bm.verts.new((px, py, z1)) for px, py in prof]
    for a in range(len(prof) - 1):
        bm.faces.new((lo[a], lo[a + 1], hi[a + 1], hi[a]))
    # bottom cap, one fan per reed (convex pieces triangulate cleanly)
    for i in range(k):
        idx = list(range(i * segs, i * segs + segs + 1))
        bm.faces.new([lo[q] for q in reversed(idx)])
        if top_cap:
            bm.faces.new([hi[q] for q in idx])
    return k


def board(bm, axis, centre, length, thick, depth, y_front, chamfer=0.0022, caps=True):
    """A rack board whose front edges are chamfered (catches a line of light), back face
    left out (it sits on the backing). axis: 'z' (a vertical divider, `thick` along x) or
    'x' (a shelf board, `thick` along z). Its front face is at y_front."""
    cx, cz = centre
    t, c = thick / 2, min(chamfer, thick * 0.3)
    yb = y_front + depth
    # cross-section (u across the board, y): back-left, front-left (chamfered), front-right, back-right
    sec = [(-t, yb), (-t, y_front + c), (-t + c, y_front), (t - c, y_front), (t, y_front + c), (t, yb)]
    def P(u, y, w):
        return (cx + u, y, cz + w) if axis == "z" else (cx + w, y, cz + u)
    a = [bm.verts.new(P(u, y, -length / 2)) for u, y in sec]
    b = [bm.verts.new(P(u, y, length / 2)) for u, y in sec]
    faces = [bm.faces.new((a[q], a[q + 1], b[q + 1], b[q])) for q in range(len(sec) - 1)]
    if caps:
        faces += [bm.faces.new(a), bm.faces.new(b[::-1])]
    mid = Vector(P(0.0, (y_front + yb) / 2, 0.0))
    for f in faces:                      # open shell: orient every face away from the board's core
        f.normal_update()
        if f.normal.dot(f.calc_center_median() - mid) < 0:
            f.normal_flip()


# --------------------------------------------------------------------- build

def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    oak = materials.smoked_oak()
    dark = materials.black_metal()
    bronze = materials.bronze()
    glass_g = common.pbr_material("M_Bottle_Green", (0.022, 0.060, 0.028), roughness=0.15)
    glass_k = common.pbr_material("M_Bottle_Black", (0.020, 0.018, 0.022), roughness=0.15)
    backing = common.pbr_material("M_Rack_Backing", (0.010, 0.0075, 0.006), roughness=0.9)

    nb, bw = p["bays"], p["bay_w"]
    W = nb * bw
    D = p["depth"]
    y_back = D / 2          # back plane of the run (against the wall)
    y_front = -D / 2

    # --- plinth, cabinet and worktop
    plinth = common.mesh_object(f"{n}_Plinth", common.box_bmesh((W - 0.06, p["cabinet_depth"] - 0.07, p["plinth_h"])),
                                col, dark, root)
    cd = p["cabinet_depth"]
    plinth.location = (0, y_back - cd / 2 + 0.0, p["plinth_h"] / 2)
    ch = p["cabinet_top"] - p["plinth_h"]
    carcass = common.mesh_object(f"{n}_Cabinet", common.box_bmesh((W - 0.01, cd - 0.03, ch)), col, oak, root)
    carcass.location = (0, y_back - (cd - 0.03) / 2, p["plinth_h"] + ch / 2)
    common.add_bevel(carcass, 0.004, 2)
    common.box_uv(carcass, 0.5)
    wt = common.mesh_object(f"{n}_Worktop", common.box_bmesh((W, cd + 0.02, p["top_t"])), col, oak, root)
    wt.location = (0, y_back - (cd + 0.02) / 2 + 0.0, p["cabinet_top"] + p["top_t"] / 2)
    common.add_bevel(wt, 0.004, 2)
    common.box_uv(wt, 0.5)

    # doors with slim bronze pulls
    door_b, pull_b = bmesh.new(), bmesh.new()
    gap = 0.004
    dw = bw / 2 - gap * 1.5
    dh = ch - 0.03
    for i in range(nb * 2):
        cx = -W / 2 + gap + dw / 2 + i * (dw + gap) + (i // 2) * (bw - 2 * dw - 3 * gap) * 0 + 0.0
        cx = -W / 2 + (i + 0.5) * (W / (nb * 2))
        bmesh.ops.create_cube(door_b, size=1.0, matrix=Matrix.Translation((cx, y_back - cd + 0.006, p["plinth_h"] + 0.01 + dh / 2)) @
                              Matrix.Diagonal((W / (nb * 2) - 0.006, 0.02, dh, 1)))
        px = cx + (0.07 if i % 2 == 0 else -0.07) * 0 + (W / (nb * 2) / 2 - 0.045) * (1 if i % 2 == 0 else -1)
        bmesh.ops.create_cone(pull_b, cap_ends=True, cap_tris=False, segments=6, radius1=0.006, radius2=0.006,
                              depth=0.36, matrix=Matrix.Translation((px, y_back - cd - 0.018, p["plinth_h"] + 0.01 + dh * 0.62)))
    doors = common.mesh_object(f"{n}_Doors", door_b, col, oak, root, smooth=False)
    pulls = common.mesh_object(f"{n}_Pulls", pull_b, col, bronze, root)
    common.box_uv(doors, 0.5)
    common.box_uv(pulls, 0.5)

    # --- racking frame: vertical and horizontal dividers (flat boards, no bevels)
    z0 = p["cabinet_top"] + p["top_t"] + 0.01
    rows, cols = p["rows"], p["cols"]
    cell_h = (p["rack_top"] - z0) / rows
    cell_w = bw / cols
    t = p["divider"]
    rd = D - 0.02            # full depth (bay boundaries and the top/bottom boards)
    sd = 0.19                # shallow dividers between cells (bottles are seen at the front)
    frame = bmesh.new()
    zmid, zh = (z0 + p["rack_top"]) / 2, p["rack_top"] - z0
    for i in range(nb * cols + 1):
        x = -W / 2 + i * cell_w
        full = (i % cols == 0)
        if full:   # bay boundaries: thicker, full depth, front flush with the cell boards
            board(frame, "z", (x, zmid), zh, t * 2.2, rd, y_front + 0.01 - 0.002, caps=False)
        else:
            board(frame, "z", (x, zmid), zh - 0.002, t, sd, y_front + 0.01, caps=False)
    for j in range(rows + 1):
        z = z0 + j * cell_h
        edge = j in (0, rows)
        board(frame, "x", (0, z), W, t * (2.0 if edge else 1.0), rd if edge else sd,
              y_front + 0.01 - (0.002 if edge else 0.0), caps=True)
    fr = common.mesh_object(f"{n}_Frame", frame, col, oak, root, smooth=False)
    common.box_uv(fr, 0.5)
    back = common.mesh_object(f"{n}_Backing", common.box_bmesh((W, 0.012, p["rack_top"] - z0)), col, backing, root)
    back.location = (0, y_back - 0.006, (z0 + p["rack_top"]) / 2)
    common.box_uv(back, 1.0)

    # --- bottles
    bg, bk, foil = bmesh.new(), bmesh.new(), bmesh.new()
    r = p["bottle_r"]
    yf = y_front + 0.03
    for i in range(nb * cols):
        for j in range(rows):
            u = _rand(i, j, p["seed"])
            if u < p["empty"]:
                continue
            x = -W / 2 + (i + 0.5) * cell_w
            z = z0 + (j + 0.5) * cell_h
            target = bg if _rand(i, j, p["seed"] + 5) < 0.62 else bk
            if _rand(i, j, p["seed"] + 9) < p["neck_out"]:
                bottle_neck_out(target, foil, x, yf, z, r, segs=p["bottle_segs"])
            else:
                bottle_bottom_out(target, x, yf + 0.004 + 0.04 * _rand(i, j, 2), z, r, p["bottle_len"],
                                  segs=p["bottle_segs"], spin=_rand(i, j, 4) * math.pi)
    for bm_, nm, mat in ((bg, "BottlesGreen", glass_g), (bk, "BottlesBlack", glass_k), (foil, "Foil", bronze)):
        ob = common.mesh_object(f"{n}_{nm}", bm_, col, mat, root)
        common.box_uv(ob, 0.5)

    # --- fluted crown up to the ceiling, with a bronze reveal under it
    zc0, zc1 = p["rack_top"] + 0.03, p["height"]
    crown_back = common.mesh_object(f"{n}_Crown", common.box_bmesh((W, 0.05, zc1 - zc0)), col, backing, root)
    crown_back.location = (0, y_back - 0.025, (zc0 + zc1) / 2)
    common.box_uv(crown_back, 1.0)
    rib = bmesh.new()
    reeded_panel(rib, -W / 2, W / 2, y_back - 0.05, 0.035, zc0 + 0.01, zc1, 0.075)
    ribs = common.mesh_object(f"{n}_CrownRibs", rib, col, oak, root, smooth=True)
    common.box_uv(ribs, 0.5)
    reveal = common.mesh_object(f"{n}_Reveal", common.box_bmesh((W, 0.06, 0.02)), col, bronze, root)
    reveal.location = (0, y_back - 0.04, p["rack_top"] + 0.015)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
