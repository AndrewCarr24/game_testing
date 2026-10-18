"""Cooking wall: a 1.2 m steel range with a steel canopy hood under a full-height
Calacatta slab, smoked-oak base drawers and counters either side, two floating
walnut shelves with jars and plates, and smoked-oak tall pantry units to the ceiling
at both ends. 4.7 m long, back against +Y, fronts face -Y; the visible end (with an
end panel) is the right-hand (+X) one. Origin is the floor centre."""
import importlib
import math
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitchen_lib as L  # noqa: E402

importlib.reload(L)
common, materials = L.common, L.materials

NAME = "KitchenRangeWall"

P = dict(
    name=NAME,
    depth=0.66,
    plinth=0.10,
    counter_z=0.92,
    counter_t=0.04,
    tall_z=2.40,
    band_z=2.43,
    top_z=4.19,
    tall_l=0.8,
    base_l=0.9,
    range_w=1.2,
    base_r=0.9,
    tall_r=0.9,
    hood_z=1.70,
    hood_w=1.30,
    hood_d=0.66,
)


def frustum(w0, d0, w1, d1, z0, z1, y_back, off=0.0):
    """Truncated pyramid hood body: bottom rect w0 x d0 at z0, top rect w1 x d1 at z1,
    both flush with the wall plane y_back and growing toward -Y."""
    bm = bmesh.new()
    pts = []
    for z, w, d in ((z0, w0, d0), (z1, w1, d1)):
        pts.append([bm.verts.new((sx * w / 2 + off, y_back - d if sy < 0 else y_back, z))
                    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    b, t = pts
    bm.faces.new(b[::-1])
    bm.faces.new(t)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((b[i], b[j], t[j], t[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def build(**overrides):
    p = {**P, **overrides}
    b = L.Builder(p["name"])
    oak = materials.smoked_oak()
    walnut = materials.walnut()
    bronze = materials.bronze()
    steel = L.brushed_steel()
    polished = materials.steel()
    black = L.carcass()
    glass = L.black_glass()
    marble = L.calacatta_mat()
    cer = L.ceramic()
    char = L.dark_glaze()
    led = materials.emissive("M_LED_Warm", (1.0, 0.8, 0.55), 4.0)

    D = p["depth"]
    yf, yb = -D / 2, D / 2
    t = 0.02
    ph, cz, ct = p["plinth"], p["counter_z"], p["counter_t"]
    segs = [("tall_l", p["tall_l"]), ("base_l", p["base_l"]), ("range", p["range_w"]), ("base_r", p["base_r"]),
            ("tall_r", p["tall_r"])]
    total = sum(w for _, w in segs)
    x = -total / 2
    xs = {}
    for k, w in segs:
        xs[k] = (x, x + w)
        x += w
    fr = L.Fronts(b, oak, bronze, yf)

    b.box("Plinth", (total - 0.04, D - 0.09, ph), (0, (yf + 0.07 + yb - 0.02) / 2, ph / 2), black, bevel=0, tile=0)

    # --- tall units at both ends: lower doors, shadow gap, upper doors
    for k in ("tall_l", "tall_r"):
        x0, x1 = xs[k]
        b.box(f"{k}_Body", (x1 - x0, yb - (yf + t), p["top_z"] - ph), ((x0 + x1) / 2, (yf + t + yb) / 2, (ph + p["top_z"]) / 2),
              black, bevel=0, tile=0)
        kind = "d2" if x1 - x0 > 0.85 else "d1"
        fr.unit(kind, x0, x1, ph, p["tall_z"], f"{k}_Lower")
        fr.unit(kind, x0, x1, p["band_z"], p["top_z"], f"{k}_Upper")

    # --- base units either side of the range, with the marble counter
    bx0, bx1 = xs["base_l"][0], xs["base_r"][1]
    for k in ("base_l", "base_r"):
        x0, x1 = xs[k]
        b.box(f"{k}_Body", (x1 - x0, yb - (yf + t), cz - ct - ph), ((x0 + x1) / 2, (yf + t + yb) / 2, (ph + cz - ct) / 2),
              black, bevel=0, tile=0)
        fr.unit("dr3", x0, x1, ph, cz - ct, k)
        b.box(f"Counter_{k}", (x1 - x0, D + 0.02, ct), ((x0 + x1) / 2, yf - 0.02 + (D + 0.02) / 2, cz - ct / 2), marble,
              bevel=0.003, seg=2, tile=1.5, world_uv=True)

    # --- the range
    rx0, rx1 = xs["range"]
    rxm = (rx0 + rx1) / 2
    rw = rx1 - rx0
    ry0 = yf - 0.04                      # stands proud of the cabinet fronts
    b.box("Range_Body", (rw - 0.004, yb - ry0 - 0.02, cz - ph - 0.04), (rxm, (ry0 + yb - 0.02) / 2, (ph + cz - 0.04) / 2),
          steel, bevel=0.004, seg=2, tile=0)
    b.box("Range_Toe", (rw - 0.06, D - 0.1, ph), (rxm, (yf + 0.06 + yb) / 2, ph / 2), black, bevel=0, tile=0)
    b.box("Range_Top", (rw - 0.004, yb - ry0 - 0.02, 0.04), (rxm, (ry0 + yb - 0.02) / 2, cz - 0.02), steel, bevel=0.003,
          seg=2, tile=0)
    # control strip with knobs
    b.box("Range_Panel", (rw - 0.03, 0.012, 0.085), (rxm, ry0 - 0.004, cz - 0.075), black, bevel=0.002, tile=0)
    for i in range(6):
        kx = rx0 + 0.13 + i * (rw - 0.26) / 5
        ob = b.lathe(f"Knob{i}", [(0, 0), (0.022, 0), (0.022, 0.03), (0.018, 0.035), (0, 0.035)], polished,
                     loc=(kx, ry0 - 0.01, cz - 0.075), segs=14, uv_tile=0)
        ob.rotation_euler = (math.radians(90) + math.pi, 0, 0)    # axis toward -Y
    # two oven doors, black glass in a steel frame, one long steel bar handle
    dw = (rw - 0.04) / 2
    zc = (ph + 0.04 + cz - 0.16) / 2
    for i, sx in enumerate((-1, 1)):
        xm = rxm + sx * (dw / 2 + 0.002)
        b.box(f"Oven{i}_Frame", (dw - 0.004, 0.03, cz - ph - 0.2), (xm, ry0 - 0.006, zc), steel,
              bevel=0.003, seg=1, tile=0)
        b.box(f"Oven{i}_Glass", (dw - 0.07, 0.006, cz - ph - 0.32), (xm, ry0 - 0.022, zc - 0.03),
              glass, bevel=0.002, tile=0)
    zh = cz - 0.2
    ys = ry0 - 0.075
    b.tube("Range_Handle", [(rx0 + 0.06, ry0 - 0.01, zh), (rx0 + 0.06, ys, zh), (rx1 - 0.06, ys, zh), (rx1 - 0.06, ry0 - 0.01, zh)],
           0.0125, polished, closed=False, res=4)
    # glass cooktop with burners and a stockpot
    b.box("Cooktop", (rw - 0.04, yb - ry0 - 0.06, 0.008), (rxm, (ry0 + 0.01 + yb - 0.05) / 2, cz + 0.004), glass,
          bevel=0.001, tile=0)
    cy = (ry0 + yb) / 2
    for i, (dx, dy, rr) in enumerate(((-0.4, -0.12, 0.1), (-0.4, 0.14, 0.085), (0.0, 0.0, 0.11), (0.4, -0.12, 0.09),
                                      (0.4, 0.14, 0.11))):
        b.lathe(f"Burner{i}", [(rr - 0.008, 0.0), (rr, 0.0), (rr, 0.003), (rr - 0.008, 0.003)], steel,
                loc=(rxm + dx, cy + dy, cz + 0.008), segs=24, uv_tile=0)
    pot = [(0.0, 0.0), (0.125, 0.0), (0.13, 0.01), (0.13, 0.20), (0.135, 0.205), (0.0, 0.205)]
    b.lathe("Pot", pot, polished, loc=(rxm, cy, cz + 0.011), segs=28, uv_tile=0)
    b.lathe("PotLid", [(0.0, 0.205), (0.138, 0.205), (0.138, 0.213), (0.1, 0.225), (0.02, 0.235), (0.0, 0.235)], steel,
            loc=(rxm, cy, cz + 0.011), segs=28, uv_tile=0)

    # --- Calacatta slab wall behind the base and range, to the ceiling
    b.box("Slab", (bx1 - bx0, 0.025, p["top_z"] - cz), ((bx0 + bx1) / 2, yb - 0.0125, (cz + p["top_z"]) / 2), marble,
          bevel=0.001, tile=1.5, world_uv=True)

    # --- hood: steel canopy and chimney to the ceiling, with a lit black underside
    hz, hw, hd = p["hood_z"], p["hood_w"], p["hood_d"]
    hood = common.mesh_object(f"{b.n}_Hood", frustum(hw, hd, 0.52, 0.42, hz, hz + 0.55, yb - 0.025, off=rxm), b.col, steel,
                              b.root, smooth=False)
    L.planar_uv(hood, 1.0)
    b.box("Chimney", (0.52, 0.42, p["top_z"] - (hz + 0.55)), (rxm, yb - 0.025 - 0.21, (hz + 0.55 + p["top_z"]) / 2),
          steel, bevel=0.003, seg=1, tile=0)
    b.box("Hood_Underside", (hw - 0.05, hd - 0.05, 0.02), (rxm, yb - 0.025 - (hd - 0.05) / 2, hz + 0.004), black,
          bevel=0, tile=0)
    b.box("Hood_Light", (hw - 0.3, 0.05, 0.01), (rxm, yb - 0.025 - hd + 0.12, hz - 0.003), led, bevel=0, tile=0)
    b.box("Hood_Lip", (hw + 0.004, 0.02, 0.05), (rxm, yb - 0.025 - hd - 0.002, hz + 0.02), steel, bevel=0.002, tile=0)

    # --- floating shelves either side of the hood, with jars, plates and bowls
    sh_z = 1.55
    for tag, k, side in (("L", "base_l", -1), ("R", "base_r", 1)):
        x0, x1 = xs[k]
        b.box(f"Shelf_{tag}", (x1 - x0 - 0.1, 0.24, 0.045), ((x0 + x1) / 2, yb - 0.025 - 0.12, sh_z), walnut,
              bevel=0.003, seg=1, tile=0.5, shift=(0.2 * side, 0.1))
    x0, x1 = xs["base_l"]
    L.jars(b, "JarsL", x0 + 0.12, yb - 0.17, sh_z + 0.0225, 5, materials.glass("M_Glass_Jar", (0.9, 0.95, 0.92), 0.25),
           bronze, common.pbr_material("M_Grain_Flour", (0.55, 0.45, 0.28), roughness=0.9), gap=0.155, seed=2)
    x0, x1 = xs["base_r"]
    L.stack_plates(b, "PlatesR", ((x0 + x1) / 2 - 0.18, yb - 0.18, sh_z + 0.0225), cer, r=0.13, count=7)
    L.stack_plates(b, "BowlsR", ((x0 + x1) / 2 + 0.15, yb - 0.17, sh_z + 0.0225), char, r=0.095, count=5, step=0.03)

    # --- end panel on the visible (right) end
    xr = xs["tall_r"][1]
    b.box("EndPanel", (0.03, D, p["top_z"]), (xr + 0.015, 0.0, p["top_z"] / 2), oak, bevel=0.002, seg=1, shift=(0.5, 0.1))
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
