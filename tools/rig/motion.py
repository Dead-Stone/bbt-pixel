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
             footR=(hx * 1.05, -0.08 * B.foot, 0.0), footL=(-hx * 1.05, -0.08 * B.foot, 0.0),
             armR=(-2.0, 7.0, 0.0, 15.0), armL=(-2.0, 7.0, 0.0, 15.0), lean=-0.5,
             wristR=-4.0, wristL=-4.0)   # upright: no forward lean, soft elbows, hands relaxed by the thighs
    # relaxed leg: knee eases forward, foot slightly ahead and out
    free = 'L' if sup == 'R' else 'R'; sg = 1 if free == 'R' else -1
    r, f, z = P['foot' + free]
    P['foot' + free] = (r + sg * 1.5 * aw, f + 4.0 * aw, z)
    P['knee_out' + free] = 0.25
    # pelvis height from the support leg: it stands straight (no soft-kneed crouch); the free knee eases
    r, f, z = P['foot' + sup]; sgs = 1 if sup == 'R' else -1
    L = (B.thigh + B.shin) * 0.995; dr = r - sgs * hx
    P['dz'] = math.sqrt(max(L * L - f * f - dr * dr, 1.0)) + B.ankle_h + z + 0.012 * B.H - B.hip_z
    return P


def idle(B, spec, k, n=8):
    ph = 2 * math.pi * k / n
    br = 0.5 - 0.5 * math.cos(ph)                         # in on 0..4, out 4..8
    w = 0.55 + 0.25 * math.sin(ph)                         # contrapposto on the right leg, easing
    P = stance(B, spec, w=w, breath=br)
    P['armR'] = (-2.0 + br, 7.0, 0, 15 + 2 * br); P['armL'] = (-1.5 - br, 7.0, 0, 16)
    # head level, chin a touch up; a small look-around on frames 5-6 keeps the idle alive
    # head level, chin a touch up.  Deliberate fidgets (meta.audit.fidget, skipped by the flicker check):
    # frames 5-6 a glance to the side, frame 7 a blink -- the looping idle never reads as a frozen stare
    look = (0, 0, 0, 0, 0, 8.0, 8.0, 0)[k % 8] if n == 8 else 0.0
    P['head_world'] = (look, 0.0, -1.5); P['swing'] = (0.0, 0.0); P['shrug'] = 0.0
    if n == 8 and k % 8 == 7: P['eyes'] = 'closed'
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
    P = dict( lean=0.25 * g.get('lean', 1.0) - 0.5,          # upright torso; character only nudges it
             pel_roll=-g.get('hip_roll', 4.0) * _ROLL[k], sway=g.get('sway', 1.2) * _SWAY[k],
             breath=0.3)
    cyc = 2 * math.pi * k / 8.0
    tw = g.get('twist', 5.0) * math.cos(cyc)               # +: right hip forward at frame 0
    P['pel_yaw'] = -tw; P['ch_yaw'] = tw; P['head_world'] = (0.0, 0.0, -2.0)   # head level, chin up a touch; hips twist, shoulders stay square to the path
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
        P['arm' + s] = (a, 7.0, 0.0, eb); P['wrist' + s] = 8.0
    # pelvis height from the legs: the lower of the two planted legs is ~straight (98%), 'down' sinks a bit more
    Lmax = (B.thigh + B.shin) * 0.985; hz = []
    for s in 'RL':
        r, f, z = P['foot' + s]
        if z < 2.5:
            dr = r - (1 if s == "R" else -1) * hx
            hz.append(math.sqrt(max(Lmax ** 2 - f ** 2 - dr ** 2, 1.0)) + B.ankle_h + z + 0.012 * B.H)
    P['dz'] = min(hz) - B.hip_z + (_BOB[k] if _BOB[k] < -2 else 0.0) * 0.4 * g.get('bob', 1.0)
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


