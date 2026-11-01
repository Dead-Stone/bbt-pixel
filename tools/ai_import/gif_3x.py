"""side-by-side GIF: a recorded game-scale clip + a 3x nearest-neighbour blow-up of its centre (the followed character)
python3 tools/ai_import/gif_3x.py in.gif out.gif [cx cy w h]"""
import sys
from PIL import Image, ImageSequence
src, dst = sys.argv[1], sys.argv[2]
g = Image.open(src); W, H = g.size
cx, cy, w, h = (int(v) for v in sys.argv[3:7]) if len(sys.argv) > 6 else (W // 2, H // 2, 80, 120)
box = (cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2); OH = max(H, 3 * h)
out, durs = [], []
for f in ImageSequence.Iterator(g):
    rgb = f.convert('RGB'); o = Image.new('RGB', (W + 8 + 3 * w, OH), (24, 24, 30))
    o.paste(rgb, (0, (OH - H) // 2)); o.paste(rgb.crop(box).resize((3 * w, 3 * h), Image.NEAREST), (W + 8, (OH - 3 * h) // 2))
    out.append(o.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)); durs.append(f.info.get('duration', 125))
out[0].save(dst, save_all=True, append_images=out[1:], duration=durs, loop=0, optimize=True, disposal=1)
print(dst, out[0].size, len(out))
