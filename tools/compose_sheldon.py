import numpy as np, math
from sheldon_rig import C, RAMP, MATS
INK = C['ink']
def seg_dist(px, py, a, b):
    ax, ay = a; bx, by = b; dx, dy = bx-ax, by-ay
    h = np.clip(((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy), 0, 1)
    return np.hypot(px-ax-h*dx, py-ay-h*dy)
EMB_C = (0.0, 63.0); EMB_R = 3.9
BOLT = [(1.3, 2.9), (-0.9, 0.2), (0.9, -0.1), (-1.3, -2.9)]   # Z-shaped, asymmetric on purpose
def emblem_code(a, w):
    """0 none, 1 disc, 2 rim, 3 bolt (in viewer coords a=right, w=up)"""
    da, dw = a-EMB_C[0], w-EMB_C[1]; r = np.hypot(da, dw)
    code = np.zeros(a.shape, int)
    code[r < EMB_R] = 1
    code[(r >= EMB_R-0.85) & (r < EMB_R)] = 2
    bd = np.full(a.shape, 9e9)
    for i in range(len(BOLT)-1): bd = np.minimum(bd, seg_dist(da, dw, BOLT[i], BOLT[i+1]))
    code[(r < EMB_R-0.6) & (bd < 0.62)] = 3
    return code

def compose(B, mirror=False, blink=False):
    B = {k: v.copy() for k, v in B.items()}
    if mirror:
        for k in B: B[k] = B[k][:, ::-1].copy()
        B['uv'][..., 0] *= -1; B['hq'][..., 0] *= -1          # decal re-evaluation in true orientation
    mat, tone = B['mat'], B['tone'].copy()
    op = mat >= 0; H, W = mat.shape
    # orphan cleanup: single (mat,tone) pixels surrounded by one other key
    key = np.where(op, mat*4+tone, -1)
    kp = np.pad(key, 1, constant_values=-1)
    nb = np.stack([kp[:-2,1:-1], kp[2:,1:-1], kp[1:-1,:-2], kp[1:-1,2:]], -1)
    for y, x in zip(*np.where(op)):
        n = nb[y, x]
        if (n != key[y, x]).all():
            vals, cnt = np.unique(n, return_counts=True)
            if cnt.max() >= 3 and vals[cnt.argmax()] >= 0 and vals[cnt.argmax()]//4 == mat[y, x]:
                tone[y, x] = vals[cnt.argmax()] % 4
    img = np.zeros((H, W, 4), np.uint8)
    for mi, m in enumerate(MATS):
        for ti in range(3):
            w = op & (mat == mi) & (tone == ti); img[w, :3] = C[RAMP[m][ti]]
    img[op, 3] = 255
    # fringe shadow: 1px skin_sh directly under the hair on the face
    hairm = op & (mat == MATS.index('hair'))
    under = np.zeros_like(op); under[1:] = hairm[:-1]
    fr = under & op & (mat == MATS.index('skin')) & (B['tag'] == 99)
    img[fr, :3] = C['skin_sh']
    # face decals (head-local q of skin pixels)
    q = B['hq']; skin = op & (mat == MATS.index('skin')) & (B['tag'] == 99)
    front = q[..., 1] > 5.5
    for sx in (-3.9, 3.9):
        eye = skin & front & (np.abs(q[..., 0]-sx) < 1.25) & (q[..., 2] > -1.2) & (q[..., 2] < 1.3)
        img[eye, :3] = C['skin_sh'] if blink else C['ink_2']
        brow = skin & front & (np.abs(q[..., 0]-sx*1.05) < 2.2) & (q[..., 2] > 2.6) & (q[..., 2] < 3.7)
        img[brow, :3] = C['hair_sh']
    mouth = skin & (q[..., 1] > 7.0) & (np.abs(q[..., 0]+0.5) < 2.4) & (q[..., 2] > -7.4) & (q[..., 2] < -6.2)
    img[mouth, :3] = C['skin_sh']
    # emblem decal from torso uv
    uv = B['uv']; valid = op & ~np.isnan(uv[..., 0])
    code = np.zeros((H, W), int)
    code[valid] = emblem_code(uv[valid][:, 0], uv[valid][:, 1])
    img[code == 1, :3] = C['emblem']; img[code == 2, :3] = C['emblem_sh']; img[code == 3, :3] = C['tee_sh']
    # interior depth lines: the FARTHER pixel next to a nearer surface gets the material's darkest value
    dep = B['depth']; dp = np.pad(dep, 1, constant_values=1e9)
    near_nb = np.minimum.reduce([dp[:-2,1:-1], dp[2:,1:-1], dp[1:-1,:-2], dp[1:-1,2:]])
    occl = op & (dep - near_nb > 3.5) & (code == 0)
    for mi, m in enumerate(MATS):
        w = occl & (mat == mi); img[w, :3] = C[RAMP[m][3]] if tone is not None else 0
    # silhouette outline: ink, sel-out on top-lit edges
    opp = np.pad(op, 1)
    edge = op & ~(opp[:-2,1:-1] & opp[2:,1:-1] & opp[1:-1,:-2] & opp[1:-1,2:])
    img[edge, :3] = INK
    sel = edge & (B['up'] > 0.55) & np.isin(mat, [MATS.index(m) for m in ('hair', 'skin', 'tee', 'pants')])
    for mi, m in enumerate(MATS):
        w = sel & (mat == mi); img[w, :3] = C[RAMP[m][3]]
    return img
