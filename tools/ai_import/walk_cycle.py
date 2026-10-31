"""4-pose walk cycle for the viewer: stride, PASS, stride, PASS (characters/<cid>/ai/chr_<cid>_walk.png/.json)

The ChatGPT walk rows (chr_<cid>.json walk_<d>, 8 frames) draw the legs apart in every frame ("all crosses"), so the
8-frame loop reads as a scissor glide. This tool keeps the art and re-sequences it per direction:

  pose 0  stride A   the widest-stride walk frame
  pose 1  PASS       the most legs-together walk frame between A and B; side / 3-4 views keep its head, torso and arms
                     and get the idle (standing) legs below the hip row (HIP = 0.42 of the body height up from the
                     soles, soles and leg centre aligned), then the upper body rises 1 px (the passing-pose bob)
  pose 2  stride B   the widest frame half a cycle (4 frames) from A -- the other leg in front
  pose 3  PASS       as pose 1, from the other half of the row

Front / back views (S, N) keep their least-lifted frame as PASS (legs already under the body), + the 1 px rise.
NE / E / SE mirror NW / W / SW (build.mirror, pivot column 64 kept). The viewer advances one pose per half step
(meta.walk_m_per_pose = stride / 2, world metres, side view 90.5 px per metre), so the planted foot stays put.

python3 tools/ai_import/walk_cycle.py [cid ...]       (run after full.py; default: all 7)
"""
import os, sys, json, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from build import DIRS, MIRROR, mirror
from full import _close_legs, _spread, _runs

CH = ['sheldon', 'leonard', 'penny', 'howard', 'raj', 'bernadette', 'amy']
SRC = ['S', 'SW', 'W', 'NW', 'N']


def load(cid):
    od = os.path.join(ROOT, 'characters', cid, 'ai')
    j = json.load(open(os.path.join(od, f'chr_{cid}.json'))); im = np.asarray(Image.open(os.path.join(od, f'chr_{cid}.png')).convert('RGBA'))
    tags = {t['name']: (t['from'], t['to']) for t in j['meta']['frameTags']}
    def row(name):
        a, b = tags[name]; out = []
        for k in range(a, b + 1):
            f = j['frames'][k]['frame']; out.append(im[f['y']:f['y'] + 128, f['x']:f['x'] + 128].copy())
        return out
    return j, row


def lift(f):
    """front/back views: height difference of the two feet (left / right half of the leg region)"""
    A = f[..., 3] > 0; ys = np.nonzero(A.any(1))[0]; yb, yt = ys[-1], ys[0]
    leg = A[int(yb - 0.3 * (yb - yt)):yb + 1]; xs = np.nonzero(leg.any(0))[0]; cx = int((xs[0] + xs[-1]) / 2)
    L = np.nonzero(A[:, :cx].any(1))[0][-1]; R = np.nonzero(A[:, cx:].any(1))[0][-1]
    return abs(int(L) - int(R)) * 3 + (xs[-1] - xs[0])


def crotch(f):
    """lowest row above the feet where the legs are one run (hip line); fallback 62 % down the figure"""
    A = f[..., 3] > 0; ys = np.nonzero(A.any(1))[0]; yb, yt = ys[-1], ys[0]; seen2 = False
    for y in range(yb, yt + int((yb - yt) * 0.55), -1):
        if len(_runs(A[y])) >= 2: seen2 = True
        elif seen2: return y
    return yt + int((yb - yt) * 0.62)


def rise(f, px=1):
    """passing pose: everything above the hip line moves up px rows (the legs, straight under the body, get px longer)"""
    A = f[..., 3] > 0; ys = np.nonzero(A.any(1))[0]; y = int(round(ys[-1] - HIP * (ys[-1] - ys[0])))
    out = f.copy(); out[:y - px + 1] = f[px:y + 1]; return out


def run_at(A, y):
    r = _runs(A[y]); return (r[0][0], r[-1][1]) if r else None


HIP = 0.42      # join row: this fraction of the figure height above the soles (just below the crotch)


def big_run(A, y):
    r = _runs(A[y]); return max(r, key=lambda q: q[1] - q[0]) if r else None


