"""8-frame ChatGPT walk sheet -> the viewer's walk sheet (replaces walk_cycle.py's synthesized 4-pose cycle)

Input : refs_ai/chatgpt/<cid>/walk8_v<N>.png (newest N), prompt docs/chatgpt_prompts/07_walk_8frame.txt:
        magenta bg, 5 rows S, SW, W, NW, N x 8 frames (contact L, down, passing, up, contact R, down, passing, up)
Output: characters/<cid>/ai/chr_<cid>_walk.png/.json -- 8 dirs x 8 frames, 128 x 128, pivot (64, 116), soles on row 119,
        tags walk_<d>; NE/E/SE mirror NW/W/SW (build.mirror, pivot column kept)

Pipeline (same as the other AI sheets, sheets.py): magenta key + despill, cell cut, a scale per row that locks the row's
tallest (passing) frame to the character's idle (neutral) height in that direction (+1 px: the passing-pose rise), so
walk <-> idle never pops in size (ChatGPT draws the rows a few % apart), area resize, the character's palette
(bbt_<cid>_ai.gpl) + outline + pixfix + audit_fix, soles on 119, head x on the turnaround still's head x, then the whole
row shifted so its median torso x = the idle torso x (no sideways hop at walk <-> idle); then full.head_lock (one head
per row: no face boil, bob kept within +-2 px) and a final convert.audit_fix pass (tools/v2/audit.py: 0 issues).
Meta: walk_m_per_pose = 2 steps / 8 frames, step = the W row's contact stride (feet centres, px) / 90.5 px per metre
(side view), so the viewer advances one frame per walk_m_per_pose metres and the planted foot does not slide;
contact / pass frames are measured (leg spread) and written so the viewer starts and settles on a passing frame.

python3 tools/ai_import/walk8.py [cid ...]          (default: every cid with a refs_ai/chatgpt/<cid>/walk8_v*.png)
Checks it prints per row: height range vs idle, torso-x drift, near-duplicate neighbours, contact / pass frames."""
import os, sys, re, glob, json, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import sheets as SH, sit as ST
from build import DIRS, MIRROR, mirror
from full import head_lock, _spread, _h
from convert import audit_fix

ROWS = ['S', 'SW', 'W', 'NW', 'N']; PX_PER_M = 90.5; FRAME_MS = 100


def source(cid):
    fs = sorted(glob.glob(os.path.join(SH.SRC, cid, 'walk8_v*.png')), key=lambda p: int(re.findall(r'_v(\d+)', p)[-1]))
    return fs[-1] if fs else None


def idle_neutral(cid):
    od = os.path.join(ROOT, 'characters', cid, 'ai')
    j = json.load(open(os.path.join(od, f'chr_{cid}.json'))); im = np.asarray(Image.open(os.path.join(od, f'chr_{cid}.png')).convert('RGBA'))
    tags = {t['name']: t['from'] for t in j['meta']['frameTags']}
    out = {}
    for d in ROWS:
        r = j['frames'][tags[f'idle_{d}']]['frame']; out[d] = im[r['y']:r['y'] + 128, r['x']:r['x'] + 128].copy()
    return out


def stride_px(f):
    """feet-centre distance in a side-view contact frame (bottom 4 rows)"""
    A = f[..., 3] > 0; y1 = np.nonzero(A.any(1))[0][-1]
    cols = np.nonzero(A[y1 - 3:y1 + 1].any(0))[0]; gaps = np.nonzero(np.diff(cols) > 1)[0]
    if len(gaps): return float(cols[gaps[-1] + 1:].mean() - cols[:gaps[0] + 1].mean())
    return float(_spread(f) - 12)


def diff_frac(a, b):
    m = (a[..., 3] > 0) | (b[..., 3] > 0)
    return float(((np.abs(a.astype(int) - b.astype(int)).sum(-1) > 30) & m).sum() / max(1, m.sum()))


