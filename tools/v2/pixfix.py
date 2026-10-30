"""Pixel-art clean-up for posed cut-out frames (palette-index images, -1 = transparent).
polish(): close tears (small enclosed holes, 1-px notches), drop detached crumbs, shave 1-px spurs, merge orphan
colour specks into their neighbourhood.  restroke(): consistent 1-px dark silhouette outline (each edge pixel =
the outline shade of its own colour) and consolidation of orphan outline / contour pixels.  The same rules are
measured by tools/v2/audit.py."""
import numpy as np
from scipy import ndimage as ndi
LW = np.array([0.299, 0.587, 0.114])
K8 = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
K4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
HOLE_MAX = 6

def nb(a, dy, dx, fill=-1):
    P = np.pad(a, 1, constant_values=fill); H, W = a.shape; return P[1 + dy:1 + dy + H, 1 + dx:1 + dx + W]

def mode_of(vals):
    v = vals[vals >= 0]
    if len(v) == 0: return -1
    u, c = np.unique(v, return_counts=True); return int(u[c.argmax()])

def extend_palette(pal, f=0.45, tol=14):
    """add the outline shade (pal * f) of every colour that has no close dark partner"""
    pal = pal.copy()
    for c in list(pal):
        t = np.round(c.astype(float) * f)
        if np.sqrt(((pal.astype(float) - t) ** 2).sum(1)).min() > tol: pal = np.vstack([pal, t.astype(pal.dtype)])
    return pal

class Shades:
    def __init__(self, pal):
        self.pal = pal.astype(float); self.L = self.pal @ LW
        n = len(pal); self.ol = np.arange(n); self.ct = np.arange(n)
        for k in range(n):
            self.ol[k] = self._dark(k, 0.45, 26); self.ct[k] = self._dark(k, 0.66, 14)
    def _dark(self, k, f, dl):
        if self.L[k] < 62: return k
        cand = np.where(self.L < min(self.L[k] - dl, max(62.0, self.L[k] * 0.62)))[0] if f < 0.5 else np.where(self.L < self.L[k] - dl)[0]
        if len(cand) == 0: return k
        d = ((self.pal[cand] - self.pal[k] * f) ** 2 * np.array([0.30, 0.59, 0.11])).sum(1)
        return int(cand[d.argmin()])

def fill_small_holes(out, og=None, dep=None):
    for _ in range(3):
        op = out >= 0
        enc = ndi.binary_fill_holes(op) & ~op
        lab, n = ndi.label(enc)
        if not n: break
        # tears: tiny pockets, and enclosed slits at most 2 px wide (a limb pressed against the body)
        sz = np.bincount(lab.ravel()); wd = ndi.maximum(ndi.distance_transform_edt(enc), lab, range(1, n + 1))
        small = np.isin(lab, [i for i in range(1, n + 1) if sz[i] <= HOLE_MAX or (sz[i] <= 48 and wd[i - 1] <= 1.0)])
        if not small.any(): break
        out = grow_into(out, small, og, dep)
    # notches: empty pixel with >= 3 opaque 4-neighbours
    for _ in range(2):
        op = out >= 0; cnt = sum((nb(out, dy, dx) >= 0).astype(int) for dy, dx in K4)
        m = ~op & (cnt >= 3)
        if not m.any(): break
        out = grow_into(out, m, og, dep)
    return out

def grow_into(out, mask, og=None, dep=None):
    """fill mask pixels from their opaque neighbours (majority colour), growing inward"""
    out = out.copy(); mask = mask.copy()
    for _ in range(8):
        if not mask.any(): break
        vals = np.stack([nb(out, dy, dx) for dy, dx in K8], -1)
        ys, xs = np.nonzero(mask & (vals >= 0).any(-1))
        newv = [mode_of(vals[y, x]) for y, x in zip(ys, xs)]
        for (y, x), v in zip(zip(ys, xs), newv):
            out[y, x] = v; mask[y, x] = False
            if og is not None:
                g = np.stack([nb(og, dy, dx, -9) for dy, dx in K8], -1)[y, x]; og[y, x] = mode_of(g[g > -9]) if (g > -9).any() else 0
            if dep is not None:
                d = np.stack([nb(dep, dy, dx, 1e9) for dy, dx in K8], -1)[y, x]; dep[y, x] = d.min()
    return out

