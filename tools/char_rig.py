import os
"""Generic procedural 'proxy-3D' sprite renderer (spec §1.5/§2): SDF body rig -> orthographic
2:1-iso raymarch (30deg elevation) -> cel tones from a laterally symmetric top-front light.
Characters: sheldon (v1), leonard (v1).  Call set_character(cid) before anything else.
All colours come from palettes/bbt_<cid>.gpl."""
import numpy as np, math
from sprite_common import load_gpl, PIVOT

ELEV = math.radians(30.0)
S_CAM = np.array([1.0, 0, 0]); U_CAM = np.array([0, math.sin(ELEV), math.cos(ELEV)])
D_CAM = np.array([0, math.cos(ELEV), -math.sin(ELEV)])
LIGHT = U_CAM*0.45 - D_CAM*0.90; LIGHT /= np.linalg.norm(LIGHT)
SCALE = 1.122            # px per world unit -- SHARED by all characters so relative heights are true
YAW = {'S': 0, 'SW': 45, 'W': 90, 'NW': 135, 'N': 180}

RAMPS = {
 'sheldon': {
  'skin': ('skin_hi','skin','skin_sh','skin_sh'), 'hair': ('hair_hi','hair','hair_sh','hair_sh'),
  'tee': ('tee_hi','tee','tee_sh','tee_xsh'), 'under': ('undershirt','undershirt','undershirt_sh','undershirt_sh'),
  'pants': ('pants','pants','pants_sh','pants_sh'), 'shoes': ('bag_strap','shoes','hair_sh','hair_sh')},
 'leonard': {
  'skin': ('skin_hi','skin','skin_sh','skin_sh'), 'hair': ('hair_hi','hair','hair_sh','hair_sh'),
  'hoodie': ('hoodie_hi','hoodie','hoodie_sh','hoodie_xsh'), 'tee': ('tee','tee','tee_sh','tee_sh'),
  'pants': ('pants','pants','pants_sh','pants_sh'), 'shoes': ('grey_lt','grey','grey_dk','grey_dk')},
 'penny': {
  'skin': ('skin_hi','skin','skin_sh','skin_sh'), 'hair': ('hair_hi','hair','hair_sh','hair_sh'),
  'top': ('top_hi','top','top_sh','top_sh'), 'pants': ('denim_hi','denim','denim_sh','denim_sh'),
  'shoes': ('boots','boots','boots_sh','boots_sh')},
 # ---- cast v1 ----
 'howard': {
  'skin': ('skin_hi','skin','skin_sh','skin_sh'), 'hair': ('hair_hi','hair','hair_sh','hair_sh'),
  'shirt': ('shirt_hi','shirt','shirt_sh','shirt_sh'), 'dickey': ('dickey','dickey','dickey_sh','dickey_sh'),
  'pants': ('pants_hi','pants','pants_sh','pants_sh'), 'belt': ('belt','belt','belt_sh','belt_sh'),
  'shoes': ('boots','boots','boots_sh','boots_sh')},
 'raj': {
  'skin': ('skin_hi','skin','skin_sh','skin_sh'), 'hair': ('hair_hi','hair','hair_sh','hair_sh'),
  'jacket': ('jacket','jacket','jacket_sh','jacket_sh'), 'shirt': ('shirt_hi','shirt','shirt_sh','shirt_sh'),
  'vest': ('vest_hi','vest','vest_sh','vest_sh'),
  'pants': ('pants_hi','pants','pants_sh','pants_sh'), 'shoes': ('shoes','shoes','ink_2','ink_2')},
 'bernadette': {
  'skin': ('skin_hi','skin','skin_sh','skin_sh'), 'hair': ('hair_hi','hair','hair_sh','hair_sh'),
  'cardigan': ('cardigan_hi','cardigan','cardigan_sh','cardigan_sh'), 'blouse': ('white_hi','floral_a','grey_lt','grey_lt'),
  'skirt': ('dress_hi','dress','dress_sh','dress_sh'), 'shoes': ('shoes','shoes','ink','ink')},
 'amy': {
  'skin': ('skin_hi','skin','skin_sh','skin_sh'), 'hair': ('hair_hi','hair','hair_sh','hair_sh'),
  'cardigan': ('cardigan_hi','cardigan','cardigan_sh','cardigan_sh'), 'blouse': ('blouse','blouse','blouse_sh','blouse_sh'),
  'skirt': ('skirt_hi','skirt','skirt_sh','skirt_sh'), 'tights': ('tights','tights','hair_sh','hair_sh'),
  'shoes': ('shoes','shoes','ink_2','ink_2')},
}
# body dimensions (world units). Sheldon v0 values preserved; Leonard is ~0.86 tall, stockier, slouched.
DIMS = {
 'sheldon': dict(hip_x=5.2, hip_z=45.5, L1=21.0, L2=21.0, thigh_r=(5.2, 4.6), shin_r=(4.6, 3.8),
                 foot=(3.5, 6.4, 2.3), pelvis=(46.5, (10.8, 6.2, 4.5)), torso_z=59.5, torso=(12.0, 6.0, 11.8), torso_r=4.6,
                 neck=(70.0, 76.0, 3.9), sh_x=13.0, sh_z=66.5, aL1=15.0, aL2=13.5, head_c=(0, 0.6, 87.0),
                 head=(9.9, 10.6, 13.0), sleeve_frac=0.62, slouch=0.0),
 'leonard': dict(hip_x=5.6, hip_z=35.2, L1=16.0, L2=15.8, thigh_r=(5.8, 5.0), shin_r=(5.0, 4.1),
                 foot=(3.7, 6.2, 2.3), pelvis=(36.2, (11.6, 6.6, 4.6)), torso_z=46.5, torso=(12.8, 6.9, 10.0), torso_r=4.8,
                 neck=(55.0, 63.0, 3.9), sh_x=13.6, sh_z=52.8, aL1=12.6, aL2=11.6, head_c=(0, 2.6, 73.0),
                 head=(9.4, 9.9, 11.4), sleeve_frac=1.0, slouch=1.4),
 # Penny: 88 px, athletic, longer legs, narrower waist, short-sleeve fitted top
 'penny': dict(hip_x=4.9, hip_z=40.2, L1=18.6, L2=18.4, thigh_r=(5.0, 4.1), shin_r=(4.0, 3.2),
                 foot=(3.1, 5.8, 2.3), pelvis=(41.2, (10.6, 6.0, 4.4)), torso_z=52.6, torso=(10.4, 5.6, 9.8), torso_r=4.4,
                 neck=(60.5, 66.8, 3.3), sh_x=11.4, sh_z=59.6, aL1=13.6, aL2=12.4, head_c=(0, 1.0, 76.6),
                 head=(8.9, 9.6, 11.0), sleeve_frac=0.32, slouch=0.0),
 # ---- cast v1 (heights per spec 2.1: Raj 90, Howard 86, Amy 86, Bernadette 78) ----
 # Howard: 86 px, slim, skinny legs, chest a touch forward (swagger)
 'howard': dict(hip_x=5.0, hip_z=35.8, L1=16.3, L2=16.0, thigh_r=(4.4, 3.8), shin_r=(3.7, 3.1),
                 foot=(3.4, 6.4, 2.3), pelvis=(36.8, (9.8, 5.6, 4.4)), torso_z=47.2, torso=(10.2, 5.6, 9.8), torso_r=4.4,
                 neck=(55.6, 63.4, 3.4), sh_x=11.2, sh_z=53.8, aL1=12.4, aL2=11.4, head_c=(0, 1.4, 73.4),
                 head=(9.0, 9.6, 11.0), sleeve_frac=1.0, slouch=0.0, chest=0.6),
 # Raj: 90 px, medium build, upright
 'raj': dict(hip_x=5.6, hip_z=37.0, L1=16.9, L2=16.6, thigh_r=(5.4, 4.7), shin_r=(4.7, 3.9),
                 foot=(3.6, 6.4, 2.3), pelvis=(38.0, (11.4, 6.4, 4.6)), torso_z=48.8, torso=(12.6, 6.6, 10.4), torso_r=4.8,
                 neck=(57.4, 65.6, 3.8), sh_x=13.6, sh_z=55.4, aL1=13.2, aL2=12.2, head_c=(0, 1.2, 76.4),
                 head=(9.4, 10.0, 11.6), sleeve_frac=1.0, slouch=0.0),
 # Bernadette: 78 px, petite, head 26 px (relatively larger), above-knee skirt
 'bernadette': dict(hip_x=4.4, hip_z=35.4, L1=16.4, L2=16.2, thigh_r=(4.6, 3.8), shin_r=(3.5, 2.8),
                 foot=(2.9, 5.4, 2.2), pelvis=(36.4, (9.6, 5.6, 4.1)), torso_z=46.4, torso=(9.6, 5.2, 8.6), torso_r=4.0,
                 neck=(53.4, 58.8, 3.0), sh_x=10.4, sh_z=52.6, aL1=12.0, aL2=11.0, head_c=(0, 1.0, 67.4),
                 head=(8.3, 8.9, 10.2), sleeve_frac=1.0, slouch=0.0,
                 skirt=(42.0, 24.0, (9.4, 6.4), (12.4, 9.2))),
 # Amy: 86 px, upright 'prim' posture, mid-calf skirt
 'amy': dict(hip_x=4.8, hip_z=39.3, L1=18.2, L2=18.0, thigh_r=(5.0, 4.2), shin_r=(3.8, 3.1),
                 foot=(3.1, 5.8, 2.1), pelvis=(40.3, (10.4, 5.9, 4.4)), torso_z=51.4, torso=(10.6, 5.8, 9.6), torso_r=4.4,
                 neck=(59.0, 65.2, 3.3), sh_x=11.4, sh_z=58.2, aL1=13.3, aL2=12.1, head_c=(0, 1.0, 74.6),
                 head=(8.9, 9.6, 11.0), sleeve_frac=1.0, slouch=0.0,
                 skirt=(46.0, 12.0, (10.2, 6.6), (13.4, 10.0))),
}
NEW_CAST = ('howard', 'raj', 'bernadette', 'amy')
# ---- v2 body proportions, matched to the actors (heights: celebheights.com measured estimates, cross-checked IMDb/CelebScale) ----
# REAL_CM -> target sprite height (head top incl. hair, px) = 100 * cm / 185 (Sheldon fixed at 100 px).
REAL_CM = {'sheldon': 185, 'raj': 171, 'penny': 167, 'leonard': 165, 'howard': 164, 'amy': 163, 'bernadette': 149}
TARGET_H = {c: round(100 * cm / 185) for c, cm in REAL_CM.items()}
# multipliers on the v1 rig: leg = leg length, tl = torso length, sh = shoulder half-width, tw/td = torso width/depth,
# hip = pelvis/hip width (+ skirt), limb = leg thickness, arm_k = arm thickness, arm_len, head_k = head size,
# slouch = forward hunch (shoulders/neck/head forward, world units), head_fwd = extra head offset forward, bust = chest volume
BODY = {
 'sheldon':    dict(leg=1.05, tl=1.00, sh=0.95, tw=0.90, td=0.88, hip=0.92, limb=0.84, arm_k=0.86, arm_len=1.06, head_k=0.94),
 'leonard':    dict(leg=0.97, tl=1.00, sh=0.92, tw=0.90, td=0.92, hip=0.94, limb=0.88, arm_k=0.92, arm_len=1.00, head_k=1.02, slouch=1.4),
 'penny':      dict(leg=1.03, tl=0.98, sh=1.00, tw=0.93, td=1.00, hip=1.07, limb=1.02, arm_k=0.96, arm_len=1.00, head_k=1.00),
 'howard':     dict(leg=0.98, tl=1.00, sh=0.90, tw=0.92, td=0.92, hip=0.94, limb=0.84, arm_k=0.86, arm_len=1.00, head_k=1.05),
 'raj':        dict(leg=0.97, tl=1.02, sh=1.03, tw=1.07, td=1.14, hip=1.06, limb=1.10, arm_k=1.06, arm_len=1.00, head_k=1.00),
 'bernadette': dict(leg=0.93, tl=0.97, sh=0.93, tw=0.95, td=1.04, hip=1.15, limb=1.10, arm_k=1.02, arm_len=0.98, head_k=1.05, bust=1.25),
 'amy':        dict(leg=1.00, tl=1.00, sh=0.95, tw=0.98, td=1.00, hip=1.05, limb=1.00, arm_k=0.96, arm_len=1.00, head_k=1.00, slouch=1.8, head_fwd=1.2),
}
# uniform model scale per character (solved by tools/fit_heights.py so the idle-S head top lands on TARGET_H)
KSCALE = {'sheldon': 0.9901, 'leonard': 1.0349, 'penny': 1.0112, 'howard': 1.0349, 'raj': 1.0337, 'bernadette': 1.0519, 'amy': 1.0476}
SCALE_EFF = SCALE

