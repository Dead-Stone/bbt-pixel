import numpy as np, time, sys
import sheldon_rig as R
from compose_sheldon import compose
from PIL import Image
R.SCALE = float(sys.argv[1]) if len(sys.argv)>1 else 1.0
pose = dict(legs=[(0,0.02),(0,0.02)], arms=[(0.03,0.12),(0.03,0.12)])
t=time.time(); frames=[]
for d in ['S','SW','W','NW','N']:
    B = R.render(pose, R.YAW[d]); img = compose(B); frames.append(img)
    ys=np.where(img[...,3].any(1))[0]; xs=np.where(img[...,3].any(0))[0]
    print(d,'top',ys[0],'bottom',ys[-1],'x',xs[0],xs[-1])
print('t',time.time()-t)
strip=np.concatenate(frames,1); Image.fromarray(strip).resize((strip.shape[1]*6,768),Image.NEAREST).save('/tmp/test4x.png')
