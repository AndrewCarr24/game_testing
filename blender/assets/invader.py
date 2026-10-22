"""The invader: a rigged, animated human (placeholder look, game-ready pipeline).

Contract for the engine: design/invaders/character.md (clips, sockets, userData, budgets).

STAGE 1  high-res body (invader_body.py): a signed distance field of the clothed body
         (jacket, cargo trousers, boots, balaclava) meshed by OpenVDB at 3.5 mm, and two
         gloved hands at 1.5 mm built in their wrist frames. Cached in build/invader_cache/.
STAGE 2  game meshes: LOD0 by QuadriFlow (even quads, edge loops follow the limbs),
         LOD1 / LOD2 by collapsing LOD0 (UVs and weights carry over).
STAGE 3  UVs (smart project, one atlas) and bakes: tangent normals from the high-res mesh,
         ambient occlusion; base colour per outfit and ORM painted in numpy from the field's
         clothing zones (invader_paint.py).
STAGE 4  rig (invader_rig.py): 34 joints, weights from the field's limb labels blended along
         each chain, <= 4 influences; sockets (non-deforming bones) for the weapons and the
         head attachments (invader_gear.py).
STAGE 5  clips (invader_anims.py): pose library + timelines + gait generator, solved per frame
         (FK + two-bone IK) and keyed (rotations; Hips also location).
STAGE 6  QA (invader_qa.py) and the crowd data (invader_crowd.py).
"""
import hashlib
import importlib
import inspect
import os
import sys
import time

import bmesh
import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common  # noqa: E402
import invader_body as body  # noqa: E402
import invader_rig as rig  # noqa: E402
import invader_anims as anims  # noqa: E402

for _m in (common, body, rig, anims):
    importlib.reload(_m)

NAME = "Invader"
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE = os.path.join(PROJECT, "build", "invader_cache")
EXPORT = dict(export_tangents=True)

P = dict(
    name=NAME,
    hem_z=0.86,             # jacket hem height (m)
    boot_z=0.22,            # boot shaft top
    body_h=0.0035,          # high-res grid cell (m)
    hand_h=0.0015,
    stage="full",           # "hires": only the high-res meshes (for shaping the body)
    lod0_body=4600,         # QuadriFlow target faces (quads) for the body; the hands below
    lod0_hand=300,
    lod1_tris=3000,
    lod2_tris=800,
    lod_distance=(12.0, 30.0),   # suggested switch distances LOD0 -> 1 -> 2 (m)
    label_sigma=0.012,      # soft limb membership: distance falloff (m) between primitives
)


def log(*a):
    print("INVADER", *a, flush=True)


def _key(*items):
    h = hashlib.sha1()
    h.update(inspect.getsource(body).encode())
    for it in items:
        h.update(repr(it).encode())
    return h.hexdigest()[:16]


