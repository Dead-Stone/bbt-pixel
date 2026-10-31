"""Import AI-generated walk strips (GenerateImage, from the cast turnaround as reference) into 128-px walk frames.

Sources live in refs_ai/gen/ (JPEG, flat magenta), one 1x4 key-pose strip per direction (see source()).

Per strip:  key magenta tolerantly (JPEG noise) -> cut 8 figures -> ONE scale for the whole strip
(tallest frames = the actor height used for the stills, so there is no size pop against idle) -> sole of each
frame on row 119 -> horizontal: head/torso centre (top 40%) on the still's head/torso centre (no side-to-side
swim) -> quantize to the character's existing 28-colour AI palette (walk colours == idle colours) -> pixfix,
outline, audit fix.
"""
import os, numpy as np
from PIL import Image
from scipy import ndimage as ndi
import slice as S, convert as CV

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
GEN = os.path.join(ROOT, 'refs_ai', 'gen')

# Each direction comes from a 1x4 strip of key poses (stride A, passing, stride B, passing) generated with
# GenerateImage (refs_ai/gen/<cid>_walk4_<dir>.jpg). Asking for 4 explicitly different key poses is far more
# reliable than asking for an 8-frame cycle (8-frame strips came back as one frozen stride repeated).
# POSES: indices into the strip; ('flip', i) = pose i with the legs (below the hip) mirrored about the body
# axis -- used for S / N where the generator draws both strides with the same foot forward.
# The 8-frame loop holds each key pose for 2 frames (the viewer steps walk frames every 0.14 tiles).
DEFAULT_POSES = {'S': [0, 1, ('flip', 0), 3], 'N': [0, 1, ('flip', 0), 3], 'SW': [0, 1, 2, 3], 'W': [0, 1, 2, 3], 'NW': [0, 1, 2, 3]}
OVERRIDE = {'sheldon': {'SW': dict(poses=[0, 3, 2, 3]), 'W': dict(poses=[0, 3, 2, 3])},
            'leonard': {'S': dict(poses=[0, 1, 2, 3]), 'N': dict(poses=[0, 1, 3, 2])},
            'howard': {'S': dict(poses=[0, 1, 2, 3]), 'N': dict(poses=[0, 1, 2, 3]), 'SW': dict(poses=[0, 3, 2, 3]), 'NW': dict(poses=[0, 3, 2, 3])},
            'raj': {'S': dict(poses=[0, 1, 2, 3])},
            'bernadette': {'S': dict(poses=[0, 1, 2, 3]), 'NW': dict(poses=[0, 1, 2, 1])},}          # {cid: {dir: dict(file=..., ncols=..., poses=[...])}} for strips that needed a fix
KEY_M = {'howard': 140}  # stricter magenta key where the outfit is magenta-ish
HIP = 0.64             # legs start below the hands (~62% down the figure in front/back views)


def source(cid, d):
    o = dict(file=f'{cid}_walk4_{d}.jpg', nrows=1, row=0, ncols=4, poses=DEFAULT_POSES[d], km=KEY_M.get(cid, 70))
    o.update(OVERRIDE.get(cid, {}).get(d, {}))
    return o


def legflip(c):
    """mirror the legs (below HIP) about the hip centre, keep the upper body"""
    h, w = c.shape[:2]; y = int(h * HIP)
    A = c[..., 3] > 0
    xs = np.nonzero(A[y - 3:y + 3].any(0))[0]; cx = (xs.min() + xs.max()) / 2.0
    pad = int(abs(cx - (w - 1) / 2.0)) + 2
    P = np.zeros((h, w + 2 * pad, 4), np.uint8); P[:, pad:pad + w] = c
    cxp = cx + pad; W2 = P.shape[1]
    legs = P[y:].copy(); fl = legs[:, ::-1]
    sh = int(round(2 * cxp - (W2 - 1)))
    fl = np.roll(fl, sh, axis=1)
    P[y:] = fl
    xs = np.nonzero(P[..., 3].any(0))[0]
    return P[:, xs.min():xs.max() + 1]


