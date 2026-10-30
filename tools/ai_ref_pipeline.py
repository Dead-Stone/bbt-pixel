"""AI reference -> 128x128 palette-snapped frames (test of the AI route).
bg key -> split views -> nearest downscale to body height -> palette snap -> 1px outline -> pivot align."""
import sys, numpy as np
from PIL import Image
from collections import deque
sys.path.insert(0, __file__.rsplit('/',1)[0])
from sprite_common import load_gpl, snap_to_palette, outline_pass, PIVOT
src, out, H = sys.argv[1], sys.argv[2], int(sys.argv[3])
pal = load_gpl('/workspace/bbt-pixel/palettes/bbt_sheldon.gpl')
im = np.asarray(Image.open(src).convert('RGB')).astype(int)
bg = np.median(np.concatenate([im[:5].reshape(-1,3), im[-5:].reshape(-1,3)]),axis=0)
fg = np.abs(im - bg).sum(2) > 90
cols = fg.sum(0) > 2
# split views by empty column runs
views=[]; x=0; W=len(cols)
while x<W:
    if cols[x]:
        s=x
        while x<W and cols[x]: x+=1
        if x-s>20: views.append((s,x))
    x+=1
names=['S','SW','W','NW','N']
strip=Image.new('RGBA',(128*len(views),128))
for i,(a,b) in enumerate(views):
    m=fg[:,a:b]; rows=np.where(m.any(1))[0]; y0,y1=rows[0],rows[-1]+1
    crop=np.dstack([im[y0:y1,a:b], (m[y0:y1]*255)]).astype(np.uint8)
    ci=Image.fromarray(crop,'RGBA'); sc=H/(y1-y0)
    ci=ci.resize((max(1,round((b-a)*sc)),H),Image.NEAREST)
    arr=np.asarray(ci).copy(); arr[...,3]=np.where(arr[...,3]>127,255,0)
    arr=snap_to_palette(arr,pal)
    frame=np.zeros((128,128,4),np.uint8)
    w=arr.shape[1]; ox=PIVOT[0]-w//2; oy=PIVOT[1]-H
    frame[oy:oy+H, ox:ox+w]=arr
    frame=outline_pass(frame,pal)
    strip.paste(Image.fromarray(frame),(128*i,0))
strip.save(out); strip.resize((strip.width*4,512),Image.NEAREST).save(out.replace('.png','_4x.png'))
print(len(views),'views')
