# QA report: chr_raj

Generated 2026-10-30 17:59 (America/Los_Angeles) by tools/build_char_sheet.py + tools/qa_char.py.

| Check | Result |
|---|---|
| Frame / pivot | 128x128, pivot (64,116) |
| Body height (spec 92 px, head top y=24) | idle S head top y=24 -> 92 px (PASS) |
| Feet on pivot line (idle, painted dirs; lowest row 116-122, house convention 119-121) | PASS (lowest px 118) |
| Palette violations | 0 (PASS) |
| Alpha values | [0, 255] |
| Frames / sheet | 352 frames, 2048x2816 |
| Animations | idle 8f@4fps x8D, walk 8f@10fps x8D, blink 3f@12fps x8D, work 6f@8fps x8D, talk 4f@6fps x8D, gesture 6f@8fps x8D, astronomy_point 4f@8fps x8D, shy_hands 5f@6fps x8D |
| Mirrors (NE/E/SE = flip NW/W/SW) | NE: silhouette DIFF, 866 px re-evaluated, E: silhouette DIFF, 676 px re-evaluated, SE: silhouette DIFF, 825 px re-evaluated |
| Eye pixels in idle S | 0 |
| GIFs | astronomy_point_8dir_4x.gif (5f), blink_8dir_4x.gif (4f), gesture_8dir_4x.gif (7f), idle_8dir_4x.gif (8f), shy_hands_8dir_4x.gif (6f), talk_8dir_4x.gif (4f), walk_8dir_4x.gif (8f), walk_E_4x.gif (8f), walk_NE_4x.gif (8f), walk_NW_4x.gif (8f), walk_N_4x.gif (8f), walk_SE_4x.gif (8f), walk_SW_4x.gif (8f), walk_S_4x.gif (8f), walk_W_4x.gif (8f), work_8dir_4x.gif (6f) |