def cut_strip(path, nrows, row, ncols=8, km=70):
    """km: magenta-key threshold (min(r,b)-g); raised for outfits that are themselves magenta-ish (Howard's trousers)"""
    rgb = np.array(Image.open(path).convert('RGB'))
    m, g = S.magenta_score(rgb)
    fg = ~((m > km) & (g < 150))                   # a bit looser than the PNG turnaround: JPEG ringing
    fg = ndi.binary_opening(fg, np.ones((2, 2)))
    lab, nl = ndi.label(fg); sz = np.bincount(lab.ravel()); sz[0] = 0
    fg = np.isin(lab, np.nonzero(sz >= 60)[0])
    rows = S.bands(fg.sum(1), nrows, min_gap=6)
    y0, y1 = rows[row]
    cols = S.bands(fg[y0:y1].sum(0), ncols, min_gap=4)
    out = []
    for x0, x1 in cols:
        mm = fg[y0:y1, x0:x1]
        l2, n2 = ndi.label(mm, np.ones((3, 3))); s2 = np.bincount(l2.ravel()); s2[0] = 0
        mm = (s2 >= max(60, 0.01 * s2.max()))[l2]
        mm = ndi.binary_fill_holes(mm) & mm | (ndi.binary_fill_holes(mm) & ~((m[y0:y1, x0:x1] > km) & (g[y0:y1, x0:x1] < 150)))
        ys, xs = np.nonzero(mm)
        b = (ys.min(), ys.max() + 1, xs.min(), xs.max() + 1)
        sub = rgb[y0:y1, x0:x1][b[0]:b[1], b[2]:b[3]]
        mk = mm[b[0]:b[1], b[2]:b[3]]
        cut = S.despill(sub, mk)
        out.append(np.dstack([cut, (mk * 255).astype(np.uint8)]))
    return out


def topc(A, frac=0.4):
    ys = np.nonzero(A.any(1))[0]; y0, y1 = ys[0], ys[-1]
    top = A[y0:y0 + int((y1 - y0) * frac)]
    xs = np.nonzero(top)[1]
    return xs.mean()


def convert_strip(cid, cuts, pal, still):
    cm = CV.REAL_CM[cid]
    crown = int(round(CV.PIV[1] - 100 * cm / 185.0)); th = CV.SOLE - crown + 1
    hs = sorted(c.shape[0] for c in cuts)
    s = th / np.mean(hs[-2:])                       # one scale per strip: tallest poses = standing height
    tx = topc(still[..., 3] > 0)
    frames = []
    for c in cuts:
        h, w = c.shape[:2]
        nh, nw = max(1, int(round(h * s))), max(1, int(round(w * s)))
        rgb, A = CV.area_resize(c, (nw, nh))
        m = A >= 0.5
        rgb = CV.unsharp(rgb, m, 0.35)
        ox = int(round(tx - topc(m)))
        oy = CV.SOLE + 1 - nh
        img = np.zeros((CV.H, CV.W, 4), np.uint8)
        sub = img[oy:oy + nh, ox:ox + nw]
        sub[m, :3] = CV.nearest(pal, rgb[m]); sub[m, 3] = 255
        img = CV.pixfix(img); img = CV.outline(img, pal); img = CV.pixfix(img)
        frames.append(CV.audit_fix(img, pal))
    return frames


def head_lock(frames, extra=2):
    """paste key pose 0's head onto the other key poses (best |d|<=2 alignment) so the face does not boil between
    generated poses; the window is the audit's head band (figure height / 6.5) plus a couple of rows"""
    f0 = frames[0]; A0 = f0[..., 3] > 0
    ys = np.nonzero(A0.any(1))[0]; c0 = ys[0]; hr = int(round((ys[-1] - ys[0]) / 6.5)) + extra
    win0 = f0[c0:c0 + hr]
    out = [f0]
    for f in frames[1:]:
        A = f[..., 3] > 0; c = np.nonzero(A.any(1))[0][0]
        best = None
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                y = c + dy
                if y < 0: continue
                cand = np.roll(win0, dx, axis=1)
                tgt = f[y:y + hr]
                if tgt.shape != cand.shape: continue
                both = (cand[..., 3] > 0) | (tgt[..., 3] > 0)
                d = (np.abs(cand.astype(int) - tgt.astype(int)).sum(-1) > 30)[both].sum()
                if best is None or d < best[0]: best = (d, dy, dx)
        _, dy, dx = best
        g = f.copy(); y = max(0, c + dy)
        g[y:y + hr] = np.roll(win0, dx, axis=1)
        out.append(g)
    return out


def walk_for(cid, pal, views):
    """{dir: [8 frames]} for S/SW/W/NW/N, or {} when this character has no generated strips yet"""
    out = {}
    for d in DEFAULT_POSES:
        src = source(cid, d); p = os.path.join(GEN, src['file'])
        if not os.path.exists(p): return {}
        cuts = cut_strip(p, src['nrows'], src['row'], src['ncols'], src.get('km', 70))
        keys = [legflip(cuts[q[1]]) if isinstance(q, tuple) else cuts[q] for q in src['poses']]
        conv = head_lock(convert_strip(cid, keys, pal, views[d]))
        conv = [CV.audit_fix(f, pal) for f in conv]
        out[d] = [f for f in conv for _ in (0, 1)]
    return out
