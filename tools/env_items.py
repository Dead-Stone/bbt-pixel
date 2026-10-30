"""Item definitions for floor 4: apartment 4A, the 4th-floor landing, apartment 4B (spec §4.4/§5.1/§5.2/§5.4).
Canonical frame: footprint fx x fy metres, FRONT faces +Y (the SW view).  Hooks use canonical metres."""
import math
from iso_render import Prism, box, cyl, MAT
from env_tex import hsh, line, wood_grain, merge, text_px, text_w

MAT.update({
 'leather2': ('leather', 'leather_dk', 'leather_xdk', 'ink_2'),
 'paint_wh': ('white_hi', 'paper', 'grey_lt', 'grey'),
 'paper': ('white_hi', 'paper', 'grey_lt', 'grey'),
})
ITEMS = {}
def item(id, loc, fp, h, rclass, prio, hooks=(), states=('default',), blocks=True, mount='floor', sort_bias=0,
         layer='objects', notes='', tags=(), outline='ink', shadow=True):
    def deco(fn):
        ITEMS[id] = dict(id=id, location=loc, footprint=list(fp), height_m=h, rotation_class=rclass, priority=prio,
                         hooks=list(hooks), states=list(states), blocks_walk=blocks, mount=mount, sort_bias=sort_bias,
                         layer=layer, notes=notes, tags=list(tags), build=fn, outline=outline, shadow=shadow)
        return fn
    return deco
def H(id, type, pos, facing, anim='', cap=1, tags=(), approach=None, z=0.0, owner=None):
    d = dict(id=id, type=type, pos=list(pos), facing=list(facing), capacity=cap, anim=anim, tags=list(tags), z=z)
    if approach is not None: d['approach'] = list(approach)
    if owner: d['priority_owner'] = owner
    return d

def rod(p0, p1, r, mat, n=None, tex=None):
    """tilted cylinder approximated by short vertical prisms (prisms are vertical in this renderer)"""
    (x0, y0, z0), (x1, y1, z1) = p0, p1
    L = math.dist(p0, p1); n = n or max(2, int(L / 0.05))
    out = []
    for k in range(n):
        t0, t1 = k/n, (k+1)/n; tm = (t0+t1)/2
        za, zb = z0 + (z1-z0)*t0, z0 + (z1-z0)*t1
        if abs(zb - za) < 0.01: zb = za + 0.02
        out.append(cyl(x0+(x1-x0)*tm, y0+(y1-y0)*tm, r, min(za, zb), max(za, zb), mat, n=8, tex=tex))
    return out

def rot_poly(pts, cx, cy, ang):
    c, s = math.cos(ang), math.sin(ang)
    return [(cx + (x-cx)*c - (y-cy)*s, cy + (x-cx)*s + (y-cy)*c) for x, y in pts]

# ---------------------------------------------------------------- textures
def cushion_tex(seams=(), base=None):
    def t(face, x, y, z, tone, rc):
        for sx in seams:
            if abs(x - sx) < 1/64: return 3
        return tone
    return t
def panel_tex(rects, tone_add=1):
    """raised-panel door/cabinet lines on the front face: rects = [(x0,z0,x1,z1)]"""
    def t(face, x, y, z, tone, rc):
        if face != 'front': return tone
        for (a, b, c, d) in rects:
            onx = (abs(x-a) < 1/64 or abs(x-c) < 1/64) and b <= z <= d
            onz = (abs(z-b) < 1/64 or abs(z-d) < 1/64) and a <= x <= c
            if onx or onz:
                return min(tone + tone_add, 3) if (abs(x-c) < 1/64 or abs(z-b) < 1/64) else 0
        return tone
    return t
def knob_tex(pts, col='brass_hi'):
    def t(face, x, y, z, tone, rc):
        if face != 'front': return tone
        for (kx, kz) in pts:
            if abs(x-kx) < 1.6/64 and abs(z-kz) < 1.6/64: return 'ccf_amber' if (x-kx)+(kz-z) > 0 else 'lamp_warm'
        return tone
    return t
def grid_tex(px, pz, col, face_only='front'):
    def t(face, x, y, z, tone, rc):
        if face_only and face != face_only: return tone
        if line(x, px) or line(z, pz): return col
        return tone
    return t
def text_tex(face_name, x0, ztop, text, col, scale=1):
    def t(face, x, y, z, tone, rc):
        if face != face_name: return None
        c = int(math.floor((x - x0)*64/scale)); r = int(math.floor((ztop - z)*64/scale))
        if text_px(text, c, r): return col
        return None
    return t
def first(*fs):
    def t(face, x, y, z, tone, rc):
        for f in fs:
            r = f(face, x, y, z, tone, rc)
            if r is not None and r is not tone and r != tone: return r
        return tone
    return t

# ================================================================== 4A
@item('4a_couch', '4A', (3, 1), 0.85, 'R4', 'P0', notes='strip-sliced per tile; seat0 = Sheldon\'s spot (viewer-left end in the SW view)',
      hooks=[H('seat0', 'sit', (0.66, 0.6), (0, 1), 'sit_couch', tags=['sheldons_spot'], approach=(0, 1), owner='sheldon'),
             H('seat1', 'sit', (1.5, 0.6), (0, 1), 'sit_couch', approach=(1, 1)),
             H('seat2', 'sit', (2.34, 0.6), (0, 1), 'sit_couch', approach=(2, 1)),
             H('armrest_r', 'perch', (2.88, 0.55), (0, 1), 'perch_armrest', approach=(2, 1))])
def couch_4a(state='default'):
    P = []
    for x in (0.08, 2.86):
        for y in (0.12, 0.86): P.append(box(x, y, 0, x+0.06, y+0.06, 0.08, 'dark'))
    P.append(box(0.04, 0.10, 0.08, 2.96, 0.95, 0.30, 'leather2', wood_grain('x', 0.2, 3)))
    w = (2.56 - 0.02) / 3
    for i in range(3):
        x0 = 0.22 + i*(w+0.01)
        P.append(box(x0, 0.34, 0.30, x0+w, 0.95, 0.46, 'leather', cushion_tex()))
        P.append(box(x0, 0.24, 0.44, x0+w, 0.42, 0.80, 'leather', cushion_tex()))
    P.append(box(0.04, 0.06, 0.30, 2.96, 0.26, 0.86, 'leather2'))
    P.append(box(0.0, 0.06, 0.0, 0.22, 0.98, 0.64, 'leather'))
    P.append(box(2.78, 0.06, 0.0, 3.0, 0.98, 0.64, 'leather'))
    return P

@item('4a_coffee_table', '4A', (2, 1), 0.45, 'R4', 'P0',
      hooks=[H('surface0', 'place_item', (0.6, 0.5), (0, 1), tags=['takeout', 'drinks'], z=0.45),
             H('surface1', 'place_item', (1.4, 0.5), (0, 1), tags=['takeout', 'drinks'], z=0.45)])
def coffee_4a(state='default'):
    P = [box(x, y, 0, x+0.07, y+0.07, 0.38, 'wood_dk') for x in (0.12, 1.81) for y in (0.2, 0.73)]
    P.append(box(0.14, 0.22, 0.10, 1.86, 0.78, 0.13, 'wood_dk'))
    P.append(box(0.08, 0.15, 0.38, 1.92, 0.85, 0.45, 'wood', wood_grain('x', 0.13, 5)))
    P.append(box(0.4, 0.3, 0.13, 0.75, 0.6, 0.17, 'red'))      # magazines on the lower shelf
    P.append(box(0.45, 0.33, 0.17, 0.78, 0.62, 0.19, 'blue'))
    return P