def reproportion(d0, b):
    d = {k: (list(v) if isinstance(v, tuple) else v) for k, v in d0.items()}
    d['pelvis'] = [d0['pelvis'][0], list(d0['pelvis'][1])]; d['torso'] = list(d0['torso'])
    leg, tl = b.get('leg', 1.0), b.get('tl', 1.0)
    dz_leg = (d0['L1'] + d0['L2']) * (leg - 1.0)
    d['L1'] = d0['L1'] * leg; d['L2'] = d0['L2'] * leg; d['hip_z'] = d0['hip_z'] + dz_leg
    th = d0['torso'][2]; dz_t = 2 * th * (tl - 1.0)
    d['torso'][2] = th * tl; d['torso_z'] = d0['torso_z'] + dz_leg + th * (tl - 1.0)
    d['pelvis'][0] = d0['pelvis'][0] + dz_leg
    up = dz_leg + dz_t
    d['neck'] = [d0['neck'][0] + up, d0['neck'][1] + up, d0['neck'][2] * b.get('limb', 1.0) ** 0.3]
    d['sh_z'] = d0['sh_z'] + up
    hk = b.get('head_k', 1.0)
    hc = list(d0['head_c']); hc[2] += up + (hk - 1.0) * d0['head'][2] * 0.85
    sl = b.get('slouch', d0.get('slouch', 0.0)); hc[1] += (sl - d0.get('slouch', 0.0)) * 1.3 * (0 if CID_PENDING in ('sheldon', 'leonard', 'penny') else 1) + b.get('head_fwd', 0.0)
    d['head_c'] = hc; d['slouch'] = sl; d['head_k'] = hk
    d['ik_off'] = (0.0, hc[1] - d0['head_c'][1], hc[2] - d0['head_c'][2])   # hand-to-face IK targets follow the head
    d['sh_x'] = d0['sh_x'] * b.get('sh', 1.0)
    d['torso'][0] = d0['torso'][0] * b.get('tw', 1.0); d['torso'][1] = d0['torso'][1] * b.get('td', 1.0)
    hip = b.get('hip', 1.0)
    d['pelvis'][1][0] = d0['pelvis'][1][0] * hip; d['pelvis'][1][1] = d0['pelvis'][1][1] * (0.5 + 0.5 * b.get('td', 1.0))
    d['hip_x'] = d0['hip_x'] * (0.5 + 0.5 * hip)
    lm = b.get('limb', 1.0)
    d['thigh_r'] = [d0['thigh_r'][0] * lm, d0['thigh_r'][1] * lm]; d['shin_r'] = [d0['shin_r'][0] * (0.5 + 0.5 * lm), d0['shin_r'][1] * (0.5 + 0.5 * lm)]
    al = b.get('arm_len', 1.0); d['aL1'] = d0['aL1'] * al; d['aL2'] = d0['aL2'] * al
    d['arm_k'] = b.get('arm_k', 1.0); d['bust'] = b.get('bust', 1.0)
    if 'skirt' in d0:
        zt, zb, rt, rb = d0['skirt']
        d['skirt'] = (zt + dz_leg, zb * leg, (rt[0] * hip, rt[1] * (0.5 + 0.5 * b.get('td', 1.0))), (rb[0] * hip, rb[1]))
    for k in ('pelvis',):
        d[k] = (d[k][0], tuple(d[k][1]))
    for k in ('torso', 'neck', 'thigh_r', 'shin_r', 'head_c'):
        d[k] = tuple(d[k])
    return d
