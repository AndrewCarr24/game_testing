"""Pool pavilion shell: a stone plinth with a teak floor, a thin cantilevered flat roof
(white render fascia, pale ballast roof, dark skylights) on slender dark-metal columns, a 14 m
floor-to-ceiling glass front with a covered terrace, and teak-fin screen walls on the other
three sides. Enclosed room 14 x 7 m (x -7..7, y -3.5..3.5), front (glass) toward -Y, floor
top at z = 0.30. Origin: centre of the room at lawn level. Interior is dressed separately
(cabana_lounge, cabana_daybed, cabana_bar)."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cabana_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common

NAME = "CabanaPavilion"

P = dict(
    name=NAME,
    half_len=7.0,          # enclosed room x -7..7
    half_dep=3.5,          # y -3.5..3.5, glass at -3.5
    floor_z=0.30,
    ceil_z=3.45,           # roof underside
    roof_t=0.30,
    roof_x=8.3,            # roof half length
    roof_y0=-6.2,          # roof front edge (covered terrace 2.7 m deep)
    roof_y1=4.55,          # roof rear edge
    col_y=-5.75,           # column line
    bays=8,
    fin_pitch=0.60,
    fin_w=0.14,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    m = cc.M()
    box, grid, quad = cc.box, cc.grid, cc.quad
    L, D, FZ, CZ, RT = p["half_len"], p["half_dep"], p["floor_z"], p["ceil_z"], p["roof_t"]

    # ---- plinth: stone terrace in front, teak-topped room floor behind
    box(f"{n}_Terrace", (-L - 0.4, -6.55, 0), (L + 0.4, -D, FZ), m["stone"], col, root, step=1.5, drop=("+y", "-z"))
    box(f"{n}_Floor", (-L - 0.4, -D, 0), (L + 0.4, D + 0.4, FZ), m["stone"], col, root, step=1.5,
        drop=("-y", "-z"), top=m["teak"])
    box(f"{n}_Step", (-L - 0.4, -7.05, 0), (L + 0.4, -6.55, 0.15), m["stone"], col, root, step=2.5, drop=("+y", "-z"))

    # ---- columns on the front line, slender dark metal
    cols = 5
    for i in range(cols):
        x = -7.5 + i * 3.75
        box(f"{n}_Column{i}", (x - 0.06, p["col_y"] - 0.06, FZ), (x + 0.06, p["col_y"] + 0.06, CZ), m["dark"], col, root,
            drop=("-z", "+z"))

    # ---- glass front: 8 bays between slim mullions, rails top and bottom
    bays = p["bays"]
    bw = 2 * L / bays
    for i in range(bays + 1):
        x = -L + i * bw
        box(f"{n}_Mullion{i}", (x - 0.035, -D - 0.06, FZ), (x + 0.035, -D + 0.04, CZ), m["dark"], col, root, drop=("-z", "+z"))
    box(f"{n}_RailTop", (-L, -D - 0.06, CZ - 0.09), (L, -D + 0.04, CZ), m["dark"], col, root, drop=("-y", "-z", "+z"))
    box(f"{n}_RailBottom", (-L, -D - 0.06, FZ), (L, -D + 0.04, FZ + 0.1), m["dark"], col, root, drop=("-z", "+z"))
    for i in range(bays):
        x0, x1 = -L + i * bw + 0.035, -L + (i + 1) * bw - 0.035
        quad(f"{n}_Glass{i}", [(x0, -D - 0.02, FZ + 0.1), (x1, -D - 0.02, FZ + 0.1), (x1, -D - 0.02, CZ - 0.09),
                               (x0, -D - 0.02, CZ - 0.09)], m["glass"], col, root)

    # ---- screen walls: bronze core, teak lining inside, vertical teak fins outside
    ct, lt = 0.12, 0.04
    fw, fd = p["fin_w"], 0.12
    y_rear = D
    # rear wall (x -L-0.24 .. L+0.24)
    box(f"{n}_CoreRear", (-L - ct - fd, y_rear, FZ), (L + ct + fd, y_rear + ct, CZ), m["warm_dark"], col, root, step=1.5,
        drop=("-y", "-z", "+z", "+x", "-x"))
    box(f"{n}_LiningRear", (-L, y_rear - lt, FZ), (L, y_rear, CZ), m["teak"], col, root, step=1.5, keep=("-y",))
    for sx in (-1, 1):
        x0, x1 = (L, L + ct) if sx > 0 else (-L - ct, -L)
        box(f"{n}_CoreEnd{sx}", (x0, -D, FZ), (x1, y_rear, CZ), m["warm_dark"], col, root, step=1.5,
            drop=("-y", "-z", "+z", "+y", "-x" if sx > 0 else "+x"))
        xl0, xl1 = (L - lt, L) if sx > 0 else (-L, -L + lt)
        box(f"{n}_LiningEnd{sx}", (xl0, -D, FZ), (xl1, y_rear, CZ), m["teak"], col, root, step=1.5,
            keep=("-x",) if sx > 0 else ("+x",))
    # fins: 2 vertical cells each (shade from the roof edge shows on them)
    pitch = p["fin_pitch"]
    nf = int((2 * L + 2 * (ct + fd)) / pitch)
    x0 = -(nf - 1) * pitch / 2
    for i in range(nf):
        x = x0 + i * pitch
        box(f"{n}_FinRear{i}", (x - fw / 2, y_rear + ct, FZ), (x + fw / 2, y_rear + ct + fd, CZ), m["teak"], col, root,
            step=1.6, drop=("-y", "-z", "+z"))
    ne = int((2 * D + fd) / pitch)
    y0 = -D + 0.2
    for sx in (-1, 1):
        for i in range(ne):
            y = y0 + i * pitch
            if y + fw / 2 > y_rear + ct:
                break
            xa, xb = (L + ct, L + ct + fd) if sx > 0 else (-L - ct - fd, -L - ct)
            box(f"{n}_FinEnd{sx}_{i}", (xa, y - fw / 2, FZ), (xb, y + fw / 2, CZ), m["teak"], col, root, step=1.6,
                drop=("-z", "+z", "-x" if sx > 0 else "+x"))

    # ---- roof: white slab (underside cut for the shade gradient), upstand ring, ballast, skylights
    rx, y0r, y1r = p["roof_x"], p["roof_y0"], p["roof_y1"]
    box(f"{n}_RoofSlab", (-rx, y0r, CZ), (rx, y1r, CZ + RT), m["white"], col, root, drop=("-z", "+z"))
    grid(f"{n}_Ceiling", (-rx, y0r), (rx, y1r), CZ, m["white"], col, root, step=1.5, up=False)
    ring, rh, rw = CZ + RT, 0.14, 0.22
    box(f"{n}_UpFront", (-rx, y0r, ring), (rx, y0r + rw, ring + rh), m["white"], col, root, drop=("-z",))
    box(f"{n}_UpRear", (-rx, y1r - rw, ring), (rx, y1r, ring + rh), m["white"], col, root, drop=("-z",))
    box(f"{n}_UpW", (-rx, y0r + rw, ring), (-rx + rw, y1r - rw, ring + rh), m["white"], col, root, drop=("-z",))
    box(f"{n}_UpE", (rx - rw, y0r + rw, ring), (rx, y1r - rw, ring + rh), m["white"], col, root, drop=("-z",))
    grid(f"{n}_Roof", (-rx + rw, y0r + rw), (rx - rw, y1r - rw), ring, m["gravel"], col, root, step=1.5, uv=2.0)
    for i, x in enumerate((-3.2, 3.6)):
        box(f"{n}_Skylight{i}", (x - 1.3, 0.2, ring), (x + 1.3, 1.5, ring + 0.22), m["dark"], col, root, drop=("-z",))

    # ---- light strips recessed in the ceiling (front terrace, room)
    for i, (y, x0s, x1s) in enumerate(((-4.6, -7.4, 7.4), (-1.0, -6.4, 6.4), (1.9, -6.4, 6.4))):
        quad(f"{n}_Strip{i}", [(x0s, y - 0.04, CZ - 0.012), (x0s, y + 0.04, CZ - 0.012), (x1s, y + 0.04, CZ - 0.012),
                               (x1s, y - 0.04, CZ - 0.012)][::-1], m["lamp"], col, root)
    return cc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
