"""ChatGPT sprite sheets (refs_ai/chatgpt/<cid>/<kind>.png): 5 rows (S, SW, W, NW, N) on magenta -> hi-res RGBA cuts.

The grid is found automatically: foreground = tolerant magenta key; 5 row bands from the row occupancy profile, then
per row the expected number of column bands (cells are uneven, so each row is split on its own profile); inside a cell
the connected components above a size floor are kept (props included)."""
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slice as S

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, 'refs_ai', 'chatgpt')
ROWS = ['S', 'SW', 'W', 'NW', 'N']
NCOL = dict(idle_actions=6, signature=6, sit=2, walk=8, work=6)      # (sit before work: Howard works seated)
# extra 4-frame sheets (optional per character): seated eating / writing, Howard's standing gadget tinkering
NCOL_X = dict(sit_eat=4, sit_write=4, work_stand=4, cook_stir=4)
KEY_M = {'howard': 140}          # stricter key where the outfit itself is magenta-ish (Howard's trousers)


def bands(prof, n, min_gap=4):
    """S.bands, plus: when two cells touch (fewer runs than n), split the widest run at its thinnest column near the
    middle"""
    prof = np.asarray(prof, float).copy()
    for _ in range(n):
        try: return S.bands(prof, n, min_gap)
        except SystemExit:
            occ = prof > 0; runs = []; i = 0
            while i < len(occ):
                if occ[i]:
                    j = i
                    while j < len(occ) and occ[j]: j += 1
                    runs.append((i, j)); i = j
                else: i += 1
            a, b = max(runs, key=lambda r: r[1] - r[0]); L = b - a
            k = a + L // 4 + int(np.argmin(prof[a + L // 4:b - L // 4]))
            prof[max(a, k - min_gap):k + min_gap] = 0
    return S.bands(prof, n, min_gap)


def keyed(rgb, km):
    m, g = S.magenta_score(rgb)
    bgm = (m > km) & (g < 150)
    fg = ndi.binary_opening(~bgm, np.ones((2, 2)))
    lab, nl = ndi.label(fg); sz = np.bincount(lab.ravel()); sz[0] = 0
    return np.isin(lab, np.nonzero(sz >= 60)[0]), bgm


def cut_sheet(cid, kind, km=None):
    """-> {dir: [rgba cut, ...]} (ncols cuts per row, left to right)"""
    km = km or KEY_M.get(cid, 70)
    rgb = np.array(Image.open(os.path.join(SRC, cid, f'{kind}.png')).convert('RGB'))
    fg, bgm = keyed(rgb, km)
    rows = bands(fg.sum(1), 5, min_gap=6)
    out = {}
    for d, (y0, y1) in zip(ROWS, rows):
        cols = bands(fg[y0:y1].sum(0), {**NCOL, **NCOL_X}[kind], min_gap=4)
        cells = []
        for x0, x1 in cols:
            mm = fg[y0:y1, x0:x1]
            l2, n2 = ndi.label(mm, np.ones((3, 3))); s2 = np.bincount(l2.ravel()); s2[0] = 0
            mm = (s2 >= max(60, 0.004 * s2.max()))[l2]
            fill = ndi.binary_fill_holes(mm)
            mm = mm | (fill & ~bgm[y0:y1, x0:x1])
            ys, xs = np.nonzero(mm)
            b = (ys.min(), ys.max() + 1, xs.min(), xs.max() + 1)
            sub = rgb[y0:y1, x0:x1][b[0]:b[1], b[2]:b[3]]; mk = mm[b[0]:b[1], b[2]:b[3]]
            cells.append(np.dstack([S.despill(sub, mk), (mk * 255).astype(np.uint8)]))
        out[d] = cells
    return out


if __name__ == '__main__':
    for cid in S.CAST:
        for kind in NCOL:
            c = cut_sheet(cid, kind)
            print(cid, kind, ' '.join(f"{d}:{'/'.join(str(x.shape[0]) for x in c[d])}" for d in ROWS))


# ------------------------------------------------------------------ scale: match the still's head
import convert as CV
from scipy.signal import fftconvolve


