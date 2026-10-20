"""Automated QA for the Grimble (blender/assets/grimble.py), run at the end of build().

Pipeline stage 7 (QA). Prints a report and raises on errors. Checks:

meshes      non-manifold edges (> 2 faces), inconsistent winding (an edge used twice in
            the same direction), degenerate triangles, loose vertices
contact     cloak vertices inside the body's closed meshes at rest (sampled): the cloak
            must sit outside the head and feet where they meet
uvs         unique-baked layouts (the body's UVMap; the cloak's UVMap on its outside,
            material 0): overlapping texels and out-of-range UVs; texel density per mesh
bakes       cloak normal bake: ray-miss % and skewed-texel %
skin        influences per vertex <= 4, weight sums = 1, no zero-weight vertices; bones
budget      triangles <= 40k; texture count and sizes
rig         eye pivots at their mesh's centre, look = True, parented to Head; action names
            and durations
"""
import math

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ACTIONS = {"Walk": 2.8, "Knock": 3.5, "Wave": 2.5, "Idle": 4.0}


def _arrays(ob):
    me = ob.data
    v = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", v)
    me.calc_loop_triangles()
    t = np.zeros(len(me.loop_triangles) * 3, np.int64)
    me.loop_triangles.foreach_get("vertices", t)
    return v.reshape(-1, 3), t.reshape(-1, 3)


def mesh_checks(ob):
    me = ob.data
    v, t = _arrays(ob)
    he = np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]])
    und = np.sort(he, 1)
    n = len(v) + 1
    ukey = und[:, 0] * n + und[:, 1]
    _, inv, cnt = np.unique(ukey, return_inverse=True, return_counts=True)
    nonman = int((cnt > 2).sum())
    dkey = he[:, 0] * n + he[:, 1]
    _, dcnt = np.unique(dkey, return_counts=True)
    flipped = int((dcnt > 1).sum())
    area = 0.5 * np.linalg.norm(np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]]), axis=1)
    degenerate = int((area < 1e-9).sum())
    used = np.zeros(len(v), bool)
    used[t.ravel()] = True
    loose = int((~used).sum())
    boundary = int((cnt == 1).sum())
    return dict(tris=len(t), nonmanifold=nonman, flipped=flipped, degenerate=degenerate, loose=loose,
                boundary_edges=boundary)


