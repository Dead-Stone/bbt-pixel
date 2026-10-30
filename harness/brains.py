"""Pluggable agent brains.

MockBrain  deterministic, offline, rule-based (seeded RNG per agent/time): day plans from the persona routine,
           hook choice, conversation topics + lines from lines.py, importance scores, reflections.
LLMBrain   any OpenAI-compatible chat-completions endpoint, configured only through env vars:
             LLM_API_KEY   (required; if unset the harness uses MockBrain)
             LLM_BASE_URL  (default https://api.openai.com/v1; works with local servers such as Ollama/vLLM/LM Studio)
             LLM_MODEL     (default gpt-4o-mini)
             LLM_MAX_CALLS (default 400; budget per run, after which the mock takes over)
           Used for dialogue lines, reflections and plan tweaks; every call falls back to the mock on any error.
No secret is stored or logged; the key is read from the environment at run time only.
"""
import os, json, random, hashlib, urllib.request, urllib.error
from lines import OPEN, REPLY, CLOSE, TOPIC, FOOD
from personas import PERSONAS

# lines that mention a time of day stop making sense after it (mock brain only)
STALE = [('half two', 14 * 3600 + 1800), ('quarter to seven', 18 * 3600 + 2400), ('6:40', 18 * 3600 + 2400),
         ('at noon', 12 * 3600), ('8:10', 8 * 3600 + 600), ('Lunch', 13 * 3600), ('lunch', 13 * 3600), ('morning', 12 * 3600)]

def hhmm(t): t = int(t) % 86400; return f'{t // 3600:02d}:{t % 3600 // 60:02d}'
def tsec(s): h, m = map(int, s.split(':')); return h * 3600 + m * 60

