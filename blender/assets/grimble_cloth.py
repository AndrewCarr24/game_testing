"""Low-poly game meshes for the Grimble's body and cloak (blender/assets/grimble.py).

Pipeline stage 1 (low-poly modelling). The TRELLIS sculpt is the high-poly source only;
every game surface here is a height field over a simple parameter domain, so it cannot
fold over itself, has one consistent side, and has no holes:

* head: an icosphere around a point inside the head; inside the face opening (the
  sculpt's fur patch) each direction's radius is the sculpt's face, under each eyeball
  the surface sits inside the ball (the lids hug it), elsewhere an ellipsoid inside the
  hood;
* feet: the same around each foot (the clawed toes come out under the hem);
* robe: rows (height) x columns (angle round the body's axis, seam at the back centre);
  each vertex is the sculpt cloak's outermost point in its direction, so it carries the
  sculpt's silhouette and large folds; the hem rises over the toes; tucked under the hood;
* hood: a dome on (angle round the face, angle from the face's axis) from the face
  opening back over the head to the back pole (seam under the chin, inside the collar);
* sleeves: flared cuffs round each wrist (seam underneath);
* thickness (Solidify): outside = M_Grimble_Cloak (unique fold normal map), inside =
  M_Grimble_CloakLining, the rolled rims = M_Grimble_CloakEdge; thicker at the edges.

Each grid piece carries two UV sets: "UVMap" (unique atlas, for the baked maps) and
"UVDetail" (world scale, 1 unit = cloak_tile metres, for the tiling wool detail).
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def _tree(verts, tris):
    return BVHTree.FromPolygons([tuple(x) for x in verts], [tuple(t) for t in tris], all_triangles=True)


def _outermost(tree, c, dirs, rmax):
    """Distance from c to the first surface met coming in from rmax along each direction
    (nan where nothing is hit)."""
    out = np.full(len(dirs), np.nan)
    rc = tree.ray_cast
    for i, d in enumerate(dirs):
        o = Vector((c + d * rmax).tolist())
        h = rc(o, Vector((-d).tolist()), rmax)
        if h[0] is not None:
            out[i] = rmax - h[3]
    return out


def _outermost_from(tree, origins, dirs, rmax):
    out = np.full(len(dirs), np.nan)
    rc = tree.ray_cast
    for i, (c, d) in enumerate(zip(origins, dirs)):
        h = rc(Vector((c + d * rmax).tolist()), Vector((-d).tolist()), rmax)
        if h[0] is not None:
            out[i] = rmax - h[3]
    return out


def _vertex_neighbours(tris, n):
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    e = np.concatenate([e, e[:, ::-1]])
    deg = np.maximum(np.bincount(e[:, 0], minlength=n), 1)
    return e, deg


def _smooth_field(x, e, deg, iters, lam=0.5, fixed=None):
    for _ in range(iters):
        acc = np.zeros_like(x)
        np.add.at(acc, e[:, 0], x[e[:, 1]])
        nx = x + lam * (acc / deg - x)
        x = nx if fixed is None else np.where(fixed, x, nx)
    return x


def _icosphere(subdiv):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    v = np.array([x.co[:] for x in bm.verts])
    bm.verts.index_update()
    t = np.array([[x.index for x in f.verts] for f in bm.faces])
    bm.free()
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    return v, t


# ------------------------------------------------------------------- body

def _dir(frame, psi, th):
    c, a, b, f = frame
    psi, th = np.asarray(psi, float), np.asarray(th, float)
    return (np.cos(th)[..., None] * f + np.sin(th)[..., None]
            * (np.cos(psi)[..., None] * b + np.sin(psi)[..., None] * a))


def _psi_th(frame, d):
    c, a, b, f = frame
    return np.arctan2(d @ a, d @ b), np.arccos(np.clip(d @ f, -1, 1))


def opening(face_tree, hood_tree, frame, p):
    """The face opening: per angle round the face's axis (psi), the angle from the axis
    (theta) out to which the face is the outermost surface (a hood brim up to
    p['open_brim'] in front of the face still counts as the opening)."""
    c = frame[0]
    psis = np.linspace(-math.pi, math.pi, p["hood_cols"], endpoint=False)
    ths = np.linspace(0.0, 1.7, 86)
    th_open = np.zeros(len(psis))
    for j, psi in enumerate(psis):
        d = _dir(frame, np.full(len(ths), psi), ths)
        rf = _outermost(face_tree, c, d, 2.6)
        rh = _outermost(hood_tree, c, d, 2.8)
        vis = ~np.isnan(rf) & (np.isnan(rh) | (rf > rh - p["open_brim"]))
        k = 0
        while k + 1 < len(ths) and (vis[k + 1] or (k + 2 < len(ths) and vis[k + 2])):
            k += 1
        th_open[j] = ths[k]
    # robust and smooth: a circular median removes single-column dips (a hood flap poking
    # in front of the face), then a wide blur
    m = len(th_open)
    th_med = np.array([np.median(np.take(th_open, range(j - 3, j + 4), mode="wrap")) for j in range(m)])
    th_open = np.maximum(th_open, th_med)
    for _ in range(2):
        th_open = np.convolve(np.r_[th_open[-5:], th_open, th_open[:5]], np.ones(11) / 11, mode="valid")
    return psis, th_open


def _eye_mid(c, d, eyes):
    """Per direction from c: the middle of the eyeball along the ray if it hits one (nan
    otherwise)."""
    out = np.full(len(d), np.nan)
    for ec, R in eyes:
        oc = c - ec
        bq = d @ oc
        disc = bq * bq - (oc @ oc - R * R)
        hit = disc > 0
        t1 = -bq - np.sqrt(np.maximum(disc, 0))
        t2 = -bq + np.sqrt(np.maximum(disc, 0))
        mid = 0.5 * (t1 + t2) + 0.15 * (t2 - t1)
        out = np.where(hit & (t2 > 0), np.fmin(out, mid), out)
    return out


def head(face_tree, frame, open_fn, p, eyes=()):
    """Head mesh (verts, tris, is_face mask): the sculpt's face inside the opening, an
    ellipsoid inside the hood elsewhere, blended."""
    c, a, b, f = frame
    d, t = _icosphere(p["head_subdiv"])
    rf = _outermost(face_tree, c, d, 2.6)
    e, deg = _vertex_neighbours(t, len(d))
    ok = ~np.isnan(rf)
    base_r = float(np.median(rf[ok])) if ok.any() else 0.9
    # spikes (fur tufts, stray scan bits): a vertex far above its neighbours' median
    r0 = np.where(ok, rf, base_r)
    nb_med = np.zeros(len(d))
    order = np.argsort(e[:, 0], kind="stable")
    es = e[order]
    starts = np.searchsorted(es[:, 0], np.arange(len(d)))
    ends = np.searchsorted(es[:, 0], np.arange(len(d)), side="right")
    for i in range(len(d)):
        nb_med[i] = np.median(r0[es[starts[i]:ends[i], 1]])
    ok &= ~(r0 > nb_med + p["head_spike"])
    # the eyes: under each eyeball the surface sits inside the ball, so the lids (the
    # sculpt's surface just outside the silhouette) hug it with no gap or ring
    em = _eye_mid(c, d, eyes)
    on_eye = ~np.isnan(em)
    rf = np.where(on_eye, em, rf)
    ok |= on_eye
    psi, th = _psi_th(frame, d)
    inside = th < open_fn(psi)
    ell = base_r * p["head_inner"] * (1 - 0.1 * np.abs(d[:, 2]))
    w = (inside & ok).astype(float)
    w = _smooth_field(w, e, deg, p["head_blend"])
    rf_f = np.where(ok, rf, ell)
    r = w * rf_f + (1 - w) * np.minimum(ell, rf_f)
    # light smoothing away from the eyes only (it would pull the lids off the eyeballs)
    near_eye = _smooth_field(on_eye.astype(float), e, deg, 3) > 0.02
    r = np.where(near_eye, r, _smooth_field(r, e, deg, 1, 0.3))
    return c + d * r[:, None], t, w > 0.5


def foot(foot_tree, centre, p):
    d, t = _icosphere(p["foot_subdiv"])
    rf = _outermost(foot_tree, centre, d, 1.4)
    e, deg = _vertex_neighbours(t, len(d))
    ok = ~np.isnan(rf)
    default = np.full(len(d), np.nanmedian(rf) * 0.8 if ok.any() else 0.25)
    r = np.where(ok, rf, default)
    r = _smooth_field(r, e, deg, 2, 0.4)
    v = centre + d * r[:, None]
    v[:, 2] = np.maximum(v[:, 2], 0.0)
    return v, t


# ------------------------------------------------------------------ cloth

def _grid_tris(n_rows, n_cols, periodic):
    tris, quads = [], []
    cols = n_cols if periodic else n_cols - 1
    for i in range(n_rows - 1):
        for j in range(cols):
            j2 = (j + 1) % n_cols
            a0, a1 = i * n_cols + j, i * n_cols + j2
            b0, b1 = (i + 1) * n_cols + j, (i + 1) * n_cols + j2
            quads.append((a0, a1, b1, b0))
    return quads


def _fill_nan_grid(r, periodic_cols=True):
    """Fill missing radii along rows then columns (linear, periodic in columns)."""
    r = r.copy()
    n_rows, n_cols = r.shape
    for i in range(n_rows):
        row = r[i]
        ok = ~np.isnan(row)
        if ok.sum() >= 2:
            idx = np.arange(n_cols)
            r[i] = np.interp(idx, idx[ok], row[ok], period=n_cols if periodic_cols else None)
    for j in range(n_cols):
        colv = r[:, j]
        ok = ~np.isnan(colv)
        if ok.sum() >= 2:
            idx = np.arange(n_rows)
            r[:, j] = np.interp(idx, idx[ok], colv[ok])
        elif ok.sum() == 1:
            r[:, j] = colv[ok][0]
    return r


def _smooth_grid(r, iters, lam=0.5, periodic=True):
    for _ in range(iters):
        up = np.vstack([r[:1], r[:-1]])
        dn = np.vstack([r[1:], r[-1:]])
        lf = np.roll(r, 1, 1) if periodic else np.hstack([r[:, :1], r[:, :-1]])
        rt = np.roll(r, -1, 1) if periodic else np.hstack([r[:, 1:], r[:, -1:]])
        r = r + lam * ((up + dn + lf + rt) / 4 - r)
    return r


def _median3(r):
    stack = [np.roll(np.roll(np.pad(r, ((1, 1), (0, 0)), mode="edge"), di, 0), dj, 1)[1:-1]
             for di in (-1, 0, 1) for dj in (-1, 0, 1)]
    return np.median(np.stack(stack), axis=0)


def hood(hood_tree, head_r_fn, frame, open_psis, open_th, p):
    """Hood grid: verts (rows x cols), uv, edge weights (1 at the face opening)."""
    c, a, b, f = frame
    n_psi, n_th = p["hood_cols"], p["hood_rows"]
    psis = open_psis

    def direction(psi, th):
        return _dir(frame, psi, th)

    th_open = open_th + p["hood_margin"]
    # where the hood ends: the direction's elevation drops below the shoulders, or round the back
    sin_lim = math.sin(math.radians(p["hood_elev"]))
    th_end = np.zeros(n_psi)
    for j, psi in enumerate(psis):
        ths = np.linspace(th_open[j], p["hood_th_max"], 200)
        d = direction(np.full(len(ths), psi), ths)
        below = np.nonzero(d[:, 2] < sin_lim)[0]
        th_end[j] = ths[below[0]] if len(below) else ths[-1]
    th_end = np.maximum(th_end, th_open + 0.4)
    # a smooth end line (a ragged one leaves slits between neighbouring columns)
    for _ in range(3):
        th_end = np.maximum(th_end, np.convolve(np.r_[th_end[-2:], th_end, th_end[:2]], np.ones(5) / 5, mode="valid"))
    V = np.linspace(0, 1, n_th)
    TH = th_open[None, :] + V[:, None] * (th_end - th_open)[None, :]
    PS = np.tile(psis, (n_th, 1))
    D = direction(PS, TH)
    rh = _outermost(hood_tree, c, D.reshape(-1, 3), 2.8).reshape(n_th, n_psi)
    rh = _fill_nan_grid(rh)
    rh = _median3(rh)
    head_r = head_r_fn(D.reshape(-1, 3)).reshape(n_th, n_psi)
    rh = np.maximum(rh, head_r + p["hood_clear"])
    # the opening hugs the face: the first rows rise from just outside the head to the
    # sculpt's hood (seen from the front, a far-out brim would hide the face's edge)
    k_lip = p["hood_lip_rows"]
    w = np.clip(np.arange(n_th) / k_lip, 0, 1)
    w = (w * w * (3 - 2 * w))[:, None]
    rh = (head_r + p["hood_clear"]) * (1 - w) + rh * w
    rh = _smooth_grid(rh, p["hood_smooth"])
    # the opening's rolled lip: a little proud
    rh[0] += p["hood_lip"]
    verts = c + D * rh[..., None]
    edge_w = np.zeros((n_th, n_psi))
    edge_w[0] = 1.0
    edge_w[1] = 0.5
    return verts, edge_w, D


def robe(cloak_tree, p, hood_cover_fn, axis_pts, top_fn, bottom_fn):
    """Robe grid around the body's axis: rows from bottom_fn(angle) (the hem, raised over
    the toes) up to top_fn(angle) (lower in front, under the chin), columns round the body
    starting at the back centre (the UV seam)."""
    n_z, n_c = p["robe_rows"], p["robe_cols"]
    th = math.pi + np.linspace(0, 2 * math.pi, n_c, endpoint=False)      # back centre first
    dirs = np.stack([np.sin(th), -np.cos(th), np.zeros(n_c)], 1)        # 0 = front (-Y)
    ztop = top_fn(th)
    zbot = bottom_fn(th)
    Vp = np.linspace(0, 1, n_z)
    Z = zbot[None, :] + Vp[:, None] * (ztop - zbot)[None, :]
    AX = np.stack([np.interp(Z, axis_pts[:, 2], axis_pts[:, k]) for k in range(2)], 2)
    R = np.full((n_z, n_c), np.nan)
    for i in range(n_z):
        origins = np.stack([AX[i, :, 0], AX[i, :, 1], Z[i]], 1)
        R[i] = _outermost_from(cloak_tree, origins, dirs, 3.6)
    R = _fill_nan_grid(R)
    R = _median3(R)
    R = _smooth_grid(R, p["robe_smooth"])
    verts = np.stack([AX[..., 0] + dirs[None, :, 0] * R, AX[..., 1] + dirs[None, :, 1] * R, Z], 2)
    # tucked in under the hood (so the two never share a surface)
    k = np.clip(hood_cover_fn(verts.reshape(-1, 3)).reshape(n_z, n_c), 0, 1)
    rad = verts[..., :2] - AX
    verts[..., :2] = AX + rad * (1 - p["robe_tuck"] * k)[..., None]
    edge_w = np.zeros((n_z, n_c))
    edge_w[0] = 1.0
    edge_w[1] = 0.5
    return verts, edge_w


def metric_uv(verts):
    """Unwrapped metric coordinates of a periodic grid (rows x cols): each row is a
    straight strip as long as the row's arc length (columns evenly spaced on it, centred),
    rows stacked at their mean spacing. Trapezoid strips can't fold or overlap, and the
    texel density stays close to uniform. Returns U (rows x cols+1), V (rows x cols), m."""
    ring = np.concatenate([verts, verts[:, :1]], axis=1)
    row_len = np.linalg.norm(np.diff(ring, axis=1), axis=2).sum(1)
    n_c = verts.shape[1]
    U = (np.arange(n_c + 1)[None, :] / n_c - 0.5) * row_len[:, None]
    gap = np.linalg.norm(np.diff(verts, axis=0), axis=2).mean(1)
    V = np.tile(np.concatenate([[0], np.cumsum(gap)])[:, None], (1, n_c))
    return U, V


def grid_object(name, verts, uv_sets, edge_w, outward_ref, col, mats, p, solid=True):
    """Periodic grid -> mesh with UV sets [(layer, U (rows x cols+1), V (rows x cols))],
    optionally solidified (material 0 outside, 1 inside, 2 the rims; thicker where edge_w
    = 1). Returns the object (modifier applied)."""
    n_rows, n_cols, _ = verts.shape
    bm = bmesh.new()
    layers = [(bm.loops.layers.uv.new(nm), U, V) for nm, U, V in uv_sets]
    flat = verts.reshape(-1, 3)
    vs = [bm.verts.new(tuple(x)) for x in flat]
    ew = edge_w.reshape(-1)
    for i in range(n_rows - 1):
        for j in range(n_cols):
            j2 = (j + 1) % n_cols
            ids = [i * n_cols + j, i * n_cols + j2, (i + 1) * n_cols + j2, (i + 1) * n_cols + j]
            f = bm.faces.new([vs[k] for k in ids])
            for uvl, U, V in layers:
                uvq = [(U[i, j], V[i, j]), (U[i, j + 1], V[i, j2]), (U[i + 1, j + 1], V[i + 1, j2]),
                       (U[i + 1, j], V[i + 1, j])]
                for l, uv in zip(f.loops, uvq):
                    l[uvl].uv = uv
    bm.normal_update()
    out = 0.0
    for f in bm.faces:
        out += f.normal.dot(f.calc_center_median() - Vector(outward_ref(np.array(f.calc_center_median()))))
    if out < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    if not solid:
        return ob
    vg = ob.vertex_groups.new(name="thick")
    wq = np.round(np.maximum(p["cloth_thin"], ew) * 100).astype(int)
    for val in np.unique(wq):
        vg.add(np.nonzero(wq == val)[0].tolist(), val / 100.0, "REPLACE")
    sol = ob.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = p["cloth_thick"]
    sol.offset = -1.0
    sol.use_rim = True
    sol.use_even_offset = False       # (even offset explodes at pinched grid poles)
    sol.use_quality_normals = True
    sol.material_offset = 1
    sol.material_offset_rim = 2
    sol.vertex_group = "thick"
    sol.thickness_vertex_group = p["cloth_thin"]
    dg = bpy.context.evaluated_depsgraph_get()
    nm = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear()
    old = ob.data
    ob.data = nm
    nm.name = name
    bpy.data.meshes.remove(old)
    ob.vertex_groups.clear()
    for poly in nm.polygons:
        poly.use_smooth = True
    return ob


def pack_atlas(islands, res, pad_px):
    """Shelf-pack metric UV islands {name: (U, V)} into one [0, 1] atlas at one texel
    density, with pad_px texels between islands and round the border. Returns
    ({name: (U', V')}, px per metre)."""
    pad = pad_px / res
    boxes = {k: (U.min(), U.max(), V.min(), V.max()) for k, (U, V) in islands.items()}
    order = sorted(boxes, key=lambda k: -(boxes[k][3] - boxes[k][2]))

    def place(s):
        x, y, shelf, out = pad, pad, 0.0, {}
        for k in order:
            u0, u1, v0, v1 = boxes[k]
            w, h = (u1 - u0) * s, (v1 - v0) * s
            if x + w + pad > 1:
                x, y, shelf = pad, y + shelf + pad, 0.0
            if x + w + pad > 1 or y + h + pad > 1:
                return None
            out[k] = (x - u0 * s, y - v0 * s)
            x += w + pad
            shelf = max(shelf, h)
        return out
    lo, hi = 1e-3, 10.0
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if place(mid) else (lo, mid)
    s = lo * 0.999
    offs = place(s)
    return {k: (U * s + offs[k][0], V * s + offs[k][1]) for k, (U, V) in islands.items()}, s * res


def sleeve(wrist, pad, p):
    """A wide sleeve cuff around a wrist: a flared tube from inside the robe out to just
    past the wrist (rows along the forearm, columns round it)."""
    ax = np.asarray(wrist, float) - np.asarray(pad, float)
    ax /= np.linalg.norm(ax)
    ref = np.array([0, 0, 1.0]) if abs(ax[2]) < 0.9 else np.array([1.0, 0, 0])
    e1 = np.cross(ax, ref)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(ax, e1)
    n_r, n_c = p["sleeve_rows"], p["sleeve_cols"]
    L0, L1 = p["sleeve_len"]
    ts = np.linspace(0, 1, n_r)
    down = np.array([0, 0, -1.0])
    th0 = math.atan2(down @ e2, down @ e1)                 # the seam underneath the sleeve
    th = th0 + np.linspace(0, 2 * math.pi, n_c, endpoint=False)
    verts = np.zeros((n_r, n_c, 3))
    rng = np.random.default_rng(int(abs(wrist[0]) * 1000) % 997)
    wob = rng.standard_normal(6)
    for i, t in enumerate(ts):
        along = -L0 + (L0 + L1) * t                     # from the opening (t=0) back into the robe
        r = p["sleeve_r"][0] + (p["sleeve_r"][1] - p["sleeve_r"][0]) * t
        rr = r * (1 + 0.08 * np.sin(3 * th + wob[0]) + 0.05 * np.sin(5 * th + wob[1]))
        sag = -0.25 * r * (1 - t) * (0.5 - 0.5 * np.cos(th - math.pi / 2))      # the opening droops
        verts[i] = (np.asarray(wrist) + ax * along)[None, :] + np.outer(np.cos(th) * rr, e1) \
            + np.outer(np.sin(th) * rr, e2) + np.outer(sag, np.array([0, 0, 1.0]))
    edge_w = np.zeros((n_r, n_c))
    edge_w[0] = 1.0
    edge_w[1] = 0.5
    centre = np.asarray(wrist) + ax * ((L1 - L0) / 2)
    return verts, edge_w, (lambda q: centre + ax * ((q - centre) @ ax))


def fringe(points, outward, down, n, length, rng, width=0.014):
    """Short tapered strand clusters (triangular pyramids, opaque) at points along an
    edge: verts, tris."""
    V, T = [], []
    idx = rng.choice(len(points), size=min(n, len(points)), replace=False)
    for i in idx:
        base = points[i]
        L = length * (0.5 + rng.random())
        dirn = outward[i] * 0.45 + down * 0.9 + rng.standard_normal(3) * 0.2
        dirn /= np.linalg.norm(dirn)
        tip = base + dirn * L
        side = np.cross(dirn, outward[i])
        side /= np.linalg.norm(side) + 1e-9
        up = np.cross(side, dirn)
        w = width * (0.7 + 0.6 * rng.random())
        o = len(V)
        ring = [base + (side * math.cos(2 * math.pi * q / 3) + up * math.sin(2 * math.pi * q / 3)) * w for q in range(3)]
        V += ring + [tip]
        axis_p = (np.mean(ring, axis=0) + tip) / 2
        for tri in ([o, o + 1, o + 3], [o + 1, o + 2, o + 3], [o + 2, o, o + 3], [o, o + 1, o + 2]):
            P = [V[tri[0]], V[tri[1]], V[tri[2]]]
            if np.cross(P[1] - P[0], P[2] - P[0]) @ (np.mean(P, axis=0) - axis_p) < 0:
                tri = [tri[0], tri[2], tri[1]]
            T.append(tri)          # a closed tetrahedron: no open base to see into
    return np.array(V), np.array(T)


def inner_core(trees, centre, p):
    """A dark star-shaped shell just inside the cloth and the head round the neck and
    chest: any gap between the chin, the hood's lip and the robe's collar shows shadowed
    cloth, never the creature's empty inside (or, in the engine, the sky through culled
    back faces)."""
    d, t = _icosphere(p["core_subdiv"])
    r = np.full(len(d), np.inf)
    for tr in trees:
        rc = tr.ray_cast
        for i, dd in enumerate(d):
            h = rc(Vector(centre.tolist()), Vector(dd.tolist()), 6.0)
            if h[0] is not None:
                r[i] = min(r[i], h[3])
    r = np.where(np.isfinite(r), r, 0.35)          # nothing there (shouldn't happen): stay small
    r = np.minimum(r, p["core_rmax"])
    e, deg = _vertex_neighbours(t, len(d))
    # min over neighbours (stay inside between rays), then inset
    for _ in range(1):
        nb = np.full(len(d), np.inf)
        np.minimum.at(nb, e[:, 0], r[e[:, 1]])
        r = np.minimum(r, nb)
    r = np.maximum(r - p["core_inset"], 0.05)
    return centre + d * r[:, None], t
