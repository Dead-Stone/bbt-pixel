"""Body-part library.  Every function draws ONE named part (or one clothing / hair layer) of the modular human
into a Canvas from the solved skeleton J.  Parts:
  head (cranium + jaw + nose + ears), neck, chest, waist, pelvis (+ glutes), bust, shoulder (trapezius + deltoid),
  upper_arm, forearm, hand, thigh, shin (+ calf), foot
Layers drawn over them (inflated volumes, same joints): top / jacket / pants / skirt / shoes / hair / props."""
import math
import numpy as np
from skeleton import unit, CAM_V, project

SIDES = (('R', 1), ('L', -1))


def ell(cv, c, axes, semi, mat, part, **kw):
    A = np.stack([unit(a) * s for a, s in zip(axes, semi)], 1)
    cv.ellipsoid(c, A, mat, part, **kw)


def far_side(J):
    """'R' or 'L': the side whose shoulder is farther from the camera (drawn one tone darker)"""
    dR = project(J['shR'])[2]; dL = project(J['shL'])[2]
    if abs(dR - dL) < 4: return None
    return 'R' if dR > dL else 'L'


# ----------------------------------------------------------------------------------------------- skin parts
def head(cv, B, J, mat='skin'):
    Mh = J['Mh']; hR, hF, hU = Mh[:, 0], Mh[:, 1], Mh[:, 2]; c = J['head_c']; w, d, h = B.head['w'], B.head['d'], B.head['h']
    ell(cv, c + hU * (0.06 * h) - hF * (0.04 * d), (hR, hF, hU), (w * 0.50, d * 0.50, h * 0.44), mat, 'head')
    ell(cv, c - hU * (0.20 * h) + hF * (0.10 * d), (hR, hF, hU), (w * 0.43, d * 0.38, h * 0.30), mat, 'head')   # jaw/cheeks
    ell(cv, c - hU * (0.36 * h) + hF * (0.26 * d), (hR, hF, hU), (w * 0.17, d * 0.16, h * 0.10), mat, 'head')   # chin
    ell(cv, c - hU * (0.07 * h) + hF * (0.47 * d), (hR, hF, hU), (0.08 * w, 0.09 * d, 0.10 * h), mat, 'head')   # nose
    for s, sg in SIDES:
        ell(cv, c + hR * (sg * w * 0.49) - hF * (0.02 * d), (hR, hF, hU), (0.06 * w, 0.08 * d, 0.13 * h), mat, 'head')


def neck(cv, B, J, mat='skin'):
    cv.chain(J['neck0'] - J['Mc'][:, 2] * 1.5, J['neck1'] + J['Mh'][:, 2] * 1.0, B.r_neck * 1.1, B.r_neck * 0.95, mat, 'neck')


def torso(cv, B, J, mat='skin', infl=0.0, part='torso', keep_chest=None, hem=None, tone=0, keep_waist=None, keep_trap=None, tex=0.0, shoulders=True, waist_infl=None):
    Mc, Mp = J['Mc'], J['Mp']
    cR, cF, cU = Mc[:, 0], Mc[:, 1], Mc[:, 2]; pR, pF, pU = Mp[:, 0], Mp[:, 1], Mp[:, 2]
    ch, wa, pe = B.chest, B.waist, B.pelvis
    br = J.get('breath', 0.0) * 0.35
    ell(cv, J['chest_c'], (cR, cF, cU), (ch['w'] + infl, ch['d'] + infl + br, ch['h'] + infl), mat, part, keep=keep_chest, tone=tone, tex=tex)
    # trapezius / shoulder line: makes the neck -> shoulder slope
    ell(cv, J['sh_c'] - cU * (0.012 * B.H) - cF * (0.008 * B.H), (cR, cF, cU), (B.sh_x * 0.94 + infl, ch['d'] * 0.78 + infl, 0.026 * B.H + infl), mat, part, keep=keep_trap, tone=tone)
    for s, sg in SIDES:
        if shoulders: cv.sphere(J['sh' + s] + cU * 0.2, B.r_upper[0] * 1.02 + infl, mat, part, tone=tone)
    if B.bust and not (keep_chest is not None and getattr(keep_chest, 'open_front', False)):
        for s, sg in SIDES:
            cv.sphere(J['chest_c'] + cF * (ch['d'] * 0.56) + cR * (sg * ch['w'] * 0.42) - cU * (ch['h'] * 0.28) + cF * br,
                      0.034 * B.H * B.bust + infl, mat, part, tone=tone)
    wz = 1.0 if hem is None else hem
    if wz > 0:
        wi = infl if waist_infl is None else waist_infl
        ell(cv, J['waist_c'] + cF * (0.004 * B.H * B.belly), (cR, cF, cU), (wa['w'] + wi, wa['d'] + infl + 0.02 * B.H * B.belly, B.spine * 0.30 + infl), mat, part, keep=keep_waist, tone=tone)


