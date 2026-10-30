'use strict';
/* BBT-pixel agent harness viewer: renders the exported iso scenes + v2 character atlases and replays (or streams)
   the simulation log written by `python3 -m harness run`.
   URL params: loc, view (floor4: 4A|hall|4B|all), t (HH:MM[:SS] or seconds), speed, follow, play=0, auto=0, bare=1,
               zoom, log (path of the sim JSON), live=1 (poll the log while the simulation is running) */
const Q = new URLSearchParams(location.search);
const ROOT = '../';                    // harness/
const CHARS = '../../characters/';
const DIRV = {S: [1, 1], N: [-1, -1], E: [1, -1], W: [-1, 1], SW: [0, 1], SE: [1, 0], NE: [0, -1], NW: [-1, 0]};
const COLORS = {sheldon: '#7ec8ff', leonard: '#ffb36b', penny: '#ff8fc8', howard: '#c6f07a', raj: '#ffd95e', bernadette: '#c9a3ff', amy: '#7ff0d0'};
const LOCNAMES = {floor4: '4th floor (4A · hall · 4B)', lobby: 'Lobby', street_exterior: 'LOS ROBLES AV (street)', raj_apartment: "Raj's apartment",
                  ait_cafeteria: 'AIT cafeteria', ait_physics: 'AIT physics', rest_amber_slice: 'The Amber Slice'};

function dirOf(dx, dy, def) {
  if (Math.abs(dx) < 1e-6 && Math.abs(dy) < 1e-6) return def || 'SW';
  let best = def || 'SW', bd = -9; const n = Math.hypot(dx, dy);
  for (const [k, [vx, vy]] of Object.entries(DIRV)) { const d = (dx * vx + dy * vy) / (n * Math.hypot(vx, vy)); if (d > bd) { bd = d; best = k; } }
  return best;
}
const hms = t => { t = Math.max(0, Math.floor(t)); const p = n => String(n).padStart(2, '0'); return `${p(Math.floor(t / 3600) % 24)}:${p(Math.floor(t / 60) % 60)}:${p(t % 60)}`; };
const parseT = s => { if (s == null) return null; if (/^\d+(\.\d+)?$/.test(s)) return +s; const a = s.split(':').map(Number); return a[0] * 3600 + (a[1] || 0) * 60 + (a[2] || 0); };
const img = src => new Promise((ok, bad) => { const i = new Image(); i.onload = () => ok(i); i.onerror = () => bad(new Error('image ' + src)); i.src = src; });
const json = async src => { const r = await fetch(src, {cache: 'no-store'}); if (!r.ok) throw new Error(src + ' ' + r.status); return r.json(); };
function bsearch(arr, t, key) { let lo = 0, hi = arr.length - 1, ans = -1; while (lo <= hi) { const m = (lo + hi) >> 1; if (arr[m][key] <= t) { ans = m; lo = m + 1; } else hi = m - 1; } return ans; }

const V = {
  scenes: {}, chars: {}, sim: null, t: 0, playing: Q.get('play') !== '0', speed: +(Q.get('speed') || 1), auto: Q.get('auto') !== '0',
  loc: Q.get('loc') || 'floor4', view: Q.get('view') || '4A', follow: Q.get('follow') || '', zoom: +(Q.get('zoom') || 1), live: Q.get('live') === '1',
  pan: [0, 0], ff: false, idx: {},
};
const cv = document.getElementById('cv'), ctx = cv.getContext('2d');