def stand_legs(f, idle):
    """passing pose: the walk frame above the hip line (same head / torso / arm swing) on the standing pose's legs
    (the idle neutral of the same direction) below it, joined at the leg run's centre; walk-frame pieces below the
    join that do not touch the legs (a swinging hand) are kept"""
    import scipy.ndimage as nd
    A = f[..., 3] > 0; Ai = idle[..., 3] > 0
    ys = np.nonzero(A.any(1))[0]; yb, yt = ys[-1], ys[0]; ybi = np.nonzero(Ai.any(1))[0][-1]
    y = int(round(yb - HIP * (yb - yt)))
    li = np.roll(idle, int(yb - ybi), axis=0); Li = li[..., 3] > 0
    rw, ri = big_run(A, y), big_run(Li, y)
    if not rw or not ri: return f
    dx = int(round((rw[0] + rw[1]) / 2 - (ri[0] + ri[1]) / 2))
    li = np.roll(li, dx, axis=1)
    out = f.copy(); out[y + 1:] = li[y + 1:]
    lab, n = nd.label(A[y + 1:])
    for k in range(1, n + 1):          # keep walk pieces below the join that are not the legs (hands)
        m = lab == k; yy, xx = np.nonzero(m)
        if yy.min() == 0 and xx.min() < rw[1] and xx.max() >= rw[0]: continue
        if m.sum() > 80: continue
        sub = out[y + 1:]; sub[m] = f[y + 1:][m]
    return out


def cycle(d, W, idle):
    side = d not in ('S', 'N')
    sc = [_spread(f) if side else lift(f) for f in W]
    A = int(np.argmax(sc)); B = max([(A + 4) % 8, (A + 3) % 8, (A + 5) % 8], key=lambda j: sc[j])
    h1 = [(A + i) % 8 for i in range(1, 4)]; h2 = [(B + i) % 8 for i in range(1, 4)]
    P1 = min(h1, key=lambda j: sc[j]); P2 = min(h2, key=lambda j: sc[j])
    sn = _spread(idle)
    def pas(j):
        f = W[j]
        if side: f = stand_legs(f, idle)
        return rise(f)
    return [W[A], pas(P1), W[B], pas(P2)], dict(stride=[A, B], pass_from=[P1, P2], spread=[int(_spread(x)) for x in (W[A], W[B])],
                                               pass_spread=[int(_spread(pas(P1))), int(_spread(pas(P2)))], idle_spread=int(sn))


def build(cid):
    j, row = load(cid); per = {}
    for d in SRC: per[d] = cycle(d, row(f'walk_{d}'), row(f'idle_{d}')[0])
    cells, frames, tags = [], [], []
    for d in DIRS:
        fr, _ = per[MIRROR.get(d, d)]
        a = len(cells)
        for k, f in enumerate(fr):
            i = len(cells); cells.append(mirror(f) if d in MIRROR else f)
            frames.append(dict(filename=f'walk4_{d}_{k}', frame=dict(x=(i % 8) * 128, y=(i // 8) * 128, w=128, h=128), duration=125))
        tags.append(dict(name=f'walk_{d}', **{'from': a, 'to': len(cells) - 1}, direction='forward'))
    sheet = np.zeros((((len(cells) + 7) // 8) * 128, 8 * 128, 4), np.uint8)
    for i, c in enumerate(cells): sheet[(i // 8) * 128:(i // 8 + 1) * 128, (i % 8) * 128:(i % 8 + 1) * 128] = c
    od = os.path.join(ROOT, 'characters', cid, 'ai')
    Image.fromarray(sheet).save(os.path.join(od, f'chr_{cid}_walk.png'))
    stride = j['meta'].get('walk_stride_px') or 26.0
    meta = dict(app='bbt-pixel/tools/ai_import/walk_cycle.py', image=f'chr_{cid}_walk.png', size=dict(w=sheet.shape[1], h=sheet.shape[0]),
                frameTags=tags, poses=['stride', 'pass', 'stride', 'pass'], pass_poses=[1, 3], pivot=[64, 116],
                walk_stride_px=stride, walk_m_per_pose=round(stride / 2 / (64 * 2 ** 0.5), 4),
                source={d: v[1] for d, v in per.items()},
                note='poses re-sequenced from chr_%s.json walk_<d> (see module doc); NE/E/SE mirror NW/W/SW' % cid)
    json.dump(dict(frames=frames, meta=meta), open(os.path.join(od, f'chr_{cid}_walk.json'), 'w'), indent=1)
    return meta


if __name__ == '__main__':
    for cid in (sys.argv[1:] or CH):
        m = build(cid); print(cid, m['walk_m_per_pose'], {d: (v['stride'], v['pass_from'], v['spread'], v['pass_spread'], v['idle_spread']) for d, v in m['source'].items()})
