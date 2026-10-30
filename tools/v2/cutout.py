"""v2 style, step 2: animate the AI master idle frames with the procedural rig skeleton (cut-out / bone
deformation).  Every master pixel is bound to the rig primitive (bone) that owns it in the rig's own render of
the same idle pose; for a target pose each bone gets a 2-D bone transform (rotate + stretch along the bone,
from the projected joint endpoints) and pixels are inverse-mapped from the master.  Depth = the rig's depth at
the bound pixel + the bone's depth change, so limbs pass in front of/behind the body correctly.  Because all
frames come from ONE master per direction, the face/hair/clothing never drift between frames."""
import math, os, sys, numpy as np
from scipy import ndimage as ndi
import char_rig as R
ROOT = '/workspace/bbt-pixel'

def anchors(P, yaw):
    """per primitive: ('cap', A, B, depth) or ('pt', C, None, depth) in screen space"""
    out = []
    for kind, args, m, t in P:
        if kind == 'cap':
            a = np.array(args[0], float); b = np.array(args[1], float)
            ca, ra, da = R.project_local(a, yaw); cb, rb, db = R.project_local(b, yaw)
            out.append(('cap', np.array([ca, ra]), np.array([cb, rb]), (da + db) / 2))
        else:
            if kind == 'skirt': c = np.array([args[4] * 0.5, args[5] * 0.5, (args[0] + args[1]) / 2])
            else: c = np.array(args[0], float)
            cc, rr, dd = R.project_local(c, yaw); out.append(('pt', np.array([cc, rr]), None, dd))
    return out

def warp_rig(B, aim):
    rim = B['mat'] >= 0; H, W = rim.shape
    sc = np.full(H, np.nan); of = np.full(H, np.nan)
    for y in range(H):
        rx = np.where(rim[y])[0]; ax = np.where(aim[y])[0]
        if len(rx) >= 2 and len(ax) >= 1:
            s_ = (ax[-1] + 1 - ax[0]) / (rx[-1] + 1 - rx[0]); sc[y] = s_; of[y] = ax[0] - rx[0] * s_
    ok = ~np.isnan(sc)
    if not ok.any(): return B, lambda p: p
    ys = np.arange(H)
    sc = np.interp(ys, ys[ok], sc[ok]); of = np.interp(ys, ys[ok], of[ok])
    sc = ndi.median_filter(sc, 5, mode='nearest'); of = ndi.median_filter(of, 5, mode='nearest')
    sc = ndi.uniform_filter1d(sc, 3, mode='nearest'); of = ndi.uniform_filter1d(of, 3, mode='nearest')
    # inverse sample rig buffers at AI pixel centres
    yy, xx = np.mgrid[0:H, 0:W]
    xr = np.clip(np.floor((xx + 0.5 - of[yy]) / sc[yy]).astype(int), 0, W - 1)
    Bw = {'mat': B['mat'][yy, xr], 'pid': B['pid'][yy, xr], 'depth': B['depth'][yy, xr]}
    def warp(p):
        y = int(np.clip(round(p[1] - 0.5), 0, H - 1))
        return np.array([p[0] * sc[y] + of[y], p[1]])
    return Bw, warp

def bind(master_idx, B):
    """label each master pixel with a rig primitive id + rig depth (nearest rig pixel when outside the rig)"""
    pid = B['pid'].copy(); pid[B['mat'] < 0] = -1
    has = pid >= 0
    _, (iy, ix) = ndi.distance_transform_edt(~has, return_indices=True)
    lab = pid[iy, ix]; dep = B['depth'][iy, ix]
    m = master_idx >= 0
    return np.where(m, lab, -1), np.where(m, dep, 1e9)

LIMB_TAGS = ('leg', 'foot', 'arm', 'sleeve', 'hand')
def limb_pairs(P):
    """index -> index of the same primitive on the other side (left/right leg, arm, ...)"""
    seen = {}
    for k, (kind, args, m, t) in enumerate(P):
        if t not in LIMB_TAGS: continue
        side = 0 if float(np.array(args[0])[0]) < 0 else 1
        seen.setdefault((t, m, kind, side), []).append(k)
    pair = {}
    for (t, m, kind, side), ks in seen.items():
        other = seen.get((t, m, kind, 1 - side), [])
        for a, b in zip(ks, other): pair[a] = b
    return pair

