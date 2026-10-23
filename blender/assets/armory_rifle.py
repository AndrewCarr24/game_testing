"""An AR-pattern carbine for the armory's safe wall (set dressing: no interact; the weapons
workstream turns it into a pickup later). Modern and unbranded: a 16" barrel with a plain
flash hider, a free-float M-LOK handguard (slots along the sides and bottom, a full-length top
rail), a collapsible polymer stock, a 20-round polymer magazine, a small tube red dot on a low
mount, folded back-up sights, QD sling swivels at the stock and the handguard. Gunmetal metal,
black polymer furniture; `variant="tan"` gives it a flat-dark-earth stock and handguard.

Stands UPRIGHT as it does in the safe: muzzle up, the buttstock's base on the origin (the origin
is on the bore line, so the barrel stands straight over it), its left side facing -Y, the top
(optic) toward +X, the grip and magazine toward -X. 0.86 m tall.

Also hosts `Gun`, the profile/prism toolkit the other armory weapons import (armory_shotgun,
armory_pistol). Parts are modelled lying down in a gun frame (x = toward the muzzle, y = the
gun's left, z = its top) and stood up at the end (`Gun.stand`)."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bunker_kit as bk  # noqa: E402
import library_kit as lk  # noqa: E402
import armory_safe_wall as sw  # noqa: E402  (cyl, knurled_torus)

importlib.reload(bk)
importlib.reload(lk)
importlib.reload(sw)
common = bk.common

NAME = "ArmoryRifle"

P = dict(
    name=NAME,
    variant="black",          # "black" | "tan" (flat dark earth stock and handguard)
)

# gun frame -> asset frame, standing: muzzle (+x) up (+Z), left side (+y) facing -Y, top (+z) toward +X
STAND = Matrix(((0, 0, 1, 0), (0, -1, 0, 0), (1, 0, 0, 0), (0, 0, 0, 1)))


class Gun(lk.Mesh):
    """lk.Mesh (one material, boxes with UVs) plus profiles extruded across the gun, prisms and
    cylinders along it, rings. All in the gun frame (x forward, y left, z up)."""

    def profile(self, pts, w, y=0.0):
        """A side-view outline [(x, z)] extruded across the gun, `w` thick, centred on y."""
        bm = self.bm
        a = [bm.verts.new((x, y - w / 2, z)) for x, z in pts]
        b = [bm.verts.new((x, y + w / 2, z)) for x, z in pts]
        faces = [bm.faces.new(a), bm.faces.new(list(reversed(b)))]
        n = len(pts)
        for k in range(n):
            j = (k + 1) % n
            faces.append(bm.faces.new((a[k], b[k], b[j], a[j])))
        for f in faces:
            f.smooth = False
        bmesh.ops.recalc_face_normals(bm, faces=faces)
        return faces

    def prism(self, x0, x1, r, n=8, y=0.0, z=0.0, offset=None, r1=None):
        """An n-sided prism along x (flats facing up/down/sides when offset is None)."""
        bm = self.bm
        off = math.pi / n if offset is None else offset
        r1 = r if r1 is None else r1
        rings = [[bm.verts.new((x, y + rr * math.cos(off + 2 * math.pi * k / n), z + rr * math.sin(off + 2 * math.pi * k / n)))
                  for k in range(n)] for x, rr in ((x0, r), (x1, r1))]
        faces = [bm.faces.new(rings[0]), bm.faces.new(list(reversed(rings[1])))]
        for k in range(n):
            j = (k + 1) % n
            faces.append(bm.faces.new((rings[0][k], rings[1][k], rings[1][j], rings[0][j])))
        for f in faces:
            f.smooth = False
        bmesh.ops.recalc_face_normals(bm, faces=faces)
        return faces

    def tube(self, x0, x1, r, segs=12, y=0.0, z=0.0, r1=None):
        """A round cylinder along x (smooth sides)."""
        return sw.cyl(self, (x0, y, z), (x1, y, z), r, r1, segs=segs)

    def rod(self, a, b, r, segs=8, r1=None):
        return sw.cyl(self, a, b, r, r1, segs=segs)

    def ring(self, x, z, R, r, segs=12, minor=5, y=0.0):
        """A loop (sling swivel) lying in the gun's side plane (its axis across the gun)."""
        return sw.knurled_torus(self, (x, y, z), R, r, segs=segs, minor=minor, knurl=0.0)

    def quad_y(self, x0, x1, z0, z1, y):
        """A flat rectangle facing +y (sign of y) at y: slots, markings."""
        bm = self.bm
        vs = [bm.verts.new(c) for c in ((x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1))]
        f = bm.faces.new(vs if y > 0 else list(reversed(vs)))
        f.smooth = False
        return f

    def stand(self, matrix=STAND):
        bmesh.ops.transform(self.bm, matrix=matrix, verts=self.bm.verts)
        return self

    def finish(self, name, col, mat, parent, bevel=0.0012, matrix=STAND):
        self.stand(matrix)
        ob = common.mesh_object(name, self.bm, col, mat, parent, smooth=False)
        if bevel:
            common.add_bevel(ob, bevel, segments=1).angle_limit = math.radians(50)
        return ob


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    gunmetal, polymer = bk.gunmetal(), bk.polymer()
    tan = p["variant"] == "tan"

    gm, pm, tn = Gun(0.5), Gun(0.5), Gun(0.5)
    gd, pd = Gun(0.5), Gun(0.5)                  # small details: no bevel (same materials, batched together)
    furn = tn if tan else pm                     # stock + handguard furniture

    # ---- stock: collapsible polymer stock on the buffer tube, rubber butt pad ---------------------
    furn.profile([(0.012, -0.098), (0.06, -0.074), (0.15, -0.040), (0.200, -0.031), (0.214, -0.020),
                  (0.214, 0.018), (0.195, 0.024), (0.06, 0.027), (0.012, 0.027)], 0.036)
    furn.profile([(0.03, 0.012), (0.17, 0.016), (0.17, 0.030), (0.03, 0.030)], 0.026)         # cheek riser on top
    pm.profile([(0.0, -0.101), (0.013, -0.101), (0.013, 0.029), (0.0, 0.029)], 0.040)          # butt pad
    pm.profile([(0.135, -0.036), (0.185, -0.031), (0.185, -0.024), (0.135, -0.028)], 0.040)     # adjustment lever
    gm.tube(0.12, 0.27, 0.0145, segs=14, z=-0.004)                                             # buffer tube
    gm.tube(0.262, 0.272, 0.0172, segs=14, z=-0.004)                                           # castle nut
    gd.tube(0.04, 0.052, 0.006, segs=8, z=-0.083, y=0)                                         # QD socket
    gd.ring(0.046, -0.099, 0.012, 0.0022)                                                      # rear sling swivel

    # ---- lower receiver, grip, trigger, magazine ------------------------------------------------
    gm.profile([(0.268, 0.0), (0.474, 0.0), (0.474, -0.018), (0.448, -0.028), (0.448, -0.072),
                (0.364, -0.072), (0.358, -0.047), (0.330, -0.043), (0.298, -0.039), (0.272, -0.026)], 0.024)
    gm.profile([(0.300, -0.068), (0.372, -0.068), (0.372, -0.074), (0.300, -0.074)], 0.012)    # trigger guard
    gm.profile([(0.300, -0.044), (0.306, -0.044), (0.306, -0.074), (0.300, -0.074)], 0.012)
    gd.profile([(0.336, -0.044), (0.342, -0.044), (0.338, -0.058), (0.333, -0.064), (0.330, -0.062), (0.334, -0.052)], 0.006)
    pm.profile([(0.290, -0.036), (0.333, -0.040), (0.318, -0.080), (0.301, -0.136), (0.294, -0.142),
                (0.268, -0.140), (0.264, -0.130), (0.282, -0.072), (0.276, -0.040)], 0.030)    # pistol grip
    pm.profile([(0.368, -0.060), (0.444, -0.060), (0.452, -0.115), (0.464, -0.162), (0.470, -0.170),
                (0.382, -0.170), (0.378, -0.160), (0.370, -0.115)], 0.022)                     # 20-rd magazine
    pm.profile([(0.378, -0.168), (0.474, -0.168), (0.474, -0.180), (0.378, -0.180)], 0.026)    # floor plate
    for xx, zz, ln in ((0.398, -0.115, 0.06), (0.420, -0.112, 0.06)):                          # mag ribs (left face)
        pd.profile([(xx, zz + ln / 2), (xx + 0.004, zz + ln / 2), (xx + 0.006, zz - ln / 2), (xx + 0.002, zz - ln / 2)],
                   0.0016, y=0.0115)
    # left-side controls: selector, bolt catch, takedown pins
    gd.profile([(0.300, -0.022), (0.324, -0.018), (0.324, -0.012), (0.300, -0.016)], 0.004, y=0.0135)
    gd.profile([(0.430, -0.016), (0.452, -0.016), (0.452, -0.004), (0.430, -0.008)], 0.004, y=0.0135)
    for xx in (0.276, 0.458):
        gd.rod((xx, 0.0, -0.008), (xx, 0.0135, -0.008), 0.0035, segs=8)

    # ---- upper receiver, charging handle, top rail -------------------------------------------------
    gm.profile([(0.262, 0.0), (0.476, 0.0), (0.476, 0.031), (0.268, 0.031), (0.262, 0.024)], 0.026)
    gm.profile([(0.300, 0.0), (0.330, 0.0), (0.330, 0.020), (0.300, 0.020)], 0.030)            # forward-assist boss
    gm.profile([(0.249, 0.022), (0.266, 0.022), (0.266, 0.031), (0.249, 0.031)], 0.052)        # charging-handle latch
    gm.box((0.369, 0, 0.034), (0.214, 0.021, 0.007))                                           # picatinny base
    x = 0.268
    while x < 0.470:                                                                           # rail teeth
        gd.box((x + 0.0027, 0, 0.0395), (0.0053, 0.021, 0.004))
        x += 0.010
    gm.profile([(0.278, 0.037), (0.302, 0.037), (0.302, 0.046), (0.292, 0.050), (0.278, 0.046)], 0.020)  # folded rear sight

    # ---- handguard, barrel, flash hider, front sight ------------------------------------------------
    hg_r, hg_z = 0.026, 0.004
    furn.prism(0.476, 0.765, hg_r, n=8, z=hg_z)
    furn.box((0.6205, 0, 0.033), (0.289, 0.020, 0.008))                                        # top rail
    flat = hg_r * math.cos(math.pi / 8)
    for k in range(5):                                                                         # M-LOK slots
        x0 = 0.50 + k * 0.052
        for side in (1, -1):
            pd.quad_y(x0, x0 + 0.032, hg_z - 0.0035, hg_z + 0.0035, side * (flat + 0.0004))
        pd.box((x0 + 0.016, 0, hg_z - flat - 0.0002), (0.032, 0.007, 0.0008))
    gm.tube(0.765, 0.838, 0.0095, segs=12)                                                     # barrel
    gm.tube(0.756, 0.766, 0.017, segs=12)                                                      # barrel nut ring at the handguard end
    gm.tube(0.838, 0.862, 0.0112, segs=12, r1=0.0102)                                          # flash hider
    gm.profile([(0.655, 0.037), (0.677, 0.037), (0.677, 0.044), (0.668, 0.049), (0.655, 0.044)], 0.018)  # folded front sight (below the safe's barrel rest)
    gd.tube(0.700, 0.712, 0.006, segs=8, z=hg_z - flat - 0.004)                                # QD socket (front)
    gd.ring(0.706, hg_z - flat - 0.019, 0.012, 0.0022)                                         # front sling swivel

    # ---- red dot: low mount, tube body with turrets, dark lens ends --------------------------------
    gm.box((0.362, 0, 0.0445), (0.046, 0.024, 0.011))
    gm.tube(0.336, 0.392, 0.0165, segs=16, z=0.066)
    gm.tube(0.332, 0.338, 0.0185, segs=16, z=0.066)                                            # rear bell
    gm.tube(0.390, 0.398, 0.0190, segs=16, z=0.066)                                            # front bell
    gd.rod((0.364, 0, 0.080), (0.364, 0, 0.092), 0.0075, segs=12)                              # elevation turret
    gd.rod((0.364, -0.014, 0.066), (0.364, -0.026, 0.066), 0.0075, segs=12)                    # windage (right)
    pd.tube(0.3315, 0.3325, 0.0155, segs=16, z=0.066)                                          # lens faces
    pd.tube(0.3975, 0.3985, 0.0160, segs=16, z=0.066)

    gm.finish(f"{n}_Metal", col, gunmetal, root)
    pm.finish(f"{n}_Polymer", col, polymer, root)
    gd.finish(f"{n}_Metal_Detail", col, gunmetal, root, bevel=0)
    pd.finish(f"{n}_Polymer_Detail", col, polymer, root, bevel=0)
    if tan:
        tn.finish(f"{n}_Furniture", col, bk.tan(), root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
