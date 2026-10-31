"""Exact 2:1 iso prism renderer for environment items (spec §1.5-§1.7, §4.3-§4.5).
World: +X -> screen lower-right (SE), +Y -> screen lower-left (SW), Z up (metres).
sx = (x-y)*64, sy = (x+y)*32 - z*64.  View ray is (1,1,1); nearness = x+y+z.
Every pixel is ray-cast against vertical prisms (polygon base, z0..z1) at native resolution, so
2:1 edges are clean staircases and every rotation is re-rendered (never mirrored) with the same
upper-left key light: top = ramp[0] (lightest), faces whose normal leans +Y (SW / left) = ramp[1],
faces whose normal leans +X (SE / right) = ramp[2], ramp[3] = occlusion/contact."""
import math, numpy as np
from sprite_common import load_gpl
ROOT = '/workspace/bbt-pixel'
PAL = load_gpl(f'{ROOT}/palettes/bbt_master.gpl')
# location sub-palette names in the gpl contain digits at the start; normalise aliases
PAL.update({'turquoise': PAL['4b_turquoise'], 'orange': PAL['4b_orange'], 'purple': PAL['4b_purple'],
            'lime': PAL['4b_lime']})
import os as _os
if _os.path.exists(f'{ROOT}/palettes/bbt_env_ai.gpl'):      # shared env palette from the ChatGPT environment sheets (ai_NN)
    PAL.update(load_gpl(f'{ROOT}/palettes/bbt_env_ai.gpl'))
C = {k: np.array(v, np.uint8) for k, v in PAL.items()}

MAT = {
 'wood':    ('wood_hi', 'wood', 'wood_dk', 'wood_xdk'),
 'wood_dk': ('wood', 'wood_dk', 'wood_xdk', 'leather_xdk'),
 'wood_lt': ('wall_4a_hi', 'wood_hi', 'wood', 'wood_dk'),
 'leather': ('leather_hi', 'leather', 'leather_dk', 'leather_xdk'),
 'wall':    ('wall_4a_hi', 'wall_4a', 'wall_4a_dk', 'stair_wall_dk'),
 'stair':   ('wall_4a_hi', 'stair_wall', 'stair_wall_dk', 'floor_hall'),
 'metal':   ('grey_lt', 'grey', 'grey_dk', 'shadow_violet'),
 'steel':   ('grey_lt', 'cafe_steel', 'grey', 'grey_dk'),
 'white':   ('white_hi', 'paper', 'grey_lt', 'grey'),
 'dark':    ('grey_dk', 'shadow_violet', 'ink_2', 'ink'),
 'black':   ('shadow_violet', 'ink_2', 'ink', 'ink'),
 'green':   ('tile_green', 'tile_green', 'tile_green_dk', 'shadow_violet'),
 'plant':   ('4b_lime', 'plant_green', 'marker_green', 'tile_green_dk'),
 'red':     ('marker_red', 'marker_red', 'ccf_booth_red', 'shadow_violet'),
 'blue':    ('screen_glow', 'marker_blue', 'comic_blue', 'shadow_violet'),
 'yellow':  ('comic_yellow', 'tape_yellow', 'tape_yellow_dk', 'wood_dk'),
 'cream':   ('white_hi', 'cafe_cream', 'wall_4a', 'wall_4a_dk'),
 'brass':   ('lamp_warm', 'ccf_amber', 'tape_yellow_dk', 'wood_dk'),
 'lamp':    ('white_hi', 'lamp_warm', 'ccf_amber', 'wood'),
 'cardboard': ('wall_4a_hi', 'wall_4a', 'wall_4a_dk', 'wood_dk'),
 'turq':    ('cafe_teal', '4b_turquoise', 'cafe_teal', 'shadow_violet'),
 'orange':  ('lamp_warm', '4b_orange', 'ccf_amber', 'wood_dk'),
 'purple':  ('4b_purple', '4b_purple', 'shadow_violet', 'ink_2'),
 'lime':    ('4b_lime', '4b_lime', 'plant_green', 'tile_green_dk'),
 'hall':    ('wood_hi', 'floor_hall', 'wood_dk', 'wood_xdk'),
 'skin':    ('skin_a1', 'skin_a2', 'skin_a3', 'skin_a4'),
 'pink':    ('paper', 'grey_lt', 'grey', 'grey_dk'),
 'glass':   ('white_hi', 'screen_glow', 'grey_lt', 'grey'),
 'wine':    ('marker_red', 'ccf_booth_red', 'shadow_violet', 'ink'),
 'bottle':  ('plant_green', 'tile_green_dk', 'shadow_violet', 'ink'),
}

