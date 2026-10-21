"""Texture atlas for dining_barrel: T_DiningBarrel_BaseColor / _Normal (1024).

Every stave of the barrel has its own strip (u across the stave, v up it, true metres: 902
px/m across the grain, 416 px/m along it), two rows of strips; under them the head (its
boards planar-mapped) and small patches for the stave ends (end grain), the toasted inside
of the chime and the bung. Each strip and head board is cut from a different place of a
scanned oak (Poly Haven oak_veneer_01, CC0, stretched 1.8x along the grain so the veneer's
flat-sawn arches read as the straight riven grain of stave wood), with its own tone, and
painted with what a used barrique carries: darker joints, chime and floor grime, iron-tannin
staining along the hoops, the wine stain and drips round the bung, glass rings on the head.

Regenerated only when missing or when the layout changes (key in build/texture_keys/)."""
import hashlib
import json
import math
import os
import random
import urllib.request

import bpy
import numpy as np

from lib import common, textures

N = 1024
G = 8                       # gutter between islands, px (4 px once the build shrinks it to 512)
STRETCH = 1.8               # scan stretch along the grain
PH_ID = "oak_veneer_01"
PH_SIZE = 1.83              # metres covered by the scan
PROJECT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SCANS = os.path.join(PROJECT, "build", "polyhaven")
KEYS = os.path.join(PROJECT, "build", "texture_keys")
BASE = "T_DiningBarrel_BaseColor"
NORMAL = "T_DiningBarrel_Normal"
VERSION = 8


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


