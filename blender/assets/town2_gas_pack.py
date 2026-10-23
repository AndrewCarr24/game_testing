"""The gas station's packaging atlas (one texture for every product in the store): chip bags,
bottle and can wraps (unrolled: u round the circumference, v up the height), boxes, pouches, jars,
jugs, cartons, multipack cases, cigarette packs, the coffee-bar supplies, cardboard, the shelf tag
strip, the ice and propane panels and the Blue Ridge mural.

Packaging is drawn as plausible graphics with no readable words: a "wordmark" is a run of chunky
letter-like strokes, "copy" is rows of short bars, and nutrition panels are ruled boxes. Drawn at
2x (192 px cells) and box-filtered to the shipped 768 x 960 (96 px cells).
"""
import math
import os

import numpy as np

import town2_gas_tex as TX

S = 192                      # cell size, drawn
COLS, ROWS = 8, 10


class Canvas:
    """Linear-RGB canvas; every shape is evaluated only inside its bounding box."""

    def __init__(self, w, h, col=(0, 0, 0)):
        self.w, self.h = w, h
        self.px = np.zeros((h, w, 3), np.float32) + TX.to_lin(np.array(col, np.float32))

    def _win(self, x0, y0, x1, y1, pad=2):
        a, b = max(int(math.floor(x0)) - pad, 0), max(int(math.floor(y0)) - pad, 0)
        c, d = min(int(math.ceil(x1)) + pad, self.w), min(int(math.ceil(y1)) + pad, self.h)
        if c <= a or d <= b:
            return None
        Y, X = np.mgrid[b:d, a:c].astype(np.float32) + 0.5
        return (a, b, c, d), X, Y

    def _put(self, win, cov, col, alpha=1.0):
        (a, b, c, d) = win
        cov = (np.clip(cov, 0, 1) * alpha)[..., None]
        col = col if isinstance(col, np.ndarray) and col.ndim == 3 else TX.to_lin(np.array(col, np.float32))
        self.px[b:d, a:c] = self.px[b:d, a:c] * (1 - cov) + col * cov

    def rect(self, x0, y0, x1, y1, col, r=0.0, alpha=1.0):
        w = self._win(x0, y0, x1, y1)
        if not w:
            return
        win, X, Y = w
        cx, cy, hx, hy = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
        r = min(r, hx, hy)
        dx, dy = np.abs(X - cx) - hx + r, np.abs(Y - cy) - hy + r
        dd = np.hypot(np.maximum(dx, 0), np.maximum(dy, 0)) + np.minimum(np.maximum(dx, dy), 0) - r
        self._put(win, 0.5 - dd / 0.8, col, alpha)

    def ellipse(self, cx, cy, rx, ry, col, alpha=1.0):
        w = self._win(cx - rx, cy - ry, cx + rx, cy + ry)
        if not w:
            return
        win, X, Y = w
        dd = (np.hypot((X - cx) / rx, (Y - cy) / ry) - 1) * min(rx, ry)
        self._put(win, 0.5 - dd / 0.8, col, alpha)

    def ring(self, cx, cy, r, t, col, alpha=1.0):
        w = self._win(cx - r - t, cy - r - t, cx + r + t, cy + r + t)
        if not w:
            return
        win, X, Y = w
        dd = np.abs(np.hypot(X - cx, Y - cy) - r) - t / 2
        self._put(win, 0.5 - dd / 0.8, col, alpha)

    def poly(self, pts, col, alpha=1.0):
        P = np.array(pts, np.float32)
        w = self._win(*P.min(axis=0), *P.max(axis=0))
        if not w:
            return
        win, X, Y = w
        cov = np.zeros_like(X)
        for sy in range(3):
            for sx in range(3):
                xs, ys = X - 0.5 + (sx + 0.5) / 3, Y - 0.5 + (sy + 0.5) / 3
                inside = np.zeros_like(X, bool)
                for i in range(len(P)):
                    ax, ay = P[i]
                    bx, by = P[(i + 1) % len(P)]
                    inside ^= ((ay > ys) != (by > ys)) & (xs < (bx - ax) * (ys - ay) / (by - ay + 1e-9) + ax)
                cov += inside
        self._put(win, cov / 9, col, alpha)

    def grad(self, x0, y0, x1, y1, c0, c1, vertical=True, alpha=1.0):
        w = self._win(x0, y0, x1, y1, pad=0)
        if not w:
            return
        win, X, Y = w
        t = np.clip(((Y - y0) / max(y1 - y0, 1e-6)) if vertical else ((X - x0) / max(x1 - x0, 1e-6)), 0, 1)[..., None]
        c = TX.to_lin(np.array(c0, np.float32)) * (1 - t) + TX.to_lin(np.array(c1, np.float32)) * t
        inside = ((X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)).astype(np.float32)
        self._put(win, inside, c, alpha)

    def mul(self, x0, y0, x1, y1, f):
        """Multiply a region by f(X, Y) (shading)."""
        w = self._win(x0, y0, x1, y1, pad=0)
        if not w:
            return
        (a, b, c, d), X, Y = w
        inside = (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)
        m = np.where(inside, f(X, Y), 1.0)[..., None]
        self.px[b:d, a:c] *= m

    def add(self, x0, y0, x1, y1, f):
        w = self._win(x0, y0, x1, y1, pad=0)
        if not w:
            return
        (a, b, c, d), X, Y = w
        inside = (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)
        self.px[b:d, a:c] += np.where(inside, f(X, Y), 0.0)[..., None]


