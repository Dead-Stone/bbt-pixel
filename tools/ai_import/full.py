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
  work_desk_<d>        Howard only: the seated laptop-desk frames WITH the desk + chair (no sim hook seats him for work)
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
# Howard's work hooks are all standing (electronics bench, rover): he gets think <-> neutral instead of the seated laptop loop
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
    seq('idle', lambda d: [(f, 250) for f in I.idle_frames(stills[d], eyes.get(d, []), base)])
    seq('walk', lambda d: [(f, 100) for f in head_lock(out['walk'][d])])   # one head per row: no face boil
    for a, c in ACT.items():
        seq(f'act_{a}', lambda d, c=c: [(out[A_][d][c], 600), (I.breathe(out[A_][d][c]), 600)])
    seq('talk', lambda d: [(out[A_][d][1], 400), (out[A_][d][NEUTRAL], 400), (I.breathe(out[A_][d][1]), 400), (out[A_][d][NEUTRAL], 400)])
    seq('gesture', lambda d: [(out[A_][d][1], 500), (out[A_][d][NEUTRAL], 200), (out[A_][d][1], 600)])
    if WORK_COLS[cid]:
        seq('work', lambda d: [(out['work'][d][c], 300) for c in WORK_COLS[cid]])
    else:
        seq('work', lambda d: [(out[A_][d][0], 900), (I.breathe(out[A_][d][0]), 900), (out[A_][d][NEUTRAL], 700)])
        seq('work_desk', lambda d: [(f, 300) for f in out['work'][d]])
    for em, spec in EMOTES[cid].items():
        seq(em, lambda d, spec=spec: [(out[k][d][c], ms) for k, c, ms in spec])

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
    json.dump(dict(frames=frames, meta=meta), open(os.path.join(od, f'chr_{cid}.json'), 'w'), indent=1)
    # sit: variant 0 (upright, feet flat) of sit.png, seat anchor from the W frame
    sitf = {d: out['sit'][d][0] for d in ST.ORDER}
    sy = ST.seat_row(sitf['W'])
    ST.write_sit(cid, sitf, sy)
    sj = os.path.join(ROOT, 'characters', cid, f'chr_{cid}_sit.json'); J = json.load(open(sj))
    J['meta']['source'] = f'refs_ai/chatgpt/{cid}/sit.png (ChatGPT sit sheet, variant 1 of 2; tools/ai_import/sheets.py)'
    json.dump(J, open(sj, 'w'), indent=1)
    return n, sy


if __name__ == '__main__':
    cid = sys.argv[1]
    conv = pickle.load(open(sys.argv[2], 'rb')) if len(sys.argv) > 2 else SH.convert(cid)
    if len(sys.argv) > 2:
        st, pal = SH.load_stills(cid); conv = (conv, st, pal)
    print(cid, *build(cid, conv))