class Atlas:
    def __init__(self, L, p):
        self.L, self.p = L, p
        st = L["staves"]
        n = len(st)
        self.m = m = (n + 1) // 2
        rows = [list(range(m)), list(range(m, n))]
        maxw = max(sum(st[k]["width"] for k in r) for r in rows)
        self.SU = SU = (N - G * (m + 1)) / maxw
        self.R_h = R_h = L["r_in"] + 0.005
        self.SV = SV = (N - 4 * G) / (2 * L["length"] + 2 * R_h)
        self.strip = {}
        for ri, r in enumerate(rows):
            u = G
            v0 = G + ri * (G + L["length"] * SV)
            for k in r:
                self.strip[k] = (u, v0, st[k]["width"] * SU)
                u += st[k]["width"] * SU + G
        vC = 3 * G + 2 * L["length"] * SV
        self.head_c = (G + R_h * SU, vC + R_h * SV)
        x0 = G + 2 * R_h * SU + G
        # patches: (u0, v0, w_px, h_px)
        self.patches = {"end": (x0, vC, 0.13 * SU, 0.07 * SV),
                        "toast": (x0, vC + 0.07 * SV + G, 0.13 * SU, 0.11 * SV),
                        "bung": (x0 + 0.13 * SU + G, vC, 0.07 * SU, 0.07 * SV)}
        rnd = random.Random(p["seed"] + 101)
        self.poff = {k: (rnd.uniform(-0.025, 0.025), rnd.uniform(0, 0.02)) for k in range(n)}

    # -- uv mapping (px -> 0..1) -----------------------------------------------------------
    def stave_uv(self, k, x, s):
        u0, v0, w = self.strip[k]
        return ((u0 + w / 2 + x * self.SU) / N, (v0 + s * self.SV) / N)

    def patch_uv(self, name, k, x, y):
        u0, v0, w, h = self.patches[name]
        ox, oy = self.poff[k]
        return ((u0 + w / 2 + (x + ox) * self.SU) / N, (v0 + (0.004 + y + oy) * self.SV) / N)

    def head_uv(self, x, y):
        cu, cv = self.head_c
        return ((cu + x * self.SU) / N, (cv + y * self.SV) / N)

    def bung_uv(self, x, y):
        u0, v0, w, h = self.patches["bung"]
        return ((u0 + w / 2 + x * self.SU) / N, (v0 + h / 2 + y * self.SV * 2) / N)

    # -- material -------------------------------------------------------------------------
    def key(self):
        L = self.L
        d = dict(v=VERSION, staves=[(round(s["width"], 5)) for s in L["staves"]], length=round(L["length"], 5),
                 s=[round(x, 5) for x in L["s"]], hoops=[(round(a, 4), round(b, 4)) for a, b in L["hoops"]],
                 r_in=round(L["r_in"], 4), seed=self.p["seed"])
        return hashlib.sha1(json.dumps(d).encode()).hexdigest()[:16]

    def material(self):
        base = os.path.join(textures.TEX_DIR, BASE + ".png")
        nor = os.path.join(textures.TEX_DIR, NORMAL + ".png")
        keyf = os.path.join(KEYS, BASE + ".key")
        key = self.key()
        have = os.path.exists(base) and os.path.exists(nor)
        current = have and os.path.exists(keyf) and open(keyf).read().strip() == key
        if not current:
            src = _scan()
            if src is not None or not have:
                self.generate(src)
                os.makedirs(KEYS, exist_ok=True)
                with open(keyf + ".tmp", "w") as f:
                    f.write(key)
                os.replace(keyf + ".tmp", keyf)
        m = common.pbr_material("M_DiningBarrel_Oak", (1, 1, 1), roughness=0.62)
        if not any(nd.type == "TEX_IMAGE" for nd in m.node_tree.nodes):
            common.set_base_color_map(m, textures.load(base))
            common.set_normal_map(m, textures.load(nor, non_color=True), 1.0)
        else:
            for nd in m.node_tree.nodes:
                if nd.type == "TEX_IMAGE" and nd.image:
                    nd.image.reload()
        return m

    # -- painting -------------------------------------------------------------------------
    def generate(self, src):
        L, p = self.L, self.p
        SU, SV = self.SU, self.SV
        Ws, Hs = round(2048 * SU / 1119.0), round(2048 * SV * STRETCH / 1119.0)
        if src is not None:
            col, nrm = _prepare(src, Ws, Hs)
        else:                                      # offline, no scan: generated grain
            rng = np.random.default_rng(3)
            g = textures._noise(512, 1.0, 12.0, 1.6, rng)
            g = np.resize(g, (Hs, Ws))
            col = np.clip(0.5 + 0.35 * g, 0, 1)[..., None] * np.array([0.42, 0.26, 0.12]) * 2
            nrm = np.zeros((Hs, Ws, 3), np.float32)
            nrm[..., 2] = 1
        mean = col.reshape(-1, 3).mean(0)
        detail = col / mean                         # scan relative to its mean colour
        target = np.array(p.get("oak_colour", (0.185, 0.117, 0.066)))
        rng = np.random.default_rng(p["seed"])
        base = np.empty((N, N, 3), np.float32)
        nor = np.empty((N, N, 3), np.float32)
        base[:] = (detail[:N, :N] if detail.shape[0] >= N and detail.shape[1] >= N
                   else np.resize(detail, (N, N, 3))) * target * 0.8
        nor[:] = (0, 0, 1)

        def crop(arr, ox, oy, w, h):
            iy = (oy + np.arange(h)) % arr.shape[0]
            ix = (ox + np.arange(w)) % arr.shape[1]
            return arr[np.ix_(iy, ix)]

        def tone():
            lum = rng.uniform(0.78, 1.2)
            warm = np.array([1.07, 0.97, 0.88])
            grey = np.array([0.95, 0.99, 1.05])
            pink = np.array([1.06, 0.94, 0.95])
            w = rng.dirichlet((1.2, 1.0, 0.7))
            return lum * (w[0] * warm + w[1] * grey + w[2] * pink), rng.uniform(0.8, 1.25)

        # profile s <-> z for the hoops
        zs = np.array([z for _, z in L["outer"]])
        ss = np.array(L["s"])
        s_of = lambda z: float(np.interp(z, zs, ss))
        hoops_s = [(s_of(lo), s_of(hi)) for lo, hi in L["hoops"]]
        s_chamfer = L["s"][-2]
        s_bung = s_of(L["bung_z"])

        # --- staves
        for k, (u0, v0, w) in self.strip.items():
            ua, ub = int(math.floor(u0 - G / 2)), int(math.ceil(u0 + w + G / 2))
            va, vb = max(0, int(math.floor(v0 - G / 2))), min(N, int(math.ceil(v0 + L["length"] * SV + G / 2)))
            ua, ub = max(0, ua), min(N, ub)
            hgt, wid = vb - va, ub - ua
            ox, oy = int(rng.integers(0, Ws)), int(rng.integers(0, Hs))
            tint, contrast = tone()
            d = crop(detail, ox, oy, wid, hgt)
            d = 1 + contrast * (d - 1)
            c = d * target * tint
            n_ = crop(nrm, ox, oy, wid, hgt).copy()
            uu = (np.arange(ua, ub) + 0.5 - u0) / SU - w / SU / 2          # metres from the stave centre
            vv = (np.arange(va, vb) + 0.5 - v0) / SV                       # metres along the stave
            X, S = np.meshgrid(uu, vv)
            half = w / SU / 2
            edge = np.maximum(half - np.abs(X), 0)
            f = 1 - 0.25 * np.exp(-edge / 0.0022)
            f *= 1 - 0.20 * np.exp(-np.maximum(S, 0) / 0.035) - 0.14 * np.exp(-np.maximum(L["length"] - S, 0) / 0.03)
            f *= np.where(S > s_chamfer, 0.8, 1.0)
            # a faint long tonal drift along each stave
            f *= 1 + rng.uniform(-0.07, 0.07) * np.cos(S / L["length"] * math.pi + rng.uniform(0, 6))
            c = c * f[..., None]
            # iron-tannin staining along the hoops (blue-grey, a few mm), dark under them
            for lo, hi in hoops_s:
                under = (S > lo) & (S < hi)
                dist = np.where(S < lo, lo - S, np.where(S > hi, S - hi, 0))
                a = 0.38 * np.exp(-dist / 0.003) * (~under)
                stain = np.array([0.55, 0.55, 0.62])
                c = c * (1 - a[..., None]) + c * stain * a[..., None]
                c[under] *= 0.3
            lum = (c @ np.array([0.2126, 0.7152, 0.0722]))[..., None]
            c = lum + rng.uniform(0.72, 0.95) * (c - lum)           # used oak greys a little, unevenly
            if k == 0:
                c = _wine_stain(c, X, S - s_bung, rng)
            base[va:vb, ua:ub] = c
            nor[va:vb, ua:ub] = n_

        # --- head: five boards, grain along y (v)
        cu, cv = self.head_c
        R = self.R_h
        ua, ub = max(0, int(cu - R * SU - G / 2)), min(N, int(cu + R * SU + G / 2))
        va, vb = max(0, int(cv - R * SV - G / 2)), min(N, int(cv + R * SV + G / 2))
        xs = (np.arange(ua, ub) + 0.5 - cu) / SU
        ys = (np.arange(va, vb) + 0.5 - cv) / SV
        X, Y = np.meshgrid(xs, ys)
        cuts = [-R - 0.01, -0.148, -0.052, 0.045, 0.142, R + 0.01]
        hb = np.zeros(X.shape + (3,), np.float32)
        hn = np.zeros(X.shape + (3,), np.float32)
        for b in range(len(cuts) - 1):
            sel = (X >= cuts[b]) & (X < cuts[b + 1])
            ox, oy = int(rng.integers(0, Ws)), int(rng.integers(0, Hs))
            tint, contrast = tone()
            d = crop(detail, ox, oy, ub - ua, vb - va)
            hb[sel] = ((1 + contrast * (d - 1)) * target * tint * 0.92)[sel]
            hn[sel] = crop(nrm, ox, oy, ub - ua, vb - va)[sel]
        for x in cuts[1:-1]:
            dx = X - x
            hb *= (1 - 0.55 * np.exp(-np.abs(dx) / 0.0011))[..., None]
            tilt = 0.35 * np.sign(dx) * np.exp(-np.abs(dx) / 0.0014)
            hn[..., 0] += tilt
        r = np.hypot(X, Y)
        hb *= (1 - 0.35 * np.clip((r - (self.L["r_head"] - 0.003)) / 0.004, 0, 1))[..., None]   # the bevel
        hb *= (1 - 0.10 * np.exp(-(self.L["r_head"] - r).clip(0) / 0.02))[..., None]           # handling at the rim
        hb = _glass_rings(hb, X, Y, rng)
        hb = _chalk(hb, X, Y, rng)
        hn /= np.linalg.norm(hn, axis=2, keepdims=True)
        base[va:vb, ua:ub] = hb
        nor[va:vb, ua:ub] = hn

        # --- patches
        def fill(name, colour, contrast, normal_amt):
            u0, v0, w, h = self.patches[name]
            a0, a1 = max(0, int(u0 - G / 2)), min(N, int(u0 + w + G / 2))
            b0, b1 = max(0, int(v0 - G / 2)), min(N, int(v0 + h + G / 2))
            ox, oy = int(rng.integers(0, Ws)), int(rng.integers(0, Hs))
            d = crop(detail, ox, oy, a1 - a0, b1 - b0)
            base[b0:b1, a0:a1] = (1 + contrast * (d - 1)) * np.array(colour)
            nn = crop(nrm, ox, oy, a1 - a0, b1 - b0).copy()
            nn[..., :2] *= normal_amt
            nor[b0:b1, a0:a1] = nn / np.linalg.norm(nn, axis=2, keepdims=True)
            return a0, a1, b0, b1

        # end grain: darker, porous (fine noise across)
        a0, a1, b0, b1 = fill("end", (0.085, 0.050, 0.028), 0.5, 0.3)
        pores = rng.normal(0, 1, (b1 - b0, a1 - a0))
        base[b0:b1, a0:a1] *= (1 + 0.18 * pores)[..., None].clip(0.6, 1.4)
        fill("toast", (0.046, 0.022, 0.011), 0.9, 0.6)
        a0, a1, b0, b1 = fill("bung", (0.078, 0.046, 0.030), 0.8, 0.6)
        uu = (np.arange(a0, a1) + 0.5 - (self.patches["bung"][0] + self.patches["bung"][2] / 2)) / SU
        vv = (np.arange(b0, b1) + 0.5 - (self.patches["bung"][1] + self.patches["bung"][3] / 2)) / (SV * 2)
        BX, BY = np.meshgrid(uu, vv)
        br = np.hypot(BX, BY)
        # the bung's crown is handled (lighter, worn), its sides and rim wine-dark
        wet = np.clip((br - 0.016) / 0.006, 0, 1)[..., None]
        base[b0:b1, a0:a1] *= (1 - wet) + wet * np.array([0.38, 0.17, 0.25])

        nor = nor / np.linalg.norm(nor, axis=2, keepdims=True)
        _save(BASE, lin_to_srgb(base))
        _save(NORMAL, nor * 0.5 + 0.5)
        print(f"dining_barrel_tex: generated {BASE} / {NORMAL} ({'scan ' + PH_ID if src else 'no scan, generated'})")


