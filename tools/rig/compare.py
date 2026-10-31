"""old (v2 whole-frame sprites, characters/<cid>/refs/v2_style) vs new (rig1) comparison sheet + measurements.
    python3 tools/rig/compare.py <cid>   ->  harness/renders/rigcheck/<cid>_compare.png + <cid>_compare.md"""
import sys, os, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE)
import compose as C, motion as M, skeleton as SK

CID = sys.argv[1] if len(sys.argv) > 1 else 'penny'
OUTD = os.path.join(ROOT, 'harness', 'renders', 'rigcheck'); os.makedirs(OUTD, exist_ok=True)
try: FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
except Exception: FONT = ImageFont.load_default()


def sheet(path):
    J = json.load(open(path + '.json')); S = Image.open(path + '.png').convert('RGBA')
    return {f['filename']: S.crop((f['frame']['x'], f['frame']['y'], f['frame']['x'] + 128, f['frame']['y'] + 128)) for f in J['frames']}


def frame(sh, cid, name):
    return sh.get(f'chr_{cid}_{name}')


def sil(im):
    a = np.array(im)[..., 3] > 0; ys, xs = np.nonzero(a)
    return a, ys.min(), ys.max(), xs.min(), xs.max()


def measure(sh, cid):
    m = {}
    a, t, b, l, r = sil(frame(sh, cid, 'idle_S_00')); m['height_px'] = int(b - t + 1); m['width_px'] = int(r - l + 1)
    tops = []; spread = []
    for k in range(8):
        im = frame(sh, cid, f'walk_W_{k:02d}')
        if im is None: continue
        a, t, b, l, r = sil(im); tops.append(int(t))
        rows = a[b - 3:b + 1]; xs = np.nonzero(rows.any(0))[0]; spread.append(int(xs.max() - xs.min() + 1))
    m['walk_bob_px'] = int(max(tops) - min(tops)) if tops else None
    m['walk_feet_spread_px_max'] = max(spread) if spread else None
    m['walk_feet_spread_px_min'] = min(spread) if spread else None
    return m


def overlay(im, J, z):
    """proportion lines (crown/chin/shoulder/hip/knee/ankle) and the skeleton on a zoomed frame"""
    big = im.resize((128 * z, 128 * z), Image.NEAREST); d = ImageDraw.Draw(big)
    P = lambda k: tuple(v * z for v in SK.project(J[k])[:2])
    for a, b in (('pel', 'sh_c'), ('sh_c', 'neck1'), ('neck1', 'head_c'), ('shR', 'elR'), ('elR', 'wrR'), ('shL', 'elL'), ('elL', 'wrL'),
                 ('hipR', 'kneeR'), ('kneeR', 'ankR'), ('hipL', 'kneeL'), ('kneeL', 'ankL'), ('shR', 'shL'), ('hipR', 'hipL')):
        if a in J and b in J: d.line([P(a), P(b)], fill=(0, 255, 140, 255), width=2)
    for k in J:
        if isinstance(J[k], np.ndarray) and J[k].shape == (3,) and k in ('head_c', 'shR', 'shL', 'elR', 'elL', 'wrR', 'wrL', 'hipR', 'hipL', 'kneeR', 'kneeL', 'ankR', 'ankL', 'pel'):
            x, y = P(k); d.ellipse([x - 3, y - 3, x + 3, y + 3], outline=(255, 255, 255, 255))
    return big


def lines(big, marks, z, x0, x1):
    d = ImageDraw.Draw(big)
    for name, y, col in marks:
        d.line([(x0, y * z), (x1, y * z)], fill=col, width=1); d.text((x1 + 3, y * z - 7), name, font=FONT, fill=col)
    return big


