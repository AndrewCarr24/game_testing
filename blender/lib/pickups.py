"""Loose things the player can lift: the pick-up rule, in one place for every decor kit.

THE RULE. Something a player would expect to lift is a throwable pickup, everywhere it appears:
a hand-sized object (no side over MAX_SIZE) standing or lying free on a table, counter, desk,
nightstand, console, shelf top or tray: vases, bowls and dishes, plates, cups and mugs, drinking
glasses, carafes and decanters, bottles, candles, books and magazines lying flat (each book of a
stack), notebooks, small ornaments (a sphere on a block, a ring, balanced stones), boxes, fruit
and bread, soap and dispensers, reading glasses, a laptop. Glass and ceramic shatter where they
land (a noise the Grimble hears); everything else (books, wood, metal, stone, fruit) thuds and
lands whole, to be picked up again. Identical kinds share one item id, so they stack in the
inventory ("Book x3").

Fixed, part of the furniture (and they read that way): books standing in rows (shelves,
bookcases, between bookends), anything inside built-ins, display cases and cabinets, trays and
boards (their contents lift), plants, flowers and branches (with the vase they stand in),
textiles (throws, towels, cushions, slippers), floor pieces (floor vases, baskets, crates),
sculpture on plinths, anything bigger than MAX_SIZE, and anything with fixed geometry resting
on it (it would leave that floating). Pickups resting on other pickups are fine: the engine
only lets the player take the one underneath once the ones on it are gone.

Mechanics. A decor kit gathers each vignette into one mesh per material (an accumulator: a
dict of material key -> geometry). `wrap(kit_module, store, items, fixed)` replaces the kit's
item functions (vase, book, candle...) with wrappers that divert the geometry they add into a
bucket of its own; the kit's finish() calls `emit()`, which turns every bucket into an empty
`<Asset>_<Kind>NN` carrying the `pickup` interact (origin at the item's base, turned like the
item) with one `_NoCollide` mesh per material under it. Nested item calls (the plate under a
cup) join the outer item; inside a `fixed` function (a shelved row of books) nothing becomes a
pickup. The engine draws resting pickups inside their room's batch (viewer/batching.js), so a
vignette split into twenty pickups still costs what it did as one mesh per material.
"""
import math

from mathutils import Matrix, Vector

RANGE = 1.5             # m from the eye to the item's nearest edge: across a table to its middle
MAX_SIZE = 0.6          # m: a bigger thing (floor vase, big basket) is furniture, not a pickup
COVER_MARGIN = 0.006    # m: fixed geometry this far inside an item's footprint and above its base covers it

# kind -> (name, behaviour). behaviour "vessel": the material decides (glass / ceramic shatter,
# others thud) and names it ("Glass bowl", "Bronze bowl"); else (shatter, noise) fixed per kind.
KINDS = {
    "vase": ("Vase", "vessel"),
    "bowl": ("Bowl", "vessel"),
    "dish": ("Dish", "vessel"),
    "plate": ("Plate", "vessel"),
    "cup": ("Cup", "vessel"),
    "mug": ("Mug", "vessel"),
    "crock": ("Utensil crock", "vessel"),
    "glass": ("Glass", (True, 0.8)),
    "wine_glass": ("Wine glass", (True, 0.8)),
    "carafe": ("Carafe", (True, 1.0)),
    "decanter": ("Decanter", (True, 1.0)),
    "wine_bottle": ("Wine bottle", (True, 1.0)),          # = ix_wine_bottle's item
    "bottle": ("Bottle", (True, 1.0)),
    "perfume": ("Perfume bottle", (True, 0.7)),
    "soap_pump": ("Soap dispenser", (True, 0.8)),
    "spray_bottle": ("Spray bottle", (False, 0.4)),
    "candle": ("Candle", (False, 0.3)),
    "book": ("Book", (False, 0.6)),                        # = ix_book's item
    "magazine": ("Magazine", (False, 0.3)),
    "notebook": ("Notebook", (False, 0.4)),
    "laptop": ("Laptop", (False, 0.9)),
    "ornament": ("Ornament", (False, 0.8)),
    "box": ("Box", (False, 0.5)),
    "spectacles": ("Reading glasses", (False, 0.2)),
    "lemon": ("Lemon", (False, 0.2)),
    "lime": ("Lime", (False, 0.2)),
    "apple": ("Apple", (False, 0.2)),
    "grapes": ("Grapes", (False, 0.1)),
    "bread": ("Bread", (False, 0.2)),
    "knife": ("Knife", (False, 0.5)),
    "mortar": ("Mortar", (False, 1.0)),
    "pepper_mill": ("Pepper mill", (False, 0.5)),
    "salt_cellar": ("Salt cellar", (False, 0.5)),
    "brush": ("Brush", (False, 0.2)),
    "soap": ("Soap", (False, 0.1)),
}