async function loadChars(cid) {
  const [atlas, sheet, sitj, sit] = await Promise.all([json(`${CHARS}${cid}/chr_${cid}.json`), img(`${CHARS}${cid}/chr_${cid}.png`),
    json(`${CHARS}${cid}/chr_${cid}_sit.json`).catch(() => null), img(`${CHARS}${cid}/chr_${cid}_sit.png`).catch(() => null)]);
  const tags = {}; for (const tg of atlas.meta.frameTags) tags[tg.name] = [tg.from, tg.to];
  const sitf = {}; if (sitj) for (const f of sitj.frames) sitf[f.dir] = f;
  V.chars[cid] = {frames: atlas.frames, tags, sheet, sit, sitf};
}
async function loadScene(id) {
  const [sc, bg, spr] = await Promise.all([json(`${ROOT}world/${id}/scene.json`), img(`${ROOT}world/${id}/bg.png`), img(`${ROOT}world/${id}/sprites.png`)]);
  sc.bgImg = bg; sc.sprImg = spr; V.scenes[id] = sc;
}
function indexSim(sim) {
  const ix = {byAgent: {}, emotes: {}, says: [], feed: []};
  for (const c of sim.meta.agents) { ix.byAgent[c] = []; ix.emotes[c] = []; }
  for (const e of sim.events) {
    if (e.agent && ['hook_start', 'walk', 'depart', 'offstage', 'appear', 'block'].includes(e.type)) ix.byAgent[e.agent].push(e);
    if (e.type === 'emote') ix.emotes[e.agent].push(e);
    if (e.type === 'say') ix.says.push(e);
    if (['say', 'hook_start', 'appear', 'depart', 'offstage', 'convo_start', 'reflect', 'evict', 'ride', 'door', 'block'].includes(e.type)) ix.feed.push(e);
  }
  return ix;
}
async function loadSim() {
  const sim = await json(Q.get('log') || `${ROOT}out/sim_day.json`);
  V.sim = sim; V.idx = indexSim(sim);
  V.tMax = V.live ? sim.meta.t_now : sim.meta.t_end;
  const sl = document.getElementById('slider'); sl.min = sim.meta.t_start; sl.max = V.tMax;
}

// ------------------------------------------------------------------ agent state at time t
function agentAt(cid, t) {
  const tr = V.sim.tracks[cid]; const i = bsearch(tr, t, 't0'); if (i < 0) return null;
  const s = tr[i];
  if (s.kind === 'away') return {cid, away: true, why: s.why};
  if (s.kind === 'walk') {
    let d = Math.max(0, (t - s.t0) * s.speed), p = s.pts, x = p[p.length - 1][0], y = p[p.length - 1][1], dir = 'SW', walked = d;
    for (let k = 0; k < p.length - 1; k++) {
      const L = Math.hypot(p[k + 1][0] - p[k][0], p[k + 1][1] - p[k][1]); dir = dirOf(p[k + 1][0] - p[k][0], p[k + 1][1] - p[k][1], dir);
      if (d <= L) { const f = L ? d / L : 1; x = p[k][0] + (p[k + 1][0] - p[k][0]) * f; y = p[k][1] + (p[k + 1][1] - p[k][1]) * f; break; }
      d -= L;
    }
    return {cid, loc: s.loc, x, y, dir, anim: 'walk', k: Math.floor(walked / 0.14) % 8, moving: true};
  }
  const st = {cid, loc: s.loc, x: s.pos[0], y: s.pos[1], dir: s.dir, anim: s.kind === 'sit' ? 'sit' : 'idle', key: s.key, z: s.z || 0, hook: s.hook};
  if (s.kind !== 'sit') {   // emote overlay
    const em = V.idx.emotes[cid]; const j = bsearch(em, t, 't');
    if (j >= 0) {
      const e = em[j], ch = V.chars[cid], tag = emoteTag(ch, e.anim, st.dir);
      if (tag) { const n = tag[1] - tag[0] + 1, dur = Math.max(2.5, n * 0.125); if (t < e.t + dur) { st.anim = 'emote'; st.frame = tag[0] + Math.min(n - 1, Math.floor((t - e.t) / dur * n)); st.emoting = true; st.dir = tag.dir; } }
    }
  }
  return st;
}
function emoteTag(ch, anim, dir) {
  const order = [dir, 'SW', 'SE', 'S', 'NW', 'NE', 'W', 'E', 'N'];
  for (const d of order) { const tg = ch.tags[`${anim}_${d}`]; if (tg) return Object.assign([...tg], {dir: d}); }
  return null;
}
function frameOf(st, wall) {
  const ch = V.chars[st.cid];
  if (st.anim === 'sit' && ch.sit && ch.sitf[st.dir]) { const f = ch.sitf[st.dir]; return {img: ch.sit, fr: f.frame, pv: f.seat || f.pivot}; }   // seat anchor (butt) -> seat point at seat_z
  let idx;
  if (st.anim === 'emote') idx = st.frame;
  else {
    const tg = ch.tags[`${st.anim === 'sit' ? 'idle' : st.anim}_${st.dir}`] || ch.tags[`idle_${st.dir}`];
    const n = tg[1] - tg[0] + 1; idx = tg[0] + (st.anim === 'walk' ? st.k % n : Math.floor(wall * 4 + st.cid.length) % n);
  }
  return {img: ch.sheet, fr: ch.frames[idx].frame, pv: [64, 116]};
}