CID_PENDING = None
CID = None; PAL = C = RAMP = MATS = DIM = None
def set_character(cid):
    global CID, PAL, C, RAMP, MATS, DIM
    CID = cid; PAL = load_gpl(f'/workspace/bbt-pixel/palettes/bbt_{cid}.gpl')
    C = {k: np.array(v, np.uint8) for k, v in PAL.items()}
    global SCALE_EFF, CID_PENDING
    CID_PENDING = cid
    RAMP = RAMPS[cid]; MATS = list(RAMP)
    DIM = reproportion(DIMS[cid], BODY[cid]) if os.environ.get('BBT_BODY', 'v2') == 'v2' else DIMS[cid]
    k = float(os.environ['BBT_K']) if os.environ.get('BBT_K') else KSCALE[cid]
    SCALE_EFF = SCALE * (k if os.environ.get('BBT_BODY', 'v2') == 'v2' else 1.0)

# ---------- SDF helpers ----------
def sd_ell(p, c, r):
    q = (p - c) / r
    k0 = np.linalg.norm(q, axis=-1); k1 = np.linalg.norm(q / r, axis=-1)
    return k0 * (k0 - 1) / np.maximum(k1, 1e-6)
def sd_cap(p, a, b, ra, rb=None, zmax=None):
    rb = ra if rb is None else rb
    pa = p - a; ba = b - a
    h = np.clip((pa @ ba) / (ba @ ba), 0, 1)
    d = np.linalg.norm(pa - h[..., None] * ba, axis=-1) - (ra + (rb - ra) * h)
    if zmax is not None: d = np.maximum(d, p[..., 2] - zmax)      # clip (keeps sleeves under the shoulder line)
    return d
def sd_rbox(p, c, half, r, R=None):
    q = p - c
    if R is not None: q = q @ R
    q = np.abs(q) - (np.array(half) - r)
    return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(-1), 0) - r
def rotx(a):
    c, s = math.cos(a), math.sin(a); return np.array([[1,0,0],[0,c,-s],[0,s,c]])
def rotz(a):
    c, s = math.cos(a), math.sin(a); return np.array([[c,-s,0],[s,c,0],[0,0,1]])
def smin(a, b, k):
    h = np.clip(0.5 + 0.5*(b-a)/k, 0, 1); return b*(1-h) + a*h - k*h*(1-h)

def leg_chain(hip, thigh_a, knee_a, L1, L2):
    d1 = np.array([0, math.sin(thigh_a), -math.cos(thigh_a)]); knee = hip + d1 * L1
    a2 = thigh_a - knee_a; d2 = np.array([0, math.sin(a2), -math.cos(a2)])
    return knee, knee + d2 * L2