class Prism:
    __slots__ = ('poly', 'z0', 'z1', 'mat', 'tex', 'tag', 'outline')
    def __init__(s, poly, z0, z1, mat, tex=None, tag='', outline=True):
        p = [tuple(map(float, q)) for q in poly]
        a = sum(p[i][0]*p[(i+1) % len(p)][1] - p[(i+1) % len(p)][0]*p[i][1] for i in range(len(p)))
        if a < 0: p = p[::-1]
        s.poly, s.z0, s.z1, s.mat, s.tex, s.tag, s.outline = p, float(z0), float(z1), mat, tex, tag, outline

def box(x0, y0, z0, x1, y1, z1, mat, tex=None, tag=''):
    return Prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat, tex, tag)
def cyl(cx, cy, r, z0, z1, mat, n=16, tex=None, tag='', ry=None):
    ry = r if ry is None else ry
    return Prism([(cx + r*math.cos(2*math.pi*(k+0.5)/n), cy + ry*math.sin(2*math.pi*(k+0.5)/n)) for k in range(n)], z0, z1, mat, tex, tag)

# rotation: canonical items face +Y (SW).  angle (deg, math CCW in x/y) that maps +Y onto the target front
ROT_ANGLE = {'SW': 0, 'SE': -90, 'NE': 180, 'NW': 90, 'S': -45, 'W': 45, 'N': 135, 'E': -135}
DIR_ORDER = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']
def dir_name(vx, vy):
    a = math.degrees(math.atan2(vy, vx)) % 360   # +X=0 (SE), +Y=90 (SW)
    names = {0: 'SE', 45: 'S', 90: 'SW', 135: 'W', 180: 'NW', 225: 'N', 270: 'NE', 315: 'E'}
    return names[int(round(a / 45.0)) % 8 * 45]

class Xform:
    """canonical (footprint fx x fy, front +Y) -> rotated local coordinates with footprint at origin"""
    def __init__(s, fx, fy, rot):
        s.fx, s.fy, s.rot = fx, fy, rot
        a = math.radians(ROT_ANGLE[rot]); s.c, s.s = round(math.cos(a), 12), round(math.sin(a), 12)
        s.cx, s.cy = fx/2, fy/2
        if ROT_ANGLE[rot] % 180 == 0: s.nfx, s.nfy = fx, fy
        elif ROT_ANGLE[rot] % 90 == 0: s.nfx, s.nfy = fy, fx
        else: s.nfx, s.nfy = fx, fy            # 45-degree views keep their (1x1) tile
    def fwd(s, x, y):
        dx, dy = x - s.cx, y - s.cy
        return s.c*dx - s.s*dy + s.nfx/2, s.s*dx + s.c*dy + s.nfy/2
    def inv(s, x, y):
        dx, dy = x - s.nfx/2, y - s.nfy/2
        return s.c*dx + s.s*dy + s.cx, -s.s*dx + s.c*dy + s.cy
    def vec(s, vx, vy): return s.c*vx - s.s*vy, s.s*vx + s.c*vy
    def ivec(s, vx, vy): return s.c*vx + s.s*vy, -s.s*vx + s.c*vy

def scr(x, y, z=0.0): return (x - y)*64.0, (x + y)*32.0 - z*64.0

