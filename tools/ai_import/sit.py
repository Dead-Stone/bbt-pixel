"""AI seated pose (GenerateImage strip refs_ai/gen/<cid>_sit6.jpg) -> characters/<cid>/chr_<cid>_sit.png/.json.

Strip = 6 figures: [standing front (size reference), seated S, SW, W, NW, N] on an invisible chair (thighs
horizontal, feet flat).  ONE scale for the strip: the standing figure is scaled to the still's actor height (the same
rule as walk.py), so seated and standing frames have identical proportions in-world.  Every seated frame: soles on
row 119, hip centre (lower torso) on column 64.  Seat anchor ("seat" = butt contact point, see tools/seating.py):
y = underside of the butt in the side view (W), used for all facings (same scale, same sole row); x = 64.
Same file format as the rig sit sheet (8 dirs x 1 frame, 128 cells, pivot = floor point under the hips), so
tools/seating.py, harness/export_world.py (front-piece occluders), tools/sitcheck and the viewer use it unchanged.
"""
import os, json, numpy as np
from PIL import Image
import convert as CV, walk as WK

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
ORDER = ['S', 'SW', 'W', 'NW', 'N']
DIRS = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']
MIRROR = {'NE': 'NW', 'E': 'W', 'SE': 'SW'}
SEAT_CM = 43


def mirror(img):
    return np.roll(img[:, ::-1], 1, axis=1)


def place(c, s, pal, hipx_fn):
    h, w = c.shape[:2]
    nh, nw = max(1, int(round(h * s))), max(1, int(round(w * s)))
    rgb, A = CV.area_resize(c, (nw, nh)); m = A >= 0.5
    rgb = CV.unsharp(rgb, m, 0.35)
    hx = hipx_fn(m)
    ox = int(round(64 - hx)); oy = CV.SOLE + 1 - nh
    img = np.zeros((CV.H, CV.W, 4), np.uint8)
    sub = img[oy:oy + nh, ox:ox + nw]
    sub[m, :3] = CV.nearest(pal, rgb[m]); sub[m, 3] = 255
    img = CV.pixfix(img); img = CV.outline(img, pal); img = CV.pixfix(img)
    return CV.audit_fix(img, pal)


def torso_x(m, lo=0.30, hi=0.48):
    """centre of the torso band (30-48% down the seated figure: chest/waist, above the hands and the lap)"""
    ys = np.nonzero(m.any(1))[0]; y0, y1 = ys[0], ys[-1]
    band = m[y0 + int((y1 - y0) * lo): y0 + int((y1 - y0) * hi)]
    xs = np.nonzero(band)[1]
    return (xs.min() + xs.max()) / 2.0


def seat_row(f):
    """W frame: underside of the butt = last opaque row of the column run that starts in the torso at x=64"""
    A = f[..., 3] > 0
    col = A[:, 62:67].any(1)
    ys = np.nonzero(col)[0]
    y = ys[0]
    while y + 1 < 128 and col[y + 1]: y += 1
    return y


def sit_for(cid, pal, still):
    p = os.path.join(ROOT, 'refs_ai', 'gen', f'{cid}_sit6.jpg')
    if not os.path.exists(p): return None
    cuts = WK.cut_strip(p, 1, 0, 6, WK.KEY_M.get(cid, 70))
    cm = CV.REAL_CM[cid]; crown = int(round(CV.PIV[1] - 100 * cm / 185.0)); th = CV.SOLE - crown + 1
    s = th / cuts[0].shape[0]
    out = {d: place(c, s, pal, torso_x) for d, c in zip(ORDER, cuts[1:])}
    sy = seat_row(out['W'])
    return out, sy


def write_sit(cid, frames, sy, extra=None, ms=None):
    """extra: {anim: {dir5: [frames]}} -> extra rows (one row per anim frame, 8 dirs each), same seat anchor as the
    base row (the extra sheets are scale-locked to it, sheets.convert_extra); frames carry anim / k / duration"""
    od = os.path.join(ROOT, 'characters', cid)
    full = {d: mirror(frames[MIRROR[d]]) if d in MIRROR else frames[d] for d in DIRS}
    rows = [('sit', 0, full, None)]
    for an, fd in (extra or {}).items():
        n = len(fd['S'])
        for k in range(n):
            rows.append((an, k, {d: mirror(fd[MIRROR[d]][k]) if d in MIRROR else fd[d][k] for d in DIRS}, (ms or {}).get(an, [400] * n)[k]))
    sheet = np.zeros((128 * len(rows), 128 * 8, 4), np.uint8); fr = []
    for r, (an, k, F, dur) in enumerate(rows):
        for i, d in enumerate(DIRS):
            sheet[r * 128:(r + 1) * 128, i * 128:(i + 1) * 128] = F[d]
            e = dict(filename=f'chr_{cid}_{an}_{d}_{k:02d}', frame=dict(x=i * 128, y=r * 128, w=128, h=128), pivot=[64, 116],
                     seat=[64.0, float(sy)], dir=d)
            if an != 'sit': e.update(anim=an, k=k, duration=dur)
            fr.append(e)
    Image.fromarray(sheet).save(os.path.join(od, f'chr_{cid}_sit.png'))
    json.dump(dict(frames=fr, meta=dict(app='bbt-pixel/tools/ai_import/sit.py', version='ai1', image=f'chr_{cid}_sit.png',
                                        size=dict(w=1024, h=128 * len(rows)), pivot=[64, 116], lift_units=0.0, seat_cm=SEAT_CM,
                                        source=f'refs_ai/gen/{cid}_sit6.jpg (GenerateImage)',
                                        note='AI seated pose (tools/ai_import/sit.py): pivot = floor point under the hips; seat = butt '
                                             'contact point (place it on the seat surface, harness/seating.py); feet flat on the floor')),
              open(os.path.join(od, f'chr_{cid}_sit.json'), 'w'), indent=1)
    return full
