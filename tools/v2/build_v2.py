"""Build the v2 sprite sheet for one character: AI master idle frames (refs/v2_master) + hand-placed face
pixels (faces.py), animated by the rig skeleton (cutout.py).  Same 128x128 cells, pivot, 8 dirs, atlas
layout and animation list as v1 (build_char_sheet.main is reused with frame_img swapped).
Run: cd tools/v2 && python3 build_v2.py <cid>"""
import sys, os, json, pickle, numpy as np
CID = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(HERE); ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS); sys.path.insert(0, HERE); os.chdir(TOOLS)
sys.argv = ['build_char_sheet.py', CID]
import build_char_sheet as BC
import char_rig as R
from cutout import Cutout
from master import to_rgba
import faces

MD = os.path.join(ROOT, 'characters', CID, 'refs', 'v2_master')
PAL0 = np.load(os.path.join(MD, 'pal.npy'))
_cut, _pal, _cache = {}, {}, {}

def base_B(d):
    bp = os.path.join(MD, f'baseB_{d}.pkl')
    if os.path.exists(bp): return pickle.load(open(bp, 'rb'))
    B = R.render(BC.idle_pose(0), R.YAW[d]); pickle.dump(B, open(bp, 'wb')); return B

def base_Bna(d):
    bp = os.path.join(MD, f'baseBna_{d}.pkl')
    if os.path.exists(bp): return pickle.load(open(bp, 'rb'))
    B = R.render(dict(BC.idle_pose(0), no_arms=True), R.YAW[d]); pickle.dump(B, open(bp, 'wb')); return B

# one palette for the whole character: master palette + face colours (added for every direction up front)
def build_masters():
    pal = PAL0.copy(); M = {}; eyes = {}
    for d in ('S', 'SW', 'W', 'NW', 'N'):
        m = np.load(os.path.join(MD, f'master_{d}.npy'))
        sk = faces.skin_index(m, pal, R.C['skin'])
        m2, pal, ey = faces.apply_face(CID, d, m, pal, tuple(pal[sk]))
        M[d] = (m2, sk, m2 != m); eyes[d] = ey
    import pixfix as PF
    pal = PF.extend_palette(pal)          # outline shade of every colour (consistent 1-px dark outline)
    return pal, M, eyes
PAL, MASTERS, EYES = build_masters()
L = PAL.astype(float) @ np.array([0.299, 0.587, 0.114])

def _matcol():
    """one colour per rig material for the whole character (repainted limbs must not change colour between
    directions): pooled over the five masters; skin = the face skin"""
    import cutout as CU
    acc = {}
    for d in ('S', 'SW', 'W', 'NW', 'N'):
        m, sk, prot = MASTERS[d]
        c = Cutout(m, base_B(d), BC.idle_pose(0), R.YAW[d], PAL, protect=prot, base_Bna=base_Bna(d))
        for mat, (u, w) in c.mat_stats.items():
            a = acc.setdefault(mat, {})
            for i, x in zip(u, w): a[int(i)] = a.get(int(i), 0.0) + float(x) * (2.0 if d == 'S' else 1.0)
    tab = {mat: max(a, key=a.get) for mat, a in acc.items() if a and max(a.values()) > 0}
    tab['skin'] = int(MASTERS['S'][1])
    CU.MATCOL.clear(); CU.MATCOL.update(tab)
_matcol()

def lid_index(sk):
    """eyelid line colour: the palette colour ~0.62x the skin, of the same hue family"""
    t = PAL[sk] * 0.62; return int(((PAL.astype(float) - t) ** 2).sum(1).argmin())

def cutout(d, eyes):
    key = (d, eyes)
    if key not in _cut:
        m, sk, prot = MASTERS[d]
        if eyes != 'open':
            m1 = faces.blink(m, PAL, EYES[d], eyes, sk, lid_index(sk)); prot = prot | (m1 != m); m = m1
        _cut[key] = Cutout(m, base_B(d), BC.idle_pose(0), R.YAW[d], PAL, protect=prot, base_Bna=base_Bna(d))
    return _cut[key]

def despeck(im):
    """last-pass cleanup: an orphan pixel (no same-colour neighbour, only a near shade of one) left where a moved arm
    meets hair / torso takes the colour of its closest neighbour (same rule as tools/v2/audit.py 'speck')"""
    import audit as AU
    for _ in range(2):
        sp = AU.audit_frame(im)['speck']
        if not sp.any(): break
        for y, x in zip(*np.nonzero(sp)):
            c = im[y, x, :3].astype(int); best = None
            for dy, dx in AU.K8:
                q = im[y + dy, x + dx]
                if q[3] == 0: continue
                dd = int(((q[:3].astype(int) - c) ** 2).sum())
                if best is None or dd < best[0]: best = (dd, q.copy())
            if best is not None: im[y, x] = best[1]
    return im

def frame_img(anim, k, d):
    src = BC.MIRROR.get(d, d)
    eyes = BC.eyes_for(anim, k)
    ck = ('idle', 0, src, eyes) if anim == 'blink' else (anim, k, src, eyes)
    if ck not in _cache:
        _cache[ck] = despeck(to_rgba(cutout(src, eyes).pose(BC.pose_for(anim, k, src)), PAL))
    im = _cache[ck]
    return np.ascontiguousarray(im[:, ::-1]) if d in BC.MIRROR else im.copy()

def save_gpl(path):
    with open(path, 'w') as f:
        f.write(f'GIMP Palette\nName: bbt_{CID}_v2\nColumns: 8\n#\n')
        for i, c in enumerate(PAL): f.write(f'{int(c[0]):3d} {int(c[1]):3d} {int(c[2]):3d}\tv2_{i:02d}\n')

if __name__ == '__main__':
    gpl = os.path.join(ROOT, 'palettes', f'bbt_{CID}_v2.gpl'); save_gpl(gpl)
    BC.GPL = gpl; BC.frame_img = frame_img
    BC.main()
    OUT = BC.OUT
    js = json.load(open(os.path.join(OUT, f'chr_{CID}.json')))
    js['meta']['app'] = 'bbt-pixel/tools/v2/build_v2.py'; js['meta']['version'] = 'v2'
    json.dump(js, open(os.path.join(OUT, f'chr_{CID}.json'), 'w'), indent=1)
    meta = json.load(open(os.path.join(OUT, f'chr_{CID}.meta.json')))
    meta.update(version='v2', palette=f'palettes/bbt_{CID}_v2.gpl',
                notes=('v2: one AI-generated master turnaround (S/SW/W/NW/N idle, refs/v2_master/master_strip.jpg) '
                       'downscaled to 128px + palette-snapped + cleaned (tools/v2/master.py), faces hand-placed per '
                       'facing (tools/v2/faces.py), animated by cut-out bone deformation driven by the v1 rig '
                       'skeleton (tools/v2/cutout.py); E/NE/SE mirror W/NW/SW.  Emotes move limbs/head only: face '
                       'expressions, head turns and hair swing are not re-drawn.  v1 sheets: refs/v1_style/.'))
    for a in meta['anims'].values():
        if 'note' in a: a['note'] = 'v1 timing kept. ' + a['note']
    json.dump(meta, open(os.path.join(OUT, f'chr_{CID}.meta.json'), 'w'), indent=1)
    print('v2 palette colours', len(PAL))