def head_template(still, frac=0.24):
    A = still[..., 3] > 0; ys = np.nonzero(A.any(1))[0]; y0, y1 = ys[0], ys[-1]
    hh = int(round((y1 - y0) * frac))
    T = still[y0:y0 + hh].astype(float); xs = np.nonzero(T[..., 3].any(0))[0]
    return T[:, xs[0]:xs[-1] + 1], (y0, xs[0])


def match(cut, T, s, win=None):
    h, w = cut.shape[:2]; nh, nw = max(1, int(round(h * s))), max(1, int(round(w * s)))
    rgb, A = CV.area_resize(cut, (nw, nh))
    I = np.dstack([rgb * A[..., None], A * 255.0])
    M = (T[..., 3] > 0).astype(float); Tm = T.copy(); Tm[..., :3] *= M[..., None]; Tm[..., 3] = M * 255
    th, tw = T.shape[:2]
    if nh < th or nw < tw: return np.inf, (0, 0)
    pad = np.zeros((nh + th, nw + 2 * tw, 4)); pad[:nh, tw:tw + nw] = I
    ssd = 0
    for c in range(4):
        X = pad[..., c]
        ssd = ssd + fftconvolve(X * X, M[::-1, ::-1], 'valid') - 2 * fftconvolve(X, Tm[::-1, ::-1, c], 'valid') + (Tm[..., c] ** 2).sum()
    ssd = ssd[:nh - th + 1 + th // 3]                  # head in the upper part of the cell
    if win is not None:                                  # (ky, kx, r): only within r px of a hinted head position
        ky0, kx0, r = win; Y, X = np.mgrid[:ssd.shape[0], :ssd.shape[1]]
        ssd = np.where((abs(Y - ky0) <= r) & (abs(X - tw - kx0) <= r), ssd, np.inf)
        if not np.isfinite(ssd).any(): return np.inf, (int(ky0), int(kx0))
    k = np.unravel_index(np.argmin(ssd), ssd.shape)
    return ssd[k] / M.sum(), (k[0], k[1] - tw)


def best_scale(cut, T, lo=0.3, hi=1.1, n=33):
    ss = np.geomspace(lo, hi, n); r = [match(cut, T, s)[0] for s in ss]
    i = int(np.argmin(r)); a, b = ss[max(0, i - 1)], ss[min(n - 1, i + 1)]
    ss2 = np.linspace(a, b, 11); r2 = [match(cut, T, s)[0] for s in ss2]
    return float(ss2[int(np.argmin(r2))])


def crown_scale(cut, T, th):
    """standing figures: the head match locates the crown (props beside / above the actor do not matter), the soles are
    the bottom of the cut -> scale that makes crown->sole the actor's still height. The head search is bracketed around
    the bbox estimate (th / cut height) so a prop cannot win the match"""
    e = th / cut.shape[0]
    s0 = best_scale(cut, T, 0.8 * e, 1.4 * e, 17)
    _, (ky, kx) = match(cut, T, s0)
    hgt = cut.shape[0] - ky / s0
    return th / hgt, s0


def sheet_scales(cid, kind, cuts, stills, per_row=3):
    th = (stills['S'][..., 3] > 0).any(1).sum()
    cs, hs = [], []
    for d in ROWS:
        T, _ = head_template(stills[d])
        for c in cuts[d][:per_row]:
            a, b = crown_scale(c, T, th); cs.append(a); hs.append(b)
    return float(np.median(cs)), float(np.median(hs))


def door_mask(cut):
    """Sheldon's knock: the drawn door = the tall brown components (fill holes) -> bool mask on the hi-res cut"""
    rgb = cut[..., :3].astype(int); A = cut[..., 3] > 0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    brown = A & (r > 70) & (r - b > 45) & (g - b > 10) & (r - g > 42) & (r - g < 95) & (r < 215)
    lab, n = ndi.label(brown); sz = np.bincount(lab.ravel()); sz[0] = 0
    tall = [i for i, sl in enumerate(ndi.find_objects(lab), 1) if sl is not None and sl[0].stop - sl[0].start > 0.4 * cut.shape[0]]
    door = np.isin(lab, [i for i in tall if sz[i] >= 0.05 * sz.max()])
    return ndi.binary_dilation(ndi.binary_fill_holes(door), iterations=3)


def disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]; return x * x + y * y <= r * r


