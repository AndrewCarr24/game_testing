# Grimble source sculpts (AI-generated from concept/grimble/front.png, 2026-10-19)

- `trellis2_gen2.glb`: Microsoft TRELLIS.2 (Hugging Face Space `microsoft/TRELLIS.2`), image-to-3D,
  seed 0, resolution 1024, extracted at 100k faces with a 2048 texture. The base for the Grimble.
- `hunyuan21_shape.glb`: Tencent Hunyuan3D 2.1 (`tencent/Hunyuan3D-2.1`), shape only, seed 1234,
  octree 256 (324k faces, untextured). Kept as a shape reference.
- `trellis2_input.png`: the background-removed image TRELLIS was given.

The game asset is built from these by `blender/assets/grimble.py`; regenerate only on purpose.
