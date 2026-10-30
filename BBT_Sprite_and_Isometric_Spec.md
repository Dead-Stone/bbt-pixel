# The Big Bang Theory — "Living Sitcom" Pixel World
## Art & Asset Production Specification · v1.0

**Project:** personal, non-commercial fan project by Mohan Moganti
**Doc date:** 2026-10-29 · **Status:** production-ready baseline (v1). Change it by bumping the version and logging the change in §12.
**Scope:** 7 autonomous AI agent characters (Sheldon, Leonard, Penny, Howard, Raj, Bernadette, Amy) walking around a 2:1 isometric HD pixel world: Apartment 4A, the 4th-floor landing, the stairwell, the lobby with the broken elevator, Apartment 4B, the Caltech cafeteria, the Comic Center, and the Cheesecake Factory.

> **IP and likeness rule (read first).** This is a private fan project. Do **not** trace, paste, or ship copyrighted stills, set photos, logos, or actor likenesses. Use reference photos only to study shapes, layouts, and colors, then draw everything from scratch. Real trademarks (superhero logos, console and game brands, the restaurant wordmark) are replaced with **original designs in the same spirit**, for example "a red tee with an original yellow atom-bolt emblem" or "a generic game console". AI prompts in this doc describe *costumes and props*, never actors. Keep the repo private.

---

## Table of contents
1. Global art direction
2. Character sprite system (128×128)
3. Per-character spec cards (×7)
4. Isometric environment system
5. Location kits and prioritized item lists
6. Depth sorting, anchors and interaction hooks (data schema)
7. Agent integration (action→animation, emotes, idle behaviors, targets)
8. Export formats and engine integration (Aseprite / TexturePacker / Phaser / Godot)
9. AI image-generation prompts
10. Consistency checklist and "perfect sheet" QA checklist
11. Production order and folder structure
12. Decisions log and open questions
13. Reference sources

**Files that ship with this doc:**
- `palettes/bbt_palette_swatches.png`: visual swatch sheet of every hex in §1.4 and §3
- `palettes/bbt_master.gpl` and `palettes/bbt_<character>.gpl`: Aseprite/GIMP palettes. Each character palette includes the shared ink/neutral ramp.
- `palettes/bbt_palettes.json`: machine-readable palettes for tooling and QA
- `templates/frame_guide_128.png` (+ `_preview4x`): 128×128 frame showing the pivot, the 4 px safe margin, the shadow ellipse, and a head-top line per character
- `templates/iso_floor_tile_128x64.png`, `templates/iso_wall_backright_full_64x224.png`, `templates/iso_wall_backright_cutaway_64x48.png`
- `tools/make_palettes.py`, `tools/make_templates.py`: regenerate all of the above

---

## 1. Global art direction

### 1.1 The one-sentence brief
*"A multi-camera sitcom seen through a cozy HD pixel-art diorama."* The frame should read like the show's proscenium sets. That means warm, even "studio" lighting, one dense lived-in nerd-clutter focal wall per room, and clear staging lanes where characters stand and talk to each other, roughly toward the camera. It is **not** a dark RPG and **not** flat vector art.

### 1.2 Pixel density and scale (the "one grid" rule)
| Parameter | Value | Notes |
|---|---|---|
| Native pixel grid | 1 art pixel = 1 texel. Characters, items, tiles, and UI icons all share the **same** density. | Never mix 2× pixels into 1× scenes. Never rotate sprites or scale them by non-integer amounts at runtime. |
| Character frame | **128 × 128 px** | The body itself is 78–100 px tall (§2.1). |
| Floor tile | **128 × 64 px** diamond (2:1) | 1 tile = **1.0 m × 1.0 m** of world floor. |
| Vertical scale | **64 px per metre** of world height | A 3.0 m wall is 192 px. A 0.45 m seat height is 29 px. Characters use stylized heights (§2.1). |
| Display scaling | Integer only: 2× at 1080p (960×540 native viewport), 3× at 1440p/4K | Nearest-neighbour filtering, mipmaps off, pixel snap on. |
| Camera | Snaps to whole native pixels. Zoom only in integer steps, with a fade between them. | This prevents shimmer on 1 px outlines. |

The 4A living room and kitchen (about 9×8 tiles) is roughly 1088 px wide, so it fits the native viewport at 3× or gets a slow camera pan at 2×.

### 1.3 Outline style
- **Silhouette outline:** 1 px of `ink #1a1420` on characters, and on items where they meet the floor or background. Never use pure black `#000`.
- **Selective outline ("sel-out"):** on lit silhouette edges (the top of heads, shoulders, and the top and upper-left of props), replace the ink with the *darkest shade of the local material*, such as `hair_sh` or `tee_xsh`. This stops sprites from looking like stickers.
- **Interior lines:** never ink. Use the next-darker ramp color of the material. For example, a fold in a red tee uses `tee_sh`.
- **Eyes and glasses:** eyes are 2×2 or 1×2 px of `ink_2`, with an optional single `paper` catch-light on the S, SW, and SE views only. Glasses frames are 1 px in the character's frame color.
- **No anti-aliasing against transparency.** Manual AA (one intermediate color) is allowed only on *interior* curves, such as the jaw against the neck or hair against the face. That keeps sprites crisp over any floor.
- **No pillow shading** (darkening all around the outline). Shade by light direction only.

### 1.4 Palette rules
1. **Master palette:** 60 colors (table below). Environment art uses only master colors. The location sub-palettes are part of the master.
2. **Character palettes:** at most 24 colors each, made of the 8 shared `Ink & neutrals` plus up to 16 character colors (§3). The total number of colors on screen is unbounded, but every sprite must validate against its own `.gpl`. QA can check this automatically with `bbt_palettes.json`.
3. **Ramps are hue-shifted.** Shadows lean violet/blue and highlights lean warm yellow. Never darken by adding black or lighten by adding white.
4. **Ramp length:** 3 values (highlight / base / shadow), plus an optional 4th "occlusion" value for creases and contact areas. Characters use 3 values. Large props may use 4.
5. **Saturation hierarchy:** characters > interactive props > background dressing > walls and floors. Walls and floors stay desaturated and mid-value. This is the sitcom rule: the actors are the brightest thing on stage.
6. **Key color per character** (the readability rule). Each character owns one hue that no one else wears as their primary color:
   - Sheldon: **red tee with a yellow emblem**
   - Leonard: **blue-grey hoodie**
   - Howard: **magenta pants and a white dickey**
   - Raj: **brown argyle vest**
   - Penny: **pink and denim**
   - Bernadette: **navy floral dress with a pink cardigan**
   - Amy: **purple striped cardigan with camel**

   Penny's pink (`#ef7fa8`) and Bernadette's cardigan pink (`#f28db2`) are close, but they separate by context: Bernadette's pink always sits against navy, and the two silhouettes are very different. Check them together in the lineup (§10).

**Master palette** (in `palettes/bbt_master.gpl`, shown in `bbt_palette_swatches.png`):

| Group | Colors (name · hex) |
|---|---|
| Ink & neutrals | ink `#1a1420` · ink_2 `#2b2233` · shadow_violet `#3d3047` · grey_dk `#5a5866` · grey `#8c8f94` · grey_lt `#c9ced6` · paper `#f4f1ea` · white_hi `#fffdf6` |
| Skin ramps | skin_a1 `#f5d6c0` · skin_a2 `#e3b394` · skin_a3 `#b9826a` · skin_a4 `#8a5a48` · skin_b1 `#c88a60` · skin_b2 `#b47a52` · skin_b3 `#93603f` · skin_b4 `#6e452c` |
| Hair | blonde_1 `#f2d98e` · blonde_2 `#d9b45e` · blonde_3 `#a8823c` · brown_1 `#7a5a3e` · brown_2 `#5a3f2b` · brown_3 `#3a281c` · black_1 `#2e2626` · black_2 `#1e1a1a` |
| Wood & leather (4A) | wood_hi `#c99a5e` · wood `#a8743f` · wood_dk `#7a4e2c` · wood_xdk `#5a3820` · leather_hi `#9a6a42` · leather `#7a4d2f` · leather_dk `#5c3a24` · leather_xdk `#3e2617` |
| Walls & floors | wall_4a_hi `#e6d8b8` · wall_4a `#d8c7a3` · wall_4a_dk `#b9a57f` · stair_wall `#cdb98f` · stair_wall_dk `#a8946c` · tile_green `#6f8f5e` · tile_green_dk `#53704a` · floor_hall `#8a6a4a` |
| Accents & signage | tape_yellow `#f2c230` · tape_yellow_dk `#c99a1f` · marker_blue `#2f5fb3` · marker_red `#c8463d` · marker_green `#3f8a4f` · screen_glow `#9fd8ff` · lamp_warm `#ffd88a` · plant_green `#5f9a48` |
| Location sub-palettes | **4B:** turquoise `#3fb8b0` · orange `#f08a3c` · purple `#8a5cb0` · lime `#a6cf4a` — **Restaurant:** amber `#d79a4a` · booth red `#9b2f2f` — **Comic Center (post-fire):** blue `#3f6fb5` · red `#c94040` · yellow `#f2c94c`, plus the greys — **Caltech cafeteria:** cream `#e9e1cc` · teal `#4f9a9a` · steel `#a7adb5` |

**Where the hexes come from.** All of these are eyeballed, pixel-art-friendly readings of the references, not colors picked from photos.
- **4A:** the "big, brown, leather sleeper sofa", wood cabinetry, neutral walls, and green kitchen tiling (RoomSketcher).
- **4B:** turquoise, orange, purple, and lime. The set decorator, Ann Shea, couldn't paint the walls, so she used colorful furniture and accessories (Good Housekeeping via Yahoo).
- **Comic Center:** after the fire it got multiple new wall colors (Looper). Grey/blue/yellow/red is a reasonable reading that still needs checking against a still.
- **Broken elevator:** yellow caution tape (WB Studio Tour coverage).

### 1.5 Lighting
- **Environment key light:** from screen upper-left, the window light from the 4A alcove side. On every iso box, the **top face is lightest, the left (SW-facing) face is mid, and the right (SE-facing) face is darkest.** Use this for every prop, wall, and tile in every location, so props can move between rooms.
- **Character lighting:** **top-front and symmetric**, from directly above and slightly toward the camera. Shadows fall under the chin, under the hair fringe, under the arms, and on the lower legs.
  - *Why:* symmetric lighting makes horizontal mirroring safe for shading (§2.2). The small mismatch with the environment's left-side key light is hidden by the contact shadow. This is standard practice in iso games.
- **Practical lights are colored glow overlays,** drawn as separate additive or soft-light sprites and never baked into the base art: TV and monitor glow (`screen_glow`), lamps and restaurant pendants (`lamp_warm`), the fridge interior. The time-of-day system can then dim a room without repainting it.
- **Time of day:** one global color-grade LUT per time (day / evening / night). The base art is painted in neutral "studio day" light, because a sitcom set is always lit.
- **Contact shadows:**
  - Characters: a separate sprite, `fx_shadow_char.png`, a 40×10 ellipse in `ink` at 35% opacity with multiply blending, drawn under the pivot.
  - Items: 2–4 px of `shadow_violet` baked into the item sprite, hugging its base.