def free(P):
    """emotes/talk turn the head relative to the neck (idle/walk keep it world-stabilised)"""
    P.pop('head_world', None); return P


def talk(B, spec, k, n=4):
    P = free(idle(B, spec, k * 2))
    P['mouth'] = ('open', 'closed', 'open', 'smile')[k % 4]
    P['head_pitch'] = (2.0, -1.0, 1.5, 0.0)[k % 4]; P['head_roll'] = (-2.0, 0.0, 1.5, 0.0)[k % 4]
    e = (55, 40, 62, 45)[k % 4]
    P['armR'] = (14.0, 8.0, -10.0, e); P['brow_up'] = (1, 0, 0, 0)[k % 4]
    return P


def gesture(B, spec, k, n=6):
    u = math.sin(math.pi * k / (n - 1)) if n > 1 else 0.0          # 0 -> 1 -> 0
    P = free(idle(B, spec, k))
    P['armR'] = (8 + 30 * u, 10 + 12 * u, -20 * u, 20 + 60 * u); P['wristR'] = -20 * u
    P['armL'] = (4 + 16 * u, 8 + 8 * u, 10 * u, 18 + 40 * u)
    P['head_roll'] = 3 * u; P['mouth'] = 'open' if k in (2, 3) else 'closed'; P['brow_up'] = 1 if 1 <= k <= 3 else 0
    return P


def hair_flip(B, spec, k, n=6):
    R0 = rest(B)
    seq = [(0, 0, 0), (-0.4, -10, 0.6), (-1.0, -16, 1.0), (0.6, 6, 0.6), (0.3, 3, 0.2), (0, 0, 0)]
    sw, roll, hand = seq[k]
    P = free(idle(B, spec, k))
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
    P = free(idle(B, spec, k))
    low = np.array([B.sh_x * 0.7, 18.0, R0['pel'][2] + 22.0])
    mouth = np.array([2.0, hc[1] + 10.0, hc[2] - 8.0])
    p = low + (mouth - low) * lift
    P['handR'] = tuple(p); P['elbow_poleR'] = (0.9, -0.2, -0.7); P['hand_dirR'] = (-0.5, 0.3, 0.8)
    P['head_pitch'] = -7.0 * (1.0 if k in (2, 3) else 0.0); P['eyes'] = 'closed' if k == 3 else 'open'
    P['props'] = [prop_wineglass('R')]
    return P


def eye_roll(B, spec, k, n=5):
    P = free(idle(B, spec, k))
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





# ----------------------------------------------------------------------------- helpers for reaching
def _lerp(a, b, t): return tuple(np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * t)


def _reach(P, s, R0, tgt, t, pole=None, hdir=None):
    """wrist IK target blended from the rest wrist (t=0) to tgt (t=1), body frame (r, f, z)"""
    if t <= 0: return P
    P['hand' + s] = _lerp(R0['wr' + s], tgt, t)
    if pole is not None: P['elbow_pole' + s] = pole
    if hdir is not None: P['hand_dir' + s] = hdir
    return P


def _point(R0, B, s, dirv, frac=0.96):
    d = np.asarray(dirv, float); d = d / np.linalg.norm(d)
    return tuple(R0['sh' + s] + d * (B.upper + B.fore) * frac), tuple(d)


# ----------------------------------------------------------------------------- props
def prop_pipette(s='R'):
    def f(cv, B, J):
        R, F, U = _W(J)
        g = J['wr' + s] + J['hd' + s] * (B.hand * 0.45)
        cv.chain(g + U * 4.5, g - U * 9.0, 0.9, 0.45, 'pipette', 'prop_pipette')
        cv.sphere(g + U * 5.4, 1.0, 'tip', 'prop_pipette')
    return f


def prop_tube(s='L'):
    def f(cv, B, J):
        R, F, U = _W(J)
        g = J['wr' + s] + J['hd' + s] * (B.hand * 0.45)
        cv.chain(g + U * 3.0, g - U * 3.5, 0.9, 0.7, 'tube', 'prop_tube')
    return f


