"""Sprite skins for floor4 items from Mohan's ChatGPT environment sheets (refs_ai/chatgpt/env/sliced/*).

The procedural item (tools/env_items*.py) stays the *proxy*: footprint, collision, hooks, seat_z and the per-pixel hit maps
(tx/ty for depth slicing, hx/hy/hz for seat occluders).  Only the visible pixels are swapped for the cleaned ChatGPT sprite:
  clean   : tolerant magenta key + despill, binary alpha, 1 px outline cleanup (speck removal, spill rim -> darkest neighbour)
  orient  : sheet sprites are near-2:1 iso; the facing (SW = long front edge descending to the right) is detected from the
            bottom profile and the sprite is mirrored when the placed rotation needs the other one.  NE (back) views are
            synthesised from the SW silhouette (flat back panel); wall pieces are sheared onto the wall plane (slope 0.5)
  scale   : footprint-diamond width ((fw+fh)*64 px; 128x64 tile = 64 px/m) capped by the proxy height (real-world heights)
  palette : snapped to the shared env palette palettes/bbt_env_ai.gpl (registered in iso_render.PAL as ai_NN)
Usage: python3 tools/env_ai/skins.py palette   (rebuild the shared env palette)
       python3 tools/env_ai/skins.py sheet     (catalog of every skinned item/rotation -> env/renders/env_ai_skins.png)"""
import os, sys, json
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SL = f'{ROOT}/refs_ai/chatgpt/env/sliced'
FW, A4, B4 = 'floors_walls_v1', '4A_furniture_v1', '4B_furniture_v1'
GPL = f'{ROOT}/palettes/bbt_env_ai.gpl'

# item -> per-state list of parts (sheet, index, tile offset along the item's long axis [canonical x], extra)
#   opts: hcap (max height vs proxy, default 1.12), fit 'diamond'|'proxy', back (synth NE view), hide (invisible proxy)
SKINS = {
    '4a_couch':                 dict(parts=[(A4, 0)]),
    '4a_armchair':              dict(parts=[(A4, 2)]),
    '4a_coffee_table':          dict(parts=[(A4, 4)]),
    '4a_tv_stand':              dict(parts=[(A4, 5)]),
    '4a_desk_laptop':           dict(parts=[(A4, 8)], hcap=1.6),          # includes Sheldon's office chair seen from behind
    '4a_office_chair':          dict(hide=True),                            # drawn as part of the desk sprite; proxy keeps hook
    '4a_kitchen_counter':       dict(parts=[(A4, 23, 0, 2), (A4, 22, 2, 1)]),   # sink counter (2 tiles) + stove (cook hook)
    '4a_kitchen_island':        dict(parts=[(A4, 17)]),
    '4a_bar_stool':             dict(parts=[(A4, 19)], hcap=1.25),
    '4a_fridge':                dict(parts=[(A4, 21)]),
    '4a_whiteboard':            dict(states={'equations_a': [(A4, 6)], 'equations_b': [(A4, 7)]}, hcap=1.3),
    '4a_bookcase_collectibles': dict(parts=[(A4, 16, 0, 1), (A4, 16, 1, 1)], hcap=1.3),
    '4a_telescope':             dict(parts=[(A4, 27)], hcap=1.3),
    '4a_floor_lamp':            dict(parts=[(A4, 26)], hcap=1.3),
    '4a_dna_model':             dict(parts=[(A4, 28)], hcap=1.6),
    '4a_takeout_set':           dict(parts=[(A4, 29)], scale=0.32),
    '4a_rug':                   dict(parts=[(A4, 31)], fit='flat'),
    '4a_front_door':            dict(states={'closed': [(FW, 25)], 'open': [(FW, 26)]}, fit='proxy'),
    '4b_couch':                 dict(parts=[(B4, 0)]),
    '4b_coffee_table':          dict(parts=[(B4, 2)]),
    '4b_dining_table_cluttered': dict(parts=[(B4, 4)], chair=(B4, 5, 'chair0', 62), at='surface0', width=130),
    '4b_kitchen_counter':       dict(parts=[(B4, 7)]),
    '4b_fridge':                dict(parts=[(B4, 8)]),
    '4b_kitchen_bar':           dict(parts=[(A4, 18)]),
    '4b_bar_stool':             dict(parts=[(A4, 20)], hcap=1.25),
    '4b_laundry_pile':          dict(parts=[(B4, 11)], scale=0.55),
    '4b_rug':                   dict(parts=[(B4, 19)], fit='flat'),
    '4b_front_door':            dict(states={'closed': [(FW, 27)], 'open': [(FW, 28)]}, fit='proxy'),
    '4b_bedroom_door':          dict(states={'closed': [(FW, 29)], 'ajar': [(FW, 30)], 'open': [(FW, 30)]}, fit='proxy'),
    'hall_elevator_broken':     dict(parts=[(FW, 31)], fit='proxy'),
}

