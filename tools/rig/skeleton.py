"""Modular human rig: skeleton + forward/inverse kinematics.

World frame (cm): x = screen right, y = away from the camera (into the screen), z = up.  The camera is the
project's 2:1 dimetric camera (30 deg elevation, orthographic).  A character stands at the origin; `yaw` turns
it (0 = facing the camera = 'S', 90 = facing screen-left = 'W', 180 = 'N').

Body-local frame: R = the character's right, F = forward, U = up.  Every joint is computed from a pose dict
(joint angles in degrees, offsets in cm) by plain forward kinematics; legs/arms can instead be solved by a
2-bone IK towards a target (feet planted on the floor, hands on a tray / glass / lap).
Proportions are anthropometric fractions of standing height H (Drillis & Contini segment table, see
tools/rig/REFERENCES.md) with per-character multipliers (tools/rig/cast.py)."""
import math
import numpy as np

ELEV = math.radians(30.0)
PX_PER_CM_SCREEN = 100.0 / 185.0                  # on-screen standing height: 100 px == 185 cm (Sheldon)
K = PX_PER_CM_SCREEN / math.cos(ELEV)              # world cm -> px scale of the orthographic camera
PIVOT = (64, 116)
DIRS = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']
YAW = {'S': 0, 'SW': 45, 'W': 90, 'NW': 135, 'N': 180}
MIRROR = {'NE': 'NW', 'E': 'W', 'SE': 'SW'}


def unit(v):
    v = np.asarray(v, float); n = np.linalg.norm(v); return v / n if n > 1e-9 else v


def rot(axis, deg):
    """Rodrigues rotation matrix about `axis` by `deg` degrees (right-handed)."""
    a = unit(axis); t = math.radians(deg); c, s = math.cos(t), math.sin(t)
    x, y, z = a
    return np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                     [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                     [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]])


def frame_yaw(yaw_deg):
    """columns R, F, U of the body frame in world coords for a facing yaw"""
    y = math.radians(yaw_deg)
    R = np.array([-math.cos(y), math.sin(y), 0.0]); F = np.array([-math.sin(y), -math.cos(y), 0.0])
    return np.stack([R, F, np.array([0, 0, 1.0])], 1)


def project(p):
    """world point(s) (..., 3) -> screen x, y (px, float) and depth (cm, larger = farther)"""
    p = np.asarray(p, float)
    sx = PIVOT[0] + K * p[..., 0]
    sy = PIVOT[1] - K * (p[..., 2] * math.cos(ELEV) + p[..., 1] * math.sin(ELEV))
    d = p[..., 1] * math.cos(ELEV) - p[..., 2] * math.sin(ELEV)
    return sx, sy, d


# camera basis in world coords: screen-right, screen-up, toward viewer
CAM_S = np.array([1.0, 0, 0])
CAM_U = np.array([0, math.sin(ELEV), math.cos(ELEV)])
CAM_V = -np.array([0, math.cos(ELEV), -math.sin(ELEV)])


class Body:
    """Segment lengths / joint offsets (cm) for one character."""
    def __init__(self, H, m=None):
        m = m or {}
        g = lambda k, d=1.0: m.get(k, d)
        self.H = H
        self.head_k = g('head_k', 1.10)
        hh = 0.142 * H * self.head_k                         # chin -> crown (stylised ~1:6.3 head:height so faces have room)
        self.head = dict(w=0.092 * H * self.head_k * g('head_w', 1.0), d=0.110 * H * self.head_k, h=hh)
        self.hair_top = g('hair_top', 1.2)                     # hair thickness above the crown (cm)
        self.thigh = 0.245 * H * g('leg', 1.0)
        self.shin = 0.246 * H * g('leg', 1.0)
        self.ankle_h = 0.039 * H
        self.hip_z = self.ankle_h + self.thigh + self.shin
        self.hip_x = 0.052 * H * g('hip', 1.0)
        top = H - self.hair_top
        self.chin_z = top - hh
        self.neck_len = max(4.0, self.chin_z - 0.818 * H - 0.012 * H) * g('neck', 1.0)
        self.sh_z = self.chin_z - self.neck_len - 0.012 * H     # shoulder joints
        self.spine = self.sh_z - self.hip_z - 0.02 * H          # pelvis centre -> shoulder line (along spine)
        self.sh_x = 0.095 * H * g('sh', 1.0)
        self.upper = 0.190 * H * g('arm', 1.0)
        self.fore = 0.165 * H * g('arm', 1.0)
        self.hand = 0.068 * H * g('hand', 1.0)
        self.foot = 0.150 * H * g('foot', 1.0)
        # volumes (half sizes, cm)
        self.chest = dict(w=0.090 * H * g('tw', 1.0), d=0.060 * H * g('td', 1.0), h=0.085 * H)
        self.waist = dict(w=0.072 * H * g('waist', 1.0) * g('tw', 1.0), d=0.052 * H * g('td', 1.0))
        self.pelvis = dict(w=0.086 * H * g('hip', 1.0), d=0.062 * H * g('td', 1.0) ** 0.5, h=0.060 * H)
        self.bust = g('bust', 0.0)
        self.belly = g('belly', 0.0)
        self.limb = g('limb', 1.0); self.arm_k = g('arm_k', 1.0)
        self.r_thigh = (0.050 * H * self.limb, 0.034 * H * self.limb)
        self.r_shin = (0.033 * H * self.limb, 0.022 * H * self.limb)
        self.r_upper = (0.026 * H * self.arm_k, 0.021 * H * self.arm_k)
        self.r_fore = (0.021 * H * self.arm_k, 0.015 * H * self.arm_k)
        self.r_neck = 0.033 * H * g('neck_r', 1.0)
        self.slouch = g('slouch', 0.0); self.head_fwd = g('head_fwd', 0.0)


