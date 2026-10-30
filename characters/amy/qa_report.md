# QA report: chr_amy

Generated 2026-10-30 00:38 (America/Los_Angeles) by tools/build_char_sheet.py + tools/qa_char.py.

| Check | Result |
|---|---|
| Frame / pivot | 128x128, pivot (64,116) |
| Body height (spec 88 px, head top y=28) | idle S head top y=28 -> 88 px (PASS) |
| Feet on pivot line (idle, painted dirs; lowest row 116-122, house convention 119-121) | PASS (lowest px 119) |
| Palette violations | 0 (PASS) |
| Alpha values | [0, 255] |
| Frames / sheet | 168 frames, 1536x4096 |
| Animations | idle 4f@4fps x8D, walk 8f@10fps x8D, blink 3f@12fps x8D, neuro_lecture 6f@8fps x8D |
| Mirrors (NE/E/SE = flip NW/W/SW) | NE: silhouette same, 213 px re-evaluated, E: silhouette same, 150 px re-evaluated, SE: silhouette same, 189 px re-evaluated |
| Decal 'hair_clip' per dir (px, mean col) | S: 26 @ 65.8, SW: 22 @ 62.0, W: 16 @ 62.5, SE: 12 @ 67.8, E: 9 @ 58.9 |
| Eye pixels in idle S | 16 |
| GIFs | blink_8dir_4x.gif (4f), idle_8dir_4x.gif (4f), neuro_lecture_8dir_4x.gif (7f), walk_8dir_4x.gif (8f), walk_E_4x.gif (8f), walk_NE_4x.gif (8f), walk_NW_4x.gif (8f), walk_N_4x.gif (8f), walk_SE_4x.gif (8f), walk_SW_4x.gif (8f), walk_S_4x.gif (8f), walk_W_4x.gif (8f) |