def _wine_stain(c, X, Y, rng):
    """Wine round the bung hole (Y metres up from the bung centre, X across): a dark wet ring
    at the hole, an irregular old halo, splashes, and drips run down the bung stave."""
    ang = np.arctan2(Y, X)
    r = np.hypot(X, Y)
    wob = 0.0
    for f, amp in ((2, 0.006), (3, 0.005), (5, 0.003), (9, 0.0015)):
        wob = wob + amp * rng.uniform(0.5, 1.0) * np.sin(f * ang + rng.uniform(0, 6))
    # soaked wood: strongest at the hole, fading out unevenly, spreading further along the grain
    re_ = np.hypot(X, Y * 0.7)
    halo = np.clip((0.052 + wob - re_) / 0.022, 0, 1) ** 1.3 * 0.72
    ring = np.clip((0.032 - r) / 0.006, 0, 1) * 0.35
    m = halo + ring
    for _ in range(5):                                   # a few small splashes
        a, d = rng.uniform(0, 2 * math.pi), rng.uniform(0.04, 0.07)
        rr = rng.uniform(0.0012, 0.0025)
        m = m + 0.3 * np.exp(-(((X - d * math.cos(a)) ** 2 + (Y - d * math.sin(a)) ** 2) / rr ** 2))
    for _ in range(4):                                   # drips running down from the hole
        x0 = rng.uniform(-0.022, 0.022)
        ln = rng.uniform(0.045, 0.105)
        wd = rng.uniform(0.0018, 0.0038)
        t = np.clip(-Y / ln, 0, 1)
        on = (Y < -0.02) & (Y > -ln)
        xc = x0 + 0.0015 * np.sin(-Y * 70 + rng.uniform(0, 6))
        prof = np.exp(-((X - xc) / (wd * (1 - 0.5 * t))) ** 2) * (1 - t) ** 0.5 * rng.uniform(0.4, 0.75)
        bead = np.exp(-((X - xc) ** 2 + (Y + ln) ** 2) / (1.3 * wd) ** 2) * 0.35    # the drop at the end
        m = m + np.where(on, prof, 0) + bead
    # an old wash below the bung
    m = m + 0.22 * np.exp(-(X / 0.04) ** 2) * np.clip(-Y / 0.02, 0, 1) * np.exp(np.minimum(Y, 0) / 0.12)
    m = np.clip(m, 0, 0.94)[..., None]
    wine = np.array([0.16, 0.05, 0.09])
    return c * (1 - m) + c * wine * m


