# QA report: chr_leonard

Generated 2026-10-30 00:44 (America/Los_Angeles) by tools/build_char_sheet.py + tools/qa_char.py.

| Check | Result |
|---|---|
| Frame / pivot | 128x128, pivot (64,116) |
| Body height (spec 89 px, head top y=27) | idle S head top y=27 -> 89 px (PASS) |
| Feet on pivot line (idle, painted dirs; lowest row 116-122, house convention 119-121) | PASS (lowest px 119) |
| Palette violations | 0 (PASS) |
| Alpha values | [0, 255] |
| Frames / sheet | 152 frames, 1536x4096 |
| Animations | idle 4f@4fps x8D, walk 8f@10fps x8D, blink 3f@12fps x8D, glasses_push 4f@10fps x8D |
| Mirrors (NE/E/SE = flip NW/W/SW) | NE: silhouette same, 38 px re-evaluated, E: silhouette same, 35 px re-evaluated, SE: silhouette same, 20 px re-evaluated |
| Eye pixels in idle S | 4 |
| GIFs | blink_8dir_4x.gif (4f), glasses_push_8dir_4x.gif (5f), idle_8dir_4x.gif (4f), walk_8dir_4x.gif (8f), walk_E_4x.gif (8f), walk_NE_4x.gif (8f), walk_NW_4x.gif (8f), walk_N_4x.gif (8f), walk_SE_4x.gif (8f), walk_SW_4x.gif (8f), walk_S_4x.gif (8f), walk_W_4x.gif (8f) |
