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
    if not ok.any(): return B, lambda p: p, np.ones(H)
    ys = np.arange(H)
    sc = np.interp(ys, ys[ok], sc[ok]); of = np.interp(ys, ys[ok], of[ok])
    sc = ndi.median_filter(sc, 5, mode='nearest'); of = ndi.median_filter(of, 5, mode='nearest')
    sc = ndi.uniform_filter1d(sc, 3, mode='nearest'); of = ndi.uniform_filter1d(of, 3, mode='nearest')
    # inverse sample rig buffers at AI pixel centres
    yy, xx = np.mgrid[0:H, 0:W]
    xr = np.clip(np.floor((xx + 0.5 - of[yy]) / sc[yy]).astype(int), 0, W - 1)
    Bw = {'mat': B['mat'][yy, xr], 'pid': B['pid'][yy, xr], 'depth': B['depth'][yy, xr]}
    Bw['_xr'] = xr
    def warp(p):
        y = int(np.clip(round(p[1] - 0.5), 0, H - 1))
        return np.array([p[0] * sc[y] + of[y], p[1]])
    return Bw, warp, sc

def bind(master_idx, B):
    """label each master pixel with a rig primitive id + rig depth (nearest rig pixel when outside the rig)"""
    pid = B['pid'].copy(); pid[B['mat'] < 0] = -1
    has = pid >= 0
    _, (iy, ix) = ndi.distance_transform_edt(~has, return_indices=True)
    lab = pid[iy, ix]; dep = B['depth'][iy, ix]
    m = master_idx >= 0
    return np.where(m, lab, -1), np.where(m, dep, 1e9)

# v3 arm painter: per character (sleeve material or 'sleeve' = the rig's sleeve material, short-sleeve length as a
# fraction of the upper arm (None = long sleeve to the wrist), material below the short sleeve) and
# (upper-arm radius px, hand half-width px)
ARM_SPEC = {'sheldon': ('tee', 0.5, 'under'), 'penny': ('top', 0.45, 'skin'), 'raj': ('shirt', None, None)}
ARM_R = {'sheldon': (2.3, 2.1), 'leonard': (2.5, 2.1), 'penny': (2.0, 1.9), 'howard': (2.1, 2.0), 'raj': (2.6, 2.2),
         'bernadette': (2.1, 1.9), 'amy': (2.1, 1.9)}
