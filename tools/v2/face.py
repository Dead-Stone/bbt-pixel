"""v2 face pass: at ~12 px head width a plain downscale smears eyes/brows/mouth into blobs.  Feature
positions are detected on the full-res AI master art and redrawn as clean, deliberate pixel features
(eyes 1x2, lash pixel for the women, 2-px brows, nose shade, mouth) on the palette-indexed master."""
import json, numpy as np
from PIL import Image
from scipy import ndimage as ndi
import sys
sys.path.insert(0, '/workspace/bbt-pixel/tools')
ROOT = '/workspace/bbt-pixel'
DIRS5 = ['S', 'SW', 'W', 'NW', 'N']
FEM = {'penny', 'bernadette', 'amy'}

def lum(c): return np.asarray(c, float) @ np.array([0.299, 0.587, 0.114])

def nearest(pal, c, mask=None):
    d = ((pal.astype(float) - np.asarray(c, float)) ** 2).sum(1)
    if mask is not None: d = d + 1e9 * ~mask
    return int(d.argmin())

def detect(cid, d, fit):
    import char_rig as R
    R.set_character(cid)
    rgb = np.array(Image.open(f'{ROOT}/characters/{cid}/refs/v2_master/master_strip.jpg').convert('RGB')).astype(float)
    i = DIRS5.index(d); W = rgb.shape[1]; x0, x1 = i * W // 5, (i + 1) * W // 5
    by0, by1 = fit['by0'], fit['by1']; hz1 = by0 + int(0.27 * (by1 - by0))
    sub = rgb[by0:hz1, x0:x1]
    sr = np.asarray(R.C['skin'], float); Rr = sub[..., 0] + 1
    skin = (abs(sub[..., 2] / Rr - sr[2] / sr[0]) < 0.09) & (abs(sub[..., 1] / Rr - sr[1] / sr[0]) < 0.07) & (lum(sub) > 110)
    skin_c = np.median(sub[skin], 0)
    skin = ndi.binary_opening(skin, iterations=1)
    lab, n = ndi.label(skin); sz = np.bincount(lab.ravel()); sz[0] = 0
    face = lab == sz.argmax()
    hull = ndi.binary_fill_holes(ndi.binary_closing(face, iterations=4))
    ys, xs = np.where(hull); fy0, fy1 = ys.min(), ys.max(); fh = fy1 - fy0
    L = lum(sub)
    feat = hull & ~face & (L < L[face].mean() - 40)
    fl, fn = ndi.label(feat); comps = []
    for k in range(1, fn + 1):
        yy, xx = np.where(fl == k)
        if len(yy) < 6: continue
        comps.append(dict(n=len(yy), cy=yy.mean(), cx=xx.mean(), w=xx.max() - xx.min() + 1, h=yy.max() - yy.min() + 1,
                          col=sub[fl == k].mean(0), rel=(yy.mean() - fy0) / fh))
    eyes = sorted([c for c in comps if 0.25 < c['rel'] < 0.62 and c['w'] < 0.3 * (xs.max() - xs.min())],
                  key=lambda c: -c['n'])[:2 if d != 'W' else 1]
    mouth = sorted([c for c in comps if 0.68 < c['rel'] < 0.97], key=lambda c: -c['n'])[:1]
    def T(cx, cy):   # full-res strip (sub coords) -> 128 frame
        sx = cx + x0; sy = cy + by0
        return ((sx - fit['bx0']) / fit['s'] + fit['ox'], (sy - fit['by0']) / fit['s'] + fit['oy'])
    fcx = xs.mean()
    out = dict(eyes=[(*T(e['cx'], e['cy']), e['w'] / fit['s']) for e in sorted(eyes, key=lambda e: e['cx'])],
               mouth=[(*T(m['cx'], m['cy']), m['w'] / fit['s'], m['col']) for m in mouth],
               face_cx=T(fcx, 0)[0], skin=skin_c, chin=T(0, fy1)[1], top=T(0, fy0)[1])
    return out

def face_pass(cid, d, idx, pal, fit):
    import char_rig as R
    f = detect(cid, d, fit)
    out = idx.copy(); P = pal.astype(float); PL = lum(P)
    skin_i = nearest(pal, f['skin'])
    skin_mask_pal = np.sqrt(((P - P[skin_i]) ** 2).sum(1)) < 55
    # face area in the master: skin pixels in the head zone + enclosed blobs (smeared features) -> skin
    hz = np.zeros_like(out, bool); hz[:int(f['chin']) + 1] = True; hz[:max(int(f['top']) - 3, 0)] = False
    sk = hz & (out >= 0) & skin_mask_pal[np.maximum(out, 0)]
    enc = ndi.binary_fill_holes(sk) & ~sk & hz
    # also: dark smears hanging on the face between eye line and mouth (not hair: hair lies above eye line)
    ey = np.mean([e[1] for e in f['eyes']]) if f['eyes'] else f['top'] + 4
    out[enc] = skin_i
    for y in range(int(ey) - 1, int(f['chin'])):
        for x in range(128):
            if out[y, x] >= 0 and not skin_mask_pal[out[y, x]] and PL[out[y, x]] < PL[skin_i] - 50:
                # dark pixel inside the face span on this row?
                row = sk[y]; xs = np.where(row)[0]
                if len(xs) and xs.min() < x < xs.max(): out[y, x] = skin_i
    darkest = int(np.argmin(PL))
    skin_sh = nearest(pal, P[skin_i] * 0.80, skin_mask_pal | (PL < PL[skin_i]))
    hair = np.asarray(R.C['hair'], float)
    brow_c = nearest(pal, hair * (0.62 if lum(hair) > 120 else 0.85), PL < PL[skin_i] - 30)
    fem = cid in FEM
    for (ex, eyy, ew) in f['eyes']:
        X = int(np.floor(ex)); Y = int(np.floor(eyy - 0.5))
        outer = -1 if ex < f['face_cx'] else 1
        if d == 'W': outer = 1
        out[Y, X] = darkest; out[Y + 1, X] = darkest
        if fem:
            out[Y, X + outer] = darkest           # lash flick at the outer top
        bx = [X, X + outer] if d != 'W' else [X, X - 1]
        for b in bx:
            if 0 <= Y - 2 < 128: out[Y - 2, b] = brow_c
    if len(f['eyes']) == 2 and d == 'S':
        nx = int(round((f['eyes'][0][0] + f['eyes'][1][0]) / 2 - 0.5)); ny = int(np.floor(ey - 0.5)) + 3
        out[ny, nx] = skin_sh
    elif d == 'SW' and f['eyes']:
        ex = f['eyes'][0][0]; out[int(np.floor(ey - 0.5)) + 3, int(np.floor(ex)) + 1] = skin_sh
    for (mx, my, mw, mcol) in f['mouth']:
        lip = nearest(pal, (190, 85, 95)) if fem else skin_sh
        Y = int(round(my - 0.5)); w = 2 if d != 'W' else 1
        X0 = int(round(mx - w / 2))
        for x in range(X0, X0 + w): out[Y, x] = lip
    return out
