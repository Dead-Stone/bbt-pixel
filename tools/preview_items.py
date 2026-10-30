"""dev helper: contact sheet of selected items (SW + one more rot) -> /tmp/v/<name>.png"""
import sys
from PIL import Image, ImageDraw
import build_env as B, env_items as E
def sheet(ids, out, rots=('SW', 'SE'), scale=1):
    cells = []
    for iid in ids:
        for r in rots:
            if r not in B.hook_rot.__globals__.get('ROTS_FOR', {}).get(E.ITEMS[iid]['rotation_class'], rots): pass
            try: cells.append((iid + ' ' + r, B.rend(iid, r)['img']))
            except Exception as e: print('ERR', iid, r, e)
    W = sum(Image.fromarray(c[1]).width + 8 for c in cells); Hh = max(Image.fromarray(c[1]).height for c in cells) + 14
    # wrap rows at 1600 px
    rows, cur, w = [], [], 0
    for c in cells:
        im = Image.fromarray(c[1]); 
        if w + im.width > 1600 and cur: rows.append(cur); cur, w = [], 0
        cur.append((c[0], im)); w += im.width + 8
    rows.append(cur)
    hs = [max(im.height for _, im in r) + 14 for r in rows]
    S = Image.new('RGBA', (1600, sum(hs)), (40, 40, 60, 255)); d = ImageDraw.Draw(S); y = 0
    for r, h in zip(rows, hs):
        x = 0
        for name, im in r:
            S.alpha_composite(im, (x, y + 12)); d.text((x, y), name[:28], fill=(255, 255, 255)); x += im.width + 8
        y += h
    if scale != 1: S = S.resize((S.width*scale, S.height*scale), Image.NEAREST)
    S.save(out); print(out, S.size)
if __name__ == '__main__':
    pre = sys.argv[1]; out = sys.argv[2]
    sheet([i for i in E.ITEMS if any(i.startswith(p) for p in pre.split(','))], out)
