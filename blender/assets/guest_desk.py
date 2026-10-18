"""Guest writing desk: pale oak top on two solid oak end panels, a shallow drawer
(pull on the sitter side) and a brass rail across the back. The sitter side is -Y.
Origin is the floor centre."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestDesk"

P = dict(name=NAME, width=1.45, depth=0.68, height=0.74, top_t=0.035, panel_t=0.032, panel_inset=0.05,
         drawer_w=0.62, drawer_h=0.11)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    oak, brass, black = guest_mats.oak(), guest_mats.brass(), guest_mats.black()
    own = (col, root, n)
    A = guest_mats.add
    W, D, H, T = p["width"], p["depth"], p["height"], p["top_t"]
    pt = p["panel_t"]
    parts = []

    A(own, "Top", common.rounded_slab_bmesh(W, D, T, 0.025), oak, (0, 0, H - T / 2), bevel=0.004, bucket=parts)
    px = W / 2 - p["panel_inset"] - pt / 2
    pd = D - 0.12
    for s, sx in (("L", -1), ("R", 1)):
        A(own, f"Panel_{s}", common.box_bmesh((pt, pd, H - T)), oak, (sx * px, 0.02, (H - T) / 2), bucket=parts)
        A(own, f"Foot_{s}", common.box_bmesh((pt + 0.004, pd - 0.06, 0.012)), black, (sx * px, 0.02, 0.006), 0, parts)
    # back stretcher panel and drawer case between the end panels
    iw = 2 * px - pt
    A(own, "BackPanel", common.box_bmesh((iw, 0.018, 0.22)), oak, (0, D / 2 - 0.08, H - T - 0.11), bucket=parts)
    dw, dh = p["drawer_w"], p["drawer_h"]
    dx = -iw / 2 + dw / 2 + 0.04
    y_front = -pd / 2 + 0.02 - 0.02
    A(own, "DrawerCase", common.box_bmesh((dw + 0.03, pd - 0.12, dh + 0.03)), oak,
      (dx, 0.02 + 0.02, H - T - (dh + 0.03) / 2), bevel=0.002, bucket=parts)
    A(own, "DrawerFront", common.box_bmesh((dw, 0.02, dh)), oak, (dx, -pd / 2 + 0.04 - 0.005, H - T - 0.015 - dh / 2),
      bevel=0.002, bucket=parts)
    pull = common.mesh_object(f"{n}_Pull", guest_mats.cyl_bmesh(0.006, 0.16, seg=10, axis="x"), col, brass, root)
    pull.location = (dx, -pd / 2 + 0.04 - 0.035, H - T - 0.015 - dh / 2 + 0.0)
    parts.append(pull)
    # brass rail along the back edge of the top: pen / cable rail
    rail = common.mesh_object(f"{n}_Rail", guest_mats.cyl_bmesh(0.006, W - 0.5, seg=10, axis="x"), col, brass, root)
    rail.location = (0, D / 2 - 0.035, H - T - 0.07)
    parts.append(rail)
    return root, [o for o in root.children_recursive if o.type == "MESH"]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
