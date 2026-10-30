"""Cast arms before/after sheet: idle S, walk SW mid-swing, walk W mid-swing, at 4x.
python3 tools/v2/arms_before_after.py <before-rev> <out.png>"""
import sys, json, io, subprocess
from PIL import Image, ImageDraw
CAST = ['sheldon', 'leonard', 'penny', 'howard', 'raj', 'bernadette', 'amy']
SHOTS = [('idle_S_00', 'idle S'), ('walk_SW_02', 'walk SW'), ('walk_W_02', 'walk W'), ('walk_S_06', 'walk S')]
CROP = (24, 6, 104, 124); SC = 4
def loader(cid, rev):
    if rev:
        g = lambda f: subprocess.check_output(['git', 'show', f'{rev}:characters/{cid}/{f}'])
        J = json.loads(g(f'chr_{cid}.json')); im = Image.open(io.BytesIO(g(f'chr_{cid}.png'))).convert('RGBA')
    else:
        J = json.load(open(f'characters/{cid}/chr_{cid}.json')); im = Image.open(f'characters/{cid}/chr_{cid}.png').convert('RGBA')
    F = {x['filename']: x['frame'] for x in J['frames']}
    return lambda n: im.crop((F[f'chr_{cid}_{n}']['x'], F[f'chr_{cid}_{n}']['y'], F[f'chr_{cid}_{n}']['x'] + 128, F[f'chr_{cid}_{n}']['y'] + 128))
rev, out = sys.argv[1], sys.argv[2]
cw, ch = (CROP[2] - CROP[0]) * SC, (CROP[3] - CROP[1]) * SC
gap = 24; W = 100 + 2 * len(SHOTS) * cw + gap; H = 40 + len(CAST) * ch
S = Image.new('RGB', (W, H), (40, 42, 50)); D = ImageDraw.Draw(S)
D.text((100, 12), f'BEFORE ({rev})', fill=(255, 150, 150)); D.text((100 + len(SHOTS) * cw + gap, 12), 'AFTER (anatomical arms)', fill=(150, 240, 150))
for r, cid in enumerate(CAST):
    D.text((8, 40 + r * ch + ch // 2), cid, fill=(230, 230, 230))
    for b, src in enumerate((rev, None)):
        get = loader(cid, src)
        for i, (n, lab) in enumerate(SHOTS):
            bg = Image.new('RGBA', (128, 128), (176, 178, 190, 255)); bg.alpha_composite(get(n))
            x = 100 + b * (len(SHOTS) * cw + gap) + i * cw; y = 40 + r * ch
            S.paste(bg.crop(CROP).convert('RGB').resize((cw, ch), Image.NEAREST), (x, y))
            if r == 0: D.text((x + 4, 28), lab, fill=(200, 200, 200))
S.save(out); print(out, S.size)