### 1.6 Shading and dithering
- **Cel shading** with 3 values per material and hard edges. Only large curved forms (couch arms, heads) may use one soft step, a 1 px AA band.
- **Characters: no dithering at all.** Dither patterns shimmer when sprites animate.
- **Environment:** a 2×2 ordered checker dither is allowed **only** for large static gradients, such as light pools under lamps, TV glow falling off across the floor, and window light shafts. It may only mix two *adjacent* ramp colors, and the dithered band is at most 6 px wide. Never use noise or random dithering.
- **Texture by suggestion, not noise.**
  - Wood grain: a 1 px `wood_dk` streak every 8–12 px.
  - Leather: one highlight crease per cushion.
  - Carpet: no texture, or a 1 px pattern at tile seams only.
- **Specular highlights:** at most one cluster per object (a glasses glint, buckle shine, screen sheen, or fridge handle).

### 1.7 Isometric 2:1 projection (the maths)
- Pixel-art dimetric "2:1": every diagonal edge steps 2 px across for 1 px down. The 128×64 diamond tile has perfect 2:1 staircase edges with no 1 px jogs (see `templates/iso_floor_tile_128x64.png`).
- **World axes:** +X points to screen lower-right (SE), +Y points to screen lower-left (SW), and Z points up.
- **World → screen** (top vertex of tile (x, y), at height z in metres):
  `sx = (x − y) · 64`
  `sy = (x + y) · 32 − z · 64`
- **Screen → world** (for picking, at z = 0):
  `x = (sx/64 + sy/32) / 2`
  `y = (sy/32 − sx/64) / 2`
- **Facing names are screen-space.** "SE" means facing toward the screen's lower-right (world +X). "S" means facing straight at the camera (world +X+Y).
- **Walls** run only along the two world axes. "Back-left" walls follow the tile's top→left edge, and "back-right" walls follow its top→right edge. Camera-side walls are drawn as 16 px **cutaway stubs**, the sitcom's missing fourth wall.

---

## 2. Character sprite system (128 × 128)

### 2.1 Frame, pivot, and proportions
- **Frame:** 128 × 128 px, transparent background, RGBA8 PNG.
- **Pivot / anchor:** **(64, 116)** (normalized **(0.5, 0.90625)**). This is the point on the floor between the feet. It aligns to the world position, and it is the y-sort key.
- **Safe area:** a 4 px margin on every side, so nothing is drawn at x < 4, x > 123, or y < 4. The 12 px below the pivot hold the shadow and any foot overshoot in jump or fall frames.
- **Shadow ellipse** (guide only; it ships as a separate sprite): 40 × 10 px, centred on the pivot.
- **Style: "chunky-real."** A head-to-body ratio of about **1 : 3.25**. That is stylized enough for big readable faces and real enough that it reads as the TV ensemble, not chibi.
  - Head: 28 × 28 px (Bernadette 26 × 26).
  - Shoulder width: 30–36 px.
  - Hands: 5 × 6 px blocks with a 1 px thumb notch.
  - Feet: 10 × 5 px.

| Character | Body height (px, feet → crown) | Head-top y | Silhouette notes |
|---|---|---|---|
| Sheldon | **100** | 16 | Tallest and lankiest. Narrow shoulders (30 px), long thin legs, long-sleeve undershirt under a tee, slightly stiff posture. |
| Raj | **90** | 26 | Medium build, upright, thick swept-back black hair. |
| Penny | **88** | 28 | Athletic and relaxed, long blonde hair past the shoulders, side part. |
| Leonard | **86** | 30 | Stocky-slim, slight slouch, thick black glasses frames, dark curly hair. |
| Howard | **86** | 30 | Slim, very skinny tight pants, Beatles-style bowl cut, big belt buckle. |
| Amy | **86** | 30 | Slightly stiff, shoulder-length straight brown hair with a side part, glasses, below-knee skirt. |
| Bernadette | **78** | 38 | Shortest. Petite, wavy blonde-ginger shoulder hair, round glasses, A-line dress. |

These stylized heights preserve the ensemble's *relative* line-up, with Sheldon the tallest and Bernadette very short. They are not literal heights in metres.

**Construction grid** (draw these as guide layers in `frame_guide_128.png`):
- Crown line, eye line at 45% of head height, chin line.
- Shoulder line at head height + 2 px below the chin.
- Waist line at 50% of body height, crotch at 46%, knee at 24% (all measured from the pivot).
- Rough box, then silhouette, then flats, then shading.

### 2.2 Directions and mirroring rules
**8 directions** in this order everywhere (rows, file suffixes, engine enums): **S, SW, W, NW, N, NE, E, SE**. Index 0–7, counter-clockwise from the camera-facing S.

| Painted (unique) | Derived by mirroring | Patch layer required |
|---|---|---|
| **S, SW, W, NW, N** (5 directions) | NE = flip(NW), E = flip(W), SE = flip(SW) | Yes: `decal` layer, repainted per mirrored direction |

**Mirror rules:**
1. Mirror with a **horizontal flip around x = 64** so the pivot stays put. Never offset after flipping.
2. Character shading is symmetric (§1.5), so it flips safely. Environment props are **never** flipped (lighting would break). Use rotations instead (§4.4).
3. **Asymmetric details live on a separate `decal` layer** that is hidden before the flip and repainted on the mirrored directions. Required decals:
   - **Sheldon:** the tee emblem. It must never read backwards. On mirrored views, redraw it so its orientation matches the original.
   - **Howard:** the alien pin on his *left* collar and the belt buckle motif.
   - **Penny:** the hair side part (left side).
   - **Amy:** hair clips and the side part.
   - **Leonard:** the hoodie zip pull.
   - **Raj:** none, beyond letting the argyle pattern flip.
   - **Bernadette:** the brooch or necklace pendant.
   - Any **text** on a prop (a book cover, the "Penny" door sign, a laptop sticker).
4. **Handedness:** everyone is right-handed in the painted views. When a held prop (a phone, a mug, a whiteboard marker) mirrors into the left hand, that is accepted for E, NE, and SE. Exceptions: "write on whiteboard" and "Halo controller" are drawn natively for all 4 diagonals (see §2.3, "4D").
5. **Runtime:** `flipX` only for NE/E/SE. In the engine, never flip the shadow sprite or any FX.

**4-direction subset ("4D")** for animations where the 8-direction cost is not justified: **SW, NW, NE, SE**. These are the only directions that line up with iso furniture, which faces along the world axes. So seated poses, "use object", and most interaction animations are 4D. For a 4D animation, the agent snaps to the closest diagonal.

### 2.3 Animation list (master)
Frame counts are per direction. **fps is the playback rate.** Per-frame durations in Aseprite override it where marked (for example a hold on the last frame). A "loop" column of 1 means it loops.

**A. Core locomotion and idle (all characters, 8D)**
| Animation tag | Frames | fps | Loop | Notes |
|---|---|---|---|---|
| `idle` | 4 | 4 | 1 | Breath: chest and shoulders move 1 px on frames 2–3. Blink every ~3 s is a separate overlay; see `blink`. |
| `blink` | 2 | — | 0 | Eyes closed on frame 1 (80 ms), open on frame 2. Mixed in randomly by the runtime. |
| `walk` | 8 | 10 | 1 | Contact, down, pass, up × 2. Head bobs 1–2 px. Arms swing in opposition. Sheldon's stride is longer and stiffer. |
| `run` | 6 | 12 | 1 | Lean of 4–6 px. Used for "Penny!" knock-runs, chases, and comic-store rush. |
| `turn` | 2 | 12 | 0 | Transition between adjacent directions. Optional, in phase P2. |
| `talk` | 4 | 8 | 1 | Mouth frames and small hand gestures. The runtime picks a random start frame. |
| `listen` | 4 | 4 | 1 | Head tilt and nods. |
| `laugh` | 6 | 10 | 1 | Shoulders shake. Character-specific on top of this: Raj covers his mouth, Penny throws her head back. |
| `sad` | 4 | 4 | 1 | Slumped shoulders. |
| `angry` | 4 | 8 | 1 | Arms tense or crossed. |
| `shrug` | 5 | 10 | 0 | Hold the last frame for 300 ms. |
| `point` | 4 | 10 | 0 | Points with the right hand. |
| `wave` | 6 | 10 | 0 | |
| `facepalm` | 6 | 10 | 0 | |
| `phone` | 4 | 4 | 1 | Phone held in the right hand, thumb taps. |

**B. Furniture and object use (4D unless noted)**
| Animation tag | Frames | fps | Loop | Notes |
|---|---|---|---|---|
| `sit_down` / `stand_up` | 4 / 4 | 10 | 0 | Pivot travels 0 px. The seat aligns the pivot to the seat anchor (§6). |
| `sit_idle` | 4 | 4 | 1 | |
| `sit_talk` | 4 | 8 | 1 | |
| `sit_eat` | 6 | 8 | 1 | Takeout carton and chopsticks (4A), or fork (restaurant/cafeteria). |
| `sit_game` | 4 | 8 | 1 | Controller in both hands. Drawn natively per diagonal, no mirroring. |
| `sit_laptop` | 4 | 6 | 1 | Typing. Screen glow overlay. |
| `stand_whiteboard` | 8 | 8 | 1 | Writes equations, natively 4D. Pairs with the `whiteboard` decal-swap state. |
| `stand_counter` | 4 | 6 | 1 | Kitchen counter or bar, hands on the surface. |
| `cook` | 6 | 8 | 1 | Stirring. |
| `pour_drink` | 6 | 8 | 0 | Penny's wine glass and waitress pour. |
| `carry_box` | 8 | 10 | 1 | 8D, a walk variant with arms forward. Used for the stairs gag and moving furniture. |
| `climb_stairs_up` / `_down` | 8 / 8 | 10 | 1 | Only along the stairwell's 2 world axes (SW↔NE / NW↔SE). Pivot y steps per frame to match stair risers (32 px rise per tile). |
| `knock` | 4 | 8 | 0 | Generic door knock. All characters, 4D. |
| `door_open` / `door_close` | 4 / 4 | 10 | 0 | Syncs with the door prop's own animation. |
| `pickup` / `putdown` | 4 / 4 | 10 | 0 | |
| `hug` | 6 | 8 | 0 | Two-agent sync (§7.5). Sheldon has a stiff variant. |

**C. Signature emotes (character-specific)** — full list in each §3 card. The template is:
| Character | Signature | Dirs | Frames | fps | Notes |
|---|---|---|---|---|---|
| Sheldon | `knock_knock_penny` | 4D (NW/NE at doors) | **16** (3 × "knock-knock-knock" + 3 × name-call holds; see card) | 8 | Loops ×3 then `idle`. Speech bubble sync: "Penny." ×3 |

### 2.4 Sheet grid layout
- **One sheet per character** for core + signature animations, plus a second sheet for a large signature set if it overflows the 4096 px texture limit.
- **Grid:** cells are 128 × 128 with **0 spacing and 0 margin** on the source sheet. Padding happens at pack time (§8).
- **12 columns** (1536 px wide), so the longest standard animation (8 frames) fits on one row with room to spare. A 16-frame signature wraps to 2 rows.
- **Rows:** grouped by animation, then by direction in the order S, SW, W, NW, N, NE, E, SE. 4D animations use SW, NW, NE, SE only.
- **Source of truth is the `.aseprite` file**, with one tag per animation+direction (for example `walk_SW`), a `body` layer, a `decal` layer, a `prop` layer, and an `fx` layer (glow, sweat drops). Mirrored directions *exist in the source file* as flipped and patched frames, because that keeps engines that do not support `flipX` happy. When the engine does support flipX, the exported mirrored frames are simply unused.

