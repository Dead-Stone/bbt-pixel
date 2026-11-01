"""CROSS / TRANSITION / STRAIGHT walk: re-sequence each character's walk into a smooth 8-pose cycle per direction
   X (stride) -> T -> | (legs straight under the body) -> T -> X (other leg forward) -> T -> | -> T

Mohan: "It should be cross leg, straight and cross leg." then "8 frames smoothness is missing." The drawn 8-frame walks
(walk8.py) draw their in-between frames almost as wide as the contact frames (they read as crossed), so this tool keeps the
drawn art and re-times it:

  CROSS    the widest drawn frame of each half cycle (side / 3-4 views: foot-band spread, full._spread; front / back S, N:
           walk_cycle.lift = 3 x foot height difference + foot width), the two picked half a cycle apart (other leg)
  STRAIGHT the narrowest drawn frame between the two crosses if it is clearly straight (spread <= 0.55 x the cross spread
           and <= 1.25 x the idle stance spread); otherwise COMPOSITE: that frame's head / torso / arms on the
           character's standing legs (stand_<d>; walk_cycle.stand_legs). S / N always composite.
  TRANS    a leg spread between the two (target 45-65 % of the cross spread): the drawn frame in between if its spread is
           in that window, else SYNTH = the drawn upper body (with_arms: its hanging hands kept whole) on the straight
           frame's (or the idle's) standing leg plus ONE leg of the cross (one_leg: the leading leg before / the trailing
           leg after the cross; close_legs may bring it in by a whole-pixel row shear), or a frame half (Lhalf / Rhalf).
           Candidates are scored (no seams / threads / lost hands / 3 feet) and the closest to the target spread wins.
           Palette only (no new colours, no blending).
  bob      CROSS -1 px (dip), STRAIGHT +1 px (rise), TRANS 0

Input : characters/<cid>/ai/chr_<cid>_walk8.png/.json (the drawn 8-frame walk; copied from chr_<cid>_walk.* the first time,
        i.e. right after walk8.py) + the standing pose (chr_<cid>.json stand_<d>)
Output: characters/<cid>/ai/chr_<cid>_walk.png/.json, 8 dirs x 8 poses (X, T, |, T, X, T, |, T), NE/E/SE mirror NW/W/SW;
        meta.pass_poses = [2, 6], walk_m_per_pose_dir = step / 4 (four poses per step), so with personas.speed = 2 x step
        the cadence is 2 steps/s at 8 poses/s, feet planted
Debug : XS_DEBUG=<dir> prints the top candidates per transition, XS_DUMP=<prefix> also saves them as <prefix><k>.png

python3 tools/ai_import/walk_xs.py [cid ...]       (default: all 7; re-run walk8.py first to refresh chr_<cid>_walk8.*)
"""
import os, sys, json, shutil, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from build import DIRS, MIRROR, mirror
from full import _spread
import walk_cycle as WC
from walk_cycle import stand_legs, rise, lift, big_run
from convert import audit_fix
from sheets import load_stills

CH = ['sheldon', 'leonard', 'penny', 'howard', 'raj', 'bernadette', 'amy']
SRC = ['S', 'SW', 'W', 'NW', 'N']
STRAIGHT_MAX = 0.55; IDLE_MAX = 1.25
# leg join height (fraction of the body height above the soles; walk_cycle.HIP = 0.42): Amy's skirt is stiff and boxy, so her
# standing legs are joined at the skirt hem instead of mid-skirt (no notch where the walk skirt meets the standing skirt)
JOIN = {'amy': 0.30}


def cells(j, im, tag):
    a, b = tag
    return [im[j['frames'][k]['frame']['y']:j['frames'][k]['frame']['y'] + 128,
               j['frames'][k]['frame']['x']:j['frames'][k]['frame']['x'] + 128].copy() for k in range(a, b + 1)]


def tags(j):
    return {t['name']: (t['from'], t['to']) for t in j['meta']['frameTags']}


def dip(f, px=1):
    """contact pose: everything above the hip line moves down px rows (the legs, apart, get px shorter)"""
    A = f[..., 3] > 0; ys = np.nonzero(A.any(1))[0]; y = int(round(ys[-1] - WC.HIP * (ys[-1] - ys[0])))
    out = f.copy(); out[px:y + 1] = f[:y + 1 - px]; out[:px] = 0; return out


