"""v2 style, step 1: AI master turnaround strip (5 dirs: S, SW, W, NW, N) -> five 128x128 palette-indexed
master idle frames fitted to the v1 rig frame (same height, feet line, centre of mass), plus a per-character
v2 palette.  Used by tools/v2/cutout.py, which animates the masters with the rig skeleton."""
import json, os, sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
ROOT = '/workspace/bbt-pixel'
DIRS5 = ['S', 'SW', 'W', 'NW', 'N']

def v1_frames(cid):
    base = f'{ROOT}/characters/{cid}/refs/v1_style'
    J = json.load(open(f'{base}/chr_{cid}.json')); fr = {f['filename']: f['frame'] for f in J['frames']}
    sh = np.array(Image.open(f'{base}/chr_{cid}.png').convert('RGBA'))
    def get(name):
        f = fr[name]; return sh[f['y']:f['y'] + 128, f['x']:f['x'] + 128]
    return get

def bg_mask(rgb, thr=38):
    near_white = (255 - rgb.astype(int)).max(-1) < thr
    lab, n = ndi.label(near_white)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    # enclosed white gaps (between arm and body, between legs) are background too; small ones are eye whites
    sz = np.bincount(lab.ravel())
    big = set(np.where(sz > 260)[0]) - {0}
    bg = np.isin(lab, list(border | big))
    # anti-aliased halo: light, low-saturation pixels touching the background
    lowsat = (rgb.max(-1).astype(int) - rgb.min(-1)) < 40
    light = (rgb.astype(int).mean(-1) > 185) & lowsat
    for _ in range(3):
        grow = ndi.binary_dilation(bg) & light
        if not (grow & ~bg).any(): break
        bg = bg | grow
    return bg

def lum(c): return c @ np.array([0.299, 0.587, 0.114])

