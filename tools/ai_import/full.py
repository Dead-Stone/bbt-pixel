"""ChatGPT action sheets (refs_ai/chatgpt/<cid>/{idle_actions,signature,sit,walk,work}.png, see sheets.py) ->
the character's full AI sheet characters/<cid>/ai/chr_<cid>.png/.json + the AI sit sheet characters/<cid>/chr_<cid>_sit.*

python3 tools/ai_import/full.py <cid> [conv.pkl]      (conv.pkl: a cached sheets.convert() result)

Tags (8 dirs each; SE/E/NE mirror SW/W/NW about column 64):
  stand_<d>            the turnaround still (unchanged)
  idle_<d>             still + 1-px breath + blink (unchanged, idle.py)
  walk_<d>             walk.png row, 8 frames x 100 ms, frame 0's head pasted on all 8 (head_lock: walk.head_lock + bob limit)
  act_think|talk|eat|drink|phone_<d>   idle_actions.png columns 0-4, pose + 1-px breath (2 x 600 ms)
  talk_<d>             talk gesture <-> neutral (idle_actions columns 1 / 5), 4 x 400 ms, loops while speaking
  work_<d>             work.png row (WORK_COLS), 300 ms; the drawn prop is stripped (sheets.strip_props) because
                       the env already draws the bench / whiteboard / table at the work hook
  work_<d> (Howard)    work_stand.png, standing gadget tinkering; work_desk_<d> = his seated laptop-desk frames (no sim hook seats him for work)
  chr_<cid>_sit.png    row 0 = sit (sit.png variant 0); extra rows sit_eat (4 frames, all) and sit_write (Sheldon), same seat anchor
  <emote>_<d>          the rig's emote names, built from signature.png / idle_actions.png columns (EMOTES)
  gesture_<d>          generic talk gesture (all characters)
"""
import os, sys, json, pickle, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import convert as CV, idle as I, sheets as SH, sit as ST, walk as WK
from build import DIRS, MIRROR, mirror

ACT = dict(think=0, talk=1, eat=2, drink=3, phone=4)
NEUTRAL = 5
# work.png columns used in the loop (frames that kept a piece of the drawn table / board after stripping are left out)
WORK_COLS = dict(sheldon=[0, 1, 2, 3, 4], leonard=[0, 1, 2, 3, 4, 5], penny=[0, 1, 2, 5], howard=None,
                 raj=[0, 1, 2, 3, 4, 5], bernadette=[0, 1, 2, 3, 4, 5], amy=[0, 1, 2, 3, 4, 5])
# directions whose work.png frames are unusable after prop stripping (Leonard's back views: head hidden behind the
# shoulders / table plate left in his hands; Amy's S/SW/W: the microscope table is drawn through her legs) -> think/phone loop
WORK_ALT = dict(leonard={'NW', 'N'}, amy={'S', 'SW', 'W'})
# Howard's work hooks are all standing (electronics bench, rover): work = work_stand.png (gadget tinkering); work_desk keeps the seated laptop frames
# emote -> [(sheet, column, ms), ...]
S_, A_ = 'signature', 'idle_actions'
EMOTES = dict(
    sheldon=dict(knock_knock_penny=[(S_, c, 300) for c in range(6)],
                 point_gotcha=[(A_, 1, 500), (A_, 5, 200), (A_, 1, 500)], spot_claim=[(A_, 0, 900), (A_, 1, 700)]),
    leonard=dict(glasses_push=[(S_, 1, 500), (S_, 2, 600), (S_, 1, 300)], sigh_shrug=[(S_, 3, 300), (S_, 5, 1000), (S_, 3, 300)],
                 wave=[(S_, 0, 400), (S_, 4, 200), (S_, 0, 400)]),
    penny=dict(hair_flip=[(S_, 0, 200), (S_, 1, 300), (S_, 2, 600), (S_, 3, 300)], wine_sip=[(S_, 4, 500), (S_, 5, 900), (S_, 4, 400)],
               eye_roll=[(A_, 0, 1200), (S_, 0, 400)]),
    howard=dict(magic_trick=[(S_, c, 300) for c in range(6)], eyebrow_waggle=[(A_, 1, 400), (A_, 5, 200), (A_, 1, 400), (A_, 5, 200)]),
    raj=dict(astronomy_point=[(S_, 1, 400), (S_, 2, 900), (S_, 1, 300)], shy_hands=[(S_, 5, 1400)], cheer=[(S_, 3, 900)]),
    bernadette=dict(sweet_to_scary=[(S_, c, 330) for c in range(6)], hands_on_hips=[(S_, 4, 1500)]),
    amy=dict(neuro_lecture=[(S_, 1, 400), (S_, 2, 500), (S_, 3, 500), (S_, 2, 400)], excited_clap=[(A_, 1, 400), (S_, 1, 400), (A_, 1, 400)]),
)

