"""Per-character QA report (characters/<id>/qa_report.json + qa_report.md) for the cast v1 builds."""
import json, os, glob, datetime
import numpy as np
from PIL import Image
import char_rig as R

DECAL_COLOR = {'howard': 'alien_pin', 'bernadette': 'floral_b', 'amy': 'hair_clip', 'raj': None, 'penny': None}

def report(cid, out, sheet, layout, qa, body_h, head_top_spec, anims):
    A = {(n, d): imgs for n, d, imgs, _ in layout}
    C = R.C
    def cnt(im, name, half=None):
        m = (im[..., 3] > 0) & (im[..., :3] == C[name]).all(-1)
        ys, xs = np.where(m); return int(m.sum()), (float(xs.mean()) if xs.size else None)
    idle = A[('idle', 'S')][0]
    ys = np.where((idle[..., 3] > 0).any(1))[0]
    head_top, lowest = int(ys[0]), int(ys[-1])
    # feet: ankle/ground contact sits on y=116; the toe + sole outline projects 3-5 px lower in the 30-degree view.
    # House convention from Sheldon/Leonard/Penny v1: lowest opaque row 119-121, so accept 116..122.
    feet_ok = all(116 <= int(np.where((im[..., 3] > 0).any(1))[0][-1]) <= 122 for d in ['S', 'SW', 'W', 'NW', 'N'] for im in A[('idle', d)])
    # mirror check: NE/E/SE vs flipped NW/W/SW (differences = decals re-evaluated in true orientation + face overlays)
    mirror = {}
    for d, src in (('NE', 'NW'), ('E', 'W'), ('SE', 'SW')):
        a = A[('idle', d)][0]; b = A[('idle', src)][0][:, ::-1]
        mirror[d] = dict(pixels_differing_from_plain_flip=int((a != b).any(-1).sum()), silhouette_identical=bool(((a[..., 3] > 0) == (b[..., 3] > 0)).all()))
    dc = DECAL_COLOR.get(cid); decal = None
    if dc:
        decal = {d: dict(zip(('px', 'mean_col'), cnt(A[('idle', d)][0], dc))) for d in ['S', 'SW', 'W', 'SE', 'E']}
    eyes = cnt(idle, 'ink_2')[0]
    gifs = {}
    for g in sorted(glob.glob(os.path.join(out, '*.gif'))):
        gifs[os.path.basename(g)] = Image.open(g).n_frames
    res = dict(character=cid, generated=datetime.datetime.now().strftime('%Y-%m-%d %H:%M %Z').strip() + ' (America/Los_Angeles)',
               frame=[128, 128], pivot=[64, 116], body_height_spec_px=body_h, head_top_spec_y=head_top_spec,
               idle_S_head_top_y=head_top, idle_S_body_height_px=116 - head_top, idle_S_lowest_px=lowest,
               head_top_within_2px_of_spec=abs(head_top - head_top_spec) <= 2, feet_on_pivot_line_idle=feet_ok,
               palette_violations=qa['palette_violations'], alpha_values=qa['alpha_values'], frames=qa['frames'], sheet_px=qa['sheet'],
               anims={a[0]: dict(frames=a[1], fps=a[2], dirs=len(a[4])) for a in anims},
               mirror_check=mirror, decal_check=decal, idle_S_eye_pixels=eyes, gifs=gifs,
               walk_8dir_gif_present='walk_8dir_4x.gif' in gifs)
    json.dump(res, open(os.path.join(out, 'qa_report.json'), 'w'), indent=1)
    L = [f'# QA report: chr_{cid}', '', f"Generated {res['generated']} by tools/build_char_sheet.py + tools/qa_char.py.", '',
         '| Check | Result |', '|---|---|',
         f"| Frame / pivot | 128x128, pivot (64,116) |",
         f"| Body height (spec {body_h} px, head top y={head_top_spec}) | idle S head top y={head_top} -> {116 - head_top} px ({'PASS' if res['head_top_within_2px_of_spec'] else 'CHECK'}) |",
         f"| Feet on pivot line (idle, painted dirs; lowest row 116-122, house convention 119-121) | {'PASS' if feet_ok else 'CHECK'} (lowest px {lowest}) |",
         f"| Palette violations | {qa['palette_violations']} ({'PASS' if qa['palette_violations'] == 0 else 'FAIL'}) |",
         f"| Alpha values | {qa['alpha_values']} |",
         f"| Frames / sheet | {qa['frames']} frames, {qa['sheet'][0]}x{qa['sheet'][1]} |",
         f"| Animations | " + ', '.join(f"{k} {v['frames']}f@{v['fps']}fps x{v['dirs']}D" for k, v in res['anims'].items()) + ' |',
         f"| Mirrors (NE/E/SE = flip NW/W/SW) | " + ', '.join(f"{d}: silhouette {'same' if v['silhouette_identical'] else 'DIFF'}, {v['pixels_differing_from_plain_flip']} px re-evaluated" for d, v in mirror.items()) + ' |']
    if decal:
        L.append(f"| Decal '{dc}' per dir (px, mean col) | " + ', '.join(f"{d}: {v['px']} @ {v['mean_col']:.1f}" if v['mean_col'] is not None else f"{d}: 0" for d, v in decal.items()) + ' |')
    L += [f"| Eye pixels in idle S | {eyes} |", f"| GIFs | " + ', '.join(f'{k} ({v}f)' for k, v in gifs.items()) + ' |', '']
    open(os.path.join(out, 'qa_report.md'), 'w').write('\n'.join(L))
    print('qa_report written', res['head_top_within_2px_of_spec'], feet_ok)


def report_from_atlas(cid, body_h, head_top_spec, anims):
    """Re-run the report from an existing atlas (no re-render)."""
    root = os.path.join(os.path.dirname(__file__), '..', 'characters', cid)
    J = json.load(open(os.path.join(root, f'chr_{cid}.json'))); sheet = np.array(Image.open(os.path.join(root, f'chr_{cid}.png')).convert('RGBA'))
    fr = J['frames']; fr = fr if isinstance(fr, dict) else {f.get('filename', f.get('name')): f for f in fr}; layout = []
    for name, n, fps, loop, dirs, ms in anims:
        for d in dirs:
            imgs = []
            for k in range(n):
                f = fr[f'chr_{cid}_{name}_{d}_{k:02d}']['frame']; imgs.append(sheet[f['y']:f['y'] + 128, f['x']:f['x'] + 128])
            layout.append((name, d, imgs, None))
    pal = {tuple(v) for v in R.C.values()}
    px = sheet[sheet[..., 3] > 0][:, :3]
    viol = sum(1 for p in {tuple(int(x) for x in p) for p in px} if p not in pal)
    qa = dict(palette_violations=viol, alpha_values=sorted(int(x) for x in np.unique(sheet[..., 3])), frames=len(fr), sheet=[sheet.shape[1], sheet.shape[0]])
    report(cid, root, sheet, layout, qa, body_h, head_top_spec, anims)