def C(c):
    return tuple(np.array(c, np.float32) / 255.0)


def darker(c, k):
    return tuple(np.array(c) * k)


def lighter(c, k):
    c = np.array(c)
    return tuple(c + (1 - c) * k)


# ------------------------------------------------------------------ packaging vocabulary
def wordmark(cv, cx, cy, w, h, col, rng, italic=0.18, outline=None):
    """A brand-like wordmark that reads as lettering at a glance but isn't: 4-7 chunky strokes of
    letter-ish widths (some with counters), on a shared baseline, slightly italic."""
    n = rng.integers(4, 8)
    widths = rng.uniform(0.6, 1.3, n)
    widths = widths / widths.sum() * w
    x = cx - w / 2
    for k in range(n):
        gw = widths[k] * 0.84
        tall = h * (1.0 if k == 0 or rng.random() < 0.25 else rng.uniform(0.62, 0.8))
        y1 = cy + h / 2
        y0 = y1 - tall
        sk = italic * tall
        pts = [(x + sk, y0), (x + gw + sk, y0), (x + gw, y1), (x, y1)]
        if outline is not None:
            o = h * 0.08
            cv.poly([(px - o, py - o) if i < 2 else (px + o * (1 if i == 2 else -1), py + o) for i, (px, py) in enumerate(pts)], outline)
        cv.poly(pts, col)
        x += widths[k]
    if rng.random() < 0.5:                                # a swoosh under it
        cv.poly([(cx - w * 0.5, cy + h * 0.62), (cx + w * 0.55, cy + h * 0.5), (cx + w * 0.5, cy + h * 0.62), (cx - w * 0.45, cy + h * 0.72)], col)


def copy(cv, x, y, w, lines, lh, col, rng, alpha=0.9):
    """Rows of 'small print': short bars of random lengths."""
    for k in range(lines):
        xx = x
        yy = y + k * lh
        end = x + w * rng.uniform(0.6, 1.0)
        while xx < end:
            ww = rng.uniform(lh * 0.6, lh * 3.0)
            cv.rect(xx, yy, min(xx + ww, end), yy + lh * 0.55, col, r=lh * 0.2, alpha=alpha)
            xx += ww + lh * 0.45


def badge(cv, cx, cy, r, col, ring_col, rng):
    cv.ellipse(cx, cy, r, r, col)
    cv.ring(cx, cy, r * 0.82, r * 0.1, ring_col)
    copy(cv, cx - r * 0.55, cy - r * 0.18, r * 1.1, 2, r * 0.28, ring_col, rng)


def shade_cyl(cv, x0, y0, x1, y1, k=0.55, gloss=0.25, at=0.32):
    """A cylinder's shading across x (the wrap's front is at the centre: the lightmap does the
    rest; this is the label's own sheen and the curvature's falloff toward the sides)."""
    cv.mul(x0, y0, x1, y1, lambda X, Y: 1 - k * (2 * (X - x0) / (x1 - x0) - 1) ** 4)
    cv.add(x0, y0, x1, y1, lambda X, Y: gloss * np.exp(-(((X - x0) / (x1 - x0) - at) / 0.035) ** 2))


