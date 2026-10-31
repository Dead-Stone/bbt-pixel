"""Environment v2 items: AIT campus (cafeteria, physics offices + lab), The Amber Slice restaurant,
street exterior + lobby, Raj's apartment.  Same conventions as env_items.py: canonical footprint fx x fy metres,
FRONT faces +Y (SW view), hooks in canonical metres.  All signage / names / crests are original (no real logos)."""
import math, random
from iso_render import Prism, box, cyl, MAT
from env_tex import hsh, line, wood_grain, text_px, text_w
from env_items import (item, H, rod, rot_poly, cushion_tex, panel_tex, knob_tex, grid_tex, text_tex, first,
                       screen_tex, book_row, armchair, DOOR_STATES)

MAT.update({
 'teal':     ('4b_turquoise', 'cafe_teal', 'tile_green_dk', 'shadow_violet'),
 'booth':    ('marker_red', 'ccf_booth_red', 'leather_xdk', 'ink_2'),
 'stone':    ('white_hi', 'wall_4a_hi', 'wall_4a', 'wall_4a_dk'),
 'concrete': ('paper', 'grey_lt', 'grey', 'grey_dk'),
 'iron':     ('grey_dk', 'shadow_violet', 'ink_2', 'ink'),
 'brick':    ('marker_red', 'ccf_booth_red', 'leather_xdk', 'ink_2'),
 'cork':     ('wall_4a_hi', 'wood_hi', 'wood', 'wood_dk'),
 'bark':     ('wood', 'wood_dk', 'wood_xdk', 'ink_2'),
 'slate':    ('grey', 'grey_dk', 'shadow_violet', 'ink_2'),
 'leaf':     ('4b_lime', 'plant_green', 'tile_green_dk', 'shadow_violet'),
 'blossom':  ('paper', '4b_purple', 'shadow_violet', 'ink_2'),
 'car':      ('screen_glow', 'comic_blue', 'marker_blue', 'shadow_violet'),
 'chrome':   ('white_hi', 'grey_lt', 'grey', 'grey_dk'),
 'mustard':  ('comic_yellow', 'tape_yellow', 'tape_yellow_dk', 'wood_dk'),
})
CAMPUS, REST, STREET, LOBBY, RAJ = 'AIT_campus', 'amber_slice', 'street', 'lobby', 'raj_apt'

def px_text(txt, c, r, sc=1):
    return c >= 0 and r >= 0 and text_px(txt, c//sc, r//sc)

# ---------------------------------------------------------------- AIT crest (original)
def crest_px(u, v, ribbon=False):
    """Arroyo Institute of Technology crest. u,v in 0..1 (v down). shield: teal sky, gold rising sun with rays and an
    atom orbit, blue arroyo river over cream ground, 3 stars.  returns palette name or None"""
    if v < 0 or v > 1 or u < 0 or u > 1: return None
    hw = 0.48 if v < 0.55 else 0.48*math.sqrt(max(0.0, 1 - ((v - 0.55)/0.45)**2))
    du = abs(u - 0.5)
    if du > hw: return None
    if du > hw - 0.07 or v < 0.06: return 'ccf_amber' if du < hw - 0.035 and v > 0.03 else 'ink'
    if v > 0.56:
        w = 0.6 + 0.04*math.sin(u*18)
        if w < v < w + 0.09: return 'comic_blue' if (int(u*40) + int(v*60)) % 3 else 'screen_glow'
        return 'cafe_cream'
    # sky half
    d = math.hypot(u - 0.5, (v - 0.56)*1.0)
    if d < 0.17: return 'comic_yellow' if v > 0.44 or u < 0.5 else 'lamp_warm'
    ang = math.degrees(math.atan2(0.56 - v, u - 0.5))
    if d < 0.3 and (ang % 30) < 8: return 'ccf_amber'
    orb = math.hypot((u - 0.5)/0.34, (v - 0.33)/0.12)
    if abs(orb - 1) < 0.12 and v < 0.5: return 'lamp_warm'
    for sx, sv in ((0.2, 0.17), (0.8, 0.17), (0.5, 0.11)):
        if abs(u - sx) + abs(v - sv) < 0.035: return 'white_hi'
    return 'cafe_teal'

def crest_tex(x0, x1, z0, z1, face_name='front'):
    def t(face, x, y, z, tone, rc):
        if face != face_name: return None
        return crest_px((x - x0)/(x1 - x0), (z1 - z)/(z1 - z0))
    return t

# ---------------------------------------------------------------- generic swing door with a custom slab texture
def swing_door(slab_mat, casing_mat, slab_tex=None, swing=1, w=0.8, glass=False):
    def b(state='closed'):
        ang = {'closed': 0, 'ajar': 18, 'open_1': 30, 'open_2': 60, 'open': 92}[state]
        x0, x1 = 0.5 - w/2, 0.5 + w/2
        P = [box(x0 - 0.08, 0.0, 0, x0, 0.08, 2.2, casing_mat), box(x1, 0.0, 0, x1 + 0.08, 0.08, 2.2, casing_mat),
             box(x0 - 0.08, 0.0, 2.1, x1 + 0.08, 0.08, 2.22, casing_mat)]
        P.append(Prism([(x0, 0.0), (x1, 0.0), (x1, 0.015), (x0, 0.015)], 0, 2.1, 'black', outline=False))
        y0, y1 = 0.02, 0.065; hx, hy = x0, (y1 if swing > 0 else y0)
        poly = rot_poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], hx, hy, math.radians(ang)*(1 if swing > 0 else -1))
        tex = first(knob_tex([(x1 - 0.1, 1.0)]), slab_tex or (lambda *a: None))
        a = math.radians(ang)*(1 if swing > 0 else -1); c, s = math.cos(-a), math.sin(-a)
        def wrap(face, x, y, z, tone, rc):
            if ang == 0: return tex(face, x, y, z, tone, rc)
            lx = x0 + (x - x0)*c - (y - hy)*s
            f = 'front' if face in ('front', 'right' if swing > 0 else 'left') and ang > 45 else face
            return tex(f, lx, y, z, tone, rc)
        P.append(Prism(poly, 0, 2.08, slab_mat, wrap))
        return P
    return b

def porthole_tex(face, x, y, z, tone, rc):
    if face not in ('front', 'back'): return None
    d = math.hypot(x - 0.5, z - 1.5)
    if d < 0.13: return 'screen_glow' if (x - 0.5) - (z - 1.5) > 0.05 or d < 0.08 else 'white_hi'
    if d < 0.16: return 'grey_dk'
    if z < 0.3 and 0.14 < x < 0.86: return 'grey_lt' if abs(z - 0.29) < 1/64 else 1
    return None

def plate_tex(lines_, zt, x0=0.18, x1=0.82, bg='lamp_warm', ink='ink_2', face_name='front'):
    """small engraved name plate on a door (lines of text, 1x font, centred)"""
    zh = len(lines_)*6/64 + 2/64
    def t(face, x, y, z, tone, rc):
        if face != face_name or not (x0 <= x <= x1 and zt - zh <= z <= zt): return None
        r = int((zt - z)*64) - 1; li, rr = divmod(r, 6)
        if li < len(lines_):
            s = lines_[li]; off = int((x1 - x0)*64 - text_w(s))//2
            if px_text(s, int((x - x0)*64) - off, rr): return ink
        if abs(z - (zt - zh)) < 1/64: return 'ccf_amber'
        return bg
    return t

def glass_door_tex(face, x, y, z, tone, rc):
    if face not in ('front', 'back'): return None
    if 0.2 < x < 0.8 and 0.35 < z < 1.95:
        d = (x - 0.2) - (z - 0.35)*0.5
        return 'white_hi' if 0.1 < d < 0.14 else ('screen_glow' if z > 1.15 else 'grey_lt')
    return None
MAT['glassd'] = ('white_hi', 'screen_glow', 'grey_lt', 'grey')

