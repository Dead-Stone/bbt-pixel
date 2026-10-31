"""One tile per seat type (item x sit_dir) across all locations, drawn exactly like the viewer, each with a seated
character in three poses: base sit, sit_eat (frame 1) and -- for Sheldon -- sit_write.  Usage:
python3 tools/sitcheck/seattypes.py OUT.png [scale]"""
import sys, os, json, math
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sitsheet as SS

def variant(cid, anim):
    j = json.load(open(f'{SS.ROOT}/characters/{cid}/chr_{cid}_sit.json'))
    fr = {f['dir']: f for f in j['frames'] if f.get('anim', 'sit') == 'sit'}
    if anim != 'sit':
        got = {f['dir']: f for f in j['frames'] if f.get('anim') == anim and f.get('k') == 1}
        if not got: return None
        fr = got
    return SS.CH[cid][0], fr

def main():
    out = sys.argv[1]; S = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    seen = {}; n = 0
    for loc in SS.LOCS:
        sc = json.load(open(f'{SS.W}/{loc}/scene.json'))
        for h in sc['hooks']:
            if h['type'] in ('sit', 'perch') and h.get('seat'):
                seen.setdefault((h['item'], h['sit_dir']), (loc, h))
    rows = []
    for (item, d), (loc, h) in sorted(seen.items()):
        cid = SS.CIDS[n % 7]; n += 1
        tiles = []
        for who, anim in [(cid, 'sit'), (cid, 'sit_eat'), ('sheldon', 'sit_write')]:
            v = variant(who, anim)
            if not v: continue
            SS.CH[(who, anim)] = v
            can, pts = SS.render(loc, [(h, (who, anim))])
            _, _, sx, sy, p = pts[0]
            c = can.crop((int(sx) - 56, int(sy) - 100, int(sx) + 56, int(sy) + 28)).resize((112 * S, 128 * S), Image.NEAREST)
            tiles.append((f'{who} {anim}', c))
        rows.append((f'{loc}  {item}  {d}  seat_z {h.get("seat_z", 0):.2f}', tiles))
    tw, th = 112 * S, 128 * S + 22
    sheet = Image.new('RGB', (3 * tw, len(rows) * th), (20, 18, 28)); dr = ImageDraw.Draw(sheet)
    for r, (lab, tiles) in enumerate(rows):
        for i, (l2, c) in enumerate(tiles):
            sheet.paste(c, (i * tw, r * th + 22)); dr.text((i * tw + 4, r * th + 4), (lab + '   ' if i == 0 else '') + l2, fill=(240, 230, 160))
    sheet.save(out); print(out, len(rows), 'seat types', sheet.size)
if __name__ == '__main__': main()
