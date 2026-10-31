"""Compose one frame: solve the skeleton, draw every body part + clothing/hair/prop layer into the z-buffered canvas,
shade, outline, add face decals, clean up.  draw(cid, pose, d) -> palette-index image (128x128, -1 = empty)."""
import math
import numpy as np
import skeleton as SK
import parts as PT
from render import Canvas, shade, outline, finish, to_rgba
from palette import Palette
from cast import CAST, REAL_CM

_CACHE = {}
DIR_KEYS = ('footR', 'footL', 'hdR', 'hdL')        # unit directions, not points: never translated


def character(cid):
    if cid in _CACHE: return _CACHE[cid]
    spec = CAST[cid]; B = SK.Body(REAL_CM[cid], spec['body'])
    pal = Palette(spec['colors'])
    _CACHE[cid] = (spec, B, pal); return _CACHE[cid]


def draw_layers(cv, cid, spec, B, J, pose):
    far = PT.far_side(J)
    ft = lambda s: 1 if s == far else 0
    o = spec['outfit']; top = o.get('top'); pants = o.get('pants'); shoes = o.get('shoes')
    # --- skin body parts
    PT.head(cv, B, J); PT.neck(cv, B, J)
    PT.torso(cv, B, J); PT.pelvis(cv, B, J)
    for s, _ in PT.SIDES:
        PT.leg(cv, B, J, s, tone=ft(s)); PT.foot(cv, B, J, s, tone=ft(s))
        PT.arm(cv, B, J, s, t_fore=(0, 1), tone=ft(s)); PT.hand(cv, B, J, s, tone=ft(s), fist=pose.get('fist' + s, False))
    # --- clothing layers
    def shirt(top, infl, sl_infl):
        m = top['mat']
        if top.get('neck') == 'scoop':
            keep = lambda q: ~((q[:, 1] > 0.15) & (q[:, 2] > 0.66 + 0.9 * q[:, 0] ** 2))
            ktrap = lambda q: ~((q[:, 1] > -0.05) & (np.abs(q[:, 0]) < 0.55))
        elif top.get('neck') == 'crew':
            keep = lambda q: ~((q[:, 1] > 0.3) & (q[:, 2] > 0.80 + 0.6 * q[:, 0] ** 2)); ktrap = None
        else: keep = None; ktrap = None
        tex = 0.0
        if top.get('logo'):                    # chest emblem painted on the shirt surface (material <mat>_alt)
            lx, lz, lr = top['logo']
            tex = lambda q: np.where((q[:, 1] > 0.55) & ((q[:, 0] - lx) ** 2 + ((q[:, 2] - lz) * 1.2) ** 2 < lr * lr), 3.0, 0.0)
        masc = not spec.get('feminine')        # men's shirts hang straight from the chest and sit lower on the shoulder
        PT.torso(cv, B, J, mat=m, infl=infl, part=top.get('part', 'top'), keep_chest=keep, keep_trap=ktrap, tex=tex,
                 waist_infl=(infl + 0.7 * (B.chest['w'] - B.waist['w'])) if masc else None, sh_drop=(0.8 + infl * 0.6) if masc else 0.0)
        if top.get('neck') == 'turtle': PT.collar_neck(cv, B, J, top.get('collar_mat', m), upto=top.get('collar', 0.7))
        for s, _ in PT.SIDES:
            sl = top.get('sleeve', 1.0)
            if sl <= 1.0: PT.arm(cv, B, J, s, mat=m, infl=sl_infl, part='sleeve_', t_upper=(0, sl), tone=ft(s))
            else:
                PT.arm(cv, B, J, s, mat=m, infl=sl_infl + 0.2, part='sleeve_', t_upper=(0, 1), t_fore=(0, sl - 1.0), tone=ft(s))
    if o.get('under'): shirt(o['under'], 0.5, 0.45)
    if top: shirt(top, 0.7 if not o.get('under') else 1.0, 0.6 if not o.get('under') else 0.95)
    if o.get('vest'): PT.vest(cv, B, J, o['vest']['mat'])
    if o.get('jacket'):
        jk = o['jacket']
        PT.jacket(cv, B, J, jk['mat'], infl=jk.get('infl', 1.6), sleeve=jk.get('sleeve', 1.95), hood=jk.get('hood', False),
                  hem=jk.get('hem', 0.5), gap=jk.get('gap', 0.16), far=far)
    if o.get('tights'):
        for s, _ in PT.SIDES:
            PT.leg(cv, B, J, s, mat=o['tights'], infl=(0.25, 0.25), part='tights_', tone=ft(s))
    if o.get('skirt'):
        sk = o['skirt']; PT.skirt(cv, B, J, sk['mat'], length=sk.get('length', 0.8), flare=sk.get('flare', 1.0), dots=sk.get('dots', False))
    if pants:
        m = pants['mat']
        PT.pelvis(cv, B, J, mat=m, infl=0.8, part='pants')
        for s, _ in PT.SIDES:
            PT.leg(cv, B, J, s, mat=m, infl=(0.7, 0.7), part='pants_', tone=ft(s), flare=pants.get('flare', 0.0), upto=0.96)
    if shoes:
        m = shoes['mat']
        for s, _ in PT.SIDES:
            PT.foot(cv, B, J, s, mat=m, infl=0.6, part='shoe_', tone=ft(s), h=shoes.get('h', 1.0))
    if o.get('belt'): PT.belt(cv, B, J, o['belt'])
    # --- hair
    if spec.get('hair'):
        PT.hair(cv, B, J, spec['hair'], swing=pose.get('swing', (0.0, 0.0)))
        PT.hair_extra(cv, B, J, spec['hair'])
    # --- props
    for pr in pose.get('props', []): pr(cv, B, J)


