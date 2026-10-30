"""Simulation core: agents, world clock (1 s ticks), perception, action execution against the engine hooks,
travel over the world graph, conversations, memory/reflection, event log + per-agent motion tracks for the viewer."""
import math, json, os, time as _time
from world import World, dir_of, TRAVEL_SECONDS
from personas import PERSONAS, ORDER, WORK_HOOK_TYPES, WORK_ITEMS
from memory import Memory
from brains import hhmm, tsec
from seating import seat_place

SIT_TYPES = ('sit', 'perch')
def is_work(h):
    """hooks that play the job animation (work/write hooks, laptops, whiteboards, the server station)"""
    hid = str(h.get('id', ''))
    return h.get('type') in WORK_HOOK_TYPES or any(w in hid for w in WORK_ITEMS)
PERCEIVE_EVERY = 20       # s
CHAT_CHECK_EVERY = 60     # s
CHAT_RADIUS = 6.0         # tiles
PAIR_COOLDOWN = 25 * 60   # s

IRREG = {'sits': 'sat', 'eats': 'ate', 'reads': 'read', 'makes': 'made', 'runs': 'ran', 'takes': 'took', 'has': 'had', 'is': 'was',
         'drinks': 'drank', 'grabs': 'grabbed', 'logs': 'logged', 'plans': 'planned', 'shops': 'shopped', 'stops': 'stopped',
         'swaps': 'swapped', 'joins': 'joined', 'leaves': 'left', 'heads': 'headed', 'gets': 'got', 'puts': 'put', 'feeds': 'fed',
         'writes': 'wrote', 'stands': 'stood', 'sets': 'set', 'brings': 'brought', 'buys': 'bought', 'tells': 'told', 'hits': 'hit',
         'plates': 'plated', 'unwinds': 'unwound', 'goes': 'went', 'does': 'did', 'chats': 'chatted', 'naps': 'napped', 'debugs': 'debugged', 'preps': 'prepped', 'jogs': 'jogged'}
def past(phrase):
    w, _, rest = phrase.partition(' ')
    if w in IRREG: v = IRREG[w]
    elif w.endswith('ies'): v = w[:-3] + 'ied'
    elif w.endswith(('shes', 'ches', 'sses', 'xes')): v = w[:-2] + 'ed'
    elif w.endswith('es') and w[-3] in 'aeiouvgcrzt': v = w[:-1] + 'd'
    elif w.endswith('s'): v = w[:-1] + 'ed'
    else: v = w
    return (v + ' ' + rest).strip()

def plen(pts): return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))

DOOR_NAMES = {'(doorway gap)': 'office doorway', 'off_door': 'office door', 'ext_entrance_doors': 'building entrance',
              'rest_kitchen_door': 'kitchen door', 'lobby_glass_door': 'glass door', '4a_front_door': '4A front door',
              '4b_front_door': '4B front door'}
def door_label(loc, item):
    if loc == 'raj_apartment' and item == '4a_front_door': return 'front door'
    return DOOR_NAMES.get(item, item.replace('_', ' ').strip('()'))

class Agent:
    def __init__(self, cid, brain):
        self.cid = cid; self.p = PERSONAS[cid]; self.name = self.p['name']; self.brain = brain
        self.mem = Memory(cid); self.plan = []
        self.loc = None; self.pos = None; self.dir = 'SW'; self.state = 'offstage'
        self.track = []; self.walk = None; self.after_walk = None
        self.hook = None; self.until = 0; self.status = 'off-screen'
        self.block_i = -1; self.step_i = 0; self.convo = None; self.travel = None
        self.hops = []; self.seen = {}; self.force = None; self.slept = None; self.next_chat = 0; self.wait_until = 0

    # ---------------------------------------------------------------- tracks for the viewer
    def seg(self, t, **kw):
        if self.track and self.track[-1].get('t1') is None: self.track[-1]['t1'] = t
        kw.update(t0=t, t1=None); self.track.append(kw)
    def still(self, t, sit=False, z=0.0, key=None, hook=None, act=None):
        """act='work': the viewer loops the character's job animation (whiteboard/laptop/microscope/pipette/tray)"""
        self.seg(t, kind='sit' if sit else 'stand', loc=self.loc, pos=[round(self.pos[0], 3), round(self.pos[1], 3)], dir=self.dir,
                 z=z, **({'key': key} if key is not None else {}), **({'hook': hook} if hook else {}), **({'act': act} if act else {}))
    def away(self, t, why):
        self.seg(t, kind='away', why=why)

    def pos_at(self, t):
        if self.walk is None: return self.pos
        pts, t0, sp = self.walk['pts'], self.walk['t0'], self.walk['speed']
        d = (t - t0) * sp
        for i in range(len(pts) - 1):
            L = math.dist(pts[i], pts[i + 1])
            if d <= L:
                f = d / L if L else 1
                return [pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f]
            d -= L
        return list(pts[-1])

