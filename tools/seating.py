"""Seated placement (single source of truth for the static scene renders, the world export and -- via the exported
scene.json fields -- the harness sim + live viewer).

A sit/perch hook is placed like this:
  * seat point  = hook pos (+ optional item-data 'seat_off' [dx, dy] in canonical metres)
  * seat_z      = top of the seat surface under the seat point, measured from the item prisms of the whole location
                  (highest prism top within 1.05 of the hook's base z), or the item-data override 'seat_z'
  * sprite      = characters/<cid>/chr_<cid>_sit.png, frame of the hook's facing; its frame.seat anchor (butt contact
                  point, tools/v2/sit_v2.py) is drawn at scr(seat x, seat y, seat_z)
  * depth key   = floor(x) + floor(y) + 1.5 (above every slice of the seat's own tile), raised past any later slice
                  that would otherwise cover the sitter with geometry that is actually behind it
  * occluder    = per hook, the item pixels that are really IN FRONT of a sitter (chair backs / booth backs / armrests
                  facing the camera) but sort below the sitter's key; redrawn on top only while the hook is occupied.
Pixel test: at one screen pixel two surfaces satisfy z_a - z_b = (c_a - c_b) / 2 with c = x + y, so an item pixel hides
the sitter iff its hit point lies nearer the camera (c > c_sitter) and rises above the cushion (z > seat_z)."""
import math, os, json
import numpy as np
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAST = ['sheldon', 'leonard', 'penny', 'howard', 'raj', 'bernadette', 'amy']
DIRS8 = ('S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE')
SIT_TYPES = ('sit', 'perch')
BODY_C = 0.12          # sitter's camera-facing body surface, in c = x + y, beyond the seat point
ABOVE = 0.04           # item pixels must rise this far above the seat surface to occlude
DEFAULT_SEAT = 0.45

def scr(x, y, z=0.0): return (x - y) * 64.0, (x + y) * 32.0 - z * 64.0

# ------------------------------------------------------------------ sit sprites
_SIT = {}
def sit_frames(cid):
    if cid not in _SIT:
        j = json.load(open(f'{ROOT}/characters/{cid}/chr_{cid}_sit.json'))
        sheet = np.array(Image.open(f'{ROOT}/characters/{cid}/chr_{cid}_sit.png').convert('RGBA'))
        fr = {}
        for f in j['frames']:
            x, y, w, h = (f['frame'][k] for k in 'xywh')
            fr[f['dir']] = dict(img=sheet[y:y + h, x:x + w], seat=tuple(f['seat']), pivot=tuple(f['pivot']))
        _SIT[cid] = fr
    return _SIT[cid]
def sit_sprite(cid, d):
    """(rgba array 128x128, anchor (x, y)) -- draw with anchor on scr(seat x, seat y, seat_z)"""
    f = sit_frames(cid)[d]; return f['img'], f['seat']

# ------------------------------------------------------------------ seat geometry
def _inside(poly, x, y):
    n = len(poly); ok = True
    for i in range(n):
        ax, ay = poly[i]; bx, by = poly[(i + 1) % n]
        if (bx - ax) * (y - ay) - (by - ay) * (x - ax) < -1e-9: return False
    return ok
class Geo:
    """world-space prisms of every placed item: placements = [(iid, ox, oy, rot, state, z)] (rotation already
    normalised as the renderer does it)"""
    def __init__(self, E, rend, placements):
        self.P = []
        for (iid, ox, oy, rot, st, z) in placements:
            it = E.ITEMS[iid]; st = st or it['states'][0]
            if it['layer'] in ('floor_decal', 'wall_decal') or it['mount'] in ('wall', 'ceiling'): continue
            X = rend(iid, rot, st)['xf']
            for p in it['build'](st):
                poly = [X.fwd(*q) for q in p.poly]
                a = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
                if a < 0: poly = poly[::-1]
                self.P.append(([(ox + qx, oy + qy) for qx, qy in poly], z + p.z0, z + p.z1, iid))
    def seat_z(self, x, y, base, reach=1.05):
        best = None
        lo, hi = (base - 0.2, base + 0.2) if base > 0.05 else (base + 0.05, base + reach)   # raised hook z = seat height already
        pts = [(x + dx, y + dy) for dx in (-0.07, 0, 0.07) for dy in (-0.07, 0, 0.07)]   # slatted seats (bench) have gaps
        for poly, z0, z1, iid in self.P:
            if z1 > hi or z1 < lo: continue
            if any(_inside(poly, px, py) for px, py in pts) and (best is None or z1 > best): best = z1
        return best

def place(h, geo=None, item=None):
    """h: exported/world hook dict (pos, z, facing, ...); item hook data may carry seat_z / seat_off overrides"""
    x, y = h['pos']; base = h.get('z', 0.0) or 0.0
    d = h['facing'] if h['facing'] in DIRS8 else 'SW'
    off = (item or {}).get('seat_off')
    if off: x += off[0]; y += off[1]
    sz = (item or {}).get('seat_z')
    found = sz is not None
    if sz is None and geo is not None: sz = geo.seat_z(x, y, base); found = sz is not None
    if sz is None: sz = base + (0.0 if 'sit_floor' in (h['type'], h.get('anim')) else DEFAULT_SEAT)
    return dict(seat=[round(x, 3), round(y, 3)], seat_z=round(float(sz), 3), sit_dir=d, sit_key=math.floor(x) + math.floor(y) + 1.5, found=found)

