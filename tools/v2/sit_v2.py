"""v2 seated pose for one character: the v2 master (AI turnaround + hand faces) bent into the rig's seated pose by
the cutout animator.  Writes characters/<cid>/chr_<cid>_sit.png + .json (8 dirs x 1 frame, 128x128 cells; the
pivot is the floor point under the hips) and env/renders/poses/<cid>_sit_SW.png/.json (scene renders).
Run: cd tools/v2 && python3 sit_v2.py <cid>"""
import sys, os, json, math
import numpy as np
from PIL import Image
CID = sys.argv[1]
sys.argv = ['build_v2.py', CID]
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_v2 as V            # builds masters + palette on import (no sheet export)
from master import to_rgba
R, BC = V.R, V.BC
DIRS = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']
RAISE = 12.0

def sit_pose(th=1.3, kn=1.3):
    lift = round((45.5 - 17.0) / R.KSCALE[CID] - R.DIM['hip_z'], 2)
    p = BC.idle_pose(0); p.update(legs=[(th, kn), (th, kn)], arms=[(0.45, 0.95), (0.6, 0.85)], abduct=0.02, lift=lift + RAISE)
    return p, lift

def front_sit(d):
    """S / N: the thighs point at (away from) the camera, which the 2D bone warp cannot foreshorten.  Seated front
    view = the upper body slides down onto the lap (only the top few rows of the thighs stay visible), shins and
    feet stay on the floor.  Pivot = floor point under the hips: ~11 px behind the feet (S) / in front of them (N)."""
    c = V.cutout(d, 'open'); m = c.idx
    caps = [a for a in c.A0 if a[0] == 'cap']
    legs = [k for k, p in enumerate(R.build(BC.idle_pose(0))) if p[3] == 'leg']
    thighs = legs[0::2]
    crotch = int(round(min(min(c.A0[k][1][1], c.A0[k][2][1]) for k in thighs)))
    knee = int(round(np.mean([max(c.A0[k][1][1], c.A0[k][2][1]) for k in thighs])))
    feet = np.nonzero((m >= 0).any(1))[0].max()
    py = feet - 11 if d == 'S' else feet + 11
    hip_row = py - 24 if d == 'S' else py - 30          # seat ~0.45 m above the floor point (character scale ~54 px/m)
    D = max(0, hip_row - crotch); T = max(0, knee - D - crotch)
    out = np.full_like(m, -1)
    out[knee:] = m[knee:]
    top = m[:crotch + T]
    sel = top >= 0
    blk = out[D:D + top.shape[0]]
    blk[sel[:blk.shape[0]]] = top[:blk.shape[0]][sel[:blk.shape[0]]]
    from cutout import drop_specks, fill_holes
    out = drop_specks(fill_holes(out))
    return to_rgba(out, V.PAL), [64, int(py)]

def main():
    pose, lift = sit_pose()
    dz = RAISE * R.SCALE_EFF * math.cos(R.ELEV)
    pv = [64, round(116 + dz)]
    cells = {}
    pivots = {}
    for d in DIRS:
        src = BC.MIRROR.get(d, d)
        if src in ('S', 'N'):
            cells[d], pivots[d] = front_sit(src); continue
        im = to_rgba(V.cutout(src, 'open').pose(pose), V.PAL)
        cells[d] = np.ascontiguousarray(im[:, ::-1]) if d in BC.MIRROR else im; pivots[d] = pv
    sheet = np.zeros((128, 128 * len(DIRS), 4), np.uint8)
    frames = []
    for i, d in enumerate(DIRS):
        sheet[:, i*128:(i+1)*128] = cells[d]
        frames.append(dict(filename=f'chr_{CID}_sit_{d}_00', frame=dict(x=i*128, y=0, w=128, h=128), pivot=pivots[d], dir=d))
    out = os.path.join(V.ROOT, 'characters', CID)
    Image.fromarray(sheet).save(f'{out}/chr_{CID}_sit.png')
    json.dump(dict(frames=frames, meta=dict(app='bbt-pixel/tools/v2/sit_v2.py', version='v2', image=f'chr_{CID}_sit.png',
                                            size=dict(w=sheet.shape[1], h=128), pivot=pv, lift_units=lift,
                                            note='seated pose (couch/chair height); pivot = floor point under the hips')),
              open(f'{out}/chr_{CID}_sit.json', 'w'), indent=1)
    P = os.path.join(V.ROOT, 'env', 'renders', 'poses')
    Image.fromarray(cells['SW']).save(f'{P}/{CID}_sit_SW.png')
    json.dump(dict(sprite=f'{CID}_sit_SW.png', pivot=pv, dir='SW', lift_units=lift, version='v2',
                   note='v2 seated pose (tools/v2/sit_v2.py); pivot = floor point under the hips'), open(f'{P}/{CID}_sit_SW.json', 'w'), indent=1)
    big = Image.fromarray(sheet).resize((sheet.shape[1]*3, 384), Image.NEAREST); big.save(f'/tmp/sit_{CID}_3x.png')
    print(CID, 'pivot', pv)

if __name__ == '__main__': main()
