"""Build a character sprite sheet (v1) from the procedural rig.
Run: cd tools && ../.venv/bin/python build_char_sheet.py sheldon"""
import json, math, os, sys, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import char_rig as R
CID = sys.argv[1] if len(sys.argv) > 1 else 'sheldon'
R.set_character(CID)
from compose_char import compose
from sprite_common import load_gpl, palette_violations, PIVOT

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'characters', CID); os.makedirs(os.path.join(OUT, 'refs'), exist_ok=True)
GPL = os.path.join(ROOT, 'palettes', f'bbt_{CID}.gpl')
CELL, COLS = 128, 12
DIRS8 = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']
MIRROR = {'NE': 'NW', 'E': 'W', 'SE': 'SW'}
PX = 1.0 / (R.SCALE_EFF * math.cos(R.ELEV))   # world units per vertical screen px (per-character model scale)
BODY_H = R.TARGET_H[CID]   # v2: real-height ratio (Sheldon 185 cm = 100 px)
HEAD_TOP_SPEC = 116 - BODY_H

IDLE_ARMS = [(0.03, 0.12), (0.03, 0.12)]
def idle_pose(k):
    return dict(breathe=[0, 1, 1, 0][k] * PX, legs=[(0, 0.02), (0, 0.02)], arms=list(IDLE_ARMS), abduct=IDLE_AB)

# v2 gaits: th = stride (thigh swing), kn = knee bend, arm = arm swing, eb = elbow bend, ab = arm abduction,
# sway = hip shift (px), roll = counter shoulder shift (px)
WALK = {'sheldon': dict(th=0.27, kn=0.30, arm=0.12, eb=0.04, ab=0.06),                 # stiff, straight-legged, arms rigid at sides
        'leonard': dict(th=0.30, kn=0.60, arm=0.28, eb=0.15, ab=0.10),                 # short, quick, slightly hunched
        'penny': dict(th=0.34, kn=0.58, arm=0.26, eb=0.15, ab=0.10, sway=1.0),         # athletic, hip sway
        'howard': dict(th=0.34, kn=0.58, arm=0.34, eb=0.20, ab=0.16, sway=1.0, roll=-0.6),   # swagger: elbows out, hips + shoulder roll
        'raj': dict(th=0.31, kn=0.56, arm=0.24, eb=0.15, ab=0.14),                     # medium, arms clear the fuller torso
        'bernadette': dict(th=0.23, kn=0.50, arm=0.22, eb=0.18, ab=0.12, sway=0.6),    # short quick steps
        'amy': dict(th=0.22, kn=0.34, arm=0.08, eb=0.10, ab=0.06)}[CID]                # stiff, small stride, arms held close
IDLE_AB = {'sheldon': 0.06, 'amy': 0.06, 'raj': 0.13, 'howard': 0.12}.get(CID, 0.10)
def walk_pose(k):
    legs, arms = [], []
    for side in (0, 1):
        ph = math.pi / 2 + 2 * math.pi * k / 8 + side * math.pi
        legs.append((WALK['th'] * math.sin(ph), 0.08 + WALK['kn'] * max(0.0, math.cos(ph)) ** 1.5))
        fl = -WALK['arm'] * math.sin(ph); arms.append((fl, WALK['eb'] + 0.1 * max(0.0, fl)))
    p = dict(legs=legs, arms=arms, abduct=WALK['ab']); p['lift'] = R.sole_lift(legs)
    c = math.cos(2 * math.pi * k / 8)
    if WALK.get('sway'): p['sway'] = WALK['sway'] * PX * c          # hip shift toward the stance leg
    if WALK.get('roll'): p['roll'] = WALK['roll'] * PX * c          # shoulders counter the hips (swagger)
    return p

