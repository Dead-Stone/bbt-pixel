"""Export the isometric world for the harness + live viewer.

For every location (floor4 = 4B + hall + 4A, and the six env/locations) this writes harness/world/<loc>/:
  bg.png       layers 0-4 (floor, decals, full walls, wall decals) with the light glow -- everything that never
               occludes a character
  sprites.png  atlas of the depth-sorted layer-5 sprites (item slices, cutaway walls, ceiling items)
  scene.json   origin, sprite list (sort key + screen rect + atlas rect), walkable grid, blocked edges, hooks (world
               pos, approach tile, facing, type, capacity), doors, exits, spawns, zones
plus harness/world/world.json (nodes + edges from env/world/world_graph.json, travel kinds/minutes).
Characters are NOT baked in: the viewer draws them from the v2 atlases, sorted with the sprites by the same keys
the offline compositor uses (feet x+y+0.01; seated floor(x)+floor(y)+1.5).
Run: python3 harness/export_world.py
"""
import os, sys, json, math
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, f'{ROOT}/tools')
import build_env as B
import rooms as RM
from iso_render import dir_name
OUT = f'{HERE}/world'
LOCS = ['ait_cafeteria', 'ait_physics', 'rest_amber_slice', 'street_exterior', 'lobby', 'raj_apartment']

def nearest_walkable(walk, x, y, prefer=None):
    H, W = len(walk), len(walk[0]); best = None
    for ty in range(H):
        for tx in range(W):
            if not walk[ty][tx]: continue
            d = (tx + 0.5 - x) ** 2 + (ty + 0.5 - y) ** 2
            if prefer is not None: d -= 0.25 * ((tx + 0.5 - x) * prefer[0] + (ty + 0.5 - y) * prefer[1])
            if best is None or d < best[0]: best = (d, [tx, ty])
    return best[1]

DV = {'S': (1, 1), 'N': (-1, -1), 'E': (1, -1), 'W': (-1, 1), 'SW': (0, 1), 'SE': (1, 0), 'NE': (0, -1), 'NW': (-1, 0)}

def fix_hooks(hooks, walk):
    H, W = len(walk), len(walk[0])
    for h in hooks:
        at = h.get('approach_tile')
        ok = at and 0 <= at[0] < W and 0 <= at[1] < H and walk[at[1]][at[0]]
        if not ok:
            f = DV.get(h['facing'], (0, 0))
            # a seat faces away from its approach side less often than towards it: prefer tiles in front of the hook
            h['approach_tile'] = nearest_walkable(walk, h['pos'][0], h['pos'][1], f)
    return hooks

def floor4_hooks():
    out = []; cnt = {}
    for (iid, ox, oy, rot, st, z) in B.PLACE:
        i = cnt.get(iid, 0); cnt[iid] = i + 1
        it = B.E.ITEMS[iid]
        if it['rotation_class'] == 'R1': rot = 'SW'
        R = B.rend(iid, rot, st or it['states'][0])
        for h in it['hooks']:
            px, py = R['xf'].fwd(*h['pos']); vx, vy = R['xf'].vec(*h['facing'])
            d = dict(id=f'{iid}#{i}.{h["id"]}', item=iid, index=i, hook=h['id'], type=h['type'], pos=[round(ox + px, 3), round(oy + py, 3)],
                     tile=[int(math.floor(ox + px)), int(math.floor(oy + py))], z=round(z + h.get('z', 0.0), 3),
                     facing=dir_name(round(vx, 6), round(vy, 6)), anim=h['anim'], capacity=h['capacity'], tags=h['tags'],
                     owner=h.get('priority_owner', ''))
            if 'approach' in h:
                ax, ay = R['xf'].fwd(*h['approach']); d['approach_tile'] = [int(math.floor(ox + ax)), int(math.floor(oy + ay))]
            out.append(d)
    return out

