"""Guest-room rug: low pile oat wool with a linen-bound edge and a thin sage border
line set in from the edge. Long side along X. Origin is the floor centre."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestRug"

P = dict(name=NAME, size=(3.4, 2.5), thickness=0.014, corner=0.03, line_inset=0.16, line_w=0.022)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    w, d = p["size"]
    t = p["thickness"]
    body = common.mesh_object(f"{n}_Body", common.rounded_slab_bmesh(w, d, t, p["corner"]),
                              col, guest_mats.rug_wool(), root)
    body.location = (0, 0, t / 2)
    common.add_bevel(body, 0.005, segments=2)
    common.box_uv(body, tile=0.5)

    sage = guest_mats.sage_light()
    li, lw = p["line_inset"], p["line_w"]
    hx, hy = w / 2 - li, d / 2 - li
    z = t + 0.0015
    parts = [body]
    for name, size, loc in (("LineN", (2 * hx + lw, lw, 0.003), (0, hy, z)),
                            ("LineS", (2 * hx + lw, lw, 0.003), (0, -hy, z)),
                            ("LineE", (lw, 2 * hy - lw, 0.003), (hx, 0, z)),
                            ("LineW", (lw, 2 * hy - lw, 0.003), (-hx, 0, z))):
        ob = common.mesh_object(f"{n}_{name}", common.box_bmesh(size), col, sage, root)
        ob.location = loc
        common.box_uv(ob, tile=0.25)
        parts.append(ob)
    # bound edge: a soft linen binding rolled round the perimeter
    r_b = t / 2 + 0.002
    loop = common.fillet_polyline([(-w / 2 + r_b * 0.6, -d / 2 + r_b * 0.6, 0), (w / 2 - r_b * 0.6, -d / 2 + r_b * 0.6, 0),
                                   (w / 2 - r_b * 0.6, d / 2 - r_b * 0.6, 0), (-w / 2 + r_b * 0.6, d / 2 - r_b * 0.6, 0)],
                                  p["corner"], segments=4, closed=True)
    bind = common.tube_object(f"{n}_Binding_Piping", [(q.x, q.y, r_b) for q in loop], r_b, col,
                              guest_mats.linen(), root, closed=True, profile_res=1)
    common.box_uv(bind, tile=0.25)
    parts.append(bind)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