def pelvis(cv, B, J, mat='skin', infl=0.0, part='pelvis', keep=None, tone=0, glutes=True, tex=0.0):
    Mp = J['Mp']; pR, pF, pU = Mp[:, 0], Mp[:, 1], Mp[:, 2]; pe = B.pelvis
    ell(cv, J['pel'] - pU * (0.010 * B.H), (pR, pF, pU), (pe['w'] + infl, pe['d'] + infl, pe['h'] + infl), mat, part, keep=keep, tone=tone, tex=tex)
    for s, sg in SIDES:     # glutes
        if not glutes: break
        cv.sphere(J['pel'] + pR * (sg * B.hip_x * 0.85) - pF * (pe['d'] * 0.30) - pU * (0.035 * B.H), 0.044 * B.H * B.limb + infl, mat, part, tone=tone)


def leg(cv, B, J, s, mat='skin', infl=(0, 0), part=None, upto=1.0, tone=0, flare=0.0):
    """thigh (hip->knee) + shin (knee->ankle) + calf. infl = (thigh, shin) inflation. upto<1 stops partway down shin"""
    hip, kn, an = J['hip' + s], J['knee' + s], J['ank' + s]
    rt, rs = B.r_thigh, B.r_shin
    cv.chain(hip + (hip - kn) * 0.06, kn, rt[0] + infl[0], rt[1] + infl[0], mat, (part or 'thigh_') + s, tone=tone)
    if upto > 0:
        cv.chain(kn, an, rs[0] + infl[0] * 0.9, rs[1] + infl[1] + flare, mat, (part or 'shin_') + s, tone=tone, t1=upto,
                 bulge=lambda t: 0.007 * B.H * B.limb * max(0.0, math.sin(math.pi * min(1, t / 0.55))) * (1 if t < 0.55 else 0))


def foot(cv, B, J, s, mat='skin', infl=0.0, part=None, tone=0, h=1.0):
    fd = J['foot' + s]; up = np.array([0, 0, 1.0]); side = unit(np.cross(fd, up))
    up2 = unit(np.cross(side, fd))
    c = (J['heel' + s] + J['toe' + s]) * 0.5 + up2 * (0.014 * B.H * h)
    L = np.linalg.norm(J['toe' + s] - J['heel' + s]) * 0.5
    ell(cv, c, (fd, side, up2), (L + infl, 0.024 * B.H + infl, 0.020 * B.H * h + infl), mat, (part or 'foot_') + s, tone=tone)
    cv.chain(J['ank' + s] + up2 * 1.0, c, B.r_shin[1] * 0.95 + infl, 0.020 * B.H + infl * 0.5, mat, (part or 'foot_') + s, tone=tone)


def arm(cv, B, J, s, mat='skin', infl=0.0, part=None, t_upper=(0, 1), t_fore=None, tone=0):
    sh, el, wr = J['sh' + s], J['el' + s], J['wr' + s]
    ru, rf = B.r_upper, B.r_fore
    if t_upper:
        cv.chain(sh, el, ru[0] + infl, ru[1] + infl, mat, (part or 'upper_arm_') + s, tone=tone, t0=t_upper[0], t1=t_upper[1])
    if t_fore:
        cv.chain(el, wr, rf[0] + infl, rf[1] + infl, mat, (part or 'forearm_') + s, tone=tone, t0=t_fore[0], t1=t_fore[1])


