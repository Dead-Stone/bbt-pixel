"""Environment v1 builder: floor tiles, wall pieces, item exports (+slices, manifests), tile map, scene renders, catalog.
Run:  ../.venv/bin/python build_env.py   (from tools/)"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from iso_render import render, C, PAL, MAT, scr, dir_name, Xform
import env_items as E
import env_items_v2  # noqa: F401  (registers the Environment v2 items into E.ITEMS)
from env_tex import hsh

ROOT = '/workspace/bbt-pixel'; ENV = f'{ROOT}/env'
TPL = f'{ROOT}/templates'
ROTS = {'R8': ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE'], 'R4': ['SW', 'NW', 'NE', 'SE'], 'R2': ['SW', 'SE'], 'R1': ['SW']}
def A(name): return np.array(Image.open(name).convert('RGBA'))
def save(arr, path): Image.fromarray(arr).save(path)

# ---------------------------------------------------------------- floor tiles
FLOOR_MASK = A(f'{TPL}/iso_floor_tile_128x64.png')[..., 3] > 0
def floor_tile(fn):
    img = np.zeros((64, 128, 4), np.uint8)
    for j in range(64):
        for i in range(128):
            if not FLOOR_MASK[j, i]: continue
            sx = i + 0.5 - 64; sy = j + 0.5
            x = (sx/64 + sy/32)/2; y = (sy/32 - sx/64)/2
            img[j, i, :3] = C[fn(min(max(x, 0), 0.9999), min(max(y, 0), 0.9999), i, j)]; img[j, i, 3] = 255
    return img
def frac(v): return v - math.floor(v)
def planks(base, seam, grain, speck, axis, n, var, messy=False):
    def f(x, y, i, j):
        a, b = (y, x) if axis == 'x' else (x, y)      # a: across planks, b: along planks
        p = int(a*n); fa = frac(a*n)
        if fa < 0.094*n/6: return seam
        jt = hsh(p, var, 3)
        if abs(frac(b - jt) ) < 1/64 or abs(frac(b - jt) - 1) < 1/64:
            return seam
        h = hsh(int(b*40), p, var)
        if h < 0.035: return grain
        if h > 0.985: return speck
        if messy and hsh(int(b*14), p, var + 7) < 0.02 and 0.3 < fa < 0.7: return grain
        return base
    return f
FLOORS = {
    'floor_4a_wood_a': planks('wood', 'wood_dk', 'wood_dk', 'wood_hi', 'x', 6, 1),
    'floor_4a_wood_b': planks('wood', 'wood_dk', 'wood_dk', 'wood_hi', 'x', 6, 2),
    'floor_4a_kitchen': lambda x, y, i, j: ('wall_4a_dk' if (frac(x*4) < 0.06 or frac(y*4) < 0.06) else
                                            ('cafe_cream' if (int(x*4) + int(y*4)) % 2 == 0 else 'wall_4a')),
    'floor_hall': lambda x, y, i, j: ('wood_dk' if (frac(x*2) < 0.035 or frac(y*2) < 0.035) else
                                      ('wood' if hsh(int(x*24), int(y*24), 5) < 0.06 else
                                       ('wood_dk' if hsh(i, j, 9) < 0.02 else 'floor_hall'))),
    'floor_4b_wood_a': planks('wood_hi', 'wood', 'wood', 'wall_4a_hi', 'y', 5, 3, True),
    'floor_4b_wood_b': planks('wood_hi', 'wood', 'wood', 'wall_4a_hi', 'y', 5, 4, True),
    # ---- Environment v2 floors
    'floor_cafe_lino': lambda x, y, i, j: ('grey' if (frac(x*2) < 0.03 or frac(y*2) < 0.03) else
                                           ('cafe_teal' if (int(x*2) + int(y*2)) % 4 == 0 else
                                            ('grey_lt' if hsh(int(x*32), int(y*32), 21) < 0.05 else 'cafe_cream'))),
    'floor_office_carpet': lambda x, y, i, j: ('stair_wall_dk' if hsh(i, j, 22) < 0.12 else ('wall_4a' if hsh(i, j, 23) < 0.05 else 'stair_wall')),
    'floor_lab_vinyl': lambda x, y, i, j: ('grey' if (frac(x*2) < 0.03 or frac(y*2) < 0.03) else
                                           ('grey_lt' if hsh(int(x*40), int(y*40), 24) > 0.06 else 'paper')),
    'floor_rest_wood_a': planks('wood_dk', 'wood_xdk', 'wood_xdk', 'wood', 'x', 5, 5),
    'floor_rest_wood_b': planks('wood_dk', 'wood_xdk', 'wood_xdk', 'wood', 'x', 5, 6),
    'floor_rest_tile': lambda x, y, i, j: ('grey_dk' if (frac(x*3) < 0.05 or frac(y*3) < 0.05) else
                                           ('ink_2' if (int(x*3) + int(y*3)) % 2 else 'paper')),
    'floor_raj_wood_a': planks('wood', 'wood_dk', 'wood_dk', 'wood_hi', 'y', 4, 7),
    'floor_raj_wood_b': planks('wood', 'wood_dk', 'wood_dk', 'wood_hi', 'y', 4, 8),
    'floor_lobby_tile': lambda x, y, i, j: ('ccf_booth_red' if min(x, y, 1 - x, 1 - y) < 0.04 else
                                            ('grey' if (frac(x*4 + 0.5*(int(y*4) % 2)) < 0.06 or frac(y*4) < 0.06) else
                                             ('paper' if hsh(int(x*4 + 0.5*(int(y*4) % 2)), int(y*4), 25) < 0.85 else 'grey_lt'))),
    'ground_sidewalk': lambda x, y, i, j: ('grey' if (frac(x) < 0.025 or frac(y*2) < 0.03) else
                                           ('grey_lt' if hsh(int(x*48), int(y*48), 26) > 0.04 else 'stair_wall')),
    'ground_curb': lambda x, y, i, j: ('paper' if y < 0.18 else ('grey' if y < 0.24 else ('grey_dk' if y < 0.55 else 'ink_2' if hsh(int(x*40), int(y*40), 27) < 0.08 else 'grey_dk'))),
    'ground_asphalt': lambda x, y, i, j: ('grey' if hsh(int(x*48), int(y*48), 28) < 0.05 else ('ink_2' if hsh(int(x*48), int(y*48), 29) < 0.05 else 'grey_dk')),
    'ground_asphalt_dash': lambda x, y, i, j: ('tape_yellow' if (abs(y - 0.5) < 0.05 and frac(x) < 0.55) else
                                               ('grey' if hsh(int(x*48), int(y*48), 28) < 0.05 else 'grey_dk')),
    'ground_grass': lambda x, y, i, j: ('plant_green' if hsh(int(x*40), int(y*40), 30) < 0.3 else
                                        ('4b_lime' if hsh(int(x*40), int(y*40), 31) < 0.06 else 'tile_green_dk' if hsh(int(x*40), int(y*40), 32) < 0.25 else 'tile_green')),
}

# ---------------------------------------------------------------- wall pieces
WALL_FULL = A(f'{TPL}/iso_wall_backright_full_64x224.png')[..., 3] > 0
WALL_CUT = A(f'{TPL}/iso_wall_backright_cutaway_64x48.png')[..., 3] > 0
WALLMAT = {
    '4a':   dict(br='wall_4a', bl='wall_4a_dk', hi='wall_4a_hi', dk='stair_wall_dk', base='wood_dk', base_hi='wood', rail=None),
    '4b':   dict(br='wall_4a', bl='wall_4a_dk', hi='wall_4a_hi', dk='stair_wall_dk', base='paper', base_hi='white_hi', rail=None),
    'hall': dict(br='stair_wall', bl='stair_wall_dk', hi='wall_4a_hi', dk='wood_dk', base='wood_xdk', base_hi='wood_dk', rail='stair_wall_dk'),
    # ---- Environment v2 wall materials (room template system; see rooms.py)
    'cafe':   dict(br='cafe_cream', bl='wall_4a', hi='white_hi', dk='grey', base='cafe_teal', base_hi='cafe_steel', rail=None,
                   stripe=('cafe_teal', 1.02, 1.1)),
    'office': dict(br='wall_4a_hi', bl='wall_4a', hi='white_hi', dk='wall_4a_dk', base='wood_dk', base_hi='wood', rail=None),
    'lab':    dict(br='grey_lt', bl='grey', hi='paper', dk='grey_dk', base='ink_2', base_hi='grey_dk', rail=None,
                   stripe=('cafe_steel', 1.2, 1.26)),
    'rest':   dict(br='ccf_amber', bl='leather', hi='lamp_warm', dk='leather_dk', base='wood_xdk', base_hi='wood_dk', rail=None,
                   wains=('wood_dk', 1.05, 'wood_hi'), wains_line='wood_xdk'),
    'raj':    dict(br='cafe_cream', bl='wall_4a', hi='white_hi', dk='wall_4a_dk', base='wood_xdk', base_hi='wood_dk', rail=None,
                   stripe=('wood_dk', 2.05, 2.1)),
    'lobby':  dict(br='leather', bl='leather_dk', hi='wall_4a_hi', dk='leather_xdk', base='ink_2', base_hi='grey_dk', rail=None,
                   brick=('stair_wall_dk', 'ccf_booth_red')),
}
def wall_piece(mat, side, mode='full', feature=None):
    """side 'br' (runs along +x, back-right) or 'bl' (runs along +y, back-left; mirrored shape).
    canvas 64x224 (full) / 64x48 (cutaway); anchor = canvas point of the segment's top floor vertex"""
    M = WALLMAT[mat]
    mask = (WALL_FULL if mode == 'full' else WALL_CUT).copy()
    Hc = mask.shape[0]; hface = 192 if mode == 'full' else 16
    img = np.zeros((Hc, 64, 4), np.uint8)
    face = M[side]
    for c in range(64):
        rows = np.where(mask[:, c])[0]
        if len(rows) == 0: continue
        bot = rows[-1]; top = rows[0]
        t = (c + 0.5)/64 if side == 'br' else 1 - (c + 0.5)/64        # position along the wall 0..1 from its top vertex
        for r in rows:
            z = (bot - r + 0.5)/64.0
            col = face
            if mode == 'cut':
                if r <= top: col = 'ink'
                elif r <= top + 2: col = M['hi']
            else:
                if r == top: col = M['dk']
                elif r == top + 1: col = M['hi']
            if col == face:
                col = face_px(M, side, t, z, c, face)
                if z < 0.1: col = M['base_hi'] if z > 0.085 else M['base']
                elif M['rail'] and 0.88 < z < 0.92: col = M['rail']
                elif M['rail'] and 0.92 <= z < 0.94: col = M['hi']
                if feature in ('window', 'window_day') and mode == 'full':
                    col = window_px(t, z, col, M, c, day=(feature == 'window_day'))
                if feature == 'window_high' and mode == 'full':
                    col = window_px(t, z, col, M, c, day=True, z0=1.5, z1=2.5)
                if feature == 'doorway' and 0.1 <= t <= 0.9 and z < 2.1:
                    col = 'ink_2'
            img[r, c, :3] = C[col]; img[r, c, 3] = 255
    if side == 'bl':
        img = img[:, ::-1].copy()
    anchor = (0, hface) if side == 'br' else (64, hface)
    return img, anchor