class MockBrain:
    name = 'mock'
    def __init__(self, seed=7):
        self.seed = seed; self.used = {}; self.counts = {}
    def rng(self, *key):
        h = hashlib.sha256(('|'.join(map(str, (self.seed,) + key))).encode()).digest()
        return random.Random(int.from_bytes(h[:8], 'big'))

    # ---------------------------------------------------------------- planning
    def plan_day(self, cid, date):
        r = self.rng('plan', cid, date); plan = []
        for b in PERSONAS[cid]['routine']:
            t = tsec(b['t'])
            if b['t'] != '06:55': t += r.choice([-3, -2, -1, 0, 0, 1, 2, 3]) * 60   # a little human jitter
            plan.append(dict(b, start=t))
        for i, b in enumerate(plan):
            b['end'] = plan[i + 1]['start'] if i + 1 < len(plan) else tsec('23:59')
        return plan
    def describe_plan(self, cid, plan):
        return '; '.join(f"{hhmm(b['start'])} {b['act']}" for b in plan)

    # ---------------------------------------------------------------- acting
    def choose_hook(self, cid, t, candidates):
        """candidates: [(selector, hook)] all free; prefer owned hooks, else a seeded pick weighted to the first selector"""
        if not candidates: return None
        own = [c for c in candidates if c[1].get('owner') == cid]
        if own: return own[0]
        r = self.rng('hook', cid, t)
        w = [1.0 / (1 + i) for i in range(len(candidates))]
        return r.choices(candidates, weights=w)[0]
    def duration(self, cid, t, sel):
        return self.rng('dur', cid, t).randint(sel['lo'], sel['hi']) * 60

    def want_chat(self, cid, t, social, others):
        return self.rng('chat', cid, t // 60).random() < 0.07 * social * (1 + 0.3 * len(others))

    # ---------------------------------------------------------------- conversation
    def pick_topic(self, cid, others, ctx):
        loc, act = ctx['loc'], ctx['act'].lower()
        pool = ['science', 'plans', 'work']
        if 'lunch' in act: pool += ['lunch'] * 3
        if 'dinner' in act or loc == 'rest_amber_slice': pool += ['dinner'] * 3
        if 'game night' in act: pool += ['gamenight'] * 3
        if loc == 'street_exterior' or ctx.get('just_travelled'): pool += ['commute'] * 2
        if ctx.get('mem'): pool += ['memory'] * 2
        return self.rng('topic', cid, ctx['t']).choice(pool)
    def line(self, cid, to, topic, turn, n_turns, ctx):
        r = self.rng('line', cid, ctx['t'], turn)
        o = PERSONAS[to]['name'] if to else 'everyone'
        if turn == 0: bank = OPEN[cid]
        elif turn == n_turns - 1: bank = CLOSE[cid]
        elif turn % 2 == 1 or topic not in TOPIC: bank = TOPIC.get(topic, {}).get(cid) or REPLY[cid]
        else: bank = REPLY[cid] + TOPIC.get(topic, {}).get(cid, [])
        if turn == 1 and topic == 'memory' and not ctx.get('mem'): bank = TOPIC['plans'][cid]
        used = {x for _, x in ctx.get('history', [])}
        tod = ctx['t']
        def ok(x):
            if x.format(o=o, place='', time='', mem='', food='', late='')[:30] in {u[:30] for u in used}: return False
            if '{mem}' in x and not (ctx.get('mem') and cid == ctx.get('mem_by') and to == ctx.get('mem_to')): return False
            for pat, until in STALE:
                if pat in x and tod > until: return False
            return True
        recent = self.used.setdefault(cid, [])
        fresh = ([x for x in bank if ok(x) and x not in recent] or [x for x in REPLY[cid] if ok(x) and x not in recent]
                 or [x for x in bank if ok(x)] or bank)
        cnt = self.counts.setdefault(cid, {}); low = min(cnt.get(x, 0) for x in fresh)
        s = r.choice([x for x in fresh if cnt.get(x, 0) == low])      # least-used lines first: spreads the small banks over the day
        cnt[s] = cnt.get(s, 0) + 1
        recent.append(s); del recent[:-10]
        return s.format(o=o, place=ctx.get('place', ''), time=hhmm(ctx['t']), mem=ctx.get('mem', 'you were busy'),
                        food=r.choice(FOOD), late=r.randint(2, 9))
    def summarize(self, cid, others, topic, lines):
        names = ', '.join(PERSONAS[o]['name'] for o in others)
        return f"talked with {names} about {topic}" + (f": \"{lines[1][1]}\"" if len(lines) > 1 else '')

    # ---------------------------------------------------------------- memory
    def importance(self, cid, text):
        t = text.lower(); s = 2
        for o, rel in PERSONAS[cid]['rel'].items():
            if PERSONAS[o]['name'].lower() in t: s += 2 if any(k in rel for k in ('girlfriend', 'boyfriend', 'wife', 'husband', 'best')) else 1
        if 'talked' in t: s += 2
        if 'my spot' in t or 'seat0' in t: s += 2
        return min(10, s)
    def reflect(self, cid, t, mems):
        names = {}
        for m in mems:
            for o in PERSONAS:
                if o != cid and PERSONAS[o]['name'] in m['text']: names[o] = names.get(o, 0) + m['imp']
        r = self.rng('reflect', cid, t)
        if not names: return r.choice(["Today has mostly been me and my work. That is fine. Mostly.",
                                       "I have kept to my plan today; the morning feels like a long time ago."])
        top = max(names, key=names.get); nm = PERSONAS[top]['name']
        rel = PERSONAS[cid]['rel'].get(top, 'friend')
        talks = sum(1 for m in mems if m['kind'] == 'conversation' and nm in m['text'])
        T = [f"{nm} keeps turning up in my day ({rel}). I should make real time for {nm} tonight.",
             f"I've talked with {nm} {talks or 'a few'} time(s) today. That matters to me more than I'd say out loud.",
             f"Note to self: {nm} seemed busy earlier. Ask how it's going instead of talking about myself.",
             f"Pattern: wherever I go today, {nm} is nearby. Coincidence, or I like it that way."]
        if hhmm(t) >= '20:00': T.append(f"Good day overall. Tonight with everyone, {nm} included, is the part I was looking forward to.")
        return r.choice(T)

class LLMBrain(MockBrain):
    name = 'llm'
    def __init__(self, seed=7):
        super().__init__(seed)
        self.key = os.environ.get('LLM_API_KEY', '')
        self.base = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
        self.model = os.environ.get('LLM_MODEL', 'gpt-4o-mini')
        self.budget = int(os.environ.get('LLM_MAX_CALLS', '400'))
        self.calls = 0; self.failures = 0; self.last_error = ''
    def chat(self, system, user, max_tokens=120):
        if self.calls >= self.budget or self.failures >= 5: return None
        self.calls += 1
        body = json.dumps(dict(model=self.model, temperature=0.8, max_tokens=max_tokens,
                               messages=[dict(role='system', content=system), dict(role='user', content=user)])).encode()
        req = urllib.request.Request(self.base + '/chat/completions', data=body, method='POST',
                                     headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.key})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                out = json.loads(resp.read().decode())
            return out['choices'][0]['message']['content'].strip()
        except Exception as e:      # network, auth, schema: fall back to the mock for this call
            self.failures += 1; self.last_error = type(e).__name__; return None
    def persona_prompt(self, cid):
        p = PERSONAS[cid]
        return (f"You are {p['name']}, {p['role']}, an autonomous character in a cozy pixel-art sitcom simulation. "
                f"Traits: {', '.join(p['traits'])}. Speaking style: {p['style']}. Tendencies: {'; '.join(p['tics'])}. "
                "Write ORIGINAL dialogue only: never quote or paraphrase lines from any TV show or film, no famous catchphrases. "
                "Places in this world are called AIT (Arroyo Institute of Technology), The Amber Slice, and LOS ROBLES AV.")
    def line(self, cid, to, topic, turn, n_turns, ctx):
        hist = '\n'.join(f"{PERSONAS[s]['name']}: {x}" for s, x in ctx.get('history', [])[-6:])
        mems = '; '.join(ctx.get('mems', [])[:4])
        role = 'open the conversation' if turn == 0 else ('wrap up the conversation' if turn == n_turns - 1 else 'reply')
        u = (f"Time {hhmm(ctx['t'])} at {ctx.get('place')}. You are talking to {PERSONAS[to]['name'] if to else 'the group'} "
             f"(relationship: {PERSONAS[cid]['rel'].get(to, 'friend')}). Topic: {topic}. Your recent memories: {mems or 'none'}.\n"
             f"Conversation so far:\n{hist or '(none)'}\nNow {role} with ONE short line (max 25 words), no name prefix, no quotes.")
        out = self.chat(self.persona_prompt(cid), u, 60)
        if not out: return super().line(cid, to, topic, turn, n_turns, ctx)
        out = out.strip().split('\n')[0]
        nm = PERSONAS[cid]['name'] + ':'
        if out.startswith(nm): out = out[len(nm):]
        return out.strip().strip('"').strip()[:220] or super().line(cid, to, topic, turn, n_turns, ctx)
    def reflect(self, cid, t, mems):
        u = ("Here are your most important recent memories:\n" + '\n'.join(f"- {m['text']}" for m in mems[:10]) +
             "\nWrite ONE first-person insight (max 30 words) about your relationships or plans.")
        out = self.chat(self.persona_prompt(cid), u, 80)
        return out.split('\n')[0][:240] if out else super().reflect(cid, t, mems)
    def plan_day(self, cid, date):
        plan = super().plan_day(cid, date)
        u = ("Your fixed schedule for today (times and places cannot change):\n" + self.describe_plan(cid, plan) +
             "\nReturn a JSON list of the same length with a short, original, first-person intention for each block (max 12 words each).")
        out = self.chat(self.persona_prompt(cid), u, 300)
        try:
            notes = json.loads(out[out.index('['):out.rindex(']') + 1]) if out else None
            if isinstance(notes, list) and len(notes) == len(plan):
                for b, n in zip(plan, notes): b['intent'] = str(n)[:120]
        except Exception: pass
        return plan

def make_brain(kind='auto', seed=7):
    """auto: LLMBrain when LLM_API_KEY is set, else MockBrain.  llm without a key -> MockBrain (with a notice)."""
    have_key = bool(os.environ.get('LLM_API_KEY'))
    if kind == 'mock' or (kind in ('auto', 'llm') and not have_key):
        if kind == 'llm': print('[harness] LLM_API_KEY not set -> using the offline mock brain')
        return MockBrain(seed)
    return LLMBrain(seed)
