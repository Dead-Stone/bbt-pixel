"""Pose generators: every animation frame is a skeleton pose (dict of joint params, see skeleton.solve).
Walk follows the classic 8-frame cycle  contact / down / passing / up  x2  (Williams; pixeli walk rules):
  * stride: in-place, feet locked to the viewer's ground speed (0.14 world units per frame -> 1.12 per cycle)
  * pelvis bob: lowest on 'down', highest on 'passing'; hip roll drops the swing-leg side; weight sways
    over the support foot; pelvis twists with the forward leg and the chest counter-twists
  * arms swing opposite the legs, widest at contact, elbows bend more on the forward swing
  * heel strike with the toe up, toe-off with the heel up, swing foot clears the floor on 'passing'
Idle breathes (chest + shoulders rise) with a slow contrapposto weight shift.  Props are 3-D prims
drawn into the same z-buffer, so they occlude correctly in every direction."""
import math
import numpy as np
import skeleton as SK

CYCLE_M = 1.12          # metres per 8-frame walk cycle (viewer: frame = floor(walked / 0.14))


def rest(B):
    J = SK.solve(B, {}, 0.0)
    bf = lambda p: np.array([-p[0], -p[1], p[2]])        # yaw 0: R=-x, F=-y
    return {k: bf(v) for k, v in J.items() if isinstance(v, np.ndarray) and v.shape == (3,) and k not in ('W',)}


# ----------------------------------------------------------------------------- props
def _W(J): return J['W'][:, 0], J['W'][:, 1], J['W'][:, 2]

def prop_tray(s='R', glasses=2):
    def f(cv, B, J):
        R, F, U = _W(J)
        c = J['wr' + s] + U * (B.hand * 0.55 + 1.2) + F * 2.0
        cv.ellipsoid(c, np.stack([R * 13.5, F * 13.5, U * 0.9], 1), 'tray', 'prop_tray')
        for k, (dr, df, wine) in enumerate([(-4.5, 3.0, True), (4.0, -2.5, False), (0.5, 7.0, True)][:glasses]):
            b = c + R * dr + F * df + U * 0.9
            cv.chain(b, b + U * 3.0, 0.5, 0.5, 'glass', 'prop_glass%d' % k)
            cv.sphere(b + U * 5.4, 2.4, 'glass', 'prop_glass%d' % k)
            if wine: cv.sphere(b + U * 4.6, 1.9, 'wine', 'prop_wine%d' % k)
    return f

def prop_wineglass(s='R'):
    def f(cv, B, J):
        R, F, U = _W(J)
        base = J['wr' + s] + J['hd' + s] * (B.hand * 0.55) + U * 0.5
        cv.chain(base, base + U * 3.4, 0.45, 0.45, 'glass', 'prop_glass')
        cv.sphere(base + U * 5.8, 2.5, 'glass', 'prop_glass')
        cv.sphere(base + U * 5.0, 2.0, 'wine', 'prop_wine')
    return f


# ----------------------------------------------------------------------------- base stance
def stance(B, spec, w=0.0, breath=0.0):
    """relaxed standing; w = weight shift (-1 left .. +1 right)."""
    g = spec.get('gait', {})
    hx = B.hip_x
    sup = 'R' if w >= 0 else 'L'; aw = abs(w)
    P = dict(breath=breath, shrug=0.45 * breath, sway=1.4 * w, pel_roll=-3.0 * w,
             ch_roll=2.0 * w, head_roll=-1.0 * w,
             footR=(hx * 1.05, -0.26 * B.foot, 0.0), footL=(-hx * 1.05, -0.26 * B.foot, 0.0),
             armR=(2.0, 5.0, 0.0, 12.0), armL=(2.0, 5.0, 0.0, 12.0), lean=g.get('lean', 0.0))
    # relaxed leg: knee eases forward, foot slightly ahead and out
    free = 'L' if sup == 'R' else 'R'; sg = 1 if free == 'R' else -1
    r, f, z = P['foot' + free]
    P['foot' + free] = (r + sg * 1.5 * aw, f + 4.0 * aw, z)
    P['knee_out' + free] = 0.25
    return P


def idle(B, spec, k, n=8):
    ph = 2 * math.pi * k / n
    br = 0.5 - 0.5 * math.cos(ph)                         # in on 0..4, out 4..8
    w = 0.55 + 0.25 * math.sin(ph)                         # contrapposto on the right leg, easing
    P = stance(B, spec, w=w, breath=br)
    P['armR'] = (2.0 + br, 5.0, 0, 12 + br); P['armL'] = (2.5 - br, 5.0, 0, 13)
    P['head_world'] = (0.0, -1.5, 0.0); P['swing'] = (0.0, 0.0); P['shrug'] = 0.0
    return P


def blink(B, spec, k):
    P = idle(B, spec, 0); P['eyes'] = ('half', 'closed', 'half')[k]
    return P