def hand(cv, B, J, s, mat='skin', tone=0, fist=False):
    wr, hd = J['wr' + s], J['hd' + s]
    up = J['Mc'][:, 2]; side = unit(np.cross(hd, up)) if abs(np.dot(hd, up)) < 0.95 else J['Mc'][:, 0]
    nrm = unit(np.cross(side, hd))
    L = B.hand * (0.36 if fist else 0.50)
    ell(cv, wr + hd * L * 0.95, (hd, side, nrm), (L, 0.020 * B.H, 0.010 * B.H), mat, 'hand_' + s, tone=tone)


# ----------------------------------------------------------------------------------------------- hair
_H2S = {}
def _head_to_sh(B):
    if id(B) not in _H2S:
        import skeleton as SK
        R = SK.solve(B, {}, 0.0); _H2S[id(B)] = R['Mh'].T @ (R['head_c'] - R['sh_c'])
    return _H2S[id(B)]


def hair(cv, B, J, st, mat='hair', t=0.0, swing=(0.0, 0.0)):
    """st: dict(kind, length, part, bangs, vol, curl).  swing = (sideways, forward) secondary-motion offset (cm)
    applied to the hanging strands, growing with distance from the scalp."""
    Mh = J['Mh']; hR, hF, hU = Mh[:, 0], Mh[:, 1], Mh[:, 2]; c = J['head_c']; w, d, h = B.head['w'], B.head['d'], B.head['h']
    vol = st.get('vol', 1.0); part = st.get('part', 1)
    hl = st.get('hairline', 0.40)
    def keep_cap(q):           # q = unit coords (R, F, U) of the cap ellipsoid: drop the face region
        face = (q[:, 1] > -0.05) & (q[:, 2] < hl + 0.10 * part * q[:, 0]) & (np.abs(q[:, 0]) < st.get('face_w', 0.80))
        return ~face
    capc = c + hU * (0.08 * h) - hF * (0.06 * d)
    caps = (w * 0.50 + 0.9 * vol, d * 0.50 + 0.9 * vol, h * 0.44 + B.hair_top * 0.85)
    streak = lambda q: ((np.sin(np.arctan2(q[:, 0], -q[:, 1]) * 7 + 0.6 * part) > 0.78) & (q[:, 2] > 0.1)).astype(float)
    ell(cv, capc, (hR, hF, hU), caps, mat, 'hair', keep=keep_cap, tex=streak)
    kind = st.get('kind', 'short')
    if st.get('bangs'):
        # side-swept fringe: a flattened lobe across the forehead, heavier on the parting's far side
        bc = c + hU * (0.27 * h) + hF * (0.38 * d) - hR * (part * 0.12 * w)
        A = (hR * math.cos(0.35 * part) - hU * math.sin(0.35 * part), hF, hU * math.cos(0.35 * part) + hR * math.sin(0.35 * part))
        ell(cv, bc, A, (w * 0.40, 0.11 * d, 0.12 * h), mat, 'hair')
    if kind in ('long', 'bob', 'shoulder'):
        L = st.get('length', 30.0)
        # the hair rests on a torso *rigid with the head* (rest-pose offset): long hair then moves as one piece with the
        # head and does not re-rasterise every time the chest breathes or twists a fraction of a pixel
        cR, cF, cU = hR, hF, hU; sh_c = c - Mh @ _head_to_sh(B)
        ch = B.chest
        angs = list(np.linspace(-112, 112, 19))
        for k, a in enumerate(angs):
            ar = math.radians(a)
            front = abs(a) > 92
            if front and not st.get('front', True): continue
            r0 = c + hR * (math.sin(ar) * (w * 0.50 + (1.3 if front else 0.6) * vol)) - hF * (math.cos(ar) * (d * 0.48 + 0.6 * vol)) - hU * (0.04 * h)
            Lk = L * (0.86 if front else 1.0) * (1 + 0.05 * math.sin(k * 2.3))
            n = max(4, int(Lk / 1.5))
            prev = r0; pts = []
            for i in range(n + 1):
                u = i / n
                p = r0 - np.array([0, 0, 1.0]) * (Lk * u)
                # flare out under the jaw (volume), wave
                rad = hR * math.sin(ar) + (-hF) * math.cos(ar)
                p = p + rad * (vol * 1.6 * math.sin(math.pi * min(1, u * 1.4)) + st.get('curl', 0.6) * math.sin(u * 9 + k))
                p = p + hR * (swing[0] * u * u) + hF * (swing[1] * u * u)
                # keep out of the torso: push behind the back or in front of the chest
                rel = p - sh_c; zr = np.dot(rel, cU)
                if zr < 0.04 * B.H:
                    xr = np.dot(rel, cR); fr = np.dot(rel, cF)
                    hw = B.sh_x * 1.05 + 1.2 if zr > -0.06 * B.H else ch['w'] + 1.2
                    hd = ch['d'] + 1.6 + 0.8 * vol
                    if abs(xr) < hw:
                        need = hd * math.sqrt(max(0.0, 1 - (xr / hw) ** 2)) * min(1.0, (0.04 * B.H - zr) / (0.03 * B.H))
                        if front and fr < need: p = p + cF * (need - fr)
                        if not front and fr > -need: p = p - cF * (fr + need)
                pts.append(p)
            for i, p in enumerate(pts):
                u = i / n
                r = (2.4 * vol) * (1 - 0.55 * u ** 1.5) * (0.75 if front and u < 0.3 else 1.0) + 0.3
                cv.sphere(p, r, mat, 'hair_back' if not front else 'hair_front', tex=float(k % 4 == 1) if u > 0.12 else 0.0)