### 2.5 Naming convention
```
chr_<id>_<anim>_<dir>_<frame:02>.png      # loose-frame export, e.g. chr_sheldon_walk_SW_03.png
chr_<id>.aseprite                         # source
chr_<id>.png + chr_<id>.json              # packed atlas + Aseprite/TexturePacker JSON
Aseprite tag names: <anim>_<dir>          # e.g. sit_idle_NE, knock_knock_penny_NW
```
- `<id>` is one of `sheldon`, `leonard`, `penny`, `howard`, `raj`, `bernadette`, `amy`.
- `<dir>` is one of S, SW, W, NW, N, NE, E, SE.
- Lowercase snake_case, no spaces, ASCII only.

### 2.6 Sprite-drawing workflow (per character)
1. Load `palettes/bbt_<id>.gpl` in Aseprite. Set the canvas to 128×128 and import `frame_guide_128.png` as a locked, low-opacity reference layer.
2. Draw the **S idle frame 1** as the hero frame and sign off on it with the lineup check (§10).
3. Derive SW, then W, NW, N by rotating the volumes. The head-top line and the pivot are fixed.
4. Animate `idle` and `walk` S first, then the other painted directions.
5. Mirror into NE, E, SE and repaint the decals.
6. Work through the remaining animations in production-order priority (§11).
7. Run the palette and pivot QA script and the in-engine lineup check.

---

## 3. Per-character spec cards

Each card has the same fields:
- **Palette** in hex (the shared ink/neutrals are always included).
- **Silhouette and wardrobe** for the canonical "default look", plus optional outfit swaps.
- **Decals** (the mirror patches from §2.2).
- **Movement personality:** timing tweaks to the shared animations.
- **Signature emotes**, with frame and fps detail.
- **Home anchors:** the places in the world this agent gravitates to.

Wardrobe is summarized from costume and style guides (§13). All logos are **original**.

### 3.1 Sheldon (`sheldon`)
- **Palette:**
  | Name | Hex |
  |---|---|
  | skin (hi / base / sh) | `#f5d6c0` / `#e3b394` / `#b9826a` |
  | hair (brown, hi / base / sh) | `#7a5a3e` / `#5a3f2b` / `#3a281c` |
  | tee red (hi / base / sh) | `#e85a50` / `#d23a32` / `#a12a26` |
  | emblem yellow | `#f5c542` |
  | undershirt navy | `#3b4f7a` (sh `#2b3a5c`) |
  | khaki pants | `#b9a27a` (sh `#8f7a56`) |
  | shoes | `#5a3f2b` |
- **Silhouette and wardrobe:** short-sleeve superhero-style graphic tee over a long-sleeve striped or plain undershirt, slim khaki or brown trousers, brown shoes, short neat side-parted hair. The emblem is an original *yellow atom-bolt in a circle*, 8 × 8 px on the chest.
  - Outfit swaps: a green tee with a "lantern ring" in an original design, a blue tee with a "sound wave" emblem, a "Flash-style" lightning tee, **a messenger bag strap** (decal) for the Caltech commute.
- **Decals:** the emblem (on every mirrored view, redraw it *not* reversed) and the bag strap.
- **Movement:** stiff, upright, quick precise steps. The walk is 8 frames at 10 fps with only a 1 px head bob. Arms swing less, with hands near his sides.
- **Signature emotes:**
  | Tag | Dirs | Frames | fps | Detail |
  |---|---|---|---|---|
  | `knock_knock_penny` | 4D | 16 | 8 | Frames 1–3: knock-knock-knock (knuckle forward 3 px, 1 frame hold each). Frame 4: hold, head turned slightly (bubble "Penny."). Frames 5–8 and 9–12: repeat. Frames 13–16: return to neutral. The runtime holds frames 4, 8, and 12 at 375 ms. |
  | `bazinga` | 8D | 8 | 10 | Arms flung forward and up, a wide grin, and a 2-frame lean. Bubble "Bazinga!" in bold. |
  | `spot_claim` | 4D | 6 | 8 | Points at the sofa cushion, then sits. Plays before sitting in his seat0. |
  | `soft_kitty` | 4D | 8 | 6 | Sways gently while "singing" (music-note emote). Paired with `sad` on the target agent. |
  | `vulcan_salute` | 8D | 4 | 8 | The hand-sign pose, held. |
  | `whiteboard_eureka` | 4D | 6 | 10 | Pauses with a finger raised, then scribbles fast. |
- **Home anchors:** 4A sofa seat0 (configurable, see §12), the 4A whiteboard, his desk, the Caltech cafeteria table, 4B's door (signature knock).

### 3.2 Leonard (`leonard`)
- **Palette:**
  | Name | Hex |
  |---|---|
  | skin | `#f5d6c0` / `#e3b394` / `#b9826a` |
  | hair (dark brown) | `#3a281c` / `#2e2626` (curly highlights `#5a3f2b`) |
  | glasses frame | `#1e1a1a` |
  | hoodie blue-grey (hi / base / sh) | `#8e9db1` / `#6f7f96` / `#525f73` |
  | tee green | `#4f8a4a` |
  | corduroy pants | `#7a5236` (sh `#5a3a24`) |
  | sneakers | `#c9ced6` / `#5a5866` |
- **Silhouette and wardrobe:** zip-up hoodie over a graphic tee, corduroy trousers, sneakers, thick black-framed glasses, short dark curly hair.
  - Outfit swaps: a brown jacket, a plaid flannel shirt.
- **Decals:** the hoodie zip pull and the tee graphic (an original "pixel retro game" motif).
- **Movement:** an average stride with a slight slouch. Hands are in his pockets in `idle` variant B.
- **Signature emotes:**
  | Tag | Dirs | Frames | fps | Detail |
  |---|---|---|---|---|
  | `inhaler` | 4D | 6 | 8 | Takes a puff (1 px prop) after running up the stairs. |
  | `glasses_push` | 8D | 4 | 10 | Pushes his glasses up his nose with one finger. |
  | `sigh_explain` | 8D | 6 | 8 | Palms up, sighing. Paired with Sheldon's `talk`. |
  | `cello` | 4D | 8 | 6 | Optional (P3). Bows a cello prop. |
- **Home anchors:** the 4A sofa, the 4A desk with laptop, the Caltech lab table, the 4B door (dating arc).

### 3.3 Penny (`penny`)
- **Palette:**
  | Name | Hex |
  |---|---|
  | skin | `#f5d6c0` / `#e3b394` / `#b9826a` |
  | hair blonde | `#f2d98e` / `#d9b45e` / `#a8823c` |
  | top pink (hi / base / sh) | `#f7a6c3` / `#ef7fa8` / `#c75a83` |
  | denim | `#6f93c2` / `#4f74a8` / `#3a5680` |
  | boots | `#7a4d2f` / `#5c3a24` |
  | waitress uniform vest | `#f2c94c` (sh `#c99a1f`) |
  | apron (green, generic) | `#2f5a3a` |
- **Silhouette and wardrobe:** a fitted tee or tank in pink or bright colors, skinny jeans or short shorts, boots, long blonde hair with a side part.
  - Outfit swaps: a waitress uniform (a generic restaurant uniform: yellow vest, green apron) and a sales-rep blazer (later seasons).
- **Decals:** the side part of her hair and the uniform name tag.
- **Movement:** loose and confident, with hip sway in `walk` (1 px pelvis shift) and big expressive arms in `talk`.
- **Signature emotes:**
  | Tag | Dirs | Frames | fps | Detail |
  |---|---|---|---|---|
  | `door_answer_annoyed` | 4D | 6 | 8 | Swings the door open, hand on hip. Reacts to Sheldon's `knock_knock_penny`. |
  | `wine_sip` | 4D | 6 | 6 | Big glass of red wine, `sit_` and `stand_` variants. |
  | `waitress_carry` | 8D | 8 | 10 | Walk variant carrying a tray. |
  | `holy_crap` | 8D | 4 | 10 | Hands on head, eyes wide. |
  | `hair_flip` | 8D | 6 | 10 | |
- **Home anchors:** the 4B sofa, the 4B door, the restaurant bar and tables (as waitress), the 4A sofa armrest.

### 3.4 Howard (`howard`)
- **Palette:**
  | Name | Hex |
  |---|---|
  | skin | `#f5d6c0` / `#e3b394` / `#b9826a` |
  | hair (dark brown) | `#3a281c` / `#2e2626` |
  | dickey / turtleneck collar white | `#f4f1ea` (sh `#c9ced6`) |
  | shirt blue | `#5c98e0` / `#3b7fd1` / `#2b5f9e` |
  | skinny pants magenta | `#d455a4` / `#b8338a` / `#8a2668` |
  | belt red | `#c8362f` |
  | belt buckle | `#c9ced6` / `#fffdf6` (glint) |
  | alien pin | `#7bd44a` |
  | boots | `#5a3f2b` |
- **Silhouette and wardrobe:** a mock-turtleneck **dickey** under a bright colored shirt, skin-tight colored pants, a big novelty belt buckle, a Beatles-style bowl cut, an alien pin on his left collar.
  - Outfit swaps: an orange-shirt variant, the NASA flight-suit look as a generic "astronaut jumpsuit" (later, P3).
- **Decals:** the alien pin (left collar) and the buckle motif (an original "UFO" or "joystick").
- **Movement:** a quick, slightly swaggering walk with his chest forward. Small "eyebrow waggle" frames in `talk`.
- **Signature emotes:**
  | Tag | Dirs | Frames | fps | Detail |
  |---|---|---|---|---|
  | `eyebrow_waggle` | 8D | 4 | 10 | |
  | `magic_trick` | 4D | 8 | 10 | A card or coin trick. Small sparkle FX. |
  | `mom_yell` | 8D | 6 | 8 | Cups his hands and yells upward (bubble with a waveform). An off-screen voice responds. |
  | `astronaut_salute` | 8D | 4 | 8 | P3. |
- **Home anchors:** the 4A chair or floor seat by the coffee table, the Caltech lab, the Comic Center counter.

### 3.5 Raj (`raj`)
- **Palette:**
  | Name | Hex |
  |---|---|
  | skin | `#c88a60` / `#b47a52` / `#93603f` |
  | hair black | `#2e2626` / `#1e1a1a` |
  | shirt cream | `#f4ecd8` / `#eee3c8` / `#c9bc9a` |
  | vest brown | `#9a6a42` / `#7a5233` / `#5a3a24` |
  | argyle accent | `#b08a4a` |
  | trousers olive | `#8a8f5a` / `#6f7442` / `#545832` |
  | jacket (optional) | `#5a3f2b` |
  | shoes | `#3a281c` |