// ------------------------------------------------------------------ camera
function viewRect(sc) {
  const W = sc.size[0], H = sc.size[1], o = sc.origin;
  let x0 = 0, x1 = W, y0 = 0, y1 = H;
  if (sc.views && V.view !== 'all' && sc.views[V.view]) [x0, x1] = sc.views[V.view];
  const pts = [[x0, y0], [x1, y0], [x0, y1], [x1, y1]].map(([x, y]) => [(x - y) * 64 - o[0], (x + y) * 32 - o[1]]);
  let l = Math.min(...pts.map(p => p[0])) - 24, r = Math.max(...pts.map(p => p[0])) + 24;
  let t = Math.min(...pts.map(p => p[1])) - 230, b = Math.max(...pts.map(p => p[1])) + 30;
  l = Math.max(0, l); t = Math.max(0, t); r = Math.min(sc.bg_size[0], r); b = Math.min(sc.bg_size[1], b);
  return [l, t, r - l, b - t];
}
const toCanvas = (sc, x, y, z = 0) => [(x - y) * 64 - sc.origin[0], (x + y) * 32 - z * 64 - sc.origin[1]];
function zoneView(sc, x) { if (!sc.views) return V.view; for (const [k, [a, b]] of Object.entries(sc.views)) if (x >= a && x < b) return k; return V.view; }

