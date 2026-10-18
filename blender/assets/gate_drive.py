"""The drive from the motor court to the gate (8 m overall like the court's drive mouth: 7 m of
pale gravel between 0.5 m limestone kerbs at the same heights as court_paving), flush
limestone cross-bands every 5 m, and a limestone apron under the gate with its steel track.
Runs along Y, centred on X = 0 and on Y = 0 (20 m); the gate line is at y = gate_y.
Units are metres. The front faces -Y. Origin: the drive centre on the lawn.
"""
import importlib
import os
import sys

import bpy  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_common as gc  # noqa: E402

importlib.reload(gc)
common, outdoor = gc.common, gc.outdoor

NAME = "GateDrive"

P = dict(
    name=NAME,
    length=20.0,
    width=8.0,
    kerb=0.5,
    kerb_h=0.05,
    gravel_z=0.03,
    gate_y=-6.0,
    apron_w=8.0,
    apron_l=1.8,
    band_w=0.36,
    bands=(8.0, 3.0, -2.0),
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    parts = gc.Parts(n, col, root)
    stone, gravel, metal = outdoor.stone(), outdoor.gravel(), outdoor.dark_metal()
    half, L, k = p["width"] / 2, p["length"], p["kerb"]
    y0, y1 = -L / 2, L / 2
    ga, gb = p["gate_y"] - p["apron_l"] / 2, p["gate_y"] + p["apron_l"] / 2
    bw = p["band_w"]
    X, Y, Z = gc.V(1, 0, 0), gc.V(0, 1, 0), gc.V(0, 0, 1)

    # transverse sections from south to north: gravel panels, stone bands, the apron
    cuts = sorted([(ga, gb, "apron")] + [(b - bw / 2, b + bw / 2, "band") for b in p["bands"]])
    secs, y = [], y0
    for a, b, kind in cuts:
        if a > y + 1e-6:
            secs.append((y, a, "gravel"))
        secs.append((a, b, kind))
        y = b
    if y1 > y + 1e-6:
        secs.append((y, y1, "gravel"))

    gbm = parts.bm("Gravel", gravel, 2.0)
    sbm = parts.bm("Stone", stone, 2.0)
    gz = p["gravel_z"]
    for a, b, kind in secs:
        if kind == "gravel":
            gc.grid_face(gbm, gc.V(-(half - k), a, gz), X, Y, 2 * (half - k), b - a)
        elif kind == "band":
            gc.grid_face(sbm, gc.V(-(half - k), a, gz + 0.004), X, Y, 2 * (half - k), b - a, step=2.0)
        else:  # apron: full width, top level with the kerbs
            gc.grid_face(sbm, gc.V(-p["apron_w"] / 2, a, p["kerb_h"]), X, Y, p["apron_w"], b - a)
    # apron edges (the faces that stand proud of the gravel / lawn)
    ap = p["apron_w"] / 2
    gc.grid_face(sbm, gc.V(-ap, ga, 0), X, Z, p["apron_w"], p["kerb_h"])                         # south edge, faces -y
    gc.grid_face(sbm, gc.V(ap, gb, 0), -X, Z, p["apron_w"], p["kerb_h"])                         # north edge, faces +y
    gc.grid_face(sbm, gc.V(-ap, gb, 0), -Y, Z, p["apron_l"], p["kerb_h"], step=2.0)              # west edge, faces -x
    gc.grid_face(sbm, gc.V(ap, ga, 0), Y, Z, p["apron_l"], p["kerb_h"], step=2.0)                # east edge, faces +x

    # kerbs: two runs either side of the apron (and the outer / inner faces)
    for sign in (-1, 1):
        for (a, b) in ((y0, ga), (gb, y1)):
            xo, xi = sign * half, sign * (half - k)
            lo = gc.V(min(xo, xi), a, 0)
            hi = gc.V(max(xo, xi), b, p["kerb_h"])
            gc.box(sbm, lo, hi, sides="", top=True)
            # long faces: outer (towards the lawn) and inner (towards the gravel)
            for x_face, up in ((xo, sign), (xi, -sign)):
                if up > 0:
                    gc.grid_face(sbm, gc.V(x_face, a, 0), Y, Z, b - a, p["kerb_h"])      # faces +x
                else:
                    gc.grid_face(sbm, gc.V(x_face, b, 0), -Y, Z, b - a, p["kerb_h"])     # faces -x

    # the gate's steel track, flush in the apron
    gc.box(parts.bm("Track", metal), gc.V(-ap, p["gate_y"] - 0.05, p["kerb_h"]), gc.V(ap, p["gate_y"] + 0.05, p["kerb_h"] + 0.012),
           step=2.0, sides="")
    mesh = parts.finish()
    return root, mesh


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