# ---- knock_knock_penny (v1: 24 frames) ----
K_UP, K_A, K_K = (0.65, 0.55), (1.22, 1.25), (1.40, 0.70)     # wind-up, ready (fist back), contact (knuckle ~3px forward)
KNOCK_SEQ = ['UP', 'A'] + ['K', 'A', 'K', 'A', 'K', 'H'] * 3 + ['R1', 'R2', 'R3', 'R4']
KNOCK_HOLDS = [i for i, s in enumerate(KNOCK_SEQ) if s == 'H']            # 7, 13, 19
KNOCK_ARM = {'SW': 1, 'NW': 0}                                             # NW uses the near (left) arm so it is visible
HEAD_TURN = 0.72
def knock_pose(k, d):
    p = idle_pose(0); arms = list(IDLE_ARMS); s = KNOCK_SEQ[k]; ai = KNOCK_ARM[d]
    if s == 'UP': arms[ai] = K_UP
    elif s in ('A',): arms[ai] = K_A
    elif s == 'K': arms[ai] = K_K
    elif s == 'H': arms[ai] = K_A; p['head_yaw'] = HEAD_TURN   # + turns toward camera in both SW and NW (checked visually)
    else:
        t = int(s[1]) / 4.0
        arms[ai] = tuple(K_A[j] * (1 - t) + IDLE_ARMS[ai][j] * t for j in range(2))
    p['arms'] = arms
    return p

ANIMS = [  # name, nframes, fps, loop, dirs, ms
    ('idle', 4, 4, True, DIRS8, 250),
    ('walk', 8, 10, True, DIRS8, 100),
]
if CID == 'sheldon':
    ANIMS.append(('knock_knock_penny', len(KNOCK_SEQ), 8, False, ['SW', 'NW', 'NE', 'SE'], 125))
ANIMS.append(('blink', 3, 12, False, DIRS8, 80))
if CID == 'leonard':
    ANIMS.append(('glasses_push', 4, 10, False, DIRS8, 100))
if CID == 'penny':
    ANIMS.append(('hair_flip', 6, 10, False, DIRS8, 100))
if CID == 'bernadette':     # spec 3.6: quick little steps, walk 12 fps
    ANIMS[1] = ('walk', 8, 12, True, DIRS8, 83)
SIG = {'howard': ('eyebrow_waggle', 4, 10, 100), 'raj': ('astronomy_point', 4, 8, 125),
       'bernadette': ('sweet_to_scary', 6, 10, 100), 'amy': ('neuro_lecture', 6, 8, 125)}
if CID in SIG:
    n_, f_, ms_ = SIG[CID][1:]
    ANIMS.append((SIG[CID][0], n_, f_, False, DIRS8, ms_))

# ---- cast v1 signature emotes (spec 3.4-3.7) ----
def ew_pose(k):    # Howard eyebrow_waggle: brows up/down twice with a smug grin, head cocked
    p = idle_pose(0); p['mouth'] = 'smile'; p['brow'] = 'up' if k in (0, 2) else None
    p['head_yaw'] = 0.10; p['head_pitch'] = -0.04
    p['ik'] = {1: ((9.0, 4.0, 37.0), (1.0, -0.4, 0.0))}       # thumb hooked at the belt (cocky)
    return p
AP_WRIST = [(10.5, 7.0, 62.0), (8.5, 10.0, 78.0), (8.0, 9.0, 84.0), (8.0, 9.0, 84.0)]
def ap_pose(k):    # Raj astronomy_point: arm rises to point up at the sky, chin lifts, 'look!'
    p = idle_pose(0); p['ik'] = {1: (AP_WRIST[k], (1.0, -0.2, -0.6))}
    p['head_pitch'] = [0.0, 0.12, 0.20, 0.20][k]; p['mouth'] = 'open' if k == 3 else ('smile' if k == 2 else None)
    return p
SS_FACE = [('smile', None), ('smile', None), (None, None), ('scowl', 'angry'), ('open', 'angry'), ('smile', None)]
SS_HOLD = [3, 4]
def ss_pose(k):    # Bernadette sweet_to_scary: sweet smile + head tilt -> scowl, chin down, fists -> back to sweet
    p = idle_pose(0); p['mouth'], p['brow'] = SS_FACE[k]
    p['head_yaw'] = [0.0, 0.14, 0.0, 0.0, 0.0, 0.08][k]; p['head_pitch'] = [0.0, 0.04, -0.06, -0.14, -0.14, 0.0][k]
    if k in (3, 4): p['arms'] = [(0.38, 1.45), (0.38, 1.45)]; p['abduct'] = 0.18
    elif k == 2: p['arms'] = [(0.18, 0.7), (0.18, 0.7)]
    return p