def prop_card(s='R'):
    def f(cv, B, J):
        R, F, U = _W(J)
        g = J['tip' + s] + U * 1.5
        cv.ellipsoid(g, np.stack([R * 2.6, F * 0.4, U * 3.6], 1), 'card', 'prop_card')
    return f


def prop_marker(s='R'):
    def f(cv, B, J):
        g = J['wr' + s] + J['hd' + s] * (B.hand * 0.5)
        cv.chain(g - J['hd' + s] * 2.0, g + J['hd' + s] * 5.5, 0.7, 0.6, 'marker', 'prop_marker')
    return f


# ----------------------------------------------------------------------------- work loops
def work_whiteboard(B, spec, k, n=6):
    """writing on a board in front: right hand up at eye level tracing a line, left hand loose, weight on the
    left foot; the board itself is scene furniture at the work hook"""
    R0 = rest(B); ph = 2 * math.pi * k / n
    P = stance(B, spec, w=-0.4, breath=0.5 - 0.5 * math.cos(ph))
    sh = R0['shR']
    tgt = (sh[0] - 6.0 + 5.0 * math.sin(ph), 26.0, sh[2] - 2.0 + 2.5 * math.sin(2 * ph))
    P['handR'] = tgt; P['elbow_poleR'] = (0.7, -0.3, -0.7); P['hand_dirR'] = (-0.2, 1.0, 0.25)
    P['armL'] = (6.0, 6.0, 0.0, 34.0)
    P['head_pitch'] = -3.0; P['props'] = [prop_marker('R')]
    return P


def work_laptop(B, spec, k, n=6):
    """typing at a laptop on the bench (furniture): hands forward at hip height, alternate finger taps, head down"""
    R0 = rest(B)
    P = stance(B, spec, w=0.3, breath=0.5 - 0.5 * math.cos(2 * math.pi * k / n))
    z = R0['pel'][2] + 14.0
    for s, sg, ph in (('R', 1, 0), ('L', -1, 1)):
        tap = 1.2 if (k + ph) % 2 == 0 else 0.0
        P['hand' + s] = (sg * 6.0, 26.0, z - tap); P['elbow_pole' + s] = (sg * 0.5, -0.6, -0.6)
        P['hand_dir' + s] = (-sg * 0.25, 1.0, -0.35)
    P['lean'] = P.get('lean', 0) + 6.0; P['head_pitch'] = 14.0
    return P


def work_pipette(B, spec, k, n=6):
    """pipetting: tube in the left hand, pipette upright in the right; the plunger presses on frames 2-3"""
    R0 = rest(B)
    P = stance(B, spec, w=0.4, breath=0.5 - 0.5 * math.cos(2 * math.pi * k / n))
    press = (0, 0.5, 1.0, 1.0, 0.4, 0)[k % 6]
    zc = R0['sh' + 'R'][2] - 18.0
    P['handR'] = (4.0, 22.0, zc + 3.0 - 1.2 * press); P['elbow_poleR'] = (0.7, -0.5, -0.6); P['hand_dirR'] = (-0.6, 0.6, 0.2)
    P['handL'] = (-3.0, 21.0, zc - 7.0); P['elbow_poleL'] = (-0.7, -0.5, -0.6); P['hand_dirL'] = (0.6, 0.6, 0.2)
    P['fistR'] = True; P['fistL'] = True
    P['head_pitch'] = 12.0; P['lean'] = P.get('lean', 0) + 3.0
    P['props'] = [prop_pipette('R'), prop_tube('L')]
    return P


