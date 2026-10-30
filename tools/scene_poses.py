"""Scene-only character poses (not part of the character sheets): e.g. Sheldon seated on his couch spot.
Writes env/renders/poses/*.png (128x128, pivot 64,116 = floor point under the hips)."""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
import char_rig as R
OUT = '/workspace/bbt-pixel/env/renders/poses'; os.makedirs(OUT, exist_ok=True)
def seated(cid, d='SW', lift=-17.0, th=1.3, kn=1.3):
    R.set_character(cid)
    import compose_char; from compose_char import compose
    pose = dict(breathe=0.0, legs=[(th, kn), (th, kn)], arms=[(0.45, 0.95), (0.6, 0.85)], abduct=0.02, lift=lift)
    B = R.render(pose, R.YAW[d])
    return compose(B, pose, R.YAW[d])
if __name__ == '__main__':
    cid = sys.argv[1] if len(sys.argv) > 1 else 'sheldon'
    # v2 bodies: put every character's hips at the same on-screen seat height Sheldon v1 used (hip_z 45.5 - 17 units at scale 1)
    R.set_character(cid)
    lift = float(sys.argv[2]) if len(sys.argv) > 2 else round((45.5 - 17.0) / R.KSCALE[cid] - R.DIM['hip_z'], 2)
    RAISE = 12.0                       # render 12 units higher so the feet stay inside the 128 frame; pivot moves down to match
    im = seated(cid, 'SW', lift + RAISE)
    dz = RAISE * R.SCALE_EFF * math.cos(R.ELEV)
    json.dump(dict(sprite=f'{cid}_sit_SW.png', pivot=[64, round(116 + dz)], dir='SW', lift_units=lift,
                   note='scene-only seated pose; pivot = floor point under the hips'), open(f'{OUT}/{cid}_sit_SW.json', 'w'), indent=1)
    Image.fromarray(im).save(f'{OUT}/{cid}_sit_SW.png')
    Image.fromarray(im).resize((512, 512), Image.NEAREST).save(f'/tmp/{cid}_sit_4x.png')
    ys = np.where((im[..., 3] > 0).any(1))[0]; print('rows', ys[0], ys[-1])
