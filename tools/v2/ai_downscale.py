"""Method (a): AI-redrawn strip -> 128x128 sprite frames. Per figure: bbox fit to the v1 frame's bbox
(feet on the pivot line, same height), palette-snap at full res, mode-downsample per target cell,
orphan cleanup, then a selective outline (darkest ramp tone of the neighbouring material)."""
import sys, json, numpy as np
from PIL import Image
sys.path.insert(0, '/workspace/bbt-pixel/tools')
from sprite_common import load_gpl
ROOT = '/workspace/bbt-pixel/characters'

def fig_boxes(rgb, n=5):
    nonbg = (np.abs(rgb.astype(int) - 255).sum(-1) > 60)
    H, W = nonbg.shape; out = []
    for i in range(n):
        x0, x1 = i * W // n, (i + 1) * W // n
        m = nonbg[:, x0:x1]; ys, xs = np.where(m)
        out.append((x0 + xs.min(), ys.min(), x0 + xs.max() + 1, ys.max() + 1))
    return out, nonbg

def v1_box(fr):
    a = fr[..., 3] > 0; ys, xs = np.where(a); return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1

def convert(cid, ai_path, v1_frames):
    pal = load_gpl(f'/workspace/bbt-pixel/palettes/bbt_{cid}.gpl'); names = list(pal); cols = np.array([pal[k] for k in names], float)
    im = np.array(Image.open(ai_path).convert('RGB')); boxes, nonbg = fig_boxes(im, len(v1_frames))
    lab = lambda c: c * np.array([0.30, 0.59, 0.11]) ** 0.5
    res = []
    for (bx0, by0, bx1, by1), v1 in zip(boxes, v1_frames):
        vx0, vy0, vx1, vy1 = v1_box(v1); th = vy1 - vy0
        s = (by1 - by0) / th                 # source px per sprite px
        tw = int(round((bx1 - bx0) / s)); cx = (vx0 + vx1) / 2
        ox = int(round(cx - tw / 2)); oy = vy1 - th
        crop = im[by0:by1, bx0:bx1].astype(float); cm = nonbg[by0:by1, bx0:bx1]
        d = ((lab(crop.reshape(-1, 1, 3)) - lab(cols[None])) ** 2).sum(-1); idx = d.argmin(1).reshape(cm.shape)
        out = np.zeros((128, 128, 4), np.uint8)
        for ty in range(th):
            for tx in range(tw):
                ys = slice(int(ty * s), max(int((ty + 1) * s), int(ty * s) + 1)); xs = slice(int(tx * s), max(int((tx + 1) * s), int(tx * s) + 1))
                mm = cm[ys, xs]
                if mm.mean() < 0.5: continue
                v = idx[ys, xs][mm]; k = np.bincount(v).argmax()
                X, Y = ox + tx, oy + ty
                if 0 <= X < 128 and 0 <= Y < 128: out[Y, X, :3] = cols[k]; out[Y, X, 3] = 255
        res.append(cleanup(out, pal))
    return res

def cleanup(img, pal):
    img = img.copy(); a = img[..., 3] > 0
    key = img[..., 0].astype(int) * 65536 + img[..., 1].astype(int) * 256 + img[..., 2]
    for _ in range(2):
        kp = np.pad(np.where(a, key, -1), 1, constant_values=-1)
        nb = np.stack([kp[:-2, 1:-1], kp[2:, 1:-1], kp[1:-1, :-2], kp[1:-1, 2:]], -1)
        for y, x in zip(*np.where(a)):
            n = nb[y, x]
            if (n != key[y, x]).all():
                v, c = np.unique(n[n >= 0], return_counts=True)
                if len(v) and c.max() >= 2: key[y, x] = v[c.argmax()]
        # drop single isolated alpha pixels
        ap = np.pad(a, 1); cnt = ap[:-2, 1:-1].astype(int) + ap[2:, 1:-1] + ap[1:-1, :-2] + ap[1:-1, 2:]
        a = a & (cnt >= 1)
    img[..., 0] = key // 65536; img[..., 1] = (key // 256) % 256; img[..., 2] = key % 256; img[..., 3] = np.where(a, 255, 0)
    return img