def work_microscope(B, spec, k, n=6):
    """bent over a bench microscope (furniture): leaning in, head down to the eyepiece, hands on the focus knobs"""
    R0 = rest(B)
    P = stance(B, spec, w=0.2, breath=0.5 - 0.5 * math.cos(2 * math.pi * k / n))
    z = R0['pel'][2] + 16.0; turn = (0, 1, 1, 0, -1, -1)[k % 6] * 0.8
    for s, sg in (('R', 1), ('L', -1)):
        P['hand' + s] = (sg * 9.0, 25.0, z + sg * turn); P['elbow_pole' + s] = (sg * 0.8, -0.4, -0.5)
        P['hand_dir' + s] = (-sg * 0.6, 0.8, 0.0)
    P['lean'] = P.get('lean', 0) + 16.0; P['head_pitch'] = 18.0
    return P


# ----------------------------------------------------------------------------- signature emotes
def glasses_push(B, spec, k, n=4):
    R0 = rest(B); hc = R0['head_c']
    t = (0.0, 0.6, 1.0, 0.5)[k]
    P = free(idle(B, spec, k))
    tgt = (hc[0] - 0.5, hc[1] + B.head['d'] * 0.55 + 3.0, hc[2] - B.hand * 0.75)
    _reach(P, 'R', R0, tgt, t, pole=(0.9, -0.2, -0.6), hdir=(-0.1, -0.15, 1.0))
    P['head_pitch'] = 2.0 * t; P['brow_in'] = k == 2
    return P


def sigh_shrug(B, spec, k, n=6):
    R0 = rest(B)
    u = (0.0, 0.5, 1.0, 1.0, 0.5, 0.0)[k]
    P = free(idle(B, spec, k))
    P['shrug'] = 2.6 * u
    for s, sg in (('R', 1), ('L', -1)):
        tgt = (sg * (B.sh_x + 5.0), 15.0, R0['pel'][2] + 13.0)
        _reach(P, s, R0, tgt, u, pole=(sg * 0.3, -0.6, -1.0), hdir=(sg * 0.7, 0.6, 0.1))
    P['head_roll'] = 5.0 * u; P['head_pitch'] = -3.0 * u
    P['eyes'] = ('open', 'half', 'open', 'open', 'open', 'open')[k]; P['brow_up'] = 1 if k in (2, 3) else 0
    return P


def point_gotcha(B, spec, k, n=5):
    R0 = rest(B); u = (0.0, 0.6, 1.0, 1.0, 0.4)[k]
    P = free(idle(B, spec, k))
    tgt, d = _point(R0, B, 'R', (0.15, 1.0, 0.35))
    _reach(P, 'R', R0, tgt, u, pole=(0.6, -0.4, -0.8), hdir=d)
    P['fistR'] = u > 0.5; P['mouth'] = 'open' if k in (2, 3) else 'closed'; P['brow_up'] = 1 if k in (2, 3) else 0
    P['lean'] = P.get('lean', 0) - 2.0 * u
    return P


def spot_claim(B, spec, k, n=5):
    R0 = rest(B); u = (0.0, 0.6, 1.0, 1.0, 0.5)[k]
    P = free(idle(B, spec, k))
    tgt, d = _point(R0, B, 'R', (0.45, 0.85, -0.55))
    _reach(P, 'R', R0, tgt, u, pole=(0.8, -0.4, -0.4), hdir=d)
    P['fistR'] = u > 0.5; P['head_pitch'] = 9.0 * u; P['head_yaw'] = 8.0 * u
    P['mouth'] = 'open' if k == 2 else 'closed'
    return P


KNOCK_SEQ = ['UP', 'A'] + ['K', 'A', 'K', 'A', 'K', 'H'] * 3 + ['R1', 'R2', 'R3', 'R4']


