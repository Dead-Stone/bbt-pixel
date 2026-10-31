"""Reachability audit for floor4: every hook's approach tile (or the hook tile) and every persona home must be reachable
from the stair head through the walkable grid (doors at x=8/x=12, y=4)."""
import json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')); sys.path.insert(0, f'{ROOT}/harness')
from world import Scene
d = json.load(open(f'{ROOT}/harness/world/floor4/scene.json')); S = Scene(d)
start = S.nearest_ok(10.5, 5.4); bad = []
for h in d['hooks']:
    t = h.get('approach_tile') or h['tile']; g = S.nearest_ok(t[0] + .5, t[1] + .5)
    far = abs(g[0] - t[0]) + abs(g[1] - t[1])
    p = S.astar(start, g)
    if p is None or far > 1: bad.append((h['id'], t, g, None if p is None else len(p)))
print('walkable', sum(map(sum, S.walk)), 'main component', len(S.main), 'hooks', len(d['hooks']))
for (x, y) in ((5.5, 3.5), (3.4, 6.4), (5.5, 6.5), (14.5, 1.45)):
    if S.path((10.5, 5.4), (x, y)) is None: bad.append(('home', (x, y)))
for row in range(S.H): print(''.join('#' if not S.walk[row][x] else ('.' if (x, row) in S.main else 'o') for x in range(S.W)))
print('UNREACHABLE' if bad else 'all hooks + homes reachable', bad)