# hand-chalked vintage on the head (stroke font, unit box 1 x 1.5, y up)
_DIGITS = {
    "2": [[(0.05, 1.12), (0.2, 1.4), (0.5, 1.5), (0.8, 1.4), (0.9, 1.12), (0.72, 0.78), (0.05, 0.02), (0.98, 0.0)]],
    "0": [[(0.5 + 0.44 * math.sin(a), 0.75 + 0.75 * math.cos(a)) for a in np.linspace(0, 2 * math.pi, 15)]],
    "1": [[(0.22, 1.12), (0.58, 1.5), (0.55, 0.0)]],
    "9": [[(0.88, 1.08)] + [(0.5 + 0.38 * math.cos(a), 1.08 + 0.38 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 13)]
          + [(0.86, 0.85), (0.72, 0.35), (0.45, 0.0)]],
}


def _chalk(hb, X, Y, rng, text="2019", at=(-0.17, -0.155), h=0.05, rot=0.1, width=0.0026):
    segs = []
    x = 0.0
    for ch in text:
        for stroke in _DIGITS[ch]:
            pts = [(x + px + rng.normal(0, 0.03), py + rng.normal(0, 0.03)) for px, py in stroke]
            segs += list(zip(pts[:-1], pts[1:]))
        x += 1.2
    s = h / 1.5
    cr, sr = math.cos(rot), math.sin(rot)
    d = np.full(X.shape, 1e9)
    for (x0, y0), (x1, y1) in segs:
        ax, ay = at[0] + s * (x0 * cr - y0 * sr), at[1] + s * (x0 * sr + y0 * cr)
        bx, by = at[0] + s * (x1 * cr - y1 * sr), at[1] + s * (x1 * sr + y1 * cr)
        vx, vy = bx - ax, by - ay
        t = np.clip(((X - ax) * vx + (Y - ay) * vy) / max(vx * vx + vy * vy, 1e-12), 0, 1)
        d = np.minimum(d, np.hypot(X - ax - t * vx, Y - ay - t * vy))
    a = np.clip(1 - d / width, 0, 1) ** 0.6
    a *= np.clip(rng.uniform(0, 1, X.shape) * 1.6 - 0.25, 0, 1) * 0.7     # dry chalk skips on the grain
    chalk = np.array([0.50, 0.49, 0.45])
    return hb * (1 - a[..., None]) + chalk * a[..., None]


