# Audio credits

Every sound in the game is CC0 (public domain) or made for it.

## Kenney (www.kenney.nl), CC0 1.0
<http://creativecommons.org/publicdomain/zero/1.0/>; crediting is optional, we do it anyway.

- **Impact Sounds** (1.0): footsteps (wood, concrete, carpet, grass, snow), glass, wood, metal,
  plate, punch and soft impacts. <https://kenney.nl/assets/impact-sounds>
- **RPG Audio**: doors, latch, clicks, books, cloth, creaks, leather, coins.
  <https://kenney.nl/assets/rpg-audio>
- **Interface Sounds**: inventory and tablet UI (open, close, tick, select, toggle, error).
  <https://kenney.nl/assets/interface-sounds>
- **Sci-fi Sounds**: one explosion crunch, under the Grimble's smash.
  <https://kenney.nl/assets/sci-fi-sounds>

They are cut, pitched, filtered and layered by `tools/build_audio.py` (which downloads the packs
into `build/audio_src/`) into `sfx.mp3`; nothing is used as shipped.

## Made for this game (CC0)
- Synthesised in `tools/build_audio.py` (numpy): glass tinkle, sub-bass thumps, the Grimble's
  growls, snarl, breathing and sniffing, whooshes, keycard beeps, switch and flashlight clicks,
  drawer slides, the power winding down and up.
- Synthesised in the browser by `viewer/audio_synth.js`: wind, room tone, mains hum, the blinds /
  garage door motor, the TV, the gas fire, and the reverb.
