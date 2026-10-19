"""Gallery console vignette: a slim walnut console (collides) dressed with a stack of art
books and a pebble object at one end, three charcoal vessels at the other, and a low
charcoal bowl on the shelf below. Origin: floor centre, front -y; back against the wall
(depth 0.36)."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_VignetteGallery"
P = dict(name=NAME, seed=3, width=1.6, depth=0.36, height=0.8, family="charcoal", mirror=False)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rnd = random.Random(p["seed"])
    col, root, k = K.new_asset(n)
    w, d, h = p["width"], p["depth"], p["height"]
    K.gallery_console(k, K.T(), w, d, h)
    sx = -1 if p["mirror"] else 1
    z, _ = K.book_stack(k, K.T(sx * -0.4, -0.01, h, rz=sx * 6), rnd, n=3, w=(0.3, 0.36), d=(0.27, 0.31),
                        t=(0.03, 0.05))
    K.sculpture(k, K.T(sx * -0.4, -0.02, h + z, rz=20), "pebbles", mat="charcoal")
    K.ceramic_trio(k, K.T(sx * 0.4, 0.02, h), rnd, p["family"], scale=1.4)
    K.bowl(k, K.T(sx * 0.25, 0.0, 0.175), "charcoal", r=0.13, h=0.06, foot=0.5)
    return K.done(k, n, col, root, collide=("walnut",))