def knock_knock_penny(B, spec, k, d='SW'):
    """three knocks + 'Penny' x3: fist at head height on the door in front; on the hold the head turns to camera"""
    R0 = rest(B); st = KNOCK_SEQ[k]
    P = free(idle(B, spec, 0))
    s = 'L' if d in ('NW', 'NE') else 'R'; sg = 1 if s == 'R' else -1
    sh = R0['sh' + s]
    A = (sg * B.sh_x * 0.35, 30.0, sh[2] + 3.0); K = (A[0], A[1] + 4.0, A[2])
    if st == 'UP': t, tg = 0.55, A
    elif st in ('A', 'H'): t, tg = 1.0, A
    elif st == 'K': t, tg = 1.0, K
    else: t, tg = 1.0 - int(st[1]) / 4.0, A
    _reach(P, s, R0, tg, t, pole=(sg * 0.8, -0.3, -0.7), hdir=(0.0, 0.45, 0.9))
    P['fist' + s] = True
    if st == 'H': P['head_yaw'] = 30.0 * (1 if d in ('SW', 'NW') else -1); P['mouth'] = 'open'
    return P


def eyebrow_waggle(B, spec, k, n=4):
    P = free(idle(B, spec, k))
    P['brow_up'] = (1, 0, 1, 0)[k]; P['mouth'] = 'smile'; P['head_roll'] = (3.0, 1.0, 3.0, 1.0)[k]
    P['look'] = (1, 0); P['head_pitch'] = 3.0
    return P


def magic_trick(B, spec, k, n=6):
    R0 = rest(B); z = R0['sh' + 'R'][2] - 16.0
    P = free(idle(B, spec, k))
    seq = [(0.0, 0.0), (1.0, 0.0), (1.0, 0.5), (0.4, 1.0), (0.0, 1.0), (0.0, 0.3)]   # together, flourish
    tog, fl = seq[k]
    for s, sg in (('R', 1), ('L', -1)):
        close = (sg * 2.0, 20.0, z)
        open_ = (sg * (B.sh_x + 10.0), 16.0, z + (14.0 if s == 'R' else 2.0))
        tgt = _lerp(close, open_, fl) if fl > 0 else close
        _reach(P, s, R0, tgt, max(tog, fl), pole=(sg * 0.6, -0.6, -0.6), hdir=(-sg * 0.3 + sg * fl, 0.8, 0.2 + 0.6 * fl))
    if k in (3, 4): P['props'] = [prop_card('R')]
    P['mouth'] = 'smile' if k >= 3 else 'closed'; P['brow_up'] = 1 if k in (3, 4) else 0
    return P


def astronomy_point(B, spec, k, n=4):
    R0 = rest(B); u = (0.5, 1.0, 1.0, 1.0)[k]
    P = free(idle(B, spec, k))
    tgt, d = _point(R0, B, 'L', (-0.3, 0.45, 0.85))
    _reach(P, 'L', R0, tgt, u, pole=(-0.6, -0.3, -0.5), hdir=d)
    P['fistL'] = True; P['head_pitch'] = -12.0 * u; P['mouth'] = 'open' if k == 2 else 'smile'; P['brow_up'] = 1
    return P


def shy_hands(B, spec, k, n=5):
    R0 = rest(B); hc = R0['head_c']; u = (0.4, 1.0, 1.0, 1.0, 0.5)[k]
    P = free(idle(B, spec, k))
    for s, sg in (('R', 1), ('L', -1)):
        tgt = (sg * 1.5, hc[1] + 12.0, hc[2] - B.head['h'] * 0.75 - B.hand * 0.6)
        _reach(P, s, R0, tgt, u, pole=(sg * 0.7, -0.5, -0.6), hdir=(-sg * 0.2, 0.3, 1.0))
    P['shrug'] = 1.6 * u; P['head_pitch'] = 9.0 * u; P['head_yaw'] = -10.0 * u
    P['eyes'] = ('open', 'half', 'closed', 'half', 'open')[k]; P['mouth'] = 'smile'
    return P


