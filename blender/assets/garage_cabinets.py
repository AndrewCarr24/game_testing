"""Garage cabinetry run (shared kit for the garage_* assets): matte graphite handleless
cabinets with brushed-aluminium finger pulls, a black quartz worktop and a
backsplash with an LED line under the wall units. Two full-height tall units frame
four 0.7 m base modules: three drawer stacks and a glass-fronted beverage fridge
(lit, with bottles), with wall units above, the one over the fridge glazed and lit.

Units are metres. The front faces -Y, the origin is the floor centre.

This file also holds the small kit (Builder, shared materials) that the other
garage_* assets import; it is the only helper module they depend on.
"""
import importlib
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "GarageCabinets"


# --------------------------------------------------------------------- shared kit

def graphite():
    return common.pbr_material("M_Garage_Graphite", (0.036, 0.038, 0.042), roughness=0.5, coat=0.05)


def graphite_dark():
    return common.pbr_material("M_Garage_GraphiteDark", (0.012, 0.012, 0.014), roughness=0.6)


def aluminium():
    return common.pbr_material("M_Garage_Aluminium", (0.66, 0.67, 0.69), roughness=0.34, metallic=1.0)


def quartz():
    return common.pbr_material("M_Garage_Quartz", (0.022, 0.023, 0.026), roughness=0.22, coat=0.2)


def led(strength=3.0):
    return materials.emissive("M_Garage_LED", (1.0, 0.86, 0.66), strength)


def glass_dark():
    return materials.glass("M_Garage_Glass", tint=(0.18, 0.22, 0.24), alpha=0.3, roughness=0.03)


def white_lacquer():
    return common.pbr_material("M_Garage_WhiteLacquer", (0.62, 0.62, 0.60), roughness=0.4, coat=0.05)


# --- mudroom palette: warm cream lacquer, light oak, sage tile -----------------

def cream():
    return common.pbr_material("M_Mudroom_Cream", (0.62, 0.59, 0.53), roughness=0.45, coat=0.05)


def oak_light():
    m = common.pbr_material("M_Mudroom_Oak", (0.30, 0.20, 0.11), roughness=0.5, coat=0.1)
    common.set_base_color_map(m, textures.load(textures.wood(
        "T_Garage_OakLight_BaseColor", dark=(0.17, 0.105, 0.052), light=(0.40, 0.27, 0.145), seed=63, rings=34)))
    return m


def sage():
    return common.pbr_material("M_Mudroom_Sage", (0.11, 0.17, 0.115), roughness=0.3, coat=0.3)


def linen(name="M_Fabric_Oat", colour=(0.42, 0.37, 0.30)):
    return materials.fabric(name, colour)


