"""A short bench (ph_bench, 2.4 m): the cold room, under its slit window."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ph_bench  # noqa: E402

importlib.reload(ph_bench)

NAME = "PHBenchShort"
P = dict(name=NAME, length=2.4)


def build(**overrides):
    return ph_bench.build(**{**P, **overrides})


if __name__ == "__main__":
    root, parts = build()
    print(root.name, len(parts))
