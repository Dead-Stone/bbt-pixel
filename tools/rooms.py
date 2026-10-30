"""Environment v2: reusable ROOM TEMPLATE system + all v2 locations.
A location is a plain dict spec (see ROOM_SCHEMA); compose_loc / export_tmj / export_engine turn any spec into
renders, a Tiled map and an engine JSON, so new rooms snap together with the same rules as floor4.
Run:  ../.venv/bin/python rooms.py [loc ...]   (no args = all + world graph + overview)"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import build_env as B
from build_env import E, scr, rend, slices, fimg, wimg, apply_glow, snap_scene, palette_check, char_frame, A, PAL, item_rots, FLOORS
from iso_render import dir_name
from env_tex import hsh
import env_items_v2 as V

ROOT = B.ROOT; ENV = B.ENV; LOC = f'{ENV}/locations'; WORLD = f'{ENV}/world'
ROOM_SCHEMA = {
    'id': 'snake_case location id', 'name': 'display name', 'kind': 'interior | exterior',
    'size': '[W, H] tiles (x along back wall, y toward camera)',
    'floor': 'list of [x0, y0, x1, y1, tile_key] rects, later wins; key ending in _* picks a/b variants by hash',
    'holes': 'tiles without floor', 'zones': '{name: [x0, y0, w, h]}',
    'walls': "{'back': [[x0, x1, mat]], 'left': [[y0, y1, mat]], 'front_cut': mat|None, 'right_cut': mat|None, 'front_gaps': [x..], 'right_gaps': [y..], "
             "'partitions': [{'side': 'bl'|'br', 'line': n, 'span': [a, b], 'mat': m, 'gaps': [..]}]}  (mats = build_env.WALLMAT keys)",
    'slots': "{'back': {x: 'window'|'window_day'|'window_high'|'doorway'}, 'left': {y: ...}}  door/window slots on full walls",
    'items': '[iid, x, y, rot, state|None, z, {opts}] ; opts.layer 3 forces the wall pass',
    'lights': "[{pos: [x, y], r: tiles, kind: lamp|screen|window|pendant}]  -> palette-step glow pools",
    'chars': "[{cid, mode: stand|sit, hook: [iid, idx, hook_id] | pos: [x, y], dir, anim, k}]",
    'spawns': '{name: [x, y]}', 'exits': "[{id, tiles: [[x, y]], to: loc_id, to_spawn, via: door|stairs|sidewalk|car}]",
}

def fk(key, x, y):
    return key.replace('_*', '_a' if hsh(x, y, 11) < 0.5 else '_b') if key.endswith('_*') else key

# ======================================================================= helpers on a spec
def floor_at(S, x, y):
    if [x, y] in S.get('holes', []) or (x, y) in S.get('holes', []): return None
    k = None
    for (x0, y0, x1, y1, key) in S['floor']:
        if x0 <= x < x1 and y0 <= y < y1: k = fk(key, x, y)
    return k
def walls_of(S):
    W, H = S['size']; w = S.get('walls', {}); sl = S.get('slots', {}); out = []
    for (x0, x1, mat) in w.get('back', []):
        for x in range(x0, x1): out.append(('br', 'full', 0, x, mat, sl.get('back', {}).get(x)))
    for (y0, y1, mat) in w.get('left', []):
        for y in range(y0, y1): out.append(('bl', 'full', 0, y, mat, sl.get('left', {}).get(y)))
    if w.get('front_cut'):
        for x in range(W):
            if x not in w.get('front_gaps', []): out.append(('br', 'cut', H, x, w['front_cut'], None))
    if w.get('right_cut'):
        for y in range(H):
            if y not in w.get('right_gaps', []): out.append(('bl', 'cut', W, y, w['right_cut'], None))
    for p in w.get('partitions', []):
        for i in range(*p['span']):
            if i in p.get('gaps', []): continue
            out.append((p['side'], 'cut', p['line'], i, p['mat'], None))
    return out
def item_R(iid, rot, st):
    it = E.ITEMS[iid]
    if it['rotation_class'] == 'R1': rot = 'SW'
    if it['rotation_class'] == 'R2' and rot in ('NE',): rot = 'SW'
    if it['rotation_class'] == 'R2' and rot in ('NW',): rot = 'SE'
    return rend(iid, rot, st or it['states'][0]), rot
def norm_items(S):
    out = []
    for t in S['items']:
        t = list(t) + [None]*(7 - len(t))
        iid, x, y, rot, st, z, op = t; out.append((iid, x, y, rot, st, z or 0, op or {}))
    return out
def world_hook(S, iid, idx, hid):
    n = 0
    for (pid, ox, oy, rot, st, z, op) in norm_items(S):
        if pid != iid: continue
        if n == idx:
            R, rot = item_R(iid, rot, st)
            for h in E.ITEMS[iid]['hooks']:
                if h['id'] == hid:
                    px, py = R['xf'].fwd(*h['pos']); v = R['xf'].vec(*h['facing'])
                    return ox + px, oy + py, z + h.get('z', 0.0), dir_name(round(v[0], 6), round(v[1], 6))
        n += 1
    raise KeyError((iid, idx, hid))
def all_hooks(S):
    out = []; cnt = {}
    for (iid, ox, oy, rot, st, z, op) in norm_items(S):
        i = cnt.get(iid, 0); cnt[iid] = i + 1
        R, rr = item_R(iid, rot, st)
        for h in E.ITEMS[iid]['hooks']:
            px, py = R['xf'].fwd(*h['pos']); vx, vy = R['xf'].vec(*h['facing'])
            d = dict(id=f'{iid}#{i}.{h["id"]}', item=iid, index=i, hook=h['id'], type=h['type'], pos=[round(ox + px, 3), round(oy + py, 3)],
                     tile=[int(math.floor(ox + px)), int(math.floor(oy + py))], z=round(z + h.get('z', 0.0), 3),
                     facing=dir_name(round(vx, 6), round(vy, 6)), anim=h['anim'], capacity=h['capacity'], tags=h['tags'])
            if 'approach' in h:
                ax, ay = R['xf'].fwd(*h['approach']); d['approach_tile'] = [int(math.floor(ox + ax)), int(math.floor(oy + ay))]
            out.append(d)
    return out

# ======================================================================= characters
POSES = f'{ENV}/renders/poses'
def chars_of(S):
    out = []
    for c in S.get('chars', []):
        cid = c['cid']
        if c.get('hook'):
            hx, hy, hz, fac = world_hook(S, *c['hook'])
            if c.get('offset'): hx += c['offset'][0]; hy += c['offset'][1]
        else:
            hx, hy = c['pos']; hz = c.get('z', 0.0); fac = c.get('dir', 'SW')
        d = c.get('dir', fac)
        if c.get('mode') == 'sit':
            js = json.load(open(f'{POSES}/{cid}_sit_SW.json'))
            out.append(dict(name=cid, img=A(f'{POSES}/{js["sprite"]}'), pos=(hx, hy), z=c.get('z', 0.0), pivot=tuple(js['pivot']),
                            key=math.floor(hx) + math.floor(hy) + 1.5, shadow=False, anim='sit (scene-only pose)', dir='SW', hook='.'.join(map(str, c.get('hook', [])))))
        else:
            anim = c.get('anim', 'idle'); k = c.get('k', 0)
            out.append(dict(name=cid, img=char_frame(cid, anim, d, k), pos=(hx, hy), z=hz if c.get('use_hook_z') else c.get('z', 0.0), anim=anim, dir=d,
                            hook='.'.join(map(str, c.get('hook', []))), key=c.get('key')))
    return out

# ======================================================================= compositor (generic)
def compose_loc(S, chars=(), labels=False, collect=None):
    """collect: optional dict -> return the background only (layers 0-4 + glow) and put the depth-sorted layer-5
    sprites [(key, img, sx, sy)] and the screen origin into it (used by harness/export_world.py for the live viewer)"""
    W, H = S['size']; ztop = S.get('ztop', 3.4)
    pts = [scr(x, y, z) for x in (0, W) for y in (0, H) for z in (0, max(ztop, S.get('sky_h', 0) if S.get('sky') else 0))]
    minx = int(min(p[0] for p in pts)) - 40; maxx = int(max(p[0] for p in pts)) + 40
    miny = int(min(p[1] for p in pts)) - 24; maxy = int(max(p[1] for p in pts)) + 24
    Wc, Hc = maxx - minx, maxy - miny
    bg = S.get('bg', 'ink')
    can = Image.new('RGBA', (Wc, Hc), tuple(PAL[bg]) + (255,))
    if S.get('sky'):   # exterior: a sky 'backdrop card' standing behind the y=0 facade line (diorama look, dark surround like every room)
        dr = ImageDraw.Draw(can); zs = S.get('sky_h', 8.8)
        def poly(z0, z1):
            return [tuple(int(v) - o for v, o in zip(scr(x, 0, z), (minx, miny))) for (x, z) in ((0, z0), (W, z0), (W, z1), (0, z1))]
        dr.polygon(poly(0, zs), fill=tuple(PAL['screen_glow']))
        dr.polygon(poly(zs - 1.2, zs), fill=tuple(PAL['comic_blue']))
        a = np.array(can); m = np.array(Image.new('L', can.size, 0)); mi = Image.new('L', can.size, 0); ImageDraw.Draw(mi).polygon(poly(zs - 1.6, zs - 1.2), fill=255)
        mm = np.array(mi) > 0; J, I = np.mgrid[0:a.shape[0], 0:a.shape[1]]; mm &= ((I + J) % 2 == 0)
        a[mm, :3] = PAL['comic_blue']; can = Image.fromarray(a)
    L = {k: [] for k in range(6)}
    for x in range(W):
        for y in range(H):
            k = floor_at(S, x, y)
            if k: sx, sy = scr(x, y); L[1].append((0, fimg(k), sx - 64, sy))
    for side, mode, line, idx, mat, feat in walls_of(S):
        img, anc = wimg(mat, side, mode, feat)
        wx, wy = (idx, line) if side == 'br' else (line, idx)
        sx, sy = scr(wx, wy)
        if mode == 'full': L[3].append((0 if side == 'bl' else 0.1, img, sx - anc[0], sy - anc[1]))
        else: L[5].append((wx + wy + (0.55 if side == 'br' else 0.45), img, sx - anc[0], sy - anc[1]))
    for (iid, ox, oy, rot, st, z, op) in norm_items(S):
        it = E.ITEMS[iid]; R, rot = item_R(iid, rot, st)
        nfx, nfy = R['fp']
        cox = R['pivot'][0] - (nfx - nfy)*64; coy = R['pivot'][1] - (nfx + nfy)*32
        sx, sy = scr(ox, oy, z); tlx, tly = sx - cox, sy - coy
        lay = op.get('layer')
        if lay is None:
            lay = 2 if it['layer'] == 'floor_decal' else (4 if it['layer'] == 'wall_decal' else 5)
        if lay != 5: L[lay].append((op.get('key', 0), R['img'], tlx, tly)); continue
        if it['mount'] == 'ceiling':
            L[5].append((ox + oy + nfx + nfy + 0.6, R['img'], tlx, tly)); continue
        for (tx, ty), im in slices(R):
            key = math.floor(ox) + tx + math.floor(oy) + ty + 1 + it['sort_bias']*0.1 + (0.02 if z > 0 else 0) + op.get('bias', 0)
            L[5].append((key, im, tlx, tly))
    for ch in chars:
        im, (fx, fy), z, key = ch['img'], ch['pos'], ch.get('z', 0), ch.get('key')
        sx, sy = scr(fx, fy, z)
        k = key if key is not None else fx + fy + 0.01
        if ch.get('shadow', True):
            sh = Image.new('RGBA', (40, 12), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse((0, 0, 39, 11), fill=tuple(PAL['shadow_violet']) + (110,))
            L[5].append((k - 0.001, np.array(sh), sx - 20, sy - 6))
        pv = ch.get('pivot', (64, 116))
        L[5].append((k, im, sx - pv[0], sy - pv[1]))
    def blit(im, sx, sy):
        nonlocal can
        can.alpha_composite(Image.fromarray(im) if isinstance(im, np.ndarray) else im, (int(round(sx - minx)), int(round(sy - miny))))
    for li in range(6):
        if li == 5 and collect is not None:
            collect.update(sprites=sorted(L[5], key=lambda t: t[0]), origin=(minx, miny)); break
        for key, im, sx, sy in sorted(L[li], key=lambda t: t[0]): blit(im, sx, sy)
        if li == 2: can = apply_glow(can, S.get('lights', []), minx, miny)
    return snap_scene(can)

# ======================================================================= engine JSON + Tiled
def walk_grid(S):
    W, H = S['size']
    walk = [[0 if floor_at(S, x, y) is None else 1 for x in range(W)] for y in range(H)]
    for (iid, ox, oy, rot, st, z, op) in norm_items(S):
        it = E.ITEMS[iid]
        if op.get('walkable') or not it['blocks_walk'] or z > 0 or it['layer'] == 'floor_decal' or it['mount'] in ('wall', 'ceiling'): continue
        R, _ = item_R(iid, rot, st)
        for tx in range(R['fp'][0]):
            for ty in range(R['fp'][1]):
                X, Y = int(math.floor(ox)) + tx, int(math.floor(oy)) + ty
                if 0 <= X < W and 0 <= Y < H: walk[Y][X] = 0
    for (x, y) in S.get('force_walk', []): walk[y][x] = 1
    for (x, y) in S.get('force_block', []): walk[y][x] = 0
    return walk
def blocked_edges(S):
    out = []
    for p in S.get('walls', {}).get('partitions', []):
        for i in range(*p['span']):
            if i in p.get('gaps', []): continue
            if p['side'] == 'bl': out.append([[p['line'] - 1, i], [p['line'], i]])
            else: out.append([[i, p['line'] - 1], [i, p['line']]])
    return out
def export_engine(S, chars):
    W, H = S['size']
    eng = dict(id=S['id'], name=S['name'], kind=S['kind'], size=[W, H], tile=[128, 64], px_per_m=64, ztop_m=S.get('ztop', 3.4),
               projection='sx=(x-y)*64, sy=(x+y)*32-z*64', zones=S.get('zones', {}),
               floor=[[floor_at(S, x, y) for x in range(W)] for y in range(H)], walkable=walk_grid(S), blocked_edges=blocked_edges(S),
               walls=[dict(zip(('side', 'mode', 'line', 'index', 'mat', 'feature'), w)) for w in walls_of(S)],
               items=[dict(item=i, x=ox, y=oy, rot=item_R(i, r, st)[1], state=st or E.ITEMS[i]['states'][0], z=z, manifest=f'../../items/{i}/{i}.json')
                      for (i, ox, oy, r, st, z, op) in norm_items(S)],
               hooks=all_hooks(S), doors=S.get('doors', []), spawns=S.get('spawns', {}), exits=S.get('exits', []), lights=S.get('lights', []),
               characters=[dict(name=c['name'], pos=[round(c['pos'][0], 3), round(c['pos'][1], 3)], anim=c['anim'], dir=c['dir'], hook=c.get('hook', '')) for c in chars],
               sort=dict(rule='slice key = tile x+y+1 (+sort_bias*0.1); characters = feet x+y; seated = seat tile x+y+1.5; ceiling items after their footprint; '
                              'full walls + wall decals before the sorted pass; cutaway stubs keyed x+y+0.45 (left/right) / +0.55 (front)'),
               renders=dict(x1=f'{S["id"]}_1x.png', x2=f'{S["id"]}_2x.png'))
    json.dump(eng, open(f'{LOC}/{S["id"]}/{S["id"]}_engine.json', 'w'), indent=1)
    return eng
def export_tmj(S, chars):
    W, H = S['size']
    names = sorted({floor_at(S, x, y) for x in range(W) for y in range(H)} - {None})
    gid = {k: i + 1 for i, k in enumerate(names)}
    data = [gid.get(floor_at(S, x, y), 0) for y in range(H) for x in range(W)]
    oid = [1]
    def obj(name, typ, wx, wy, props):
        o = dict(id=oid[0], name=name, type=typ, x=round(wx*64, 2), y=round(wy*64, 2), width=0, height=0, rotation=0, visible=True, point=True,
                 properties=[dict(name=k, type=('bool' if isinstance(v, bool) else 'int' if isinstance(v, int) else 'float' if isinstance(v, float) else 'string'),
                                  value=(v if isinstance(v, (str, int, float, bool)) else json.dumps(v))) for k, v in props.items()])
        oid[0] += 1; return o
    walls = []
    for side, mode, line, idx, mat, feat in walls_of(S):
        wx, wy = (idx, line) if side == 'br' else (line, idx)
        nm = f'wall_{mat}_{"backright" if side == "br" else "backleft"}_{"full" if mode == "full" else "cutaway"}' + (f'_{feat}' if feat else '')
        walls.append(obj(nm, 'wall', wx, wy, dict(sprite=f'../../tiles/{nm}.png', mode=mode, world_x=wx, world_y=wy, runs_along='+x' if side == 'br' else '+y')))
    items = []
    for (iid, ox, oy, rot, st, z, op) in norm_items(S):
        R, rr = item_R(iid, rot, st); it = E.ITEMS[iid]
        items.append(obj(iid, 'item', ox, oy, dict(item_id=iid, rot=rr, state=st or it['states'][0], z=float(z), world_x=float(ox), world_y=float(oy),
                                                   footprint=list(R['fp']), manifest=f'../../items/{iid}/{iid}.json', blocks_walk=it['blocks_walk'])))
    hooks = [obj(h['id'], 'hook', h['pos'][0], h['pos'][1], dict(hook_type=h['type'], facing=h['facing'], anim=h['anim'] or '', z=float(h['z']),
                                                                    capacity=h['capacity'], tags=','.join(h['tags']))) for h in all_hooks(S)]
    sp = [obj(k, 'spawn', v[0], v[1], {}) for k, v in S.get('spawns', {}).items()]
    ex = [obj(e['id'], 'exit', e['tiles'][0][0] + 0.5, e['tiles'][0][1] + 0.5, dict(to=e['to'], to_spawn=e.get('to_spawn', ''), via=e['via'], tiles=e['tiles'])) for e in S.get('exits', [])]
    ch = [obj(c['name'], 'character', c['pos'][0], c['pos'][1], dict(anim=c['anim'], dir=c['dir'], hook=c.get('hook', ''))) for c in chars]
    zones = []
    for nm, (x0, y0, w, h) in S.get('zones', {}).items():
        zones.append(dict(id=oid[0], name=nm, type='zone', x=x0*64, y=y0*64, width=w*64, height=h*64, rotation=0, visible=True)); oid[0] += 1
    lay = lambda i, n, objs, d='index': dict(id=i, name=n, type='objectgroup', objects=objs, opacity=1, visible=True, x=0, y=0, draworder=d)
    tm = dict(type='map', version='1.10', tiledversion='1.10.2', orientation='isometric', renderorder='right-down', width=W, height=H,
              tilewidth=128, tileheight=64, infinite=False, nextlayerid=10, nextobjectid=oid[0],
              properties=[dict(name='location', type='string', value=S['id']), dict(name='px_per_m', type='int', value=64),
                          dict(name='note', type='string', value='object x,y = world tiles*64 (Tiled iso object space); world_x/world_y in properties')],
              tilesets=[dict(firstgid=1, name='bbt_floors', tilewidth=128, tileheight=64, tilecount=len(names), columns=0,
                             grid=dict(orientation='isometric', width=128, height=64),
                             tiles=[dict(id=i, image=f'../../tiles/{k}.png', imagewidth=128, imageheight=64, properties=[dict(name='name', type='string', value=k)])
                                    for i, k in enumerate(names)])],
              layers=[dict(id=1, name='floor', type='tilelayer', width=W, height=H, x=0, y=0, opacity=1, visible=True, data=data),
                      lay(2, 'zones', zones), lay(3, 'walls', walls), lay(4, 'items', items, 'topdown'), lay(5, 'hooks', hooks),
                      lay(6, 'spawns', sp), lay(7, 'exits', ex), lay(8, 'characters', ch, 'topdown')])
    json.dump(tm, open(f'{LOC}/{S["id"]}/{S["id"]}.tmj', 'w'), indent=1)

def build(S):
    os.makedirs(f'{LOC}/{S["id"]}', exist_ok=True)
    ch = chars_of(S)
    im = compose_loc(S, ch)
    im.save(f'{LOC}/{S["id"]}/{S["id"]}_1x.png'); im.resize((im.width*2, im.height*2), Image.NEAREST).save(f'{LOC}/{S["id"]}/{S["id"]}_2x.png')
    eng = export_engine(S, ch); export_tmj(S, ch)
    json.dump({k: v for k, v in S.items()}, open(f'{LOC}/{S["id"]}/{S["id"]}_spec.json', 'w'), indent=1, default=str)
    return dict(size=im.size, off_palette=len(palette_check(im)), chars=[c['name'] for c in ch], hooks=len(eng['hooks']),
                walkable=sum(map(sum, eng['walkable'])))

from locations import ROOMS, WORLD_EDGES   # noqa: E402  (location specs live in locations.py)

# ======================================================================= world graph + overview + crest
def crest_png():
    n = 64; im = np.zeros((n, n, 4), np.uint8)
    for j in range(n):
        for i in range(n):
            c = V.crest_px((i + 0.5)/n, (j + 0.5)/n)
            if c: im[j, i, :3] = PAL[c]; im[j, i, 3] = 255
    Image.fromarray(im).save(f'{WORLD}/ait_crest_64.png'); Image.fromarray(im).resize((256, 256), Image.NEAREST).save(f'{WORLD}/ait_crest_256.png')
def world_graph(ids):
    nodes = []
    for i in ids:
        S = ROOMS[i]; nodes.append(dict(id=i, name=S['name'], kind=S['kind'], size=S['size'], engine=f'../locations/{i}/{i}_engine.json',
                                        tmj=f'../locations/{i}/{i}.tmj', render=f'../locations/{i}/{i}_1x.png', spawns=S.get('spawns', {}),
                                        exits=S.get('exits', [])))
    nodes.append(dict(id='floor4', name='4th floor: 4A + landing + 4B (Environment v1)', kind='interior', size=[23, 8],
                      engine='../maps/floor4_engine.json', tmj='../maps/floor4_4A_hall_4B.tmj', render='../renders/floor4_combined_1x.png',
                      spawns={'stairs_top': [10.5, 7.5]}, exits=[dict(id='stairs_down', tiles=[[10, 7], [11, 7]], to='lobby', to_spawn='from_stairs', via='stairs')]))
    g = dict(world='bbt_pixel_living_sitcom', version=2, nodes=nodes, edges=WORLD_EDGES,
             stubs=['kitchen_stub (Amber Slice kitchen)', 'raj_bedroom_stub'],
             note='edges are bidirectional; via=door|stairs|sidewalk|car. Car edges are travel transitions (no road map).')
    json.dump(g, open(f'{WORLD}/world_graph.json', 'w'), indent=1)
    json.dump(dict(schema=ROOM_SCHEMA, wall_materials={k: {kk: vv for kk, vv in v.items()} for k, v in B.WALLMAT.items()},
                   floors=list(FLOORS), rooms={i: {k: v for k, v in ROOMS[i].items() if k not in ('items', 'chars')} for i in ids}),
              open(f'{WORLD}/room_specs.json', 'w'), indent=1, default=str)
    return g
def overview(ids):
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 18); fs = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
    except Exception: f = fs = ImageFont.load_default()
    tiles = [(i, ROOMS[i]['name'], f'{LOC}/{i}/{i}_1x.png') for i in ids] + [('floor4', '4th floor: 4A + landing + 4B', f'{ENV}/renders/floor4_combined_1x.png')]
    order = ['street_exterior', 'lobby', 'floor4', 'rest_amber_slice', 'ait_cafeteria', 'ait_physics', 'raj_apartment']
    tiles.sort(key=lambda t: order.index(t[0]) if t[0] in order else 99)
    cw, chh, cols = 620, 400, 3; rows = (len(tiles) + cols - 1)//cols
    W = cols*cw + 40; H = 70 + rows*(chh + 50) + 150
    sheet = Image.new('RGBA', (W, H), (40, 38, 50, 255)); dr = ImageDraw.Draw(sheet)
    dr.text((20, 18), 'BBT Pixel - World overview (Environment v2). Arroyo Institute of Technology, The Amber Slice, 2311 building + street, Raj. Grok Bot build.', font=f, fill=(245, 236, 210))
    for n, (i, nm, p) in enumerate(tiles):
        im = Image.open(p).convert('RGBA'); s = min(cw/im.width, chh/im.height)
        th = im.resize((max(1, int(im.width*s)), max(1, int(im.height*s))), Image.NEAREST if s >= 1 else Image.LANCZOS)
        cx, cy = 20 + (n % cols)*cw, 60 + (n//cols)*(chh + 50)
        dr.rectangle((cx - 2, cy - 2, cx + cw - 18, cy + chh + 30), outline=(90, 88, 110))
        sheet.alpha_composite(th, (cx + (cw - 20 - th.width)//2, cy + (chh - th.height)//2))
        dr.text((cx + 6, cy + chh + 6), f'{nm}   [{i}]', font=fs, fill=(250, 230, 160))
    n = len(tiles)
    if n % cols:   # spare cell: AIT crest + a mini node graph
        cx, cy = 20 + (n % cols)*cw, 60 + (n//cols)*(chh + 50)
        cr = Image.open(f'{WORLD}/ait_crest_256.png').convert('RGBA'); sheet.alpha_composite(cr, (cx + 10, cy + 20))
        dr.text((cx + 10, cy + 290), 'Arroyo Institute of Technology (AIT)', font=fs, fill=(250, 230, 160))
        dr.text((cx + 10, cy + 310), 'original crest - env/world/ait_crest_256.png', font=fs, fill=(200, 210, 235))
        pos = {'floor4': (470, 40), 'lobby': (470, 110), 'street_exterior': (430, 180), 'rest_amber_slice': (300, 250),
               'ait_cafeteria': (470, 250), 'ait_physics': (470, 320), 'raj_apartment': (330, 320)}
        for e in WORLD_EDGES:
            if e['a'] in pos and e['b'] in pos:
                (x0, y0), (x1, y1) = pos[e['a']], pos[e['b']]
                dr.line((cx + x0, cy + y0, cx + x1, cy + y1), fill=(150, 150, 190) if e['via'] != 'car' else (110, 160, 230), width=2)
        for k, (px_, py_) in pos.items():
            dr.ellipse((cx + px_ - 5, cy + py_ - 5, cx + px_ + 5, cy + py_ + 5), fill=(250, 200, 90))
            dr.text((cx + px_ - 60, cy + py_ + 7), k, font=fs, fill=(235, 235, 245))
    y = 60 + rows*(chh + 50) + 10
    dr.text((20, y), 'Connections (world_graph.json):', font=f, fill=(245, 236, 210))
    for k, e in enumerate(WORLD_EDGES):
        dr.text((30 + (k % 2)*700, y + 30 + (k//2)*22), f"{e['a']}  <-{e['via']}->  {e['b']}" + (f"   ({e['travel']})" if e.get('travel') else ''), font=fs, fill=(200, 210, 235))
    sheet.save(f'{WORLD}/world_overview.png'); return sheet.size

if __name__ == '__main__':
    args = sys.argv[1:] or list(ROOMS)
    os.makedirs(WORLD, exist_ok=True)
    for i in [a for a in args if a in ROOMS]:
        print(i, build(ROOMS[i]), flush=True)
    if not sys.argv[1:] or 'world' in args:
        crest_png(); world_graph([i for i in ROOMS if os.path.exists(f'{LOC}/{i}/{i}_1x.png')])
        print('overview', overview([i for i in ROOMS if os.path.exists(f'{LOC}/{i}/{i}_1x.png')]))
