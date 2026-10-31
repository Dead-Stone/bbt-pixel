"""Build a character's sheets from the modular rig (tools/rig): every frame is a skeleton pose (motion.py) drawn
part-by-part (parts.py) into a z-buffer, shaded with the character palette and cleaned (pixfix).
Same 128x128 cells / pivot (64,116) / 8 dirs / atlas layout / anim list + durations as before, so the viewer
and harness need no changes (build_char_sheet.main is reused with frame_img swapped, like tools/v2/build_v2.py).
Run:  cd tools/rig && python3 build.py <cid>
Writes characters/<cid>/chr_<cid>{.png,.json,.meta.json,_sit.png,_sit.json}, GIFs, palettes/bbt_<cid>_rig.gpl,
env/renders/poses/<cid>_sit_<dir>.{png,json}; keeps the previous sheet in characters/<cid>/refs/v2_style/."""
import sys, os, json, shutil, math
import numpy as np
from PIL import Image
CID = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(HERE); ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, HERE); sys.path.insert(0, TOOLS)
import compose as C, motion as M, skeleton as SK
cwd = os.getcwd(); os.chdir(TOOLS); sys.argv = ['build_char_sheet.py', CID]
import build_char_sheet as BC
os.chdir(cwd)

spec, B, pal = C.character(CID)
OUT = os.path.join(ROOT, 'characters', CID)


def pose_for(anim, k):
    if anim == 'idle': return M.idle(B, spec, k)
    if anim == 'walk': return M.walk(B, spec, k)
    if anim == 'blink': return M.blink(B, spec, k)
    if anim == 'talk': return M.talk(B, spec, k)
    if anim == 'work': return M.WORK[spec['work']](B, spec, k)
    return M.EMOTE[anim](B, spec, k)


_cache = {}
def frame_img(anim, k, d):
    key = (anim, k, d)
    if key not in _cache:
        idx, _ = C.draw(CID, pose_for(anim, k), d)
        _cache[key] = C.to_rgba(idx, pal.arr)
    return _cache[key].copy()


def keep_previous():
    dst = os.path.join(OUT, 'refs', 'v2_style'); os.makedirs(dst, exist_ok=True)
    for f in (f'chr_{CID}.png', f'chr_{CID}.json', f'chr_{CID}_sit.png', f'chr_{CID}_sit.json'):
        p = os.path.join(OUT, f)
        if os.path.exists(p) and not os.path.exists(os.path.join(dst, f)): shutil.copy(p, dst)


def build_sit():
    P, seat_h = M.sit(B, spec)
    cells, frames = [], []
    for i, d in enumerate(SK.DIRS):
        src = SK.MIRROR.get(d, d)
        idx, info = C.draw(CID, P, d); J = info['J']
        butt = J['pel'].copy(); butt[2] = seat_h
        sx, sy, _ = SK.project(butt)
        if d in SK.MIRROR: sx = 128 - sx
        cells.append(C.to_rgba(idx, pal.arr))
        frames.append(dict(filename=f'chr_{CID}_sit_{d}_00', frame=dict(x=i * 128, y=0, w=128, h=128),
                           pivot=[64, 116], seat=[round(float(sx), 1), round(float(sy), 1)], dir=d))
    sheet = np.concatenate(cells, 1)
    Image.fromarray(sheet).save(os.path.join(OUT, f'chr_{CID}_sit.png'))
    note = ('rig seated pose (tools/rig/motion.py sit): pivot = floor point under the hips; seat = butt contact point '
            '(place it on the seat surface, harness/seating.py); feet flat on the floor, seat height %.0f cm' % seat_h)
    json.dump(dict(frames=frames, meta=dict(app='bbt-pixel/tools/rig/build.py', version='rig1', image=f'chr_{CID}_sit.png',
                                            size=dict(w=sheet.shape[1], h=128), pivot=[64, 116], lift_units=0.0, seat_cm=round(seat_h, 1), note=note)),
              open(os.path.join(OUT, f'chr_{CID}_sit.json'), 'w'), indent=1)
    PD = os.path.join(ROOT, 'env', 'renders', 'poses')
    for i, d in enumerate(SK.DIRS):
        Image.fromarray(cells[i]).save(os.path.join(PD, f'{CID}_sit_{d}.png'))
        json.dump(dict(sprite=f'{CID}_sit_{d}.png', pivot=frames[i]['pivot'], seat=frames[i]['seat'], dir=d, lift_units=0.0,
                       version='rig1', note=note), open(os.path.join(PD, f'{CID}_sit_{d}.json'), 'w'), indent=1)
    return frames


