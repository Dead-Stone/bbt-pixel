"""Seat contact sheet for floor4: every seat hook (sit type) rendered with the skinned furniture and a seated character,
two passes so each seat shows two different cast members and all 7 characters appear. -> env/renders/seat_contact_floor4.png"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
import build_env as B
from PIL import Image, ImageDraw
CAST = ['sheldon', 'leonard', 'penny', 'howard', 'raj', 'bernadette', 'amy']
def seats():
    out, cnt = [], {}
    for (iid, ox, oy, rot, st, z) in B.PLACE:
        i = cnt.get(iid, 0); cnt[iid] = i + 1
        for h in B.E.ITEMS[iid]['hooks']:
            if h['type'] in ('sit', 'perch'): out.append((iid, h['id'], i))
    return out
def origin():
    pts = [B.scr(x, y, z) for x in (0, 23) for y in (0, 8) for z in (0, 3.6, -1.7)]
    return int(min(p[0] for p in pts)) - 40, int(min(p[1] for p in pts)) - 24
def main(out=f'{B.ROOT}/env/renders/seat_contact_floor4.png'):
    S = seats(); mx, my = origin(); cells = []
    for p in range(2):
        chars, info = [], []
        for k, (iid, hid, i) in enumerate(S):
            cid = CAST[(k + p * 4) % 7]
            e = B.seat_char(cid, iid, hid, i); e['hook'] = f'{iid}.{hid}'; chars.append(e)
            info.append((iid, hid, cid, B.seat_place4(iid, hid, i)))
        im = B.compose('combined', chars)
        for (iid, hid, cid, sp) in info:
            sx, sy = B.scr(sp['seat'][0], sp['seat'][1], sp['seat_z']); sx -= mx; sy -= my
            c = im.crop((int(sx) - 80, int(sy) - 130, int(sx) + 80, int(sy) + 60)).resize((320, 380), Image.NEAREST).convert('RGB')
            d = ImageDraw.Draw(c); d.rectangle((0, 0, 319, 14), fill=(0, 0, 0))
            d.text((3, 2), f'{iid.replace("4a_","A:").replace("4b_","B:")}.{hid} {cid} z{sp["seat_z"]}', fill=(255, 255, 255))
            cells.append(c)
    n = len(cells); cols = 6; rows = (n + cols - 1) // cols
    sheet = Image.new('RGB', (cols * 320, rows * 380), (20, 16, 28))
    for k, c in enumerate(cells): sheet.paste(c, ((k % cols) * 320, (k // cols) * 380))
    sheet.save(out); return S, out
if __name__ == '__main__':
    S, out = main(*sys.argv[1:]); print(len(S), 'seats ->', out)
