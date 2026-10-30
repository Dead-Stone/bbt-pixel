"""python3 -m harness [run] [--brain auto|mock|llm] [--seed N] [--start HH:MM] [--end HH:MM] [--serve] [--port 8765] [--live X]"""
import argparse, json, os, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from brains import make_brain
from sim import Sim

def main():
    ap = argparse.ArgumentParser(prog='python3 -m harness')
    ap.add_argument('cmd', nargs='?', default='run', choices=['run', 'serve', 'export'])
    ap.add_argument('--brain', default='auto', choices=['auto', 'mock', 'llm'])
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--start', default='06:55'); ap.add_argument('--end', default='23:45')
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'sim_day.json'))
    ap.add_argument('--serve', action='store_true', help='serve the viewer after simulating')
    ap.add_argument('--live', type=float, default=0, help='stream: simulate at X sim-seconds per wall second while serving')
    ap.add_argument('--port', type=int, default=8765)
    a = ap.parse_args()
    if a.cmd == 'export':
        import export_world; export_world.main(); return
    if not os.path.exists(os.path.join(HERE, 'world', 'world.json')):
        print('[harness] exporting world assets first ...'); import export_world; export_world.main()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    def flush(sim):
        tmp = a.out + '.tmp'; json.dump(sim.snapshot(), open(tmp, 'w'), separators=(',', ':')); os.replace(tmp, a.out)
    if a.cmd == 'serve':
        from serve import serve; serve(a.port); return
    brain = make_brain(a.brain, a.seed)
    sim = Sim(brain, start=a.start, end=a.end)
    print(f'[harness] brain={brain.name} seed={a.seed} day {a.start}-{a.end}')
    if a.live:
        from serve import serve
        th = threading.Thread(target=lambda: (sim.run(realtime=a.live, on_flush=flush, flush_every=5), print('[harness] live day finished')), daemon=True)
        th.start(); serve(a.port, live=True); return
    t0 = time.time(); sim.run(); flush(sim)
    open(a.out.replace('.json', '.log'), 'w').write(sim.text_log())
    n_say = sum(1 for e in sim.events if e['type'] == 'say')
    print(f'[harness] simulated in {time.time() - t0:.1f}s: {len(sim.events)} events, {len(sim.convos)} conversations, {n_say} lines'
          + (f", {brain.calls} LLM calls ({brain.failures} failed -> mock fallback{', ' + brain.last_error if brain.failures else ''})" if hasattr(brain, 'calls') else '') + f' -> {a.out}')
    if a.serve:
        from serve import serve; serve(a.port)

if __name__ == '__main__': main()
