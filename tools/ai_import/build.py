"""AI turnaround -> per-character 128-px frames (stand + idle), audit-compatible sheets, review renders.

python3 tools/ai_import/build.py [refs_ai/chatgpt_penny_1.png]
writes
  characters/<cid>/ai/chr_<cid>.png/.json   stand (8 dirs x 1) + idle (8 dirs x 8) [+ walk (8 dirs x 8) when
                                            refs_ai/gen/<cid>_walk4_<dir>.jpg exist, see walk.py] in the rig's sheet format
  harness/renders/aiimport/walk_<cid>.gif / walk_<cid>.png   walk preview (8 dirs, 3x) + idle-vs-walk compare
  characters/<cid>/ai/stand_<DIR>.png       single standing frames
  characters/<cid>/ai/bbt_<cid>_ai.gpl      the character's palette
  harness/renders/aiimport/cast_turnaround_128.png   35 converted frames, 3x
  harness/renders/aiimport/compare_cast.png          rig vs AI, S and SW, 3x, true relative heights
  harness/renders/aiimport/compare_cast_1x.png       the same at game size (1x and 2x)
SE/E/NE are mirrors of SW/W/NW (flipped about the pivot column 64).
"""
import os, sys, json, numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import slice as S, convert as CV, idle as I, walk as WK

DIRS = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']
MIRROR = {'NE': 'NW', 'E': 'W', 'SE': 'SW'}
BG = (70, 72, 84, 255)
NAMES = dict(sheldon='Sheldon', leonard='Leonard', penny='Penny', howard='Howard', raj='Raj', bernadette='Bernadette', amy='Amy')


def mirror(img):
    return np.roll(img[:, ::-1], 1, axis=1)      # x -> 128 - x keeps the pivot column 64 in place


def flatten(rgba, bg=BG):
    im = Image.new('RGBA', (rgba.shape[1], rgba.shape[0]), bg); im.alpha_composite(Image.fromarray(rgba)); return im