# ----------------------------------------------------------------------------------------------- face
FACE = dict(eyeR=(0.25, 0.43, -0.01), eyeL=(-0.25, 0.43, -0.01), browR=(0.26, 0.45, 0.10), browL=(-0.26, 0.45, 0.10),
            mouth=(0.0, 0.47, -0.27), nose=(0.0, 0.55, -0.12))


def landmarks(B, J):
    Mh = J['Mh']; c = J['head_c']; w, d, h = B.head['w'], B.head['d'], B.head['h']
    out = {}
    for k, (r, f, u) in FACE.items():
        p = c + Mh[:, 0] * (r * w) + Mh[:, 1] * (f * d) + Mh[:, 2] * (u * h)
        sx, sy, dep = project(p)
        facing = float(np.dot(unit(p - (c - Mh[:, 1] * 0.2 * d)), CAM_V))
        out[k] = (sx, sy, dep, facing)
    return out


# ----------------------------------------------------------------------------------------------- extra clothing layers
def _leg_point(B, J, s, t):
    """point at fraction t down the leg (0 hip, 1 knee, 2 ankle)"""
    hip, kn, an = J['hip' + s], J['knee' + s], J['ank' + s]
    return hip + (kn - hip) * t if t <= 1 else kn + (an - kn) * (t - 1)


