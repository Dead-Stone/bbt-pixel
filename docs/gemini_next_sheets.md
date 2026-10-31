# Next AI sheets to generate (after the cast turnaround)

The ChatGPT turnaround (`refs_ai/chatgpt_penny_1.png`: 7 characters x 5 directions S/SW/W/NW/N, magenta
background) is now the art source for **standing + idle** (`characters/<cid>/ai/`, built by
`python3 tools/ai_import/build.py`). Everything that moves is still the old rig. Warping the stills into a walk
was tried and rejected (`harness/renders/aiimport/walk_warp_rejected.png`: scissor legs in S, torn legs in
profile), so real drawn frames are needed.

## What to generate, in priority order

| # | Sheet | Per character | Layout | Why |
|---|-------|---------------|--------|-----|
| 1 | **walk** | 8 frames x 5 dirs (S, SW, W, NW, N) = 40 figures | 5 rows (dirs) x 8 cols (frames) | biggest visible style break: characters switch to the rig look the moment they walk |
| 2 | sit (on couch / stool) | 1 frame x 5 dirs | 1 row x 5 | the second most common pose in the sim |
| 3 | work (typing / writing at a board) | 4 frames x 5 dirs | 5 rows x 4 cols | AIT physics + Amber Slice scenes |
| 4 | talk / gesture | 4 frames x 3 dirs (S, SW, W) | 3 rows x 4 cols | emotes |

**One image per character per sheet** (7 walk images first). Do not ask for all 7 characters in one walk
image: at 8x5 the figures get too small and the model drifts off-model.

E / SE / NE are made by mirroring W / SW / NW in `tools/ai_import/build.py`, so never generate them.

## Rules that make the import work (same as the turnaround)

- Attach `refs_ai/chatgpt_penny_1.png` (the turnaround) to every request; the walk must match it exactly.
- Solid flat magenta `#FF00FF` background, no floor, no shadow, no gradient, no text or labels.
- A strict grid with even gaps; every figure the same scale; feet on the same baseline in each row.
- Full body, nothing cropped, figures not touching each other.
- Same clothes, hair, glasses and proportions as the turnaround.

## Ready-to-paste prompt (walk; swap in the character name and outfit line)

```
Using the attached character turnaround as the exact reference, create a pixel-art WALK CYCLE sprite sheet
for ONE character: PENNY (blonde wavy hair past the shoulders, pink tank top, blue jeans, brown ankle boots).

Layout: a strict grid of 5 rows x 8 columns on a solid flat magenta (#FF00FF) background.
- Row 1: facing the viewer (S)
- Row 2: facing down-left, three-quarter front (SW)
- Row 3: facing left, side profile (W)
- Row 4: facing up-left, three-quarter back (NW)
- Row 5: facing away from the viewer (N)
Columns 1-8 are one looping walk cycle: contact, down, passing, up, contact (other foot), down, passing, up.
Frame 1 and frame 5 are mirror-opposite leg poses; the arms swing opposite to the legs; the head bobs at most
a tiny amount; the feet stay on one shared baseline per row.

Match the attached turnaround exactly: the same art style, pixel density, palette, outline, face, hair,
clothing and body proportions, and the same figure height as in the turnaround. Every figure must be full
body, the same scale, evenly spaced, not overlapping and not cropped. No floor, no shadows, no text, no
labels, no border, no background other than flat magenta.
```

Outfit lines for the other six (from the turnaround):
- SHELDON: tall and thin, short neat brown hair, red superhero-logo t-shirt over a long-sleeve dark red shirt, khaki trousers, brown shoes
- LEONARD: curly dark brown hair, black thick-rimmed glasses, green hoodie over a graphic t-shirt, brown trousers
- HOWARD: dark bowl-cut hair, high-collar turtleneck with a belt buckle, tight coloured trousers
- RAJ: neat black hair, sweater vest over a collared shirt, dark trousers
- BERNADETTE: short (much shorter than the others), blonde wavy hair, glasses, cardigan over a blouse, skirt
- AMY: long straight brown hair, glasses, cardigan over a blouse, long skirt, flat shoes

(Check each against the attached image before sending and correct it if the turnaround shows something else.)

## Importing the result

Save it as `refs_ai/walk_<cid>.png`. The slicer (`tools/ai_import/slice.py`) already auto-detects grid
bands, so it needs only a `rows=5, cols=8` variant plus a `walk_<dir>` tag writer in `build.py` (the same
downscale, palette and audit path as the stills; use the character's existing 28-colour palette so the colours
match the idle). Then the viewer can take `walk_<dir>` from the AI sheet the same way it takes `idle_<dir>`.
