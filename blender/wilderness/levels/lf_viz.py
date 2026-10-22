"""Debug views of a Laurel Fork terrain run: hillshade + contours + routed trails, cropped to an
estate-frame box. $PY lf_viz.py <run> <out.png> [x0 y0 x1 y1] [--paths extra.json]"""
import json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import terrain
OY = 810.0
run, out = sys.argv[1], sys.argv[2]
box = list(map(float, sys.argv[3:7])) if len(sys.argv) >= 7 else [-700, -1300, 650, -40]
D = os.path.join(terrain.OUT_ROOT, run)
H = np.load(D + "/terrain.npz")["H"].astype(float)
st = json.load(open(D + "/stats.json"))
cell = st["cell_m"]; N = H.shape[0]
n, _, _ = terrain.normals(H, cell)
L = np.array([-0.5, 0.5, 0.7]); L /= np.linalg.norm(L)
sh = np.clip((n * L).sum(axis=2), 0, 1) ** 1.2
img = np.dstack([sh * 0.85 + 0.1, sh * 0.82 + 0.1, sh * 0.75 + 0.1])
cont = (np.abs(((H / 10.0) % 1.0) - 0.5) > 0.47)
img[cont] *= 0.6
m = lambda k: terrain.read_png_fast(f"{D}/masks/{k}.png")[::-1].astype(float) / 255
water = np.maximum(m("rivers"), m("lakes")) > 0.3
img[water] = (0.2, 0.45, 0.85)
try:
    img[m("cliff") > 0.3] = (0.9, 0.3, 0.9)
except Exception:
    pass
def draw(pts, col, w=1):
    for a, b in zip(pts[:-1], pts[1:]):
        L = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / (cell * 0.5)))
        for t in np.linspace(0, 1, L):
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            i, j = int(round((x + 768) / cell)), int(round((y + 768) / cell))
            img[max(0, j - w):j + w + 1, max(0, i - w):i + w + 1] = col
cols = [(1, 0.2, 0.1), (1, 0.6, 0.0), (0.9, 0.9, 0.1), (0.6, 0.1, 0.9)]
for k, (nm, pts) in enumerate(st.get("routed_paths", {}).items()):
    draw(terrain.spline(pts, 2.0), cols[k % 4])
if "--paths" in sys.argv:
    for k, pts in enumerate(json.load(open(sys.argv[sys.argv.index("--paths") + 1]))):
        draw(terrain.spline([(x, y + OY) for x, y in pts], 2.0), (0.1, 0.9, 0.9))
i0, i1 = int((box[0] + 768) / cell), int((box[2] + 768) / cell)
j0, j1 = int((box[1] + OY + 768) / cell), int((box[3] + OY + 768) / cell)
crop = img[max(0, j0):j1, max(0, i0):i1]
terrain.write_png(out, np.round(np.clip(crop, 0, 1) * 255).astype(np.uint8))
print(out, crop.shape)