def arm_chain(sh, flex, elbow, abduct, L1, L2):
    side = math.copysign(1, sh[0])
    d1 = np.array([side*math.sin(abduct), math.sin(flex), -math.cos(flex)])
    el = sh + d1 / np.linalg.norm(d1) * L1
    a2 = flex + elbow
    d2 = np.array([side*math.sin(abduct)*0.5, math.sin(a2), -math.cos(a2)]); d2 /= np.linalg.norm(d2)
    return el, el + d2 * L2, d2
def arm_ik(sh, target, pole, L1, L2):
    v = target - sh; d = min(np.linalg.norm(v), L1 + L2 - 0.05); u = v / np.linalg.norm(v)
    a = (L1*L1 - L2*L2 + d*d) / (2*d); h = math.sqrt(max(L1*L1 - a*a, 0))
    pl = pole - u * (pole @ u); pl /= np.linalg.norm(pl)
    el = sh + u*a + pl*h; wr = sh + u*d; d2 = (wr - el) / np.linalg.norm(wr - el)
    return el, wr, d2

def sole_lift(legs):
    D = DIM; zs = []
    for i, sx in enumerate((-D['hip_x'], D['hip_x'])):
        _, ank = leg_chain(np.array([sx, 0, D['hip_z']]), *legs[i], D['L1'], D['L2']); zs.append(ank[2])
    rest = D['hip_z'] - D['L1'] - D['L2']
    return -(min(zs) - rest)

def head_center(pose):
    D = DIM; up = pose.get('breathe', 0.0); lift = pose.get('lift', 0.0)
    return np.array(D['head_c']) + np.array([0, 0, up + lift])

# ---------- pose -> primitives (local: +x character's RIGHT, +y forward, +z up) ----------
def build(pose):
    P = build_cast(pose) if CID in NEW_CAST else _build_main(pose)
    ak = DIM.get('arm_k', 1.0)
    if ak != 1.0:
        P = [(t, (a[0], a[1], a[2] * ak, a[3] * ak) + tuple(a[4:]), m, g) if (t == 'cap' and g in ('arm', 'sleeve', 'hand')) else (t, a, m, g) for t, a, m, g in P]
    return P

def _build_main(pose):
    D = DIM; up = pose.get('breathe', 0.0); lift = pose.get('lift', 0.0)
    P = []; o = np.array([0, 0, lift])
    sw = np.array([pose.get('sway', 0.0), 0, 0])          # Penny walk hip sway (1 px pelvis shift)
    for i, sx in enumerate((-D['hip_x'], D['hip_x'])):
        th, kn = pose['legs'][i]
        hip = o + sw + np.array([sx, 0, D['hip_z']])
        knee, ank = leg_chain(hip, th, kn, D['L1'], D['L2'])
        P.append(('cap', (hip, knee, *D['thigh_r']), 'pants', 'leg'))
        P.append(('cap', (knee, ank + np.array([0, 0, 1.0]), *D['shin_r']), 'pants', 'leg'))
        fc = ank + np.array([0, 2.6, -1.2]) + np.array([0, 0, 3.5 - (D['hip_z'] - D['L1'] - D['L2'])])
        P.append(('rbox', (fc, D['foot'], 1.6), 'shoes', 'foot'))
        if CID == 'penny':   # boot shaft to mid-shin
            P.append(('cap', (ank + np.array([0, 0, 0.6]), ank + (knee - ank) * 0.50, D['shin_r'][1] + 0.7, D['shin_r'][1] + 0.9), 'shoes', 'leg'))
    pz, ph = D['pelvis']
    P.append(('rbox', (o + sw + np.array([0, 0, pz]), ph, 3.0), 'pants', 'pelvis'))
    ub = o + np.array([0, 0, up]); sl = D['slouch']
    tmat = {'sheldon': 'tee', 'leonard': 'hoodie', 'penny': 'top'}[CID]
    tz = D['torso_z']; tw, td, th_ = D['torso']
    P.append(('rbox', (ub + np.array([0, sl*0.4, tz]), (tw, td, th_), D['torso_r']), tmat, 'torso'))
    if CID == 'penny':   # fitted top: chest volume + hem flare over the waistband
        P.append(('ell', (ub + np.array([0, td*0.42, tz + 3.4]), np.array([8.6, 3.6, 3.8])), 'top', 'torso'))
        P.append(('rbox', (ub + sw*0.5 + np.array([0, 0, tz - th_ + 2.2]), (tw - 0.6, td - 0.2, 2.6), 2.4), 'top', 'torso'))
    if CID == 'leonard':
        # hoodie hem flare over the hips + bunched hood behind the neck
        P.append(('rbox', (ub + np.array([0, 0, tz - th_ + 3.0]), (tw + 0.4, td + 0.4, 3.4), 2.6), 'hoodie', 'torso'))
        P.append(('ell', (ub + np.array([0, -td + 0.6 + sl*0.3, tz + th_ - 1.4]), np.array([8.4, 4.4, 4.0])), 'hoodie', 'hood'))
    n0, n1, nr = D['neck']
    P.append(('cap', (ub + np.array([0, -0.3 + sl, n0]), ub + np.array([0, 0.2 + sl*1.3, n1]), nr), 'skin', 'neck'))
    shoulder_top = tz + th_ - 1.2
    for i, sx in enumerate((-D['sh_x'], D['sh_x'])):
        sh = ub + np.array([sx, sl*0.8, D['sh_z']])
        if pose.get('ik') and i in pose['ik']:
            tgt, pole = pose['ik'][i]
            el, wr, d2 = arm_ik(sh, ub + np.array(tgt) + np.array(D.get('ik_off', (0, 0, 0))), np.array(pole), D['aL1'], D['aL2'])
        else:
            fl, eb = pose['arms'][i]
            el, wr, d2 = arm_chain(sh, fl, eb, pose.get('abduct', 0.10), D['aL1'], D['aL2'])
        if CID == 'sheldon':
            sleeve_end = sh + (el - sh) * D['sleeve_frac']
            P.append(('cap', (sh, sleeve_end, 4.2, 3.9, ub[2] + shoulder_top), 'tee', 'sleeve'))
            P.append(('cap', (sh, el, 3.5, 3.3, ub[2] + shoulder_top), 'under', 'arm'))
            P.append(('cap', (el, wr, 3.3, 3.0), 'under', 'arm'))
        elif CID == 'penny':
            sleeve_end = sh + (el - sh) * D['sleeve_frac']
            P.append(('cap', (sh, sleeve_end, 3.9, 3.6, ub[2] + shoulder_top), 'top', 'sleeve'))
            P.append(('cap', (sh, el, 3.0, 2.8, ub[2] + shoulder_top), 'skin', 'arm'))
            P.append(('cap', (el, wr, 2.8, 2.4), 'skin', 'arm'))
        else:
            P.append(('cap', (sh, el, 4.0, 3.7, ub[2] + shoulder_top + 0.4), 'hoodie', 'sleeve'))
            P.append(('cap', (el, wr, 3.7, 3.5), 'hoodie', 'sleeve'))
        if CID == 'penny': P.append(('cap', (wr + d2*1.2, wr + d2*4.2, 2.5, 2.2), 'skin', 'hand'))
        else: P.append(('cap', (wr + d2*1.2, wr + d2*4.4, 2.9, 2.6), 'skin', 'hand'))
    hargs = (head_center(pose), pose.get('head_yaw', 0.0), pose.get('head_pitch', 0.0))
    if CID == 'penny': hargs = hargs + (pose.get('hair_swing', 0.0),)
    P.append(('head', hargs, None, 'head'))
    return P

