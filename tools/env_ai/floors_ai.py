"""Floor tiles + wall colours from the ChatGPT floors/walls sheet.
Floor diamonds are unprojected to a square texture, made seamless (narrow border crossfade with the half-offset copy),
and re-projected onto the game's 128x64 iso tile mask; the kitchen checker is re-laid from the fixups sheet's checker squares."""
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
FX18 = f'{ROOT}/refs_ai/chatgpt/env/sliced/fixups_v1/18.png'
def checker():
    """kitchen checker from the fixups sheet (fixups_v1/18, a 2x2 tile with 3x3 squares): the top diamond is unprojected,
    one cream and one charcoal square (texture + grout) are cut out and re-laid as 2x2 squares per game tile (seamless)"""
    a = np.array(Image.open(FX18).convert('RGBA')).astype(float); m = a[..., 3] > 0; ys, xs = np.where(m)
    T = np.array([xs[ys == ys.min()].mean(), ys.min()]); L = np.array([xs.min(), ys[xs == xs.min()].mean()])
    R = np.array([xs.max(), ys[xs == xs.max()].mean()])
    M = 96; U = np.zeros((M, M, 3))
    for j in range(M):
        for i in range(M):
            p = T + (i + .5) / M * (R - T) + (j + .5) / M * (L - T); U[j, i] = a[int(p[1]), int(p[0]), :3]
    q = M // 3; h = N // 2
    def sq(r, c):
        t = U[r*q + 2:(r+1)*q - 2, c*q + 2:(c+1)*q - 2]
        return np.array(Image.fromarray(t.astype(np.uint8)).resize((h, h), Image.NEAREST)).astype(float)
    lt, dk = sq(1, 1), sq(1, 0)
    S = np.zeros((N, N, 3))
    for r in range(2):
        for c in range(2): S[r*h:(r+1)*h, c*h:(c+1)*h] = lt if (r + c) % 2 == 0 else dk
    g = (np.arange(N) % h == 0); S[g, :] *= 0.85; S[:, g] *= 0.85      # grout on the square edges (seamless)
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