def limb_colours(still):
    """skin + the shirt (upper torso median) -> arms reaching out of the still's silhouette are kept"""
    A = still[..., 3] > 0; ys = np.nonzero(A.any(1))[0]; y0, y1 = ys[0], ys[-1]; h = y1 - y0
    band = still[y0 + int(h * 0.30):y0 + int(h * 0.42)]; m = band[..., 3] > 0
    xs = np.nonzero(m.any(0))[0]; cx = (xs[0] + xs[-1]) // 2
    shirt = np.median(band[:, cx - 4:cx + 5][m[:, cx - 4:cx + 5]][:, :3].astype(float), 0)
    return shirt


HANDHELD = {'penny': 0.56}     # the tray is carried: everything above this fraction of the still's height is kept


def strip_props(C, A, still, shirt, core=5, reach=14, upper=None):
    """C, A: the 128-canvas rgb/alpha of a work/knock frame already aligned to the still (head on head, soles on 119).
    Props drawn in the sheet (whiteboard, bench, desk, telescope, table, door) are removed: keep what lies within
    `core` px of the still's silhouette, plus skin / shirt-coloured limbs up to `reach` px out; then the largest
    connected figure (+ pieces touching it)"""
    S0 = still[..., 3] > 0
    d1 = ndi.binary_dilation(S0, disk(core)); d2 = ndi.binary_dilation(S0, disk(reach))
    r, g, b = C[..., 0], C[..., 1], C[..., 2]
    skin = (r > 150) & (g > 95) & (b > 60) & (r - b > 35) & (r > g)
    shirtish = np.sqrt(((C - shirt) ** 2).sum(-1)) < 42
    keep = d1 | (d2 & (skin | shirtish))
    # prop surfaces hugging the body (whiteboard / bench / desk / door panels): pale or grey, low-saturation pixels
    # outside the still's own silhouette go even inside the core band
    mx, mn = C.max(-1), C.min(-1)
    propc = ((mn > 175) & (mx - mn < 60)) | ((mx - mn < 30) & (C.mean(-1) > 90))
    keep &= ~(propc & ~S0)
    if upper:
        ys = np.nonzero(S0.any(1))[0]; yh = int(ys[0] + upper * (ys[-1] - ys[0]))
        keep[:yh] = True
    m = (A >= 0.5) & keep
    lab, n = ndi.label(m, np.ones((3, 3))); sz = np.bincount(lab.ravel()); sz[0] = 0
    if n: m = (sz >= max(6, 0.03 * sz.max()))[lab]
    return m


def strip_door(cut):
    return cut


# ------------------------------------------------------------------ 128-px frames
import json
SCALES = os.path.join(HERE, 'sheet_scales.json')


def resize_mask(mk, nw, nh):
    from PIL import Image as _I
    return np.array(_I.fromarray((mk * 255).astype(np.uint8)).resize((nw, nh), _I.BILINEAR)) >= 128


def quantize(C, m, pal, sharpen=0.35):
    C = CV.unsharp(C, m, sharpen)
    img = np.zeros((CV.H, CV.W, 4), np.uint8)
    img[m, :3] = CV.nearest(pal, C[m]); img[m, 3] = 255
    img = CV.pixfix(img); img = CV.outline(img, pal); img = CV.pixfix(img)
    return CV.audit_fix(img, pal)


def paste(rgb, A, ox, oy):
    C = np.zeros((CV.H, CV.W, 3)); AA = np.zeros((CV.H, CV.W))
    h, w = A.shape
    ys0, xs0 = max(0, -oy), max(0, -ox); ys1, xs1 = min(h, CV.H - oy), min(w, CV.W - ox)
    C[oy + ys0:oy + ys1, ox + xs0:ox + xs1] = rgb[ys0:ys1, xs0:xs1]; AA[oy + ys0:oy + ys1, ox + xs0:ox + xs1] = A[ys0:ys1, xs0:xs1]
    return C, AA


