"""A 1980s strip plaza at the highway end: one storey of painted block, a flat roof behind a
shingled mansard fascia that runs out over a covered walk on square posts, four 16 m units
with aluminium storefronts: a vacant one (blinds down, a blank lease board), a laundromat, a
pharmacy (a green neon cross), and, at the east end, the video store that never closed (lit,
posters as blank coloured rectangles, a tape return slot by the door, a cassette pictogram).

Walk-in: the video store: rows of racks of tapes, the counter with a register, posters, and
behind a door at the back the back room (block walls, a bare bulb; room for the layout's
town_crt_wall against its north wall), a back exit. Its light is baked into COLOR_0.

Origin: floor centre at the door sills; front (the parking lot) -Y. Doors: TownPlaza_Door_1
(video store front), _2 (its back room), _3 (back room exit).
"""
import importlib
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import town_common as tc  # noqa: E402
import town_light  # noqa: E402

importlib.reload(tc.tt)
importlib.reload(tc)
importlib.reload(town_light)
V = tc.V

NAME = "TownPlaza"
P = dict(name=NAME, module="town_plaza", x0=-32.0, x1=32.0, y0=-5.5, y1=8.0, walk=2.5, height=4.3, ceiling=3.2, bake=True)
UNITS = [("vacant", "bk_blinds"), ("laundry", "bk_transom"), ("pharmacy", "bk_shop"), ("video", "bk_video")]


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    x0, x1, y0, y1, T, Hh, C = p["x0"], p["x1"], p["y0"], p["y1"], 0.2, p["height"], p["ceiling"]
    wy = y0 - p["walk"]
    uw = (x1 - x0) / 4
    rng = random.Random(8)

    # ---------------------------------------------------------------- the shell
    front = []
    doors = []
    for i in range(4):
        ux0 = x0 + i * uw
        front.append((ux0 + 0.6, ux0 + uw - 0.6, 0.0, 3.0))
        doors.append(ux0 + uw - 3.0)
    vid_x0, vid_x1 = x0 + 3 * uw, x1
    back_exit = (vid_x1 - 3.0, vid_x1 - 2.0, 0.0, 2.2)
    openings = {"S": front, "N": [back_exit] + [(x0 + i * uw + 2.0, x0 + i * uw + 3.0, 0.0, 2.2) for i in range(3)]}
    tc.shell(kit, x0, x1, y0, y1, Hh, openings, "block", thick=T, reveal_part=kit.p("Reveals", "metal_galv"))
    kit.colliders = [c for c in kit.colliders if not (abs(c[1] - y0) < 0.01 and c[4] - c[1] < 0.3)]   # the front: rebuilt below
    tc.flat_roof(kit, x0, x1, y0, y1, Hh, parapet=0.4, wall="block", coping="metal_galv", sides="NEW")
    # unit party walls (inside the shell, for the colliders and the video store's room)
    for i in range(1, 4):
        tc.wall_collider(kit, "y", x0 + i * uw, y0, y1, T, Hh)
    # storefronts: aluminium framing, a door per unit
    for i, (kind, cell) in enumerate(UNITS):
        a0, a1 = front[i][0], front[i][1]
        dx = doors[i]
        tc.wbox(kit.p("Kick", "metal_galv"), "S", y0, a0, a1, 0.0, 0.4, -0.12, 0.0, skip="back")
        mull = [a0 + (a1 - a0) * k / 5 for k in range(1, 5)]
        mull = [m for m in mull if abs(m - dx) > 0.9] + [dx - 0.6, dx + 0.6]
        cells = [cell, cell, cell, cell, cell, cell] if kind != "video" else ["bk_video", "bk_shop", "bk_video", "bk_video"]
        tc.glazing(kit, "S", y0, a0, a1, 0.4, 3.0, cells=cells, mullions=sorted(mull), transom=2.4, depth=0.1, frame="metal_galv")
        kit.collide((a0, y0, 0), (dx - 0.6, y0 + 0.2, 3.0))
        kit.collide((dx + 0.6, y0, 0), (a1, y0 + 0.2, 3.0))
        kit.collide((x0 + i * uw, y0, 0), (a0, y0 + 0.2, Hh))
        kit.collide((a1, y0, 0), (x0 + (i + 1) * uw, y0 + 0.2, Hh))
        kit.collide((a0, y0, 3.0), (a1, y0 + 0.2, Hh))
        if kind == "video":
            tc.hinged_door(kit, col, root, "S", y0, dx, 1.2, 2.4, depth=0.1, leaf="metal_galv", index=1, style="glass", glass="bk_video")
            tc.wbox(kit.p("ReturnSlot", "metal_galv"), "S", y0, dx + 0.9, dx + 1.5, 0.95, 1.3, 0.0, 0.08)
            tc.wquad(kit.p("ReturnSlot", "glass_dark"), "S", y0, dx + 0.98, dx + 1.42, 1.08, 1.16, 0.082)
            for k in range(3):                       # posters in the windows: blank coloured rectangles
                pa = a0 + 0.5 + k * 1.4
                colr = ("paint_red", "paint_blue", "paint_orange")[k]
                tc.wquad(kit.p("Posters", colr), "S", y0, pa, pa + 0.9, 1.0, 2.3, -0.08)
                tc.wquad(kit.p("Posters", "trim_black"), "S", y0, pa + 0.1, pa + 0.8, 1.8, 2.2, -0.079)
        else:
            tc.door(kit, "S", y0, dx, 1.2, 2.4, leaf="metal_galv", trim="metal_galv", style="glass", glass=cell, casing=0.0, depth=0.1)
        kit.entrance((dx, wy - 0.1, 0.0), "-Y", 1.2, kind="door", note=("TownPlaza_Door_1, the video store" if kind == "video"
                                                                       else f"{kind}, closed"))
    # the covered walk: square posts, the shingled mansard fascia over it, signs on it
    zm0, zm1, out = 3.15, Hh + 0.55, 0.9
    posts = [x0 + 0.3 + k * (x1 - x0 - 0.6) / 16 for k in range(17)]
    for x in posts:
        kit.p("Posts", "block").box((x - 0.18, wy + 0.05, 0.0), (x + 0.18, wy + 0.41, zm0), skip="b")
        kit.collide((x - 0.18, wy + 0.05, 0), (x + 0.18, wy + 0.41, zm0))
    kit.p("WalkCeiling", "paint_white").face([(x0, wy, zm0), (x1, wy, zm0), (x1, y0, zm0), (x0, y0, zm0)], toward=(0, 0, -1))
    M = kit.p("Mansard", "shingle")
    M.face([(x0 - 0.2, wy - 0.3, zm0), (x1 + 0.2, wy - 0.3, zm0), (x1 + 0.2, wy + out, zm1), (x0 - 0.2, wy + out, zm1)],
           toward=(0, -1, 0.6))
    for (xa, s) in ((x0 - 0.2, -1), (x1 + 0.2, 1)):
        M.face([(xa, wy - 0.3, zm0), (xa, y0, zm0), (xa, y0, zm1), (xa, wy + out, zm1)], toward=(s, 0, 0))
    kit.p("MansardTop", "tar").face([(x0 - 0.2, wy + out, zm1), (x1 + 0.2, wy + out, zm1), (x1 + 0.2, y0, zm1),
                                     (x0 - 0.2, y0, zm1)], toward=(0, 0, 1))
    kit.p("MansardTrim", "metal_galv").box((x0 - 0.25, wy - 0.35, zm0 - 0.12), (x1 + 0.25, wy - 0.25, zm0 + 0.02))
    kit.p("WalkSlab", "concrete").box((x0, wy, 0.0), (x1, y0, 0.02), skip="b")
    for k in range(8):
        lx = x0 + 4.0 + k * 8.0
        kit.p("WalkLights", "glow_white").face([(lx - 0.3, wy + 1.0, zm0 - 0.01), (lx + 0.3, wy + 1.0, zm0 - 0.01),
                                                (lx + 0.3, wy + 1.5, zm0 - 0.01), (lx - 0.3, wy + 1.5, zm0 - 0.01)], toward=(0, 0, -1))
    # unit signs on the mansard: blank boards, the green cross, the cassette lit
    Pf = lambda a, t: V(a, wy - 0.3 + (out + 0.3) * t - 0.05, zm0 + (zm1 - zm0) * t)      # noqa: E731
    for i, (kind, cell) in enumerate(UNITS):
        cxs = x0 + i * uw + uw / 2
        if kind == "video":
            q = [Pf(cxs - 2.2, 0.15), Pf(cxs + 2.2, 0.15), Pf(cxs + 2.2, 0.85), Pf(cxs - 2.2, 0.85)]
            kit.p("Signs", "signs", glow=True).face([qq + V(0, -0.04, 0) for qq in q], uvs=tc.sign_uv("video"), toward=(0, -1, 0.6))
        elif kind == "pharmacy":
            q = [Pf(cxs - 2.4, 0.15), Pf(cxs + 2.4, 0.15), Pf(cxs + 2.4, 0.85), Pf(cxs - 2.4, 0.85)]
            kit.p("SignBoards", "paint_white").face([qq + V(0, -0.03, 0) for qq in q], toward=(0, -1, 0.6))
            c0 = Pf(cxs - 1.6, 0.5) + V(0, -0.06, 0)
            G = kit.p("Cross", "neon_green")
            G.cbox(c0, (0.7, 0.08, 0.2))
            G.cbox(c0, (0.22, 0.08, 0.62))
        else:
            q = [Pf(cxs - 2.4, 0.15), Pf(cxs + 2.4, 0.15), Pf(cxs + 2.4, 0.85), Pf(cxs - 2.4, 0.85)]
            kit.p("SignBoards", "paint_blue" if kind == "laundry" else "paint_white").face([qq + V(0, -0.03, 0) for qq in q],
                                                                                         toward=(0, -1, 0.6))
    # the vacant unit's lease board in the window, the back: doors, HVACs, a dumpster
    tc.wquad(kit.p("LeaseBoard", "paper"), "S", y0, x0 + 4.0, x0 + 5.6, 1.2, 2.2, -0.08)
    tc.wquad(kit.p("LeaseBoard", "trim_red"), "S", y0, x0 + 4.1, x0 + 5.5, 1.95, 2.1, -0.078)
    for i in range(3):
        tc.door(kit, "N", y1, x0 + i * uw + 2.5, 1.0, 2.2, leaf="metal_galv", trim="metal_galv",
                wall_part=kit.p("Walls", "block"), casing=0.05)
    tc.hinged_door(kit, col, root, "N", y1, back_exit[0] + 0.5, 1.0, 2.2, depth=0.1, leaf="metal_galv", index=3)
    for i in range(4):
        tc.hvac(kit, x0 + i * uw + 8.0, 3.0, z=Hh, w=1.4, d=1.1, h=0.9)
        tc.meter(kit, "N", y1, x0 + i * uw + 5.0)
    D = kit.p("Dumpster", "trim_green")
    D.box((x0 + 30.0, y1 + 0.8, 0.15), (x0 + 32.0, y1 + 2.2, 1.3))
    kit.p("Dumpster", "rubber").box((x0 + 29.95, y1 + 0.75, 1.3), (x0 + 32.05, y1 + 2.25, 1.38))
    kit.collide((x0 + 30.0, y1 + 0.8, 0), (x0 + 32.0, y1 + 2.2, 1.38))

    # ---------------------------------------------------------------- the video store
    vx0, vx1 = vid_x0 + T / 2, vid_x1 - T
    vy0, vwall, vy1 = y0 + T, 3.9, y1 - T
    br_door = (vx1 - 4.5, vx1 - 3.5, 0.0, 2.2)
    kit.sub = 0.8
    tc.room(kit, vx0, vx1, vy0, vwall - T / 2, 0.0, C, walls="plaster", floor="tile_floor", ceiling="paint_white", name="Video",
            wainscot="trim_black" if False else None, base="trim_black",
            openings={"S": [front[3]], "N": [br_door]})
    tc.room(kit, vx0, vx1, vwall + T / 2, vy1, 0.0, C, walls="block", floor="concrete", ceiling="plaster", name="BackRoom",
            base="trim_black", openings={"S": [br_door], "N": [back_exit]})
    kit.sub = None
    tc.reveals(kit.p("Reveals", "metal_galv"), "N", vwall + T / 2, [br_door], T, sill=False)
    tc.wall_collider(kit, "x", vwall, vid_x0, vid_x1, T, C, [(br_door[0], br_door[1])])
    tc.hinged_door(kit, col, root, "N", vwall + T / 2, (br_door[0] + br_door[1]) / 2, 1.0, 2.2, depth=0.1, leaf="darkwood", index=2,
                   swing=-1)
    # racks of tapes: double-sided, in rows; wall racks along the sides
    for k in range(4):
        rx = vx0 + 3.0 + k * 2.4
        if rx > vx1 - 5.0:
            break
        Rk = kit.p("Racks", "trim_black")
        Rk.box((rx - 0.35, -3.0, 0.0), (rx + 0.35, 2.4, 0.1), skip="b")
        Rk.box((rx - 0.03, -3.0, 0.1), (rx + 0.03, 2.4, 1.8), skip="b")
        for s in (-1, 1):
            for j in range(4):
                z = 0.2 + j * 0.4
                sx0, sx1 = sorted((rx + s * 0.03, rx + s * 0.32))
                Rk.box((sx0, -3.0, z), (sx1, 2.4, z + 0.02))
                uv = tc.cell_uv(tc.WIN["bk_video"], sub=(0.03, 0.16 + 0.2 * (j % 3), 0.97, 0.3 + 0.2 * (j % 3)))
                gx = rx + s * 0.3
                pts = [(gx, -2.95, z + 0.03), (gx, 2.35, z + 0.03), (gx, 2.35, z + 0.36), (gx, -2.95, z + 0.36)]
                kit.p("Tapes", "windows").face(pts if s > 0 else pts[::-1], uvs=uv if s > 0 else uv[::-1], toward=(s, 0, 0))
        kit.collide((rx - 0.35, -3.0, 0), (rx + 0.35, 2.4, 1.8))
    for (ax, s) in ((vx0, 1),):
        for j in range(5):
            z = 0.2 + j * 0.38
            kit.p("WallRack", "trim_black").box((ax, -4.5, z), (ax + 0.3, 3.2, z + 0.02))
            uv = tc.cell_uv(tc.WIN["bk_video"], sub=(0.03, 0.16 + 0.2 * (j % 3), 0.97, 0.3 + 0.2 * (j % 3)))
            kit.p("Tapes", "windows").face([(ax + 0.28, -4.45, z + 0.03), (ax + 0.28, 3.15, z + 0.03), (ax + 0.28, 3.15, z + 0.34),
                                            (ax + 0.28, -4.45, z + 0.34)], uvs=uv, toward=(1, 0, 0))
        kit.collide((ax, -4.5, 0), (ax + 0.3, 3.2, 2.1))
    # posters on the walls: blank coloured rectangles in black frames
    for k in range(6):
        pa = vx0 + 1.0 + k * 2.3
        colr = ("paint_red", "paint_blue", "paint_orange", "paint_teal", "paint_yellow", "trim_red")[k]
        tc.wquad(kit.p("WallPosters", "trim_black"), "S", vwall - T / 2, pa - 0.05, pa + 0.85, 2.0, 3.05, -0.005, inward=True)
        tc.wquad(kit.p("WallPosters", colr), "S", vwall - T / 2, pa, pa + 0.8, 2.05, 3.0, -0.01, inward=True)
    # the counter by the door with a register, a TV on a bracket, a candy rack
    cx0, cx1 = vx1 - 4.6, vx1 - 0.4
    kit.p("Counter", "trim_black").box((cx0, -3.4, 0.0), (cx1, -2.7, 1.0), skip="bt")
    kit.p("CounterTop", "formica").box((cx0 - 0.05, -3.45, 1.0), (cx1 + 0.05, -2.65, 1.05))
    kit.collide((cx0 - 0.05, -3.45, 0), (cx1 + 0.05, -2.65, 1.05))
    kit.p("Register", "metal_dark").box((cx0 + 1.0, -3.3, 1.05), (cx0 + 1.5, -2.9, 1.25))
    kit.p("Register", "glow_cool").face([(cx0 + 1.03, -3.305, 1.12), (cx0 + 1.47, -3.305, 1.12), (cx0 + 1.47, -3.305, 1.23),
                                         (cx0 + 1.03, -3.305, 1.23)], toward=(0, -1, 0))
    kit.p("Candy", "paint_red").box((cx0 + 2.4, -3.48, 1.05), (cx0 + 3.2, -3.1, 1.4))
    kit.p("TV", "metal_dark").box((vx1 - 0.6, -1.0, 2.2), (vx1 - 0.05, 0.0, 2.85))
    kit.p("TV", "glow_cool").face([(vx1 - 0.605, -0.95, 2.25), (vx1 - 0.605, -0.05, 2.25), (vx1 - 0.605, -0.05, 2.8),
                                   (vx1 - 0.605, -0.95, 2.8)], toward=(-1, 0, 0))
    for k in range(3):
        for j in range(2):
            lx, ly = vx0 + 3.0 + k * 5.0, -2.8 + j * 4.0
            kit.p("CeilingPanels", "glow_white").face([(lx - 1.0, ly - 0.25, C - 0.01), (lx + 1.0, ly - 0.25, C - 0.01),
                                                      (lx + 1.0, ly + 0.25, C - 0.01), (lx - 1.0, ly + 0.25, C - 0.01)],
                                                     toward=(0, 0, -1))
            kit.light((lx, ly, C - 0.05), (0.85, 0.9, 1.0), 35, 1.2, kind="AREA")
    kit.light((vx0 + 8.0, y0 + 0.6, 1.8), (1.0, 0.4, 0.8), 15, 1.5, kind="AREA", direction=(0, 1, 0))   # the window glow
    # the back room: a bare bulb, space for the CRT wall on its north wall
    kit.p("Cords", "trim_black").tube(V((vx0 + vx1) / 2, 5.9, 2.6), V((vx0 + vx1) / 2, 5.9, C), 0.006, 3)
    kit.p("Bulbs", "lamp").cyl(((vx0 + vx1) / 2, 5.9), 0.06, 2.45, 2.62, sides=6, caps="tb")
    kit.light(((vx0 + vx1) / 2, 5.9, 2.4), (1.0, 0.7, 0.42), 25, 0.06)
    kit.info["crt_wall_spot"] = [round((vx0 + vx1) / 2 + 2.5, 3), round(vy1 - 0.35, 3), 0.0]

    far = tc.Far(n)
    far.box((x0, y0, 0), (x1, y1, Hh + 0.4), "block", top="tar")
    far.box((x0 - 0.2, wy - 0.3, zm0), (x1 + 0.2, wy + out, zm1), "shingle", top="tar", skip="b")
    for i, (kind, cell) in enumerate(UNITS):
        far.quad("S", y0, front[i][0], front[i][1], 0.4, 3.0, "window_lit" if kind in ("video", "laundry") else "glass_dark")
    kit.info.update(walk_in=True, storeys=1, units=[k for k, _ in UNITS], unit_width=uw,
                    rooms=["video store 15.8 x 9.2 (racks, counter, posters)", "back room 15.8 x 3.9 (CRT wall spot)"],
                    footprint=[round(x0 - 0.25, 3), round(wy - 0.35, 3), x1, round(y1 + 2.3, 3)])
    parts = tc.finish(kit, col, root, far)
    if p["bake"]:
        meshes = [o for o in root.children_recursive if o.type == "MESH" and not o.name.endswith("_LOD1")]
        town_light.bake(kit, root, meshes, [(vx0, vy0, 0.0, vx1, vwall - T / 2, C), (vx0, vwall + T / 2, 0.0, vx1, vy1, C)])
    return root, parts
