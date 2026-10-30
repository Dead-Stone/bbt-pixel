"""characters/cast_lineup_4x.png: all 7 characters, idle S frame 0, on one shared pivot line (y=116), labeled,
heights scaled from the actors' real heights (Sheldon 185 cm = 100 px)."""
import json, numpy as np
from PIL import Image, ImageDraw, ImageFont
import char_rig as R
ROOT = '/workspace/bbt-pixel'
ORDER = ['sheldon', 'leonard', 'penny', 'howard', 'raj', 'bernadette', 'amy']
NAMES = {'sheldon': 'Sheldon', 'leonard': 'Leonard', 'penny': 'Penny', 'howard': 'Howard', 'raj': 'Raj', 'bernadette': 'Bernadette', 'amy': 'Amy'}
CW, TOP, S = 76, 8, 4
def frame(cid):
    sheet = np.array(Image.open(f'{ROOT}/characters/{cid}/chr_{cid}.png').convert('RGBA'))
    js = json.load(open(f'{ROOT}/characters/{cid}/chr_{cid}.json'))
    fr = js['frames']; nm = f'chr_{cid}_idle_S_00'
    f = fr[nm] if isinstance(fr, dict) else next(x for x in fr if x.get('filename', x.get('name')) == nm)
    f = f.get('frame', f)
    return sheet[f['y']:f['y'] + f['h'], f['x']:f['x'] + f['w']]
W, H = CW * len(ORDER) + 40, 128 + 30
can = Image.new('RGBA', (W * S, H * S), (205, 210, 220, 255)); d = ImageDraw.Draw(can)
try: font = ImageFont.truetype('DejaVuSans-Bold.ttf', 30); fsm = ImageFont.truetype('DejaVuSans.ttf', 22)
except Exception: font = fsm = ImageFont.load_default()
# height guides every 10 px above the pivot line (= 18.5 cm at this scale)
for h in range(0, 101, 10):
    y = (116 - h + TOP) * S
    d.line([(36 * S, y), (W * S, y)], fill=(185, 190, 202, 255), width=2)
    d.text((4, y - 12), f'{h}px', fill=(120, 125, 140, 255), font=fsm)
d.line([(36 * S, (116 + TOP) * S), (W * S, (116 + TOP) * S)], fill=(200, 40, 40, 255), width=4)
info = {}
for i, cid in enumerate(ORDER):
    im = frame(cid); a = im[..., 3] > 0; top = int(np.where(a.any(1))[0][0])
    x0 = 40 + i * CW
    cell = Image.fromarray(im[:, 64 - CW // 2: 64 + CW // 2]).resize((CW * S, 128 * S), Image.NEAREST)
    can.alpha_composite(cell, (x0 * S, TOP * S))
    hpx = 116 - top; info[cid] = dict(cm=R.REAL_CM[cid], px=hpx)
    d.line([((x0 + 8) * S, (top + TOP) * S), ((x0 + CW - 8) * S, (top + TOP) * S)], fill=(60, 90, 200, 255), width=2)
    cx = (x0 + CW / 2) * S
    for txt, fnt, yy in ((NAMES[cid], font, 128 + TOP + 4), (f"{R.REAL_CM[cid]} cm  /  {hpx} px", fsm, 128 + TOP + 13)):
        tw = d.textlength(txt, font=fnt); d.text((cx - tw / 2, yy * S), txt, fill=(30, 32, 40, 255), font=fnt)
can.convert('RGB').save(f'{ROOT}/characters/cast_lineup_4x.png')
json.dump(dict(scale='Sheldon 185 cm = 100 px; pivot line y=116; heights = idle S head top to pivot', cast=info),
          open(f'{ROOT}/characters/cast_lineup.json', 'w'), indent=1)
print(info)
