"""Build chr_sheldon v0 sprite sheet procedurally (proxy-3D SDF rig -> cel-shaded pixel frames).
Run: cd tools && ../.venv/bin/python build_sheldon_sheet.py"""
import json, math, os, sys, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sheldon_rig as R
from compose_sheldon import compose
from sprite_common import load_gpl, palette_violations, PIVOT

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'characters', 'sheldon'); os.makedirs(os.path.join(OUT, 'refs'), exist_ok=True)
GPL = os.path.join(ROOT, 'palettes', 'bbt_sheldon.gpl')
R.SCALE = float(os.environ.get('SCALE', '1.122'))
CELL, COLS = 128, 12
DIRS8 = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']
MIRROR = {'NE': 'NW', 'E': 'W', 'SE': 'SW'}
PX = 1.0 / (R.SCALE * math.cos(R.ELEV))          # world units per vertical screen px

def sole_lift(legs):
    zs = []
    for i, sx in enumerate((-5.2, 5.2)):
        _, ank = R.leg_chain(np.array([sx, 0, 45.5]), *legs[i]); zs.append(ank[2] - 3.5)
    return -min(zs)

IDLE_ARMS = [(0.03, 0.12), (0.03, 0.12)]
def idle_pose(k):
    br = [0, 1, 1, 0][k] * PX
    return dict(breathe=br, legs=[(0, 0.02), (0, 0.02)], arms=IDLE_ARMS, abduct=0.10)

def walk_pose(k):
    legs, arms = [], []
    for side in (0, 1):
        ph = math.pi / 2 + 2 * math.pi * k / 8 + side * math.pi
        legs.append((0.30 * math.sin(ph), 0.08 + 0.55 * max(0.0, math.cos(ph)) ** 1.5))
        fl = -0.22 * math.sin(ph)
        arms.append((fl, 0.15 + 0.1 * max(0.0, fl)))
    p = dict(legs=legs, arms=arms, abduct=0.10)
    p['lift'] = sole_lift(legs)
    return p

KA, KB = (1.35, 0.85), (1.15, 1.20)
HEAD_TURN = float(os.environ.get('HEAD_TURN', '0.45'))
def knock_pose(k):
    p = idle_pose(0)
    arms = list(IDLE_ARMS)
    if k < 12:
        j = k % 4
        arms[1] = [KA, KB, KA, KB][j]
        if j == 3: p['head_yaw'] = HEAD_TURN
    else:
        t = (k - 11) / 4.0                          # 0.25..1.0 lower the arm
        arms[1] = (KA[0] * (1 - t) + IDLE_ARMS[1][0] * t, KA[1] * (1 - t) + IDLE_ARMS[1][1] * t)
    p['arms'] = arms
    return p

ANIMS = [  # name, nframes, fps, loop, dirs, posefn, ms per frame
    ('idle', 4, 4, True, DIRS8, idle_pose, 250),
    ('walk', 8, 10, True, DIRS8, walk_pose, 100),
    ('knock_knock_penny', 16, 8, False, ['SW', 'NW', 'NE', 'SE'], knock_pose, 125),
    ('blink', 2, 12, False, DIRS8, None, 80),
]
HOLDS = {3: 375, 7: 375, 11: 375}

_cache = {}
def buffers(anim, k, d):
    key = (anim, k, d)
    if key not in _cache:
        pose = (idle_pose(0) if anim == 'blink' else dict(ANIMS_BY[anim][5](k)))
        _cache[key] = R.render(pose, R.YAW[d])
    return _cache[key]
ANIMS_BY = {a[0]: a for a in ANIMS}