def face(idx, cv, spec, pal, B, J, pose):
    """eyes / brows / mouth as pixel decals at the projected landmarks (only where the head surface is visible)"""
    L = PT.landmarks(B, J); R = pal.ramps
    hp = [i for i, p in enumerate(cv.parts) if p == 'head']
    if not hp: return idx, np.zeros_like(idx, bool)
    hp = hp[0]
    eyes = pose.get('eyes', 'open')
    look = pose.get('look', (0, 0))
    prot = np.zeros_like(idx, bool)
    def vis(x, y, dep, tol=2.6):
        return 0 <= x < 128 and 0 <= y < 128 and cv.part[y, x] == hp and abs(cv.z[y, x] - dep) < tol
    def put(x, y, col):
        if 0 <= x < 128 and 0 <= y < 128 and cv.part[y, x] == hp: idx[y, x] = col; prot[y, x] = True
    for s in ('R', 'L'):
        sx, sy, dep, fac = L['eye' + s]
        if fac < 0.15: continue
        x, y = int(sx), int(sy)
        if not vis(x, y, dep): continue
        x += look[0]
        if eyes == 'closed':
            put(x, y, R['lash'][1])
        elif eyes == 'half':
            put(x, y - 1, R['skin'][2]); put(x, y, R['lash'][1])
        else:
            # a 1px eye reads as a speck and the clean-up passes eat it: lash/upper lid + iris = a 2px-tall eye
            put(x, y - 1 + look[1], R['lash'][1] if spec.get('feminine') else R['eye'][3]); put(x, y + look[1], R['eye'][1])
            if eyes == 'up': put(x, y - 1, R['eye'][1]); put(x, y, R['skin'][1])
            if fac > 0.62 and spec.get('feminine'):          # outer lash in near-frontal views
                ox = x + (1 if (sx - project_x(J['head_c'])) > 0 else -1)
                if vis(ox, y - 1, dep, 3.5): put(ox, y - 1, R['lash'][1])
        bx, by, bdep, bf = L['brow' + s]
        if not spec.get('feminine'): by -= 1                  # men: brow one row higher, a skin row between brow and eye
        if bf > 0.2 and vis(int(bx), int(by), bdep, 3.0):
            put(int(bx), int(by) - pose.get('brow_up', 0), R['brow'][2])
            ox = int(bx) + (1 if (bx - project_x(J['head_c'])) > 0 else -1)
            if bf > 0.5: put(ox, int(by) - pose.get('brow_up', 0) + (1 if pose.get('brow_in') else 0), R['brow'][2])
    if spec.get('glasses'):
        glasses(put, vis, L, R, J)
    mx, my, mdep, mf = L['mouth']
    if mf > 0.15 and vis(int(mx), int(my), mdep, 3.0):
        x, y = int(mx), int(my)
        m = pose.get('mouth', 'closed')
        if m == 'open':
            put(x, y, R['lash'][1]); put(x, y + 1, R['lip'][2])
            if mf > 0.6: put(x - 1, y, R['lip'][2]); put(x + 1, y, R['lip'][2])
        elif m == 'smile':
            put(x, y, R['lip'][1]); put(x - 1, y - (0 if mf < 0.6 else 1), R['lip'][2]); put(x + 1, y - (0 if mf < 0.6 else 1), R['lip'][2])
        else:
            put(x, y, R['lip'][1])
            if mf > 0.6: put(x + (1 if mx - int(mx) > 0.5 else -1), y, R['lip'][1])
    return idx, prot