FITS = {}
def build_masters(cid, strip_path, ncol=48, overrides=None):
    rgb = np.array(Image.open(strip_path).convert('RGB')); H, W = rgb.shape[:2]
    fg = ~bg_mask(rgb)
    fg = ndi.binary_opening(fg, iterations=1)
    get = v1_frames(cid)
    # palette from all figure pixels (median cut on the full-res art)
    px = rgb[fg].reshape(-1, 1, 3)
    q = Image.fromarray(px.astype(np.uint8)).quantize(colors=ncol, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = np.array(q.getpalette()[:ncol * 3]).reshape(-1, 3)
    # small but important accents (emblems, pins, eyes) get swallowed by median cut: add up to 4 colours for
    # pixel groups that sit far from every palette entry
    fpx = rgb[fg].astype(float)
    for _ in range(4):
        dm = np.sqrt(((fpx[:, None, :] - pal[None].astype(float)) ** 2).sum(-1)).min(1)
        sat = fpx.max(1) - fpx.min(1)
        far = (dm > 48) & (sat > 40)          # only chromatic accents (greys/whites here are leftover halo)
        if far.sum() < 120: break
        sel = fpx[far]; c = sel[np.argsort(dm[far])[-max(120, far.sum() // 2):]]
        pal = np.vstack([pal, np.median(c, 0).round().astype(pal.dtype)])
    idx_full = np.full((H, W), -1)
    d = ((rgb[fg][:, None, :].astype(float) - pal[None]) ** 2 * np.array([0.30, 0.59, 0.11])).sum(-1)
    idx_full[fg] = d.argmin(1)
    masters = {}; PL = lum(pal.astype(float))
    lab, n = ndi.label(fg)
    for i, dname in enumerate(DIRS5):
        x0, x1 = i * W // 5, (i + 1) * W // 5
        sub = lab[:, x0:x1]; ids, cnt = np.unique(sub[sub > 0], return_counts=True)
        keep = ids[cnt > 0.02 * cnt.max()]
        m = np.zeros_like(fg); m[:, x0:x1] = np.isin(sub, keep)
        core = ndi.binary_erosion(m, iterations=2)
        ys, xs = np.where(m); by0, by1, bx0, bx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        v1 = get(f'chr_{cid}_idle_{dname}_00'); a1 = v1[..., 3] > 0
        vy, vx = np.where(a1); th = vy.max() + 1 - vy.min()
        if overrides and dname in overrides: th = overrides[dname]
        s = (by1 - by0) / th
        cmx_src = (xs.mean() - bx0) / s; cmx_v1 = vx.mean()
        tw = int(np.ceil((bx1 - bx0) / s))
        ox = int(round(cmx_v1 - cmx_src)); oy = vy.max() + 1 - th
        out = np.full((128, 128), -1)
        def cell(ty, tx, py, px, PL=PL):
            Y0 = by0 + int(round(ty * s + py)); Y1 = max(by0 + int(round((ty + 1) * s + py)), Y0 + 1)
            X0 = bx0 + int(round(tx * s + px)); X1 = max(bx0 + int(round((tx + 1) * s + px)), X0 + 1)
            if Y0 < 0 or X0 < 0: return -1, 0.0
            mm = m[Y0:Y1, X0:X1]
            if mm.size == 0 or mm.mean() < 0.42: return -1, 0.0
            mc = core[Y0:Y1, X0:X1]
            sel = mc if mc.sum() >= 3 else mm
            v = idx_full[Y0:Y1, X0:X1][sel]
            cnt = np.bincount(v, minlength=ncol); k = cnt.argmax()
            return k, cnt[k] / len(v)
        # the AI art has its own pixel grid at ~1 art px per target px; search the sampling phase per band so
        # cells line up with art pixels (crisp 1-px features instead of mode-smear)
        bands = [(0, int(0.27 * th)), (int(0.27 * th), int(0.6 * th)), (int(0.6 * th), th)]
        offs = np.linspace(-s / 2, s / 2, 6, endpoint=False)
        for (t0, t1) in bands:
            best = None
            for py in offs:
                for px in offs:
                    pur = [cell(ty, tx, py, px)[1] for ty in range(t0, t1, 2) for tx in range(0, tw, 2)]
                    sc_ = float(np.mean(pur))
                    if best is None or sc_ > best[0]: best = (sc_, py, px)
            _, py, px = best
            for ty in range(t0, t1):
                for tx in range(tw):
                    k, _ = cell(ty, tx, py, px)
                    if k < 0: continue
                    X, Y = ox + tx, oy + ty
                    if 0 <= X < 128 and 0 <= Y < 128: out[Y, X] = k
        masters[dname] = out
        FITS[dname] = dict(bx0=int(bx0), by0=int(by0), by1=int(by1), s=float(s), ox=int(ox), oy=int(oy), th=int(th))
    return masters, pal

def cleanup_idx(out, pal, passes=2):
    out = out.copy()
    for _ in range(passes):
        P = np.pad(out, 1, constant_values=-2)
        nb = np.stack([P[:-2, 1:-1], P[2:, 1:-1], P[1:-1, :-2], P[1:-1, 2:]], -1)
        ys, xs = np.where(out >= 0)
        for y, x in zip(ys, xs):
            n = nb[y, x]; v = out[y, x]
            if (n != v).all():
                nn = n[n >= 0]
                if len(nn) == 0: out[y, x] = -1; continue
                vals, c = np.unique(nn, return_counts=True)
                # keep isolated DARK feature pixels (pupils, nostrils) if much darker than all neighbours
                if lum(pal[v]) + 45 < lum(pal[nn]).min(): continue
                if c.max() >= 2: out[y, x] = vals[c.argmax()]
        # 8-neighbour lone pixels (no same-colour neighbour at all) -> majority colour, unless dark feature
        P8 = np.pad(out, 1, constant_values=-2)
        n8 = np.stack([P8[1 + dy:129 + dy, 1 + dx:129 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx], -1)
        for y, x in zip(*np.where(out >= 0)):
            n = n8[y, x]; v = out[y, x]
            if (n == v).any(): continue
            nn = n[n >= 0]
            if len(nn) < 5: continue
            if lum(pal[v]) + 45 < np.median(lum(pal[nn])): continue
            vals, c = np.unique(nn, return_counts=True); out[y, x] = vals[c.argmax()]
        # fill 1-px holes inside the silhouette
        hole = (out < 0) & ((nb >= 0).sum(-1) >= 3)
        for y, x in zip(*np.where(hole)):
            n = nb[y, x]; n = n[n >= 0]; vals, c = np.unique(n, return_counts=True); out[y, x] = vals[c.argmax()]
    return out

def outline_idx(out, pal, ink_idx):
    """selective coloured outline: silhouette edge -> darkest palette colour of the same hue family,
    except edges facing up/left (light side) which keep a mid-dark shade; bottom/right edges get ink."""
    op = out >= 0; P = np.pad(op, 1)
    up_e = op & ~P[:-2, 1:-1]; dn_e = op & ~P[2:, 1:-1]; lf_e = op & ~P[1:-1, :-2]; rt_e = op & ~P[1:-1, 2:]
    edge = up_e | dn_e | lf_e | rt_e
    res = out.copy(); L = lum(pal)
    def darker(k, f):
        c = pal[k]; tgt = c * f
        dd = ((pal - tgt) ** 2).sum(1) + 1e9 * (L > L[k] - 8)
        return int(dd.argmin()) if dd.min() < 1e8 else k
    for y, x in zip(*np.where(edge)):
        k = out[y, x]
        if L[k] < 70: continue
        res[y, x] = darker(k, 0.55) if (dn_e[y, x] or rt_e[y, x]) else darker(k, 0.72)
    return res

def to_rgba(idx, pal):
    img = np.zeros((128, 128, 4), np.uint8); m = idx >= 0
    img[m, :3] = pal[idx[m]]; img[m, 3] = 255; return img

def save_palette(cid, pal, path):
    with open(path, 'w') as f:
        f.write(f'GIMP Palette\nName: BBT {cid.title()} v2\nColumns: 8\n#\n')
        for i, c in enumerate(pal): f.write(f'{int(c[0]):3d} {int(c[1]):3d} {int(c[2]):3d}\tv2_{i:02d}\n')

if __name__ == '__main__':
    cid = sys.argv[1]
    M, pal = build_masters(cid, f'{ROOT}/characters/{cid}/refs/v2_master/master_strip.jpg', ncol=int(os.environ.get('NCOL', 36)))
    np.save(f'{ROOT}/characters/{cid}/refs/v2_master/pal.npy', pal)
    for d, idx in M.items():
        c = cleanup_idx(idx, pal)
        np.save(f'{ROOT}/characters/{cid}/refs/v2_master/master_{d}.npy', c)
    json.dump(FITS, open(f'{ROOT}/characters/{cid}/refs/v2_master/fits.json', 'w'))
    print('ok', len(pal))
