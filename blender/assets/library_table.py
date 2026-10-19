"""Library reading table: a walnut top framed round a sunk green leather writing surface
with a bronze inlay line, on two tapered trestle ends joined by a stretcher with keyed
through-tenons, an apron with two drawers a side, bronze sabots at the feet. 3.2 x 1.2 m, 0.76 m high. Origin: floor centre; the long side faces -Y."""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import library_kit as kit  # noqa: E402
from library_kit import Mesh, common, materials  # noqa: E402

importlib.reload(kit)

NAME = "LibraryTable"

P = dict(
    name=NAME,
    size=(3.2, 1.2),
    height=0.76,
    top_t=0.06,
    inset=(2.62, 0.74),          # leather writing surface
    end_t=0.075,
    end_w=0.86,                  # depth of a trestle end
    end_inset=0.28,
)


def grain_uv(ob):
    """The walnut map's grain runs along v; kit.Mesh puts u along a part's length."""
    for d in ob.data.uv_layers["UVMap"].data:
        pass  # the walnut scan is rotated so its grain runs along u (polyhaven_textures ROTATE): no swap


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    walnut, bronze, leather = materials.walnut(), materials.bronze(), kit.leather_green()

    W, D = p["size"]
    H, tt = p["height"], p["top_t"]
    wood, brz, lea = Mesh(0.5), Mesh(0.5), Mesh(0.2)
    iw, idp = p["inset"]
    rec = 0.003                                  # the leather sits 3 mm below the wood

    # top: a frame of four boards round a sunk leather writing surface, a bronze
    # inlay line round the leather, and a narrower under-slab (shadow line)
    bx, by = (W - iw) / 2, (D - idp) / 2
    for sy in (-1, 1):
        wood.box((0, sy * (D - by) / 2, H - tt / 2), (W, by, tt), shift=(0.1, 0.2 + 0.3 * sy))
    for sx in (-1, 1):
        wood.box((sx * (W - bx) / 2, 0, H - tt / 2), (bx, idp, tt), shift=(0.7, 0.1 + 0.2 * sx))
    wood.box((0, 0, H - tt / 2 - rec / 2), (iw, idp, tt - rec - 0.002), shift=(0.4, 0.4))     # panel under the leather
    wood.box((0, 0, H - tt - 0.016), (W - 0.12, D - 0.12, 0.032), shift=(0.4, 0.7))
    lea.box((0, 0, H - rec - 0.001), (iw, idp, 0.002))
    for sy in (-1, 1):
        brz.box((0, sy * (idp / 2 + 0.006), H + 0.0002), (iw + 0.024, 0.006, 0.0024))
    for sx in (-1, 1):
        brz.box((sx * (iw / 2 + 0.006), 0, H + 0.0002), (0.006, idp, 0.0024))

    # trestle ends: a slab that widens toward the foot, a head block under the top,
    # a stepped foot and bronze sabots
    h_end = H - tt - 0.032
    et = p["end_t"]
    for sx in (-1, 1):
        x = sx * (W / 2 - p["end_inset"])
        z0 = 0.13
        wood.box((x, 0, z0 + (h_end - 0.06 - z0) / 2), (et, p["end_w"] - 0.3, h_end - 0.06 - z0),
                 taper=(1.0, 0.72), shift=(0.2 * sx, 0.3))
        wood.box((x, 0, h_end - 0.03), (et + 0.02, p["end_w"] - 0.1, 0.06), shift=(0.3, 0.4))     # head
        wood.box((x, 0, 0.024 + 0.053), (et + 0.03, p["end_w"] - 0.04, 0.106),
                 taper=(0.8, 0.86), shift=(0.5, 0.1))                                               # foot
        brz.box((x, 0, 0.012), (et + 0.044, p["end_w"] + 0.0, 0.024))                              # sabot
    # stretcher: through-tenons stand proud of the ends, locked by bronze keys
    xs = W / 2 - p["end_inset"]
    proud = 0.05
    wood.box((0, 0, 0.30), (2 * xs + et + 2 * proud, 0.07, 0.085), shift=(0.1, 0.9))
    for sx in (-1, 1):
        brz.box((sx * (xs + et / 2 + proud * 0.45), 0, 0.30 + 0.01), (0.014, 0.05, 0.13), taper=(1.0, 0.7))
    # apron between the ends, with two drawers a side: 3 mm reveals, bronze pulls
    ap_h = 0.085
    za = H - tt - 0.032 - ap_h / 2
    ya = D / 2 - 0.12
    xa = xs - et / 2
    for sy in (-1, 1):
        wood.box((0, sy * ya, za), (2 * xa, 0.022, ap_h), shift=(0.2, 0.4 * sy))
        for k in (-1, 1):
            xd = k * xa / 2
            wood.box((xd, sy * (ya + 0.013), za), (xa - 0.12, 0.012, ap_h - 0.02), shift=(0.3 * k, 0.1))
            brz.box((xd, sy * (ya + 0.024), za), (0.12, 0.012, 0.012))
            for e_ in (-1, 1):
                brz.box((xd + e_ * 0.05, sy * (ya + 0.0215), za), (0.012, 0.008, 0.012))

    w = wood.to_object(f"{n}_Wood", col, walnut, root)
    grain_uv(w)
    common.add_bevel(w, 0.003, segments=1)
    lea.to_object(f"{n}_Leather", col, leather, root)
    b = brz.to_object(f"{n}_Bronze", col, bronze, root)
    common.add_bevel(b, 0.001, segments=1)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