def project_x(p): return SK.project(p)[0]


def glasses(put, vis, L, R, J):
    """frames as pixel decals around the eye landmarks: a top bar over both eyes (+ bridge), rim sides, a lens glint
    on the inner pixel; in profile the near lens plus a temple arm running back towards the ear"""
    fr = R['frame'][1]; gl = R['skin'][0]
    cx = project_x(J['head_c'])
    seen = [(s, L['eye' + s]) for s in ('R', 'L') if L['eye' + s][3] >= 0.15 and vis(int(L['eye' + s][0]), int(L['eye' + s][1]), L['eye' + s][2])]
    for s, (sx, sy, dep, fac) in seen:
        x, y = int(sx), int(sy)
        out = 1 if sx > cx else -1
        put(x - 1, y - 1, fr); put(x + 1, y - 1, fr)
        put(x + out, y, fr)
        if fac > 0.5: put(x - out, y, gl)
        if len(seen) == 1:                                   # profile: temple arm towards the back of the head
            back = -1 if (L['nose'][0] > sx) else 1
            for i in range(1, 4): put(x + back * (1 + i), y - 1, fr)
    if len(seen) == 2:
        (xa, ya), (xb, yb) = sorted([(int(v[0]), int(v[1])) for _, v in seen])
        for x in range(xa + 2, xb - 1): put(x, min(ya, yb) - 1, fr)


def draw(cid, pose, d, raw=False):
    spec, B, pal = character(cid)
    src = SK.MIRROR.get(d, d); yaw = SK.YAW[src]
    J = SK.solve(B, pose, yaw)
    # snap the head to the pixel grid: an unrotated head that moves by whole pixels rasterises identically
    hx, hy, _ = SK.project(J['head_c'])
    v = SK.CAM_S * ((round(hx) - hx) / SK.K) - SK.CAM_U * ((round(hy) - hy) / SK.K)
    for k in list(J):                     # move the whole body (< half a pixel) so head and shoulders stay in register
        if isinstance(J[k], np.ndarray) and J[k].shape == (3,) and k not in DIR_KEYS: J[k] = J[k] + v
    cv = Canvas(); draw_layers(cv, cid, spec, B, J, pose); cv.fill_pinholes(); cv.fill_holes()
    idx, op = shade(cv, pal.ramps, None)
    idx = outline(idx, cv, pal.ramps)
    idx, prot = face(idx, cv, spec, pal, B, J, pose)
    if not raw: idx = finish(idx, pal.arr, protect=prot)
    if d in SK.MIRROR: idx = np.ascontiguousarray(np.roll(idx[:, ::-1], 1, axis=1))   # x -> 128-x keeps pivot x=64
    return idx, dict(J=J, cv=cv, B=B)