def build(cid, path=None):
    path = path or source(cid); kind = os.path.splitext(os.path.basename(path))[0]
    SH.NCOL_X[kind] = 8
    cuts = SH.cut_sheet(cid, kind)
    stills, pal = SH.load_stills(cid); idle = idle_neutral(cid)
    # one sheet-wide scale: the tallest frame of each row (passing, body up) -> idle neutral height of that direction
    per_row = {d: (_h(idle[d]) + 1) / max(c.shape[0] for c in cuts[d]) for d in ROWS}
    s = float(np.median(list(per_row.values())))
    rows, info = {}, {}
    for d in ROWS:
        fr = [SH.frame128(c, per_row[d], stills[d], pal, 'stand') for c in cuts[d]]
        ti = ST.torso_x(idle[d][..., 3] > 0, 0.25, 0.45)
        dx = int(round(ti - np.median([ST.torso_x(f[..., 3] > 0, 0.25, 0.45) for f in fr])))
        fr = head_lock([np.roll(f, dx, axis=1) for f in fr])
        fr = [audit_fix(f, pal) for f in fr]          # the paste + shift can leave a speck at the seams
        hs = [_h(f) for f in fr]; sp = [_spread(f) for f in fr]
        tx = [ST.torso_x(f[..., 3] > 0, 0.25, 0.45) for f in fr]
        dup = [k for k in range(8) if diff_frac(fr[k], fr[(k + 1) % 8]) < 0.03]
        half = [round(diff_frac(fr[k], fr[k + 4]), 3) for k in range(4)]     # L vs R half: ~0 = the same drawing twice
        side = d not in ('S', 'N')
        c0 = int(np.argmax(sp[:4])) if side else 0; c1 = 4 + int(np.argmax(sp[4:])) if side else 4
        p0 = int(np.argmin(sp[:4])) if side else 2; p1 = 4 + int(np.argmin(sp[4:])) if side else 6
        rows[d] = fr
        info[d] = dict(height=[int(min(hs)), int(max(hs))], idle_height=int(_h(idle[d])), row_scale=round(per_row[d], 4),
                       torso_x=[round(float(min(tx)), 1), round(float(max(tx)), 1)], idle_torso_x=float(ti), shift_x=dx, spread=[int(v) for v in sp], half_diff=half, contact=[c0, c1], passing=[p0, p1],
                       near_duplicates=[[k, (k + 1) % 8] for k in dup])
    stride = float(np.mean([stride_px(rows['W'][k]) for k in info['W']['contact']]))
    cells, frames, tags = [], [], []
    for d in DIRS:
        a = len(cells)
        for k, f in enumerate(rows[MIRROR.get(d, d)]):
            i = len(cells); cells.append(mirror(f) if d in MIRROR else f)
            frames.append(dict(filename=f'chr_{cid}_walk_{d}_{k:02d}', frame=dict(x=(i % 8) * 128, y=(i // 8) * 128, w=128, h=128), duration=FRAME_MS))
        tags.append(dict(name=f'walk_{d}', **{'from': a, 'to': len(cells) - 1}, direction='forward'))
    sheet = np.zeros((len(DIRS) * 128, 8 * 128, 4), np.uint8)
    for i, c in enumerate(cells): sheet[(i // 8) * 128:(i // 8 + 1) * 128, (i % 8) * 128:(i % 8 + 1) * 128] = c
    od = os.path.join(ROOT, 'characters', cid, 'ai')
    Image.fromarray(sheet).save(os.path.join(od, f'chr_{cid}_walk.png'))
    pp = {d: info[MIRROR.get(d, d)]['passing'] for d in DIRS}
    meta = dict(app='bbt-pixel/tools/ai_import/walk8.py', image=f'chr_{cid}_walk.png', size=dict(w=sheet.shape[1], h=sheet.shape[0]),
                frameTags=tags, frames_per_cycle=8, steps_per_cycle=2, pivot=[64, 116], scale=round(s, 4), row_scale={d: round(v, 4) for d, v in per_row.items()},
                walk_stride_px=round(stride, 1), walk_m_per_pose=round(2 * stride / PX_PER_M / 8, 4),
                pass_poses=pp, source=os.path.relpath(path, ROOT), rows={d: {k: v for k, v in info[d].items() if k != 'spread'} for d in ROWS},
                note='ChatGPT 8-frame walk (07_walk_8frame.txt), NE/E/SE mirror NW/W/SW')
    json.dump(dict(frames=frames, meta=meta), open(os.path.join(od, f'chr_{cid}_walk.json'), 'w'), indent=1)
    return meta, info


if __name__ == '__main__':
    cids = sys.argv[1:] or [c for c in ['sheldon', 'leonard', 'penny', 'howard', 'raj', 'bernadette', 'amy'] if source(c)]
    for cid in cids:
        m, info = build(cid)
        print(f"{cid}: {m['source']} scale {m['scale']} stride {m['walk_stride_px']} px -> {m['walk_m_per_pose']} m/frame "
              f"({2 * m['walk_stride_px'] / PX_PER_M:.3f} m per cycle of 2 steps)")
        for d in ROWS:
            r = info[d]; print(f"  {d:2} h {r['height']} idle {r['idle_height']} (row scale {r['row_scale']}) torso_x {r['torso_x']} "
                               f"spread {r['spread']} contact {r['contact']} pass {r['passing']} dup {r['near_duplicates']} L/R-half diff {r['half_diff']} shift {r['shift_x']}")