def crinkle(cv, x0, y0, x1, y1, rng, k=0.18):
    """A foil bag's crinkle: soft random light and dark creases."""
    def f(X, Y):
        out = np.ones_like(X)
        for _ in range(9):
            a = rng.uniform(0, math.pi)
            px, py = rng.uniform(x0, x1), rng.uniform(y0, y1)
            d = (X - px) * math.cos(a) + (Y - py) * math.sin(a)
            out += k * rng.uniform(-1, 1) * np.exp(-(d / rng.uniform(2, 9)) ** 2)
        return out
    cv.mul(x0, y0, x1, y1, f)


# ------------------------------------------------------------------ cells
BAG_COLS = [(214, 38, 36), (244, 190, 32), (28, 92, 180), (36, 140, 68), (110, 36, 140), (240, 112, 28), (26, 26, 28), (210, 208, 200),
            (184, 26, 88), (24, 158, 178), (148, 192, 40), (226, 72, 46), (70, 48, 36), (38, 58, 124), (240, 214, 58), (192, 38, 38)]


def bag(cv, x, y, i, rng):
    c = C(BAG_COLS[i])
    acc = C(BAG_COLS[(i * 5 + 3) % 16])
    W = S
    cv.rect(x, y, x + W, y + W, (0.12, 0.12, 0.12))
    cv.rect(x + 4, y + 4, x + W - 4, y + W - 4, c, r=8)
    d = i % 6
    if d == 0:
        cv.ellipse(x + W * 0.5, y + W * 0.66, W * 0.34, W * 0.22, (0.95, 0.93, 0.88))
        for k in range(7):
            cv.ellipse(x + W * rng.uniform(0.28, 0.72), y + W * rng.uniform(0.6, 0.76), W * 0.07, W * 0.045, C((222, 170, 74)))
    elif d == 1:
        cv.poly([(x + 4, y + W * 0.62), (x + W - 4, y + W * 0.28), (x + W - 4, y + W * 0.44), (x + 4, y + W * 0.78)], acc)
        for k in range(5):
            cv.ellipse(x + W * rng.uniform(0.45, 0.8), y + W * rng.uniform(0.72, 0.85), W * 0.08, W * 0.05, C((226, 176, 80)))
    elif d == 2:
        cv.rect(x + 4, y + W * 0.56, x + W - 4, y + W - 4, darker(c, 0.6), r=6)
        cv.ellipse(x + W * 0.5, y + W * 0.56, W * 0.22, W * 0.22, acc)
        for k in range(10):
            a = k / 10 * 2 * math.pi
            cv.poly([(x + W * 0.5, y + W * 0.56), (x + W * 0.5 + math.cos(a) * W * 0.32, y + W * 0.56 + math.sin(a) * W * 0.32),
                     (x + W * 0.5 + math.cos(a + 0.12) * W * 0.32, y + W * 0.56 + math.sin(a + 0.12) * W * 0.32)], acc, alpha=0.5)
    elif d == 3:
        for k in range(6):
            cv.rect(x + 4, y + 26 + k * 28, x + W - 4, y + 36 + k * 28, darker(c, 0.7))
        cv.rect(x + 26, y + W * 0.38, x + W - 26, y + W * 0.64, (0.95, 0.93, 0.88), r=10)
    elif d == 4:
        cv.grad(x + 4, y + 4, x + W - 4, y + W - 4, c, darker(c, 0.55))
        for k in range(5):
            bx = x + 26 + k * 30
            cv.poly([(bx, y + W * 0.86), (bx + 24, y + W * 0.6 + 8 * (k % 2)), (bx + 44, y + W * 0.86)], C((228, 178, 76)))
    else:
        cv.rect(x + 22, y + W * 0.42, x + W - 22, y + W - 26, C((156, 116, 70)), r=16)
        for k in range(8):
            cv.ring(x + 52 + (k % 4) * 30, y + W * 0.56 + (k // 4) * 34, 11, 5, C((112, 64, 30)))
    # the wordmark and the strap line; the crimp seals (with teeth)
    wordmark(cv, x + W * 0.5, y + W * 0.28, W * 0.62, W * 0.13, (0.98, 0.97, 0.94) if d != 7 else acc, rng, outline=darker(c, 0.45))
    cv.rect(x + W * 0.3, y + W * 0.4, x + W * 0.7, y + W * 0.44, acc, r=3)
    for yy in (y + 4, y + W - 16):
        cv.rect(x + 4, yy, x + W - 4, yy + 12, darker(c, 0.72), r=3)
        for k in range(18):
            cv.rect(x + 8 + k * 10, yy + 2, x + 12 + k * 10, yy + 10, darker(c, 0.55))
    copy(cv, x + 20, y + W * 0.86, W * 0.5, 1, 7, (0.95, 0.95, 0.92), rng, 0.7)
    crinkle(cv, x + 4, y + 4, x + W - 4, y + W - 4, rng)
    shade_cyl(cv, x + 4, y + 4, x + W - 4, y + W - 4, k=0.45, gloss=0.18, at=0.3)


BOTTLES = [  # liquid, label, cap, accent
    ((120, 170, 215), (40, 110, 200), (230, 230, 232), (255, 255, 255)),     # water
    ((60, 28, 16), (196, 28, 32), (196, 28, 32), (250, 250, 250)),           # cola
    ((176, 220, 140), (38, 140, 64), (38, 140, 64), (250, 240, 120)),        # lemon-lime
    ((240, 140, 30), (250, 250, 250), (240, 120, 20), (40, 40, 40)),         # orange
    ((60, 120, 230), (30, 30, 34), (60, 120, 230), (250, 250, 250)),         # sport blue
    ((220, 40, 52), (30, 30, 34), (220, 40, 52), (250, 250, 250)),           # sport red
    ((170, 90, 30), (236, 220, 160), (236, 220, 160), (120, 60, 20)),        # tea
    ((240, 150, 40), (40, 140, 60), (40, 140, 60), (250, 250, 250)),         # juice
]


def bottle(cv, x, y, i, rng):
    liq, lab, cap, acc = (C(c) for c in BOTTLES[i])
    W = S
    # (v up the bottle: cell bottom = base, top = cap; the drawing's y is down)
    cv.grad(x, y, x + W, y + W, lighter(liq, 0.25), darker(liq, 0.75))
    cv.rect(x, y, x + W, y + W * 0.1, cap)
    cv.rect(x, y + W * 0.1, x + W, y + W * 0.13, darker(cap, 0.7))
    l0, l1 = y + W * 0.42, y + W * 0.74
    cv.rect(x, l0, x + W, l1, lab)
    cv.rect(x, l0, x + W, l0 + 6, acc)
    cv.rect(x, l1 - 6, x + W, l1, acc)
    wordmark(cv, x + W * 0.5, (l0 + l1) / 2 - 4, W * 0.36, (l1 - l0) * 0.42, acc, rng)
    copy(cv, x + W * 0.72, l0 + 14, W * 0.22, 5, 8, acc, rng, 0.6)       # the back (nutrition)
    copy(cv, x + W * 0.06, l0 + 14, W * 0.14, 4, 8, acc, rng, 0.6)
    cv.rect(x, y + W * 0.92, x + W, y + W, darker(liq, 0.6))             # the base's ribs
    shade_cyl(cv, x, y, x + W, y + W, k=0.3, gloss=0.35, at=0.5)


CANS = [((196, 28, 32), (250, 250, 250)), ((200, 202, 206), (196, 28, 32)), ((24, 24, 26), (120, 220, 60)), ((190, 192, 196), (30, 60, 160)),
        ((240, 240, 238), (230, 60, 140)), ((230, 236, 240), (80, 170, 210)), ((40, 70, 40), (230, 210, 150)), ((230, 200, 90), (40, 80, 50))]


def can(cv, x, y, i, rng):
    body, acc = (C(c) for c in CANS[i])
    W = S
    cv.rect(x, y, x + W, y + W, body)
    d = i % 4
    if d == 0:
        cv.poly([(x, y + W * 0.55), (x + W, y + W * 0.3), (x + W, y + W * 0.42), (x, y + W * 0.67)], acc)
    elif d == 1:
        for k in range(3):
            cv.rect(x + k * W / 3, y + W * 0.2, x + k * W / 3 + W / 6, y + W * 0.9, acc, alpha=0.8)
    elif d == 2:
        cv.poly([(x + W * 0.5, y + W * 0.2), (x + W * 0.62, y + W * 0.5), (x + W * 0.55, y + W * 0.5), (x + W * 0.66, y + W * 0.85),
                 (x + W * 0.4, y + W * 0.45), (x + W * 0.48, y + W * 0.45)], acc)
    else:
        cv.ellipse(x + W * 0.5, y + W * 0.55, W * 0.2, W * 0.2, acc)
    wordmark(cv, x + W * 0.5, y + W * 0.38, W * 0.34, W * 0.16, acc if d != 3 else (0.98, 0.98, 0.98), rng)
    copy(cv, x + W * 0.75, y + W * 0.5, W * 0.18, 5, 7, acc, rng, 0.6)
    cv.rect(x, y, x + W, y + W * 0.06, C((188, 190, 194)))             # the lid and the rim
    cv.rect(x, y + W * 0.94, x + W, y + W, C((170, 172, 176)))
    shade_cyl(cv, x, y, x + W, y + W, k=0.35, gloss=0.5, at=0.5)


BOX_COLS = [(200, 40, 40), (40, 90, 170), (240, 200, 60), (120, 70, 40), (60, 140, 80), (232, 232, 226), (170, 40, 120), (240, 140, 40)]


def box(cv, x, y, i, rng):
    c = C(BOX_COLS[i])
    W = S
    cv.rect(x, y, x + W, y + W, c)
    if i % 2 == 0:       # cereal / crackers: a "photo" bowl, a big wordmark at the top
        cv.rect(x + 10, y + 10, x + W - 10, y + W * 0.3, darker(c, 0.7), r=8)
        wordmark(cv, x + W * 0.5, y + W * 0.2, W * 0.7, W * 0.12, (1, 1, 1), rng, outline=darker(c, 0.4))
        cv.ellipse(x + W * 0.5, y + W * 0.7, W * 0.34, W * 0.18, (0.96, 0.95, 0.92))
        for k in range(12):
            cv.ellipse(x + W * rng.uniform(0.25, 0.75), y + W * rng.uniform(0.6, 0.72), W * 0.05, W * 0.035, C((214, 160, 70)))
        badge(cv, x + W * 0.82, y + W * 0.42, W * 0.1, (0.98, 0.85, 0.2), darker(c, 0.5), rng)
    else:                # candy / medicine: a white panel, a coloured stripe, small print
        cv.rect(x + 14, y + W * 0.3, x + W - 14, y + W - 18, (0.96, 0.95, 0.9), r=10)
        cv.rect(x + 14, y + W * 0.62, x + W - 14, y + W * 0.7, c)
        wordmark(cv, x + W * 0.5, y + W * 0.46, W * 0.52, W * 0.1, c, rng)
        copy(cv, x + 26, y + W * 0.76, W * 0.6, 3, 9, darker(c, 0.6), rng)
    cv.mul(x, y, x + W, y + W, lambda X, Y: 0.94 + 0.06 * (1 - (Y - y) / W))


def pouch(cv, x, y, i, rng):
    base = C([(150, 116, 80), (40, 40, 42), (160, 40, 30), (40, 80, 50)][i])
    W = S
    cv.rect(x, y, x + W, y + W, (0.14, 0.14, 0.14))
    cv.rect(x + 14, y + 6, x + W - 14, y + W - 4, base, r=12)
    cv.rect(x + 40, y + W * 0.44, x + W - 40, y + W - 30, C((120, 64, 34)) if i % 2 == 0 else C((168, 128, 74)), r=16)
    for k in range(6):
        cv.ellipse(x + rng.uniform(50, W - 50), y + rng.uniform(W * 0.5, W - 40), 10, 5, C((90, 44, 22)))
    wordmark(cv, x + W * 0.5, y + W * 0.28, W * 0.5, W * 0.11, (0.96, 0.9, 0.78), rng)
    crinkle(cv, x + 14, y + 6, x + W - 14, y + W - 4, rng, 0.12)
    shade_cyl(cv, x + 14, y + 6, x + W - 14, y + W - 4, k=0.4, gloss=0.08, at=0.35)


def jar(cv, x, y, i, rng):
    fill = C([(150, 90, 40), (200, 60, 40), (230, 200, 120), (90, 120, 40)][i])
    lid = C([(200, 40, 40), (30, 30, 30), (40, 90, 170), (220, 200, 60)][i])
    W = S
    cv.grad(x, y, x + W, y + W, fill, darker(fill, 0.7))
    cv.rect(x, y, x + W, y + W * 0.16, lid)
    for k in range(6):
        cv.rect(x + k * W / 6, y, x + k * W / 6 + 4, y + W * 0.16, darker(lid, 0.7))
    cv.rect(x, y + W * 0.36, x + W, y + W * 0.78, (0.96, 0.94, 0.88))
    wordmark(cv, x + W * 0.5, y + W * 0.52, W * 0.34, W * 0.1, lid, rng)
    copy(cv, x + W * 0.36, y + W * 0.64, W * 0.3, 2, 8, darker(lid, 0.6), rng)
    shade_cyl(cv, x, y, x + W, y + W, k=0.3, gloss=0.4, at=0.5)


def jug(cv, x, y, i, rng):
    c = C([(30, 60, 150), (24, 24, 26), (230, 190, 30), (40, 130, 200)][i])
    W = S
    cv.rect(x, y, x + W, y + W, c)
    cv.rect(x + 20, y + W * 0.36, x + W - 20, y + W * 0.8, (0.96, 0.96, 0.93), r=10)
    cv.rect(x + 20, y + W * 0.36, x + W - 20, y + W * 0.46, C([(200, 40, 40), (230, 190, 30), (30, 30, 30), (240, 240, 240)][i]), r=10)
    wordmark(cv, x + W * 0.5, y + W * 0.58, W * 0.5, W * 0.1, c, rng)
    copy(cv, x + 34, y + W * 0.66, W * 0.5, 2, 9, darker(c, 0.5), rng)
    shade_cyl(cv, x, y, x + W, y + W, k=0.3, gloss=0.2, at=0.4)


def carton(cv, x, y, i, rng):
    c = C([(246, 246, 244), (120, 70, 40), (240, 150, 30), (240, 240, 240)][i])
    acc = C([(40, 90, 170), (240, 240, 240), (40, 140, 60), (200, 40, 60)][i])
    W = S
    cv.rect(x, y, x + W, y + W, c)
    cv.rect(x, y + W * 0.5, x + W, y + W * 0.62, acc)
    cv.poly([(x, y + W * 0.9), (x + W * 0.5, y + W * 0.7), (x + W, y + W * 0.9), (x + W, y + W), (x, y + W)], acc)
    wordmark(cv, x + W * 0.5, y + W * 0.34, W * 0.6, W * 0.12, acc, rng)
    copy(cv, x + 20, y + W * 0.68, W * 0.4, 2, 8, darker(acc, 0.6), rng)


def pack_grid(cv, x, y, i, rng):
    """Cigarette packs, 3 x 2 per cell (the tobacco wall's facings)."""
    W = S
    cv.rect(x, y, x + W, y + W, (0.08, 0.08, 0.08))
    tones = [(250, 250, 248), (200, 30, 36), (230, 200, 120), (40, 60, 120), (30, 30, 30), (90, 140, 80), (160, 120, 60), (110, 110, 120)]
    for r in range(2):
        for k in range(3):
            c = C(tones[(i * 3 + k + r * 2) % 8])
            x0, y0 = x + 6 + k * 62, y + 6 + r * 92
            cv.rect(x0, y0, x0 + 56, y0 + 86, c, r=2)
            cv.rect(x0, y0 + 50, x0 + 56, y0 + 86, (0.95, 0.95, 0.93))       # the warning panel (blank)
            cv.rect(x0 + 4, y0 + 56, x0 + 52, y0 + 60, (0.1, 0.1, 0.1))
            wordmark(cv, x0 + 28, y0 + 26, 40, 12, darker(c, 0.35) if sum(c) > 2 else (0.95, 0.9, 0.7), rng, italic=0.05)
            cv.mul(x0, y0, x0 + 56, y0 + 86, lambda X, Y: 0.9 + 0.1 * np.cos((X - x0) / 56 * math.pi - math.pi / 2))


def case(cv, x, y, i, rng):
    c = C([(190, 150, 60), (30, 70, 40), (200, 40, 40), (240, 240, 236)][i])
    acc = C([(30, 40, 90), (230, 220, 200), (240, 240, 240), (40, 60, 130)][i])
    W = S
    cv.rect(x, y, x + W, y + W, c)
    cv.rect(x, y + W * 0.3, x + W, y + W * 0.66, acc)
    wordmark(cv, x + W * 0.5, y + W * 0.48, W * 0.6, W * 0.14, c, rng, outline=darker(acc, 0.5))
    for k in range(4):        # the cans' tops shown through the window
        cv.ellipse(x + W * (0.2 + 0.2 * k), y + W * 0.84, W * 0.08, W * 0.06, C((200, 200, 204)))
    cv.rect(x + W * 0.82, y + W * 0.08, x + W * 0.95, y + W * 0.22, (0.98, 0.98, 0.98), r=4)


def tags(cv, x, y, rng):
    """The shelf-edge label strip: a clear rail with white tags (a big price-like block, small
    print) every few facings, a yellow sale tag now and then."""
    W = S
    cv.rect(x, y, x + W, y + W, C((236, 236, 232)))
    for k in range(4):
        yy = y + k * 48
        cv.rect(x, yy, x + W, yy + 4, C((150, 150, 150)))
        xx = x + 4
        while xx < x + W - 40:
            col = C((246, 214, 40)) if rng.random() < 0.18 else (1, 1, 1)
            cv.rect(xx, yy + 8, xx + 40, yy + 44, col, r=2)
            cv.rect(xx + 4, yy + 14, xx + 26, yy + 30, (0.1, 0.1, 0.1), r=2)
            cv.rect(xx + 4, yy + 34, xx + 36, yy + 38, (0.4, 0.4, 0.4))
            xx += 46


def misc(cv, x, y, key, rng):
    W = S
    if key == "cups":
        cv.rect(x, y, x + W, y + W, (0.95, 0.94, 0.91))
        cv.rect(x, y + W * 0.4, x + W, y + W * 0.64, C((38, 110, 80)))
        badge(cv, x + W * 0.5, y + W * 0.52, W * 0.1, (0.98, 0.98, 0.96), C((38, 110, 80)), rng)
        for k in range(6):
            cv.rect(x, y + 8 + k * 6, x + W, y + 10 + k * 6, (0.8, 0.78, 0.74))
    elif key == "lids":
        cv.rect(x, y, x + W, y + W, (0.1, 0.1, 0.11))
        for k in range(14):
            cv.rect(x, y + k * 14, x + W, y + k * 14 + 3, (0.24, 0.24, 0.25))
    elif key == "coffeebag":
        cv.rect(x, y, x + W, y + W, (0.12, 0.08, 0.06))
        cv.rect(x + 22, y + 14, x + W - 22, y + W - 10, (0.2, 0.13, 0.09), r=8)
        badge(cv, x + W / 2, y + W * 0.45, W * 0.2, (0.85, 0.72, 0.45), (0.25, 0.15, 0.1), rng)
    elif key.startswith("cardboard"):
        cv.rect(x, y, x + W, y + W, C((176, 138, 96)) if key == "cardboard" else C((158, 122, 84)))
        cv.rect(x, y + W / 2 - 5, x + W, y + W / 2 + 5, C((206, 186, 140)))
        cv.rect(x + 18, y + 120, x + 92, y + 166, (0.95, 0.95, 0.93), r=2)
        copy(cv, x + 24, y + 128, 60, 3, 9, (0.2, 0.2, 0.2), rng)
        wordmark(cv, x + W * 0.5, y + W * 0.28, W * 0.5, W * 0.1, C((90, 66, 40)), rng)
    elif key == "tickets":
        cv.rect(x, y, x + W, y + W, (0.1, 0.1, 0.1))
        tc = [(230, 40, 120), (40, 180, 220), (250, 200, 30), (60, 200, 90), (240, 90, 30), (150, 60, 200)]
        for j in range(6):
            x0, y0 = x + 6 + (j % 3) * 62, y + 6 + (j // 3) * 92
            cv.rect(x0, y0, x0 + 56, y0 + 86, C(tc[j]), r=3)
            cv.ellipse(x0 + 28, y0 + 32, 16, 16, (0.98, 0.9, 0.3))
            copy(cv, x0 + 6, y0 + 60, 44, 2, 7, (1, 1, 1), rng)
    elif key == "ice_panel":
        cv.grad(x, y, x + W, y + W, C((70, 160, 225)), C((24, 84, 170)))
        cx, cy = x + W / 2, y + W / 2
        for j in range(3):
            a = j * math.pi / 3
            dx, dy, nx, ny = math.cos(a) * 66, math.sin(a) * 66, -math.sin(a) * 6, math.cos(a) * 6
            cv.poly([(cx - dx + nx, cy - dy + ny), (cx + dx + nx, cy + dy + ny), (cx + dx - nx, cy + dy - ny), (cx - dx - nx, cy - dy - ny)], (1, 1, 1))
        cv.ellipse(cx, cy, 12, 12, (1, 1, 1))
    elif key == "propane_panel":
        cv.rect(x, y, x + W, y + W, C((30, 70, 150)))
        cv.poly([(x + 96, y + 20), (x + 138, y + 90), (x + 144, y + 135), (x + 96, y + 174), (x + 48, y + 135), (x + 56, y + 84), (x + 74, y + 104)], (1, 1, 1))
        cv.poly([(x + 96, y + 100), (x + 114, y + 132), (x + 96, y + 156), (x + 78, y + 132)], C((30, 70, 150)))


def build():
    """Draws the atlas; returns (srgb image at shipped size, cells {key: uv rect})."""
    rng = np.random.default_rng(42)
    W, H = COLS * S, ROWS * S
    cv = Canvas(W, H, (0.2, 0.2, 0.2))
    A = TX.Atlas("T_Town2_Gas_Goods", W, H)
    cell = lambda c, r: (c * S, r * S, (c + 1) * S, (r + 1) * S)
    for i in range(16):
        c, r = i % 8, i // 8
        bag(cv, c * S, r * S, i, rng)
        A.add(f"bag{i}", *cell(c, r), inset=4)
    for i in range(8):
        bottle(cv, i * S, 2 * S, i, rng)
        A.add(f"bottle{i}", *cell(i, 2), inset=4)
        can(cv, i * S, 3 * S, i, rng)
        A.add(f"can{i}", *cell(i, 3), inset=4)
        box(cv, i * S, 4 * S, i, rng)
        A.add(f"box{i}", *cell(i, 4), inset=4)
    for i in range(4):
        pouch(cv, i * S, 5 * S, i, rng)
        A.add(f"pouch{i}", *cell(i, 5), inset=4)
        jar(cv, (4 + i) * S, 5 * S, i, rng)
        A.add(f"jar{i}", *cell(4 + i, 5), inset=4)
        jug(cv, i * S, 6 * S, i, rng)
        A.add(f"jug{i}", *cell(i, 6), inset=4)
        carton(cv, (4 + i) * S, 6 * S, i, rng)
        A.add(f"carton{i}", *cell(4 + i, 6), inset=4)
        pack_grid(cv, i * S, 7 * S, i, rng)
        A.add(f"pack{i}", *cell(i, 7), inset=4)
        case(cv, (4 + i) * S, 7 * S, i, rng)
        A.add(f"case{i}", *cell(4 + i, 7), inset=4)
    for i, k in enumerate(["cups", "lids", "coffeebag", "cardboard", "cardboard2", "tickets", "ice_panel", "propane_panel"]):
        misc(cv, i * S, 8 * S, k, rng)
        A.add(k, *cell(i, 8), inset=4)
    # row 9: the shelf tag strip (one cell) and the mural (seven cells wide)
    tags(cv, 0, 9 * S, rng)
    A.add("tags", *cell(0, 9), inset=4)
    sub = TX.Canvas(7 * S, S)
    TX.mural(sub, 0, 0, 7 * S, S, np.random.default_rng(23))
    cv.px[9 * S:10 * S, S:8 * S] = sub.px
    A.add("mural", S, 9 * S, 8 * S, 10 * S, inset=4)
    # (packaging under store light, not a cartoon: a touch less saturated; a fine print grain)
    lum = cv.px.mean(axis=2, keepdims=True)
    cv.px = lum + (cv.px - lum) * 0.88
    cv.px *= (1 + (np.random.default_rng(3).random((H, W, 1)) - 0.5) * 0.04).astype(np.float32)
    return cv, A


def save():
    cv, A = build()
    f = 2
    h, w = cv.h // f, cv.w // f
    px = cv.px.reshape(h, f, w, f, 3).mean(axis=(1, 3))
    path = TX.write_png(os.path.join(TX.OUT, A.name + ".png"), TX.to_srgb(px))
    return path, A.cells
