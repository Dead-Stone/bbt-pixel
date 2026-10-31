"""World model for the harness: scenes (walk grids, hooks, exits), A* pathfinding, hook reservations and the
world-graph router.  Data comes from harness/world/*.json (written by export_world.py from the env/ engine files)."""
import os, json, math, heapq
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD_DIR = os.path.join(HERE, 'world')

# world-space unit vectors of the 8 sprite directions (screen: sx=(x-y)*64, sy=(x+y)*32)
DIRV = {'S': (1, 1), 'N': (-1, -1), 'E': (1, -1), 'W': (-1, 1), 'SW': (0, 1), 'SE': (1, 0), 'NE': (0, -1), 'NW': (-1, 0)}

def dir_of(dx, dy, default='SW'):
    if abs(dx) < 1e-6 and abs(dy) < 1e-6: return default
    best, bd = default, -9
    n = math.hypot(dx, dy)
    for k, (vx, vy) in DIRV.items():
        d = (dx * vx + dy * vy) / (n * math.hypot(vx, vy))
        if d > bd: best, bd = k, d
    return best

TRAVEL_SECONDS = {'door': 3, 'stairs': 60, 'sidewalk': 5 * 60, 'car': 10 * 60}

class Scene:
    def __init__(self, data):
        self.d = data; self.id = data['id']; self.name = data['name']
        self.W, self.H = data['size']
        self.walk = data['walkable']
        self.blocked = set()
        for a, b in data.get('blocked_edges', []):
            self.blocked.add((tuple(a), tuple(b))); self.blocked.add((tuple(b), tuple(a)))
        if self.id == 'floor4':
            # the 4B | hall | 4A partition walls (x = 8 and x = 12) are only passable through the front doors (y = 4, facing each other)
            for y in range(self.H):
                if y == 4: continue
                for x in (8, 12):
                    self.blocked.add(((x - 1, y), (x, y))); self.blocked.add(((x, y), (x - 1, y)))
        self.hooks = {h['id']: h for h in data['hooks']}
        self.exits = {e['id']: e for e in data['exits']}
        self.spawns = data['spawns']
        if self.id == 'floor4':
            # the engine marks only the stair foot (10..11, 7) as the exit, which is boxed in by the flight and rail;
            # agents use the head of the flight instead (top step tiles, reachable from the hall landing)
            self.walk = [list(r) for r in self.walk]
            for x in (10, 11): self.walk[5][x] = 1
            self.exits['stairs_down']['tiles'] = [[10, 5], [11, 5]]
            self.spawns['stairs_top'] = [10.5, 5.4]
        self.main = self._main_component()
        self.zones = data.get('zones', {})

    # ------------------------------------------------------------------ grid
    def ok(self, t):
        x, y = t; return 0 <= x < self.W and 0 <= y < self.H and bool(self.walk[y][x])
    def step_ok(self, a, b):
        if not self.ok(b) or (a, b) in self.blocked: return False
        dx, dy = b[0] - a[0], b[1] - a[1]
        if dx and dy:   # diagonal: both orthogonal detours must be open (no corner cutting through items or walls)
            c1, c2 = (a[0] + dx, a[1]), (a[0], a[1] + dy)
            return (self.ok(c1) and self.ok(c2) and (a, c1) not in self.blocked and (c1, b) not in self.blocked
                    and (a, c2) not in self.blocked and (c2, b) not in self.blocked)
        return True
    def _main_component(self):
        seen, best = set(), set()
        for y in range(self.H):
            for x in range(self.W):
                if self.ok((x, y)) and (x, y) not in seen:
                    comp = {(x, y)}; st = [(x, y)]; seen.add((x, y))
                    while st:
                        a = st.pop()
                        for dx in (-1, 0, 1):
                            for dy in (-1, 0, 1):
                                n = (a[0] + dx, a[1] + dy)
                                if n not in seen and self.step_ok(a, n): seen.add(n); comp.add(n); st.append(n)
                    if len(comp) > len(best): best = comp
        return best
    def nearest_ok(self, x, y):
        t = (int(math.floor(x)), int(math.floor(y)))
        if t in self.main: return t
        best = None
        for ty in range(self.H):
            for tx in range(self.W):
                if (tx, ty) in self.main:
                    d = (tx + .5 - x) ** 2 + (ty + .5 - y) ** 2
                    if best is None or d < best[0]: best = (d, (tx, ty))
        return best[1]
    def astar(self, s, g):
        s, g = tuple(s), tuple(g)
        if s == g: return [s]
        openh = [(0, 0, s)]; came = {s: None}; cost = {s: 0}
        while openh:
            _, c, cur = heapq.heappop(openh)
            if cur == g: break
            if c > cost[cur]: continue
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if not dx and not dy: continue
                    n = (cur[0] + dx, cur[1] + dy)
                    if not self.step_ok(cur, n): continue
                    nc = c + (1.4142 if dx and dy else 1.0)
                    if nc < cost.get(n, 1e9):
                        cost[n] = nc; came[n] = cur
                        h = max(abs(n[0] - g[0]), abs(n[1] - g[1])) + 0.4142 * min(abs(n[0] - g[0]), abs(n[1] - g[1]))
                        heapq.heappush(openh, (nc + h, nc, n))
        if g not in came: return None
        out = [g]
        while came[out[-1]] is not None: out.append(came[out[-1]])
        return out[::-1]
    def path(self, p0, p1):
        """world-space polyline from p0 to p1 through walkable tile centres (None if unreachable)"""
        a = self.nearest_ok(*p0); b = self.nearest_ok(*p1)
        tiles = self.astar(a, b)
        if tiles is None: return None
        pts = [list(p0)] + [[t[0] + .5, t[1] + .5] for t in tiles[1:-1]] + [list(p1)]
        if len(tiles) == 1: pts = [list(p0), list(p1)]
        # drop collinear interior points
        out = [pts[0]]
        for i in range(1, len(pts) - 1):
            ax, ay = out[-1]; bx, by = pts[i]; cx, cy = pts[i + 1]
            if abs((bx - ax) * (cy - by) - (by - ay) * (cx - bx)) > 1e-6: out.append(pts[i])
        out.append(pts[-1])
        return [[round(x, 3), round(y, 3)] for x, y in out]

    def zone_of(self, pos):
        for z, (x0, y0, w, h) in self.zones.items():
            if x0 <= pos[0] < x0 + w and y0 <= pos[1] < y0 + h: return z
        return self.id
    def place_name(self, pos):
        z = self.zone_of(pos)
        return {'4A': 'apartment 4A', '4B': 'apartment 4B', 'hall_4f': 'the 4th-floor hall'}.get(z, self.name)
    def hook_label(self, h):
        return h['item'].split('_', 1)[1].replace('_', ' ') if '_' in h['item'] else h['item']
    def spawn_pos(self, name):
        v = self.spawns.get(name)
        if isinstance(v, list): return list(v)
        if isinstance(v, str) and v in self.hooks: return list(self.hooks[v]['pos'])
        return None