def foot_side(f):
    """front / back views: +1 if the left foot is lower (nearer) than the right, -1 if higher, 0 level"""
    A = f[..., 3] > 0; ys = np.nonzero(A.any(1))[0]; yb, yt = ys[-1], ys[0]
    leg = A[int(yb - 0.3 * (yb - yt)):yb + 1]; xs = np.nonzero(leg.any(0))[0]; cx = int((xs[0] + xs[-1]) / 2)
    L = np.nonzero(A[:, :cx].any(1))[0][-1]; R = np.nonzero(A[:, cx:].any(1))[0][-1]
    return int(np.sign(int(L) - int(R)))


def runs(row):
    """(start, end) column runs of a boolean row"""
    x = np.nonzero(np.diff(np.concatenate([[0], row.astype(np.int8), [0]])))[0]
    return list(zip(x[0::2], x[1::2] - 1))


def leg_mask(f):
    """the legs: opaque pieces below the hip line that reach the soles (a hand hanging below the hip does not)"""
    import scipy.ndimage as nd
    A = f[..., 3] > 0; ys = np.nonzero(A.any(1))[0]; yb, yt = ys[-1], ys[0]; y = int(round(yb - WC.HIP * (yb - yt)))
    lab, n = nd.label(A[y + 1:]); M = np.zeros_like(A)
    for k in range(1, n + 1):
        m = lab == k
        if np.nonzero(m)[0].max() + y + 1 >= yb - 4: M[y + 1:] |= m
    return M, y, yb


def close_legs(f, k):
    """TRANSITION legs: both feet slide toward the hip centre by fraction k of their offset; each leg is sheared row by
    row (whole-pixel row shifts, linear from where the legs part to the foot, the foot moved rigidly), so the art keeps
    its pixels and palette (no resampling, no blending); the bigger leg (the near one) is painted last"""
    M, y, yb = leg_mask(f); H = f.shape[0]
    lab = np.zeros(M.shape, np.int8); split = None                       # 1 = left leg, 2 = right leg, 3 = shared
    for r in range(y + 1, H):
        rr = runs(M[r])
        if not rr: continue
        if len(rr) == 1: lab[r, rr[0][0]:rr[0][1] + 1] = 3; continue
        if split is None: split = r
        cL, cR = (rr[0][0] + rr[0][1]) / 2, (rr[-1][0] + rr[-1][1]) / 2
        for a, b in rr: lab[r, a:b + 1] = 1 if (a + b) / 2 - cL <= cR - (a + b) / 2 else 2
    if split is None: return f.copy()
    hip = runs(M[split - 1]) if split - 1 > y else runs(M[split])
    cx = (hip[0][0] + hip[-1][1]) / 2
    foot = {}
    for L in (1, 2):
        rows = np.nonzero((lab == L).any(1))[0]
        if not len(rows): return f.copy()
        lo = rows.max(); band = lab[lo - 5:lo + 1] == L; xs = np.nonzero(band)[1]
        foot[L] = (xs.mean(), lo - 5)
    sh = {L: k * (cx - foot[L][0]) for L in (1, 2)}
    def t(r, L): return float(np.clip((r - split) / max(1, foot[L][1] - split), 0, 1))
    out = f.copy(); out[M] = 0
    area = {L: int((lab == L).sum()) for L in (1, 2)}
    for L in [3] + sorted((1, 2), key=lambda q: area[q]):
        for r in range(y + 1, H):
            xs = np.nonzero(lab[r] == L)[0]
            if not len(xs): continue
            d = int(round((sh[1] * t(r, 1) + sh[2] * t(r, 2)) / 2)) if L == 3 else int(round(sh[L] * t(r, L)))
            nx = xs + d; ok = (nx >= 0) & (nx < f.shape[1]); out[r, nx[ok]] = f[r, xs[ok]]
    return out


def tween(f, target):
    """close_legs with the k that lands the foot spread nearest the target"""
    best = min(((abs(_spread(g) - target), kk, g) for kk in np.linspace(0, 1, 21) for g in [close_legs(f, kk)]), key=lambda q: q[0])
    return best[2], round(float(best[1]), 2)


def half_legs(base, other, side, cx, y):
    """front / back TRANSITION: below the hip line, one side (0 = left, 1 = right of the leg centre cx) from other"""
    out = base.copy(); sl = slice(0, cx) if side == 0 else slice(cx, base.shape[1])
    out[y + 1:, sl] = other[y + 1:, sl]; return out


