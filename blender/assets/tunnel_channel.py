"""A 6.0 x 0.3 m drainage channel grate set into the tunnel floor at its edge: three 2 m
galvanised bar-grate sections in a galvanised angle frame over a dark recess. The depth is
faked: a dark inner floor lies 0.002 under the grate's top, so everything stays within 0.012 m of
the floor (it walks flat: the whole asset is NoCollide by name).

Origin: floor centre of the grate; the run lies along x, 0.3 wide in y."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bunker_door  # noqa: E402

importlib.reload(bunker_door)
Geo, bk = bunker_door.Geo, bunker_door.bk
common = bk.common

NAME = "TunnelChannel"

P = dict(
    name=NAME,
    length=6.0,
    width=0.30,
    top=0.010,          # top of the bars above the floor
    frame_h=0.0115,      # the frame stands a hair proud of the bars
    frame_w=0.022,
    bar_pitch=0.030,
    sections=3,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    gal, dark, rust = bk.galvanised(), bk.polymer(), bk.rust()
    L, W, top, fh, fw = p["length"], p["width"], p["top"], p["frame_h"], p["frame_w"]

    g = Geo()                                                    # the dark recess, 2 mm under the bar tops
    g.box((0, 0, top - 0.002 - 0.0005), (L - 0.01, W - 0.01, 0.001))
    g.finish(f"{n}_Recess_NoCollide", col, dark, root)

    g = Geo()
    for sy in (-1, 1):                                           # long angle rails
        g.box((0, sy * (W / 2 - fw / 2), fh / 2), (L, fw, fh))
    seg = L / p["sections"]
    for k in range(p["sections"] + 1):                           # end / joint bars
        g.box((-L / 2 + k * seg + (0.011 if k == 0 else -0.011 if k == p["sections"] else 0), 0, fh / 2),
              (0.022, W - 2 * fw, fh))
    nb = int((W - 2 * fw) / p["bar_pitch"])
    inner = W - 2 * fw - 0.012
    for k in range(p["sections"]):                               # bearing bars along x in each section
        x0 = -L / 2 + k * seg + 0.026
        sl = seg - 0.052
        for i in range(nb):
            y = -inner / 2 + 0.006 + i * (inner - 0.012) / (nb - 1)
            g.box((x0 + sl / 2, y, top - 0.003), (sl, 0.006, 0.006))
        for j in range(int(sl / 0.12) + 1):                      # cross rods
            g.box((x0 + 0.01 + j * (sl - 0.02) / int(sl / 0.12), 0, top - 0.0055), (0.005, inner, 0.004))
    g.finish(f"{n}_Grate_NoCollide", col, gal, root)

    g = Geo()                                                    # rust at one joint
    g.box((-L / 2 + seg, -W / 2 + fw + 0.03, fh + 0.0002), (0.05, 0.05, 0.0006))
    g.box((L / 2 - 0.4, W / 2 - fw - 0.04, fh + 0.0002), (0.09, 0.03, 0.0006))
    g.finish(f"{n}_Stain_NoCollide", col, rust, root)

    return root, [o for o in root.children_recursive if o.type == "MESH"]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
