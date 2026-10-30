"""v2 comparison images.
  python3 compare.py before_after <cid>        -> characters/<cid>/chr_<cid>_before_after_4x.png
  python3 compare.py style_test sheldon penny  -> characters/style_test_v2/style_test_v2_4x.png
  python3 compare.py plain <cid> [<cid> ...]   -> characters/style_test_v2/plain_clothes_4x.png"""
import sys, os, json, numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BG = (201, 206, 214); SH = (150, 154, 160)
try: FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
except Exception: FONT = ImageFont.load_default()

def sheet(cid, v1=False):
    d = os.path.join(ROOT, 'characters', cid, 'refs', 'v1_style') if v1 else os.path.join(ROOT, 'characters', cid)
    js = json.load(open(os.path.join(d, f'chr_{cid}.json'))); sh = np.array(Image.open(os.path.join(d, f'chr_{cid}.png')).convert('RGBA'))
    F = {f['filename']: f['frame'] for f in js['frames']}
    return lambda n: sh[F[f'chr_{cid}_{n}']['y']:F[f'chr_{cid}_{n}']['y'] + 128, F[f'chr_{cid}_{n}']['x']:F[f'chr_{cid}_{n}']['x'] + 128].copy()

def stage(fr, crop=(4, 126, 24, 104), z=4):
    y0, y1, x0, x1 = crop
    base = Image.new('RGBA', (128, 128), BG + (255,))
    ImageDraw.Draw(base).ellipse((64 - 18, 116 - 4, 64 + 17, 116 + 3), fill=SH + (255,))
    base.alpha_composite(Image.fromarray(fr))
    return base.crop((x0, y0, x1, y1)).resize(((x1 - x0) * z, (y1 - y0) * z), Image.NEAREST).convert('RGB')

