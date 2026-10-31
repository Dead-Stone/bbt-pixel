"""Downscale sliced AI figures into 128x128 game frames (pivot (64,116) = floor point under the feet).

Height is actor-matched exactly like the rig (tools/rig/cast.py REAL_CM, 100 px = 185 cm): crown row =
round(116 - 100*cm/185); soles end on row 119 (the rig's feet also reach 118-120, the near edge of the sole
sits in front of the ground point), so AI frames and rig frames line up in-world.

Pipeline per character (all 5 views share one palette, so the colours cannot drift between facings):
  1. premultiplied-alpha area (BOX) resample of the cut-out, alpha >= 0.5 -> opaque
  2. a light unsharp pass on the downscaled colour (recovers the eye/mouth/outline contrast that area-averaging smears)
  3. palette: weighted k-means (sqrt count weights so small but important colours like eye whites survive), <= K colours,
     nearest-colour mapping, no dithering
  4. outline: every silhouette pixel (4-neighbour of transparency) is forced dark (palette colour nearest to 0.42x itself)
  5. pixfix: spurs removed, tiny islands removed, <=6 px holes filled, specks (orphan pixels within 48 RGB of a neighbour)
     snapped to that neighbour -- the same rules tools/v2/audit.py checks, so the result audits clean
"""
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

REAL_CM = dict(sheldon=185, raj=171, penny=167, leonard=165, howard=164, amy=163, bernadette=149)
PIV = (64, 116); SOLE = 119; W = H = 128


def lum(c):
    c = np.asarray(c, float); return 0.299 * c[..., 0] + 0.587 * c[..., 1] + 0.114 * c[..., 2]


def area_resize(rgba, size):
    a = rgba[..., 3].astype(np.float32) / 255
    chans = []
    for i in range(3):
        chans.append(np.array(Image.fromarray(rgba[..., i].astype(np.float32) * a, 'F').resize(size, Image.BOX)))
    A = np.array(Image.fromarray(a, 'F').resize(size, Image.BOX))
    rgb = np.dstack(chans) / np.maximum(A, 1e-6)[..., None]
    return np.clip(rgb, 0, 255), A


def unsharp(rgb, mask, amt=0.45):
    # blur only over opaque pixels (so the transparent outside does not bleed in)
    m = mask.astype(float)
    bl = np.dstack([ndi.gaussian_filter(rgb[..., i] * m, 0.8) for i in range(3)]) / np.maximum(ndi.gaussian_filter(m, 0.8), 1e-6)[..., None]
    return np.clip(rgb + amt * (rgb - bl), 0, 255)


def kmeans(cols, w, k, it=30, seed=0):
    rng = np.random.default_rng(seed)
    # k-means++ init
    C = [cols[rng.choice(len(cols), p=w / w.sum())]]
    for _ in range(1, k):
        d = np.min(((cols[:, None] - np.array(C)[None]) ** 2).sum(-1), 1) * w
        C.append(cols[rng.choice(len(cols), p=d / d.sum())])
    C = np.array(C, float)
    for _ in range(it):
        lab = np.argmin(((cols[:, None] - C[None]) ** 2).sum(-1), 1)
        for j in range(k):
            s = lab == j
            if s.any(): C[j] = (cols[s] * w[s, None]).sum(0) / w[s].sum()
    return np.round(C).astype(np.uint8)


def nearest(pal, rgb):
    d = ((rgb[..., None, :].astype(float) - pal[None].astype(float)) ** 2).sum(-1)
    return pal[np.argmin(d, -1)]


N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
N4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def edge_mask(op):
    p = np.pad(op, 1)
    tr = np.zeros_like(op)
    for dy, dx in N4: tr |= ~p[1 + dy:1 + dy + op.shape[0], 1 + dx:1 + dx + op.shape[1]]
    return op & tr


def outline(img, pal):
    op = img[..., 3] > 0
    e = edge_mask(op)
    rgb = img[..., :3].astype(float)
    inner = op & ~e
    for y, x in zip(*np.nonzero(e)):
        L = lum(rgb[y, x])
        y0, y1, x0, x1 = max(0, y - 2), y + 3, max(0, x - 2), x + 3
        ii = inner[y0:y1, x0:x1]
        Lin = lum(rgb[y0:y1, x0:x1][ii]).max() if ii.any() else 255
        if L > 62 and L > Lin - 30:
            tgt = rgb[y, x] * 0.42
            c = nearest(pal, tgt[None])[0]
            if lum(c) > 62 and lum(c) > Lin - 30:   # palette has nothing dark enough near that hue
                c = np.clip(tgt, 0, 255).astype(np.uint8)
            img[y, x, :3] = c
    return img


