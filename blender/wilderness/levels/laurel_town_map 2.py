"""The town's plan at scale (design/town/map.svg), drawn from the level's own data (laurel_town.py
layout + the terrain run's heights and water): hillshade with 5 m contours, the river, streets
and the road from the estate, the heritage line and its tunnel, bridges, buildings coloured by
type, the cahoots evidence, the townspeople's posts, hiding places, exits, the two arrivals and
the sightlines that matter. Then design/town/map.png is rendered from it in Chrome.

  $PY blender/wilderness/levels/laurel_town_map.py     (after laurel_town.py's terrain step)
  node viewer/tools/svg_png.mjs design/town/map.svg design/town/map.png
"""
import base64
import json
import math
import os
import sys
import zlib
import struct

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import terrain  # noqa: E402
import laurel_town as LT  # noqa: E402

PROJECT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
X0, X1, Y0, Y1 = -2290.0, -730.0, -1110.0, -560.0      # estate frame
S = 1.6                                                 # px per m
W, H = int((X1 - X0) * S), int((Y1 - Y0) * S)
TYPE = {   # fill colour, legend label
    "bar": ("#c0392b", "the bar (roadhouse)"), "law": ("#2c3e50", "sheriff"), "civic": ("#f5f2e8", "church, museum, school"),
    "shop": ("#b5651d", "downtown shops"), "highway": ("#e67e22", "gas, drive-through, plaza (video), motel"),
    "house": ("#d9cbb0", "houses, garages"), "rental": ("#9fc5b4", "Mill Hill rentals (cottages)"), "mill": ("#7f4f3a", "brewery + lofts, stack, water tower"),
    "inn": ("#e8d9a8", "inn, outfitter, realty"),
}


def btype(b):
    k, i = b["kind"], b["id"]
    if k == "town_bar": return "bar"
    if k == "town_sheriff": return "law"
    if k in ("town_church", "town_church_hall", "town_depot", "town_school"): return "civic"
    if k in ("town_gas_station", "town_fastfood", "town_plaza") or k.startswith("town_motel"): return "highway"
    if k.startswith("town_cottage"): return "rental"
    if k in ("town_mill", "town_mill_stack", "town_water_tower"): return "mill"
    if i in ("inn", "outfitter", "realty", "shop_s4"): return "inn"
    if k.startswith("town_shop"): return "shop"
    return "house"


def px(x, y):
    return ((x - X0) * S, (Y1 - y) * S)


def png_bytes(rgb):
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[j].tobytes() for j in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def background():
    D = os.path.join(terrain.OUT_ROOT, LT.NAME)
    z = np.load(os.path.join(D, "terrain.npz"))
    Hm, rl = z["H"].astype(np.float64), z["river_level"]
    st = json.load(open(os.path.join(D, "stats.json")))
    g = st["grid"]
    grid = terrain.Grid(g["x0"], g["y0"], g["cell"], g["nx"], g["ny"])
    # sample at the map's pixels (y down)
    xs = X0 + (np.arange(W) + 0.5) / S
    ys = Y1 - (np.arange(H) + 0.5) / S
    Xe, Ye = np.meshgrid(xs, ys)
    Xl, Yl = Xe - LT.CX, Ye + LT.OY
    h = terrain.sample(Hm, grid, Xl, Yl)
    wl = terrain.sample(np.where(np.isfinite(rl), rl, -1e4), grid, Xl, Yl)
    gy, gx = np.gradient(h, 1 / S)
    nrm = np.dstack([-gx, gy, np.ones_like(h)])
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    Lv = np.array([-0.5, 0.55, 0.67]); Lv /= np.linalg.norm(Lv)
    shade = np.clip((nrm * Lv).sum(axis=2), 0, 1)
    t = np.clip((h + 192) / 220, 0, 1)[..., None]
    low, high = np.array([0.84, 0.86, 0.74]), np.array([0.62, 0.66, 0.5])
    col = (low * (1 - t) + high * t) * (0.55 + 0.5 * shade[..., None])
    con = (np.abs(((h + 1000) % 5.0) - 2.5) > 2.32) & (t[..., 0] > 0.02)
    col[con] *= 0.88
    con25 = np.abs(((h + 1000) % 25.0) - 12.5) > 12.25
    col[con25] *= 0.8
    water = wl > h - 0.05
    col[water] = (0.45, 0.62, 0.78)
    return png_bytes(np.round(np.clip(col, 0, 1) * 255).astype(np.uint8))