def pack(sprites, origin):
    """crop each layer-5 sprite to its alpha bbox and shelf-pack into one atlas"""
    ents = []
    for key, im, sx, sy in sprites:
        a = np.array(Image.fromarray(im) if isinstance(im, np.ndarray) else im.convert('RGBA'))
        ys, xs = np.nonzero(a[..., 3] > 0)
        if not len(xs): continue
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        ents.append(dict(key=round(float(key), 4), img=a[y0:y1, x0:x1], x=int(round(sx - origin[0])) + int(x0), y=int(round(sy - origin[1])) + int(y0)))
    AW = 2048; cx = cy = rowh = 0
    for e in ents:
        h, w = e['img'].shape[:2]
        if cx + w > AW: cx = 0; cy += rowh + 1; rowh = 0
        e['ax'], e['ay'] = cx, cy; cx += w + 1; rowh = max(rowh, h)
    atlas = np.zeros((cy + rowh + 1, AW, 4), np.uint8)
    for e in ents:
        h, w = e['img'].shape[:2]; atlas[e['ay']:e['ay'] + h, e['ax']:e['ax'] + w] = e['img']
    return atlas, [dict(key=e['key'], x=e['x'], y=e['y'], w=int(e['img'].shape[1]), h=int(e['img'].shape[0]), ax=e['ax'], ay=e['ay']) for e in ents]

def write(loc, bg, col, data):
    d = f'{OUT}/{loc}'; os.makedirs(d, exist_ok=True)
    bg.save(f'{d}/bg.png')
    atlas, spr = pack(col['sprites'], col['origin'])
    Image.fromarray(atlas).save(f'{d}/sprites.png')
    data.update(origin=list(col['origin']), bg_size=list(bg.size), sprites=spr, tile=[128, 64],
                projection='sx=(x-y)*64, sy=(x+y)*32-z*64; canvas = screen - origin')
    json.dump(data, open(f'{d}/scene.json', 'w'), indent=None, separators=(',', ':'))
    print(loc, bg.size, len(spr), 'sprites', len(data['hooks']), 'hooks')

def main():
    os.makedirs(OUT, exist_ok=True)
    wg = json.load(open(f'{ROOT}/env/world/world_graph.json'))
    nodes = {n['id']: n for n in wg['nodes']}
    # ---- floor4 (4B + hall + 4A)
    col = {}; bg = B.compose('combined', [], collect=col)
    eng = json.load(open(f'{ROOT}/env/maps/floor4_engine.json'))
    walk = [list(r) for r in eng['walkable']]
    for dd in eng['doors']:
        tx, ty = dd['tile']
        if dd['item'] != 'hall_stair_flight': walk[ty][tx] = 1
    n4 = nodes['floor4']
    exits = [dict(e) for e in n4.get('exits', [])]
    spawns = dict(n4.get('spawns', {}))
    spawns.setdefault('stairs_top', [10.5, 7.5])
    for e in exits:
        for tx, ty in e['tiles']: walk[ty][tx] = 1
    hooks = fix_hooks(floor4_hooks(), walk)
    write('floor4', bg, col, dict(id='floor4', name='4th floor: 4A (the guys), hall, 4B (Penny)', kind='interior', size=eng['size'],
                                  zones=eng['zones'], walkable=walk, blocked_edges=eng.get('blocked_edges', []), hooks=hooks,
                                  doors=eng['doors'], exits=exits, spawns=spawns,
                                  views={'4A': [12, 23], 'hall': [8, 12], '4B': [0, 8]}))
    # ---- the six locations
    for loc in LOCS:
        S = RM.ROOMS[loc]; col = {}
        bg = RM.compose_loc(S, [], collect=col)
        eng = json.load(open(f'{ROOT}/env/locations/{loc}/{loc}_engine.json'))
        walk = [list(r) for r in eng['walkable']]
        for e in eng['exits']:
            for tx, ty in e['tiles']:
                if 0 <= ty < len(walk) and 0 <= tx < len(walk[0]): walk[ty][tx] = 1
        write(loc, bg, col, dict(id=loc, name=eng['name'], kind=eng['kind'], size=eng['size'], zones=eng['zones'], walkable=walk,
                                 blocked_edges=eng.get('blocked_edges', []), hooks=fix_hooks(eng['hooks'], walk), doors=eng['doors'],
                                 exits=eng['exits'], spawns=eng['spawns']))
    json.dump(dict(nodes=[dict(id=n['id'], name=n['name'], kind=n.get('kind'), spawns=n.get('spawns', {}), exits=n.get('exits', [])) for n in wg['nodes']],
                   edges=wg.get('edges', [])), open(f'{OUT}/world.json', 'w'), indent=1)

if __name__ == '__main__': main()