def uv_checks(ob, layer, res, faces=None):
    """Overlapping texels / out-of-range UVs / texel density for the given polygon mask."""
    me = ob.data
    uv = np.zeros(len(me.loops) * 2)
    me.uv_layers[layer].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    me.calc_loop_triangles()
    lt = np.zeros(len(me.loop_triangles) * 3, np.int64)
    me.loop_triangles.foreach_get("loops", lt)
    lt = lt.reshape(-1, 3)
    pidx = np.zeros(len(me.loop_triangles), np.int64)
    me.loop_triangles.foreach_get("polygon_index", pidx)
    if faces is not None:
        keep = faces[pidx]
        lt = lt[keep]
    v, _ = _arrays(ob)
    li = np.zeros(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", li)
    T = uv[lt]
    oob = int(((T < 0) | (T > 1)).any(axis=(1, 2)).sum())
    # rasterise at 1024: count texel centres covered by more than one triangle
    R = 1024
    cover = np.zeros((R, R), np.int32)
    for tri in T:
        p = tri * R
        x0, y0 = np.floor(p.min(0)).astype(int)
        x1, y1 = np.ceil(p.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, R), min(y1, R)
        if x1 <= x0 or y1 <= y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        a, b, c = p
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        w1 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / d
        w2 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / d
        inside = (w1 >= 0) & (w2 >= 0) & (w1 + w2 <= 1)
        cover[y0:y1, x0:x1] += inside
    covered = int((cover > 0).sum())
    overlap = int((cover > 1).sum())
    # texel density (px / m at res): sqrt(uv area * res^2 / world area), area-weighted median
    P = v[li[lt]]
    a3 = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    e1, e2 = T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
    a2 = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
    ok = a3 > 1e-7
    dens = np.sqrt(a2[ok] * res * res / a3[ok])
    order = np.argsort(dens)
    cw = np.cumsum(a3[ok][order])
    med = float(dens[order][np.searchsorted(cw, cw[-1] / 2)]) if len(dens) else 0.0
    return dict(oob_tris=oob, overlap_pct=100.0 * overlap / max(covered, 1), coverage_pct=100.0 * covered / R / R,
                density_px_m=med)


def _inside(tree, pt, far=40.0):
    """Point-in-closed-mesh by ray parity (+X)."""
    o = Vector(pt.tolist())
    d = Vector((1.0, 0.0001, 0.0002)).normalized()
    hits = 0
    for _ in range(50):
        h = tree.ray_cast(o, d, far)
        if h[0] is None:
            break
        hits += 1
        o = h[0] + d * 1e-4
    return hits % 2 == 1


def contact_checks(body, cloak, samples=4000):
    bv, bt = _arrays(body)
    tree = BVHTree.FromPolygons([tuple(x) for x in bv], [tuple(x) for x in bt], all_triangles=True)
    me = cloak.data
    cv, ct = _arrays(cloak)
    mi = np.zeros(len(me.polygons), np.int64)
    me.polygons.foreach_get("material_index", mi)
    pidx = np.zeros(len(me.loop_triangles), np.int64)
    me.loop_triangles.foreach_get("polygon_index", pidx)
    outer_v = np.unique(ct[mi[pidx] == 0].ravel())
    rng = np.random.default_rng(3)
    pick = rng.choice(outer_v, size=min(samples, len(outer_v)), replace=False)
    lo, hi = bv.min(0) - 0.05, bv.max(0) + 0.05
    inside = 0
    for i in pick:
        q = cv[i]
        if (q < lo).any() or (q > hi).any():
            continue
        if _inside(tree, q):
            inside += 1
    return dict(cloak_in_body_pct=100.0 * inside / len(pick), sampled=len(pick))


def skin_checks(objs):
    out = {}
    for ob in objs:
        if not ob.vertex_groups:
            continue
        me = ob.data
        n_inf, sums, zero = [], [], 0
        for v in me.vertices:
            ws = [g.weight for g in v.groups if g.weight > 1e-6]
            n_inf.append(len(ws))
            sums.append(sum(ws))
            if not ws:
                zero += 1
        sums = np.array(sums)
        out[ob.name] = dict(max_influences=int(max(n_inf)), zero_weight=zero,
                            weight_sum_err=float(np.abs(sums[sums > 0] - 1).max()) if (sums > 0).any() else 1.0)
    return out


def run(root, parts, info):
    errors, lines = [], []

    def line(s_):
        lines.append(s_)

    def err(cond, msg):
        if cond:
            errors.append(msg)
    line("QA ===== Grimble ====================================")
    total = 0
    for ob in parts:
        if ob.type != "MESH":
            continue
        m = mesh_checks(ob)
        total += m["tris"]
        line(f"QA mesh {ob.name:16s} tris {m['tris']:6d} nonmanifold {m['nonmanifold']} flipped {m['flipped']} "
             f"degenerate {m['degenerate']} loose {m['loose']} boundary {m['boundary_edges']}")
        err(m["nonmanifold"] > 0, f"{ob.name}: {m['nonmanifold']} non-manifold edges")
        err(m["flipped"] > 0, f"{ob.name}: {m['flipped']} edges with inconsistent winding")
        err(m["degenerate"] > 0, f"{ob.name}: {m['degenerate']} degenerate triangles")
        err(m["loose"] > 0, f"{ob.name}: {m['loose']} loose vertices")
    line(f"QA triangles total {total} (budget 40000)")
    err(total > 40000, f"{total} triangles > 40000")
    body = next(o for o in parts if o.name.endswith("_Body"))
    cloak = next(o for o in parts if o.name.endswith("_Cloak"))
    c = contact_checks(body, cloak)
    line(f"QA contact: cloak outside vertices inside the body {c['cloak_in_body_pct']:.2f}% ({c['sampled']} sampled)")
    err(c["cloak_in_body_pct"] > 0.5, f"cloak through body: {c['cloak_in_body_pct']:.2f}% of sampled cloak vertices")
    bu = uv_checks(body, "UVMap", info["tex_body"])
    line(f"QA uv body:  density {bu['density_px_m']:.0f} px/m @{info['tex_body']}, overlap {bu['overlap_pct']:.2f}%, "
         f"out-of-range tris {bu['oob_tris']}, coverage {bu['coverage_pct']:.0f}%")
    me = cloak.data
    mi = np.zeros(len(me.polygons), np.int64)
    me.polygons.foreach_get("material_index", mi)
    cu = uv_checks(cloak, "UVMap", info["tex_cloak_unique"], faces=(mi == 0))
    line(f"QA uv cloak: density {cu['density_px_m']:.0f} px/m @{info['tex_cloak_unique']}, overlap {cu['overlap_pct']:.2f}%, "
         f"out-of-range tris {cu['oob_tris']}, coverage {cu['coverage_pct']:.0f}%")
    for nm, u in (("body", bu), ("cloak", cu)):
        err(u["overlap_pct"] > 0.5, f"{nm} UVs overlap ({u['overlap_pct']:.2f}% of texels)")
        err(u["oob_tris"] > 0, f"{nm} UVs out of range ({u['oob_tris']} triangles)")
    bs = info.get("bake", {})
    line(f"QA bake cloak normal: ray misses {bs.get('ray_miss_pct', float('nan')):.1f}% (the procedural cuffs, the hem "
         f"over the toes, the hood's back: flat there), skewed texels {bs.get('skew_raw_pct', float('nan')):.1f}% raw "
         f"-> {bs.get('skew_pct', float('nan')):.1f}% after taming")
    err(bs.get("ray_miss_pct", 100) > 12.0, f"cloak bake ray misses {bs.get('ray_miss_pct'):.1f}%")
    err(bs.get("skew_pct", 100) > 1.0, f"cloak bake skewed texels {bs.get('skew_pct'):.1f}%")
    arm = next((o for o in root.children_recursive if o.type == "ARMATURE"), None)
    if arm is not None:
        nb = len(arm.data.bones)
        line(f"QA bones {nb}")
        sk = skin_checks([o for o in parts if o.type == "MESH" and o.vertex_groups])
        for nm, s_ in sk.items():
            line(f"QA skin {nm:16s} max influences {s_['max_influences']} weight-sum error {s_['weight_sum_err']:.4f} "
                 f"zero-weight {s_['zero_weight']}")
            err(s_["max_influences"] > 4, f"{nm}: {s_['max_influences']} influences")
            err(s_["weight_sum_err"] > 0.01, f"{nm}: weights not normalised ({s_['weight_sum_err']:.3f})")
            err(s_["zero_weight"] > 0, f"{nm}: {s_['zero_weight']} vertices without weights")
        for ob in parts:
            if "_Eye_" in ob.name:
                v, _ = _arrays(ob)
                off = float(np.linalg.norm(v.mean(0)))
                look = bool(ob.get("look"))
                line(f"QA eye {ob.name}: pivot offset {off * 100:.1f} cm, look={look}, parent bone {ob.parent_bone!r}")
                err(off > 0.02 or not look or ob.parent_bone != "Head", f"{ob.name}: pivot / look / parent")
        fps = bpy.context.scene.render.fps
        for name, dur in ACTIONS.items():
            act = bpy.data.actions.get(name)
            got = (act.frame_range[1] - act.frame_range[0]) / fps if act else None
            line(f"QA action {name}: {got if got is None else round(got, 2)} s (expected {dur})")
            err(got is None or abs(got - dur) > 0.05, f"action {name} missing or wrong length")
    imgs = {}
    for ob in parts:
        for m in ob.data.materials:
            if m is None:
                continue
            for nd in m.node_tree.nodes:
                if nd.type == "TEX_IMAGE" and nd.image:
                    imgs[nd.image.name] = tuple(nd.image.size)
    line(f"QA textures {len(imgs)}: " + ", ".join(f"{k} {w}x{h}" for k, (w, h) in sorted(imgs.items())))
    for k, (w, h) in imgs.items():
        err(max(w, h) > 2048, f"texture {k} is {w}x{h}")
    line("QA ===== " + ("PASS" if not errors else f"FAIL ({len(errors)} errors)") + " =============================")
    for s_ in lines:
        print(s_, flush=True)
    for e in errors:
        print("QA ERROR", e, flush=True)
    return errors
