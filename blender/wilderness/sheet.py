"""Contact sheet of a terrain's masks and previews (numpy only): build/wilderness/<name>/sheet.png.
  $PY blender/wilderness/sheet.py <name>"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import terrain  # noqa: E402

FONT = {  # 3x5 bitmap glyphs for labels
    "a": "010101111101101", "b": "110101110101110", "c": "011100100100011", "d": "110101101101110",
    "e": "111100110100111", "f": "111100110100100", "g": "011100101101011", "h": "101101111101101",
    "i": "111010010010111", "k": "101101110101101", "l": "100100100100111", "m": "101111111101101",
    "n": "110101101101101", "o": "010101101101010", "p": "110101110100100", "r": "110101110101101",
    "s": "011100010001110", "t": "111010010010010", "u": "101101101101111", "v": "101101101101010",
    "w": "101101111111101", "x": "101101010101101", "y": "101101010010010", "_": "000000000000111",
    "1": "010110010010111", "6": "011100110101010", " ": "000000000000000", "-": "000000111000000",
}


def text(img, s, x, y, scale=3):
    for k, ch in enumerate(s.lower()):
        g = FONT.get(ch, FONT[" "])
        for r in range(5):
            for c in range(3):
                if g[r * 3 + c] == "1":
                    y0, x0 = y + r * scale, x + (k * 4 + c) * scale
                    img[y0:y0 + scale, x0:x0 + scale] = (255, 255, 255)


def main(name, tile=340):
    d = os.path.join(terrain.OUT_ROOT, name)
    names = ["relief", "albedo", "bake", "masks/slope", "masks/altitude", "masks/flow", "masks/wetness",
             "masks/curvature", "masks/aspect", "masks/path", "masks/rivers", "masks/lakes", "masks/sediment"]
    tiles = []
    for nm in names:
        a = terrain.read_png_fast(os.path.join(d, nm + ".png"))
        h, w = a.shape[:2]
        st = max(1, h // tile)
        a = a[::st, ::st][:tile, :tile]
        if a.ndim == 2:
            a = np.dstack([a] * 3)
        a = a[..., :3].copy()
        bar = np.zeros((22, a.shape[1], 3), np.uint8)
        text(bar, nm.split("/")[-1], 4, 4)
        tiles.append(np.vstack([bar, a]))
    cols = 5
    rows = -(-len(tiles) // cols)
    th, tw = tiles[0].shape[:2]
    sheet = np.zeros((rows * (th + 4), cols * (tw + 4), 3), np.uint8)
    for k, t in enumerate(tiles):
        r, c = divmod(k, cols)
        sheet[r * (th + 4):r * (th + 4) + t.shape[0], c * (tw + 4):c * (tw + 4) + t.shape[1]] = t
    terrain.write_png(os.path.join(d, "sheet.png"), sheet, flip=False)
    print(os.path.join(d, "sheet.png"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "demo")
