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
import invader_gear as gear  # noqa: E402
import invader_paint as paint  # noqa: E402

for _m in (common, body, rig, anims, gear, paint):
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
    tex=1024,               # body texture size
    gear_tex=256,           # gear palette atlas
    ao_samples=64,
    attach_tris=dict(Mask=700, Cap=420, Hood=900),
)
TEX_DIR = os.path.join(PROJECT, "assets", "models", "textures")
# the fist's grip point in the hand frame: along the fingers, toward the palm, toward the thumb (m)
GRIP = (0.072, -0.034, 0.004)
GRIP_TILT = 0.5


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
    key = _key(p["hem_z"], p["boot_z"], p["body_h"], p["hand_h"], p["lod0_body"], p["lod0_hand"], "qf3")
    path = os.path.join(CACHE, f"lowpoly_{key}.npz")
    out = {}
    if os.path.exists(path):
        try:
            z = np.load(path, allow_pickle=True)
            return {k: (z[k + "_v"], list(z[k + "_f"])) for k in H}
        except Exception:
            out = {}
    for k, (v, f) in H.items():
        if k == "hand_R":
            continue
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
    # the right hand is the left one mirrored (the high-res hands are exact mirrors)
    v, f = out["hand_L"]
    out["hand_R"] = (v * np.array([-1.0, 1.0, 1.0]), [tuple(fc[::-1]) for fc in f])
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


def _textures(p, lod0, H, L, col):
    """UVs + bakes + paint (cached by the LOD0 mesh, its UVs and the painter's source)."""
    paint_src = inspect.getsource(paint) + inspect.getsource(body)
    vco = _arrays(lod0)
    uv = np.zeros(len(lod0.data.loops) * 2)
    lod0.data.uv_layers["UVMap"].data.foreach_get("uv", uv)
    key = hashlib.sha1(paint_src.encode() + np.round(vco, 5).tobytes() + np.round(uv, 5).tobytes()
                       + repr((p["tex"], p["ao_samples"], p["hem_z"], p["boot_z"])).encode()).hexdigest()[:16]
    path = os.path.join(CACHE, f"paint_{key}.npz")
    if os.path.exists(path):
        try:
            z = np.load(path)
            return {k: z["alb_" + k] for k in paint.OUTFITS}, z["normal"], z["orm"], dict(cached=1.0)
        except Exception:
            pass
    t0 = time.time()
    size = p["tex"]
    scene = bpy.context.scene
    paint.cycles(scene, 1)
    pos_img = paint.image("_bake_pos", size)
    paint.bake(lod0, pos_img, "position", margin=16)
    hi = []
    for k, (v, f) in H.items():
        ob = _mesh_object("_hi_" + k, v, f, col)
        _fix_normals(ob)
        hi.append(ob)
    nrm_img = paint.image("_bake_nrm", size, non_color=True)
    scene.cycles.samples = 4
    paint.bake(lod0, nrm_img, "target", sources=hi, bake_type="NORMAL", margin=16, extrusion=0.012, ray=0.04,
               normal_space="TANGENT")
    for ob in hi:
        me = ob.data
        ob.select_set(False)
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)
    bpy.context.view_layer.update()
    scene.cycles.samples = p["ao_samples"]
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    ao_img = paint.image("_bake_ao", size)
    paint.bake(lod0, ao_img, "target", bake_type="AO", margin=16)
    pos = paint.pixels(pos_img)
    nrm = paint.pixels(nrm_img)
    ao = paint.pixels(ao_img)[..., 0]
    for im in (pos_img, nrm_img, ao_img):
        bpy.data.images.remove(im)
    alb, orm, stats = paint.paint(pos, nrm, ao, p, L, size)
    np.savez(path, normal=nrm, orm=orm, **{"alb_" + k: v for k, v in alb.items()})
    log(f"textures baked + painted in {time.time() - t0:.1f}s; zones " +
        " ".join(f"{k} {v * 100:.1f}%" for k, v in stats.items() if v > 0.001))
    return alb, nrm, orm, stats


def _image(name, arr, non_color):
    im = bpy.data.images.get(name)
    if im is not None:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, arr.shape[1], arr.shape[0], alpha=False, float_buffer=False)
    if non_color:
        im.colorspace_settings.name = "Non-Color"
    paint.set_pixels(im, arr)
    im.pack()
    return im


