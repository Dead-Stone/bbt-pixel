"""4th-floor wall segments from the approved fixups_v2 sheet (#02 wall L, #03 wall R, #04 wall L window, #05 wall R window).

Each sheet piece is one wall section with a visible cap and end face.  The front face (cap top edge .. baseboard bottom, end
face excluded) is resampled column-by-column onto the engine's 1-tile wall canvas (64 x 224, top vertex anchor), so segments
tile seamlessly along a wall line; 2x2 supersampled, tinted to the room's wall colour, snapped to the env palette.
Night windows: the sheet's pale panes are repainted with the Pasadena night sky + skyline used by the procedural walls.
Also: door_pillar() = a full-height wall section of arbitrary length around a front door (cutaway view: doors sit in a wall)."""
import os
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
D = f'{ROOT}/refs_ai/chatgpt/env/sliced/fixups_v2'
SRC = {None: (2, 3), 'window': (4, 5)}       # feature -> (br piece "wall L", bl piece "wall R")
_G = {}
def _src(feature, side):
    """sheet piece in the 'br' shape (top edge descending right, end face on the right) + its face geometry"""
    k = (feature, side)
    if k in _G: return _G[k]
    n = SRC[feature][0 if side == 'br' else 1]
    a = np.array(Image.open(f'{D}/{n:02d}.png').convert('RGBA')).astype(float)
    if side == 'bl': a = a[:, ::-1].copy()          # wall R mirrored -> br shape (keeps its own, darker shading)
    m = a[..., 3] > 0; H, W = m.shape
    cols = [c for c in range(W) if m[:, c].any()]
    top = np.array([np.where(m[:, c])[0][0] if m[:, c].any() else 0 for c in range(W)])
    bot = np.array([np.where(m[:, c])[0][-1] if m[:, c].any() else 0 for c in range(W)])
    hgt = bot - top
    xl = next(c for c in cols if hgt[c] > 0.8 * hgt.max()) + 2               # skip the 1-2 px left outline
    xr = int(np.argmax(bot[:int(W * 0.97)])) - 1                            # front-bottom corner = start of the end face
    xs = np.arange(xl + 4, xr - 3)
    pt = np.polyfit(xs, top[xs], 1); pb = np.polyfit(xs, bot[xs], 1)
    lum = a[..., :3] @ np.array([0.3, 0.59, 0.11])
    band = [(int(np.polyval(pt, c) + 0.82 * (np.polyval(pb, c) - np.polyval(pt, c))), c) for c in xs]
    face = np.median(np.array([a[r, c, :3] for r, c in band]), 0)
    _G[k] = (a, xl, xr, pt, pb, face)
    return _G[k]

def _sky(t, u, c, r, C, hsh):
    """night sky over Pasadena inside a pane (t across the wall 0..1, u up the pane 0..1)"""
    bh = 0.18 + 0.3 * hsh(int(t * 20), 1, 2)
    if u < bh:
        return C['lamp_warm'] if hsh(int(t * 70), int(u * 40), 4) < 0.12 else C['shadow_violet']
    if hsh(int(t * 90), int(u * 90) + r, 8) < 0.008: return C['white_hi']
    return C['comic_blue'] if u > 0.62 or (u > 0.56 and (c + r) % 2) else C['screen_glow']

def face_map(feature, side, mask, tint, C, hsh, night=True, x_span=None):
    """resample the sheet face onto a wall canvas mask (br shape; caller mirrors for bl).  x_span=(u0,u1): the part of the
    sheet face (0..1 along the wall) used across the canvas width (door pillars use the plain-wall middle)"""
    a, xl, xr, pt, pb, face = _src(feature, side)
    H, W = mask.shape; out = np.zeros((H, W, 4), np.uint8)
    u0, u1 = x_span or (0.0, 1.0)
    ratio = np.asarray(tint, float) / _src(None, 'br')[5]                    # one tint per room: keeps the sheet's L/R shading
    pane = (a[..., 2] > a[..., 0] + 18) & (a[..., 2] > 110) & (a[..., 3] > 0)
    if feature == 'window':     # per source column: the pane's top / bottom row (the window is sheared along the wall)
        ptop = np.array([np.where(pane[:, x])[0][0] if pane[:, x].any() else 0 for x in range(a.shape[1])])
        pbot = np.array([np.where(pane[:, x])[0][-1] if pane[:, x].any() else 1 for x in range(a.shape[1])])
    for c in range(W):
        rows = np.where(mask[:, c])[0]
        if len(rows) == 0: continue
        rt, rb = rows[0], rows[-1]
        for r in rows:
            acc = []; pn = 0
            for dx in (0.25, 0.75):
                for dy in (0.25, 0.75):
                    u = u0 + (u1 - u0) * (c + dx) / W; sx = xl + u * (xr - xl)
                    v = (r - rt + dy) / (rb - rt + 1)
                    tt, bb = np.polyval(pt, sx), np.polyval(pb, sx)
                    sy = tt + v * (bb - tt)
                    yi, xi = int(np.clip(sy, 0, a.shape[0] - 1)), int(np.clip(sx, 0, a.shape[1] - 1))
                    if a[yi, xi, 3] > 0: acc.append(a[yi, xi, :3]); pn += pane[yi, xi]
            if not acc: continue
            col = np.mean(acc, 0)
            if feature == 'window' and pn >= 2 and night:
                uu = (pbot[xi] - sy) / max(1, pbot[xi] - ptop[xi])
                col = np.array(_sky((c + 0.5) / W, float(np.clip(uu, 0, 1)), c, r, C, hsh), float)
            elif not (feature == 'window' and pn >= 2):
                col = np.clip(col * ratio, 0, 255)
            out[r, c, :3] = col; out[r, c, 3] = 254 if (feature == 'window' and pn >= 2 and night) else 255   # 254 = sky (keeps base-palette colours)
    return out

PAL_TINTS = [(192, 152, 92), (228, 203, 158), (168, 148, 108)]   # 4A / 4B / hall wall face colours (build_env.WALLMAT)
def palette_samples():
    """sheet wall pixels as they will be drawn in each room (feeds the env palette, so the walls snap cleanly)"""
    base = _src(None, 'br')[5]; out = []
    for feature in SRC:
        for side in ('br', 'bl'):
            a = _src(feature, side)[0]
            pane = (a[..., 2] > a[..., 0] + 18) & (a[..., 2] > 110)
            px = a[(a[..., 3] > 0) & ~pane][:, :3]
            for t in PAL_TINTS: out.append(np.clip(px * (np.array(t) / base), 0, 255))
    return out
