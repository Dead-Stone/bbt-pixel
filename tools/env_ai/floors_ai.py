"""Floor tiles + wall colours from the ChatGPT floors/walls sheet.
Floor diamonds are unprojected to a square texture, made seamless (narrow border crossfade with the half-offset copy),
and re-projected onto the game's 128x64 iso tile mask; the kitchen checker is regenerated geometrically from its two colours."""
import os
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SL = f'{ROOT}/refs_ai/chatgpt/env/sliced/floors_walls_v1'
MASK = np.array(Image.open(f'{ROOT}/templates/iso_floor_tile_128x64.png').convert('RGBA'))[..., 3] > 0
TILES = {'floor_4a_wood_a': 0, 'floor_4a_wood_b': 1, 'floor_4b_wood_a': 2, 'floor_4b_wood_b': 2, 'floor_hall': 4}
N = 64
def _src(i): return np.array(Image.open(f'{SL}/{i:02d}.png').convert('RGBA')).astype(float)
def unproject(a):
    h, w = a.shape[:2]; dh = w / 2.0          # top surface diamond = full width, height w/2 (the rest is the slab edge)
    S = np.zeros((N, N, 3))
    for j in range(N):
        for i in range(N):
            u, v = (i + 0.5) / N, (j + 0.5) / N
            sx = (u - v) * w / 2 + w / 2; sy = (u + v) * dh / 2
            # shrink 6% toward the centre to stay off the outline/edge
            sx = w / 2 + (sx - w / 2) * 0.9; sy = dh / 2 + (sy - dh / 2) * 0.9
            S[j, i] = a[min(int(sy), h - 1), min(int(sx), w - 1), :3]
    return S
def seamless(S, band=8):
    r = np.roll(np.roll(S, N // 2, 0), N // 2, 1)
    d = np.minimum.outer(np.minimum(np.arange(N), N - 1 - np.arange(N)), np.minimum(np.arange(N), N - 1 - np.arange(N)))
    wgt = np.clip(d / band, 0, 1)[..., None]
    return S * wgt + r * (1 - wgt)
def project(S):
    out = np.zeros((64, 128, 4), np.uint8)
    for j in range(64):
        for i in range(128):
            if not MASK[j, i]: continue
            sx = i + 0.5 - 64; sy = j + 0.5
            x = (sx / 64 + sy / 32) / 2; y = (sy / 32 - sx / 64) / 2
            out[j, i, :3] = S[min(max(int(y * N), 0), N - 1), min(max(int(x * N), 0), N - 1)]; out[j, i, 3] = 255
    return out
def checker():
    a = _src(3); m = a[..., 3] > 0; px = a[m][:, :3]
    lum = px @ np.array([0.3, 0.59, 0.11]); lt = np.median(px[lum > np.percentile(lum, 70)], 0); dk = np.median(px[lum < np.percentile(lum, 30)], 0)
    S = np.zeros((N, N, 3))
    for j in range(N):
        for i in range(N):
            c = ((i * 2 // N) + (j * 2 // N)) % 2
            S[j, i] = lt if c == 0 else dk
            if i % (N // 2) == 0 or j % (N // 2) == 0: S[j, i] = S[j, i] * 0.82   # grout line (tile-edge, seamless)
    return S
_T = None
def raw_tiles():
    global _T
    if _T is None:
        _T = {k: project(seamless(unproject(_src(i)))) for k, i in TILES.items()}
        _T['floor_4a_kitchen'] = project(checker())
    return _T
def wall_samples():
    return [_src(i)[_src(i)[..., 3] > 0][:, :3] for i in (12, 14, 23)]
def wall_colours():
    """representative colours sampled from the beige (12, 4A/hall) and cream (14, 4B) wall pieces:
    face (lit), face shaded, cap highlight, baseboard"""
    out = {}
    for nm, i in (('beige', 12), ('cream', 14)):
        a = _src(i); m = a[..., 3] > 0; h, w = m.shape
        mid = a[int(h * 0.3):int(h * 0.7), int(w * 0.35):int(w * 0.65)]; mm = mid[..., 3] > 0
        face = np.median(mid[mm][:, :3], 0)
        side = a[int(h * 0.3):int(h * 0.7), int(w * 0.8):int(w * 0.95)]; sm = side[..., 3] > 0
        shade = np.median(side[sm][:, :3], 0) if sm.any() else face * 0.85
        cap = np.percentile(a[:int(h * 0.08)][a[:int(h * 0.08)][..., 3] > 0][:, :3], 85, axis=0)
        base = np.median(a[int(h * 0.88):int(h * 0.96), int(w * 0.3):int(w * 0.7)][..., :3].reshape(-1, 3), 0)
        out[nm] = dict(face=face, shade=shade, hi=cap, base=base)
    return out
