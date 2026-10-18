// linumeRT Plant: panel testowy (sesja 022). SPDX-License-Identifier: GPL-2.0-or-later.
// Model-Author: Claude. Telemetria z /ws (≤ 20 Hz), akcje przez REST /api/...
"use strict";

const $ = (id) => document.getElementById(id);
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const S = { state: null, drive: null, buf: {}, windowS: 10, charts: null, dial: 0 };

async function api(path, body) {
  const opt = body === undefined ? { method: "GET" } :
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const res = await fetch(path, opt);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail?.errors ? data.detail.errors.join("; ") : (data.detail || `HTTP ${res.status}`));
  return data;
}

function fmt(v, digits = 3) {
  if (!isFinite(v)) return "—";
  const a = Math.abs(v);
  if (a !== 0 && (a < 1e-3 || a >= 1e5)) return v.toExponential(2);
  return v.toFixed(a >= 100 ? 1 : digits).replace(/\.?0+$/, (m) => (m.startsWith(".") ? "" : m));
}

// ---- stan i parametry live -----------------------------------------------------------
async function loadState() {
  S.state = await api("/api/state");
  const st = S.state;
  S.windowS = st.window_s;
  $("window").textContent = st.window_s;
  $("machine").textContent = `${st.machine} · tryb ${st.mode === "lockstep" ? "ramkowy" : "czasu rzeczywistego"}` +
    ` · ${Math.round(1e9 / st.cycle_ns)} ramek/s`;
  if (!S.drive || !st.drives.some((d) => d.name === S.drive)) S.drive = st.drives[0]?.name;
  renderDrives();
  renderPresets();
  renderDesk(st.desk);
  renderRecord(st.record);
  refreshFiles();
}

function current() { return S.state.drives.find((d) => d.name === S.drive); }

function renderDrives() {
  const box = $("live-drives");
  box.innerHTML = "";
  for (const d of S.state.drives) {
    const b = document.createElement("button");
    b.className = "btn small" + (d.name === S.drive ? " on" : "");
    b.textContent = `${d.axis} · ${d.name}`;
    b.onclick = () => { S.drive = d.name; renderDrives(); resetCharts(); };
    box.appendChild(b);
  }
  const d = current();
  $("live-axis").textContent = $("chart-axis").textContent = $("lost-axis").textContent = d ? d.axis : "—";
  renderSliders(d);
}

function renderSliders(d) {
  const box = $("sliders");
  box.innerHTML = "";
  if (!d || !d.live.length) { box.innerHTML = '<p class="note">Napęd bez parametrów live.</p>'; return; }
  for (const p of d.live) {
    const row = document.createElement("div");
    row.className = "slider" + (p.value !== p.base ? " changed" : "");
    const id = `sl-${p.path}`;
    row.innerHTML = `<label for="${id}" title="${p.path}: ${p.doc}">${label(p.path)}</label>` +
      `<span class="val">${fmt(p.value * p.scale)} ${p.unit}</span>` +
      `<input type="range" id="${id}" min="${p.min}" max="${p.max}" step="${p.int ? 1 : (p.max - p.min) / 500}" value="${p.value}">`;
    const input = row.querySelector("input");
    const val = row.querySelector(".val");
    let timer = null;
    input.oninput = () => {
      val.textContent = `${fmt(input.value * p.scale)} ${p.unit}`;
      clearTimeout(timer);
      timer = setTimeout(() => setLive(d.name, p, Number(input.value), row), 120);
    };
    box.appendChild(row);
  }
}

const LABELS = {
  "mechanics.load": "Masa / bezwładność obciążenia", "motor.rotor_inertia": "Bezwładność silnika",
  "mechanics.j_screw": "Bezwładność śruby", "mechanics.friction_coulomb": "Tarcie Coulomba",
  "mechanics.friction_static": "Tarcie statyczne", "mechanics.friction_viscous": "Tarcie lepkie",
  "mechanics.backlash": "Luz", "electrical.supply_voltage": "Napięcie zasilania",
  "limits.torque_limit_permille": "Limit momentu",
};
function label(path) { return LABELS[path] || path; }

async function setLive(drive, p, value, row) {
  $("live-err").textContent = "";
  try {
    const rec = await api("/api/live", { drive, path: p.path, value: p.int ? Math.round(value) : value });
    p.value = rec.new;
    row.classList.toggle("changed", p.value !== p.base);
  } catch (e) {
    $("live-err").textContent = e.message;
    row.querySelector("input").value = p.value;
    row.querySelector(".val").textContent = `${fmt(p.value * p.scale)} ${p.unit}`;
  }
}

function renderPresets() {
  const box = $("presets");
  box.innerHTML = "";
  for (const p of S.state.presets) {
    const b = document.createElement("button");
    b.className = "btn small";
    b.textContent = p.name.replace(/_/g, " ");
    b.title = `${p.kind}: ${p.desc}`;
    b.onclick = async () => {
      $("live-err").textContent = "";
      try { await api(`/api/presets/${encodeURIComponent(p.name)}/load`, {}); await loadState(); b.classList.add("on"); }
      catch (e) { $("live-err").textContent = e.message; }
    };
    box.appendChild(b);
  }
}