NL_WRIST = [(10.0, 6.0, 56.0), (11.5, 7.5, 63.0), (11.5, 8.0, 65.0), (11.5, 7.5, 63.0), (11.5, 8.0, 65.0), (10.0, 6.0, 56.0)]   # v2: finger up beside the cheek, not over the face
def nl_pose(k):    # Amy neuro_lecture: index finger up, chin raised, talking beats
    p = idle_pose(0); p['ik'] = {1: (NL_WRIST[k], (1.0, -0.3, -1.0))}
    p['head_pitch'] = [0.04, 0.08, 0.08, 0.08, 0.08, 0.04][k]; p['mouth'] = 'open' if k in (1, 3) else None
    p['brow'] = None
    return p

# ---- hair_flip (Penny, 8D, 6 f @ 10 fps): head dips, right hand sweeps up behind the hair, head tosses back, hair swings, settles ----
HF_SWING = [0.0, 0.35, 0.6, -1.0, -0.55, -0.15]
HF_PITCH = [0.0, -0.14, -0.20, 0.22, 0.10, 0.0]   # negative = chin down (checked visually)
HF_YAW = [0.0, -0.10, -0.18, 0.12, 0.06, 0.0]
# v1.1: the v1 targets put the hand at the brow with a sideways elbow (read as a salute). The wrist now rises
# beside the cheek INTO the hair at the temple, sweeps up and back over the crown-side, and exits behind the
# shoulder; the pole points up/back so the elbow lifts above the shoulder line instead of jutting forward.
HF_WRIST = [None, (10.0, 1.0, 81.5), (9.0, -3.0, 84.5), (4.5, -6.5, 83.0), (8.0, -6.0, 66.0), None]   # v1.1: hand rises beside the ear, over the crown, back through the hair
HF_POLE = [None, (1.0, 0.3, -0.9), (1.0, 0.4, 0.1), (0.6, -0.2, 1.0), (0.8, 0.0, -1.0), None]   # elbow out/up, forearm steep (no salute)
def hf_pose(k):
    p = idle_pose(0); p['hair_swing'] = HF_SWING[k]; p['head_pitch'] = HF_PITCH[k]; p['head_yaw'] = HF_YAW[k]
    if HF_WRIST[k]: p['ik'] = {1: (HF_WRIST[k], HF_POLE[k])}
    return p

# ---- glasses_push (Leonard, 8D, 4 f @ 10 fps): right hand rises, index finger meets the bridge, pushes up, lowers ----
GP_WRIST = [(6.5, 9.0, 60.0), (2.4, 13.0, 68.6), (2.2, 13.0, 69.6), (6.0, 9.5, 61.0)]   # wrist targets, ub-relative
GP_DZ = [0.0, 0.0, 1.0, 0.0]
def gp_pose(k):
    p = idle_pose(0); p['ik'] = {1: (GP_WRIST[k], (1.0, 0.2, -1.0))}
    return p
ANIMS_BY = {a[0]: a for a in ANIMS}
BLINK_EYES = ['half', 'closed', 'half']

def pose_for(anim, k, d):
    if anim == 'idle': return idle_pose(k)
    if anim == 'walk': return walk_pose(k)
    if anim == 'knock_knock_penny': return knock_pose(k, d)
    if anim == 'blink': return idle_pose(0)
    if anim == 'glasses_push': return gp_pose(k)
    if anim == 'hair_flip': return hf_pose(k)
    if anim == 'eyebrow_waggle': return ew_pose(k)
    if anim == 'astronomy_point': return ap_pose(k)
    if anim == 'sweet_to_scary': return ss_pose(k)
    if anim == 'neuro_lecture': return nl_pose(k)
_cache = {}
def frame_img(anim, k, d):
    src = MIRROR.get(d, d)
    pose = pose_for(anim, k, src)
    ck = ('idle', 0, src) if anim == 'blink' else (anim, k, src)
    if ck not in _cache: _cache[ck] = R.render(pose, R.YAW[src])
    eyes = BLINK_EYES[k] if anim == 'blink' else 'open'
    gdz = GP_DZ[k] if anim == 'glasses_push' else 0.0
    return compose(_cache[ck], pose, R.YAW[src], mirror=(d in MIRROR), eyes=eyes, glasses_dz=gdz)