# material name keyword -> (class, adjective); first match wins
MATERIAL_CLASSES = [
    ("Glass", "glass", "Glass"), ("Crystal", "glass", "Glass"),
    ("Ceramic", "ceramic", None), ("Stoneware", "ceramic", None), ("Porcelain", "ceramic", None),
    ("Glaze", "ceramic", None), ("Terracotta", "ceramic", None), ("Planter", "ceramic", None),
    ("Clay", "ceramic", None), ("Charcoal", "ceramic", None),
    ("Marble", "stone", "Stone"), ("Limestone", "stone", "Stone"), ("Stone", "stone", "Stone"),
    ("Bronze", "metal", "Bronze"), ("Brass", "metal", "Brass"), ("Copper", "metal", "Copper"),
    ("Steel", "metal", "Steel"), ("Aluminium", "metal", "Metal"), ("Metal", "metal", "Metal"),
    ("Walnut", "wood", "Wooden"), ("Oak", "wood", "Wooden"), ("Wood", "wood", "Wooden"),
    ("Teak", "wood", "Wooden"), ("Wicker", "wood", "Wicker"), ("Lacquer", "metal", "Enamel"),
]


def material_class(mat):
    name = mat.name if mat is not None else ""
    for key, cls, adj in MATERIAL_CLASSES:
        if key.lower() in name.lower():
            return cls, adj
    return "ceramic", None          # (a vessel in a plain colour: glazed ceramic)


def define(kind, mat):
    """The pickup interact for an item of `kind` whose body is material `mat`."""
    name, how = KINDS[kind]
    item = kind
    if how == "vessel":
        cls, adj = material_class(mat)
        shatter = cls in ("glass", "ceramic")
        noise = {"glass": 1.0, "ceramic": 0.9, "stone": 1.0, "metal": 0.8, "wood": 0.5}.get(cls, 0.6)
        if cls == "glass":
            # a glass vase is vase.py's item (the vases already in the house)
            item, name = ("vase", "Glass vase") if kind == "vase" else (f"glass_{kind}", f"Glass {name.lower()}")
        elif adj and cls != "ceramic":
            item, name = f"{adj.lower()}_{kind}", f"{adj} {name.lower()}"
        elif kind == "vase":
            item = "ceramic_vase"          # ("vase" is the glass one)
    else:
        shatter, noise = how
    return {"type": "pickup", "item": item, "name": name, "prompt": f"Take {name.lower()}", "range": RANGE,
            "throwable": True, "noise": noise, "shatter": shatter}


# ------------------------------------------------------------------ wrapping a kit

def _state(acc):
    st = acc.__dict__.get("_pickups")
    if st is None:
        st = acc.__dict__["_pickups"] = {"depth": 0, "fixed": 0, "items": []}
    return st


def _matrix(args, kwargs):
    for x in list(args) + list(kwargs.values()):
        if isinstance(x, Matrix) and len(x) == 4:
            return x
    return None


def _item(fn, kind, store):
    def wrapper(acc, *args, **kwargs):
        st = _state(acc)
        k = kind(args, kwargs) if callable(kind) else kind
        if st["depth"] or st["fixed"] or k is None:
            return fn(acc, *args, **kwargs)
        M = _matrix(args, kwargs)
        saved = getattr(acc, store)
        setattr(acc, store, {})
        st["depth"] += 1
        try:
            out = fn(acc, *args, **kwargs)
        finally:
            st["depth"] -= 1
            bucket = getattr(acc, store)
            setattr(acc, store, saved)
        st["items"].append({"kind": k, "M": M.copy() if M is not None else None, "bucket": bucket})
        return out
    wrapper.__name__, wrapper.__doc__ = fn.__name__, fn.__doc__
    return wrapper


def _fixed(fn):
    def wrapper(acc, *args, **kwargs):
        st = _state(acc)
        st["fixed"] += 1
        try:
            return fn(acc, *args, **kwargs)
        finally:
            st["fixed"] -= 1
    wrapper.__name__, wrapper.__doc__ = fn.__name__, fn.__doc__
    return wrapper


def wrap(module, store, items, fixed=()):
    """Make `module`'s item functions emit pickups. `store`: the accumulator attribute holding
    {material key: geometry}; `items`: {function name: kind, or fn(args, kwargs) -> kind | None};
    `fixed`: functions whose geometry never becomes a pickup (a shelved row of books)."""
    for fname, kind in items.items():
        setattr(module, fname, _item(getattr(module, fname), kind, store))
    for fname in fixed:
        setattr(module, fname, _fixed(getattr(module, fname)))


# ------------------------------------------------------------------ emitting the items

def _label(key):
    return key.split("@")[0].replace("M_", "").replace("_", " ").title().replace(" ", "")


