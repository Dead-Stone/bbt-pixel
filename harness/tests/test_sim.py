"""Mock-day invariants: python3 harness/tests/test_sim.py"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from brains import MockBrain
from sim import Sim

def end_pos(s):
    if s['kind'] == 'walk': return s['loc'], s['pts'][-1]
    if s['kind'] in ('stand', 'sit'): return s['loc'], s['pos']
    return None, None
def start_pos(s):
    if s['kind'] == 'walk': return s['loc'], s['pts'][0]
    if s['kind'] in ('stand', 'sit'): return s['loc'], s['pos']
    return None, None

def check(seed=7):
    sim = Sim(MockBrain(seed)); sim.run(); snap = sim.snapshot()
    problems = []
    for cid, tr in snap['tracks'].items():
        for a, b in zip(tr, tr[1:]):
            if a.get('t1') is not None and abs(a['t1'] - b['t0']) > 1e-6: problems.append(f'{cid}: gap {a["t1"]}->{b["t0"]}')
            la, pa = end_pos(a); lb, pb = start_pos(b)
            if la and lb and la == lb and math.dist(pa, pb) > 0.05: problems.append(f'{cid}: jump {pa}->{pb} at {b["t0"]}')
        for s in tr:
            if s['kind'] == 'walk':
                sc = sim.w.scenes[s['loc']]
                for x, y in s['pts'][1:-1]:   # end points may be a seat on furniture
                    if not sc.ok((int(math.floor(x)), int(math.floor(y)))): problems.append(f'{cid}: walk through blocked tile {x,y} in {s["loc"]}')
    ev = snap['events']
    assert all(ev[i]['t'] <= ev[i + 1]['t'] for i in range(len(ev) - 1)), 'events not sorted'
    says = [e for e in ev if e['type'] == 'say']
    convs = [e for e in ev if e['type'] == 'convo_start']
    locs = {e['loc'] for e in says}
    print(f'seed {seed}: {len(ev)} events, {len(convs)} conversations, {len(says)} lines in {sorted(locs)}; problems: {len(problems)}')
    for p in problems[:10]: print('  ', p)
    assert not problems, 'track invariants failed'
    assert len(convs) > 20 and 'floor4' in locs and len(locs) >= 3
    return snap

if __name__ == '__main__':
    for s in (sys.argv[1:] or ['7', '11']): check(int(s))
    print('OK')