def grid(rows, rlabels, clabels, title):
    cw, ch = rows[0][0].size; lw = 150; th = 40
    W = lw + cw * max(len(r) for r in rows); H = th + 30 + ch * len(rows)
    g = Image.new('RGB', (W, H), (236, 236, 232)); d = ImageDraw.Draw(g)
    d.text((10, 8), title, font=FONT, fill=(20, 20, 30))
    for j, c in enumerate(clabels): d.text((lw + j * cw + 8, th + 4), c, font=FONT, fill=(60, 60, 80))
    for i, (r, l) in enumerate(zip(rows, rlabels)):
        for k, l2 in enumerate(l.split('\n')): d.text((8, th + 30 + i * ch + ch // 2 - 14 + 26 * k), l2, font=FONT, fill=(20, 20, 30))
        for j, im in enumerate(r):
            if im is not None: g.paste(im, (lw + j * cw, th + 30 + i * ch))
    return g

def ai_cell(cid, d, ref):
    """the AI master art for one facing, scaled to the same pixel scale as the 128 frame (smooth, pre-cleanup)"""
    MD = os.path.join(ROOT, 'characters', cid, 'refs', 'v2_master'); F = json.load(open(os.path.join(MD, 'fits.json')))[d]
    im = Image.open(os.path.join(MD, 'master_strip.jpg')).convert('RGB'); s = F['s']
    # frame (0..128) -> strip coordinates
    x0 = F['bx0'] + (0 - F['ox']) * s; y0 = F['by0'] + (0 - F['oy']) * s
    big = Image.new('RGB', (int(128 * s) + 2, int(128 * s) + 2), (255, 255, 255)); big.paste(im, (int(-x0), int(-y0)))
    fr = big.resize((128, 128), Image.LANCZOS)
    a = np.array(fr); m = (a.min(-1) < 235)
    rgba = np.dstack([a, np.where(m, 255, 0).astype(np.uint8)])
    return stage(rgba)

def greyout(fr, cid, v1):
    """plain-clothes check: every pixel whose nearest rig colour is clothing (not skin/hair/lips) becomes
    neutral grey; the head zone (hair + face features + outline) is kept whole"""
    sys.path.insert(0, os.path.join(ROOT, 'tools')); import char_rig as R; R.set_character(cid)
    skip = ('ink', 'ink_2', 'shadow_violet', 'grey_dk', 'grey', 'grey_lt', 'paper', 'white_hi')
    names = [k for k in R.C if k not in skip and not k.startswith('uni_')]
    A = np.array([R.C[k] for k in names], float)
    keepcls = np.array([k.startswith('skin') or k.startswith('hair') or k == 'lips' for k in names])
    rgb = fr[..., :3].astype(float); op = fr[..., 3] > 0
    near = ((rgb[..., None, :] - A) ** 2 * np.array([0.30, 0.59, 0.11])).sum(-1).argmin(-1)
    ys = np.where(op.any(1))[0]; top = ys[0]; ht = ys[-1] - top
    yy = np.arange(128)[:, None].repeat(128, 1)
    skincls = np.array([k.startswith('skin') for k in names])
    keep = skincls[near] | (keepcls[near] & (yy < top + ht * 0.42) & ~np.array([k == 'lips' for k in names])[near])
    keep |= yy < top + ht * 0.14
    L = rgb @ np.array([0.299, 0.587, 0.114]); g = (118 + (L - 128) * 0.6).clip(28, 225)
    out = fr.copy(); m = op & ~keep
    out[m, 0] = g[m]; out[m, 1] = g[m]; out[m, 2] = np.minimum(g[m] + 4, 255)
    return out

if __name__ == '__main__':
    mode = sys.argv[1]; cids = sys.argv[2:]
    if mode == 'before_after':
        cid = cids[0]; v1, v2 = sheet(cid, True), sheet(cid)
        names = ['idle_S_00', 'idle_SW_00', 'idle_W_00', 'idle_NW_00', 'idle_N_00', 'walk_SW_02', 'walk_W_04', 'blink_S_01']
        rows = [[stage(v1(n)) for n in names], [stage(v2(n)) for n in names]]
        g = grid(rows, ['v1\n(rig)', 'v2\n(AI master\n+ rig anim)'], [n.replace('_0', ' f') for n in names], f'{cid}: v1 vs v2 (4x, 128px cells, same pivot)')
        p = os.path.join(ROOT, 'characters', cid, f'chr_{cid}_before_after_4x.png'); g.save(p); print(p)
    elif mode == 'style_test':
        rows, labels = [], []
        names = ['idle_S_00', 'idle_SW_00', 'idle_N_00', 'walk_S_02', 'walk_S_06']
        for cid in cids:
            v1, v2 = sheet(cid, True), sheet(cid)
            rows.append([stage(v1(n)) for n in names]); labels.append(f'{cid}\nv1 rig')
            rows.append([ai_cell(cid, d, None) for d in ('S', 'SW', 'N')] + [None, None]); labels.append(f'{cid}\n(a) raw AI\nart, 128px')
            rows.append([stage(v2(n)) for n in names]); labels.append(f'{cid}\n(a) hybrid\nv2 final')
        g = grid(rows, labels, ['idle S', 'idle SW', 'idle N', 'walk S f2', 'walk S f6'], 'v2 style test: v1 rig  |  raw AI art  |  v2 (AI master, cleaned, rig-animated)')
        p = os.path.join(ROOT, 'characters', 'style_test_v2', 'style_test_v2_4x.png'); g.save(p); print(p)
    elif mode == 'plain':
        rows, labels = [], []
        for ver in ('v1', 'v2'):
            r = []
            for cid in cids:
                try: s = sheet(cid, ver == 'v1')
                except FileNotFoundError: s = sheet(cid)   # no v1 backup -> current
                r.append(stage(greyout(s('idle_SW_00'), cid, ver == 'v1')))
            rows.append(r); labels.append(f'{ver}\ngrey outfits')
        g = grid(rows, labels, cids, 'plain-clothes check: outfits greyed, only skin/hair/face kept (idle SW)')
        p = os.path.join(ROOT, 'characters', 'style_test_v2', 'plain_clothes_4x.png'); g.save(p); print(p)
