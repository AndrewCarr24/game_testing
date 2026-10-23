"""A polymer-frame striker pistol for the armory (set dressing: no interact). Modern and
unbranded: a squared gunmetal slide with rear and front cocking serrations, low sights, the
barrel's crown at the muzzle, a black polymer frame with an accessory rail, a squared trigger
guard, a textured grip (raised panels) with a slight beavertail and a flared magazine base,
a slide-stop lever and a takedown lever on the left.

Lies on its RIGHT side (its left side up): origin at the centre of its underside (the right
side's bounding face), the muzzle toward +X, the top of the slide toward -Y, the grip toward +Y.
0.19 long x 0.14 high (the pistol's own length and height, here along x and y) x 0.03 thick (z).
Modelled in armory_rifle's gun frame (x = muzzle, y = left, z = top), then laid down."""
import importlib
import os
import sys

import bmesh
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import armory_rifle as ar  # noqa: E402

importlib.reload(ar)
bk, common, Gun = ar.bk, ar.common, ar.Gun

NAME = "ArmoryPistol"
P = dict(name=NAME)

# gun frame -> lying on its right side: x stays, the gun's left (+y) up (+Z), its top (+z) toward -Y
LIE = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    gm, pm, gd, pd = (Gun(0.5) for _ in range(4))

    # ---- slide, sights, muzzle ---------------------------------------------------------------------
    gm.profile([(-0.093, 0.0), (0.093, 0.0), (0.0955, 0.006), (0.0955, 0.025), (0.090, 0.032),
                (-0.088, 0.032), (-0.093, 0.026)], 0.0245)
    for x0, k in ((-0.086, 6), (0.060, 4)):                         # cocking serrations (both faces)
        for i in range(k):
            x = x0 + i * 0.0042
            for sy in (1, -1):
                pd.quad_y(x, x + 0.0018, 0.008, 0.028, sy * 0.01235)
    gd.profile([(0.078, 0.032), (0.086, 0.032), (0.086, 0.038), (0.080, 0.038)], 0.0045)         # front sight
    gd.profile([(-0.088, 0.032), (-0.074, 0.032), (-0.074, 0.039), (-0.084, 0.039), (-0.088, 0.036)], 0.018)  # rear sight
    gd.tube(0.0955, 0.0962, 0.0060, segs=12, z=0.016)                                            # barrel crown
    pd.tube(0.0962, 0.0965, 0.0042, segs=12, z=0.016)                                            # bore

    # ---- frame: dust cover with rail, trigger guard, grip, magazine base ----------------------------
    pm.profile([(-0.092, 0.0), (0.089, 0.0), (0.089, -0.017), (0.026, -0.019), (0.020, -0.022),
                (-0.040, -0.022), (-0.090, -0.013)], 0.0275)
    for i in range(3):                                                                           # rail slots
        x = 0.048 + i * 0.012
        pd.box((x, 0, -0.0172), (0.004, 0.0285, 0.0012))
    pm.profile([(-0.094, -0.006), (-0.032, -0.018), (-0.034, -0.034), (-0.039, -0.044), (-0.041, -0.056),
                (-0.046, -0.068), (-0.049, -0.082), (-0.052, -0.101), (-0.098, -0.103), (-0.097, -0.093),
                (-0.086, -0.032), (-0.095, -0.014)], 0.0295)                                     # grip
    pm.profile([(-0.034, -0.040), (0.012, -0.040), (0.012, -0.021), (0.020, -0.021), (0.021, -0.046),
                (-0.034, -0.046)], 0.020)                                                        # trigger guard
    pd.profile([(-0.004, -0.021), (0.002, -0.021), (0.001, -0.031), (-0.003, -0.037), (-0.006, -0.035),
                (-0.004, -0.029)], 0.006)                                                        # trigger
    pm.profile([(-0.053, -0.099), (-0.098, -0.101), (-0.100, -0.109), (-0.051, -0.107)], 0.032)    # magazine base
    for sy in (1, -1):                                                                           # grip texture panels
        pd.profile([(-0.083, -0.036), (-0.040, -0.046), (-0.046, -0.088), (-0.090, -0.090)], 0.001,
                   y=sy * 0.01495)
    gd.profile([(-0.012, -0.006), (0.010, -0.006), (0.010, -0.002), (-0.012, -0.002)], 0.002, y=0.0145)  # slide stop
    gd.profile([(0.020, -0.008), (0.030, -0.008), (0.030, -0.004), (0.020, -0.004)], 0.0015, y=0.0143)   # takedown

    meshes = [(gm, f"{n}_Metal", bk.gunmetal(), 0.0008), (pm, f"{n}_Polymer", bk.polymer(), 0.0008),
              (gd, f"{n}_Metal_Detail", bk.gunmetal(), 0), (pd, f"{n}_Polymer_Detail", bk.polymer(), 0)]
    for g, *_ in meshes:
        g.stand(LIE)
    # origin: the centre of the underside
    vs = [v.co for g, *_ in meshes for v in g.bm.verts]
    lo = [min(v[i] for v in vs) for i in range(3)]
    hi = [max(v[i] for v in vs) for i in range(3)]
    shift = (-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2])
    for g, name, mat, bevel in meshes:
        bmesh.ops.translate(g.bm, vec=shift, verts=g.bm.verts)
        g.finish(name, col, mat, root, bevel=bevel, matrix=Matrix.Identity(4))
    return root, [o for o in root.children_recursive if o.type == "MESH"]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
