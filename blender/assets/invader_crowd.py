"""The crowd path of the invader: a bone animation texture (blender/assets/invader.py, stage 6).

For drawing 20-50 invaders as a few InstancedMeshes (GPU skinning from a texture, one draw call
per outfit / weapon / attachment kind) instead of 50 SkinnedMeshes with 50 mixers.

assets/models/invader_anim.bin   float16, row-major RGBA texels: one row per frame (every clip's
                                 frames one after another), 3 texels per joint = the 3 rows of
                                 the joint's skinning matrix (glTF frame: bone pose x inverse
                                 bind), joints in `joints` order, then extra rows `extra`
                                 (Socket_Hand_R: weapon-local -> model, for rigid weapons).
assets/models/invader_anim.json  {fps, width, height, joints, extra, clips: {name: {start,
                                 frames, duration, loop}}}

Vertices of the exported meshes are in the model frame (glTF), so a vertex's skinned position
is sum_i w_i * M[joint_i] * p, the same as three.js's SkinnedMesh with the bind pose at rest.
"""
import json
import os

import numpy as np
from mathutils import Matrix

# Blender (Z up, -Y forward) -> glTF (Y up, +Z forward): (x, y, z) -> (x, z, -y)
C = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
Ci = C.inverted()


def write(sv, info, sockets_rel, out_dir, fps=15):
    names = [n for n in sv.order if n != "Root"]
    extra = ["Socket_Hand_R"]
    rows, clips = [], {}
    for name, d in info.items():
        fr = d["frames"]
        step = max(1, int(round(30 / fps)))
        pick = list(range(0, len(fr), step))
        if pick[-1] != len(fr) - 1 and not d["loop"]:
            pick.append(len(fr) - 1)
        if d["loop"] and pick[-1] == len(fr) - 1:
            pick = pick[:-1]                       # the last keyed frame of a loop repeats the first
        clips[name] = dict(start=len(rows), frames=len(pick), duration=round(d["T"], 4), loop=bool(d["loop"]))
        for i in pick:
            PM = fr[i]
            row = []
            for n in names:
                M = C @ PM[n] @ sv.Ri[n] @ Ci
                row.append(np.array(M)[:3, :4])
            bone, S = sockets_rel["Socket_Hand_R"]
            M = C @ PM[bone] @ S @ Ci
            row.append(np.array(M)[:3, :4])
            rows.append(np.concatenate(row, 0))   # (3 * njoints, 4)
    A = np.array(rows, np.float32)                  # (frames, 3 * nj, 4)
    h, w = A.shape[0], A.shape[1]
    os.makedirs(out_dir, exist_ok=True)
    A.astype(np.float16).tofile(os.path.join(out_dir, "invader_anim.bin"))
    meta = dict(fps=fps, width=w, height=h, joints=names, extra=extra, clips=clips,
                format="float16 RGBA, row = frame, 3 texels per joint (matrix rows)")
    with open(os.path.join(out_dir, "invader_anim.json"), "w") as fh:
        json.dump(meta, fh, separators=(",", ":"))
    print(f"INVADER crowd: bone animation texture {w} x {h} texels ({A.nbytes // 2 / 1024:.0f} KB float16), "
          f"{len(clips)} clips at {fps} fps", flush=True)
    return meta
