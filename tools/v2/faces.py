"""Hand-placed v2 face features (eyes, brows, nose, mouth) per character and facing.  At ~12-14 px head width
an automatic downscale smears features into blobs, so faces are redrawn as deliberate pixels on top of the
downscaled AI master (positions read off the full-res AI master art).  Template chars: '.' keep, others from
LEGEND/per-face colours.  Eye chars (blink-able): k (lash/lid line), w (eye white), i (iris), p (pupil)."""
import numpy as np

LEGEND = {'s': 'skin', 'S': 'skin_sh', 'H': 'skin_hi', 'b': 'brow', 'm': 'mouth', 'l': 'lip', 't': 'teeth',
          'k': 'lash', 'w': 'white', 'i': 'iris', 'p': 'pupil', 'c': 'cheek'}
EYE = set('kwip')

FACES = {
 'sheldon': dict(colors=dict(brow=(66, 44, 30), lash=(40, 30, 34), white=(236, 232, 226), iris=(52, 72, 120),
                             pupil=(30, 32, 48), mouth=(146, 86, 76), lip=(196, 128, 112), skin_sh=(206, 146, 116)),
   faces={
    'S':  dict(o=(58, 25), rows=['.bbb...bbb..',
                                 '............',
                                 '..wi...iw...',
                                 '............',
                                 '............',
                                 '.....S......',
                                 '............',
                                 '...mmmm.....']),
    'SW': dict(o=(55, 25), rows=['..b..bbbb..',
                                 '...........',
                                 '...i....iw.',
                                 '...........',
                                 '...........',
                                 '.S.........',
                                 '...........',
                                 '..mmm......']),
    'W':  dict(o=(56, 24), rows=['.bb..',
                                 '.....',
                                 '.wi..',
                                 '.....',
                                 '.....',
                                 '.....',
                                 '.....',
                                 'mm...']),
   }),
 'penny': dict(colors=dict(brow=(150, 108, 60), lash=(46, 30, 34), white=(240, 236, 230), iris=(46, 128, 96),
                           pupil=(30, 52, 44), mouth=(150, 60, 70), lip=(214, 104, 116), teeth=(246, 240, 232),
                           skin_sh=(214, 150, 118), cheek=(236, 160, 150)),
   faces={
    'S':  dict(o=(57, 37), rows=['.bb.....bb..',
                                 '............',
                                 'kkk.....kkk.',
                                 '.wi.....iw..',
                                 'c..........c',
                                 '.....S......',
                                 '............',
                                 '....mttm....',
                                 '.....ll.....']),
    'SW': dict(o=(54, 37), rows=['.b....bb...',
                                 '...........',
                                 'kk....kkk..',
                                 'i.....iww..',
                                 '..........c',
                                 '..S........',
                                 '...........',
                                 '..mtm......',
                                 '...l.......']),
    'W':  dict(o=(55, 35), rows=['.b..',
                                 '....',
                                 'kk..',
                                 'i...',
                                 '....',
                                 '....',
                                 '....',
                                 '....',
                                 'm...']),
   }),
}

def snap(pal, rgb, tol=14):
    """palette index for rgb; appends the colour if nothing within tol"""
    rgb = np.asarray(rgb, float); d = np.sqrt(((pal.astype(float) - rgb) ** 2).sum(1))
    if d.min() <= tol: return pal, int(d.argmin())
    return np.vstack([pal, rgb.round().astype(pal.dtype)]), len(pal)

def apply_face(cid, d, idx, pal, skin_rgb):
    """returns (idx, pal, eye_pixels) -- eye_pixels: list of (y, x, char) for blink"""
    F = FACES.get(cid, {}).get('faces', {}).get(d)
    if F is None: return idx, pal, []
    cols = dict(FACES[cid]['colors']); cols.setdefault('skin', skin_rgb)
    cols.setdefault('skin_sh', tuple(np.asarray(skin_rgb) * 0.86)); cols.setdefault('skin_hi', tuple(np.minimum(np.asarray(skin_rgb) * 1.06, 255)))
    out = idx.copy(); pal = pal.copy(); x0, y0 = F['o']; eyes = []
    pal, skin_i = snap(pal, cols['skin'], 24)
    L = pal.astype(float) @ np.array([0.299, 0.587, 0.114])
    # clear AI smears inside the template box first (dark non-skin pixels -> skin), keeping the hair/outline at
    # the box border rows/cols untouched
    h, w = len(F['rows']), len(F['rows'][0])
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            v = out[y, x]
            if v >= 0 and L[v] < L[skin_i] - 45 and F.get('clear', True):
                # only if the row has skin on both sides (inside the face)
                row = out[y]; lft = (row[:x] == skin_i).any() or (np.abs(L[row[:x][row[:x] >= 0]] - L[skin_i]) < 25).any()
                rgt = (np.abs(L[row[x + 1:][row[x + 1:] >= 0]] - L[skin_i]) < 25).any()
                if lft and rgt: out[y, x] = skin_i
    for j, r in enumerate(F['rows']):
        for i, ch in enumerate(r):
            if ch == '.': continue
            pal, k = snap(pal, cols[LEGEND[ch]]); out[y0 + j, x0 + i] = k
            if ch in EYE: eyes.append((y0 + j, x0 + i, ch))
    return out, pal, eyes

def blink(idx, pal, eyes, state, skin_i, lid_i):
    """state: 'half' -> top eye row becomes lid (skin shadow); 'closed' -> eyes become skin with a lash line on
    the lowest eye row"""
    if state == 'open' or not eyes: return idx
    out = idx.copy()
    ys = sorted(set(y for y, x, c in eyes)); top, bot = ys[0], ys[-1]
    for y, x, c in eyes:
        if state == 'half':
            if y == top and len(ys) > 1: out[y, x] = lid_i
            elif y == top: out[y, x] = lid_i if c in 'wi' else out[y, x]
        else:
            out[y, x] = lid_i if y == bot else skin_i
    return out

def skin_index(M, pal, rig_skin):
    """the AI master's main skin palette entry: of the 4 palette colours nearest the rig skin, the most used
    in the top 30 rows of the figure"""
    ys = np.where((M >= 0).any(1))[0]; hv = M[ys[0]:ys[0] + 30]
    d2 = ((pal.astype(float) - np.asarray(rig_skin, float)) ** 2).sum(1); cand = np.argsort(d2)[:4]
    return int(cand[int(np.argmax([(hv == c).sum() for c in cand]))])
