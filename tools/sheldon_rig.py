"""Procedural 'proxy-3D' sprite renderer for the Sheldon-inspired character (spec §2/§3.1).
Builds the body from SDF primitives, ray-marches orthographically from a 2:1-iso camera
(30deg elevation), cel-shades with a symmetric top-front light (spec §1.5), assigns ONLY
palette colours from palettes/bbt_sheldon.gpl, then applies outline / sel-out / interior lines."""
import numpy as np, math
from sprite_common import load_gpl, PIVOT
PAL = load_gpl('/workspace/bbt-pixel/palettes/bbt_sheldon.gpl')
C = {k: np.array(v, np.uint8) for k, v in PAL.items()}
# material ramps: (hi, base, sh, xsh/darkest)
RAMP = {
 'skin': ('skin_hi','skin','skin_sh','skin_sh'),
 'hair': ('hair_hi','hair','hair_sh','hair_sh'),
 'tee':  ('tee_hi','tee','tee_sh','tee_xsh'),
 'under':('undershirt','undershirt','undershirt_sh','undershirt_sh'),
 'pants':('pants','pants','pants_sh','pants_sh'),
 'shoes':('bag_strap','shoes','hair_sh','hair_sh'),
 'emb':  ('emblem','emblem','emblem_sh','emblem_sh'),
}
MATS = list(RAMP)
ELEV = math.radians(30.0)
S_CAM = np.array([1.0, 0, 0]); U_CAM = np.array([0, math.sin(ELEV), math.cos(ELEV)])
D_CAM = np.array([0, math.cos(ELEV), -math.sin(ELEV)])
LIGHT = U_CAM*0.45 - D_CAM*0.90; LIGHT /= np.linalg.norm(LIGHT)   # top-front, laterally symmetric
SCALE = 1.0   # px per unit; fitted in fit_scale()
YAW = {'S':0,'SW':45,'W':90,'NW':135,'N':180}

# ---------- SDF helpers (p: (...,3)) ----------
def sd_ell(p, c, r):
    q = (p - c) / r
    k0 = np.linalg.norm(q, axis=-1); k1 = np.linalg.norm(q / r, axis=-1)
    return k0 * (k0 - 1) / np.maximum(k1, 1e-6)
def sd_cap(p, a, b, ra, rb=None):
    rb = ra if rb is None else rb
    pa = p - a; ba = b - a
    h = np.clip((pa @ ba) / (ba @ ba), 0, 1)
    return np.linalg.norm(pa - h[..., None] * ba, axis=-1) - (ra + (rb - ra) * h)
def sd_rbox(p, c, half, r, R=None):
    q = p - c
    if R is not None: q = q @ R
    q = np.abs(q) - (np.array(half) - r)
    return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(-1), 0) - r
def rotx(a):  # rotate about local x (pitch forward: +y toward -z)
    c, s = math.cos(a), math.sin(a); return np.array([[1,0,0],[0,c,-s],[0,s,c]])
def rotz(a):
    c, s = math.cos(a), math.sin(a); return np.array([[c,-s,0],[s,c,0],[0,0,1]])

# ---------- pose -> list of primitives (character-local coords: +x = character's RIGHT, +y forward, +z up) ----------
def leg_chain(hip, thigh_a, knee_a, L1=21.0, L2=21.0):
    d1 = np.array([0, math.sin(thigh_a), -math.cos(thigh_a)])
    knee = hip + d1 * L1
    a2 = thigh_a - knee_a
    d2 = np.array([0, math.sin(a2), -math.cos(a2)])
    ankle = knee + d2 * L2
    return knee, ankle
def arm_chain(sh, flex, elbow, abduct=0.08, L1=15.0, L2=13.5):
    # flex: forward raise (rad), elbow: forearm extra flex (rad)
    side = math.copysign(1, sh[0])
    d1 = np.array([side*math.sin(abduct), math.sin(flex), -math.cos(flex)])
    el = sh + d1 / np.linalg.norm(d1) * L1
    a2 = flex + elbow
    d2 = np.array([side*math.sin(abduct)*0.5, math.sin(a2), -math.cos(a2)])
    wr = el + d2 / np.linalg.norm(d2) * L2
    return el, wr, d2 / np.linalg.norm(d2)

