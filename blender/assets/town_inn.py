"""The boutique inn: a big restored Victorian (two and a half storeys of cream lap siding, a
cross-gabled roof in architectural shingle with scrolled gable trim, a round corner turret
with a conical roof and a finial, a deep wraparound porch with turned posts and rocking
chairs, flower boxes, a lit sign board with a pictogram).

Walk-in: the lobby (reception desk, a staircase going up to a landing, a sofa and armchairs by
a fireplace, a rug, lamps), its light baked into COLOR_0.

Origin: floor centre at the front door's sill; front -Y. Door: TownInn_Door_1.
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import town_common as tc  # noqa: E402
import town_light  # noqa: E402

importlib.reload(tc.tt)
importlib.reload(tc)
importlib.reload(town_light)
V = tc.V

NAME = "TownInn"
P = dict(name=NAME, module="town_inn", x0=-8.0, x1=8.0, y0=-6.0, y1=8.0, storey=3.3, pitch=0.9, porch=3.0, bake=True)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    x0, x1, y0, y1, T, sh = p["x0"], p["x1"], p["y0"], p["y1"], 0.2, p["storey"]
    H = 2 * sh + 0.2
    ridge = H + (y1 - y0) / 2 * p["pitch"]
    Wl = kit.p("Walls", "lap_cream")
    kit.tints["Walls"] = (0.98, 0.96, 0.9)
    door = (-1.6, -0.4, 0.0, 2.4)
    ops = {"S": [door], "N": [(2.0, 3.0, 0.0, 2.2)], "E": [], "W": []}
    for s in range(2):
        z = s * sh + 0.9
        for a in (-6.0, -3.2, 1.6, 4.0):
            if s == 0 and -2.0 < a < 0.0:
                continue
            ops["S"].append((a - 0.5, a + 0.5, z, z + 1.7))
        for a in (-5.5, -2.0, 2.0, 5.5):
            ops["N"].append((a - 0.5, a + 0.5, z, z + 1.7)) if not (s == 0 and 1.5 < a < 3.5) else None
        for a in (-3.5, 0.5, 4.5):
            ops["E"].append((a - 0.5, a + 0.5, z, z + 1.7))
            ops["W"].append((a - 0.5, a + 0.5, z, z + 1.7))
    for side, plane, a0, a1 in (("S", y0, x0, x1), ("N", y1, x0, x1), ("E", x1, y0, y1), ("W", x0, y0, y1)):
        tc.wall(kit.p("Foundation", "brick_red"), side, plane, a0, a1, -0.6, 0.3)
        tc.wall(Wl, side, plane, a0, a1, 0.3, H, ops[side], gable=ridge if side in "EW" else None)
        tc.reveals(kit.p("Reveals", "trim"), side, plane, ops[side], T)
        for o in ops[side]:
            if o[2] > 0.1:
                tc.window(kit, side, plane, (o[0] + o[1]) / 2, o[2], o[1] - o[0], o[3] - o[2],
                          cell=("dh_lamp", "dh_lace", "dh_curtain")[int(o[0] * 3 + o[2]) % 3], trim="trim_green", casing=0.1)
                if side == "S" and o[2] > sh:
                    tc.wbox(kit.p("FlowerBoxes", "trim_green"), side, plane, o[0] - 0.05, o[1] + 0.05, o[2] - 0.35, o[2] - 0.1, 0.05, 0.3,
                            skip="back")
                    for k in range(4):
                        fa = o[0] + k * (o[1] - o[0]) / 4
                        tc.wbox(kit.p("Flowers", ("door_red", "paint_white", "trim_red", "paint_yellow")[k]), side, plane, fa, fa + 0.22,
                                o[2] - 0.1, o[2] + 0.0, 0.07, 0.28)
    tc.corner_boards(kit, x0, x1, y0, y1, 0.3, H, mat="trim_green")
    tc.band(kit, x0, x1, y0, y1, sh - 0.05, sh + 0.15, mat="trim_green")
    tc.gable_roof(kit, x0, x1, y0, y1, H, p["pitch"], axis="x", over_eave=0.45, over_gable=0.35, roof="shingle", soffit="trim",
                  fascia="trim_green")
    # the cross gable over the front, scrolled trim
    fx0, fx1 = -4.5, 1.5
    fr = H + 3.0 * p["pitch"] + 0.4
    tc.wall(Wl, "S", y0 - 0.01, fx0, fx1, H, H, gable=fr)
    tc.window(kit, "S", y0 - 0.02, -1.5, H + 0.5, 1.0, 1.3, cell="dh_lamp", trim="trim_green", casing=0.08)
    tc.gable_roof(kit, fx0, fx1, y0 - 0.01, 1.5, H, p["pitch"] * 1.13, axis="y", over_eave=0.3, over_gable=0.35, roof="shingle",
                  soffit="trim", fascia="trim_green", collide=False)
    for k in range(9):
        ang = math.pi * (k + 0.5) / 9
        kit.p("GableTrim", "trim").beam(V(-1.5, y0 - 0.38, H + 0.35), V(-1.5 + 1.3 * math.cos(ang), y0 - 0.38, H + 0.35 + 1.0 * math.sin(ang)),
                                        0.06, 0.03)
    # the turret at the south-east corner
    tx, ty, tr = x1 - 0.3, y0 + 0.3, 2.0
    Tt = kit.p("Turret", "lap_cream")
    kit.tints["Turret"] = (0.98, 0.96, 0.9)
    Tt.cyl((tx, ty), tr, -0.6, H + 1.4, sides=12, caps="")
    for s in range(3):
        z = s * sh + 0.9
        for k in range(3):
            a = -math.pi / 2 + (k - 1) * 0.75
            c = V(tx + (tr + 0.01) * math.cos(a), ty + (tr + 0.01) * math.sin(a), z)
            t = V(-math.sin(a), math.cos(a), 0) * 0.45
            nrm = V(math.cos(a), math.sin(a), 0)
            kit.p("Window", "windows").face([c - t, c + t, c + t + V(0, 0, 1.5), c - t + V(0, 0, 1.5)],
                                            uvs=tc.cell_uv(tc.WIN["dh_lamp"]), toward=nrm)
            kit.p("Trim", "trim_green").face([c - t * 1.25 + nrm * 0.02, c + t * 1.25 + nrm * 0.02, c + t * 1.25 + nrm * 0.02 + V(0, 0, 0.12),
                                              c - t * 1.25 + nrm * 0.02 + V(0, 0, 0.12)], toward=nrm)
    kit.p("TurretRoof", "shingle").cyl((tx, ty), tr + 0.3, H + 1.4, H + 5.2, sides=12, caps="", r1=0.06)
    kit.p("TurretRoof", "soot").cyl((tx, ty), tr + 0.3, H + 1.39, H + 1.4, sides=12, caps="b")
    kit.p("Finial", "brass").cyl((tx, ty), 0.06, H + 5.1, H + 5.9, sides=5, r1=0.01)
    kit.collide((tx - tr, ty - tr, -0.6), (tx + tr, ty + tr, H + 1.4))
    tc.chimney(kit, -5.0, 3.0, H, ridge + 0.8, w=0.8, d=0.6, mat="brick_red")
    kit.collide((x0, y0, -0.6), (x1, y1, ridge))
    # the wraparound porch (front and west side), turned posts, rocking chairs, steps
    pz = -0.15
    xs, y_out = tc.porch(kit, x0, x1 - 2.2, y0, p["porch"], pz, sh - 0.1, posts=6, roof="shingle", rail=True, steps_at=-1.0, step_w=2.0,
                         deck="deck", trim="trim", post_mat="trim", rail_style="bars", rail_mat="trim")
    kit.p("Deck", "deck").box((x0 - p["porch"], y_out, pz - 0.06), (x0, y1 - 3.0, pz), skip="b")
    kit.collide((x0 - p["porch"], y_out, -0.6), (x0, y1 - 3.0, pz))
    R = kit.p("Roof", "shingle")
    R.face([(x0, y_out - 0.2, sh), (x0, y1 - 2.8, sh), (x0 - p["porch"] - 0.2, y1 - 2.8, sh - 0.6), (x0 - p["porch"] - 0.2, y_out - 0.2, sh - 0.6)],
           toward=(-1, 0, 1))
    kit.p("Soffit", "trim").face([(x0, y_out - 0.2, sh - 0.1), (x0, y1 - 2.8, sh - 0.1), (x0 - p["porch"] - 0.2, y1 - 2.8, sh - 0.7),
                                  (x0 - p["porch"] - 0.2, y_out - 0.2, sh - 0.7)], toward=(1, 0, -1))
    for y in (y_out + 2.5, y_out + 5.5, y1 - 3.2):
        kit.p("Posts", "trim").box((x0 - p["porch"] + 0.1, y - 0.07, pz), (x0 - p["porch"] + 0.24, y + 0.07, sh - 0.7), skip="bt")
    tc.railing(kit, (x0 - p["porch"] + 0.17, y_out + 0.3), (x0 - p["porch"] + 0.17, y1 - 3.1), pz, mat="trim", style="bars")
    nst = 3
    tc.steps(kit, -2.0, 0.0, y_out, pz, n=nst, run=0.3, mat="deck", z_bottom=-0.6)
    for (cx, cy, rot) in ((-6.5, y0 - 1.6, 0.0), (-5.3, y0 - 1.6, 0.0), (3.0, y0 - 1.6, 0.0), (4.2, y0 - 1.6, 0.0),
                          (x0 - 1.6, 0.0, 1.0), (x0 - 1.6, 1.3, 1.0)):
        Rk = kit.p("Rockers", "paint_white")
        if rot:
            Rk.box((cx - 0.25, cy - 0.25, pz + 0.4), (cx + 0.25, cy + 0.25, pz + 0.45))
            Rk.box((cx - 0.3, cy - 0.25, pz + 0.45), (cx - 0.25, cy + 0.25, pz + 1.05))
            for yy in (cy - 0.24, cy + 0.24):
                kit.p("Rockers", "paint_white").polyline([V(cx - 0.35, yy, pz + 0.05), V(cx, yy, pz), V(cx + 0.35, yy, pz + 0.05)], 0.015, 3)
        else:
            Rk.box((cx - 0.25, cy - 0.25, pz + 0.4), (cx + 0.25, cy + 0.25, pz + 0.45))
            Rk.box((cx - 0.25, cy + 0.25, pz + 0.45), (cx + 0.25, cy + 0.3, pz + 1.05))
            for xx in (cx - 0.24, cx + 0.24):
                kit.p("Rockers", "paint_white").polyline([V(xx, cy - 0.35, pz + 0.05), V(xx, cy, pz), V(xx, cy + 0.35, pz + 0.05)], 0.015, 3)
        kit.collide((cx - 0.3, cy - 0.3, pz), (cx + 0.3, cy + 0.3, pz + 0.5))
    tc.hinged_door(kit, col, root, "S", y0, -1.0, 1.2, 2.4, depth=0.1, leaf="door_green", index=1, glass="dh_lamp")
    tc.blade_sign(kit, "S", y_out, x1 - 3.2, 1.6, w=1.0, h=0.5, kind="museum" if False else "cafe", arm=0.9)
    kit.p("PorchLights", "lamp").cyl((-2.2, y0 - 0.1), 0.07, 2.1, 2.3, sides=6)
    kit.p("PorchLights", "lamp").cyl((0.2, y0 - 0.1), 0.07, 2.1, 2.3, sides=6)

    # ---------------------------------------------------------------- the lobby (walk-in)
    lx0, lx1, ly0, ly1 = x0 + T, 3.0, y0 + T, 3.0
    C = sh - 0.2
    kit.sub = 0.8
    tc.room(kit, lx0, lx1, ly0, ly1, 0.0, C, walls="plaster", floor="woodfloor", ceiling="paint_white", name="Lobby",
            wainscot="darkwood", wainscot_h=1.0, base="trim_black",
            openings={"S": [o for o in ops["S"] if o[2] < sh and o[1] < lx1], "W": [o for o in ops["W"] if o[2] < sh and o[1] < ly1]})
    kit.sub = None
    tc.wall_collider(kit, "y", lx1 + 0.1, y0, y1, 0.2, C)
    tc.wall_collider(kit, "x", ly1 + 0.1, x0, lx1, 0.2, C)
    kit.p("Desk", "varnish").box((0.4, -1.5, 0.0), (2.5, -0.8, 1.05), skip="bt")
    kit.p("DeskTop", "darkwood").box((0.3, -1.55, 1.05), (2.6, -0.75, 1.1))
    kit.collide((0.3, -1.55, 0), (2.6, -0.75, 1.1))
    kit.p("Bell", "brass").cyl((1.0, -1.15), 0.05, 1.1, 1.16, sides=6)
    for k in range(10):                                     # the staircase up the north wall to a landing
        z = (k + 1) * C / 10
        kit.p("Stairs", "darkwood").box((-6.6 + k * 0.28, ly1 - 1.1, 0.0), (-6.32 + k * 0.28, ly1, z), skip="b")
        kit.collide((-6.6 + k * 0.28, ly1 - 1.1, 0), (-6.32 + k * 0.28, ly1, z))
    tc.railing(kit, (-6.6, ly1 - 1.1), (-3.8, ly1 - 1.1), 0.0, h=1.0, mat="varnish", style="bars", collide=False)
    kit.p("Fireplace", "fieldstone").box((lx0, -2.5, 0.0), (lx0 + 0.6, -0.7, 2.4), skip="b")
    kit.p("Fireplace", "soot").face([(lx0 + 0.605, -2.0, 0.2), (lx0 + 0.605, -1.2, 0.2), (lx0 + 0.605, -1.2, 0.9), (lx0 + 0.605, -2.0, 0.9)],
                                    toward=(1, 0, 0))
    kit.p("Fire", "neon_amber").face([(lx0 + 0.5, -1.9, 0.22), (lx0 + 0.5, -1.3, 0.22), (lx0 + 0.5, -1.4, 0.5), (lx0 + 0.5, -1.8, 0.55)],
                                     toward=(1, 0, 0))
    kit.collide((lx0, -2.5, 0), (lx0 + 0.6, -0.7, 2.4))
    kit.p("Rug", "trim_red").face([(-6.0, -3.6, 0.005), (-3.0, -3.6, 0.005), (-3.0, 0.4, 0.005), (-6.0, 0.4, 0.005)], toward=(0, 0, 1))
    kit.p("Sofa", "fabric_blue").box((-4.0, -3.0, 0.0), (-3.2, -0.6, 0.45), skip="b")
    kit.p("Sofa", "fabric_blue").box((-3.4, -3.0, 0.45), (-3.2, -0.6, 0.9))
    kit.collide((-4.0, -3.0, 0), (-3.2, -0.6, 0.9))
    for cy in (-3.4, 0.0):
        kit.p("Armchairs", "fabric_tan").box((-6.0, cy - 0.4, 0.0), (-5.2, cy + 0.4, 0.45), skip="b")
        kit.p("Armchairs", "fabric_tan").box((-6.0, cy - 0.4, 0.45), (-5.8, cy + 0.4, 0.95))
        kit.collide((-6.0, cy - 0.4, 0), (-5.2, cy + 0.4, 0.95))
    for (lx, ly) in ((-4.6, -3.6), (2.2, -2.4)):
        kit.p("Lamps", "darkwood").cyl((lx, ly), 0.04, 0.0, 1.4, sides=5)
        kit.p("Lamps", "lamp").cyl((lx, ly), 0.22, 1.35, 1.65, sides=8, caps="tb", r1=0.16)
        kit.light((lx, ly, 1.5), (1.0, 0.72, 0.45), 35, 0.2)
    kit.light((lx0 + 0.9, -1.6, 0.5), (1.0, 0.5, 0.15), 20, 0.3)
    kit.light((-2.0, -1.0, C - 0.1), (1.0, 0.85, 0.65), 25, 2.0, kind="AREA")

    far = tc.Far(n)
    far.gable(x0, x1, y0, y1, -0.6, H, ridge, axis="x", wall="lap_cream", roof="shingle", over=0.45)
    far.cyl((tx, ty), tr, -0.6, H + 1.4, "lap_cream", sides=8, cap=False)
    far.cyl((tx, ty), tr + 0.3, H + 1.4, H + 5.2, "shingle", sides=8, cap=False, r1=0.06)
    far.shed(x0, x1 - 2.2, y0, y_out, sh - 0.1, sh - 0.1 - p["porch"] * 0.25, roof="shingle")
    for s in range(2):
        far.windows("S", y0, [-6.0, -3.2, 1.6, 4.0], s * sh + 0.9, 1.0, 1.7, "window_lit")
    kit.entrance((-1.0, y_out - nst * 0.3, -0.6), "-Y", 1.2, kind="door", note="TownInn_Door_1, up three steps")
    kit.info.update(walk_in=True, storeys=2.5, rooms=["lobby 10.8 x 8.8 (desk, stairs to a landing, fireplace, sofa)"],
                    footprint=[round(x0 - p["porch"] - 0.2, 3), round(y_out - nst * 0.3, 3), round(x1 + 2.3, 3), round(y1 + 0.45, 3)])
    parts = tc.finish(kit, col, root, far)
    if p["bake"]:
        meshes = [o for o in root.children_recursive if o.type == "MESH" and not o.name.endswith("_LOD1")]
        town_light.bake(kit, root, meshes, [(lx0, ly0, 0.0, lx1, ly1, C)])
    return root, parts
