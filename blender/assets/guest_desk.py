"""Guest writing desk: a pale oak top with rounded corners and eased edges on two solid
oak end panels (black steel foot strips), joined by a front apron with a shallow
drawer set into it (3 mm reveals, dark backer behind the gaps, brass bar pull on
stand-offs, sitter side) and a modesty panel with a brass cable rail at the back.
The sitter side is -Y. Origin is the floor centre."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402
import guest_wardrobe  # noqa: E402

importlib.reload(guest_mats)
importlib.reload(guest_wardrobe)
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
    g = 0.003

    A(own, "Top", common.rounded_slab_bmesh(W, D, T, 0.025), oak, (0, 0, H - T / 2), bevel=0.005)
    z_u = H - T                                          # underside of the top
    px = W / 2 - p["panel_inset"] - pt / 2
    pd = D - 0.12
    for s, sx in (("L", -1), ("R", 1)):
        A(own, f"Panel_{s}", common.box_bmesh((pt, pd, z_u - 0.012)), oak, (sx * px, 0.02, 0.012 + (z_u - 0.012) / 2),
          bevel=0.003)
        A(own, f"Foot_{s}", common.box_bmesh((pt + 0.004, pd - 0.02, 0.012)), black, (sx * px, 0.02, 0.006), 0.001)
    iw = 2 * px - pt                                     # clear width between the panels
    xl, xr = -iw / 2, iw / 2

    # modesty panel at the back, brass cable rail on its sitter face
    A(own, "BackPanel", common.box_bmesh((iw, 0.018, 0.22)), oak, (0, D / 2 - 0.08, z_u - 0.11), bevel=0.002)
    rail = common.mesh_object(f"{n}_Rail_Piping", guest_mats.cyl_bmesh(0.006, iw - 0.3, seg=10, axis="x"), col, brass, root)
    rail.location = (0, D / 2 - 0.08 - 0.009 - 0.02, z_u - 0.07)
    for k, x in enumerate((-(iw - 0.3) / 2 + 0.02, (iw - 0.3) / 2 - 0.02)):
        A(own, f"RailPost_Piping{k}", guest_mats.cyl_bmesh(0.004, 0.02, seg=8, axis="y"), brass,
          (x, D / 2 - 0.08 - 0.009 - 0.01, z_u - 0.07), 0)

    # front apron with the drawer set into it
    dw, dh = p["drawer_w"], p["drawer_h"]
    ah = dh + 2 * g
    y_ap = -pd / 2 + 0.02 + 0.01                         # apron front face
    at = 0.02
    dx0 = -dw / 2 - g                                   # drawer centred on the sitter
    dx1 = dx0 + dw + 2 * g
    za = z_u - ah / 2
    # apron boards either side, set 8 mm behind the drawer front so the drawer reads as its own box
    ar = 0.008
    A(own, "Apron_L", common.box_bmesh((dx0 - xl, at, ah)), oak, ((xl + dx0) / 2, y_ap + ar + at / 2, za), 0.0015)
    A(own, "Apron_R", common.box_bmesh((xr - dx1, at, ah)), oak, ((dx1 + xr) / 2, y_ap + ar + at / 2, za), 0.0015)
    A(own, "DrawerCase", common.box_bmesh((dw + 0.03, pd - 0.12, 0.012)), oak,
      ((dx0 + dx1) / 2, 0.04, z_u - ah - 0.006), 0.0015)
    A(own, "Backer", common.box_bmesh((dw + 2 * g, 0.004, ah)), black, ((dx0 + dx1) / 2, y_ap + at + 0.004, za), 0)
    dxc = (dx0 + dx1) / 2
    A(own, "DrawerFront", common.box_bmesh((dw, at, dh)), oak, (dxc, y_ap + at / 2, za), 0.0015)
    pw, stand, pr = 0.15, 0.022, 0.005
    pts = common.fillet_polyline([(dxc - pw / 2, y_ap, za), (dxc - pw / 2, y_ap - stand, za),
                                  (dxc + pw / 2, y_ap - stand, za), (dxc + pw / 2, y_ap, za)],
                                 0.009, segments=4, closed=False)
    common.tube_object(f"{n}_Pull_Piping", pts, pr, col, brass, root, closed=False, profile_res=2)
    guest_wardrobe.fix_oak(root)
    return root, [o for o in root.children_recursive if o.type == "MESH"]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