class Builder:
    """Collection + root + helpers for boxes, cylinders and UVs. Every part is built as
    its own object, then finish() merges them into one mesh per (material, solid):
    a prop with hundreds of small parts would otherwise cost hundreds of draw calls.
    Parts bigger than SOLID_VOLUME (or created with solid=True) merge into meshes that
    become one collider box each; small fittings (pulls, bottles, shoes, glass...) merge
    into a "Detail_Piping" mesh per material, whose name keeps it out of the colliders
    (common.COLLIDER_SKIP)."""

    SOLID_VOLUME = 0.02          # m3 of bounding box

    def __init__(self, name):
        self.n = name
        self.col = common.fresh_collection(name)
        self.root = common.empty(name, self.col)
        self.items = []          # (object, solid or None)

    def _add(self, name, bm, mat, loc, tile, bevel, seg, smooth=False, solid=None):
        ob = common.mesh_object(f"{self.n}_{name}", bm, self.col, mat, self.root, smooth=bool(bevel) or smooth)
        ob.location = loc
        if bevel:
            common.add_bevel(ob, bevel, segments=seg)
        common.box_uv(ob, tile=tile)
        self.items.append((ob, solid))
        return ob

    def box(self, name, size, centre, mat, bevel=0.002, tile=0.5, seg=2, solid=None):
        return self._add(name, common.box_bmesh(size), mat, centre, tile, bevel, seg, solid=solid)

    def lo_hi(self, name, lo, hi, mat, **kw):
        size = [hi[i] - lo[i] for i in range(3)]
        centre = [(hi[i] + lo[i]) / 2 for i in range(3)]
        return self.box(name, size, centre, mat, **kw)

    def cyl(self, name, r, h, centre, mat, axis="z", seg=12, tile=0.5, r2=None, bevel=0, solid=None):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                              radius1=r, radius2=r if r2 is None else r2, depth=h)
        if axis == "x":
            bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "Y"))
        elif axis == "y":
            bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "X"))
        return self._add(name, bm, mat, centre, tile, bevel, 2, smooth=True, solid=solid)

    def sphere(self, name, r, centre, mat, scale=(1, 1, 1), seg=12, rings=8, tile=0.5, solid=None):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
        bmesh.ops.scale(bm, vec=Vector(scale), verts=bm.verts)
        return self._add(name, bm, mat, centre, tile, 0, 2, smooth=True, solid=solid)

    def tube(self, name, pts, r, mat, closed=False, res=6):
        ob = common.tube_object(f"{self.n}_{name}", pts, r, self.col, mat, self.root, closed=closed, profile_res=res)
        self.items.append((ob, False))
        return ob

    def parts(self):
        return [o for o in self.root.children_recursive if o.type == "MESH"]

    def finish(self):
        """Merge the parts (modifiers applied) into one mesh per material and solidity."""
        view_layer = bpy.context.view_layer
        view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        buckets = {}
        for ob, solid in self.items:
            mat = ob.data.materials[0] if ob.data.materials else None
            mname = mat.name if mat else "None"
            if solid is None:
                d = ob.evaluated_get(dg).dimensions
                solid = d.x * d.y * d.z > self.SOLID_VOLUME and "Glass" not in mname
            buckets.setdefault((bool(solid), mname), []).append(ob)
        for (solid, mname), obs in buckets.items():
            tmp = []
            for ob in obs:
                me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
                me.transform(ob.matrix_world)
                t = bpy.data.objects.new("tmp", me)
                self.col.objects.link(t)
                tmp.append(t)
            for o in view_layer.objects.selected:
                o.select_set(False)
            for t in tmp:
                t.select_set(True)
            view_layer.objects.active = tmp[0]
            if len(tmp) > 1:
                bpy.ops.object.join()
            merged = view_layer.objects.active
            slug = mname.replace("M_", "")
            merged.name = f"{self.n}_{'Body' if solid else 'Detail_Piping'}_{slug}"
            merged.data.name = merged.name
            merged.parent = self.root
            merged.matrix_parent_inverse = self.root.matrix_world.inverted()
            merged.select_set(False)
        for ob, _ in self.items:
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if me.users == 0:
                bpy.data.meshes.remove(me)
        self.items = []
        return self.root, self.parts()


def front_pull(b, name, width, centre, mat, stand=0.014, h=0.016):
    """Brushed-aluminium finger pull (a slim L-section bar) fixed along a drawer's top edge."""
    b.box(name, (width, stand, h), centre, mat, bevel=0.0015, seg=1)


# ------------------------------------------------------------------------ asset

P = dict(
    name=NAME,
    modules=4,            # base modules between the tall units
    module_w=0.70,
    tall_w=0.70,
    depth=0.62,
    base_h=0.86,          # carcass top (worktop sits on it)
    work_t=0.04,
    tall_h=2.40,
    plinth_h=0.10,
    plinth_recess=0.05,
    wall_z0=1.52,
    wall_z1=2.32,
    wall_depth=0.34,
    door_t=0.020,
    reveal=0.003,
    fridge_module=2,      # 0-based index of the beverage fridge among the base modules
)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402  (react definitions, prompts/interactivity.md)