def _glass_rings(hb, X, Y, rng):
    for cx, cy, rr, amt, a0, span in ((0.09, -0.05, 0.034, 0.28, 0.3, 4.6), (-0.07, 0.11, 0.036, 0.18, 2.0, 3.6),
                                      (0.12, 0.02, 0.033, 0.12, 4.0, 2.8)):
        dx, dy = X - cx, Y - cy
        r = np.hypot(dx, dy)
        ang = (np.arctan2(dy, dx) - a0) % (2 * math.pi)
        arc = np.clip(1 - np.maximum(ang - span, 0) / 0.6, 0, 1)
        line = np.exp(-((r - rr) / 0.0018) ** 2) * arc * amt
        m = line[..., None]
        hb = hb * (1 - m) + hb * np.array([0.42, 0.20, 0.28]) * m
    return hb


# ----------------------------------------------------------------------------- scan io

def _scan():
    """(diffuse path, normal path) of the oak scan, fetched once into build/polyhaven/."""
    d = os.path.join(SCANS, f"{PH_ID}_diff_2k.jpg")
    n = os.path.join(SCANS, f"{PH_ID}_nor_gl_2k.jpg")
    try:
        if not (os.path.exists(d) and os.path.exists(n)):
            ua = {"User-Agent": "game_testing-texture-fetch/1.0 (Blender; CC0 assets)"}
            get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers=ua), timeout=30).read()
            files = json.loads(get(f"https://api.polyhaven.com/files/{PH_ID}"))
            os.makedirs(SCANS, exist_ok=True)
            for key, path in (("Diffuse", d), ("nor_gl", n)):
                if not os.path.exists(path):
                    data = get(files[key]["2k"]["jpg"]["url"])
                    open(path + ".tmp", "wb").write(data)
                    os.replace(path + ".tmp", path)
        return d, n
    except Exception as e:  # offline
        print(f"dining_barrel_tex: scan {PH_ID} unavailable ({e})")
        return None


