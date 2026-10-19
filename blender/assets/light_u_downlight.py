"""Recessed downlight: the house's small architectural light (galleries, accent and wall-wash
light in the upper rooms). Seen from below it is a warm glowing lens set in a shallow
chamfered collar, 10 cm across, standing 7 mm proud of the ceiling (enough to never z-fight
with the ceiling plane at gallery distances).

One material (the lens and its collar are the same warm emissive), because galleries always
draw: one material = one draw call per room however many are placed. The light itself is a
`spot` in the room's LIGHTS (pos just under the lens, aimed where it washes).

Origin: the ceiling attachment point (centre of the lens on the ceiling plane): place it with
z = the room's ceiling height; everything hangs below it (to z = -0.007). Units are metres.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitchen_lib as L  # noqa: E402

importlib.reload(L)
common, materials = L.common, L.materials

NAME = "LightUDownlight"

P = dict(name=NAME, radius=0.05, lens_r=0.036, drop=0.007, segs=12, emission=8.0)


def build(**overrides):
    p = {**P, **overrides}
    b = L.Builder(p["name"])
    glow = materials.emissive("M_LightU_Downlight", (1.0, 0.86, 0.68), p["emission"])
    R, r, d = p["radius"], p["lens_r"], p["drop"]
    # lens (flat disc) -> chamfered collar -> up into the ceiling slab (hidden)
    prof = [(0.0, -d), (r, -d), (R, -d * 0.35), (R, 0.004)]
    ob = b.lathe("Lens_NoCollide", prof, glow, segs=p["segs"], sharp=20, uv_tile=0, closed=False)
    # an open shell: make every face look down and out, away from a point above the lens
    # (three.js culls back faces)
    from mathutils import Vector
    up = Vector((0, 0, 0.05))
    for poly in ob.data.polygons:
        if poly.normal.dot(poly.center - up) < 0:
            poly.flip()
    ob.data.update()
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
