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


def keep_slices(a0, a1, z0, z1, holes):
    """A wall rectangle (a0..a1 along it, z0..z1) minus `holes` [(a0, a1, z0, z1)]: split into
    vertical slices at every hole edge; in each slice keep the z ranges no hole covers;
    neighbouring slices with the same ranges merge. Returns [(s0, s1, [(kz0, kz1), ...])]."""
    cuts = sorted({a0, a1} | {h[0] for h in holes if a0 < h[0] < a1} | {h[1] for h in holes if a0 < h[1] < a1})
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
    return slices


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
        self.gap_air = []                 # [(lo, hi)]: the gaps through the walls at cuts (lightmap_uv)
        self.probes = {}                  # room -> Blender point
        self.strips, self.points, self.spots, self.areas = [], [], [], []
        self.lights = []                  # engine fallback lights (when there's no bake)
        self.ramps = []                   # invisible slopes over stairs (player.js walks them smoothly)
        self.breakables = []              # glass the engine can shatter (glazing(breakable=...))
        self.doors = []                   # door placements generated from cuts
        self.glow = materials.emissive("M_LightStrip", (1.0, 0.92, 0.82), 4.0)
        self.frame = materials.black_metal()
        # (below ground) shafts that pierce the rooms they stand in: [(room, rect, (z0, z1) incl. slabs)]
        self.shafts = [(n, r["rect"], (self.z_range(n)[0] - plan.SLAB, self.z_range(n)[1] + plan.SLAB))
                       for n, r in plan.ROOMS.items() if r.get("kind") == "shaft"]
        self.hatch_list = list(getattr(plan, "HATCHES", []))
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
            c = common.aabb_gltf(lo, hi)
            # (below ground) the engine keeps these out of the sun's shadow box
            if room and self.plan.ROOMS.get(room, {}).get("level", 0) < 0:
                c["under"] = True
            self.colliders.append(c)
        if bake and room:
            self.baked.setdefault(room, []).append(ob)
        return ob

    def z_range(self, room):
        r = self.plan.ROOMS[room]
        if "z" in r:                      # (below ground) a room with its own extent: a shaft, the armory
            return tuple(r["z"])
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
            self.cut_air(cut)
        self.stair(P.STAIR)
        self.below_ground()
        return self

    def cut_air(self, c):
        """The gap a cut leaves through the walls on its line (both linings, its span and
        height) counts as air for the lightmap UVs: the reveals, the soffit over an opening and
        the wall top under a balustrade face into it and are seen, so they need texels (they
        collapsed to one black texel before). Openings with a door are skinned (DoorReveal)."""
        if c["kind"] == "opening" and c.get("door"):
            return
        T, L, (a0, a1), (z0, z1) = self.plan.T, c["line"], c["span"], c["z"]
        if c["axis"] == "x":
            self.gap_air.append(((a0, L - T, z0), (a1, L + T, z1)))
        else:
            self.gap_air.append(((L - T, a0, z0), (L + T, a1, z1)))

    def room_shell(self, room, r):
        P, T = self.plan, self.plan.T
        x0, y0, x1, y1 = r["rect"]
        z0, z1 = self.z_range(room)
        f = self.finishes[room]
        kind = r.get("kind", "room")
        self.slab(room, f"{room}_Floor", (x0, y0, z0 - P.SLAB), (x1, y1, z0), f["floor"],
                  uv_tile=f.get("floor_uv_tile", 2.0))
        if kind != "courtyard":
            self.slab(room, f"{room}_Ceiling", (x0, y0, z1), (x1, y1, z1 + P.SLAB), f["ceiling"])
            for side in "NSEW":
                self.lining(room, r, side, f.get("walls_by_side", {}).get(side, f["walls"]),
                            f.get("wall_uv_tile", 1.0))
            self.air[room] = self.minus_shafts(room, ((x0 + T, y0 + T, z0), (x1 - T, y1 - T, z1)), grow=T)
            self.shaft_walls(room, r, f["walls"], f.get("wall_uv_tile", 1.0))
        else:
            self.air[room] = [((x0, y0, z0), (x1, y1, z1 + 2.0))]
        self.probes[room] = ((x0 + x1) / 2, (y0 + y1) / 2, z0 + 1.6)

    # ---------------------------------------------------------------- below ground
    def shafts_in(self, room, z0, z1):
        """The shafts (other rooms) that pierce `room` between z0 and z1: [(name, rect)]."""
        x0, y0, x1, y1 = self.plan.ROOMS[room]["rect"]
        out = []
        for name, (sx0, sy0, sx1, sy1), (sz0, sz1) in self.shafts:
            if name == room or sz1 <= z0 + 1e-6 or sz0 >= z1 - 1e-6:
                continue
            if sx0 < x1 - 1e-6 and sx1 > x0 + 1e-6 and sy0 < y1 - 1e-6 and sy1 > y0 + 1e-6:
                out.append((name, (sx0, sy0, sx1, sy1)))
        return out

    def minus_rects(self, lo, hi, holes):
        """A box minus vertical prisms over xy rects `holes`: the pieces, [(lo, hi)]."""
        hs = [(max(lo[0], a), min(hi[0], c), max(lo[1], b), min(hi[1], d)) for a, b, c, d in holes]
        hs = [h for h in hs if h[1] - h[0] > 1e-4 and h[3] - h[2] > 1e-4]
        if not hs:
            return [(tuple(lo), tuple(hi))]
        return [((s0, k0, lo[2]), (s1, k1, hi[2])) for s0, s1, keep in keep_slices(lo[0], hi[0], lo[1], hi[1], hs)
                for k0, k1 in keep if s1 - s0 > 1e-4 and k1 - k0 > 1e-4]

    def minus_shafts(self, room, box, grow=0.0):
        """A room's box (its air, a slab) minus the shafts through it (grown by `grow`: the
        walls the room puts round them)."""
        lo, hi = box
        holes = [(a - grow, b - grow, c + grow, d + grow) for _, (a, b, c, d) in self.shafts_in(room, lo[2], hi[2])]
        return self.minus_rects(lo, hi, holes)

    def slab(self, room, name, lo, hi, mat, uv_tile=1.0):
        """A floor or ceiling slab, minus the shafts through it and the hatches in its z range."""
        holes = [(a, b, c, d) for _, (a, b, c, d) in self.shafts_in(room, lo[2], hi[2])]
        for h in self.hatch_list:
            if h["z"][1] > lo[2] + 1e-6 and h["z"][0] < hi[2] - 1e-6:
                holes.append(h["rect"])
        for i, (a, b) in enumerate(self.minus_rects(lo, hi, holes)):
            self.box(room, name if i == 0 else f"{name}_{i}", a, b, mat, uv_tile=uv_tile, bake=True)

    def lining_shaft_holes(self, room, axis, line, d0, d1, a0, a1, z0, z1):
        """The parts of a lining (along `axis` at `line`, depth band d0..d1) a shaft stands in."""
        holes = []
        for _, (sx0, sy0, sx1, sy1) in self.shafts_in(room, z0, z1):
            b0, b1, c0, c1 = (sy0, sy1, sx0, sx1) if axis == "x" else (sx0, sx1, sy0, sy1)
            if b0 <= d0 + 1e-6 and b1 >= d1 - 1e-6:
                ha0, ha1 = _overlap(a0, a1, c0, c1)
                if ha1 - ha0 > 1e-4:
                    holes.append((ha0, ha1, z0, z1))
        return holes

    def shaft_walls(self, room, r, mat, uv_tile):
        """The walls a room puts round a shaft standing in it (on the shaft's sides inside the
        room's rect; a side on the room's own wall line is the shaft's wall alone), its finish."""
        T = self.plan.T
        x0, y0, x1, y1 = r["rect"]
        z0, z1 = self.z_range(room)
        for name, (sx0, sy0, sx1, sy1) in self.shafts_in(room, z0, z1):
            ix0, iy0, ix1, iy1 = x0 + T, y0 + T, x1 - T, y1 - T
            sides = []
            if sy1 < y1 - 1e-6:       # its north side: the room's wall faces north, y sy1..sy1+T
                sides.append(("N", "x", sy1, (sy1, sy1 + T), (max(ix0, sx0 - T), min(ix1, sx1 + T))))
            if sy0 > y0 + 1e-6:
                sides.append(("S", "x", sy0, (sy0 - T, sy0), (max(ix0, sx0 - T), min(ix1, sx1 + T))))
            if sx1 < x1 - 1e-6:
                sides.append(("E", "y", sx1, (sx1, sx1 + T), (max(iy0, sy0), min(iy1, sy1))))
            if sx0 > x0 + 1e-6:
                sides.append(("W", "y", sx0, (sx0 - T, sx0), (max(iy0, sy0), min(iy1, sy1))))
            for side, axis, line, (d0, d1), (a0, a1) in sides:
                holes = self.holes_on(axis, line, a0, a1, z0, z1, room)
                for i, (s0, s1, keep) in enumerate(keep_slices(a0, a1, z0, z1, holes)):
                    for j, (kz0, kz1) in enumerate(keep):
                        lo, hi = ((s0, d0, kz0), (s1, d1, kz1)) if axis == "x" else ((d0, s0, kz0), (d1, s1, kz1))
                        self.box(room, f"{room}_Shaft{side}_{i}_{j}", lo, hi, mat, bake=True, uv_tile=uv_tile)
                        if kz0 <= z0 + 1e-4 and s1 - s0 > 0.05:      # a baseboard on the room's face
                            face = d1 if side in "NE" else d0
                            out = 1 if side in "NE" else -1
                            f0, f1 = sorted((face, face + out * 0.012))
                            blo, bhi = ((s0, f0, z0), (s1, f1, z0 + 0.07)) if axis == "x" else ((f0, s0, z0), (f1, s1, z0 + 0.07))
                            self.box(room, f"{room}_ShaftBase{side}_{i}", blo, bhi, mat, collide=False, solid=False,
                                     bake=True, uv_tile=uv_tile)

    def below_ground(self):
        """Hatches (cut out of the slabs in room_shell; a `fold` fills one with floor strips that
        drop into a stair), flights, landings and the stair's spine (plan.FLIGHTS, LANDINGS,
        DIVIDERS), the exit stub."""
        P = self.plan
        steel = common.pbr_material("M_Steel_Blackened", (0.035, 0.034, 0.033), roughness=0.42, metallic=0.85)
        for h in self.hatch_list:
            x0, y0, x1, y1 = h["rect"]
            hz0, hz1 = h["z"]
            self.gap_air.append(((x0, y0, hz0), (x1, y1, hz1)))     # the slab's cut faces round it are seen
            fold = h.get("fold")
            if fold:
                self.fold_floor(h, fold)
        for k, fl in enumerate(getattr(P, "FLIGHTS", [])):
            self.flight(k, fl, steel)
        for k, L in enumerate(getattr(P, "LANDINGS", [])):
            a, b, c, d = L["rect"]
            self.box(L["room"], f"Landing_{k}", (a, b, L["z"] - 0.2), (c, d, L["z"]), steel, uv_tile=0.5, bake=True)
        for k, D in enumerate(getattr(P, "DIVIDERS", [])):
            self.box(D["room"], f"Spine_{k}", D["lo"], D["hi"], steel, uv_tile=0.5, bake=True)
        stub = getattr(P, "SECRET_EXIT_STUB", None)
        if stub:
            self.colliders.append(dict(common.aabb_gltf(stub["lo"], stub["hi"]), under=True, stub=True))

    def fold_floor(self, h, fold):
        """A hatch filled with floor strips (the room above's floor: same material, same lightmap
        chart as the floor round them) that drop into a stair when `fold["signal"]` is on: strip k
        (k = 0..treads-1, from the edge at `top` in direction `dir`) by (k+1) rises, the rest of
        the hatch (a landing plate) by treads+1. Each strip is its own mesh with a `react` (slide
        down, a moving collider; motor: false, so it works without the house's power)."""
        room = h["room"]
        f = self.finishes[room]
        x0, y0, x1, y1 = h["rect"]
        top, d, g, rise = fold["top"], fold["dir"], fold["going"], fold["rise"]
        z1 = h["z"][1]
        z0 = z1 - fold.get("thick", 0.4)
        far = y0 if d < 0 else y1
        spans = [(top + d * k * g, top + d * (k + 1) * g, (k + 1) * rise) for k in range(fold["treads"])]
        spans.append((top + d * fold["treads"] * g, far, (fold["treads"] + 1) * rise))
        for k, (a, b, drop) in enumerate(spans):
            ya, yb = min(a, b), max(a, b)
            ob = self.box(room, f"{room}_Fold_{k:02d}", (x0, ya, z0), (x1, yb, z1), f["floor"], collide=False,
                          uv_tile=f.get("floor_uv_tile", 2.0), bake=True)
            ob["moving"] = f"fold{k:02d}"
            # the deeper the strip, the longer it travels: the floor sinks and leaves a step behind
            # at every strip (the nearest first)
            ob["react"] = {"signal": fold["signal"], "on": {"slide": {"axis": "y", "distance": -round(drop, 4)}},
                           "duration": round(1.2 + 1.1 * drop, 3), "collide": True, "motor": False}

    def flight(self, k, fl, mat):
        """A straight flight down from `z` at the nosing line y=`start`, `dir` +1 north / -1 south,
        `n` risers; open-riser plate treads, a steel handrail on both sides and an invisible ramp
        along the nosings (player.js, `along: "z"`)."""
        P = self.plan
        g, rise = fl.get("going", getattr(P, "STAIR_GOING", 0.28)), fl.get("rise", getattr(P, "SR", 0.18))
        x0, x1 = fl["x"]
        s, d, n, z = fl["start"], fl["dir"], fl["n"], fl["z"]
        if fl.get("treads", True):
            for i in range(1, n):
                a, b = s + d * (i - 1) * g, s + d * i * g
                zt = z - i * rise
                self.box(fl["room"], f"Flight{k}_Tread_{i:02d}", (x0, min(a, b), zt - 0.04), (x1, max(a, b), zt), mat,
                         uv_tile=0.5, bake=True, solid=False)
        end = s + d * n * g
        lo, hi = common.to_gltf((x0, s, z)), common.to_gltf((x1, end, z - n * rise))
        self.ramps.append({"x": [lo[0], hi[0]], "z": [lo[2], hi[2]], "y": [z, z - n * rise], "along": "z"})
        # handrails: a 40 mm steel bar 0.9 m over the nosings, 40 mm off each side
        if not fl.get("rails", fl.get("treads", True)):
            return
        rail = common.pbr_material("M_Steel_Satin", (0.55, 0.55, 0.56), roughness=0.3, metallic=1.0)
        for side, xr in (("A", x0 + 0.045), ("B", x1 - 0.045)):
            a = (xr, s + d * 0.15, z + 0.9 - 0.15 * rise / g)
            b = (xr, s + d * (n - 1) * g, z - (n - 1) * rise + 0.9)
            self.bar(fl["room"], f"Flight{k}_Rail{side}", a, b, 0.04, 0.04, rail)
            if fl.get("led") and side == fl.get("led_side", "B"):
                # a LED line under the rail (its light is a LIGHTS area light in the room module)
                c = fl["led"]
                glow = materials.emissive("M_RailLED_" + "".join(f"{int(round(v * 255)):02X}" for v in c), tuple(c), 5.0)
                self.bar(fl["room"], f"Flight{k}_LED", (a[0], a[1], a[2] - 0.026), (b[0], b[1], b[2] - 0.026),
                         0.012, 0.006, glow)

    def bar(self, room, name, a, b, w, h, mat):
        """A bar of section w (x) by h (z) from a to b (points on its axis; x the same at both
        ends): a sloped handrail. Not baked (a metal rail shows its reflections), no collider."""
        import bmesh
        bm = bmesh.new()
        rings = []
        for p in (a, b):
            rings.append([bm.verts.new((p[0] + dx, p[1], p[2] + dz)) for dx, dz in
                          ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))])
        f, k = rings
        for q in ((f[3], f[2], f[1], f[0]), (k[0], k[1], k[2], k[3]), (f[0], f[1], k[1], k[0]),
                  (f[1], f[2], k[2], k[1]), (f[2], f[3], k[3], k[2]), (f[3], f[0], k[0], k[3])):
            bm.faces.new(q)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        ob = common.mesh_object(f"{self.name}_{name}", bm, self.col, mat, self.root, smooth=False)
        if room:
            ob["room"] = room
        return ob


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
        holes += self.lining_shaft_holes(room, axis, line, d0, d1, a0, a1, z0, z1)   # (a shaft stands there)
        slices = keep_slices(a0, a1, z0, z1, holes)
        for i, (s0, s1, keep) in enumerate(slices):
            for j, (kz0, kz1) in enumerate(keep):
                if axis == "x":
                    lo, hi = (s0, d0, kz0), (s1, d1, kz1)
                else:
                    lo, hi = (d0, s0, kz0), (d1, s1, kz1)
                self.box(room, f"{room}_Wall{side}_{i}_{j}", lo, hi, mat, bake=True, uv_tile=uv_tile)
        # the trim stops short of a corner only where a crossing wall stands there: at an open
        # corner (plan.OPEN) it runs to the end, meeting the next room's trim (was a 0.3 m gap)
        ends = {}
        for end, a in (("lo", a0), ("hi", a1)):
            ends[end] = {zz: self.crossing_wall(room, r, axis, a, (d0, d1), zz) for zz in (z0 + 0.03, z1 - 0.03)}
        self.trim(room, side, axis, slices, (a0, a1), ends, (d0, d1), z0, z1, mat, uv_tile)

    def crossing_wall(self, room, r, axis, a, depth, z):
        """Does this room's perpendicular lining stand at wall coordinate `a` (an end of a
        lining on `axis`), across the depth band `depth`, at height z?"""
        x0, y0, x1, y1 = r["rect"]
        z0, z1 = self.z_range(room)
        if axis == "x":         # this wall runs along x; the crossing wall is the W or E lining at x = a
            line, b0, b1 = a, y0, y1
            perp = "y"
        else:
            line, b0, b1 = a, x0, x1
            perp = "x"
        mid = (depth[0] + depth[1]) / 2
        for h0, h1, hz0, hz1 in self.holes_on(perp, line, b0, b1, z0, z1, room):
            if h0 - 1e-6 <= mid <= h1 + 1e-6 and hz0 - 1e-6 <= z <= hz1 + 1e-6:
                return False
        return True

    # ---------------------------------------------------------------- trim
    def trim(self, room, side, axis, slices, span, ends, depth, z0, z1, mat, uv_tile,
             base_h=0.07, base_d=0.012, gap_h=0.012):
        """Architectural trim along one wall's room face: a baseboard (the wall's own material,
        so it merges into the wall mesh and is baked) wherever the wall reaches the floor, and a
        shadow gap (a thin dark line, merged with the window frames) where it meets the ceiling.
        span: the wall's full extent; ends["lo"/"hi"][z]: a crossing wall stands at that end (the
        trim stops at its face, T in; otherwise it runs to the end)."""
        d0, d1 = depth
        T = self.plan.T
        face, out = (d0, -1) if side in "NE" else (d1, 1)      # interior face, direction into the room

        def run(name, s0, s1, za, zb, prot, material, bake):
            zc = z0 + 0.03 if za < z0 + 0.05 else z1 - 0.03
            lo_end = span[0] + (T if ends["lo"][zc] else 0.0)
            hi_end = span[1] - (T if ends["hi"][zc] else 0.0)
            s0, s1 = max(s0, lo_end), min(s1, hi_end)
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
            # the garage's (it was nobody's: no lightmap, no environment -> flat tan)
            ob = self.wall_box("garage", "GarageDoor", c["axis"], L, a0, a1, z0, z1, 0.06,
                               common.pbr_material("M_GarageDoor", (0.18, 0.18, 0.19), roughness=0.4, metallic=0.6))
            self.baked.setdefault("garage", []).append(ob)
        elif c["kind"] == "balustrade":
            self.rail(c, a0, a1, z0, L)
        elif c["kind"] == "opening" and c.get("door"):
            # the opening's reveals (the cut through both linings) skinned dark, like the door's
            # black stops; 3 mm, inside the slab's 4 mm clearance
            T2, sk = 2 * self.plan.T, 0.003
            # exterior doors (going outside): the wall is one lining, L..L+-T on the room's side;
            # a solid door sits in its middle (inset), a glass door on the glass line (inset 0,
            # no reveals: its own surround meets the window mullions)
            ext = self.exterior_side(c)
            Lc = L
            if ext:
                T2 = self.plan.T
                Lc = L + ext * c.get("inset", self.plan.T / 2)
            for nm, (b0, b1, h0, h1) in (("L", (a0, a0 + sk, z0, z1)), ("R", (a1 - sk, a1, z0, z1)),
                                         ("Head", (a0, a1, z1 - sk, z1))):
                if not c.get("reveal", True):
                    break
                self.wall_box(None, f"DoorReveal_{int(a0 * 10)}_{int(L * 10)}_{nm}", c["axis"], L + (ext or 0) * self.plan.T / 2,
                              b0, b1, h0, h1, T2, self.frame, collide=False)
            rot = self.door_rotation(c)
            pos = ((a0 + a1) / 2, Lc, z0) if c["axis"] == "x" else (Lc, (a0 + a1) / 2, z0)
            self.doors.append(dict(asset=c["door"], pos=pos, rot=rot, lock=c.get("lock"),
                                   room=c["swing"], exterior=bool(ext)))

    def door_rotation(self, c):
        """Door assets swing toward their local +Y; turn that toward the `swing` room (away
        from it with swing_out: an exterior door opening outward)."""
        x0, y0, x1, y1 = self.plan.ROOMS[c["swing"]]["rect"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        flip = 180 if c.get("swing_out") else 0
        if c["axis"] == "x":
            return (0 if cy > c["line"] else 180) + flip
        return (-90 if cx > c["line"] else 90) + flip

    def exterior_side(self, c):
        """For a cut in an outer wall (rooms on one side of its line only): the direction
        (+1 / -1 along the wall's normal axis) toward the room; None for an inner wall."""
        if c["z"][1] <= 0.0 + 1e-6:
            return None                   # (below ground: nothing outside to go out to)
        sides = set()
        for r in self.plan.ROOMS.values():
            if self.z_range_of(r)[0] > c["z"][0] + 1e-6 or self.z_range_of(r)[1] < c["z"][1] - 1e-6:
                continue
            x0, y0, x1, y1 = r["rect"]
            lo, hi, b0, b1 = (y0, y1, x0, x1) if c["axis"] == "x" else (x0, x1, y0, y1)
            if b0 >= c["span"][1] - 1e-6 or b1 <= c["span"][0] + 1e-6:
                continue
            if abs(lo - c["line"]) < 1e-6:
                sides.add(1)
            if abs(hi - c["line"]) < 1e-6:
                sides.add(-1)
            if lo + 1e-6 < c["line"] < hi - 1e-6:
                sides.update((1, -1))     # (a shaft's wall inside a room it pierces: the slot into the den)
        return sides.pop() if len(sides) == 1 else None

    def z_range_of(self, r):
        if "z" in r:
            return tuple(r["z"])
        z0 = self.plan.LEVEL_Z[r["level"]]
        return (z0, self.plan.TOP) if r.get("double") or r.get("kind") == "courtyard" else (z0, z0 + self.plan.HEIGHT[r["level"]])

    def wall_box(self, room, name, axis, L, a0, a1, z0, z1, depth, mat, collide=True):
        if axis == "x":
            return self.box(room, name, (a0, L - depth / 2, z0), (a1, L + depth / 2, z1), mat, collide=collide)
        return self.box(room, name, (L - depth / 2, a0, z0), (L + depth / 2, a1, z1), mat, collide=collide)

    def glazing(self, c, a0, a1, z0, z1, L, pitch=1.5, mw=0.05, md=0.12):
        n = f"Window_{len(self.lights)}_{int(a0 * 10)}_{int(L * 10)}_{int(z0)}"
        self.wall_box(None, f"{n}_Sill", c["axis"], L, a0, a1, z0, z0 + 0.05, md, self.frame, collide=False)
        self.wall_box(None, f"{n}_Head", c["axis"], L, a0, a1, z1 - 0.05, z1, md, self.frame, collide=False)
        count = max(1, int(round((a1 - a0) / pitch)))
        at = lambda i: a0 + i * (a1 - a0) / count
        ext = {0: self.jamb_overlap(c, a0, md), count: self.jamb_overlap(c, a1, md)}
        # breakable=(i, j): bays i..j are their own mesh (glass + the mullions inside them), not
        # merged, listed in level["breakables"]: the engine shatters them (the Grimble's way in)
        bi, bj = c.get("breakable", (None, None))
        brk = f"{self.name}_Breakable_{len(self.breakables)}" if bi is not None else None
        for i in range(count + 1):
            m = at(i)
            lo_m = a0 - ext[0] if i == 0 else max(a0, m - mw / 2)
            hi_m = a1 + ext[count] if i == count else min(a1, m + mw / 2)
            ob = self.wall_box(None, f"{n}_Mullion_{i}", c["axis"], L, lo_m, hi_m, z0 + 0.05, z1 - 0.05, md,
                               self.frame, collide=False)
            if brk and bi < i < bj:
                ob["breakable"] = brk
        spans = [(a0, a1, None)] if not brk else [(a0, at(bi), None), (at(bi), at(bj), brk), (at(bj), a1, None)]
        if c.get("glass") == "smoked" and not hasattr(self, "smoked"):
            # (below ground) the slot from the secret stair into the den: dark from the lit side
            self.smoked = materials.glass("M_Glass_Smoked", tint=(0.006, 0.007, 0.007), alpha=0.62, roughness=0.04)
        pane = self.smoked if c.get("glass") == "smoked" else self.glass
        for s0, s1, tag in spans:
            ob = self.wall_box(None, f"{n}_Glass{'_B' if tag else ''}_{int(s0 * 10)}", c["axis"], L, s0, s1,
                               z0 + 0.05, z1 - 0.05, 0.012, pane, collide=False)
            if tag:
                ob["breakable"] = tag
        if brk:
            lo_b, hi_b = ((at(bi), L - md / 2, z0), (at(bj), L + md / 2, z1)) if c["axis"] == "x" else \
                         ((L - md / 2, at(bi), z0), (L + md / 2, at(bj), z1))
            self.breakables.append({"name": brk, "min": common.to_gltf(lo_b), "max": common.to_gltf(hi_b)})
        lo, hi = ((a0, L - md / 2, z0), (a1, L + md / 2, z1)) if c["axis"] == "x" else \
                 ((L - md / 2, a0, z0), (L + md / 2, a1, z1))
        # glass: solid to bodies and swipes, but a sight line passes it (grimble_hunt.js)
        self.colliders.append(dict(common.aabb_gltf(lo, hi), glass=True))
        self.solids.append((lo, hi))

    def jamb_overlap(self, c, a, md):
        """How far a window's end mullion reaches past its end at `a`: into the wall lining
        (1.5 cm, so no sky shows through the joint), or, where another window's glass meets this
        one at a corner (the courtyard), half the frame depth so the corner closes (light leaked
        through the 6 cm square gap in the bake); none where another cut continues the line."""
        P = self.plan
        for o in P.CUTS:
            if o is c:
                continue
            if o["axis"] == c["axis"] and abs(o["line"] - c["line"]) < 1e-6 and \
                    (abs(o["span"][0] - a) < 1e-6 or abs(o["span"][1] - a) < 1e-6) and \
                    o["z"][0] < c["z"][1] and o["z"][1] > c["z"][0]:
                return 0.0
        for o in P.CUTS:
            if o["kind"] == "window" and o["axis"] != c["axis"] and abs(o["line"] - a) < 1e-6 and \
                    o["span"][0] - 1e-6 <= c["line"] <= o["span"][1] + 1e-6 and \
                    o["z"][0] < c["z"][1] and o["z"][1] > c["z"][0]:
                return md / 2
        return 0.015

    def rail(self, c, a0, a1, z0, L):
        n = f"Rail_{int(a0 * 10)}_{int(L * 10)}"
        self.wall_box(None, f"{n}_Glass", c["axis"], L, a0, a1, z0, z0 + 1.0, 0.02, self.rail_glass, collide=False)
        self.wall_box(None, f"{n}_Cap", c["axis"], L, a0, a1, z0 + 1.0, z0 + 1.05, 0.05, self.frame, collide=False)
        # invisible collider higher than a jump, so nobody vaults into the void
        lo, hi = ((a0, L - 0.05, z0), (a1, L + 0.05, z0 + 2.2)) if c["axis"] == "x" else \
                 ((L - 0.05, a0, z0), (L + 0.05, a1, z0 + 2.2))
        # seeThrough: a sight line passes it (the Grimble sees players on the galleries)
        self.colliders.append(dict(common.aabb_gltf(lo, hi), seeThrough=True))

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
            self.colliders.append(dict(common.aabb_gltf((xa, y0 - 0.08, zt), (xa + run, y0, zt + 1.2)), seeThrough=True))
        # an invisible ramp along the nosings (from the floor one run before the first tread to
        # the landing): the player glides up and down instead of popping up 18 cm per tread
        lo, hi = common.to_gltf((x0 - run, y1, 0.0)), common.to_gltf((x1, y0, top))
        self.ramps.append({"x": [lo[0], hi[0]], "z": [lo[2], hi[2]], "y": [0.0, top]})
        lx0, lx1 = s["landing"]
        self.box(s["room"], "Stair_Landing", (lx0, y0, top - 0.2), (lx1, y1 + P.T, top), oak, uv_tile=0.5,
                 solid=False, bake=True)
        self.colliders.append(dict(common.aabb_gltf((lx0, y0 - 0.08, top), (lx1, y0, top + 1.2)), seeThrough=True))
        # glass balustrade: a run of separate panels with 12 mm gaps, as it's built: on the
        # flight, parallelograms (vertical ends, top and bottom parallel to the pitch), then
        # level panels along the landing and one across its far end
        H, gap, yg = 0.95, 0.012, y0 - 0.04
        pitch = lambda x: top * (x - x0) / (x1 - x0) + 0.075          # bottom edge, 7.5 cm over the nosings
        n = math.ceil((x1 - x0) / 1.3)
        for i in range(n):
            xa, xb = x0 + (x1 - x0) * i / n, x0 + (x1 - x0) * (i + 1) / n - gap
            self.glass_panel(f"Stair_Glass_{i}", (xa, yg, pitch(xa)), (xb, yg, pitch(xb)), H)
        n = math.ceil((lx1 + 0.03 - lx0) / 1.6)
        for i in range(n):
            xa = lx0 + gap + (lx1 + 0.03 - lx0 - gap) * i / n
            xb = lx0 + gap + (lx1 + 0.03 - lx0 - gap) * (i + 1) / n - (gap if i < n - 1 else 0)
            self.glass_panel(f"Stair_Glass_Landing_{i}", (xa, yg, top + 0.075), (xb, yg, top + 0.075), H)
        self.glass_panel("Stair_Glass_End", (lx1 + 0.04, y0 - 0.03 + gap, top + 0.075), (lx1 + 0.04, y1 + P.T, top + 0.075), H, along="y")
        self.colliders.append(dict(common.aabb_gltf((lx1, y0 - 0.08, top), (lx1 + 0.08, y1 + P.T, top + 1.2)),
                                   seeThrough=True))

    def glass_panel(self, name, a, b, height, along="x", t=0.02):
        """A glass panel `t` thick from a to b (bottom corners, world), `height` tall
        measured vertically: a parallelogram when a and b differ in z."""
        import bmesh
        bm = bmesh.new()
        off = (0, t / 2, 0) if along == "x" else (t / 2, 0, 0)
        rings = []
        for s_ in (-1, 1):
            o = [s_ * c for c in off]
            rings.append([bm.verts.new((p[0] + o[0], p[1] + o[1], p[2] + dz)) for p, dz in
                          ((a, 0), (b, 0), (b, height), (a, height))])
        f, k = rings
        for q in ((f[0], f[1], f[2], f[3]), (k[3], k[2], k[1], k[0]), (f[0], k[0], k[1], f[1]),
                  (f[1], k[1], k[2], f[2]), (f[2], k[2], k[3], f[3]), (f[3], k[3], k[0], f[0])):
            bm.faces.new(q)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        return common.mesh_object(f"{self.name}_{name}", bm, self.col, self.rail_glass, self.root, smooth=False)

    # ---------------------------------------------------------------- exterior
    def outer_z(self, room):
        """A room's z extent including its floor and ceiling slabs."""
        z0, z1 = self.z_range(room)
        return z0 - self.plan.SLAB, z1 + self.plan.SLAB      # (the courtyard: open up past the roof slabs)

    def exterior_walls(self):
        """The outside of the house: every room side's outer face (its rect edge, slabs
        included) where no other room (the courtyard counts as one) lies beyond it, minus the
        cuts on that line. For the grounds (cladding, outdoor-baked): the faces seen over the
        low roofs from the upper windows were unlit black. Returns
        [(axis, line, outward sign, a0, a1, z0, z1)]."""
        P, out = self.plan, []
        for room, r in P.ROOMS.items():
            if r.get("kind") == "courtyard" or r.get("level", 0) < 0:     # (below ground: no outside)
                continue
            x0, y0, x1, y1 = r["rect"]
            z0, z1 = self.outer_z(room)
            for side in "NSEW":
                if side in "NS":
                    axis, line, a0, a1, sign = "x", (y1 if side == "N" else y0), x0, x1, (1 if side == "N" else -1)
                else:
                    axis, line, a0, a1, sign = "y", (x1 if side == "E" else x0), y0, y1, (1 if side == "E" else -1)
                holes = []
                for o, q in P.ROOMS.items():
                    if o == room:
                        continue
                    qx0, qy0, qx1, qy1 = q["rect"]
                    near = (qy0 if sign > 0 else qy1) if axis == "x" else (qx0 if sign > 0 else qx1)
                    if abs(near - line) > 1e-6:
                        continue
                    b0, b1 = (qx0, qx1) if axis == "x" else (qy0, qy1)
                    ha0, ha1 = _overlap(a0, a1, b0, b1)
                    hz0, hz1 = _overlap(z0, z1, *self.outer_z(o))
                    if ha1 - ha0 > 1e-4 and hz1 - hz0 > 1e-4:
                        holes.append((ha0, ha1, hz0, hz1))
                for c in P.CUTS:
                    if c["axis"] == axis and abs(c["line"] - line) < 1e-6:
                        ha0, ha1 = _overlap(a0, a1, *c["span"])
                        hz0, hz1 = _overlap(z0, z1, *c["z"])
                        if ha1 - ha0 > 1e-4 and hz1 - hz0 > 1e-4:
                            holes.append((ha0, ha1, hz0, hz1))
                for s0, s1, keep in keep_slices(a0, a1, z0, z1, holes):
                    for kz0, kz1 in keep:
                        if s1 - s0 > 1e-3 and kz1 - kz0 > 1e-3:
                            out.append((axis, line, sign, s0, s1, kz0, kz1))
        return out

    def roofs(self):
        """Ceiling-slab tops with no room above them: the low roofs over the cloak and the
        garage (seen from the upper windows) and the main roof. Returns
        [(room, (x0, y0, x1, y1), z_top)], one rectangle per uncovered part."""
        P, out = self.plan, []
        for room, r in P.ROOMS.items():
            if r.get("kind") == "courtyard" or r.get("level", 0) < 0:     # (below ground: under the lawn)
                continue
            top = self.outer_z(room)[1]
            x0, y0, x1, y1 = r["rect"]
            above = []
            for o, q in P.ROOMS.items():
                if o != room and abs(self.outer_z(o)[0] - top) < 1e-6:
                    qx0, qy0, qx1, qy1 = q["rect"]
                    ax0, ax1 = _overlap(x0, x1, qx0, qx1)
                    ay0, ay1 = _overlap(y0, y1, qy0, qy1)
                    if ax1 - ax0 > 1e-4 and ay1 - ay0 > 1e-4:
                        above.append((ax0, ax1, ay0, ay1))
            # the uncovered parts: keep_slices over x (as "a") and y (as "z")
            for s0, s1, keep in keep_slices(x0, x1, y0, y1, above):
                for ky0, ky1 in keep:
                    out.append((room, (s0, ky0, s1, ky1), top))
        return out

    # ---------------------------------------------------------------- lights
    def strip(self, room, pos, size, z, power, color=None):
        """A glowing ceiling slot; `color` (below ground: the armory's cold 6000 K) gives it its
        own glow material (M_LightStrip_<hex>; one strip colour per room) and bake light colour."""
        (x, y), (sw, sd) = pos, size
        glow = self.glow
        if color:
            tag = "".join(f"{int(round(c * 255)):02X}" for c in color)
            glow = materials.emissive(f"M_LightStrip_{tag}", tuple(color), 4.0)
        self.box(room, f"LightStrip_{len(self.strips)}", (x - sw / 2, y - sd / 2, z - 0.006),
                 (x + sw / 2, y + sd / 2, z - 0.001), glow, collide=False, solid=False)
        self.strips.append(dict(pos=pos, size=size, z=z, power=power, **({"color": tuple(color)} if color else {})))
        self.lights.append({"type": "rect", "position": common.to_gltf((x, y, z - 0.01)),
                            "width": max(sw, 0.25), "height": max(sd, 0.25), "intensity": 6.0,
                            "color": list(color or (1.0, 0.92, 0.82)), "lookAt": common.to_gltf((x, y, 0))})

    def point(self, pos, power, color=(1.0, 0.78, 0.55), radius=0.1):
        self.points.append(dict(pos=pos, power=power, color=color, radius=radius))

    def spot(self, pos, aim, power, angle=40.0, blend=0.6, color=(1.0, 0.82, 0.62), radius=0.03):
        """A spot (downlight, picture light, wall grazer): pos -> aim are world points."""
        self.spots.append(dict(pos=pos, aim=aim, power=power, angle=angle, blend=blend, color=color, radius=radius))

    def area(self, pos, size, aim, power, color=(1.0, 0.84, 0.66), shape="rectangle"):
        """A hidden soft area light, no glowing geometry of its own (a cove's wash out of a
        slot, a backlit panel, under-cabinet light): the fixture that motivates it is a prop
        or trim. pos, aim: world points; size (w, d) metres; shape "rectangle" or "ellipse"
        (a round or pill mirror's backlight: no square halo)."""
        if shape not in ("rectangle", "ellipse"):
            raise ValueError(f"area light shape {shape!r}: rectangle or ellipse")
        self.areas.append(dict(pos=pos, size=size, aim=aim, power=power, color=color, shape=shape))

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
            # rugs and wall art (lm_borrow: lit by the floor's / wall's lightmap, hidden from the
            # bake) merge apart
            if ob.get("breakable"):
                key = (ob["breakable"], ob.data.materials[0].name, "")      # its own mesh, by name
                groups.setdefault(key, []).append(ob)
                continue
            key = (ob.get("room", "_"), ob.data.materials[0].name,
                   ob.get("lm_borrow") or ("frames" if ob.get("art_frame") else "") or ob.get("moving", ""))
            groups.setdefault(key, []).append(ob)
        merged = {}
        for (room, mat, rug), obs in groups.items():
            if len(obs) > 1:
                with bpy.context.temp_override(active_object=obs[0], selected_editable_objects=obs,
                                               selected_objects=obs, object=obs[0]):
                    bpy.ops.object.join()
            ob = obs[0]
            ob.name = (f"{room}_{mat}" if room.startswith(f"{self.name}_Breakable") else
                       f"{self.name}_{room}_{mat}" + {"floor": "_Rug", "wall": "_Art", "frames": "_ArtFrames"}.get(
                           rug, f"_{rug}" if rug else ""))     # (a moving piece: Mansion_library_M_..._fold03)
            ob.data.name = ob.name
            merged[(room, mat, rug)] = ob
        self.baked = {}
        for (room, mat, rug), ob in merged.items():
            if room != "_" and "Lightmap" in ob.data.uv_layers:
                self.baked.setdefault(room, []).append(ob)
        return merged