# ------------------------------------------------------------------ occluders
def sitter_mask(sp, cids=CAST):
    """union of every cast member's sit frame at this seat: (bool mask, screen x0, y0)"""
    sx, sy = scr(sp['seat'][0], sp['seat'][1], sp['seat_z'])
    m = np.zeros((128, 128), bool); ax0 = ay0 = None
    for c in cids:
        img, (ax, ay) = sit_sprite(c, sp['sit_dir'])
        dx, dy = int(round(sx - ax)), int(round(sy - ay))
        if ax0 is None: ax0, ay0 = dx, dy
        sh = np.zeros_like(m); a = img[..., 3] > 0
        ox, oy = dx - ax0, dy - ay0
        ys, xs = np.nonzero(a); ys = ys + oy; xs = xs + ox
        ok = (ys >= 0) & (ys < 128) & (xs >= 0) & (xs < 128); m[ys[ok], xs[ok]] = True
    # 1 px dilation
    p = np.pad(m, 1); m = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    return m, ax0, ay0

def slice_hits(meta):
    """meta: dict(key, R, t=(tx, ty), tl=(sx, sy), o=(ox, oy, z)) -> rgba, c-map, z-map (world), alpha mask"""
    if 'cache' not in meta:
        R = meta['R']; tx, ty = meta['t']; ox, oy, z = meta['o']
        m = R['op'] & (R['tx'] == tx) & (R['ty'] == ty) & (R['img'][..., 3] > 0)
        meta['cache'] = (m, R['hx'] + R['hy'] + ox + oy, R['hz'] + z)
    return meta['cache']

def analyse(sp, metas):
    """-> (key, occluder rgba, screen x, y) for one seat placement"""
    msk, mx, my = sitter_mask(sp)
    c0 = sp['seat'][0] + sp['seat'][1]; cS = c0 + BODY_C; zS = sp['seat_z']
    key = sp['sit_key']
    hits = []
    for mt in metas:
        R = mt['R']; H, W = R['img'].shape[:2]; tlx, tly = int(round(mt['tl'][0])), int(round(mt['tl'][1]))
        x0, x1 = max(mx, tlx), min(mx + 128, tlx + W); y0, y1 = max(my, tly), min(my + 128, tly + H)
        if x0 >= x1 or y0 >= y1: continue
        m, cm, zm = slice_hits(mt)
        sl = (slice(y0 - tly, y1 - tly), slice(x0 - tlx, x1 - tlx)); ml = msk[y0 - my:y1 - my, x0 - mx:x1 - mx]
        a = m[sl] & ml
        if not a.any(): continue
        front = a & (cm[sl] > cS) & (zm[sl] > zS + ABOVE)
        behind = a & ~front & (zm[sl] > -5)
        hits.append((mt, sl, (x0, y0, x1, y1), front, behind))
    # slices sorting after the sitter but drawing (mostly) geometry behind it: lift the sitter above them
    for mt, sl, bb, front, behind in hits:
        if mt['key'] > key and behind.sum() >= 6 and behind.sum() > 2 * front.sum() and mt['key'] < sp['sit_key'] + 1.0:
            key = max(key, mt['key'] + 0.005)
    occ = np.zeros((128, 128, 4), np.uint8); any_ = False
    for mt, sl, (x0, y0, x1, y1), front, behind in sorted(hits, key=lambda t: t[0]['key']):
        if mt['key'] >= key or not front.any(): continue
        img = mt['R']['img'][sl]; dst = occ[y0 - my:y1 - my, x0 - mx:x1 - mx]
        dst[front] = img[front]; any_ = True
    if not any_: return key, None, mx, my
    ys, xs = np.nonzero(occ[..., 3]); a, b, c, d = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    return key, occ[a:b, c:d], mx + c, my + a

def char_entry(cid, sp):
    """a seated character for the compositors (pos/z/pivot convention of build_env.compose / rooms.compose_loc)"""
    img, (ax, ay) = sit_sprite(cid, sp['sit_dir'])
    return dict(name=cid, img=img, pos=tuple(sp['seat']), z=sp['seat_z'], pivot=(ax, ay), key=sp['sit_key'], shadow=False,
                anim='sit', dir=sp['sit_dir'], seat=sp)

def add_occluders(L5, metas, chars):
    """compositor hook: for every seated character append its occluder above it and fix its key in place"""
    for ch in chars:
        sp = ch.get('seat')
        if not sp: continue
        key, occ, ox, oy = analyse(sp, metas)
        ch['key'] = key
        if occ is not None: L5.append((key + 0.001, occ, ox, oy))
