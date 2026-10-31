# rig1 references (measurement / comparison only)

No art from any of these sources is copied, traced, or committed. They were read for proportions, timing and
pose structure; every pixel in `characters/*/chr_*.png` is drawn by `tools/rig` from 3-D volumes.

| source | what we took (numbers / rules only) | licence of their art |
|---|---|---|
| Liberated Pixel Cup (LPC) base sprites, OpenGameArt — https://opengameart.org/content/liberated-pixel-cup-lpc-base-assets-sprites-map-tiles | comparison only: 64x64 frames, ~2.5-3 heads tall chibi body, 9-frame walk, separate body/hair/clothing layers (the same layer idea as our rig) | CC-BY-SA 3.0 / GPL 3.0 — not used, nothing included |
| Universal LPC Spritesheet Character Generator — https://github.com/LiberatedPixelCup/Universal-LPC-Spritesheet-Character-Generator | layer order (body -> legs -> torso -> hair -> props) | CC-BY-SA / GPL / OGA-BY per asset — not used |
| Richard Williams, *The Animator's Survival Kit* (walk chapter) | contact / down / passing / up keys; body lowest on *down*, highest on *passing/up*; arms counter-swing, widest at contact; hips drop on the swing side and shoulders counter-tilt | book, notes only |
| Pixel-art walk tutorials (Pixeli / "8-frame walk cycle" write-ups, pixnote, mostlydecent walk template, manningkrull) | 8 frames at 100-140 ms; stride ~1/3 of height at contact; feet together at passing; 1-2 px head bob at this size; heel strike toe-up, toe-off heel-up | tutorials, notes only |
| Figure-drawing canons (Loomis) | adult 7-7.5 heads; shoulders ~2 head widths (men) / ~1.75 (women); hips at ~1/2 height; fingertips at mid-thigh; elbow at the waist; upper arm : forearm ~ 1.15-1.2 | notes only |

## Numbers used in `skeleton.py` / `motion.py`
* height: 100 px = 185 cm (project scale); 2:1 dimetric, camera elevation 30 deg, K = (100/185)/cos30 px per cm.
* head 0.13 H (x head_k per character, 1.0-1.14 so faces still read at 1x), shoulders 0.098 H half-width (x sh),
  hip 0.086 H half-width, hand 0.068 H, foot 0.15 H; knee at 0.285 H, hip joint at 0.53 H.
* walk: cycle = 1.12 m (8 frames x 0.14 m, the viewer's frame step), foot excursion +-28 cm, planted leg 98.5 % straight,
  pelvis bob 0.6 x (-3 cm) on *down*, hip roll 4 deg, weight sway 1.2 cm, pelvis twist 5 deg with the shoulders kept square,
  arm swing +-19-22 deg widest at contact with extra elbow bend on the forward swing, swing-foot lift 9.5 cm at passing,
  heel strike +16 deg, toe-off -26 deg.
* idle: 8-frame breath (chest scale), contrapposto weight shift 0.55 +- 0.25, head held level.
* sit: seat height 0.255 H, thighs horizontal, feet flat, hands on thighs.
