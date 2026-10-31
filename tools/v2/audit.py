"""Pixel-quality audit of a character's sprite frames (main sheet + sit sheet): every anim x dir x frame.
Flags per frame
  hole    enclosed transparent pocket of <= HOLE_MAX px inside the silhouette (a tear, not a real gap)
  island  opaque 8-connected component detached from the main body
  speck   orphan pixel: no same-colour 8-neighbour and only a near shade (RGB dist < 48) of a neighbour = texture
          noise (a pixel far from every neighbour colour is a deliberate detail: pupil, nostril, button, eye glint)
  spur    1-px protrusion: an opaque pixel with <= 1 opaque 8-neighbour
  outline silhouette-edge pixel that is not dark (outline broken / missing): edge pixels must be darker than the
          interior pixel behind them (or absolutely dark)
  flicker colour changes in the head between consecutive idle/walk frames after the best integer re-alignment
Usage: python3 tools/v2/audit.py <cid> [--sheet out.png] [--json out.json] [--src characters dir]"""
import os, sys, json, argparse, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOLE_MAX = 6
LW = np.array([0.299, 0.587, 0.114])
K8 = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
K4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]

def frames_of(cid, src=None):
    base = src or os.path.join(ROOT, 'characters', cid)
    out = []
    for suf in ('', '_sit'):
        jp = os.path.join(base, f'chr_{cid}{suf}.json')
        if not os.path.exists(jp): continue
        J = json.load(open(jp)); sh = np.array(Image.open(os.path.join(base, f'chr_{cid}{suf}.png')).convert('RGBA'))
        for f in J['frames']:
            r = f['frame']; out.append((f['filename'][len(f'chr_{cid}_'):], sh[r['y']:r['y'] + r['h'], r['x']:r['x'] + r['w']].copy()))
    return out

def shift(a, dy, dx, fill):
    P = np.pad(a, [(2, 2), (2, 2)] + [(0, 0)] * (a.ndim - 2), constant_values=fill)
    H, W = a.shape[:2]; return P[2 + dy:2 + dy + H, 2 + dx:2 + dx + W]

def audit_frame(im):
    op = im[..., 3] > 0; rgb = im[..., :3].astype(int)
    key = np.where(op, rgb[..., 0] * 65536 + rgb[..., 1] * 256 + rgb[..., 2], -1)
    L = np.where(op, rgb @ LW, np.nan)
    res = {}
    # holes
    enc = ndi.binary_fill_holes(op) & ~op; lab, n = ndi.label(enc)
    sz = np.bincount(lab.ravel()); hp = np.isin(lab, [i for i in range(1, n + 1) if sz[i] <= HOLE_MAX])
    res['hole'] = hp
    # islands
    lab, n = ndi.label(op, structure=np.ones((3, 3)))
    if n > 1:
        sz = np.bincount(lab.ravel()); sz[0] = 0; res['island'] = (lab > 0) & (lab != sz.argmax())
    else: res['island'] = np.zeros_like(op)
    # specks + spurs
    same = np.zeros(op.shape, int); nop = np.zeros(op.shape, int)
    nl = []
    for dy, dx in K8:
        k2 = shift(key, dy, dx, -1); same += (k2 == key) & op; nop += k2 >= 0
        nl.append(shift(L, dy, dx, np.nan))
    nl = np.stack(nl, -1)
    with np.errstate(all='ignore'):
        mn = np.nanmin(nl, -1); mx = np.nanmax(nl, -1)
    # an orphan that is only a near shade of a neighbour (RGB distance < 48) is noise; a pixel far from every
    # neighbour colour is a deliberate single-pixel detail (pupil, nostril, button, highlight)
    dmin = np.full(op.shape, 1e9)
    for dy, dx in K8:
        r2 = np.stack([shift(rgb[..., i], dy, dx, -999) for i in range(3)], -1)
        okn = shift(key, dy, dx, -1) >= 0
        dmin = np.where(okn, np.minimum(dmin, np.sqrt(((r2 - rgb) ** 2).sum(-1))), dmin)
    res['speck'] = op & (same == 0) & (dmin < 48) & (nop >= 3)
    res['spur'] = op & (nop <= 1)
    # outline: edge pixel must be dark relative to the interior behind it
    edge = np.zeros_like(op)
    for dy, dx in K4: edge |= op & (shift(key, dy, dx, -1) < 0)
    inner = op & ~edge
    bad = np.zeros_like(op)
    for dy, dx in K4:
        # interior pixel on the opposite side of the transparent neighbour
        tr = shift(key, dy, dx, -1) < 0
        # (looking 1-2 px in: at a junction the first pixel behind can be another part's dark line)
        Li = np.where(inner, L, np.nan)
        with np.errstate(all='ignore'):
            Lin = np.fmax(shift(Li, -dy, -dx, np.nan), shift(Li, -2 * dy, -2 * dx, np.nan))
            for ey in (-1, 0, 1):          # an outline pixel at a junction outlines the lightest part beside it
                for ex in (-1, 0, 1):
                    if ey or ex: Lin = np.fmax(Lin, shift(Li, -dy + ey, -dx + ex, np.nan))
        with np.errstate(invalid='ignore'):
            b = edge & tr & ~np.isnan(Lin) & (L > 62) & (L > Lin - 18)
        bad |= b
    res['outline'] = bad
    return res