def drop_islands(out, keep_min=24):
    lab, n = ndi.label(out >= 0, structure=np.ones((3, 3)))
    if n <= 1: return out
    sz = np.bincount(lab.ravel()); sz[0] = 0
    bad = (sz < keep_min) & (np.arange(len(sz)) != sz.argmax())
    out = out.copy(); out[bad[lab] & (lab > 0)] = -1; return out

def bridge_islands(out, og=None, dep=None, reach=3):
    """a part that a pose moved 1-3 px away from the body (head bob vs collar, shoe vs ankle) is re-joined by
    filling the narrow gap between it and the main body from the neighbouring colours"""
    for _ in range(reach):
        lab, n = ndi.label(out >= 0, structure=np.ones((3, 3)))
        if n <= 1: break
        sz = np.bincount(lab.ravel()); sz[0] = 0; main = lab == sz.argmax()
        gap = np.zeros_like(main)
        for i in range(1, n + 1):
            if i == sz.argmax(): continue
            isl = lab == i
            g = (out < 0) & ndi.binary_dilation(isl, np.ones((3, 3))) & ndi.binary_dilation(main, np.ones((3, 3)), iterations=reach)
            # only the pixels between the two (not a halo around the island)
            g &= ndi.binary_dilation(main, np.ones((3, 3)), iterations=reach) & ndi.binary_dilation(isl, np.ones((3, 3)), iterations=reach)
            gap |= g
        if not gap.any(): break
        out = grow_into(out, gap, og, dep)
    return out

def shave_spurs(out):
    for _ in range(6):
        cnt = sum((nb(out, dy, dx) >= 0).astype(int) for dy, dx in K8)
        m = (out >= 0) & (cnt <= 1)
        if not m.any(): break
        out = out.copy(); out[m] = -1
    return out

def is_feature(out, L, y, x):
    """dark feature (pupil, nostril, brow end) or bright glint: keep as a single pixel"""
    v = out[y, x]; nn = [out[y + dy, x + dx] for dy, dx in K8 if 0 <= y + dy < out.shape[0] and 0 <= x + dx < out.shape[1]]
    nn = [n for n in nn if n >= 0]
    if not nn: return False
    ln = L[nn]; return L[v] + 45 < ln.min() or L[v] > ln.max() + 60

def merge_specks(out, pal, protect=None, passes=3):
    L = pal.astype(float) @ LW
    for _ in range(passes):
        key = out; same = sum(((nb(key, dy, dx) == key) & (key >= 0)).astype(int) for dy, dx in K8)
        cnt = sum((nb(key, dy, dx) >= 0).astype(int) for dy, dx in K8)
        ys, xs = np.nonzero((out >= 0) & (same == 0) & (cnt >= 3))
        if len(ys) == 0: break
        new = out.copy(); ch = 0
        for y, x in zip(ys, xs):
            if protect is not None and protect[y, x]: continue
            if is_feature(out, L, y, x): continue
            vals = np.array([out[y + dy, x + dx] for dy, dx in K8 if 0 <= y + dy < 128 and 0 <= x + dx < 128])
            vals = vals[vals >= 0]
            u, c = np.unique(vals, return_counts=True)
            if c.max() >= 2: v = u[c.argmax()]
            else: v = u[np.argmin(((pal[u].astype(float) - pal[out[y, x]]) ** 2).sum(1))]
            new[y, x] = v; ch += 1
        out = new
        if not ch: break
    return out

def polish(out, pal, og=None, dep=None, protect=None):
    out = fill_small_holes(out, og, dep)
    out = bridge_islands(out, og, dep)
    out = drop_islands(out)
    out = shave_spurs(out)
    out = fill_small_holes(out, og, dep)
    out = merge_specks(out, pal, protect)
    return out

def edge_mask(out):
    op = out >= 0; e = np.zeros_like(op)
    for dy, dx in K4: e |= op & (nb(out, dy, dx) < 0)
    return e