- **Silhouette and wardrobe:** layered and preppy. A collared shirt under an **argyle sweater vest**, chinos, sometimes a jacket on top, thick swept-back black hair.
- **Decals:** none required (the argyle pattern can flip).
- **Movement:** graceful and expressive. Hands often fold in `idle` variant B.
- **Signature emotes:**
  | Tag | Dirs | Frames | fps | Detail |
  |---|---|---|---|---|
  | `mute_whisper` | 4D | 6 | 8 | Leans to whisper into Howard's ear. Two-agent sync. Shows up when an agent of a different gender is in range (an early-season mechanic, toggle in settings). |
  | `cinnamon_dog` | 4D | 6 | 6 | P3. Cradles a small dog prop. |
  | `drink_courage` | 4D | 6 | 6 | Sips (generic drink), then a sparkle emote and he becomes talkative. |
  | `astronomy_point` | 8D | 4 | 8 | Points up with a star emote. |
- **Home anchors:** the 4A armchair, the Caltech cafeteria, the Comic Center browsing aisle.

### 3.6 Bernadette (`bernadette`)
- **Palette:**
  | Name | Hex |
  |---|---|
  | skin | `#f5d6c0` / `#e3b394` / `#b9826a` |
  | hair strawberry-blonde | `#e0b562` / `#c99a45` / `#9a7230` |
  | dress navy | `#3e4f80` / `#2c3a66` / `#1f2a4a` |
  | floral accent | `#f4f1ea`, `#f2c94c` |
  | cardigan pink | `#f7aac6` / `#f28db2` / `#c96a8e` |
  | glasses frame | `#6b4a33` |
  | shoes (Mary-Jane) | `#2b2233` |
- **Silhouette and wardrobe:** petite. A fitted A-line or floral dress, a short cardigan, Peter Pan collars, round glasses, wavy shoulder-length hair. Later, a lab coat over the dress (pharmaceutical microbiologist).
- **Decals:** the brooch or pendant.
- **Movement:** small quick steps (the walk at 12 fps instead of 10).
- **Signature emotes:**
  | Tag | Dirs | Frames | fps | Detail |
  |---|---|---|---|---|
  | `sweet_to_scary` | 8D | 6 | 10 | Smile, then a scowl (2-frame hold), with a "loud voice" bubble. |
  | `lab_coat_pose` | 8D | 4 | 8 | Coat-on outfit swap. |
- **Home anchors:** the 4B sofa, the restaurant (as waitress, early arc), Howard's side.

### 3.7 Amy (`amy`)
- **Palette:**
  | Name | Hex |
  |---|---|
  | skin | `#f5d6c0` / `#e3b394` / `#b9826a` |
  | hair brown | `#7a5a3e` / `#5a3f2b` / `#3a281c` |
  | cardigan purple | `#8a66a3` / `#6e4a87` / `#523568` |
  | cardigan stripe | `#c9b8d6` |
  | blouse burgundy | `#7a2a3a` |
  | skirt camel | `#cfa672` / `#b58a55` / `#8a663a` |
  | tights | `#5a3d2e` |
  | glasses frame | `#3a281c` |
  | shoes (flat) | `#3a281c` |
- **Silhouette and wardrobe:** layered and conservative. A cardigan over a blouse (often a collared one), a below-knee pleated or A-line skirt, thick tights, flat shoes, glasses, straight shoulder-length hair with a side part and clips.
- **Decals:** the hair clips and the side part.
- **Movement:** upright and deliberate, a little stiff, which mirrors Sheldon's walk. Hand on chest in `talk`.
- **Signature emotes:**
  | Tag | Dirs | Frames | fps | Detail |
  |---|---|---|---|---|
  | `bestie_hug` | 4D | 6 | 8 | A two-agent hug with Penny. Amy holds on longer (an extra 2-frame hold). |
  | `harp` | 4D | 8 | 6 | P3. Plays a harp prop. |
  | `neuro_lecture` | 8D | 6 | 8 | Lecture pose with a brain emote. |
  | `tiara_dream` | 8D | 4 | 6 | A dreamy-sigh emote. |
- **Home anchors:** next to Sheldon on the 4A sofa, the 4B sofa, the Caltech lab.

---

## 4. Isometric environment system

### 4.1 Tiles
| Asset | Size (px) | Pivot | Notes |
|---|---|---|---|
| Floor tile | 128 × 64 | top vertex (64, 0) in tilemap. Atlas export also has a centre pivot (64, 32). | Diamond with clean 2:1 edges. Hardwood, carpet, kitchen tile, linoleum, restaurant floor, comic-store carpet. |
| Floor tile with thickness (edge pieces) | 128 × 80 | (64, 0) | Shows 16 px of floor slab. Used only where the cutaway reveals the edge. |
| Floor decal | 128 × 64 | (64, 32) | Rugs, spills, light pools. Draw as overlays, without y-sort. |
| Full wall segment (back-left / back-right) | **64 × 224** | bottom vertex of the base edge | 192 px tall (3.0 m) + the 32 px diagonal of the base. One segment per tile edge. |
| Cutaway wall stub | 64 × 48 | same | 16 px tall. Used on camera-side walls (S/E edges). Shows the wall cap and an ink line. |
| Wall cap / corner post | 16 × 224 | bottom | Hides seams at corners. |
| Door frame / opening | 64 × 224 | same | A door is a separate animated item. |