importlib.reload(ix_common)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    b = Builder(n)
    gr, grd, al, qz = graphite(), graphite_dark(), aluminium(), quartz()
    glow, gl = led(), glass_dark()

    M, mw, tw = p["modules"], p["module_w"], p["tall_w"]
    W = M * mw + 2 * tw
    D = p["depth"]
    yf, yb = -D / 2, D / 2                 # front / back of the carcass
    dt, g = p["door_t"], p["reveal"]
    ph = p["plinth_h"]
    bh = p["base_h"]
    x0 = -W / 2

    # carcass blocks (dark: seen through the reveals)
    fm = p["fridge_module"]

    def modx(i):
        return x0 + tw + i * mw

    # base carcass in runs either side of the fridge cavity, a dark liner around the cavity
    for nm, (ia, ib) in (("A", (0, fm)), ("B", (fm + 1, M))):
        if ib > ia:
            b.lo_hi(f"Carcass_Base{nm}", (modx(ia), yf + dt + 0.004, ph), (modx(ib), yb, bh), grd, bevel=0)
    fa, fb = modx(fm), modx(fm + 1)
    b.lo_hi("Fridge_Liner_B", (fa, yf + dt + 0.004, ph), (fb, yb, ph + 0.04), grd, bevel=0)
    b.lo_hi("Fridge_Liner_T", (fa, yf + dt + 0.004, bh - 0.04), (fb, yb, bh), grd, bevel=0)
    b.lo_hi("Fridge_Liner_L", (fa, yf + dt + 0.004, ph), (fa + 0.02, yb, bh), grd, bevel=0)
    b.lo_hi("Fridge_Liner_R", (fb - 0.02, yf + dt + 0.004, ph), (fb, yb, bh), grd, bevel=0)
    for side, sx in (("L", -1), ("R", 1)):
        xa = sx * (W / 2 - tw / 2)
        b.box(f"Carcass_Tall_{side}", (tw, D - dt - 0.004, p["tall_h"] - ph), (xa, (yf + dt + 0.004 + yb) / 2, (p["tall_h"] + ph) / 2), grd, bevel=0)
    # recessed black plinth
    b.lo_hi("Plinth", (x0 + 0.03, yf + p["plinth_recess"], 0), (-x0 - 0.03, yb - 0.02, ph), grd, bevel=0)

    # --- tall units: two stacked doors each, full-height pull at the inner edge
    for side, sx in (("L", -1), ("R", 1)):
        xc = sx * (W / 2 - tw / 2)
        zs = [(ph + g, 1.30), (1.30 + g, p["tall_h"] - g)]
        for k, (za, zb) in enumerate(zs):
            b.lo_hi(f"Tall_{side}_Door{k}", (xc - tw / 2 + g, yf, za), (xc + tw / 2 - g, yf + dt, zb), gr, bevel=0.002)
        px = xc - sx * (tw / 2 - 0.04)
        b.box(f"Tall_{side}_Pull", (0.018, 0.026, 1.5), (px, yf - 0.011, 1.30), al, bevel=0.002, seg=1)

    # --- base modules
    for i in range(M):
        xa = x0 + tw + i * mw
        xb = xa + mw
        if i == p["fridge_module"]:
            # beverage fridge: aluminium frame, dark glass, lit interior with bottles
            fz0, fz1 = ph + g, bh - g
            b.lo_hi("Fridge_Frame_L", (xa + g, yf, fz0), (xa + 0.035, yf + dt, fz1), al, bevel=0.0015, seg=1)
            b.lo_hi("Fridge_Frame_R", (xb - 0.035, yf, fz0), (xb - g, yf + dt, fz1), al, bevel=0.0015, seg=1)
            b.lo_hi("Fridge_Frame_T", (xa + g, yf, fz1 - 0.035), (xb - g, yf + dt, fz1), al, bevel=0.0015, seg=1)
            b.lo_hi("Fridge_Frame_B", (xa + g, yf, fz0), (xb - g, yf + dt, fz0 + 0.035), al, bevel=0.0015, seg=1)
            b.lo_hi("Fridge_Glass", (xa + 0.035, yf + 0.008, fz0 + 0.035), (xb - 0.035, yf + 0.012, fz1 - 0.035), gl, bevel=0, tile=1.0)
            b.lo_hi("Fridge_Back", (xa + 0.02, yb - 0.03, fz0 + 0.04), (xb - 0.02, yb - 0.025, fz1 - 0.04), glow, bevel=0, tile=1.0)
            nsh = 3
            for s in range(nsh):
                zs_ = fz0 + 0.075 + s * (fz1 - fz0 - 0.15) / (nsh - 0.4)
                b.lo_hi(f"Fridge_Shelf{s}", (xa + 0.025, yf + 0.06, zs_), (xb - 0.025, yb - 0.035, zs_ + 0.008), al, bevel=0, tile=1.0)
                for k in range(4):
                    bx = xa + 0.085 + k * (mw - 0.17) / 3
                    b.cyl(f"Fridge_Bottle{s}_{k}", 0.03, 0.2, (bx, (yf + yb) / 2 + 0.02, zs_ + 0.108), grd, seg=8)
            continue
        # three drawers: 0.16 / 0.20 / the rest
        zt = bh - g
        hs = [0.17, 0.21]
        z = zt
        spans = []
        for h in hs:
            spans.append((z - h, z))
            z -= h + g
        spans.append((ph + g, z))
        for k, (za, zb) in enumerate(spans):
            b.lo_hi(f"Drawer{i}_{k}", (xa + g / 2, yf, za), (xb - g / 2, yf + dt, zb), gr, bevel=0.002)
            front_pull(b, f"Drawer{i}_{k}_Pull", mw - 0.16, ((xa + xb) / 2, yf - 0.007, zb - 0.026), al)

    # --- worktop (black quartz, 2 cm overhang at the front) and aluminium backsplash
    b.lo_hi("Worktop", (x0 + tw, yf - 0.02, bh), (x0 + tw + M * mw, yb, bh + p["work_t"]), qz, bevel=0.002, tile=1.0)
    zb0 = bh + p["work_t"]
    b.lo_hi("Backsplash", (x0 + tw, yb - 0.018, zb0), (x0 + tw + M * mw, yb, p["wall_z0"]), al, bevel=0, tile=0.5)

    # --- wall units over each base module: flat graphite doors, a glazed lit one over the fridge
    wz0, wz1, wd = p["wall_z0"], p["wall_z1"], p["wall_depth"]
    wy0 = yb - wd
    for nm, (ia, ib) in (("A", (0, fm)), ("B", (fm + 1, M))):
        if ib > ia:
            b.lo_hi(f"Wall_Carcass{nm}", (modx(ia), wy0 + dt + 0.004, wz0), (modx(ib), yb, wz1), grd, bevel=0)
    b.lo_hi("Wall_Liner_T", (fa, wy0 + dt + 0.004, wz1 - 0.02), (fb, yb, wz1), grd, bevel=0)
    b.lo_hi("Wall_Liner_B", (fa, wy0 + dt + 0.004, wz0), (fb, yb, wz0 + 0.02), grd, bevel=0)
    b.lo_hi("Wall_Liner_L", (fa, wy0 + dt + 0.004, wz0), (fa + 0.02, yb, wz1), grd, bevel=0)
    b.lo_hi("Wall_Liner_R", (fb - 0.02, wy0 + dt + 0.004, wz0), (fb, yb, wz1), grd, bevel=0)
    for i in range(M):
        xa = x0 + tw + i * mw
        xb = xa + mw
        if i == p["fridge_module"]:
            b.lo_hi(f"Wall{i}_Frame_L", (xa + g, wy0, wz0 + g), (xa + 0.03, wy0 + dt, wz1 - g), al, bevel=0.0015, seg=1)
            b.lo_hi(f"Wall{i}_Frame_R", (xb - 0.03, wy0, wz0 + g), (xb - g, wy0 + dt, wz1 - g), al, bevel=0.0015, seg=1)
            b.lo_hi(f"Wall{i}_Frame_T", (xa + g, wy0, wz1 - 0.03), (xb - g, wy0 + dt, wz1 - g), al, bevel=0.0015, seg=1)
            b.lo_hi(f"Wall{i}_Frame_B", (xa + g, wy0, wz0 + g), (xb - g, wy0 + dt, wz0 + 0.03), al, bevel=0.0015, seg=1)
            b.lo_hi(f"Wall{i}_Glass", (xa + 0.03, wy0 + 0.008, wz0 + 0.03), (xb - 0.03, wy0 + 0.012, wz1 - 0.03), gl, bevel=0, tile=1.0)
            b.lo_hi(f"Wall{i}_Back", (xa + 0.02, yb - 0.02, wz0 + 0.02), (xb - 0.02, yb - 0.015, wz1 - 0.02), glow, bevel=0, tile=1.0)
            zmid = (wz0 + wz1) / 2
            b.lo_hi(f"Wall{i}_Shelf", (xa + 0.02, wy0 + 0.05, zmid), (xb - 0.02, yb - 0.02, zmid + 0.008), al, bevel=0, tile=1.0)
            for k in range(3):   # tumblers
                b.cyl(f"Wall{i}_Glass{k}", 0.032, 0.11, (xa + 0.16 + k * 0.19, yb - 0.12, zmid + 0.063), gl, seg=10, tile=1.0)
            continue
        b.lo_hi(f"Wall{i}_Door", (xa + g / 2, wy0, wz0 + g), (xb - g / 2, wy0 + dt, wz1 - g), gr, bevel=0.002)
        b.box(f"Wall{i}_Pull", (mw - 0.2, 0.014, 0.016), ((xa + xb) / 2, wy0 - 0.007, wz0 + 0.05), al, bevel=0.0015, seg=1)
    # LED line under the wall units
    b.lo_hi("Under_LED", (x0 + tw + 0.03, wy0 + 0.03, wz0 - 0.008), (x0 + tw + M * mw - 0.03, wy0 + 0.05, wz0), glow, bevel=0, tile=1.0)

    ix_common.tag_emissive(b.root)   # interactivity: glowing parts follow the room's light switch
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