LIMB_TAGS = ('leg', 'foot', 'arm', 'sleeve', 'hand')
MATCOL = {}
REPAINT = tuple(t for t in os.environ.get('BBT_REPAINT', 'leg,arm,sleeve,hand').split(',') if t)
def _radii(p):
    a = p[1]; ra = float(a[2]); rb = float(a[3]) if len(a) > 3 and np.isscalar(a[3]) else ra
    return ra, rb


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
    def __init__(self, master_idx, base_B, base_pose, yaw, pal=None, protect=None, base_Bna=None):
        self.pal = pal
        self.protect = protect if protect is not None else np.zeros(master_idx.shape, bool)
        self.idx = flatten_rim(master_idx, pal) if pal is not None else master_idx; self.yaw = yaw
        # the AI figure is slimmer than the rig: warp the rig's labels/anchors row-by-row onto the AI silhouette
        Bw, self.warp, self.wsc = warp_rig(base_B, master_idx >= 0)
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
                tg = P0[b][3]
                # feet follow their shins (rig order: thigh, shin, foot): copy a far foot only when the shins overlap
                ca, cb = (a - 1, b - 1) if (tg == 'foot' and P0[a - 1][3] == 'leg' and P0[b - 1][3] == 'leg') else (a, b)
                if abs(cen(ca)[0] - cen(cb)[0]) < 6:
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
            # skirts / dresses stay on the (static) skirt primitive down to the rig's hem: only the legs below
            # the hem walk, otherwise the leg bones tear the cloth apart in side views
            sk_ids = [k for k, t in enumerate(tags) if t == 'skirt']
            if sk_ids and pal is not None:
                rigp = Bw['pid']; skm = np.isin(rigp, sk_ids)
                if skm.any():
                    hem = np.nonzero(skm.any(1))[0].max() + 1
                    skmats = set(P0[k][2] for k in sk_ids) | set(P0[k][2] for k, t in enumerate(tags) if t == 'pelvis')
                    okk = np.array([c in skmats for c in cls])
                    cloth = reg & (yy <= hem - 1)
                    own[cloth] = sk_ids[0]
            self.lab[reg] = own[reg]
        self.lab = coherent_labels(self.lab, master_idx >= 0)
        # a foot is ONE shoe: keep the foot label's biggest blob (side-view masters show both shoes under the near
        # foot's label; the stray second shoe would walk along with it)
        for k, p in enumerate(P0):
            if p[3] != 'foot' or not (self.lab == k).any(): continue
            cc, n = ndi.label(self.lab == k, structure=np.ones((3, 3)))
            if n > 1:
                sz = np.bincount(cc.ravel())[1:]; keep = cc == (1 + int(sz.argmax()))
                self.lab[(self.lab == k) & ~ndi.binary_dilation(keep, iterations=1)] = -2   # dropped
        self.P0 = P0; self.tags = [p[3] for p in P0]
        self.arms0 = [tuple(np.array(v, float) for v in a) for a in R.LAST_ARMS]   # filled by R.build(base_pose) above? (rebuilt below)
        R.build(base_pose); self.arms0 = [tuple(np.array(v, float) for v in a) for a in R.LAST_ARMS]
        self.arm_paint = pal is not None and 'arm' in REPAINT and len(self.arms0) == 2 and 'hand_l' in R.DIM
        if self.arm_paint and base_Bna is not None:
            # v3 arms are shorter/slimmer than the AI master's: the body the AI arm covered is revealed.  Where the
            # arm-less rig has body under an arm pixel, re-own it to the nearest non-arm body pixel (label + colour);
            # elsewhere the old arm pixel is simply dropped (the painter draws the new arm)
            arm_ids = [k for k, t in enumerate(self.tags) if t in ('arm', 'sleeve', 'hand')]
            op = master_idx >= 0; armpx = op & np.isin(self.lab, arm_ids)
            xr = Bw['_xr']; Bn = base_Bna
            yy2 = np.mgrid[0:128, 0:128][0]
            bmat = Bn['mat'][yy2, xr]; bpid = Bn['pid'][yy2, xr]
            body = (bmat >= 0) & ~np.isin(bpid, arm_ids)
            body = ndi.binary_erosion(body, iterations=2)
            src = op & ~armpx & (self.lab >= 0)
            if src.any() and armpx.any():
                _, (iy, ix) = ndi.distance_transform_edt(~src, return_indices=True)
                # only inside the row span of the non-arm body (a hand that hung beside the hips must not become a hip bulge)
                xs = np.arange(128)[None, :]; has = src.any(1)
                lo = np.where(has, src.argmax(1), 999)[:, None]; hi = np.where(has, 127 - src[:, ::-1].argmax(1), -1)[:, None]
                rev = armpx & body & (xs >= lo) & (xs <= hi)
                self.lab[rev] = self.lab[iy, ix][rev]; self.idx = self.idx.copy(); self.idx[rev] = self.idx[iy, ix][rev]
                self.dep[rev] = self.dep[iy, ix][rev]
                self.lab[armpx & ~body] = -2
        # rig material of each primitive -> nearest palette colour (patch colour for joints / hidden limb segments)
        self.patch_col = {}
        if pal is not None:
            for k, p in enumerate(P0):
                if p[3] not in LIMB_TAGS or p[0] != 'cap': continue
                src = self.idx[self.lab == k]; src = src[src >= 0]
                if len(src) >= 12:
                    Lp = pal[src].astype(float) @ np.array([0.299, 0.587, 0.114]); med = np.median(Lp)
                    cand = src[np.abs(Lp - med) <= 30]; cand = cand if len(cand) else src; u, c = np.unique(cand, return_counts=True); self.patch_col[k] = int(u[c.argmax()])
                elif p[2] in R.C:
                    self.patch_col[k] = int((((pal.astype(float) - R.C[p[2]].astype(float)) ** 2).sum(1)).argmin())
        self.dark = darker_map(pal) if pal is not None else np.arange(int(master_idx.max()) + 1)
        # limb repaint: limbs are re-drawn as clean shaded capsules in the target pose (rotating the AI's textured
        # limb pixels shreds them); width calibrated to the master's own limb pixels
        self.rep = {}
        self.mat_col = {}; self.mat_stats = {}
        if pal is not None:
            Lw = np.array([0.299, 0.587, 0.114])
            for m in set(p[2] for p in P0):
                ids = [k for k, p in enumerate(P0) if p[2] == m]
                if m == 'skin' and (self.idx[np.isin(self.lab, ids)] >= 0).sum() < 12:
                    ids += [k for k, p in enumerate(P0) if p[3] == 'head']
                src = self.idx[np.isin(self.lab, ids)]; src = src[src >= 0]
                rk = R.RAMP[m][1] if (getattr(R, 'RAMP', None) and m in R.RAMP) else m
                ref = R.C[rk].astype(float) if rk in R.C else None
                if len(src) >= 12:
                    Lp = pal[src].astype(float) @ Lw; med = np.percentile(Lp, 65)
                    cand = src[np.abs(Lp - med) <= 32]; u, c = np.unique(cand, return_counts=True)
                    if ref is not None:   # prefer the commonest master colour that is plausibly this material
                        dd = np.sqrt(((pal[u].astype(float) - ref) ** 2).sum(1)); c = c * np.exp(-(dd / 45.0) ** 2) * (dd < 90)
                    self.mat_stats[m] = (u, c)
                    if c.max() > 0: self.mat_col[m] = int(u[c.argmax()]); continue
                if ref is not None: self.mat_col[m] = int((((pal.astype(float) - ref) ** 2).sum(1)).argmin())
        self.mat_col.update(MATCOL)          # character-wide table (build_v2), same limb colours in every direction
        if pal is not None and REPAINT:
            Ls = [p[3] for p in P0]
            for k, p in enumerate(P0):
                if p[0] != 'cap' or p[3] not in REPAINT or (k not in self.patch_col and p[2] not in self.mat_col): continue
                an = self.A0[k]; L0 = float(np.linalg.norm(an[2] - an[1])); yc = int(np.clip((an[1][1] + an[2][1]) / 2, 0, 127))
                rr = sum(_radii(p)) / 2 * R.SCALE_EFF * float(self.wsc[yc])
                area = float((self.lab == k).sum())
                kw = area / (2 * L0 * rr + np.pi * rr * rr) if area > 20 and L0 > 2 else 0.8
                lo = {'leg': 0.8, 'hand': 0.9}.get(p[3], 0.7)
                self.rep[k] = [float(np.clip(kw, lo, 1.0)), self.mat_col.get(p[2], self.patch_col.get(k, 0))]
            for a, b in self.copy_of.items():
                if a in self.rep and b in self.rep: self.rep[a] = [self.rep[b][0], int(self.dark[self.rep[b][1]])]
            # left/right pairs share width (the hidden one has few master pixels)
            for a, b in limb_pairs(P0).items():
                if a in self.rep and b in self.rep and a not in self.copy_of and b not in self.copy_of:
                    w = max(self.rep[a][0], self.rep[b][0]); self.rep[a][0] = self.rep[b][0] = w
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

    mirror_x = False
    def pose(self, tgt_pose, fill=True):
        A1r = anchors(R.build(tgt_pose), self.yaw); arms1 = [tuple(np.array(v, float) for v in a) for a in R.LAST_ARMS]
        assert len(A1r) == len(self.A0)
        A1 = [(a[0], a[1] + (w[1] - r[1]), None if a[2] is None else a[2] + (w[2] - r[2]), a[3])
              for a, w, r in zip(A1r, self.A0, self.A0raw)]
        H = W = 128
        best_d = np.full((H, W), 1e9); out = np.full((H, W), -1); og = np.full((H, W), -1); prot = np.zeros((H, W), bool)
        ty, tx = np.mgrid[0:H, 0:W]; T = np.stack([tx + 0.5, ty + 0.5], -1)
        order = sorted(range(len(A1)), key=lambda k: (self.P0[k][3] == 'neck'))
        for k in order:
            a1 = A1[k]
            if self.arm_paint and self.tags[k] in ('arm', 'sleeve', 'hand'): continue
            if k in self.rep:
                self.paint_limb(k, a1, T, out, og, best_d); continue
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
            elif self.P0[k][3] == 'foot' and k > 0 and self.P0[k - 1][3] == 'leg' and A1[k - 1][0] == 'cap':
                sh0 = self.A0[ks - 1]; sh1 = A1[k - 1]      # shoe stays attached to its own shin's ankle
                S = T - np.round(sh1[2] - sh0[2])
            else:
                S = T - np.round(a1[1] - a0[1])          # rigid, whole-pixel move (no resampling shimmer)
                if self.P0[k][3] == 'head' and tgt_pose.get('head_off'):   # v2.1: nods / tilts / hunches as whole-pixel head shifts
                    ho = np.array(tgt_pose['head_off'], float)
                    if self.mirror_x: ho[0] = -ho[0]
                    S = S - ho
            sx = np.floor(S[..., 0]).astype(int); sy = np.floor(S[..., 1]).astype(int)
            ok = (sx >= 0) & (sx < W) & (sy >= 0) & (sy < H)
            sxc = np.clip(sx, 0, W - 1); syc = np.clip(sy, 0, H - 1)
            hit = ok & src[syc, sxc]
            d = np.where(hit, self.dep[syc, sxc] + dz, 1e9)
            w = d < best_d
            vals = self.idx[syc, sxc]
            if ks != k: vals = np.where(vals >= 0, self.dark[np.maximum(vals, 0)], -1)
            best_d[w] = d[w]; out[w] = vals[w]; og[w] = self.grp[k]; prot[w] = self.protect[syc, sxc][w] & (ks == k)
        if self.arm_paint:
            for i in (0, 1): self.paint_arm(i, arms1[i], T, out, og, best_d)
        if self.pal is not None:
            self.underlay(A1, out, og, best_d)
            import pixfix as PF
            out = PF.polish(out, self.pal, og, best_d, prot)
            og[out < 0] = -1; best_d[out < 0] = 1e9
        else:
            if fill: out = fill_holes(out)
            out = drop_specks(out)
        self.prot = prot
        self.last = (out, og, best_d)
        if self.pal is not None: out = finish(out, og, best_d, self.pal, prot)
        return out

    def paint_limb(self, k, a1, T, out, og, best_d):
        kw, base = self.rep[k]
        P, Q = a1[1], a1[2]; v = Q - P; L2 = max(v @ v, 1e-6)
        tt = np.clip(((T - P) @ v) / L2, 0, 1); C = P + tt[..., None] * v; off = T - C
        dist = np.linalg.norm(off, axis=-1)
        ra, rb = _radii(self.P0[k])
        yc = int(np.clip((P[1] + Q[1]) / 2, 0, 127))
        r = (ra + (rb - ra) * tt) * R.SCALE_EFF * float(self.wsc[yc]) * kw
        if self.P0[k][3] == 'hand': r = np.maximum(r, 2.1)
        m = dist <= np.maximum(r, 0.9)
        d = a1[3] - (ra + rb) / 2 * R.SCALE_EFF
        # side views: the near arm (its partner is drawn as a darker copy) is in front of the torso, whose master
        # pixels carry the rig's chest depth; without the bias the chest swallows the swinging near arm
        if self.P0[k][3] in ('arm', 'sleeve', 'hand') and k in self.copy_of.values(): d -= 8.0
        if self.P0[k][3] == 'neck': d = 1e7      # neck only fills what head / collar leave open
        w = m & (d < best_d)
        # 2 tones: lit left, one shade darker on the right third (light from the upper left, like the masters)
        shade = (off[..., 0] > 0.34 * r) & (r >= 1.6)
        col = np.where(shade, self.dark[base], base)
        out[w] = col[w]; og[w] = self.grp[k]; best_d[w] = d

    def paint_arm(self, i, arm, T, out, og, best_d):
        """v3 arm: deltoid-rounded upper arm tapering to the wrist, visible elbow, sleeve to its real length (short
        sleeve hem at mid upper arm / long sleeve with a darker cuff), skin forearm where bare, and a mitten hand
        (palm a little wider than the wrist, rounded fingertips, 1-px thumb bump on the thumb side), two tones,
        per-pixel depth along each bone so a forward-swung forearm passes in front of the body"""
        sh, el, wr, d2 = arm; sh0 = self.arms0[i][0]
        c0, r0, _ = R.project_local(sh0, self.yaw); off = self.warp(np.array([c0, r0])) - np.array([c0, r0])
        def pj(p):
            c, r, d = R.project_local(p, self.yaw); return np.array([c, r]) + off, d
        side = -1.0 if i == 0 else 1.0
        S, dS = pj(sh); E, dE = pj(el); W, dW = pj(wr)
        D = R.DIM; hl = D['hand_l']
        H, dH = pj(wr + d2 * hl)
        ids = [k for k, t in enumerate(self.tags) if t in ('arm', 'sleeve', 'hand') and self.grp[k] == 20 + i]
        far = any(k in self.copy_of for k in ids); near = any(k in self.copy_of.values() for k in ids)
        spec = ARM_SPEC.get(R.CID, ('sleeve', None, None))
        smat = spec[0]
        if smat == 'sleeve':
            smat = next((self.P0[k][2] for k in ids if self.tags[k] == 'sleeve'), 'skin')
        frac, under = spec[1], spec[2] or smat
        ru, hw = ARM_R.get(R.CID, (2.3, 2.0))
        re, rw = ru * 0.86, ru * 0.70
        col = lambda m: self.mat_col.get(m, self.mat_col.get('skin', 0))
        cs, cu, ck = col(smat), col(under), col('skin')
        if far: cs, cu, ck = int(self.dark[cs]), int(self.dark[cu]), int(self.dark[ck])
        bias = -16.0 if near else (0.0 if far else -10.0)   # near arm always over the torso side (bulky hoodies / cardigans); a hanging arm sits outside the skirt flare
        sc = R.SCALE_EFF
        def seg(P, Q):
            v = Q - P; L2 = max(v @ v, 1e-6); t = np.clip(((T - P) @ v) / L2, 0, 1)
            o = T - (P + t[..., None] * v); return t, o, np.linalg.norm(o, axis=-1)
        Ld = np.array([0.86, 0.5])
        def put(m, d, c, r, o, lit=True):
            shade = ((o @ Ld) > 0.30 * r) & (r >= 1.5) if lit else np.zeros_like(m)
            cc = np.where(shade, self.dark[c], c)
            w = m & (d < best_d)
            out[w] = cc[w]; og[w] = 20 + i; best_d[w] = d[w]
        # upper arm (deltoid bulge over the top ~40 %)
        t, o, dist = seg(S, E)
        r = ru + (re - ru) * t + 0.55 * np.clip(1 - t / 0.42, 0, 1) ** 1.5
        d = dS + (dE - dS) * t - r / sc + bias
        m = dist <= r
        if frac is None:
            put(m, d, cs, r, o)
        else:
            put(m & (t > frac), d, cu, r, o)
            rs = r + 0.5
            ms = (dist <= rs) & (t <= frac)
            hem = ms & (t > frac - 1.2 / max(np.linalg.norm(E - S), 1.0))
            put(ms & ~hem, d - 0.3, cs, rs, o); put(hem, d - 0.3, int(self.dark[cs]), rs, o, lit=False)
        # forearm (+ cuff on long sleeves)
        t, o, dist = seg(E, W)
        r = re + (rw - re) * t + 0.25 * np.exp(-((t - 0.2) / 0.2) ** 2)
        d = dE + (dW - dE) * t - r / sc + bias - 0.05
        m = dist <= r
        if under != 'skin':
            Lf = max(np.linalg.norm(W - E), 1.0); cuff = m & (t > 1 - 1.6 / Lf)
            put(m & ~cuff, d, cu, r, o)
            mc = (dist <= r + 0.35) & (t > 1 - 1.6 / Lf)
            put(mc, d - 0.1, int(self.dark[cu]), r + 0.35, o, lit=False)
        else:
            put(m, d, cu, r, o)
        # mitten hand: capsule wrist -> knuckles widening to the palm, round fingertips, thumb bump
        hv = H - W; Lh = float(np.linalg.norm(hv))
        if Lh > 1e-3: hu = hv / Lh
        else: hu = np.array([0.0, 1.0])
        P1 = W + hu * min(0.6, Lh * 0.2); Q1 = W + hv - hu * min(hw, Lh * 0.5)
        t, o, dist = seg(P1, Q1)
        r = rw * 0.95 + (hw - rw * 0.95) * np.clip(t * 1.6, 0, 1)
        d = dW + (dH - dW) * t - r / sc + bias - 0.2
        put(dist <= r, d, ck, r, o)
        # thumb: forward + medial of the hand, perpendicular to it
        fwd = np.array([0.0, 1.0, 0.0]); med = np.array([-side, 0.0, 0.0])
        th = 0.8 * fwd + 0.6 * med; th = th - d2 * (th @ d2); n3 = np.linalg.norm(th)
        if n3 > 1e-3:
            th = th / n3
            Tp, dT = pj(wr + d2 * hl * 0.30 + th * 1.0)
            tv = Tp - (W + hv * 0.30)
            if np.linalg.norm(tv) > 0.35:
                tn = tv / np.linalg.norm(tv); cen = W + hv * 0.30 + tn * (hw * 0.95)
                mt = np.linalg.norm(T - cen, axis=-1) <= 0.85
                put(mt, np.full(mt.shape, dT - 0.6 / sc + bias + (0.0 if dT <= dW else 0.4)), ck, np.full(mt.shape, 0.85), T - cen, lit=False)

    def underlay(self, A1, out, og, dep):
        """joint / hidden-segment patch layer: every limb capsule of the target pose (core radius) is painted UNDER the
        posed pixels with the limb's own dominant colour, so bones that rotate apart never open tears at joints and a
        foot never floats free of its shin"""
        ty, tx = np.mgrid[0:128, 0:128]; T = np.stack([tx + 0.5, ty + 0.5], -1)
        sc = R.SCALE_EFF
        for k, a1 in enumerate(A1):
            if k not in self.patch_col or a1[0] != 'cap': continue
            if self.arm_paint and self.tags[k] in ('arm', 'sleeve', 'hand'): continue
            ks = self.copy_of.get(k, k)
            col = self.patch_col.get(ks, self.patch_col[k])
            if ks != k: col = int(self.dark[col])
            P, Q = a1[1], a1[2]; v = Q - P; L2 = max(v @ v, 1e-6)
            tt = np.clip(((T - P) @ v) / L2, 0, 1); dist = np.linalg.norm(T - (P + tt[..., None] * v), axis=-1)
            ra, rb = _radii(self.P0[k])
            yc = int(np.clip((P[1] + Q[1]) / 2, 0, 127))
            r = (ra + (rb - ra) * tt) * sc * float(self.wsc[yc]) * 0.6
            m = (dist <= np.maximum(r, 1.0)) & (out < 0)
            if not m.any(): continue
            out[m] = col; og[m] = self.grp[k]; dep[m] = 1e8