def _load(path, w, h):
    img = bpy.data.images.load(path)
    img.colorspace_settings.name = "Non-Color"      # read the stored values as they are
    fl = bpy.data.images.new("_dbt", img.size[0], img.size[1], alpha=False, float_buffer=True)
    fl.colorspace_settings.name = "Non-Color"
    fl.pixels.foreach_set(np.array(img.pixels[:], np.float32))
    bpy.data.images.remove(img)
    fl.scale(w, h)
    px = np.array(fl.pixels[:], np.float32).reshape(h, w, 4)[..., :3]
    bpy.data.images.remove(fl)
    return px                                       # rows bottom-up, v = 0 first


def _prepare(src, w, h):
    col = srgb_to_lin(np.clip(_load(src[0], w, h), 0, 1))
    n = _load(src[1], w, h) * 2 - 1
    n[..., 1] /= STRETCH                            # the stretch flattens slopes along the grain
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return col, n


def _save(name, px):
    """px: rows bottom-up (v = 0 first), stored values 0..1. Written atomically."""
    path = os.path.join(textures.TEX_DIR, name + ".png")
    tmp = os.path.join(textures.TEX_DIR, name + ".tmp.png")
    img = bpy.data.images.new("_dbt_save", N, N, alpha=False)
    img.pixels.foreach_set(np.concatenate([np.clip(px, 0, 1), np.ones((N, N, 1))], axis=2).astype(np.float32).ravel())
    img.filepath_raw = tmp
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    os.replace(tmp, path)
    old = bpy.data.images.get(os.path.basename(path))
    if old is not None:
        old.reload()
