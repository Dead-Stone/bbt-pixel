"""Trim the 3 m wall slab around the fixups_v1 door 4A pieces (#13 closed, #14 open) down to the door + casing, so the proxy fit
scales the door itself to door height instead of shrinking it to fit a whole wall section.  The sheet draws the door in a
y-wall (top edge descending right); 4A's door sits in an x-wall (rising right), so the pieces are mirrored here and the "4A"
plaque is re-drawn unmirrored (columns re-sheared along the 2:1 wall slope) so it still reads 4A.
-> refs_ai/chatgpt/env/sliced/fixups_v1/13_door.png, 14_door.png (x-wall orientation; skins.py uses slope=-K)"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
D = f'{ROOT}/refs_ai/chatgpt/env/sliced/fixups_v1'
CUT = {13: 27, 14: 22}
K = 0.47                          # the sheet's wall slope (px down per px right)
PK = {13: K, 14: -0.26}           # slope of the plaque's door leaf (closed: in the wall plane; open: the swung leaf)            # outer edge of the left casing on each piece; right casing ends at x=118 on both
def unmirror_plaque(a, k, strict=False):
    """mirror the piece, then copy the gold number plaque back unmirrored, each column shifted so it follows the new slope"""
    H, W = a.shape[:2]; r, g, b = [a[..., i].astype(int) for i in range(3)]
    gold = (a[..., 3] > 0) & (r > 170) & (g > 120) & (b < 110) & (r - b > 90)
    if strict: gold = (a[..., 3] > 0) & (r > 200) & (g > 150) & (b < 140) & (r - b > 90)   # 4B: brighter brass; wood highlights pass the loose test
    lab, n = ndi.label(gold); best = None
    if strict:
        sz = ndi.sum(gold, lab, range(1, n + 1)); best = (0, 1 + int(np.argmax(sz)))
    for i in (range(1, n + 1) if not strict else ()):
        ys, xs = np.where(lab == i)
        if len(ys) < 40: continue
        if best is None or ys.mean() < best[0]: best = (ys.mean(), i)
    m = ndi.binary_dilation(ndi.binary_fill_holes(lab == best[1]), iterations=1)
    ys, xs = np.where(m); x0, x1 = xs.min(), xs.max(); w = x1 - x0 + 1
    out = a[:, ::-1].copy()
    for u in range(w):
        xo, xm = x0 + u, (W - 1 - x1) + u; dy = int(round(k * (w - 1 - 2 * u)))
        for y in np.where(m[:, xo])[0]:
            if 0 <= y + dy < H: out[y + dy, xm] = a[y, xo]
    return out
def casing_bbox(a):
    r, g, b = [a[..., i].astype(int) for i in range(3)]
    m = (a[..., 3] > 200) & (r > 190) & (g > 175) & (b > 140) & (r - b < 70); ys, xs = np.nonzero(m)
    return xs.min(), xs.max(), ys.min(), ys.max()
def match_casing(a, ref):
    """the sheet draws the open door ~5% wider than the closed one: rescale it so both casings share one bbox (same top-left
    origin), which lets skins.py place the open state with the closed state's scale + offset (spec frame='closed')"""
    rx0, rx1, ry0, ry1 = casing_bbox(np.array(Image.open(ref).convert('RGBA'))); x0, x1, y0, y1 = casing_bbox(a)
    sx, sy = (rx1 - rx0 + 1) / (x1 - x0 + 1), (ry1 - ry0 + 1) / (y1 - y0 + 1)
    im = Image.fromarray(a); W, H = im.size
    im = im.resize((max(1, round(W * sx)), max(1, round(H * sy))), Image.LANCZOS)
    b = np.array(im); b[..., 3] = np.where(b[..., 3] > 110, 255, 0)
    return b
D2 = f'{ROOT}/refs_ai/chatgpt/env/sliced/fixups_v2'
CUT2 = {6: (48, 164, 58), 7: (45, 164, 56)}      # door 4B (fixups_v2): casing left/right outer edge, casing top at the left edge
def plaque_slope(a):
    """slope of the gold plaque's top edge (the leaf plane): least-squares over its columns"""
    r, g, b = [a[..., i].astype(int) for i in range(3)]
    gold = (a[..., 3] > 0) & (r > 200) & (g > 150) & (b < 140) & (r - b > 90)
    lab, n = ndi.label(gold); sz = ndi.sum(gold, lab, range(1, n + 1)); m = lab == (1 + int(np.argmax(sz)))
    xs = [x for x in range(a.shape[1]) if m[:, x].any()]; xs = xs[2:-2]
    tops = [np.where(m[:, x])[0][0] for x in xs]
    return float(np.polyfit(xs, tops, 1)[0])
def main_4b():
    for n, (xl, xr, yt) in CUT2.items():
        a = np.array(Image.open(f'{D2}/{n:02d}.png').convert('RGBA')); H, W = a.shape[:2]
        yy, xx = np.mgrid[:H, :W]
        keep = (xx >= xl) & (xx <= xr) & (yy >= yt + 0.47 * (xx - xl))
        a[~keep] = 0
        ys, xs = np.where(a[..., 3] > 0); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        k = plaque_slope(a); a = unmirror_plaque(a, k, strict=True)
        if n == 7: a = match_casing(a, f'{D2}/06_door.png')
        Image.fromarray(a).save(f'{D2}/{n:02d}_door.png'); print('4B', n, 'plaque slope %.2f' % k, a.shape)
def main():
    main_4b()
    for n, xl in CUT.items():
        a = np.array(Image.open(f'{D}/{n}.png').convert('RGBA')); H, W = a.shape[:2]
        yy, xx = np.mgrid[:H, :W]
        keep = (xx >= xl) & (xx <= 118) & (yy >= 31 + 0.46 * (xx - 23))     # below the casing's top edge (2:1 wall slope)
        a[~keep] = 0
        ys, xs = np.where(a[..., 3] > 0); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        a = unmirror_plaque(a, PK[n])
        if n == 14: a = match_casing(a, f'{D}/13_door.png')
        Image.fromarray(a).save(f'{D}/{n}_door.png'); print(n, a.shape, '->', a.shape)
if __name__ == '__main__':
    main()