def leg_labels(f):
    """per pixel: 1 = left leg, 2 = right leg (from the feet up: where the legs overlap, split at the last gap seen
    below); split = the topmost row where the legs are apart"""
    M, y, yb = leg_mask(f); lab = np.zeros(M.shape, np.int8); split = None; gap = None
    for r in range(yb, y, -1):
        rr = runs(M[r])
        if not rr: continue
        if len(rr) >= 2:
            # the widest gap between runs separates the legs
            g = max(range(len(rr) - 1), key=lambda i: rr[i + 1][0] - rr[i][1]); gap = (rr[g][1] + rr[g + 1][0]) / 2; split = r
        if gap is None: continue
        xs = np.nonzero(M[r])[0]; lab[r, xs[xs <= gap]] = 1; lab[r, xs[xs > gap]] = 2
    if split is not None: lab[:split] = 0
    lb = np.nonzero((lab > 0).any(1))[0]                    # one foot below the other's lifted one: it belongs to the leg above it
    if len(lb):
        for r in range(lb[-1] + 1, yb + 1):
            for a, b in runs(M[r]):
                above = lab[r - 1, max(a - 1, 0):b + 2]; v = np.bincount(above[above > 0], minlength=3)
                if v[1:].any(): lab[r, a:b + 1] = 1 + int(np.argmax(v[1:]))
    return lab, split, y


THIGH = True