def darker_map(pal, f=0.80):
    L = pal @ np.array([0.299, 0.587, 0.114]); out = np.arange(len(pal))
    for k, c in enumerate(pal):
        cand = np.where(L < L[k] - 6)[0]
        if len(cand) == 0: continue
        d = ((pal[cand] - c * f) ** 2 * np.array([0.30, 0.59, 0.11])).sum(1); out[k] = cand[d.argmin()]
    return out

class Cutout:
    def __init__(self, master_idx, base_B, base_pose, yaw, pal=None):
        self.pal = pal
        self.idx = flatten_rim(master_idx, pal) if pal is not None else master_idx; self.yaw = yaw
        # the AI figure is slimmer than the rig: warp the rig's labels/anchors row-by-row onto the AI silhouette
        Bw, self.warp = warp_rig(base_B, master_idx >= 0)
        self.lab, self.dep = bind(master_idx, Bw)
        P0 = R.build(base_pose); self.A0raw = anchors(P0, yaw)
        self.A0 = [(a[0], self.warp(a[1]), None if a[2] is None else self.warp(a[2]), a[3]) for a in self.A0raw]
        self.grp = np.array([group_of(p) for p in P0] + [-1])
        # hidden far limbs (side views): bind the sliver of the far limb to the near one and draw the far
        # limb as a one-shade-darker copy of the near limb
        self.copy_of = {}
        pair = limb_pairs(P0); cnt = np.bincount(self.lab[self.lab >= 0], minlength=len(P0))
        yy, xx = np.mgrid[0:128, 0:128]; Pp = np.stack([xx + 0.5, yy + 0.5], -1)
        def segd(k):
            an = self.A0[k]
            if an[0] != 'cap': return np.linalg.norm(Pp - an[1], axis=-1)
            P, Q = an[1], an[2]; v = Q - P; L2 = max(v @ v, 1e-6)
            tt = np.clip(((Pp - P) @ v) / L2, 0, 1); return np.linalg.norm(Pp - (P + tt[..., None] * v), axis=-1)
        def cen(k):
            an = self.A0[k]; return an[1] if an[0] != 'cap' else (an[1] + an[2]) / 2
        for a, b in pair.items():
            if cnt[a] < 0.6 * cnt[b]:
                if abs(cen(a)[0] - cen(b)[0]) < 6:
                    self.copy_of[a] = b          # genuinely overlapping (side view): far limb = darker copy
                else:
                    # limbs apart on screen but the rig labels went to one of them: split by nearest bone
                    reg = np.isin(self.lab, [a, b]); da, db = segd(a), segd(b)
                    self.lab[reg & (da < db)] = a; self.lab[reg & (da >= db)] = b
        for a, b in self.copy_of.items(): self.lab[self.lab == a] = b
        # side views: the two legs overlap in the master, so rig labels below the crotch are a patchwork of
        # pelvis / torso / near leg / far leg; static pelvis remnants shred the walk.  Re-own every master
        # pixel below the crotch (except hands/sleeves) to the nearest NEAR leg bone (thigh / shin / foot).
        tags = [p[3] for p in P0]
        near_legs = sorted(set(b for a, b in self.copy_of.items() if tags[b] in ('leg', 'foot')))
        if not near_legs:      # legs apart on screen: both legs own the region below the crotch
            near_legs = [k for k, t in enumerate(tags) if t in ('leg', 'foot')]
        if near_legs and any(self.A0[k][0] == 'cap' for k in near_legs):
            caps = [k for k in near_legs if self.A0[k][0] == 'cap']; feet = [k for k in near_legs if self.A0[k][0] != 'cap']
            crotch = min(min(self.A0[k][1][1], self.A0[k][2][1]) for k in caps) + 2
            yy, xx = np.mgrid[0:128, 0:128]; Pp = np.stack([xx + 0.5, yy + 0.5], -1)
            arm_ids = [k for k, t in enumerate(tags) if t in ('arm', 'sleeve', 'hand')]
            arm = np.isin(self.lab, arm_ids)
            # an arm-labelled pixel below the crotch stays on the arm only if its colour is closest to an arm
            # material (skin / sleeve) among the rig's materials (pants pixels nearest-bound to a hanging hand
            # would otherwise swing with it)
            if pal is not None:
                mats = sorted(set(p[2] for p in P0 if p[2] in R.C)); mc = np.array([R.C[m] for m in mats], float)
                cls = np.array([mats[int(((mc - c) ** 2).sum(1).argmin())] for c in pal.astype(float)])
                armm = set(P0[k][2] for k in arm_ids)
                okc = np.array([c in armm for c in cls])
                arm = arm & ((yy <= crotch - 4) | okc[np.maximum(master_idx, 0)])
            reg = (master_idx >= 0) & (yy > crotch) & ~arm
            best = np.full((128, 128), 1e9); own = np.full((128, 128), -1)
            for k in caps:
                P, Q = self.A0[k][1], self.A0[k][2]; v = Q - P; L2 = max(v @ v, 1e-6)
                tt = np.clip(((Pp - P) @ v) / L2, 0, 1); dist = np.linalg.norm(Pp - (P + tt[..., None] * v), axis=-1)
                w = dist < best; best[w] = dist[w]; own[w] = k
            if feet:
                shin_end = max(max(self.A0[k][1][1], self.A0[k][2][1]) for k in caps)
                low = yy + 0.5 > shin_end
                if len(feet) == 1: own[low] = feet[0]
                else:
                    # each foot takes the low pixels on the side of its own shin
                    fd = np.stack([np.abs(xx + 0.5 - self.A0[f][1][0]) for f in feet]); fo = np.array(feet)[fd.argmin(0)]
                    own[low] = fo[low]
            self.lab[reg] = own[reg]
        # copy sources: only master pixels close to the near limb's bone (no stray nearest-bound pixels)
        self.copy_src = {}
        yy, xx = np.mgrid[0:128, 0:128]; Pp = np.stack([xx + 0.5, yy + 0.5], -1)
        rig = Bw['pid']
        for a, b in self.copy_of.items():
            an = self.A0[b]
            if an[0] != 'cap' or b in near_legs: self.copy_src[b] = self.lab == b; continue
            P, Q = an[1], an[2]; v = Q - P; L2 = max(v @ v, 1e-6)
            tt = np.clip(((Pp - P) @ v) / L2, 0, 1); dist = np.linalg.norm(Pp - (P + tt[..., None] * v), axis=-1)
            own = rig == b
            r = dist[own].max() if own.any() else 3.0
            self.copy_src[b] = (self.lab == b) & (dist <= r + 1.5)
        self.dark = darker_map(pal) if pal is not None else np.arange(int(master_idx.max()) + 1)

    def pose(self, tgt_pose, fill=True):
        A1r = anchors(R.build(tgt_pose), self.yaw)
        assert len(A1r) == len(self.A0)
        A1 = [(a[0], a[1] + (w[1] - r[1]), None if a[2] is None else a[2] + (w[2] - r[2]), a[3])
              for a, w, r in zip(A1r, self.A0, self.A0raw)]
        H = W = 128
        best_d = np.full((H, W), 1e9); out = np.full((H, W), -1); og = np.full((H, W), -1)
        ty, tx = np.mgrid[0:H, 0:W]; T = np.stack([tx + 0.5, ty + 0.5], -1)
        for k, (a1,) in enumerate(zip(A1)):
            ks = self.copy_of.get(k, k); a0 = self.A0[ks]
            src = self.copy_src[ks] if ks != k else (self.lab == ks)
            if not src.any(): continue
            dz = a1[3] - a0[3]
            if a0[0] == 'cap':
                P0, Q0 = a0[1], a0[2]; P1, Q1 = a1[1], a1[2]
                L0 = np.linalg.norm(Q0 - P0); L1 = np.linalg.norm(Q1 - P1)
                if L0 < 1.0 or L1 < 1.0:
                    mid0 = (P0 + Q0) / 2; mid1 = (P1 + Q1) / 2
                    S = T - mid1 + mid0
                else:
                    u0 = (Q0 - P0) / L0; n0 = np.array([-u0[1], u0[0]])
                    u1 = (Q1 - P1) / L1; n1 = np.array([-u1[1], u1[0]])
                    rel = T - P1; s = rel @ u1; t = rel @ n1
                    s0 = np.where(s < 0, s, np.where(s > L1, L0 + (s - L1), s * L0 / L1))   # stretch only inside the bone
                    S = P0 + s0[..., None] * u0 + t[..., None] * n0
            else:
                S = T - a1[1] + a0[1]
            sx = np.floor(S[..., 0]).astype(int); sy = np.floor(S[..., 1]).astype(int)
            ok = (sx >= 0) & (sx < W) & (sy >= 0) & (sy < H)
            sxc = np.clip(sx, 0, W - 1); syc = np.clip(sy, 0, H - 1)
            hit = ok & src[syc, sxc]
            d = np.where(hit, self.dep[syc, sxc] + dz, 1e9)
            w = d < best_d
            vals = self.idx[syc, sxc]
            if ks != k: vals = np.where(vals >= 0, self.dark[np.maximum(vals, 0)], -1)
            best_d[w] = d[w]; out[w] = vals[w]; og[w] = self.grp[k]
        if fill: out = fill_holes(out)
        out = drop_specks(out)
        self.last = (out, og, best_d)
        if self.pal is not None: out = finish(out, og, best_d, self.pal)
        return out

