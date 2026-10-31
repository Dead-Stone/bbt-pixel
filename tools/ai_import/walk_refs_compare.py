"""Side-by-side walk comparison: online refs (CC0 / CC-BY-SA, see refs_ai/walk_refs/SOURCES.md) vs our walk8 sheets.
Every figure is scaled so its body height is ~96 px (nearest-neighbour). Per frame: red bars = pixels touching the ground,
grey guide = frame 0's front-foot centre (a planted foot should drift back from it), cyan tick = head top (bob),
number = foot-band spread px (source res), C/P = widest/narrowest frames. Read-only: does not touch the game.
Usage: python3 tools/ai_import/walk_refs_compare.py [out.png]"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import walk_refs_measure as M
ROOT = M.ROOT
F = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
fnt = ImageFont.truetype(F, 13); fntb = ImageFont.truetype(F.replace('Sans.ttf', 'Sans-Bold.ttf'), 15); fnts = ImageFont.truetype(F, 10)
LPC, BEE, CD = (M.REFS[k][0] for k in ['LPC (Redshrike)', 'Bumblebee 8dir', 'Chrome District 22deg'])
SECTIONS = [
    ('W  (side view: stride, planted foot, arms)', [
        ('LPC male (Redshrike) W, 8 fr', LPC, 'W'), ('8-Dir Walk (Ordinary Bumblebee) W, 8 fr', BEE, 'W'), ('CHROME DISTRICT 22deg W, 6 fr', CD, 'W'),
        ('OURS raj W', 'raj', 'W'), ('OURS penny W', 'penny', 'W'), ('OURS sheldon W', 'sheldon', 'W')]),
    ('SW  (3/4 view)', [
        ('8-Dir Walk (Ordinary Bumblebee) SW', BEE, 'SW'), ('CHROME DISTRICT 22deg SW', CD, 'SW'), ('OURS raj SW', 'raj', 'SW'), ('OURS penny SW', 'penny', 'SW')]),
    ('S  (toward camera: how a step reads)', [
        ('LPC male S', LPC, 'S'), ('8-Dir Walk (Bumblebee) S', BEE, 'S'), ('OURS raj S', 'raj', 'S'), ('OURS penny S', 'penny', 'S')]),
    ('N  (away from camera)', [
        ('LPC male N', LPC, 'N'), ('8-Dir Walk (Bumblebee) N', BEE, 'N'), ('OURS penny N', 'penny', 'N'), ('OURS sheldon N', 'sheldon', 'N')]),
]
CELL, LAB, TH = 104, 250, 96

def frames_of(src, d):
    return M.ours(src, d) if isinstance(src, str) else src(d)

def strip(frames):
    ms = M.metrics(frames); arrs = [np.array(f)[:, :, 3] > 24 for f in frames]
    s = TH / ms['H']; out = []
    pts = [np.argwhere(a) for a in arrs]; bot = max(p[:, 0].max() for p in pts); top = min(p[:, 0].min() for p in pts)
    cx = int(np.median(np.concatenate([p[:, 1] for p in pts])))
    g0 = np.where(arrs[0][bot - 1:bot + 1].any(0))[0]
    front0 = None
    if len(g0):  # leftmost ground run centre in frame 0 (W/SW face left)
        e = g0[0]; r = [e]
        for x in g0[1:]:
            if x == r[-1] + 1: r.append(x)
            else: break
        front0 = (r[0] + r[-1]) / 2
    for i, (f, a) in enumerate(zip(frames, arrs)):
        c = Image.new('RGBA', (CELL, CELL + 30), (246, 244, 238, 255))
        w, h = f.size; fs = f.resize((max(1, round(w * s)), max(1, round(h * s))), Image.NEAREST)
        ox = CELL // 2 - round(cx * s); oy = CELL - 6 - round(bot * s)
        d = ImageDraw.Draw(c)
        if front0 is not None: d.line([(ox + front0 * s, 4), (ox + front0 * s, CELL)], fill=(170, 170, 170), width=1)
        c.alpha_composite(fs, (ox, oy)) if ox >= 0 and oy >= 0 else c.paste(fs, (ox, oy), fs)
        d = ImageDraw.Draw(c)
        row = a[bot - 1:bot + 1].any(0); xs = np.where(row)[0]
        for x in xs: d.line([(ox + x * s, CELL - 4), (ox + (x + 1) * s - 1, CELL - 4)], fill=(220, 40, 40), width=3)
        ty = oy + round(min(np.argwhere(a)[:, 0]) * s); d.line([(2, ty), (12, ty)], fill=(0, 170, 200), width=2)
        tag = 'C' if ms['spreads'][i] == max(ms['spreads']) else ('P' if ms['spreads'][i] == min(ms['spreads']) else '')
        d.text((4, CELL + 2), f"{i}", font=fnts, fill=(90, 90, 90)); d.text((22, CELL + 2), f"sp {ms['spreads'][i]}", font=fnts, fill=(40, 40, 40))
        d.text((CELL - 16, CELL + 2), tag, font=fntb, fill=(200, 30, 30) if tag == 'C' else (30, 60, 200))
        d.text((4, CELL + 15), f"bob {ms['tops'][i]}", font=fnts, fill=(0, 130, 160))
        out.append(c)
    return out, ms

def main(path):
    rows = []
    for title, items in SECTIONS:
        rows.append(('H', title, None, None))
        for lab, src, d in items: rows.append(('R', lab, *strip(frames_of(src, d))))
    W = LAB + 8 * (CELL + 4) + 10; H = 70 + sum(34 if r[0] == 'H' else CELL + 36 for r in rows) + 10
    img = Image.new('RGB', (W, H), (255, 255, 255)); d = ImageDraw.Draw(img)
    d.text((10, 8), 'Walk cycles: online refs vs ours (all scaled to ~96 px body height, nearest-neighbour)', font=fntb, fill=(0, 0, 0))
    d.text((10, 30), 'red = pixels on the ground | grey line = frame-0 front foot (a planted foot should drift BACK from it) | cyan = head top | sp = foot spread px | C/P = widest/narrowest',
           font=fnts, fill=(60, 60, 60))
    d.text((10, 44), 'Refs: LPC Base Assets walkcycle by Stephen Challener (Redshrike), CC-BY-SA 3.0 / GPL 3.0 / OGA-BY 3.0; 8 Direction Walk Cycle by Ordinary Bumblebee, CC0; CHROME DISTRICT by booliebuilds, CC0',
           font=fnts, fill=(60, 60, 60))
    y = 70
    for kind, lab, cells, ms in rows:
        if kind == 'H':
            d.rectangle([0, y + 4, W, y + 30], fill=(40, 40, 52)); d.text((10, y + 9), lab, font=fntb, fill=(255, 255, 255)); y += 34; continue
        ours = lab.startswith('OURS')
        d.rectangle([0, y, LAB - 6, y + CELL + 30], fill=(255, 236, 214) if ours else (228, 238, 250))
        d.text((8, y + 6), lab, font=fntb if ours else fnt, fill=(0, 0, 0))
        d.text((8, y + 30), f"{ms['n']} frames, body {ms['H']} px", font=fnts, fill=(50, 50, 50))
        d.text((8, y + 44), f"bob {ms['bob']} px = {ms['bob_pct']}% H", font=fnts, fill=(50, 50, 50))
        d.text((8, y + 58), f"stride {ms['stride_pct']}% H, pass {ms['pass_pct']}%", font=fnts, fill=(50, 50, 50))
        d.text((8, y + 72), f"foot lift {ms['lift_pct']}% H", font=fnts, fill=(50, 50, 50))
        d.text((8, y + 86), f"arm/hand swing {ms['arm_pct']}% H", font=fnts, fill=(50, 50, 50))
        for i, c in enumerate(cells): img.paste(c.convert('RGB'), (LAB + i * (CELL + 4), y))
        y += CELL + 36
    os.makedirs(os.path.dirname(path), exist_ok=True); img.save(path); print(path, img.size)

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'env', 'renders', 'walk', 'walk_refs_compare.png'))
