"""Contact strips of the built walk sheets (characters/<cid>/ai/chr_<cid>_walk.*), stride / pass frames marked.
   python3 tools/ai_import/walk8_strip.py [--dirs W,SW] [--out env/renders/walk/cast_walk8_W_SW.png] [cid ...]"""
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAST = ['penny', 'sheldon', 'leonard', 'howard', 'raj', 'amy', 'bernadette']
MODE_COL = {'walk8': (120, 220, 120), 'pick4': (240, 200, 90), 'synth4': (240, 120, 110)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cids', nargs='*'); ap.add_argument('--dirs', default='W,SW')
    ap.add_argument('--out', default='env/renders/walk/cast_walk8_W_SW.png'); ap.add_argument('--scale', type=int, default=2)
    a = ap.parse_args(); cids = a.cids or CAST; dirs = a.dirs.split(',')
    y0, y1, x0, x1 = 12, 124, 22, 106; cw, ch = x1 - x0, y1 - y0; lw = 120
    rows = [(c, d) for c in cids for d in dirs]
    out = Image.new('RGB', (lw + 8 * cw, 22 + len(rows) * (ch + 14)), (46, 46, 54)); D = ImageDraw.Draw(out)
    D.text((4, 4), 'walk sheets  green S = stride (contact)  blue P = passing (legs together)  '
           'mode: walk8 = drawn 8 / pick4 = 4 drawn frames / synth4 = synthesized fallback', fill=(230, 230, 230))
    for r, (cid, d) in enumerate(rows):
        j = json.load(open(f'{ROOT}/characters/{cid}/ai/chr_{cid}_walk.json')); m = j['meta']
        im = np.array(Image.open(f'{ROOT}/characters/{cid}/ai/chr_{cid}_walk.png').convert('RGBA'))
        tag = next(t for t in m['frameTags'] if t['name'] == f'walk_{d}'); info = m['rows'].get(d, {})
        mode = info.get('mode', '?'); ff = info.get('frames_from')
        oy = 22 + r * (ch + 14); D.line([(0, oy + ch + 12), (out.width, oy + ch + 12)], fill=(80, 80, 90))
        D.text((4, oy + 30), f'{cid}', fill=(255, 255, 255)); D.text((4, oy + 44), f'{d}', fill=(255, 255, 255))
        D.text((4, oy + 58), mode, fill=MODE_COL.get(mode, (200, 200, 200)))
        if mode == 'pick4' and ff: D.text((4, oy + 72), 'from ' + ','.join(map(str, ff)), fill=(200, 200, 200))
        D.line([(lw, oy + 104 - y0), (out.width, oy + 104 - y0)], fill=(110, 50, 50))
        for k in range(tag['from'], tag['to'] + 1):
            fr = j['frames'][k]['frame']; t = im[fr['y']:fr['y'] + 128, fr['x']:fr['x'] + 128][y0:y1, x0:x1]
            i = k - tag['from']; ox = lw + i * cw; ti = Image.fromarray(np.ascontiguousarray(t)); out.paste(ti, (ox, oy), ti)
            lab, col = ('S', (90, 230, 90)) if i in info.get('contact', []) else ('P', (110, 160, 255)) if i in info.get('passing', []) else ('', None)
            D.text((ox + 2, oy), str(i), fill=(200, 200, 200))
            if lab: D.rectangle([ox + 4, oy + ch + 2, ox + cw - 4, oy + ch + 9], fill=col); D.text((ox + cw // 2 - 3, oy + ch), lab, fill=(0, 0, 0))
    os.makedirs(os.path.dirname(os.path.join(ROOT, a.out)), exist_ok=True)
    out.resize((out.width * a.scale, out.height * a.scale), Image.NEAREST).save(os.path.join(ROOT, a.out), optimize=True)
    print(a.out, out.size)


if __name__ == '__main__':
    main()