$("preset-save").onclick = async () => {
  const name = $("preset-name").value.trim();
  $("live-err").textContent = "";
  try { await api(`/api/presets/${encodeURIComponent(name)}/save`, {}); await loadState(); }
  catch (e) { $("live-err").textContent = e.message; }
};

// ---- wykresy uPlot -------------------------------------------------------------------
function chartOpts(el, series, axes, scales) {
  const grid = { stroke: css("--line"), width: 1 };
  return {
    width: el.clientWidth || 600, height: 170, legend: { show: false }, cursor: { show: false },
    scales: Object.assign({ x: { time: false } }, scales),
    axes: [{ stroke: css("--fg3"), grid, ticks: grid, values: (u, v) => v.map((x) => x.toFixed(1)) }]
      .concat(axes.map((a) => Object.assign({ stroke: css("--fg3"), grid, ticks: grid, size: 56 }, a))),
    series: [{}].concat(series),
  };
}

function makeCharts() {
  const pos = $("chart-pos"), dyn = $("chart-dyn");
  const line = (stroke, scale) => ({ stroke: css(stroke), width: 1.5, scale, points: { show: false } });
  const empty = (n) => [[]].concat(Array.from({ length: n }, () => []));
  S.charts = {
    pos: new uPlot(chartOpts(pos, [line("--teal", "u"), line("--info", "u"), line("--amber", "e")],
      [{ scale: "u" }, { scale: "e", side: 1, grid: { show: false } }], {}), empty(3), pos),
    dyn: new uPlot(chartOpts(dyn, [line("--teal", "v"), line("--amber", "m"), line("--err", "k")],
      [{ scale: "v" }, { scale: "m", side: 1, grid: { show: false } }], {}), empty(3), dyn),
  };
  window.addEventListener("resize", () => {
    for (const [k, el] of [["pos", pos], ["dyn", dyn]]) S.charts[k].setSize({ width: el.clientWidth, height: 170 });
  });
}

function resetCharts() { /* bufory wszystkich napędów zostają; zmiana osi tylko przerysowuje */ draw(); }

function append(tele) {
  if (!tele.t.length) return;
  for (const [name, cols] of Object.entries(tele.drives)) {
    const b = S.buf[name] || (S.buf[name] = { t: [], cmd: [], act: [], ferr: [], vel: [], torque: [], lost: [] });
    b.t.push(...tele.t);
    for (const f of ["cmd", "act", "ferr", "vel", "torque", "lost"]) b[f].push(...cols[f]);
    const tmin = b.t[b.t.length - 1] - S.windowS;
    let cut = 0;
    while (cut < b.t.length && b.t[cut] < tmin) cut++;
    if (cut) for (const k of Object.keys(b)) b[k].splice(0, cut);
  }
}

function draw() {
  const b = S.buf[S.drive];
  if (!S.charts || !b) return;
  const lost0 = b.lost.length ? b.lost[0] : 0;
  S.charts.pos.setData([b.t, b.cmd, b.act, b.ferr]);
  S.charts.dyn.setData([b.t, b.vel, b.torque, b.lost.map((x) => x - lost0)]);
  $("lost").textContent = b.lost.length ? b.lost[b.lost.length - 1] : 0;
  $("accel").innerHTML = `przyspieszenie maks. z fizyki: <b class="c-amber mono">${fmt(maxAccel(b), 0)}</b> ${current()?.unit || ""}/s²`;
}

function maxAccel(b) {  // |Δv/Δt| na oknie 20 ms (wygładza szum próbkowania)
  let best = 0;
  for (let i = 0, j = 0; i < b.t.length; i++) {
    while (j < i && b.t[i] - b.t[j] > 0.02) j++;
    const dt = b.t[i] - b.t[j];
    if (dt > 0.004) best = Math.max(best, Math.abs((b.vel[i] - b.vel[j]) / dt));
  }
  return best;
}

// ---- WebSocket -----------------------------------------------------------------------
function connect() {
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
  ws.onopen = () => { $("link").className = "pill ok"; $("link-text").textContent = "Plant połączony"; };
  ws.onclose = () => {
    $("link").className = "pill bad"; $("link-text").textContent = "brak połączenia z panelem";
    setTimeout(connect, 1000);
  };
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    append(msg.telemetry);
    draw();
    renderStats(msg.stats);
    if (msg.desk) renderDeskState(msg.desk);
    renderRecord(msg.record);
  };
}

function renderStats(s) {
  $("stats").textContent = `t ${s.time.toFixed(2)} s · ramki ${s.frames} · utracone ${s.lost} · ` +
    `spóźnione ${s.late} · odrzucone ${s.rejected} · jitter ${s.jitter_us} µs` +
    (s.watchdog ? " · WATCHDOG E-4003" : "") + (s.model_failed ? " · BŁĄD MODELU E-4200" : "");
  const box = $("msgs");
  box.innerHTML = "";
  for (const m of s.messages.slice().reverse()) {
    const li = document.createElement("li");
    li.textContent = m;
    box.appendChild(li);
  }
}