def durations(name, n):
    ms = ANIMS_BY[name][5]
    if name == 'knock_knock_penny': return [375 if k in KNOCK_HOLDS else ms for k in range(n)]
    if name == 'sweet_to_scary': return [200 if k in SS_HOLD else ms for k in range(n)]
    return [ms] * n

def main():
    t0 = time.time(); layout, r = [], 0
    for name, n, fps, loop, dirs, ms in ANIMS:
        for d in dirs:
            imgs = [frame_img(name, k, d) for k in range(n)]
            layout.append((name, d, imgs, [(r + k // COLS, k % COLS) for k in range(n)])); r += (n + COLS - 1) // COLS
            print(f'{name}_{d} done {time.time()-t0:.0f}s', flush=True)
    H = r * CELL; W = COLS * CELL; assert H <= 4096
    sheet = np.zeros((H, W, 4), np.uint8); frames, tags = [], []
    for name, d, imgs, cells in layout:
        start = len(frames); du = durations(name, len(imgs))
        for k, (im, (rr, cc)) in enumerate(zip(imgs, cells)):
            sheet[rr*CELL:(rr+1)*CELL, cc*CELL:(cc+1)*CELL] = im
            frames.append(dict(filename=f'chr_{CID}_{name}_{d}_{k:02d}', frame=dict(x=cc*CELL, y=rr*CELL, w=CELL, h=CELL),
                               rotated=False, trimmed=False, spriteSourceSize=dict(x=0, y=0, w=CELL, h=CELL),
                               sourceSize=dict(w=CELL, h=CELL), duration=du[k]))
        tags.append({'name': f'{name}_{d}', 'from': start, 'to': len(frames) - 1, 'direction': 'forward', 'color': '#000000ff'})
    Image.fromarray(sheet).save(os.path.join(OUT, f'chr_{CID}.png'))
    Image.fromarray(sheet).resize((W*4, H*4), Image.NEAREST).save(os.path.join(OUT, f'chr_{CID}_preview4x.png'))
    js = dict(frames=frames, meta=dict(app='bbt-pixel/tools/build_char_sheet.py', version='v1', image=f'chr_{CID}.png',
              format='RGBA8888', size=dict(w=W, h=H), scale='1', frameTags=tags,
              layers=[dict(name='body', opacity=255, blendMode='normal')],
              slices=[dict(name='pivot', color='#ff0000ff', keys=[dict(frame=0, bounds=dict(x=0, y=0, w=CELL, h=CELL),
                                                                         pivot=dict(x=PIVOT[0], y=PIVOT[1]))])]))
    json.dump(js, open(os.path.join(OUT, f'chr_{CID}.json'), 'w'), indent=1)
    anims = {}
    for name, n, fps, loop, dirs, ms in ANIMS:
        a = dict(frames=n, fps=fps, loop=loop, dirs=dirs, frame_ms=ms)
        if name == 'knock_knock_penny':
            a.update(holds_ms={str(k): 375 for k in KNOCK_HOLDS}, bubble_cues=[dict(frame=k, text='Penny.') for k in KNOCK_HOLDS],
                     sequence=KNOCK_SEQ, knock_hand={'SW': 'right', 'NW': 'left', 'NE': 'right (mirror of NW)', 'SE': 'left (mirror of SW)'},
                     note='v1: 24 frames (wind-up, 3 visible knocks + hold per block, x3, 4-frame return); spec §3.1 lists 16 -- update the spec table if approved.')
        if name == 'blink': a.update(eyes=BLINK_EYES, note='v1: half/closed/half (spec §2.3 lists 2 frames; the runtime returns to idle after).')
        if name == 'glasses_push': a.update(hand='right (left on mirrored NE/E/SE, accepted per spec §2.2 rule 4)', glasses_lift_px={'2': 1},
                                            note='hand is hidden behind the head in N/NW/NE; the frame still rides up 1 px on f2 where the face is visible')
        if name == 'hair_flip': a.update(hand='right (left on mirrored NE/E/SE, accepted per spec §2.2 rule 4)', hair_swing=HF_SWING,
                                         head_pitch=HF_PITCH, note='spec §3.3 signature emote (8D, 6 f @ 10 fps); returns to idle')
        if name == 'walk' and CID == 'penny': a.update(hip_sway_px=1)
        if name == 'hair_flip': a.update(version='v1.1', wrist_targets=HF_WRIST, elbow_poles=HF_POLE)
        if name == 'eyebrow_waggle': a.update(brows=['up', 'rest', 'up', 'rest'], mouth='smile', hand='right thumb at belt (left on mirrored NE/E/SE)')
        if name == 'astronomy_point': a.update(hand='right (left on mirrored NE/E/SE)', wrist_targets=AP_WRIST, emote_icon='star (runtime UI, spec 7.3; not baked into the sprite)')
        if name == 'sweet_to_scary': a.update(face=[dict(mouth=m or 'rest', brow=b or 'none') for m, b in SS_FACE], holds_ms={str(k): 200 for k in SS_HOLD})
        if name == 'neuro_lecture': a.update(hand='right index up (left on mirrored NE/E/SE)', wrist_targets=NL_WRIST)
        anims[name] = a
    meta = dict(id=f'chr_{CID}', version=('v1.1' if CID == 'penny' else 'v1'), sheet=f'chr_{CID}.png', atlas=f'chr_{CID}.json', frame=[CELL, CELL],
                pivot_px=list(PIVOT), pivot_norm=[PIVOT[0]/CELL, PIVOT[1]/CELL], body_height_px=BODY_H,
                palette=f'palettes/bbt_{CID}.gpl', camera=dict(projection='2:1 dimetric', elevation_deg=30, px_per_unit=R.SCALE),
                dirs=DIRS8, mirror=MIRROR, decals_on_mirror={'sheldon': ['emblem', 'shirt_folds', 'hair_part'], 'leonard': ['zip_pull', 'tee_graphic'],
                                  'penny': ['hair_part (left)', 'neckline'], 'howard': ['alien_pin (left collar)', 'belt_buckle glint', 'dickey V'],
                                  'raj': ['hair_part (left)', 'argyle vest'], 'bernadette': ['brooch (left)', 'hair_part (left)', 'skirt florals'],
                                  'amy': ['hair_clip + side part (left)', 'cardigan stripes']}[CID],
                anims=anims, notes='Procedural: tools/char_rig.py + tools/compose_char.py + tools/build_char_sheet.py. Face features are projected overlays applied after the outline; mirrored dirs re-evaluate torso/hair decals in true orientation.')
    json.dump(meta, open(os.path.join(OUT, f'chr_{CID}.meta.json'), 'w'), indent=1)
    pal = load_gpl(GPL); tops, bots = [], []
    for name, d, imgs, cells in layout:
        for im in imgs:
            ys = np.where((im[..., 3] > 0).any(1))[0]; tops.append(int(ys[0])); bots.append(int(ys[-1]))
    qa = dict(palette_violations=int(palette_violations(sheet, pal)), head_top_min=min(tops), head_top_max=max(tops),
              idle_S_head_top=tops[0], lowest_px_min=min(bots), lowest_px_max=max(bots), frames=len(frames), sheet=[W, H],
              alpha_values=sorted(np.unique(sheet[..., 3]).tolist()), seconds=round(time.time()-t0))
    print(json.dumps(qa)); json.dump(qa, open(os.path.join(OUT, 'refs', 'qa_report.json'), 'w'), indent=1)
    A = {(n, d): imgs for n, d, imgs, _ in layout}
    make_gifs(A)
    if CID in SIG or CID == 'penny':
        import qa_char; qa_char.report(CID, OUT, sheet, layout, qa, BODY_H, HEAD_TOP_SPEC, ANIMS)
    pass

def key_frames(A):
    ks = [A[('idle', 'S')][0], A[('walk', 'S')][0], A[('walk', 'SW')][2], A[('walk', 'W')][0], A[('walk', 'NW')][2]]
    if CID == 'sheldon': ks.append(A[('knock_knock_penny', 'SW')][KNOCK_HOLDS[0]])
    if CID == 'penny': ks.append(A[('hair_flip', 'SW')][3])
    if CID in SIG: ks.append(A[(SIG[CID][0], 'SW')][2])
    return ks

def stage(im, bubble=None, bg=(201, 206, 214), shadow=(140, 143, 148)):
    base = Image.new('RGBA', (CELL, CELL), bg + (255,))
    ImageDraw.Draw(base).ellipse((PIVOT[0]-20, PIVOT[1]-5, PIVOT[0]+19, PIVOT[1]+4), fill=shadow + (255,))
    base.alpha_composite(Image.fromarray(im)); big = base.resize((CELL*4, CELL*4), Image.NEAREST)
    if bubble:
        d = ImageDraw.Draw(big)
        try: f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 28)
        except Exception: f = ImageFont.load_default()
        tw = d.textlength(bubble, font=f); x0, y0 = 256 - (tw + 28) / 2, 4
        d.rounded_rectangle((x0, y0, x0+tw+28, y0+46), 12, fill=(244, 241, 234), outline=(26, 20, 32), width=4)
        d.polygon([(250, y0+44), (274, y0+44), (262, y0+60)], fill=(244, 241, 234), outline=(26, 20, 32))
        d.text((x0+14, y0+6), bubble, font=f, fill=(26, 20, 32))
    return big.convert('RGB')

def grid(cells, ncol):
    nrow = (len(cells) + ncol - 1) // ncol
    g = Image.new('RGB', (ncol*512, nrow*512), (201, 206, 214))
    for i, c in enumerate(cells): g.paste(c, ((i % ncol)*512, (i // ncol)*512))
    return g

def save_gif(path, frames, durs):
    # disposal=2 + optimize=False stops Pillow from merging identical consecutive frames (idle f1==f2)
    q = [f.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    q[0].save(path, save_all=True, append_images=q[1:], duration=durs, loop=0, disposal=2, optimize=False)
    n = Image.open(path).n_frames
    if n != len(frames):                       # fallback: tag each frame with an invisible-in-practice index pixel
        q = []
        for i, f in enumerate(frames):
            f = f.copy(); f.putpixel((0, 0), (201, 206, 214 - (i % 2))); q.append(f.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))
        q[0].save(path, save_all=True, append_images=q[1:], duration=durs, loop=0, disposal=2, optimize=False)
    return Image.open(path).n_frames

def make_gifs(A):
    for name, ncol in (('walk', 4), ('idle', 4), ('blink', 4)) + ((('glasses_push', 4),) if CID == 'leonard' else ()) + ((('hair_flip', 4),) if CID == 'penny' else ()) + (((SIG[CID][0], 4),) if CID in SIG else ()):
        n = ANIMS_BY[name][1]
        fr = [grid([stage(A[(name, d)][k]) for d in DIRS8], ncol) for k in range(n)]
        du = durations(name, n)
        if name in ('blink', 'glasses_push', 'hair_flip') + tuple(v[0] for v in SIG.values()):   # show it in context: open hold, blink, open hold
            fr = [grid([stage(A[('idle', d)][0]) for d in DIRS8], ncol)] + fr; du = [900] + du
        print(name, 'gif frames', save_gif(os.path.join(OUT, f'{name}_8dir_4x.gif'), fr, du))
    for d in DIRS8:
        save_gif(os.path.join(OUT, f'walk_{d}_4x.gif'), [stage(A[('walk', d)][k]) for k in range(8)], [ANIMS_BY['walk'][5]]*8)
    if CID == 'sheldon':
        kd = ['SW', 'NW', 'NE', 'SE']; n = ANIMS_BY['knock_knock_penny'][1]
        fr = [grid([stage(A[('knock_knock_penny', d)][k], bubble=('Penny.' if k in KNOCK_HOLDS else None)) for d in kd], 2) for k in range(n)]
        print('knock gif frames', save_gif(os.path.join(OUT, 'knock_4d_4x.gif'), fr, durations('knock_knock_penny', n)))

if __name__ == '__main__':
    main()
