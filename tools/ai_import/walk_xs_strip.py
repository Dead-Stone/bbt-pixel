"""What the viewer plays: for every character x direction, the walk sheet frames in the order viewer.js agentAt picks
them (k = (floor(walked / walk_m_per_pose_dir[d]) + pass_poses[0]) % frames, sampled every 1/8 pose over 2 cycles,
consecutive repeats collapsed), labelled X (cross, red) / T (transition, yellow) / | (straight, blue) with the measured
foot spread. Fails (exit 1) if two crossed poses ever play in a row, or the legs do not go monotonically
cross > transition > straight < transition < cross: side / 3-4 views by foot spread (or walk_cycle.lift when the back
foot is lifted above the spread band), front / back (S, N) by how far the legs are from the standing legs (pixels of the
leg region that differ from the nearest straight pose).
  python3 tools/ai_import/walk_xs_strip.py [--dirs S,SW,W,NW,N,NE,E,SE] [--out env/renders/walk/walk_xs_<cid>.png] [cid ...]"""
import argparse, json, os, sys, math
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE)
from full import _spread
from walk_cycle import lift
from walk_xs import legdist
CAST = ['penny', 'sheldon', 'leonard', 'howard', 'raj', 'amy', 'bernadette']
DIRS = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']


def plays(m, d, n, cycles=2):
    mpp = (m.get('walk_m_per_pose_dir') or {}).get(d) or m['walk_m_per_pose']; pp = m['pass_poses']
    pp = pp[0] if isinstance(pp, list) else pp[d][0]; seq = []
    for i in range(int(cycles * n * 8)):
        k = (math.floor(i * mpp / 8 / mpp + 1e-9) + pp) % n
        if not seq or seq[-1] != k: seq.append(k)
    return seq


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cids', nargs='*'); ap.add_argument('--dirs', default=','.join(DIRS))
    ap.add_argument('--out', default=None); ap.add_argument('--scale', type=int, default=2); ap.add_argument('--cycles', type=float, default=2)
    a = ap.parse_args(); cids = a.cids or CAST; dirs = a.dirs.split(','); bad = []
    y0, y1, x0, x1 = 14, 124, 24, 104; cw, ch = x1 - x0, y1 - y0; lw = 96
    rows = [(c, d) for c in cids for d in dirs]; ncol = int(a.cycles * 8)
    out = Image.new('RGB', (lw + ncol * cw, 24 + len(rows) * (ch + 16)), (46, 46, 54)); D = ImageDraw.Draw(out)
    D.text((4, 4), 'what the viewer plays (walk start -> 2 cycles): X = cross (stride), T = transition, | = straight (legs together); number = foot spread px',
           fill=(230, 230, 230))
    for r, (cid, d) in enumerate(rows):
        j = json.load(open(f'{ROOT}/characters/{cid}/ai/chr_{cid}_walk.json')); m = j['meta']
        im = np.array(Image.open(f'{ROOT}/characters/{cid}/ai/chr_{cid}_walk.png').convert('RGBA'))
        tag = next(t for t in m['frameTags'] if t['name'] == f'walk_{d}'); n = tag['to'] - tag['from'] + 1
        poses = m.get('poses') or ['?'] * n; seq = plays(m, d, n, a.cycles)[:ncol]
        info = (m.get('rows') or {}).get(d, {})
        oy = 24 + r * (ch + 16); D.line([(0, oy + ch + 14), (out.width, oy + ch + 14)], fill=(80, 80, 90))
        D.text((4, oy + 30), cid, fill=(255, 255, 255)); D.text((4, oy + 44), d, fill=(255, 255, 255))
        mode = info.get('straight_mode')
        if mode: D.text((4, oy + 58), '|: ' + '/'.join('C' if x == 'composite' else 'D' for x in mode), fill=(200, 200, 120))
        sp = []; cel = lambda k: im[j['frames'][tag['from'] + k]['frame']['y']:j['frames'][tag['from'] + k]['frame']['y'] + 128,
                                       j['frames'][tag['from'] + k]['frame']['x']:j['frames'][tag['from'] + k]['frame']['x'] + 128]
        straights = [cel(k) for k in range(n) if poses[k % len(poses)] == 'straight']
        for i, k in enumerate(seq):
            fr = j['frames'][tag['from'] + k]['frame']; c = im[fr['y']:fr['y'] + 128, fr['x']:fr['x'] + 128]
            t = c[y0:y1, x0:x1]; ox = lw + i * cw; ti = Image.fromarray(np.ascontiguousarray(t)); out.paste(ti, (ox, oy), ti)
            lab = {'cross': 'X', 'straight': '|', 'trans': 'T'}.get(poses[k % len(poses)], '?'); s = int(_spread(c))
            sp.append((lab, s, int(lift(c)), min(legdist(c, q) for q in straights) if straights else 0))
            col = {'X': (240, 110, 90), 'T': (240, 210, 80)}.get(lab, (110, 170, 255))
            D.rectangle([ox + 3, oy + ch + 2, ox + cw - 3, oy + ch + 12], fill=col); D.text((ox + 6, oy + ch + 2), f'{lab} {s}', fill=(0, 0, 0))
        labs = [q[0] for q in sp]
        if any(labs[i] == 'X' and labs[i + 1] == 'X' for i in range(len(labs) - 1)): bad.append((cid, d, 'two X in a row', labs))
        qs = (1, 2, 3) if d not in ('S', 'N') else (3,)     # side views: spread, lift or (feet level, e.g. Raj NW) leg distance
        for i in range(1, len(sp) - 1):
            if sp[i][0] != 'T': continue
            x = [sp[i + o] for o in (-1, 1) if sp[i + o][0] == 'X']; st = [sp[i + o] for o in (-1, 1) if sp[i + o][0] == '|']
            if len(x) != 1 or len(st) != 1: bad.append((cid, d, 'T not between an X and a |', labs)); continue
            if not any(x[0][q] > sp[i][q] > st[0][q] for q in qs): bad.append((cid, d, f'T at {i} not between X and |', sp[i - 1:i + 2]))
    of = a.out or f'env/renders/walk/walk_xs_{"_".join(cids) if len(cids) < 3 else "cast"}.png'
    os.makedirs(os.path.dirname(os.path.join(ROOT, of)), exist_ok=True)
    out.resize((out.width * a.scale, out.height * a.scale), Image.NEAREST).save(os.path.join(ROOT, of), optimize=True)
    print(of, out.size, 'OK' if not bad else 'FAIL'); [print(' ', b) for b in bad]
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