def row_hints(cuts, s, ref, door=False, r=5):
    """work / knock rows: the prop (bench, telescope, door) can out-match the head in a frame or two -> the row's
    median head position relative to the cell (bottom + left or right edge, whichever is steadier) and a search
    window around it for every frame"""
    T, _ = head_template(ref); rel = []
    for c in cuts:
        if door: c = c.copy(); c[door_mask(c), 3] = 0
        nh, nw = int(round(c.shape[0] * s)), int(round(c.shape[1] * s))
        _, (ky, kx) = match(c, T, s); rel.append((ky - nh, kx, kx - nw))
    rel = np.array(rel, float); med = np.median(rel, 0); mad = np.median(abs(rel - med), 0)
    side = 1 if mad[1] <= mad[2] else 2
    out = []
    for c in cuts:
        nh, nw = int(round(c.shape[0] * s)), int(round(c.shape[1] * s))
        out.append((med[0] + nh, med[side] + (0 if side == 1 else nw), r))
    return out


def frame128(cut, s, ref, pal, mode, shirt=None, door=False, upper=None, win=None, snap=4):
    """mode: 'stand' (soles on 119, head x on the still's head x), 'work' (head on the reference's head, props stripped,
    soles snapped to 119), 'sit' (soles on 119, torso centre on x=64)"""
    h, w = cut.shape[:2]; nh, nw = max(1, int(round(h * s))), max(1, int(round(w * s)))
    rgb, A = CV.area_resize(cut, (nw, nh))
    if door:
        dm = door_mask(cut); A = np.where(resize_mask(dm, nw, nh), 0, A)
        cut = cut.copy(); cut[dm, 3] = 0          # head match without the door in the way
    T, (ty, tx) = head_template(ref)
    _, (ky, kx) = match(cut, T, s, win)
    m0 = A >= 0.5; ys = np.nonzero(m0.any(1))[0]
    if mode == 'sit':
        import sit as ST
        ox = int(round(64 - ST.torso_x(m0))); oy = CV.SOLE - ys[-1]
    else:
        ox = int(round(tx - kx)); oy = CV.SOLE - ys[-1] if mode == 'stand' else int(round(ty - ky))
    C, AA = paste(rgb, A, ox, oy)
    m = AA >= 0.5
    if mode == 'work' or door:
        m = strip_props(C, AA, ref, shirt, upper=upper)
        ys = np.nonzero(m.any(1))[0]; dy = CV.SOLE - ys[-1] if len(ys) else 0
        if 0 < abs(dy) <= snap:
            C = np.roll(C, dy, 0); m = np.roll(m, dy, 0)
    return quantize(C, m, pal)


def scales_for(cid, cuts, stills, sitref=None):
    allsc = json.load(open(SCALES)) if os.path.exists(SCALES) else {}
    sc = allsc.get(cid, {})
    th = (stills['S'][..., 3] > 0).any(1).sum()
    for kind in ['idle_actions', 'walk', 'signature', 'sit', 'work']:
        if kind in sc: continue
        if kind == 'sit' or (kind == 'work' and cid == 'howard'):
            hs = []
            refs = stills if kind == 'sit' or sitref is None else sitref
            for d in ROWS:
                T, _ = head_template(stills[d])
                hs += [best_scale(c, T, 0.55 * th / c.shape[0], 1.6 * th / c.shape[0], 25) for c in cuts[kind][d][:2]]
            corr = float(np.median([sc[k]['crown'] / sc[k]['head'] for k in ['idle_actions', 'walk', 'signature', 'work'] if 'crown' in sc.get(k, {})]))
            sc[kind] = dict(head=float(np.median(hs)), corr=corr, use=float(np.median(hs)) * corr)
        else:
            a, b = sheet_scales(cid, kind, cuts[kind], stills)
            sc[kind] = dict(crown=a, head=b, use=a)
        print(cid, kind, {k: round(v, 4) for k, v in sc[kind].items()}, flush=True)
        allsc = json.load(open(SCALES)) if os.path.exists(SCALES) else {}
        allsc[cid] = sc; json.dump(allsc, open(SCALES, 'w'), indent=1, sort_keys=True)
    return sc


