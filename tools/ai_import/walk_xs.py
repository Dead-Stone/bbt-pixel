"""CROSS / STRAIGHT walk: re-sequence each character's walk into a clean 4-pose alternation per direction
   X (stride, one leg forward) -> | (legs straight, together under the body) -> X (stride, other leg forward) -> |

Mohan: "It should be cross leg, straight and cross leg." The drawn 8-frame walks (walk8.py) draw frames 1/3/5/7 almost as
wide as the contact frames, so the 8-frame loop read X X | X X X | X (mostly crossed). This tool keeps the drawn art:

  CROSS    the widest drawn frame of each half cycle (side / 3-4 views: foot-band spread, full._spread; front / back S, N:
           walk_cycle.lift = 3 x foot height difference + foot width), the two picked half a cycle apart (other leg)
  STRAIGHT the narrowest drawn frame between the two crosses if it is clearly straight (spread <= 0.55 x the cross spread
           and <= 1.25 x the idle stance spread); otherwise COMPOSITE: that frame's head / torso / arms on the
           character's standing legs (stand_<d>; walk_cycle.stand_legs, soles + hip centre aligned, pivot kept). S / N always
           composite (their drawn walks barely change foot spacing, so only the standing legs read as straight).
  bob      STRAIGHT: upper body +1 px (rise), CROSS: -1 px (dip) -> 2 px two-beat bob, low on contact, high on passing

Input : characters/<cid>/ai/chr_<cid>_walk8.png/.json (the drawn 8-frame walk; copied from chr_<cid>_walk.* the first time,
        i.e. right after walk8.py) + the standing pose (chr_<cid>.json stand_<d>: arms at the sides; idle_<d> clasps hands behind / in front, which would
        double the hands under a walking torso)
Output: characters/<cid>/ai/chr_<cid>_walk.png/.json, 8 dirs x 4 poses (X, |, X, |), NE/E/SE mirror NW/W/SW;
        meta.pass_poses = [1, 3] (walk starts / settles on STRAIGHT), walk_m_per_pose_dir = step / 2 (two poses per step,
        step = 4 x the walk8 per-frame metres), so with personas.speed = 2 x step the cadence is 2 steps/s

python3 tools/ai_import/walk_xs.py [cid ...]       (default: all 7; re-run walk8.py first to refresh chr_<cid>_walk8.*)
"""
import os, sys, json, shutil, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from build import DIRS, MIRROR, mirror
from full import _spread
import walk_cycle as WC
from walk_cycle import stand_legs, rise, lift
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


def cycle(d, W, idle, pal):
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
        else: ok = False                    # S / N: always the idle legs (drawn walks barely change)
        f = W[j] if ok else stand_legs(W[j], idle)
        return audit_fix(rise(f), pal), ('drawn' if ok else 'composite')
    (S1, m1), (S2, m2) = straight(P1), straight(P2)
    X1, X2 = audit_fix(dip(W[A]), pal), audit_fix(dip(W[B]), pal)
    poses = [X1, S1, X2, S2]
    info = dict(cross_from=[A, B], straight_from=[P1, P2], straight_mode=[m1, m2], metric='spread' if side else 'lift',
                drawn=sc, cross_spread=[int(_spread(X1)), int(_spread(X2))], straight_spread=[int(_spread(S1)), int(_spread(S2))],
                idle_spread=int(_spread(idle)), cross_lift=[int(lift(X1)), int(lift(X2))], straight_lift=[int(lift(S1)), int(lift(S2))],
                idle_lift=int(lift(idle)))
    info['ratio'] = round(np.mean(info['straight_spread']) / max(1, np.mean(info['cross_spread'])), 2)
    return poses, info


def build(cid):
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
            frames.append(dict(filename=f'walkxs_{d}_{k}_{"X|"[k % 2]}', frame=dict(x=(i % 8) * 128, y=(i // 8) * 128, w=128, h=128), duration=250))
        tg.append(dict(name=f'walk_{d}', **{'from': a, 'to': len(out) - 1}, direction='forward'))
    sheet = np.zeros((((len(out) + 7) // 8) * 128, 8 * 128, 4), np.uint8)
    for i, c in enumerate(out): sheet[(i // 8) * 128:(i // 8 + 1) * 128, (i % 8) * 128:(i % 8 + 1) * 128] = c
    Image.fromarray(sheet).save(os.path.join(od, f'chr_{cid}_walk.png'), optimize=True)
    m8 = wj['meta']; mpp8 = m8.get('walk_m_per_pose_dir') or {d: m8['walk_m_per_pose'] for d in DIRS}
    step = {d: round(4 * mpp8[d], 4) for d in DIRS}
    rows = {d: per[MIRROR.get(d, d)][1] for d in DIRS}
    meta = dict(app='bbt-pixel/tools/ai_import/walk_xs.py', image=f'chr_{cid}_walk.png', size=dict(w=sheet.shape[1], h=sheet.shape[0]),
                frameTags=tg, poses=['cross', 'straight', 'cross', 'straight'], pass_poses=[1, 3], pivot=[64, 116],
                frames_per_cycle={d: 4 for d in DIRS}, steps_per_cycle=2, step_m=step,
                walk_m_per_pose=round(step['W'] / 2, 4), walk_m_per_pose_dir={d: round(step[d] / 2, 4) for d in DIRS},
                walk_stride_px=m8.get('walk_stride_px'), rows=rows, source=f'chr_{cid}_walk8.png (walk8.py: {m8.get("source")})',
                note='X | X | per direction (module doc); NE/E/SE mirror NW/W/SW; persona speed = 2 x step -> 2 steps/s')
    json.dump(dict(frames=frames, meta=meta), open(cur_js, 'w'), indent=1)
    return meta


if __name__ == '__main__':
    for cid in (sys.argv[1:] or CH):
        m = build(cid)
        print(cid, 'step', m['step_m']['W'], 'm/pose', m['walk_m_per_pose'], '-> 2 steps/s at', round(2 * m['step_m']['W'], 2), 'm/s')
        for d in SRC:
            r = m['rows'][d]
            print(f"  {d:2} X{r['cross_from']} |{r['straight_from']} {r['straight_mode']}  X spread {r['cross_spread']} | spread {r['straight_spread']} "
                  f"idle {r['idle_spread']} ratio {r['ratio']}  lift X {r['cross_lift']} | {r['straight_lift']} idle {r['idle_lift']}")