# per-emote source direction swaps: Sheldon's S knock cells barely show the arm -> S plays the SW knock cells
EMOTE_DIR = {('sheldon', 'knock_knock_penny'): {'S': 'SW'}}


def head_lock(frames, extra=2):
    """walk.head_lock with a bob limit: frame 0's head is pasted on every frame (best |d|<=2 fit), and the paste row
    (and column shift) moves at most 2 px from the previous frame's, so the head never jumps more than the audit's +-2 window"""
    f0 = frames[0]; A0 = f0[..., 3] > 0
    ys = np.nonzero(A0.any(1))[0]; c0 = ys[0]; hr = int(round((ys[-1] - ys[0]) / 6.5)) + extra
    win0 = f0[c0:c0 + hr]; out = [f0]; prev = c0; pdx = 0
    for f in frames[1:]:
        c = np.nonzero((f[..., 3] > 0).any(1))[0][0]; best = None
        for y in range(c - 2, c + 3):
            if y < 0 or abs(y - prev) > 2: continue
            for dx in range(-2, 3):
                if abs(dx - pdx) > 2: continue
                cand = np.roll(win0, dx, axis=1); tgt = f[y:y + hr]
                both = (cand[..., 3] > 0) | (tgt[..., 3] > 0)
                d = (np.abs(cand.astype(int) - tgt.astype(int)).sum(-1) > 30)[both].sum() + 40 * abs(y - c)
                if best is None or d < best[0]: best = (d, y, dx)
        if best is None: best = (0, prev + int(np.clip(c - prev, -2, 2)), 0)
        _, y, dx = best
        g = f.copy(); g[y:y + hr] = np.roll(win0, dx, axis=1); out.append(g); prev = y; pdx = dx
    return out


def _h(f):
    ys = np.nonzero((f[..., 3] > 0).any(1))[0]; return ys[-1] - ys[0]


def _spread(f):
    """leg spread: width of the bottom 15 rows"""
    A = f[..., 3] > 0; y1 = np.nonzero(A.any(1))[0][-1]; xs = np.nonzero(A[y1 - 14:y1 + 1].any(0))[0]
    return xs.max() - xs.min()


def _torso(f):
    return ST.torso_x(f[..., 3] > 0, 0.25, 0.45)


def _rescale(f, k):
    """nearest-neighbour rescale of the figure about its bottom-centre (soles stay on the cell's sole row)"""
    A = f[..., 3] > 0; ys = np.nonzero(A.any(1))[0]; xs = np.nonzero(A.any(0))[0]
    y0, y1, x0, x1 = ys[0], ys[-1] + 1, xs[0], xs[-1] + 1
    cx = _torso(f); crop = Image.fromarray(f[y0:y1, x0:x1])
    w, h = max(1, round((x1 - x0) * k)), max(1, round((y1 - y0) * k))
    g = np.array(crop.resize((w, h), Image.NEAREST)); out = np.zeros_like(f)
    nx0 = int(round(cx - (cx - x0) * k)); ny0 = y1 - h
    out[ny0:y1, nx0:nx0 + w] = g
    return out