def _mesh_object(name, verts, faces, col, parent=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.validate()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    return ob


def _fix_normals(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    for poly in ob.data.polygons:
        poly.use_smooth = True


def hires(p):
    """(verts, quads) of the body and of each hand, world frame (cached)."""
    os.makedirs(CACHE, exist_ok=True)
    key = _key(p["hem_z"], p["boot_z"], p["body_h"], p["hand_h"])
    path = os.path.join(CACHE, f"hires_{key}.npz")
    if os.path.exists(path):
        try:
            z = np.load(path)
            return {k: (z[k + "_v"], z[k + "_f"]) for k in ("body", "hand_L", "hand_R")}
        except Exception:
            pass
    t0 = time.time()
    L = body.landmarks()
    prims = body.body_prims(L, p)
    h = p["body_h"]
    d, lo = body.eval_grid(prims, (-0.66, -0.26, -0.01), (0.66, 0.2, 1.83), h, details=body.details(p))
    v, f = body.mesh_grid(d, lo, h)
    out = dict(body=(v, f))
    log(f"body field {d.shape} -> {len(v)} verts, {len(f)} quads ({time.time() - t0:.1f}s)")
    for sd in "LR":
        hp = body.hand_prims(p, sd)
        hh = p["hand_h"]
        d, lo = body.eval_grid(hp, (-0.065, -0.075, -0.05), (0.095, 0.22, 0.05), hh, details=[body.hand_details])
        hv, hf = body.mesh_grid(d, lo, hh)
        M = body.hand_frame(L, sd)
        hv = hv @ M[:3, :3].T + M[:3, 3]
        if np.linalg.det(M[:3, :3]) < 0:
            hf = hf[:, ::-1]
        out["hand_" + sd] = (hv, hf)
        log(f"hand {sd}: {len(hv)} verts")
    np.savez(path, **{k + "_v": v for k, (v, f) in out.items()}, **{k + "_f": f for k, (v, f) in out.items()})
    return out



def _select_only(ob):
    vl = bpy.context.view_layer
    for o in vl.objects:
        if o.select_get():
            o.select_set(False)
    vl.objects.active = ob
    ob.select_set(True)


def _arrays(ob):
    me = ob.data
    v = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", v)
    return v.reshape(-1, 3)


def _faces(ob):
    return [tuple(p.vertices) for p in ob.data.polygons]


def lowpoly(p, H, col):
    """QuadriFlow game meshes of the body and hands (cached: QuadriFlow is seeded but slow-ish)."""
    key = _key(p["hem_z"], p["boot_z"], p["body_h"], p["hand_h"], p["lod0_body"], p["lod0_hand"], "qf2")
    path = os.path.join(CACHE, f"lowpoly_{key}.npz")
    out = {}
    if os.path.exists(path):
        try:
            z = np.load(path, allow_pickle=True)
            return {k: (z[k + "_v"], list(z[k + "_f"])) for k in H}
        except Exception:
            out = {}
    for k, (v, f) in H.items():
        ob = _mesh_object("_qf_" + k, v, f, col)
        _fix_normals(ob)
        _select_only(ob)
        m = ob.modifiers.new("pre", "DECIMATE")
        m.ratio = 0.25 if k == "body" else 0.25
        bpy.ops.object.modifier_apply(modifier="pre")
        target = p["lod0_body"] if k == "body" else p["lod0_hand"]
        bpy.ops.object.quadriflow_remesh(mode="FACES", target_faces=target, use_mesh_symmetry=(k == "body"),
                                         use_preserve_sharp=False, use_preserve_boundary=False, seed=3)
        out[k] = (_arrays(ob), _faces(ob))
        log(f"lowpoly {k}: {len(ob.data.polygons)} faces")
        me = ob.data
        ob.select_set(False)
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)
        bpy.context.view_layer.update()
    np.savez(path, **{k + "_v": v for k, (v, f) in out.items()},
             **{k + "_f": np.array(f, dtype=object) for k, (v, f) in out.items()})
    return out


def body_labels(p, L):
    prims = [q for q in body.body_prims(L, p) if q.get("op", "u") == "u"]
    return lambda P: _soft_labels(prims, P, p["label_sigma"])


def hand_labels(p):
    cache = {s: [q for q in body.hand_prims(p, s) if q.get("op", "u") == "u"] for s in "LR"}
    return lambda P, s: _soft_labels(cache[s], P, 0.004)


def _soft_labels(prims, P, sigma):
    _, per = body.eval_points(prims, P)
    per = per.astype(float)
    dmin = per.min(1, keepdims=True)
    w = np.exp(-(per - dmin) / sigma)
    w[per - dmin > 6 * sigma] = 0
    out = {}
    for i, q in enumerate(prims):
        out[q["bone"]] = out.get(q["bone"], 0) + w[:, i]
    tot = sum(out.values())
    return {b: x / tot for b, x in out.items()}


def _material(name, color, roughness=0.85):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    return m


def _decimated(src, name, tris, col, parent):
    me = src.data.copy()
    me.name = name
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    ob.parent = parent
    for g in src.vertex_groups:
        ob.vertex_groups.new(name=g.name)
    # vertex groups live in the mesh data, so the copy has the weights; decimate keeps them
    _select_only(ob)
    me.calc_loop_triangles()
    m = ob.modifiers.new("lod", "DECIMATE")
    m.ratio = min(1.0, tris / max(len(me.loop_triangles), 1))
    m.use_symmetry = True
    m.symmetry_axis = "X"
    bpy.ops.object.modifier_apply(modifier="lod")
    return ob


def build(**overrides):
    with np.errstate(all="ignore"):
        return _build({**P, **overrides})


def _build(p):
    t0 = time.time()
    col = common.fresh_collection(p["name"])
    for a in list(bpy.data.actions):
        if a.name.startswith(("Idle", "Walk")) or a.users == 0:
            bpy.data.actions.remove(a)
    root = common.empty(p["name"], col)
    H = hires(p)
    if p["stage"] == "hires":
        parts = []
        for k, (v, f) in H.items():
            ob = _mesh_object(f"{p['name']}_Hi_{k}", v, f, col, root)
            _fix_normals(ob)
            parts.append(ob)
        return root, parts
    L = body.landmarks()
    LP = lowpoly(p, H, col)
    # LOD0 = body + hands (separate islands: the glove cuffs sit inside the sleeves)
    verts, faces, part = [], [], []
    off = 0
    for pi, k in enumerate(("body", "hand_L", "hand_R")):
        v, f = LP[k]
        verts.append(v)
        faces += [tuple(int(i) + off for i in fc) for fc in f]
        part.append(np.full(len(v), pi))
        off += len(v)
    verts = np.concatenate(verts)
    part = np.concatenate(part)
    lod0 = _mesh_object(p["name"] + "_Body_LOD0", verts, faces, col, root)
    _fix_normals(lod0)
    lod0.data.materials.append(_material("M_Invader_Body", (0.06, 0.06, 0.065)))
    # rig
    hf = {s: body.hand_frame(L, s) for s in "LR"}
    bones = rig.skeleton(L, hf, body.hand_joints())
    arm = rig.build_armature(p["name"] + "_Armature", bones, col, root)
    names = [b[0] for b in bones if b[0] != "Root"]
    vco = _arrays(lod0)
    fl = [np.array(f) for f in _faces(lod0)]
    quads = np.array([f for f in fl if len(f) == 4]) if any(len(f) == 4 for f in fl) else np.zeros((0, 4), int)
    tris = np.array([f for f in fl if len(f) == 3]) if any(len(f) == 3 for f in fl) else np.zeros((0, 3), int)
    edges_src = quads if len(quads) else tris
    W = rig.weights(vco, edges_src, part, names, L, body_labels(p, L), hand_labels(p), hf)
    rig.assign_weights(lod0, W, names)
    log(f"skinned LOD0: {len(vco)} verts, {len(names)} deforming bones")
    lods = [lod0]
    for i, tris_n in ((1, p["lod1_tris"]), (2, p["lod2_tris"])):
        lods.append(_decimated(lod0, f"{p['name']}_Body_LOD{i}", tris_n, col, root))
    for ob in lods:
        mod = ob.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        ob.parent = arm
    sv = rig.Solver(arm, bones, L)
    PM = sv.solve(rig.rest_controls())
    err = max(max(abs(B[i][j] - (1 if i == j else 0)) for i in range(4) for j in range(4)) for B in sv.basis(PM).values())
    log(f"rig: {len(bones)} bones, rest-pose check {err:.2e}")
    acts, info = anims.bake_all(sv)
    md = dict(anims.metadata())
    md.update(height=1.81, lods=[dict(mesh=o.name, tris=_tri_count(o)) for o in lods])
    for k, v in md.items():
        root[k] = v
    rig.LAST = dict(solver=sv, info=info, lods=lods, arm=arm, part=part)
    log(f"built in {time.time() - t0:.1f}s")
    return root, lods


def _tri_count(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)
