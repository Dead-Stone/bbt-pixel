"""Solve the per-character uniform model scale (char_rig.KSCALE) so the idle-S head top hits TARGET_H (real height ratio).
usage: python fit_heights.py [cid ...]   -> prints KSCALE values"""
import sys, os, subprocess, json
import char_rig as R
def top(cid, k):
    code = ("import sys,numpy as np; sys.argv=['x','%s']; import build_char_sheet as BS; im=BS.frame_img('idle',0,'S');"
            "ys=np.where((im[...,3]>0).any(1))[0]; print(ys[0], ys[-1])" % cid)
    out = subprocess.run([sys.executable, '-c', code], env=dict(os.environ, BBT_K=str(k)), capture_output=True, text=True, cwd=os.path.dirname(__file__) or '.')
    t, b = map(int, out.stdout.split()[-2:]); return t, b
res = {}
for cid in (sys.argv[1:] or list(R.TARGET_H)):
    k = 1.0
    for it in range(3):
        t, b = top(cid, k); h = 116 - t
        if h == R.TARGET_H[cid]: break
        k = round(k * R.TARGET_H[cid] / h, 4)
    t, b = top(cid, k)
    res[cid] = dict(k=k, head_top=t, height_px=116 - t, target=R.TARGET_H[cid], lowest_row=b)
    print(cid, res[cid], flush=True)
json.dump(res, open('/tmp/fit_heights.json', 'w'), indent=1)