def one_leg(idle, cross, L, under):
    """side-view TRANSITION legs: the standing legs plus one leg of the cross (L: 1 = the leading leg, 2 = the
    trailing leg of a left-facing walker), its sole on the ground, hip over the hip; drawn pixels only"""
    lab, split, y = leg_labels(cross)
    if split is None: return None
    Ai = idle[..., 3] > 0; Ac = cross[..., 3] > 0
    if np.nonzero((lab > 0).any(1))[0][-1] < np.nonzero(Ac.any(1))[0][-1] - 4: return None   # legs overlap at the sole: no clean split
    dy = int(np.nonzero(Ai.any(1))[0][-1] - np.nonzero(Ac.any(1))[0][-1])
    hc = runs(Ac[split - 1]) or runs(Ac[split]); ri = big_run(Ai, y + dy)
    dx = int(round((ri[0] + ri[1]) / 2 - (hc[0][0] + hc[-1][1]) / 2)) if ri else 0
    import scipy.ndimage as nd
    m = lab == L
    if THIGH:                                               # legs merged above the split (thighs touching): cut on the split's gap up to the hip
        c1 = np.nonzero(lab[split] == 1)[0]; c2 = np.nonzero(lab[split] == 2)[0]
        if len(c1) and len(c2):
            gx = (c1.max() + c2.min()) / 2; cols = np.arange(m.shape[1]); side = cols <= gx if L == 1 else cols > gx
            top = y + max(2, (split - y) // 3)
            m[top:split] |= Ac[top:split] & side[None, :]
    cl, n = nd.label(m)                       # the leg itself: no stray hand / hem pieces caught by the split
    if n > 1:
        sz = nd.sum(m, cl, range(1, n + 1)); m = np.isin(cl, 1 + np.nonzero(sz >= 0.25 * sz.max())[0])
    up = np.zeros_like(Ac); up[:max(split - 1, 0)] = Ac[:max(split - 1, 0)]; lo = np.zeros_like(Ai); lo[y + dy + 1:] = Ai[y + dy + 1:]
    yb = np.nonzero(Ai.any(1))[0][-1]; low = np.zeros_like(Ai); low[(yb + y + dy) // 2:] = Ai[(yb + y + dy) // 2:]   # the idle's shins + feet
    K = np.array(sorted(colours(cross, up) - colours(idle, low)), np.int64)   # no hand / sleeve of the cross comes with its leg
    if len(K):
        c = cross[..., :3].astype(np.int64); m &= ~np.isin(c[..., 0] << 16 | c[..., 1] << 8 | c[..., 2], K)
        m &= nd.binary_opening(m, np.ones((2, 2), bool)) | nd.binary_erosion(nd.binary_dilation(m, iterations=1), iterations=1) & m
    keep = np.zeros_like(m); prev = None; wd = []                    # trace the leg up from its sole: per row the one run over the run below
    for r in range(m.shape[0] - 1, -1, -1):
        rr = runs(m[r])
        if not rr: continue
        if prev is None: pick = [q for q in rr if q[1] - q[0] >= 1] or rr
        else:
            pick = [q for q in rr if q[0] <= prev[1] + 1 and q[1] >= prev[0] - 1]
            if not pick: continue
        lo_, hi_ = min(q[0] for q in pick), max(q[1] for q in pick)
        if prev is not None and (hi_ - lo_) > 3 * (prev[1] - prev[0] + 1) + 4: pick = [max(pick, key=lambda q: q[1] - q[0])]; lo_, hi_ = pick[0]
        if len(wd) >= 6 and hi_ - lo_ + 1 > 1.5 * max(wd[-8:]) + 2: break   # widening into the hem / a hand: the leg ends here
        wd.append(hi_ - lo_ + 1)
        for q in pick: keep[r, q[0]:q[1] + 1] = m[r, q[0]:q[1] + 1]
        prev = (lo_, hi_)
    m = keep
    out = idle.copy()
    yy, xx = np.nonzero(m); ny, nx = yy + dy, xx + dx
    ok = (ny >= 0) & (ny < out.shape[0]) & (nx >= 0) & (nx < out.shape[1]); yy, xx, ny, nx = yy[ok], xx[ok], ny[ok], nx[ok]
    t = ny.min(); top = nx[ny == t]; ir = runs(out[t, :, 3] > 0)   # a knee-high split: slide the lower leg in to meet its thigh
    if len(top) and ir:
        a, b = int(top.min()), int(top.max())
        g = min((q for q in ir), key=lambda q: max(q[0] - b, a - q[1]))
        if g[0] - b > -2: nx = nx + (g[0] - b + 2)
        elif a - g[1] > -2: nx = nx - (a - g[1] + 2)
        ok = (nx >= 0) & (nx < out.shape[1]); yy, xx, ny, nx = yy[ok], xx[ok], ny[ok], nx[ok]
    if under: free = out[ny, nx, 3] == 0; yy, xx, ny, nx = yy[free], xx[free], ny[free], nx[free]
    out[ny, nx] = cross[yy, xx]; return out


# drawn walk frames whose upper body must not carry a transition: the back hand sits on the waist as a dark band that
# reads as a belt / strap once the legs under it change (looked at frame by frame)
NO_UPPER = {('leonard', 'W'): (2, 4, 6)}
CID = None


def with_arms(walk, legs):
    """stand_legs, then the walk frame's hanging arms / hands below the join put back whole (pieces clear of the hip
    run's columns, into empty pixels only), so a hand is never cut and no walk-frame thigh comes back"""
    import scipy.ndimage as nd
    out = stand_legs(walk, legs)
    A = walk[..., 3] > 0; ys = np.nonzero(A.any(1))[0]; y = int(round(ys[-1] - WC.HIP * (ys[-1] - ys[0])))
    rw = big_run(A, y)
    if not rw: return out
    lab, n = nd.label(A[y + 1:])
    for k in range(1, n + 1):
        m = lab == k; yy, xx = np.nonzero(m)
        if yy.min() > 0 or ((xx >= rw[0] + 1) & (xx <= rw[1] - 1)).any() or yy.max() + y + 1 >= ys[-1] - 6: continue   # arms hang from above the join
        sub = out[y + 1:]; put = m & (sub[..., 3] == 0); sub[put] = walk[y + 1:][put]
    arm = arm_px(walk, legs, y)                             # sleeve / skin colours that the legs never use: the arm in front, whole
    if arm.any():
        yy, xx = np.nonzero(arm); out[yy, xx] = walk[yy, xx]
        ring = np.zeros_like(arm)                           # its outline, into empty pixels
        for dy_, dx_ in ((0, 1), (0, -1), (1, 0), (-1, 0)): ring |= np.roll(np.roll(arm, dy_, 0), dx_, 1)
        ring &= (walk[..., 3] > 0) & (out[..., 3] == 0); out[ring] = walk[ring]
    return out


def colours(f, m):
    c = f[m][:, :3].astype(np.int32); return set((c[:, 0] << 16 | c[:, 1] << 8 | c[:, 2]).tolist())


def arm_px(walk, legs, y):
    """walk-frame pixels below the hip line y in a colour of the upper body (above y) that the leg frame's legs never
    use (sleeve, skin): arms / hands"""
    A = walk[..., 3] > 0; L = legs[..., 3] > 0
    up = np.zeros_like(A); up[:y] = A[:y]; lo = np.zeros_like(L); lo[y + 1:] = L[y + 1:]
    K = np.array(sorted(colours(walk, up) - colours(legs, lo)), np.int64)
    if not len(K): return np.zeros_like(A)
    c = walk[..., :3].astype(np.int64); key = c[..., 0] << 16 | c[..., 1] << 8 | c[..., 2]
    m = np.isin(key, K) & A; m[:y + 1] = False
    import scipy.ndimage as nd                              # pieces joined to the arm above the line, not lone specks
    cl, n = nd.label(m | up)
    keep = np.isin(cl, np.unique(cl[up & (cl > 0)])); return m & keep


def arm_cut(g, src):
    """pixels of the drawn frame's arms / hands just below the hip line (clear of the hip run) that the composite lost"""
    A = src[..., 3] > 0; ys = np.nonzero(A.any(1))[0]; y = int(round(ys[-1] - WC.HIP * (ys[-1] - ys[0])))
    rw = big_run(A, y)
    if not rw: return 0
    z = slice(y + 1, y + 1 + int(0.35 * (ys[-1] - y))); lost = A[z] & (g[z][..., 3] == 0)
    lost[:, max(rw[0] - 1, 0):rw[1] + 2] = False; return int(lost.sum())


def threads(g):
    """1-px-wide stray columns / pixels in the legs (seams of a composite)"""
    A = g[..., 3] > 0; ys = np.nonzero(A.any(1))[0]; y = int(round(ys[-1] - WC.HIP * (ys[-1] - ys[0])))
    B = A[y:]; l = np.zeros_like(B); r = np.zeros_like(B); l[:, 1:] = B[:, :-1]; r[:, :-1] = B[:, 1:]
    return int((B & ~l & ~r).sum())


def pieces(g):
    """extra bits in the legs: pieces of the lower body beyond two legs, and feet beyond two (a third foot, a torn shin)"""
    import scipy.ndimage as nd
    A = g[..., 3] > 0; ys = np.nonzero(A.any(1))[0]; y = int(round(ys[-1] - WC.HIP * (ys[-1] - ys[0])))
    big = lambda m: int(sum(1 for v in nd.sum(m, nd.label(m)[0], range(1, nd.label(m)[1] + 1)) if v >= 3))
    feet = A[ys[-1] - 5:ys[-1] + 1]
    return max(big(A[y:]) - 2, 0) + max(big(feet) - 2, 0) + max(len(runs(A[ys[-1] - 2])) - 2, 0)


def legdist(c, s):
    """front / back: pixels of the lower 40% (legs) that differ from pose s, aligned on the soles and at the best
    horizontal offset (+-4 px); 0 = the same legs"""
    a, b = c[..., 3] > 0, s[..., 3] > 0
    ya, yb = np.nonzero(a.any(1))[0], np.nonzero(b.any(1))[0]; b = np.roll(b, ya[-1] - yb[-1], axis=0)
    y = int(ya[-1] - 0.4 * (ya[-1] - ya[0])); return min(int((a[y:] ^ np.roll(b, dx, axis=1)[y:]).sum()) for dx in range(-4, 5))


def cycle(d, W, idle, pal):
    """8 poses: X1, T, |1, T, X2, T, |2, T (X = cross, | = straight, T = transition between them)"""
    side = d not in ('S', 'N'); n = len(W)
    sc = [int(_spread(f)) if side else int(lift(f)) for f in W]
    A = int(np.argmax(sc)); opp = [(A + k) % n for k in (n // 2, n // 2 - 1, n // 2 + 1)]
    if not side:                                       # the other cross: the other foot forward if any frame shows it
        s0 = foot_side(W[A]); o2 = [j for j in opp if foot_side(W[j]) == -s0 and s0]
        opp = o2 or opp
    B = max(opp, key=lambda j: sc[j])
    h1 = [(A + i) % n for i in range(1, (B - A) % n)]; h2 = [(B + i) % n for i in range(1, (A - B) % n)]
    P1 = min(h1, key=lambda j: sc[j]); P2 = min(h2, key=lambda j: sc[j])
    cross = (sc[A] + sc[B]) / 2.0; sp_idle = int(_spread(idle)) if side else int(lift(idle))
    def straight(j):
        if side: ok = sc[j] <= STRAIGHT_MAX * cross and sc[j] <= IDLE_MAX * sp_idle
        else: ok = False                    # S / N: always the standing legs (drawn walks barely change)
        f = W[j] if ok else stand_legs(W[j], idle)
        return f, ('drawn' if ok else 'composite')
    (S1r, m1), (S2r, m2) = straight(P1), straight(P2)
    def mid(a, b):                          # the drawn frame half way between pose a and pose b (else a itself)
        bw = [(a + i) % n for i in range(1, (b - a) % n)]
        return bw[(len(bw) - 1) // 2] if bw else a
    X1, X2 = audit_fix(dip(W[A]), pal), audit_fix(dip(W[B]), pal)
    S1, S2 = audit_fix(rise(S1r), pal), audit_fix(rise(S2r), pal)
    tw, tinfo = [], []
    for (xa, Xn, Sn, pa, pb) in [(A, X1, S1, A, P1), (B, X2, S1, P1, B), (B, X2, S2, B, P2), (A, X1, S2, P2, A)]:
        after = pa == xa; j = mid(pa, pb); cf = W[xa]; cands = []
        if side:                            # foot spread (or the lift, when the spread does not tell them apart, e.g. Raj NW)
            mets = [q for q in (_spread, lift) if q(Xn) - q(Sn) >= 5] or [_spread]
            q0 = mets[0]; xs_, ss_ = q0(Xn), q0(Sn); tgt = min(max((xs_ + ss_) / 2.0, 0.45 * xs_), 0.65 * xs_)
            if not ss_ + 2 < tgt < xs_ - 2: tgt = (xs_ + ss_) / 2.0
            cands.append((W[j], f'drawn {j}', 0, W[j]))
            for jj in [q for q in dict.fromkeys([j, pa, pb, (j - 1) % n, (j + 1) % n] if (CID, d) in NO_UPPER else [j, pa, pb]) if q not in NO_UPPER.get((CID, d), ())]:   # upper body: the middle drawn frame, else a neighbour whose arms clear the hip
                for L in ((2, 1) if after else (1, 2)):   # standing legs + one leg of the cross: after X its trailing leg, before X its leading leg
                    for kk in (0, 0.1):                     # a far-out leg may be brought in a little (row shear, whole pixels); more tears it
                      for bn, bs in (('/S', Sn), ('', idle)):    # the standing leg from the idle or from the drawn straight frame
                        lg = one_leg(bs, close_legs(cf, kk) if kk else cf, L, under=(L == 2))
                        if lg is None: continue
                        cands.append((with_arms(W[jj], lg), f'synth {jj}+X{xa}{"_lead" if L == 1 else "_trail"}{bn}' + (f' k={kk}' if kk else ''), 1 + (L != (2 if after else 1)), W[jj]))
                base = with_arms(W[jj], idle); xl = with_arms(W[jj], cf)     # and the front/back recipe: one side of the legs the cross's
                Aj = W[jj][..., 3] > 0; ys = np.nonzero(Aj.any(1))[0]; y = int(round(ys[-1] - WC.HIP * (ys[-1] - ys[0])))
                r = big_run(base[..., 3] > 0, y + 1) or big_run(Aj, y)
                if r:
                    cx = int(round((r[0] + r[1]) / 2)) + 1; lo = int(ys[-1] - 0.75 * (ys[-1] - y))
                    cost = lambda c: int((base[lo:, c - 1:c + 1, 3] > 0).sum() + (xl[lo:, c - 1:c + 1, 3] > 0).sum())
                    cx = min(range(cx - 4, cx + 5), key=lambda c: (cost(c), abs(c - cx)))
                    for k_ in (0, 1): cands.append((half_legs(base, xl, k_, cx, y), f'synth {jj}+X{xa}_{"LR"[k_]}half', 2, W[jj]))
            def score(c):
                g, how, pen, src = c; ok = any(q(Sn) + 2 < q(g) < q(Xn) - 2 for q in mets) or (q0 is lift and not how.startswith('drawn') and 0.2 * legdist(Xn, Sn) < legdist(g, Sn) < 0.85 * legdist(Xn, Sn))
                bad = 0 if how.startswith('drawn') else arm_cut(g, src) / 2.0 + threads(g) + 6 * pieces(g) + 2 * ('X' not in how.split('+')[0] and not how.startswith(f'synth {j}+'))
                return (0 if ok else 1, pen if how.startswith('drawn') and abs(q0(g) - tgt) > 0.1 * xs_ else 0, abs(q0(g) - tgt) + 3 * (pen > 1) + 8 * how.endswith('half') + 6 * ('_trail' in how) + 1.5 * (('_lead' in how or '_trail' in how) and '/S' not in how) + bad)   # halves seam the legs: last resort
        else:                               # front / back: one leg (one side of the leg centre) still the cross's, the other standing
            for jj in [q for q in dict.fromkeys([j, pa, pb, (j - 1) % n, (j + 1) % n] if (CID, d) in NO_UPPER else [j, pa, pb]) if q not in NO_UPPER.get((CID, d), ())]:   # body from the middle drawn frame first, else a neighbour
                base = with_arms(W[jj], idle); xl = with_arms(W[jj], cf)
                Aj = W[jj][..., 3] > 0; ys = np.nonzero(Aj.any(1))[0]; y = int(round(ys[-1] - WC.HIP * (ys[-1] - ys[0])))
                r = big_run(base[..., 3] > 0, y + 1) or big_run(Aj, y); cx = int(round((r[0] + r[1]) / 2)) + 1
                lo = int(ys[-1] - 0.75 * (ys[-1] - y))       # cut where the fewest leg pixels are (the gap between the legs): no slivers
                cost = lambda c: int((base[lo:, c - 1:c + 1, 3] > 0).sum() + (xl[lo:, c - 1:c + 1, 3] > 0).sum())
                cx = min(range(cx - 4, cx + 5), key=lambda c: (cost(c), abs(c - cx)))
                for k_ in (0, 1): cands.append((half_legs(base, xl, k_, cx, y), f'synth {jj}+X{xa}_{"LR"[k_]}leg', 0 if jj == j else 0.5, W[jj]))
            cands.append((W[j], f'drawn {j}', 1, W[j]))
            full = legdist(Xn, Sn)
            def score(c):
                dv = legdist(c[0], Sn); return (0 if 0.2 * full < dv < 0.85 * full else 1, abs(dv - full / 2) + 5 * c[2])
        if os.environ.get('XS_DEBUG') == d: print('   ', len(tw), sorted((tuple(round(float(v), 1) for v in score(c)), c[1]) for c in cands)[:8])
        if os.environ.get('XS_DEBUG') == d and os.environ.get('XS_DUMP'):
            from PIL import Image as _I; top = sorted(cands, key=lambda c: tuple(score(c)))[:6]
            im = np.concatenate([c[0][60:124, 20:108] for c in top], 1); bg = _I.new('RGBA', (im.shape[1], im.shape[0]), (60, 60, 70, 255)); bg.alpha_composite(_I.fromarray(im))
            bg.convert('RGB').resize((bg.width * 3, bg.height * 3), _I.NEAREST).save(os.environ['XS_DUMP'] + f'{len(tw)}.png'); print('   dump', [c[1] for c in top])
        g, how = min(cands, key=score)[:2]; tw.append(audit_fix(g, pal)); tinfo.append(how)
    poses = [X1, tw[0], S1, tw[1], X2, tw[2], S2, tw[3]]
    m = lambda f: int(_spread(f)) if side else int(lift(f))
    info = dict(cross_from=[A, B], straight_from=[P1, P2], straight_mode=[m1, m2], transition=tinfo, metric='spread' if side else 'lift',
                drawn=sc, seq_spread=[int(_spread(f)) for f in poses], seq_lift=[int(lift(f)) for f in poses],
                cross_spread=[int(_spread(X1)), int(_spread(X2))], straight_spread=[int(_spread(S1)), int(_spread(S2))],
                trans_spread=[int(_spread(f)) for f in tw], idle_spread=int(_spread(idle)), idle_lift=int(lift(idle)))
    info['ratio'] = round(np.mean(info['straight_spread']) / max(1, np.mean(info['cross_spread'])), 2)
    info['trans_ratio'] = [round(int(_spread(tw[i])) / max(1, int(_spread(poses[0 if i in (0, 3) else 4]))), 2) for i in range(4)]
    return poses, info


def build(cid):
    global CID; CID = cid
    od = os.path.join(ROOT, 'characters', cid, 'ai')
    src_png, src_js = os.path.join(od, f'chr_{cid}_walk8.png'), os.path.join(od, f'chr_{cid}_walk8.json')
    cur_js = os.path.join(od, f'chr_{cid}_walk.json')
    cur = json.load(open(cur_js))
    if cur['meta'].get('app', '').endswith('walk8.py'):      # fresh walk8.py output -> keep it as the drawn source
        shutil.copy(os.path.join(od, f'chr_{cid}_walk.png'), src_png); shutil.copy(cur_js, src_js)
    wj = json.load(open(src_js)); wim = np.asarray(Image.open(src_png).convert('RGBA')); wt = tags(wj)
    aj = json.load(open(os.path.join(od, f'chr_{cid}.json'))); aim = np.asarray(Image.open(os.path.join(od, f'chr_{cid}.png')).convert('RGBA'))
    at = tags(aj); pal = load_stills(cid)[1]; WC.HIP = JOIN.get(cid, 0.42)
    per = {d: cycle(d, cells(wj, wim, wt[f'walk_{d}']), cells(aj, aim, at[f'stand_{d}'])[0], pal) for d in SRC}
    out, frames, tg = [], [], []
    for d in DIRS:
        fr, _ = per[MIRROR.get(d, d)]; a = len(out)
        for k, f in enumerate(fr):
            i = len(out); out.append(mirror(f) if d in MIRROR else f)
            frames.append(dict(filename=f'walkxs_{d}_{k}_{"XT|T"[k % 4]}', frame=dict(x=(i % 8) * 128, y=(i // 8) * 128, w=128, h=128), duration=125))
        tg.append(dict(name=f'walk_{d}', **{'from': a, 'to': len(out) - 1}, direction='forward'))
    sheet = np.zeros((((len(out) + 7) // 8) * 128, 8 * 128, 4), np.uint8)
    for i, c in enumerate(out): sheet[(i // 8) * 128:(i // 8 + 1) * 128, (i % 8) * 128:(i % 8 + 1) * 128] = c
    Image.fromarray(sheet).save(os.path.join(od, f'chr_{cid}_walk.png'), optimize=True)
    m8 = wj['meta']; mpp8 = m8.get('walk_m_per_pose_dir') or {d: m8['walk_m_per_pose'] for d in DIRS}
    step = {d: round(4 * mpp8[d], 4) for d in DIRS}
    rows = {d: per[MIRROR.get(d, d)][1] for d in DIRS}
    meta = dict(app='bbt-pixel/tools/ai_import/walk_xs.py', image=f'chr_{cid}_walk.png', size=dict(w=sheet.shape[1], h=sheet.shape[0]),
                frameTags=tg, poses=['cross', 'trans', 'straight', 'trans', 'cross', 'trans', 'straight', 'trans'], pass_poses=[2, 6], pivot=[64, 116],
                frames_per_cycle={d: 8 for d in DIRS}, steps_per_cycle=2, step_m=step,
                walk_m_per_pose=round(step['W'] / 4, 4), walk_m_per_pose_dir={d: round(step[d] / 4, 4) for d in DIRS},
                walk_stride_px=m8.get('walk_stride_px'), rows=rows, source=f'chr_{cid}_walk8.png (walk8.py: {m8.get("source")})',
                note='X T | T X T | T per direction (module doc); NE/E/SE mirror NW/W/SW; persona speed = 2 x step -> 2 steps/s')
    json.dump(dict(frames=frames, meta=meta), open(cur_js, 'w'), indent=1)
    return meta


if __name__ == '__main__':
    for cid in (sys.argv[1:] or CH):
        m = build(cid)
        print(cid, 'step', m['step_m']['W'], 'm/pose', m['walk_m_per_pose'], '-> 2 steps/s at', round(2 * m['step_m']['W'], 2), 'm/s')
        for d in SRC:
            r = m['rows'][d]
            print(f"  {d:2} X{r['cross_from']} |{r['straight_from']} {r['straight_mode']} T {r['transition']}\n      spread {r['seq_spread']}  lift {r['seq_lift']}  |/X {r['ratio']} T/X {r['trans_ratio']}")
