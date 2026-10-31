# Gemini sprite-sheet prompts (BBT Pixel)

How to use:
1. Paste the STYLE BLOCK + one CHARACTER block + the TURNAROUND prompt. Keep the best result.
2. In the SAME chat, attach that turnaround image and paste each ANIMATION prompt (one per message).
3. Save every image and send them to me. I'll snap them to the 128x128 grid, lock the palette, fix the pivot and wire them into the rig.
Tip: if Gemini drifts (outfit or face changes), re-attach the turnaround and say "match this character exactly".

---------------------------------------------------------------
## STYLE BLOCK (paste first, every time)

High-quality isometric pixel art sprite sheet, 2:1 isometric game view (camera looking down ~30 degrees),
style like modern indie pixel games (Stardew Valley / Eastward / Habbo quality but more realistic proportions).
Crisp hard-edged pixels, no anti-aliasing, no blur, no gradients, limited palette (max 24 colors per character),
1-pixel dark outline (not pure black, a darker shade of each color), soft top-left lighting with one highlight and one shadow tone.
Stylized but human proportions: head-to-body ratio about 1:6, upright confident posture, relaxed shoulders,
natural hands (fingertips reach mid-thigh), lively expressive face with clear eyes (white + pupil), eyebrows and a small mouth.
NOT chibi, NOT zombie-like, NOT stiff. Feet planted on the ground.
Each frame is a square cell, the character centered horizontally with feet at the same baseline in every cell,
same scale in every cell, plain flat solid magenta background (#FF00FF), no shadows on the background, no text, no labels, no grid lines.
Character must look IDENTICAL in every frame (same outfit, colors, hair, proportions).

---------------------------------------------------------------
## CHARACTER BLOCKS (paste one)

### Sheldon
Tall, very slim, lanky man in his 30s, height 186 cm, long thin limbs, narrow shoulders, very upright almost rigid posture.
Short neat brown hair combed to the side, clean-shaven, pale skin, wide-eyed alert expression.
Outfit: red long-sleeve undershirt with a short-sleeve red t-shirt on top showing a yellow lightning-flash superhero-style logo
(original design), khaki chino trousers, brown lace-up shoes.
Movement personality: precise, stiff, deliberate steps, arms tight to the body.

### Leonard
Short slim man in his 30s, height 165 cm, slightly hunched-nervous but friendly.
Dark brown curly messy hair, thick black rectangular glasses (thin frames, eyes visible), light skin.
Outfit: green-and-grey zip hoodie open over a graphic t-shirt, dark brown corduroy trousers, white sneakers.
Movement personality: quick small steps, hands often in hoodie pockets, earnest.

### Penny
Woman in her late 20s, height 168 cm, athletic fit build, confident easy posture.
Long wavy golden-blonde hair past the shoulders, light tan skin, bright friendly face, light makeup.
Outfit: fitted pink v-neck top, blue jeans, brown ankle boots. (Work variant: Amber Slice waitress uniform,
mustard-yellow shirt, black apron, notepad.)
Movement personality: relaxed hip sway, swinging arms, expressive hands, hair bounces.

### Howard
Slim man in his 30s, height 170 cm, narrow build.
Dark brown "bowl-cut" hair with straight fringe to the eyebrows, light skin, smug grin.
Outfit: very tight bright-colored outfit: royal-blue fitted turtleneck dickey under a fitted top, magenta/pink skinny trousers,
big shiny metal belt buckle, brown boots.
Movement personality: cocky swagger, little shoulder bounce, eyebrow waggles.

### Raj
Man in his 30s, height 170 cm, average slim build, South Asian, brown skin.
Short black hair neatly styled up, clean-shaven, warm big eyes.
Outfit: brown sweater vest over a white long-sleeve collared shirt, dark charcoal trousers, brown shoes.
Movement personality: loose, a bit theatrical, shy hand gestures, sometimes clutches a drink.

### Bernadette
Petite woman in her late 20s, height 152 cm, small frame.
Shoulder-length curly blonde hair, light skin, glasses (thin frames), sweet face.
Outfit: pink cardigan over a white blouse with collar, navy blue knee-length skirt with white polka dots, dark tights, flat shoes.
Movement personality: small quick steps, sweet but sharp, hands clasped in front.

### Amy
Woman in her 30s, height 163 cm, average build, slightly awkward posture.
Long straight brown hair parted in the middle, light skin, big glasses (thin frames, eyes visible).
Outfit: layered conservative look: purple cardigan over a patterned blouse, long tan/olive pleated skirt to mid-calf,
dark tights, brown flat shoes.
Movement personality: stiff, earnest, eager, arms slightly held out.

---------------------------------------------------------------
## TURNAROUND (first image)

Create a character turnaround sheet: 1 row of 5 cells, standing neutral pose, in this order:
1 facing toward the camera (south), 2 facing down-left (south-west, 3/4 front), 3 facing left (west, side profile),
4 facing up-left (north-west, 3/4 back), 5 facing away (north, back view).
(The right-facing directions are mirrored by me, don't draw them.)

---------------------------------------------------------------
## ANIMATION SHEETS (one message each, attach the turnaround)

Rows are ALWAYS the 5 directions in this order: south, south-west, west, north-west, north.
Columns are frames, left to right, in order. Same baseline and scale everywhere.

### 1. IDLE (5 rows x 4 frames)
Breathing idle loop. F1 neutral, F2 chest rises slightly and shoulders lift 1 px, F3 small weight shift to one hip,
F4 back to neutral with a blink. Arms relaxed, slight elbow bend. Subtle and alive.

### 2. WALK (5 rows x 8 frames)
Natural walk cycle, upright torso, no forward lean.
F1 contact (right heel strikes, legs widest, left arm forward), F2 down (body lowest, knee bends),
F3 passing (left leg passes right, body rising), F4 up (body highest, on right toe),
F5 contact (left heel strikes, right arm forward), F6 down, F7 passing, F8 up.
Arms swing opposite to legs from the shoulder, slight elbow bend, relaxed hands.

### 3. WORK (5 rows x 6 frames)
Character-specific (pick one):
- Sheldon: writing equations on a whiteboard with a marker, small arm strokes, then steps back to check.
- Leonard: adjusting a laser on a lab bench, leans in, nods.
- Penny: carrying a tray at shoulder height, then sets down a plate.
- Howard: typing on a laptop, then a pleased grin.
- Raj: looking through a telescope eyepiece, then points up excitedly.
- Bernadette: using a pipette at a lab bench, careful hands.
- Amy: looking into a microscope, adjusting the focus knob.

### 4. TALK (5 rows x 4 frames)
Conversation loop: F1 neutral, F2 mouth open + one hand gestures out, F3 head tilt + eyebrows up, F4 mouth open + other hand gesture.

### 5. SIT (5 rows x 2 frames)
F1 sitting upright on an invisible chair (thighs horizontal, knees bent 90 degrees, feet flat, hands on thighs),
F2 same but leaning back slightly and relaxed. No chair drawn.

### 6. SIGNATURE MOVE (5 rows x 6 frames)
- Sheldon: knocking on a door three times with the knuckle (raise, knock, knock, knock, pause, lower).
- Leonard: pushing glasses up the nose with one finger, then a sigh and shrug.
- Penny: hair flip with a confident smile, then sips a glass of wine.
- Howard: eyebrow waggle, then a quick magic card trick reveal.
- Raj: excitedly pointing at the sky (astronomy), hand to chest.
- Bernadette: sweet smile turning into a stern scary frown, then sweet again.
- Amy: lecturing with one finger raised (neuroscience), then a proud nod.

---------------------------------------------------------------
## Fixing common Gemini mistakes (paste as a follow-up)
"Keep every cell the same size and the feet on the same baseline. Make the character identical in every frame.
Pure flat magenta background. No anti-aliasing, crisp pixels only. Don't add text or numbers."
