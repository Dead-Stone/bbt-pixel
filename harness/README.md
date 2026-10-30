# BBT-pixel agentic harness

A Generative-Agents-style simulation of one day at 2311 LOS ROBLES AV, AIT and The Amber Slice, played back
on the v2 isometric pixel-art sets. Seven agents (sheldon, leonard, penny, howard, raj, bernadette, amy) have
personas, memory, a daily plan, perception, conversations and engine-hook actions. All dialogue is original.

## Quick start (one command)

```bash
cd bbt-pixel
python3 -m harness run --serve        # simulate a full day with the mock brain, then serve the viewer
# open the printed URL, e.g. http://127.0.0.1:8765/harness/viewer/index.html
```

Python 3.9+ and the standard library are enough to simulate and serve. Pillow is only needed for the GIF tool.
If the port is busy, the server tries the next 19 ports and prints the one it used.

Other commands:

| command | what it does |
|---|---|
| `python3 -m harness run [--brain auto\|mock\|llm] [--seed 7] [--start 06:55] [--end 23:45]` | simulate, write `harness/out/sim_day.json` and `sim_day.log` |
| `python3 -m harness serve [--port 8765]` | serve the repo root and print the viewer URL (replays `out/sim_day.json`) |
| `python3 -m harness run --live 30` | stream: simulate at 30 sim-seconds per wall second while serving, the viewer polls (`?live=1`) |
| `python3 -m harness export` | re-export `harness/world/` (scene, walk grid, hooks, exits, sliced sprites) from `env/` |
| `python3 harness/tests/test_sim.py [seed]` | invariants: continuous tracks, walkable paths, sorted events, conversations, locations visited |
| `python3 harness/tests/test_llm_fake.py` | runs a day against a local fake OpenAI-compatible server (no network, dummy key) |
| `PLAYWRIGHT_DIR=/path/to/node_modules/.. node harness/record.js http://127.0.0.1:PORT` | headless screenshots + GIFs into `harness/renders/` (needs npm `playwright` + chromium, and Pillow) |

## Layout

```
harness/
  world.py        scenes from harness/world/*: walk grid, A* pathfinding, hooks (sit/use/stand/work/queue/knock), doors, exits, world-graph routes
  world/          exported per-location scene.json + bg.png + sprites.png (sliced depth-sorted items), world_graph.json
  personas.py     7 personas: traits, home, speed, whether they drive, daily routine templates
  memory.py       memory stream: observations, reflections, plan; recency x importance x relevance retrieval
  lines.py        original mock dialogue banks (openers, replies, topics, emotes)
  brains.py       MockBrain (deterministic, seeded) and LLMBrain (OpenAI-compatible, falls back to mock)
  sim.py          world clock (1 s ticks), plan blocks -> intents -> hook actions, travel, rides, chats, event log
  serve.py        static server + live mode
  viewer/         index.html, viewer.js, viewer.css (canvas playback)
  record.js       playwright recorder, make_gif.py palette GIF writer
  out/            sim_day.json (events + per-agent tracks), sim_day.log (readable log)
  renders/        screenshots, GIFs, event_log_excerpt.txt
```

### Simulation model

* Clock: one tick = 1 sim second, default day 06:55-23:45.
* Plan: each morning the brain writes a day plan of blocks (time, location, activity, hook selector). The LLM
  brain adds a one-line intent per block. A forced block (accepted ride, invitation) can override the clock.
* Actions map to engine hooks: `walk` (A* over the walk grid, 8-way), `sit`/`use`/`stand`/`work`/`queue`/`knock`
  on hook spots with their facing direction, `door` events whenever a path crosses a door tile, `exit` hops
  (stairs, doors) to another scene, and `car` hops that turn into an off-screen trip (scene transition).
  Leonard (the driver) offers rides to people in the same place heading to the same destination. The
  riders and the driver wait at the car and leave together.
