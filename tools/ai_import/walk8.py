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

python3 tools/ai_import/walk8.py [cid ...]          (default: every cid with a refs_ai/chatgpt/<cid>/walk8_v1.png)
BASE / OVERRIDE: per character, the sheet version per direction (e.g. raj SW, NW from walk8_v2.png; the rest v1)
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


# approved sheet version per character (base) and per-direction overrides from a newer redo sheet (only the
# directions the user approved from that redo; every other direction stays on the base version)
BASE = {}                                   # cid -> 'vN' (default v1)
OVERRIDE = {'raj': {'SW': 'v2', 'NW': 'v2'}, 'bernadette': {'W': 'v2'}, 'howard': {'N': 'v2'}}


def sheet_path(cid, ver):
    return os.path.join(SH.SRC, cid, f'walk8_{ver}.png')


def source(cid):
    p = sheet_path(cid, BASE.get(cid, 'v1'))
    return p if os.path.exists(p) else None


def versions(cid):
    """-> {dir: 'vN'} the sheet version each direction is taken from"""
    return {d: OVERRIDE.get(cid, {}).get(d, BASE.get(cid, 'v1')) for d in ROWS}


def palette_match(fr, ref, bands=6, min_share=0.004):
    """redo frames -> only the colours the reference (base row + idle, same direction) uses in the same height band
    (top..sole split into `bands`): a colour the redo puts somewhere the base never has it (Howard N v2: shirt-back
    highlights quantised to the trouser grey) is replaced by the nearest colour the base uses there. -> (frames, px changed)"""
    def band_of(f):
        A = f[..., 3] > 0; ys = np.nonzero(A.any(1))[0]; y0, y1 = ys[0], ys[-1] + 1
        b = np.full(A.shape[0], -1); b[y0:y1] = np.minimum((np.arange(y1 - y0) * bands) // (y1 - y0), bands - 1); return A, b
    allow = []
    for i in range(bands):
        cols, cnt = [], []
        for f in ref:
            A, b = band_of(f); px = f[..., :3][A & (b[:, None] == i)]
            u, c = np.unique(px.reshape(-1, 3), axis=0, return_counts=True); cols.append(u); cnt.append(c)
        u, inv = np.unique(np.concatenate(cols), axis=0, return_inverse=True); c = np.bincount(inv.ravel(), np.concatenate(cnt))
        allow.append(u[c >= min_share * c.sum()].astype(int))
    out, n = [], 0
    for f in fr:
        f = f.copy(); A, b = band_of(f)
        for i in range(bands):
            m = A & (b[:, None] == i); px = f[..., :3][m].astype(int)
            ok = (px[:, None, :] == allow[i][None]).all(-1).any(1)
            if (~ok).any():
                bad = px[~ok]; j = ((bad[:, None, :] - allow[i][None]) ** 2).sum(-1).argmin(1)
                px[~ok] = allow[i][j]; n += int((~ok).sum()); f[..., :3][m] = px.astype(np.uint8)
        out.append(f)
    return out, n


def row_match(a, b):
    """v1 row vs v2 row of the same direction after normalisation: median height, shoulder width (30 % down), head
    width (8 % down) and mean colour of the body -- so a v1 <-> v2 turn does not pop"""
    def m(fr):
        hs, sw, hw, col = [], [], [], []
        for f in fr:
            A = f[..., 3] > 0; ys = np.nonzero(A.any(1))[0]; y0, h = ys[0], ys[-1] - ys[0]
            w = lambda fy: int(np.ptp(np.nonzero(A[int(y0 + fy * h)])[0])) if A[int(y0 + fy * h)].any() else 0
            hs.append(h); sw.append(w(0.30)); hw.append(w(0.08)); col.append(f[..., :3][A].mean(0))
        return np.median(hs), np.median(sw), np.median(hw), np.mean(col, 0)
    (h1, s1, w1, c1), (h2, s2, w2, c2) = m(a), m(b)
    return dict(height=[float(h1), float(h2)], shoulder_w=[float(s1), float(s2)], head_w=[float(w1), float(w2)],
                colour_delta=round(float(np.abs(c1 - c2).max()), 1))


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


def legs(f):
    """leg band silhouette (bottom 35 % of the figure), x-centred on the torso"""
    A = f[..., 3] > 0; ys = np.nonzero(A.any(1))[0]; yb, yt = ys[-1], ys[0]
    m = np.zeros_like(A); y0 = int(yb - 0.35 * (yb - yt)); m[y0:yb + 1] = A[y0:yb + 1]
    return np.roll(m, 64 - int(round(ST.torso_x(A, 0.25, 0.45))), axis=1)


def iou(a, b):
    return float((a & b).sum() / max(1, (a | b).sum()))


def labels(sp, lo_f=0.5, hi_f=0.5):
    """hi (wide stride) / lo (legs together) / mid per frame, and the cyclic groups of hi and lo (mid ignored)"""
    mn, mx = min(sp), max(sp); r = mx - mn
    lab = ['h' if v >= mn + hi_f * r else 'l' if v <= mn + lo_f * r else 'm' for v in sp]
    seq = [(k, c) for k, c in enumerate(lab) if c != 'm']
    if not seq: return lab, []
    st = next((i for i in range(len(seq)) if seq[i][1] != seq[i - 1][1]), 0)      # start at a group boundary
    seq = seq[st:] + seq[:st]; groups = []
    for k, c in seq:
        if groups and groups[-1][0] == c: groups[-1][1].append(k)
        else: groups.append((c, [k]))
    return lab, groups


def gate(d, fr, idle):
    """per-direction quality gate -> (ok, reasons, contact, passing). Side views (SW/W/NW): the foot spread must
    alternate wide stride / narrow legs-together twice per cycle (2 wide groups + 2 narrow groups) with a clear
    contrast; front/back (S/N, where a stride is depth, not width): the legs must move (leg-band change between
    frames) and the two halves must be different steps. All: height vs idle, torso drift, no repeated neighbours."""
    n = len(fr); why = []
    hs = [_h(f) for f in fr]; hi_ = _h(idle); tx = [ST.torso_x(f[..., 3] > 0, 0.25, 0.45) for f in fr]
    if max(hs) > hi_ + 2 or max(hs) < hi_ - 1: why.append(f'height {min(hs)}-{max(hs)} vs idle {hi_}')
    if min(hs) < hi_ - 5: why.append(f'bob: shortest frame {min(hs)} vs idle {hi_} (> 5 px)')
    # torso band includes the swinging arms, so a few px of 'drift' is arm swing; 8 px is a visible slide
    if max(tx) - min(tx) > 8: why.append(f'torso drift {max(tx) - min(tx):.1f} px')
    dup = [k for k in range(n) if diff_frac(fr[k], fr[(k + 1) % n]) < 0.03]
    if dup: why.append(f'repeated neighbours {dup}')
    sp = [int(_spread(f)) for f in fr]
    if d in ('S', 'N'):
        L = [legs(f) for f in fr]
        mov = [1 - iou(L[k], L[(k + 1) % n]) for k in range(n)]
        if sum(m > 0.12 for m in mov) < n // 2: why.append(f'legs barely move (leg-band change {[round(m, 2) for m in mov]})')
        # front/back: L and R steps are near-mirror silhouettes, so compare pixels (colours) of the leg band
        if n == 8:
            same = [k for k in range(4) if diff_frac(*(np.where(legs(f)[..., None], np.roll(f, 64 - int(round(
                ST.torso_x(f[..., 3] > 0, 0.25, 0.45))), axis=1), 0) for f in (fr[k], fr[k + 4]))) < 0.05]
            if len(same) >= 2: why.append(f'the two steps are the same drawing (frames {same} vs +4)')
        return not why, why, ([0, 4] if n == 8 else [0, 2]), ([2, 6] if n == 8 else [1, 3]), sp
    lab, groups = labels(sp)
    hg = [g for c, g in groups if c == 'h']; lg = [g for c, g in groups if c == 'l']
    if len(hg) != 2 or len(lg) != 2:
        why.append(f'spread {sp} does not alternate stride/pass twice ({"".join(lab)})')
        return False, why, None, None, sp
    A = sorted(max(g, key=lambda k: sp[k]) for g in hg); P = sorted(min(g, key=lambda k: sp[k]) for g in lg)
    c = min(sp[k] for k in A) - max(sp[k] for k in P)
    if c < max(5, 0.15 * max(sp[k] for k in A)): why.append(f'weak stride/pass contrast {c} px (spread {sp})')
    return not why, why, A, P, sp


def pick4(d, fr, idle):
    """simple fix: a stride, pass, stride, pass subset of the drawn frames (in drawn order) that passes the gate,
    the two strides being different drawings (left / right leg)"""
    best = None; n = len(fr)
    if d not in ('S', 'N'):
        lab, groups = labels([int(_spread(f)) for f in fr])
        if sum(c == 'h' for c, _ in groups) != 2: return None      # e.g. a kick every other frame: not a 2-step walk
    for r in range(n):
        for a, b, c, e in [(0, 1, 2, 3), (0, 2, 4, 6), (0, 1, 4, 5), (0, 2, 4, 5), (0, 1, 4, 6), (0, 2, 3, 6), (0, 3, 4, 7)]:
            ks = [(r + x) % n for x in (a, b, c, e)]
            if len(set(ks)) < 4: continue
            sub = [fr[k] for k in ks]
            if diff_frac(sub[0], sub[2]) < 0.15: continue
            ok, why, A, P, sp = gate(d, sub, idle)
            if ok and A == [0, 2] and P == [1, 3]:
                sc = min(sp[0], sp[2]) - max(sp[1], sp[3])
                if best is None or sc > best[0]: best = (sc, ks)
    return best[1] if best else None


def process(cid, path):
    kind = os.path.splitext(os.path.basename(path))[0]
    SH.NCOL_X[kind] = 8
    cuts = SH.cut_sheet(cid, kind)
    stills, pal = SH.load_stills(cid); idle = idle_neutral(cid)
    # per-row scale: the tallest frame of each row (passing, body up) -> idle neutral height of that direction (+1)
    # (if a frame is drawn > 3 % taller than the row median -- e.g. Howard W passing frames -- scale by the median
    # instead and cap each frame at idle + 2, so one tall drawing does not shrink the whole row)
    per_row, per_fr = {}, {}
    for d in ROWS:
        hs = [c.shape[0] for c in cuts[d]]; ih = _h(idle[d]); med = float(np.median(hs))
        if max(hs) <= 1.03 * med:
            per_row[d] = (ih + 1) / max(hs); per_fr[d] = [per_row[d]] * len(hs)
        else:
            per_row[d] = (ih + 0.5) / med; per_fr[d] = [min(per_row[d], (ih + 2) / h) for h in hs]
    rows, extra = {}, {}
    for d in ROWS:
        fr = [SH.frame128(c, s_, stills[d], pal, 'stand') for c, s_ in zip(cuts[d], per_fr[d])]
        ti = ST.torso_x(idle[d][..., 3] > 0, 0.25, 0.45)
        dx = int(round(ti - np.median([ST.torso_x(f[..., 3] > 0, 0.25, 0.45) for f in fr])))
        fr = head_lock([np.roll(f, dx, axis=1) for f in fr])
        rows[d] = [audit_fix(f, pal) for f in fr]          # the paste + shift can leave a speck at the seams
        extra[d] = dict(row_scale=round(per_row[d], 4), shift_x=dx, idle_torso_x=float(ti))
    return rows, extra, idle, pal, per_row


def fringe(fr, pal_rgb=None):
    """fraction of the 2-px inner edge ring that is magenta-ish (min(r, b) - g > 40) -- key / despill leftovers"""
    tot = bad = 0
    import scipy.ndimage as nd
    for f in fr:
        A = f[..., 3] > 0; ring = A & ~nd.binary_erosion(A, iterations=2)
        c = f[..., :3].astype(int); m = np.minimum(c[..., 0], c[..., 2]) - c[..., 1]
        tot += ring.sum(); bad += (ring & (m > 40)).sum()
    return bad / max(1, tot)


def build(cid, path=None, only8=None):
    """only8: directions forced to stay on the drawn 8 frames (None = gate decides). Directions in OVERRIDE[cid]
    come from that redo sheet if its row passes the gate; otherwise they keep the base sheet's fallback."""
    path = path or source(cid)
    rows, extra, idle, pal, per_row = process(cid, path)
    vers = versions(cid); base_v = BASE.get(cid, 'v1'); red = {}
    for v in sorted(set(vers.values()) - {base_v}):
        rv, ev, _, _, sv = process(cid, sheet_path(cid, v)); red[v] = (rv, ev, sv)
    sys.path.insert(0, HERE); import walk_cycle as WC
    j0, row0 = WC.load(cid)
    use, info = {}, {}
    for d in ROWS:
        v = vers[d]; redo = None
        if v != base_v:
            rv, ev, sv = red[v]; rv[d], npm = palette_match(rv[d], rows[d] + [idle[d]])
            rv[d] = [audit_fix(f, pal) for f in rv[d]]                 # re-snap specks the remap can leave
            ok2, why2, A2, P2, sp2 = gate(d, rv[d], idle[d])
            redo = dict(version=v, gate=('pass' if ok2 else 'fail'), why=why2, spread=sp2, match_base=row_match(rows[d], rv[d]),
                        fringe=round(float(fringe(rv[d])), 4), row_scale=round(float(sv[d]), 4), palette_px_fixed=npm)
            if ok2: rows[d], extra[d] = rv[d], ev[d]          # the redo row replaces the base row
        fr = rows[d]; ok, why, A, P, sp = gate(d, fr, idle[d])
        hs = [_h(f) for f in fr]; tx = [ST.torso_x(f[..., 3] > 0, 0.25, 0.45) for f in fr]
        rec = dict(height=[int(min(hs)), int(max(hs))], idle_height=int(_h(idle[d])), torso_x=[round(float(min(tx)), 1), round(float(max(tx)), 1)],
                   spread=sp, idle_spread=int(_spread(idle[d])), gate_8=('pass' if ok else 'fail'), gate_8_why=why,
                   fringe=round(fringe(fr), 4), idle_fringe=round(fringe([idle[d]]), 4), **extra[d])
        if ok:
            use[d] = dict(mode='walk8', frames=fr, contact=A, passing=P, src=list(range(8)))
        else:
            ks = pick4(d, fr, idle[d])
            if ks:
                sub = [fr[k] for k in ks]; _, _, A4, P4, _ = gate(d, sub, idle[d])
                use[d] = dict(mode='pick4', frames=sub, contact=A4, passing=P4, src=ks)
            else:
                f4, cinfo = WC.cycle(d, row0(f'walk_{d}'), row0(f'idle_{d}')[0], pal)
                use[d] = dict(mode='synth4', frames=f4, contact=[0, 2], passing=[1, 3], src='walk_cycle.py (chr_%s.json walk_%s)' % (cid, d))
        rec.update(mode=use[d]['mode'], contact=use[d]['contact'], passing=use[d]['passing'], frames_from=use[d]['src'],
                   sheet=(redo['version'] if redo and redo['gate'] == 'pass' else base_v) if use[d]['mode'] != 'synth4' else 'main')
        if redo: rec['redo'] = redo
        info[d] = rec
    # stride: W contact frames of the drawn sheet when W uses them, else the main sheet's measured stride
    if use['W']['mode'] != 'synth4':
        stride = float(np.mean([stride_px(use['W']['frames'][k]) for k in use['W']['contact']]))
    else:
        stride = float(j0['meta'].get('walk_stride_px') or 26.0)
    cells, frames, tags, mpp, pp = [], [], [], {}, {}
    for r, d in enumerate(DIRS):
        u = use[MIRROR.get(d, d)]; a = len(frames)
        for k, f in enumerate(u['frames']):
            frames.append(dict(filename=f'chr_{cid}_walk_{d}_{k:02d}', frame=dict(x=k * 128, y=r * 128, w=128, h=128), duration=FRAME_MS))
            cells.append((r, k, mirror(f) if d in MIRROR else f))
        tags.append(dict(name=f'walk_{d}', **{'from': a, 'to': len(frames) - 1}, direction='forward'))
        n = len(u['frames']); mpp[d] = round(2 * stride / PX_PER_M / n, 4)       # every cycle = 2 steps
        if u['mode'] == 'synth4': mpp[d] = round(stride / 2 / PX_PER_M, 4)
        pp[d] = u['passing']
    sheet = np.zeros((len(DIRS) * 128, 8 * 128, 4), np.uint8)
    for r, k, c in cells: sheet[r * 128:(r + 1) * 128, k * 128:(k + 1) * 128] = c
    od = os.path.join(ROOT, 'characters', cid, 'ai')
    Image.fromarray(sheet).save(os.path.join(od, f'chr_{cid}_walk.png'))
    meta = dict(app='bbt-pixel/tools/ai_import/walk8.py', image=f'chr_{cid}_walk.png', size=dict(w=sheet.shape[1], h=sheet.shape[0]),
                frameTags=tags, frames_per_cycle={d: len(use[MIRROR.get(d, d)]['frames']) for d in DIRS}, steps_per_cycle=2, pivot=[64, 116],
                row_scale={d: round(v, 4) for d, v in per_row.items()}, walk_stride_px=round(stride, 1),
                walk_m_per_pose=mpp['W'], walk_m_per_pose_dir=mpp, pass_poses=pp, source=os.path.relpath(path, ROOT),
                source_dir={d: os.path.relpath(sheet_path(cid, info[d]['sheet']), ROOT) if info[d]['sheet'] != 'main' else 'walk_cycle.py' for d in ROWS},
                rows={d: {k: v for k, v in info[d].items()} for d in ROWS},
                note='ChatGPT 8-frame walk (07_walk_8frame.txt) per direction where it passes the gate (walk8.gate); '
                     'pick4 = a stride/pass/stride/pass subset of the drawn frames; synth4 = walk_cycle.py fallback; NE/E/SE mirror NW/W/SW')
    json.dump(dict(frames=frames, meta=meta), open(os.path.join(od, f'chr_{cid}_walk.json'), 'w'), indent=1)
    return meta, info


if __name__ == '__main__':
    cids = sys.argv[1:] or [c for c in ['sheldon', 'leonard', 'penny', 'howard', 'raj', 'bernadette', 'amy'] if source(c)]
    for cid in cids:
        m, info = build(cid)
        print(f"{cid}: {m['source']} stride {m['walk_stride_px']} px -> W {m['walk_m_per_pose']} m/frame")
        for d in ROWS:
            r = info[d]
            print(f"  {d:2} {r['mode']:6} gate8 {r['gate_8']:4} frames {r['frames_from']} contact {r['contact']} pass {r['passing']} "
                  f"h {r['height']} idle {r['idle_height']} torso {r['torso_x']} spread {r['spread']} (idle {r['idle_spread']}) "
                  f"fringe {r['fringe']} (idle {r['idle_fringe']}) sheet {r['sheet']} {'; '.join(r['gate_8_why'])}")
            if 'redo' in r: print(f"     redo {r['redo']}")