def fill_holes(out):
    """close pixel gaps opened at joints (both horizontal or both vertical neighbours opaque)"""
    for _ in range(2):
        op = out >= 0; P = np.pad(out, 1, constant_values=-1)
        l, r, u, d = P[1:-1, :-2], P[1:-1, 2:], P[:-2, 1:-1], P[2:, 1:-1]
        hz = (~op) & (l >= 0) & (r >= 0); vt = (~op) & (u >= 0) & (d >= 0)
        out = out.copy(); out[hz] = l[hz]; out[vt & ~hz] = u[vt & ~hz]
    return out

def drop_specks(out, keep_min=24):
    lab, n = ndi.label(out >= 0)
    if n <= 1: return out
    sz = np.bincount(lab.ravel()); sz[0] = 0
    bad = (sz < keep_min) & (np.arange(len(sz)) != sz.argmax())
    out = out.copy(); out[bad[lab] & (lab > 0)] = -1
    return out

def group_of(p):
    kind, args, m, t = p
    if t in ('leg', 'foot'): return 10 + (0 if float(np.array(args[0])[0]) < 0 else 1)
    if t in ('arm', 'sleeve', 'hand'): return 20 + (0 if float(np.array(args[0])[0]) < 0 else 1)
    if kind == 'head': return 1
    return 0

