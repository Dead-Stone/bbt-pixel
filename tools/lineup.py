"""4x side-by-side height check: Sheldon vs Leonard idle_00 at the shared pivot (64,116). Read-only on both sheets."""
import json, os, numpy as np
from PIL import Image, ImageDraw
ROOT = os.path.join(os.path.dirname(__file__), '..', 'characters')
def frame(cid, name):
    sh = np.array(Image.open(f'{ROOT}/{cid}/chr_{cid}.png').convert('RGBA'))
    fr = {f['filename']: f['frame'] for f in json.load(open(f'{ROOT}/{cid}/chr_{cid}.json'))['frames']}[f'chr_{cid}_{name}']
    return sh[fr['y']:fr['y']+128, fr['x']:fr['x']+128]
def crown(im):
    return int(np.nonzero(im[..., 3].any(1))[0][0])
DIRS = ['S', 'SW', 'W', 'SE']
BG = (201, 206, 214); S = 4; W = 128
cols = []
for d in DIRS:
    for cid in ('sheldon', 'leonard'):
        cols.append((cid, d, frame(cid, f'idle_{d}_00')))
img = Image.new('RGB', (W*S*len(cols)//2 + 0, 128*S + 40), BG)
dr = ImageDraw.Draw(img)
# pair = two frames overlapping 40 px so they stand shoulder to shoulder on the same pivot row
pair_w = (128 + 88) * S; img = Image.new('RGB', (pair_w*len(DIRS), 128*S + 44), BG); dr = ImageDraw.Draw(img)
for i, d in enumerate(DIRS):
    x0 = i*pair_w
    for j, cid in enumerate(('sheldon', 'leonard')):
        im = frame(cid, f'idle_{d}_00'); c = crown(im)
        big = Image.fromarray(im).resize((128*S, 128*S), Image.NEAREST)
        ox = x0 + j*88*S
        img.paste(big, (ox, 0), big)
        dr.line([(ox + 64*S - 30, c*S), (ox + 64*S + 30, c*S)], fill=(200, 40, 40), width=2)
        dr.text((ox + 64*S - 40, 128*S + 4), f'{cid} {d}  crown y={c}  h={116-c}px', fill=(30, 30, 40))
    dr.line([(x0, 116*S), (x0 + pair_w - 8, 116*S)], fill=(40, 120, 200), width=2)   # shared pivot row
    dr.text((x0 + 6, 116*S + 6), 'pivot y=116', fill=(40, 80, 160))
img.save(f'{ROOT}/leonard/chr_leonard_vs_sheldon_4x.png'); print('ok', img.size)
