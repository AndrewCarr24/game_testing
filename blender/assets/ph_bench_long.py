"""The bath hall's long bench (ph_bench, 6.4 m), along the glass's south bays and the walkway."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ph_bench  # noqa: E402

importlib.reload(ph_bench)

NAME = "PHBenchLong"
P = dict(name=NAME, length=6.4)


def build(**overrides):
    return ph_bench.build(**{**P, **overrides})


if __name__ == "__main__":
    root, parts = build()
    print(root.name, len(parts))