def restroke(out, pal, sh, contour=None, protect=None):
    """silhouette edge -> outline shade of the colour behind it; contour (internal overlap lines) -> contour shade.
    Orphan outline/contour pixels take the shade most common among their outline neighbours."""
    res = out.copy(); edge = edge_mask(out)
    inner = (out >= 0) & ~edge
    # colour behind an edge pixel: the nearest interior pixel's colour (thin parts: their own colour)
    if inner.any():
        _, (iy, ix) = ndi.distance_transform_edt(~inner, return_indices=True); base = out[iy, ix]
        dist = np.hypot(iy - np.arange(128)[:, None], ix - np.arange(128)[None, :])
        base = np.where(dist <= 2.0, base, out)
    else: base = out
    sel = edge          # the silhouette is always outlined (also across hand-placed face pixels: profile nose/chin)
    res[sel] = sh.ol[np.maximum(base[sel], 0)]
    line = edge.copy()
    if contour is not None:
        c = contour & ~edge & (out >= 0)
        res[c] = sh.ct[np.maximum(out[c], 0)]; line |= c
    # consolidate: a line pixel whose colour no 8-neighbour shares takes the majority colour of neighbouring line px
    for _ in range(2):
        same = sum(((nb(res, dy, dx) == res) & (res >= 0)).astype(int) for dy, dx in K8)
        ys, xs = np.nonzero(line & (same == 0))
        if len(ys) == 0: break
        new = res.copy()
        for y, x in zip(ys, xs):
            vals = [res[y + dy, x + dx] for dy, dx in K8 if 0 <= y + dy < 128 and 0 <= x + dx < 128 and line[y + dy, x + dx]]
            if vals: new[y, x] = mode_of(np.array(vals))
        res = new
    for _ in range(4):          # re-darkened line pixels can orphan again: alternate until stable
        nxt = enforce_outline(despeckle(res, pal, protect), pal, sh)
        if np.array_equal(nxt, res): break
        res = nxt
    return res

def enforce_outline(res, pal, sh, steps=3):
    """a silhouette pixel must read as line: absolutely dark (L <= 62) or >= 18 darker than the lightest interior
    pixel touching it.  Pixels that fail (thin parts, junctions) step down their own outline ramp."""
    L = pal.astype(float) @ LW
    for _ in range(steps):
        edge = edge_mask(res); inner = (res >= 0) & ~edge
        Li = np.where(inner, L[np.maximum(res, 0)], -1.0)
        L3 = ndi.maximum_filter(Li, size=3, mode='constant', cval=-1.0)
        Lmax = np.where(L3 >= 0, L3, ndi.maximum_filter(Li, size=5, mode='constant', cval=-1.0))   # thin tips
        Le = L[np.maximum(res, 0)]
        bad = edge & (Le > 62) & (Lmax >= 0) & (Le > Lmax - 18)
        if not bad.any(): break
        res = res.copy(); res[bad] = sh.ol[res[bad]]
    return res

SPECK_D = 48.0   # an orphan within this RGB distance of a neighbour's colour is noise; farther = deliberate detail

def despeckle(out, pal, protect=None, passes=3):
    """merge orphan pixels (no same-colour 8-neighbour) that are only a near-shade of a neighbour into that
    neighbour's colour -- removes AI texture noise while keeping deliberate single-pixel details (pupils, buttons).
    Outline pixels only merge into neighbouring outline/dark pixels (the line stays a line, one shade per run).
    Applied in place, pixel by pixel, so two adjacent near-twins cannot swap colours forever."""
    P = pal.astype(float); out = out.copy(); edge = edge_mask(out); Lp = P @ LW
    for _ in range(passes):
        op = out >= 0
        same = sum(((nb(out, dy, dx) == out) & op).astype(int) for dy, dx in K8)
        nop = sum((nb(out, dy, dx) >= 0).astype(int) for dy, dx in K8)
        # (face pixels too: a near-shade orphan there is master noise; true features are far from every neighbour)
        ys, xs = np.nonzero(op & (same == 0) & (nop >= 3))
        if len(ys) == 0: break
        ch = 0
        for y, x in zip(ys, xs):
            v = out[y, x]
            if any(out[y + dy, x + dx] == v for dy, dx in K8 if 0 <= y + dy < 128 and 0 <= x + dx < 128): continue
            nn = [(y + dy, x + dx) for dy, dx in K8 if 0 <= y + dy < 128 and 0 <= x + dx < 128 and out[y + dy, x + dx] >= 0]
            if edge[y, x]: nn = [q for q in nn if edge[q] or Lp[out[q]] <= 62]     # line px join line/dark px
            if not nn: continue
            u, c = np.unique(np.array([out[q] for q in nn]), return_counts=True)
            d = np.sqrt(((P[u] - P[v]) ** 2).sum(1))
            if d.min() >= SPECK_D: continue
            sc = d - 0.5 * c; sc[d >= SPECK_D] = 1e9      # nearest shade; near-ties -> the commoner neighbour colour
            out[y, x] = u[int(sc.argmin())]; ch += 1
        if not ch: break
    return out
