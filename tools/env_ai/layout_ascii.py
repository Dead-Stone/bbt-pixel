"""ASCII top-down diagram of the floor4 PLACE list (x right, y down = toward the camera / fourth wall).
Usage: python3 tools/env_ai/layout_ascii.py > out.txt"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import build_env as B
E = B.E
CODE = {'couch': 'C', 'armchair': 'A', 'coffee_table': 'T', 'tv_stand': 'V', 'desk': 'D', 'office_chair': 'o',
        'kitchen_counter': 'K', 'kitchen_island': 'I', 'kitchen_bar': 'I', 'bar_stool': 's', 'fridge': 'F', 'whiteboard': 'W',
        'bookcase': 'B', 'telescope': 't', 'floor_lamp': 'l', 'front_door': 'E', 'bedroom_door': 'b', 'elevator': 'L',
        'stair_flight': '#', 'stair_rail': '|', 'dining': 'R', 'laundry': 'u', 'plant': 'p', 'dna': 'n'}
def code(iid):
    for k, v in CODE.items():
        if k in iid: return v
    return None
def diagram(place=None):
    place = place or B.PLACE
    g = [['.' for _ in range(B.W_)] for _ in range(B.H_)]
    for (x, y) in B.STAIRS: g[y][x] = '#'
    for (iid, ox, oy, rot, st, z) in place:
        c = code(iid); it = E.ITEMS[iid]
        if c is None or z > 0 or it['mount'] == 'wall' and 'door' not in iid and 'elevator' not in iid: continue
        fw, fh = it['footprint']
        if rot in ('SE', 'NW'): fw, fh = fh, fw
        for i in range(fw):
            for j in range(fh):
                X, Y = int(ox) + i, int(oy) + j
                if 0 <= X < B.W_ and 0 <= Y < B.H_: g[Y][X] = c
    hdr = ''.join('4B'[0] if x < 8 else ('h' if x < 12 else 'A') for x in range(B.W_))
    out = ['     x: ' + ''.join(str(x % 10) for x in range(B.W_)), '  zone: ' + hdr,
           '  back wall y=0 (windows: ' + ','.join(str(x) for (w, x) in sorted(B.WINDOWS, key=lambda t: t[1])) + ')']
    for y in range(B.H_): out.append(f'   y={y}: ' + ''.join(g[y]))
    out.append('  front (fourth wall / camera side) y=8')
    out.append('  legend: ' + ' '.join(f'{v}={k}' for k, v in CODE.items()))
    return '\n'.join(out)
if __name__ == '__main__': print(diagram())