def sweet_to_scary(B, spec, k, n=6):
    R0 = rest(B); P = free(idle(B, spec, k))
    if k < 3:
        for s, sg in (('R', 1), ('L', -1)):
            _reach(P, s, R0, (sg * 1.5, 14.0, R0['pel'][2] + 6.0), 1.0, pole=(sg * 0.8, -0.3, -0.6), hdir=(-sg * 0.6, 0.6, -0.4))
        P['head_roll'] = 7.0; P['mouth'] = 'smile'; P['brow_up'] = 1
    else:
        for s, sg in (('R', 1), ('L', -1)):
            _reach(P, s, R0, (sg * (B.sh_x + 3.0), 8.0, R0['pel'][2] + 18.0), 1.0, pole=(sg * 0.9, -0.6, -0.2), hdir=(0, 0.6, 0.8))
            P['fist' + s] = True
        P['lean'] = P.get('lean', 0) + 9.0; P['head_pitch'] = -4.0; P['brow_in'] = True; P['mouth'] = 'open'
        P['shrug'] = 1.0
    return P


def hands_on_hips(B, spec, k, n=4):
    R0 = rest(B); u = (0.5, 1.0, 1.0, 1.0)[k]
    P = free(idle(B, spec, k))
    for s, sg in (('R', 1), ('L', -1)):
        tgt = (sg * (B.pelvis['w'] + 3.5), -1.0, R0['pel'][2] + 4.0)
        _reach(P, s, R0, tgt, u, pole=(sg * 1.0, -0.4, 0.0), hdir=(-sg * 0.5, 0.6, -0.6))
        P['fist' + s] = True
    P['head_roll'] = (0, 4.0, -3.0, 4.0)[k]; P['brow_in'] = k >= 1; P['mouth'] = 'closed'
    return P


def neuro_lecture(B, spec, k, n=6):
    R0 = rest(B); sh = R0['shR']
    P = free(idle(B, spec, k))
    up = (0.5, 1.0, 1.0, 1.0, 1.0, 0.6)[k]
    _reach(P, 'R', R0, (sh[0] + 3.0, 14.0, sh[2] + 2.0 + (1.5 if k % 2 else 0.0)), up, pole=(0.9, -0.2, -0.8), hdir=(0.0, 0.2, 1.0))
    _reach(P, 'L', R0, (-2.0, 12.0, sh[2] - 22.0), 1.0, pole=(-0.8, -0.4, -0.6), hdir=(0.7, 0.4, 0.3))
    P['mouth'] = ('open', 'closed', 'open', 'open', 'closed', 'open')[k]; P['head_pitch'] = (0, 2, -1, 2, 0, 1)[k]
    P['head_roll'] = (0, -2, 0, -2, 0, 0)[k]; P['brow_up'] = 1 if k in (1, 3) else 0
    return P


def excited_clap(B, spec, k, n=6):
    R0 = rest(B); z = R0['shR'][2] - 14.0
    s_ = (0, 1, 2, 1, 2, 0)[k]
    P = free(idle(B, spec, k))
    if s_:
        g = 4.0 if s_ == 1 else 0.6
        for s, sg in (('R', 1), ('L', -1)):
            _reach(P, s, R0, (sg * g, 18.0, z), 1.0, pole=(sg * 0.8, -0.5, -0.5), hdir=(-sg * 0.9, 0.3, 0.4))
        P['shrug'] = 1.0 if s_ == 2 else 0.4
    P['mouth'] = 'smile'; P['brow_up'] = 1 if s_ else 0
    return P


WORK = dict(tray=work_tray, whiteboard=work_whiteboard, laptop=work_laptop, pipette=work_pipette, microscope=work_microscope)
EMOTE = dict(gesture=gesture, hair_flip=hair_flip, wine_sip=wine_sip, eye_roll=eye_roll, glasses_push=glasses_push,
             sigh_shrug=sigh_shrug, point_gotcha=point_gotcha, spot_claim=spot_claim, eyebrow_waggle=eyebrow_waggle,
             magic_trick=magic_trick, astronomy_point=astronomy_point, shy_hands=shy_hands, sweet_to_scary=sweet_to_scary,
             hands_on_hips=hands_on_hips, neuro_lecture=neuro_lecture, excited_clap=excited_clap)