def render(prims, fx, fy, rot, shadow=True, min_canvas_h=None, footprint_canvas=True):
    """returns dict(img RGBA, pivot (px,py), tile map, near, fp=(nfx,nfy), xf)"""
    X = Xform(fx, fy, rot)
    P = [Prism([X.fwd(*q) for q in p.poly], p.z0, p.z1, p.mat, p.tex, p.tag, p.outline) for p in prims]
    nfx, nfy = X.nfx, X.nfy
    xs, ys = [], []
    for p in P:
        g = 0.0   # contact shadows are clipped to the canvas, not allowed to grow it
        for (x, y) in p.poly:
            for z in (p.z0, p.z1):
                for ex, ey in ((0, 0), (g, 0), (0, g), (g, -g), (-g, g)):
                    a, b = scr(x+ex, y+ey, z); xs.append(a); ys.append(b)
    zmax = max(p.z1 for p in P)
    hpx = int(math.ceil(zmax*64 - 1e-6)); hpx += hpx % 2
    fminx, fmaxx, fminy, fmaxy = -nfy*64, nfx*64, -hpx, (nfx+nfy)*32     # spec §4.3 canvas formula
    minx = min(fminx, math.floor(min(xs))); maxx = max(fmaxx, math.ceil(max(xs)))
    miny = min(fminy, math.floor(min(ys))); maxy = max(fmaxy, math.ceil(max(ys)))
    minx -= minx % 2; miny -= miny % 2
    W = maxx - minx; H = maxy - miny; W += W % 2; H += H % 2
    formula_ok = (minx, maxx, miny, maxy) == (fminx, fmaxx, fminy, fmaxy)
    ox, oy = -minx, -miny
    I, J = np.meshgrid(np.arange(W), np.arange(H))
    SX = I + 0.5 - ox; SY = J + 0.5 - oy
    U = SX / 64.0
    near = np.full((H, W), -1e9); pid = np.full((H, W), -1, int); face = np.zeros((H, W), int)
    hx = np.zeros((H, W)); hy = np.zeros((H, W)); hz = np.zeros((H, W)); hn = np.zeros((H, W, 2))
    for k, p in enumerate(P):
        poly = p.poly; n = len(poly)
        # top face
        V = (SY + 64*p.z1) / 32.0; x = (U + V)/2; y = (V - U)/2
        inside = np.ones((H, W), bool)
        for i in range(n):
            ax, ay = poly[i]; bx, by = poly[(i+1) % n]
            inside &= ((bx-ax)*(y-ay) - (by-ay)*(x-ax)) >= -1e-9
        nr = V + p.z1; w = inside & (nr > near)
        near[w] = nr[w]; pid[w] = k; face[w] = 0; hx[w] = x[w]; hy[w] = y[w]; hz[w] = p.z1; hn[w] = 0
        for i in range(n):
            ax, ay = poly[i]; bx, by = poly[(i+1) % n]; dx, dy = bx-ax, by-ay
            nx, ny = dy, -dx; L = math.hypot(nx, ny); nx /= L; ny /= L
            if nx + ny <= 1e-6 or abs(dx - dy) < 1e-9: continue
            s_ = (U - (ax - ay)) / (dx - dy)
            x = ax + s_*dx; y = ay + s_*dy; V = x + y; z = (32*V - SY) / 64.0
            ok = (s_ >= 0) & (s_ <= 1) & (z >= p.z0 - 1e-9) & (z <= p.z1 + 1e-9)
            nr = V + z; w = ok & (nr > near)
            tone = 1 if (ny - nx) > -0.25 else 2
            near[w] = nr[w]; pid[w] = k; face[w] = tone; hx[w] = x[w]; hy[w] = y[w]; hz[w] = z[w]
            hn[w] = (nx, ny)
    op = pid >= 0
    img = np.zeros((H, W, 4), np.uint8)
    tonemap = face.copy()
    # canonical coordinates for textures
    cx, cy = X.inv(hx, hy)
    cnx, cny = X.ivec(hn[..., 0], hn[..., 1])
    names = np.empty((H, W), object)
    for k, p in enumerate(P):
        w = op & (pid == k)
        if not w.any(): continue
        ramp = MAT[p.mat]
        if p.tex is None:
            for t in range(4):
                m = w & (tonemap == t); img[m, :3] = C[ramp[t]]
        else:
            for (r, c) in zip(*np.where(w)):
                f = face[r, c]
                fn = 'top' if f == 0 else side_name(cnx[r, c], cny[r, c])
                res = p.tex(fn, cx[r, c], cy[r, c], hz[r, c], f, (r, c))
                if res is None: res = f
                if isinstance(res, str) and res == 'clear':
                    pid[r, c] = -1; continue
                if isinstance(res, (int, np.integer)):
                    res = int(min(max(res, 0), 3)); tonemap[r, c] = res; img[r, c, :3] = C[ramp[res]]
                else:
                    img[r, c, :3] = C[res]; tonemap[r, c] = 9
    op = pid >= 0
    img[op, 3] = 255
    img[~op] = 0
    # interior occlusion lines: a pixel directly behind a nearer, different prism edge gets the occlusion tone
    npd = np.pad(near, 1, constant_values=-1e9); ppd = np.pad(pid, 1, constant_values=-1)
    occl = np.zeros((H, W), bool)
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nn = npd[1+dr:H+1+dr, 1+dc:W+1+dc]; pp = ppd[1+dr:H+1+dr, 1+dc:W+1+dc]
        occl |= op & (pp >= 0) & (pp != pid) & (nn - near > 0.18)
    for k, p in enumerate(P):
        if not p.outline: continue
        m = occl & (pid == k) & (tonemap != 9); img[m, :3] = C[MAT[p.mat][3]]
    # silhouette: sel-out (darkest local shade) on top / upper-left edges, ink elsewhere
    opd = np.pad(op, 1)
    up_t = ~opd[0:H, 1:W+1]; dn_t = ~opd[2:H+2, 1:W+1]; lf_t = ~opd[1:H+1, 0:W]; rt_t = ~opd[1:H+1, 2:W+2]
    edge = op & (up_t | dn_t | lf_t | rt_t)
    sel = edge & (up_t | lf_t) & ~dn_t & ~rt_t
    img[edge & ~sel, :3] = C['ink']
    for k, p in enumerate(P):
        m = sel & (pid == k); img[m, :3] = C[MAT[p.mat][3]]
    # tile index of each pixel (for per-tile slicing): nudge side hits inward
    tx = np.floor(np.clip(hx - hn[..., 0]*0.01, 0, nfx - 1e-6)).astype(int) if nfx > 0 else np.zeros((H, W), int)
    ty = np.floor(np.clip(hy - hn[..., 1]*0.01, 0, max(nfy, 1) - 1e-6)).astype(int)
    # contact shadow: 2-4 px of shadow_violet (alpha) hugging grounded prims, offset to the lower right
    if shadow:
        sh = np.zeros((H, W), bool)
        V0 = SY / 32.0; x0 = (U + V0)/2; y0 = (V0 - U)/2
        for p in P:
            if p.z0 > 0.02: continue
            poly = p.poly; n = len(poly); cxp = sum(q[0] for q in poly)/n; cyp = sum(q[1] for q in poly)/n
            ins = np.ones((H, W), bool)
            for i in range(n):
                ax, ay = poly[i]; bx, by = poly[(i+1) % n]
                # expand polygon by e (outward) and shift shadow +x
                dx, dy = bx-ax, by-ay; L = math.hypot(dx, dy); nx, ny = dy/L, -dx/L; e = 0.045
                ins &= ((bx-ax)*(y0-(ay+ny*e)) - (by-ay)*(x0-(ax+nx*e+0.03))) >= 0
            sh |= ins
        m = sh & ~op
        img[m, :3] = C['shadow_violet']; img[m, 3] = 110
        tx2 = np.floor(np.clip(x0, 0, max(nfx, 1) - 1e-6)).astype(int); ty2 = np.floor(np.clip(y0, 0, max(nfy, 1) - 1e-6)).astype(int)
        tx = np.where(m, tx2, tx); ty = np.where(m, ty2, ty)
    pivot = (ox + (nfx - nfy)*64, oy + (nfx + nfy)*32)
    return dict(formula_ok=formula_ok, img=img, pivot=pivot, tx=tx, ty=ty, op=op | (img[..., 3] > 0), fp=(nfx, nfy), xf=X, near=near,
                hx=np.where(op, hx, 0.0), hy=np.where(op, hy, 0.0), hz=np.where(op, hz, -9.0))   # local hit point per pixel (seat occluders)

def side_name(nx, ny):
    if abs(ny) >= abs(nx): return 'front' if ny > 0 else 'back'
    return 'right' if nx > 0 else 'left'

def crop_to(res):
    """trim fully transparent margins, keeping the pivot consistent"""
    img = res['img']; a = img[..., 3] > 0
    ys, xs = np.where(a)
    if len(xs) == 0: return res
    x0 = max(0, xs.min() - 1); y0 = max(0, ys.min() - 1)
    x0 -= x0 % 2; y0 -= y0 % 2
    x1 = xs.max() + 2; y1 = max(ys.max() + 2, res['pivot'][1])
    out = dict(res)
    for k in ('img', 'tx', 'ty', 'op', 'near'):
        out[k] = res[k][y0:y1, x0:x1]
    out['pivot'] = (res['pivot'][0] - x0, res['pivot'][1] - y0)
    return out