def build(pose):
    """pose dict: lift(z offset), breathe(z of upper body), legs:[(thigh,knee) L,R], arms:[(flex,elbow) L,R], head_yaw"""
    up = pose.get('breathe', 0.0); lift = pose.get('lift', 0.0)
    P = []  # (kind, args, material, tag)
    o = np.array([0, 0, lift])
    # legs  (index 0 = character LEFT (x<0), 1 = RIGHT)
    for i, sx in enumerate((-5.2, 5.2)):
        th, kn = pose['legs'][i]
        hip = o + np.array([sx, 0, 45.5])
        knee, ank = leg_chain(hip, th, kn)
        P.append(('cap', (hip, knee, 5.2, 4.6), 'pants', 'leg'))
        P.append(('cap', (knee, ank + np.array([0,0,1.0]), 4.6, 3.8), 'pants', 'leg'))
        fc = ank + np.array([0, 2.6, -1.2])
        P.append(('rbox', (fc, (3.5, 6.4, 2.3), 1.6), 'shoes', 'foot'))
    # pelvis
    P.append(('rbox', (o + np.array([0, 0, 46.5]), (10.8, 6.2, 4.5), 3.0), 'pants', 'pelvis'))
    ub = o + np.array([0, 0, up])
    # torso (tee)
    P.append(('rbox', (ub + np.array([0, 0, 59.5]), (12.0, 6.0, 11.8), 4.6), 'tee', 'torso'))
    # neck
    P.append(('cap', (ub + np.array([0, -0.3, 70.0]), ub + np.array([0, 0.2, 76.0]), 3.9), 'skin', 'neck'))
    # arms
    for i, sx in enumerate((-13.0, 13.0)):
        fl, eb = pose['arms'][i]
        sh = ub + np.array([sx, 0, 67.0])
        el, wr, d2 = arm_chain(sh, fl, eb, abduct=pose.get('abduct', 0.10))
        sleeve_end = sh + (el - sh) * 0.62
        P.append(('cap', (sh, sleeve_end, 4.4, 4.0), 'tee', 'sleeve'))
        P.append(('cap', (sh, el, 3.6, 3.4), 'under', 'arm'))
        P.append(('cap', (el, wr, 3.4, 3.1), 'under', 'arm'))
        P.append(('cap', (wr + d2*1.2, wr + d2*4.6, 3.0, 2.7), 'skin', 'hand'))
    # head (own frame for head yaw)
    hc = ub + np.array([0, 0.6, 87.0])
    P.append(('head', (hc, pose.get('head_yaw', 0.0)), None, 'head'))
    return P

def head_sdf(p, hc, hy):
    q = (p - hc) @ rotz(hy)  # head-local
    d_head = sd_ell(q, np.array([0, 0, 0.0]), np.array([9.9, 10.6, 13.0]))
    d_nose = sd_ell(q, np.array([0, 10.5, -1.6]), np.array([1.6, 2.0, 2.6]))
    d_ear = np.minimum(sd_ell(q, np.array([9.7, -0.5, -1.0]), np.array([1.8, 2.6, 3.6])),
                       sd_ell(q, np.array([-9.7, -0.5, -1.0]), np.array([1.8, 2.6, 3.6])))
    skin = np.minimum(np.minimum(d_head, d_nose), d_ear)
    # hair: shell over top/back, cut by a sloped plane so the face is open
    d_hair = sd_ell(q, np.array([0, -0.8, 1.6]), np.array([10.7, 11.7, 12.6]))
    hl = np.clip(-4.5 + 0.95 * (q[..., 1] + 5.0), -4.5, 5.2)   # hairline height vs forward
    cut = hl - q[..., 2]                                         # >0 below hairline
    d_hair = np.maximum(d_hair, cut)
    ear_clear = np.minimum(sd_ell(q, np.array([9.6, -0.6, -1.5]), np.array([3.6, 4.2, 4.6])),
                           sd_ell(q, np.array([-9.6, -0.6, -1.5]), np.array([3.6, 4.2, 4.6])))
    d_hair = np.maximum(d_hair, -ear_clear)
    return skin, d_hair, q

def scene(p, P):
    """returns dist, material index, aux(head-local q / torso uv)"""
    n = p.shape[0]
    dist = np.full(n, 1e9); mat = np.zeros(n, int); tag = np.zeros(n, int)
    hq = np.zeros((n, 3))
    for kind, args, m, t in P:
        if kind == 'cap': d = sd_cap(p, *args)
        elif kind == 'rbox': d = sd_rbox(p, *args)
        elif kind == 'head':
            ds, dh, q = head_sdf(p, *args)
            for d, mm in ((ds, 'skin'), (dh, 'hair')):
                w = d < dist; dist = np.where(w, d, dist); mat[w] = MATS.index(mm); tag[w] = 99
                hq[w] = q[w]
            continue
        w = d < dist; dist = np.where(w, d, dist); mat[w] = MATS.index(m)
        tag[w] = {'torso': 1, 'sleeve': 2}.get(t, 0)
    return dist, mat, tag, hq

def world_from_local(yaw_deg):
    a = math.radians(yaw_deg)
    fwd = np.array([-math.sin(a), -math.cos(a), 0]); right = np.array([fwd[1], -fwd[0], 0])
    return np.stack([right, fwd, [0, 0, 1]], 1)   # columns: local x,y,z in world