def write_character(cid, views, pal, walk=None):
    od = os.path.join(ROOT, 'characters', cid, 'ai'); os.makedirs(od, exist_ok=True)
    full = {d: CV.audit_fix(mirror(views[MIRROR[d]]), pal) if d in MIRROR else views[d] for d in DIRS}
    base = I.skin_of(views['S'], I.SKIN_AT[cid])
    eyes = I.EYES.get(cid, {})
    cells, frames, tags = [], [], []
    for d in DIRS:
        Image.fromarray(full[d]).save(os.path.join(od, f'stand_{d}.png'))
    def add(name, img, dur):
        i = len(cells); cells.append(img)
        frames.append(dict(filename=f'chr_{cid}_{name}', frame=dict(x=(i % 16) * 128, y=(i // 16) * 128, w=128, h=128),
                           rotated=False, trimmed=False, spriteSourceSize=dict(x=0, y=0, w=128, h=128),
                           sourceSize=dict(w=128, h=128), duration=dur))
        return i
    for d in DIRS:
        a = add(f'stand_{d}_00', full[d], 250); tags.append(dict(name=f'stand_{d}', **{'from': a, 'to': a}, direction='forward'))
    for d in DIRS:
        src = MIRROR.get(d, d)
        seq = I.idle_frames(views[src], eyes.get(src, []), base)
        if d in MIRROR: seq = [mirror(f) for f in seq]
        seq = [CV.audit_fix(f.copy(), pal) for f in seq]
        ids = [add(f'idle_{d}_{k:02d}', f, 250) for k, f in enumerate(seq)]
        tags.append(dict(name=f'idle_{d}', **{'from': ids[0], 'to': ids[-1]}, direction='forward'))
    walk_full = {}
    if walk:
        for d in DIRS:
            seq = [mirror(f) for f in walk[MIRROR[d]]] if d in MIRROR else walk[d]
            seq = [CV.audit_fix(f.copy(), pal) for f in seq]
            walk_full[d] = seq
            ids = [add(f'walk_{d}_{k:02d}', f, 100) for k, f in enumerate(seq)]
            tags.append(dict(name=f'walk_{d}', **{'from': ids[0], 'to': ids[-1]}, direction='forward'))
    n = len(cells); rows = (n + 15) // 16
    sheet = np.zeros((rows * 128, 16 * 128, 4), np.uint8)
    for i, c in enumerate(cells): sheet[(i // 16) * 128:(i // 16 + 1) * 128, (i % 16) * 128:(i % 16 + 1) * 128] = c
    Image.fromarray(sheet).save(os.path.join(od, f'chr_{cid}.png'))
    # head rows per facing for the audit's flicker window: crown -> ~chin (AI heads are ~1/6.5 of the figure)
    hrd = {}
    for d in DIRS:
        y0, y1 = I.extent(full[d]); hrd[d] = int(round((y1 - y0) / 6.5))
    meta = dict(app='bbt-pixel/tools/ai_import/build.py', version='ai1', image=f'chr_{cid}.png', format='RGBA8888',
                size=dict(w=sheet.shape[1], h=sheet.shape[0]), scale='1', pivot=[64, 116], frameTags=tags,
                source='refs_ai/chatgpt_penny_1.png (ChatGPT cast turnaround, row %s)' % NAMES[cid],
                audit=dict(head_rows=max(hrd.values()), head_rows_dir=hrd, fidget=dict(idle=[7]),
                           fidget_why='idle frame 7 is the blink (eyes repainted on purpose)'),
                note='stand = the converted still; idle = 1-px breath + blink (tools/ai_import/idle.py); ' + (
                     'walk = 4 generated key poses per direction, each held 2 frames (tools/ai_import/walk.py)' if walk else
                     'no walk yet: the rig walk (characters/<cid>/chr_<cid>.png) stays until a real AI walk sheet exists'))
    if walk: meta['source_walk'] = 'refs_ai/gen/%s_walk4_<dir>.jpg (GenerateImage, turnaround as reference)' % cid
    json.dump(dict(frames=frames, meta=meta), open(os.path.join(od, f'chr_{cid}.json'), 'w'), indent=1)
    with open(os.path.join(od, f'bbt_{cid}_ai.gpl'), 'w') as f:
        f.write(f'GIMP Palette\nName: bbt_{cid}_ai\nColumns: 8\n#\n')
        for c in pal: f.write(f'{c[0]:3d} {c[1]:3d} {c[2]:3d}\n')
    if walk_full: walk_renders(cid, full, walk_full)
    return full


def walk_renders(cid, still, walk, Z=3):
    rd = os.path.join(ROOT, 'harness', 'renders', 'aiimport'); os.makedirs(rd, exist_ok=True)
    x0, x1, y0, y1 = 24, 104, 14, 124
    w, h = (x1 - x0) * Z, (y1 - y0) * Z
    gif = []
    for k in range(0, 8, 2):                       # 4 distinct poses, 200 ms each = in-game cadence
        fr = Image.new('RGBA', (w * 8, h + 16), BG)
        for c, d in enumerate(DIRS):
            fr.paste(flatten(walk[d][k][y0:y1, x0:x1]).resize((w, h), Image.NEAREST), (c * w, 16))
            label(fr, (c * w + w // 2 - 6, 2), d)
        gif.append(fr.convert('P', palette=Image.ADAPTIVE, colors=255))
    gif[0].save(os.path.join(rd, f'walk_{cid}.gif'), save_all=True, append_images=gif[1:], duration=200, loop=0, disposal=2)
    # still: idle frame (col 0) then the 4 key poses, per direction (rows)
    out = Image.new('RGBA', (60 + w * 5, (h + 6) * 8 + 20), BG)
    label(out, (60 + w // 2 - 10, 4), 'idle'); [label(out, (60 + (i + 1) * w + w // 2 - 20, 4), t) for i, t in enumerate(['stride A', 'pass', 'stride B', 'pass'])]
    for r, d in enumerate(DIRS):
        yy = 20 + r * (h + 6); label(out, (6, yy + h // 2), d)
        for c, f in enumerate([still[d]] + walk[d][::2]):
            out.paste(flatten(f[y0:y1, x0:x1]).resize((w, h), Image.NEAREST), (60 + c * w, yy))
        ImageDraw.Draw(out).line([(60, yy + (116 - y0) * Z), (out.width, yy + (116 - y0) * Z)], fill=(110, 112, 126, 255))
    out.save(os.path.join(rd, f'walk_{cid}.png'))


def label(im, xy, t, fill=(235, 235, 235, 255)):
    ImageDraw.Draw(im).text(xy, t, fill=fill)


def renders(allv):
    rd = os.path.join(ROOT, 'harness', 'renders', 'aiimport'); os.makedirs(rd, exist_ok=True)
    # 35 frames at 3x
    Z = 3; cw, ch = 128 * Z, 128 * Z
    out = Image.new('RGBA', (cw * 5 + 90, ch * 7 + 30), BG)
    for c, d in enumerate(S.DIRS5): label(out, (90 + c * cw + cw // 2 - 8, 8), d)
    for r, cid in enumerate(S.CAST):
        label(out, (6, 30 + r * ch + ch // 2), NAMES[cid])
        for c, d in enumerate(S.DIRS5):
            out.paste(flatten(allv[cid][d]).resize((cw, ch), Image.NEAREST), (90 + c * cw, 30 + r * ch))
    out.save(os.path.join(rd, 'cast_turnaround_128.png'))
    # rig vs AI, S and SW: frames share the pivot, so pasting both on one baseline keeps true relative heights
    rig = {}
    for cid in S.CAST:
        sh = np.array(Image.open(os.path.join(ROOT, 'characters', cid, f'chr_{cid}.png')).convert('RGBA'))
        J = json.load(open(os.path.join(ROOT, 'characters', cid, f'chr_{cid}.json')))
        fr = {f['filename']: f['frame'] for f in J['frames']}
        rig[cid] = {d: sh[fr[f'chr_{cid}_idle_{d}_00']['y']:fr[f'chr_{cid}_idle_{d}_00']['y'] + 128,
                          fr[f'chr_{cid}_idle_{d}_00']['x']:fr[f'chr_{cid}_idle_{d}_00']['x'] + 128] for d in ('S', 'SW')}
    def compare(Z, path, title=True):
        x0, x1, y0, y1 = 36, 92, 8, 124            # crop: 56 x 116 per figure
        w, h = (x1 - x0) * Z, (y1 - y0) * Z
        lw = 70 if Z >= 2 else 0
        out = Image.new('RGBA', (lw + w * 7, (h + 14) * 4 + 16), BG)
        rows = [('rig S', rig, 'S'), ('AI S', None, 'S'), ('rig SW', rig, 'SW'), ('AI SW', None, 'SW')]
        for r, (lab, srcd, d) in enumerate(rows):
            yy = 16 + r * (h + 14)
            if lw: label(out, (4, yy + h // 2), lab)
            for c, cid in enumerate(S.CAST):
                fr = (srcd[cid][d] if srcd else allv[cid][d])[y0:y1, x0:x1]
                out.paste(flatten(fr).resize((w, h), Image.NEAREST), (lw + c * w, yy))
                if r == 0 and Z >= 2: label(out, (lw + c * w + 4, 2), NAMES[cid])
            ImageDraw.Draw(out).line([(lw, yy + (116 - y0) * Z), (out.width, yy + (116 - y0) * Z)], fill=(110, 112, 126, 255))
        out.save(path)
    compare(3, os.path.join(rd, 'compare_cast.png'))
    a = Image.open(os.path.join(rd, 'compare_cast.png'))
    # game size: 1x and 2x side by side
    tmp1 = os.path.join(rd, '_c1.png'); tmp2 = os.path.join(rd, '_c2.png')
    compare(1, tmp1); compare(2, tmp2)
    i1, i2 = Image.open(tmp1), Image.open(tmp2)
    g = Image.new('RGBA', (i1.width + i2.width + 20, max(i1.height, i2.height)), BG)
    g.paste(i1, (0, 0)); g.paste(i2, (i1.width + 20, 0)); g.save(os.path.join(rd, 'compare_cast_1x.png'))
    os.remove(tmp1); os.remove(tmp2)


def main(src):
    cuts = S.slice_sheet(src)
    allv = {}
    for cid in S.CAST:
        views, pal = CV.convert_character(cid, {d: cuts[(cid, d)]['rgba'] for d in S.DIRS5}, S.DIRS5)
        walk = WK.walk_for(cid, pal, views)
        write_character(cid, views, pal, walk); allv[cid] = views
        if walk: print(cid, 'walk', ' '.join(f'{d}:{len(v)}' for d, v in walk.items()))
        print(cid, 'palette', len(pal), 'colours')
    renders(allv)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'refs_ai', 'chatgpt_penny_1.png'))
