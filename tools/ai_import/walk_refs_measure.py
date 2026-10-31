"""Measure walk cycles (ours vs online refs) -- read-only analysis, does not touch the game.
Per frame on the alpha mask: head top (bob), foot-band spread (stride), foot lift (S/N step), mid-band width (arm swing)."""
import json, os, sys
import numpy as np
from PIL import Image, ImageSequence
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(ROOT, 'refs_ai', 'walk_refs')
DIRS8 = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']

def cells(path, cw, ch, row, cols):
    im = Image.open(path).convert('RGBA')
    return [im.crop((c * cw, row * ch, (c + 1) * cw, (row + 1) * ch)) for c in cols]

def ours(cid, d):
    return cells(os.path.join(ROOT, 'characters', cid, 'ai', f'chr_{cid}_walk.png'), 128, 128, DIRS8.index(d), range(8))

REFS = {  # name: (loader(dir) -> frames, fps, note)
    'LPC (Redshrike)': (lambda d: cells(os.path.join(R, 'lpc_male_walkcycle.png'), 64, 64, {'N': 0, 'W': 1, 'S': 2, 'E': 3}[d], range(1, 9)), None, '4 dir, 8 walk + 1 stand'),
    'Bumblebee 8dir': (lambda d: cells(os.path.join(R, 'bumblebee_8dir_walk_blue.png'), 32, 48, DIRS8.index(d), range(8)), None, '8 dir x 8'),
    'Chrome District 22deg': (lambda d: cells(os.path.join(R, 'chrome_district_VX-0001_ortho22.png'), 56, 84, DIRS8.index(d), range(6)), 10, '8 dir x 6, demo 10 fps'),
}

def metrics(frames):
    tops, spreads, lifts, mids, Hs = [], [], [], [], []
    boxes = [np.argwhere(np.array(f)[:, :, 3] > 24) for f in frames]
    bot = max(b[:, 0].max() for b in boxes); top0 = min(b[:, 0].min() for b in boxes); H = bot - top0 + 1
    for b in boxes:
        ys, xs = b[:, 0], b[:, 1]
        tops.append(ys.min())
        fb = b[ys >= bot - 0.12 * H]
        spreads.append(int(fb[:, 1].max() - fb[:, 1].min() + 1) if len(fb) else 0)
        lb = b[ys >= bot - 0.25 * H]
        cx = np.median(lb[:, 1]); L = lb[lb[:, 1] < cx]; Rr = lb[lb[:, 1] >= cx]
        lifts.append(abs(int(L[:, 0].max()) - int(Rr[:, 0].max())) if len(L) and len(Rr) else 0)
        mb = b[(ys >= top0 + 0.35 * H) & (ys <= top0 + 0.6 * H)]
        mids.append(int(mb[:, 1].max() - mb[:, 1].min() + 1))
    return dict(n=len(frames), H=int(H), bob=int(max(tops) - min(tops)), bob_pct=round(100 * (max(tops) - min(tops)) / H, 1),
                stride_pct=round(100 * max(spreads) / H, 1), pass_pct=round(100 * min(spreads) / H, 1),
                lift_pct=round(100 * max(lifts) / H, 1), arm_pct=round(100 * (max(mids) - min(mids)) / H, 1),
                tops=[int(t - min(tops)) for t in tops], spreads=spreads, lifts=lifts)

if __name__ == '__main__':
    out = {}
    for name, (ld, fps, note) in REFS.items():
        for d in ['S', 'SW', 'W', 'N']:
            try: out[f'{name}|{d}'] = metrics(ld(d))
            except (KeyError, ValueError): pass
    for cid in ['raj', 'penny', 'sheldon', 'howard', 'bernadette', 'leonard', 'amy']:
        for d in ['S', 'SW', 'W', 'N']:
            out[f'ours {cid}|{d}'] = metrics(ours(cid, d))
    for k, v in out.items():
        print(f"{k:28s} n={v['n']} H={v['H']:3d} bob={v['bob']}px ({v['bob_pct']}%) stride={v['stride_pct']}% pass={v['pass_pct']}% lift={v['lift_pct']}% arm={v['arm_pct']}% tops={v['tops']} spread={v['spreads']} lift={v['lifts']}")
    json.dump(out, open(sys.argv[1], 'w'), indent=1) if len(sys.argv) > 1 else None
