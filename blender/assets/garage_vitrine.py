"""Wall display case for the showroom garage: a slim aluminium-framed vitrine with
a glass front, a warm lit back panel and a black plinth, holding racing helmets,
1:18 scale models, a wheel rim and two trophies on three glass shelves.

Units are metres. The front faces -Y (back at +Y against the wall), the origin is
the floor centre.
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import garage_cabinets as gk  # noqa: E402

importlib.reload(gk)
common, materials = gk.common, gk.materials

NAME = "GarageVitrine"

P = dict(name=NAME, width=3.6, depth=0.42, height=2.5, plinth_h=0.22, frame=0.04)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402  (react definitions, prompts/interactivity.md)

importlib.reload(ix_common)


def build(**overrides):
    p = {**P, **overrides}
    b = gk.Builder(p["name"])
    gr, grd, al = gk.graphite(), gk.graphite_dark(), gk.aluminium()
    glow = materials.emissive("M_Garage_VitrineGlow", (1.0, 0.88, 0.7), 1.3)
    glass = materials.glass("M_Garage_VitrineGlass", tint=(0.8, 0.9, 0.92), alpha=0.10, roughness=0.02)
    shelf_glass = materials.glass("M_Garage_ShelfGlass", tint=(0.6, 0.8, 0.8), alpha=0.35, roughness=0.05)
    white = gk.white_lacquer()
    red = common.pbr_material("M_Garage_RaceRed", (0.5, 0.03, 0.02), roughness=0.3, coat=0.5)
    silver = common.pbr_material("M_Garage_RaceSilver", (0.62, 0.64, 0.68), roughness=0.3, coat=0.5)
    blue = common.pbr_material("M_Garage_RaceBlue", (0.02, 0.06, 0.22), roughness=0.3, coat=0.5)
    gold = common.pbr_material("M_Garage_Gold", (0.75, 0.52, 0.16), roughness=0.25, metallic=1.0)
    tyre = common.pbr_material("M_Garage_Tyre", (0.012, 0.012, 0.013), roughness=0.85)

    W, D, H, ph, f = p["width"], p["depth"], p["height"], p["plinth_h"], p["frame"]
    yf, yb = -D / 2, D / 2
    # plinth, frame, back panel, top hood
    b.lo_hi("Plinth", (-W / 2, yf + 0.03, 0), (W / 2, yb, ph), grd, bevel=0.003, seg=1)
    b.lo_hi("Back", (-W / 2 + f, yb - 0.02, ph), (W / 2 - f, yb, H - f), glow, bevel=0, tile=1.0)
    b.lo_hi("Hood", (-W / 2, yf, H - f), (W / 2, yb, H), gr, bevel=0.003, seg=1)
    b.lo_hi("Sill", (-W / 2, yf, ph), (W / 2, yf + 0.04, ph + 0.02), al, bevel=0.002, seg=1)
    nmul = 4
    for i in range(nmul + 1):
        x = -W / 2 + f / 2 + i * (W - f) / nmul
        b.lo_hi(f"Mullion{i}", (x - f / 2, yf, ph), (x + f / 2, yf + 0.03, H - f), al, bevel=0.0015, seg=1)
        b.lo_hi(f"Divider{i}", (x - 0.005, yf + 0.03, ph), (x + 0.005, yb - 0.02, H - f), shelf_glass, bevel=0, tile=1.0) if 0 < i < nmul else None
    b.lo_hi("Glass", (-W / 2 + f, yf + 0.012, ph + 0.02), (W / 2 - f, yf + 0.016, H - f), glass, bevel=0, tile=1.0, solid=True)

    shelves = [ph + 0.02, 1.0, 1.55, 2.05]
    for k, z in enumerate(shelves[1:], 1):
        b.lo_hi(f"Shelf{k}", (-W / 2 + f, yf + 0.04, z), (W / 2 - f, yb - 0.03, z + 0.012), shelf_glass, bevel=0, tile=1.0)
    ym = (yf + yb) / 2 + 0.03

    def helmet(name, x, z, mat, trim):
        b.sphere(f"{name}", 0.14, (x, ym, z + 0.14), mat, scale=(0.85, 1.05, 0.95), seg=14, rings=9)
        b.box(f"{name}_Visor", (0.15, 0.1, 0.05), (x, ym - 0.1, z + 0.17), grd, bevel=0.012, seg=2)
        b.box(f"{name}_Stripe", (0.03, 0.2, 0.008), (x, ym, z + 0.262), trim, bevel=0.002, seg=1)

    def model(name, x, z, mat, scale=1.0):
        s = scale
        b.box(f"{name}_Body", (0.17 * s, 0.4 * s, 0.05 * s), (x, ym, z + 0.04 * s), mat, bevel=0.01, seg=2)
        b.box(f"{name}_Cabin", (0.13 * s, 0.17 * s, 0.04 * s), (x, ym + 0.02 * s, z + 0.085 * s), grd, bevel=0.012, seg=2)
        for sx in (-1, 1):
            for sy in (-1, 1):
                b.cyl(f"{name}_W{sx}{sy}", 0.03 * s, 0.025 * s, (x + sx * 0.085 * s, ym + sy * 0.13 * s, z + 0.03 * s), tyre, axis="x", seg=10)

    def trophy(name, x, z, scale=1.0):
        s = scale
        b.box(f"{name}_Base", (0.14 * s, 0.14 * s, 0.05 * s), (x, ym, z + 0.025 * s), grd, bevel=0.004, seg=1)
        b.cyl(f"{name}_Stem", 0.012 * s, 0.14 * s, (x, ym, z + 0.12 * s), gold, seg=8)
        b.cyl(f"{name}_Cup", 0.06 * s, 0.14 * s, (x, ym, z + 0.26 * s), gold, seg=12, r2=0.028 * s)

    # lower shelf (on the plinth): wheel rim, tyre stack, a model
    z0 = shelves[0]
    b.cyl("Rim", 0.24, 0.16, (-1.2, ym, z0 + 0.24), silver, axis="y", seg=20)
    b.cyl("Rim_Hub", 0.1, 0.17, (-1.2, ym - 0.002, z0 + 0.24), grd, axis="y", seg=12)
    b.cyl("Tyre_Stack0", 0.26, 0.2, (-0.55, ym, z0 + 0.1), tyre, seg=20)
    b.cyl("Tyre_Stack1", 0.26, 0.2, (-0.55, ym, z0 + 0.3), tyre, seg=20)
    model("ModelA", 0.2, z0, red, 1.3)
    model("ModelB", 0.9, z0, silver, 1.3)
    trophy("TrophyA", 1.45, z0, 2.0)
    # shelf 1: helmets
    for i, (x, m, tm) in enumerate(((-1.4, white, red), (-0.7, red, white), (0.0, blue, silver), (0.7, silver, red), (1.4, grd, gold))):
        helmet(f"Helmet{i}", x, shelves[1] + 0.012, m, tm)
    # shelf 2: scale models
    for i, (x, m) in enumerate(((-1.35, red), (-0.45, blue), (0.45, silver), (1.35, white))):
        model(f"Model{i}", x, shelves[2] + 0.012, m)
    # shelf 3: trophies
    for i, x in enumerate((-1.0, -0.35, 0.35, 1.0)):
        trophy(f"Trophy{i}", x, shelves[3] + 0.012, 1.0 if i % 2 else 1.3)
    ix_common.tag_emissive(b.root)   # interactivity: glowing parts follow the room's light switch
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
