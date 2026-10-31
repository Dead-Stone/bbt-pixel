// Headless recorder: screenshots + GIF clips of the viewer replaying harness/out/sim_day.json.
//   node harness/record.js [baseURL]        (needs the `playwright` npm package + chromium; set PLAYWRIGHT_DIR if it lives elsewhere)
// Start the server first: python3 -m harness serve   (prints the base URL)
const path = require('path'), fs = require('fs'), {execFileSync} = require('child_process');
const {chromium} = require(process.env.PLAYWRIGHT_DIR ? path.join(process.env.PLAYWRIGHT_DIR, 'node_modules/playwright') : 'playwright');
const BASE = (process.argv[2] || 'http://127.0.0.1:8765') + '/harness/viewer/index.html';
const OUT = path.join(__dirname, 'renders'); fs.mkdirSync(OUT, {recursive: true});

const SHOTS = [
  ['shot_4A_couch_eviction.png', 'loc=floor4&view=4A&t=17:49:24'],
  ['shot_ait_physics_work.png', 'loc=ait_physics&t=09:38:28'],
  ['shot_amber_slice_shift.png', 'loc=rest_amber_slice&t=15:09:10'],
  ['shot_floor4_game_night.png', 'loc=floor4&view=4A&t=20:38:43'],
  ['shot_floor4_overview.png', 'loc=floor4&view=all&t=20:38:43'],
  ['shot_ait_cafeteria_lunch.png', 'loc=ait_cafeteria&t=12:02:21'],
  ['shot_amber_slice_dinner.png', 'loc=rest_amber_slice&t=18:58:34'],
  ['shot_ait_physics_morning.png', 'loc=ait_physics&t=08:23:31'],
  ['shot_raj_sofa.png', 'loc=raj_apartment&t=07:23:00'],
];
const CLIPS = [  // name, query, sim start, sim end, fps[, viewport w, h] (GIFs stay under 4 MB)
  ['clip_4A_evening.gif', 'loc=floor4&view=all&follow=sheldon&zoom=2.5&speed=4&talk=2', '17:44:40', '17:47:40', 6, 760, 460],
  ['clip_4A_game_night_ai.gif', 'loc=floor4&view=all&follow=penny&zoom=2.2&speed=4&talk=2', '21:53:00', '21:55:00', 6, 760, 460],
  ['clip_4B_nightcap_ai.gif', 'loc=floor4&view=all&follow=penny&zoom=2.2&speed=4&talk=2', '22:19:30', '22:23:30', 8, 800, 480],
  ['clip_ait_physics_work.gif', 'loc=ait_physics&follow=howard&zoom=2.2&speed=3&talk=1.5', '09:37:50', '09:39:10', 10],
  ['clip_amber_slice_shift.gif', 'loc=rest_amber_slice&follow=penny&zoom=3&speed=3&auto=0', '15:08:50', '15:09:40', 10],
  ['clip_ait_cafeteria_lunch.gif', 'loc=ait_cafeteria&speed=8&talk=3', '12:00:02', '12:02:46', 8],
  ['clip_penny_walk_ai.gif', 'loc=floor4&view=all&follow=penny&zoom=3&speed=1&auto=0', '12:08:00', '12:08:14', 5, 380, 300],
  ['clip_sheldon_walk_ai.gif', 'loc=floor4&view=all&follow=sheldon&zoom=3&speed=1&auto=0', '17:44:44', '17:44:58', 5, 400, 320],
];
const sec = s => { const [h, m, x] = s.split(':').map(Number); return h * 3600 + m * 60 + (x || 0); };

async function open(browser, q, w, h) {
  const p = await browser.newPage({viewport: {width: w, height: h}});
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto(`${BASE}?${q}`); await p.waitForFunction(() => document.title.includes('ready'), null, {timeout: 60000});
  p.errs = errs; return p;
}
(async () => {
  const browser = await chromium.launch();
  for (const [name, q] of SHOTS) {
    if (process.env.ONLY && !new RegExp(process.env.ONLY).test(name)) continue;
    const p = await open(browser, q + '&play=0&manual=1', 1440, 810);
    await p.evaluate(() => viewer.render(1.0)); await p.screenshot({path: path.join(OUT, name)});
    console.log('shot', name, p.errs.length ? p.errs : ''); await p.close();
  }
  const only = process.env.ONLY ? new RegExp(process.env.ONLY) : null;
  for (const [name, q, t0, t1, fps, w = 960, h = 560] of CLIPS) {
    if (only && !only.test(name)) continue;
    const dir = fs.mkdtempSync('/tmp/bbt_clip_'); const p = await open(browser, `${q}&t=${t0}&bare=1&manual=1`, w, h);
    let t = sec(t0), i = 0;
    while (t < sec(t1) && i < 400) {
      t = await p.evaluate(([dt, w]) => viewer.step(dt, w), [1 / fps, i / fps]);
      await p.screenshot({path: path.join(dir, `f${String(i).padStart(4, '0')}.png`)}); i++;
    }
    await p.close();
    execFileSync('python3', [path.join(__dirname, 'make_gif.py'), dir, path.join(OUT, name), String(fps)], {stdio: 'inherit'});
    fs.rmSync(dir, {recursive: true});
  }
  await browser.close();
})();
