"""4x before/after of Sheldon key poses: top row v0 (refs/v0/chr_sheldon.png), bottom row v1."""
import os, numpy as np
from PIL import Image, ImageDraw, ImageFont
D = '/workspace/bbt-pixel/characters/sheldon'
DIRS8 = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']; K4 = ['SW', 'NW', 'NE', 'SE']
def cell(sheet, base_row, rows_per, di, k):
    r = base_row + di * rows_per + k // 12; c = k % 12
    return sheet.crop((c*128, r*128, c*128+128, r*128+128))
def pick(sheet, v):
    kp = 2  # knock rows per dir in both versions
    hold = 3 if v == 0 else 7; contact = 1 if v == 0 else 2; closed = 0 if v == 0 else 1
    return [('idle S', cell(sheet, 0, 1, 0, 0)), ('idle SW', cell(sheet, 0, 1, 1, 0)), ('idle W', cell(sheet, 0, 1, 2, 0)),
            ('walk SW f2', cell(sheet, 8, 1, 1, 2)), ('walk E f0 (mirror)', cell(sheet, 8, 1, 6, 0)), ('walk N f0', cell(sheet, 8, 1, 4, 0)),
            ('knock SW contact', cell(sheet, 16, kp, 0, contact)), ('knock SW hold', cell(sheet, 16, kp, 0, hold)),
            ('knock NW contact', cell(sheet, 16, kp, 1, contact)), ('blink S closed', cell(sheet, 24, 1, 0, closed))]
v0 = Image.open(os.path.join(D, 'refs/v0/chr_sheldon.png')).convert('RGBA'); v1 = Image.open(os.path.join(D, 'chr_sheldon.png')).convert('RGBA')
rows = [pick(v0, 0), pick(v1, 1)]
CW, CH, TOP = 88, 116, 10   # crop 20..108 x 8..124
n = len(rows[0]); LBL = 40
out = Image.new('RGB', (n*CW*4 + 160, 2*(CH*4 + LBL) + 10), (201, 206, 214)); d = ImageDraw.Draw(out)
try: f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22); fs = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
except Exception: f = fs = ImageFont.load_default()
for ri, row in enumerate(rows):
    y0 = ri*(CH*4 + LBL) + 5
    d.text((10, y0 + CH*2), ['v0', 'v1'][ri], font=f, fill=(26, 20, 32))
    for i, (name, im) in enumerate(row):
        bg = Image.new('RGBA', (128, 128), (201, 206, 214, 255)); bg.alpha_composite(im)
        c = bg.crop((20, 8, 108, 124)).resize((CW*4, CH*4), Image.NEAREST)
        out.paste(c.convert('RGB'), (160 + i*CW*4, y0 + LBL))
        d.text((160 + i*CW*4 + 6, y0 + 8), name, font=fs, fill=(26, 20, 32))
out.save(os.path.join(D, 'chr_sheldon_before_after_4x.png')); print(out.size)