def coherent_labels(lab, op, min_keep=0.0):
    """every bone owns ONE connected patch of master pixels: stray fragments of a label (nearest-rig binding noise)
    are handed to the label they touch most, so no pixel crumbs fly off with a far-away bone"""
    lab = lab.copy()
    for _ in range(3):
        changed = False
        for k in np.unique(lab[lab >= 0]):
            cl, n = ndi.label(lab == k, structure=np.ones((3, 3)))
            if n <= 1: continue
            sz = np.bincount(cl.ravel()); sz[0] = 0; big = sz.argmax()
            for i in range(1, n + 1):
                if i == big or sz[i] >= 0.35 * sz[big]: continue
                frag = cl == i; ring = ndi.binary_dilation(frag, structure=np.ones((3, 3))) & ~frag & op
                v = lab[ring]; v = v[(v >= 0) & (v != k)]
                if len(v) == 0: continue
                u, c = np.unique(v, return_counts=True); lab[frag] = u[c.argmax()]; changed = True
        if not changed: break
    return lab

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

def finish(out, og, dep, pal, prot=None):
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
    import pixfix as PF
    return PF.restroke(out, pal, _shades(pal), contour=mark, protect=prot)

_SH = {}
def _shades(pal):
    import pixfix as PF
    k = (len(pal), int(pal.sum()))
    if k not in _SH: _SH[k] = PF.Shades(pal)
    return _SH[k]
