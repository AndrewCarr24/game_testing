"""Run an asset generator inside Blender.

From the Blender Python console (or via MCP):
    exec(open("/Users/andrewcarr/Documents/projects/game_testing/blender/run.py").read())
with ASSET set beforehand, e.g. ASSET = "lounge_chair".
"""
import os
import runpy

ROOT = "/Users/andrewcarr/Documents/projects/game_testing/blender"
runpy.run_path(os.path.join(ROOT, "assets", f"{ASSET}.py"), run_name="__main__")  # noqa: F821