def main():
    base = os.path.join(ROOT, 'characters', CID)
    old = sheet(os.path.join(base, 'refs', 'v2_style', f'chr_{CID}')); new = sheet(os.path.join(base, f'chr_{CID}'))
    spec, B, pal = C.character(CID); z = 4
    J = C.draw(CID, M.idle(B, spec, 0), 'S')[1]['J']
    # body landmarks (screen y, S view) from the rig
    yy = lambda p: 116.0 - SK.K * p[2] * math.cos(math.radians(30))     # world height -> screen y on the pivot plane
    crown = yy(np.array([0, 0, B.H]))
    marks = [('crown', crown), ('chin', yy(np.array([0, 0, B.chin_z]))), ('shoulder', yy(J['sh_c'])), ('hip', yy(J['pel'])),
             ('knee', yy((J['kneeR'] + J['kneeL']) / 2)), ('sole', 116.0)]
    hh = marks[1][1] - marks[0][1]
    cols = [(255, 220, 90, 255), (255, 160, 60, 255), (120, 200, 255, 255), (200, 120, 255, 255), (120, 255, 160, 255), (255, 255, 255, 255)]
    marks = [(n, y, c) for (n, y), c in zip(marks, cols)]
    W = 128 * z
    canvas = Image.new('RGBA', (W * 4 + 220, 128 * z + 40 + 112 * 2 * 2 + 70 + 260), (36, 36, 44, 255)); d = ImageDraw.Draw(canvas)
    d.text((10, 8), f'{CID}: v2 whole-frame sprite (left)  vs  rig1 modular human (right).  4x, idle S + SW.  '
           f'lines = rig landmarks; head = {hh:.1f}px, body = {116 - marks[0][1]:.1f}px = {(116 - marks[0][1]) / hh:.2f} heads', font=FONT, fill=(230, 230, 230, 255))
    x = 0
    for lab, sh, ov in (('old S', old, False), ('old SW', old, False), ('new S', new, True), ('new SW', new, True)):
        dd = lab.split()[1]; im = frame(sh, CID, f'idle_{dd}_00')
        big = overlay(im, C.draw(CID, M.idle(B, spec, 0), dd)[1]['J'], z) if (ov and dd == 'S') else im.resize((W, W), Image.NEAREST)
        if dd == 'S': big = lines(big, marks, z, 0, W - 70)
        canvas.alpha_composite(big, (x, 30)); d.text((x + 8, 34), lab, font=FONT, fill=(255, 255, 255, 255)); x += W
    # walk strips (W), old above new, 2x
    y0 = 30 + W + 10
    for lab, sh in (('old walk W', old), ('new walk W', new)):
        d.text((10, y0), lab, font=FONT, fill=(230, 230, 230, 255))
        for k in range(8):
            im = frame(sh, CID, f'walk_W_{k:02d}')
            if im is None: continue
            canvas.alpha_composite(im.crop((16, 10, 112, 122)).resize((192, 224), Image.NEAREST), (10 + 192 * k + (0 if k < 4 else 20), y0 + 16))
        y0 += 224 + 24
    # exploded part map (raw canvas segmentation), S and W
    d.text((10, y0), 'rig parts (each a separate volume; colours = part id) and layers drawn in order skin -> clothing -> hair -> props', font=FONT, fill=(230, 230, 230, 255))
    rng = np.random.RandomState(3); xx = 10
    for dd in ('S', 'W', 'N'):
        info = C.draw(CID, M.idle(B, spec, 0), dd, raw=True)[1]; cv = info['cv']
        lut = (rng.randint(60, 255, (len(cv.parts) + 1, 3))).astype(np.uint8)
        pm = np.zeros((128, 128, 4), np.uint8); op = cv.part >= 0
        pm[op, :3] = lut[cv.part[op]]; pm[op, 3] = 255
        canvas.alpha_composite(Image.fromarray(pm).crop((24, 14, 104, 122)).resize((160 * 1, 216), Image.NEAREST).resize((240, 324), Image.NEAREST).crop((0, 0, 240, 250)), (xx, y0 + 16)); xx += 250
    names = sorted(set(info['cv'].parts))
    d.text((xx + 10, y0 + 20), 'parts:\n' + '\n'.join(', '.join(names[i:i + 4]) for i in range(0, len(names), 4)), font=FONT, fill=(230, 230, 230, 255))
    out = os.path.join(OUTD, f'{CID}_compare.png'); canvas.convert('RGB').save(out)
    mo, mn = measure(old, CID), measure(new, CID)
    md = [f'# {CID}: v2 sprite vs rig1 modular human', '', f'![compare]({CID}_compare.png)', '',
          'Measured from the shipped sheets (128x128 frames, pivot (64,116), 100 px = 185 cm, 2:1 dimetric).', '',
          '| metric | v2 (old) | rig1 (new) | target |', '|---|---|---|---|',
          f"| standing height, idle S (px) | {mo['height_px']} | {mn['height_px']} | {B.H / 185 * 100:.1f} body + hair/feet in view ({B.H:.0f} cm) |",
          f"| silhouette width, idle S (px) | {mo['width_px']} | {mn['width_px']} | shoulders {2 * B.sh_x * SK.K:.1f}px + arms |",
          f"| walk bob, W (px, crown range) | {mo['walk_bob_px']} | {mn['walk_bob_px']} | 1-2 px (lowest on 'down', highest on 'passing') |",
          f"| walk foot spread, W (px max/min) | {mo['walk_feet_spread_px_max']}/{mo['walk_feet_spread_px_min']} | {mn['walk_feet_spread_px_max']}/{mn['walk_feet_spread_px_min']} | stride ~ 1/3 height at contact, feet together at passing |",
          f'| head height (px) | - | {hh:.1f} ({B.H - B.chin_z:.1f} cm) | ~1/7.3 of the body; enlarged a little (head_k) so faces read at 1x |',
          f'| heads tall | - | {(116 - marks[0][1]) / hh:.2f} | 7-7.5 realistic; ~6.5 here on purpose (head_k) |', '',
          'Rig landmarks (screen y, S view): ' + ', '.join(f'{n} {y:.1f}' for n, y, _ in marks), '',
          'Body spec: ' + json.dumps({k: v for k, v in spec.get('body', {}).items()}), '',
          'Gait: ' + json.dumps(spec.get('gait', {})), '']
    open(os.path.join(OUTD, f'{CID}_compare.md'), 'w').write('\n'.join(md))
    print(out); print(json.dumps(dict(old=mo, new=mn)))


if __name__ == '__main__':
    main()