# ----------------------------------------------------------------------------- walk
#            contact  down   pass    up   | contact down  pass   up      (leg R leads at frame 0)
_F = np.array([1.00, 0.62, 0.00, -0.55, -1.00, -0.62, -0.08, 0.60])   # foot fore/aft  (x half-step)
_LIFT = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 5.0, 9.5, 4.0])            # swing-foot clearance (cm)
_PITCH = np.array([16.0, 2.0, 0.0, -6.0, -26.0, -22.0, -4.0, 12.0])    # + toe up (heel strike), - heel up (toe off)
_BOB = np.array([-1.4, -3.0, 0.4, -0.2, -1.4, -3.0, 0.4, -0.2])       # pelvis height (cm)
_ROLL = np.array([0.2, 1.0, 0.7, 0.3, -0.2, -1.0, -0.7, -0.3])        # hip drop of the swing side
_SWAY = np.array([0.2, 0.8, 1.0, 0.6, -0.2, -0.8, -1.0, -0.6])        # weight over the support foot


def walk(B, spec, k):
    g = spec.get('gait', {}); hx = B.hip_x
    half = CYCLE_M * 100 / 4.0                              # one step = half a cycle; foot travels +-half/... per step
    A = half                                                # foot excursion from under the hip (step = 2A)
    P = dict( lean=g.get('lean', 1.0) + 1.0,
             pel_roll=-g.get('hip_roll', 4.0) * _ROLL[k], sway=g.get('sway', 1.2) * _SWAY[k],
             breath=0.3)
    cyc = 2 * math.pi * k / 8.0
    tw = g.get('twist', 5.0) * math.cos(cyc)               # +: right hip forward at frame 0
    P['pel_yaw'] = -tw; P['ch_yaw'] = tw; P['head_world'] = (0.0, 0.0, 2.0)   # hips twist, shoulders stay square to the path
    P['ch_roll'] = -P['pel_roll']                          # shoulders stay level while the hips drop (counter-tilt)
    toe_len = B.foot * 0.78; heel_len = B.foot * 0.22
    for s, sg, off in (('R', 1, 0), ('L', -1, 4)):
        i = (k + off) % 8
        f = A * _F[i]; pitch = _PITCH[i]
        lift = _LIFT[i]
        if pitch < 0: lift += toe_len * math.sin(math.radians(-pitch)) * 0.9      # toe stays on the floor
        elif pitch > 0: lift += heel_len * math.sin(math.radians(pitch))          # heel pivot
        P['foot' + s] = (sg * hx * 0.92, f - 0.26 * B.foot, lift)
        P['foot_pitch' + s] = pitch
        P['knee_out' + s] = 0.05
        # arm of the same side swings opposite to this leg; widest at contact
        a = -g.get('arm', 22.0) * math.cos(2 * math.pi * i / 8.0 - 0.25)
        eb = g.get('elbow', 14.0) + max(a, 0) * 0.35
        P['arm' + s] = (a, 5.0, 0.0, eb)
    # pelvis height from the legs: the lower of the two planted legs is ~straight (98%), 'down' sinks a bit more
    Lmax = (B.thigh + B.shin) * 0.985; hz = []
    for s in 'RL':
        r, f, z = P['foot' + s]
        if z < 2.5:
            dr = r - (1 if s == "R" else -1) * hx
            hz.append(math.sqrt(max(Lmax ** 2 - f ** 2 - dr ** 2, 1.0)) + B.ankle_h + z + 0.012 * B.H)
    P['dz'] = min(hz) - B.hip_z + (_BOB[k] if _BOB[k] < -2 else 0.0) * 0.6 * g.get('bob', 1.0)
    P['swing'] = (0.0, 0.0)
    return P


# ----------------------------------------------------------------------------- work / talk / gestures
def work_tray(B, spec, k, n=6):
    """carrying a drinks tray on the right hand at shoulder height; left hand sets a glass down and back."""
    R0 = rest(B); sh = R0['shR']
    ph = 2 * math.pi * k / n; br = 0.5 - 0.5 * math.cos(ph)
    P = stance(B, spec, w=0.45, breath=br)
    P['handR'] = (sh[0] + 1.0, 24.0, sh[2] - 6.0 + 0.6 * math.sin(ph)); P['elbow_poleR'] = (0.35, -0.1, -1.0)
    P['hand_dirR'] = (-0.15, 0.55, 0.85)
    reach = 0.5 - 0.5 * math.cos(ph)                      # 0 -> 1 -> 0
    P['handL'] = (-B.sh_x * 0.45, 24.0 + 12.0 * reach, R0['pel'][2] + 22.0 - 6.0 * reach)
    P['elbow_poleL'] = (-0.3, -0.5, -1.0); P['hand_dirL'] = (0.1, 0.8, -0.5)
    P['lean'] = P.get('lean', 0) + 4.0 * reach; P['head_pitch'] = 5.0 * reach
    P['props'] = [prop_tray('R')]
    return P


