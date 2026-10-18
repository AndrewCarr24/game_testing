"""Library reading table: a thick walnut top with a green leather writing inset and a
bronze inlay line, on two solid trestle ends joined by a stretcher, bronze sabots at
the feet. 3.2 x 1.2 m, 0.76 m high. Origin: floor centre; the long side faces -Y."""
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


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    walnut, bronze, leather = materials.walnut(), materials.bronze(), kit.leather_green()

    W, D = p["size"]
    H, tt = p["height"], p["top_t"]
    wood, brz, lea = Mesh(0.5), Mesh(0.5), Mesh(0.2)

    # top: slab, a slightly narrower lower slab (shadow line), a leather inset
    wood.box((0, 0, H - tt / 2), (W, D, tt), shift=(0.1, 0.2))
    wood.box((0, 0, H - tt - 0.03), (W - 0.12, D - 0.12, 0.06), shift=(0.4, 0.7))
    iw, idp = p["inset"]
    # recess the leather: frame boards around it stay proud by 3 mm
    lea.box((0, 0, H), (iw, idp, 0.004))
    brz.box((0, (idp + 0.012) / 2, H + 0.0005), (iw + 0.024, 0.006, 0.0024))
    brz.box((0, -(idp + 0.012) / 2, H + 0.0005), (iw + 0.024, 0.006, 0.0024))
    brz.box(((iw + 0.012) / 2, 0, H + 0.0005), (0.006, idp, 0.0024))
    brz.box((-(iw + 0.012) / 2, 0, H + 0.0005), (0.006, idp, 0.0024))

    # trestle ends: a solid slab with a curved-looking stepped profile, and a foot
    h_end = H - tt - 0.05
    for sx in (-1, 1):
        x = sx * (W / 2 - p["end_inset"])
        wood.box((x, 0, 0.05 + (h_end - 0.05) / 2), (p["end_t"], p["end_w"] - 0.14, h_end - 0.05), shift=(0.2 * sx, 0.3))
        wood.box((x, 0, 0.05 + 0.05), (p["end_t"] + 0.02, p["end_w"], 0.1), shift=(0.5, 0.1))   # plinth step
        wood.box((x, 0, h_end - 0.02), (p["end_t"] + 0.02, p["end_w"] + 0.02, 0.06), shift=(0.3, 0.4))  # head
        brz.box((x, 0, 0.012), (p["end_t"] + 0.034, p["end_w"] + 0.03, 0.024))                    # sabot
    # stretcher between the ends, pegged through with bronze
    xs = W / 2 - p["end_inset"]
    wood.box((0, 0, 0.30), (2 * xs - p["end_t"], 0.085, 0.085), shift=(0.1, 0.9))
    for sx in (-1, 1):
        brz.box((sx * (xs - p["end_t"] / 2 - 0.004), 0, 0.30), (0.008, 0.11, 0.11))
    # a shallow drawer front on each long side of the apron
    for sy in (-1, 1):
        wood.box((0, sy * (D / 2 - 0.15), H - tt - 0.06), (2.0, 0.025, 0.1), shift=(0.2, 0.4 * sy))

    w = wood.to_object(f"{n}_Wood", col, walnut, root)
    common.add_bevel(w, 0.004, segments=2)
    lea.to_object(f"{n}_Leather", col, leather, root)
    brz.to_object(f"{n}_Bronze", col, bronze, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
