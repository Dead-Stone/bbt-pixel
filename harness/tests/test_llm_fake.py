"""Exercise the OpenAI-compatible LLM path against a local fake server (no network, no real key).
   python3 harness/tests/test_llm_fake.py"""
import http.server, json, os, re, sys, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SEEN = []
class Fake(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        SEEN.append(dict(path=self.path, auth=self.headers.get('Authorization', ''), model=body['model']))
        sys_p, user = body['messages'][0]['content'], body['messages'][1]['content']
        who = re.match(r'You are (\w+)', sys_p).group(1)
        assert 'ORIGINAL dialogue' in sys_p
        if 'JSON list' in user:
            n = len(user.split(':\n', 1)[1].split('\n')[0].split('; '))
            content = json.dumps([f'{who} intends to make block {i + 1} count' for i in range(n)])
        elif 'insight' in user: content = f'{who} (fake-llm reflection): people matter more than schedules today.'
        else: content = f'{who}: [fake-llm] line {len(SEEN)} from {who}.'
        out = json.dumps(dict(choices=[dict(message=dict(role='assistant', content=content))])).encode()
        self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(out)))
        self.end_headers(); self.wfile.write(out)

def main():
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ.update(LLM_API_KEY='dummy-local-test', LLM_BASE_URL=f'http://127.0.0.1:{srv.server_address[1]}/v1',
                      LLM_MODEL='fake-model', LLM_MAX_CALLS='120')
    from brains import make_brain
    from sim import Sim
    brain = make_brain('auto', 7); assert brain.name == 'llm', brain.name
    sim = Sim(brain, start='11:45', end='12:30'); sim.run()
    says = [e for e in sim.events if e['type'] == 'say']
    llm_lines = [e for e in says if '[fake-llm]' in e['text']]
    intents = [b.get('intent') for a in sim.agents.values() for b in a.plan if b.get('intent')]
    refl = [e for e in sim.events if e['type'] == 'reflect' and 'fake-llm' in e['text']]
    print(f'calls={brain.calls} failures={brain.failures} lines={len(says)} llm_lines={len(llm_lines)} intents={len(intents)} reflections={len(refl)}')
    print('sample:', llm_lines[0]['text'] if llm_lines else None, '|', intents[0] if intents else None)
    assert SEEN and SEEN[0]['path'] == '/v1/chat/completions' and SEEN[0]['auth'] == 'Bearer dummy-local-test' and SEEN[0]['model'] == 'fake-model'
    assert llm_lines and intents and brain.failures == 0
    assert not any(e['text'].startswith(sim.agents[e['agent']].name + ':') for e in says), 'name prefix not stripped'
    # budget exhausted -> remaining lines come from the mock brain, the day still completes
    assert brain.calls <= 120
    srv.shutdown(); print('OK')

if __name__ == '__main__': main()