// ------------------------------------------------------------------ rendering
function wrap(text, maxw) {
  const words = text.split(' '), lines = []; let cur = '';
  for (const w of words) { const tst = cur ? cur + ' ' + w : w; if (ctx.measureText(tst).width > maxw && cur) { lines.push(cur); cur = w; } else cur = tst; }
  if (cur) lines.push(cur); return lines;
}
function render(wall) {
  const dpr = window.devicePixelRatio || 1, cw = cv.clientWidth, chh = cv.clientHeight;
  if (cv.width !== Math.round(cw * dpr) || cv.height !== Math.round(chh * dpr)) { cv.width = Math.round(cw * dpr); cv.height = Math.round(chh * dpr); }
  const t = V.t, states = {};
  for (const c of V.sim.meta.agents) states[c] = agentAt(c, t);
  // follow camera: switch location / view with the followed agent
  if (V.follow && states[V.follow] && !states[V.follow].away && states[V.follow].loc !== V.loc) setLoc(states[V.follow].loc, true);
  const sc = V.scenes[V.loc]; if (!sc) return;
  if (V.follow && states[V.follow] && !states[V.follow].away && sc.views && V.view !== 'all') {
    const zv = zoneView(sc, states[V.follow].x); if (zv !== V.view) { V.view = zv; document.getElementById('view').value = zv; }
  }
  let [vx, vy, vw, vh] = viewRect(sc);
  let scale = Math.min(cw / vw, chh / vh) * V.zoom; scale = scale >= 1 ? Math.floor(scale * 4) / 4 : scale;
  let cx = vx + vw / 2 + V.pan[0], cy = vy + vh / 2 + V.pan[1];
  if (V.follow && states[V.follow] && !states[V.follow].away && states[V.follow].loc === V.loc && V.zoom > 1) {
    const [fx, fy] = toCanvas(sc, states[V.follow].x, states[V.follow].y); cx = fx; cy = fy - 50;
  }
  const ox = cw / 2 - cx * scale, oy = chh / 2 - cy * scale;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.imageSmoothingEnabled = false;
  ctx.fillStyle = '#0d0b12'; ctx.fillRect(0, 0, cw, chh);
  ctx.setTransform(dpr * scale, 0, 0, dpr * scale, dpr * ox, dpr * oy); ctx.imageSmoothingEnabled = false;
  ctx.drawImage(sc.bgImg, 0, 0);
  // depth-sorted layer 5: item slices + characters (+ shadows)
  const here = Object.values(states).filter(s => s && !s.away && s.loc === V.loc);
  const seated = new Set(here.filter(s => s.anim === 'sit' && s.hook).map(s => s.hook));
  // hook-tagged sprites = the seat's own back/armrest pixels that sit in front of a sitter: drawn only while occupied
  const L = sc.sprites.filter(s => !s.hook || seated.has(s.hook)).map(s => ({k: s.key, s}));
  for (const st of here) {
    const k = st.key != null ? st.key : st.x + st.y + 0.01;
    if (st.anim !== 'sit') L.push({k: k - 0.001, shadow: st});
    L.push({k, ch: st});
  }
  L.sort((a, b) => a.k - b.k);
  for (const it of L) {
    if (it.s) { const s = it.s; ctx.drawImage(sc.sprImg, s.ax, s.ay, s.w, s.h, s.x, s.y, s.w, s.h); }
    else if (it.shadow) { const [sx, sy] = toCanvas(sc, it.shadow.x, it.shadow.y); ctx.fillStyle = 'rgba(40,24,60,0.43)'; ctx.beginPath(); ctx.ellipse(sx, sy, 20, 6, 0, 0, 7); ctx.fill(); }
    else { const st = it.ch, f = frameOf(st, wall), [sx, sy0] = toCanvas(sc, st.x, st.y), sy = sy0 - (st.z || 0) * 64; st.sx = sx; st.sy = sy; st.top = sy - f.pv[1] + 18;
      ctx.drawImage(f.img, f.fr.x, f.fr.y, f.fr.w, f.fr.h, Math.round(sx - f.pv[0]), Math.round(sy - f.pv[1]), f.fr.w, f.fr.h); }
  }
  // overlays in screen space: name tags + speech bubbles
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const scr = (x, y) => [ox + x * scale, oy + y * scale];
  ctx.font = '11px ui-monospace, Menlo, monospace'; ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
  for (const st of here) {
    const [x, y] = scr(st.sx, st.top); const nm = V.sim.meta.names[st.cid];
    ctx.fillStyle = 'rgba(10,8,16,0.65)'; const w = ctx.measureText(nm).width + 8; ctx.fillRect(x - w / 2, y - 14, w, 14);
    ctx.fillStyle = COLORS[st.cid] || '#fff'; ctx.fillText(nm, x, y - 3);
  }
  const says = activeSays(t).filter(e => e.loc === V.loc);
  const placed = [];
  ctx.font = '13px ui-monospace, Menlo, monospace';
  for (const e of says) {
    const st = states[e.agent]; if (!st || st.away || st.loc !== V.loc || st.sx == null) continue;
    const lines = wrap(e.text, 230), lh = 16, bw = Math.max(...lines.map(l => ctx.measureText(l).width)) + 16, bh = lines.length * lh + 10;
    let [x, y] = scr(st.sx, st.top); y -= 20; let bx = Math.min(Math.max(4, x - bw / 2), cw - bw - 4), by = y - bh;
    for (let tries = 0; tries < 8; tries++) { const hit = placed.find(r => bx < r[0] + r[2] && bx + bw > r[0] && by < r[1] + r[3] && by + bh > r[1]); if (!hit) break; by = hit[1] - bh - 4; }
    by = Math.max(4, by); placed.push([bx, by, bw, bh]);
    ctx.fillStyle = 'rgba(255,253,245,0.96)'; ctx.strokeStyle = COLORS[e.agent] || '#333'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.roundRect(bx, by, bw, bh, 6); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x - 6, by + bh - 1); ctx.lineTo(x + 6, by + bh - 1); ctx.lineTo(x, Math.min(y + 10, by + bh + 12)); ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#1b1726'; ctx.textAlign = 'left';
    lines.forEach((l, i) => ctx.fillText(l, bx + 8, by + 18 + i * lh)); ctx.textAlign = 'center';
  }
  // clock / location stamp (also shown in bare mode for recordings)
  ctx.textAlign = 'left'; ctx.font = 'bold 15px ui-monospace, Menlo, monospace';
  const stamp = `${hms(t)}  ${LOCNAMES[V.loc] || V.loc}${sc.views && V.view !== 'all' ? ' · ' + V.view : ''}${V.ff ? '  ⏩' : ''}`;
  const sw = ctx.measureText(stamp).width + 16; ctx.fillStyle = 'rgba(10,8,16,0.7)'; ctx.fillRect(8, chh - 30, sw, 24);
  ctx.fillStyle = '#9fe0ff'; ctx.fillText(stamp, 16, chh - 13);
  V.states = states; V.busy = here.some(s => s.moving || s.emoting) || says.length > 0;
}
function activeSays(t) {
  const S = V.idx.says; let i = bsearch(S, t, 't'); const out = [];
  for (; i >= 0 && S[i].t > t - 30; i--) if (t < S[i].t + S[i].dur) out.push(S[i]);
  return out;
}