# ------------------------------------------------------------------ clean
_RAW = {}
def clean(sheet, idx):
    k = (sheet, idx)
    if k in _RAW: return _RAW[k]
    a = np.array(Image.open(f'{SL}/{sheet}/{idx:02d}.png').convert('RGBA')).astype(np.int32)
    rgb, al = a[..., :3], a[..., 3]
    op = al >= 100
    # despill: magenta tint (r,b >> g) pulled back to g on the rim; deep spill anywhere
    spill = np.clip(np.minimum(rgb[..., 0], rgb[..., 2]) - rgb[..., 1], 0, None)
    rim = op & ndi.binary_dilation(~op, iterations=2)
    sp = np.where(rim, spill, np.where(spill > 60, spill - 60, 0))
    rgb[..., 0] -= sp; rgb[..., 2] -= sp
    # speck removal (opaque px with < 2 opaque 4-neighbours), then hole fill
    nb = ndi.convolve(op.astype(int), np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]]), mode='constant')
    op &= nb >= 2
    lab, n = ndi.label(op)
    if n > 1:
        sz = ndi.sum(op, lab, range(1, n + 1)); keep = np.isin(lab, 1 + np.where(sz >= 12)[0]); op &= keep
    # outline: rim px still tinted / too light -> darkest opaque neighbour (crisp 1 px dark outline like the char art)
    lum = rgb @ np.array([0.3, 0.59, 0.11])
    rim = op & ndi.binary_dilation(~op, iterations=1)
    spill2 = np.clip(np.minimum(rgb[..., 0], rgb[..., 2]) - rgb[..., 1], 0, None)
    bad = rim & (spill2 > 25)
    if bad.any():
        big = np.where(op, lum, 1e9)
        mn = ndi.minimum_filter(big, size=3)
        ys, xs = np.where(bad)
        for y, x in zip(ys, xs):
            y0, x0 = max(0, y - 1), max(0, x - 1); win = big[y0:y + 2, x0:x + 2]
            j = np.unravel_index(np.argmin(win), win.shape); rgb[y, x] = rgb[y0 + j[0], x0 + j[1]]
    out = np.zeros(a.shape, np.uint8); out[..., :3] = np.clip(rgb, 0, 255); out[..., 3] = np.where(op, 255, 0)
    ys, xs = np.where(op); out = out[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    _RAW[k] = out
    return out

def bottom_profile(a):
    m = a[..., 3] > 0; w = m.shape[1]
    return np.array([np.where(m[:, c])[0].max() if m[:, c].any() else -1 for c in range(w)])
def facing_of(a):
    """'SW' if the longest bottom (front) edge descends to the right, else 'SE'"""
    b = bottom_profile(a); p = int(np.argmax(b)); w = len(b)
    return 'SW' if p > w / 2 else 'SE'
def wall_slope(a):
    b = bottom_profile(a); w = len(b); c = np.arange(w)
    lo, hi = int(w * 0.15), int(w * 0.85)
    return float(np.polyfit(c[lo:hi], b[lo:hi], 1)[0])

# ------------------------------------------------------------------ palette
def pal_load():
    if not os.path.exists(GPL): return None
    cols = []
    for line in open(GPL):
        p = line.split()
        if len(p) >= 4 and p[0].isdigit(): cols.append((int(p[0]), int(p[1]), int(p[2])))
    return np.array(cols, int)
_PAL = None
def snap(a):
    global _PAL
    if _PAL is None: _PAL = pal_load()
    if _PAL is None: return a
    m = a[..., 3] > 0; px = a[m][:, :3].astype(int)
    out = a.copy()
    u, inv = np.unique(px, axis=0, return_inverse=True)
    d = (((u[:, None, :] - _PAL[None]) ** 2) * np.array([0.3, 0.59, 0.11])).sum(2)
    out[m, :3] = _PAL[d.argmin(1)][inv.reshape(-1)]
    return out
def all_sources():
    s = set()
    for v in SKINS.values():
        for parts in ([v['parts']] if 'parts' in v else list(v.get('states', {}).values())):
            for p in parts: s.add((p[0], p[1]))
    return sorted(s)
def build_palette(n=96):
    import floors_ai
    px = [clean(*k)[..., :3][clean(*k)[..., 3] > 0] for k in all_sources()]
    px += [t[..., :3][t[..., 3] > 0] for t in floors_ai.raw_tiles().values()]
    px += [w for w in floors_ai.wall_samples()]
    allp = np.concatenate([p.reshape(-1, 3) for p in px]).astype(np.uint8)
    im = Image.fromarray(allp.reshape(1, -1, 3))
    q = im.quantize(colors=n, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    cols = np.array(q.getpalette()[:n * 3]).reshape(-1, 3)
    cols = sorted({tuple(c) for c in cols}, key=lambda c: 0.3*c[0] + 0.59*c[1] + 0.11*c[2])
    with open(GPL, 'w') as f:
        f.write('GIMP Palette\nName: BBT Env (ChatGPT sheets)\nColumns: 8\n#\n')
        for i, c in enumerate(cols): f.write(f'{c[0]:3d} {c[1]:3d} {c[2]:3d}\tai_{i:02d}\n')
    return len(cols)

# ------------------------------------------------------------------ build skin
def _resize(a, s):
    if abs(s - 1) < 0.02: return a
    h, w = a.shape[:2]; nw, nh = max(1, round(w * s)), max(1, round(h * s))
    pre = a.astype(np.float32); pre[..., :3] *= pre[..., 3:4] / 255
    r = np.array(Image.fromarray(pre.astype(np.uint8)).resize((nw, nh), Image.LANCZOS if s < 1 else Image.NEAREST)).astype(np.float32)
    al = r[..., 3]; o = np.zeros(r.shape, np.uint8)
    keep = al >= 110
    o[..., :3] = np.clip(r[..., :3] * 255 / np.maximum(al[..., None], 1), 0, 255); o[..., 3] = np.where(keep, 255, 0)
    return o
def _shear(a, k):
    """y' = y + k*x (vertical shear), keeps columns"""
    h, w = a.shape[:2]; off = [int(round(k * c)) for c in range(w)]; mn, mx = min(off), max(off)
    o = np.zeros((h + mx - mn, w, 4), np.uint8)
    for c in range(w): o[off[c] - mn: off[c] - mn + h, c] = a[:, c]
    return o
def _back(a):
    """synthesised back view (object turned 180 deg): same silhouette, flat darkened back panel, outline kept"""
    m = a[..., 3] > 0; o = a.copy()
    rgb = a[..., :3].astype(float)
    med = np.stack([ndi.median_filter(rgb[..., i], size=9) for i in range(3)], -1)
    lum = rgb @ np.array([0.3, 0.59, 0.11])
    dark = lum < 60                                   # screen / bezel stays dark
    body = med * 0.78
    o[..., :3] = np.where(dark[..., None], rgb, body).astype(np.uint8)
    rim = m & ndi.binary_dilation(~m, iterations=1)
    o[rim, :3] = (rgb[rim] * 0.5).astype(np.uint8)
    return o
def _orient(a, want):
    have = facing_of(a)
    return a[:, ::-1].copy() if have != want else a

def compose_parts(parts, rot, nfx, nfy):
    """multi-part item along its long (canonical x) axis, built in the canonical SW view then mirrored for SE.
    part (sheet, idx, t0, n): fitted to the sub-diamond of tiles t0..t0+n-1 (width (n+1)*64, bottom at (t0+n+1)*32)"""
    want = 'SE' if rot in ('SE', 'NW') else 'SW'
    L = max(nfx, nfy); W = (L + 1) * 64 + 64; H = 420
    can = np.zeros((H, W, 4), np.uint8)
    for p in sorted(parts, key=lambda p: p[2]):
        a = _orient(clean(p[0], p[1]), 'SW'); t0, n = p[2], p[3]
        r = _resize(a, (n + 1) * 64 / a.shape[1]); h, w = r.shape[:2]
        x0 = t0 * 64; by = H - 40 - (L - t0 - n) * 32
        y0 = by - bottom_profile(r).max()
        m = r[..., 3] > 0; can[y0:y0 + h, x0:x0 + w][m] = r[m]
    ys, xs = np.where(can[..., 3] > 0); a = can[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    if want == 'SE': a = a[:, ::-1].copy()
    if rot in ('NE', 'NW'): a = _back(a)
    return a, 'composite'

def _corners(a):
    m = a[..., 3] > 0; ys, xs = np.where(m)
    def at(sel): return np.array([xs[sel].mean(), ys[sel].mean()])
    return dict(T=at(ys == ys.min()), B=at(ys == ys.max()), L=at(xs == xs.min()), R=at(xs == xs.max()))
def _flat(a, R):
    """flat items (rugs): the sprite's quad is re-mapped onto the exact footprint diamond (bilinear in world u,v)"""
    X = R['xf']; nfx, nfy = R['fp']; px, py = R['pivot']
    tx, ty = px - (nfx - nfy) * 64, py - (nfx + nfy) * 32
    c = _corners(a)
    lx = np.linalg.norm(c['R'] - c['T']); ly = np.linalg.norm(c['L'] - c['T'])
    if (lx >= ly) != (nfx >= nfy):
        a = a[:, ::-1].copy(); c = _corners(a)
    W, H = (nfx + nfy) * 64, (nfx + nfy) * 32
    out = np.zeros((H, W, 4), np.uint8)
    T, Rr, B, L = c['T'], c['R'], c['B'], c['L']
    for j in range(H):
        for i in range(W):
            sx = i + 0.5 - nfy * 64; sy = j + 0.5
            u = (sx / 64 + sy / 32) / 2 / nfx; v = (sy / 32 - sx / 64) / 2 / nfy
            if not (0 <= u < 1 and 0 <= v < 1): continue
            u = 0.03 + u * 0.94; v = 0.03 + v * 0.94          # stay off the outline, then redraw a crisp 1 px outline
            p = (1 - u) * (1 - v) * T + u * (1 - v) * Rr + u * v * B + (1 - u) * v * L
            out[j, i] = a[int(np.clip(p[1], 0, a.shape[0] - 1)), int(np.clip(p[0], 0, a.shape[1] - 1))]
    m = out[..., 3] > 0; out[..., 3] = np.where(m, 255, 0)
    rim = m & ndi.binary_dilation(~m)
    out[rim, :3] = (out[rim, :3] * 0.55).astype(np.uint8)
    return snap(out), int(tx - nfy * 64), int(ty)

def skin(iid, rot, state, R):
    spec = SKINS.get(iid)
    if spec is None: return R
    op = R['op'] & (R['img'][..., 3] == 255)
    if spec.get('hide'):
        R2 = dict(R); im = R['img'].copy(); im[..., 3] = 0; R2['img'] = im; R2['skinned'] = 'hidden'; return R2
    parts = spec['parts'] if 'parts' in spec else spec['states'].get(state) or list(spec['states'].values())[0]
    nfx, nfy = R['fp']
    ys, xs = np.where(op)
    if len(ys) == 0: return R
    py0, py1, px0, px1 = ys.min(), ys.max(), xs.min(), xs.max()
    ph, pw = py1 - py0 + 1, px1 - px0 + 1
    if spec.get('fit') == 'flat':
        r, x0, y0 = _flat(clean(parts[0][0], parts[0][1]), R); h, w = r.shape[:2]
    elif spec.get('fit') == 'proxy':
        a = clean(parts[0][0], parts[0][1])
        want_s = 0.5 if rot in ('SW', 'NE') else -0.5     # wall plane slope on screen: y=0 wall descends right, x wall rises right
        s0 = wall_slope(a)
        if np.sign(s0) != np.sign(want_s) and abs(s0) > 0.08: a = a[:, ::-1].copy(); s0 = -s0
        a = _shear(a, want_s - s0)
        s = pw / a.shape[1]; s = min(s, ph * 1.04 / a.shape[0]) if a.shape[0] * s > ph * 1.04 else s
        r = snap(_resize(a, s)); h, w = r.shape[:2]
        x0 = px0 + (pw - w) // 2; y0 = py1 + 1 - h
    else:
        if any(len(p) >= 4 for p in parts):
            a, _ = compose_parts(parts, rot, nfx, nfy)
        else:
            want = 'SE' if rot in ('SE', 'NW') else 'SW'
            a = _orient(clean(parts[-1][0], parts[-1][1]), want)
            if rot in ('NE', 'NW'): a = _back(a)
        tw = spec.get('width') or (nfx + nfy) * 64
        s = spec.get('scale') or tw / a.shape[1]
        if a.shape[0] * s > ph * spec.get('hcap', 1.12): s = ph * spec.get('hcap', 1.12) / a.shape[0]
        r = snap(_resize(a, s)); h, w = r.shape[:2]
        # anchor: bottom-most column of the sprite (front corner / front legs) on the proxy's bottom-most column
        b = bottom_profile(r); fc = int(np.mean(np.where(b >= b.max() - 1)[0]))
        pb = np.array([np.where(op[:, c])[0].max() if op[:, c].any() else -1 for c in range(op.shape[1])])
        pfc = int(np.mean(np.where(pb >= pb.max() - 1)[0]))
        if spec.get('at'):      # free-standing (round table): base centred under a hook point, front foot +22 px
            import env_items as E
            hk = next(q for q in E.ITEMS[iid]['hooks'] if q['id'] == spec['at']); hx_, hy_ = R['xf'].fwd(*hk['pos'])
            topx = R['pivot'][0] - (nfx - nfy) * 64; topy = R['pivot'][1] - (nfx + nfy) * 32
            x0 = int(topx + (hx_ - hy_) * 64 - w / 2); y0 = int(topy + (hx_ + hy_) * 32 + 22 - h)
        elif spec.get('scale'):   # small props: centre on the proxy
            x0 = px0 + (pw - w) // 2; y0 = py1 + 1 - h
        else:
            x0 = pfc - fc; y0 = py1 + 1 - h
            x0 = int(np.clip(x0, px0 - (w - pw) - 8, px0 + 8)) if w >= pw else int(np.clip(x0, px0, px1 + 1 - w))
    # grow the canvas if needed; keep pivot consistent
    H0, W0 = R['img'].shape[:2]
    padT, padL = max(0, -y0), max(0, -x0)
    padB, padR = max(0, y0 + h - H0), max(0, x0 + w - W0)
    def pad(m, v=0):
        return np.pad(m, ((padT, padB), (padL, padR)) + ((0, 0),) * (m.ndim - 2), constant_values=v)
    img = np.zeros((H0 + padT + padB, W0 + padL + padR, 4), np.uint8)
    x0 += padL; y0 += padT
    mm = r[..., 3] > 0
    img[y0:y0 + h, x0:x0 + w][mm] = r[mm]
    # contact shadow from the proxy (under the sprite only)
    sh = pad(R['img']); shm = (sh[..., 3] > 0) & (sh[..., 3] < 255) & (img[..., 3] == 0)
    img[shm] = sh[shm]
    if spec.get('chair'):      # dining chair drawn behind the table at the chair0 seat point, facing the table
        import env_items as E
        from iso_render import dir_name
        h = next(h for h in E.ITEMS[iid]['hooks'] if h['id'] == spec['chair'][2])
        X = R['xf']; hx_, hy_ = X.fwd(*h['pos']); vx, vy = X.vec(*h['facing']); d = dir_name(round(vx, 6), round(vy, 6))
        c = clean(spec['chair'][0], spec['chair'][1]); want = 'SE' if d in ('SE', 'E', 'NE') else 'SW'
        c = _orient(c, want)
        if d in ('NE', 'NW', 'N'): c = _back(c)
        c = snap(_resize(c, spec['chair'][3] / c.shape[0])); ch_, cw_ = c.shape[:2]
        topx = R['pivot'][0] + padL - (nfx - nfy) * 64; topy = R['pivot'][1] + padT - (nfx + nfy) * 32
        sx_, sy_ = topx + (hx_ - hy_) * 64, topy + (hx_ + hy_) * 32 + 14
        cx0, cy0 = int(sx_ - cw_ / 2), int(sy_ - ch_)
        if cx0 >= 0 and cy0 >= 0 and cx0 + cw_ <= img.shape[1] and cy0 + ch_ <= img.shape[0]:
            sub = img[cy0:cy0 + ch_, cx0:cx0 + cw_]; m = (c[..., 3] > 0) & (sub[..., 3] < 255)
            sub[m] = c[m]
    newop = img[..., 3] == 255
    pop = pad(op, False)
    _, (iy, ix) = ndi.distance_transform_edt(~pop, return_indices=True)
    R2 = dict(R)
    R2['img'] = img; R2['pivot'] = (R['pivot'][0] + padL, R['pivot'][1] + padT)
    for k in ('tx', 'ty', 'hx', 'hy', 'hz'):
        src = pad(R[k], 0 if k != 'hz' else -9.0)
        R2[k] = np.where(newop | shm, src[iy, ix], src)
    R2['op'] = newop | shm
    R2['skinned'] = True
    return R2

if __name__ == '__main__':
    sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
    if 'palette' in sys.argv: print('palette colours', build_palette())