def load_stills(cid):
    base = os.path.join(ROOT, 'characters', cid, 'ai')
    st = {d: np.array(Image.open(os.path.join(base, f'stand_{d}.png'))) for d in ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']}
    pal = []
    for ln in open(os.path.join(base, f'bbt_{cid}_ai.gpl')).read().splitlines()[4:]:
        if ln.strip(): pal.append([int(v) for v in ln.split()[:3]])
    return st, np.array(pal, float)


def convert(cid):
    """-> {kind: {dir5: [128 RGBA frames]}} for the five sheets (sit: both variants)"""
    stills, pal = load_stills(cid)
    cuts = {k: cut_sheet(cid, k) for k in NCOL}
    sc = scales_for(cid, cuts, stills)
    shirt = limb_colours(stills['S'])
    out = {}
    for kind in NCOL:
        out[kind] = {}
        for d in ROWS:
            fr = []; door = cid == 'sheldon' and kind == 'signature'
            hints = [None] * len(cuts[kind][d])
            if (kind == 'work' and cid != 'howard') or door: hints = row_hints(cuts[kind][d], sc[kind]['use'], stills[d], door)
            for c, hw in zip(cuts[kind][d], hints):
                if kind == 'sit': f = frame128(c, sc['sit']['use'], stills[d], pal, 'sit')
                elif kind == 'work' and cid == 'howard':
                    f = frame128(c, sc['work']['use'], out['sit'][d][0], pal, 'work', shirt)
                elif kind == 'work': f = frame128(c, sc['work']['use'], stills[d], pal, 'work', shirt, upper=HANDHELD.get(cid), win=hw, snap=99)   # standing at the station: soles on 119
                else: f = frame128(c, sc[kind]['use'], stills[d], pal, 'stand', shirt, door=door, win=hw)
                fr.append(f)
            out[kind][d] = fr
        if kind == 'idle_actions': pass
    return out, stills, pal


def convert_extra(cid):
    """the optional NCOL_X sheets present for cid -> {kind: {dir5: [128 frames]}}. Seated sheets: head-matched scale x the
    sheet-family correction (same rule as sit.png), soles on 119, torso centre on x=64 (= the sit frames' convention, so
    the seat anchor is measured the same way); work_stand: crown->sole = the still's height, head x on the still's"""
    stills, pal = load_stills(cid)
    kinds = [k for k in NCOL_X if os.path.exists(os.path.join(SRC, cid, f'{k}.png'))]
    allsc = json.load(open(SCALES)); sc = allsc[cid]; th = (stills['S'][..., 3] > 0).any(1).sum()
    out = {}
    for kind in kinds:
        cuts = cut_sheet(cid, kind)
        if kind not in sc:
            if kind.startswith('sit'):
                hs = []
                for d in ROWS:
                    T, _ = head_template(stills[d])
                    hs += [best_scale(c, T, 0.55 * th / c.shape[0], 1.6 * th / c.shape[0], 25) for c in cuts[d][:2]]
                sc[kind] = dict(head=float(np.median(hs)), corr=sc['sit']['corr'], use=float(np.median(hs)) * sc['sit']['corr'])
            else:
                a, b = sheet_scales(cid, kind, cuts, stills); sc[kind] = dict(crown=a, head=b, use=a)
            print(cid, kind, {k: round(v, 4) for k, v in sc[kind].items()}, flush=True)
            allsc[cid] = sc; json.dump(allsc, open(SCALES, 'w'), indent=1, sort_keys=True)
        mode = 'sit' if kind.startswith('sit') else 'stand'
        out[kind] = {d: [frame128(c, sc[kind]['use'], stills[d], pal, mode) for c in cuts[d]] for d in ROWS}
        if mode == 'sit':
            # the head match is loose on seated sheets (+-20 %): lock the scale to the base sit frames instead (same
            # seated height per facing, soles on 119, torso on x=64) so the base sit's seat anchor fits these frames too
            base = np.array(Image.open(os.path.join(ROOT, 'characters', cid, f'chr_{cid}_sit.png')).convert('RGBA'))[:128]   # row 0 = base sit (extra rows below)
            hgt = lambda f: np.ptp(np.nonzero((f[..., 3] > 0).any(1))[0])
            r = float(np.median([hgt(base[:, i * 128:(i + 1) * 128]) / np.median([hgt(f) for f in out[kind][d]]) for i, d in enumerate(ROWS)]))
            if abs(r - 1) > 0.02:
                sc[kind]['use_base_lock'] = sc[kind]['use'] * r
                out[kind] = {d: [frame128(c, sc[kind]['use'] * r, stills[d], pal, mode) for c in cuts[d]] for d in ROWS}
            print(cid, kind, 'base-lock ratio', round(r, 3), flush=True)
            allsc[cid] = sc; json.dump(allsc, open(SCALES, 'w'), indent=1, sort_keys=True)
    return out