class World:
    def __init__(self):
        wj = json.load(open(os.path.join(WORLD_DIR, 'world.json')))
        self.scenes = {}
        for n in wj['nodes']:
            p = os.path.join(WORLD_DIR, n['id'], 'scene.json')
            if os.path.exists(p): self.scenes[n['id']] = Scene(json.load(open(p)))
        # directed links: loc -> [(exit_id, to_loc, to_spawn, via)]
        self.links = {k: [] for k in self.scenes}
        for sid, sc in self.scenes.items():
            for e in sc.exits.values():
                to = e.get('to')
                if to in self.scenes:
                    spawn = (e.get('to_spawn') or '').split(' ')[0]
                    self.links[sid].append((e['id'], to, spawn, e.get('via', 'door')))
        self.edges = wj.get('edges', [])
        self.occ = {}       # (loc, hook_id) -> [agent names]

    def route(self, a, b):
        """BFS over the world graph: list of hops (exit_id, to_loc, to_spawn, via)"""
        if a == b: return []
        q = deque([a]); prev = {a: None}
        while q:
            cur = q.popleft()
            if cur == b: break
            for hop in self.links[cur]:
                if hop[1] not in prev: prev[hop[1]] = (cur, hop); q.append(hop[1])
        if b not in prev: return None
        hops = []; cur = b
        while prev[cur] is not None: c, hop = prev[cur]; hops.append(hop); cur = c
        return hops[::-1]

    # ------------------------------------------------------------------ hook reservations
    def free(self, loc, hid):
        h = self.scenes[loc].hooks[hid]
        return len(self.occ.get((loc, hid), [])) < h.get('capacity', 1)
    def occupants(self, loc, hid): return list(self.occ.get((loc, hid), []))
    def reserve(self, loc, hid, who):
        if not self.free(loc, hid): return False
        self.occ.setdefault((loc, hid), []).append(who); return True
    def release(self, loc, hid, who):
        l = self.occ.get((loc, hid), [])
        if who in l: l.remove(who)
