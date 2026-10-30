"""Arm-proportion check (v2.1).  python3 armcheck.py <cid> [--json]

Measures the painted arm in the S idle pose from the rig anchors that paint_arm uses
(warped into the cutout's pixel space):
  upper = shoulder->elbow, fore = elbow->wrist, hand = wrist->fingertip  (px)
  tip_vs_midthigh = fingertip y - mid-thigh y   (target 0, |d| <= 3 px)
  elbow_vs_waist  = elbow y - waist y           (waist = torso/pelvis midpoint, |d| <= 3 px)
  upper/fore ratio in [0.9, 1.35]; hand 3..7 px.
Exit code 1 if any check fails."""
import sys, json, numpy as np
cid = sys.argv[1]
sys.argv = ['build_v2.py', cid]
import build_v2 as V, char_rig as R, build_char_sheet as BC
from cutout import anchors

def measure():
    c = V.cutout('S', 'open')
    P = R.build(BC.idle_pose(0)); A = anchors(P, 0)
    W = lambda p: None if p is None else np.asarray(c.warp(p), float)
    segs = []; leg = None; pel = tor = None; hand = None
    for k, p in enumerate(P):
        kind = p[3]; a = A[k]; g = p[1]
        if kind == 'pelvis' and pel is None: pel = W(a[1])
        elif kind == 'torso' and tor is None: tor = W(a[1])
        if not (isinstance(g, tuple) and len(g) > 1 and isinstance(g[1], np.ndarray) and np.ndim(g[0]) == 1):
            continue
        if g[0][0] <= 0: continue                      # character's right side (+x) only
        if kind == 'leg' and leg is None: leg = (W(a[1]), W(a[2]))
        if kind in ('arm', 'sleeve'): segs.append((np.asarray(g[0]), np.asarray(g[1]), W(a[1]), W(a[2])))
        if kind == 'hand': hand = (np.asarray(g[0]), W(a[1]), W(a[2]))
    sh = segs[0][2]
    fore = min(segs, key=lambda s: np.linalg.norm(s[1] - hand[0]))
    el, wr, tipp = fore[2], hand[1], hand[2]
    L = lambda a, b: float(np.hypot(*(b - a)))
    m = dict(upper=L(sh, el), fore=L(el, wr), hand=L(wr, tipp),
             tip_vs_midthigh=float(tipp[1] - (leg[0][1] + leg[1][1]) / 2),
             elbow_vs_waist=float(el[1] - (tor[1] + pel[1]) / 2))
    m['ratio'] = m['upper'] / m['fore']
    fails = []
    if abs(m['tip_vs_midthigh']) > 3: fails.append('fingertip not at mid-thigh')
    if abs(m['elbow_vs_waist']) > 3: fails.append('elbow not at waist')
    if not 0.9 <= m['ratio'] <= 1.35: fails.append('upper/fore ratio')
    if not 3 <= m['hand'] <= 7: fails.append('hand size')
    return {k: round(v, 1) if isinstance(v, float) else v for k, v in m.items()}, fails

if __name__ == '__main__':
    m, f = measure()
    print(cid, json.dumps(m), 'OK' if not f else 'FAIL: ' + ', '.join(f))
    sys.exit(1 if f else 0)
