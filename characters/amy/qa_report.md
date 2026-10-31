# QA report: chr_amy

Generated 2026-10-30 18:47 (America/Los_Angeles) by tools/build_char_sheet.py + tools/qa_char.py.

| Check | Result |
|---|---|
| Frame / pivot | 128x128, pivot (64,116) |
| Body height (spec 88 px, head top y=28) | idle S head top y=27 -> 89 px (PASS) |
| Feet on pivot line (idle, painted dirs; lowest row 116-122, house convention 119-121) | CHECK (lowest px 119) |
| Palette violations | 0 (PASS) |
| Alpha values | [0, 255] |
| Frames / sheet | 376 frames, 2048x3072 |
| Animations | idle 8f@4fps x8D, walk 8f@10fps x8D, blink 3f@12fps x8D, work 6f@8fps x8D, talk 4f@6fps x8D, gesture 6f@8fps x8D, neuro_lecture 6f@8fps x8D, excited_clap 6f@10fps x8D |
| Mirrors (NE/E/SE = flip NW/W/SW) | NE: silhouette DIFF, 731 px re-evaluated, E: silhouette DIFF, 700 px re-evaluated, SE: silhouette DIFF, 773 px re-evaluated |
| Decal 'hair_clip' per dir (px, mean col) | S: 0, SW: 0, W: 0, SE: 0, E: 0 |
| Eye pixels in idle S | 0 |
| GIFs | blink_8dir_4x.gif (4f), excited_clap_8dir_4x.gif (7f), gesture_8dir_4x.gif (7f), idle_8dir_4x.gif (8f), neuro_lecture_8dir_4x.gif (7f), talk_8dir_4x.gif (4f), walk_8dir_4x.gif (8f), walk_E_4x.gif (8f), walk_NE_4x.gif (8f), walk_NW_4x.gif (8f), walk_N_4x.gif (8f), walk_SE_4x.gif (8f), walk_SW_4x.gif (8f), walk_S_4x.gif (8f), walk_W_4x.gif (8f), work_8dir_4x.gif (6f) |