def face_px(M, side, t, z, c, face):
    """v2 wall-material extras: wainscot (lower panel + cap), brick coursing, accent stripe"""
    if 'wains' in M:
        wc, wz, cap = M['wains']
        if wz - 0.03 <= z < wz: return cap
        if z < wz:
            if (c % 32) in (0, 31) and 0.12 < z < wz - 0.08: return M.get('wains_line', 'wood_xdk')
            return wc
    if 'stripe' in M:
        sc, s0, s1 = M['stripe']
        if s0 <= z < s1: return sc
    if 'brick' in M:
        mortar, alt = M['brick']
        row = int(z*64) // 6; rz = int(z*64) % 6
        if rz == 0: return mortar
        cc = (c + (row % 2)*8) % 16
        if cc == 0: return mortar
        if hsh(row, (c + (row % 2)*8)//16, 3 if side == 'br' else 4) < 0.22: return alt
    return face
def window_px(t, z, col, M, c, day=False, z0=0.9, z1=2.2):
    x0, x1 = 0.12, 0.88
    if not (x0 - 0.04 <= t <= x1 + 0.04 and z0 - 0.06 <= z <= z1 + 0.04): return col
    if z < z0 - 0.02: return 'ink' if z < z0 - 0.045 else 'paper'          # sill
    if not (x0 <= t <= x1 and z0 <= z <= z1): return 'paper'                 # trim
    if abs(t - 0.5) < 0.02 or abs(z - (z0 + z1)/2 + 0.05) < 0.015: return 'grey_lt'        # mullions
    if t < x0 + 0.02 or z > z1 - 0.025: return 'grey'                       # inner reveal shade
    if day:
        # Pasadena daytime: pale sky, San Gabriel ridge, palm/street-tree tops
        u = (z - z0) / (z1 - z0)
        ridge = 0.32 + 0.12*math.sin(t*9 + 1) + 0.05*math.sin(t*23)
        if u < 0.22 + 0.1*hsh(int(t*12), 2, 3): return 'plant_green' if hsh(int(t*40), int(z*30), 5) < 0.75 else 'tile_green_dk'
        if u < ridge: return 'grey_lt' if u > ridge - 0.04 else 'stair_wall'
        if abs(t - 0.3) < 0.012 and u < 0.8: return 'wood_dk'
        if math.hypot((t - 0.3)*2.2, u - 0.8) < 0.08: return 'plant_green'
        return 'white_hi' if u > 0.92 else 'screen_glow'
    # night sky over Pasadena: banded with a 2x2 dither transition, skyline silhouette
    sky = 'comic_blue' if z > 1.75 else 'screen_glow'
    if 1.70 < z <= 1.75 and (c + int(z*64)) % 2: sky = 'comic_blue'
    bh = 0.95 + 0.35*hsh(int(t*9), 1, 2)
    if z < bh:
        if hsh(int(t*40), int(z*32), 4) < 0.12: return 'lamp_warm'
        return 'shadow_violet'
    if hsh(int(t*64), int(z*64), 8) < 0.006: return 'white_hi'
    return sky

# ---------------------------------------------------------------- practical-light glow (spec 1.5)
def _lum(c): return 0.3*c[0] + 0.59*c[1] + 0.11*c[2]
GLOW_TINT = {'lamp': 'lamp_warm', 'screen': 'screen_glow', 'window': 'white_hi', 'pendant': 'lamp_warm'}
_STEP = {}
def glow_step(kind):
    """palette -> palette 'one step lighter, tinted toward the light' lookup (keeps scenes palette-strict)"""
    if kind in _STEP: return _STEP[kind]
    tint = np.array(PAL[GLOW_TINT[kind]], float); names = [k for k in PAL if not k[0].isdigit() or k.startswith('4b')]
    cols = {k: np.array(PAL[k], float) for k in names}; m = {}
    for k, c in cols.items():
        tgt = c*0.62 + tint*0.38
        best, bd = None, 1e18
        for k2, c2 in cols.items():
            if _lum(c2) <= _lum(c) + 4: continue
            d = (((c2 - tgt)**2)*np.array([0.3, 0.59, 0.11])).sum()
            if d < bd: best, bd = k2, d
        if best is not None: m[tuple(PAL[k])] = tuple(PAL[best])
    _STEP[kind] = m; return m
def apply_glow(can, lights, minx, miny):
    """floor-level light pools: one-step palette lift inside an iso ellipse, 2x2 checker dither on the outer <=6 px rim"""
    if not lights: return can
    a = np.array(can)
    for L in lights:
        m = glow_step(L.get('kind', 'lamp'))
        cx, cy = scr(*L['pos']); cx -= minx; cy -= miny
        r = L.get('r', 1.5); rx, ry = r*90.5, r*45.25
        x0, x1 = int(max(cx - rx, 0)), int(min(cx + rx + 1, a.shape[1])); y0, y1 = int(max(cy - ry, 0)), int(min(cy + ry + 1, a.shape[0]))
        if x1 <= x0 or y1 <= y0: continue
        J, I = np.mgrid[y0:y1, x0:x1]
        d = np.sqrt(((I + 0.5 - cx)/rx)**2 + ((J + 0.5 - cy)/ry)**2)
        rim = 1 - 6.0/rx
        sel = (d < rim) | ((d < 1) & (((I//2) + (J//2)) % 2 == 0))
        sub = a[y0:y1, x0:x1]
        for (r_, c_) in zip(*np.where(sel)):
            k = tuple(int(v) for v in sub[r_, c_, :3])
            if k in m: sub[r_, c_, :3] = m[k]
    return Image.fromarray(a)
LIGHTS4 = [dict(pos=(17.5, 1.5), r=1.7, kind='lamp', src='4a_floor_lamp'), dict(pos=(19.0, 3.25), r=1.35, kind='screen', src='4a_tv_stand'),
           dict(pos=(21.6, 1.2), r=0.75, kind='screen', src='4a_desk_laptop'), dict(pos=(0.5, 2.5), r=1.6, kind='lamp', src='4b_floor_lamp')]

# ---------------------------------------------------------------- items
def item_rots(it): return ROTS[it['rotation_class']]
CACHE = {}
def rend(iid, rot, state=None):
    it = E.ITEMS[iid]; state = state or it['states'][0]
    k = (iid, rot, state)
    if k not in CACHE:
        CACHE[k] = render(it['build'](state), *it['footprint'], rot, shadow=it['shadow'])
    return CACHE[k]
def slices(R):
    nfx, nfy = R['fp']; out = []
    for tx in range(max(nfx, 1)):
        for ty in range(max(nfy, 1)):
            m = R['op'] & (R['tx'] == tx) & (R['ty'] == ty)
            if not m.any(): continue
            im = R['img'].copy(); im[~m] = 0
            out.append(((tx, ty), im))
    return out
def hook_rot(h, R):
    X = R['xf']; px, py = X.fwd(*h['pos']); vx, vy = X.vec(*h['facing'])
    sx, sy = scr(px, py, h.get('z', 0.0))
    d = dict(id=h['id'], type=h['type'], tile=[int(math.floor(px)), int(math.floor(py))], local=[round(px, 3), round(py, 3)],
             offset_px=[round(sx), round(sy)], z=h.get('z', 0.0), facing=dir_name(round(vx, 6), round(vy, 6)), capacity=h['capacity'],
             anim=h['anim'], tags=h['tags'])
    if 'approach' in h:
        ax, ay = X.fwd(*h['approach']); d['approach_tile'] = [int(math.floor(ax)), int(math.floor(ay))]
    if 'priority_owner' in h: d['priority_owner'] = h['priority_owner']
    return d
def export_items():
    report = {}
    for iid, it in E.ITEMS.items():
        d = f'{ENV}/items/{iid}'; os.makedirs(d, exist_ok=True)
        man = dict(id=iid, location=it['location'], footprint=it['footprint'], height_m=it['height_m'],
                   rotation_class=it['rotation_class'], priority=it['priority'], mount=it['mount'], layer=it['layer'],
                   blocks_walk=it['blocks_walk'], sort_bias=it['sort_bias'], states=it['states'], tags=it['tags'],
                   notes=it['notes'], z_anchor_px=0, mirrored=False, rotations={}, hooks_canonical=it['hooks'])
        for rot in item_rots(it):
            rr = {}
            for st in it['states']:
                R = rend(iid, rot, st)
                suf = '' if st == it['states'][0] else f'_{st}'
                fn = f'item_{iid}_{rot}{suf}.png'; save(R['img'], f'{d}/{fn}')
                ent = dict(sprite=fn, pivot=list(map(int, R['pivot'])), canvas=[R['img'].shape[1], R['img'].shape[0]],
                           footprint=list(R['fp']), formula_ok=R['formula_ok'])
                sl = slices(R)
                if len(sl) > 1:
                    ent['slices'] = []
                    for i, ((tx, ty), im) in enumerate(sl):
                        sfn = f'item_{iid}_{rot}{suf}_s{i}.png'; save(im, f'{d}/{sfn}')
                        ent['slices'].append(dict(sprite=sfn, tile=[tx, ty], sort_key_offset=tx + ty + 1 + it['sort_bias']))
                if st == it['states'][0]:
                    ent['hooks'] = [hook_rot(h, R) for h in it['hooks']]
                    rr.update(ent); rr['states'] = {}
                else:
                    rr['states'][st] = ent
            man['rotations'][rot] = rr
        json.dump(man, open(f'{d}/{iid}.json', 'w'), indent=1)
        report[iid] = all(v['formula_ok'] for v in man['rotations'].values())
    return report

# ---------------------------------------------------------------- map
W_, H_ = 23, 8
def zone(x): return '4B' if x < 8 else ('hall' if x < 12 else '4A')
STAIRS = {(x, y) for x in (10, 11) for y in (5, 6, 7)}
def floor_kind(x, y):
    if (x, y) in STAIRS: return None
    z = zone(x); v = 'a' if hsh(x, y, 11) < 0.5 else 'b'
    if z == '4B': return f'floor_4b_wood_{v}'
    if z == 'hall': return 'floor_hall'
    if 12 <= x <= 16 and y <= 1: return 'floor_4a_kitchen'
    return f'floor_4a_wood_{v}'
def wmat(x): return {'4B': '4b', 'hall': 'hall', '4A': '4a'}[zone(x)]
# placements: (item, origin x, y, rot, state, z, extra)
PLACE = [
    # ---- 4A (x 12..22)
    ('4a_fridge', 12, 0, 'SW', 'closed', 0), ('4a_kitchen_counter', 13, 0, 'SW', None, 0),
    ('4a_bookcase_collectibles', 16, 0, 'SW', None, 0), ('4a_couch', 18, 0, 'SW', None, 0),
    ('4a_flag_banner', 18.5, 0, 'SW', None, 0), ('4a_desk_laptop', 21, 0, 'SW', 'on', 0),
    ('4a_office_chair', 22, 1, 'NE', None, 0), ('4a_rug', 18, 1, 'SW', None, 0),
    ('4a_coffee_table', 18, 2, 'SW', None, 0), ('4a_takeout_set', 18, 2, 'SW', None, 0.45),
    ('4a_tv_stand', 18, 4, 'NE', 'on', 0), ('4a_armchair', 21, 2, 'SW', None, 0),
    ('4a_telescope', 22, 3, 'SW', None, 0), ('4a_whiteboard', 21, 5, 'SW', 'equations_a', 0),
    ('4a_whiteboard', 22, 5, 'SW', 'equations_b', 0), ('4a_floor_lamp', 17, 1, 'S', None, 0),
    ('4a_kitchen_island', 13, 2, 'SW', None, 0), ('4a_bar_stool', 13, 3, 'SW', None, 0), ('4a_bar_stool', 14, 3, 'SW', None, 0),
    ('4a_takeout_set', 14, 2, 'SW', None, 0.92), ('4a_dna_model', 20, 5, 'SW', None, 0),
    ('4a_front_door', 12, 3, 'SE', 'closed', 0),
    # ---- landing (x 8..11)
    ('hall_elevator_broken', 9, 0, 'SW', None, 0), ('hall_stair_flight', 10, 5, 'SW', None, 0),
    ('hall_stair_rail', 9, 5, 'NW', None, 0), ('4b_front_door', 8, 3, 'SE', 'closed', 0),
    # ---- 4B (x 0..7)
    ('4b_bedroom_door', 1, 0, 'SW', 'ajar', 0), ('4b_kitchen_counter', 4, 0, 'SW', None, 0), ('4b_fridge', 7, 0, 'SW', None, 0),
    ('4b_kitchen_bar', 5, 2, 'SW', None, 0), ('4b_bar_stool', 5, 3, 'SW', None, 0), ('4b_bar_stool', 6, 3, 'SW', None, 0),
    ('4b_wine_set', 6, 2, 'SW', None, 1.02), ('4b_couch', 0, 3, 'SE', None, 0), ('4b_rug', 1, 3, 'SW', None, 0),
    ('4b_coffee_table', 2, 3, 'SE', None, 0), ('4b_armchair_patterned', 3, 1, 'SW', None, 0),
    ('4b_dining_table_cluttered', 3, 5, 'SW', None, 0), ('4b_laundry_pile', 6, 5, 'SW', None, 0),
    ('4b_floor_lamp', 0, 2, 'SE', None, 0), ('4b_plant', 1, 7, 'SW', None, 0),
]
WINDOWS = {('y0', 21), ('y0', 22), ('y0', 2), ('y0', 3)}
DOORWAYS = {('x8', 3), ('x12', 3), ('y0', 1)}
def walls_for(scene):
    """list of (kind 'br'/'bl', mode, line, index, mat)"""
    xr = {'combined': range(0, 23), '4A': range(12, 23), '4B': range(0, 8)}[scene]
    out = []
    for x in xr:  # back wall y=0
        f = 'window' if ('y0', x) in WINDOWS else ('doorway' if ('y0', x) in DOORWAYS else None)
        out.append(('br', 'full', 0, x, wmat(x), f))
        if (x, 7) not in STAIRS: out.append(('br', 'cut', 8, x, wmat(x), None))      # front cutaway
    for y in range(8):
        if scene in ('combined', '4B'): out.append(('bl', 'full', 0, y, '4b', None))
        if scene == '4A': out.append(('bl', 'full', 12, y, '4a', 'doorway' if y == 3 else None))
        if scene in ('combined', '4B'): out.append(('bl', 'cut', 8, y, '4b' if scene == '4B' else 'hall', 'doorway' if y == 3 else None))
        if scene == 'combined': out.append(('bl', 'cut', 12, y, '4a', 'doorway' if y == 3 else None))
        if scene in ('combined', '4A'): out.append(('bl', 'cut', 23, y, '4a', None))
    return out

def build_tiles():
    for k, fn in FLOORS.items(): save(floor_tile(fn), f'{ENV}/tiles/{k}.png')
    meta = dict(floor={k: dict(sprite=f'{k}.png', size=[128, 64], anchor=[64, 0]) for k in FLOORS}, walls={})
    for mat in WALLMAT:
        for side in ('br', 'bl'):
            for mode in ('full', 'cut'):
                for feat in (None, 'window', 'window_day', 'doorway'):
                    if feat in ('window', 'window_day') and mode == 'cut': continue
                    img, anc = wall_piece(mat, side, mode, feat)
                    nm = f'wall_{mat}_{ {"br": "backright", "bl": "backleft"}[side]}_{ {"full": "full", "cut": "cutaway"}[mode]}' + (f'_{feat}' if feat else '')
                    save(img, f'{ENV}/tiles/{nm}.png')
                    meta['walls'][nm] = dict(sprite=f'{nm}.png', size=[img.shape[1], img.shape[0]], anchor=list(anc),
                                             runs_along='+x' if side == 'br' else '+y',
                                             note='anchor = segment top-vertex at floor level')
    json.dump(meta, open(f'{ENV}/tiles/tiles.json', 'w'), indent=1)
WCACHE = {}
def wimg(mat, side, mode, feat):
    k = (mat, side, mode, feat)
    if k not in WCACHE: WCACHE[k] = wall_piece(mat, side, mode, feat)
    return WCACHE[k]
FCACHE = {}
def fimg(k):
    if k not in FCACHE: FCACHE[k] = floor_tile(FLOORS[k])
    return FCACHE[k]

# ---------------------------------------------------------------- characters
def load_char(cid):
    p = f'{ROOT}/characters/{cid}'
    sheet = A(f'{p}/chr_{cid}.png'); at = json.load(open(f'{p}/chr_{cid}.json'))
    fr = {f['filename']: f['frame'] for f in at['frames']}
    return sheet, fr
def char_frame(cid, anim, d, k=0):
    sheet, fr = load_char(cid)
    nm = f'chr_{cid}_{anim}_{d}_{k:02d}'
    if nm not in fr:
        # mirrored directions are exported explicitly in the atlas; fall back to flip of the mirror source
        mir = {'E': 'W', 'NE': 'NW', 'SE': 'SW'}
        f = fr[f'chr_{cid}_{anim}_{mir[d]}_{k:02d}']
        return sheet[f['y']:f['y']+f['h'], f['x']:f['x']+f['w']][:, ::-1].copy()
    f = fr[nm]; return sheet[f['y']:f['y']+f['h'], f['x']:f['x']+f['w']].copy()

# ---------------------------------------------------------------- compositor
def compose(scene, chars=(), scale=1, labels=False, collect=None):
    xr = {'combined': (0, 23), '4A': (12, 23), '4B': (0, 8)}[scene]
    x0, x1 = xr
    # screen bounds
    pts = [scr(x, y, z) for x in (x0, x1) for y in (0, 8) for z in (0, 3.6, -1.7)]
    minx = int(min(p[0] for p in pts)) - 40; maxx = int(max(p[0] for p in pts)) + 40
    miny = int(min(p[1] for p in pts)) - 24; maxy = int(max(p[1] for p in pts)) + 24
    Wc, Hc = maxx - minx, maxy - miny
    can = Image.new('RGBA', (Wc, Hc), tuple(PAL['ink']) + (255,))
    def blit(im, sx, sy):  # sx,sy: screen pos of image top-left
        can.alpha_composite(Image.fromarray(im) if isinstance(im, np.ndarray) else im, (int(round(sx - minx)), int(round(sy - miny))))
    layers = {0: [], 1: [], 2: [], 3: [], 4: [], 5: []}
    inside = lambda x: x0 <= x < x1
    # floor
    for x in range(x0, x1):
        for y in range(8):
            k = floor_kind(x, y)
            if k:
                sx, sy = scr(x, y); layers[1].append((0, fimg(k), sx - 64, sy))
    # walls
    for side, mode, line, idx, mat, feat in walls_for(scene):
        img, anc = wimg(mat, side, mode, feat)
        if side == 'br': wx, wy = idx, line
        else: wx, wy = line, idx
        sx, sy = scr(wx, wy)
        if mode == 'full': layers[3].append((0, img, sx - anc[0], sy - anc[1]))
        else:
            key = (wx + wy) + (0.5 if side == 'br' else 0.4) - (0 if side == 'br' else 0)
            if side == 'br': key = wx + wy + 0.0 + 0.55        # in front of tile (x, 7) contents
            else: key = wx + wy + 0.45                           # between tiles (x-1,y) and (x,y)
            layers[5].append((key, img, sx - anc[0], sy - anc[1]))
    # items
    for (iid, ox, oy, rot, st, z) in PLACE:
        if not inside(int(ox)) and not (scene == '4B' and iid == '4b_front_door'): continue
        if scene == '4A' and iid == '4b_front_door': continue
        if scene == '4B' and iid == '4b_front_door': pass
        it = E.ITEMS[iid]
        if it['rotation_class'] == 'R1': rot = 'SW'
        R = rend(iid, rot, st or it['states'][0])
        nfx, nfy = R['fp']
        cox = R['pivot'][0] - (nfx - nfy)*64; coy = R['pivot'][1] - (nfx + nfy)*32
        sx, sy = scr(ox, oy, z); tlx, tly = sx - cox, sy - coy
        if scene == '4B' and iid == '4b_front_door':
            # in the solo 4B render its wall (x=8) is a FRONT wall, drawn as a cutaway stub -> cut the door down to the
            # same stub height (Sims-style cutaway door) so it sits in the doorway gap instead of standing free
            stub = WALL_CUT.shape[0] - 32
            for (tx, ty), im in slices(R):
                im = im.copy(); h, w = im.shape[:2]
                for c in range(w):
                    X = tlx + c; wy = ox - (X - scr(ox, 0)[0]) / 64.0
                    floor_sy = scr(ox, wy)[1]
                    cut = int(round(floor_sy - stub - tly))
                    if cut > 0: im[:min(cut, h), c, 3] = 0
                layers[5].append((ox + tx + oy + ty + 1 + it['sort_bias']*0.1, im, tlx, tly))
            continue
        if iid == 'hall_stair_flight': layers[0].append((0, R['img'], tlx, tly)); continue
        if it['layer'] == 'floor_decal': layers[2].append((0, R['img'], tlx, tly)); continue
        if it['mount'] == 'wall' and iid in ('4a_flag_banner', 'hall_elevator_broken'):
            layers[4].append((0, R['img'], tlx, tly)); continue
        for (tx, ty), im in slices(R):
            key = ox + tx + oy + ty + 1 + it['sort_bias']*0.1 + (0.02 if z > 0 else 0)
            layers[5].append((key, im, tlx, tly))
    # characters: (img128, feet world x,y, z, key_override)
    for ch in chars:
        im, (fx, fy), z, key = ch['img'], ch['pos'], ch.get('z', 0), ch.get('key')
        sx, sy = scr(fx, fy, z)
        k = key if key is not None else fx + fy + 0.01
        if ch.get('shadow', True):
            sh = Image.new('RGBA', (40, 12), (0, 0, 0, 0)); dr = ImageDraw.Draw(sh)
            dr.ellipse((0, 0, 39, 11), fill=tuple(PAL['shadow_violet']) + (110,))
            layers[5].append((k - 0.001, np.array(sh), sx - 20, sy - 6))
        layers[5].append((k, im, sx - ch.get('pivot', (64, 116))[0], sy - ch.get('pivot', (64, 116))[1]))
    for L in range(6):
        if L == 5 and collect is not None:   # background only; layer-5 sprites handed to the caller (live viewer export)
            collect.update(sprites=sorted(layers[5], key=lambda t: t[0]), origin=(minx, miny)); break
        for key, im, sx, sy in sorted(layers[L], key=lambda t: t[0]):
            blit(im, sx, sy)
        if L == 2:
            can = apply_glow(can, [l for l in LIGHTS4 if x0 <= l['pos'][0] < x1], minx, miny)
    out = snap_scene(can)
    if scale != 1: out = out.resize((Wc*scale, Hc*scale), Image.NEAREST)
    return out

from sprite_common import load_gpl as _lg
CHAR_COLS = {tuple(v) for c in ('sheldon', 'leonard', 'penny', 'howard', 'raj', 'bernadette', 'amy') for v in _lg(f'{ROOT}/palettes/bbt_{c}.gpl').values()}
def snap_scene(img):
    """scene renders are palette-strict: pixels blended by the translucent contact shadows are snapped to the nearest palette colour"""
    a = np.array(img.convert('RGBA')); cols = np.array(list(PAL.values()), int)
    flat = a[..., :3].reshape(-1, 3).astype(int)
    key = flat[:, 0]*65536 + flat[:, 1]*256 + flat[:, 2]
    pk = cols[:, 0]*65536 + cols[:, 1]*256 + cols[:, 2]
    ck = np.array([r*65536 + g*256 + b_ for r, g, b_ in CHAR_COLS])
    bad = ~np.isin(key, pk) & ~np.isin(key, ck)        # character sprites keep their own (character-palette) colours
    if bad.any():
        d = (((flat[bad][:, None, :] - cols[None]) ** 2) * np.array([0.3, 0.59, 0.11])).sum(2)
        flat[bad] = cols[d.argmin(1)]
    a[..., :3] = flat.reshape(a.shape[:2] + (3,)); a[..., 3] = 255
    return Image.fromarray(a.astype(np.uint8))

def palette_check(img):
    a = np.array(img.convert('RGBA')); cols = {tuple(v) for v in PAL.values()} | CHAR_COLS
    px = a[a[..., 3] == 255][:, :3]
    u = {tuple(p) for p in np.unique(px, axis=0)}
    return sorted(u - cols)

# ---------------------------------------------------------------- catalog
def catalog(ids=None, out='env_item_catalog.png', title=None):
    try: font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 12); fb = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 13)
    except Exception: font = fb = ImageFont.load_default()
    rows = []
    for iid, it in E.ITEMS.items():
        if ids is not None and iid not in ids: continue
        cells = [(rot, rend(iid, rot)['img']) for rot in item_rots(it)]
        for st in it['states'][1:]:
            cells.append((f'SW:{st}', rend(iid, item_rots(it)[0] if 'SW' not in item_rots(it) else 'SW', st)['img']))
        rows.append((iid, it, cells))
    cw = 300; lw = 230; pad = 8
    heights = [max(c[1].shape[0] for c in cells) + 26 for _, _, cells in rows]
    ncol = max(len(c) for _, _, c in rows)
    W = lw + ncol*cw; cols_per = [min(len(c), ncol) for _, _, c in rows]
    widths = [max([lw] + [lw + sum(min(cw, c[1].shape[1] + 16) for c in cells)]) for _, _, cells in rows]
    W = max(widths) + pad
    Ht = sum(heights) + 50
    sheet = Image.new('RGBA', (W, Ht), (52, 50, 62, 255)); dr = ImageDraw.Draw(sheet)
    dr.text((10, 12), title or f'BBT Pixel - Environment v2 item catalog ({len(rows)} items, all locations). Grok Bot build. Rotations left->right, extra states at end.', font=fb, fill=(240, 236, 220))
    y = 44
    for (iid, it, cells), h in zip(rows, heights):
        dr.line((0, y - 2, W, y - 2), fill=(80, 78, 92))
        dr.text((8, y + 4), iid, font=fb, fill=(250, 240, 200))
        info = [f"{it['location']}  P{it['priority']}  {it['rotation_class']}", f"fp {it['footprint'][0]}x{it['footprint'][1]}  h {it['height_m']} m",
                f"states: {', '.join(it['states'])}"[:34], f"hooks: {len(it['hooks'])}  {it['mount']}/{it['layer']}"[:34]]
        for n, s in enumerate(info): dr.text((8, y + 24 + 15*n), s, font=font, fill=(200, 198, 210))
        x = lw
        for lab, im in cells:
            pim = Image.fromarray(im)
            ww = min(cw, im.shape[1] + 16)
            sheet.alpha_composite(pim, (x + (ww - im.shape[1])//2, y + h - 22 - im.shape[0]))
            dr.text((x + 4, y + h - 18), lab, font=font, fill=(170, 220, 255))
            x += ww
        y += h
    sheet.save(f'{ENV}/renders/{out}'); return sheet.size

# ---------------------------------------------------------------- scene characters + map export
def world_hook(iid, hook_id, idx=0):
    n = 0
    for (pid, ox, oy, rot, st, z) in PLACE:
        if pid != iid: continue
        if n == idx:
            R = rend(iid, rot, st or E.ITEMS[iid]['states'][0])
            for h in E.ITEMS[iid]['hooks']:
                if h['id'] == hook_id:
                    px, py = R['xf'].fwd(*h['pos']); return ox + px, oy + py, dir_name(*[round(v, 6) for v in R['xf'].vec(*h['facing'])])
        n += 1
    raise KeyError(hook_id)
def scene_chars(scene):
    out = []
    if scene in ('combined', '4A'):
        js = json.load(open(f'{ENV}/renders/poses/sheldon_sit_SW.json'))
        sx_, sy_, fac = world_hook('4a_couch', 'seat0')
        out.append(dict(name='sheldon', img=A(f'{ENV}/renders/poses/{js["sprite"]}'), pos=(sx_, sy_), pivot=tuple(js['pivot']),
                        key=20.5, shadow=False, anim='sit (scene-only pose)', dir='SW', hook='4a_couch.seat0'))
        out.append(dict(name='leonard', img=char_frame('leonard', 'idle', 'SW', 0), pos=(15.5, 1.45), anim='idle', dir='SW'))
    if scene in ('combined', '4B') and os.path.exists(f'{ROOT}/characters/penny/chr_penny.png'):
        out.append(dict(name='penny', img=char_frame('penny', 'idle', 'SW', 0), pos=PENNY_POS, anim='idle', dir='SW'))
        # v2 cast: Bernadette and Amy visiting Penny (girls' night)
        for nm, pos, d in (('bernadette', BERNADETTE_POS, 'SE'), ('amy', AMY_POS, 'SW')):
            if os.path.exists(f'{ROOT}/characters/{nm}/chr_{nm}.png'):
                out.append(dict(name=nm, img=char_frame(nm, 'idle', d, 0), pos=pos, anim='idle', dir=d))
    return out
PENNY_POS = (4.5, 4.4)
BERNADETTE_POS = (4.3, 5.1)
AMY_POS = (5.5, 5.0)

def export_map():
    floor_names = list(FLOORS)
    gid = {k: i + 1 for i, k in enumerate(floor_names)}
    data = []
    for y in range(H_):
        for x in range(W_):
            k = floor_kind(x, y); data.append(gid[k] if k else 0)
    objs, oid = [], 1
    def obj(name, typ, wx, wy, props, layer):
        nonlocal oid
        o = dict(id=oid, name=name, type=typ, x=round(wx*64, 2), y=round(wy*64, 2), width=0, height=0, rotation=0, visible=True, point=True,
                 properties=[dict(name=k, type=('string' if isinstance(v, str) else 'float' if isinstance(v, float) else 'int' if isinstance(v, int) and not isinstance(v, bool) else 'bool' if isinstance(v, bool) else 'string'),
                                  value=(v if isinstance(v, (str, int, float, bool)) else json.dumps(v))) for k, v in props.items()])
        oid += 1; layer.append(o)
    walls, items, hooks, chars = [], [], [], []
    for side, mode, line, idx, mat, feat in walls_for('combined'):
        wx, wy = (idx, line) if side == 'br' else (line, idx)
        nm = f'wall_{mat}_{"backright" if side == "br" else "backleft"}_{"full" if mode == "full" else "cutaway"}' + (f'_{feat}' if feat else '')
        obj(nm, 'wall', wx, wy, dict(sprite=f'../tiles/{nm}.png', runs_along='+x' if side == 'br' else '+y', world_x=wx, world_y=wy,
                                     mode=mode, sort_key=float(wx + wy + (0.55 if side == 'br' else 0.45)) if mode == 'cut' else -1.0), walls)
    for (iid, ox, oy, rot, st, z) in PLACE:
        it = E.ITEMS[iid]; st = st or it['states'][0]
        R = rend(iid, rot if it['rotation_class'] != 'R1' else 'SW', st)
        obj(iid, 'item', ox, oy, dict(item_id=iid, rot=rot, state=st, z=float(z), world_x=float(ox), world_y=float(oy),
                                      footprint=list(R['fp']), manifest=f'../items/{iid}/{iid}.json', zone=zone(int(ox)),
                                      sort_key=float(ox + oy + 1 + it['sort_bias']*0.1), blocks_walk=it['blocks_walk']), items)
        for h in it['hooks']:
            px, py = R['xf'].fwd(*h['pos']); vx, vy = R['xf'].vec(*h['facing'])
            obj(f'{iid}.{h["id"]}', 'hook', ox + px, oy + py, dict(item_id=iid, hook=h['id'], hook_type=h['type'], facing=dir_name(round(vx, 6), round(vy, 6)),
                                                                   anim=h['anim'], capacity=h['capacity'], z=float(h.get('z', 0) + z), tags=','.join(h['tags']),
                                                                   owner=h.get('priority_owner', '')), hooks)
    for ch in scene_chars('combined'):
        obj(ch['name'], 'character', ch['pos'][0], ch['pos'][1], dict(anim=ch['anim'], dir=ch['dir'], hook=ch.get('hook', '')), chars)
    zones = []
    for nm, (a, b) in (('4B', (0, 8)), ('hall_4f', (8, 12)), ('4A', (12, 23))):
        zones.append(dict(id=oid, name=nm, type='zone', x=a*64, y=0, width=(b - a)*64, height=8*64, rotation=0, visible=True)); oid += 1
    tm = dict(type='map', version='1.10', tiledversion='1.10.2', orientation='isometric', renderorder='right-down',
              width=W_, height=H_, tilewidth=128, tileheight=64, infinite=False, nextlayerid=8, nextobjectid=oid,
              properties=[dict(name='px_per_m', type='int', value=64), dict(name='projection', type='string', value='sx=(x-y)*64, sy=(x+y)*32-z*64'),
                          dict(name='note', type='string', value='object x,y are world tiles*64 (Tiled iso object space); see properties world_x/world_y')],
              tilesets=[dict(firstgid=1, name='bbt_floors', tilewidth=128, tileheight=64, tilecount=len(floor_names), columns=0,
                             grid=dict(orientation='isometric', width=128, height=64),
                             tiles=[dict(id=i, image=f'../tiles/{k}.png', imagewidth=128, imageheight=64,
                                         properties=[dict(name='name', type='string', value=k)]) for i, k in enumerate(floor_names)])],
              layers=[dict(id=1, name='floor', type='tilelayer', width=W_, height=H_, x=0, y=0, opacity=1, visible=True, data=data),
                      dict(id=2, name='zones', type='objectgroup', objects=zones, opacity=1, visible=True, x=0, y=0, draworder='index'),
                      dict(id=3, name='walls', type='objectgroup', objects=walls, opacity=1, visible=True, x=0, y=0, draworder='index'),
                      dict(id=4, name='items', type='objectgroup', objects=items, opacity=1, visible=True, x=0, y=0, draworder='topdown'),
                      dict(id=5, name='hooks', type='objectgroup', objects=hooks, opacity=1, visible=True, x=0, y=0, draworder='index'),
                      dict(id=6, name='characters', type='objectgroup', objects=chars, opacity=1, visible=True, x=0, y=0, draworder='topdown')])
    json.dump(tm, open(f'{ENV}/maps/floor4_4A_hall_4B.tmj', 'w'), indent=1)
    # engine map (simple)
    walk = [[0 if floor_kind(x, y) is None else 1 for x in range(W_)] for y in range(H_)]
    for (iid, ox, oy, rot, st, z) in PLACE:
        it = E.ITEMS[iid]
        if not it['blocks_walk'] or z > 0 or it['layer'] == 'floor_decal' or it['mount'] == 'wall': continue
        R = rend(iid, rot if it['rotation_class'] != 'R1' else 'SW', st or it['states'][0])
        for tx in range(R['fp'][0]):
            for ty in range(R['fp'][1]):
                X, Y = int(ox) + tx, int(oy) + ty
                if 0 <= X < W_ and 0 <= Y < H_: walk[Y][X] = 0
    eng = dict(id='floor4', size=[W_, H_], tile=[128, 64], px_per_m=64,
               zones={'4B': [0, 0, 8, 8], 'hall_4f': [8, 0, 4, 8], '4A': [12, 0, 11, 8]},
               floor=[[floor_kind(x, y) for x in range(W_)] for y in range(H_)], walkable=walk,
               doors=[dict(item='4b_front_door', tile=[8, 3], connects=['hall_4f', '4B']), dict(item='4a_front_door', tile=[12, 3], connects=['hall_4f', '4A']),
                      dict(item='hall_stair_flight', tile=[10, 7], connects=['hall_4f', 'floor3 (stub)'])],
               walls=[dict(zip(('side', 'mode', 'line', 'index', 'mat', 'feature'), w)) for w in walls_for('combined')],
               items=[dict(item=i, x=ox, y=oy, rot=r, state=st or E.ITEMS[i]['states'][0], z=z) for (i, ox, oy, r, st, z) in PLACE],
               spawns={'sheldon': '4a_couch.seat0', 'leonard': [15.5, 1.45], 'penny': list(PENNY_POS), 'bernadette': list(BERNADETTE_POS), 'amy': list(AMY_POS)},
               sort=dict(rule='slice key = tile x+y+1 (+sort_bias*0.1); character key = feet x+y; seated = after seat slices; wall-mounted & full walls drawn before sorted pass; cutaway stubs keyed x+y+0.45/0.55'))
    json.dump(eng, open(f'{ENV}/maps/floor4_engine.json', 'w'), indent=1)
    return len(items), len(hooks)

def renders():
    out = {}
    for scene, nm in (('combined', 'floor4_combined'), ('4A', 'apt4A'), ('4B', 'apt4B')):
        ch = scene_chars(scene)
        im = compose(scene, ch); im.save(f'{ENV}/renders/{nm}_1x.png')
        im.resize((im.width*2, im.height*2), Image.NEAREST).save(f'{ENV}/renders/{nm}_2x.png')
        out[nm] = dict(size=im.size, off_palette=len(palette_check(im)), chars=[c['name'] for c in ch])
    return out

if __name__ == '__main__':
    what = sys.argv[1:] or ['tiles', 'items', 'catalog', 'map', 'renders']
    if 'tiles' in what: build_tiles(); print('tiles ok')
    if 'items' in what: r = export_items(); print('items', len(r), 'formula_ok all:', all(r.values()), [k for k, v in r.items() if not v])
    if 'catalog' in what: print('catalog', catalog())
    if 'map' in what: print('map', export_map())
    if 'renders' in what: print('renders', renders())
