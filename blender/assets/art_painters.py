"""Painting styles for the house's art collection (used by picture_frame.py).

Pure numpy (no bpy), so the paintings can be iterated outside Blender. Each style is a
function `style(w, h, s)` returning an (h, w, 3) sRGB image in 0..1, rows top to bottom;
`s` is the piece's spec dict (always has a `seed`). `paint(style, w, h, spec)` renders
at `ss` x the size and box-filters down, so hard edges and fine lines are antialiased.

Coordinates inside a painter: X runs 0..aspect and Y 0..1 (top to bottom), both in units
of the picture height; composition specs give centres / edges as fractions of the
width and height and radii / widths in picture heights.

Styles: colorfield, hardedge (taped geometric, Albers, Kelly, zips, stained targets,
painterly still life), blocks (stacked painterly bars), mono (textured monochrome),
weave (textile grids), stain (soak-stain pools), rings (wine-glass rings), wash
(watercolour), cyano (cyanotype botanicals), grid (pencil grid), contour (topographic
drawing), ink (gestural brush strokes), gold (gold-leaf panel), photo (photographs as
abstraction: seascape, dune, fog, clouds, salt ponds, moon, shoreline, vineyard).
"""
import numpy as np

# =============================================================================
# toolkit
# =============================================================================


def fnoise(h, w, rng, beta=2.0, ax=1.0, ay=1.0, angle=0.0):
    """Fractal noise with unit standard deviation, isotropic in pixels. ax / ay
    penalise detail along x / y (a large ax gives streaks running along x); `angle`
    (radians) turns those axes."""
    white = rng.standard_normal((h, w))
    ky = np.fft.fftfreq(h)[:, None] * h
    kx = np.fft.fftfreq(w)[None, :] * h
    if angle:
        c, s = np.cos(angle), np.sin(angle)
        kx, ky = kx * c + ky * s, -kx * s + ky * c
    k = np.sqrt((kx * ax) ** 2 + (ky * ay) ** 2)
    k[0, 0] = 1.0
    spec = np.fft.fft2(white) / k ** beta
    spec[0, 0] = 0
    out = np.real(np.fft.ifft2(spec))
    return out / (out.std() + 1e-9)


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def grid(h, w):
    y = (np.arange(h) + 0.5) / h
    x = (np.arange(w) + 0.5) / h
    return np.meshgrid(x, y)


def col(c):
    return np.array(c, dtype=float)


def blur(img, sigma):
    """Gaussian blur, sigma in pixels (2D or HxWxC)."""
    if sigma <= 0:
        return img
    h, w = img.shape[:2]
    ky = np.fft.fftfreq(h)[:, None]
    kx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi * sigma) ** 2 * (kx ** 2 + ky ** 2))
    if img.ndim == 3:
        g = g[..., None]
        return np.real(np.fft.ifft2(np.fft.fft2(img, axes=(0, 1)) * g, axes=(0, 1)))
    return np.real(np.fft.ifft2(np.fft.fft2(img) * g))


def down(img, s):
    if s == 1:
        return img
    h, w = img.shape[0] // s, img.shape[1] // s
    return img[:h * s, :w * s].reshape(h, s, w, s, -1).mean(axis=(1, 3))


def over(img, c, a):
    a = np.clip(a, 0, 1)[..., None]
    return img * (1 - a) + np.asarray(c, dtype=float) * a


def multiply(img, c, a):
    """Transparent pigment (watercolour, stain): darkens towards colour c."""
    a = np.clip(a, 0, 1)[..., None]
    return img * (1 - a * (1 - np.asarray(c, dtype=float)))


def edge_dist(X, Y):
    asp = X.max() + X.min()
    return np.minimum.reduce([X, asp - X, Y, 1 - Y])


def lerp(stops, t):
    """Piecewise-linear palette: stops = [(t, colour), ...]."""
    t = np.clip(t, stops[0][0], stops[-1][0])
    out = np.zeros(t.shape + (3,))
    for (t0, c0), (t1, c1) in zip(stops[:-1], stops[1:]):
        m = (t >= t0) & (t <= t1)
        f = ((t - t0) / max(t1 - t0, 1e-9))[..., None]
        out = np.where(m[..., None], col(c0) * (1 - f) + col(c1) * f, out)
    return out


def weave(h, w, rng, ppm, amp=0.012, pitch_m=0.0011):
    """Canvas weave as a multiplicative pattern; skipped when the threads would be
    under 2 px (low-resolution textures) and replaced by faint tooth."""
    pitch = pitch_m * ppm
    if pitch < 2.0:
        return 1.0 + amp * 0.5 * fnoise(h, w, rng, 0.3)
    yy, xx = np.mgrid[0:h, 0:w]
    jx = 0.35 * fnoise(h, w, rng, 1.0)
    jy = 0.35 * fnoise(h, w, rng, 1.0)
    a = np.sin(2 * np.pi * xx / pitch + jx)
    b = np.sin(2 * np.pi * yy / pitch + jy)
    return 1.0 + amp * (0.55 * a * b + 0.15 * (a + b) + 0.2 * fnoise(h, w, rng, 0.5))


def emboss(n, k):
    """Relief shading from a height field (light from the upper left)."""
    return 1 + k * (n - np.roll(np.roll(n, 1, 0), 1, 1))


def paper(h, w, rng, c, drift=0.018, fibre=0.012):
    X, Y = grid(h, w)
    img = col(c) * (1 + drift * fnoise(h, w, rng, 2.6) + fibre * fnoise(h, w, rng, 0.6)
                    + 0.006 * fnoise(h, w, rng, 0.2))[..., None]
    return img


def raw_canvas(h, w, rng, ppm, c=(0.80, 0.74, 0.62)):
    img = col(c) * (1 + 0.03 * fnoise(h, w, rng, 2.2) + 0.012 * fnoise(h, w, rng, 0.8))[..., None]
    return img * weave(h, w, rng, ppm, amp=0.03)[..., None]


def vignette(img, X, Y, k):
    asp = X.max() + X.min()
    r = ((X / asp - 0.5) ** 2 + (Y - 0.5) ** 2) * 2
    return img * (1 - k * r)[..., None]


def sdf_box(X, Y, cx, cy, hx, hy):
    qx = np.abs(X - cx) - hx
    qy = np.abs(Y - cy) - hy
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0)


def shape_sdf(sh, X, Y, asp):
    t = sh["t"]
    if t in ("rect", "rrect"):
        x0, y0, x1, y1 = sh["r"]
        rad = sh.get("rad", 0.0)
        return sdf_box(X, Y, (x0 + x1) / 2 * asp, (y0 + y1) / 2, (x1 - x0) / 2 * asp - rad,
                       (y1 - y0) / 2 - rad) - rad
    if t == "circle":
        cx, cy, r = sh["p"]
        return np.hypot(X - cx * asp, Y - cy) - r
    if t == "ring":
        cx, cy, r0, r1 = sh["p"]
        return np.abs(np.hypot(X - cx * asp, Y - cy) - (r0 + r1) / 2) - (r1 - r0) / 2
    if t == "ellipse":
        cx, cy, rx, ry = sh["p"]
        return (np.hypot((X - cx * asp) / rx, (Y - cy) / ry) - 1) * min(rx, ry)
    raise ValueError(t)


def rng_of(s):
    return np.random.default_rng(s["seed"])


# =============================================================================
# colour fields (soft stacked blocks)
# =============================================================================

