import numpy as np
PIVOT=(64,116)
def load_gpl(path):
    pal={}
    for line in open(path):
        p=line.split()
        if len(p)>=4 and p[0].isdigit():
            pal[p[3]]=(int(p[0]),int(p[1]),int(p[2]))
    return pal
def snap_to_palette(arr,pal):
    cols=np.array(list(pal.values()))
    rgb=arr[...,:3].astype(int).reshape(-1,1,3)
    # perceptual-ish weighted distance
    d=(((rgb-cols[None])**2)*np.array([0.3,0.59,0.11])).sum(2)
    out=arr.copy(); out[...,:3]=cols[d.argmin(1)].reshape(arr.shape[:2]+(3,))
    return out
def outline_pass(frame,pal):
    """make the outermost opaque ring ink (simple 1px inner silhouette outline)"""
    a=frame[...,3]>0; f=frame.copy()
    pad=np.pad(a,1)
    edge=a & ~(pad[:-2,1:-1]&pad[2:,1:-1]&pad[1:-1,:-2]&pad[1:-1,2:])
    f[edge,:3]=pal['ink']; return f
def palette_violations(frame,pal):
    cols={tuple(c) for c in pal.values()}
    px=frame[frame[...,3]>0][:,:3]
    return sum(1 for p in map(tuple,px) if p not in cols)