def skirt(cv, B, J, mat, length=0.8, flare=1.0, part='skirt', dots=False):
    """waistband -> hem as a stack of slices, each an ellipse wrapping both legs at that depth (works walking and
    seated: the slices follow the thighs).  length in leg units (1 = knee, 2 = ankle)."""
    Mp = J['Mp']; pR, pF, pU = Mp[:, 0], Mp[:, 1], Mp[:, 2]; pe = B.pelvis
    pelvis(cv, B, J, mat=mat, infl=1.2, part=part, glutes=True)
    n = max(4, int(round(6 * length)))
    rt = B.r_thigh
    for i in range(1, n + 1):
        t = length * i / n
        a, b = _leg_point(B, J, 'R', t), _leg_point(B, J, 'L', t)
        c = (a + b) * 0.5
        ax = b - a; span = np.linalg.norm(ax); ax = unit(ax) if span > 1e-6 else pR
        dn = unit(_leg_point(B, J, 'R', min(t + 0.05, 2)) + _leg_point(B, J, 'L', min(t + 0.05, 2)) - 2 * c) if t < 2 else -pU
        fw = unit(np.cross(dn, ax))
        legr = rt[0] + (rt[1] - rt[0]) * min(t, 1) if t <= 1 else B.r_shin[0]
        r_out = span * 0.5 + legr + 1.0 + flare * 2.2 * (t / max(length, 1e-3))
        tex = 0.0
        if dots:
            def tex(q, i=i):
                ang = np.arctan2(q[:, 0], q[:, 1])
                return np.where((np.cos(ang * 7 + (i % 2) * math.pi / 7 * 2) > 0.93) & (np.abs(q[:, 2]) < 0.45) & (i % 2 == 0), 3.0, 0.0)
        ell(cv, c, (ax, fw, dn), (r_out, legr + 1.6 + flare * 0.8 * t / max(length, 1e-3), (B.thigh * length / n) * 0.75 + 1.0), mat, part, tex=tex)


def open_front(fn):
    fn.open_front = True; return fn


def jacket(cv, B, J, mat, infl=1.5, sleeve=1.95, hood=False, hem=0.5, gap=0.16, far=None, part='jacket'):
    """open-front jacket / cardigan / hoodie: a torso shell with the front strip removed, long sleeves, a hem over
    the hips, optional hood bunched behind the neck"""
    kc = open_front(lambda q: ~((q[:, 1] > 0.25) & (np.abs(q[:, 0]) < gap + 0.1 * np.clip(q[:, 2], 0, 1))))
    kw = lambda q: ~((q[:, 1] > 0.25) & (np.abs(q[:, 0]) < gap * 1.2))
    kt = lambda q: ~((q[:, 1] > 0.1) & (np.abs(q[:, 0]) < 0.42))
    torso(cv, B, J, mat=mat, infl=infl, part=part, keep_chest=kc, keep_waist=kw, keep_trap=kt,
          waist_infl=infl + 0.8 * (B.chest['w'] - B.waist['w']))
    if hem > 0:
        pelvis(cv, B, J, mat=mat, infl=infl + 1.9, part=part, glutes=True,
               keep=lambda q: (q[:, 2] > 1.0 - 2.0 * hem) & ~((q[:, 1] > 0.25) & (np.abs(q[:, 0]) < gap * 1.3)))
        for s, _ in SIDES:           # the hem also covers the top of each thigh, so trouser hips can't poke through
            hip, kn = J['hip' + s], J['knee' + s]; rt = B.r_thigh
            cv.chain(hip + (hip - kn) * 0.06, kn, rt[0] + infl + 1.6, rt[1] + infl + 1.6, mat, part, t0=0.0, t1=0.10 * hem / 0.5)
    for s, sg in SIDES:
        tone = 1 if s == far else 0
        arm(cv, B, J, s, mat=mat, infl=infl * 0.75, part='jsleeve_', t_upper=(0, 1), t_fore=(0, sleeve - 1.0), tone=tone)
    if hood:
        Mc = J['Mc']; cR, cF, cU = Mc[:, 0], Mc[:, 1], Mc[:, 2]
        ell(cv, J['neck0'] - cF * (B.chest['d'] * 0.80) - cU * 2.2, (cR, cF, cU), (B.sh_x * 0.40, 2.4, 3.0), mat, part + '_hood')


def vest(cv, B, J, mat, infl=1.3, part='vest'):
    """sleeveless V-neck sweater vest down to the hip"""
    kv = lambda q: ~((q[:, 1] > 0.2) & (q[:, 2] > 0.15 + 1.6 * np.abs(q[:, 0])))
    torso(cv, B, J, mat=mat, infl=infl, part=part, keep_chest=kv, keep_trap=lambda q: ~(q[:, 1] > 0.05), shoulders=False)
    pelvis(cv, B, J, mat=mat, infl=infl + 0.4, part=part, glutes=False, keep=lambda q: q[:, 2] > 0.2)


