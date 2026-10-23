"""The diner's far version (town2_diner.py): `Town2Diner_LOD1`, ~1.5k triangles, the lot, the car's
skin and barrel roof, the vestibule, the roof sign, the annex, the pylon and the cars as plain
volumes. build.py bakes the full building's look onto it (Cycles COMBINED, selected to active:
the windows carry the lit interior, the neon its glow) into one small emissive texture,
T_Town2_Diner_Far; viewer/wild/town.js shows it beyond its lodDistance."""
import math

import bpy

import town2_diner_geo as G


def build(k, M, p):
    far = bpy.data.objects.new("Town2Diner_LOD1", None)
    k.col.objects.link(far)
    far.parent = k.root
    far["lodDistance"] = 90.0
    k.lod_root = far
    mat = M["far"]
    C, A, fz = p["car"], p["annex"], p["fz"]
    sx, sy = p["site"]

    def add(name, bm):
        ob = k.add(name, bm, mat, tile=None, lod=1, zone="out")
        ob.parent = far
        return ob
    add("Far_Lot", G.quad((-sx / 2, -sy / 2, p["lot_z"]), (sx / 2, -sy / 2, p["lot_z"]), (sx / 2, sy / 2, p["lot_z"]), (-sx / 2, sy / 2, p["lot_z"])))
    # the car: its skin (sill to eave) round the rounded plan, the barrel roof and its gable ends
    path = G.rrect_path(C["x0"], C["yf"], C["x1"], C["yb"], C["r"], n=3, start="bw")
    add("Far_CarSkin", G.path_sweep(path, [(0.02, 0.0), (0.02, fz - 0.1), (0.0, fz - 0.1), (0.0, C["zw0"]), (0.0, C["zw1"]), (0.0, C["ze"] - 0.05), (0.22, C["ze"])]))
    ze = C["ze"]
    prof = [(y, C["roof_z"](y)) for y in [C["yf"] - 0.12 + (C["yb"] - C["yf"] + 0.24) * t / 6 for t in range(7)]]
    add("Far_CarRoof", G.open_sweep(prof, C["x1"] - 0.05, C["x0"] + 0.05, axis="x"))
    gable = prof + [(prof[-1][0], ze), (prof[0][0], ze)]
    add("Far_CarGable", G.sweep(gable, C["x0"] + 0.02, C["x0"] + 0.05, axis="x"))
    add("Far_CarGable", G.sweep(gable, C["x1"] - 0.05, C["x1"] - 0.02, axis="x"))
    vx, vy0 = p["vest_w"] / 2, C["yf"] - p["vest_d"]
    add("Far_Vest", G.box_lohi((-vx, vy0, 0.0), (vx, C["yf"], fz + 2.42)))
    add("Far_Walk", G.box_lohi((-10.6, -2.2, 0.0), (10.6, C["yf"] + 0.4, p["walk_z"])))
    # the roof sign
    yb = C["yf"] + 0.55
    add("Far_Sign", G.box_lohi((-3.2, yb - 0.08, ze + 0.42), (3.2, yb + 0.08, ze + 1.42)))
    # the annex: walls and the shed roof
    rz0, rz1 = fz + 2.62, fz + 2.40
    ab = G.box_lohi((A["x0"], A["y0"], 0.0), (A["x1"], A["y1"], 1.0))
    for v in ab.verts:
        if v.co.z > 0.5:
            v.co.z = rz0 + (rz1 - rz0) * (v.co.y - A["y0"]) / (A["y1"] - A["y0"])
    add("Far_Annex", ab)
    # the pylon sign (posts, cabinet, arrow)
    x, y = -12.0, -sy / 2 + 0.9
    add("Far_PylonBase", G.box_lohi((x - 1.0, y - 0.4, 0.0), (x + 1.0, y + 0.4, 0.6)))
    for dx in (-0.6, 0.6):
        add("Far_PylonPost", G.box_lohi((x + dx - 0.1, y - 0.1, 0.6), (x + dx + 0.1, y + 0.1, 3.4)))
    add("Far_PylonCab", G.box_lohi((x - 1.85, y - 0.23, 3.4), (x + 1.85, y + 0.23, 4.83)))
    add("Far_PylonArrow", G.box_lohi((x - 1.6, y - 0.07, 2.52), (x + 1.65, y + 0.07, 3.36)))
    # the planters along the road and the cars, as boxes
    for pa, pb in ((-sx / 2 + 0.2, -9.0), (-2.6, 2.6), (9.0, sx / 2 - 0.2)):
        add("Far_Planter", G.box_lohi((pa, -sy / 2 + 0.25, 0.0), (pb, -sy / 2 + 1.55, 0.75)))
    for kind, cx, cy, yaw, _ in p.get("cars", []):
        L, W, H = {"wagon": (4.75, 1.82, 1.5), "pickup": (5.85, 2.0, 1.9), "van": (5.9, 2.08, 2.45)}[kind]
        bm = G.box_lohi((-L / 2, -W / 2, 0.0), (L / 2, W / 2, H), bevel=0.25)
        G.xform(bm, loc=(cx, cy, p["lot_z"]), rz=math.radians(yaw))
        add("Far_Car", bm)
    enc = G.box_lohi((11.0, A["y1"] + 0.6, 0.0), (14.6, sy / 2 - 0.3, 1.8))
    add("Far_Enclosure", enc)