def _shift(f, dx):
    return np.roll(f, int(dx), axis=1)


def _runs(row):
    xs = np.nonzero(row)[0]
    if not len(xs): return []
    br = np.nonzero(np.diff(xs) > 1)[0]
    return [(int(a), int(b) + 1) for a, b in zip(np.r_[xs[0], xs[br + 1]], np.r_[xs[br], xs[-1]])]


def _close_legs(f, D):
    """passing pose from a stride frame: below the crotch the back and front leg runs are sheared towards each other,
    0 px at the crotch -> D px at the soles (shoes keep their width; the right-hand leg is drawn first)"""
    D = int(round(D))
    if D <= 0: return f
    A = f[..., 3] > 0; ys = np.nonzero(A.any(1))[0]; yb = ys[-1]; yt = ys[0]
    yc = None; seen2 = False
    for y in range(yb, yt + int((yb - yt) * 0.55), -1):      # lowest row (above the feet) where the legs are one run
        n2 = len(_runs(A[y])) >= 2
        if n2: seen2 = True
        elif seen2: yc = y; break
    if yc is None or yb - yc < 6: return f
    out = f.copy(); out[yc + 1:yb + 1] = 0
    for y in range(yc + 1, yb + 1):
        r = _runs(A[y]); s = int(round(D * (y - yc) / (yb - yc)))
        if len(r) < 2:
            out[y] = f[y]; continue
        mid = (r[0][1] + r[-1][0]) / 2.0
        L = [q for q in r if (q[0] + q[1]) / 2 < mid]; R = [q for q in r if (q[0] + q[1]) / 2 >= mid]
        for (a, b) in R: out[y, a - s:b - s] = np.where(f[y, a:b, 3:] > 0, f[y, a:b], out[y, a - s:b - s])
        for (a, b) in L: out[y, a + s:b + s] = np.where(f[y, a:b, 3:] > 0, f[y, a:b], out[y, a + s:b + s])
    return out


def walk_row(out, d):
    """walk.png row -> 8 walk frames, fixed for the viewer's distance-driven playback:
    * scale: rows drawn bigger than the same direction's neutral pose (N/NW back views, up to +7 %) are scaled to the
      neutral height, so walk -> idle (= neutral) never pops in size;
    * passing pose: side-view (W/E) rows where ChatGPT drew every frame as a wide stride (legs never close, so the
      figure scissor-glides) get their legs sheared together below the crotch with weights 0, .5, 1, .5, 0, .5, 1, .5
      (contact, down, PASS, up, contact, ...) -- a real contact-pass-contact cycle in the same art.
    Returns (frames, stride_px, pass_index)."""
    W = [f.copy() for f in out['walk'][d]]; n = out[A_][d][NEUTRAL]
    hw = float(np.median([_h(f) for f in W])); hn = _h(n)
    if abs(hw / hn - 1) > 0.025: W = [_rescale(f, hn / hw) for f in W]
    sp = [_spread(f) for f in W]; sn = _spread(n)
    closure = (min(sp) - sn) / max(1e-6, max(sp) - sn)
    if closure > 0.5 and d in ('W', 'SW'):
        sh = [0, .5, 1, .5, 0, .5, 1, .5]
        W = [_close_legs(f, a * max(0.0, (_spread(f) - sn - 2) / 2.0)) for f, a in zip(W, sh)]
        sp = [_spread(f) for f in W]
    stride = None
    if d == 'W':   # feet centres of the widest (contact) frames, bottom 4 rows
        A = W[int(np.argmax(sp))][..., 3] > 0; y1 = np.nonzero(A.any(1))[0][-1]
        cols = np.nonzero(A[y1 - 3:y1 + 1].any(0))[0]; gaps = np.nonzero(np.diff(cols) > 1)[0]
        if len(gaps): stride = float(cols[gaps[-1] + 1:].mean() - cols[:gaps[0] + 1].mean())
        else: stride = float(max(sp) - 12)
    return W, stride, int(np.argmin(sp))


