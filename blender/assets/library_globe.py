"""Antique floor globe: a hand-painted sphere (T_Library_Globe, continents on a
parchment sea with graticule lines) in a bronze meridian ring on a walnut tripod stand.
Origin: floor centre. About 0.62 m across, 1.0 m high."""
import importlib
import math
import os
import sys

import bmesh
import numpy as np
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import library_kit as kit  # noqa: E402
from library_kit import Mesh, common, materials, textures  # noqa: E402

importlib.reload(kit)

NAME = "LibraryGlobe"

P = dict(name=NAME, radius=0.2, centre_z=0.78, tilt=23.5)


def globe_texture(force=False):
    path = os.path.join(textures.TEX_DIR, "T_Library_Globe.png")
    if os.path.exists(path) and not force:
        return path
    n, m = 1024, 512
    rng = np.random.default_rng(8)
    lon = np.linspace(-np.pi, np.pi, n)[None, :] * np.ones((m, 1))
    lat = np.linspace(np.pi / 2, -np.pi / 2, m)[:, None] * np.ones((1, n))
    # seamless continents: noise on the sphere via 3D coordinates, built from random plane waves
    x, y, z = np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)
    h = np.zeros((m, n))
    for _ in range(14):
        k = rng.normal(size=3)
        k /= np.linalg.norm(k)
        freq = rng.uniform(1.2, 4.5)
        h += rng.uniform(0.4, 1.0) / freq * np.sin(freq * (k[0] * x + k[1] * y + k[2] * z) * 2.2 + rng.uniform(0, 6.28))
    land = h > np.quantile(h, 0.57)
    sea = np.array([0.30, 0.26, 0.15])
    land_c = np.array([0.42, 0.20, 0.07])
    img = np.where(land[..., None], land_c, sea)
    shade = 0.9 + 0.12 * np.sin(h * 3)
    img = img * shade[..., None]
    # graticule: every 15 degrees, fine dark lines; the equator and tropics a touch stronger
    deg_lat, deg_lon = np.degrees(lat), np.degrees(lon)
    gl = (np.abs(((deg_lat + 7.5) % 15) - 7.5) < 0.35) | (np.abs(((deg_lon + 7.5) % 15) - 7.5) < 0.35)
    img[gl] *= 0.55
    img[np.abs(deg_lat) < 0.5] = np.array([0.12, 0.05, 0.02])
    return textures._save("T_Library_Globe", textures._to_srgb(np.clip(img, 0, 1)))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    walnut, bronze = materials.walnut(), materials.bronze()
    gm = common.pbr_material("M_Library_Globe", (1, 1, 1), roughness=0.45, coat=0.2)
    common.set_base_color_map(gm, textures.load(globe_texture()))
    R, cz, tilt = p["radius"], p["centre_z"], math.radians(p["tilt"])

    # sphere (poles along the tilted axis), equirectangular UVs from the sphere's own UV unwrap
    bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=20, radius=R, calc_uvs=True)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((0, 0, cz)) @ Matrix.Rotation(tilt, 4, "Y"), verts=bm.verts)
    common.mesh_object(f"{n}_Sphere", bm, col, gm, root, smooth=True)

    wood, brz = Mesh(0.5), Mesh(0.5)
    # bronze meridian ring (a flattened torus, built from a circle of boxes would be heavy: use a tube)
    ring_pts = [(0, 0, 0)]
    pts = []
    for i in range(41):
        a = 2 * math.pi * i / 40
        x, z = (R + 0.03) * math.cos(a), (R + 0.03) * math.sin(a)
        pts.append((x * math.cos(0.0), 0.0, cz + z))
    common.tube_object(f"{n}_Meridian", pts, 0.008, col, bronze, root, closed=True, profile_res=2)
    # axis pin through the poles
    axis = Matrix.Rotation(tilt, 4, "Y")
    from mathutils import Vector
    top = Vector((0, 0, R + 0.05))
    brz.box((0, 0, cz), (0.01, 0.01, 2 * (R + 0.05)), rot=(tilt, "y"))
    # stand: a bronze hub below the globe and three splayed walnut legs
    brz.lathe([(0, 0.0), (0.03, 0.0), (0.03, 0.06), (0.016, 0.07), (0.016, 0.12), (0, 0.12)], segs=14, centre=(0, 0, cz - R - 0.16))
    for i in range(3):
        a = i * 2 * math.pi / 3 + math.pi / 2
        reach = 0.27
        top_z, bot_z = cz - R - 0.11, 0.012
        h = math.hypot(reach, top_z - bot_z)
        splay = math.atan2(reach, top_z - bot_z)
        mid = (reach * 0.5 * math.cos(a), reach * 0.5 * math.sin(a), (top_z + bot_z) / 2)
        # build the leg as a box leaning outward in direction a
        leg = wood.box((0, 0, 0), (0.035, 0.035, h), rot=(-splay, "y"))
        # rotate about Z by a, then place
        bmesh.ops.rotate(wood.bm, verts=leg, cent=(0, 0, 0), matrix=Matrix.Rotation(a - 0.0, 3, "Z"))
        bmesh.ops.translate(wood.bm, vec=mid, verts=leg)
        brz.box((reach * math.cos(a), reach * math.sin(a), 0.01), (0.04, 0.04, 0.02))
    # three stretchers: a ring of thin bars joining the legs part-way up
    wood.to_object(f"{n}_Stand", col, walnut, root)
    brz.to_object(f"{n}_Bronze", col, bronze, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
