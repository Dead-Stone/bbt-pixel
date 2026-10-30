"""frames dir -> optimised GIF.  python3 harness/make_gif.py <dir> <out.gif> [fps]"""
import glob, os, sys
from PIL import Image
d, out = sys.argv[1], sys.argv[2]; fps = float(sys.argv[3]) if len(sys.argv) > 3 else 8
files = sorted(glob.glob(os.path.join(d, '*.png')))
frames = [Image.open(f).convert('RGB') for f in files]
# one shared palette from a few sample frames keeps colours stable (no flicker) and the file small
sample = Image.new('RGB', (frames[0].width, frames[0].height * 4))
for k, f in enumerate(frames[::max(1, len(frames) // 4)][:4]): sample.paste(f, (0, k * frames[0].height))
pal = sample.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
q[0].save(out, save_all=True, append_images=q[1:], duration=int(1000 / fps), loop=0, optimize=True, disposal=1)
print(f'[gif] {out}: {len(q)} frames, {os.path.getsize(out) / 1e6:.1f} MB')
