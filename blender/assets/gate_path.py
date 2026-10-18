"""Stepping path of limestone slabs from the drive's kerb to the gatehouse stoop: two
95 cm slabs with 5 cm joints, 1.3 m wide. Runs along Y from the origin. Units are metres.
Origin: the start edge of the first slab, centred on X = 0; the strip runs along +Y."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_common as gc  # noqa: E402

importlib.reload(gc)
common, outdoor = gc.common, gc.outdoor

NAME = "GatePath"

P = dict(name=NAME, width=1.3, slab=0.95, joint=0.05, count=2, thick=0.05)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    parts = gc.Parts(n, col, root)
    sb = parts.bm("Slabs", outdoor.stone(), 2.0)
    V = gc.V
    y = 0.0
    for i in range(p["count"]):
        gc.box(sb, V(-p["width"] / 2, y, 0), V(p["width"] / 2, y + p["slab"], p["thick"]), step=2.0)
        y += p["slab"] + p["joint"]
    return root, parts.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