def flatten_rim(idx, pal):
    """drop the AI's baked silhouette outline / white halo: rim pixels take the colour of the nearest
    interior pixel (the outline is redrawn after posing)"""
    op = idx >= 0
    inner = ndi.binary_erosion(op, structure=np.ones((3, 3)))
    if not inner.any(): return idx
    _, (iy, ix) = ndi.distance_transform_edt(~inner, return_indices=True)
    out = idx.copy(); rim = op & ~inner
    L = pal @ np.array([0.299, 0.587, 0.114])
    # keep genuinely dark rim pixels that are dark features (hair, shoes): only replace if the interior
    # neighbour is clearly different (outline) or the rim pixel is a light halo
    src = idx[iy, ix]
    rep = rim & ((L[np.maximum(idx, 0)] < L[np.maximum(src, 0)] - 25) | (L[np.maximum(idx, 0)] > L[np.maximum(src, 0)] + 40))
    out[rep] = src[rep]
    return out

def finish(out, og, dep, pal):
    """internal contour where a limb passes over another body part + coloured selective silhouette outline"""
    from master import outline_idx
    L = pal @ np.array([0.299, 0.587, 0.114])
    def darker(k, f):
        c = pal[k]; dd = ((pal - c * f) ** 2).sum(1) + 1e9 * (L > L[k] - 8)
        return int(dd.argmin()) if dd.min() < 1e8 else k
    res = out.copy(); op = out >= 0
    Po = np.pad(out, 1, constant_values=-1); Pg = np.pad(og, 1, constant_values=-9); Pd = np.pad(dep, 1, constant_values=1e9)
    mark = np.zeros_like(op)
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        qo = Po[1 + dy:129 + dy, 1 + dx:129 + dx]; qg = Pg[1 + dy:129 + dy, 1 + dx:129 + dx]; qd = Pd[1 + dy:129 + dy, 1 + dx:129 + dx]
        m = op & (qo >= 0) & (qg != og) & (dep > qd + 1.0) & ~((og <= 1) & (qg <= 1)) & ~(((og == 0) & (qg >= 10) & (qg < 20)) | ((qg == 0) & (og >= 10) & (og < 20)))
        mark |= m
    for y, x in zip(*np.where(mark)):
        k = out[y, x]
        if L[k] >= 60: res[y, x] = darker(k, 0.70)
    return outline_idx(res, pal, None)