**Wall rules:**
- Back walls (along the room's N edges) are **full height**. Camera-side walls are always **cutaway**.
- When an agent is behind a full wall piece (only in corridors), that wall fades to 35% alpha in a soft 1-tile radius around the agent.
- Walls are lit by the global key light (§1.5): back-left walls are lit (mid value) and back-right walls are shaded (darker value).

### 4.2 Wall heights and vertical rhythm
- Floor to ceiling: 3.0 m = **192 px** in every room. Door height 2.1 m = 134 px. Door width 1 tile.
- Window sill 0.9 m (58 px), window head 2.2 m (141 px).
- Kitchen counter top 0.9 m (58 px). Upper cabinets 1.5–2.3 m.
- Sofa seat 0.45 m (29 px), sofa back 0.85 m (54 px). Coffee table 0.45 m. Dining table and desk 0.75 m (48 px).
- Bar stool seat 0.75 m. Stair riser 0.5 m per tile (32 px, matching the iso staircase). Stair tread is 1 tile deep.

### 4.3 Item sizes
- Item sprites are drawn in **iso projection with the same 2:1 edges** and lit by the environment key light (§1.5).
- An item canvas is `footprint width × (footprint height + world height)`:
  `canvas_w = (fx + fy) · 64`
  `canvas_h = (fx + fy) · 32 + h_m · 64`
  (both rounded up to multiples of 2 px). Example: a 3×1 sofa that is 0.85 m tall is 256 × (128 + 54) = **256 × 182**.
- **Pivot** = the **bottom vertex of the footprint**: the screen point of world corner (x0+fx, y0+fy) at z = 0, written in item-canvas coordinates. This is the item's y-sort point (§6). For small items (1×1), the pivot is (64, canvas_h − 0).

### 4.4 Rotation classes (8 directions for items)
Items are **never mirrored** (that would break their lighting). Each item is in one rotation class:
| Class | Views drawn | Used for |
|---|---|---|
| **R8** | 8 (S, SW, W, NW, N, NE, E, SE) | **Free-standing small/medium props that can be placed at any angle**: chairs, the office chair, stools, the armchair, floor lamp, a person-sized cardboard cutout, the telescope, the Halo controller stand, plants. The 4 axis-aligned views (SW, NW, NE, SE) are required. The 4 cardinal views (S, W, N, E) show the item turned 45° in the room. |
| **R4** | 4 (SW, NW, NE, SE) | Anything aligned to walls or the grid: sofa, desks, tables, counters, shelves, bookcases, whiteboards, beds, booths, display racks. |
| **R2** | 2 (SW-and-NE share one, NW-and-SE share one) | Symmetric items: a round table, the arcade-cabinet back, the rug, the tile floor, a stool. |
| **R1** | 1 | Rotationally symmetric: plant pot, trash can, round pouf. |

- In-engine, "8 directions for the location" means: **the camera is fixed**, and each *item* can be placed in up to 8 orientations within its rotation class.
- A *camera-rotation* mode (rotating the whole room 90°) is out of scope for v1. It would require R4 for every item and a second set of wall views (logged in §12).

### 4.5 Long items and multi-tile y-sorting
- An item whose footprint is longer than 1 tile on **both** axes (sofas are 3×1, beds 2×2, counters N×1) is **sliced per tile column** at export into vertical strips, each sorted by its own tile's depth. This avoids classic iso sort errors, such as an agent walking "through" a long sofa.
- The slicing script uses the footprint metadata (§6) and exports `item_<id>_<rot>_s<i>.png`. The engine reassembles the strips with offsets.
- The exception is flat floor items (rugs, mats), which don't need slicing.

### 4.6 Occlusion: silhouette x-ray
When an agent is hidden behind a tall item (more than 30% overlap), draw the agent's silhouette in their **key color at 40% alpha** on top of the item. Either a second sprite pass with a flat-color shader, or (in Phaser) a second sprite with `setTintFill`. Viewers never lose track of an agent, and you never have to cut tall props.

---

## 5. Location kits and prioritized item lists

**Priority legend:**
- **P0:** needed for the first playable 4A + hallway loop.
- **P1:** core locations and the first recognizable show beats.
- **P2:** richer life and gags.
- **P3:** nice-to-have.

Footprints are in tiles (x × y). Height (h) is in metres. The rotation class is from §4.4. **Hooks** are interaction points (§6/§7).

### 5.1 Apartment 4A (`loc_4a`) — living room, kitchen, dining, alcove, plus a corridor to the bedrooms
**Layout** (about 10 × 8 tiles; read from RoomSketcher and floor-plan sources):
- The **front door** opens into the living room from the 4th-floor landing.
- Living room: the **3-seat brown leather couch** faces the TV, with the **coffee table** in front.
- An **armchair** and a desk area.
- Open **kitchen** with an island or breakfast bar and stools, backed by green tile.
- A window in the dining/desk alcove with a desk, the "telescope" corner, **whiteboards**, and shelves of collectibles and figurines.
- A corridor leads off to the bedrooms and the bathroom.

| Pri | Item id | Footprint | h (m) | Rot | Hooks (id · type · capacity) | Notes |
|---|---|---|---|---|---|---|
| P0 | `4a_couch` | 3×1 | 0.85 | R4 | `seat0..seat2` · sit · 1 each; `armrest_r` · perch · 1 | Brown leather (leather ramp). **seat0 = "Sheldon's spot"** (configurable). Sliced. |
| P0 | `4a_coffee_table` | 2×1 | 0.45 | R4 | `surface` · place_item; `floor_seat_n` · sit_floor | Takeout cartons are dressing. |
| P0 | `4a_tv_stand` + `tv_flat` | 2×1 | 1.2 | R4 | `watch` (target for seats); `game_console` · use | Screen glow overlay. Generic console. |
| P0 | `4a_armchair` | 1×1 | 0.9 | R8 | `seat` · sit · 1 | Raj and Howard's usual seats. |
| P0 | `4a_front_door` | 1×0 (wall) | 2.1 | R4 | `door` · open/close · 1; `knock_spot_outside`, `knock_spot_inside` | Animated: 4 frames open. Door number "4A" as a decal. |
| P0 | `4a_desk_laptop` | 2×1 | 0.75 | R4 | `chair0` · sit+laptop | Leonard's or Sheldon's desk by the window. |
| P0 | `4a_kitchen_counter` | N×1 modular (1, 2, corner) | 0.9 | R4 | `stand_counter` · 1 per tile; `cook` (stove tile) | Green tile backsplash (`tile_green`). |
| P0 | `4a_kitchen_island` | 2×1 | 0.9 | R4 | `stool0..stool2` · sit | Paired with `4a_stool` (R2). |
| P0 | `4a_fridge` | 1×1 | 1.8 | R4 | `use` (open, grab drink) | 2 frames: closed / open, with an interior glow overlay. |
| P1 | `4a_whiteboard` | 1×0 (wall) or 1×1 free-standing | 1.9 | R4 | `write` · 1 | **Decal-swap states:** `blank`, `equations_a`, `equations_b`, `string_theory`, `roommate_agreement_vote`. Original scribbles only. |
| P1 | `4a_dining_table_chairs` | 2×2 | 0.75 | R4 | `seat0..seat3` | |
| P1 | `4a_bookcase_collectibles` | 2×1 | 2.0 | R4 | `browse` · 1 | Original figurines and "comic" spines. |
| P1 | `4a_telescope` | 1×1 | 1.6 | R8 | `look` · 1 | By the window. |
| P1 | `4a_window_alcove` | wall piece | — | R4 | `look_out` | Light shaft dither decal. |
| P1 | `4a_flag_banner` | wall decal | — | R4 | — | Hung behind the couch. An original heraldic flag design (see §12 open question). |
| P1 | `4a_floor_lamp` | 1×1 | 1.7 | R8 | — | `lamp_warm` glow. |
| P1 | `4a_rug` | 3×2 | 0 | R2 | — | Under the couch and coffee table. Floor decal. |
| P2 | `4a_takeout_set` | 0.5×0.5 | 0.15 | R1 | `pickup` | Generic Chinese takeout cartons and Thai containers. Spawned on Thursday/"takeout night" schedule events. |
| P2 | `4a_dna_model` | 1×1 | 1.4 | R8 | `admire` | Double helix sculpture. |
| P2 | `4a_cardboard_cutout` | 1×1 | 1.8 | R8 | `pose_with` | An original "sci-fi hero" cutout. |
| P2 | `4a_bedroom_doors` (corridor) | wall | 2.1 | R4 | `enter_bedroom_sheldon`, `enter_bedroom_leonard` | Teleport targets to off-screen rooms in v1. |
| P2 | `4a_desk_chair_office` | 1×1 | 1.0 | R8 | `seat` | |
| P3 | `4a_bathroom_door`, `4a_coat_rack`, `4a_mail_bowl`, `4a_wall_art_set`, `4a_plants` | — | — | various | — | Dressing. |

### 5.2 4th-floor landing, stairwell, and lobby (`loc_hall4`, `loc_stair`, `loc_lobby`)
- **Landing:** a small square between 4A and 4B, which face each other across it. The stair flight wraps down from here.
- **Stairwell:** the show's famously walked stairs. Every episode-style walk-and-talk happens here, so it needs its **own camera framing**.
  - Each flight is 4–5 tiles along one world axis, with a landing (2×2) at each half floor.
  - Floor "decks" stack vertically using the z offset, so the camera tracks up and down.
  - Walls are `stair_wall` (warm beige) with a handrail.
- **Lobby:** the elevator door with caution tape (out of order), mailboxes, and the main entrance.

| Pri | Item id | Footprint | h (m) | Rot | Hooks | Notes |
|---|---|---|---|---|---|---|
| P0 | `stair_flight` | 1×4 (or 4×1) | 2.0 rise | R4 | `climb_lane_up/down` (path, not a slot) | 32 px rise per tread tile. Drawn as stacked tread blocks so agents y-sort correctly. |
| P0 | `stair_landing` | 2×2 | — | R2 | `talk_spot_a/b` · stand | Walk-and-talk anchor points. |
| P0 | `stair_rail` | per tile | 1.0 | R4 | — | Sliced per tile. Rails on the camera side are low-alpha. |
| P0 | `hall4_door_4b` | wall | 2.1 | R4 | `door`, `knock_spot_outside` ← **Sheldon's `knock_knock_penny` target** | Decal "4B". |
| P0 | `hall4_floor_kit` | tiles | — | — | — | `floor_hall` wood/carpet, 3×3 landing. |
| P1 | `lobby_elevator_broken` | 2×1 wall | 2.4 | R4 | `inspect` · 1 | Doors with **yellow-and-black caution tape** in an X, and an "out of order" sign (original wording). |
| P1 | `lobby_mailboxes` | 1×0 wall | 1.4 | R4 | `check_mail` · 1 | Bank of brass mailboxes. |
| P1 | `lobby_entrance_door` | wall | 2.1 | R4 | `exit_world`, `enter_world` | Glass doors with a street-light glow. |
| P2 | `stair_window`, `stair_wall_lamp`, `hall_plant`, `hall_light_fixture` | — | — | — | — | Dressing. |
| P2 | `stair_box_obstacle` | 1×1 | 0.6 | R4 | `carry` | Used for the "moving furniture up the stairs" beat. |

### 5.3 Apartment 4B (`loc_4b`) — Penny's apartment
A mirror-image plan of 4A, but **distinct dressing** in turquoise, orange, purple, and lime (§1.4). Messier: laundry on chairs, a smaller couch, a bar counter, a cozy floor lamp, a dining table often covered in stuff.

| Pri | Item id | Footprint | h | Rot | Hooks | Notes |
|---|---|---|---|---|---|---|
| P1 | `4b_couch` | 3×1 | 0.85 | R4 | `seat0..seat2` | Colorful throws. A different silhouette from 4A's couch. |
| P1 | `4b_front_door` | wall | 2.1 | R4 | `door`, `knock_spot_inside`, `answer_spot` | Syncs with `door_answer_annoyed`. |
| P1 | `4b_kitchen_bar` | 2×1 | 1.0 | R4 | `stool0..1`, `pour_wine` | Wine bottle and glass props. |
| P1 | `4b_dining_table_cluttered` | 2×1 | 0.75 | R4 | `seat0..1` | Laundry and mail clutter decal. |
| P1 | `4b_coffee_table` | 2×1 | 0.45 | R4 | `surface` | |
| P2 | `4b_armchair_patterned` | 1×1 | 0.9 | R8 | `seat` | |
| P2 | `4b_mirror_wall`, `4b_plants`, `4b_lamp_tiffany`, `4b_bookshelf`, `4b_laundry_pile` | — | — | — | — | Dressing. |
| P3 | `4b_bedroom_door` | wall | — | R4 | `enter_bedroom_penny` | |

### 5.4 Caltech cafeteria (`loc_cafe`)
Long tables with chairs, an institutional cream and teal palette, a food line, windows.

| Pri | Item id | Footprint | h | Rot | Hooks | Notes |
|---|---|---|---|---|---|---|
| P1 | `cafe_table_long` | 3×1 | 0.75 | R4 | `seat0..seat5` (both sides) | Sliced. |
| P1 | `cafe_chair` | 1×1 | 0.9 | R8 | `seat` | |
| P1 | `cafe_food_line` | 4×1 | 1.0 | R4 | `queue0..queue3`, `take_tray` | |
| P1 | `cafe_tray` (prop) | — | — | — | `carry` | |
| P2 | `cafe_window_wall`, `cafe_trash`, `cafe_drink_station`, `cafe_bulletin_board` | — | — | — | — | |

### 5.5 The Comic Center comic store (`loc_comic`)
Long racks of comics, wall shelves, a counter with a register, action-figure displays, a gaming table at the back, and posters on the walls. Post-fire it was re-done with multiple new wall colors (Looper). Use the comic sub-palette and make every cover, poster, and logo **original**.

| Pri | Item id | Footprint | h | Rot | Hooks | Notes |
|---|---|---|---|---|---|---|
| P1 | `comic_rack_island` | 2×1 | 1.2 | R4 | `browse0..1` | Generic comic covers (16 original designs as decals). |
| P1 | `comic_wall_shelf` | 2×0 wall | 2.0 | R4 | `browse` | |
| P1 | `comic_counter_register` | 2×1 | 1.0 | R4 | `cashier` (staff NPC), `buy` | |
| P2 | `comic_figure_display_case` | 1×1 | 1.8 | R8 | `admire` | Glass case with a glint. |
| P2 | `comic_game_table` | 2×2 | 0.75 | R4 | `seat0..3`, `play_cards` | Generic fantasy card game. |
| P2 | `comic_posters`, `comic_cardboard_standee` | — | — | — | — | Original. |

### 5.6 The Cheesecake Factory (`loc_ccf`)
Warm amber lighting, dark wood, booths along a wall, a bar with stools, ornate column and pendant-lamp shapes. Use only the generic "restaurant" look: **no real wordmark** (use an original sign, such as "The Cheesecake Place").

| Pri | Item id | Footprint | h | Rot | Hooks | Notes |
|---|---|---|---|---|---|---|
| P1 | `ccf_booth` | 2×1 | 1.1 | R4 | `seat0..3`, `order` (waitress target) | `booth red` upholstery. |
| P1 | `ccf_bar_counter` | N×1 modular | 1.1 | R4 | `stool0..N`, `bartender`, `pour_drink` | Penny's waitress/bartender station. |
| P1 | `ccf_table_2top` | 1×1 | 0.75 | R2 | `seat0..1` | |
| P1 | `ccf_pendant_lamp` | ceiling decal | — | R1 | — | Amber `lamp_warm` glow pool. |
| P2 | `ccf_host_stand`, `ccf_column_ornate`, `ccf_cake_display`, `ccf_plants`, `ccf_kitchen_door` | — | — | — | `kitchen_door`: waitress path | |

### 5.7 Later kits (P3 backlog)
Leonard and Sheldon's Caltech **lab** (lasers, a lab bench, a blackboard), the **university office** corridor, Howard's mom's house (the voice-only mom is an off-screen bubble), the laundry room in the basement, the train, the roof, Amy's apartment. Each kit follows the same rules (§4–§6).

---

## 6. Depth sorting, anchors and interaction hooks (data schema)

### 6.1 Y-sort rules
- The sort key is the **pivot's world (x + y), then z, then a per-asset `sort_bias`** (integer, default 0). For screen-space engines, use `pivot screen y` + `sort_bias`.
- Characters sort by their **pivot (feet)**. Items sort by their **footprint bottom vertex**, per slice (§4.5).
- **Wall-mounted items** (whiteboards, posters, door frames) use the wall's sort key minus 1, so they draw on the wall and behind everyone in the room.
- **Seated characters** take the seat's sort key + 1, so they draw in front of the seat back but behind the armrest's front slice. Set the armrest slice's `sort_bias` to +2 so it overlaps the agent.
- **Floor decals** (rugs, light pools) and the **character shadow** draw in a separate floor layer under everything.

### 6.2 Item metadata (JSON sidecar) — one file per item
```json
{
  "id": "4a_couch",
  "location": "loc_4a",
  "footprint": [3, 1],
  "height_m": 0.85,
  "rotation_class": "R4",
  "rotations": {
    "SE": {"sprite": "item_4a_couch_SE", "pivot": [64, 181], "slices": 3},
    "SW": {"sprite": "item_4a_couch_SW", "pivot": [192, 181], "slices": 3},
    "NE": {"sprite": "item_4a_couch_NE", "pivot": [64, 181], "slices": 3},
    "NW": {"sprite": "item_4a_couch_NW", "pivot": [192, 181], "slices": 3}
  },
  "blocks_walk": [[0,0],[1,0],[2,0]],
  "sort_bias": 0,
  "hooks": [
    {"id": "seat0", "type": "sit", "tile": [0,0], "offset_px": [0, -10],
     "facing": "SE", "capacity": 1, "anim": "sit_idle", "tags": ["sheldon_spot"],
     "approach_tile": [0, 1]},
    {"id": "seat1", "type": "sit", "tile": [1,0], "offset_px": [0, -10],
     "facing": "SE", "capacity": 1, "anim": "sit_idle", "approach_tile": [1, 1]},
    {"id": "seat2", "type": "sit", "tile": [2,0], "offset_px": [0, -10],
     "facing": "SE", "capacity": 1, "anim": "sit_idle", "approach_tile": [2, 1]},
    {"id": "armrest_r", "type": "perch", "tile": [2,0], "offset_px": [20, -16],
     "facing": "SW", "capacity": 1, "anim": "sit_idle", "approach_tile": [3, 0]}
  ],
  "states": ["default"],
  "z_anchor_px": 29
}
```
- `pivot` values are in the item canvas's pixel coordinates.
- `offset_px` is the agent pivot's offset from the hook tile centre. `facing` is in **rotation-local** terms: the engine rotates hooks with the item.
- `approach_tile` is where the agent must stand before it plays `sit_down`.
- `z_anchor_px` is the seat or surface height. It is used to place props (mugs, laptops) on the item and to offset a seated agent's pivot.

### 6.3 Hook types (canonical list)
| Hook types |
|---|
| `sit`, `sit_floor`, `perch`, `stand`, `use`, `write`, `look`, `browse`, `cook`, `pour_drink` |
| `door`, `knock_spot_outside`, `knock_spot_inside`, `answer_spot` |
| `queue`, `cashier`, `order`, `bartender` |
| `pickup`, `place_item`, `carry`, `watch`, `talk_spot`, `climb_lane_up/down`, `exit_world`, `enter_world` |

---

## 7. Agent integration

### 7.1 Architecture in one paragraph
Each character is an **autonomous agent** (an LLM or behavior-tree "brain") that only ever emits **high-level actions** such as `go_to(hook)`, `say(text, target)`, `emote(tag)`, or `use(hook)`. A deterministic **animation director** on the client turns each action into a pathfind, a walk, an approach, then an animation, a bubble, and a return to idle. Brains never pick frames, so art can change without retraining prompts. A **scene director** (the "showrunner") watches the agents and adds sitcom texture: camera framing, a laugh track on punchlines, and "cold-open" events such as takeout night.

### 7.2 Action → animation table
| Agent action (API) | Pre-steps (director) | Animation(s) | Dirs | Bubble / SFX | Ends with |
|---|---|---|---|---|---|
| `go_to(target)` | A* on the walk grid, `turn` at corners | `walk` (or `run` if `urgent`) | 8D | footsteps | `idle` |
| `sit(hook)` | go to `approach_tile`, face the hook | `sit_down` → `sit_idle` | 4D | cushion SFX | stays seated |
| `stand_up()` | — | `stand_up` | 4D | — | `idle` |
| `say(text, to)` | face `to` (8D) or keep the seated facing (4D) | `talk` / `sit_talk` | 8D/4D | speech bubble with the text, typewriter at 30 cps | `listen` while the other agent replies |
| `listen(from)` | face `from` | `listen` / `sit_idle` | 8D/4D | — | — |
| `emote(tag)` | facing optional | the signature tag from §3 (or a generic one) | per tag | emote icon (§7.3) | `idle` |
| `knock(door)` | go to `knock_spot_outside` | `knock`, or Sheldon's `knock_knock_penny` | 4D | knock SFX ×3 + "Penny." bubble ×3 | waits for `door_answer` or a timeout (6 s) |
| `answer_door(door)` | go to `answer_spot` | `door_open` → `door_answer_annoyed` (Penny) | 4D | door SFX | `idle` |
| `use(hook)` | approach | per hook type: `use`, `write` → `stand_whiteboard`, `cook`, `browse`, `look`, `pour_drink` | 4D | context SFX | `idle` |
| `eat(hook)` | sit first if needed | `sit_eat` | 4D | — | `sit_idle` |
| `play_game(hook)` | sit | `sit_game` | 4D | game blips | `sit_idle` |
| `work_laptop(hook)` | sit | `sit_laptop` | 4D | typing | `sit_idle` |
| `climb(stair, up/down)` | snap to the climb lane | `climb_stairs_up/down` | 2 axes | — | `idle` at the landing |
| `carry(item, to)` | `pickup` | `carry_box` | 8D | effort grunt bubble | `putdown` |
| `hug(agent)` | both approach a shared `talk_spot` | `hug` (sync) | 4D | heart emote | `idle` |
| `give(item, agent)` | approach | `point` + item transfer | 4D | — | `idle` |
| `leave(location)` | go to `exit_world` / door | `walk` → `door_open` → fade | 4D | — | removed from the scene |
| `phone(call)` | — | `phone` | 8D | phone bubble | `idle` |

### 7.3 Emote bubbles
- **Bubble sprite:** a 9-slice speech bubble.
  - 16 × 16 px corners, 1 px `ink` outline on `paper` fill, a 6 px tail pointing at the speaker's head.
  - Tail origin: pivot + (0, −(body_height + 8)).
  - Max width 240 px native. 8 px Pixel Operator- or m5x7-style font (SIL OFL licensed) at 1×.
  - Variants: `bubble_say`, `bubble_shout` (spiky), `bubble_think` (clouds), `bubble_whisper` (dashed).
- **Emote icons:** 16 × 16 px, 2–4 frames each, 6 fps, popping above the head with a 4-frame scale-in step: 50% → 100% (that is the only non-integer scale allowed, and only on UI).
- **Icon set (v1, 24):**

  | Emote icons |
  |---|
  | `!` (surprise), `?` (confused), `...` (silence), `heart`, `broken_heart`, `sweat`, `anger_vein`, `music_note` |
  | `idea_bulb`, `zzz`, `star`, `atom` (science), `brain`, `wine`, `game_pad`, `takeout_box` |
  | `phone`, `laugh_tears`, `blush`, `tear`, `skull` (mortified), `sparkle`, `eye_roll`, `bazinga_burst` |

### 7.4 Idle behaviors (when the brain is "thinking" or has no task)
The director picks an idle every 4–10 s, weighted per character:
| Character | Idle pool (weight) |
|---|---|
| Sheldon | adjust posture (3), `whiteboard_eureka` near a whiteboard (2), `spot_claim` stare at his seat if occupied (2), `blink` (always) |
| Leonard | `glasses_push` (3), `phone` (2), sigh (1) |
| Penny | `hair_flip` (2), `phone` (3), `wine_sip` if she has a glass (2) |
| Howard | `eyebrow_waggle` (2), `magic_trick` (1), adjust belt buckle (2) |
| Raj | hands folded (3), `astronomy_point` near a window (1), look at Howard (2) |
| Bernadette | adjust cardigan (2), `phone` (2), smile (2) |
| Amy | adjust glasses (2), look adoringly at Sheldon if he is within 3 tiles (3), `tiara_dream` (1) |

### 7.5 Multi-agent sync rules
- **Two-agent animations** (`hug`, `mute_whisper`, `bestie_hug`) reserve a shared `talk_spot` pair. Both agents approach, then the director starts both animations on the **same frame tick**.
- **Conversation staging (the sitcom rule):** when two or more agents talk, the director spaces them 1–2 tiles apart on a **diagonal that opens toward the camera** (SW–NE pairs face SE/SW). Nobody's back faces the camera unless they are walking away.
- **Doors** are a shared resource: a mutex per door, so two agents never use the door animation at once.
- **Seats** are reserved on `go_to(sit)`. Sheldon's `seat0` has a `priority_owner` of `sheldon`. If someone else sits there, Sheldon's brain receives a `spot_taken` event (the classic gag).

### 7.6 Interaction points and agent senses (perception payload)
Each tick, the director sends each brain:
- its location, the nearby agents and their current actions;
- the free hooks in the room (`id`, `type`, distance);
- held items, time of day, and the weekly **schedule events** (for example "takeout night", "comic book night", "Halo night"; the exact schedule is an open question in §12);
- recent dialogue lines it overheard (within 4 tiles).

That is enough for emergent sitcom behavior without the brain ever handling frames or pixels.

### 7.7 Laugh-track director (optional, toggle)
After a `say` from any agent, a small classifier (or a keyword/LLM-judge) scores "punchline-ness" from 0 to 1.
- At ≥ 0.7, it triggers a canned-laugh SFX (a royalty-free crowd laugh) and a 0.4 s camera **micro-zoom** of 1 integer step.
- It never fires more often than every 12 s.
- The global setting `laugh_track: off | subtle | full` defaults to `subtle`.

---

## 8. Export formats and engine integration

### 8.1 Aseprite (source of truth)
One `.aseprite` file per character and per item.
- Layers: `guide` (hidden), `body`, `decal`, `prop`, `fx`.
- Tags: `<anim>_<dir>` with per-frame durations.
- Slice: a `pivot` slice at (64,116) on characters, or the footprint bottom vertex on items.

**CLI export** (per character):
```bash
aseprite -b chr_sheldon.aseprite \
  --ignore-layer guide \
  --sheet-type rows --sheet-columns 12 \
  --sheet out/chr_sheldon.png \
  --data  out/chr_sheldon.json \
  --format json-array --list-tags --list-slices \
  --filename-format '{title}_{tag}_{tagframe00}' \
  --trim-sprite false
```
- Keep the 128×128 frames **untrimmed** from Aseprite (a stable pivot). Trim later in TexturePacker, which stores the offset.
- `json-array` + `frameTags` + `slices` gives Phaser and Godot everything they need.

### 8.2 TexturePacker (shipping atlases)
| Setting | Value |
|---|---|
| Data format | Phaser 3 (JSON Hash) for web; Godot SpriteFrames via plugin, or the generic JSON |
| Texture | PNG-32, max **4096 × 4096**, power-of-two **off** |
| Trim mode | **Trim** (keep the original size and offset) |
| Extrude | 1 px. Border padding 2 px. **Shape padding 2 px** |
| Algorithm | MaxRects, best area. Allow rotation **off**. |
| Scale | 1.0 only. Filter: nearest. |
| Pivot | from the sidecar `meta.json` (below), or "custom" (0.5, 0.90625) for characters |
| Multipack | on (if a character overflows a single 4096² sheet) |

### 8.3 Sidecar `meta.json` (per character)
```json
{
  "id": "sheldon",
  "frame": [128, 128],
  "pivot_px": [64, 116],
  "pivot_norm": [0.5, 0.90625],
  "body_height_px": 100,
  "palette": "palettes/bbt_sheldon.gpl",
  "dirs": ["S","SW","W","NW","N","NE","E","SE"],
  "mirror": {"NE": "NW", "E": "W", "SE": "SW"},
  "anims": {
    "idle":  {"frames": 4,  "fps": 4,  "loop": true,  "dirs": "8D"},
    "walk":  {"frames": 8,  "fps": 10, "loop": true,  "dirs": "8D"},
    "sit_idle": {"frames": 4, "fps": 4, "loop": true, "dirs": "4D"},
    "knock_knock_penny": {"frames": 16, "fps": 8, "loop": false, "dirs": "4D",
                          "holds_ms": {"3": 375, "7": 375, "11": 375},
                          "bubble_cues": {"3": "Penny.", "7": "Penny.", "11": "Penny."}}
  },
  "decals_on_mirror": ["emblem", "bag_strap"]
}
```

### 8.4 Phaser 3
```js
// preload
this.load.aseprite('sheldon', 'chr/chr_sheldon.png', 'chr/chr_sheldon.json');
// create
this.anims.createFromAseprite('sheldon');          // one anim per tag: e.g. walk_SW
const s = this.add.sprite(x, y, 'sheldon').setOrigin(0.5, 0.90625);
s.play({ key: 'walk_SW', repeat: -1 });
// mirrored direction when the source only exports 5 dirs:
function playDir(sprite, anim, dir) {
  const map = { NE: 'NW', E: 'W', SE: 'SW' };
  sprite.setFlipX(!!map[dir]);
  sprite.play({ key: `${anim}_${map[dir] || dir}`, repeat: -1 }, true);
}
// y-sort every frame
this.events.on('update', () => sortables.forEach(o => o.setDepth(o.y + (o.sortBias || 0))));
// Game config: pixelArt: true, roundPixels: true
```

### 8.5 Godot 4
- Import with **Texture Filter = Nearest**, mipmaps off. Project setting `rendering/2d/snap/snap_2d_transforms_to_pixel = true`.
- **TileMapLayer:** a TileSet with tile shape *Isometric*, layout *Diamond Down*, tile size **128×64**. Turn `y_sort_enabled` on for the layer and its parent.
- **Characters:** an `AnimatedSprite2D` with a SpriteFrames resource, created via an Aseprite importer plugin (for example "Aseprite Wizard") or a small script that reads the JSON. Set `offset = Vector2(0, -52)` so the node origin is the feet (128/2 − 116 = −52 on y).
- **Items:** a `Sprite2D` per slice, with `y_sort_enabled` on the parent. Hooks are `Marker2D` children named after the hook ids, with metadata from the sidecar JSON.
- `flip_h` for NE/E/SE when the source only exports 5 directions.

---

## 9. AI image-generation prompts

> **Rules.** AI output is **concept and reference only**. Every shipped pixel is hand-placed or hand-cleaned in Aseprite against the `.gpl` palette. Prompts **never** name actors, the show, or real logos. They describe archetypes and costumes. Generate a turnaround concept first, then redraw it at 128×128.

### 9.1 Global style block (prepend to every prompt)
```
HD pixel art, crisp 1-pixel dark violet-black outlines with selective outlining, hue-shifted cel shading (3 tones per material, violet shadows, warm highlights), no dithering on characters, no anti-aliasing against background, transparent background, 2:1 isometric dimetric projection, warm even sitcom studio lighting from top-front, cozy lived-in apartment aesthetic, limited palette, game sprite sheet clarity, orthographic, no perspective distortion, no text, no logos, no watermark
```
**Negative prompt** (if supported): `blurry, painterly, 3D render, photo, realistic, perspective, gradient banding, noise, jpeg artifacts, text, logo, watermark, extra limbs, cropped feet`

### 9.2 Character turnaround prompts (one per character)
Template: `[GLOBAL] + character turnaround sheet, 5 views (front, front-left 3/4, left profile, back-left 3/4, back), full body standing idle, 1:3.25 head-to-body "chunky-real" proportions, character is [DESCRIPTION], palette: [HEXES]`

- **Sheldon:** `a very tall lanky young man physicist, short neat brown side-parted hair, red short-sleeve tee with an original yellow atom-and-lightning-bolt circle emblem worn over a long-sleeve navy undershirt, slim khaki trousers, brown shoes, stiff upright posture, slight smug expression` · palette `#d23a32 #f5c542 #3b4f7a #b9a27a #5a3f2b #e3b394 #1a1420`
- **Leonard:** `a short slim young man experimental physicist, thick black rectangular glasses, short dark curly hair, blue-grey zip-up hoodie over a green graphic tee with an original pixel game motif, brown corduroy trousers, grey sneakers, slight friendly slouch` · `#6f7f96 #4f8a4a #7a5236 #2e2626 #e3b394 #1a1420`
- **Penny:** `a young woman with long wavy blonde hair parted on the side, fitted pink tee, blue skinny jeans, brown ankle boots, confident relaxed stance, bright expressive face` · `#ef7fa8 #4f74a8 #d9b45e #5c3a24 #e3b394 #1a1420`
- **Howard:** `a slim young man engineer with a dark bowl haircut, white mock-turtleneck dickey under a bright blue shirt, skin-tight magenta trousers, red belt with a big novelty silver buckle, small green alien pin on his left collar, cocky grin` · `#f4f1ea #3b7fd1 #b8338a #c8362f #c9ced6 #7bd44a #e3b394 #1a1420`
- **Raj:** `a young South Asian man astrophysicist, thick swept-back black hair, cream collared shirt under a brown argyle sweater vest, olive chinos, dark shoes, gentle shy expression` · `#eee3c8 #7a5233 #b08a4a #6f7442 #b47a52 #2e2626 #1a1420`
- **Bernadette:** `a petite young woman microbiologist, wavy shoulder-length strawberry-blonde hair, round brown glasses, navy floral A-line dress, short pink cardigan, dark Mary-Jane shoes, sweet smile` · `#2c3a66 #f28db2 #c99a45 #6b4a33 #e3b394 #1a1420`
- **Amy:** `a young woman neuroscientist, straight shoulder-length brown hair with side part and hair clips, glasses, purple striped cardigan over a burgundy blouse, below-knee camel skirt, brown tights, flat shoes, earnest upright posture` · `#6e4a87 #c9b8d6 #7a2a3a #b58a55 #5a3d2e #5a3f2b #1a1420`

### 9.3 Animation key-pose prompts
`[GLOBAL] + [CHARACTER DESCRIPTION] + sprite animation key poses in a row, [N] frames, [ANIM DESCRIPTION], facing [front-left 3/4 view], consistent proportions and colors in every frame, evenly spaced on a grid, same height baseline`
- Example, Sheldon's knock: `... 4 key poses: knuckles raised at a door, knock forward, knock back, pause with head turned calling a name`
- Example, walk: `... 8-frame walk cycle: contact, down, passing, up, contact, down, passing, up`

### 9.4 Environment and item prompts
- **Room concept:** `[GLOBAL] + isometric cutaway diorama of a cozy nerdy apartment living room, front walls cut away, big brown leather 3-seat sofa facing a TV, coffee table with takeout boxes, two whiteboards covered in scribbled physics equations, shelves of collectible figurines, kitchen with green tile backsplash and breakfast bar, warm beige walls, window alcove with telescope and desk, original hero flag on wall, 128x64 tile grid, no people`
- **Hall and stairs:** `[GLOBAL] + isometric cutaway of an old apartment building stairwell and 4th-floor landing with two facing apartment doors, beige walls, wooden handrails, stairs wrapping down, broken elevator with yellow caution tape crossed over its doors in the lobby below, mailboxes, warm hallway lighting, no people`
- **Item template:** `[GLOBAL] + single isometric game item, [ITEM], footprint [X]x[Y] tiles of 128x64, viewed from [SE] rotation, light from upper-left (top face lightest, left face mid, right face darkest), soft violet contact shadow, transparent background, centered, no text`
- **4B:** `... colorful apartment with turquoise, orange, purple and lime furniture and accessories, slightly messy, small sofa with throws, bar counter with wine bottle ...`
- **Comic store:** `... comic book store interior, long central racks of original comic covers, wall shelves, counter with register, glass case of action figures, game table at back, blue-grey walls with red and yellow accents, original posters ...`
- **Restaurant:** `... upscale-casual restaurant, warm amber pendant lamps, dark wood, red booths along a wall, ornate columns, bar with stools, cake display, original generic signage ...`

### 9.5 Converting AI concepts into shippable pixels
1. Downscale the concept to target size with **nearest**, then *repaint*. Never just quantize.
2. Remap to the `.gpl` palette (Aseprite: *Sprite → Color Mode → Indexed* with the character palette, then fix by hand).
3. Rebuild outlines at 1 px and fix the 2:1 staircases.
4. Match the pivot and head-top line to `frame_guide_128.png`.
5. Run the QA checklist (§10).

---

## 10. Consistency and QA checklists

### 10.1 Consistency rules (the whole team, every asset)
- [ ] Only colors from the asset's `.gpl` palette are used. Automated check: `tools/qa_palette.py` against `bbt_palettes.json`.
- [ ] Outlines use `ink #1a1420` or sel-out ramp colors. No `#000000`, no semi-transparent pixels except in `fx` layers.
- [ ] The character pivot is exactly at (64,116). Feet touch y = 116 in all grounded frames.
- [ ] The head-top line matches the character's §2.1 value (±1 px for the bob in walk or idle frames).
- [ ] Iso edges are clean 2:1 staircases (no 1-px jogs). The tile diamond is exactly 128×64.
- [ ] Environment light: top face lightest, SW face mid, SE face darkest, on every rotation.
- [ ] Item rotations are drawn, never mirrored. Character NE/E/SE are mirrored and patched.
- [ ] No real logos, wordmarks, or actor likenesses. All text and emblems are original.
- [ ] File names follow §2.5. Every animation tag exists for every required direction (8D or 4D).

### 10.2 "Perfect 128×128 sheet" QA checklist (per character)
**Silhouette and readability**
- [ ] The black-fill silhouette test: each character is recognizable from silhouette alone in S, SW, W, and N.
- [ ] Lineup test: all 7 characters in S idle side by side on a 4A floor. Heights read in the right order, and the key colors are unique at 1× zoom.
- [ ] The face reads at 1×: eyes, glasses, and mouth are visible in S and SW.

**Animation**
- [ ] `walk`: no foot sliding. One 8-frame cycle at 10 fps (0.8 s) moves the agent exactly 1 tile (about 72 px of screen travel on an axis diagonal), so `walk_speed` = 1.25 tiles/s. `run` is 6 frames at 12 fps (0.5 s) per 1.5 tiles, or 3 tiles/s.
- [ ] Volume is preserved, with no pixel "boiling" on idle frames (only intended pixels change).
- [ ] Arc and secondary motion: hair (Penny, Bernadette, Amy) lags 1 frame behind the head.
- [ ] Loops are seamless: the last frame flows into the first.
- [ ] Sync animations (`hug`, `mute_whisper`) line up when both are played on the same tick with a 1-tile separation.

**Directions and mirroring**
- [ ] All 8 directions exist (painted or mirrored) for 8D animations, and all 4 diagonals for 4D animations.
- [ ] Mirrored directions: the decals are repainted correctly (Sheldon's emblem is not reversed, Howard's pin is still on his left collar).
- [ ] Turning in place through S→SW→W→NW→N→NE→E→SE shows no pop in height, width, or pivot.

**Technical**
- [ ] The sheet is 1536 px wide with 12 columns and 128 px rows. Unused cells are fully transparent.
- [ ] JSON: frame tags match `meta.json`, durations match fps, pivots are included.
- [ ] Imports into Phaser and Godot with no blur (nearest filtering), no seams, and no bleed (2 px padding + 1 px extrude).
- [ ] Integer scaling test at 2× and 3× on 1080p and 1440p, panning slowly: no shimmer.

### 10.3 Item and environment QA
- [ ] The canvas size matches the §4.3 formula and the pivot sits on the footprint's bottom vertex.
- [ ] Slices for multi-tile items sort correctly with an agent walking a full loop around the item.
- [ ] Hooks: an agent can `approach_tile` → animate → leave without clipping. Sitting looks seated (hips on the seat, `z_anchor_px` matches).
- [ ] Wall fade and x-ray triggers work behind tall items (bookcase, fridge, whiteboard).
- [ ] Glows sit on a separate `fx` layer and dim correctly with the time-of-day LUT.

---

## 11. Production order and folder structure

### 11.1 Phases
| Phase | Goal | Deliverables (in order) | Exit criterion |
|---|---|---|---|
| **P0: Vertical slice** | Sheldon and Penny live in 4A + the 4th-floor landing | Palettes and templates (done) → 4A floor and wall kit → `4a_couch`, `4a_coffee_table`, `4a_tv_stand`, `4a_front_door`, `hall4_door_4b` → Sheldon: `idle`, `walk`, `talk`, `sit_*`, `knock_knock_penny` → Penny: `idle`, `walk`, `talk`, `door_answer_annoyed` → bubble UI → director with 6 actions | The "knock-knock-Penny" loop plays out autonomously end to end |
| **P1: The ensemble** | All 7 agents, core rooms | Leonard, Howard, Raj, Bernadette, Amy (core anims) → the rest of the 4A P0/P1 items → stairwell + lobby (broken elevator) → 4B → cafeteria → emotes v1 → laugh-track director (subtle) | A 10-minute unsupervised session that looks like an episode |
| **P2: Show texture** | Gags and routines | Signature emotes for everyone → comic store → restaurant (with Penny's waitress outfit) → weekly schedule events → carry-box stairs gag → time-of-day LUTs | Viewers recognize scenarios without captions |
| **P3: Expansion** | Later seasons and kits | Lab, Amy's apartment, outfit swaps, instruments (cello, harp), a camera-rotation study | Backlog |

### 11.2 Folder structure
```
bbt-pixel/
├── BBT_Sprite_and_Isometric_Spec.md / .pdf
├── palettes/
│   ├── bbt_master.gpl
│   ├── bbt_<character>.gpl            (×7)
│   ├── bbt_palettes.json
│   └── bbt_palette_swatches.png
├── templates/
│   ├── frame_guide_128.png (+ _preview4x)
│   ├── iso_floor_tile_128x64.png
│   ├── iso_wall_backright_full_64x224.png
│   └── iso_wall_backright_cutaway_64x48.png
├── source/                          # .aseprite — source of truth
│   ├── characters/chr_<id>.aseprite
│   ├── items/<location>/item_<id>.aseprite
│   ├── tiles/<location>_tiles.aseprite
│   └── ui/bubbles.aseprite, emotes.aseprite
├── concept/                         # AI concepts & refs (never shipped)
├── export/
│   ├── characters/chr_<id>.png + .json + .meta.json
│   ├── items/<location>/item_<id>_<rot>[_s<i>].png + item_<id>.json
│   ├── tiles/<location>_tileset.png + .json
│   └── ui/
├── atlases/                         # TexturePacker output (.tps project + sheets)
├── tools/
│   ├── make_palettes.py
│   ├── make_templates.py
│   ├── qa_palette.py                (to write: palette + pivot validation)
│   └── slice_items.py               (to write: multi-tile slicing)
└── engine/
    ├── phaser/                      (web viewer "living sitcom")
    └── godot/                       (optional)
```

---

## 12. Decisions log and open questions

### 12.1 Notable decisions (v1)
1. **128×128 frames with "chunky-real" proportions of 1 : 3.25**, pivot at (64,116). Faces read well and the ensemble line-up stays recognizable without going chibi.
2. **Floor tiles of 128×64, with 1 tile = 1 m and 64 px per metre vertical** (walls 192 px). One rule keeps furniture, characters, and rooms in proportion.
3. **Paint 5 directions, mirror 3, plus decal patching.** This saves about 37% of character drawing time while keeping asymmetric identity details correct.
4. **Symmetric top-front light on characters vs. an upper-left key light on the environment.** This makes character mirroring safe while keeping a consistent 3-face light model on props.
5. **Interaction animations are 4D (diagonals only),** because iso furniture only aligns along world axes.
6. **Items rotate by rotation class (R8/R4/R2/R1) and are never mirrored.** "8 directions" for items means placement orientations under a fixed camera.
7. **Multi-tile items are sliced per tile for y-sorting**, plus a silhouette x-ray, to avoid classic iso sort bugs.
8. **The brain/animation director split:** agents emit high-level actions only, which keeps art and AI decoupled.
9. **Original replacements for every logo, wordmark, and emblem;** AI prompts never name actors or the show.
10. **No dithering on characters,** with limited ordered dither on static environment gradients only.

### 12.2 Open questions (verify against reference stills before final art)
- **Flag behind the 4A couch:** commonly described as a heraldic animal on a coloured field. Design an original banner in that spirit, and check the composition against a reference.
- **Sheldon's spot:** confirm which end of the couch, from the camera's point of view, it is. It is `seat0` in data and configurable either way.
- **Weekly schedule events** (takeout, game, and comic-store nights): exact days vary by season. Keep them configurable in `schedule.json`.
- **Comic Center post-fire colors:** confirm against a season 8+ still. The current sub-palette is a plausible reading.
- **4A and 4B mirroring:** the sets are often described as mirror-image floor plans. Verify door and kitchen placement before blocking out 4B.
- **Camera rotation:** out of scope for v1. It would need a second set of wall art and R4 for all items.

---

## 13. Reference sources
*Used for studying shapes, layouts, and colors only. No images are copied or shipped.*

**Sets and locations**
- RoomSketcher, "Tour The Big Bang Theory's Apartments in 3D": https://www.roomsketcher.com/blog/the-big-bang-theory-apartments/
- Live Home 3D, The Big Bang Theory virtual apartment: https://www.livehome3d.com/the-big-bang-theory-virtual-apartment/
- Wikimedia Commons, TBBT apartment photo (studio tour): https://commons.wikimedia.org/wiki/File:Tbbt_apartment.jpg
- Yahoo / Good Housekeeping, "The One Thing You Never Noticed About Penny's Apartment": https://www.yahoo.com/lifestyle/one-thing-never-noticed-penny-172220730.html
- TDN Blog, "5 things you didn't know about The Big Bang Theory set": https://blog.tdn.tv/5-things-you-didnt-know-about-the-big-bang-theory-set/
- Ann Shea Interiors, Set Decoration: https://annsheainteriors.com/set-decoration
- EW, "Big Bang Theory: Set design" (paywalled, cited via search excerpt): https://ew.com/article/2012/09/21/big-bang-theory-set-design/
- Warner Bros. Studio Tour Hollywood, The Big Bang Theory sets: https://www.wbstudiotour.com/the-big-bang-theory-sets/ and https://www.wbstudiotour.com/news/the-big-bang-theory/
- "How does The Big Bang Theory staircase work?": https://www.mixdexhq.com/tv-answers/how-does-the-big-bang-theory-staircase-work/
- Movies & TV Stack Exchange, visual cues for the different floors: https://movies.stackexchange.com/questions/105471/what-visual-cues-distinguish-the-different-floors-on-the-big-bang-theory
- Looper, "The Big Bang Theory Comic Book Store Hides A Cool Real Life Detail": https://www.looper.com/1598629/big-bang-theory-comic-book-shop-current-issues-detail/
- Looper, "Where Is The Big Bang Theory Set?": https://www.looper.com/1484557/where-the-big-bang-theory-set-pasadena-california/
- ScreenRant, "10 Hidden Details About The Comic Book Store": https://screenrant.com/big-bang-theory-hidden-details-comic-book-store/
- LAist, Pasadena locations: https://laist.com/news/entertainment/15-of-the-big-bang-theorys-pasadena-locations

**Wardrobe**
- TV Style Guide, Sheldon Cooper: https://www.tvstyleguide.com/big-bang-theory/sheldon-cooper/how-to-dress-like-dr-sheldon-cooper/
- TV Style Guide, Leonard Hofstadter: https://www.tvstyleguide.com/big-bang-theory/leonard-hofstadter/how-to-dress-like-dr-leonard-hofstadter/
- TV Style Guide, Howard Wolowitz: https://www.tvstyleguide.com/big-bang-theory/howard-wolowitz/how-to-dress-like-howard-wolowitz/
- Costume Wall, Sheldon Cooper: https://costumewall.com/dress-like-sheldon-cooper/
- Costume Wall, Raj Koothrappali: https://costumewall.com/dress-like-raj-koothrappali/
- Costume Wall, Bernadette: https://costumewall.com/dress-like-bernadette-rostenkowski-wolowitz/
- Carbon Costume, Howard Wolowitz: https://carboncostume.com/howard-wolowitz/
- Carbon Costume, Raj Koothrappali: https://carboncostume.com/raj-koothrappali/
- Carbon Costume, Amy Farrah Fowler: https://carboncostume.com/amy-farrah-fowler/
- TV Guide, "50 Sheldon Shirts, Ranked": https://www.tvguide.com/galleries/50-sheldon-shirts-the-big-bang-theory-ranked-best-to-worst/
- Big Bang Theory Wiki (Fandom), Howard's Wardrobe (blocked a direct fetch, cited via search): https://bigbangtheory.fandom.com/wiki/Howard%27s_Wardrobe
- Sheldon Shirts, Howard's belt buckles and lapel pins: http://www.sheldonshirts.com/howard-wolowitz-belt-buckles-lapel-pins/
- Wizzley, Big Bang Theory costumes: https://wizzley.com/big-bang-theory-costumes/
- Worn on TV, Bernadette outfits: https://wornontv.net/the-big-bang-theory/bernadette/page/2/
- Wikipedia, Howard Wolowitz: https://en.wikipedia.org/wiki/Howard_Wolowitz

**Engine and tool documentation**
- Phaser, AsepriteFile loader: https://docs.phaser.io/api-documentation/class/loader-filetypes-asepritefile
- Phaser, Sprite concepts: https://docs.phaser.io/phaser/concepts/gameobjects/sprite
- Godot, Using TileMaps: https://docs.godotengine.org/en/stable/tutorials/2d/using_tilemaps.html
- Godot, TileMapLayer class: https://docs.godotengine.org/en/4.3/classes/class_tilemaplayer.html
- Aseprite CLI documentation: https://www.aseprite.org/docs/cli/
- TexturePacker documentation: https://www.codeandweb.com/texturepacker/documentation
