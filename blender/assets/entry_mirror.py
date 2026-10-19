"""Wall mirror with a slim bronze frame and a warm LED halo behind it (an emissive ring
or outline on the wall). `build(shape="round")` is the 1.3 m round vanity mirror;
`shape="tall"` is a 0.8 x 2.2 m full-length rectangle (see entry_mirror_tall.py).

The mirror glass is a smooth near-black-silver metal, so it picks up the room's probe
panorama in the engine. Hangs on a wall: origin = centre of the mirror on the wall
plane, the face looks toward -Y. Units are metres.
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import table_lamp  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "EntryMirror"

P = dict(
    name=NAME,
    shape="round",
    radius=0.65,              # round: outer radius of the frame
    size=(0.80, 2.20),        # tall: outer width x height
    frame=0.022,              # visible frame width
    depth=0.04,               # frame depth off the wall
    halo=0.035,               # LED outline width (visible round the frame)
    emission=3.0,
)


def _to_wall_plane(bm):
    """Lathe is about Z; turn it so the axis points along -Y (front toward -Y)."""
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "X"))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    bronze = materials.bronze()
    black = materials.black_metal()
    glass = common.pbr_material("M_Entry_Mirror", (0.78, 0.80, 0.82), roughness=0.03, metallic=1.0)
    halo = materials.emissive("M_Entry_Halo", (1.0, 0.80, 0.55), p["emission"])
    d = p["depth"]
    fw = p["frame"]
    hw = p["halo"]

    if p["shape"] == "round":
        R = p["radius"]
        Ri = R - fw
        # Rotating Z->-Y with +90 deg about X: +Z maps to -Y? (x, y, z) -> (x, -z, y): +z becomes -y. Good.
        seg = 64
        glass_bm = table_lamp.lathe([(0.0, d * 0.45), (Ri + 0.002, d * 0.45), (Ri + 0.002, d * 0.35), (0.0, d * 0.35)], seg)
        # glass: the disc's visible face has normal +z in lathe space -> -Y after rotation
        _to_wall_plane(glass_bm)
        common.mesh_object(f"{n}_Glass", glass_bm, col, glass, root, smooth=False)
        frame_bm = table_lamp.lathe([(Ri, d * 0.30), (Ri, d), (R - 0.004, d), (R, d - 0.004), (R, 0.012),
                                     (R - 0.004, 0.008), (Ri, 0.008)], seg, sharp=40)
        # wall side open ring section is closed by lathe(closed=True)
        _to_wall_plane(frame_bm)
        common.mesh_object(f"{n}_Frame", frame_bm, col, bronze, root, smooth=False)
        back_bm = table_lamp.lathe([(0.0, 0.010), (Ri, 0.010), (Ri, d * 0.35), (0.0, d * 0.35)], seg)
        _to_wall_plane(back_bm)
        common.mesh_object(f"{n}_Back", back_bm, col, black, root, smooth=False)
        halo_bm = table_lamp.lathe([(R + 0.004, 0.0), (R + hw, 0.0), (R + hw, 0.006), (R + 0.004, 0.006)], seg)
        _to_wall_plane(halo_bm)
        common.mesh_object(f"{n}_Halo", halo_bm, col, halo, root, smooth=False)
        # flip: after the +90 X rotation the lathe's -Z end lies toward +Y (the wall) and
        # +Z toward -Y; the thin parts above were built with z = depth off the wall.
    else:
        W, H = p["size"]
        mk = lambda name, size, loc, mat: _box(name, size, loc, mat, col, root)
        # lamp outline on the wall
        for name, size, loc in (
            ("HaloL", (hw, 0.006, H + 2 * hw), (-(W / 2 + hw / 2), -0.003, 0)),
            ("HaloR", (hw, 0.006, H + 2 * hw), ((W / 2 + hw / 2), -0.003, 0)),
            ("HaloT", (W, 0.006, hw), (0, -0.003, H / 2 + hw / 2)),
            ("HaloB", (W, 0.006, hw), (0, -0.003, -H / 2 - hw / 2))):
            mk(name, size, loc, halo)
        mk("Back", (W - 2 * fw, 0.012, H - 2 * fw), (0, -0.006, 0), black)
        mk("Glass", (W - 2 * fw + 0.004, 0.004, H - 2 * fw + 0.004), (0, -d * 0.4, 0), glass)
        for name, size, loc in (
            ("FrameL", (fw, d, H), (-(W / 2 - fw / 2), -d / 2, 0)),
            ("FrameR", (fw, d, H), ((W / 2 - fw / 2), -d / 2, 0)),
            ("FrameT", (W - 2 * fw, d, fw), (0, -d / 2, H / 2 - fw / 2)),
            ("FrameB", (W - 2 * fw, d, fw), (0, -d / 2, -H / 2 + fw / 2))):
            mk(name, size, loc, bronze)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


def _box(name, size, loc, mat, col, root):
    ob = common.mesh_object(f"{NAME}_{name}", common.box_bmesh(size), col, mat, root, smooth=False)
    ob.location = loc
    return ob


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