# ---------------------------------------------------------------- whiteboards (wall-mounted, wide)
WB_STATES = ('equations_a', 'equations_b', 'diagram', 'music', 'blank')
def wb_tex(state, x0, x1, z0, z1, seed=0):
    R = random.Random(hash((state, seed)) & 0xffff)
    syms = '=+-()^/0123456789EMCXYZNPKLAR'
    nlines = int((z1 - z0)*64 - 6)//7
    rows = [(''.join(R.choice(syms) for _ in range(R.randint(6, 18))), R.choice(['marker_blue', 'marker_blue', 'marker_red', 'marker_green', 'ink_2']),
             R.randint(0, 20)) for _ in range(nlines)]
    def t(face, x, y, z, tone, rc):
        if face != 'front': return None
        if x < x0 or x > x1 or z < z0 or z > z1: return None
        if x < x0 + 2/64 or x > x1 - 2/64 or z < z0 + 2/64 or z > z1 - 2/64: return 'grey'
        c = int((x - x0)*64) - 4; r = int((z1 - z)*64) - 4
        if state == 'blank': return 'white_hi' if (x - z*0.7) % 0.7 < 0.05 else 'paper'
        if state == 'music':      # staves + notes
            li, rr = divmod(r, 14)
            if rr < 9 and rr % 2 == 0: return 'grey' if rr else 'ink_2'
            if rr < 9 and (c % 11) in (3, 4) and (rr + li + c//11) % 3 == 0: return 'ink'
            return 'paper'
        if state == 'diagram':    # original "Feynman-style" sketch: wiggly line, arrows, boxes
            u = (x - x0)/(x1 - x0); v = (z1 - z)/(z1 - z0)
            if 0.15 < u < 0.45 and abs(v - 0.5 - 0.08*math.sin(u*70)) < 0.03: return 'marker_red'
            if abs(v - 0.5) < 0.02 and (0.05 < u < 0.15 or 0.45 < u < 0.55): return 'marker_blue'
            if abs(abs(u - 0.15)*1.0 - abs(v - 0.5)*0.4) < 0.01 and u < 0.15 and abs(v - 0.5) < 0.25: return 'marker_blue'
            if 0.62 < u < 0.92 and (abs(v - 0.2) < 0.02 or abs(v - 0.8) < 0.02) or (abs(u - 0.62) < 0.008 or abs(u - 0.92) < 0.008) and 0.2 < v < 0.8:
                return 'marker_green'
            li, rr = divmod(r, 7)
            if 0.64 < u < 0.9 and rr < 5 and li % 2 and px_text(rows[li % len(rows)][0], c - int((0.65*(x1-x0))*64), rr): return 'ink_2'
            return 'paper'
        li, rr = divmod(r, 7)
        if 0 <= li < len(rows) and rr < 5:
            s, col, ind = rows[li]
            if px_text(s, c - ind, rr): return col
        if state == 'equations_b' and abs(math.hypot(x - (x0 + x1)/2 - 0.3, z - (z0 + 0.3)) - 0.12) < 1/64: return 'marker_red'
        return 'paper'
    return t

# ================================================================== AIT CAFETERIA
@item('cafe_table_long', CAMPUS, (3, 1), 0.76, 'R2', 'P0',
      notes='6-seat cafeteria table; chairs (cafe_chair) sit on the tiles in front/behind. seat0-2 north side (face SW), seat3-5 south side (face NE)',
      hooks=[H(f'seat{i}', 'sit', (0.5 + i, -0.45), (0, 1), 'sit_chair_eat', approach=(i, -1), tags=['needs_chair']) for i in range(3)] +
            [H(f'seat{3+i}', 'sit', (0.5 + i, 1.45), (0, -1), 'sit_chair_eat', approach=(i, 1), tags=['needs_chair']) for i in range(3)] +
            [H(f'tray{i}', 'place_item', (0.5 + i, 0.5), (0, 1), tags=['tray', 'lunch'], z=0.76) for i in range(3)])
def cafe_table(state='default'):
    P = []
    for x in (0.25, 2.65):
        P.append(box(x, 0.2, 0, x + 0.1, 0.8, 0.04, 'steel')); P.append(box(x + 0.02, 0.46, 0.04, x + 0.08, 0.54, 0.72, 'steel'))
    P.append(box(0.3, 0.47, 0.3, 2.7, 0.53, 0.34, 'steel'))
    def top(face, x, y, z, tone, rc):
        if face == 'top': return 'white_hi' if (x + y*2) % 0.9 < 0.03 else 'cafe_cream'
        return 'cafe_teal' if z > 0.73 else 'tile_green_dk'
    P.append(box(0.04, 0.08, 0.71, 2.96, 0.92, 0.76, 'cream', top))
    # lunch clutter: trays, plates, a juice box
    P.append(box(0.25, 0.15, 0.76, 0.75, 0.48, 0.775, 'orange')); P.append(cyl(0.45, 0.31, 0.1, 0.775, 0.79, 'white', n=10))
    P.append(box(1.4, 0.55, 0.76, 1.85, 0.85, 0.775, 'teal')); P.append(cyl(1.6, 0.7, 0.09, 0.775, 0.79, 'white', n=10))
    P.append(box(2.4, 0.2, 0.76, 2.48, 0.26, 0.86, 'yellow'))
    return P

@item('cafe_chair', CAMPUS, (1, 1), 0.86, 'R4', 'P0', notes='stackable teal shell chair, back toward canonical -Y',
      hooks=[H('seat0', 'sit', (0.5, 0.55), (0, 1), 'sit_chair', approach=(0, 1))])
def cafe_chair(state='default'):
    P = [box(x, y, 0, x + 0.04, y + 0.04, 0.44, 'steel') for x in (0.24, 0.72) for y in (0.26, 0.76)]
    P.append(box(0.2, 0.24, 0.42, 0.8, 0.82, 0.47, 'teal'))
    P.append(box(0.22, 0.2, 0.47, 0.78, 0.27, 0.86, 'teal', lambda f, x, y, z, t, rc: 0 if f == 'top' else (3 if abs(z - 0.62) < 1/64 else None)))
    return P

def food_wells(face, x, y, z, tone, rc):
    if face != 'top' or z < 0.89: return None
    if 0.15 < y < 0.75:
        i = int((x - 0.1)/0.62)
        if 0 <= i < 6 and 0.14 < (x - 0.1) % 0.62 < 0.58:
            cols = [('plant_green', 'marker_green'), ('ccf_amber', 'lamp_warm'), ('marker_red', 'ccf_booth_red'),
                    ('cafe_cream', 'paper'), ('wood_hi', 'wood'), ('4b_orange', 'ccf_amber')][i]
            return cols[0] if hsh(int(x*64)//2, int(y*64)//2, i) < 0.6 else cols[1]
        return 'grey_lt'
    return None
@item('cafe_food_line', CAMPUS, (4, 1), 1.45, 'R4', 'P0', notes='hot-food line with sneeze guard and tray rail. Diners queue on the front (+Y) side; staff serve from behind',
      hooks=[H(f'queue{i}', 'queue', (0.5 + i, 1.4), (0, -1), 'stand_queue', approach=(i, 1)) for i in range(4)] +
            [H('take_tray', 'use', (0.3, 1.4), (0, -1), 'take_tray', approach=(0, 1), tags=['tray']),
             H('serve', 'work', (2.0, -0.45), (0, 1), 'serve_food', approach=(2, -1), tags=['staff'])])
def cafe_food_line(state='default'):
    P = [box(0.02, 0.1, 0, 3.98, 0.85, 0.12, 'teal'),
         box(0.02, 0.1, 0.12, 3.98, 0.85, 0.88, 'steel', lambda f, x, y, z, t, rc: (3 if f == 'front' and (x % 1.0) < 1/64 else None)),
         box(0.0, 0.08, 0.88, 4.0, 0.88, 0.92, 'steel', food_wells)]
    P.append(box(0.0, 0.88, 0.8, 4.0, 1.0, 0.84, 'chrome'))                 # tray slide
    for x in (0.05, 1.98, 3.9): P.append(box(x, 0.4, 0.92, x + 0.05, 0.45, 1.4, 'chrome'))
    P.append(box(0.0, 0.62, 1.38, 4.0, 0.92, 1.41, 'glass', lambda f, x, y, z, t, rc: ('white_hi' if (x*1.5 - y) % 0.8 < 0.06 else ('screen_glow' if f == 'top' else None))))
    P.append(box(0.08, 0.92, 0.84, 0.48, 1.0, 1.0, 'orange'))                # tray stack at the start of the line
    return P

@item('cafe_menu_board', CAMPUS, (2, 1), 2.6, 'R4', 'P1', blocks=False, mount='wall', sort_bias=-1, shadow=False, layer='wall_decal',
      notes='wall menu over the food line: original daily specials')
def cafe_menu_board(state='default'):
    lines_ = [('TODAY', 'comic_yellow', 2), ('SOUP 2.50', 'white_hi', 1), ('PASTA 4.75', 'white_hi', 1), ('TACOS 4.25', 'white_hi', 1)]
    def t(face, x, y, z, tone, rc):
        if face != 'front': return None
        if x < 0.24 or x > 1.76 or z < 1.72 or z > 2.5: return None
        if x < 0.27 or x > 1.73 or z < 1.75 or z > 2.47: return 'cafe_teal'
        c = int((x - 0.32)*64); r = int((2.43 - z)*64); y0 = 0
        for s, col, sc in lines_:
            if y0 <= r < y0 + 5*sc and px_text(s, c, r - y0, sc): return col
            y0 += 5*sc + 3
        return 'ink_2'
    return [box(0.24, 0.0, 1.72, 1.76, 0.04, 2.5, 'dark', t)]

def vend_tex(kind):
    def t(face, x, y, z, tone, rc):
        if face != 'front': return None
        if 0.08 < x < 0.62 and 0.55 < z < 1.75:
            row = int((1.75 - z)/0.2); rz = (1.75 - z) % 0.2
            if rz < 0.03: return 'grey_lt'
            col = int((x - 0.08)/0.09)
            if rz > 0.07 and (x - 0.08) % 0.09 > 0.02:
                pal = ['marker_red', 'comic_yellow', 'comic_blue', 'marker_green', '4b_orange', 'paper'] if kind == 'snack' else ['marker_red', 'comic_blue', '4b_lime', 'paper']
                return pal[int(hsh(row, col, len(kind))*len(pal))]
            return 'screen_glow' if (x + z) % 0.5 < 0.05 else 'ink_2'
        if 0.68 < x < 0.88:
            if 1.35 < z < 1.5: return 'marker_green' if (int(x*64) + int(z*64)) % 2 else 'ink_2'
            if 0.9 < z < 1.3: return 'grey_dk' if int((z - 0.9)*64) % 4 == 0 else 1
        if 0.12 < x < 0.6 and 0.2 < z < 0.4: return 'ink_2'
        return None
    return t
for _kind, _mat in (('snack', 'red'), ('drink', 'blue'), ('coffee', 'wood_dk')):
    item(f'cafe_vending_{_kind}', CAMPUS, (1, 1), 1.9, 'R4', 'P1', notes='original unbranded vending machine',
         hooks=[H('use', 'use', (0.5, 1.35), (0, -1), 'use_vending', approach=(0, 1), tags=[_kind])])(
         (lambda m, k: lambda state='default': [box(0.04, 0.1, 0, 0.96, 0.9, 1.9, m, vend_tex(k))])(_mat, _kind))

@item('cafe_drink_station', CAMPUS, (1, 1), 1.35, 'R4', 'P1', hooks=[H('use', 'use', (0.5, 1.35), (0, -1), 'fill_cup', approach=(0, 1), tags=['drink'])])
def cafe_drink(state='default'):
    P = [box(0.04, 0.12, 0, 0.96, 0.88, 0.9, 'teal', panel_tex([(0.1, 0.1, 0.9, 0.8)])), box(0.02, 0.1, 0.9, 0.98, 0.9, 0.94, 'steel')]
    def disp(face, x, y, z, tone, rc):
        if face == 'front' and z > 1.15 and 0.15 < x < 0.85: return ['marker_red', 'comic_yellow', '4b_orange'][int((x - 0.15)/0.234)] if (x - 0.15) % 0.234 > 0.03 else 'grey_lt'
        if face == 'front' and 1.0 < z < 1.06 and (x - 0.15) % 0.234 < 0.06: return 'grey_dk'
        return None
    P.append(box(0.12, 0.2, 0.94, 0.88, 0.62, 1.35, 'steel', disp))
    for i in range(3): P.append(cyl(0.2 + 0.08*i, 0.75, 0.035, 0.94, 1.02 + 0.03*i, 'white', n=8))
    return P

@item('cafe_trash_bin', CAMPUS, (1, 1), 1.0, 'R1', 'P2', hooks=[H('use', 'use', (0.5, 1.3), (0, -1), 'throw_away', approach=(0, 1))])
def cafe_trash(state='default'):
    return [box(0.25, 0.25, 0, 0.75, 0.75, 0.95, 'teal', lambda f, x, y, z, t, rc: 0 if f == 'top' else None),
            box(0.22, 0.22, 0.95, 0.78, 0.78, 1.0, 'steel', lambda f, x, y, z, t, rc: 'ink_2' if f == 'top' and abs(y - 0.5) < 0.05 and abs(x - 0.5) < 0.18 else None)]

def cork_tex(seed, x0, x1, z0, z1):
    def t(face, x, y, z, tone, rc):
        if face != 'front' or not (x0 <= x <= x1 and z0 <= z <= z1): return None
        if x < x0 + 2/64 or x > x1 - 2/64 or z < z0 + 2/64 or z > z1 - 2/64: return 'wood_dk'
        for k in range(9):
            fx = x0 + 0.06 + hsh(seed, k)*(x1 - x0 - 0.3); fz = z0 + 0.06 + hsh(seed, k, 1)*(z1 - z0 - 0.3)
            w, h = 0.14 + 0.08*hsh(seed, k, 2), 0.16 + 0.08*hsh(seed, k, 3)
            if fx <= x <= fx + w and fz <= z <= fz + h:
                col = ['paper', 'white_hi', 'comic_yellow', 'screen_glow', '4b_lime', 'paper'][int(hsh(seed, k, 4)*6)]
                if abs(x - fx - w/2) < 1.5/64 and abs(z - fz - h + 0.02) < 1.5/64: return 'marker_red'     # pin
                if int((fz + h - z)*64) % 3 == 0 and 0.02 < x - fx < w - 0.03 and z < fz + h - 0.04: return 'grey'
                return col
        return 'wood_hi' if hsh(int(x*64)//2, int(z*64)//2, seed) < 0.3 else 'wood'
    return t
@item('cafe_bulletin_board', CAMPUS, (1, 1), 1.9, 'R4', 'P2', blocks=False, mount='wall', sort_bias=-1, shadow=False, layer='wall_decal',
      notes='cork board with flyers (lecture notices, roommate-wanted, lost calculator)', hooks=[H('read', 'look', (0.5, 0.6), (0, -1), 'read_board', approach=(0, 0))])
def cafe_board(state='default'):
    return [box(0.1, 0.0, 1.0, 0.9, 0.04, 1.85, 'cork', cork_tex(7, 0.1, 0.9, 1.0, 1.85))]

def poster_tex(kind, x0, x1, z0, z1):
    def t(face, x, y, z, tone, rc):
        if face != 'front' or not (x0 <= x <= x1 and z0 <= z <= z1): return None
        if x < x0 + 1.5/64 or x > x1 - 1.5/64 or z < z0 + 1.5/64 or z > z1 - 1.5/64: return 'ink_2'
        u = (x - x0)/(x1 - x0); v = (z1 - z)/(z1 - z0)
        if kind == 'particles':     # original particle-family chart: 4x4 coloured tiles
            if v > 0.86: return 'ink_2' if (int(u*40) % 3) and abs(v - 0.93) < 0.03 else 'paper'
            gx, gy = int(u*4.2), int(v*4.6)
            if (u*4.2) % 1 < 0.12 or (v*4.6) % 1 < 0.12: return 'paper'
            return ['marker_green', 'marker_green', 'comic_red', 'comic_yellow'][min(gx, 3)] if gy < 3 else 'screen_glow'
        if kind == 'neutrino':      # detector sphere with photomultiplier dots
            d = math.hypot(u - 0.5, (v - 0.45)*1.3)
            if v > 0.85: return 'comic_yellow' if (int(u*40) % 3) and abs(v - 0.92) < 0.03 else 'ink_2'
            if d < 0.32: return 'lamp_warm' if (int(u*30) + int(v*30)) % 2 == 0 and d < 0.3 else 'ccf_amber'
            return 'ink_2' if hsh(int(u*50), int(v*60)) > 0.04 else 'white_hi'
        if kind == 'journal':       # framed journal cover (original masthead "PHYS REV X")
            if v < 0.16: return 'white_hi' if px_text('PHYS', int((u - 0.12)*(x1 - x0)*64), int((v - 0.03)*(z1 - z0)*64)) else 'marker_red'
            if 0.25 < v < 0.75 and 0.15 < u < 0.85:
                return 'comic_blue' if math.sin(u*20 + v*8) > 0.2 else 'screen_glow'
            return 'grey' if (int(v*(z1 - z0)*64) % 3 == 0 and 0.1 < u < 0.9 and v > 0.8) else 'paper'
        if kind == 'nebula':
            d = math.hypot(u - 0.45, v - 0.5)
            if d < 0.25: return '4b_purple' if hsh(int(u*40), int(v*40)) < 0.7 else 'marker_red'
            if d < 0.36 and hsh(int(u*30), int(v*30), 2) < 0.5: return 'shadow_violet'
            return 'white_hi' if hsh(int(u*60), int(v*80), 3) < 0.03 else 'ink'
        if kind == 'award':         # certificate with gold seal
            if abs(math.hypot((u - 0.75)*1.2, v - 0.75)) < 0.11: return 'lamp_warm' if (u + v) % 0.08 < 0.04 else 'ccf_amber'
            if 0.12 < v < 0.17 and 0.2 < u < 0.8: return 'ink_2'
            if 0.3 < v < 0.6 and int(v*(z1 - z0)*64) % 3 == 0 and 0.15 < u < 0.85: return 'grey'
            return 'cafe_cream' if 0.05 < u < 0.95 and 0.05 < v < 0.95 else 'ccf_amber'
        if kind == 'diploma':
            if 0.1 < v < 0.2 and 0.15 < u < 0.85: return 'ink_2' if (int(u*40) % 2) else 'paper'
            if abs(math.hypot((u - 0.5)*1.4, v - 0.7)) < 0.1: return 'marker_red'
            if 0.3 < v < 0.5 and int(v*(z1 - z0)*64) % 3 == 0 and 0.2 < u < 0.8: return 'grey'
            return 'paper' if 0.05 < u < 0.95 and 0.05 < v < 0.95 else 'wood_dk'
        if kind == 'space':         # Raj: original planetary art
            d = math.hypot(u - 0.4, v - 0.55)
            if d < 0.22: return '4b_orange' if math.sin(v*40) > -0.3 else 'ccf_amber'
            if abs(math.hypot(u - 0.4, (v - 0.55)*3.2) - 0.32) < 0.025 and not (d < 0.22): return 'lamp_warm'
            if math.hypot(u - 0.8, v - 0.2) < 0.06: return 'screen_glow'
            return 'white_hi' if hsh(int(u*60), int(v*80), 5) < 0.04 else 'shadow_violet'
        return 'paper'
    return t
for _k in ('particles', 'neutrino', 'journal', 'nebula', 'award', 'diploma', 'space'):
    item(f'poster_{_k}', CAMPUS if _k != 'space' else RAJ, (1, 1), 2.0, 'R4', 'P2', blocks=False, mount='wall', sort_bias=-1, shadow=False,
         layer='wall_decal', notes=f'original framed wall art ({_k}); no real logos')(
         (lambda k: lambda state='default': [box(0.18, 0.0, 1.2, 0.82, 0.03, 1.95 if k not in ('award', 'diploma') else 1.68, 'dark',
                                                  poster_tex(k, 0.18, 0.82, 1.2, 1.95 if k not in ('award', 'diploma') else 1.68))])(_k))

@item('ait_crest_banner', CAMPUS, (2, 1), 2.6, 'R4', 'P0', blocks=False, mount='wall', sort_bias=-1, shadow=False, layer='wall_decal',
      notes='Arroyo Institute of Technology banner: original crest (teal shield, rising gold sun + atom orbit, blue arroyo) and wordmark')
def ait_banner(state='default'):
    def t(face, x, y, z, tone, rc):
        if face != 'front': return None
        r = crest_px((x - 0.16)/0.5, (2.48 - z)/0.62)
        if r: return r
        c = int((x - 0.74)*64); rr = int((2.36 - z)*64)
        if px_text('ARROYO', c, rr, 2): return 'white_hi'
        if px_text('INSTITUTE OF', c, rr - 13): return 'comic_yellow'
        if px_text('TECHNOLOGY', c, rr - 20): return 'comic_yellow'
        if abs(z - 1.9) < 1/64 and 0.74 < x < 1.8: return 'ccf_amber'
        return 'cafe_teal' if z > 1.86 else 'tile_green_dk'
    return [box(0.1, 0.0, 2.52, 1.9, 0.05, 2.56, 'brass'), box(0.12, 0.0, 1.78, 1.88, 0.03, 2.52, 'teal', t)]

# ================================================================== AIT PHYSICS: offices + lab
@item('off_whiteboard_wall', CAMPUS, (2, 1), 2.15, 'R4', 'P0', blocks=False, mount='wall', sort_bias=-1, shadow=False, layer='wall_decal',
      states=WB_STATES, notes="Sheldon's wall of whiteboards: equation soup, diagram, or the 'music' staves gag. Hang several side by side",
      hooks=[H('write', 'write', (1.0, 0.6), (0, -1), 'write_whiteboard', approach=(1, 0), tags=['sheldon']),
             H('ponder', 'look', (1.0, 1.3), (0, -1), 'ponder_board', approach=(1, 1))])
def off_wb(state='equations_a'):
    return [box(0.06, 0.0, 0.88, 1.94, 0.04, 2.1, 'white', wb_tex(state, 0.06, 1.94, 0.88, 2.1, seed=1)),
            box(0.1, 0.0, 0.84, 1.9, 0.09, 0.88, 'steel'), box(0.5, 0.02, 0.88, 0.58, 0.07, 0.9, 'blue'), box(0.7, 0.02, 0.88, 0.78, 0.07, 0.9, 'red')]

@item('off_desk', CAMPUS, (2, 1), 1.3, 'R4', 'P0', states=('on', 'off'),
      notes='academic desk: CRT-free monitor, tidy paper stacks, desk lamp, name block; worker sits on the front side facing -Y',
      hooks=[H('work', 'work', (1.0, 1.4), (0, -1), 'type_desk', approach=(1, 1), tags=['computer', 'needs_chair']),
             H('surface', 'place_item', (1.6, 0.5), (0, 1), z=0.75)])
def off_desk(state='on'):
    on = state == 'on'
    P = [box(0.04, 0.1, 0, 0.6, 0.85, 0.72, 'wood_dk', first(panel_tex([(0.1, 0.06, 0.54, 0.3), (0.1, 0.36, 0.54, 0.66)]), knob_tex([(0.32, 0.5), (0.32, 0.2)]))),
         box(1.4, 0.1, 0, 1.96, 0.85, 0.72, 'wood_dk', first(panel_tex([(1.46, 0.06, 1.9, 0.66)]), knob_tex([(1.68, 0.55)]))),
         box(0.6, 0.1, 0.3, 1.4, 0.14, 0.72, 'wood_dk'),
         box(0.0, 0.05, 0.72, 2.0, 0.92, 0.77, 'wood', wood_grain('x', 0.14, 21))]
    P.append(box(0.75, 0.2, 0.77, 0.95, 0.32, 0.79, 'dark')); P.append(box(0.82, 0.24, 0.79, 0.88, 0.28, 0.9, 'dark'))
    P.append(box(0.5, 0.22, 0.9, 1.2, 0.26, 1.3, 'black', screen_tex(on, 0.53, 1.17, 0.93, 1.27, 'code')))
    P.append(box(0.6, 0.5, 0.77, 1.1, 0.64, 0.79, 'metal'))
    for k, (x, n) in enumerate(((0.1, 5), (1.45, 8))):
        for i in range(n): P.append(box(x, 0.2, 0.77 + i*0.012, x + 0.3, 0.6, 0.782 + i*0.012, 'paper' if i % 3 else 'white'))
    P += rod((1.85, 0.25, 0.77), (1.8, 0.35, 1.15), 0.015, 'dark', n=6); P.append(cyl(1.75, 0.45, 0.08, 1.08, 1.18, 'green', n=10))
    P.append(box(1.45, 0.7, 0.77, 1.85, 0.8, 0.84, 'brass', text_tex('front', 1.5, 0.83, 'DR S C', 'ink_2')))
    return P

@item('off_bookshelf', CAMPUS, (2, 1), 2.2, 'R4', 'P1', notes='tall office bookcase: journals, binders, textbooks',
      hooks=[H('browse', 'browse', (1.0, 1.3), (0, -1), 'browse_shelf', approach=(1, 1))])
def off_shelf(state='default'):
    P = [box(0.02, 0.05, 0, 1.98, 0.1, 2.2, 'wood_dk'), box(0.02, 0.05, 0, 0.08, 0.5, 2.2, 'wood_dk'),
         box(1.92, 0.05, 0, 1.98, 0.5, 2.2, 'wood_dk'), box(0.02, 0.05, 2.15, 1.98, 0.5, 2.2, 'wood_dk'), box(0.02, 0.05, 0, 1.98, 0.5, 0.1, 'wood_dk')]
    for i, z in enumerate((0.1, 0.52, 0.94, 1.36, 1.78)):
        if i: P.append(box(0.08, 0.05, z - 0.03, 1.92, 0.5, z, 'wood_dk'))
        P += book_row(0.1, 1.9, 0.12, 0.45, z, 60 + i, 0.34)
    return P

@item('off_filing_cabinet', CAMPUS, (1, 1), 1.32, 'R4', 'P2', hooks=[H('use', 'use', (0.5, 1.3), (0, -1), 'open_drawer', approach=(0, 1))])
def off_filing(state='default'):
    return [box(0.18, 0.15, 0, 0.82, 0.85, 1.32, 'steel', first(panel_tex([(0.22, 0.04 + 0.32*i, 0.78, 0.32*(i+1)) for i in range(4)]),
                                                              knob_tex([(0.5, 0.25 + 0.32*i) for i in range(4)])))]

@item('off_door', CAMPUS, (1, 1), 2.22, 'R4', 'P0', states=DOOR_STATES, blocks=False, mount='wall',
      notes='office door with a brass name plaque on the hallway side (back face) and a small notice card on the inside face',
      hooks=[H('door', 'door', (0.5, 0.55), (0, -1), 'open_door', approach=(0, 0)),
             H('knock_spot_outside', 'knock_spot_outside', (0.5, -0.45), (0, 1), 'knock', approach=(0, -1))])
def off_door(state='closed'):
    return swing_door('wood', 'wood_dk', first(plate_tex(['S COOPER PHD', 'THEORETICAL', 'PHYSICS'], 1.78, 0.14, 0.86, face_name='back'),
                                               plate_tex(['OFFICE', 'HOURS', 'NONE'], 1.75, 0.3, 0.7, bg='paper', face_name='front'),
                                               panel_tex([(0.2, 0.15, 0.8, 1.2)])), swing=1)(state)

def scope_tex(face, x, y, z, tone, rc):
    if face == 'front' and 0.12 < x < 0.88 and 0.95 < z < 1.3:
        if abs(z - (1.12 + 0.1*math.sin(x*40))) < 1.2/64: return 'marker_green'
        return 'grey_dk' if (int(x*64) % 8 == 0 or int(z*64) % 8 == 0) else 'ink_2'
    return None
@item('lab_bench_electronics', CAMPUS, (3, 1), 1.6, 'R4', 'P0', states=('on', 'off'),
      notes="Howard's electronics bench: oscilloscope, bench supply, soldering station, parts-bin riser",
      hooks=[H('work0', 'work', (0.8, 1.4), (0, -1), 'solder', approach=(0, 1), tags=['howard', 'needs_stool']),
             H('work1', 'work', (2.2, 1.4), (0, -1), 'use_scope', approach=(2, 1), tags=['needs_stool'])])
def lab_bench(state='on'):
    P = [box(x, y, 0, x + 0.06, y + 0.06, 0.88, 'steel') for x in (0.06, 2.88) for y in (0.12, 0.82)]
    P.append(box(0.06, 0.15, 0.2, 2.94, 0.85, 0.24, 'steel'))
    P.append(box(0.0, 0.08, 0.88, 3.0, 0.95, 0.93, 'concrete', lambda f, x, y, z, t, rc: 'grey_dk' if f == 'top' and hsh(int(x*32), int(y*32)) < 0.04 else None))
    P.append(box(0.0, 0.05, 0.93, 3.0, 0.3, 1.6, 'steel'))                                   # riser
    def bins(face, x, y, z, tone, rc):
        if face == 'front' and z > 1.3: return ['comic_blue', 'marker_red', 'comic_yellow', 'marker_green'][int(x/0.25) % 4] if (x % 0.25) > 0.03 and (z - 1.3) % 0.15 > 0.03 else 'grey_dk'
        return None
    P.append(box(0.0, 0.3, 1.28, 3.0, 0.36, 1.6, 'steel', bins))
    P.append(box(1.8, 0.35, 0.93, 2.7, 0.75, 1.32, 'metal', scope_tex if state == 'on' else None))
    P.append(box(1.2, 0.35, 0.93, 1.6, 0.7, 1.15, 'mustard', knob_tex([(1.3, 1.05), (1.45, 1.05)])))
    P.append(box(0.3, 0.45, 0.93, 0.7, 0.75, 1.0, 'red')); P += rod((0.6, 0.6, 1.0), (0.9, 0.65, 1.12), 0.012, 'dark', n=4)
    P.append(box(0.2, 0.62, 0.93, 0.95, 0.88, 0.94, 'green'))    # circuit board on the mat
    return P

@item('lab_optical_table', CAMPUS, (2, 1), 1.35, 'R4', 'P0', states=('on', 'off'),
      notes="Leonard's laser experiment: honeycomb optical table, laser head, mirrors on posts, a visible red beam path",
      hooks=[H('align', 'work', (1.0, 1.4), (0, -1), 'align_laser', approach=(1, 1), tags=['leonard']),
             H('observe', 'look', (2.4, 0.5), (-1, 0), 'look_experiment', approach=(2, 0))])
def lab_optical(state='on'):
    P = [box(x, y, 0, x + 0.14, y + 0.14, 0.75, 'dark') for x in (0.08, 1.78) for y in (0.12, 0.74)]
    P.append(box(0.0, 0.05, 0.75, 2.0, 0.95, 0.9, 'metal', lambda f, x, y, z, t, rc: ('grey_dk' if f == 'top' and int(x*64) % 5 == 0 and int(y*64) % 5 == 0 else None)))
    P.append(box(0.15, 0.2, 0.9, 0.65, 0.4, 1.08, 'blue', text_tex('front', 0.22, 1.04, 'LASER', 'white_hi')))
    mir = [(1.0, 0.3), (1.0, 0.75), (1.75, 0.75)]
    for (mx, my) in mir:
        P.append(cyl(mx, my, 0.025, 0.9, 1.05, 'chrome', n=6)); P.append(box(mx - 0.05, my - 0.05, 1.03, mx + 0.05, my + 0.05, 1.12, 'glass'))
    if state == 'on':
        segs = [((0.65, 0.3), (1.0, 0.3)), ((1.0, 0.3), (1.0, 0.75)), ((1.0, 0.75), (1.75, 0.75))]
        for (a, b) in segs:
            P.append(Prism([(min(a[0], b[0]) - 0.008, min(a[1], b[1]) - 0.008), (max(a[0], b[0]) + 0.008, min(a[1], b[1]) - 0.008),
                            (max(a[0], b[0]) + 0.008, max(a[1], b[1]) + 0.008), (min(a[0], b[0]) - 0.008, max(a[1], b[1]) + 0.008)],
                           1.065, 1.08, 'red', outline=False))
    P.append(box(1.6, 0.15, 0.9, 1.9, 0.4, 1.0, 'black'))   # detector
    return P

@item('lab_robot_arm', CAMPUS, (1, 1), 1.55, 'R4', 'P1', notes='small yellow industrial arm on a pedestal (gripper toward the front)',
      hooks=[H('program', 'use', (0.5, 1.35), (0, -1), 'program_robot', approach=(0, 1), tags=['howard'])])
def lab_arm(state='default'):
    P = [box(0.2, 0.2, 0, 0.8, 0.8, 0.6, 'dark'), cyl(0.5, 0.5, 0.18, 0.6, 0.72, 'mustard', n=12)]
    P += rod((0.5, 0.5, 0.72), (0.5, 0.35, 1.3), 0.07, 'mustard', n=10)
    P.append(cyl(0.5, 0.35, 0.08, 1.24, 1.36, 'dark', n=10))
    P += rod((0.5, 0.35, 1.32), (0.5, 0.8, 1.15), 0.055, 'mustard', n=8)
    P.append(box(0.44, 0.8, 1.0, 0.56, 0.86, 1.18, 'dark')); P.append(box(0.43, 0.84, 0.96, 0.46, 0.92, 1.05, 'chrome')); P.append(box(0.54, 0.84, 0.96, 0.57, 0.92, 1.05, 'chrome'))
    return P

@item('lab_rover', CAMPUS, (1, 1), 0.8, 'R4', 'P1', notes='six-wheeled planetary rover prototype (original design) on the lab floor',
      hooks=[H('tinker', 'work', (0.5, 1.35), (0, -1), 'kneel_work', approach=(0, 1), tags=['howard'])])
def lab_rover(state='default'):
    P = []
    for y in (0.18, 0.5, 0.82):
        for x in (0.14, 0.86): P.append(cyl(x, y, 0.09, 0.0, 0.18, 'black', n=10)); P.append(cyl(x, y, 0.04, 0.0, 0.185, 'metal', n=6))
    P.append(box(0.2, 0.15, 0.12, 0.8, 0.85, 0.16, 'metal'))
    P.append(box(0.24, 0.22, 0.16, 0.76, 0.78, 0.36, 'white', panel_tex([(0.3, 0.2, 0.7, 0.32)])))
    P.append(box(0.1, 0.12, 0.36, 0.9, 0.88, 0.38, 'blue', grid_tex(0.1, 0.1, 'ink_2', face_only='top')))
    P.append(cyl(0.5, 0.75, 0.025, 0.38, 0.7, 'metal', n=6)); P.append(box(0.42, 0.72, 0.68, 0.58, 0.82, 0.78, 'white',
              lambda f, x, y, z, t, rc: 'ink' if f == 'front' and abs(z - 0.73) < 0.025 and abs(x - 0.5) < 0.05 else None))
    return P

@item('lab_tool_chest', CAMPUS, (1, 1), 1.25, 'R4', 'P1', notes='red rolling tool chest with drawers',
      hooks=[H('use', 'use', (0.5, 1.3), (0, -1), 'get_tool', approach=(0, 1))])
def lab_chest(state='default'):
    rects = [(0.14, 0.12 + 0.11*i, 0.86, 0.11*(i+1) + 0.1) for i in range(9)]
    P = [cyl(x, y, 0.04, 0, 0.08, 'black', n=6) for x in (0.18, 0.82) for y in (0.25, 0.75)]
    P.append(box(0.1, 0.18, 0.08, 0.9, 0.82, 1.18, 'red', first(panel_tex(rects), lambda f, x, y, z, t, rc: ('grey_lt' if f == 'front' and abs(x - 0.5) < 0.2 and ((z - 0.08) % 0.11) < 1.5/64 + 0.02 and ((z - 0.08) % 0.11) > 0.02 else None))))
    P.append(box(0.08, 0.16, 1.18, 0.92, 0.84, 1.24, 'dark'))
    P.append(box(0.3, 0.4, 1.24, 0.75, 0.5, 1.28, 'chrome'))
    return P

@item('lab_3d_printer', CAMPUS, (1, 1), 1.55, 'R4', 'P2', states=('printing', 'idle'), notes='open-frame 3D printer on a cart',
      hooks=[H('use', 'use', (0.5, 1.3), (0, -1), 'use_printer', approach=(0, 1))])
def lab_printer(state='printing'):
    P = [box(0.15, 0.2, 0, 0.85, 0.8, 0.8, 'dark', panel_tex([(0.2, 0.1, 0.8, 0.7)]))]
    for x in (0.2, 0.76):
        for y in (0.25, 0.71): P.append(box(x, y, 0.8, x + 0.04, y + 0.04, 1.5, 'black'))
    P.append(box(0.2, 0.25, 1.48, 0.8, 0.75, 1.52, 'black'))
    P.append(box(0.26, 0.3, 0.84, 0.74, 0.7, 0.87, 'chrome'))
    if state == 'printing': P.append(cyl(0.5, 0.5, 0.09, 0.87, 1.0, 'orange', n=10)); P.append(box(0.44, 0.44, 1.12, 0.56, 0.56, 1.2, 'red'))
    P.append(box(0.2, 0.48, 1.16, 0.8, 0.52, 1.18, 'chrome'))
    return P

@item('lab_stool', CAMPUS, (1, 1), 0.7, 'R1', 'P2', hooks=[H('seat0', 'sit', (0.5, 0.5), (0, 1), 'sit_stool', approach=(0, 1))])
def lab_stool(state='default'):
    return [cyl(0.5, 0.5, 0.2, 0, 0.03, 'dark', n=10), cyl(0.5, 0.5, 0.03, 0.03, 0.64, 'chrome', n=6), cyl(0.5, 0.5, 0.17, 0.64, 0.7, 'black', n=12)]

@item('lab_pegboard', CAMPUS, (2, 1), 2.0, 'R4', 'P2', blocks=False, mount='wall', sort_bias=-1, shadow=False, layer='wall_decal',
      notes='tool pegboard with silhouettes (wrench, pliers, screwdrivers, hammer)')
def lab_peg(state='default'):
    def t(face, x, y, z, tone, rc):
        if face != 'front': return None
        if x < 0.14 or x > 1.86 or z < 1.1 or z > 1.95: return 'wood_dk'
        tools = [('w', 0.3), ('p', 0.6), ('s', 0.85), ('s', 1.0), ('s', 1.15), ('h', 1.45), ('w', 1.7)]
        for k, (kind, tx) in enumerate(tools):
            u = x - tx
            if kind == 's' and abs(u) < 0.015 and 1.35 < z < 1.75: return 'grey_lt' if z < 1.6 else ['marker_red', 'comic_yellow', 'comic_blue'][k % 3]
            if kind == 'w' and abs(u) < 0.02 + (0.02 if z > 1.7 else 0) and 1.3 < z < 1.82: return 'grey_lt'
            if kind == 'p' and abs(abs(u) - 0.02 - (z - 1.3)*0.1) < 0.015 and 1.3 < z < 1.75: return 'marker_red' if z < 1.5 else 'grey_lt'
            if kind == 'h' and ((abs(u) < 0.02 and 1.3 < z < 1.7) or (abs(u) < 0.08 and 1.68 < z < 1.76)): return 'wood' if z < 1.68 else 'grey'
        if int((x - 0.14)*64) % 6 == 3 and int((z - 1.1)*64) % 6 == 3: return 'wood_xdk'
        return 'cork' if False else ('wood_hi' if hsh(int(x*64)//4, int(z*64)//4) < 0.2 else 'wood')
    return [box(0.12, 0.0, 1.08, 1.88, 0.03, 1.97, 'wood', t)]

@item('lab_laser_sign', CAMPUS, (1, 1), 2.1, 'R4', 'P2', blocks=False, mount='wall', sort_bias=-1, shadow=False, layer='wall_decal',
      notes='generic laser-hazard warning sign (no regulatory logos)')
def lab_sign(state='default'):
    def t(face, x, y, z, tone, rc):
        if face != 'front': return None
        if 1.72 < z < 2.02 and 0.28 < x < 0.72:
            u = x - 0.5; v = 2.0 - z
            if v > 0.02 and abs(u) < v*0.62:
                if abs(u) > v*0.62 - 0.03 or v > 0.19: return 'ink'
                if abs(u) < 0.012 or (abs(abs(u) - (v - 0.06)*0.4) < 0.012 and v > 0.06): return 'ink'
                return 'comic_yellow'
            if z < 1.79 and px_text('LASER', int((x - 0.41)*64), int((1.775 - z)*64)): return 'ink'
            return 'comic_yellow'
        return 'comic_yellow'
    return [box(0.26, 0.0, 1.66, 0.74, 0.03, 2.04, 'yellow', t)]

# ================================================================== THE AMBER SLICE (Penny's restaurant; original name)
def tuft(face, x, y, z, tone, rc):
    if face in ('front', 'back') and z > 0.5:
        if (x % 0.25) < 1/64: return 3
        if abs(((x % 0.25) - 0.125)) < 1.5/64 and abs((z % 0.22) - 0.11) < 1.5/64: return 3
    return None
@item('rest_booth', REST, (2, 2), 1.2, 'R4', 'P0', notes='red tufted 4-seat booth with dark wood caps and a table; open at both x-ends',
      hooks=[H('seat0', 'sit', (0.6, 0.38), (0, 1), 'sit_booth', approach=(0, 0)), H('seat1', 'sit', (1.4, 0.38), (0, 1), 'sit_booth', approach=(1, 0)),
             H('seat2', 'sit', (0.6, 1.62), (0, -1), 'sit_booth', approach=(0, 1)), H('seat3', 'sit', (1.4, 1.62), (0, -1), 'sit_booth', approach=(1, 1)),
             H('take_order', 'work', (2.35, 1.0), (-1, 0), 'take_order', approach=(2, 1), tags=['waitress', 'penny']),
             H('table', 'place_item', (1.0, 1.0), (0, 1), tags=['plates', 'drinks'], z=0.76)])
def rest_booth(state='default'):
    P = []
    for (y0, y1, by0, by1) in ((0.05, 0.62, 0.0, 0.2), (1.38, 1.95, 1.8, 2.0)):
        P.append(box(0.06, y0, 0, 1.94, y1, 0.12, 'wood_dk'))
        P.append(box(0.06, y0, 0.12, 1.94, y1, 0.46, 'booth', lambda f, x, y, z, t, rc: (3 if f == 'top' and (x % 0.5) < 1/64 else None)))
        P.append(box(0.06, by0, 0.46, 1.94, by1, 1.14, 'booth', tuft))
        P.append(box(0.04, by0 - 0.02 if by0 > 0 else by0, 1.14, 1.96, by1 + (0.0 if by1 < 2 else 0.0), 1.2, 'wood_dk'))
    P.append(cyl(1.0, 1.0, 0.06, 0, 0.72, 'dark', n=8)); P.append(box(0.75, 0.85, 0, 1.25, 1.15, 0.03, 'dark'))
    P.append(box(0.18, 0.72, 0.72, 1.82, 1.28, 0.77, 'wood_dk', wood_grain('x', 0.12, 31)))
    P.append(cyl(0.55, 0.88, 0.1, 0.77, 0.79, 'white', n=10)); P.append(cyl(1.45, 1.12, 0.1, 0.77, 0.79, 'white', n=10))
    P.append(box(0.5, 0.84, 0.79, 0.62, 0.93, 0.83, 'cream')); P.append(box(1.38, 1.07, 0.79, 1.52, 1.16, 0.83, 'wood_dk'))     # cake slices
    P.append(cyl(0.95, 1.18, 0.035, 0.77, 0.92, 'glass', n=8)); P.append(cyl(1.1, 0.82, 0.035, 0.77, 0.92, 'glass', n=8))
    P.append(box(0.9, 0.95, 0.77, 1.04, 1.02, 0.86, 'chrome'))     # napkin dispenser
    return P

@item('rest_bar_counter', REST, (4, 1), 1.3, 'R4', 'P0',
      notes='dark-wood paneled bar with amber top trim, brass foot rail and taps. Guests on stools on the +Y side; bartender works the -Y side',
      hooks=[H(f'stool{i}', 'sit', (0.5 + i, 1.45), (0, -1), 'sit_stool_bar', approach=(i, 1), tags=['needs_stool']) for i in range(4)] +
            [H('bartend', 'work', (2.0, -0.45), (0, 1), 'bartend', approach=(2, -1), tags=['penny', 'staff']),
             H('pour', 'use', (0.8, -0.45), (0, 1), 'pour_drink', approach=(0, -1), tags=['staff'])])
def rest_bar(state='default'):
    P = [box(0.02, 0.3, 0, 3.98, 0.86, 1.02, 'wood_dk', first(panel_tex([(0.1 + i, 0.15, 0.9 + i, 0.9) for i in range(4)]), wood_grain('x', 0.18, 41)))]
    P.append(box(0.0, 0.22, 1.02, 4.0, 0.97, 1.08, 'wood', lambda f, x, y, z, t, rc: ('ccf_amber' if f == 'front' else ('lamp_warm' if f == 'top' and y > 0.93 else None))))
    for x in (0.4, 1.4, 2.4, 3.4): P.append(box(x, 0.86, 0.12, x + 0.04, 0.95, 0.2, 'brass'))
    P.append(box(0.05, 0.9, 0.16, 3.95, 0.95, 0.2, 'brass'))
    P.append(box(1.6, 0.25, 1.08, 2.4, 0.33, 1.14, 'brass'))
    for i in range(4): P.append(box(1.67 + i*0.2, 0.3, 1.14, 1.73 + i*0.2, 0.36, 1.3, ['wood_dk', 'red', 'black', 'wood_dk'][i]))
    for x, m in ((0.5, 'glass'), (0.8, 'wine'), (3.1, 'glass'), (3.4, 'orange')):
        P.append(cyl(x, 0.65, 0.04, 1.08, 1.2, m, n=8))
    P.append(box(2.8, 0.5, 1.08, 3.0, 0.8, 1.1, 'white'))
    return P

@item('rest_bar_stool', REST, (1, 1), 0.82, 'R1', 'P1', hooks=[H('seat0', 'sit', (0.5, 0.5), (0, -1), 'sit_stool_bar', approach=(0, 1))])
def rest_stool(state='default'):
    return [cyl(0.5, 0.5, 0.18, 0, 0.03, 'brass', n=10), cyl(0.5, 0.5, 0.03, 0.03, 0.74, 'brass', n=6),
            cyl(0.5, 0.5, 0.14, 0.32, 0.34, 'brass', n=10), cyl(0.5, 0.5, 0.2, 0.74, 0.82, 'booth', n=14)]

@item('rest_back_bar', REST, (3, 1), 2.3, 'R4', 'P0', notes='back bar: lower cabinets, mirror, lit bottle shelves, amber under-shelf strip',
      hooks=[H('get_bottle', 'use', (1.5, 1.25), (0, -1), 'reach_shelf', approach=(1, 1), tags=['staff'])])
def rest_back_bar(state='default'):
    P = [box(0.02, 0.1, 0, 2.98, 0.6, 0.9, 'wood_dk', panel_tex([(0.1 + i*0.72, 0.1, 0.76 + i*0.72, 0.8) for i in range(4)])),
         box(0.0, 0.08, 0.9, 3.0, 0.62, 0.95, 'wood')]
    def mirror(face, x, y, z, tone, rc):
        if face != 'front': return None
        if (x - z*0.5) % 0.9 < 0.05: return 'white_hi'
        return 'grey_lt' if (x + z) % 0.3 < 0.15 else 'screen_glow'
    P.append(box(0.05, 0.0, 0.95, 2.95, 0.05, 2.25, 'glass', mirror))
    for z in (1.35, 1.8):
        P.append(box(0.1, 0.05, z - 0.03, 2.9, 0.32, z, 'wood_dk', lambda f, x, y, zz, t, rc: ('lamp_warm' if f == 'front' else None)))
        for k in range(13):
            x = 0.22 + k*0.205; m = ['bottle', 'wine', 'brass', 'glass', 'bottle', 'orange'][int(hsh(k, int(z*10))*6)]
            h = 0.22 + 0.1*hsh(k, int(z*10), 1)
            P.append(cyl(x, 0.18, 0.045, z, z + h, m, n=8)); P.append(cyl(x, 0.18, 0.018, z + h, z + h + 0.07, m, n=6))
    P.append(box(0.0, 0.05, 2.25, 3.0, 0.4, 2.3, 'wood_dk'))
    return P

@item('rest_table_2top', REST, (1, 1), 0.78, 'R2', 'P0', notes='square two-top; chairs (rest_chair) on the -Y/+Y sides',
      hooks=[H('seat0', 'sit', (0.5, -0.45), (0, 1), 'sit_chair_eat', approach=(0, -1), tags=['needs_chair']),
             H('seat1', 'sit', (0.5, 1.45), (0, -1), 'sit_chair_eat', approach=(0, 1), tags=['needs_chair']),
             H('serve', 'work', (1.4, 0.5), (-1, 0), 'serve_plate', approach=(1, 0), tags=['waitress'])])
def rest_table(state='default'):
    return [box(0.4, 0.4, 0, 0.6, 0.6, 0.03, 'dark'), cyl(0.5, 0.5, 0.04, 0.03, 0.72, 'dark', n=8),
            box(0.1, 0.1, 0.72, 0.9, 0.9, 0.77, 'wood_dk', wood_grain('x', 0.12, 51)),
            box(0.3, 0.15, 0.77, 0.7, 0.3, 0.775, 'white'), box(0.3, 0.7, 0.77, 0.7, 0.85, 0.775, 'white'),
            box(0.45, 0.45, 0.77, 0.55, 0.55, 0.9, 'brass', lambda f, x, y, z, t, rc: 'lamp_warm' if z > 0.85 else None)]

@item('rest_chair', REST, (1, 1), 0.95, 'R4', 'P1', hooks=[H('seat0', 'sit', (0.5, 0.55), (0, 1), 'sit_chair', approach=(0, 1))])
def rest_chair(state='default'):
    P = [box(x, y, 0, x + 0.05, y + 0.05, 0.45, 'wood_dk') for x in (0.25, 0.7) for y in (0.25, 0.72)]
    P.append(box(0.22, 0.22, 0.42, 0.78, 0.8, 0.48, 'booth'))
    P.append(box(0.24, 0.2, 0.45, 0.3, 0.26, 0.95, 'wood_dk')); P.append(box(0.7, 0.2, 0.45, 0.76, 0.26, 0.95, 'wood_dk'))
    P.append(box(0.24, 0.2, 0.62, 0.76, 0.26, 0.9, 'booth', lambda f, x, y, z, t, rc: 3 if abs(z - 0.76) < 1/64 else None))
    return P

@item('rest_host_stand', REST, (1, 1), 1.35, 'R4', 'P0', notes='host podium with a little amber lamp and a stack of menus; host stands on the -Y side',
      hooks=[H('host', 'work', (0.5, -0.4), (0, 1), 'host_greet', approach=(0, -1), tags=['penny', 'staff']),
             H('wait_to_be_seated', 'queue', (0.5, 1.45), (0, -1), 'stand_wait', approach=(0, 1), cap=4)])
def rest_host(state='default'):
    def front(face, x, y, z, tone, rc):
        if face == 'front' and math.hypot(x - 0.5, z - 0.75) < 0.1: return 'lamp_warm' if math.hypot(x - 0.47, z - 0.78) < 0.05 else 'ccf_amber'
        return None
    P = [Prism([(0.22, 0.25), (0.78, 0.25), (0.82, 0.75), (0.18, 0.75)], 0, 1.05, 'wood_dk', first(front, wood_grain('z', 0.2, 61)))]
    P.append(box(0.14, 0.2, 1.05, 0.86, 0.8, 1.1, 'wood'))
    P.append(box(0.3, 0.4, 1.1, 0.62, 0.7, 1.16, 'booth'))
    P.append(cyl(0.75, 0.3, 0.02, 1.1, 1.28, 'brass', n=6)); P.append(cyl(0.75, 0.3, 0.07, 1.25, 1.35, 'lamp', n=10))
    return P

@item('rest_kitchen_door', REST, (1, 1), 2.22, 'R4', 'P0', states=DOOR_STATES, blocks=False, mount='wall',
      notes='stainless swing door with a porthole window and kick plate; staff only',
      hooks=[H('door', 'door', (0.5, 0.55), (0, -1), 'push_door', approach=(0, 0), tags=['staff']),
             H('pickup', 'use', (0.5, 0.9), (0, -1), 'pickup_order', approach=(0, 0), tags=['waitress'])])
def rest_kdoor(state='closed'):
    return swing_door('steel', 'dark', first(porthole_tex, text_tex('front', 0.27, 2.0, 'KITCHEN', 'ink_2')), swing=1)(state)

@item('rest_column', REST, (1, 1), 3.0, 'R1', 'P1', notes='faux-stone column with a flared amber capital (signature dining-room piece)', shadow=True)
def rest_column(state='default'):
    P = [box(0.18, 0.18, 0, 0.82, 0.82, 0.12, 'stone'), box(0.22, 0.22, 0.12, 0.78, 0.78, 0.3, 'stone')]
    P.append(cyl(0.5, 0.5, 0.2, 0.3, 2.45, 'stone', n=12, tex=lambda f, x, y, z, t, rc: (t + 1 if hsh(int(z*16), int((x + y)*20)) < 0.08 else None)))
    for k, (z0, z1, r) in enumerate(((2.45, 2.55, 0.22), (2.55, 2.68, 0.27), (2.68, 2.8, 0.32), (2.8, 2.9, 0.36))):
        P.append(cyl(0.5, 0.5, r, z0, z1, 'brass' if k % 2 == 0 else 'stone', n=12))
    P.append(box(0.08, 0.08, 2.9, 0.92, 0.92, 3.0, 'stone'))
    return P

@item('rest_pendant_lamp', REST, (1, 1), 2.95, 'R1', 'P1', blocks=False, mount='ceiling', shadow=False, states=('on', 'off'),
      notes='hanging amber glass pendant over a booth/table (casts a warm floor pool when on)')
def rest_pendant(state='on'):
    on = state == 'on'
    return [cyl(0.5, 0.5, 0.012, 2.4, 2.95, 'dark', n=4),
            cyl(0.5, 0.5, 0.05, 2.36, 2.42, 'brass', n=8),
            cyl(0.5, 0.5, 0.18, 2.16, 2.36, 'brass' if on else 'wood', n=12, tex=lambda f, x, y, z, t, rc: ('lamp_warm' if on and z < 2.19 else None)),
            cyl(0.5, 0.5, 0.12, 2.12, 2.16, 'lamp' if on else 'dark', n=10)]

@item('rest_cake_display', REST, (1, 1), 1.5, 'R4', 'P0', notes='signature cake case: open-sided glass display on a wood base, two tiers of cakes and pies',
      hooks=[H('browse', 'look', (0.5, 1.35), (0, -1), 'look_cakes', approach=(0, 1)),
             H('serve_slice', 'work', (0.5, -0.4), (0, 1), 'serve_slice', approach=(0, -1), tags=['staff'])])
def rest_cake(state='default'):
    P = [box(0.06, 0.1, 0, 0.94, 0.9, 0.85, 'wood_dk', panel_tex([(0.12, 0.1, 0.88, 0.75)])), box(0.04, 0.08, 0.85, 0.96, 0.92, 0.9, 'brass')]
    for x in (0.06, 0.9):
        for y in (0.1, 0.86): P.append(box(x, y, 0.9, x + 0.04, y + 0.04, 1.48, 'brass'))
    P.append(box(0.04, 0.08, 1.46, 0.96, 0.92, 1.5, 'glass', lambda f, x, y, z, t, rc: 'white_hi' if f == 'top' and (x - y) % 0.5 < 0.05 else ('screen_glow' if f == 'top' else None)))
    P.append(box(0.1, 0.12, 1.16, 0.9, 0.88, 1.18, 'glass'))
    cakes = [((0.3, 0.5, 0.9), 'cream', 'red'), ((0.7, 0.5, 0.9), 'wood_dk', 'wood'), ((0.3, 0.5, 1.18), 'yellow', 'cream'), ((0.7, 0.5, 1.18), 'cream', 'wood_dk')]
    for (cx, cy, z), m1, m2 in cakes:
        P.append(cyl(cx, cy, 0.15, z, z + 0.02, 'white', n=12))
        P.append(Prism([(cx + 0.14*math.cos(a), cy + 0.14*math.sin(a)) for a in [math.radians(d) for d in range(-150, 151, 30)]] + [(cx, cy)], z + 0.02, z + 0.14, m1))
        P.append(Prism([(cx + 0.14*math.cos(a), cy + 0.14*math.sin(a)) for a in [math.radians(d) for d in range(-150, 151, 30)]] + [(cx, cy)], z + 0.14, z + 0.17, m2))
    for x in (0.06, 0.9): P.append(box(x, 0.88, 0.9, x + 0.04, 0.9, 1.46, 'chrome'))
    return P

@item('rest_stage', REST, (3, 2), 1.6, 'R4', 'P1', notes='small performance stage: keyboard on an X-stand, mic stand, practice amp',
      hooks=[H('perform', 'stand', (1.2, 1.0), (0, 1), 'sing', approach=(1, 1), z=0.3, tags=['open_mic']),
             H('play_keys', 'work', (2.2, 0.35), (0, 1), 'play_keyboard', approach=(2, 0), z=0.3)])
def rest_stage(state='default'):
    P = [box(0.0, 0.0, 0, 3.0, 2.0, 0.3, 'wood_dk', lambda f, x, y, z, t, rc: (3 if f in ('front', 'right') and abs(z - 0.15) < 1/64 else ('wood' if f == 'top' and (x % 0.33) > 1/64 else (2 if f == 'top' else None))))]
    P += rod((1.85, 0.5, 0.3), (2.55, 0.7, 0.85), 0.02, 'dark', n=6); P += rod((2.55, 0.5, 0.3), (1.85, 0.7, 0.85), 0.02, 'dark', n=6)
    def keys(face, x, y, z, tone, rc):
        if face == 'top' and 0.65 < y < 0.8: return 'ink' if (int(x*64) % 3 == 0) or (int(x*64) % 7 < 2 and y < 0.72) else 'white_hi'
        return None
    P.append(box(1.6, 0.5, 0.85, 2.8, 0.82, 0.92, 'black', keys))
    P.append(cyl(1.2, 1.3, 0.14, 0.3, 0.33, 'dark', n=10)); P.append(cyl(1.2, 1.3, 0.015, 0.33, 1.5, 'chrome', n=6))
    P.append(cyl(1.2, 1.3, 0.035, 1.48, 1.6, 'dark', n=8))
    P.append(box(0.2, 0.3, 0.3, 0.7, 0.6, 0.8, 'black', lambda f, x, y, z, t, rc: ('grey_dk' if f == 'front' and z < 0.68 and (int(x*64) + int(z*64)) % 2 else None)))
    return P

@item('rest_wall_sign', REST, (2, 1), 2.4, 'R4', 'P0', blocks=False, mount='wall', sort_bias=-1, shadow=False, layer='wall_decal',
      notes="original restaurant sign 'THE AMBER SLICE' with a cake-slice mark (stand-in for the show's restaurant)")
def rest_sign(state='default'):
    def t(face, x, y, z, tone, rc):
        if face != 'front': return None
        if x < 0.12 or x > 1.88 or z < 1.6 or z > 2.36: return None
        if x < 0.15 or x > 1.85 or z < 1.63 or z > 2.33: return 'ccf_amber'
        c = int((x - 0.15)*64); r = int((2.33 - z)*64)
        if px_text('THE AMBER', c - 20, r - 5, 2): return 'lamp_warm'
        if px_text('SLICE', c - 50, r - 22, 2): return 'lamp_warm'
        u, v = c - 22, r - 21               # cake-slice wedge icon
        if 0 <= v <= 12 and 0 <= u <= 22 and u >= (12 - v)*1.4 - 6 and u <= 22:
            if v < 3: return 'marker_red'
            return 'cafe_cream' if v % 4 else 'wood'
        return 'wood_xdk'
    return [box(0.12, 0.0, 1.6, 1.88, 0.05, 2.36, 'wood_dk', t)]

@item('rest_server_station', REST, (1, 1), 1.45, 'R4', 'P1', notes='server station: order screen, tray stack, water pitcher, check folders',
      hooks=[H('enter_order', 'work', (0.5, 1.35), (0, -1), 'enter_order', approach=(0, 1), tags=['waitress', 'penny'])])
def rest_station(state='default'):
    return [box(0.06, 0.15, 0, 0.94, 0.85, 0.95, 'wood_dk', panel_tex([(0.12, 0.1, 0.88, 0.8)])), box(0.04, 0.12, 0.95, 0.96, 0.88, 1.0, 'wood'),
            box(0.15, 0.3, 1.0, 0.45, 0.4, 1.05, 'dark'), box(0.2, 0.32, 1.05, 0.42, 0.36, 1.32, 'black', screen_tex(True, 0.22, 0.4, 1.08, 1.3, 'code')),
            cyl(0.75, 0.6, 0.18, 1.0, 1.08, 'chrome', n=12), cyl(0.68, 0.32, 0.06, 1.0, 1.22, 'glass', n=8), box(0.25, 0.6, 1.0, 0.5, 0.8, 1.03, 'black')]

def palm_fronds(cx, cy, z, n, L, mat='leaf', droop=0.5, seed=1, r=0.035):
    P = []
    for k in range(n):
        a = 2*math.pi*k/n + hsh(seed, k)*0.4; Lk = L*(0.8 + 0.3*hsh(seed, k, 1))
        pts = []
        for s in range(6):
            t = s/5; pts.append((cx + math.cos(a)*Lk*t, cy + math.sin(a)*Lk*t, z + 0.35*Lk*t - droop*Lk*t*t*1.6))
        for i in range(5): P += rod(pts[i], pts[i+1], r*(1.6 - i*0.25), mat, n=2)
    return P
@item('gen_potted_palm', 'shared', (1, 1), 1.8, 'R1', 'P2', notes='indoor potted palm (restaurant, lobby, Raj)')
def potted_palm(state='default'):
    P = [cyl(0.5, 0.5, 0.22, 0, 0.42, 'brass', n=12), cyl(0.5, 0.5, 0.2, 0.42, 0.44, 'bark', n=12)]
    P += rod((0.5, 0.5, 0.44), (0.52, 0.48, 1.25), 0.03, 'bark', n=4)
    P += palm_fronds(0.5, 0.5, 1.25, 9, 0.45, droop=0.7, seed=3, r=0.03)
    return P

# ================================================================== STREET EXTERIOR (2311 N. Los Robles-style; fictional)
def wheel(cx, cy, r, x0, x1, mat='black'):
    """wheel with a horizontal axle (along x) approximated by z-slices"""
    P = []; n = 6
    for k in range(n):
        za, zb = 2*r*k/n, 2*r*(k+1)/n; zm = (za + zb)/2
        hw = math.sqrt(max(r*r - (zm - r)**2, 0.0004))
        def hub(face, x, y, z, tone, rc, cy=cy, r=r):
            if face in ('left', 'right') and math.hypot(y - cy, z - r) < r*0.5: return 'grey_lt' if math.hypot(y - cy, z - r) > r*0.2 else 'grey'
            return None
        P.append(box(x0, cy - hw, za, x1, cy + hw, zb, mat, hub))
    return P
def car_body_tex(face, x, y, z, tone, rc):
    if face == 'front':
        if z < 0.42: return 'grey_dk' if z > 0.36 else 'ink_2'
        if 0.55 < z < 0.7 and (0.22 < x < 0.5 or 1.5 < x < 1.78): return 'white_hi' if z > 0.6 else 'lamp_warm'
        if 0.45 < z < 0.6 and 0.7 < x < 1.3: return 'ink_2' if int(z*64) % 2 else 'grey_dk'
    if face == 'back':
        if z < 0.42: return 'grey_dk' if z > 0.36 else 'ink_2'
        if 0.6 < z < 0.75 and (0.2 < x < 0.42 or 1.58 < x < 1.8): return 'marker_red'
        if 0.45 < z < 0.58 and 0.75 < x < 1.25:
            return 'ink_2' if px_text('4ZX 217', int((x - 0.77)*64), int((0.56 - z)*64)) else 'white_hi'
    if face in ('left', 'right'):
        if z < 0.4: return 'ink_2' if z < 0.34 else 'grey_dk'
        if abs(y - 1.7) < 0.8/64 or abs(y - 2.75) < 0.8/64: return 3
        if abs(z - 0.66) < 0.8/64: return 0
        if abs(y - 2.55) < 0.06 and abs(z - 0.7) < 0.012: return 'grey_lt'
    return None
def cabin_tex(face, x, y, z, tone, rc):
    if face == 'top': return None
    if z > 1.32: return None
    if face in ('left', 'right'):
        if abs(y - 1.75) < 0.05 or abs(y - 2.7) < 0.04 or y < 0.7: return None
    return 'grey_lt' if (y + z*1.5) % 0.9 < 0.08 else ('screen_glow' if z > 1.12 else 'grey')
@item('ext_car_hatchback', STREET, (2, 4), 1.45, 'R4', 'P0', notes='generic parked hatchback, no badges; canonical nose at +Y. Place SE/NW to park along a street that runs along x',
      hooks=[H('driver_door', 'use', (-0.35, 2.3), (1, 0), 'enter_car', approach=(-1, 2), tags=['drive']),
             H('passenger_door', 'use', (2.35, 2.3), (-1, 0), 'enter_car', approach=(2, 2), tags=['ride']),
             H('lean', 'stand', (2.4, 1.2), (1, 0), 'lean_on_car', approach=(2, 1))])
def car(state='default'):
    P = []
    for cy in (0.8, 3.15):
        P += wheel(cy and 0, cy, 0.31, 0.12, 0.34); P += wheel(0, cy, 0.31, 1.66, 1.88)
    P.append(box(0.14, 0.12, 0.3, 1.86, 3.9, 0.86, 'car', car_body_tex))
    P.append(box(0.12, 3.8, 0.32, 1.88, 3.95, 0.45, 'dark')); P.append(box(0.12, 0.06, 0.32, 1.88, 0.2, 0.45, 'dark'))
    for k in range(5):
        za, zb = 0.86 + k*0.11, 0.86 + (k+1)*0.11
        yb = 0.32 + k*0.04; yf = 2.95 - k*0.17; xi = 0.2 + k*0.03
        P.append(box(xi, yb, za, 2 - xi, yf, zb, 'car', cabin_tex))
    P.append(box(0.0, 2.6, 0.86, 0.14, 2.72, 0.98, 'car')); P.append(box(1.86, 2.6, 0.86, 2.0, 2.72, 0.98, 'car'))
    return P

def mailbox_tex(face, x, y, z, tone, rc):
    if face == 'front':
        if 0.82 < z < 0.88 and 0.3 < x < 0.7: return 'ink'
        if 0.55 < z < 0.75 and 0.3 < x < 0.7: return 'white_hi' if px_text('MAIL', int((x - 0.36)*64), int((0.72 - z)*64)) else ('paper' if abs(x - 0.5) < 0.19 and abs(z - 0.65) < 0.09 else None)
    return None
@item('ext_mailbox', STREET, (1, 1), 1.25, 'R4', 'P1', notes='blue curbside collection box with a rounded top, unbranded',
      hooks=[H('post', 'use', (0.5, 1.3), (0, -1), 'post_letter', approach=(0, 1))])
def mailbox(state='default'):
    P = [box(x, y, 0, x + 0.05, y + 0.05, 0.3, 'iron') for x in (0.25, 0.7) for y in (0.28, 0.67)]
    P.append(box(0.22, 0.25, 0.3, 0.78, 0.75, 1.0, 'car', mailbox_tex))
    for k in range(4):
        hw = 0.25*math.sqrt(1 - ((k + 0.5)/4)**2)
        P.append(box(0.22, 0.5 - hw, 1.0 + k*0.06, 0.78, 0.5 + hw, 1.06 + k*0.06, 'car'))
    return P

@item('ext_hydrant', STREET, (1, 1), 0.8, 'R1', 'P2', notes='yellow fire hydrant')
def hydrant(state='default'):
    return [cyl(0.5, 0.5, 0.16, 0, 0.08, 'mustard', n=10), cyl(0.5, 0.5, 0.11, 0.08, 0.62, 'mustard', n=10),
            box(0.3, 0.45, 0.4, 0.7, 0.55, 0.5, 'mustard'), cyl(0.5, 0.5, 0.13, 0.62, 0.68, 'mustard', n=10),
            cyl(0.5, 0.5, 0.08, 0.68, 0.76, 'mustard', n=8), cyl(0.5, 0.5, 0.03, 0.76, 0.8, 'mustard', n=6)]

@item('ext_street_lamp', STREET, (1, 1), 4.3, 'R1', 'P1', states=('off', 'on'), notes='black cast-iron post lantern (day = off)')
def street_lamp(state='off'):
    on = state == 'on'
    return [cyl(0.5, 0.5, 0.14, 0, 0.35, 'iron', n=8), cyl(0.5, 0.5, 0.05, 0.35, 3.6, 'iron', n=8),
            cyl(0.5, 0.5, 0.1, 3.6, 3.68, 'iron', n=8),
            Prism([(0.36, 0.36), (0.64, 0.36), (0.64, 0.64), (0.36, 0.64)], 3.68, 4.08, 'lamp' if on else 'glass'),
            Prism([(0.32, 0.32), (0.68, 0.32), (0.68, 0.68), (0.32, 0.68)], 4.08, 4.16, 'iron'), cyl(0.5, 0.5, 0.1, 4.16, 4.3, 'iron', n=8)]

@item('ext_bench', STREET, (2, 1), 0.85, 'R4', 'P1', notes='wood-slat bench on cast-iron legs',
      hooks=[H('seat0', 'sit', (0.6, 0.6), (0, 1), 'sit_bench', approach=(0, 1)), H('seat1', 'sit', (1.4, 0.6), (0, 1), 'sit_bench', approach=(1, 1))])
def bench(state='default'):
    P = []
    for x in (0.15, 1.8):
        P.append(box(x, 0.25, 0, x + 0.05, 0.85, 0.45, 'iron')); P.append(box(x, 0.2, 0.45, x + 0.05, 0.3, 0.85, 'iron'))
    for k in range(4): P.append(box(0.1, 0.35 + k*0.13, 0.42, 1.9, 0.45 + k*0.13, 0.46, 'wood'))
    for k in range(2): P.append(box(0.1, 0.22, 0.58 + k*0.14, 1.9, 0.27, 0.68 + k*0.14, 'wood'))
    return P

@item('ext_palm', STREET, (1, 1), 6.2, 'R1', 'P0', notes='tall Mexican fan palm (Pasadena street palm)', shadow=True)
def palm(state='default'):
    P = []
    for k in range(20):
        z0, z1 = k*0.28, (k+1)*0.28; ox = 0.06*math.sin(k*0.18)
        P.append(cyl(0.5 + ox, 0.5, 0.11 - k*0.002, z0, z1, 'bark', n=8, tex=lambda f, x, y, z, t, rc: (3 if (z % 0.14) < 1/64 else None)))
    P.append(cyl(0.56, 0.5, 0.16, 5.5, 5.75, 'bark', n=8))
    P += palm_fronds(0.56, 0.5, 5.75, 13, 1.05, droop=0.55, seed=11, r=0.05)
    return P

@item('ext_jacaranda', STREET, (1, 1), 4.6, 'R1', 'P0', notes='street tree in purple bloom (jacaranda), canopy overhangs neighbouring tiles')
def jacaranda(state='default'):
    P = [cyl(0.5, 0.5, 0.1, 0, 2.2, 'bark', n=8)]
    P += rod((0.5, 0.5, 1.8), (0.15, 0.4, 2.8), 0.05, 'bark', n=5); P += rod((0.5, 0.5, 1.9), (0.85, 0.6, 2.9), 0.05, 'bark', n=5)
    bl = lambda f, x, y, z, t, rc: ('paper' if hsh(int(x*24), int(y*24), int(z*24)) < 0.07 else ('4b_purple' if hsh(int(x*20), int(y*20), int(z*20), 2) < 0.55 else ('shadow_violet' if t >= 2 else None)))
    for (cx, cy, cz, r) in ((0.5, 0.5, 3.3, 0.85), (0.1, 0.35, 3.1, 0.55), (0.9, 0.7, 3.2, 0.55), (0.45, 0.45, 3.9, 0.6), (0.75, 0.15, 3.0, 0.45), (0.25, 0.85, 3.0, 0.45)):
        n = 5
        for k in range(n):
            t0 = -1 + 2*k/n; t1 = -1 + 2*(k+1)/n; tm = (t0 + t1)/2
            rr = r*math.sqrt(max(1 - tm*tm, 0.05))
            P.append(cyl(cx, cy, rr, cz + t0*r*0.7, cz + t1*r*0.7, 'blossom', n=14, tex=bl))
    return P

@item('ext_hedge', STREET, (2, 1), 0.9, 'R4', 'P2', notes='clipped boxwood hedge in a low planter')
def hedge(state='default'):
    lf = lambda f, x, y, z, t, rc: ('4b_lime' if hsh(int(x*30), int(y*30), int(z*30)) < 0.12 else ('tile_green_dk' if hsh(int(x*30), int(y*30), int(z*30), 1) < 0.2 else None))
    return [box(0.05, 0.15, 0, 1.95, 0.85, 0.25, 'concrete'), box(0.1, 0.2, 0.25, 1.9, 0.8, 0.9, 'leaf', lf)]

@item('ext_street_sign', STREET, (1, 1), 3.0, 'R4', 'P2', notes="green street-name blade 'LOS ROBLES AV' (fictional address 2311 is used on the door transom)")
def street_sign(state='default'):
    def t(face, x, y, z, tone, rc):
        if face in ('front', 'back') and 2.62 < z < 2.78:
            if px_text('LOS ROBLES AV', int((x + 0.1)*64), int((2.75 - z)*64)): return 'white_hi'
            return 'tile_green' if z > 2.64 else 'white_hi'
        return None
    return [cyl(0.5, 0.5, 0.03, 0, 2.95, 'steel', n=6), box(-0.02, 0.48, 2.6, 0.98, 0.52, 2.8, 'green', t)]

@item('ext_trash_can', STREET, (1, 1), 0.95, 'R1', 'P2')
def street_trash(state='default'):
    return [cyl(0.5, 0.5, 0.24, 0, 0.9, 'green', n=12, tex=lambda f, x, y, z, t, rc: (3 if (math.atan2(y - 0.5, x - 0.5)*8) % 1 < 0.2 else None)),
            cyl(0.5, 0.5, 0.26, 0.9, 0.95, 'iron', n=12)]

def entrance_tex(face, x, y, z, tone, rc):
    if face != 'front': return None
    # transom with the fictional street number
    if 2.12 < z < 2.48 and 0.28 < x < 1.72:
        if px_text('2311', int((x - 0.86)*64)//2, int((2.42 - z)*64)//2): return 'lamp_warm'
        return 'grey' if abs(x - 1.0) < 0.02 else 'ink_2'
    if 0.3 < x < 1.7 and z < 2.1:
        if abs(x - 1.0) < 0.02: return 'ink'
        lx = (x - 0.3) % 0.7
        if 0.12 < lx < 0.58 and 0.7 < z < 1.85: return 'white_hi' if (lx - z*0.4) % 0.5 < 0.04 else ('screen_glow' if z > 1.3 else 'grey')
        if abs(lx - 0.62) < 0.02 and abs(z - 1.05) < 0.03: return 'lamp_warm'
        return None
    return None
@item('ext_entrance_doors', STREET, (2, 1), 2.7, 'R4', 'P0', blocks=False, mount='wall', notes='building front doors: double wood/glass doors, transom with the fictional number 2311, stone surround. Placed at z=0.45 on top of ext_entry_steps',
      hooks=[H('door', 'door', (1.0, 0.55), (0, -1), 'open_door', approach=(1, 0), tags=['to_lobby']),
             H('buzzer', 'use', (1.85, 0.5), (0, -1), 'press_buzzer', approach=(1, 0))])
def entrance(state='closed'):
    P = [box(0.0, 0.0, 0, 0.3, 0.12, 2.6, 'stone'), box(1.7, 0.0, 0, 2.0, 0.12, 2.6, 'stone'), box(0.0, 0.0, 2.5, 2.0, 0.14, 2.7, 'stone')]
    P.append(box(0.3, 0.02, 0, 1.7, 0.06, 2.5, 'wood_dk', entrance_tex))
    P.append(box(1.78, 0.12, 1.0, 1.9, 0.15, 1.3, 'brass'))
    return P

@item('ext_entry_steps', STREET, (2, 1), 0.45, 'R4', 'P0', blocks=False, notes='three stone steps up to the entrance (top at the -Y side), iron handrails',
      hooks=[H('climb', 'climb_lane_up', (1.0, 0.9), (0, -1), 'walk_stairs_up', approach=(1, 1)), H('sit_steps', 'sit', (0.4, 0.75), (0, 1), 'sit_floor', approach=(0, 1))])
def steps(state='default'):
    nos = lambda f, x, y, z, t, rc: ('white_hi' if f == 'top' and (y % (1/3)) > (1/3 - 1.5/64) else None)
    P = [box(0.0, 0.0, 0, 2.0, 1/3, 0.45, 'stone', nos), box(0.0, 1/3, 0, 2.0, 2/3, 0.3, 'stone', nos), box(0.0, 2/3, 0, 2.0, 1.0, 0.15, 'stone', nos)]
    for x in (0.05, 1.92):
        P.append(box(x, 0.85, 0.15, x + 0.04, 0.9, 1.05, 'iron')); P.append(box(x, 0.1, 0.45, x + 0.04, 0.15, 1.35, 'iron'))
        P += rod((x + 0.02, 0.88, 1.05), (x + 0.02, 0.12, 1.35), 0.02, 'iron', n=6)
    return P

@item('ext_wall_lantern', STREET, (1, 1), 2.6, 'R4', 'P2', blocks=False, mount='wall', sort_bias=-1, layer='wall_decal', shadow=False, notes='coach lantern beside the entrance')
def wall_lantern(state='default'):
    return [box(0.45, 0.0, 1.95, 0.55, 0.12, 2.0, 'iron'), box(0.42, 0.08, 2.0, 0.58, 0.24, 2.3, 'lamp'), box(0.4, 0.06, 2.3, 0.6, 0.26, 2.36, 'iron')]

# ================================================================== LOBBY
@item('lobby_mailboxes', LOBBY, (2, 1), 1.9, 'R4', 'P0', blocks=False, mount='wall', sort_bias=-1, layer='wall_decal', shadow=False,
      notes='bank of brass tenant mailboxes (spec §5.2 brass mailboxes)', hooks=[H('check_mail', 'use', (1.0, 0.6), (0, -1), 'check_mail', approach=(1, 0), cap=2)])
def lobby_mail(state='default'):
    def t(face, x, y, z, tone, rc):
        if face != 'front': return None
        cx = (x - 0.12) % 0.25; cz = (z - 0.95) % 0.2
        if cx < 1.2/64 or cz < 1.2/64: return 'wood_dk'
        if abs(cx - 0.19) < 1.2/64 and abs(cz - 0.1) < 1.2/64: return 'ink_2'
        if 0.03 < cx < 0.15 and 0.13 < cz < 0.16: return 'paper'
        return None
    return [box(0.12, 0.0, 0.95, 1.88, 0.1, 1.75, 'brass', t)]

@item('lobby_stair_up', LOBBY, (2, 4), 2.0, 'R4', 'P0', blocks=False, sort_bias=-0.5, notes='bottom flight of the stairwell, rising toward -Y (wraps around the broken elevator, spec §5.2)',
      hooks=[H('climb_lane_up', 'climb_lane_up', (1.0, 3.85), (0, -1), 'walk_stairs_up', approach=(1, 4)),
             H('climb_lane_down', 'climb_lane_down', (1.0, 0.2), (0, 1), 'walk_stairs_down')])
def lobby_stairs(state='default'):
    P = []
    for k in range(12):
        P.append(box(0.0, 4 - (k + 1)/3, 0, 2.0, 4 - k/3, (k + 1)/6, 'hall', lambda f, x, y, z, t, rc: ('wood_hi' if f == 'top' and (y % (1/3)) < 1.5/64 else None)))
    for k in range(0, 12, 2):
        P.append(box(1.92, 4 - (k + 1)/3 + 0.1, (k + 1)/6, 1.96, 4 - (k + 1)/3 + 0.14, (k + 1)/6 + 0.9, 'paint_wh'))
    P += rod((1.94, 3.9, 0.95), (1.94, 0.1, 2.95), 0.045, 'wood', n=60)
    return P

@item('lobby_mat', LOBBY, (2, 1), 0.012, 'R2', 'P2', blocks=False, layer='floor_decal', shadow=False, outline='soft')
def lobby_mat(state='default'):
    return [box(0.1, 0.1, 0, 1.9, 0.9, 0.012, 'dark', lambda f, x, y, z, t, rc: ('grey_dk' if (int(x*32) + int(y*32)) % 2 else None))]

@item('lobby_glass_door', LOBBY, (1, 1), 2.22, 'R4', 'P0', states=DOOR_STATES, blocks=False, mount='wall', notes='lobby side of the building entrance: wood door with a big glass light',
      hooks=[H('door', 'door', (0.5, 0.55), (0, -1), 'open_door', approach=(0, 0), tags=['to_street'])])
def lobby_door(state='closed'):
    return swing_door('wood_dk', 'wood', glass_door_tex, swing=1)(state)

@item('lobby_sconce', LOBBY, (1, 1), 2.2, 'R1', 'P2', blocks=False, mount='wall', sort_bias=-1, layer='wall_decal', shadow=False, states=('on',))
def lobby_sconce(state='on'):
    return [box(0.44, 0.0, 1.85, 0.56, 0.05, 2.05, 'brass'), cyl(0.5, 0.12, 0.08, 1.9, 2.1, 'lamp', n=10)]

# ================================================================== RAJ'S APARTMENT (Danish mid-century + Indian accents; original pieces)
def camel_pillow(face, x, y, z, tone, rc):
    if face == 'front':
        u, v = (x % 1.0), z
        if abs(v - 0.6 - 0.05*math.sin(u*25)) < 0.02: return 'cafe_cream'
        return None
    return None
@item('raj_sofa', RAJ, (3, 1), 0.82, 'R4', 'P0', notes='slim Danish-modern sofa on tapered walnut legs; camel-print and paisley throw pillows',
      hooks=[H(f'seat{i}', 'sit', (0.66 + 0.84*i, 0.6), (0, 1), 'sit_couch', approach=(i, 1)) for i in range(3)])
def raj_sofa(state='default'):
    P = []
    for x in (0.15, 2.8):
        for y in (0.15, 0.8): P += rod((x, y, 0), (x + (0.02 if x < 1 else -0.02), y, 0.2), 0.025, 'wood', n=3)
    P.append(box(0.06, 0.1, 0.2, 2.94, 0.92, 0.3, 'wood_dk'))
    for i in range(3): P.append(box(0.16 + i*0.9, 0.32, 0.3, 0.16 + (i + 1)*0.9 - 0.02, 0.92, 0.44, 'stone'))
    P.append(box(0.06, 0.1, 0.3, 2.94, 0.3, 0.82, 'stone', cushion_tex((1.0, 2.0))))
    P.append(box(0.04, 0.1, 0.2, 0.16, 0.92, 0.58, 'wood_dk')); P.append(box(2.84, 0.1, 0.2, 2.96, 0.92, 0.58, 'wood_dk'))
    P.append(box(0.25, 0.3, 0.44, 0.6, 0.42, 0.74, 'orange', lambda f, x, y, z, t, rc: ('wood_dk' if f == 'front' and (abs(z - 0.58 - 0.04*math.sin(x*60)) < 0.015 or (abs(x - 0.36) < 0.02 and 0.5 < z < 0.62) or (abs(x - 0.48) < 0.02 and 0.5 < z < 0.6)) else None)))
    P.append(box(2.35, 0.3, 0.44, 2.7, 0.42, 0.72, 'purple', lambda f, x, y, z, t, rc: ('lamp_warm' if f == 'front' and (int(x*64) + int(z*64)) % 5 == 0 else None)))
    return P

@item('raj_coffee_oval', RAJ, (2, 1), 0.42, 'R2', 'P0', notes='oval glass-top coffee table on a walnut base',
      hooks=[H('surface', 'place_item', (1.0, 0.5), (0, 1), z=0.42)])
def raj_coffee(state='default'):
    return [box(0.4, 0.35, 0, 1.6, 0.65, 0.3, 'wood_dk', wood_grain('x', 0.12, 71)),
            cyl(1.0, 0.5, 0.92, 0.36, 0.42, 'glass', n=20, ry=0.44, tex=lambda f, x, y, z, t, rc: ('white_hi' if f == 'top' and (x - y) % 0.7 < 0.05 else ('screen_glow' if f == 'top' else None))),
            box(0.6, 0.38, 0.42, 0.9, 0.58, 0.45, 'red'), cyl(1.35, 0.5, 0.05, 0.42, 0.52, 'brass', n=8)]

@item('raj_ufo_lamp', RAJ, (1, 1), 1.85, 'R1', 'P0', states=('on', 'off'), notes="Raj's one-of-a-kind UFO floor lamp: chrome saucer shade with a ring of lights (original design)")
def ufo_lamp(state='on'):
    on = state == 'on'
    ring = lambda f, x, y, z, t, rc: (('lamp_warm' if on else 'grey') if f != 'top' and int(math.degrees(math.atan2(y - 0.5, x - 0.5)) // 30) % 2 == 0 else None)
    return [cyl(0.5, 0.5, 0.2, 0, 0.04, 'chrome', n=12), cyl(0.5, 0.5, 0.02, 0.04, 1.5, 'chrome', n=6),
            cyl(0.5, 0.5, 0.42, 1.5, 1.58, 'chrome', n=18, tex=ring),
            cyl(0.5, 0.5, 0.32, 1.58, 1.66, 'chrome', n=16), cyl(0.5, 0.5, 0.16, 1.66, 1.8, 'lamp' if on else 'glass', n=12),
            cyl(0.5, 0.5, 0.3, 1.46, 1.5, 'lamp' if on else 'metal', n=16)]

@item('raj_buttercup_chair', RAJ, (1, 1), 0.95, 'R4', 'P1', notes='swivel bucket "buttercup" chair on a chrome pedestal',
      hooks=[dict(H('seat0', 'sit', (0.5, 0.55), (0, 1), 'sit_chair', approach=(0, 1)), seat_off=[0, -0.1])])   # back into the bucket
def buttercup(state='default'):
    P = [cyl(0.5, 0.5, 0.28, 0, 0.03, 'chrome', n=12), cyl(0.5, 0.5, 0.04, 0.03, 0.32, 'chrome', n=6)]
    P.append(cyl(0.5, 0.5, 0.34, 0.32, 0.46, 'mustard', n=16))
    pts = [(0.5 + 0.42*math.cos(math.radians(a)), 0.5 + 0.42*math.sin(math.radians(a))) for a in range(180, 361, 15)]
    inner = [(0.5 + 0.34*math.cos(math.radians(a)), 0.5 + 0.34*math.sin(math.radians(a))) for a in range(360, 179, -15)]
    P.append(Prism(pts + inner, 0.32, 0.95, 'mustard'))
    return P

@item('raj_dining_round', RAJ, (2, 2), 0.95, 'R1', 'P1', notes='round walnut dining table with four metallic chairs (built in); holds the glowing-crystal display',
      hooks=[dict(H(f'seat{i}', 'sit', (1 + 0.78*math.cos(a), 1 + 0.78*math.sin(a)), (-math.cos(a), -math.sin(a)), 'sit_chair_eat', approach=(int(1 + 0.78*math.cos(a)), int(1 + 0.78*math.sin(a)))),
                  seat_off=[0.08*math.cos(a), 0.08*math.sin(a)])      # hips back against the chair's backrest
             for i, a in enumerate((math.pi/2, 0.0, -math.pi/2, math.pi))] + [H('centre', 'place_item', (1.0, 1.0), (0, 1), z=0.75)])
def raj_dining(state='default'):
    P = [cyl(1.0, 1.0, 0.3, 0, 0.04, 'wood_dk', n=12), cyl(1.0, 1.0, 0.07, 0.04, 0.72, 'wood_dk', n=8), cyl(1.0, 1.0, 0.6, 0.72, 0.76, 'wood', n=20)]
    for a in (math.pi/2, 0.0, -math.pi/2, math.pi):
        cx, cy = 1 + 0.82*math.cos(a), 1 + 0.82*math.sin(a)
        P.append(cyl(cx, cy, 0.03, 0, 0.44, 'chrome', n=6)); P.append(cyl(cx, cy, 0.2, 0.44, 0.48, 'chrome', n=12))
        bx, by = 1 + 1.0*math.cos(a), 1 + 1.0*math.sin(a); tx, ty = -math.sin(a)*0.18, math.cos(a)*0.18
        P.append(Prism([(bx - tx - math.cos(a)*0.02, by - ty - math.sin(a)*0.02), (bx + tx - math.cos(a)*0.02, by + ty - math.sin(a)*0.02),
                        (bx + tx + math.cos(a)*0.02, by + ty + math.sin(a)*0.02), (bx - tx + math.cos(a)*0.02, by - ty + math.sin(a)*0.02)], 0.48, 0.92, 'chrome'))
    for k, (dx, dy, h) in enumerate(((0, 0, 0.26), (0.08, 0.05, 0.17), (-0.07, 0.06, 0.14), (0.03, -0.08, 0.12))):   # original glowing crystals
        P.append(Prism([(1 + dx - 0.04, 1 + dy), (1 + dx, 1 + dy - 0.04), (1 + dx + 0.04, 1 + dy), (1 + dx, 1 + dy + 0.04)], 0.76, 0.76 + h, 'lime'))
    return P

@item('raj_bar_cart', RAJ, (1, 1), 0.95, 'R4', 'P2', notes='three-shelf metallic rolling cart: teapot, bottles, the orange owl cookie jar on top',
      hooks=[H('use', 'use', (0.5, 1.3), (0, -1), 'make_tea', approach=(0, 1))])
def bar_cart(state='default'):
    P = [cyl(x, y, 0.04, 0, 0.08, 'black', n=6) for x in (0.18, 0.82) for y in (0.25, 0.75)]
    for x in (0.16, 0.8):
        for y in (0.22, 0.74): P.append(box(x, y, 0.08, x + 0.04, y + 0.04, 0.9, 'chrome'))
    for z in (0.12, 0.45, 0.8): P.append(box(0.14, 0.2, z, 0.86, 0.8, z + 0.03, 'chrome'))
    P.append(cyl(0.35, 0.5, 0.06, 0.48, 0.66, 'bottle', n=8)); P.append(cyl(0.55, 0.45, 0.05, 0.48, 0.62, 'wine', n=8))
    P.append(cyl(0.4, 0.45, 0.1, 0.83, 0.95, 'white', n=10))
    owl = lambda f, x, y, z, t, rc: ('ink' if f == 'front' and z > 1.0 and abs(abs(x - 0.68) - 0.035) < 0.018 and abs(z - 1.04) < 0.018 else ('paper' if f == 'front' and z > 1.0 and abs(abs(x - 0.68) - 0.035) < 0.03 and abs(z - 1.04) < 0.03 else None))
    P.append(cyl(0.68, 0.5, 0.1, 0.83, 1.1, 'orange', n=10, tex=owl)); P.append(box(0.62, 0.47, 1.1, 0.74, 0.53, 1.14, 'orange'))
    return P

@item('raj_telescope_big', RAJ, (1, 1), 1.75, 'R8', 'P0', notes='big orange-tube catadioptric telescope on a fork mount and tripod; tube points to the item back (window)',
      hooks=[H('look', 'look', (0.5, 1.0), (0, -1), 'look_telescope', approach=(0, 1), tags=['raj', 'stargazing'])])
def big_scope(state='default'):
    P = []
    for a in (90, 210, 330):
        f = (0.5 + 0.38*math.cos(math.radians(a)), 0.5 + 0.38*math.sin(math.radians(a)), 0.0)
        P += rod(f, (0.5, 0.5, 0.9), 0.022, 'black', n=10)
    P.append(cyl(0.5, 0.5, 0.1, 0.88, 0.98, 'black', n=10))
    P.append(box(0.32, 0.45, 0.98, 0.38, 0.55, 1.35, 'black')); P.append(box(0.62, 0.45, 0.98, 0.68, 0.55, 1.35, 'black'))
    P += rod((0.5, 0.82, 1.15), (0.5, 0.1, 1.5), 0.13, 'orange', n=14)
    P.append(cyl(0.5, 0.1, 0.14, 1.46, 1.54, 'black', n=12)); P.append(cyl(0.5, 0.86, 0.04, 1.1, 1.2, 'black', n=6))
    return P

@item('raj_tv_console', RAJ, (2, 1), 1.25, 'R4', 'P0', states=('on', 'off'), notes='low Danish media console + wide plasma TV',
      hooks=[H('watch_target', 'look', (1.0, 0.45), (0, 1), tags=['tv'], z=0.9)])
def raj_tv(state='on'):
    P = [box(0.05, 0.25, 0.12, 1.95, 0.8, 0.5, 'wood', first(panel_tex([(0.12, 0.18, 0.95, 0.45), (1.05, 0.18, 1.88, 0.45)]), wood_grain('x', 0.15, 81)))]
    P += [box(x, y, 0, x + 0.04, y + 0.04, 0.12, 'wood_dk') for x in (0.12, 1.84) for y in (0.3, 0.72)]
    P.append(box(0.9, 0.45, 0.5, 1.1, 0.6, 0.6, 'black'))
    P.append(box(0.1, 0.5, 0.6, 1.9, 0.56, 1.25, 'black', screen_tex(state == 'on', 0.14, 1.86, 0.64, 1.21)))
    P.append(box(1.55, 0.35, 0.5, 1.75, 0.55, 0.62, 'brass'))     # little brass elephant stand-in
    return P

def tapestry_tex(face, x, y, z, tone, rc):
    if face not in ('front',): return None
    if not (0.14 < x < 0.86 and 0.2 < z < 2.0): return None
    if x < 0.18 or x > 0.82 or z < 0.24 or z > 1.96: return 'lamp_warm' if (int(z*32) % 2) else 'ccf_amber'
    u, v = (x - 0.5), (z - 1.1)
    d = abs(u)*1.3 + abs(v)*0.6
    if abs(d - 0.32) < 0.025 or abs(d - 0.18) < 0.02: return 'lamp_warm'
    if d < 0.1: return '4b_orange'
    if (int((x + z)*12) + int((x - z)*12)) % 3 == 0 and d > 0.36: return '4b_orange'
    return 'ccf_booth_red' if d > 0.36 else '4b_purple'
@item('raj_tapestry_door', RAJ, (1, 1), 2.22, 'R4', 'P0', states=DOOR_STATES, blocks=False, mount='wall',
      notes='bedroom door draped with an Indian-style tapestry (original medallion pattern)',
      hooks=[H('door', 'door', (0.5, 0.55), (0, -1), 'open_door', approach=(0, 0))])
def raj_tdoor(state='closed'):
    return swing_door('wood_dk', 'wood_dk', tapestry_tex, swing=1)(state)

@item('raj_display_shelf', RAJ, (2, 1), 2.1, 'R4', 'P1', blocks=False, mount='wall', sort_bias=-1, layer='wall_decal', shadow=False,
      notes='floating walnut shelf: vintage-style tin robots (red/black), a model rocket, incense holder')
def raj_shelf(state='default'):
    P = [box(0.1, 0.0, 1.5, 1.9, 0.3, 1.54, 'wood_dk')]
    for k, (x, m) in enumerate(((0.3, 'red'), (0.75, 'black'), (1.15, 'red'))):
        P.append(box(x - 0.07, 0.1, 1.54, x + 0.07, 0.2, 1.72, m, lambda f, xx, y, z, t, rc: ('lamp_warm' if f == 'front' and 1.6 < z < 1.66 and (int(xx*64) % 3 == 0) else None)))
        P.append(box(x - 0.05, 0.11, 1.72, x + 0.05, 0.19, 1.82, 'chrome', lambda f, xx, y, z, t, rc, x=x: ('screen_glow' if f == 'front' and abs(z - 1.78) < 0.015 and abs(abs(xx - x) - 0.02) < 0.012 else None)))
        P.append(cyl(x, 0.15, 0.008, 1.82, 1.88, 'dark', n=4))
    P.append(cyl(1.6, 0.15, 0.04, 1.54, 1.85, 'white', n=8)); P.append(Prism([(1.56, 0.15), (1.6, 0.11), (1.64, 0.15), (1.6, 0.19)], 1.85, 1.92, 'red'))
    P.append(box(1.75, 0.1, 1.54, 1.85, 0.2, 1.58, 'brass')); P.append(cyl(1.8, 0.15, 0.005, 1.58, 1.75, 'wood', n=4))
    return P

@item('raj_rug', RAJ, (3, 2), 0.012, 'R2', 'P1', blocks=False, layer='floor_decal', shadow=False, outline='soft', notes='Indian medallion area rug')
def raj_rug(state='default'):
    def t(face, x, y, z, tone, rc):
        if face != 'top': return None
        ex = min(x - 0.1, 2.9 - x, y - 0.1, 1.9 - y)
        if ex < 0.06: return 'lamp_warm' if (int(x*16) + int(y*16)) % 2 else 'ccf_amber'
        if ex < 0.16: return 'shadow_violet' if (int(x*24) + int(y*24)) % 3 else 'lamp_warm'
        d = abs(x - 1.5)*0.7 + abs(y - 1.0)
        if abs(d - 0.45) < 0.035 or abs(d - 0.3) < 0.03: return 'lamp_warm'
        if d < 0.15: return '4b_turquoise'
        return 'ccf_booth_red' if d > 0.45 else 'wine_' if False else 'marker_red'
    return [box(0.1, 0.1, 0, 2.9, 1.9, 0.012, 'wine', t)]

@item('raj_kitchenette', RAJ, (3, 1), 2.3, 'R4', 'P1', notes='modern kitchenette run (reuses the counter builder): pale wood and steel',
      hooks=[H('cook', 'work', (1.8, 1.2), (0, -1), 'cook', approach=(1, 1)), H('use_sink', 'use', (0.7, 1.3), (0, -1), 'wash', approach=(0, 1))])
def raj_kitchen(state='default'):
    from env_items import counter_builder
    return counter_builder('wood_lt', 'steel', 'orange', 'ccf_amber', True)(state)

# ---------------------------------------------------------------- building facade (exterior back plane of the street location)
FAC_W = 16
FAC_WIN = (1.6, 3.6, 5.6, 10.4, 12.4, 14.4)        # window centres (door bay at x 7..9)
def facade_tex(face, x, y, z, tone, rc):
    if face == 'top': return None
    if face != 'front': return None
    # entrance bay is behind the door item
    if 6.95 < x < 9.05 and z < 3.05: return 'ink_2'
    if z < 0.45: return 1 if (x % 0.5) > 0.02 else 3
    if 3.15 <= z < 3.45 or z >= 6.25: return None                  # string course / cornice have own prims
    up = z >= 3.45
    for cx in FAC_WIN:
        hw = 0.5
        z0, z1 = (0.95, 2.75) if not up else (3.7, 5.7)
        if abs(x - cx) <= hw + 0.06 and z0 - 0.08 <= z <= z1 + 0.32:
            if z > z1 + 0.05:      # arch / pediment
                if z1 + 0.05 < z < z1 + 0.32 and abs(x - cx) < hw + 0.06 - (z - z1 - 0.05)*1.2: return 'paper' if (z - z1) > 0.2 else 'grey_lt'
                break
            if z < z0: return 'paper'
            if abs(x - cx) > hw: return 'paper'
            if abs(x - cx) < 0.02 or (int((z - z0)/0.3) != int((z - z0 - 1/64)/0.3)): return 'white_hi'
            # shutters (open) outside the frame are drawn via prims; glass reflection
            u = (z - z0)/(z1 - z0)
            if (x - cx + u*0.6) % 0.55 < 0.05: return 'white_hi'
            return 'screen_glow' if u > 0.55 else ('grey' if u > 0.2 else 'shadow_violet')
    if not up:
        if (z - 0.45) % 0.34 < 1.2/64: return 2               # rusticated stucco coursing
        if hsh(int(x*30), int(z*30), 41) < 0.03: return 2
    else:
        if hsh(int(x*30), int(z*30), 42) < 0.025: return 2
    return None
@item('ext_building_facade', STREET, (FAC_W, 1), 6.7, 'R1', 'P0', blocks=True, mount='wall', shadow=False,
      notes='front of the (fictional) 2311 apartment building: stucco ground floor with rustication, arched French windows with shutters, iron balconettes, string course, cornice. Drawn as the back plane of street_exterior')
def facade(state='default'):
    P = [box(0, 0.0, 0, FAC_W, 0.3, 6.25, 'cream', facade_tex),
         box(0, 0.0, 0, 6.95, 0.38, 0.45, 'stone'), box(9.05, 0.0, 0, FAC_W, 0.38, 0.45, 'stone'),
         box(-0.05, 0.0, 3.15, FAC_W + 0.05, 0.42, 3.45, 'stone', lambda f, x, y, z, t, rc: (3 if f == 'front' and z < 3.18 else None)),
         box(-0.1, 0.0, 6.25, FAC_W + 0.1, 0.5, 6.55, 'stone', lambda f, x, y, z, t, rc: ('paper' if f == 'front' and int(x*8) % 2 == 0 and z < 6.33 else None)),
         box(-0.1, 0.0, 6.55, FAC_W + 0.1, 0.4, 6.7, 'stone')]
    for cx in FAC_WIN:
        for s in (-1, 1):   # open shutters on both floors
            for (z0, z1) in ((0.95, 2.75), (3.7, 5.7)):
                xs = cx + s*0.62
                P.append(box(xs - 0.12 if s > 0 else xs - 0.12, 0.3, z0, xs + 0.12, 0.34, z1, 'green',
                             lambda f, x, y, z, t, rc: (3 if f == 'front' and (z*64) % 6 < 1 else None)))
        # iron balconette on the upper window
        P.append(box(cx - 0.55, 0.3, 3.7, cx + 0.55, 0.62, 3.76, 'iron'))
        P.append(box(cx - 0.55, 0.58, 3.76, cx + 0.55, 0.62, 4.45, 'iron', lambda f, x, y, z, t, rc: ('clear' if f in ('front', 'back') and (x*64) % 6 > 1.2 and 3.8 < z < 4.38 else None)))
    # entrance canopy
    P.append(box(6.8, 0.3, 3.0, 9.2, 0.9, 3.12, 'iron'))
    return P