def ik2(a, b, la, lb, pole):
    """2-bone IK: root a, target b, lengths la/lb, bend towards `pole` direction. Returns mid joint, end."""
    d = b - a; L = np.linalg.norm(d)
    L = min(max(L, abs(la - lb) + 1e-3), la + lb - 1e-3)
    dirv = unit(d); end = a + dirv * L
    x = (la * la - lb * lb + L * L) / (2 * L); h = math.sqrt(max(la * la - x * x, 0))
    pv = pole - np.dot(pole, dirv) * dirv
    pv = unit(pv) if np.linalg.norm(pv) > 1e-6 else unit(np.cross(dirv, [0, 0, 1]))
    return a + dirv * x + pv * h, end


def solve(body, pose, yaw):
    """pose -> dict of world-space joints/frames.  See motion.py for the pose fields."""
    B = body; P = dict(pose)
    W = frame_yaw(yaw + P.get('turn', 0.0))
    Rw, Fw, Uw = W[:, 0], W[:, 1], W[:, 2]
    root = Rw * P.get('dx', 0.0) + Fw * P.get('dy', 0.0)
    # pelvis frame: twist (yaw about U), roll (hip drop, about F), pitch (tilt, about R)
    Mp = rot(Uw, P.get('pel_yaw', 0)) @ rot(Fw, P.get('pel_roll', 0)) @ rot(Rw, P.get('pel_pitch', 0)) @ W
    pel_c = root + Uw * (B.hip_z + P.get('dz', 0.0)) + Rw * P.get('sway', 0.0)
    if 'pel_z' in P: pel_c = root + Uw * P['pel_z'] + Rw * P.get('sway', 0.0) + Fw * P.get('pel_f', 0.0)
    pR, pF, pU = Mp[:, 0], Mp[:, 1], Mp[:, 2]
    J = dict(W=W, root=root, pel=pel_c, Mp=Mp)
    # spine: lean forward (pitch about R), side bend (roll), chest twist (yaw) relative to pelvis
    lean = P.get('lean', 0.0) + B.slouch * 4.0
    Mc = rot(pU, P.get('ch_yaw', 0)) @ rot(pF, P.get('ch_roll', 0)) @ rot(pR, -lean) @ Mp
    cR, cF, cU = Mc[:, 0], Mc[:, 1], Mc[:, 2]
    breath = P.get('breath', 0.0)
    sh_c = pel_c + cU * (B.spine + 0.02 * B.H + breath * 0.25) + cF * (-0.6)
    J.update(Mc=Mc, sh_c=sh_c, chest_c=pel_c + cU * (B.spine * 0.62 + breath * 0.2), waist_c=pel_c + cU * (B.spine * 0.25))
    J['breath'] = breath
    # neck + head
    neck0 = sh_c + cU * 0.5 + cF * (B.slouch * 0.8 - 0.4)   # neck rises from just behind the shoulder line
    Mn = rot(cR, -(P.get('neck_pitch', 0) + B.slouch * 6)) @ Mc
    neck1 = neck0 + Mn[:, 2] * B.neck_len + Mn[:, 1] * (B.head_fwd * 0.6)
    Mh = rot(Mn[:, 2], P.get('head_yaw', 0)) @ rot(Mn[:, 1], P.get('head_roll', 0)) @ rot(Mn[:, 0], -(P.get('head_pitch', 0) - B.slouch * 4)) @ Mn
    if 'head_world' in P:        # head orientation fixed in the world (gaze stabilisation; no sub-pixel head re-rasterising)
        hy, hr, hp = P['head_world']
        Mh = rot(Uw, hy) @ rot(Fw, hr) @ rot(Rw, -hp) @ W
    J.update(neck0=neck0, neck1=neck1, Mh=Mh)
    # shoulders (shrug lifts, protraction moves forward)
    for s, sg in (('R', 1), ('L', -1)):
        shr = P.get('shrug' + s, P.get('shrug', 0.0)); pro = P.get('protract' + s, 0.0)
        J['sh' + s] = sh_c + cR * (sg * B.sh_x) + cU * (shr - 0.007 * B.H) + cF * (pro + 0.3)   # relaxed: shoulders down, a touch rounded
    # hips
    for s, sg in (('R', 1), ('L', -1)):
        J['hip' + s] = pel_c + pR * (sg * B.hip_x) - pU * (0.012 * B.H)
    # legs: IK to foot targets (default: under the hip) or FK angles
    for s, sg in (('R', 1), ('L', -1)):
        hip = J['hip' + s]
        if ('foot' + s) in P:                     # target ankle position in body-root frame (r, f, z)
            r, f, z = P['foot' + s]
            tgt = root + Rw * r + Fw * f + Uw * (B.ankle_h + z)
            knee_pole = Fw * 1.0 + Rw * (sg * P.get('knee_out' + s, 0.08))
            knee, ank = ik2(hip, tgt, B.thigh, B.shin, knee_pole)
        else:
            fl, ab, kn = P.get('hip' + s, (0, 0, 0))
            Mt = rot(pR, fl) @ rot(pF, -sg * ab)
            d1 = Mt @ (-pU)
            knee = hip + d1 * B.thigh
            d2 = rot(Mt @ pR, -kn) @ d1
            ank = knee + d2 * B.shin
        J['knee' + s] = knee; J['ank' + s] = ank
        pitch = P.get('foot_pitch' + s, 0.0)                     # + = toe up
        fyaw = P.get('foot_yaw' + s, sg * 6.0)                   # slight toe-out
        fdir = rot(Uw, fyaw) @ Fw
        fdir = rot(np.cross(fdir, Uw), pitch) @ fdir
        J['foot' + s] = fdir
        J['toe' + s] = ank + fdir * (B.foot * 0.78) - Uw * (B.ankle_h * 0.6)
        J['heel' + s] = ank - fdir * (B.foot * 0.22) - Uw * (B.ankle_h * 0.7)
    # arms
    for s, sg in (('R', 1), ('L', -1)):
        sh = J['sh' + s]
        if ('hand' + s) in P:                     # IK target for the wrist, body frame (r, f, z) relative to root
            r, f, z = P['hand' + s]
            tgt = root + Rw * r + Fw * f + Uw * z
            pole = P.get('elbow_pole' + s, (sg * 0.6, -0.8, -0.4))
            pole = Rw * pole[0] + Fw * pole[1] + Uw * pole[2]
            el, wr = ik2(sh, tgt, B.upper, B.fore, pole)
        else:
            fl, ab, tw, eb = P.get('arm' + s, (0, 6, 0, 10))
            Ma = rot(cR, fl) @ rot(cF, -sg * ab)
            d1 = Ma @ (-cU)
            el = sh + d1 * B.upper
            hinge = rot(d1, sg * tw) @ (Ma @ cR)
            d2 = rot(hinge, -eb) @ d1 if True else d1
            # elbow flexion swings the forearm forward/up (towards F)
            if np.dot(d2 - d1, cF) < 0: d2 = rot(hinge, eb) @ d1
            wr = el + d2 * B.fore
        J['el' + s] = el; J['wr' + s] = wr
        fd = unit(wr - el)
        wf = P.get('wrist' + s, 0.0)
        side = unit(np.cross(fd, cU)) if abs(np.dot(fd, cU)) < 0.97 else cR
        hd = rot(side, wf) @ fd
        if ('hand_dir' + s) in P:
            r, f, z = P['hand_dir' + s]; hd = unit(Rw * r + Fw * f + Uw * z)
        J['hd' + s] = hd
        J['tip' + s] = wr + hd * B.hand
    J['head_c'] = neck1 + Mh[:, 2] * (B.head['h'] * 0.42) + Mh[:, 1] * (-0.02 * B.head['d'] + B.head_fwd)   # skull stacked on the spine
    J['chin'] = J['head_c'] - Mh[:, 2] * (B.head['h'] * 0.5) + Mh[:, 1] * (B.head['d'] * 0.32)
    return J