def screen_tex(on, x0, x1, z0, z1, style='tv'):
    def t(face, x, y, z, tone, rc):
        if face != 'front' or not (x0 <= x <= x1 and z0 <= z <= z1): return tone
        if not on:
            d = (x - x0) - (z - z0)*1.4
            return 'grey_dk' if 0.25 < d < 0.31 or 0.36 < d < 0.38 else 'shadow_violet'
        if style == 'code':
            r = int((z1 - z) * 64) // 3; c = int((x - x0) * 64)
            if (z1 - z)*64 % 3 < 1 and hsh(r, c // 3) < 0.55 and c > 2 + 3*hsh(r, 9)*4: return 'marker_green' if r % 4 else 'white_hi'
            return 'ink_2'
        u = (x - x0) / (x1 - x0); v = (z - z0) / (z1 - z0)
        if v < 0.3: return 'plant_green' if hsh(int(u*30), 1) < 0.7 else 'marker_green'
        if abs(u - 0.62) < 0.1 and 0.25 < v < 0.7: return 'marker_red' if v > 0.55 else 'comic_blue'
        return 'screen_glow' if v > 0.55 or (int(u*64*1.6) + int(v*40)) % 2 else 'comic_blue'
    return t

@item('4a_tv_stand', '4A', (2, 1), 1.2, 'R4', 'P0', states=('off', 'on'),
      notes='media console + flat TV + game console; seen from behind in the sitcom staging (faces the couch)',
      hooks=[H('watch_target', 'look', (1.0, 0.45), (0, 1), tags=['tv'], z=0.9),
             H('game_console', 'use', (1.35, 1.35), (0, -1), 'use_console', approach=(1, 1), tags=['console'])])
def tv_4a(state='off'):
    P = [box(0.05, 0.25, 0.0, 1.95, 0.8, 0.5, 'wood_dk', first(panel_tex([(0.12, 0.08, 0.95, 0.42), (1.05, 0.08, 1.88, 0.42)]),
                                                                 wood_grain('x', 0.15, 2)))]
    P.append(box(1.2, 0.35, 0.5, 1.55, 0.62, 0.58, 'black', knob_tex([(1.5, 0.54)])))
    P.append(box(0.85, 0.42, 0.5, 1.15, 0.6, 0.53, 'black'))
    P.append(box(0.97, 0.47, 0.53, 1.03, 0.53, 0.62, 'black'))
    P.append(box(0.18, 0.46, 0.6, 1.82, 0.52, 1.2, 'black', screen_tex(state == 'on', 0.22, 1.78, 0.63, 1.17)))
    P.append(box(0.15, 0.62, 0.5, 0.35, 0.72, 0.62, 'cream'))   # DVD stack
    return P

def armchair(mat, pat=None):
    def b(state='default'):
        P = [box(x, y, 0, x+0.06, y+0.06, 0.08, 'dark') for x in (0.14, 0.8) for y in (0.14, 0.82)]
        P.append(box(0.1, 0.1, 0.08, 0.9, 0.94, 0.3, mat, pat))
        P.append(box(0.24, 0.34, 0.3, 0.76, 0.94, 0.47, mat, pat))
        P.append(box(0.1, 0.08, 0.3, 0.9, 0.34, 0.92, mat, pat))
        P.append(box(0.1, 0.1, 0.0, 0.24, 0.96, 0.62, mat, pat))
        P.append(box(0.76, 0.1, 0.0, 0.9, 0.96, 0.62, mat, pat))
        return P
    return b
item('4a_armchair', '4A', (1, 1), 0.92, 'R8', 'P0',
     hooks=[H('seat0', 'sit', (0.5, 0.62), (0, 1), 'sit_chair', approach=(0, 1))])(armchair('leather2', wood_grain('x', 0.2, 7)))

def door_builder(slab_mat, casing_mat, front_plate=None, back_plate=None, swing=1, robe=False, void='ink_2'):
    def b(state='closed'):
        ang = {'closed': 0, 'ajar': 18, 'open_1': 30, 'open_2': 60, 'open': 92}[state]
        P = [box(0.02, 0.0, 0, 0.1, 0.08, 2.2, casing_mat), box(0.9, 0.0, 0, 0.98, 0.08, 2.2, casing_mat),
             box(0.02, 0.0, 2.1, 0.98, 0.08, 2.22, casing_mat)]
        P.append(Prism([(0.1, 0.0), (0.9, 0.0), (0.9, 0.015), (0.1, 0.015)], 0, 2.1, 'black', outline=False))   # void
        y0, y1 = 0.02, 0.065
        hx, hy = 0.1, (y1 if swing > 0 else y0)
        slab = [(0.1, y0), (0.9, y0), (0.9, y1), (0.1, y1)]
        a = math.radians(ang) * (1 if swing > 0 else -1)
        poly = rot_poly(slab, hx, hy, a)
        texs = [panel_tex([(0.2, 0.15, 0.8, 0.95), (0.2, 1.1, 0.8, 1.95)])]
        if front_plate:
            texs.insert(0, text_tex('front', 0.5 - text_w(front_plate)/128, 1.70, front_plate, 'lamp_warm'))
        texs.insert(0, knob_tex([(0.8, 1.0)]))
        if robe:
            def rb(face, x, y, z, tone, rc):
                if face == 'front' and 0.3 < x < 0.62 and 0.9 < z < 1.85 - abs(x-0.46)*0.6: return 2 if x > 0.56 else 1
                return None
            P_robe = True
        tex = first(*texs)
        if ang == 0:
            def wrap(face, x, y, z, tone, rc, tex=tex):
                return tex(face, x, y, z, tone, rc)
            P.append(Prism(poly, 0, 2.08, slab_mat, wrap))
        else:
            # rotated slab: re-map texture into slab-local x so the panels/knob follow the door
            c, s = math.cos(-a), math.sin(-a)
            def wrap(face, x, y, z, tone, rc, tex=tex):
                lx = 0.1 + (x-0.1)*c - (y-hy)*s
                f = 'front' if face in ('front', 'right' if swing > 0 else 'left') and ang > 45 else face
                return tex(f, lx, y, z, tone, rc)
            P.append(Prism(poly, 0, 2.08, slab_mat, wrap))
        if robe and ang < 30:
            P.append(box(0.32, 0.065, 0.95, 0.6, 0.11, 1.75, 'purple'))
            P.append(box(0.36, 0.11, 1.25, 0.56, 0.13, 1.3, 'purple'))
        return P
    return b
DOOR_STATES = ('closed', 'open_1', 'open_2', 'open')
item('4a_front_door', '4A', (1, 1), 2.22, 'R4', 'P0', states=DOOR_STATES, blocks=False, mount='wall',
     notes='front = inside 4A (plain); the "4A" plate is on the landing side.  Placed SE in the x=12 wall.  anim open: closed,open_1,open_2,open @12fps',
     hooks=[H('door', 'door', (0.5, 0.55), (0, -1), 'open_door', approach=(0, 0)),
            H('knock_spot_inside', 'knock_spot_inside', (0.5, 0.6), (0, -1), 'knock', approach=(0, 0)),
            H('knock_spot_outside', 'knock_spot_outside', (0.5, -0.45), (0, 1), 'knock', approach=(0, -1))])(
     door_builder('wood_dk', 'wood', back_plate='4A'))
item('4b_front_door', '4B', (1, 1), 2.22, 'R4', 'P0', states=DOOR_STATES, blocks=False, mount='wall',
     notes='alias hall4_door_4b. front = landing side with the brass "4B" plate; swings into 4B. Placed SE in the x=8 wall; knock target for Sheldon\'s knock_knock_penny (NW)',
     tags=['hall4_door_4b'],
     hooks=[H('door', 'door', (0.5, 0.55), (0, -1), 'open_door', approach=(0, 0)),
            H('knock_spot_outside', 'knock_spot_outside', (0.5, 0.6), (0, -1), 'knock_knock_penny', approach=(0, 0), tags=['knock_x3']),
            H('knock_spot_inside', 'knock_spot_inside', (0.5, -0.45), (0, 1), 'knock', approach=(0, -1)),
            H('answer_spot', 'answer_spot', (0.5, -0.4), (0, 1), 'door_answer_annoyed', approach=(0, -1))])(
     door_builder('paint_wh', 'paint_wh', front_plate='4B', swing=-1))
item('4b_bedroom_door', '4B', (1, 1), 2.22, 'R4', 'P0', states=('ajar', 'closed', 'open'), blocks=False, mount='wall',
     notes='bedroom-door hint: default state ajar, robe on a hook; dark gap = the bedroom beyond',
     hooks=[H('door', 'door', (0.5, 0.55), (0, -1), 'open_door', approach=(0, 0))])(
     door_builder('paint_wh', 'paint_wh', swing=1, robe=True))

@item('4a_desk_laptop', '4A', (2, 1), 0.75, 'R4', 'P0', states=('off', 'on'),
      hooks=[H('use0', 'use', (0.55, 1.15), (0, -1), 'type_desk', approach=(0, 1), tags=['computer', 'needs_chair']),
             H('use1', 'use', (1.45, 1.15), (0, -1), 'type_laptop', approach=(1, 1), tags=['laptop', 'needs_chair'])])
def desk_4a(state='on'):
    on = state == 'on'
    P = [box(0.06, 0.12, 0, 0.12, 0.18, 0.7, 'dark'), box(0.06, 0.66, 0, 0.12, 0.72, 0.7, 'dark')]
    P.append(box(1.4, 0.1, 0, 1.94, 0.72, 0.7, 'wood', first(panel_tex([(1.46, 0.06, 1.88, 0.3), (1.46, 0.36, 1.88, 0.64)]),
                                                         knob_tex([(1.67, 0.5), (1.67, 0.2)]))))
    P.append(box(0.02, 0.06, 0.7, 1.98, 0.76, 0.75, 'wood', wood_grain('x', 0.14, 11)))
    P.append(box(0.36, 0.16, 0.75, 0.6, 0.3, 0.77, 'dark')); P.append(box(0.45, 0.2, 0.77, 0.51, 0.25, 0.86, 'dark'))
    P.append(box(0.1, 0.2, 0.86, 0.86, 0.25, 1.28, 'black', screen_tex(on, 0.13, 0.83, 0.89, 1.25, 'code')))
    P.append(box(0.25, 0.42, 0.75, 0.75, 0.56, 0.77, 'metal'))                 # keyboard
    P.append(box(1.05, 0.34, 0.75, 1.5, 0.62, 0.775, 'metal'))                 # laptop base
    P.append(box(1.05, 0.31, 0.775, 1.5, 0.34, 1.04, 'metal', screen_tex(on, 1.08, 1.47, 0.8, 1.01, 'tv')))
    P.append(cyl(1.72, 0.3, 0.05, 0.75, 0.86, 'red'))                           # mug
    return P

@item('4a_office_chair', '4A', (1, 1), 1.05, 'R4', 'P2',
      hooks=[H('seat0', 'sit', (0.5, 0.55), (0, 1), 'sit_desk', approach=(0, 1))])
def office_chair(state='default'):
    P = [cyl(0.5, 0.5, 0.3, 0.02, 0.06, 'dark', n=5), cyl(0.5, 0.5, 0.035, 0.06, 0.42, 'metal')]
    P.append(box(0.22, 0.24, 0.42, 0.78, 0.8, 0.5, 'black'))
    P.append(box(0.24, 0.16, 0.5, 0.76, 0.24, 1.05, 'black'))
    return P

def counter_builder(body, top, splash, splash_grid, uppers, sink_dishes=False, mug_shelf=False):
    def b(state='default'):
        P = [box(0, 0.08, 0, 3, 0.58, 0.08, 'black')]
        doors = [(0.04 + i*0.5, 0.12, 0.5 + i*0.5 - 0.04, 0.8) for i in range(6) if not (1.4 <= 0.04 + i*0.5 < 2.1)]
        P.append(box(0, 0.04, 0.08, 3, 0.62, 0.86, body, first(panel_tex(doors), knob_tex([(d[2]-0.06, 0.74) for d in doors]))))
        # oven front
        def oven(face, x, y, z, tone, rc):
            if face == 'front' and 1.55 <= x <= 2.05:
                if abs(z - 0.72) < 1.5/64: return 'grey_lt'
                if 0.2 < z < 0.62 and 1.6 < x < 2.0: return 'ink_2' if z > 0.3 else 'shadow_violet'
                return 2
            return None
        P.append(box(1.5, 0.05, 0.08, 2.1, 0.63, 0.86, 'steel', oven))
        def toptex(face, x, y, z, tone, rc):
            if face == 'top':
                for (bx, by) in ((1.67, 0.22), (1.93, 0.22), (1.67, 0.46), (1.93, 0.46)):
                    d = math.hypot(x-bx, (y-by)*1.0)
                    if 0.05 < d < 0.085: return 'ink_2'
                if 0.32 < x < 0.88 and 0.15 < y < 0.52: return 'grey' if (0.34 < x < 0.86 and 0.17 < y < 0.5) else 'grey_dk'
            return tone
        P.append(box(0, 0.02, 0.86, 3, 0.65, 0.91, top, toptex))
        P.append(box(1.55, 0.04, 0.91, 2.05, 0.1, 1.0, 'steel'))                       # stove back panel
        P.append(box(0, 0, 0.91, 3, 0.03, 1.45, splash, grid_tex(0.1, 0.1, splash_grid)))
        P.append(cyl(0.6, 0.08, 0.02, 0.91, 1.12, 'steel')); P.append(box(0.58, 0.08, 1.08, 0.62, 0.2, 1.12, 'steel'))
        if uppers:
            P.append(box(0, 0, 1.45, 1.45, 0.34, 2.15, body, first(panel_tex([(0.05, 1.5, 0.7, 2.1), (0.75, 1.5, 1.4, 2.1)]),
                                                                      knob_tex([(0.65, 1.56), (0.8, 1.56)]))))
            P.append(box(2.15, 0, 1.45, 3, 0.34, 2.15, body, panel_tex([(2.2, 1.5, 2.95, 2.1)])))
            P.append(box(1.5, 0, 1.6, 2.1, 0.42, 1.75, 'steel'))                     # range hood
            P.append(box(1.62, 0, 1.75, 1.98, 0.22, 2.15, 'steel'))
        if mug_shelf:
            P.append(box(0.1, 0, 1.6, 1.4, 0.24, 1.63, 'wood'))
            for i, m in enumerate(('orange', 'turq', 'purple', 'lime', 'red')):
                P.append(cyl(0.2 + i*0.25, 0.12, 0.05, 1.63, 1.72, m, n=8))
            P.append(box(2.2, 0, 1.6, 2.95, 0.24, 1.63, 'wood'))
            P.append(box(2.25, 0.02, 1.63, 2.55, 0.2, 1.9, 'cream')); P.append(box(2.6, 0.04, 1.63, 2.9, 0.2, 1.8, 'orange'))
        P.append(box(2.35, 0.1, 0.91, 2.85, 0.45, 1.2, 'steel', screen_tex(False, 2.4, 2.65, 0.95, 1.16)))   # microwave
        if sink_dishes:
            for i, (dx, dy, m) in enumerate(((0.45, 0.3, 'white'), (0.62, 0.35, 'orange'), (0.52, 0.42, 'turq'), (0.75, 0.25, 'white'))):
                P.append(cyl(dx, dy, 0.07, 0.86, 0.95 + i*0.025, m, n=10))
            P.append(cyl(1.25, 0.35, 0.06, 0.91, 1.08, 'purple', n=8))
        return P
    return b
item('4a_kitchen_counter', '4A', (3, 1), 2.15, 'R4', 'P0',
     notes='3 modules (sink, stove+oven+hood, microwave); green tile backsplash; upper cabinets',
     hooks=[H('cook', 'cook', (1.8, 1.2), (0, -1), 'cook_stove', approach=(1, 1)),
            H('sink', 'use', (0.6, 1.2), (0, -1), 'wash_dishes', approach=(0, 1)),
            H('counter', 'pour_drink', (2.6, 1.2), (0, -1), 'pour_drink', approach=(2, 1))])(
     counter_builder('wood', 'cream', 'green', 'tile_green_dk', True))
item('4b_kitchen_counter', '4B', (3, 1), 2.0, 'R4', 'P0', notes='4B kitchen: orange tile backsplash, open mug shelves, dishes piled in the sink',
     hooks=[H('cook', 'cook', (1.8, 1.2), (0, -1), 'cook_stove', approach=(1, 1)),
            H('sink', 'use', (0.6, 1.2), (0, -1), 'wash_dishes', approach=(0, 1))])(
     counter_builder('cream', 'wood_lt', 'orange', 'ccf_amber', False, sink_dishes=True, mug_shelf=True))

@item('4a_kitchen_island', '4A', (2, 1), 0.92, 'R4', 'P0',
      hooks=[H('stool0', 'perch', (0.5, 1.5), (0, -1), 'sit_stool', approach=(0, 1), z=0.75),
             H('stool1', 'perch', (1.5, 1.5), (0, -1), 'sit_stool', approach=(1, 1), z=0.75),
             H('surface0', 'place_item', (1.0, 0.5), (0, 1), tags=['takeout'], z=0.92)])
def island_4a(state='default'):
    P = [box(0.08, 0.12, 0, 1.92, 0.7, 0.08, 'black'),
         box(0.05, 0.08, 0.08, 1.95, 0.72, 0.86, 'wood_dk', first(panel_tex([(0.1, 0.12, 0.95, 0.8), (1.05, 0.12, 1.9, 0.8)]), wood_grain('x', 0.15, 4))),
         box(0, 0.04, 0.86, 2, 0.98, 0.92, 'wood_lt', wood_grain('x', 0.1, 6))]
    P.append(cyl(1.55, 0.4, 0.12, 0.92, 0.98, 'white')); P.append(cyl(1.5, 0.37, 0.05, 0.98, 1.03, 'red', n=8))
    P.append(cyl(1.62, 0.43, 0.05, 0.98, 1.02, 'lime', n=8))
    return P

@item('4a_bar_stool', '4A', (1, 1), 0.78, 'R1', 'P0', notes='pair with island stool hooks',
      hooks=[H('seat0', 'perch', (0.5, 0.5), (0, -1), 'sit_stool', z=0.75)])
def stool(state='default'):
    return [cyl(0.5, 0.5, 0.17, 0, 0.03, 'steel', n=12), cyl(0.5, 0.5, 0.03, 0.03, 0.7, 'steel', n=8),
            cyl(0.5, 0.5, 0.11, 0.3, 0.32, 'steel', n=10), cyl(0.5, 0.5, 0.18, 0.7, 0.78, 'leather', n=12)]
ITEMS['4b_bar_stool'] = dict(ITEMS['4a_bar_stool'], id='4b_bar_stool', location='4B',
                             build=lambda state='default': [cyl(0.5, 0.5, 0.17, 0, 0.03, 'dark', n=12), cyl(0.5, 0.5, 0.03, 0.03, 0.78, 'dark', n=8),
                                                            cyl(0.5, 0.5, 0.18, 0.78, 0.86, 'turq', n=12)])

def fridge_builder(body, magnets=0):
    def b(state='closed'):
        op = state == 'open'
        def front(face, x, y, z, tone, rc):
            if face != 'front': return tone
            if op:
                if 0.14 < x < 0.86 and 0.08 < z < 1.74:
                    if any(abs(z - s) < 1.5/64 for s in (0.5, 0.9, 1.25, 1.3)): return 'white_hi'
                    k = int(x*12) + int(z*7)*13
                    if hsh(k, 3) < 0.35 and (z % 0.4) < 0.2: return ['marker_red', 'lime', 'orange', 'comic_blue', 'cafe_cream'][int(hsh(k, 4)*5)]
                    return 'lamp_warm' if z > 1.3 else 'cafe_cream'
                return tone
            if abs(z - 1.22) < 1/64: return 3
            if magnets:
                k = int(x*14) * 31 + int(z*10)
                if 0.45 < z < 1.65 and hsh(k, 7) < magnets and (x*14) % 1 < 0.6 and (z*10) % 1 < 0.7:
                    return ['marker_red', '4b_turquoise', '4b_orange', '4b_purple', '4b_lime', 'white_hi', 'comic_yellow'][int(hsh(k, 8)*7)]
            return tone
        P = [box(0.08, 0.1, 0, 0.92, 0.84, 1.8, body, front)]
        if not op:
            P.append(box(0.8, 0.84, 0.95, 0.84, 0.88, 1.15, 'steel')); P.append(box(0.8, 0.84, 1.3, 0.84, 0.88, 1.55, 'steel'))
        else:
            slab = rot_poly([(0.08, 0.84), (0.92, 0.84), (0.92, 0.9), (0.08, 0.9)], 0.92, 0.9, math.radians(-100))
            P.append(Prism(slab, 0.02, 1.78, body))
        return P
    return b
item('4a_fridge', '4A', (1, 1), 1.8, 'R4', 'P0', states=('closed', 'open'),
     hooks=[H('use', 'use', (0.5, 1.3), (0, -1), 'open_fridge', approach=(0, 1), tags=['food', 'drinks'])])(fridge_builder('white'))
item('4b_fridge', '4B', (1, 1), 1.8, 'R4', 'P1', states=('closed', 'open'), notes='covered in magnets and photos',
     hooks=[H('use', 'use', (0.5, 1.3), (0, -1), 'open_fridge', approach=(0, 1), tags=['food', 'wine'])])(fridge_builder('white', 0.55))

def board_tex(state):
    seed = {'blank': 0, 'equations_a': 1, 'equations_b': 2, 'equations_c': 3}[state]
    syms = 'ħψλπΣ∫=+-()^/0123456789EMCXYZ'
    lines_ = []
    if seed:
        import random
        R = random.Random(seed*97)
        for li in range(6):
            s = ''.join(R.choice(syms) for _ in range(R.randint(5, 11)))
            lines_.append((s, R.choice(['marker_blue', 'marker_blue', 'marker_red', 'marker_green', 'ink_2']), R.randint(0, 4)))
    def t(face, x, y, z, tone, rc):
        if face != 'front': return tone
        if x < 0.11 or x > 0.89 or z < 0.79 or z > 1.81: return 'grey'
        if not seed: return 'white_hi' if (x - z*0.7) % 0.6 < 0.04 else 'paper'
        c = int((x - 0.13)*64); r = int((1.78 - z)*64)
        li, rr = divmod(r, 7)
        if li < len(lines_) and rr < 5:
            s, col, ind = lines_[li]
            if text_px(s, c - ind, rr): return col
        if seed == 2 and abs(math.hypot(x-0.7, z-1.0) - 0.08) < 1/64: return 'marker_red'
        return 'paper'
    return t
@item('4a_whiteboard', '4A', (1, 1), 1.9, 'R4', 'P1', states=('blank', 'equations_a', 'equations_b', 'equations_c'),
      notes='free-standing rolling whiteboard; equations are procedural glyph soup (no real text)',
      hooks=[H('write', 'write', (0.5, 1.25), (0, -1), 'write_whiteboard', approach=(0, 1)),
             H('look', 'look', (0.5, 1.7), (0, -1), 'look_whiteboard', approach=(0, 1))])
def whiteboard(state='blank'):
    P = []
    for x in (0.06, 0.88):
        P.append(box(x, 0.3, 0, x+0.06, 0.7, 0.04, 'steel'))
        P.append(box(x+0.01, 0.47, 0.04, x+0.05, 0.53, 1.88, 'steel'))
    P.append(box(0.1, 0.48, 0.76, 0.9, 0.52, 1.84, 'white', board_tex(state)))
    P.append(box(0.12, 0.52, 0.74, 0.88, 0.58, 0.77, 'steel'))
    P.append(box(0.3, 0.53, 0.77, 0.36, 0.56, 0.79, 'blue')); P.append(box(0.4, 0.53, 0.77, 0.46, 0.56, 0.79, 'red'))
    return P

def book_row(x0, x1, y0, y1, z0, seed, hmax=0.3):
    out = []; x = x0; k = 0
    pal = ['comic_blue', 'comic_red', 'comic_yellow', 'marker_green', '4b_purple', 'paper', 'leather', 'ink_2', 'cafe_teal', '4b_orange']
    while x < x1 - 0.02:
        w = 0.12 + 0.2*hsh(seed, k); w = min(w, x1 - x)
        h = hmax*(0.7 + 0.3*hsh(seed, k, 1)); k += 1
        cols = [pal[int(hsh(seed, k, j)*len(pal))] for j in range(8)]
        def t(face, xx, yy, zz, tone, rc, x=x, cols=cols, h=h):
            if face == 'front':
                i = int((xx - x) / 0.035)
                if ((xx - x) % 0.035) < 1/64: return 'ink_2'
                if abs(zz - (z0 + h*0.75)) < 1/64: return 'lamp_warm'
                return cols[i % 8]
            if face == 'top': return 'paper'
            return None
        if hsh(seed, k, 5) < 0.12:     # collectible figure instead of books
            out.append(cyl(x + w/2, (y0+y1)/2, 0.04, z0, z0+0.14, 'red' if k % 2 else 'blue', n=8))
            out.append(cyl(x + w/2, (y0+y1)/2, 0.03, z0+0.14, z0+0.2, 'skin', n=8))
        else:
            out.append(box(x, y0, z0, x+w, y1, z0+h, 'cardboard', t))
        x += w + 0.01
    return out
@item('4a_bookcase_collectibles', '4A', (2, 1), 2.0, 'R4', 'P1', notes='books + boxed collectibles + figures; against a back wall',
      hooks=[H('browse', 'browse', (1.0, 1.25), (0, -1), 'browse_shelf', approach=(0, 1))])
def bookcase(state='default'):
    P = [box(0.02, 0.05, 0, 1.98, 0.1, 2.0, 'wood_dk'), box(0.02, 0.05, 0, 0.08, 0.55, 2.0, 'wood'),
         box(1.92, 0.05, 0, 1.98, 0.55, 2.0, 'wood'), box(0.02, 0.05, 1.95, 1.98, 0.55, 2.0, 'wood'),
         box(0.02, 0.05, 0, 1.98, 0.55, 0.1, 'wood')]
    for i, z in enumerate((0.1, 0.55, 1.0, 1.45)):
        if i: P.append(box(0.08, 0.05, z - 0.03, 1.92, 0.55, z, 'wood'))
        P += book_row(0.1, 1.9, 0.12, 0.48, z, 20 + i, 0.36)
    # boxed collectible on top
    def win(face, x, y, z, tone, rc):
        if face == 'front' and 0.36 < x < 0.62 and 2.05 < z < 2.27: return 'screen_glow' if (x+z) % 0.1 > 0.02 else 'white_hi'
        return tone
    P.append(box(0.3, 0.15, 2.0, 0.68, 0.4, 2.32, 'red', win))
    P.append(cyl(1.4, 0.3, 0.07, 2.0, 2.06, 'dark')); P.append(cyl(1.4, 0.3, 0.035, 2.06, 2.25, 'blue', n=8))
    return P

@item('4a_telescope', '4A', (1, 1), 1.6, 'R8', 'P1', notes='tube points to the item\'s back (toward the window)',
      hooks=[H('look', 'look', (0.5, 0.95), (0, -1), 'look_telescope', approach=(0, 1))])
def telescope(state='default'):
    P = []
    top = (0.5, 0.5, 1.05)
    for a in (90, 210, 330):
        f = (0.5 + 0.3*math.cos(math.radians(a)), 0.5 + 0.3*math.sin(math.radians(a)), 0.0)
        P += rod(f, top, 0.018, 'dark', n=10)
    P.append(cyl(0.5, 0.5, 0.05, 1.0, 1.1, 'dark', n=8))
    P += rod((0.5, 0.72, 1.02), (0.5, 0.08, 1.48), 0.07, 'white', n=12)
    P += rod((0.5, 0.78, 0.98), (0.5, 0.72, 1.02), 0.03, 'dark', n=2)
    P.append(cyl(0.5, 0.08, 0.085, 1.46, 1.52, 'dark', n=10))
    return P

def flag_tex(face, x, y, z, tone, rc):
    if face != 'front': return None
    u = (x - 0.15) / 1.7; v = (2.05 - z) / 0.85
    if v < 0.06 or v > 0.94 or u < 0.03 or u > 0.97: return 'comic_yellow' if (int(x*64) + int(z*64)) % 6 < 3 else 'tape_yellow_dk'
    px = (x - 0.6)*64; pz = (z - 1.62)*64
    d = math.hypot(px, pz)
    ring = abs(math.hypot(px, pz*3.2) - 16) < 1.4 and not (d < 9.5 and pz > -1)
    if ring: return 'comic_red'
    if d < 9.5: return 'comic_yellow' if px + pz < 4 else 'tape_yellow_dk'
    for (sx, sz) in ((1.35, 1.85), (1.6, 1.7), (1.25, 1.45), (1.7, 1.42), (1.48, 1.27)):
        if abs((x-sx)*64) + abs((z-sz)*64) < 2.2: return 'white_hi'
    if 0.78 < v < 0.94: return 'comic_red'
    return 'comic_blue'
@item('4a_flag_banner', '4A', (2, 1), 2.1, 'R4', 'P1', blocks=False, mount='wall', sort_bias=-1, shadow=False,
      notes='original banner: ringed planet + stars on blue with a red stripe and yellow border (no logos). Hangs above the couch on the back wall.')
def flag(state='default'):
    return [box(0.12, 0.0, 2.06, 1.88, 0.03, 2.09, 'wood_dk'), box(0.15, 0.0, 1.2, 1.85, 0.02, 2.05, 'blue', flag_tex)]

@item('4a_floor_lamp', '4A', (1, 1), 1.7, 'R8', 'P1', states=('on', 'off'),
      hooks=[H('switch', 'use', (0.5, 0.95), (0, -1), 'use_switch', approach=(0, 1))])
def lamp_4a(state='on'):
    sh = 'lamp' if state == 'on' else 'cream'
    return [cyl(0.5, 0.5, 0.16, 0, 0.04, 'dark', n=12), cyl(0.5, 0.5, 0.022, 0.04, 1.4, 'brass', n=6),
            cyl(0.5, 0.5, 0.21, 1.36, 1.7, sh, n=14)]

def rug_tex(kind):
    def t(face, x, y, z, tone, rc):
        if face != 'top': return None
        if kind == '4a':
            fx, fy = 2.8, 1.8
            ex = min(x - 0.1, fx + 0.1 - x, y - 0.1, fy + 0.1 - y)
            if ex < 0.08: return 'leather_dk'
            if ex < 0.12: return 'lamp_warm' if (int(x*16) + int(y*16)) % 2 else 'leather_dk'
            d = abs(x - 1.5) + abs(y - 1.0)*1.4
            if abs(d - 0.5) < 0.04 or abs(d - 0.25) < 0.04: return 'lamp_warm'
            if d < 0.12: return 'comic_blue'
            return 'ccf_booth_red' if ex < 0.25 else 'leather'
        # 4b stripes
        cols = ['4b_orange', '4b_purple', '4b_turquoise', 'paper', '4b_lime', '4b_purple']
        if min(x-0.08, 1.92-x, y-0.08, 1.92-y) < 0.05: return 'paper' if (int(x*32)+int(y*32)) % 2 else 'grey_lt'
        return cols[int((x + y)*3) % 6]
    return t
@item('4a_rug', '4A', (3, 2), 0.012, 'R2', 'P1', blocks=False, layer='floor_decal', shadow=False, outline='soft')
def rug_4a(state='default'):
    return [box(0.1, 0.1, 0, 2.9, 1.9, 0.012, 'leather', rug_tex('4a'))]
@item('4b_rug', '4B', (2, 2), 0.012, 'R2', 'P1', blocks=False, layer='floor_decal', shadow=False, outline='soft')
def rug_4b(state='default'):
    return [box(0.08, 0.08, 0, 1.92, 1.92, 0.012, 'orange', rug_tex('4b'))]

@item('4a_takeout_set', '4A', (1, 1), 0.16, 'R1', 'P2', blocks=False, notes='placed on a surface hook (z offset); original generic boxes, red band, no logos',
      hooks=[H('pickup', 'pickup', (0.5, 0.5), (0, 1), 'eat_takeout', tags=['food'])])
def takeout(state='default'):
    def band(face, x, y, z, tone, rc):
        if face != 'top' and 0.055 < (z % 0.13) < 0.075: return 'marker_red'
        return tone
    P = []
    for (cx, cy, r) in ((0.35, 0.4, 0.085), (0.6, 0.35, 0.08), (0.48, 0.62, 0.09)):
        P.append(Prism([(cx-r*0.8, cy-r), (cx+r*0.8, cy-r), (cx+r, cy+r*0.8), (cx-r, cy+r*0.8)], 0, 0.13, 'white', band))
    P.append(box(0.66, 0.55, 0.0, 0.69, 0.85, 0.02, 'wood_lt')); P.append(box(0.71, 0.55, 0.0, 0.74, 0.85, 0.02, 'wood_lt'))
    return P

@item('4a_dna_model', '4A', (1, 1), 1.25, 'R1', 'P2', blocks=False, notes='desktop / floor double-helix model, coloured base pairs')
def dna(state='default'):
    P = [cyl(0.5, 0.5, 0.14, 0, 0.05, 'dark', n=10), cyl(0.5, 0.5, 0.015, 0.05, 1.2, 'metal', n=6)]
    for k in range(14):
        a = k*0.55; z = 0.12 + k*0.075
        for s, m in ((0, 'red'), (math.pi, 'blue')):
            P.append(cyl(0.5 + 0.13*math.cos(a+s), 0.5 + 0.13*math.sin(a+s), 0.03, z, z+0.05, m, n=6))
    return P

# ================================================================== landing / hall
def elev_tex(face, x, y, z, tone, rc):
    if face != 'front': return None
    # out-of-order sign (original wording, hand-lettered).  v2: bigger card, 2x lettering so it reads at 1x
    if 0.54 <= x <= 1.46 and 1.04 <= z <= 1.62:
        c = int((x - 0.54)*64); r = int((1.62 - z)*64)
        W_ = int(0.92*64)
        for txt, row0, col, sc in (('OUT OF', 3, 'ink', 2), ('ORDER', 15, 'marker_red', 2), ('USE STAIRS', 28, 'ink_2', 1)):
            w = text_w(txt)*sc; off = (W_ - w)//2
            if (c - off) >= 0 and (r - row0) >= 0 and text_px(txt, (c - off)//sc, (r - row0)//sc): return col
        if r <= 0 or c <= 0 or c >= W_ - 1 or z < 1.04 + 1/64: return 'grey_dk'
        if abs(z - 1.25) < 0.5/64 and 0.62 < x < 1.38: return 'grey_lt'
        return 'paper' if c > 2 else 'grey_lt'
    # caution tape X across the doors (two bands)
    if 0.28 <= x <= 1.72 and 0.15 <= z <= 2.0:
        for sgn in (1, -1):
            u = x - 1.0; v = z - 1.07
            d = (v - sgn*0.62*u)
            if abs(d) < 0.075:
                along = u + sgn*v*0.62
                return 'ink' if (along*64) % 12 < 4 else 'tape_yellow'
            if abs(abs(d) - 0.085) < 0.5/64: return 'tape_yellow_dk'
    if 0.3 <= x <= 1.7 and z <= 2.1:
        if abs(x - 1.0) < 1/64: return 'ink_2'
        if abs(x - 1.0) < 2/64: return 'grey_lt'
        return 1 if x < 1.0 else 2
    # floor indicator above the doors + call buttons
    if abs(x - 1.0) < 0.22 and 2.15 < z < 2.33:
        d = math.hypot((x-1.0)/0.22, (z-2.16)/0.17)
        if d < 1:
            if abs((x - 1.0) + (z - 2.16)*0.4) < 0.01 and d < 0.85: return 'ink'
            return 'ccf_amber' if d > 0.8 else 'lamp_warm'
    if 1.8 <= x <= 1.92 and 1.0 <= z <= 1.3:
        if abs(z - 1.2) < 0.03 or abs(z - 1.1) < 0.03: return 'grey_dk' if abs(x - 1.86) < 0.03 else 'grey'
        return 'grey'
    return None
@item('hall_elevator_broken', 'hall4', (2, 1), 2.4, 'R4', 'P0', blocks=True, mount='wall', sort_bias=-1,
      notes='wall-mounted elevator doors with caution-tape X and an original hand-lettered OUT OF ORDER / USE STAIRS sign',
      hooks=[H('look', 'look', (1.0, 0.9), (0, -1), 'look_elevator', approach=(0, 0), tags=['running_gag']),
             H('call_button', 'use', (1.85, 0.8), (0, -1), 'press_button', approach=(1, 0))])
def elevator(state='default'):
    return [box(0.18, 0.0, 0, 1.82, 0.1, 2.4, 'steel', elev_tex), box(0.18, 0.1, 0, 1.82, 0.13, 0.02, 'dark')]

def stair_tex(face, x, y, z, tone, rc):
    if face in ('left', 'right') and z < -0.005: return 'clear'
    if face == 'front':
        if (z % (1/6)) > (1/6 - 1.2/64): return 'wood_hi'   # nosing highlight
        return tone
    return None
@item('hall_stair_flight', 'hall4', (2, 3), 0.0, 'R4', 'P0', blocks=False, sort_bias=-0.5, shadow=False,
      notes='top of the flight going DOWN toward the camera; 0.5 m drop per tile (3 visual risers per tile); below-floor side faces are clipped so the neighbouring floor reads over them',
      hooks=[H('climb_lane_down', 'climb_lane_down', (1.0, 0.15), (0, 1), 'walk_stairs_down', approach=(0, -1)),
             H('climb_lane_up', 'climb_lane_up', (1.0, 2.85), (0, -1), 'walk_stairs_up')])
def stairs(state='default'):
    P = []
    for k in range(9):
        P.append(box(0.0, k/3, -1.6, 2.0, (k+1)/3, -(k+1)/6, 'hall', stair_tex))
    return P

@item('hall_stair_rail', 'hall4', (3, 1), 0.95, 'R4', 'P0', blocks=True, notes='guard rail along the open side of the stairwell')
def rail(state='default'):
    P = [box(0.02, 0.02, 0.88, 2.98, 0.1, 0.95, 'wood')]
    for x in (0.02, 1.47, 2.9):
        P.append(box(x, 0.02, 0, x+0.08, 0.1, 0.88, 'wood_dk'))
    x = 0.2
    while x < 2.85:
        if not (1.4 < x < 1.6): P.append(box(x, 0.04, 0.05, x+0.025, 0.07, 0.88, 'paint_wh'))
        x += 0.15
    P.append(box(0.02, 0.02, 0.0, 2.98, 0.1, 0.05, 'wood_dk'))
    return P

# ================================================================== 4B
@item('4b_couch', '4B', (3, 1), 0.82, 'R4', 'P0', notes='cream couch, rolled arms, orange/turquoise/purple throw pillows and a lime throw',
      hooks=[H('seat0', 'sit', (0.66, 0.6), (0, 1), 'sit_couch', approach=(0, 1)),
             H('seat1', 'sit', (1.5, 0.6), (0, 1), 'sit_couch', approach=(1, 1)),
             H('seat2', 'sit', (2.34, 0.6), (0, 1), 'sit_couch', approach=(2, 1), tags=['penny_spot']),
             H('armrest_l', 'perch', (0.12, 0.55), (0, 1), 'perch_armrest', approach=(0, 1))])
def couch_4b(state='default'):
    P = []
    for x in (0.12, 2.82):
        for y in (0.15, 0.82): P.append(cyl(x+0.03, y+0.03, 0.035, 0, 0.1, 'brass', n=6))
    P.append(box(0.05, 0.1, 0.1, 2.95, 0.96, 0.3, 'cream'))
    P.append(box(0.24, 0.32, 0.3, 2.76, 0.96, 0.44, 'cream', cushion_tex((1.08, 1.92))))
    P.append(box(0.05, 0.06, 0.3, 2.95, 0.3, 0.76, 'cream'))
    for x0, x1 in ((0.0, 0.26), (2.74, 3.0)):
        P.append(box(x0, 0.08, 0.05, x1, 0.98, 0.52, 'cream'))
        P.append(cyl((x0+x1)/2, 0.53, 0.14, 0.52, 0.6, 'cream', ry=0.45, n=12))
    def stripes(face, x, y, z, tone, rc):
        return 'paper' if ((x*64 + (z*64 if face != 'top' else y*64)) % 10) < 2 else tone
    P.append(box(0.3, 0.3, 0.44, 0.62, 0.46, 0.74, 'orange'))
    P.append(box(0.65, 0.32, 0.44, 0.93, 0.47, 0.7, 'turq'))
    P.append(box(2.3, 0.3, 0.44, 2.66, 0.46, 0.73, 'purple', stripes))
    # lime throw draped over the back + right side of the seat
    P.append(box(1.6, 0.03, 0.62, 2.45, 0.33, 0.79, 'lime', stripes))
    P.append(box(1.75, 0.32, 0.44, 2.3, 0.85, 0.47, 'lime', stripes))
    return P

@item('4b_coffee_table', '4B', (2, 1), 0.42, 'R4', 'P1', notes='painted turquoise legs, magazines, nail polish, a pizza box',
      hooks=[H('surface0', 'place_item', (0.6, 0.5), (0, 1), tags=['drinks', 'magazines'], z=0.42)])
def coffee_4b(state='default'):
    P = [box(x, y, 0, x+0.07, y+0.07, 0.36, 'turq') for x in (0.15, 1.78) for y in (0.22, 0.72)]
    P.append(box(0.1, 0.16, 0.36, 1.9, 0.86, 0.42, 'wood_lt', wood_grain('x', 0.12, 9)))
    P.append(box(0.25, 0.3, 0.42, 0.65, 0.6, 0.44, 'purple')); P.append(box(0.3, 0.38, 0.44, 0.7, 0.66, 0.455, 'orange'))
    for i, m in enumerate(('red', 'purple', 'turq')):
        P.append(cyl(1.0 + i*0.08, 0.35, 0.018, 0.42, 0.48, m, n=6))
    def pz(face, x, y, z, tone, rc):
        return 'marker_red' if face != 'top' and abs(z - 0.45) < 1/64 else tone
    P.append(box(1.2, 0.4, 0.42, 1.7, 0.82, 0.48, 'cardboard', pz))
    return P

@item('4b_kitchen_bar', '4B', (2, 1), 1.02, 'R4', 'P0', notes='breakfast bar with turquoise front panel; stools on the front, Penny pours wine from behind',
      hooks=[H('stool0', 'perch', (0.5, 1.5), (0, -1), 'sit_stool', approach=(0, 1), z=0.86),
             H('stool1', 'perch', (1.5, 1.5), (0, -1), 'sit_stool', approach=(1, 1), z=0.86),
             H('pour_wine', 'pour_drink', (1.0, -0.35), (0, 1), 'pour_wine', approach=(1, -1), tags=['wine']),
             H('surface0', 'place_item', (1.0, 0.5), (0, 1), tags=['wine'], z=1.02)])
def bar_4b(state='default'):
    P = [box(0.05, 0.1, 0, 1.95, 0.7, 0.96, 'turq', first(panel_tex([(0.12, 0.1, 0.95, 0.88), (1.05, 0.1, 1.88, 0.88)]))),
         box(0.0, 0.05, 0.96, 2.0, 0.98, 1.02, 'wood', wood_grain('x', 0.1, 13))]
    P.append(cyl(0.3, 0.4, 0.12, 1.02, 1.07, 'orange', n=12)); P.append(cyl(0.27, 0.38, 0.05, 1.07, 1.11, 'lime', n=8))
    P.append(box(1.55, 0.25, 1.02, 1.85, 0.6, 1.05, 'paper')); P.append(box(1.6, 0.3, 1.05, 1.82, 0.55, 1.06, 'blue'))
    return P

@item('4b_wine_set', '4B', (1, 1), 0.36, 'R1', 'P0', blocks=False, notes='wine bottle + 2 glasses (one poured); place on a surface hook',
      hooks=[H('wine_glass', 'pickup', (0.6, 0.6), (0, 1), 'wine_sip', tags=['wine']),
             H('bottle', 'pour_drink', (0.35, 0.4), (0, 1), 'pour_wine', tags=['wine'])])
def wine(state='default'):
    def lab(face, x, y, z, tone, rc):
        return 'paper' if face != 'top' and 0.1 < z < 0.2 else tone
    P = [cyl(0.35, 0.4, 0.045, 0, 0.24, 'bottle', n=10, tex=lab), cyl(0.35, 0.4, 0.018, 0.24, 0.34, 'bottle', n=6),
         cyl(0.35, 0.4, 0.02, 0.34, 0.36, 'red', n=6)]
    for (gx, gy, full) in ((0.62, 0.6, True), (0.68, 0.32, False)):
        P.append(cyl(gx, gy, 0.035, 0, 0.01, 'glass', n=8)); P.append(cyl(gx, gy, 0.008, 0.01, 0.1, 'glass', n=4))
        def wt(face, x, y, z, tone, rc, full=full):
            if full and z < 0.15: return 'marker_red' if face == 'top' else 'ccf_booth_red'
            return 'white_hi' if face == 'top' else tone
        P.append(cyl(gx, gy, 0.04, 0.1, 0.19 if full else 0.18, 'glass', n=10, tex=wt))
    return P

@item('4b_laundry_pile', '4B', (1, 1), 0.38, 'R1', 'P0', blocks=True, notes='clothes clutter heap + a stray boot',
      hooks=[H('pickup', 'pickup', (0.5, 0.95), (0, -1), 'pickup_clothes', approach=(0, 1), tags=['laundry'])])
def laundry(state='default'):
    P = []
    cols = ['pink', 'blue', 'orange', 'white', 'purple', 'lime', 'turq', 'red', 'cream']
    import random
    R = random.Random(7)
    for k in range(22):
        cx, cy = 0.5 + R.uniform(-0.3, 0.3), 0.5 + R.uniform(-0.28, 0.28)
        dz = 0.4*(1 - math.hypot(cx-0.5, cy-0.5)/0.5)
        w, d = R.uniform(0.2, 0.4), R.uniform(0.14, 0.3)
        z1 = max(0.04, dz*R.uniform(0.6, 1.0))
        P.append(Prism(rot_poly([(cx-w/2, cy-d/2), (cx+w/2, cy-d/2), (cx+w/2, cy+d/2), (cx-w/2, cy+d/2)], cx, cy, R.uniform(0, 3)),
                       z1 - R.uniform(0.04, 0.09), z1, cols[k % len(cols)]))
    P.append(box(0.06, 0.8, 0, 0.34, 0.92, 0.07, 'wood_dk')); P.append(box(0.06, 0.8, 0.07, 0.17, 0.92, 0.3, 'wood_dk'))
    return P
MAT['pink'] = ('white_hi', 'paper', 'grey_lt', 'grey')   # overridden in build_env with Penny pink if available

@item('4b_dining_table_cluttered', '4B', (2, 2), 1.06, 'R4', 'P1',
      notes='table buried in mail, a laundry basket and shopping bags; chair at the back with a sweater over it (2x2 incl. chair)',
      hooks=[H('chair0', 'sit', (0.6, 0.75), (0, 1), 'sit_chair', approach=(0, 0)),
             H('surface0', 'place_item', (1.4, 1.4), (0, 1), tags=['mail', 'laundry'], z=0.75)])
def dining_4b(state='default'):
    Y = 0.9
    P = [box(x, y + Y, 0, x+0.06, y + Y + 0.06, 0.7, 'wood_dk') for x in (0.1, 1.84) for y in (0.12, 0.82)]
    P.append(box(0.05, 0.08 + Y, 0.7, 1.95, 0.92 + Y, 0.75, 'wood_lt', wood_grain('x', 0.12, 21)))
    def basket(face, x, y, z, tone, rc):
        return 3 if face != 'top' and (int(x*64 + y*64) + int(z*64)) % 4 == 0 else tone
    P.append(box(0.15, 0.25 + Y, 0.75, 0.75, 0.75 + Y, 1.0, 'cardboard', basket))
    for k, m in enumerate(('pink', 'blue', 'purple', 'white')):
        P.append(box(0.2 + 0.12*k, 0.3 + 0.08*(k % 2) + Y, 0.95, 0.4 + 0.12*k, 0.6 + 0.05*k + Y, 1.04 + 0.02*k, m))
    P.append(box(1.0, 0.3 + Y, 0.75, 1.4, 0.6 + Y, 0.8, 'paper')); P.append(box(1.05, 0.35 + Y, 0.8, 1.35, 0.62 + Y, 0.83, 'cream'))
    P.append(box(1.55, 0.2 + Y, 0.75, 1.85, 0.4 + Y, 1.05, 'orange'))
    # chair behind the table, sweater over its back
    P.append(box(0.35, 0.6, 0, 0.85, 0.95, 0.45, 'wood_dk')); P.append(box(0.35, 0.58, 0.45, 0.85, 0.65, 0.95, 'wood_dk'))
    P.append(box(0.33, 0.56, 0.6, 0.87, 0.67, 0.95, 'purple'))
    return P
item('4b_armchair_patterned', '4B', (1, 1), 0.92, 'R8', 'P1', notes='purple armchair with lime polka-dot pattern',
     hooks=[H('seat0', 'sit', (0.5, 0.62), (0, 1), 'sit_chair', approach=(0, 1))])(
     armchair('purple', lambda f, x, y, z, t, rc: ('4b_lime' if (t < 2 and (x*64 + (y*64 if f in ('left', 'right') else 0)) % 10 < 2 and ((z if f != 'top' else y)*64) % 10 < 2) else t)))

@item('4b_floor_lamp', '4B', (1, 1), 1.6, 'R8', 'P1', states=('on', 'off'), notes='stained-glass style shade in the 4B sub-palette',
      hooks=[H('switch', 'use', (0.5, 0.95), (0, -1), 'use_switch', approach=(0, 1))])
def lamp_4b(state='on'):
    def shade(face, x, y, z, tone, rc):
        cols = ['4b_turquoise', '4b_orange', '4b_purple', '4b_lime']
        if face == 'top': return 'lamp_warm' if state == 'on' else 'cafe_cream'
        if abs(z - 1.35) < 1/64 or abs(z - 1.58) < 1/64: return 'ink_2'
        k = int(math.atan2(y-0.5, x-0.5)*4) % 4
        return cols[k] if state == 'on' or tone < 2 else 'shadow_violet'
    return [cyl(0.5, 0.5, 0.15, 0, 0.04, 'brass', n=12), cyl(0.5, 0.5, 0.02, 0.04, 1.35, 'brass', n=6),
            cyl(0.5, 0.5, 0.22, 1.32, 1.6, 'lamp', n=14, tex=shade)]

@item('4b_plant', '4B', (1, 1), 1.0, 'R1', 'P2', notes='slightly neglected potted plant')
def plant(state='default'):
    P = [cyl(0.5, 0.5, 0.15, 0, 0.3, 'orange', n=10)]
    import random
    R = random.Random(3)
    for k in range(9):
        a = R.uniform(0, 6.28); r = R.uniform(0.02, 0.2)
        z0 = 0.3 + R.uniform(0, 0.45)
        P.append(cyl(0.5 + r*math.cos(a), 0.5 + r*math.sin(a), R.uniform(0.07, 0.13), z0, z0 + R.uniform(0.12, 0.25),
                     'plant' if k % 3 else 'lime', n=7))
    return P