def poly(pts, **kw):
    a = " ".join(f"{px(x, y)[0]:.1f},{px(x, y)[1]:.1f}" for x, y in pts)
    attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
    return f'<polyline points="{a}" fill="none" {attrs}/>'


def rect_pts(cx, cy, w, d, yaw):
    a = math.radians(yaw); c, s = math.cos(a), math.sin(a)
    return [(cx + u * c - v * s, cy + u * s + v * c) for u, v in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2))]


def text(x, y, s, size=11, anchor="start", weight="normal", fill="#1b1b1b", halo=True):
    X, Y = px(x, y)
    h = ' stroke="#ffffffcc" stroke-width="3" paint-order="stroke"' if halo else ""
    return f'<text x="{X:.1f}" y="{Y:.1f}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}"{h}>{s}</text>'


def main():
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H + 150}" viewBox="0 0 {W} {H + 150}" '
           f'font-family="Helvetica, Arial, sans-serif">',
           f'<rect width="{W}" height="{H + 150}" fill="#fbfaf6"/>',
           f'<image href="data:image/png;base64,{base64.b64encode(background()).decode()}" x="0" y="0" width="{W}" height="{H}"/>',
           f'<clipPath id="m"><rect width="{W}" height="{H}"/></clipPath><g clip-path="url(#m)">']
    # streets (from the routed paths: what the terrain was cut to)
    st = json.load(open(os.path.join(terrain.OUT_ROOT, LT.NAME, "stats.json")))
    routed = {k: [(x + LT.CX, y - LT.OY) for x, y in v] for k, v in st["routed_paths"].items()}
    kinds = {s[0]: (s[2], s[3]) for s in LT.STREETS}
    for nm, pts in routed.items():
        if nm == "rail":
            continue
        w, kind = kinds.get(nm, (4, "street"))
        P = terrain.spline(pts, 3.0)[:, :2]
        if kind == "road":
            out.append(poly(P, stroke="#2b2b2b", stroke_width=f"{w * S:.1f}", stroke_linecap="round", stroke_linejoin="round"))
            out.append(poly(P, stroke="#e3b300", stroke_width="1.2"))
        elif kind == "street":
            out.append(poly(P, stroke="#555", stroke_width=f"{w * S:.1f}", stroke_linecap="round", stroke_linejoin="round"))
        elif kind == "walk":
            out.append(poly(P, stroke="#f4f1ea", stroke_width=f"{w * S:.1f}", stroke_linecap="round"))
        else:
            out.append(poly(P, stroke="#8a5a2b", stroke_width="1.6", stroke_dasharray="5 3"))
    rail = terrain.spline(routed["rail"], 3.0)[:, :2]
    out.append(poly(rail, stroke="#222", stroke_width="4"))
    out.append(poly(rail, stroke="#fbfaf6", stroke_width="2", stroke_dasharray="3 5"))
    # bridges
    for (a, b, w, col) in ((LT.BRIDGE["a"], LT.BRIDGE["b"], 10, "#1e5631"), (LT.FOOTBRIDGE["a"], LT.FOOTBRIDGE["b"], 3, "#777")):
        out.append(poly([a, b], stroke=col, stroke_width=f"{(w + 2) * S:.1f}"))
        out.append(poly([a, b], stroke="#2b2b2b" if w > 5 else "#ddd", stroke_width=f"{w * 0.7 * S:.1f}"))
    tu = LT.TUNNEL
    out.append(f'<path d="M{px(tu["x"], tu["y"] - 6)[0]:.1f},{px(tu["x"], tu["y"] - 6)[1]:.1f} a{6 * S:.1f},{6 * S:.1f} 0 0 0 0,{12 * S:.1f}" fill="#111"/>')
    # buildings
    for b in LT.layout_buildings():
        t = btype(b)
        P = rect_pts(b["x"], b["y"], b["w"], b["d"], b["yaw"])
        a = " ".join(f"{px(x, y)[0]:.1f},{px(x, y)[1]:.1f}" for x, y in P)
        out.append(f'<polygon points="{a}" fill="{TYPE[t][0]}" stroke="#222" stroke-width="0.8"/>')
        # the front (door side): a tick
        fx, fy = (P[0][0] + P[1][0]) / 2, (P[0][1] + P[1][1]) / 2
        X, Y = px(fx, fy)
        out.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="1.6" fill="#222"/>')
    # vans and vehicles
    for e in LT.EVIDENCE:
        for (x, y) in e["pts"]:
            X, Y = px(x, y)
            if e["kind"] == "van":
                out.append(f'<rect x="{X - 4.5:.1f}" y="{Y - 2:.1f}" width="9" height="4" fill="#000"/>')
            else:
                out.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="4.2" fill="#c0392b" stroke="#fff" stroke-width="1.2"/>')
    # sightlines
    sights = [((-1405, -828), (-1707, -716), "the reveal: steeple, truss, tower over the trees"),
              ((-1612, -741), (-1585, -830), "the sheriff's window on the bridge"),
              ((-1707, -716), (-2066, -690), None), ((-1707, -716), (-1760, -968), None), ((-1707, -716), (-1585, -842), None)]
    for a, b, lab in sights:
        out.append(poly([a, b], stroke="#6c3483", stroke_width="1.4", stroke_dasharray="7 4", opacity="0.85"))
    # arrivals
    road = terrain.spline(routed["road_gorge"], 4.0)[:, :2]
    river = terrain.spline(routed["gorge_path"], 4.0)[:, :2]
    out.append(poly(road, stroke="#1f77b4", stroke_width="3", opacity="0.75", stroke_dasharray="12 6"))
    out.append(poly(river, stroke="#17becf", stroke_width="3", opacity="0.85", stroke_dasharray="12 6"))
    # hides, exits, people
    for hd in LT.HIDES:
        X, Y = px(hd["x"], hd["y"])
        out.append(f'<polygon points="{X:.1f},{Y - 6:.1f} {X + 5:.1f},{Y + 4:.1f} {X - 5:.1f},{Y + 4:.1f}" fill="#27ae60" stroke="#fff" stroke-width="1"/>')
    for p in LT.PEOPLE:
        X, Y = px(p["x"], p["y"])
        out.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="2.6" fill="#f1c40f" stroke="#333" stroke-width="0.8"/>')
    for e in LT.EXITS:
        x0, y0, x1, y1 = e["rect"]
        x0, x1, y0, y1 = max(x0, X0), min(x1, X1), max(y0, Y0), min(y1, Y1)
        if x1 <= x0 or y1 <= y0:
            continue
        a, b = px(x0, y1), px(x1, y0)
        out.append(f'<rect x="{a[0]:.1f}" y="{a[1]:.1f}" width="{b[0] - a[0]:.1f}" height="{b[1] - a[1]:.1f}" fill="#e74c3c33" stroke="#e74c3c" stroke-width="1.5"/>')
    # labels
    L = [(-1650, -690, "DOWNTOWN (Main Street)", 13, "bold"), (-1612, -748, "sheriff", 10, "normal"), (-1707, -676, "church", 10, "normal"),
         (-1735, -752, "depot museum", 10, "normal"), (-1880, -690, "gas", 10, "normal"), (-1926, -688, "drive-thru", 10, "normal"),
         (-1990, -684, "plaza / video", 10, "normal"), (-2066, -672, "motel (vans behind)", 10, "normal"), (-2112, -826, "THE BAR", 13, "bold"),
         (-1700, -853, "brewery (old mill)", 10, "normal"), (-1640, -918, "water tower", 10, "normal"), (-1760, -1015, "MILL HILL (rentals)", 12, "bold"),
         (-1745, -645, "Church St", 10, "normal"), (-1880, -592, "school", 10, "normal"), (-1592, -812, "truss bridge (road)", 10, "normal"),
         (-2176, -748, "tunnel", 10, "normal"), (-1060, -840, "THE GORGE: road from the estate (south) and the fishermen's path (north)", 12, "bold"),
         (-1810, -726, "inn", 10, "normal"), (-1580, -600, "Gap Road", 10, "normal"), (-1630, -1050, "Tannery Branch trail", 10, "normal"),
         (-1400, -805, "Laurel River", 12, "normal"), (-760, -770, "seam (cove)", 11, "bold"), (-1405, -838, "the reveal", 10, "normal")]
    for x, y, s, sz, wt in L:
        out.append(text(x, y, s, sz, "middle", wt))
    out.append("</g>")
    # legend, scale, north
    ly = H + 18
    out.append(f'<text x="14" y="{ly}" font-size="15" font-weight="bold">Sourwood, N.C.: blockout plan (estate frame; 1 px = {1 / S:.2f} m; contours 5 m, bold 25 m)</text>')
    col, row = 0, 0
    for k, (c, lab) in TYPE.items():
        x, y = 14 + col * 300, ly + 22 + row * 20
        out.append(f'<rect x="{x}" y="{y - 10}" width="14" height="12" fill="{c}" stroke="#222" stroke-width="0.8"/><text x="{x + 20}" y="{y}" font-size="12">{lab}</text>')
        row += 1
        if row == 3:
            row, col = 0, col + 1
    sym = [('<rect x="{x}" y="{y}" width="9" height="4" fill="#000"/>', "the invaders' vans"),
           ('<circle cx="{x}" cy="{y}" r="4" fill="#c0392b" stroke="#fff"/>', "evidence (loot, masks, phones, monitors, model)"),
           ('<circle cx="{x}" cy="{y}" r="3" fill="#f1c40f" stroke="#333"/>', "townspeople's posts"),
           ('<polygon points="{x},{y0} {x5},{y4} {xm5},{y4}" fill="#27ae60"/>', "hiding places"),
           ('<rect x="{x}" y="{y0}" width="14" height="10" fill="#e74c3c33" stroke="#e74c3c"/>', "exits"),
           ('<line x1="{x}" y1="{y}" x2="{x30}" y2="{y}" stroke="#1f77b4" stroke-width="3" stroke-dasharray="8 4"/>', "arrival by the road"),
           ('<line x1="{x}" y1="{y}" x2="{x30}" y2="{y}" stroke="#17becf" stroke-width="3" stroke-dasharray="8 4"/>', "arrival by the river"),
           ('<line x1="{x}" y1="{y}" x2="{x30}" y2="{y}" stroke="#6c3483" stroke-width="1.5" stroke-dasharray="7 4"/>', "sightlines"),
           ('<line x1="{x}" y1="{y}" x2="{x30}" y2="{y}" stroke="#222" stroke-width="4"/>', "heritage rail line")]
    for k, (svg, lab) in enumerate(sym):
        x, y = 14 + 1200 + (k // 5) * 420, ly + 18 + (k % 5) * 20
        out.append(svg.format(x=x, y=y - 4, y0=y - 9, y4=y + 1, x5=x + 5, xm5=x - 5, x30=x + 30) + f'<text x="{x + 40}" y="{y}" font-size="12">{lab}</text>')
    sx = W - 260
    out.append(f'<rect x="{sx}" y="{H - 30}" width="{200 * S:.1f}" height="6" fill="#222"/><text x="{sx}" y="{H - 36}" font-size="12">0</text>'
               f'<text x="{sx + 200 * S:.1f}" y="{H - 36}" font-size="12" text-anchor="end">200 m</text>')
    out.append(f'<g transform="translate({W - 40},{50})"><polygon points="0,-22 9,10 0,4 -9,10" fill="#222"/><text y="28" font-size="14" text-anchor="middle">N</text></g>')
    out.append("</svg>")
    os.makedirs(os.path.join(PROJECT, "design", "town"), exist_ok=True)
    p = os.path.join(PROJECT, "design", "town", "map.svg")
    with open(p, "w") as fh:
        fh.write("\n".join(out))
    print("wrote", p, W, "x", H + 150)


if __name__ == "__main__":
    main()
