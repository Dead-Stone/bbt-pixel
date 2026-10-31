"""Slice an AI-generated cast turnaround (flat magenta background) into one RGBA cut-out per figure.

Layout: 7 rows (CAST order) x 5 columns (S, SW, W, NW, N).  The grid is found from the image itself:
foreground row/column projections split it into bands (no fixed cell size assumed).

Keying: a pixel is background when it is magenta-dominated (min(R,B) - G large and G low), which also catches the
pinkish anti-aliased fringe (magenta blended with a dark outline).  Pink/red clothes stay: their min(R,B)-G is small.
Despill: on the 2-px ring along the cut edge, any leftover magenta cast (R and B both well above G) is pulled down.

Usage: python3 tools/ai_import/slice.py refs_ai/chatgpt_penny_1.png [out_dir]
"""
import os, sys, json, numpy as np
from PIL import Image
from scipy import ndimage as ndi

CAST = ['sheldon', 'leonard', 'penny', 'howard', 'raj', 'bernadette', 'amy']
DIRS5 = ['S', 'SW', 'W', 'NW', 'N']


def magenta_score(rgb):
    r, g, b = [rgb[..., i].astype(float) for i in range(3)]
    return np.minimum(r, b) - g, g


def key(rgb):
    """True = foreground"""
    m, g = magenta_score(rgb)
    bg = (m > 90) & (g < 140)                      # pure magenta and magenta-heavy fringe
    fg = ~bg
    fg = ndi.binary_opening(fg, np.ones((2, 2)))   # 1-px fringe slivers
    return fg


def despill(rgb, fg):
    out = rgb.astype(float).copy()
    ring = fg & ~ndi.binary_erosion(fg, iterations=2)
    m, g = magenta_score(out)
    sp = ring & (m > 25)
    exc = np.where(sp, m - 25, 0)
    out[..., 0] -= exc; out[..., 2] -= exc
    return np.clip(out, 0, 255).astype(np.uint8)


def bands(prof, n, min_gap=3):
    """split a 1-D occupancy profile into n runs (merging the closest runs / splitting the widest if needed)"""
    occ = prof > 0
    runs = []; i = 0
    while i < len(occ):
        if occ[i]:
            j = i
            while j < len(occ) and occ[j]: j += 1
            runs.append([i, j]); i = j
        else: i += 1
    # merge runs separated by tiny gaps
    merged = [runs[0]]
    for r in runs[1:]:
        if r[0] - merged[-1][1] < min_gap: merged[-1][1] = r[1]
        else: merged.append(r)
    runs = merged
    while len(runs) > n:                           # drop/merge the smallest run into its nearest neighbour
        k = int(np.argmin([b - a for a, b in runs]))
        if k == 0: runs[1][0] = runs[0][0]
        elif k == len(runs) - 1: runs[-2][1] = runs[-1][1]
        else:
            if runs[k][0] - runs[k - 1][1] < runs[k + 1][0] - runs[k][1]: runs[k - 1][1] = runs[k][1]
            else: runs[k + 1][0] = runs[k][0]
        runs.pop(k)
    if len(runs) != n: raise SystemExit(f'expected {n} bands, found {len(runs)}')
    return runs


def slice_sheet(path):
    rgb = np.array(Image.open(path).convert('RGB'))
    fg = key(rgb)
    lab, nl = ndi.label(fg); sz = np.bincount(lab.ravel()); sz[0] = 0
    fg = np.isin(lab, np.nonzero(sz >= 40)[0])     # drop specks of noise
    rows = bands(fg.sum(1), len(CAST))
    out = {}
    for ri, (y0, y1) in enumerate(rows):
        cols = bands(fg[y0:y1].sum(0), len(DIRS5))
        for ci, (x0, x1) in enumerate(cols):
            m = fg[y0:y1, x0:x1]
            # keep only the components that belong to the figure (largest + anything near it, e.g. a detached hand)
            l2, n2 = ndi.label(m, np.ones((3, 3))); s2 = np.bincount(l2.ravel()); s2[0] = 0
            keep = s2 >= max(40, 0.002 * s2.max())
            m = keep[l2]
            ys, xs = np.nonzero(m)
            by0, by1, bx0, bx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            cut = despill(rgb[y0 + by0:y0 + by1, x0 + bx0:x0 + bx1], m[by0:by1, bx0:bx1])
            a = (m[by0:by1, bx0:bx1] * 255).astype(np.uint8)
            out[(CAST[ri], DIRS5[ci])] = dict(rgba=np.dstack([cut, a]), box=[int(x0 + bx0), int(y0 + by0), int(bx1 - bx0), int(by1 - by0)])
    return out


if __name__ == '__main__':
    src = sys.argv[1]; od = sys.argv[2] if len(sys.argv) > 2 else '/tmp/ai_cuts'
    os.makedirs(od, exist_ok=True)
    cuts = slice_sheet(src); boxes = {}
    for (cid, d), c in cuts.items():
        Image.fromarray(c['rgba']).save(f'{od}/{cid}_{d}.png'); boxes[f'{cid}_{d}'] = c['box']
    json.dump(boxes, open(f'{od}/boxes.json', 'w'), indent=1)
    print(len(cuts), 'figures ->', od)
    for cid in CAST: print(cid, [boxes[f'{cid}_{d}'][3] for d in DIRS5], 'px tall')
