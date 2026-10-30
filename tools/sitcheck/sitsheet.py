"""Contact sheet of every sit hook in every location with an occupying character, drawn exactly like the
viewer (bg + depth-sorted item slices + character sit frame).  Usage: python3 tools/sitcheck/sitsheet.py OUT.png [scale]"""
import sys, os, json, math
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W = f'{ROOT}/harness/world'
LOCS = ['floor4', 'ait_cafeteria', 'ait_physics', 'rest_amber_slice', 'street_exterior', 'raj_apartment']
CIDS = ['sheldon', 'leonard', 'penny', 'howard', 'raj', 'bernadette', 'amy']
sys.path.insert(0, f'{ROOT}/harness')
from seating import seat_place          # shared with sim (key, z) so the sheet shows what the viewer shows

def load_char(cid):
    j = json.load(open(f'{ROOT}/characters/{cid}/chr_{cid}_sit.json'))
    return Image.open(f'{ROOT}/characters/{cid}/chr_{cid}_sit.png').convert('RGBA'), {f['dir']: f for f in j['frames']}
CH = {c: load_char(c) for c in CIDS}

def render(loc, occupants):
    sc = json.load(open(f'{W}/{loc}/scene.json'))
    bg = Image.open(f'{W}/{loc}/bg.png').convert('RGBA'); spr = Image.open(f'{W}/{loc}/sprites.png').convert('RGBA')
    ox, oy = sc['origin']
    occ_ids = {h['id'] for h, _ in occupants}
    L = [(s['key'], 0, ('s', s)) for s in sc['sprites'] if s.get('hook') is None or s['hook'] in occ_ids]
    for i, (h, cid) in enumerate(occupants):
        p = seat_place(h)
        L.append((p['key'], 1, ('c', h, cid, p)))
    L.sort(key=lambda t: (t[0], t[1]))
    can = bg.copy(); pts = []
    for _, _, it in L:
        if it[0] == 's':
            s = it[1]; can.alpha_composite(spr.crop((s['ax'], s['ay'], s['ax'] + s['w'], s['ay'] + s['h'])), (s['x'], s['y']))
        else:
            _, h, cid, p = it; img, fr = CH[cid]; f = fr[p['dir']]
            x, y = p['pos']; sx = (x - y) * 64 - ox; sy = (x + y) * 32 - p['z'] * 64 - oy
            fx = f['frame']
            can.alpha_composite(img.crop((fx['x'], fx['y'], fx['x'] + 128, fx['y'] + 128)), (round(sx - f['seat'][0]), round(sy - f['seat'][1])))
            pts.append((h, cid, sx, sy, p))
    return can, pts

def main():
    out = sys.argv[1]; S = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    tiles = []; full = {}
    for loc in LOCS:
        sc = json.load(open(f'{W}/{loc}/scene.json'))
        hooks = [h for h in sc['hooks'] if h['type'] in ('sit', 'perch')]
        # several passes so overlapping hooks (table seat vs its chair) never share a render
        passes = []
        for h in hooks:
            for P in passes:
                if all(math.dist(h['pos'], q['pos']) > 0.9 for q in P): P.append(h); break
            else: passes.append([h])
        n = 0
        for pi, P in enumerate(passes):
            occ = [(h, CIDS[(n + i) % 7]) for i, h in enumerate(P)]; n += len(P)
            can, pts = render(loc, occ)
            full[f'{loc}_{pi}'] = can
            for h, cid, sx, sy, p in pts:
                c = can.crop((int(sx) - 56, int(sy) - 100, int(sx) + 56, int(sy) + 28)).resize((112 * S, 128 * S), Image.NEAREST)
                tiles.append((f"{loc} {h['id']}", f"{p['dir']} seat_z {p['z']:.2f} ({cid})", c))
    cols = 6; tw, th = 112 * S, 128 * S + 34
    sheet = Image.new('RGB', (cols * tw, math.ceil(len(tiles) / cols) * th), (20, 18, 28)); d = ImageDraw.Draw(sheet)
    for i, (lab, lab2, c) in enumerate(tiles):
        x, y = (i % cols) * tw, (i // cols) * th
        sheet.paste(c, (x, y + 34)); d.text((x + 4, y + 4), lab, fill=(240, 230, 160)); d.text((x + 4, y + 18), lab2, fill=(170, 200, 240))
    sheet.save(out); print(out, len(tiles), 'hooks', sheet.size)
    for k, c in full.items(): c.save(f'/tmp/sitfull_{k}.png')
if __name__ == '__main__': main()
