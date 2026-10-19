"""EV charging post: a slim graphite column with a brushed-aluminium face plate, a
black screen, a vertical light bar (cool white, emissive), a connector holster and
a coiled-down charging cable. Stands against a wall (back at +Y) on the floor.

Units are metres. The front faces -Y, the origin is the floor centre of the post.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import garage_cabinets as gk  # noqa: E402

importlib.reload(gk)
common, materials = gk.common, gk.materials

NAME = "GarageEVCharger"

P = dict(name=NAME, width=0.24, depth=0.12, height=1.45, cable_r=0.0125)


def build(**overrides):
    p = {**P, **overrides}
    b = gk.Builder(p["name"])
    gr, grd, al = gk.graphite(), gk.graphite_dark(), gk.aluminium()
    bar = materials.emissive("M_Garage_ChargeLight", (0.55, 0.85, 1.0), 4.0)
    screen = common.pbr_material("M_Garage_Screen", (0.01, 0.014, 0.02), roughness=0.12, coat=0.4)
    cable = common.pbr_material("M_Garage_Cable", (0.015, 0.015, 0.017), roughness=0.55)

    W, D, H = p["width"], p["depth"], p["height"]
    yf, yb = -D / 2, D / 2
    b.box("Foot", (W + 0.04, D + 0.02, 0.03), (0, 0, 0.015), grd, bevel=0.004, seg=2)
    b.box("Body", (W, D, H - 0.03), (0, 0, 0.03 + (H - 0.03) / 2), gr, bevel=0.03, seg=4)
    b.box("Cap", (W + 0.008, D + 0.008, 0.012), (0, 0, H + 0.006), al, bevel=0.004, seg=2)
    # face plate, screen and light bar
    b.box("Face", (W - 0.07, 0.006, 0.62), (0, yf - 0.002, 1.02), al, bevel=0.002, seg=1)
    b.box("Screen", (W - 0.12, 0.004, 0.12), (0, yf - 0.006, 1.22), screen, bevel=0.0015, seg=1)
    b.box("Light", (0.012, 0.004, 0.36), (0, yf - 0.006, 0.93), bar, bevel=0, seg=1)
    # holster on the right side and the cable that hangs from it in a loop
    hx = W / 2 + 0.035
    b.box("Holster", (0.07, 0.1, 0.13), (hx - 0.015, yf + 0.05, 0.82), grd, bevel=0.012, seg=3)
    b.cyl("Connector", 0.026, 0.09, (hx, yf - 0.005, 0.82), grd, axis="y", seg=12)
    b.cyl("Connector_Ring", 0.022, 0.012, (hx, yf - 0.052, 0.82), al, axis="y", seg=12)
    y0 = yf + 0.02
    pts = common.fillet_polyline([(hx, y0, 0.76), (hx, y0, 0.46), (hx + 0.06, y0 - 0.17, 0.26),
                                  (hx + 0.02, y0 - 0.24, 0.10), (hx - 0.14, y0 - 0.12, 0.05),
                                  (hx - 0.2, y0, 0.09), (W / 2 - 0.03, y0 + 0.01, 0.36)], 0.07, segments=5, closed=False)
    b.tube("Cable", pts, p["cable_r"], cable, res=2)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
