"""Hue-shifted 5-step ramps (hi, base, shade, deep, outline) from one base colour per material."""
import colorsys
import numpy as np


def _hsv(rgb): return colorsys.rgb_to_hsv(*[c / 255.0 for c in rgb])


def _rgb(h, s, v): return tuple(int(round(255 * c)) for c in colorsys.hsv_to_rgb(h % 1.0, min(max(s, 0), 1), min(max(v, 0), 1)))


def ramp(base, hi=None, warm=0.025, cool=0.03):
    h, s, v = _hsv(base)
    # shading hue moves towards red/purple, highlights towards yellow (classic pixel-art hue shifting)
    tow = lambda h0, target, amt: h0 + ((target - h0 + 0.5) % 1.0 - 0.5) * amt
    hi_c = hi or _rgb(tow(h, 0.14, 0.06), s * 0.82, v * 1.10 + 0.03)
    sh = _rgb(tow(h, 0.80, 0.10), s * 1.08 + 0.04, v * 0.80)
    dp = _rgb(tow(h, 0.80, 0.18), s * 1.12 + 0.08, v * 0.62)
    ol = _rgb(tow(h, 0.80, 0.22), min(1, s * 1.1 + 0.12), max(0.10, v * 0.34))
    return [tuple(hi_c), tuple(base), sh, dp, ol]


class Palette:
    def __init__(self, mats):
        """mats: {name: base rgb or full 5-list}"""
        self.cols = []; self.ramps = {}
        for k, v in mats.items():
            r = v if (isinstance(v, list) and len(v) == 5) else ramp(tuple(v))
            self.ramps[k] = [self.add(c) for c in r]
    def add(self, c):
        c = tuple(int(x) for x in c)
        if c not in self.cols: self.cols.append(c)
        return self.cols.index(c)
    @property
    def arr(self): return np.array(self.cols, np.uint8)
    def save_gpl(self, path, name):
        with open(path, 'w') as f:
            f.write(f'GIMP Palette\nName: {name}\nColumns: 5\n#\n')
            names = {}
            for k, r in self.ramps.items():
                for t, i in zip(('hi', 'base', 'sh', 'deep', 'ol'), r): names.setdefault(i, f'{k}_{t}')
            for i, c in enumerate(self.cols): f.write(f'{c[0]:3d} {c[1]:3d} {c[2]:3d}\t{names.get(i, "x%d" % i)}\n')