def render(pose, yaw_deg, ss=3, shadows=True):
    """returns dict of per-pixel buffers at 128x128 (majority of ss x ss subsamples)"""
    M = world_from_local(yaw_deg); P = build(pose)
    N = 128 * ss
    js, is_ = np.meshgrid(np.arange(N), np.arange(N))
    X = ((js + 0.5) / ss - PIVOT[0]) / SCALE
    Y = (PIVOT[1] - (is_ + 0.5) / ss) / SCALE
    org_w = X[..., None] * S_CAM + Y[..., None] * U_CAM - 160 * D_CAM
    org = (org_w.reshape(-1, 3)) @ M          # to character-local (M orthonormal)
    dirl = D_CAM @ M
    t = np.zeros(org.shape[0]); alive = np.ones(org.shape[0], bool); hit = np.zeros_like(alive)
    for _ in range(110):
        idx = np.where(alive)[0]
        if idx.size == 0: break
        d, _, _, _ = scene(org[idx] + t[idx, None] * dirl, P)
        t[idx] += d * 0.9
        h = d < 0.04; hit[idx[h]] = True; alive[idx[h]] = False
        alive[idx[t[idx] > 330]] = False
    pts = org + t[:, None] * dirl
    hi = np.where(hit)[0]
    mat = np.full(org.shape[0], -1); tone = np.zeros(org.shape[0], int)
    nrm_up = np.zeros(org.shape[0]); depth = np.full(org.shape[0], 1e9)
    tagb = np.zeros(org.shape[0], int); hqb = np.zeros((org.shape[0], 3)); uvb = np.zeros((org.shape[0], 2))
    if hi.size:
        ph = pts[hi]
        d0, m0, tg, hq = scene(ph, P)
        e = 0.35; g = np.zeros_like(ph)
        for k in range(3):
            dv = np.zeros(3); dv[k] = e
            g[:, k] = scene(ph + dv, P)[0] - scene(ph - dv, P)[0]
        nl = g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-6)
        L_loc = LIGHT @ M
        lam = nl @ L_loc
        tn = np.where(lam > 0.75, 0, np.where(lam > 0.30, 1, 2))
        skin_i = MATS.index('skin')
        tn = np.where((tg == 99) & (m0 == skin_i), np.where(lam > 0.75, 0, np.where(lam > 0.0, 1, 2)), tn)
        if shadows:
            so = ph + nl * 0.6; ts = np.full(hi.size, 0.8); blocked = np.zeros(hi.size, bool); al = np.ones(hi.size, bool)
            for _ in range(40):
                ii = np.where(al)[0]
                if ii.size == 0: break
                dd = scene(so[ii] + ts[ii, None] * L_loc, P)[0]
                ts[ii] += np.maximum(dd, 0.3)
                b = dd < 0.05; blocked[ii[b]] = True; al[ii[b]] = False
                al[ii[ts[ii] > 40]] = False
            selfhead = (tg == 99)   # head: no cast shadows (fringe shadow is painted in compose)
            tn = np.where(blocked & ~selfhead & (tn < 2), 2, tn)
        mat[hi] = m0; tone[hi] = tn; nrm_up[hi] = (nl @ M.T) @ U_CAM; depth[hi] = t[hi]
        tagb[hi] = tg; hqb[hi] = hq
        # torso uv: a = viewer-right coordinate when facing camera (= -local x), w = z
        uvb[hi, 0] = -ph[:, 0]; uvb[hi, 1] = ph[:, 2] - pose.get('breathe', 0) - pose.get('lift', 0)
        uvb[hi] = np.where((tg == 1)[:, None] & (nl[:, 1:2] > 0.35), uvb[hi], np.nan)
    def grid(a): return a.reshape(N, N, *a.shape[1:])
    B = dict(mat=grid(mat), tone=grid(tone), up=grid(nrm_up), depth=grid(depth), tag=grid(tagb), hq=grid(hqb), uv=grid(uvb))
    return downsample(B, ss)

def downsample(B, ss):
    mat = B['mat']; N = mat.shape[0]; n = N // ss
    def blocks(a): return a.reshape(n, ss, n, ss, *a.shape[2:]).swapaxes(1, 2).reshape(n, n, ss*ss, *a.shape[2:])
    mb = blocks(mat); tb = blocks(B['tone'])
    key = np.where(mb >= 0, mb * 4 + tb, -1)
    cover = (mb >= 0).sum(-1)
    out = {}
    # mode of (material,tone) among covered subsamples
    best = np.full((n, n), -1); bestc = np.zeros((n, n), int)
    for k in np.unique(key[key >= 0]):
        c = (key == k).sum(-1); w = c > bestc; best[w] = k; bestc[w] = c[w]
    opaque = cover * 2 > ss * ss
    out['mat'] = np.where(opaque, best // 4, -1); out['tone'] = np.where(opaque, best % 4, 0)
    ctr = (ss * ss) // 2
    for k in ('up', 'depth', 'tag'):
        out[k] = blocks(B[k])[:, :, ctr]
    out['depth'] = np.where(opaque, np.nanmin(np.where(mb >= 0, blocks(B['depth']), np.inf), -1), 1e9)
    out['hq'] = blocks(B['hq'])[:, :, ctr]; out['uv'] = blocks(B['uv'])[:, :, ctr]
    return out
