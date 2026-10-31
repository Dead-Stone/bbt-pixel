"""Idle loop from a single still: 1-px breathing (head + shoulders rise, the chest row stretches) and a blink.

Breath: rows crown..chest line move up 1 px and the chest row is duplicated (a stretch, not a tear); legs never move.
Blink: per-view eye boxes (EYES below); the lash row stays, the white/iris rows under it take the cheek colour.
Automatic eye detection was tried (dark/white pixels inside the face-skin region) and was unreliable at this size
(eyes are 1-2 px tall, brows/glasses/hair look the same), so the boxes are explicit.  Back views never blink.

Loop (8 frames, 250 ms each = the rig idle's tag layout, so the viewer needs no change):
  0 base, 1 base, 2 up, 3 up, 4 up, 5 base, 6 base, 7 blink
"""
import numpy as np

LOOP = ['base', 'base', 'up', 'up', 'up', 'base', 'base', 'blink']


def lum(c): c = np.asarray(c, float); return 0.299 * c[..., 0] + 0.587 * c[..., 1] + 0.114 * c[..., 2]


def extent(img):
    ys = np.nonzero((img[..., 3] > 0).any(1))[0]; return ys[0], ys[-1]


def breathe(img, chest_frac=0.30):
    y0, y1 = extent(img); chest = int(y0 + chest_frac * (y1 - y0))
    out = img.copy()
    out[y0 - 1:chest] = img[y0:chest + 1]
    return out


# face skin sample point on the S still (x, y) per character, picked from the converted 128-px frames
SKIN_AT = dict(sheldon=(64, 25), leonard=(64, 38), penny=(64, 34), howard=(60, 44), raj=(64, 36), bernadette=(65, 40), amy=(65, 38))


def skin_of(img_s, at):
    x, y = at
    cs = [tuple(img_s[yy, xx, :3]) for yy in range(y - 1, y + 2) for xx in range(x - 1, x + 2) if img_s[yy, xx, 3]]
    return np.array(max(set(cs), key=cs.count), float)


# Eye boxes (y0, y1, x0, x1), inclusive, on the converted S/SW/W stills.  These were read off 16x zooms of the 128-px frames
# (eyes are 1-2 px tall at game size, too small for reliable automatic detection).  Glasses wearers (Leonard, Amy,
# Bernadette) and Howard's profile (his eye is already a 1-px dark line) get no blink: at this size their eyes are lens pixels and repainting them breaks the frames.
EYES = {
    'sheldon': {'S': [(29, 30, 58, 61), (29, 30, 66, 69)], 'SW': [(29, 30, 59, 62), (29, 30, 66, 68)], 'W': [(29, 30, 57, 59)]},
    'penny': {'S': [(38, 39, 57, 60), (38, 39, 66, 69)], 'SW': [(38, 39, 56, 59), (38, 39, 62, 65)], 'W': [(38, 39, 57, 60)]},
    'howard': {'S': [(41, 42, 58, 61), (41, 42, 66, 69)], 'SW': [(41, 42, 59, 62), (41, 42, 65, 67)], 'W': []},
    'raj': {'S': [(39, 40, 57, 60), (39, 40, 66, 69)], 'SW': [(39, 40, 56, 59), (39, 40, 62, 65)], 'W': [(38, 39, 57, 60)]},
}


def blink_boxes(img, boxes, base):
    """close each eye the pixel-art way: the top row of the box (upper lid / lash line) stays, the rows under it
    (white + iris + pupil) take the cheek colour found just under the box -> only the lash line is left"""
    out = img.copy()
    for y0, y1, x0, x1 in boxes:
        for x in range(x0, x1 + 1):
            below = img[y1 + 1, x, :3].astype(float)
            fill = below if (img[y1 + 1, x, 3] and np.sqrt(((below - base) ** 2).sum()) < 70) else base
            for y in range(y0 + 1, y1 + 1):
                if out[y, x, 3]: out[y, x, :3] = fill
    return out


def idle_frames(img, boxes, base):
    up = breathe(img); bl = blink_boxes(img, boxes, base) if boxes else img
    return [dict(base=img, up=up, blink=bl)[k] for k in LOOP]