def emit(acc, name, col, root, fixed_bms, bm_of, mat_of):
    """Turn every pickup bucket gathered on `acc` into an item under `root`. `fixed_bms`: the
    bmeshes of the vignette's fixed geometry (in asset space), for the 'covered' test;
    `bm_of(value)` -> the bmesh of a store value; `mat_of(key)` -> its material.
    Returns the new mesh objects."""
    from lib import common

    st = _state(acc)
    items, st["items"] = st["items"], []
    fixed_pts = [v.co.copy() for bm in fixed_bms for v in bm.verts]
    boxes = []
    for it in items:
        pts = [v.co for v in (vv for value in it["bucket"].values() for vv in bm_of(value).verts)]
        if not pts:
            boxes.append(None)
            continue
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        boxes.append((lo, hi))
    keep = [b is not None and max(b[1] - b[0]) <= MAX_SIZE for b in boxes]
    big = [i for i, b in enumerate(boxes) if b is not None and not keep[i]]

    def covered(i, pts):
        lo, hi = boxes[i]
        m = COVER_MARGIN
        return any(lo.x + m < p.x < hi.x - m and lo.y + m < p.y < hi.y - m and lo.z + m < p.z < hi.z + 0.05
                   for p in pts)

    # an item under fixed geometry (or under an item that had to stay fixed) stays fixed too
    changed = True
    while changed:
        changed = False
        extra = [v.co for j, it in enumerate(items) if not keep[j] and boxes[j]
                 for value in it["bucket"].values() for v in bm_of(value).verts]
        for i in range(len(items)):
            if keep[i] and (covered(i, fixed_pts) or covered(i, extra)):
                keep[i] = False
                changed = True

    fixed = [f"{items[i]['kind']} ({'too big' if i in big else 'under fixed things'})"
             for i in range(len(items)) if boxes[i] is not None and not keep[i]]
    if items:
        print(f"PICKUPS {name}: {sum(keep)} pickups" + (f", kept fixed: {', '.join(fixed)}" if fixed else ""))
    out, counts = [], {}
    for i, it in enumerate(items):
        if boxes[i] is None:
            for value in it["bucket"].values():
                bm_of(value).free()
            continue
        lo, hi = boxes[i]
        kind = it["kind"]
        counts[kind] = counts.get(kind, 0) + 1
        label = f"{''.join(w.title() for w in kind.split('_'))}{counts[kind]:02d}"
        if not keep[i]:
            # fixed after all: plain static meshes (the room batch merges them like the rest)
            for key, value in it["bucket"].items():
                out.append(common.mesh_object(f"{name}_{label}_{_label(key)}_NoCollide", bm_of(value), col,
                                              mat_of(key), root, smooth=False))
            continue
        # the item's frame: its base centre (under the authored origin if there is one), turned
        # like the item about z only, so it lands the way it was placed
        M = it["M"]
        if M is not None:
            x, y = M.translation.x, M.translation.y
            ax = M.to_3x3() @ Vector((1, 0, 0))
            yaw = math.atan2(ax.y, ax.x) if abs(ax.x) + abs(ax.y) > 1e-6 else 0.0
            if not (lo.x - 0.02 <= x <= hi.x + 0.02 and lo.y - 0.02 <= y <= hi.y + 0.02):
                x, y = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
        else:
            x, y, yaw = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2, 0.0
        E = Matrix.Translation((x, y, lo.z)) @ Matrix.Rotation(yaw, 4, "Z")
        inv = E.inverted()
        node = common.empty(f"{name}_{label}", col)
        node.parent = root
        node.matrix_basis = E
        node.empty_display_size = 0.05
        body = None
        for key, value in it["bucket"].items():
            bm = bm_of(value)
            if not bm.faces:
                bm.free()
                continue
            bm.transform(inv)
            m = mat_of(key)
            body = body or m
            out.append(common.mesh_object(f"{name}_{label}_{_label(key)}_NoCollide", bm, col, m, node, smooth=False))
        node["interact"] = define(kind, body)
    return out


def make(name, col, root, kind, parts, base, yaw=0.0, uv_tile=None, **extra):
    """A hand-made asset's loose thing as a pickup: an empty `name` at `base` (the item's base
    centre, in the asset's space) carrying the interact, with one `_NoCollide` mesh per
    (label, bmesh in asset space, material) of `parts`. The first part's material is the body
    (it names the item and, thrown, its shards); `extra` overrides interact fields (a `range` to
    reach across a wide table). Returns the empty."""
    from lib import common

    E = Matrix.Translation(base) @ Matrix.Rotation(yaw, 4, "Z")
    node = common.empty(name, col)
    node.parent = root
    node.matrix_basis = E
    node.empty_display_size = 0.05
    inv = E.inverted()
    for label, bm, mat in parts:
        bm.transform(inv)
        ob = common.mesh_object(f"{name}_{label}_NoCollide", bm, col, mat, node)
        if uv_tile:
            common.box_uv(ob, uv_tile)
    node["interact"] = {**define(kind, parts[0][2]), **extra}
    return node


def adopt(name, col, root, kind, objects, base, yaw=0.0):
    """Like make(), for objects already built under `root` (at the asset's origin): an empty
    `name` at `base` takes them over (keeping where they are) and carries the interact; the
    first object's material is the body. Returns the empty."""
    from lib import common

    E = Matrix.Translation(base) @ Matrix.Rotation(yaw, 4, "Z")
    node = common.empty(name, col)
    node.parent = root
    node.matrix_basis = E
    node.empty_display_size = 0.05
    inv = E.inverted()
    for ob in objects:
        basis = ob.matrix_basis.copy()            # (in root space: the parts hang off the root)
        ob.parent = node
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.matrix_basis = inv @ basis
    body = objects[0].active_material if objects and objects[0].type == "MESH" else None
    node["interact"] = define(kind, body)
    return node