def pixfix(img, rounds=6):
    for _ in range(rounds):
        changed = 0
        op = img[..., 3] > 0
        # spurs: <=1 opaque 8-neighbour
        cnt = sum(np.roll(np.roll(op, dy, 0), dx, 1) for dy, dx in N8)
        sp = op & (cnt <= 1)
        if sp.any(): img[sp] = 0; changed += sp.sum(); op = img[..., 3] > 0
        # islands: keep the largest 8-connected component
        lab, n = ndi.label(op, np.ones((3, 3)))
        if n > 1:
            s = np.bincount(lab.ravel()); s[0] = 0; big = s.argmax()
            kill = op & (lab != big); img[kill] = 0; changed += kill.sum(); op = img[..., 3] > 0
        # holes <= 6 px: fill with the mean of the surrounding colours, snapped to the most common neighbour
        hl, hn = ndi.label(~op)
        for j in range(1, hn + 1):
            m = hl == j
            if m.sum() <= 6 and not (m[0].any() or m[-1].any() or m[:, 0].any() or m[:, -1].any()):
                ring = ndi.binary_dilation(m) & ~m
                cols = [tuple(c) for c in img[ring][:, :3]]
                c = max(set(cols), key=cols.count)
                img[m, :3] = c; img[m, 3] = 255; changed += m.sum()
        op = img[..., 3] > 0
        # specks: orphan pixel whose nearest neighbour colour is within 48 and >=3 opaque neighbours -> snap to it
        rgb = img[..., :3].astype(int)
        for y, x in zip(*np.nonzero(op)):
            if y in (0, H - 1) or x in (0, W - 1): continue
            same = False; best = None; bd = 1e9; nop = 0
            for dy, dx in N8:
                if not op[y + dy, x + dx]: continue
                nop += 1
                d = np.sqrt(((rgb[y + dy, x + dx] - rgb[y, x]) ** 2).sum())
                if d == 0: same = True; break
                if d < bd: bd, best = d, (y + dy, x + dx)
            if not same and nop >= 3 and bd < 48:
                img[y, x, :3] = img[best][:3]; rgb[y, x] = rgb[best]; changed += 1
        if not changed: break
    return img


def place(cut_rgba, cid):
    """scale a cut-out so crown->sole matches the actor height, return (rgb float, alpha float) on a 128 canvas"""
    cm = REAL_CM[cid]
    crown = int(round(PIV[1] - 100 * cm / 185.0))
    th = SOLE - crown + 1
    h, w = cut_rgba.shape[:2]
    s = th / h
    nw = max(1, int(round(w * s)))
    rgb, A = area_resize(cut_rgba, (nw, th))
    # feet centre: opaque columns in the lowest 8% of the figure
    fb = A[int(th * 0.92):] >= 0.5
    xs = np.nonzero(fb.any(0))[0]
    fx = (xs.min() + xs.max()) / 2 if len(xs) else nw / 2
    ox = int(round(PIV[0] - fx))
    C = np.zeros((H, W, 3)); AA = np.zeros((H, W))
    C[crown:crown + th, ox:ox + nw] = rgb; AA[crown:crown + th, ox:ox + nw] = A
    return C, AA, s


def convert_character(cid, cuts, dirs, k=28, sharpen=0.45):
    """cuts: {dir: rgba uint8 hi-res}; returns {dir: 128x128 RGBA uint8}, palette"""
    staged = {}
    for d in dirs:
        C, A, s = place(cuts[d], cid)
        m = A >= 0.5
        if sharpen: C = unsharp(C, m, sharpen)
        staged[d] = (C, m)
    allc = np.concatenate([staged[d][0][staged[d][1]] for d in dirs]).round().astype(np.uint8)
    u, cnt = np.unique(allc, axis=0, return_counts=True)
    pal = kmeans(u.astype(float), np.sqrt(cnt.astype(float)), k)
    out = {}
    for d in dirs:
        C, m = staged[d]
        img = np.zeros((H, W, 4), np.uint8)
        img[m, :3] = nearest(pal, C[m]); img[m, 3] = 255
        img = pixfix(img)
        img = outline(img, pal)
        img = pixfix(img)
        out[d] = audit_fix(img, pal)
    return out, pal


def audit_fix(img, pal=None, rounds=8):
    """make a frame pass tools/v2/audit.py's per-frame checks exactly: outline pixels it flags are darkened
    (palette colour near 0.42x, else scaled until luminance <= 62), specks snap to their nearest neighbour colour,
    then the pixfix rules run again"""
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'v2'))
    from audit import audit_frame
    for _ in range(rounds):
        r = audit_frame(img)
        bad = {k: r[k] for k in ('hole', 'island', 'speck', 'spur', 'outline')}
        if not any(m.any() for m in bad.values()): break
        for y, x in zip(*np.nonzero(r['outline'])):
            c = img[y, x, :3].astype(float); t = c * 0.42
            if pal is not None:
                n = nearest(pal, t[None])[0]
                if lum(n) <= 62: img[y, x, :3] = n; continue
            k = 1.0
            while lum(c * k) > 62: k -= 0.05
            img[y, x, :3] = np.clip(c * k, 0, 255).astype(np.uint8)
        rgb = img[..., :3].astype(int)
        for y, x in zip(*np.nonzero(r['speck'])):
            best, bd = None, 1e9
            for dy, dx in N8:
                yy, xx = y + dy, x + dx
                if 0 <= yy < H and 0 <= xx < W and img[yy, xx, 3]:
                    d = ((rgb[yy, xx] - rgb[y, x]) ** 2).sum()
                    if d < bd: bd, best = d, (yy, xx)
            if best: img[y, x, :3] = img[best][:3]
        img = pixfix(img, rounds=2)
    return img