// ------------------------------------------------------------------ UI
function setLoc(loc, fromFollow) {
  V.loc = loc; V.pan = [0, 0]; document.getElementById('loc').value = loc;
  const sc = V.scenes[loc]; const vw = document.getElementById('viewwrap');
  vw.style.display = sc && sc.views ? '' : 'none';
  if (!fromFollow && V.follow) { V.follow = ''; document.getElementById('follow').value = ''; }
}
function feedText(e) {
  const n = V.sim.meta.names, nm = n[e.agent] || '';
  switch (e.type) {
    case 'say': return [`${nm}: “${e.text}”`, 'say'];
    case 'hook_start': return [`${nm} ${e.activity}`, 'sys'];
    case 'appear': return [`${nm} arrives (${e.why})`, 'sys'];
    case 'depart': return [`${nm} leaves by ${e.via} → ${LOCNAMES[e.to] || e.to}`, 'sys'];
    case 'offstage': return [`${nm} ${e.why}`, 'sys'];
    case 'convo_start': return [`— ${e.who.map(c => n[c]).join(', ')} talk (${e.topic})`, 'sys'];
    case 'reflect': return [`${nm} reflects: ${e.text}`, 'refl'];
    case 'evict': return [`${nm} reclaims his spot from ${n[e.who]}`, 'sys'];
    case 'ride': return [`${nm} offers ${n[e.who]} a ride`, 'sys'];
    case 'door': return [`${nm} goes through the ${e.label || e.item.replace(/_/g, ' ')}`, 'sys'];
    case 'block': return [`${nm} plan → ${e.act}`, 'sys'];
  }
  return null;
}
let lastPanel = 0;
function updatePanels(force) {
  const now = performance.now(); if (!force && now - lastPanel < 250) return; lastPanel = now;
  const t = V.t, all = document.getElementById('allfeed').checked;
  document.getElementById('clock').textContent = hms(t);
  document.getElementById('slider').value = Math.floor(t);
  document.getElementById('mode').textContent = (V.live ? 'LIVE ' : '') + `brain: ${V.sim.meta.brain}`;
  const F = V.idx.feed; let i = bsearch(F, t, 't'); const rows = [];
  for (; i >= 0 && rows.length < 60; i--) { const e = F[i]; if (!all && e.loc !== V.loc) continue; const ft = feedText(e); if (ft) rows.push(`<div class="ev"><span class="t">${hms(e.t).slice(0, 5)}</span><span class="${ft[1]}">${esc(ft[0])}</span></div>`); }
  document.getElementById('feed').innerHTML = rows.join('');
  const ag = [];
  for (const c of V.sim.meta.agents) {
    const st = V.states && V.states[c]; const E = V.idx.byAgent[c]; const j = bsearch(E, t, 't'); let what = '';
    for (let k = j; k >= 0; k--) { const e = E[k]; if (e.type === 'hook_start') { what = e.activity; break; } if (e.type === 'walk') { what = e.to; break; } if (e.type === 'depart') { what = `travelling (${e.via})`; break; } if (e.type === 'offstage') { what = e.why; break; } if (e.type === 'appear') { what = 'arrives'; break; } if (e.type === 'block') { what = e.act; break; } }
    const where = !st || st.away ? (st && st.why && st.why.includes(' to ') ? 'in transit' : 'off-screen') : (LOCNAMES[st.loc] || st.loc) + (st.loc === 'floor4' ? ' · ' + zoneView(V.scenes.floor4, st.x) : '');
    ag.push(`<div class="ag${V.follow === c ? ' on' : ''}" data-c="${c}"><b style="color:${COLORS[c]}">${V.sim.meta.names[c]}</b><span class="where">${esc(where)}</span><span class="what">${esc(what)}</span></div>`);
  }
  document.getElementById('agents').innerHTML = ag.join('');
}
const esc = s => String(s).replace(/[&<>]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;'})[c]);

function nextBusy(t) {   // next time something visible starts in the current location
  let best = Infinity;
  for (const c of V.sim.meta.agents) {
    const tr = V.sim.tracks[c]; const i = bsearch(tr, t, 't0');
    for (let k = i + 1; k < tr.length && k < i + 4; k++) if (tr[k].loc === V.loc || (tr[i] && tr[i].loc === V.loc)) { best = Math.min(best, tr[k].t0); break; }
  }
  const S = V.idx.says; const j = bsearch(S, t, 't'); for (let k = j + 1; k < S.length; k++) if (S[k].loc === V.loc) { best = Math.min(best, S[k].t); break; }
  return best;
}
let lastWall = performance.now();
const TALK = +(Q.get('talk') || 1.5);   // max playback speed while someone in view is talking (auto pace)
function advance(dt) {
  if (!V.playing) return;
  let sp = V.speed; V.ff = false;
  if (V.auto && !V.busy) { const nb = nextBusy(V.t); if (nb - V.t > 3) { sp = Math.max(sp, 240); V.ff = true; if (nb - V.t < sp * dt) { V.t = nb - 0.5; sp = 0; } } }
  if (V.auto && V.busy && activeSays(V.t).some(e => e.loc === V.loc)) sp = Math.min(sp, TALK);
  V.t = Math.min(V.tMax, V.t + sp * dt);
}
function tick(now) {
  const dt = Math.min(0.25, (now - lastWall) / 1000); lastWall = now;
  advance(dt); render(now / 1000); updatePanels(); requestAnimationFrame(tick);
}

async function main() {
  if (Q.get('bare') === '1') document.body.classList.add('bare');
  await loadSim();
  const locs = V.sim.meta.locations;
  await Promise.all([...locs.map(loadScene), ...V.sim.meta.agents.map(loadChars)]);
  const ls = document.getElementById('loc'); for (const l of locs) ls.add(new Option(LOCNAMES[l] || l, l));
  const vs = document.getElementById('view'); for (const v of ['4A', 'hall', '4B', 'all']) vs.add(new Option(v, v)); vs.value = V.view;
  const fs = document.getElementById('follow'); for (const c of V.sim.meta.agents) fs.add(new Option(V.sim.meta.names[c], c)); fs.value = V.follow;
  const sp = document.getElementById('speed'); if (![...sp.options].some(o => +o.value === V.speed)) sp.add(new Option(V.speed + '×', V.speed)); sp.value = String(V.speed);
  document.getElementById('auto').checked = V.auto;
  V.t = parseT(Q.get('t')) ?? (V.sim.meta.t_start + 60);
  setLoc(V.loc, true);
  ls.onchange = () => setLoc(ls.value); vs.onchange = () => { V.view = vs.value; V.pan = [0, 0]; };
  fs.onchange = () => { V.follow = fs.value; }; sp.onchange = () => { V.speed = +sp.value; };
  document.getElementById('auto').onchange = e => { V.auto = e.target.checked; };
  const pb = document.getElementById('play'); const syncPlay = () => { pb.textContent = V.playing ? '⏸' : '▶'; }; syncPlay();
  pb.onclick = () => { V.playing = !V.playing; syncPlay(); };
  document.getElementById('slider').oninput = e => { V.t = +e.target.value; updatePanels(true); };
  document.getElementById('agents').onclick = e => { const d = e.target.closest('.ag'); if (d) { V.follow = d.dataset.c; fs.value = V.follow; } };
  document.getElementById('allfeed').onchange = () => updatePanels(true);
  addEventListener('keydown', e => { if (e.target.tagName === 'SELECT') return;
    if (e.key === ' ') { V.playing = !V.playing; syncPlay(); e.preventDefault(); }
    if (e.key === 'ArrowRight') V.t += 60; if (e.key === 'ArrowLeft') V.t -= 60;
    if (e.key === '+' || e.key === '=') V.zoom *= 1.25; if (e.key === '-') V.zoom /= 1.25; });
  cv.addEventListener('wheel', e => { V.zoom = Math.min(6, Math.max(0.5, V.zoom * (e.deltaY < 0 ? 1.1 : 1 / 1.1))); e.preventDefault(); }, {passive: false});
  let drag = null; cv.onmousedown = e => { drag = [e.clientX, e.clientY, ...V.pan]; }; addEventListener('mouseup', () => { drag = null; });
  addEventListener('mousemove', e => { if (drag) { const s = 1 / Math.max(0.3, V.zoom); V.pan = [drag[2] - (e.clientX - drag[0]) * s, drag[3] - (e.clientY - drag[1]) * s]; } });
  if (V.live) setInterval(async () => { try { const atEdge = V.tMax - V.t < 5; await loadSim(); if (atEdge) V.t = Math.max(V.t, V.tMax - 2); } catch (e) {} }, 2000);
  render(performance.now() / 1000); updatePanels(true);
  window.viewer = {V, render, setTime: t => { V.t = parseT(String(t)); render(performance.now() / 1000); updatePanels(true); }, setLoc,
                   frame: (t, wall) => { V.t = t; render(wall ?? t); updatePanels(true); },
                   step: (dt, wall) => { advance(dt); render(wall); updatePanels(true); return V.t; }, manual: () => { V.manual = true; }};
  document.title = 'BBT-pixel agents · ready';
  if (Q.get('manual') !== '1') requestAnimationFrame(tick);
}
main().catch(e => { document.body.insertAdjacentHTML('beforeend', `<pre style="color:#f88;padding:20px">${esc(e.stack || e)}</pre>`); console.error(e); });