// ---- pulpit --------------------------------------------------------------------------
function renderDesk(desk) {
  $("desk-off").hidden = !!desk;
  $("desk-on").hidden = !desk;
  if (!desk) return;
  const mk = (box, items, sel, text, path, key) => {
    $(box).innerHTML = "";
    for (const it of items) {
      const b = document.createElement("button");
      b.className = "btn small";
      b.dataset.v = it;
      b.textContent = text(it);
      b.onclick = () => deskCall(path, { [key]: it });
      $(box).appendChild(b);
    }
  };
  mk("desk-axes", desk.axes, desk.axis, (a) => a, "axis", "axis");
  mk("desk-steps", desk.steps, desk.step, (s) => `×${s}`, "step", "step");
  renderDeskState(desk);
}

function renderDeskState(d) {
  for (const b of $("desk-axes").children) b.classList.toggle("on", b.dataset.v === d.axis);
  for (const b of $("desk-steps").children) b.classList.toggle("on", Number(b.dataset.v) === d.step);
  $("key").checked = d.key;
  $("btn-start").classList.toggle("flash", d.buttons.cycle_start);
  $("btn-hold").classList.toggle("flash", d.buttons.feed_hold);
  $("desk-bits").textContent = Object.entries(d.bits).map(([n, b]) => `${n}=din-${String(b).padStart(2, "0")}`).join("  ") +
    `  · MPG zbocza ${d.mpg_edges}, w kolejce ${d.mpg_pending}`;
}

async function deskCall(path, body) {
  try { renderDeskState(await api(`/api/desk/${path}`, body)); }
  catch (e) { $("live-err").textContent = e.message; }
}

$("btn-start").onclick = () => deskCall("press", { button: "cycle_start" });
$("btn-hold").onclick = () => deskCall("press", { button: "feed_hold" });
$("key").onchange = (e) => deskCall("key", { on: e.target.checked });
for (const b of document.querySelectorAll("[data-mpg]")) b.onclick = () => turn(Number(b.dataset.mpg));

const DETENT_DEG = 3.6;  // 100 pozycji na obrót
let pendingDetents = 0, sendTimer = null;
function turn(detents) {
  if (!detents) return;
  S.dial = (S.dial + detents * DETENT_DEG) % 360;
  $("dial").querySelector(".knob").style.transform = `rotate(${S.dial}deg)`;
  pendingDetents += detents;
  if (!sendTimer) sendTimer = setTimeout(async () => {
    const n = pendingDetents; pendingDetents = 0; sendTimer = null;
    await deskCall("mpg", { detents: n });
  }, 50);
}

(function dial() {
  const el = $("dial");
  let last = null, acc = 0;
  const angle = (e) => {
    const r = el.getBoundingClientRect();
    return Math.atan2(e.clientY - r.top - r.height / 2, e.clientX - r.left - r.width / 2) * 180 / Math.PI;
  };
  el.onpointerdown = (e) => { last = angle(e); el.setPointerCapture(e.pointerId); };
  el.onpointermove = (e) => {
    if (last === null) return;
    const a = angle(e);
    let d = a - last;
    if (d > 180) d -= 360; if (d < -180) d += 360;
    last = a; acc += d;
    const n = Math.trunc(acc / DETENT_DEG);
    if (n) { acc -= n * DETENT_DEG; turn(n); }
  };
  el.onpointerup = el.onpointercancel = () => { last = null; acc = 0; };
  el.onwheel = (e) => {  // tylko z fokusem: przewijanie strony nie może dawać impulsów MPG
    if (document.activeElement !== el) return;
    e.preventDefault(); turn(e.deltaY < 0 ? 1 : -1);
  };
  el.onkeydown = (e) => {
    if (e.key === "ArrowRight" || e.key === "ArrowUp") turn(1);
    if (e.key === "ArrowLeft" || e.key === "ArrowDown") turn(-1);
  };
})();

// ---- nagrywanie ----------------------------------------------------------------------
function renderRecord(r) {
  $("rec-start").disabled = r.active;
  $("rec-stop").disabled = !r.active;
  $("rec-status").textContent = r.active ? `● ${r.file} · ${r.rows} wierszy` +
    (r.dropped ? ` · utracone ${r.dropped}` : "") : (r.file ? `zapisano ${r.file} (${r.rows} wierszy)` : "");
}
async function refreshFiles() {
  const files = await api("/api/records");
  $("rec-files").innerHTML = files.slice(-5).map((f) =>
    `<li><a href="/api/records/${encodeURIComponent(f.name)}" download>${f.name}</a> · ${(f.bytes / 1024).toFixed(1)} kB</li>`).join("");
}
$("rec-start").onclick = async () => { try { renderRecord(await api("/api/record/start", {})); } catch (e) { $("live-err").textContent = e.message; } };
$("rec-stop").onclick = async () => { renderRecord(await api("/api/record/stop", {})); refreshFiles(); };

// ---- start ---------------------------------------------------------------------------
loadState().then(() => { makeCharts(); connect(); }).catch((e) => { $("link-text").textContent = e.message; });