def talk(B, spec, k, n=4):
    P = idle(B, spec, k * 2)
    P['mouth'] = ('open', 'closed', 'open', 'smile')[k % 4]
    P['head_pitch'] = (2.0, -1.0, 1.5, 0.0)[k % 4]; P['head_roll'] = (-2.0, 0.0, 1.5, 0.0)[k % 4]
    e = (55, 40, 62, 45)[k % 4]
    P['armR'] = (14.0, 8.0, -10.0, e); P['brow_up'] = (1, 0, 0, 0)[k % 4]
    return P


def gesture(B, spec, k, n=6):
    u = math.sin(math.pi * k / (n - 1)) if n > 1 else 0.0          # 0 -> 1 -> 0
    P = idle(B, spec, k)
    P['armR'] = (8 + 30 * u, 10 + 12 * u, -20 * u, 20 + 60 * u); P['wristR'] = -20 * u
    P['armL'] = (4 + 16 * u, 8 + 8 * u, 10 * u, 18 + 40 * u)
    P['head_roll'] = 3 * u; P['mouth'] = 'open' if k in (2, 3) else 'closed'; P['brow_up'] = 1 if 1 <= k <= 3 else 0
    return P


def hair_flip(B, spec, k, n=6):
    R0 = rest(B)
    seq = [(0, 0, 0), (-0.4, -10, 0.6), (-1.0, -16, 1.0), (0.6, 6, 0.6), (0.3, 3, 0.2), (0, 0, 0)]
    sw, roll, hand = seq[k]
    P = idle(B, spec, k)
    P['head_roll'] = roll; P['head_yaw'] = -roll * 0.4; P['ch_roll'] = roll * 0.2
    P['swing'] = (sw * 9.0, -2.0 * abs(sw))
    if hand > 0:
        hc = R0['head_c']
        tgt = np.array([hc[0] + 12.0, hc[1] + 1.0, hc[2] - 2.0])
        rest_w = R0['wrR']
        p = rest_w + (tgt - rest_w) * hand
        P['handR'] = tuple(p); P['elbow_poleR'] = (1.0, 0.3, 0.1); P['hand_dirR'] = (-0.5, 0.2, 0.8)
    P['mouth'] = 'smile' if k >= 3 else 'closed'
    return P


def wine_sip(B, spec, k, n=6):
    R0 = rest(B); hc = R0['head_c']
    lift = (0.0, 0.5, 1.0, 1.0, 0.5, 0.0)[k]
    P = idle(B, spec, k)
    low = np.array([B.sh_x * 0.7, 18.0, R0['pel'][2] + 22.0])
    mouth = np.array([2.0, hc[1] + 10.0, hc[2] - 8.0])
    p = low + (mouth - low) * lift
    P['handR'] = tuple(p); P['elbow_poleR'] = (0.9, -0.2, -0.7); P['hand_dirR'] = (-0.5, 0.3, 0.8)
    P['head_pitch'] = -7.0 * (1.0 if k in (2, 3) else 0.0); P['eyes'] = 'closed' if k == 3 else 'open'
    P['props'] = [prop_wineglass('R')]
    return P


def eye_roll(B, spec, k, n=5):
    P = idle(B, spec, k)
    P['eyes'] = ('open', 'up', 'up', 'open', 'open')[k]
    P['head_roll'] = (0, -4, -6, -3, 0)[k]; P['head_pitch'] = (0, -3, -4, 0, 2)[k]
    P['shrug'] = (0, 0.8, 1.2, 0.2, -0.4)[k]; P['brow_up'] = (0, 1, 1, 0, 0)[k]
    P['mouth'] = 'closed'
    return P


# ----------------------------------------------------------------------------- sit
def sit(B, spec):
    """seated on a chair/sofa: seat height ~ knee height, thighs level, feet flat, hands on the lap."""
    seat = 0.255 * B.H
    pz = seat + B.pelvis['h'] * 0.55
    P = dict(pel_z=pz, pel_f=0.0, pel_pitch=-6.0, lean=4.0, breath=0.3,
             footR=(B.hip_x * 1.1, B.thigh * 0.95, 0.0), footL=(-B.hip_x * 1.1, B.thigh * 0.92, 0.0),
             foot_yawR=8.0, foot_yawL=-8.0, knee_outR=0.05, knee_outL=0.05)
    lap = pz - B.pelvis['h'] * 0.2 + 6.0
    P['handR'] = (B.hip_x * 1.5, B.thigh * 0.72, lap + 2.0); P['handL'] = (-B.hip_x * 1.5, B.thigh * 0.66, lap + 2.0)
    P['elbow_poleR'] = (0.6, -0.6, -0.4); P['elbow_poleL'] = (-0.6, -0.6, -0.4)
    P['hand_dirR'] = (-0.2, 1.0, -0.3); P['hand_dirL'] = (0.2, 1.0, -0.3)
    return P, seat


WORK = dict(tray=work_tray)
EMOTE = dict(gesture=gesture, hair_flip=hair_flip, wine_sip=wine_sip, eye_roll=eye_roll)
