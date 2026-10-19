"""Library rug: a large hand-knotted style carpet (deep red field, ink-blue border with
ivory lozenges, a central medallion and corner spandrels) painted with numpy into
T_Library_Rug. The map is mapped once across the whole rug, so the border always hugs the
edge. Origin: floor centre; 5.0 x 3.4 m, 12 mm pile."""
import importlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import library_kit as kit  # noqa: E402
from library_kit import Mesh, common, materials, textures  # noqa: E402

importlib.reload(kit)

NAME = "LibraryRug"

P = dict(name=NAME, size=(5.0, 3.4), thickness=0.012)

RED = np.array([0.20, 0.016, 0.012])
NAVY = np.array([0.010, 0.018, 0.050])
IVORY = np.array([0.50, 0.40, 0.26])
GOLD = np.array([0.36, 0.22, 0.05])
RUST = np.array([0.33, 0.07, 0.02])


def rug_texture(size, n=1024, seed=41, force=False):
    path = os.path.join(textures.TEX_DIR, "T_Library_Rug.png")
    if os.path.exists(path) and not force:
        return path
    W, D = size
    rng = np.random.default_rng(seed)
    x = ((np.arange(n) + 0.5) / n - 0.5) * W
    y = (0.5 - (np.arange(n) + 0.5) / n) * D
    x, y = np.meshgrid(x, y)
    img = np.ones((n, n, 3)) * RED
    E = np.minimum(W / 2 - np.abs(x), D / 2 - np.abs(y))

    def paint(mask, col):
        img[mask] = col

    # field lattice of small lozenges
    per = 0.34
    fx, fy = (x % per) - per / 2, (y % per) - per / 2
    a = np.abs(fx) + np.abs(fy)
    field = E > 0.62
    paint(field & (a < 0.085), NAVY)
    paint(field & (a < 0.06), RUST)
    paint(field & (a < 0.025), IVORY)
    # corner spandrels: quarter arcs in navy and gold
    cdist = np.hypot(W / 2 - 0.62 - np.abs(x), D / 2 - 0.62 - np.abs(y))
    paint(field & (cdist < 1.0), RED)
    paint(field & (cdist < 0.95) & (cdist > 0.80), NAVY)
    paint(field & (cdist < 0.90) & (cdist > 0.86), GOLD)
    paint(field & (cdist < 0.66), NAVY)
    paint(field & (cdist < 0.62) & (cdist > 0.58), GOLD)
    paint(field & (cdist < 0.45), RED)
    paint(field & (cdist < 0.18), IVORY)
    # central medallion
    rho = np.sqrt((x / 1.55) ** 2 + (y / 1.0) ** 2)
    paint(rho < 1.0, NAVY)
    paint(rho < 0.93, GOLD)
    paint(rho < 0.9, NAVY)
    paint(rho < 0.82, RED)
    ang = np.arctan2(y / 1.0, x / 1.55)
    petal = (np.cos(10 * ang) * 0.5 + 0.5) * 0.18 + 0.52
    paint((rho < 0.78) & (rho > petal), RUST)
    paint((rho < 0.78) & (rho > petal + 0.06), NAVY)
    paint(rho < 0.5, IVORY)
    paint(rho < 0.47, NAVY)
    loz = np.abs(x / 0.95) + np.abs(y / 0.6)
    paint((rho < 0.47) & (loz < 0.92), RED)
    paint((rho < 0.47) & (loz < 0.75), GOLD)
    paint((rho < 0.47) & (loz < 0.7), NAVY)
    paint((rho < 0.47) & (loz < 0.3), IVORY)
    # border: ink blue with ivory lozenges, framed by guard stripes
    paint(E < 0.62, NAVY)
    horiz = (W / 2 - np.abs(x)) > (D / 2 - np.abs(y))        # nearest edge is top/bottom
    t = np.where(horiz, x, y)
    q = E - 0.34
    per_b = 0.40
    bt = (t % per_b) - per_b / 2
    ab = np.abs(bt) / 1.0 + np.abs(q) * 1.1
    border = (E > 0.12) & (E < 0.56)
    paint(border & (ab < 0.2), IVORY)
    paint(border & (ab < 0.15), RED)
    paint(border & (ab < 0.08), GOLD)
    dot = np.hypot((np.abs(bt) - per_b / 2), q)
    paint(border & (dot < 0.045), RUST)
    paint((E < 0.12), NAVY)
    paint((E > 0.035) & (E < 0.075), IVORY)
    paint((E > 0.565) & (E < 0.595), IVORY)
    paint((E > 0.60) & (E < 0.62), GOLD)
    paint((E < 0.012), IVORY)
    # wool: pile noise, abrash (uneven dye) and a little wear
    fine = textures._noise(n, 1.0, 1.0, 0.25, rng)
    abrash = textures._noise(n, 0.7, 1.0, 2.2, rng)
    tone = 0.9 + 0.09 * fine + 0.14 * abrash
    img = np.clip(img * tone[..., None], 0, 1)
    return textures._save("T_Library_Rug", textures._to_srgb(img))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    W, D = p["size"]
    t = p["thickness"]
    mat = common.pbr_material("M_Library_Rug", (1, 1, 1), roughness=0.95)
    common.set_base_color_map(mat, textures.load(rug_texture(p["size"])))
    m = Mesh(0.25)
    fr = 0.05                                   # fringe length (inside the overall size)
    Wp = W - 2 * fr
    m.box((0, 0, t / 2), (Wp, D, t), taper=(1 - 0.016 / Wp, 1 - 0.016 / D))    # bound edge, rolled over
    # fringe: knotted warp ends on the short sides, ivory, lying on the floor
    for sx in (-1, 1):
        m.box((sx * (Wp / 2 + fr / 2 - 0.004), 0, 0.0015), (fr + 0.008, D - 0.06, 0.003), taper=(0.9, 1.0))
    uv = m.uv
    for f in m.bm.faces:
        for lp in f.loops:
            c = lp.vert.co
            if abs(c.x) > Wp / 2 + 0.002:         # fringe: sample the ivory guard stripe
                lp[uv].uv = (0.5 + (Wp / 2 - 0.006) / Wp * (1 if c.x > 0 else -1), 0.5 + c.y / D)
            else:
                lp[uv].uv = (0.5 + c.x / Wp, 0.5 + c.y / D)
    m.to_object(f"{n}_Pile", col, mat, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