def build(cid, conv):
    out, stills, pal = conv
    od = os.path.join(ROOT, 'characters', cid, 'ai')
    old = json.load(open(os.path.join(od, f'chr_{cid}.json')))
    base = I.skin_of(stills['S'], I.SKIN_AT[cid]); eyes = I.EYES.get(cid, {})
    cells, frames, tags = [], [], []

    def add(name, img, dur):
        i = len(cells); cells.append(CV.audit_fix(img.copy(), pal))
        frames.append(dict(filename=f'chr_{cid}_{name}', frame=dict(x=(i % 16) * 128, y=(i // 16) * 128, w=128, h=128),
                           rotated=False, trimmed=False, spriteSourceSize=dict(x=0, y=0, w=128, h=128),
                           sourceSize=dict(w=128, h=128), duration=dur))
        return i

    def seq(name, per_dir):
        """per_dir(d5) -> [(img, ms)] for S/SW/W/NW/N; mirrored for NE/E/SE"""
        for d in DIRS:
            src = MIRROR.get(d, d); fr = per_dir(src)
            ids = [add(f'{name}_{d}_{k:02d}', mirror(f) if d in MIRROR else f, ms) for k, (f, ms) in enumerate(fr)]
            tags.append(dict(name=f'{name}_{d}', **{'from': ids[0], 'to': ids[-1]}, direction='forward'))

    seq('stand', lambda d: [(stills[d], 250)])
    # idle = the action sheets' neutral pose (+1-px breath): same art, scale and proportions as walk / act_* / talk,
    # so walk -> idle and idle -> act never swap drawing styles (the turnaround still stays as 'stand')
    seq('idle', lambda d: [(out[A_][d][NEUTRAL], 1400), (I.breathe(out[A_][d][NEUTRAL]), 1100)])
    WR = {d: walk_row(out, d) for d in ['S', 'SW', 'W', 'NW', 'N']}
    seq('walk', lambda d: [(f, 100) for f in head_lock(WR[d][0])])   # one head per row: no face boil
    for a, c in ACT.items():
        seq(f'act_{a}', lambda d, c=c: [(out[A_][d][c], 600), (I.breathe(out[A_][d][c]), 600)])
    seq('talk', lambda d: [(out[A_][d][1], 400), (out[A_][d][NEUTRAL], 400), (I.breathe(out[A_][d][1]), 400), (out[A_][d][NEUTRAL], 400)])
    seq('gesture', lambda d: [(out[A_][d][1], 500), (out[A_][d][NEUTRAL], 200), (out[A_][d][1], 600)])
    ph = lambda d: out[A_][d][ACT['phone']]; th = lambda d: out[A_][d][ACT['think']]
    # think <-> phone loop: desk work (viewer: desk / laptop hooks) and the work directions whose drawn frames are unusable
    desk = lambda d: [(th(d), 1300), (I.breathe(th(d)), 1000), (ph(d), 1300), (I.breathe(ph(d)), 1000)]
    if WORK_COLS[cid]:
        seq('work', lambda d: desk(d) if d in WORK_ALT.get(cid, ()) else [(out['work'][d][c], 300) for c in WORK_COLS[cid]])
    elif 'work_stand' in out:   # Howard: work_stand.png -- standing, tinkering with a handheld gadget (4 frames)
        seq('work', lambda d: [(f, ms) for f, ms in zip(out['work_stand'][d], (450, 350, 450, 350))])
        seq('work_desk', lambda d: [(f, 300) for f in out['work'][d]])
    else:   # Howard without work_stand.png: standing tinker loop (phone-sized gadget in hand, the odd explaining gesture)
        seq('work', lambda d: [(ph(d), 900), (I.breathe(ph(d)), 700), (ph(d), 600), (out[A_][d][ACT['talk']], 700)])
        seq('work_desk', lambda d: [(f, 300) for f in out['work'][d]])
    seq('desk', desk)
    for em, spec in EMOTES[cid].items():
        sub = EMOTE_DIR.get((cid, em), {})
        seq(em, lambda d, spec=spec, sub=sub: [(out[k][sub.get(d, d)][c], ms) for k, c, ms in spec])

    n = len(cells); rows = (n + 15) // 16
    sheet = np.zeros((rows * 128, 16 * 128, 4), np.uint8)
    for i, c in enumerate(cells): sheet[(i // 16) * 128:(i // 16 + 1) * 128, (i % 16) * 128:(i % 16 + 1) * 128] = c
    Image.fromarray(sheet).save(os.path.join(od, f'chr_{cid}.png'))
    meta = old['meta']
    meta.update(app='bbt-pixel/tools/ai_import/full.py', version='ai2', size=dict(w=sheet.shape[1], h=sheet.shape[0]), frameTags=tags,
                source_actions=f'refs_ai/chatgpt/{cid}/{{idle_actions,signature,sit,walk,work}}.png (ChatGPT sprite sheets; '
                               'rows S, SW, W, NW, N on magenta) via tools/ai_import/sheets.py',
                scales=json.load(open(SH.SCALES))[cid],
                note='stand = turnaround still; idle = breath + blink; walk/act_*/talk/gesture/work/emotes = ChatGPT action '
                     'sheets, one shared palette (bbt_%s_ai.gpl), heights normalised to the turnaround by crown/head matching '
                     '(sheets.py). Work frames: the drawn prop (bench/whiteboard/table/telescope/microscope/door) is stripped and '
                     'the frame stays 128x128 -- the env already draws the furniture at every work hook.' % cid)
    meta.pop('source_walk', None)
    # viewer walk playback: one 8-frame cycle = 2 steps = 2 x stride (px, side view, 90.5 px per world metre along W/E)
    meta['walk_stride_px'] = round(WR['W'][1], 1)
    meta['walk_m_per_frame'] = round(2 * WR['W'][1] / 8 / (64 * 2 ** 0.5), 4)
    meta['walk_pass'] = {d: WR[MIRROR.get(d, d)][2] for d in DIRS}
    json.dump(dict(frames=frames, meta=meta), open(os.path.join(od, f'chr_{cid}.json'), 'w'), indent=1)
    # sit: variant 0 (upright, feet flat) of sit.png, seat anchor from the W frame
    sitf = {d: out['sit'][d][0] for d in ST.ORDER}
    sy = ST.seat_row(sitf['W'])
    extra = {k: out[k] for k in ('sit_eat', 'sit_write') if k in out}      # seated loops (sheets.convert_extra)
    ST.write_sit(cid, sitf, sy, extra, dict(sit_eat=[500, 400, 650, 400], sit_write=[350, 300, 350, 300]))
    sj = os.path.join(ROOT, 'characters', cid, f'chr_{cid}_sit.json'); J = json.load(open(sj))
    J['meta']['source'] = f'refs_ai/chatgpt/{cid}/sit.png (ChatGPT sit sheet, variant 1 of 2) + rows ' + ', '.join(f'{k}.png' for k in extra) + ' (tools/ai_import/sheets.py)'
    json.dump(J, open(sj, 'w'), indent=1)
    return n, sy


if __name__ == '__main__':
    cid = sys.argv[1]
    conv = pickle.load(open(sys.argv[2], 'rb')) if len(sys.argv) > 2 else SH.convert(cid)
    if len(sys.argv) > 2:
        st, pal = SH.load_stills(cid); conv = (conv, st, pal)
    print(cid, *build(cid, conv))