# Leonard curl bumps (head-local), fixed so every frame matches
_rng = np.random.default_rng(7)
CURLS = []
for k in range(26):
    th = _rng.uniform(0, 2*math.pi); ph = _rng.uniform(0.05, 1.25)
    v = np.array([math.cos(th)*math.sin(ph), math.sin(th)*math.sin(ph)*0.95 - 0.08, math.cos(ph)])
    if v[1] > 0.40 and v[2] < 0.80: continue          # keep the forehead clear
    CURLS.append((v * np.array([9.6, 10.0, 11.4]) + np.array([0, -0.6, 1.2]), _rng.uniform(2.2, 2.9)))

def head_rot(hy, hp=0.0):
    return rotz(hy) @ rotx(hp)
def head_sdf(p, hc, hy, hp=0.0, hs=0.0):
    hk = DIM.get('head_k', 1.0)
    if hk == 1.0: return _head_sdf(p, hc, hy, hp, hs)
    sk, hh, q = _head_sdf(hc + (p - hc) / hk, hc, hy, hp, hs)
    return sk * hk, hh * hk, q
def _head_sdf(p, hc, hy, hp=0.0, hs=0.0):
    q = (p - hc) @ head_rot(hy, hp)
    hr = np.array(DIM['head'])
    d_head = sd_ell(q, np.zeros(3), hr)
    d_nose = sd_ell(q, np.array([0, hr[1] - 0.1, -1.6]), np.array([1.6, 2.0, 2.6]))
    d_ear = np.minimum(sd_ell(q, np.array([hr[0] - 0.2, -0.5, -1.0]), np.array([1.8, 2.6, 3.6])),
                       sd_ell(q, np.array([-hr[0] + 0.2, -0.5, -1.0]), np.array([1.8, 2.6, 3.6])))
    skin = np.minimum(np.minimum(d_head, d_nose), d_ear)
    ear_clear = np.minimum(sd_ell(q, np.array([9.6, -0.6, -1.5]), np.array([3.6, 4.2, 4.6])),
                           sd_ell(q, np.array([-9.6, -0.6, -1.5]), np.array([3.6, 4.2, 4.6])))
    if CID in NEW_CAST:
        return skin, cast_hair(q, hs), q
    if CID == 'penny':
        # crown cap clipped at the hairline + side-swept volume on the character's RIGHT of a LEFT part (x=-3.2)
        cap = sd_ell(q, np.array([0, -0.6, 1.4]), np.array([9.7, 10.4, 11.7]))
        cap = smin(cap, sd_ell(q, np.array([1.8, 3.6, 7.6]), np.array([8.4, 6.4, 4.4])), 1.4)
        cap = np.maximum(cap, -sd_ell(q, np.array([-3.4, 2.0, 12.2]), np.array([0.8, 9.0, 1.2])))   # part groove
        hl = np.clip(-3.0 + 0.95 * (q[..., 1] + 5.0), -3.0, 7.2) + 0.6*np.sin(q[..., 0]*1.2)
        cap = np.maximum(cap, hl - q[..., 2])
        # long fall behind, past the shoulders, + two face-framing side strands; hs swings it (hair_flip)
        off = np.array([2.8*hs, -5.0*abs(hs), 4.2*abs(hs)])
        fall = sd_rbox(q - off*np.clip((2.0 - q[..., 2:3]) / 22.0, 0, 1.2), np.array([0, -4.4, -9.0]), (10.0, 5.6, 14.0), 4.2)
        fall = np.maximum(fall, q[..., 1] - 1.0 + 0.0*q[..., 2])           # never in front of the ear line
        st = np.minimum(sd_cap(q - off*np.clip((2.0 - q[..., 2:3]) / 22.0, 0, 1.2), np.array([8.4, 1.2, 1.0]), np.array([9.4, 0.4, -19.0]), 2.6, 3.0),
                        sd_cap(q - off*np.clip((2.0 - q[..., 2:3]) / 22.0, 0, 1.2), np.array([-8.4, 1.2, 1.0]), np.array([-9.4, 0.4, -19.0]), 2.6, 3.0))
        d_hair = smin(smin(cap, fall, 1.5), st, 1.2)
        return skin, d_hair, q
    if CID == 'sheldon':
        d_hair = sd_ell(q, np.array([0, -0.8, 1.6]), np.array([10.7, 11.7, 12.6]))
        # side-part volume: the larger sweep sits on the character's RIGHT of a part at x=-3.6, with a front quiff
        d_hair = smin(d_hair, sd_ell(q, np.array([1.4, 3.0, 9.0]), np.array([7.6, 5.4, 4.0])), 1.5)
        d_hair = np.maximum(d_hair, -sd_ell(q, np.array([-3.9, 2.0, 13.6]), np.array([0.9, 9.0, 1.3])))  # part groove
        hl = np.clip(-4.5 + 0.95 * (q[..., 1] + 5.0), -4.5, 6.8) + 0.5*np.sin(q[..., 0]*1.1 + 0.8)
    else:
        d_hair = sd_ell(q, np.array([0, -0.7, 1.2]), np.array([10.1, 10.8, 11.6]))
        for c, r in CURLS: d_hair = smin(d_hair, sd_ell(q, c, np.array([r, r, r*0.9])), 0.8)
        hl = np.clip(-4.0 + 0.95 * (q[..., 1] + 5.0), -4.0, 8.2) + 0.7*np.sin(q[..., 0]*1.6)
    d_hair = np.maximum(d_hair, hl - q[..., 2])
    d_hair = np.maximum(d_hair, -ear_clear)
    return skin, d_hair, q