def _pbr(name, albedo, orm, normal=None, closest=False):
    m = bpy.data.materials.get(name)
    if m is not None:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    t_a = nt.nodes.new("ShaderNodeTexImage")
    t_a.image = albedo
    nt.links.new(t_a.outputs["Color"], bsdf.inputs["Base Color"])
    t_o = nt.nodes.new("ShaderNodeTexImage")
    t_o.image = orm
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(t_o.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    if closest:
        t_a.interpolation = t_o.interpolation = "Closest"
    if normal is not None:
        t_n = nt.nodes.new("ShaderNodeTexImage")
        t_n.image = normal
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(t_n.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def _body_material(p, alb, nrm, orm):
    outfit0 = next(iter(paint.OUTFITS))
    m = _pbr("M_Invader_Body", _image(f"T_Invader_Body_{outfit0}", alb[outfit0], False),
             _image("T_Invader_Body_ORM", orm, True), _image("T_Invader_Body_Normal", nrm, True))
    # the other outfits: base colour maps next to the exported ones (the engine swaps them)
    os.makedirs(TEX_DIR, exist_ok=True)
    for name, arr in alb.items():
        if name != outfit0:
            paint.save_webp(arr, os.path.join(TEX_DIR, f"T_Invader_Body_{name}.webp"), name)
    return m


def _gear_material(p):
    A, O = gear.atlas(p["gear_tex"])
    return _pbr("M_Invader_Gear", _image("T_Invader_Gear_Albedo", A, False), _image("T_Invader_Gear_ORM", O, True),
                closest=True)


def _limit_weights(ob, n=4):
    """Keep the n largest influences per vertex, normalised (decimation blends weights)."""
    names = [g.name for g in ob.vertex_groups]
    W = np.zeros((len(ob.data.vertices), len(names)))
    for v in ob.data.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    idx = np.argsort(-W, axis=1)
    keep = np.zeros_like(W, bool)
    np.put_along_axis(keep, idx[:, :n], True, axis=1)
    W = np.where(keep & (W > 0.01), W, 0.0)
    W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
    rig.assign_weights(ob, W, names)


def _sockets(L, hf, col, arm):
    """Socket empties on bones -> {name: empty}. A socket's -Y is the held thing's forward,
    +Z its up (glTF: +Z forward, +Y up)."""
    from mathutils import Matrix
    out = {}

    def make(name, bone, origin, fwd, up, size=0.06):
        f = np.asarray(fwd, float)
        f /= np.linalg.norm(f)
        u = np.asarray(up, float)
        u = u - (u @ f) * f
        u /= np.linalg.norm(u)
        ys, zs = -f, u
        xs = np.cross(ys, zs)
        M = Matrix.Identity(4)
        for r in range(3):
            M[r][0], M[r][1], M[r][2], M[r][3] = xs[r], ys[r], zs[r], origin[r]
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "ARROWS"
        e.empty_display_size = size
        col.objects.link(e)
        e.matrix_world = M
        bpy.context.view_layer.update()
        rig.attach(e, arm, bone)
        out[name] = e
        return e

    for s in "LR":
        M = hf[s]
        hx, hy, hz = M[:3, 0], M[:3, 1], M[:3, 2]
        c = M[:3, 3] + hy * GRIP[0] + hz * GRIP[1] + hx * GRIP[2]
        up = hx + GRIP_TILT * hy           # along the fist, out of the thumb side, tilted toward the fingers
        fwd = hy - GRIP_TILT * hx
        make("Socket_Hand_" + s, "Hand_" + s, c, fwd, up)
    make("Socket_Head", "Head", L["head"] + np.array([0, -0.01, 0.09]), (0, -1, 0), (0, 0, 1))
    make("Socket_Back", "Chest", np.array([0.0, 0.16, 1.3]), (0.55, 0.0, -0.83), (0, 1, 0))
    make("Socket_Hip_R", "Hips", np.array([-0.2, 0.01, 0.9]), (0, 0, -1), (0, -1, 0))
    return out


def _gear_objects(col, sockets, mat):
    out = {}
    for name, mk in gear.WEAPONS.items():
        m, marks = mk()
        ob = gear.mesh_object("Invader_" + name, m, col, mat)
        ob.parent = sockets["Socket_Hand_R"]
        ob.matrix_parent_inverse.identity()
        ob.matrix_basis.identity()
        for k, pos in marks.items():
            if k not in ("muzzle", "tip"):
                continue
            e = bpy.data.objects.new(f"Invader_{name}_{k.capitalize()}", None)
            e.empty_display_size = 0.03
            col.objects.link(e)
            e.parent = ob
            e.location = pos
        out[name] = (ob, marks)
    return out


def _attachments(p, L, col, arm, mat):
    att = gear.head_attachments(L, p)
    out = {}
    for name, (v, f, sw) in att.items():
        m = gear.Mesh().add(v, [tuple(int(i) for i in fc) for fc in f], sw)
        ob = gear.mesh_object("Invader_" + name, m, col, mat)
        _select_only(ob)
        md = ob.modifiers.new("lod", "DECIMATE")
        md.ratio = min(1.0, p["attach_tris"][name] / max(len(ob.data.polygons) * 2, 1))
        md.use_symmetry = True
        md.symmetry_axis = "X"
        bpy.ops.object.modifier_apply(modifier="lod")
        ob.data.validate()
        for poly in ob.data.polygons:
            poly.use_smooth = True
        # skin: rigid on the head; the hood's lower part follows the neck and chest
        vv = _arrays(ob)
        names = ["Head", "Neck", "Chest"]
        if name == "Hood":
            z = vv[:, 2]
            w_chest = rig.smoothstep(1.56, 1.5, z)
            w_head = rig.smoothstep(1.58, 1.64, z)
            W = np.stack([w_head, np.clip(1 - w_head - w_chest, 0, 1), w_chest], 1)
        else:
            W = np.zeros((len(vv), 3))
            W[:, 0] = 1
        W /= W.sum(1, keepdims=True)
        rig.assign_weights(ob, W, names)
        mod = ob.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        ob.parent = arm
        out[name] = ob
    return out


def build(**overrides):
    with np.errstate(all="ignore"):
        return _build({**P, **overrides})


def _build(p):
    t0 = time.time()
    col = common.fresh_collection(p["name"])
    for a in list(bpy.data.actions):
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
    lod0.data.uv_layers.new(name="UVMap")
    paint.uv_unwrap(lod0, p["tex"])
    alb, nrm, orm, _ = _textures(p, lod0, H, L, col)
    lod0.data.materials.clear()
    lod0.data.materials.append(_body_material(p, alb, nrm, orm))
    gmat = _gear_material(p)
    # rig
    hf = {s: body.hand_frame(L, s) for s in "LR"}
    bones = rig.skeleton(L, hf, body.hand_joints())
    arm = rig.build_armature(p["name"] + "_Armature", bones, col, root)
    names = [b[0] for b in bones if b[0] != "Root"]
    vco = _arrays(lod0)
    fl = [np.array(f) for f in _faces(lod0)]
    quads = np.array([f for f in fl if len(f) == 4])
    W = rig.weights(vco, quads, part, names, L, body_labels(p, L), hand_labels(p), hf)
    rig.assign_weights(lod0, W, names)
    log(f"skinned LOD0: {len(vco)} verts, {len(names)} deforming bones")
    lods = [lod0]
    for i, tris_n in ((1, p["lod1_tris"]), (2, p["lod2_tris"])):
        ob = _decimated(lod0, f"{p['name']}_Body_LOD{i}", tris_n, col, root)
        _limit_weights(ob)
        lods.append(ob)
    for ob in lods:
        mod = ob.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        ob.parent = arm
    sockets = _sockets(L, hf, col, arm)
    weapons = _gear_objects(col, sockets, gmat)
    atts = _attachments(p, L, col, arm, gmat)
    sv = rig.Solver(arm, bones, L)
    PM = sv.solve(rig.rest_controls())
    err = max(max(abs(B[i][j] - (1 if i == j else 0)) for i in range(4) for j in range(4)) for B in sv.basis(PM).values())
    log(f"rig: {len(bones)} bones, rest-pose check {err:.2e}")
    # socket frames relative to their bones (rest), for the clips that place hands by a weapon
    sv.sockets = {k: (e.parent_bone, arm.data.bones[e.parent_bone].matrix_local.inverted() @ e.matrix_world)
                  for k, e in sockets.items()}
    sv.weapons = {k: m for k, (o, m) in weapons.items()}
    acts, info = anims.bake_all(sv)
    md = dict(anims.metadata(sv))
    md.update(
        height=round(float(verts[:, 2].max()), 3), radius=0.3,
        lods=[dict(mesh=o.name, tris=_tri_count(o)) for o in lods], lodDistance=list(p["lod_distance"]),
        outfits=[dict(name=k, map=f"T_Invader_Body_{k}") for k in paint.OUTFITS],
        attachments=["Invader_" + k for k in atts], weapons=["Invader_" + k for k in weapons],
        sockets=list(sockets), upperBody=list(anims.UPPER_BODY),
    )
    for k, v in md.items():
        root[k] = v
    rig.LAST = dict(solver=sv, info=info, lods=lods, arm=arm, part=part, weapons=weapons, atts=atts,
                    sockets=sockets, root=root, p=p)
    log(f"built in {time.time() - t0:.1f}s")
    return root, lods + [o for o, _ in weapons.values()] + list(atts.values())


def _tri_count(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)
