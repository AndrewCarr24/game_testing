"""Chef's knife (the kitchen island's, on the end-grain board): a 20 cm satin-steel blade with a
flat spine, a curved belly up to the tip and a polished edge bevel, a forged bolster, and a
full-tang handle (black acetal scales either side of a steel tang, three steel rivets).

The player's first weapon (viewer/weapons.js `kitchen_knife`): a pickup (item "kitchen_knife")
whose `weapon` names its weapon definition. Seen up close in the hand (the first-person view
model), so it is modelled for that: lofted blade and handle, no textures.

Lies flat along X (tip at +X, edge toward -Y); origin at the centre of its underside. Empties
for the view model: `<n>_Grip` (handle centre), `<n>_Tip`, `<n>_Edge` (a point on the edge
side, so grip -> edge gives the edge direction)."""
import importlib
import math
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ix_common  # noqa: E402

importlib.reload(ix_common)
common, materials = ix_common.common, ix_common.materials

NAME = "KitchenKnife"

P = dict(
    name=NAME,
    blade=0.200,          # heel to tip
    heel=0.046,           # blade height at the heel (spine to edge)
    spine=0.0024,         # spine thickness at the heel
    handle=0.122,
    handle_h=0.0245,      # handle height (along the blade's height)
    handle_t=0.0185,      # handle thickness
    bolster=0.013,
    stations=30,          # along the blade
    ring=20,              # around the handle
    item="kitchen_knife",
    label="Chef's knife",
)


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def blade_bmesh(p):
    """Rows from the spine (j=0) to the edge (j=M) at stations from the heel (u=0) to the tip."""
    L, H, T = p["blade"], p["heel"], p["spine"]
    top, bottom = 0.020, 0.020 - H
    tip_y = top - 0.0125
    rows = [0.0, 0.18, 0.45, 0.72, 0.9, 1.0]          # across, spine -> edge
    thick = [1.0, 0.92, 0.66, 0.36, 0.13, 0.0]        # flat grind, then the edge bevel
    N = p["stations"]
    bm = bmesh.new()
    top_v, bot_v = [], []
    for i in range(N + 1):
        k = i / N
        u = 1 - (1 - k) ** 1.35                        # denser toward the tip
        ys = top - (top - tip_y) * smooth((u - 0.55) / 0.45) ** 1.6
        f = 0.0 if u < 0.42 else ((u - 0.42) / 0.58) ** 2.1
        ye = bottom + (tip_y - bottom) * f
        ye = min(ye, ys - 0.0005)                      # (the tip keeps a hair of width)
        # the heel's choil: the edge's last few mm curve up into the bolster
        if u < 0.035:
            ye += 0.004 * (1 - u / 0.035) ** 2
        ts = T * (1 - 0.72 * u) + 0.0003
        tr, br = [], []
        for s, th in zip(rows, thick):
            y = ys + (ye - ys) * s
            t = max(0.00025, ts * th) if s < 1 else 0.00025
            tr.append(bm.verts.new((u * L, y, t / 2)))
            br.append(bm.verts.new((u * L, y, -t / 2)))
        top_v.append(tr)
        bot_v.append(br)
    M = len(rows) - 1
    edge_faces = []
    for i in range(N):
        for j in range(M):
            f1 = bm.faces.new((top_v[i][j], top_v[i][j + 1], top_v[i + 1][j + 1], top_v[i + 1][j]))
            f2 = bm.faces.new((bot_v[i][j], bot_v[i + 1][j], bot_v[i + 1][j + 1], bot_v[i][j + 1]))
            if j == M - 1:
                edge_faces += [f1, f2]
        bm.faces.new((top_v[i][0], top_v[i + 1][0], bot_v[i + 1][0], bot_v[i][0]))         # spine
        bm.faces.new((top_v[i][M], bot_v[i][M], bot_v[i + 1][M], top_v[i + 1][M]))         # edge
    bm.faces.new([top_v[0][j] for j in range(M + 1)][::-1] + [bot_v[0][j] for j in range(M + 1)])   # heel (in the bolster)
    bm.faces.new([top_v[N][j] for j in range(M + 1)] + [bot_v[N][j] for j in range(M + 1)][::-1])  # tip
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in edge_faces:
        f.material_index = 1
    # hard edges along the spine corners and the grind line
    for e in bm.edges:
        ys = [v.co.y for v in e.verts]
        if all(abs(v.co.z) > 1e-5 for v in e.verts) and e.is_manifold and len(e.link_faces) == 2:
            n0, n1 = e.link_faces[0].normal, e.link_faces[1].normal
            if n0.dot(n1) < 0.8:
                e.smooth = False
    return bm


