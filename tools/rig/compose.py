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
    if top:
        m = top['mat']
        if top.get('neck') == 'scoop':
            keep = lambda q: ~((q[:, 1] > 0.15) & (q[:, 2] > 0.66 + 0.9 * q[:, 0] ** 2))
            ktrap = lambda q: ~((q[:, 1] > -0.05) & (np.abs(q[:, 0]) < 0.55))
        elif top.get('neck') == 'crew':
            keep = lambda q: ~((q[:, 1] > 0.3) & (q[:, 2] > 0.80 + 0.6 * q[:, 0] ** 2)); ktrap = None
        else: keep = None; ktrap = None
        PT.torso(cv, B, J, mat=m, infl=0.7, part='top', keep_chest=keep, keep_trap=ktrap)
        for s, _ in PT.SIDES:
            sl = top.get('sleeve', 1.0)
            if sl <= 1.0: PT.arm(cv, B, J, s, mat=m, infl=0.6, part='sleeve_', t_upper=(0, sl), tone=ft(s))
            else:
                PT.arm(cv, B, J, s, mat=m, infl=0.8, part='sleeve_', t_upper=(0, 1), t_fore=(0, sl - 1.0), tone=ft(s))
    if pants:
        m = pants['mat']
        PT.pelvis(cv, B, J, mat=m, infl=0.8, part='pants')
        for s, _ in PT.SIDES:
            PT.leg(cv, B, J, s, mat=m, infl=(0.7, 0.7), part='pants_', tone=ft(s), flare=pants.get('flare', 0.0), upto=0.96)
    if shoes:
        m = shoes['mat']
        for s, _ in PT.SIDES:
            PT.foot(cv, B, J, s, mat=m, infl=0.6, part='shoe_', tone=ft(s), h=shoes.get('h', 1.0))
    # --- hair
    if spec.get('hair'):
        PT.hair(cv, B, J, spec['hair'], swing=pose.get('swing', (0.0, 0.0)))
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
            put(x, y - 1 + look[1], R['lash'][1]); put(x, y + look[1], R['eye'][1])
            if eyes == 'up': put(x, y - 1, R['eye'][1]); put(x, y, R['skin'][1])
            if fac > 0.62 and spec.get('feminine'):          # outer lash in near-frontal views
                ox = x + (1 if (sx - project_x(J['head_c'])) > 0 else -1)
                if vis(ox, y - 1, dep, 3.5): put(ox, y - 1, R['lash'][1])
        bx, by, bdep, bf = L['brow' + s]
        if bf > 0.2 and vis(int(bx), int(by), bdep, 3.0):
            put(int(bx), int(by) - pose.get('brow_up', 0), R['brow'][2])
            ox = int(bx) + (1 if (bx - project_x(J['head_c'])) > 0 else -1)
            if bf > 0.5: put(ox, int(by) - pose.get('brow_up', 0) + (1 if pose.get('brow_in') else 0), R['brow'][2])
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


def draw(cid, pose, d, raw=False):
    spec, B, pal = character(cid)
    src = SK.MIRROR.get(d, d); yaw = SK.YAW[src]
    J = SK.solve(B, pose, yaw)
    # snap the head to the pixel grid: an unrotated head that moves by whole pixels rasterises identically
    hx, hy, _ = SK.project(J['head_c'])
    v = SK.CAM_S * ((round(hx) - hx) / SK.K) - SK.CAM_U * ((round(hy) - hy) / SK.K)
    for k in list(J):                     # move the whole body (< half a pixel) so head and shoulders stay in register
        if isinstance(J[k], np.ndarray) and J[k].shape == (3,): J[k] = J[k] + v
    cv = Canvas(); draw_layers(cv, cid, spec, B, J, pose)
    idx, op = shade(cv, pal.ramps, None)
    idx = outline(idx, cv, pal.ramps)
    idx, prot = face(idx, cv, spec, pal, B, J, pose)
    if not raw: idx = finish(idx, pal.arr, protect=prot)
    if d in SK.MIRROR: idx = np.ascontiguousarray(np.roll(idx[:, ::-1], 1, axis=1))   # x -> 128-x keeps pivot x=64
    return idx, dict(J=J, cv=cv, B=B)