class Sim:
    def __init__(self, brain, date='2026-10-30', start='06:55', end='23:45', log_every=None):
        self.brain = brain; self.date = date
        self.t = tsec(start); self.t_end = tsec(end); self.t_start = self.t
        self.w = World()
        self.agents = {c: Agent(c, brain) for c in ORDER}
        self.events = []; self.convos = []; self.pair_last = {}
        self.cars = {}     # (from_loc, exit) -> list of (t, cid) for carpool grouping

    # ---------------------------------------------------------------- logging
    def ev(self, type_, agent=None, **kw):
        e = dict(t=self.t, type=type_); 
        if agent: e['agent'] = agent.cid; e.setdefault('loc', agent.loc)
        e.update(kw); self.events.append(e); return e
    def scene(self, a): return self.w.scenes[a.loc]
    def place(self, a): return self.scene(a).place_name(a.pos) if a.loc else 'off-screen'
    def observe(self, a, text, subject=None, dedupe=1800, imp=None):
        m = a.mem.add(self.t, 'observation', text, imp if imp is not None else self.brain.importance(a.cid, text), subject, dedupe)
        return m

    # ---------------------------------------------------------------- movement primitives
    def appear(self, a, loc, pos, why):
        sc = self.w.scenes[loc]; pos = list(pos)
        taken = [o.pos for o in self.agents.values() if o is not a and o.loc == loc and o.pos is not None]
        if any(math.dist(pos, q) < 0.6 for q in taken):      # step aside if someone just arrived on the same spot
            for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1)):
                q = [pos[0] + dx, pos[1] + dy]
                if sc.ok((int(math.floor(q[0])), int(math.floor(q[1])))) and not any(math.dist(q, r) < 0.6 for r in taken):
                    pos = q; break
        a.loc = loc; a.pos = pos; a.state = 'idle'; a.walk = None
        a.still(self.t)
        self.ev('appear', a, pos=a.pos, why=why, place=self.place(a))
        self.observe(a, f"arrived at {self.place(a)} ({why})", imp=2)
    def go_offstage(self, a, why):
        if a.hook: self.w.release(a.loc, a.hook['id'], a.cid); a.hook = None
        self.ev('offstage', a, why=why)
        a.loc = None; a.pos = None; a.state = 'offstage'; a.walk = None; a.status = why
        a.away(self.t, why)
    def walk_to(self, a, target, then, label):
        sc = self.scene(a)
        pts = sc.path(a.pos, target)
        if pts is None or len(pts) < 2 or plen(pts) < 0.05:
            a.pos = list(target); then(); return
        a.walk = dict(pts=pts, t0=self.t, speed=a.p.get('speed', 1.3), t1=self.t + plen(pts) / a.p.get('speed', 1.3))
        a.dir = dir_of(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1], a.dir)
        a.state = 'walking'; a.after_walk = then; a.status = label
        a.seg(self.t, kind='walk', loc=a.loc, pts=pts, speed=a.walk['speed'])
        self.ev('walk', a, to=label, dist=round(plen(pts), 1), eta=round(a.walk['t1'] - self.t, 1))
        self.door_events(a, pts)
    def door_events(self, a, pts):
        doors = {tuple(d['tile']): d['item'] for d in self.scene(a).d.get('doors', []) if 'stair' not in d['item']}
        if not doors: return
        d = 0.0; seen = set(); sp = a.walk['speed']
        end = [int(math.floor(pts[-1][0])), int(math.floor(pts[-1][1]))]
        end_exit = any(end in [list(t) for t in ex['tiles']] for ex in self.scene(a).exits.values())
        for i in range(len(pts) - 1):
            L = math.dist(pts[i], pts[i + 1]); n = max(1, int(L / 0.2))
            for k in range(n):
                f = k / n; x = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f; y = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f
                tile = (int(math.floor(x)), int(math.floor(y)))
                if tile in doors and tile not in seen and (math.dist((x, y), pts[-1]) > 1.0 or end_exit):   # knocking outside is not going through
                    seen.add(tile)
                    self.events.append(dict(t=round(self.t + (d + L * f) / sp, 1), type='door', agent=a.cid, loc=a.loc, item=doors[tile],
                                            label=door_label(a.loc, doors[tile]), tile=list(tile)))
            d += L
    def finish_walk(self, a):
        pts = a.walk['pts']; a.pos = list(pts[-1])
        a.dir = dir_of(pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1], a.dir)
        a.walk = None; a.state = 'idle'
        cb = a.after_walk; a.after_walk = None
        if cb: cb()
        if a.state == 'idle': a.still(self.t)

    # ---------------------------------------------------------------- hooks
    def stand_spot(self, sc, h):
        if h['type'] in SIT_TYPES: return list(h['pos'])
        tx, ty = int(math.floor(h['pos'][0])), int(math.floor(h['pos'][1]))
        if sc.ok((tx, ty)): return list(h['pos'])
        ax, ay = h['approach_tile']; return [ax + .5, ay + .5]
    def matches(self, h, sel):
        if sel.get('item') and not h['item'].startswith(sel['item']): return False
        ty = sel.get('type')
        if ty and h['type'] not in ((ty,) if isinstance(ty, str) else ty): return False
        if sel.get('hook') and not h['hook'].startswith(sel['hook']): return False
        return True
    def candidates(self, a, sel):
        sc = self.scene(a); zone = sc.zone_of(a.pos) if sc.id != 'floor4' else None
        out = []
        for h in sc.hooks.values():
            if not self.matches(h, sel): continue
            occ = self.w.occupants(a.loc, h['id'])
            if a.cid in occ: continue
            if self.w.free(a.loc, h['id']): out.append((sel, h))
            elif h.get('owner') == a.cid: out.append((sel, dict(h, evict=occ[0])))
        return out
    def use_hook(self, a, sel, h):
        sc = self.scene(a)
        if h.get('evict'):
            pass
        elif not self.w.reserve(a.loc, h['id'], a.cid): return False
        label = sel.get('label') or f"uses the {sc.hook_label(h)}"
        spot = self.stand_spot(sc, h)
        ax, ay = h['approach_tile']; app = [ax + .5, ay + .5]
        def at_hook():
            if h.get('evict'):
                self.evict(a, h)
            a.hook = sc.hooks[h['id']]; a.pos = list(spot)
            sit = h['type'] in SIT_TYPES
            if sit or math.dist(spot, h['pos']) < 0.2: a.dir = h['facing']
            else: a.dir = dir_of(h['pos'][0] - spot[0], h['pos'][1] - spot[1], h['facing'])
            dur = self.brain.duration(a.cid, self.t, sel)
            a.state = 'using'; a.until = self.t + dur; a.status = label; a.hook_block = self.block(a)[0]
            if sit:   # seat point / seat height / facing / depth key exported per hook (tools/seating.py)
                sp = seat_place(h); a.pos = list(sp['pos']); a.dir = sp['dir']
                a.still(self.t, sit=True, z=sp['z'], key=sp['key'], hook=h['id'])
            else: a.still(self.t, act='work' if is_work(h) else None)
            self.ev('hook_start', a, hook=h['id'], hook_type=h['type'], activity=label, minutes=round(dur / 60), place=self.place(a),
                    **({'anim': 'work'} if is_work(h) and not sit else {}))
            if h['type'] == 'knock_spot_outside' and 'knock_knock_penny' in a.p.get('emotes', {}):
                self.events.append(dict(t=round(self.t + 0.5, 1), type='emote', agent=a.cid, loc=a.loc, anim='knock_knock_penny'))
            self.observe(a, f"I {label.replace('his ', 'my ').replace('her ', 'my ')} in {self.place(a)}", imp=2)
        def to_seat():
            if math.dist(a.pos, spot) > 0.05 and h['type'] in SIT_TYPES:
                pts = [list(a.pos), list(spot)]
                a.walk = dict(pts=pts, t0=self.t, speed=1.0, t1=self.t + plen(pts))
                a.state = 'walking'; a.after_walk = at_hook
                a.seg(self.t, kind='walk', loc=a.loc, pts=pts, speed=1.0)
            else: at_hook()
        self.walk_to(a, app if h['type'] in SIT_TYPES else spot, to_seat, label)
        return True
    def evict(self, a, h):
        sc = self.scene(a); occ = h['evict']; o = self.agents[occ]
        self.say(a, [occ], "Pardon me. That cushion is assigned to me by precedent, posture and a very detailed diagram.")
        self.say(o, [a.cid], {'leonard': "Okay, okay. It's all yours.", 'penny': "Fine. It's warm, you're welcome.",
                              'howard': "Ladies and gentlemen, the throne is vacated.", 'raj': "Sorry! Sorry. I was just keeping it warm.",
                              'bernadette': "Sure, sweetie. This time.", 'amy': "Of course. I was studying the view from your side."}.get(occ, "Fine."), dt=3)
        self.release_hook(o, early=True)
        o.wait_until = self.t + 8
        self.w.reserve(a.loc, h['id'], a.cid)
        self.ev('evict', a, hook=h['id'], who=occ)
        self.observe(o, f"{a.name} asked me to leave his spot on the couch", imp=5)
    def release_hook(self, a, early=False):
        if a.hook:
            self.w.release(a.loc, a.hook['id'], a.cid)
            self.ev('hook_end', a, hook=a.hook['id'], early=early)
            h = a.hook; a.hook = None
            if h['type'] in SIT_TYPES and a.loc:      # stand up and step off the seat to its approach tile
                ax, ay = h['approach_tile']; pts = [list(a.pos), [ax + .5, ay + .5]]
                if plen(pts) > 0.05:
                    a.walk = dict(pts=pts, t0=self.t, speed=1.0, t1=self.t + plen(pts)); a.state = 'walking'; a.after_walk = None
                    a.dir = dir_of(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1], a.dir)
                    a.seg(self.t, kind='walk', loc=a.loc, pts=pts, speed=1.0); return
        a.state = 'idle'; a.still(self.t) if a.loc else None

    # ---------------------------------------------------------------- travel
    def start_travel(self, a, hop):
        exit_id, to, spawn, via = hop
        sc = self.scene(a); ex = sc.exits[exit_id]
        tiles = [t for t in ex['tiles']]
        tgt = min(tiles, key=lambda t: math.dist(a.pos, [t[0] + .5, t[1] + .5]))
        def depart():
            g = getattr(a, 'ride', None)
            if via == 'car' and g:
                if self.t < g['deadline'] and a.cid not in g['ready']:
                    g['ready'][a.cid] = depart
                    if set(g['ready']) < g['members']:
                        a.state = 'waiting'; a.status = 'waits by the car'
                        a.still(self.t)
                        return
                for m in sorted(g['members']):
                    if m != a.cid and m in g['ready'] and getattr(self.agents[m], 'ride', None) is g:
                        self.agents[m].ride = None; g['ready'][m]()
                a.ride = None
            dur = TRAVEL_SECONDS.get(via, 30)
            key = (a.loc, exit_id, to)
            mates = [c for (tt, c) in self.cars.get(key, []) if self.t - tt < 180 and c != a.cid]
            self.cars.setdefault(key, []).append((self.t, a.cid))
            self.ev('depart', a, exit=exit_id, to=to, via=via, minutes=round(dur / 60, 1), with_=mates)
            if via == 'car' and mates:
                self.observe(a, f"rode in the car with {', '.join(self.agents[m].name for m in mates)} to {self.w.scenes[to].name}", imp=4)
            frm = a.loc
            a.loc = None; a.state = 'travelling'; a.travel = dict(to=to, spawn=spawn, via=via, frm=frm, until=self.t + dur)
            a.away(self.t, f'{via} to {to}'); a.status = f'{via} to {self.w.scenes[to].name}'
        self.walk_to(a, [tgt[0] + .5, tgt[1] + .5], depart, f"heads out ({via} to {self.w.scenes[to].name})")
    def arrive(self, a):
        tr = a.travel; a.travel = None
        sc = self.w.scenes[tr['to']]
        pos = sc.spawn_pos(tr['spawn']) or [sc.W / 2, sc.H / 2]
        self.appear(a, tr['to'], pos, f"{tr['via']} from {self.w.scenes[tr['frm']].name}")
        a.just_travelled = tr['via'] == 'car'

    # ---------------------------------------------------------------- deciding
    def block(self, a):
        n = len(a.plan) - 1
        for i, b in enumerate(a.plan):
            if b['start'] <= self.t < b['end']: n = i; break
        if a.force is not None:
            if n >= a.force: a.force = None
            else: return a.force, a.plan[a.force]
        return n, a.plan[n]
    def offer_ride(self, a, dest):
        """drivers bring along friends in the same place whose next block (within 15 min) heads to the same location"""
        if not a.p.get('drives'): return
        hops = self.w.route(a.loc, dest) or []
        if not any(h[3] == 'car' for h in hops): return     # only worth offering for an actual drive
        n = 0
        for o in self.agents.values():
            if o is a or o.loc != a.loc or o.convo or o.state not in ('idle', 'using') or o.force is not None: continue
            i0, _ = self.block(o)
            for j in range(i0 + 1, len(o.plan)):
                b = o.plan[j]
                if b['start'] - self.t > 900: break
                if b['loc'] == dest:
                    self.say(a, [o.cid], f"{o.name}, I'm heading out now. Want a ride?", dt=n * 6)
                    self.say(o, [a.cid], {'sheldon': "Leaving early. Unscheduled, but the alternative is the bus. Agreed."}.get(o.cid, "Yes! Give me two seconds."), dt=n * 6 + 3)
                    n += 1
                    o.force = j; o.wait_until = self.t + 5 + n * 6
                    self.ev('ride', a, who=o.cid, to=dest)
                    g = getattr(a, 'ride', None)
                    if not g or g['to'] != dest: g = a.ride = dict(to=dest, members={a.cid}, ready={}, deadline=self.t + 480)
                    g['members'].add(o.cid); o.ride = g
                    if o.state == 'using': self.release_hook(o, early=True)
                    break
    def decide(self, a):
        if self.t < a.wait_until or a.state == 'waiting': return
        i, b = self.block(a)
        if i != a.block_i:
            a.block_i = i; a.step_i = 0
            self.ev('block', a, act=b['act'], target=b['loc'] or 'off-screen', intent=b.get('intent'))
            a.mem.add(self.t, 'plan', f"{hhmm(self.t)} now: {b['act']}", 3)
        if a.state == 'offstage':
            if getattr(a, 'slept', None) == i: return
            if b['loc'] is None or b.get('leave') == 'sleep_until': return
            if b.get('arrive'):
                loc, sp = b['arrive']; sc = self.w.scenes[loc]
                pos = sc.spawn_pos(sp) or (sc.hooks[sp]['pos'] if sp in sc.hooks else None) or [sc.W / 2, sc.H / 2]
                if sp in sc.hooks and sc.hooks[sp]['type'] == 'door':
                    ax, ay = sc.hooks[sp]['approach_tile']; pos = [ax + .5, ay + .5]
                self.appear(a, loc, pos, 'arrives'); return
            home = a.p.get('home')
            if home:
                sc = self.w.scenes[home[0]]; sp = home[1]
                pos = sp if isinstance(sp, list) else (sc.spawn_pos(sp) or sc.hooks[sp]['approach_tile'])
                self.appear(a, home[0], pos, 'wakes up'); return
            return
        if a.state != 'idle': return
        # leaving the stage
        if b['loc'] is None:
            if a.loc != 'street_exterior':
                hops = self.w.route(a.loc, 'street_exterior'); self.start_travel(a, hops[0]); return
            self.start_travel_off(a); return
        if a.loc != b['loc']:
            if a.block_i != getattr(a, 'ride_offered', None): a.ride_offered = a.block_i; self.offer_ride(a, b['loc'])
            hops = self.w.route(a.loc, b['loc'])
            if hops: self.start_travel(a, hops[0]); return
        # in place: steps, then loop selectors
        sels = b['steps'][a.step_i:a.step_i + 1] if a.step_i < len(b['steps']) else b['loop']
        if not sels:
            if b.get('leave') == 'sleep': a.slept = i; self.go_offstage(a, 'goes to bed'); return
            self.wander(a); return
        if a.step_i < len(b['steps']): a.step_i += 1
        elif b.get('leave') == 'sleep': a.slept = i; self.go_offstage(a, 'goes to bed'); return
        cands = []
        for s in sels: cands += self.candidates(a, s)
        # perception-driven preference: hooks near friends (social) score first
        pick = self.brain.choose_hook(a.cid, self.t, cands)
        if pick and self.use_hook(a, *pick): return
        self.wander(a)
    def start_travel_off(self, a):
        sc = self.scene(a); ex = sc.exits.get('drive_campus')
        tgt = ex['tiles'][0]
        def gone(): self.go_offstage(a, 'drives off along LOS ROBLES AV')
        self.walk_to(a, [tgt[0] + .5, tgt[1] + .5], gone, 'walks to the car')
    def wander(self, a):
        sc = self.scene(a); r = self.brain.rng('wander', a.cid, self.t)
        zone = sc.zone_of(a.pos)
        tiles = [(x, y) for y in range(sc.H) for x in range(sc.W) if sc.ok((x, y)) and sc.zone_of((x + .5, y + .5)) == zone
                 and math.dist((x + .5, y + .5), a.pos) < 5]
        if not tiles: a.wait_until = self.t + 60; return
        x, y = r.choice(tiles)
        def done(): a.wait_until = self.t + r.randint(30, 120)
        self.walk_to(a, [x + .5, y + .5], done, 'wanders')

    # ---------------------------------------------------------------- perception
    def near(self, a, radius=CHAT_RADIUS):
        if not a.loc: return []
        sc = self.scene(a); z = sc.zone_of(a.pos); out = []
        for o in self.agents.values():
            if o is a or o.loc != a.loc or o.pos is None: continue
            p = o.pos_at(self.t)
            if sc.zone_of(p) == z and math.dist(p, a.pos_at(self.t)) <= radius: out.append(o)
        return out
    def perceive(self, a):
        if not a.loc: return
        for o in self.near(a, 8.0):
            m = self.observe(a, f"saw {o.name} in {self.place(a)}: {o.status}", subject=o.cid, dedupe=45 * 60)
            if m: m['about'] = (o.cid, o.status, self.place(a))
        if a.mem.since_reflect >= 90:
            mems = a.mem.retrieve(self.t, PERSONAS[a.cid]['name'], k=12, kinds=('observation', 'conversation'))
            txt = self.brain.reflect(a.cid, self.t, mems)
            a.mem.add(self.t, 'reflection', txt, 6); a.mem.since_reflect = 0
            self.ev('reflect', a, text=txt)

    # ---------------------------------------------------------------- conversation
    def say(self, a, to, text, dt=0):
        dur = round(1.6 + 0.055 * len(text), 1)
        e = dict(t=self.t + dt, type='say', agent=a.cid, loc=a.loc, to=to, text=text, dur=dur)
        self.events.append(e); return dur
    def maybe_chat(self, a):
        if a.convo or a.state not in ('using', 'idle') or not a.loc or self.t < a.next_chat: return
        i, b = self.block(a)
        if b['social'] <= 0: return
        others = [o for o in self.near(a) if not o.convo and o.state in ('using', 'idle')
                  and self.t - self.pair_last.get(frozenset((a.cid, o.cid)), -1e9) > PAIR_COOLDOWN]
        if not others or not self.brain.want_chat(a.cid, self.t, b['social'], others): return
        group = [a] + others[:2]
        mem = None
        tgt = others[0].cid
        recent = [m for m in a.mem.recent(self.t, 4 * 3600, kinds=('observation',))
                  if m.get('about') and m['about'][0] == tgt and m['about'][1] not in ('wanders', 'off-screen') and 'heads out' not in m['about'][1]]
        if recent:
            m = recent[-1]; mem = 'you ' + past(m['about'][1]).replace(' his ', ' your ').replace(' her ', ' your ')
        ctx = dict(t=self.t, loc=a.loc, act=b['act'], place=self.place(a), mem=mem, mem_by=a.cid, mem_to=tgt, just_travelled=getattr(a, 'just_travelled', False))
        topic = self.brain.pick_topic(a.cid, [o.cid for o in others], ctx)
        n = self.brain.rng('n', a.cid, self.t).randint(4, 7)
        lines = []; t = 0.0
        self.ev('convo_start', a, who=[g.cid for g in group], topic=topic, place=self.place(a))
        for k in range(n):
            sp = group[0] if k % 2 == 0 else group[1 + (k // 2) % (len(group) - 1)]
            to = group[1].cid if sp is group[0] else group[0].cid
            c2 = dict(ctx, t=self.t + int(t), history=lines, mems=[m['text'] for m in sp.mem.retrieve(self.t, topic, k=4)])
            tp = topic if not (topic == 'memory' and (sp is not group[0] or k > 2)) else 'plans'
            text = self.brain.line(sp.cid, to, tp, k, n, c2)
            d = self.say(sp, [g.cid for g in group if g is not sp], text, dt=t)
            lines.append((sp.cid, text)); t += d + 0.6
            em = self.brain.choose_emote(sp.cid, dict(c2, loc=sp.loc), text, k)     # body language picked by the brain
            if em and not (sp.hook and sp.hook.get('type') in SIT_TYPES):     # seated agents keep the sit pose
                self.events.append(dict(t=round(self.t + t - d - 0.6 + 0.3, 1), type='emote', agent=sp.cid, loc=sp.loc, anim=em))
        end = self.t + t
        for g in group:
            if not g.walk and g.state != 'using':     # standing: face the group's centre
                cx = sum(o.pos[0] for o in group) / len(group); cy = sum(o.pos[1] for o in group) / len(group)
                g.dir = dir_of(cx - g.pos[0], cy - g.pos[1], g.dir); g.still(self.t)
            g.convo = end; g.next_chat = end + 120
            if g.state == 'using': g.until = max(g.until, end + 20)
            else: g.wait_until = max(g.wait_until, end + 5)
            others_g = [o.cid for o in group if o is not g]
            g.mem.add(self.t, 'conversation', self.brain.summarize(g.cid, others_g, topic, lines), self.brain.importance(g.cid, ' '.join(self.agents[o].name for o in others_g)) + 2)
            for o in group:
                if o is not g: self.pair_last[frozenset((g.cid, o.cid))] = self.t
        self.convos.append(dict(t0=self.t, t1=end, who=[g.cid for g in group], topic=topic, loc=a.loc, lines=lines))
        self.events.append(dict(t=round(end, 1), type='convo_end', agent=a.cid, loc=a.loc, who=[g.cid for g in group]))
        a.just_travelled = False

    # ---------------------------------------------------------------- main loop
    def run(self, realtime=0.0, on_flush=None, flush_every=60):
        for a in self.agents.values():
            a.plan = self.brain.plan_day(a.cid, self.date)
            a.mem.plan = a.plan
            self.ev('plan', a, plan=[dict(t=hhmm(b['start']), act=b['act'], loc=b['loc'] or 'off-screen', intent=b.get('intent')) for b in a.plan])
            a.away(self.t, 'not yet in scene')
        wall0 = _time.time()
        while self.t < self.t_end:
            for a in self.agents.values():
                if a.convo and self.t >= a.convo: a.convo = None
                if a.state == 'travelling' and self.t >= a.travel['until']: self.arrive(a)
                elif a.state == 'walking' and self.t >= a.walk['t1']: self.finish_walk(a)
                elif a.state == 'waiting' and self.t >= a.ride['deadline']:
                    g = a.ride; a.ride = None
                    for m in g['members']:            # give up waiting: whoever is ready leaves now
                        if m in g['ready'] and getattr(self.agents[m], 'ride', None) is g:
                            self.agents[m].ride = None; g['ready'][m]()
                elif a.state == 'using' and not a.convo and (self.t >= a.until or self.block(a)[0] != a.hook_block):
                    self.release_hook(a, early=self.t < a.until)
                if not a.convo: self.decide(a)
                if self.t % PERCEIVE_EVERY == ORDER.index(a.cid): self.perceive(a)
                if self.t % CHAT_CHECK_EVERY == (ORDER.index(a.cid) * 4) % CHAT_CHECK_EVERY: self.maybe_chat(a)
            self.t += 1
            if realtime:
                lag = (self.t - self.t_start) / realtime - (_time.time() - wall0)
                if lag > 0: _time.sleep(lag)
            if on_flush and self.t % flush_every == 0: on_flush(self)
        for a in self.agents.values():
            if a.track and a.track[-1]['t1'] is None: a.track[-1]['t1'] = self.t
        self.events.sort(key=lambda e: e['t'])
        if on_flush: on_flush(self)
        return self

    # ---------------------------------------------------------------- output
    def snapshot(self):
        return dict(meta=dict(date=self.date, t_start=self.t_start, t_end=self.t_end, t_now=self.t, brain=self.brain.name,
                              llm_calls=getattr(self.brain, 'calls', 0), agents=ORDER,
                              names={c: PERSONAS[c]['name'] for c in ORDER}, locations=list(self.w.scenes)),
                    tracks={c: a.track for c, a in self.agents.items()},
                    events=sorted(self.events, key=lambda e: e['t']),
                    memories={c: dict(reflections=[m['text'] for m in a.mem.items if m['kind'] == 'reflection'],
                                      n_items=len(a.mem.items)) for c, a in self.agents.items()})
    def text_log(self):
        out = []
        for e in sorted(self.events, key=lambda e: e['t']):
            nm = PERSONAS[e['agent']]['name'] if e.get('agent') else ''
            loc = e.get('loc') or '-'
            ts = f"{int(e['t']) // 3600:02d}:{int(e['t']) % 3600 // 60:02d}:{int(e['t']) % 60:02d}"
            ty = e['type']
            if ty == 'say': s = f'{nm}: "{e["text"]}"'
            elif ty == 'hook_start': s = f"{nm} {e['activity']} [{e['hook']}, {e['minutes']} min]"
            elif ty == 'depart': s = f"{nm} leaves by {e['via']} -> {e['to']}" + (f" (with {', '.join(PERSONAS[m]['name'] for m in e['with_'])})" if e.get('with_') else '')
            elif ty == 'appear': s = f"{nm} appears at {e['place']} ({e['why']})"
            elif ty == 'offstage': s = f"{nm} {e['why']}"
            elif ty == 'convo_start': s = f"-- conversation: {', '.join(PERSONAS[c]['name'] for c in e['who'])} on '{e['topic']}' at {e['place']}"
            elif ty == 'reflect': s = f"{nm} reflects: {e['text']}"
            elif ty == 'emote': s = f"{nm} *{e['anim'].replace('_', ' ')}*"
            elif ty == 'block': s = f"{nm} plan -> {e['act']} ({e['target']})"
            elif ty == 'evict': s = f"{nm} reclaims {e['hook']} from {PERSONAS[e['who']]['name']}"
            elif ty == 'walk': s = f"{nm} walks: {e['to']} ({e['dist']} m)"
            elif ty == 'door': s = f"{nm} goes through the {e.get('label') or e['item']}"
            elif ty == 'ride': s = f"{nm} offers {PERSONAS[e['who']]['name']} a ride to {e['to']}"
            else: continue
            out.append(f"{ts} [{loc}] {s}")
        return '\n'.join(out)