def head_rows():
    n = 0
    for d in ('S', 'SW', 'W', 'NW', 'N'):
        im = np.array(frame_img('idle', 0, d)); top = np.nonzero((im[..., 3] > 0).any(1))[0][0]
        J = SK.solve(B, M.idle(B, spec, 0), SK.YAW[d])
        n = max(n, int(round(SK.project(J['chin'])[1])) - int(top) + 1)
    return n


def armcheck():
    """rig-based arm proportions in the relaxed idle pose (all 5 source dirs): fingertip ~ mid-thigh, elbow ~ waist,
    upper/fore ratio, hand length in px.  Tolerances as tools/v2/armcheck.py."""
    rows = []
    J = SK.solve(B, M.idle(B, spec, 0), 0.0)
    px = lambda cm: cm * SK.K * math.cos(math.radians(SK.ELEV))
    hipz = J['hipR'][2]; kneez = J['kneeR'][2]; mid_thigh = (hipz + kneez) / 2
    waist = J['waist_c'][2]
    for s in 'RL':
        tip = J['tip' + s][2]; el = J['el' + s][2]
        rows.append(dict(side=s, fingertip_vs_midthigh_px=round(px(tip - mid_thigh), 1), elbow_vs_waist_px=round(px(el - waist), 1),
                         upper_fore_ratio=round(B.upper / B.fore, 2), hand_px=round(px(B.hand), 1)))
    ok = all(abs(r['fingertip_vs_midthigh_px']) <= 3 and abs(r['elbow_vs_waist_px']) <= 3 and 0.9 <= r['upper_fore_ratio'] <= 1.35
             and 3 <= r['hand_px'] <= 7 for r in rows)
    return dict(ok=bool(ok), rows=[{k: (float(v) if not isinstance(v, str) else v) for k, v in r.items()} for r in rows])


if __name__ == '__main__':
    keep_previous()
    gpl = os.path.join(ROOT, 'palettes', f'bbt_{CID}_rig.gpl'); pal.save_gpl(gpl, f'bbt_{CID}_rig')
    BC.GPL = gpl; BC.frame_img = frame_img
    BC.main()
    js = json.load(open(os.path.join(OUT, f'chr_{CID}.json')))
    js['meta']['app'] = 'bbt-pixel/tools/rig/build.py'; js['meta']['version'] = 'rig1'
    js['meta']['audit'] = dict(head_rows=head_rows(), why='rows from the crown to the chin: the flicker check covers the '
                               'head only (real 7-7.5-head proportions put the shoulders inside a fixed 22-row window)')
    json.dump(js, open(os.path.join(OUT, f'chr_{CID}.json'), 'w'), indent=1)
    meta = json.load(open(os.path.join(OUT, f'chr_{CID}.meta.json')))
    ac = armcheck()
    meta.update(version='rig1', palette=f'palettes/bbt_{CID}_rig.gpl', body_height_px=round(B.H / 185 * 100),
                camera=dict(projection='2:1 dimetric', elevation_deg=30, px_per_cm=round(SK.K, 4), scale='100 px = 185 cm'),
                rig=dict(height_cm=B.H, parts=['head', 'neck', 'chest', 'pelvis', 'upper arm', 'forearm', 'hand', 'thigh', 'shin', 'foot'],
                         layers=['skin', 'top', 'pants/skirt', 'shoes', 'hair', 'props'], gait=spec.get('gait'), armcheck=ac),
                notes=('rig1: modular human rig (tools/rig).  Every frame is a skeleton pose (motion.py: walk contact/down/'
                       'passing/up with pelvis bob, hip roll, weight sway, pelvis/chest counter-twist, counter-swinging arms; '
                       'breathing idle; IK sit) drawn part by part as shaded 3-D volumes into a z-buffer (parts.py/render.py), '
                       'clothing + hair + props as layers, palette-shaded, outlined, cleaned with tools/v2/pixfix.  '
                       'E/NE/SE mirror W/NW/SW.  Previous sheets: refs/v2_style/.'))
    for a in meta['anims'].values():
        if 'note' in a: a['note'] = a['note'].replace(' (v2 masters: body/hands only, no mouth frames)', ' (mouth open/closed frames)')
    json.dump(meta, open(os.path.join(OUT, f'chr_{CID}.meta.json'), 'w'), indent=1)
    build_sit()
    print('armcheck', json.dumps(ac))
