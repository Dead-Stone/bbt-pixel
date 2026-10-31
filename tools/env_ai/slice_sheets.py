"""Slice Mohan's ChatGPT environment sheets (magenta bg) into raw object cutouts by connected components.
Label text (dark glyph rows under each object) is detected and dropped.
Usage: python3 tools/env_ai/slice_sheets.py  -> refs_ai/chatgpt/env/sliced/<sheet>/<nn>.png + index.json + _contact.png"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = f'{ROOT}/refs_ai/chatgpt/env'
SHEETS = ['floors_walls_v1', '4A_furniture_v1', '4B_furniture_v1', 'fixups_v1', 'fixups_v2']

def keymask(a):
    """alpha 0..255 from magenta distance (tolerant key)"""
    r, g, b = (a[..., i].astype(int) for i in range(3))
    m = np.minimum(r, b) - g                       # magenta-ness
    mag = (m > 150) & (np.abs(r - b) < 70)
    soft = (m > 70) & (np.abs(r - b) < 90) & ~mag  # blended rim
    al = np.where(mag, 0, 255).astype(np.uint8)
    al[soft] = 128
    return al

def drop_label(m, lum):
    """remove glyph components of a caption that touches the object (bottom band, small, dark)"""
    lab, n = ndi.label(m, structure=np.ones((3, 3)))
    H = m.shape[0]; out = m.copy()
    for i, sl in enumerate(ndi.find_objects(lab)):
        h = sl[0].stop - sl[0].start; cm = lab[sl] == i + 1
        if h <= 24 and cm.sum() < 500 and sl[0].start > H - 46 and lum[sl][cm].mean() < 110: out[sl][cm] = False
    return out

def slice_sheet(name):
    a = np.array(Image.open(f'{SRC}/{name}.png').convert('RGB'))
    al = keymask(a); fg = al > 0
    lab, n = ndi.label(ndi.binary_dilation(fg, iterations=3))
    objs = ndi.find_objects(lab)
    lum = a.astype(int) @ np.array([30, 59, 11]) // 100
    groups = []
    for i, sl in enumerate(objs):
        m = (lab[sl] == i + 1) & fg[sl]
        if m.sum() < 30: continue
        h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
        dark = (lum[sl][m] < 70).mean()
        is_text = h <= 44 and dark > 0.55
        groups.append(dict(sl=sl, n=int(m.sum()), text=bool(is_text), dark=float(dark), h=h, w=w, id=i + 1))
    out = f'{SRC}/sliced/{name}'; os.makedirs(out, exist_ok=True)
    objs_ = [g for g in groups if not g['text']]
    objs_.sort(key=lambda g: (g['sl'][0].start // 60, g['sl'][1].start))
    # row-major order: cluster by vertical centre into rows
    objs_.sort(key=lambda g: (g['sl'][0].start + g['sl'][0].stop) / 2)
    rows, cur = [], []
    for g in objs_:
        c = (g['sl'][0].start + g['sl'][0].stop) / 2
        if cur and c - np.mean([(q['sl'][0].start + q['sl'][0].stop) / 2 for q in cur]) > 70: rows.append(cur); cur = []
        cur.append(g)
    if cur: rows.append(cur)
    order = [g for r in rows for g in sorted(r, key=lambda q: q['sl'][1].start)]
    idx = []
    for k, g in enumerate(order):
        sl = g['sl']; m = (lab[sl] == g['id']) & fg[sl]
        m = drop_label(m, lum[sl])
        if m.sum() < 200: continue
        ys, xs = np.nonzero(m); sl = (slice(sl[0].start + ys.min(), sl[0].start + ys.max() + 1), slice(sl[1].start + xs.min(), sl[1].start + xs.max() + 1))
        m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]; g['w'] = m.shape[1]; g['h'] = m.shape[0]
        rgba = np.dstack([a[sl], np.where(m, al[sl], 0)]).astype(np.uint8)
        Image.fromarray(rgba).save(f'{out}/{k:02d}.png')
        idx.append(dict(k=k, x=int(sl[1].start), y=int(sl[0].start), w=int(g['w']), h=int(g['h']), px=int(m.sum())))
    json.dump(idx, open(f'{out}/index.json', 'w'), indent=1)
    # contact sheet with indices
    cs = Image.fromarray(a).convert('RGBA'); dr = ImageDraw.Draw(cs)
    for e in idx:
        dr.rectangle((e['x'], e['y'], e['x'] + e['w'], e['y'] + e['h']), outline=(0, 255, 0))
        dr.rectangle((e['x'], e['y'], e['x'] + 22, e['y'] + 12), fill=(0, 0, 0)); dr.text((e['x'] + 2, e['y']), str(e['k']), fill=(255, 255, 0))
    cs.save(f'/tmp/contact_{name}.png')
    return len(idx), sum(g['text'] for g in groups)

if __name__ == '__main__':
    for s in SHEETS: print(s, slice_sheet(s))