TAGS = {'torso': 1, 'sleeve': 2, 'hood': 3, 'foot': 4, 'leg': 5, 'pelvis': 5, 'hand': 6, 'arm': 2, 'skirt': 7, 'collar': 8}
def scene(p, P):
    n = p.shape[0]
    global _PID
    dist = np.full(n, 1e9); mat = np.zeros(n, int); tag = np.zeros(n, int); hq = np.zeros((n, 3)); pid = np.zeros(n, int)
    for pi_, (kind, args, m, t) in enumerate(P):
        if kind == 'cap': d = sd_cap(p, *args)
        elif kind == 'skirt': d = sd_skirt(p, *args)
        elif kind == 'rbox': d = sd_rbox(p, *args)
        elif kind == 'ell': d = sd_ell(p, *args)
        elif kind == 'head':
            ds, dh, q = head_sdf(p, *args)
            for d, mm in ((ds, 'skin'), (dh, 'hair')):
                w = d < dist; dist = np.where(w, d, dist); mat[w] = MATS.index(mm); tag[w] = 99; hq[w] = q[w]; pid[w] = pi_
            continue
        w = d < dist; dist = np.where(w, d, dist); mat[w] = MATS.index(m); tag[w] = TAGS.get(t, 0); pid[w] = pi_
        if t == 'foot': hq[w] = p[w] - args[0]          # foot-local offsets (for sneaker soles)
    _PID = pid
    return dist, mat, tag, hq
_PID = None

def world_from_local(yaw_deg):
    a = math.radians(yaw_deg)
    fwd = np.array([-math.sin(a), -math.cos(a), 0]); right = np.array([fwd[1], -fwd[0], 0])
    return np.stack([right, fwd, [0, 0, 1]], 1)

def project_local(pl, yaw_deg):
    """character-local points (...,3) -> (col, row) float pixel coords + ray depth"""
    w = pl @ world_from_local(yaw_deg).T
    col = (w @ S_CAM) * SCALE_EFF + PIVOT[0]; row = PIVOT[1] - (w @ U_CAM) * SCALE_EFF
    return col, row, w @ D_CAM + 160
def head_to_local(q, pose):
    return head_center(pose) + (q * DIM.get('head_k', 1.0)) @ head_rot(pose.get('head_yaw', 0.0), pose.get('head_pitch', 0.0)).T
def head_facing(qn, pose, yaw_deg):
    """dot of a head-local normal with the direction toward the camera"""
    n = qn @ head_rot(pose.get('head_yaw', 0.0), pose.get('head_pitch', 0.0)).T @ world_from_local(yaw_deg).T
    return -(n @ D_CAM)

def render(pose, yaw_deg, ss=3, shadows=True):
    M = world_from_local(yaw_deg); P = build(pose)
    N = 128 * ss
    js, is_ = np.meshgrid(np.arange(N), np.arange(N))
    X = ((js + 0.5) / ss - PIVOT[0]) / SCALE_EFF
    Y = (PIVOT[1] - (is_ + 0.5) / ss) / SCALE_EFF
    org = (X[..., None] * S_CAM + Y[..., None] * U_CAM - 160 * D_CAM).reshape(-1, 3) @ M
    dirl = D_CAM @ M
    t = np.zeros(org.shape[0]); alive = np.ones(org.shape[0], bool); hit = np.zeros_like(alive)
    for _ in range(110):
        idx = np.where(alive)[0]
        if idx.size == 0: break
        d = scene(org[idx] + t[idx, None] * dirl, P)[0]
        t[idx] += d * 0.9
        h = d < 0.04; hit[idx[h]] = True; alive[idx[h]] = False
        alive[idx[t[idx] > 330]] = False
    pts = org + t[:, None] * dirl
    hi = np.where(hit)[0]; n = org.shape[0]
    mat = np.full(n, -1); tone = np.zeros(n, int); nrm_up = np.zeros(n); depth = np.full(n, 1e9)
    pidb = np.full(n, -1); tagb = np.zeros(n, int); hqb = np.zeros((n, 3)); uvb = np.full((n, 3), np.nan)
    if hi.size:
        ph = pts[hi]
        d0, m0, tg, hq = scene(ph, P); pidv = _PID.copy()
        e = 0.35; g = np.zeros_like(ph)
        for k in range(3):
            dv = np.zeros(3); dv[k] = e
            g[:, k] = scene(ph + dv, P)[0] - scene(ph - dv, P)[0]
        nl = g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-6)
        L_loc = LIGHT @ M; lam = nl @ L_loc
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
            tn = np.where(blocked & (tg != 99) & (tn < 2), 2, tn)
        mat[hi] = m0; tone[hi] = tn; nrm_up[hi] = (nl @ M.T) @ U_CAM; depth[hi] = t[hi]
        tagb[hi] = tg; hqb[hi] = hq; pidb[hi] = pidv
        tor = (tg == 1) | (tg == 7)
        uvb[hi[tor], 0] = -ph[tor, 0]
        uvb[hi[tor], 1] = ph[tor, 2] - pose.get('breathe', 0) - pose.get('lift', 0)
        uvb[hi[tor], 2] = nl[tor, 1]              # +front / -back facing
    def grid(a): return a.reshape(N, N, *a.shape[1:])
    B = dict(mat=grid(mat), tone=grid(tone), up=grid(nrm_up), depth=grid(depth), tag=grid(tagb), hq=grid(hqb), uv=grid(uvb), pid=grid(pidb))
    return downsample(B, ss)

