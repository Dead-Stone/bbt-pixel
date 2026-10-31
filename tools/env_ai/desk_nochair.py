"""Remove the office chair that the ChatGPT 4A sheet merged into the desk sprite (4A_furniture_v1/08.png) so the chair can be
a separate item (fixups_v1/00-01).  Chair mask = the large connected grey/black blob in front of the desktop (monitor, keyboard
and PC tower excluded by position); masked pixels are filled by tracing along the desk's front-edge direction (slope -0.4 on
the sheet): above the front edge from the right (desktop), below it from the left (edge band, shadowed back panel, or
transparent under the desk).  -> refs_ai/chatgpt/env/sliced/4A_furniture_v1/08_nochair.png"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
D = f'{ROOT}/refs_ai/chatgpt/env/sliced/4A_furniture_v1'
def main():
    a = np.array(Image.open(f'{D}/08.png').convert('RGBA')); H, W = a.shape[:2]
    rgb = a[..., :3].astype(int); al = a[..., 3] > 0
    lum = rgb @ np.array([0.3, 0.59, 0.11])
    grey = al & (rgb.max(-1) - rgb.min(-1) < 45) & (lum < 150)
    yy, xx = np.mgrid[:H, :W]
    cand = grey & (yy >= 56) & (xx >= 72) & ~((yy < 90) & (xx < 108))
    lab, n = ndi.label(ndi.binary_closing(cand, iterations=1)); sz = ndi.sum(cand, lab, range(1, n + 1))
    m = ndi.binary_fill_holes(ndi.binary_dilation(lab == 1 + int(np.argmax(sz)), iterations=1) & al) & al
    m[:, 155:] = False                                   # keep the drawer pedestal's outline
    E0 = lambda x: 100 - 0.4 * (x - 70)                  # desk front edge (bottom outline) on the sheet
    out = a.copy()
    for y, x in zip(*np.where(m)):
        sgn = 1 if y < E0(x) else -1; val = None
        for k in range(1, 200):
            x2, y2 = x + sgn * k, int(round(y - sgn * 0.4 * k))
            if not (0 <= x2 < W and 0 <= y2 < H): break
            if m[y2, x2] or (sgn == 1 and a[y2, x2, 3] > 0 and lum[y2, x2] < 90): continue
            val = a[y2, x2]; break
        out[y, x] = val if val is not None else (0, 0, 0, 0)
    r, g, b, al2 = [out[..., i].astype(int) for i in range(4)]
    bad = ((r > 120) & (b > 120) & (g < 90)) | ((al2 < 230) & (xx >= 70) & (xx < 157) & (yy > 95))
    out[bad] = 0
    op = out[..., 3] > 0; lab, n = ndi.label(op); sz = ndi.sum(op, lab, range(1, n + 1))
    for i, s in enumerate(sz):
        if s < 30: out[lab == i + 1] = 0
    Image.fromarray(out).save(f'{D}/08_nochair.png'); return f'{D}/08_nochair.png'
if __name__ == '__main__':
    print(main())