def head_window(o, rows_n):
    """the head's box: rows crown -> chin, columns spanned by the upper half of the head (+1 px each side).
    The far shoulder rises beside the jaw in 3/4 views; it moves with the arm swing and is not the head."""
    y0 = np.nonzero(o.any(1))[0][0]
    cols = np.nonzero(o[y0:y0 + max(1, rows_n // 2)].any(0))[0]
    w = np.zeros(o.shape, bool); w[y0:y0 + rows_n, max(0, cols[0] - 1):cols[-1] + 2] = True
    return w


def head_flicker(a, b, rows_n=None):
    """colour mismatches in the head box (see head_window) after the best integer shift (|d| <= 2);
    shoulders are left out: swinging arms legitimately change them"""
    oa, ob = a[..., 3] > 0, b[..., 3] > 0
    if not oa.any() or not ob.any(): return 0, None
    rows = head_window(oa, rows_n or HEAD_ROWS)
    ka = np.where(oa, a[..., :3].astype(int) @ [65536, 256, 1], -1)
    kb = np.where(ob, b[..., :3].astype(int) @ [65536, 256, 1], -1)
    best = None
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            kb2 = np.roll(np.roll(kb, dy, 0), dx, 1)
            m = (ka[rows] >= 0) & (kb2[rows] >= 0) & (ka[rows] != kb2[rows])
            u = (ka[rows] >= 0) ^ (kb2[rows] >= 0)
            c = int(m.sum() + u.sum())
            if best is None or c < best[0]: best = (c, dy, dx, m | u)
    mask = np.zeros(oa.shape, bool); mask[rows] = best[3]
    return best[0], mask

KINDS = ['hole', 'island', 'speck', 'spur', 'outline', 'flicker']
COL = {'hole': (255, 0, 255), 'island': (255, 0, 0), 'speck': (0, 200, 255), 'spur': (255, 160, 0), 'outline': (0, 255, 0), 'flicker': (255, 255, 0)}
FLICKER_MAX = 10
HEAD_ROWS = 22

def head_rows_dir_of(cid, src=None):
    jp = os.path.join(src or os.path.join(ROOT, 'characters', cid), f'chr_{cid}.json')
    try: return json.load(open(jp))['meta'].get('audit', {}).get('head_rows_dir') or {}
    except Exception: return {}

def head_rows_of(cid, src=None):
    """a sheet may declare its head height (crown -> chin) in meta.audit.head_rows; default HEAD_ROWS"""
    jp = os.path.join(src or os.path.join(ROOT, 'characters', cid), f'chr_{cid}.json')
    try: return int(json.load(open(jp))['meta'].get('audit', {}).get('head_rows') or HEAD_ROWS)
    except Exception: return HEAD_ROWS

def fidget_of(cid, src=None):
    """meta.audit.fidget = {anim: [frame, ...]}: frames where the head moves on purpose (a glance, a blink)"""
    jp = os.path.join(src or os.path.join(ROOT, 'characters', cid), f'chr_{cid}.json')
    try: return {k: set(v) for k, v in json.load(open(jp))['meta'].get('audit', {}).get('fidget', {}).items()}
    except Exception: return {}

def audit(cid, src=None):
    fr = frames_of(cid, src); rows = []; prev = {}; hr = head_rows_of(cid, src); fid = fidget_of(cid, src)
    hrd = head_rows_dir_of(cid, src)
    for name, im in fr:
        r = audit_frame(im); seq = name.rsplit('_', 1)[0]; anim = seq.rsplit('_', 1)[0]
        fl = 0; flm = np.zeros(im.shape[:2], bool)
        try: k = int(name.rsplit('_', 1)[1])
        except ValueError: k = -1
        deliberate = k in fid.get(anim, ()) or (k - 1) in fid.get(anim, ())
        if anim in ('idle', 'walk') and seq in prev and not deliberate:      # (blink redraws the eyes on purpose)
            fl, m = head_flicker(prev[seq], im, hrd.get(seq.rsplit('_', 1)[-1], hr))
            if fl > FLICKER_MAX and m is not None: flm = m
        prev[seq] = im
        r['flicker'] = flm
        cnt = {k: int(r[k].sum()) for k in KINDS[:-1]}; cnt['flicker'] = fl if fl > FLICKER_MAX else 0; cnt['flicker_raw'] = fl
        rows.append((name, im, r, cnt))
    return rows

def summary(rows):
    tot = {k: sum(c[k] for _, _, _, c in rows) for k in KINDS}
    flagged = sum(1 for _, _, _, c in rows if any(c[k] for k in KINDS))
    return dict(frames=len(rows), flagged_frames=flagged, **tot)

def sheet(rows, path, scale=4, cols=16, crop=(20, 4, 108, 126), only_flagged=False):
    sel = [r for r in rows if not only_flagged or any(r[3][k] for k in KINDS)]
    x0, y0, x1, y1 = crop; cw, ch = (x1 - x0) * scale, (y1 - y0) * scale + 28
    n = max(1, len(sel)); R = (n + cols - 1) // cols
    S = Image.new('RGB', (cols * cw, R * ch + 40), (34, 32, 44)); D = ImageDraw.Draw(S)
    sm = summary(rows)
    D.text((8, 10), '  '.join(f'{k}={v}' for k, v in sm.items()) + '   (magenta hole, red island, cyan speck, orange spur, green outline, yellow flicker)', fill=(255, 255, 255))
    for i, (name, im, r, cnt) in enumerate(sel):
        cx, cy = (i % cols) * cw, 40 + (i // cols) * ch
        bg = Image.new('RGBA', (x1 - x0, y1 - y0), (176, 178, 190, 255)); bg.alpha_composite(Image.fromarray(im[y0:y1, x0:x1]))
        S.paste(bg.convert('RGB').resize((cw, (y1 - y0) * scale), Image.NEAREST), (cx, cy + 28))
        for k in KINDS:
            ys, xs = np.nonzero(r[k][y0:y1, x0:x1])
            for y, x in zip(ys, xs):
                D.rectangle([cx + x * scale - 1, cy + 28 + y * scale - 1, cx + (x + 1) * scale, cy + 28 + (y + 1) * scale], outline=COL[k])
        bad = any(cnt[k] for k in KINDS)
        D.text((cx + 4, cy + 2), name, fill=(255, 120, 120) if bad else (150, 230, 150))
        D.text((cx + 4, cy + 14), ' '.join(f'{k[:3]}{cnt[k]}' for k in KINDS if cnt[k]) or 'ok', fill=(230, 230, 230))
    S.save(path)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cid'); ap.add_argument('--sheet'); ap.add_argument('--json'); ap.add_argument('--src')
    ap.add_argument('--flagged', action='store_true'); ap.add_argument('--arms', action='store_true', help='also run the arm-proportion check (armcheck.py)')
    a = ap.parse_args()
    rows = audit(a.cid, a.src); sm = summary(rows); print(a.cid, json.dumps(sm))
    if a.arms:
        import subprocess, sys as _s
        r = subprocess.run([_s.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'armcheck.py'), a.cid], capture_output=True, text=True)
        print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr.strip()[-300:])
        if r.returncode: _s.exit(1)
    if a.sheet: sheet(rows, a.sheet, only_flagged=a.flagged)
    if a.json:
        json.dump(dict(summary=sm, frames={n: c for n, _, _, c in rows if any(c[k] for k in KINDS)}), open(a.json, 'w'), indent=1)