def frame_img(anim, k, d):
    src = MIRROR.get(d, d)
    B = buffers(anim, k, src)
    blink = (anim == 'blink' and k == 0)
    return compose(B, mirror=(d in MIRROR), blink=blink)

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    t0 = time.time()
    rows = []   # (anim, dir, [imgs])
    for name, n, fps, loop, dirs, fn, ms in ANIMS:
        for d in dirs:
            rows.append((name, d, [frame_img(name, k, d) for k in range(n)]))
            print(f'{name}_{d} done {time.time()-t0:.0f}s', flush=True)
    # layout: each tag starts on a new row, wraps every 12
    layout, r = [], 0
    for name, d, imgs in rows:
        cells = []
        for k, im in enumerate(imgs):
            cells.append((r + k // COLS, k % COLS)); 
        layout.append((name, d, imgs, cells)); r += (len(imgs) + COLS - 1) // COLS
    H = r * CELL; W = COLS * CELL
    assert H <= 4096 and W <= 4096, (W, H)
    sheet = np.zeros((H, W, 4), np.uint8)
    frames, tags = [], []
    for name, d, imgs, cells in layout:
        ms = ANIMS_BY[name][6]; start = len(frames)
        for k, (im, (rr, cc)) in enumerate(zip(imgs, cells)):
            sheet[rr*CELL:(rr+1)*CELL, cc*CELL:(cc+1)*CELL] = im
            dur = HOLDS.get(k, ms) if name == 'knock_knock_penny' else ms
            frames.append(dict(filename=f'chr_sheldon_{name}_{d}_{k:02d}',
                               frame=dict(x=cc*CELL, y=rr*CELL, w=CELL, h=CELL), rotated=False, trimmed=False,
                               spriteSourceSize=dict(x=0, y=0, w=CELL, h=CELL), sourceSize=dict(w=CELL, h=CELL),
                               duration=dur))
        tags.append(dict(name=f'{name}_{d}', **{'from': start, 'to': len(frames) - 1},
                         direction='forward', color='#000000ff'))
    Image.fromarray(sheet).save(os.path.join(OUT, 'chr_sheldon.png'))
    Image.fromarray(sheet).resize((W*4, H*4), Image.NEAREST).save(os.path.join(OUT, 'chr_sheldon_preview4x.png'))
    js = dict(frames=frames, meta=dict(app='bbt-pixel/tools/build_sheldon_sheet.py', version='v0',
              image='chr_sheldon.png', format='RGBA8888', size=dict(w=W, h=H), scale='1',
              frameTags=tags, layers=[dict(name='body', opacity=255, blendMode='normal')],
              slices=[dict(name='pivot', color='#ff0000ff',
                           keys=[dict(frame=0, bounds=dict(x=0, y=0, w=CELL, h=CELL), pivot=dict(x=PIVOT[0], y=PIVOT[1]))])]))
    json.dump(js, open(os.path.join(OUT, 'chr_sheldon.json'), 'w'), indent=1)
    meta = dict(id='chr_sheldon', version='v0', sheet='chr_sheldon.png', atlas='chr_sheldon.json',
                frame=[CELL, CELL], pivot_px=list(PIVOT), pivot_norm=[PIVOT[0]/CELL, PIVOT[1]/CELL],
                body_height_px=100, palette='palettes/bbt_sheldon.gpl', camera=dict(projection='2:1 dimetric', elevation_deg=30),
                dirs=DIRS8, mirror=MIRROR, decals_on_mirror=['emblem'],
                anims={name: dict(frames=n, fps=fps, loop=loop, dirs=dirs, frame_ms=ms,
                                  **(dict(holds_ms={str(k): v for k, v in HOLDS.items()},
                                          bubble_cues=[dict(frame=k, text='Penny.') for k in HOLDS]) if name == 'knock_knock_penny' else {}))
                       for name, n, fps, loop, dirs, fn, ms in ANIMS},
                notes='Procedurally rendered from tools/sheldon_rig.py (SDF proxy rig) + tools/compose_sheldon.py. Mirrored dirs re-stamp the emblem unflipped.')
    json.dump(meta, open(os.path.join(OUT, 'chr_sheldon.meta.json'), 'w'), indent=1)
    # ---------- QA ----------
    pal = load_gpl(GPL)
    viol = palette_violations(sheet, pal)
    tops, bots, cx = [], [], []
    for name, d, imgs, cells in layout:
        for im in imgs:
            a = im[..., 3] > 0; ys = np.where(a.any(1))[0]; tops.append(ys[0]); bots.append(ys[-1])
    qa = dict(palette_violations=int(viol if np.isscalar(viol) else len(viol)), head_top_min=int(min(tops)), head_top_max=int(max(tops)),
              lowest_px_min=int(min(bots)), lowest_px_max=int(max(bots)), frames=len(frames), sheet=[W, H],
              alpha_values=sorted(set(np.unique(sheet[..., 3]).tolist())), seconds=round(time.time()-t0))
    print(json.dumps(qa)); json.dump(qa, open(os.path.join(OUT, 'refs', 'qa_report.json'), 'w'), indent=1)
    np.save('/tmp/sheldon_layout.npy', np.array([0]))
    # ---------- previews ----------
    make_gifs({(n, d): imgs for n, d, imgs, _ in layout}, pal)

def stage(im, bg=(201, 206, 214), shadow=(140, 143, 148), bubble=None):
    """4x preview cell on a neutral floor colour with a 40x10 shadow ellipse under the pivot"""
    base = Image.new('RGBA', (CELL, CELL), bg + (255,))
    dr = ImageDraw.Draw(base); dr.ellipse((PIVOT[0]-20, PIVOT[1]-5, PIVOT[0]+19, PIVOT[1]+4), fill=shadow + (255,))
    base.alpha_composite(Image.fromarray(im))
    big = base.resize((CELL*4, CELL*4), Image.NEAREST)
    if bubble:
        d = ImageDraw.Draw(big)
        try: f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30)
        except Exception: f = ImageFont.load_default()
        x0, y0 = 300, 6; tw = d.textlength(bubble, font=f)
        d.rounded_rectangle((x0, y0, x0+tw+28, y0+50), 12, fill=(244, 241, 234), outline=(26, 20, 32), width=4)
        d.polygon([(x0+20, y0+48), (x0+44, y0+48), (x0+8, y0+76)], fill=(244, 241, 234), outline=(26, 20, 32))
        d.text((x0+14, y0+7), bubble, font=f, fill=(26, 20, 32))
    return big.convert('RGB')

def grid(cells, ncol):
    nrow = (len(cells) + ncol - 1) // ncol
    g = Image.new('RGB', (ncol*512, nrow*512), (201, 206, 214))
    for i, c in enumerate(cells): g.paste(c, ((i % ncol)*512, (i // ncol)*512))
    return g

def save_gif(path, frames, durs):
    q = [f.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    q[0].save(path, save_all=True, append_images=q[1:], duration=durs, loop=0, disposal=1, optimize=False)

def make_gifs(A, pal):
    for name, n, dirs, ncol in (('walk', 8, DIRS8, 4), ('idle', 4, DIRS8, 4)):
        fr = [grid([stage(A[(name, d)][k]) for d in dirs], ncol) for k in range(n)]
        ms = ANIMS_BY[name][6]
        save_gif(os.path.join(OUT, f'{name}_8dir_4x.gif'), fr, [ms]*n)
    for d in DIRS8:
        save_gif(os.path.join(OUT, f'walk_{d}_4x.gif'), [stage(A[('walk', d)][k]) for k in range(8)], [100]*8)
    kd = ['SW', 'NW', 'NE', 'SE']
    fr = [grid([stage(A[('knock_knock_penny', d)][k], bubble=('Penny.' if k in HOLDS else None)) for d in kd], 2) for k in range(16)]
    save_gif(os.path.join(OUT, 'knock_4d_4x.gif'), fr, [HOLDS.get(k, 125) for k in range(16)])
    # refs contact sheet of S frames for quick review
    cs = grid([stage(A[('idle', 'S')][0]), stage(A[('walk', 'S')][0]), stage(A[('walk', 'SW')][2]),
               stage(A[('walk', 'W')][0]), stage(A[('knock_knock_penny', 'SW')][3], bubble='Penny.')], 5)
    cs.save(os.path.join(OUT, 'refs', 'contact_key_poses_4x.png'))

if __name__ == '__main__':
    main()
