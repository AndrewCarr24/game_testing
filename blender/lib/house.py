"""Builds a house shell from a floor plan (see blender/levels/plan.py).

Every room gets a floor slab, a ceiling slab (not courtyards) and a 0.15 m lining
on each side, owned by that room (its finishes, its lightmap). Openings, windows,
balustrades and garage doors are cut through every lining on their line. Glazing,
rails, the stair and colliders are added here too. The result is a `Shell` with
the colliders, solids, air volumes, baked objects per room, probes and lights the
level script and the bake need.
"""
import importlib
import math

from mathutils import Vector

from . import common, materials

importlib.reload(common)
importlib.reload(materials)


def _overlap(a0, a1, b0, b1):
    return max(a0, b0), min(a1, b1)


class House:
    def __init__(self, plan, finishes, name="Mansion"):
        self.plan = plan
        self.finishes = finishes          # room -> dict(floor, walls, ceiling, walls_by_side, floor_uv_tile)
        self.name = name
        self.col = common.fresh_collection(f"{name}_Shell")
        self.root = common.empty(f"{name}_Shell", self.col)
        self.colliders, self.solids = [], []
        self.baked = {}                   # room -> [objects]
        self.air = {}                     # room -> [(lo, hi)]
        self.probes = {}                  # room -> Blender point
        self.strips, self.points, self.spots, self.areas = [], [], [], []
        self.lights = []                  # engine fallback lights (when there's no bake)
        self.ramps = []                   # invisible slopes over stairs (player.js walks them smoothly)
        self.doors = []                   # door placements generated from cuts
        self.glow = materials.emissive("M_LightStrip", (1.0, 0.92, 0.82), 4.0)
        self.frame = materials.black_metal()
        # window glass has (almost) no diffuse colour: a light tint here would be lit by the
        # sun like a white sheet and veil the view; dark + low alpha = a faint tint + reflections
        self.glass = materials.glass("M_Glass", tint=(0.02, 0.026, 0.026), alpha=0.1, roughness=0.02)
        self.rail_glass = materials.glass("M_Glass_Rail", tint=(0.03, 0.045, 0.045), alpha=0.14, roughness=0.02)

    # ------------------------------------------------------------- geometry
    def box(self, room, name, lo, hi, mat, collide=True, uv_tile=1.0, bake=False, solid=True):
        size = [hi[i] - lo[i] for i in range(3)]
        if min(size) < 1e-4:
            return None
        ob = common.mesh_object(f"{self.name}_{name}", common.box_bmesh(size), self.col, mat, self.root, smooth=False)
        ob.location = [(lo[i] + hi[i]) / 2 for i in range(3)]
        if room:
            ob["room"] = room
        common.box_uv(ob, tile=uv_tile)
        if solid:
            self.solids.append((tuple(lo), tuple(hi)))
        if collide:
            self.colliders.append(common.aabb_gltf(lo, hi))
        if bake and room:
            self.baked.setdefault(room, []).append(ob)
        return ob

    def z_range(self, room):
        r = self.plan.ROOMS[room]
        z0 = self.plan.LEVEL_Z[r["level"]]
        if r.get("double"):
            return z0, self.plan.TOP
        if r.get("kind") == "courtyard":
            return z0, self.plan.TOP
        return z0, z0 + self.plan.HEIGHT[r["level"]]

    # ---------------------------------------------------------------- build
    def build(self):
        P = self.plan
        for room, r in P.ROOMS.items():
            self.room_shell(room, r)
        for cut in P.CUTS:
            self.cut_fill(cut)
        self.stair(P.STAIR)
        return self

    def room_shell(self, room, r):
        P, T = self.plan, self.plan.T
        x0, y0, x1, y1 = r["rect"]
        z0, z1 = self.z_range(room)
        f = self.finishes[room]
        kind = r.get("kind", "room")
        self.box(room, f"{room}_Floor", (x0, y0, z0 - P.SLAB), (x1, y1, z0), f["floor"],
                 uv_tile=f.get("floor_uv_tile", 2.0), bake=True)
        if kind != "courtyard":
            self.box(room, f"{room}_Ceiling", (x0, y0, z1), (x1, y1, z1 + P.SLAB), f["ceiling"], bake=True)
            for side in "NSEW":
                self.lining(room, r, side, f.get("walls_by_side", {}).get(side, f["walls"]),
                            f.get("wall_uv_tile", 1.0))
            self.air[room] = [((x0 + T, y0 + T, z0), (x1 - T, y1 - T, z1))]
        else:
            self.air[room] = [((x0, y0, z0), (x1, y1, z1 + 2.0))]
        self.probes[room] = ((x0 + x1) / 2, (y0 + y1) / 2, z0 + 1.6)

    def holes_on(self, axis, line, a0, a1, z0, z1, room):
        """Rectangles (a0, a1, z0, z1) cut out of a lining on this line."""
        P = self.plan
        holes = []
        for c in P.CUTS:
            if c["axis"] != axis or abs(c["line"] - line) > 1e-6:
                continue
            ha0, ha1 = _overlap(a0, a1, *c["span"])
            hz0, hz1 = _overlap(z0, z1, *c["z"])
            if ha1 - ha0 > 1e-4 and hz1 - hz0 > 1e-4:
                holes.append((ha0, ha1, hz0, hz1))
        # open boundaries between rooms (gallery ring corners)
        for a, b in P.OPEN:
            if room not in (a, b):
                continue
            other = b if room == a else a
            ox0, oy0, ox1, oy1 = P.ROOMS[other]["rect"]
            if axis == "x" and (abs(oy0 - line) < 1e-6 or abs(oy1 - line) < 1e-6):
                ha0, ha1 = _overlap(a0, a1, ox0, ox1)
            elif axis == "y" and (abs(ox0 - line) < 1e-6 or abs(ox1 - line) < 1e-6):
                ha0, ha1 = _overlap(a0, a1, oy0, oy1)
            else:
                continue
            if ha1 - ha0 > 1e-4:
                holes.append((ha0, ha1, z0, z1))
        return holes

    def lining(self, room, r, side, mat, uv_tile=1.0):
        P, T = self.plan, self.plan.T
        x0, y0, x1, y1 = r["rect"]
        z0, z1 = self.z_range(room)
        if side in "NS":
            axis, line, a0, a1 = "x", (y1 if side == "N" else y0), x0, x1
            d0, d1 = (y1 - T, y1) if side == "N" else (y0, y0 + T)
        else:
            axis, line, a0, a1 = "y", (x1 if side == "E" else x0), y0, y1
            d0, d1 = (x1 - T, x1) if side == "E" else (x0, x0 + T)
        holes = self.holes_on(axis, line, a0, a1, z0, z1, room)
        # split the wall into vertical slices at every hole edge; in each slice keep the
        # z ranges not covered by a hole; merge neighbouring slices with the same ranges
        cuts = sorted({a0, a1} | {h[0] for h in holes} | {h[1] for h in holes})
        slices = []
        for s0, s1 in zip(cuts, cuts[1:]):
            mid = (s0 + s1) / 2
            covered = sorted((h[2], h[3]) for h in holes if h[0] <= mid <= h[1])
            keep, z = [], z0
            for hz0, hz1 in covered:
                if hz0 > z + 1e-4:
                    keep.append((z, hz0))
                z = max(z, hz1)
            if z1 > z + 1e-4:
                keep.append((z, z1))
            if slices and slices[-1][2] == keep and abs(slices[-1][1] - s0) < 1e-6:
                slices[-1] = (slices[-1][0], s1, keep)
            else:
                slices.append((s0, s1, keep))
        for i, (s0, s1, keep) in enumerate(slices):
            for j, (kz0, kz1) in enumerate(keep):
                if axis == "x":
                    lo, hi = (s0, d0, kz0), (s1, d1, kz1)
                else:
                    lo, hi = (d0, s0, kz0), (d1, s1, kz1)
                self.box(room, f"{room}_Wall{side}_{i}_{j}", lo, hi, mat, bake=True, uv_tile=uv_tile)
        self.trim(room, side, axis, slices, (a0 + T, a1 - T), (d0, d1), z0, z1, mat, uv_tile)

    # ---------------------------------------------------------------- trim
    def trim(self, room, side, axis, slices, span, depth, z0, z1, mat, uv_tile,
             base_h=0.07, base_d=0.012, gap_h=0.012):
        """Architectural trim along one wall's room face: a baseboard (the wall's own material,
        so it merges into the wall mesh and is baked) wherever the wall reaches the floor, and a
        shadow gap (a thin dark line, merged with the window frames) where it meets the ceiling."""
        d0, d1 = depth
        face, out = (d0, -1) if side in "NE" else (d1, 1)      # interior face, direction into the room

        def run(name, s0, s1, za, zb, prot, material, bake):
            s0, s1 = max(s0, span[0]), min(s1, span[1])
            if s1 - s0 < 0.05:
                return
            f0, f1 = sorted((face, face + out * prot))
            lo, hi = ((s0, f0, za), (s1, f1, zb)) if axis == "x" else ((f0, s0, za), (f1, s1, zb))
            self.box(room if bake else None, name, lo, hi, material, collide=False, solid=False,
                     bake=bake, uv_tile=uv_tile)

        for i, (s0, s1, keep) in enumerate(slices):
            if keep and keep[0][0] <= z0 + 1e-4 and keep[0][1] >= z0 + base_h:
                run(f"{room}_Base{side}_{i}", s0, s1, z0, z0 + base_h, base_d, mat, True)
            if keep and keep[-1][1] >= z1 - 1e-4 and keep[-1][0] <= z1 - gap_h:
                run(f"{room}_Gap{side}_{i}", s0, s1, z1 - gap_h, z1, 0.003, self.frame, False)

    # ---------------------------------------------------------------- cuts
    def cut_fill(self, c):
        a0, a1 = c["span"]
        z0, z1 = c["z"]
        L = c["line"]
        if c["kind"] == "window":
            self.glazing(c, a0, a1, z0, z1, L)
        elif c["kind"] == "garage_door":
            self.wall_box(None, "GarageDoor", c["axis"], L, a0, a1, z0, z1, 0.06,
                          common.pbr_material("M_GarageDoor", (0.18, 0.18, 0.19), roughness=0.4, metallic=0.6))
        elif c["kind"] == "balustrade":
            self.rail(c, a0, a1, z0, L)
        elif c["kind"] == "opening" and c.get("door"):
            # the opening's reveals (the cut through both linings) skinned dark, like the door's
            # black stops; 3 mm, inside the slab's 4 mm clearance
            T2, sk = 2 * self.plan.T, 0.003
            for nm, (b0, b1, h0, h1) in (("L", (a0, a0 + sk, z0, z1)), ("R", (a1 - sk, a1, z0, z1)),
                                         ("Head", (a0, a1, z1 - sk, z1))):
                self.wall_box(None, f"DoorReveal_{int(a0 * 10)}_{int(L * 10)}_{nm}", c["axis"], L, b0, b1, h0, h1,
                              T2, self.frame, collide=False)
            rot = self.door_rotation(c)
            pos = ((a0 + a1) / 2, L, z0) if c["axis"] == "x" else (L, (a0 + a1) / 2, z0)
            self.doors.append(dict(asset=c["door"], pos=pos, rot=rot, lock=c.get("lock"),
                                   room=c["swing"]))

    def door_rotation(self, c):
        """Door assets swing toward their local +Y; turn that toward the `swing` room."""
        x0, y0, x1, y1 = self.plan.ROOMS[c["swing"]]["rect"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if c["axis"] == "x":
            return 0 if cy > c["line"] else 180
        return -90 if cx > c["line"] else 90

    def wall_box(self, room, name, axis, L, a0, a1, z0, z1, depth, mat, collide=True):
        if axis == "x":
            return self.box(room, name, (a0, L - depth / 2, z0), (a1, L + depth / 2, z1), mat, collide=collide)
        return self.box(room, name, (L - depth / 2, a0, z0), (L + depth / 2, a1, z1), mat, collide=collide)

    def glazing(self, c, a0, a1, z0, z1, L, pitch=1.5, mw=0.05, md=0.12):
        n = f"Window_{len(self.lights)}_{int(a0 * 10)}_{int(L * 10)}_{int(z0)}"
        self.wall_box(None, f"{n}_Sill", c["axis"], L, a0, a1, z0, z0 + 0.05, md, self.frame, collide=False)
        self.wall_box(None, f"{n}_Head", c["axis"], L, a0, a1, z1 - 0.05, z1, md, self.frame, collide=False)
        count = max(1, int(round((a1 - a0) / pitch)))
        for i in range(count + 1):
            m = a0 + i * (a1 - a0) / count
            self.wall_box(None, f"{n}_Mullion_{i}", c["axis"], L, max(a0, m - mw / 2), min(a1, m + mw / 2),
                          z0 + 0.05, z1 - 0.05, md, self.frame, collide=False)
        self.wall_box(None, f"{n}_Glass", c["axis"], L, a0, a1, z0 + 0.05, z1 - 0.05, 0.012, self.glass, collide=False)
        lo, hi = ((a0, L - md / 2, z0), (a1, L + md / 2, z1)) if c["axis"] == "x" else \
                 ((L - md / 2, a0, z0), (L + md / 2, a1, z1))
        self.colliders.append(common.aabb_gltf(lo, hi))
        self.solids.append((lo, hi))

    def rail(self, c, a0, a1, z0, L):
        n = f"Rail_{int(a0 * 10)}_{int(L * 10)}"
        self.wall_box(None, f"{n}_Glass", c["axis"], L, a0, a1, z0, z0 + 1.0, 0.02, self.rail_glass, collide=False)
        self.wall_box(None, f"{n}_Cap", c["axis"], L, a0, a1, z0 + 1.0, z0 + 1.05, 0.05, self.frame, collide=False)
        # invisible collider higher than a jump, so nobody vaults into the void
        lo, hi = ((a0, L - 0.05, z0), (a1, L + 0.05, z0 + 2.2)) if c["axis"] == "x" else \
                 ((L - 0.05, a0, z0), (L + 0.05, a1, z0 + 2.2))
        self.colliders.append(common.aabb_gltf(lo, hi))

    def stair(self, s):
        """Floating (cantilevered) stair: thin treads with open risers, a landing at the
        top, a glass balustrade on the open side. Treads are steps the player walks up."""
        P = self.plan
        (x0, x1), (y0, y1) = s["x"], s["y"]
        top = P.LEVEL_Z[1]
        n = s["risers"]
        rise, run = top / n, (x1 - x0) / (n - 1)
        oak = materials.walnut()
        for i in range(n - 1):
            zt = rise * (i + 1)
            xa = x0 + i * run
            self.box(s["room"], f"Stair_Tread_{i:02d}", (xa, y0, zt - 0.06), (xa + run, y1, zt), oak, uv_tile=0.5,
                     solid=False, bake=True)
            # rail collider per tread on the open side
            self.colliders.append(common.aabb_gltf((xa, y0 - 0.08, zt), (xa + run, y0, zt + 1.2)))
        # an invisible ramp along the nosings (from the floor one run before the first tread to
        # the landing): the player glides up and down instead of popping up 18 cm per tread
        lo, hi = common.to_gltf((x0 - run, y1, 0.0)), common.to_gltf((x1, y0, top))
        self.ramps.append({"x": [lo[0], hi[0]], "z": [lo[2], hi[2]], "y": [0.0, top]})
        lx0, lx1 = s["landing"]
        self.box(s["room"], "Stair_Landing", (lx0, y0, top - 0.2), (lx1, y1 + P.T, top), oak, uv_tile=0.5,
                 solid=False, bake=True)
        self.colliders.append(common.aabb_gltf((lx0, y0 - 0.08, top), (lx1, y0, top + 1.2)))
        # glass balustrade along the stair's open side, following the slope
        length = math.hypot(x1 - x0, top)
        glass = common.mesh_object(f"{self.name}_Stair_Glass", common.box_bmesh((length, 0.02, 0.95)), self.col,
                                   self.rail_glass, self.root, smooth=False)
        glass.location = ((x0 + x1) / 2, y0 - 0.04, top / 2 + 0.55)
        glass.rotation_euler = (0, -math.atan2(top, x1 - x0), 0)
        # the landing's open side (its collider is above) gets the same glass, level
        side = common.mesh_object(f"{self.name}_Stair_Glass_Landing", common.box_bmesh((lx1 - lx0 + 0.02, 0.02, 0.95)),
                                  self.col, self.rail_glass, self.root, smooth=False)
        side.location = ((lx0 + lx1) / 2 + 0.01, y0 - 0.04, top + 0.55)
        # the landing's far end overlooks the entry too: glass + rail collider across it
        end = common.mesh_object(f"{self.name}_Stair_Glass_End", common.box_bmesh((0.02, y1 + P.T - y0, 0.95)), self.col,
                                 self.rail_glass, self.root, smooth=False)
        end.location = (lx1 + 0.04, (y0 + y1 + P.T) / 2, top + 0.55)
        self.colliders.append(common.aabb_gltf((lx1, y0 - 0.08, top), (lx1 + 0.08, y1 + P.T, top + 1.2)))

    # ---------------------------------------------------------------- lights
    def strip(self, room, pos, size, z, power):
        (x, y), (sw, sd) = pos, size
        self.box(room, f"LightStrip_{len(self.strips)}", (x - sw / 2, y - sd / 2, z - 0.006),
                 (x + sw / 2, y + sd / 2, z - 0.001), self.glow, collide=False, solid=False)
        self.strips.append(dict(pos=pos, size=size, z=z, power=power))
        self.lights.append({"type": "rect", "position": common.to_gltf((x, y, z - 0.01)),
                            "width": max(sw, 0.25), "height": max(sd, 0.25), "intensity": 6.0,
                            "color": [1.0, 0.92, 0.82], "lookAt": common.to_gltf((x, y, 0))})

    def point(self, pos, power, color=(1.0, 0.78, 0.55), radius=0.1):
        self.points.append(dict(pos=pos, power=power, color=color, radius=radius))

    def spot(self, pos, aim, power, angle=40.0, blend=0.6, color=(1.0, 0.82, 0.62), radius=0.03):
        """A spot (downlight, picture light, wall grazer): pos -> aim are world points."""
        self.spots.append(dict(pos=pos, aim=aim, power=power, angle=angle, blend=blend, color=color, radius=radius))

    def area(self, pos, size, aim, power, color=(1.0, 0.84, 0.66)):
        """A hidden soft area light, no glowing geometry of its own (a cove's wash out of a
        slot, a backlit panel, under-cabinet light): the fixture that motivates it is a prop
        or trim. pos, aim: world points; size (w, d) metres."""
        self.areas.append(dict(pos=pos, size=size, aim=aim, power=power, color=color))

    # ---------------------------------------------------------------- helpers
    def interior(self, room):
        """Interior rectangle (inside the linings) and floor z, for room-local coords."""
        T = self.plan.T
        x0, y0, x1, y1 = self.plan.ROOMS[room]["rect"]
        if self.plan.ROOMS[room].get("kind") == "courtyard":
            T = 0
        z0, z1 = self.z_range(room)
        return (x0 + T, y0 + T, x1 - T, y1 - T), z0, z1

    def to_world(self, room, local):
        (x0, y0, x1, y1), z0, _ = self.interior(room)
        lx, ly, *lz = local
        return ((x0 + x1) / 2 + lx, (y0 + y1) / 2 + ly, z0 + (lz[0] if lz else 0.0))

    def lightmap_resolution(self, room):
        """Atlas size by the room's visible surface (floor + ceiling + walls) at roughly
        22 texels per metre (4.5 cm), plenty for soft indoor light: most rooms fit 512,
        the big volumes (great room, entry, kitchen, garage, courtyard) get 1024."""
        (x0, y0, x1, y1), z0, z1 = self.interior(room)
        w, d, h = x1 - x0, y1 - y0, z1 - z0
        area = 2 * w * d + 2 * (w + d) * h
        return 512 if area <= 540 else 1024

    # ---------------------------------------------------------------- merge
    def merge(self):
        """Join the shell into one mesh per (room, material) so the engine draws a few
        dozen meshes instead of hundreds. Run after the lightmap UVs are made (the
        Lightmap layer survives the join). Keeps each room's "room" tag."""
        import bpy
        groups = {}
        for ob in list(self.col.objects):
            if ob.type != "MESH" or not ob.data.materials:
                continue
            # rugs (lm_borrow: lit by the floor's lightmap, hidden from the bake) merge apart
            key = (ob.get("room", "_"), ob.data.materials[0].name, bool(ob.get("lm_borrow")))
            groups.setdefault(key, []).append(ob)
        merged = {}
        for (room, mat, rug), obs in groups.items():
            if len(obs) > 1:
                with bpy.context.temp_override(active_object=obs[0], selected_editable_objects=obs,
                                               selected_objects=obs, object=obs[0]):
                    bpy.ops.object.join()
            ob = obs[0]
            ob.name = f"{self.name}_{room}_{mat}" + ("_Rug" if rug else "")
            ob.data.name = ob.name
            merged[(room, mat, rug)] = ob
        self.baked = {}
        for (room, mat, rug), ob in merged.items():
            if room != "_" and "Lightmap" in ob.data.uv_layers:
                self.baked.setdefault(room, []).append(ob)
        return merged