def loft_bmesh(stations, ring, flat=0.0011, caps=True):
    """Superellipse rings along X: stations = [(x, cy, ry, rz, n)], n = squareness (2 = ellipse).
    Each ring has vertices at z = +-flat on both sides (the tang line). Returns (bm, tang faces)."""
    half = ring // 2
    angs = []
    a0 = math.asin(min(0.9, flat / 0.008))
    for k in range(half):
        angs.append(-math.pi / 2 + (math.pi) * k / (half - 1) if half > 1 else 0)
    # one half from -90 to +90 deg (the +y side), mirrored for the -y side, plus the tang line
    base = sorted(set([round(a, 6) for a in angs] + [-a0, a0]))
    full = base + [math.pi - a for a in reversed(base) if abs(abs(a) - math.pi / 2) > 1e-6]
    bm = bmesh.new()
    rings = []
    for x, cy, ry, rz, n in stations:
        r = []
        for a in full:
            c, s = math.cos(a), math.sin(a)
            # superellipse: |y/ry|^n + |z/rz|^n = 1
            y = ry * math.copysign(abs(c) ** (2 / n), c)
            z = rz * math.copysign(abs(s) ** (2 / n), s)
            if abs(abs(a) - a0) < 1e-6 or abs(abs(math.pi - a) - a0) < 1e-6:
                z = math.copysign(min(flat, rz * 0.5), s)
            r.append(bm.verts.new((x, cy + y, z)))
        rings.append(r)
    m = len(full)
    tang = []
    for ra, rb in zip(rings, rings[1:]):
        for k in range(m):
            j = (k + 1) % m
            f = bm.faces.new((ra[k], ra[j], rb[j], rb[k]))
            if abs(ra[k].co.z) <= flat + 1e-6 and abs(ra[j].co.z) <= flat + 1e-6:
                tang.append(f)
    if caps:
        for r in (rings[0], rings[-1]):
            ctr = bm.verts.new((r[0].co.x, sum(v.co.y for v in r) / m, 0))
            for k in range(m):
                bm.faces.new((r[k], r[(k + 1) % m], ctr))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm, tang


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    root["interact"] = ix_common.pickup(
        p["item"], p["label"], weapon=p["item"],
        purpose="A weapon. Arm it: click or Enter to stab, right-click to slash. From behind, unseen: a silent takedown.")

    satin = common.pbr_material("M_Knife_Steel", (0.74, 0.74, 0.75), roughness=0.24, metallic=1.0)
    polished = materials.steel()                      # M_Steel_Polished: the edge bevel, the rivets
    acetal = common.pbr_material("M_Knife_Handle", (0.016, 0.016, 0.018), roughness=0.36)

    # ---- blade (x 0 .. blade), material 0 satin, 1 the polished edge bevel
    blade = common.mesh_object(f"{n}_Blade", blade_bmesh(p), col, satin, root)
    blade.data.materials.append(polished)

    hh, ht, Lh, Lb = p["handle_h"] / 2, p["handle_t"] / 2, p["handle"], p["bolster"]
    cy = 0.0085                                       # the handle sits toward the spine
    # ---- bolster: from the handle's section to a thin wedge into the blade's heel
    bol, _ = loft_bmesh([
        (-Lb, cy, hh * 0.98, ht * 0.86, 2.6),
        (-Lb * 0.55, cy - 0.0008, hh * 1.03, ht * 0.8, 2.6),
        (-Lb * 0.15, cy - 0.002, hh * 1.12, ht * 0.5, 2.4),
        (0.0015, cy - 0.003, hh * 1.18, 0.0016, 2.2),
    ], p["ring"], flat=0.0006)
    bolster = common.mesh_object(f"{n}_Bolster", bol, col, satin, root)

    # ---- handle: scales either side of the tang; a gentle belly, a swell at the butt
    st = []
    K = 14
    for k in range(K + 1):
        t = k / K
        x = -Lb - t * Lh
        bulge = 1 + 0.07 * math.sin(math.pi * min(1, t / 0.8))        # palm swell
        butt = 1 + 0.12 * smooth((t - 0.82) / 0.18)                     # flare at the butt
        dome = math.sqrt(max(0.0, 1 - ((t - 0.965) / 0.035) ** 2)) if t > 0.965 else 1.0
        st.append((x, cy - 0.0012 * math.sin(math.pi * t), hh * bulge * butt * max(0.35, dome),
                   ht * bulge * (1 + 0.04 * smooth((t - 0.8) / 0.2)) * max(0.35, dome), 2.7))
    hb, tang = loft_bmesh(st, p["ring"])
    for f in tang:
        f.material_index = 1
    handle = common.mesh_object(f"{n}_Handle", hb, col, acetal, root)
    handle.data.materials.append(satin)

    # ---- rivets: one pin through the handle each, both heads just proud of the scales
    for k, t in enumerate((0.2, 0.5, 0.8)):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=0.0027, radius2=0.0027, depth=2 * ht * 1.07 + 0.0004)
        rv = common.mesh_object(f"{n}_Rivet{k}", bm, col, polished, root)
        rv.location = (-Lb - t * Lh, cy - 0.0012 * math.sin(math.pi * t), 0)

    # ---- the view model's reference points
    for name, at in (("Grip", (-Lb - 0.5 * Lh, cy, 0)), ("Tip", (p["blade"], 0.0075, 0)), ("Edge", (0.05, -0.03, 0))):
        e = common.empty(f"{n}_{name}", col, at)
        e.parent = root
        e.empty_display_size = 0.02

    # lie it on its side: the handle's underside on z = 0, centred along X
    x0, x1 = -Lb - Lh, p["blade"]
    for ob in root.children:
        ob.location = (ob.location[0] - (x0 + x1) / 2, ob.location[1], ob.location[2] + ht * 1.16)
    return ix_common.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