def colorfield(w, h, s):
    rng = rng_of(s)
    X, Y = grid(h, w)
    asp = w / h
    img = col(s["ground"]) * (1 + 0.035 * fnoise(h, w, rng, 2.2, ax=2) + 0.018 * fnoise(h, w, rng, 1.6, ax=5)
                              + 0.006 * fnoise(h, w, rng, 0.45))[..., None]
    img *= (1 - 0.10 * (1 - smooth(0.0, 0.05, edge_dist(X, Y))))[..., None]
    for b in s["blocks"]:
        fx0, fy0, fx1, fy1 = b["box"]
        x0, x1, y0, y1 = fx0 * asp, fx1 * asp, fy0, fy1
        wob = 0.0034 * fnoise(h, w, rng, 2.4, ax=2) + 0.0012 * fnoise(h, w, rng, 1.0, ax=10)
        rad = 0.03
        base_d = rad - sdf_box(X, Y, (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 - rad, (y1 - y0) / 2 - rad) + wob
        low = fnoise(h, w, rng, 2.7, ax=1.3)
        mid = fnoise(h, w, rng, 1.7, ax=6)
        brush = fnoise(h, w, rng, 1.0, ax=18)
        for c, inset, bl, alpha in b["glazes"]:
            m = smooth(-bl, bl, base_d - inset) * alpha
            m = m * np.clip(1 + 0.14 * fnoise(h, w, rng, 2.4, ax=1.5), 0.5, 1.4)
            tone = 1 + 0.075 * low + 0.035 * mid + 0.007 * brush
            img = over(img, col(c) * tone[..., None], m)
    img *= weave(h, w, rng, s["_ppm"], amp=0.010)[..., None]
    return np.clip(img, 0, 1)


# =============================================================================
# hard edge: taped geometric, Albers squares, Kelly curve, zips, stained rings,
# painterly still life
# =============================================================================

def hardedge(w, h, s):
    """Flat paint shapes over a ground. Per piece: `soft` edge (px at render size),
    `wobble` (hand / tape wobble, picture heights), `raw` (unprimed canvas ground:
    shapes soak in as transparent stains), `painterly` (brushwork inside shapes)."""
    rng = rng_of(s)
    X, Y = grid(h, w)
    asp = w / h
    soft = s.get("soft", 0.7) * s["_ss"]
    drift = fnoise(h, w, rng, 2.4)
    stipple = fnoise(h, w, rng, 0.25)
    roller = fnoise(h, w, rng, 1.3, ax=6)
    grain = s.get("grain", 0.012)
    if s.get("raw"):
        img = raw_canvas(h, w, rng, s["_ppm"], s["ground"])
    else:
        img = col(s["ground"]) * (1 + 0.012 * drift + 0.5 * grain * stipple)[..., None]
        if s.get("ground2"):            # e.g. a still life's table top below a line
            y0 = s["ground2"][0]
            img = over(img, col(s["ground2"][1]) * (1 + 0.012 * drift)[..., None],
                       smooth(-0.003, 0.003, Y - y0 - 0.004 * fnoise(h, w, rng, 2.0, ax=4)))
    wob_amp = s.get("wobble", 0.00045)
    wob = wob_amp * fnoise(h, w, rng, 1.6)
    for sh in s["shapes"]:
        d = shape_sdf(sh, X, Y, asp) + wob * sh.get("wob", 1.0)
        cov = smooth(soft, -soft, d * h) * sh.get("a", 1.0)
        c = col(sh["c"])
        if s.get("painterly"):
            ang = np.radians(sh.get("dir", 90))
            br = fnoise(h, w, rng, 1.2, ax=8, ay=1, angle=ang)
            br2 = fnoise(h, w, rng, 2.2)
            paint = c * (1 + 0.045 * br + 0.03 * br2)[..., None]
            # the brush drags the edge: slightly broken coverage near the boundary
            cov = cov * np.clip(1 + 0.25 * fnoise(h, w, rng, 1.0, ax=6, angle=ang) * smooth(-6 * soft, 0, d * h), 0, 1)
        else:
            paint = c * (1 + 0.022 * drift + 0.014 * roller + grain * stipple)[..., None]
            ridge = np.exp(-((d * h / s["_ss"] + 1.2) / 1.6) ** 2) * 0.05
            paint = paint * (1 - ridge[..., None])
        if s.get("raw"):
            # stain: transparent, slightly darker at the soaked edge
            halo = np.exp(-((d * h + soft) / (2.5 * soft)) ** 2) * 0.15
            img = multiply(img, np.clip(c * (1 + 0.03 * drift)[..., None], 0, 1), cov * (0.92 + 0.08 * stipple))
            img *= (1 - halo * cov)[..., None]
        else:
            img = over(img, paint, cov)
    if s.get("shadows"):                # soft cast shadows (still life)
        for sh in s["shadows"]:
            d = shape_sdf(sh, X, Y, asp)
            img *= (1 - sh.get("a", 0.25) * smooth(0.02, -0.02, d))[..., None]
    if not s.get("raw"):
        img *= weave(h, w, rng, s["_ppm"], amp=0.010)[..., None]
    img *= (1 - 0.05 * (1 - smooth(0.0, 0.03, edge_dist(X, Y))))[..., None]
    return np.clip(img, 0, 1)


# =============================================================================
# blocks: stacked painterly bars (horizontal rows of blocks, breathing edges)
# =============================================================================

def blocks(w, h, s):
    rng = rng_of(s)
    X, Y = grid(h, w)
    asp = w / h
    under = col(s["under"])
    img = under * (1 + 0.05 * fnoise(h, w, rng, 2.0) + 0.03 * fnoise(h, w, rng, 1.0, ax=5))[..., None]
    ys = np.concatenate([[0], np.cumsum(s["rows"])])
    ys = ys / ys[-1]
    pal = s["palette"]
    k = 0
    for ri in range(len(s["rows"])):
        y0, y1 = ys[ri], ys[ri + 1]
        cuts = s["cols"][ri]
        xs = np.concatenate([[0], np.cumsum(cuts)])
        xs = xs / xs[-1]
        for ci in range(len(cuts)):
            x0, x1 = xs[ci], xs[ci + 1]
            c = col(pal[s["order"][k % len(s["order"])]])
            k += 1
            horiz = (ri + ci) % 2 == 0
            ang = 0.0 if horiz else np.pi / 2
            g = s.get("gap", 0.008)
            wob = 0.006 * fnoise(h, w, rng, 2.2) + 0.002 * fnoise(h, w, rng, 1.2, ax=4, angle=ang)
            d = sdf_box(X, Y, (x0 + x1) / 2 * asp, (y0 + y1) / 2, (x1 - x0) / 2 * asp - g, (y1 - y0) / 2 - g) + wob
            m = smooth(0.004, -0.006, d)
            br = fnoise(h, w, rng, 1.1, ax=10, angle=ang)
            br2 = fnoise(h, w, rng, 2.4)
            paint = c * (1 + 0.06 * br + 0.05 * br2)[..., None]
            # top layer thins out towards the edges so the underpaint breathes through
            thin = np.clip(0.82 + 0.25 * fnoise(h, w, rng, 1.4, ax=6, angle=ang) + 0.6 * smooth(0, -0.05, d), 0, 1)
            img = over(img, paint, m * thin)
            # a second, lighter scumble over part of the block
            sc = smooth(0.35, 0.9, fnoise(h, w, rng, 2.0, ax=3, angle=ang)) * m * 0.35
            img = over(img, np.clip(c * 1.18 + 0.03, 0, 1), sc)
    img *= weave(h, w, rng, s["_ppm"], amp=0.012)[..., None]
    img *= (1 - 0.06 * (1 - smooth(0.0, 0.03, edge_dist(X, Y))))[..., None]
    return np.clip(img, 0, 1)


# =============================================================================
# mono: a single colour, all in the brushwork
# =============================================================================

def mono(w, h, s):
    rng = rng_of(s)
    X, Y = grid(h, w)
    asp = w / h
    # brush height field: patches of strokes in a few directions
    hgt = np.zeros((h, w))
    for ang in s.get("angles", (0, 90)):
        a = np.radians(ang)
        strokes = fnoise(h, w, rng, 1.25, ax=s.get("stretch", 9), angle=a)
        patch = smooth(-0.4, 0.4, fnoise(h, w, rng, 2.3))
        hgt += strokes * patch
        rng.standard_normal(1)
    hgt /= hgt.std() + 1e-9
    if s.get("dabs"):
        # thick, overlapping short strokes laid edge to edge (Ryman): each dab a ridged slab
        hgt = 0.15 * hgt
        yy, xx = np.mgrid[0:h, 0:w] + 0.5
        for _ in range(s["dabs"]):
            cx, cy = rng.uniform(-0.05, asp + 0.05) * h, rng.uniform(-0.05, 1.05) * h
            L = rng.uniform(0.07, 0.15) * h
            Wd = rng.uniform(0.035, 0.065) * h
            a = rng.normal(0, 0.08)
            r = int(L + Wd) + 2
            i0, i1, j0, j1 = max(0, int(cy) - r), min(h, int(cy) + r), max(0, int(cx) - r), min(w, int(cx) + r)
            if i0 >= i1 or j0 >= j1:
                continue
            dx, dy = xx[i0:i1, j0:j1] - cx, yy[i0:i1, j0:j1] - cy
            u = dx * np.cos(a) + dy * np.sin(a)
            v = -dx * np.sin(a) + dy * np.cos(a)
            m = smooth(1.0, 0.75, np.abs(u) / L + 0.15 * rng.uniform()) * smooth(1.0, 0.8, np.abs(v) / Wd)
            ridge = 0.8 + 0.2 * np.sin(v / Wd * rng.uniform(5, 9) + rng.uniform(0, 6)) * smooth(1, 0.3, np.abs(u) / L)
            hgt[i0:i1, j0:j1] = hgt[i0:i1, j0:j1] * (1 - m) + (ridge + rng.normal(0, 0.15)) * m
        hgt = (hgt - hgt.mean()) / (hgt.std() + 1e-9)
    tone = 1 + s.get("tone", 0.04) * fnoise(h, w, rng, 2.4) + s.get("amp", 0.03) * hgt
    img = col(s["c"]) * tone[..., None]
    img *= emboss(blur(hgt, 0.8 * s["_ss"]), s.get("relief", 0.05))[..., None]
    for z in s.get("zips", []):
        x0, x1 = z["x"]
        rag = z.get("rag", 0.0015) * fnoise(h, w, rng, 1.3, ay=6)
        d = np.maximum(x0 * asp - X, X - x1 * asp) + rag
        m = smooth(0.0012, -0.0012, d)
        zc = col(z["c"]) * (1 + 0.04 * fnoise(h, w, rng, 1.0, ay=8))[..., None]
        img = over(img, zc, m * z.get("a", 1.0))
    if s.get("band"):                   # a barely-there division (Reinhardt-like)
        y0, y1, f = s["band"]
        img *= (1 + f * smooth(-0.004, 0.004, np.minimum(Y - y0, y1 - Y)))[..., None]
    img *= weave(h, w, rng, s["_ppm"], amp=0.012)[..., None]
    img *= (1 - s.get("edge", 0.05) * (1 - smooth(0.0, 0.04, edge_dist(X, Y))))[..., None]
    return np.clip(img, 0, 1)


# =============================================================================
# weave: textiles (tartan / check, or a grid of woven blocks)
# =============================================================================

def _threads(h, w, pitch, rng):
    """Over-under texture for a 2/2 twill: returns (warp_on_top mask, shading)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    jx = 0.25 * pitch * fnoise(h, w, rng, 2.0)
    ix = np.floor((xx + jx) / pitch)
    iy = np.floor((yy + 0.25 * pitch * fnoise(h, w, rng, 2.0)) / pitch)
    top = ((ix + iy) // 2) % 2 == 0
    fx = ((xx + jx) / pitch) % 1.0
    fy = (yy / pitch) % 1.0
    shade = np.where(top, 0.80 + 0.20 * np.sin(np.pi * fx), 0.80 + 0.20 * np.sin(np.pi * fy))
    return top, shade


def weave_art(w, h, s):
    rng = rng_of(s)
    X, Y = grid(h, w)
    asp = w / h
    pitch = max(2.4, s.get("pitch_m", 0.004) * s["_ppm"])
    top, shade = _threads(h, w, pitch, rng)
    slub = 1 + 0.06 * fnoise(h, w, rng, 1.0, ax=12) + 0.05 * fnoise(h, w, rng, 1.0, ay=12)
    if s["mode"] == "check":
        def seq(stripes, coord):
            # stripes: list of (width, colour) repeating along coord (picture heights)
            widths = np.array([st[0] for st in stripes])
            cols = np.array([st[1] for st in stripes], dtype=float)
            period = widths.sum()
            edges = np.cumsum(widths)
            idx = np.searchsorted(edges, coord % period, side="right")
            return cols[np.clip(idx, 0, len(cols) - 1)]
        warp = seq(s["warp"], X + s.get("warp_off", 0.0))
        weft = seq(s["weft"], Y + s.get("weft_off", 0.0))
        img = np.where(top[..., None], warp, weft)
    else:   # grid of woven blocks
        img = np.zeros((h, w, 3))
        rows = np.concatenate([[0], np.cumsum(s["rows"])]) / sum(s["rows"])
        for ri in range(len(s["rows"])):
            cuts = s["cols"][ri]
            xs = np.concatenate([[0], np.cumsum(cuts)]) / sum(cuts)
            for ci in range(len(cuts)):
                c = col(s["palette"][s["order"][ri][ci]])
                m = (Y >= rows[ri]) & (Y < rows[ri + 1]) & (X >= xs[ci] * asp) & (X < xs[ci + 1] * asp)
                # warp and weft of slightly different tone, like two yarns
                cc = np.where(top[..., None], c * 1.04, c * 0.93)
                img = np.where(m[..., None], cc, img)
        for x0, y0, x1, y1, ci in s.get("insets", []):
            c = col(s["palette"][ci])
            m = (X >= x0 * asp) & (X < x1 * asp) & (Y >= y0) & (Y < y1)
            img = np.where(m[..., None], np.where(top[..., None], c * 1.04, c * 0.93), img)
    img = img * (shade * slub)[..., None]
    img *= (1 - 0.05 * (1 - smooth(0.0, 0.02, edge_dist(X, Y))))[..., None]
    return np.clip(img, 0, 1)


# =============================================================================
# stain: soak-stained pools on raw canvas
# =============================================================================

def stain(w, h, s):
    rng = rng_of(s)
    X, Y = grid(h, w)
    asp = w / h
    img = raw_canvas(h, w, rng, s["_ppm"], s.get("ground", (0.80, 0.74, 0.62)))
    for p in s["pools"]:
        cx, cy, rx, ry = p["e"]
        warp = p.get("rough", 0.18) * fnoise(h, w, rng, 2.1) + 0.05 * fnoise(h, w, rng, 1.3)
        d = np.hypot((X - cx * asp) / rx, (Y - cy) / ry) - 1 + warp
        m = smooth(0.06, -0.06, d)
        # the pigment collects at the drying edge: a tide line
        rim = np.clip(m - blur(m, 4.0 * s["_ss"]), 0, 1) * p.get("rim", 0.5)
        dens = np.clip(p.get("a", 0.7) * (0.85 + 0.15 * fnoise(h, w, rng, 1.8)) + rim, 0, 1)
        img = multiply(img, p["c"], m * dens)
    img *= (1 - 0.04 * (1 - smooth(0.0, 0.03, edge_dist(X, Y))))[..., None]
    return np.clip(img, 0, 1)


# =============================================================================
# rings: wine-glass rings and spills on paper
# =============================================================================

def rings(w, h, s):
    rng = rng_of(s)
    X, Y = grid(h, w)
    asp = w / h
    img = paper(h, w, rng, s.get("paper", (0.93, 0.91, 0.86)))
    tex = fnoise(h, w, rng, 1.2)
    for cx, cy, r, a, c in s["rings"]:
        dx, dy = X - cx * asp, Y - cy
        d = np.hypot(dx, dy)
        th = np.arctan2(dy, dx)
        wob = 0.012 * r * np.sin(2 * th + rng.uniform(0, 6)) + 0.006 * r * np.sin(5 * th + rng.uniform(0, 6))
        e = d - r - wob
        # coffee-ring: a sharp outer edge, fading inward
        ring = np.where(e < 0, np.exp(e / (0.10 * r)), np.exp(-(e / (0.012 * r)) ** 2))
        # the ring is broken where the glass lifted
        ph = rng.uniform(0, 2 * np.pi)
        brk = smooth(-0.6, 0.4, np.sin(th + ph) * rng.uniform(0.5, 1.5) + rng.uniform(-0.2, 1.0))
        inner = smooth(0.002, -0.002, e) * 0.10
        dens = np.clip(ring * brk * a + inner * a, 0, 1) * (0.85 + 0.15 * tex)
        img = multiply(img, c, dens)
    for cx, cy, r, c in s.get("drops", []):
        d = np.hypot(X - cx * asp, Y - cy) - r * (1 + 0.15 * fnoise(h, w, rng, 2.0))
        img = multiply(img, c, smooth(0.002, -0.002, d) * 0.75)
    img *= (1 - 0.04 * (1 - smooth(0.0, 0.03, edge_dist(X, Y))))[..., None]
    return np.clip(img, 0, 1)


# =============================================================================
# wash: watercolour (swatch chart, translucent circles, landscape bands)
# =============================================================================

def _wash(img, m, c, a, rng, h, w, ss, gran=0.12):
    """Watercolour layer: transparent, pigment pooled at the wet edge, granulating."""
    rim = np.clip(m - blur(m, 3.0 * ss), 0, 1)
    dens = a * m * (0.80 + 0.12 * fnoise(h, w, rng, 2.2)) + 0.9 * a * rim
    dens *= 1 + gran * fnoise(h, w, rng, 0.4)
    return multiply(img, c, dens)


def wash(w, h, s):
    rng = rng_of(s)
    X, Y = grid(h, w)
    asp = w / h
    ss = s["_ss"]
    img = paper(h, w, rng, s.get("paper", (0.94, 0.92, 0.87)), drift=0.02, fibre=0.02)
    if s["mode"] == "chart":
        rows, cols_ = s["grid"]
        mx, my0, my1 = s.get("margin", (0.12, 0.1, 0.14))
        gx, gy = s.get("gap", (0.022, 0.022))
        cw = (1 - 2 * mx - (cols_ - 1) * gx) / cols_
        chh = (1 - my0 - my1 - (rows - 1) * gy) / rows
        for r in range(rows):
            for c in range(cols_):
                x0 = mx + c * (cw + gx)
                y0 = my0 + r * (chh + gy)
                warp = 0.0025 * fnoise(h, w, rng, 2.0)
                d = sdf_box(X, Y, (x0 + cw / 2) * asp, y0 + chh / 2, cw / 2 * asp, chh / 2) + warp
                m = smooth(0.0015, -0.0015, d)
                colr = s["colours"][(r * cols_ + c) % len(s["colours"])]
                img = _wash(img, m, colr, s.get("a", 0.85) * rng.uniform(0.85, 1.05), rng, h, w, ss)
    elif s["mode"] == "circles":
        for cx, cy, r, c, a in s["circles"]:
            warp = 0.006 * fnoise(h, w, rng, 2.2)
            d = np.hypot(X - cx * asp, Y - cy) - r + warp
            img = _wash(img, smooth(0.002, -0.002, d), c, a, rng, h, w, ss)
    else:   # bands: wet-in-wet horizontal washes, top edges bleeding
        for y0, y1, c, a in s["bands"]:
            top = y0 + 0.012 * fnoise(h, w, rng, 2.4, ax=3) + 0.004 * fnoise(h, w, rng, 1.2, ax=6)
            bot = y1 + 0.010 * fnoise(h, w, rng, 2.4, ax=3)
            xm = s.get("xmargin", 0.08)
            side = np.minimum(X - xm * asp, (1 - xm) * asp - X) + 0.006 * fnoise(h, w, rng, 2.0, ay=3)
            m = smooth(-0.004, 0.006, Y - top) * smooth(0.004, -0.004, Y - bot) * smooth(-0.002, 0.002, side)
            img = _wash(img, m, c, a, rng, h, w, ss)
    img *= (1 - 0.03 * (1 - smooth(0.0, 0.03, edge_dist(X, Y))))[..., None]
    return np.clip(img, 0, 1)


# =============================================================================
# stamping helpers for drawn marks (pixel coordinates)
# =============================================================================

class Stamp:
    """Accumulates coverage of capsules / ellipses into an array (max blend)."""

    def __init__(self, h, w):
        self.a = np.zeros((h, w))
        self.h, self.w = h, w

    def _win(self, x0, y0, x1, y1):
        i0, i1 = max(0, int(np.floor(y0))), min(self.h, int(np.ceil(y1)) + 1)
        j0, j1 = max(0, int(np.floor(x0))), min(self.w, int(np.ceil(x1)) + 1)
        if i0 >= i1 or j0 >= j1:
            return None
        yy, xx = np.mgrid[i0:i1, j0:j1] + 0.5
        return (i0, i1, j0, j1), xx, yy

    def capsule(self, p0, p1, r, v=1.0):
        (ax, ay), (bx, by) = p0, p1
        win = self._win(min(ax, bx) - r - 2, min(ay, by) - r - 2, max(ax, bx) + r + 2, max(ay, by) + r + 2)
        if win is None:
            return
        (i0, i1, j0, j1), xx, yy = win
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy + 1e-9
        t = np.clip(((xx - ax) * dx + (yy - ay) * dy) / L2, 0, 1)
        d = np.hypot(xx - ax - t * dx, yy - ay - t * dy)
        c = np.clip(r - d + 0.5, 0, 1) * v
        np.maximum(self.a[i0:i1, j0:j1], c, out=self.a[i0:i1, j0:j1])

    def ellipse(self, cx, cy, rx, ry, ang, v=1.0):
        R = max(rx, ry) + 2
        win = self._win(cx - R, cy - R, cx + R, cy + R)
        if win is None:
            return
        (i0, i1, j0, j1), xx, yy = win
        c_, s_ = np.cos(ang), np.sin(ang)
        u = (xx - cx) * c_ + (yy - cy) * s_
        v_ = -(xx - cx) * s_ + (yy - cy) * c_
        d = (np.hypot(u / rx, v_ / ry) - 1) * min(rx, ry)
        c = np.clip(0.5 - d, 0, 1) * v
        np.maximum(self.a[i0:i1, j0:j1], c, out=self.a[i0:i1, j0:j1])

    def polyline(self, pts, radii, v=1.0):
        for i in range(len(pts) - 1):
            self.capsule(pts[i], pts[i + 1], radii[i], v)


def catmull(points, per_seg=24):
    """Centripetal Catmull-Rom spline through points (Nx2)."""
    p = np.asarray(points, dtype=float)
    p = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-6) ** 0.5
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-6) ** 0.5
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-6) ** 0.5
        t = np.linspace(t1, t2, per_seg, endpoint=False)[:, None]
        a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
        a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
        b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
        out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    out.append(p[-2][None, :])
    return np.vstack(out)


def resample(pts, step):
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    arc = np.concatenate([[0], np.cumsum(seg)])
    n = max(2, int(arc[-1] / step) + 1)
    a = np.linspace(0, arc[-1], n)
    return np.stack([np.interp(a, arc, pts[:, 0]), np.interp(a, arc, pts[:, 1])], 1)


# =============================================================================
# ink: gestural brush strokes (dry-brush bristle marks along splines)
# =============================================================================

def _brush_stroke(img, X, Y, h, w, rng, st, ss):
    """One stroke: st = dict(pts=[(xf, yf), ...] fractions of width/height, w=half width
    (picture heights) or a list of half widths along the stroke, c=colour, a=opacity,
    dry=how much the brush runs out towards the end, bristle=streak strength)."""
    asp = w / h
    pts = np.array([(x * asp * h, y * h) for x, y in st["pts"]])
    path = resample(catmull(pts, 30), 0.7)
    n = len(path)
    t = np.linspace(0, 1, n)
    ww = st["w"]
    if np.ndim(ww) == 0:
        hw = np.full(n, ww * h)
    else:
        hw = np.interp(t, np.linspace(0, 1, len(ww)), np.array(ww) * h)
    tang = np.gradient(path, axis=0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True) + 1e-9
    D = np.full((h, w), np.inf)
    T = np.zeros((h, w))
    S = np.zeros((h, w))
    for i in range(0, n):
        x, y = path[i]
        r = hw[i] * 1.25 + 2
        i0, i1 = max(0, int(y - r)), min(h, int(y + r) + 1)
        j0, j1 = max(0, int(x - r)), min(w, int(x + r) + 1)
        if i0 >= i1 or j0 >= j1:
            continue
        yy, xx = np.mgrid[i0:i1, j0:j1] + 0.5
        dx, dy = xx - x, yy - y
        d = np.hypot(dx, dy) / hw[i]
        win = D[i0:i1, j0:j1]
        m = d < win
        win[m] = d[m]
        T[i0:i1, j0:j1][m] = t[i]
        S[i0:i1, j0:j1][m] = (tang[i, 0] * dy - tang[i, 1] * dx)[m] / hw[i]
    u = np.clip(S, -1.5, 1.5)
    # bristle streaks: noise across the brush (u), stretched along it (t)
    nb = 512
    b1 = rng.standard_normal(nb)
    b1 = np.convolve(b1, np.ones(3) / 3, "same")
    b1 = (b1 - b1.mean()) / (b1.std() + 1e-9)
    bristle = np.interp(u, np.linspace(-1.5, 1.5, nb), b1)
    along = np.interp(T, np.linspace(0, 1, 64), rng.standard_normal(64))
    long_n = fnoise(h, w, rng, 1.6)
    load = 1 - st.get("dry", 0.5) * smooth(0.35, 1.0, T) ** 1.4
    load = load - 0.25 * st.get("dry", 0.5) * smooth(0.12, 0.0, T)       # dabbed start
    val = load + st.get("bristle", 0.35) * bristle * (0.6 + 0.4 * smooth(0.2, 1.0, T)) \
        + 0.08 * along + 0.10 * long_n
    edge = 1 + 0.10 * fnoise(h, w, rng, 1.4) + 0.05 * bristle
    inside = smooth(edge, edge - 0.08, D)
    cov = inside * smooth(0.25, 0.55, val) * st.get("a", 1.0)
    c = col(st["c"]) * (1 + 0.05 * long_n)[..., None]
    return over(img, np.clip(c, 0, 1), cov)


def ink(w, h, s):
    rng = rng_of(s)
    X, Y = grid(h, w)
    ss = s["_ss"]
    if s.get("ground_kind") == "linen":
        img = raw_canvas(h, w, rng, s["_ppm"], s["ground"])
    elif s.get("ground_kind") == "paper":
        img = paper(h, w, rng, s["ground"])
    else:   # primed canvas, with scumbled passages of a second white
        img = col(s["ground"]) * (1 + 0.025 * fnoise(h, w, rng, 2.2) + 0.02 * fnoise(h, w, rng, 1.2, ax=6))[..., None]
        if s.get("ground2"):
            m = smooth(0.2, 0.9, fnoise(h, w, rng, 2.4, ax=1.5))
            img = over(img, col(s["ground2"]) * (1 + 0.03 * fnoise(h, w, rng, 1.1, ax=8))[..., None], m * 0.7)
        img *= weave(h, w, rng, s["_ppm"], amp=0.012)[..., None]
    for st in s["strokes"]:
        img = _brush_stroke(img, X, Y, h, w, rng, st, ss)
    for cx, cy, n_, spread, r0, c in s.get("splatter", []):
        st = Stamp(h, w)
        asp = w / h
        for _ in range(n_):
            ang = rng.uniform(0, 2 * np.pi)
            rr = abs(rng.normal(0, spread))
            x = (cx * asp + rr * np.cos(ang)) * h
            y = (cy + rr * np.sin(ang)) * h
            st.ellipse(x, y, r0 * h * rng.uniform(0.3, 1.2), r0 * h * rng.uniform(0.3, 1.0), ang)
        img = over(img, col(c), st.a)
    img *= (1 - 0.05 * (1 - smooth(0.0, 0.03, edge_dist(X, Y))))[..., None]
    return np.clip(img, 0, 1)


# =============================================================================
# grid: hand-ruled pencil lines over pale washed bands
# =============================================================================

def grid_art(w, h, s):
    rng = rng_of(s)
    X, Y = grid(h, w)
    asp = w / h
    img = col(s["ground"]) * (1 + 0.012 * fnoise(h, w, rng, 2.4) + 0.006 * fnoise(h, w, rng, 0.6))[..., None]
    img *= weave(h, w, rng, s["_ppm"], amp=0.008)[..., None]
    m0 = s.get("margin", 0.0)
    # pale bands
    nb = len(s["bands"])
    band = np.clip(((Y - m0) / (1 - 2 * m0) * nb).astype(int), 0, nb - 1)
    for i, (c, a) in enumerate(s["bands"]):
        wob = 0.002 * fnoise(h, w, rng, 2.0, ax=4)
        y0 = m0 + (1 - 2 * m0) * i / nb
        y1 = m0 + (1 - 2 * m0) * (i + 1) / nb
        m = smooth(-0.002, 0.002, Y - y0 + wob) * smooth(0.002, -0.002, Y - y1 + wob) * a
        m *= 0.85 + 0.15 * fnoise(h, w, rng, 1.5, ax=8)
        img = over(img, col(c), np.clip(m, 0, 1))
    # pencil lines: horizontal at `rows`, vertical at `cols`, inside the margin
    lw = s.get("line_w", 0.0012) * h
    gr = col(s.get("pencil", (0.42, 0.42, 0.44)))
    tooth = np.clip(0.55 + 0.45 * fnoise(h, w, rng, 0.3), 0, 1)
    st = Stamp(h, w)
    x0, x1 = m0 * asp * h + 2, (1 - m0) * asp * h - 2
    for i in range(s["rows"] + 1):
        y = (m0 + (1 - 2 * m0) * i / s["rows"]) * h
        xs = np.linspace(x0, x1, 40)
        ys = y + np.cumsum(rng.normal(0, 0.12, 40)) + rng.normal(0, 0.3)
        st.polyline(list(zip(xs, ys)), [lw * rng.uniform(0.8, 1.2)] * 40, rng.uniform(0.6, 1.0))
    if s.get("cols"):
        y0, y1 = m0 * h + 2, (1 - m0) * h - 2
        for i in range(s["cols"] + 1):
            x = (m0 * asp + (1 - 2 * m0) * asp * i / s["cols"]) * h
            ys = np.linspace(y0, y1, 40)
            xs = x + np.cumsum(rng.normal(0, 0.12, 40))
            st.polyline(list(zip(xs, ys)), [lw * 0.9] * 40, rng.uniform(0.5, 0.9))
    img = over(img, gr, st.a * tooth * s.get("pencil_a", 0.55))
    img *= (1 - 0.04 * (1 - smooth(0.0, 0.03, edge_dist(X, Y))))[..., None]
    return np.clip(img, 0, 1)


# =============================================================================
# contour: a topographic drawing (iso-lines of a terrain), with a lake
# =============================================================================

def contour(w, h, s):
    rng = rng_of(s)
    X, Y = grid(h, w)
    asp = w / h
    img = paper(h, w, rng, s.get("paper", (0.93, 0.90, 0.83)))
    terr = fnoise(h, w, rng, s.get("beta", 3.0)) + 0.35 * fnoise(h, w, rng, 2.2)
    for cx, cy, r, a in s.get("hills", []):
        terr += a * np.exp(-((X - cx * asp) ** 2 + (Y - cy) ** 2) / (r * r))
    m0 = s.get("margin", 0.08)
    inside = smooth(0, 0.004, edge_dist(X, Y) - m0)
    lake = smooth(s.get("lake", -1.4) + 0.02, s.get("lake", -1.4) - 0.02, terr)
    img = multiply(img, col(s.get("water", (0.55, 0.68, 0.78))), lake * inside * 0.55)
    f = terr / s.get("step", 0.16)
    gy, gx = np.gradient(f)
    g = np.hypot(gx, gy) + 1e-6
    dist = np.abs(f - np.round(f)) / g           # px to the nearest contour line
    idx = np.round(f).astype(int)
    major = (idx % 5) == 0
    lw = np.where(major, 1.25, 0.55) * s["_ss"]
    line = np.clip(lw - dist + 0.5, 0, 1) * np.where(major, 1.0, 0.8)
    line *= 1 - lake * 0.6
    img = over(img, col(s.get("ink", (0.30, 0.20, 0.12))), line * inside)
    # a neat ruled border
    e = edge_dist(X, Y)
    b = np.clip(0.7 * s["_ss"] - np.abs(e - m0 + 0.006) * h + 0.5, 0, 1)
    img = over(img, col(s.get("ink", (0.30, 0.20, 0.12))), b)
    return np.clip(img, 0, 1)


# =============================================================================
# cyano: cyanotype botanicals (white silhouettes on Prussian blue)
# =============================================================================

def _fern(st, rng, base, tip, length_px, lean, pinnae=22):
    """A fern frond: curved rachis, alternating pinnae of pinnules."""
    bx, by = base
    tx, ty = tip
    n = 80
    t = np.linspace(0, 1, n)
    mx = (bx + tx) / 2 + lean * length_px
    my = (by + ty) / 2
    px = (1 - t) ** 2 * bx + 2 * (1 - t) * t * mx + t ** 2 * tx
    py = (1 - t) ** 2 * by + 2 * (1 - t) * t * my + t ** 2 * ty
    pts = np.stack([px, py], 1)
    st.polyline(pts, np.linspace(0.010, 0.003, n) * length_px)
    tang = np.gradient(pts, axis=0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True)
    for k in range(pinnae):
        f = 0.12 + 0.86 * k / pinnae
        i = int(f * (n - 1))
        p0 = pts[i]
        tg = tang[i]
        for side in (-1, 1):
            nrm = np.array([-tg[1], tg[0]]) * side
            L = length_px * 0.30 * np.sin(np.pi * min(1, f * 1.05)) ** 0.7 * (1 - 0.6 * f)
            L *= rng.uniform(0.9, 1.1)
            d = nrm * 0.85 + tg * 0.45
            d /= np.linalg.norm(d)
            curve = tg * 0.15
            m = 9
            for j in range(m):
                g = (j + 0.5) / m
                q = p0 + d * L * g + curve * L * g * g
                rr = L * 0.075 * (1 - 0.65 * g)
                ang = np.arctan2(d[1], d[0])
                for side2 in (-1, 1):
                    off = np.array([-d[1], d[0]]) * side2 * rr * 1.1
                    st.ellipse(q[0] + off[0], q[1] + off[1], rr * 1.2, rr * 0.55, ang + side2 * 0.9, 1.0)
            st.capsule(p0, p0 + d * L + curve * L, max(0.8, length_px * 0.002))


def _umbel(st, rng, base, head, size_px):
    st.capsule(base, head, max(1.0, size_px * 0.012))
    rays = rng.integers(11, 16)
    for k in range(rays):
        a = -np.pi / 2 + (k / (rays - 1) - 0.5) * 2.4 + rng.normal(0, 0.05)
        L = size_px * rng.uniform(0.38, 0.5) * (0.75 + 0.25 * np.cos(a + np.pi / 2))
        e = (head[0] + np.cos(a) * L, head[1] + np.sin(a) * L * 0.75)
        st.capsule(head, e, max(0.6, size_px * 0.004))
        fl = rng.integers(9, 14)
        for j in range(fl):
            b = -np.pi / 2 + (j / (fl - 1) - 0.5) * 2.6
            l2 = size_px * 0.09 * rng.uniform(0.8, 1.1)
            f = (e[0] + np.cos(b) * l2, e[1] + np.sin(b) * l2 * 0.7)
            st.capsule(e, f, max(0.5, size_px * 0.0025))
            st.ellipse(f[0], f[1], size_px * 0.012, size_px * 0.012, 0, 1.0)
    # a few leaves at the stem
    for k in range(2):
        y = base[1] + (head[1] - base[1]) * rng.uniform(0.2, 0.5)
        x = base[0] + (head[0] - base[0]) * (y - base[1]) / (head[1] - base[1] + 1e-9)
        side = 1 if k == 0 else -1
        for j in range(5):
            st.ellipse(x + side * size_px * (0.05 + 0.05 * j), y - size_px * 0.03 * j, size_px * 0.04,
                       size_px * 0.012, side * 0.6, 1.0)


def cyano(w, h, s):
    rng = rng_of(s)
    X, Y = grid(h, w)
    asp = w / h
    img = paper(h, w, rng, s.get("paper", (0.94, 0.93, 0.89)))
    # brushed-on emulsion: a rectangle with dragged, uneven edges
    mg = s.get("margin", 0.07)
    rag = 0.010 * fnoise(h, w, rng, 1.2, ax=6) + 0.008 * fnoise(h, w, rng, 1.2, ay=6)
    d = sdf_box(X, Y, asp / 2, 0.5, asp / 2 - mg * 0.8, 0.5 - mg) + rag
    coat = smooth(0.004, -0.004, d) * (0.9 + 0.1 * smooth(-0.04, 0, d))
    blue = col(s.get("blue", (0.07, 0.21, 0.42))) * (1 + 0.06 * fnoise(h, w, rng, 2.2) + 0.04 * fnoise(h, w, rng, 1.0, ax=8))[..., None]
    img = over(img, blue, coat)
    st = Stamp(h, w)
    for plant in s["plants"]:
        kind = plant[0]
        if kind == "fern":
            _, bx, by, tx, ty, lean = plant
            base, tip = (bx * asp * h, by * h), (tx * asp * h, ty * h)
            _fern(st, rng, base, tip, np.hypot(tip[0] - base[0], tip[1] - base[1]), lean)
        elif kind == "umbel":
            _, bx, by, hx, hy, size = plant
            _umbel(st, rng, (bx * asp * h, by * h), (hx * asp * h, hy * h), size * h)
    sil = blur(st.a, 0.7 * s["_ss"])
    pale = col(s.get("pale", (0.86, 0.90, 0.93)))
    img = over(img, pale * (1 + 0.03 * fnoise(h, w, rng, 1.5))[..., None], sil * coat * 0.95)
    return np.clip(img, 0, 1)


# =============================================================================
# gold: gold-leaf squares on a dark ground
# =============================================================================

def gold(w, h, s):
    rng = rng_of(s)
    X, Y = grid(h, w)
    asp = w / h
    img = col(s.get("ground", (0.035, 0.032, 0.03))) * (1 + 0.08 * fnoise(h, w, rng, 2.0))[..., None]
    x0, y0, x1, y1 = s["panel"]
    inside = (X >= x0 * asp) & (X < x1 * asp) & (Y >= y0) & (Y < y1)
    p = s.get("leaf", 0.085)
    ix = np.floor((X - x0 * asp) / p)
    iy = np.floor((Y - y0) / p + 0.3 * (ix % 2))
    cell = (ix * 7.13 + iy * 3.71) % 1.0
    tone = 0.90 + 0.12 * np.sin(cell * 40.0) + 0.04 * fnoise(h, w, rng, 1.6)
    leafc = col(s.get("gold", (0.80, 0.62, 0.30)))
    leaf = leafc * tone[..., None]
    fx = ((X - x0 * asp) / p) % 1.0
    fy = ((Y - y0) / p + 0.3 * (ix % 2)) % 1.0
    seam = np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy)) * p * h
    leaf = leaf * (1 - 0.18 * np.clip(1.2 - seam, 0, 1))[..., None]
    # cracks and losses show the red bole underneath
    cr = np.abs(fnoise(h, w, rng, 1.5))
    crack = np.clip(1.0 - cr * 18, 0, 1) * s.get("cracks", 0.6)
    loss = smooth(2.3, 2.7, fnoise(h, w, rng, 1.2)) * s.get("losses", 1.0)
    bole = col((0.42, 0.13, 0.07))
    leaf = over(leaf, bole, np.maximum(crack, loss))
    edge_rag = 0.002 * fnoise(h, w, rng, 1.2)
    d = sdf_box(X, Y, (x0 + x1) / 2 * asp, (y0 + y1) / 2, (x1 - x0) / 2 * asp, (y1 - y0) / 2) + edge_rag
    img = over(img, leaf, smooth(0.0008, -0.0008, d))
    return np.clip(img, 0, 1)


# =============================================================================
# photo: photographs as abstraction
# =============================================================================

def _grain(h, w, rng, amt):
    return amt * blur(rng.standard_normal((h, w)), 0.6)


def photo(w, h, s):
    rng = rng_of(s)
    X, Y = grid(h, w)
    asp = w / h
    sc = s["scene"]
    if sc == "seascape":
        hz = s.get("horizon", 0.5)
        sky = lerp([(0, s["sky"][0]), (hz, s["sky"][1])], Y)
        sky *= (1 + 0.015 * fnoise(h, w, rng, 3.0, ax=3))[..., None]
        sea = lerp([(hz, s["sea"][0]), (1, s["sea"][1])], Y)
        swell = fnoise(h, w, rng, 1.5, ax=14) * (0.25 + 0.75 * smooth(hz, 1, Y))
        sea *= (1 + 0.035 * swell + 0.012 * fnoise(h, w, rng, 2.4, ax=4))[..., None]
        img = over(sky, sea, smooth(-0.0025, 0.0025, Y - hz))
        haze = np.exp(-((Y - hz + 0.015) / 0.06) ** 2) * s.get("haze", 0.05)
        img = img + haze[..., None]
    elif sc == "dune":
        r1 = s["crest1"]        # [(xf, yf), ...] the near crest; shadow face above it
        r2 = s["crest2"]        # the far crest; lit far dune above it
        c1 = np.interp(X / asp, [p[0] for p in r1], [p[1] for p in r1])
        c2 = np.interp(X / asp, [p[0] for p in r2], [p[1] for p in r2])
        c1 = blur(c1, 0)
        lit = lerp([(0, s["lit"][0]), (1, s["lit"][1])], (Y - c1) / (1 - c1 + 1e-6))
        rip = np.sin(2 * np.pi * (Y * s.get("ripples", 38) + 2.2 * X + 0.6 * fnoise(h, w, rng, 2.4)))
        lit *= (1 + 0.035 * rip * smooth(0.0, 0.06, Y - c1) + 0.02 * fnoise(h, w, rng, 2.2))[..., None]
        shade = lerp([(0, s["shadow"][0]), (1, s["shadow"][1])], (Y - c2) / (c1 - c2 + 1e-6))
        far = lerp([(0, s["far"][0]), (1, s["far"][1])], Y / (c2 + 1e-6))
        far *= (1 + 0.02 * fnoise(h, w, rng, 2.4, ax=3))[..., None]
        img = over(far, shade, smooth(-0.002, 0.002, Y - c2))
        img = over(img, lit, smooth(-0.0015, 0.0015, Y - c1))
        if s.get("sky"):
            img = over(img, col(s["sky"]) * (1 + 0.1 * Y)[..., None], smooth(0.002, -0.002, Y - s["sky_y"]))
    elif sc == "fog":
        img = lerp([(0, s["fog"][0]), (0.6, s["fog"][1]), (1, s["fog"][2])], Y)
        img *= (1 + 0.02 * fnoise(h, w, rng, 3.0))[..., None]
        for layer, (n_, wpx, contrast, sig) in enumerate(s["layers"]):
            st = Stamp(h, w)
            for _ in range(n_):
                x = rng.uniform(-0.05, 1.05) * asp * h
                lean = rng.normal(0, 0.012) * h
                top = rng.uniform(-0.1, 0.05) * h
                bot = (s.get("ground_y", 0.86) + 0.03 * layer + rng.uniform(-0.01, 0.01)) * h
                r = wpx * h * rng.uniform(0.7, 1.3)
                st.polyline([(x + lean, top), (x, bot)], [r * 0.8, r])
                for b in range(int(rng.integers(0, 4)) if layer >= 1 else 0):     # a few dead branches
                    y = rng.uniform(0.05, 0.55) * h
                    sd = rng.choice([-1, 1])
                    L = rng.uniform(0.015, 0.045) * h
                    st.capsule((x, y), (x + sd * L, y + L * rng.uniform(0.35, 0.8)), max(0.5, r * 0.12))
            cov = blur(st.a, sig * s["_ss"])
            dark = col(s["dark"])
            img = over(img, dark, cov * contrast)
        g = s.get("ground_y", 0.86)
        img = over(img, col(s["floor"]), smooth(g - 0.02, g + 0.06, Y) * 0.8)
    elif sc == "clouds":
        img = lerp([(0, s["sky"][0]), (1, s["sky"][1])], Y)
        c = fnoise(h, w, rng, 2.7, ax=1.8) + 0.18 * fnoise(h, w, rng, 1.8)
        c = c + s.get("bias", -0.3) + s.get("bank", 1.4) * smooth(0.3, 1.0, Y) - 0.9 * smooth(0.5, 0.0, Y)
        m = smooth(0.0, 1.1, c)
        top = np.clip(c - np.roll(c, int(0.04 * h), axis=0), -1, 1)      # lit where density rises upward
        shade = lerp([(-1, s["cloud"][0]), (1, s["cloud"][1])], top * 2.5)
        img = over(img, shade, m)
        img = blur(img, 1.2 * s["_ss"])
    elif sc == "ponds":
        warpx = 0.02 * fnoise(h, w, rng, 2.6)
        warpy = 0.02 * fnoise(h, w, rng, 2.6)
        U, V = np.clip(X / asp + warpx, 0, 0.9999), np.clip(Y + warpy, 0, 0.9999)
        cells = [(0.0, 0.0, 1.0, 1.0)]
        for _ in range(s.get("splits", 26)):
            i = int(np.argmax([(c[2] - c[0]) * asp * (c[3] - c[1]) * rng.uniform(0.6, 1.4) for c in cells]))
            x0, y0, x1, y1 = cells.pop(i)
            if (x1 - x0) * asp > (y1 - y0):
                xm = x0 + (x1 - x0) * rng.uniform(0.3, 0.7)
                cells += [(x0, y0, xm, y1), (xm, y0, x1, y1)]
            else:
                ym = y0 + (y1 - y0) * rng.uniform(0.3, 0.7)
                cells += [(x0, y0, x1, ym), (x0, ym, x1, y1)]
        img = np.zeros((h, w, 3))
        dike = np.full((h, w), 9.0)
        pal = s["palette"]
        for k, (x0, y0, x1, y1) in enumerate(cells):
            m = (U >= x0) & (U < x1) & (V >= y0) & (V < y1)
            c = col(pal[int(rng.integers(0, len(pal)))])
            grad = 1 + 0.08 * ((U - x0) / (x1 - x0 + 1e-6) - 0.5) * rng.uniform(-1, 1)
            streak = 1 + 0.05 * fnoise(h, w, rng, 1.8, ax=rng.uniform(1, 6))
            img = np.where(m[..., None], c * (grad * streak)[..., None], img)
            e = np.minimum.reduce([(U - x0) * asp, (x1 - U) * asp, V - y0, y1 - V])
            dike = np.where(m, e, dike)
        dw = s.get("dike", 0.006)
        img = over(img, col(s["earth"]) * (1 + 0.08 * fnoise(h, w, rng, 1.2))[..., None], smooth(dw, dw * 0.4, dike))
        img = blur(img, 0.5 * s["_ss"])
    elif sc == "moon":
        hz = s.get("horizon", 0.58)
        sky = lerp([(0, s["sky"][0]), (hz, s["sky"][1])], Y)
        mx, my, mr = s["moon"]
        d = np.hypot(X - mx * asp, Y - my)
        glow = np.exp(-(d / (mr * 6)) ** 2) * 0.10 + np.exp(-(d / (mr * 1.8)) ** 2) * 0.10
        sky = sky + glow[..., None] * col(s["moonc"])
        sky = over(sky, col(s["moonc"]) * (1 - 0.05 * fnoise(h, w, rng, 2.0))[..., None], smooth(mr + 0.002, mr - 0.002, d))
        sea = lerp([(hz, s["sea"][0]), (1, s["sea"][1])], Y)
        waves = fnoise(h, w, rng, 1.1, ax=10)
        spread = 0.025 + 0.16 * smooth(hz, 1, Y)
        glade = np.exp(-((X - mx * asp) / spread) ** 2) * smooth(hz, hz + 0.01, Y)
        spark = smooth(0.6, 1.8, waves) * glade
        sea = sea + (spark * 0.9 + glade * 0.10)[..., None] * col(s["moonc"])
        img = over(sky, sea, smooth(-0.0015, 0.0015, Y - hz))
    elif sc == "shore":
        sh = np.interp(X / asp, [p[0] for p in s["shore"]], [p[1] for p in s["shore"]])
        sh = sh + 0.012 * fnoise(h, w, rng, 2.4, ax=3)
        dist = Y - sh             # > 0: sea side (below the shoreline)
        sand = col(s["sand"]) * (1 + 0.04 * fnoise(h, w, rng, 1.6) + 0.02 * fnoise(h, w, rng, 1.0, ax=4))[..., None]
        sand = over(sand, col(s["wet"]), smooth(-0.05, 0.0, dist))
        water = lerp([(0, s["water"][0]), (0.08, s["water"][1]), (0.35, s["water"][2]), (1, s["water"][3])],
                     np.clip(dist * 1.2 + 0.03 * fnoise(h, w, rng, 2.2), 0, 1))
        water *= (1 + 0.04 * fnoise(h, w, rng, 1.3, ax=6))[..., None]
        img = over(sand, water, smooth(-0.004, 0.004, dist))
        lace = smooth(0.4, 1.6, fnoise(h, w, rng, 0.9, ax=3))
        for off, wdt, a in s["foam"]:
            band = np.exp(-((dist - off) / wdt) ** 2)
            img = over(img, col((0.95, 0.96, 0.95)), band * (0.35 + 0.65 * lace) * a)
        img = blur(img, 0.5 * s["_ss"])
    elif sc == "vineyard":
        warpx = 0.015 * fnoise(h, w, rng, 2.8)
        U, V = np.clip(X / asp + warpx, 0, 0.9999), np.clip(Y + 0.015 * fnoise(h, w, rng, 2.8), 0, 0.9999)
        cells = [(0.0, 0.0, 1.0, 1.0)]
        for _ in range(s.get("splits", 9)):
            i = int(np.argmax([(c[2] - c[0]) * asp * (c[3] - c[1]) * rng.uniform(0.6, 1.4) for c in cells]))
            x0, y0, x1, y1 = cells.pop(i)
            if (x1 - x0) * asp > (y1 - y0) * rng.uniform(0.6, 1.4):
                xm = x0 + (x1 - x0) * rng.uniform(0.35, 0.65)
                cells += [(x0, y0, xm, y1), (xm, y0, x1, y1)]
            else:
                ym = y0 + (y1 - y0) * rng.uniform(0.35, 0.65)
                cells += [(x0, y0, x1, ym), (x0, ym, x1, y1)]
        terrain = fnoise(h, w, rng, 3.2) * 0.12
        img = np.zeros((h, w, 3))
        track = np.full((h, w), 9.0)
        pitch = s.get("pitch", 0.012)
        for k, (x0, y0, x1, y1) in enumerate(cells):
            m = (U >= x0) & (U < x1) & (V >= y0) & (V < y1)
            ang = rng.uniform(0, np.pi)
            field = (X * np.cos(ang) + Y * np.sin(ang)) + terrain * rng.uniform(0.5, 1.5)
            rows_ = 0.5 + 0.5 * np.sin(2 * np.pi * field / pitch)
            vine_c = col(s["vines"][int(rng.integers(0, len(s["vines"])))])
            earth_c = col(s["soil"][int(rng.integers(0, len(s["soil"])))])
            if rng.uniform() < s.get("fallow", 0.12):
                vine_c = earth_c * 0.9
            leafy = smooth(0.35, 0.75, rows_ + 0.25 * fnoise(h, w, rng, 1.0))
            cc = earth_c * (1 + 0.05 * fnoise(h, w, rng, 1.6))[..., None]
            cc = over(cc, vine_c * (1 + 0.08 * fnoise(h, w, rng, 1.0))[..., None], leafy)
            img = np.where(m[..., None], cc, img)
            e = np.minimum.reduce([(U - x0) * asp, (x1 - U) * asp, V - y0, y1 - V])
            track = np.where(m, e, track)
        tw = s.get("track", 0.006)
        img = over(img, col(s["track_c"]), smooth(tw, tw * 0.4, track))
        img *= (1 + 0.10 * fnoise(h, w, rng, 3.0))[..., None]        # cloud shadow / terrain light
        img = blur(img, 0.45 * s["_ss"])
    else:
        raise ValueError(sc)
    img = vignette(img, X, Y, s.get("vignette", 0.08))
    img = img * (1 + _grain(h, w, rng, s.get("grain", 0.015)))[..., None]
    return np.clip(img, 0, 1)


STYLES = {
    "colorfield": (colorfield, 1),
    "hardedge": (hardedge, 2),
    "blocks": (blocks, 1),
    "mono": (mono, 1),
    "weave": (weave_art, 2),
    "stain": (stain, 1),
    "rings": (rings, 2),
    "wash": (wash, 1),
    "cyano": (cyano, 2),
    "grid": (grid_art, 2),
    "contour": (contour, 2),
    "ink": (ink, 2),
    "gold": (gold, 2),
    "photo": (photo, 1),
}


def paint(style, w, h, spec, size_m=None):
    """Render `style` at w x h px. `size_m` = the artwork's (width, height) in metres
    (sets the canvas weave's pixel pitch)."""
    fn, ss = STYLES[style]
    ss = spec.get("ss", ss)
    s = dict(spec)
    s["_ss"] = ss
    s["_ppm"] = (h * ss) / (size_m[1] if size_m else 1.0)
    img = fn(w * ss, h * ss, s)
    return np.clip(down(img, ss), 0, 1)
