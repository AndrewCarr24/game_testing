"""A pump-action shotgun for the armory's safe wall (set dressing: no interact). A plain modern
pump gun: black polymer stock with a rubber recoil pad and a ribbed polymer forend on the
magazine tube, a gunmetal receiver, an 18" plain barrel with a brass bead, a barrel clamp and a
magazine cap with a sling swivel, and a polymer side saddle on the left of the receiver holding
six red shells (brass heads down).

Stands UPRIGHT like the rifle: muzzle up, the butt's base on the origin (the origin is on the bore
line), its left side (the side saddle) facing -Y, the top toward +X, the stock's toe toward -X.
1.0 m tall. Modelled lying in armory_rifle's gun frame (x = muzzle, y = left, z = top)."""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import armory_rifle as ar  # noqa: E402

importlib.reload(ar)
bk, common, Gun = ar.bk, ar.common, ar.Gun
materials = bk.materials

NAME = "ArmoryShotgun"
P = dict(name=NAME, shells=6)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    gm, pm, gd, pd, rd, br = (Gun(0.5) for _ in range(6))

    # ---- stock: recoil pad, a straight comb, a pistol-grip wrist into the receiver -----------------
    pm.profile([(0.0, -0.011), (0.024, -0.011), (0.024, -0.152), (0.0, -0.150)], 0.044)                # recoil pad
    pm.profile([(0.024, -0.012), (0.24, -0.004), (0.30, 0.000), (0.362, 0.012), (0.362, -0.044),
                (0.335, -0.052), (0.300, -0.064), (0.272, -0.084), (0.250, -0.090), (0.200, -0.086),
                (0.024, -0.150)], 0.040)
    gd.tube(0.085, 0.097, 0.005, segs=8, z=-0.131 + 0.004)                                             # swivel stud
    gd.ring(0.091, -0.146, 0.012, 0.0022)

    # ---- receiver, trigger group, action bars -------------------------------------------------------
    gm.profile([(0.360, 0.018), (0.556, 0.018), (0.560, 0.010), (0.560, -0.036), (0.540, -0.046),
                (0.360, -0.046)], 0.034)
    gm.profile([(0.370, 0.018), (0.548, 0.018), (0.548, 0.022), (0.370, 0.022)], 0.020)                # top flat
    pm.profile([(0.372, -0.046), (0.452, -0.046), (0.452, -0.052), (0.440, -0.078), (0.380, -0.080),
                (0.372, -0.070)], 0.022)                                                               # trigger guard
    pd.profile([(0.408, -0.050), (0.414, -0.050), (0.410, -0.064), (0.404, -0.069), (0.401, -0.066),
                (0.405, -0.058)], 0.006, y=0.0)                                                        # trigger
    for sy in (-1, 1):
        gd.box((0.585, sy * 0.0115, -0.026), (0.05, 0.003, 0.006))                                    # action bars
    gd.rod((0.420, 0.0, 0.003), (0.420, 0.0175, 0.003), 0.003, segs=8)                                 # trigger-group pins
    gd.rod((0.505, 0.0, 0.003), (0.505, 0.0175, 0.003), 0.003, segs=8)

    # ---- barrel, magazine tube, forend, clamp, cap, bead ---------------------------------------------
    gm.tube(0.556, 1.0, 0.0105, segs=14)
    gm.tube(0.556, 0.575, 0.0145, segs=14)                                                             # barrel ring
    gm.tube(0.556, 0.862, 0.011, segs=12, z=-0.025)                                                    # magazine tube
    gm.tube(0.862, 0.892, 0.0128, segs=12, z=-0.025, r1=0.0115)                                        # magazine cap
    gm.profile([(0.836, 0.011), (0.852, 0.011), (0.852, -0.038), (0.836, -0.038)], 0.028)              # barrel clamp
    gd.ring(0.877, -0.0475, 0.011, 0.002)                                                              # front swivel
    br.rod((0.990, 0.0, 0.0095), (0.990, 0.0, 0.0145), 0.0022, segs=8, r1=0.0018)                      # bead
    pm.prism(0.600, 0.795, 0.0215, n=10, z=-0.021, r1=0.0205)                                          # forend
    for k in range(7):                                                                                 # grip ribs
        x = 0.625 + k * 0.022
        pd.prism(x, x + 0.008, 0.0228, n=10, z=-0.021)

    # ---- side saddle (left of the receiver) with shells, brass heads down ------------------------------
    sy0 = 0.017
    pm.box((0.455, sy0 + 0.003, -0.012), (0.150, 0.006, 0.050))                                        # back plate
    ns = p["shells"]
    pitch = 0.140 / ns
    for k in range(ns):
        x = 0.385 + pitch * (k + 0.5)
        y = sy0 + 0.006 + 0.0104
        rd.rod((x, y, -0.030), (x, y, 0.034), 0.0102, segs=10)                                          # hull
        rd.rod((x, y, 0.034), (x, y, 0.036), 0.0102, segs=10, r1=0.0085)                                # crimp
        br.rod((x, y, -0.046), (x, y, -0.030), 0.0105, segs=10)                                         # brass head
        br.rod((x, y, -0.047), (x, y, -0.046), 0.0112, segs=10)                                         # rim
    pm.box((0.455, sy0 + 0.014, 0.004), (0.150, 0.026, 0.012))                                          # retaining band
    pm.box((0.455, sy0 + 0.014, -0.038), (0.150, 0.024, 0.006))                                         # lower lip

    gm.finish(f"{n}_Metal", col, bk.gunmetal(), root)
    pm.finish(f"{n}_Polymer", col, bk.polymer(), root)
    gd.finish(f"{n}_Metal_Detail", col, bk.gunmetal(), root, bevel=0)
    pd.finish(f"{n}_Polymer_Detail", col, bk.polymer(), root, bevel=0)
    rd.finish(f"{n}_Shells", col, bk.red(), root, bevel=0)
    br.finish(f"{n}_Brass", col, materials.bronze(), root, bevel=0)
    return root, [o for o in root.children_recursive if o.type == "MESH"]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