def downsample(B, ss):
    mat = B['mat']; N = mat.shape[0]; n = N // ss
    def blocks(a): return a.reshape(n, ss, n, ss, *a.shape[2:]).swapaxes(1, 2).reshape(n, n, ss*ss, *a.shape[2:])
    mb = blocks(mat); tb = blocks(B['tone'])
    key = np.where(mb >= 0, mb * 4 + tb, -1); cover = (mb >= 0).sum(-1)
    best = np.full((n, n), -1); bestc = np.zeros((n, n), int)
    for k in np.unique(key[key >= 0]):
        c = (key == k).sum(-1); w = c > bestc; best[w] = k; bestc[w] = c[w]
    opaque = cover * 2 > ss * ss; out = {}
    out['mat'] = np.where(opaque, best // 4, -1); out['tone'] = np.where(opaque, best % 4, 0)
    ctr = (ss * ss) // 2
    for k in ('up', 'tag', 'hq', 'uv', 'pid'):
        if k in B: out[k] = blocks(B[k])[:, :, ctr]
    out['depth'] = np.where(opaque, np.nanmin(np.where(mb >= 0, blocks(B['depth']), np.inf), -1), 1e9)
    return out


# =====================================================================================
# Cast v1 (Howard, Raj, Bernadette, Amy): shared body builder + per-character hair SDFs
# =====================================================================================
def sd_skirt(p, ztop, zbot, rt, rb, cx=0.0, cy=0.0):
    """elliptical truncated cone (A-line skirt); hem centre offset (cx, cy) lets it sway"""
    t = np.clip((ztop - p[..., 2]) / (ztop - zbot), 0, 1)
    rx = rt[0] + (rb[0] - rt[0]) * t; ry = rt[1] + (rb[1] - rt[1]) * t
    qx = p[..., 0] - cx * t; qy = p[..., 1] - cy * t
    side = (np.sqrt((qx / rx) ** 2 + (qy / ry) ** 2) - 1) * np.minimum(rx, ry) * 0.85
    return np.maximum(side, np.maximum(p[..., 2] - ztop, zbot - p[..., 2]))

CAST_MATS = {   # torso, sleeve, legs, pelvis
 'howard': ('shirt', 'shirt', 'pants', 'pants'),
 'raj': ('jacket', 'jacket', 'pants', 'pants'),
 'bernadette': ('cardigan', 'cardigan', 'skin', 'skirt'),
 'amy': ('cardigan', 'cardigan', 'tights', 'skirt'),
}
def build_cast(pose):
    D = DIM; up = pose.get('breathe', 0.0); lift = pose.get('lift', 0.0)
    P = []; o = np.array([0, 0, lift]); tmat, smat, lmat, pmat = CAST_MATS[CID]
    sw = np.array([pose.get('sway', 0.0), 0, 0])          # gait hip sway (Howard swagger, Bernadette)
    for i, sx in enumerate((-D['hip_x'], D['hip_x'])):
        th, kn = pose['legs'][i]
        hip = o + sw + np.array([sx, 0, D['hip_z']])
        knee, ank = leg_chain(hip, th, kn, D['L1'], D['L2'])
        P.append(('cap', (hip, knee, *D['thigh_r']), lmat, 'leg'))
        P.append(('cap', (knee, ank + np.array([0, 0, 1.0]), *D['shin_r']), lmat, 'leg'))
        fc = ank + np.array([0, 2.6, -1.2]) + np.array([0, 0, 3.5 - (D['hip_z'] - D['L1'] - D['L2'])])
        P.append(('rbox', (fc, D['foot'], 1.6), 'shoes', 'foot'))
    pz, ph = D['pelvis']
    P.append(('rbox', (o + sw + np.array([0, 0, pz]), ph, 3.0), pmat, 'pelvis'))
    ub = o + np.array([pose.get('roll', 0.0), 0, up]); ch = D.get('chest', 0.0)
    tz = D['torso_z']; tw, td, th_ = D['torso']
    P.append(('rbox', (ub + np.array([0, ch * 0.5, tz]), (tw, td, th_), D['torso_r']), tmat, 'torso'))
    if ch: P.append(('ell', (ub + np.array([0, td * 0.40 + ch, tz + 3.0]), np.array([9.4, 3.6, 4.2])), tmat, 'torso'))
    if CID == 'howard':   # wide belt (tag torso so the buckle decal gets uv); tucked shirt
        P.append(('rbox', (o + sw + np.array([0, 0, pz + ph[2] - 0.6]), (ph[0] + 0.4, ph[1] + 0.4, 1.25), 1.2), 'belt', 'torso'))
    if CID == 'raj':      # jacket hem over the hips
        P.append(('rbox', (ub + np.array([0, 0, tz - th_ + 2.0]), (tw + 0.5, td + 0.5, 3.6), 2.8), 'jacket', 'torso'))
    if CID == 'amy':      # long cardigan to the hips over the skirt waist
        P.append(('rbox', (ub + np.array([0, 0, tz - th_ + 1.4]), (tw + 0.4, td + 0.4, 3.4), 2.6), 'cardigan', 'torso'))
    if CID == 'bernadette':   # chest volume (fitted cardigan)
        P.append(('ell', (ub + np.array([0, td * 0.40, tz + 2.6]), np.array([7.8, 3.2, 3.4]) * np.array([1.0, D.get('bust', 1.0), D.get('bust', 1.0) ** 0.5])), 'cardigan', 'torso'))
    if 'skirt' in D:
        zt, zb, rt, rb = D['skirt']
        # hem follows the legs a little (forward leg pushes the hem forward)
        fy = 0.5 * (math.sin(pose['legs'][0][0]) + math.sin(pose['legs'][1][0])) * (zt - zb) * 0.5
        sp = abs(pose['legs'][0][0] - pose['legs'][1][0])
        rb2 = (rb[0], rb[1] + sp * 3.0)
        P.append(('skirt', (zt + lift, zb + lift, rt, rb2, 0.8 * sw[0], fy), pmat, 'skirt'))
    n0, n1, nr = D['neck']
    sl = D.get('slouch', 0.0)   # forward hunch: neck leans forward, shoulders roll forward
    P.append(('cap', (ub + np.array([0, -0.3 + 0.3 * sl, n0]), ub + np.array([0, 0.2 + 1.1 * sl, n1]), nr), 'skin', 'neck'))
    # collars: Howard turtleneck dickey, Raj shirt collar, Bernadette/Amy blouse collar
    col = {'howard': ('dickey', 4.6, 1.15), 'raj': ('shirt', 2.4, 1.3), 'bernadette': ('blouse', 1.8, 1.0), 'amy': ('blouse', 1.8, 1.0)}[CID]
    P.append(('cap', (ub + np.array([0, -0.2 + 0.3 * sl, n0 - 0.4]), ub + np.array([0, 0.1 + 0.7 * sl, n0 + col[1]]), nr + col[2]), col[0], 'collar'))
    shoulder_top = tz + th_ - 1.2
    sr = {'howard': (3.3, 3.0), 'raj': (4.0, 3.6), 'bernadette': (3.4, 3.1), 'amy': (3.6, 3.3)}[CID]
    for i, sx in enumerate((-D['sh_x'], D['sh_x'])):
        sh = ub + np.array([sx, 0.8 * sl, D['sh_z'] - 0.3 * sl])
        if pose.get('ik') and i in pose['ik']:
            tgt, pole = pose['ik'][i]
            el, wr, d2 = arm_ik(sh, ub + np.array(tgt) + np.array(D.get('ik_off', (0, 0, 0))), np.array(pole), D['aL1'], D['aL2'])
        else:
            fl, eb = pose['arms'][i]
            el, wr, d2 = arm_chain(sh, fl, eb, pose.get('abduct', D.get('abduct', 0.10)), D['aL1'], D['aL2'])
        P.append(('cap', (sh, el, sr[0] + 0.3, sr[0], ub[2] + shoulder_top + 0.4), smat, 'sleeve'))
        P.append(('cap', (el, wr, sr[0], sr[1]), smat, 'sleeve'))
        hr_ = 2.5 if CID in ('bernadette', 'amy') else 2.8
        P.append(('cap', (wr + d2 * 1.2, wr + d2 * 4.2, hr_, hr_ - 0.3), 'skin', 'hand'))
    P.append(('head', (head_center(pose), pose.get('head_yaw', 0.0), pose.get('head_pitch', 0.0), pose.get('hair_swing', 0.0)), None, 'head'))
    return P

def cast_hair(q, hs=0.0):
    x, y, z = q[..., 0], q[..., 1], q[..., 2]
    if CID == 'howard':
        # bowl cut: full rounded cap, straight bangs at the brow, sides over the ear tops, short at the nape
        cap = sd_ell(q, np.array([0, -0.6, 1.6]), np.array([9.8, 10.3, 12.0]))
        hl = 4.8 - 9.5 * np.clip((1.0 - y) / 12.0, 0, 1)
        cap = np.maximum(cap, hl - z)
        ear = np.minimum(sd_ell(q, np.array([9.4, -0.6, -2.4]), np.array([3.4, 3.8, 2.8])),
                         sd_ell(q, np.array([-9.4, -0.6, -2.4]), np.array([3.4, 3.8, 2.8])))
        return np.maximum(cap, -ear)
    if CID == 'raj':
        # thick, side-parted (his LEFT, x=-3.6), swept up and back with a raised front
        cap = sd_ell(q, np.array([0, -0.8, 1.8]), np.array([10.2, 11.2, 12.4]))
        cap = smin(cap, sd_ell(q, np.array([1.0, 2.4, 9.4]), np.array([8.6, 7.4, 4.8])), 1.6)
        cap = np.maximum(cap, -sd_ell(q, np.array([-3.6, 1.6, 13.4]), np.array([0.9, 8.0, 1.4])))
        hl = np.clip(-4.0 + 0.95 * (y + 5.0), -4.0, 6.0) + 0.4 * np.sin(x * 1.1)
        cap = np.maximum(cap, hl - z)
        ear = np.minimum(sd_ell(q, np.array([9.8, -0.6, -1.5]), np.array([3.6, 4.2, 4.6])),
                         sd_ell(q, np.array([-9.8, -0.6, -1.5]), np.array([3.6, 4.2, 4.6])))
        return np.maximum(cap, -ear)
    hr = np.array(DIM['head'])
    if CID == 'bernadette':
        # blonde wavy, shoulder length, side part on her LEFT (x=-2.8), soft volume
        cap = sd_ell(q, np.array([0, -0.6, 1.4]), hr * np.array([1.12, 1.10, 1.08]))
        cap = smin(cap, sd_ell(q, np.array([1.6, 3.2, 6.8]), np.array([7.6, 5.8, 4.0])), 1.3)
        cap = np.maximum(cap, -sd_ell(q, np.array([-2.8, 1.8, 11.2]), np.array([0.8, 8.0, 1.1])))
        hl = np.clip(-2.6 + 0.95 * (y + 4.6), -2.6, 6.4) + 0.6 * np.sin(x * 1.2)
        cap = np.maximum(cap, hl - z)
        off = np.array([2.6 * hs, -4.0 * abs(hs), 3.0 * abs(hs)])
        qq = q - off * np.clip((2.0 - q[..., 2:3]) / 18.0, 0, 1.2)
        wave = 0.9 * np.sin(qq[..., 2] * 0.85 + np.arctan2(qq[..., 0], -qq[..., 1]) * 3.0)
        fall = sd_rbox(qq, np.array([0, -3.4, -4.6]), (10.4, 5.8, 9.4), 4.6) + wave * 0.6
        fall = np.maximum(fall, qq[..., 1] - 1.6)
        st = np.minimum(sd_cap(qq, np.array([8.4, -1.2, 1.0]), np.array([9.6, -0.8, -12.6]), 2.4, 3.4),
                        sd_cap(qq, np.array([-8.4, -1.2, 1.0]), np.array([-9.6, -0.8, -12.6]), 2.4, 3.4)) + wave * 0.5
        return smin(smin(cap, fall, 1.4), st, 1.2)
    # amy: long straight brown hair, side part on her LEFT (x=-2.4), flat on top, curtains past the shoulders
    cap = sd_ell(q, np.array([0, -0.5, 1.2]), hr * np.array([1.08, 1.08, 1.05]))
    cap = smin(cap, sd_ell(q, np.array([1.4, 3.4, 6.6]), np.array([7.8, 5.6, 3.6])), 1.2)
    cap = np.maximum(cap, -sd_ell(q, np.array([-2.4, 1.6, 12.0]), np.array([0.8, 8.0, 1.1])))
    hl = np.clip(-2.6 + 0.95 * (y + 4.6), -2.6, 6.6) + 0.4 * np.sin(x * 1.2)
    cap = np.maximum(cap, hl - z)
    off = np.array([2.0 * hs, -3.0 * abs(hs), 2.0 * abs(hs)])
    qq = q - off * np.clip((2.0 - q[..., 2:3]) / 22.0, 0, 1.2)
    fall = sd_rbox(qq, np.array([0, -4.2, -8.2]), (10.0, 5.4, 13.0), 3.6)
    fall = np.maximum(fall, qq[..., 1] - 1.2)
    st = np.minimum(sd_cap(qq, np.array([8.2, 1.4, 0.8]), np.array([8.8, 0.8, -19.6]), 2.7, 2.9),
                    sd_cap(qq, np.array([-8.2, 1.4, 0.8]), np.array([-8.8, 0.8, -19.6]), 2.7, 2.9))
    return smin(smin(cap, fall, 1.2), st, 1.0)