* Perception: every 20 s each agent observes agents within 8 tiles in its zone, plus the hook it is using.
* Memory: observations (importance 1-10), reflections when importance accumulates (for example "I've talked
  with Sheldon 6 times today"), and retrieval by recency, importance and keyword relevance. Retrieved memories
  can be quoted in conversation, but only by the agent who owns them.
* Conversations: co-located idle or seated agents within 6 tiles in the same zone may start a turn-taking
  chat (4-7 lines, up to 3 people). Topics come from the place, the plan and memories. Each line is a `say` event the viewer
  shows as a bubble.
* Social rules: Sheldon's spot (`4a_couch#0.seat0`) is reclaimed if someone is in it. Sheldon's knock-knock-Penny emote
  plays only on floor 4, and so on.

## LLM modes

| `--brain` | behaviour |
|---|---|
| `auto` (default) | LLM if `LLM_API_KEY` is set, otherwise the mock |
| `mock` | deterministic, seeded, offline |
| `llm` | requires a key; without one it prints a notice and uses the mock |

Environment (nothing is stored or logged; nothing is hard-coded):

```bash
export LLM_API_KEY=...                         # any OpenAI-compatible provider; for a local server any dummy value
export LLM_BASE_URL=http://localhost:11434/v1  # default https://api.openai.com/v1
export LLM_MODEL=llama3.1                      # default gpt-4o-mini
export LLM_MAX_CALLS=400                       # budget; after it is spent the rest of the day uses the mock
python3 -m harness run --brain llm --serve
```

The LLM writes plan intents, dialogue lines (one per turn, in persona, given place, recent memories and
the conversation so far) and reflections. Any HTTP or parse error falls back to the mock for that call. The
run summary prints `N LLM calls (F failed -> mock fallback)`.

## Viewer

Open `harness/viewer/index.html` through the server (it fetches JSON, so `file://` does not work).

* Top bar: location switcher, floor-4 view (all / 4A / hall / 4B), follow an agent (the camera switches
  location and view with them), speed, play/pause, auto pace (skips quiet stretches and slows down for
  speech), clock and time slider.
* Side panel: where everyone is and what they are doing, plus an event feed (current location or all).
* Drawing: the v2 iso background, sliced item sprites and characters depth-sorted together. Uses the v2
  character atlases: 8-direction walk (8 frames), idle (4 frames), emotes, and sit poses with per-frame
  pivots. Includes name tags, speech bubbles, and a clock and location stamp.
* Keys: space play/pause, left/right -/+1 min, `+`/`-` zoom. Mouse wheel zooms, drag pans, and clicking an
  agent in the side panel follows them.
* URL params: `loc=floor4|ait_cafeteria|ait_physics|rest_amber_slice|street_exterior|lobby|raj_apartment`,
  `view=all|4A|hall|4B`, `t=HH:MM[:SS]`, `speed=N`, `follow=<cid>`, `play=0`, `auto=0`, `zoom=1.5`,
  `bare=1` (canvas only), `log=<path to json>`, `live=1`, `talk=1.5` (playback speed cap while speaking).

## Renders (end-to-end check)

`harness/renders/` contains the following, made from the mock day (seed 7) with `record.js`:

* Screenshots:
  * `shot_4A_couch_eviction.png`
  * `shot_floor4_game_night.png`
  * `shot_floor4_overview.png`
  * `shot_ait_cafeteria_lunch.png`
  * `shot_amber_slice_dinner.png`
  * `shot_ait_physics_morning.png`
* `clip_4A_evening.gif`: Leonard and Sheldon come home, chat, Leonard takes the spot, Sheldon reclaims it,
  and Leonard goes to knock on 4B.
* `clip_ait_cafeteria_lunch.gif`: the lunch queue and a table conversation.
* `event_log_excerpt.txt`

## Known limitations

* The mock dialogue banks are small. Over a full day some lines repeat (the least-used line is preferred),
  and the LLM brain gives much more variety.
* Doors do not animate open. Crossing a door is logged as a `door` event only.
* Car trips are off-screen transitions with a fixed travel time. There is no driving animation.
* Only one floor-4 scene combines 4A, the hall and 4B. The `view` selector frames each part, but at small
  sizes the 4A frame still shows some of the hall.
* Conversations are turn-based with fixed timing (about 4-5 s per line). There is no interruption.
* Perception is zone- and radius-based, with no line-of-sight.
* `street_exterior`, `lobby` and `raj_apartment` are pass-through or short visits in the default routines.

## Seating

Sit hooks are resolved against the rendered item geometry (`tools/seating.py`): each hook gets a
`seat` point, `seat_z` (cushion height probed from the item's height map), `sit_dir` (the seat's
facing) and a depth `sit_key`. Sit sprites carry a `seat` anchor (butt contact pixel), so the viewer
and the static renders draw the sitter at `scr(seat) - seat_z*64`, and seat backs / armrests that
are in front of the sitter are emitted as hook-tagged occluder sprites. Contact sheet of every sit
hook: `harness/renders/sitcheck/sit_contact_4x.png` (`python3 tools/sitcheck/sitsheet.py`).
