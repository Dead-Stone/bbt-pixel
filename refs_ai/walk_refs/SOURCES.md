# Walk-cycle references (downloaded 2026-10-31, links checked the same day)

Reference only: none of these files is used by the game. The analysis is in `tools/ai_import/walk_refs_measure.py`
and the comparison sheet is in `tools/ai_import/walk_refs_compare.py` -> `env/renders/walk/walk_refs_compare.png`.

## Committed (clear, permissive license)

| File | Title / author | Source URL | License |
|---|---|---|---|
| `lpc_male_walkcycle.png`, `lpc_female_walkcycle.png` | LPC Base Assets, "Character templates" walkcycle by Stephen Challener (Redshrike). 4 dirs (N, W, S, E) x 9 cols (1 stand + 8 walk), 64x64 cells | https://opengameart.org/content/liberated-pixel-cup-lpc-base-assets-sprites-map-tiles (zip: https://opengameart.org/sites/default/files/lpc_base_assets.zip) | CC-BY-SA 3.0 (https://creativecommons.org/licenses/by-sa/3.0/) / GPL 3.0; Redshrike's parts are also OGA-BY 3.0 (https://static.opengameart.org/OGA-BY-3.0.txt). Credits: `LPC_CREDITS.TXT` |
| `bumblebee_8dir_walk_blue.png` (+ `bumblebee_License_CC0.txt`) | 8 Direction Walk Cycle by Ordinary Bumblebee. Blue colour; the 8 per-direction sheets stacked as rows S, SW, W, NW, N, NE, E, SE x 8 frames, 32x48 cells | https://ordinary-bumblebee.itch.io/8-direction-walk-cycle | CC0 1.0 (https://creativecommons.org/publicdomain/zero/1.0/) |
| `chrome_district_VX-0001_ortho22.png` | CHROME DISTRICT by booliebuilds, character VX-0001 "ortho" view (22 deg pitch). Rows S, SW, W, NW, N, NE, E, SE x 6 frames, 56x84 cells; demo plays at 10 fps. Procedural 3D-to-sprite (counter-example: duplicated frames, no bob) | https://booliebuilds.itch.io/chrome-district | CC0 1.0 (LICENSE in the zip) |
| `puny_character_base.png` | Puny Characters by Shade, Character-Base sheet (8 dirs, 32x32 chibi) | https://opengameart.org/content/puny-characters | CC0 |
| `basic_isometric_human.png` | Basic isometric human animation by ToxSickProductions.com | https://opengameart.org/content/basic-isometric-human-animation | CC0 |
| `hormelz_boxer_walkforward_dir1.gif` | Free 8-Directional Melee Character by Hormelz, "Walk Forward" dir1 (24 frames @ 40 ms). Not used for the comparison: the export mixes view angles within a cycle and it's a boxer's guard walk | https://hormelz.itch.io/8-directional-melee-character | CC0 |

## Local only (gitignored: `refs_ai/walk_refs/local/`, no stated license)

| File | Title / author | Source URL | License |
|---|---|---|---|
| `local/s11_Walk.gif` | "Walk Cycle" pixel-art tutorial by Pedro Medeiros (saint11). 12 frames @ 100 ms; contact / down / down+ / prepare-passing / passing / up | https://saint11.art/img/pixel-tutorials/Walk.gif (index https://saint11.art/blog/pixel-art-tutorials/, post https://www.patreon.com/saint11/posts/simple-walk-14234033) | Free to view, no license stated. Do not commit |
| `local/s11_TopDownWalkCycle.gif` | "Top Down Walk Cycle" by Pedro Medeiros (saint11) | https://saint11.art/img/pixel-tutorials/TopDownWalkCycle.gif (post https://www.patreon.com/saint11/posts/top-down-walk-21353953) | Free to view, no license stated. Do not commit |

## Principles only (copyrighted, nothing downloaded)

- Richard Williams, *The Animator's Survival Kit*: contact / down / passing / up; a normal walk is "on 12s", i.e. 2 steps/s. https://en.wikipedia.org/wiki/The_Animator%27s_Survival_Kit
- Isometric Hero and Heroine by Clint Bellanger (Flare), CC-BY 3.0: 8-direction 128x128 iso cells, but the cycle is a run, not a walk, so it wasn't downloaded. https://opengameart.org/content/isometric-hero-and-heroine
- Universal LPC Spritesheet Character Generator, for previewing LPC walks: https://liberatedpixelcup.github.io/Universal-LPC-Spritesheet-Character-Generator/
