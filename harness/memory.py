"""Generative-Agents-style memory stream: observations, conversations, reflections and the day plan, retrieved by
recency x importance x relevance (keyword overlap)."""
import re

def words(s): return set(w for w in re.findall(r'[a-z0-9]+', s.lower()) if len(w) > 2)

class Memory:
    def __init__(self, owner):
        self.owner = owner; self.items = []; self.plan = []; self.reflections = []
        self.since_reflect = 0.0; self._last = {}

    def add(self, t, kind, text, importance=3, subject=None, dedupe_s=0):
        if subject and dedupe_s:
            prev = self._last.get(subject)
            if prev and prev[1] == text and t - prev[0] < dedupe_s: return None
            self._last[subject] = (t, text)
        m = dict(t=t, kind=kind, text=text, imp=importance, kw=words(text))
        self.items.append(m)
        if kind != 'reflection': self.since_reflect += importance
        return m

    def retrieve(self, t, query='', k=5, kinds=None):
        q = words(query)
        def score(m):
            rec = 0.995 ** max(0.0, (t - m['t']) / 60.0)
            rel = len(q & m['kw']) / (len(q) or 1)
            return rec + m['imp'] / 10.0 + 1.5 * rel
        pool = [m for m in self.items if kinds is None or m['kind'] in kinds]
        return sorted(pool, key=score, reverse=True)[:k]

    def recent(self, t, window_s=3600, kinds=None):
        return [m for m in self.items if t - m['t'] <= window_s and (kinds is None or m['kind'] in kinds)]