def belt(cv, B, J, mat, infl=1.2, buckle=True, part='belt'):
    Mp = J['Mp']; pR, pF, pU = Mp[:, 0], Mp[:, 1], Mp[:, 2]; pe = B.pelvis
    c = J['pel'] + pU * (pe['h'] * 0.62)
    tex = (lambda q: np.where((q[:, 1] > 0.75) & (np.abs(q[:, 0]) < 0.28), 3.0, 0.0)) if buckle else 0.0
    ell(cv, c, (pR, pF, pU), (B.waist['w'] * 1.08 + infl, pe['d'] * 0.98 + infl, 1.6), mat, part, tex=tex)


def collar_neck(cv, B, J, mat, infl=0.8, upto=0.75, part='collar'):
    """turtleneck / dickey: the neck wrapped in cloth up to `upto` of its length"""
    a = J['neck0'] - J['Mc'][:, 2] * 1.5; b = J['neck1'] + J['Mh'][:, 2] * 1.0
    cv.chain(a, a + (b - a) * upto, B.r_neck * 1.1 + infl, B.r_neck * 0.95 + infl, mat, part)


# ----------------------------------------------------------------------------------------------- short hair kinds
def hair_extra(cv, B, J, st, mat='hair'):
    """volume pieces on top of the cap for the short styles: curly (Leonard), bowl (Howard), side (Raj), neat (Sheldon)"""
    Mh = J['Mh']; hR, hF, hU = Mh[:, 0], Mh[:, 1], Mh[:, 2]; c = J['head_c']; w, d, h = B.head['w'], B.head['d'], B.head['h']
    kind = st.get('kind'); vol = st.get('vol', 1.0)
    if kind == 'curly':
        for i, (a, e) in enumerate([(-60, 40), (-20, 55), (20, 55), (60, 40), (-90, 15), (90, 15), (-140, 30), (140, 30), (180, 45), (0, 70)]):
            ar, er = math.radians(a), math.radians(e)
            dirv = hR * (math.sin(ar) * math.cos(er)) + hF * (math.cos(ar) * math.cos(er) * 0.9) + hU * math.sin(er)
            p = c + hU * (0.10 * h) - hF * (0.05 * d) + dirv * (0.46 * h)
            cv.sphere(p, 2.2 * vol, mat, 'hair', tex=float(i % 3 == 1))
    elif kind == 'bowl':
        # straight fringe to the brows + sides over the ears + full back, like a helmet
        fr = c + hU * (0.22 * h) + hF * (0.36 * d)
        ell(cv, fr, (hR, hF, hU), (w * 0.47, 0.13 * d, 0.14 * h), mat, 'hair')
        for s, sg in SIDES:
            ell(cv, c + hR * (sg * w * 0.47) - hF * (0.06 * d) + hU * (0.02 * h), (hR, hF, hU), (0.10 * w + 0.6 * vol, 0.34 * d, 0.24 * h), mat, 'hair')
        ell(cv, c - hF * (0.30 * d) - hU * (0.02 * h), (hR, hF, hU), (w * 0.44, 0.22 * d, 0.30 * h), mat, 'hair')
    elif kind == 'side':
        part = st.get('part', 1)
        q = c + hU * (0.34 * h) + hF * (0.24 * d) + hR * (part * 0.10 * w)
        ell(cv, q, (hR, hF, hU), (w * 0.40, 0.22 * d, 0.13 * h), mat, 'hair', tex=lambda u: (np.sin(u[:, 0] * 9) > 0.7).astype(float))
    elif kind == 'neat':
        ell(cv, c + hU * (0.30 * h) + hF * (0.20 * d), (hR, hF, hU), (w * 0.42, 0.20 * d, 0.10 * h), mat, 'hair')
