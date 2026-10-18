// linumeRT Plant: zakładki Napędy, Maszyna (widok 3D z modelu) i Awarie (sesja 023).
// SPDX-License-Identifier: GPL-2.0-or-later. Model-Author: Claude.
// Widok 3D: własny rzut perspektywiczny na canvas 2D (bez bibliotek), ≤ 30 FPS (CLAUDE.md §5).
"use strict";

const E = { tab: "praca", m: null, base: null, sel: null, scene: null, pick: null, dirty: false,
            d: { list: [], sel: null, inst: [], selInst: null }, f: null };
const col = (n) => css(n);
const clone = (o) => JSON.parse(JSON.stringify(o));
function getp(o, path) { return path.split(".").reduce((a, k) => (a == null ? a : a[k]), o); }
function setp(o, path, v) {
  const ks = path.split("."); let n = o;
  for (const k of ks.slice(0, -1)) { if (n[k] == null) n[k] = {}; n = n[k]; }
  n[ks[ks.length - 1]] = v;
}
const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// ---- zakładki i dolny pasek akcji --------------------------------------------------------
for (const b of document.querySelectorAll(".tab")) b.onclick = () => showTab(b.dataset.tab);
function showTab(tab) {
  E.tab = tab;
  for (const b of document.querySelectorAll(".tab")) b.classList.toggle("on", b.dataset.tab === tab);
  for (const v of document.querySelectorAll(".view")) v.hidden = v.id !== `view-${tab}`;
  ({ maszyna: loadMachine, napedy: loadDrives, awarie: loadFaults })[tab]?.();
  actions();
}
function actions() {
  const bar = $("actions");
  const defs = {
    maszyna: [["primary", "Zapisz wersję", "walidacja i historia", saveMachine],
              ["", "Przeładuj model", "napędy wyłączone", reloadMachine],
              ["", "Odrzuć zmiany", "wczytaj plik", loadMachine],
              ["", "Historia", "wersje machine.yaml", showHistory]],
    napedy: [["primary", "Kopiuj", "→ nowy szablon", () => cloneDrive(E.d.sel)],
             ["", "Zapisz jako szablon", "wybrana instancja", () => cloneDrive(E.d.selInst)],
             ["", "Porównaj", "z bazowym", () => $("d-diff").scrollIntoView()]],
  }[E.tab] || [];
  bar.innerHTML = "";
  bar.hidden = !defs.length;
  for (const [kind, label, sub, fn] of defs) {
    const b = document.createElement("button");
    b.className = `btn ${kind}`;
    b.innerHTML = `${esc(label)}<small>${esc(sub)}</small>`;
    b.onclick = fn;
    bar.appendChild(b);
  }
}

// ---- Maszyna: drzewo, formularz, walidacja --------------------------------------------------
async function loadMachine() {
  try {
    const r = await api("/api/machine");
    E.m = r.data; E.base = clone(r.data); E.dirty = false;
    $("m-file").textContent = r.file;
    renderTree(r.tree);
    renderValid(r.errors);
    if (!E.sel) E.sel = r.tree[1]?.path || r.tree[0].path;
    renderForm();
    E.scene = await api("/api/machine/scene");
    legend();
  } catch (e) { renderValid([e.message]); }
}

function renderTree(tree) {
  const box = $("m-tree"); box.innerHTML = "";
  for (const n of tree) {
    const b = document.createElement("button");
    b.className = "node" + (n.path === E.sel ? " on" : "");
    b.innerHTML = `${esc(n.title)}<small>${esc(n.sub)}</small>`;
    b.onclick = () => { E.sel = n.path; E.pick = null; renderTree(tree); renderForm(); };
    box.appendChild(b);
  }
}

function fields(obj, prefix, out, depth) {
  if (Array.isArray(obj) && obj.every((v) => typeof v === "number")) { out.push([prefix, obj]); return; }
  if (obj !== null && typeof obj === "object") {
    if (depth > 3) return;
    for (const [k, v] of Object.entries(obj)) fields(v, prefix ? `${prefix}.${k}` : k, out, depth + 1);
    return;
  }
  out.push([prefix, obj]);
}

function renderForm() {
  const box = $("m-form"); box.innerHTML = "";
  const node = getp(E.m, E.sel);
  $("m-form-title").textContent = E.sel;
  const list = []; fields(node, E.sel, list, 0);
  for (const [path, value] of list) {
    const lab = document.createElement("label");
    const short = path.slice(E.sel.length + 1) || path;
    lab.textContent = short;
    const changed = JSON.stringify(getp(E.base, path)) !== JSON.stringify(value);
    if (Array.isArray(value)) {
      lab.className = "wide";
      const vec = document.createElement("div"); vec.className = "vec";
      value.forEach((v, i) => {
        const inp = input(v, (nv) => { const a = getp(E.m, path).slice(); a[i] = nv; setp(E.m, path, a); }, changed);
        vec.appendChild(inp);
      });
      lab.appendChild(vec);
    } else {
      lab.appendChild(input(value, (nv) => setp(E.m, path, nv), changed));
    }
    box.appendChild(lab);
  }
  moveTools();
}

function input(value, apply, changed) {
  const inp = document.createElement(typeof value === "boolean" ? "select" : "input");
  if (typeof value === "boolean") inp.innerHTML = "<option>true</option><option>false</option>";
  inp.value = String(value);
  if (changed) inp.classList.add("changed");
  inp.onchange = () => {
    let v = inp.value;
    if (typeof value === "number") v = Number(v);
    else if (typeof value === "boolean") v = v === "true";
    else if (value === null && v !== "" && !isNaN(Number(v))) v = Number(v);
    apply(v); E.dirty = true; inp.classList.add("changed"); validateDraft();
  };
  return inp;
}

let vTimer = null;
function validateDraft() {
  clearTimeout(vTimer);
  vTimer = setTimeout(async () => {
    const r = await api("/api/machine/validate", { data: E.m });
    renderValid(r.errors);
    renderTree(r.tree);
  }, 250);
}
function renderValid(errors) {
  const v = $("m-valid");
  v.className = "valid " + (errors.length ? "bad" : "ok");
  v.innerHTML = errors.length ? `Walidacja: ${errors.length} błędów<br>` + errors.map(esc).join("<br>")
    : `Walidacja: 0 błędów${E.dirty ? " · zmiany niezapisane" : ""} · REQ-VM-11`;
}

async function saveMachine() {
  const comment = prompt("Opis wersji (historia):", "") ?? null;
  if (comment === null) return;
  try {
    const r = await api("/api/machine/save", { data: E.m, comment });
    E.dirty = false;
    await loadMachine();
    $("m-valid").innerHTML += ` · zapisano wersję ${r.version}`;
  } catch (e) { renderValid([e.message]); }
}
async function reloadMachine() {
  if (E.dirty && !confirm("Są niezapisane zmiany — przeładować model z pliku?")) return;
  try {
    const r = await api("/api/machine/reload", {});
    await loadMachine();
    $("m-valid").innerHTML += ` · model przeładowany (${esc(r.machine)})`;
  } catch (e) { renderValid([e.message]); }
}
async function showHistory() {
  const h = await api("/api/machine/history");
  $("m-history").innerHTML = "<h3>Historia</h3>" + (h.map((v) => `<li class="mono">${v.number} · ${esc(v.file)}` +
    `${v.comment ? " — " + esc(v.comment) : ""}</li>`).join("") || "<li class='note'>brak wersji</li>");
}

// ---- przesuwanie magazynu i pozycji wymiany ---------------------------------------------------
function editPath() {
  if (E.pick?.edit) return E.pick.edit;
  return { toolchanger: "toolchanger.base_position", positions: "positions.manual_change" }[E.sel] || null;
}
function moveTools() {
  const box = $("m-move"); const path = editPath();
  box.hidden = !path || !Array.isArray(getp(E.m, path));
  if (box.hidden) return;
  box.innerHTML = `<span class="note mono">${esc(path)}</span> <select id="m-step"><option>1</option><option selected>10</option><option>50</option></select>`;
  for (const [ax, i] of [["X", 0], ["Y", 1], ["Z", 2]]) for (const s of [-1, 1]) {
    const b = document.createElement("button");
    b.className = "btn small"; b.textContent = `${ax}${s < 0 ? "−" : "+"}`;
    b.onclick = () => {
      const a = getp(E.m, path).slice(); a[i] = Math.round((a[i] + s * Number($("m-step").value)) * 1000) / 1000;
      setp(E.m, path, a); E.dirty = true; renderForm(); validateDraft();
    };
    box.appendChild(b);
  }
}

// ---- widok 3D --------------------------------------------------------------------------------
const V = { yaw: -0.7, pitch: 0.55, zoom: 1, drag: null, hits: [] };
function legend() {
  $("m-legend").innerHTML = [["--fg3", "zakres mechaniczny"], ["--teal", "ograniczenia programowe"], ["--amber", "krańcówki, gniazda"],
    ["--err", "zderzaki, strefy zakazane"], ["--fg2", "bryły kolizyjne"], ["--info", "czujnik, wymiana"]]
    .map(([c, t]) => `<span style="color:${col(c)}">■ ${t}</span>`).join("");
}
function delta(path) {  // przesunięcie szkicu względem modelu (podgląd przed zapisem)
  const a = getp(E.m || {}, path), b = getp(E.base || {}, path);
  return Array.isArray(a) && Array.isArray(b) ? a.map((v, i) => v - b[i]) : [0, 0, 0];
}
function project(cv, sc) {
  const t = sc.boxes.find((b) => b.kind === "travel");
  const c = t ? t.min.map((v, i) => (v + t.max[i]) / 2) : [0, 0, 0];
  const size = t ? Math.max(...t.max.map((v, i) => v - t.min[i])) : 500;
  const f = Math.min(cv.width, cv.height) * 0.9 * V.zoom / size;
  const cy = Math.cos(V.yaw), sy = Math.sin(V.yaw), cp = Math.cos(V.pitch), sp = Math.sin(V.pitch);
  return ([x, y, z]) => {
    x -= c[0]; y -= c[1]; z -= c[2];
    const x1 = x * cy - y * sy, y1 = x * sy + y * cy;
    const y2 = y1 * cp - z * sp, z2 = y1 * sp + z * cp;
    const persp = 1 / (1 + y2 / (size * 3));
    return [cv.width / 2 + x1 * f * persp, cv.height / 2 - z2 * f * persp];
  };
}
function boxEdges(lo, hi) {
  const p = (i) => [i & 1 ? hi[0] : lo[0], i & 2 ? hi[1] : lo[1], i & 4 ? hi[2] : lo[2]];
  const out = [];
  for (let i = 0; i < 8; i++) for (const b of [1, 2, 4]) if (!(i & b)) out.push([p(i), p(i | b)]);
  return out;
}
function draw3d() {
  const cv = $("m-3d"); const sc = E.scene;
  if (!cv || E.tab !== "maszyna" || !sc) return;
  const dpr = window.devicePixelRatio || 1;
  if (cv.width !== cv.clientWidth * dpr) { cv.width = cv.clientWidth * dpr; cv.height = cv.clientHeight * dpr; }
  const g = cv.getContext("2d"); const P = project(cv, sc);
  g.clearRect(0, 0, cv.width, cv.height); g.lineWidth = 1.2 * dpr; V.hits = [];
  const line = (a, b, c, dash) => { const p = P(a), q = P(b); g.strokeStyle = c; g.setLineDash(dash || []);
    g.beginPath(); g.moveTo(...p); g.lineTo(...q); g.stroke(); };
  const colors = { travel: col("--fg3"), soft: col("--teal"), zone: col("--err"), body: col("--fg2") };
  const travel = sc.boxes.find((b) => b.kind === "travel");
  for (const b of sc.boxes) {
    const d = b.edit ? delta(b.edit) : [0, 0, 0];
    const lo = b.min.map((v, i) => v + d[i]), hi = b.max.map((v, i) => v + d[i]);
    for (const [a, c] of boxEdges(lo, hi)) line(a, c, colors[b.kind] || col("--fg2"), b.kind === "soft" ? [6 * dpr, 4 * dpr] : null);
    if (b.kind === "zone" || b.kind === "body") V.hits.push({ xy: P(lo.map((v, i) => (v + hi[i]) / 2)), el: b });
  }
  for (const cyl of sc.cylinders) {
    const d = cyl.edit ? delta(cyl.edit) : [0, 0, 0];
    const c = cyl.center.map((v, i) => v + d[i]);
    const ring = (z) => { const pts = []; for (let k = 0; k <= 24; k++) { const a = k / 24 * 2 * Math.PI;
      pts.push(P([c[0] + Math.cos(a) * cyl.d / 2, c[1] + Math.sin(a) * cyl.d / 2, z])); } return pts; };
    g.strokeStyle = cyl.kind === "pocket" ? col("--amber") : col("--fg2"); g.setLineDash([]);
    for (const z of [c[2], c[2] + cyl.h]) { g.beginPath(); ring(z).forEach((p, k) => (k ? g.lineTo(...p) : g.moveTo(...p))); g.stroke(); }
    line(c, [c[0], c[1], c[2] + cyl.h], g.strokeStyle);
    V.hits.push({ xy: P(c), el: cyl });
  }
  if (travel) for (const pt of sc.points.filter((p) => p.axis)) {  // krańcówki i zderzaki na krawędzi zakresu
    const i = "XYZ".indexOf(pt.axis); if (i < 0) continue;
    const xyz = [travel.min[0], travel.min[1], travel.max[2]]; xyz[i] = pt.value;
    const p = P(xyz); g.fillStyle = pt.kind === "limit" ? col("--amber") : col("--err");
    g.fillRect(p[0] - 3 * dpr, p[1] - 3 * dpr, 6 * dpr, 6 * dpr);
  }
  for (const pt of sc.points.filter((p) => p.xyz)) {
    const d = pt.edit ? delta(pt.edit) : [0, 0, 0];
    const p = P(pt.xyz.map((v, i) => v + d[i])); g.strokeStyle = col("--info"); g.setLineDash([]);
    g.strokeRect(p[0] - 6 * dpr, p[1] - 6 * dpr, 12 * dpr, 12 * dpr);
    g.fillStyle = col("--info"); g.font = `${11 * dpr}px monospace`; g.fillText(pt.name, p[0] + 9 * dpr, p[1] + 4 * dpr);
    V.hits.push({ xy: p, el: pt });
  }
  if (sc.tool) {  // bieżący koniec narzędzia z modelu (odświeżany)
    const p = P(sc.tool); g.fillStyle = col("--amber"); g.beginPath(); g.arc(p[0], p[1], 5 * dpr, 0, 7); g.fill();
    line(sc.tool, [sc.tool[0], sc.tool[1], sc.tool[2] + 40], col("--amber"));
  }
  if (E.pick) { const h = V.hits.find((x) => x.el === E.pick); if (h) { g.strokeStyle = col("--teal2"); g.setLineDash([]);
    g.beginPath(); g.arc(h.xy[0], h.xy[1], 14 * dpr, 0, 7); g.stroke(); } }
  // osie układu
  const o = travel ? travel.min : [0, 0, 0];
  [["X", [80, 0, 0]], ["Y", [0, 80, 0]], ["Z", [0, 0, 80]]].forEach(([n, v]) => {
    const q = o.map((a, i) => a + v[i]); line(o, q, col("--fg2")); const p = P(q);
    g.fillStyle = col("--fg2"); g.fillText(n, p[0] + 4, p[1]);
  });
}
(function view3d() {
  const cv = $("m-3d");
  cv.onpointerdown = (e) => { V.drag = [e.clientX, e.clientY, false]; cv.setPointerCapture(e.pointerId); };
  cv.onpointermove = (e) => { if (!V.drag) return; const dx = e.clientX - V.drag[0], dy = e.clientY - V.drag[1];
    if (Math.abs(dx) + Math.abs(dy) > 3) V.drag[2] = true;
    V.yaw += dx * 0.01; V.pitch = Math.max(-1.5, Math.min(1.5, V.pitch + dy * 0.01)); V.drag[0] = e.clientX; V.drag[1] = e.clientY; };
  cv.onpointerup = (e) => {
    if (V.drag && !V.drag[2]) {  // klik: wybór najbliższego elementu
      const r = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
      const x = (e.clientX - r.left) * dpr, y = (e.clientY - r.top) * dpr;
      let best = null, bd = 30 * dpr;
      for (const h of V.hits) { const d = Math.hypot(h.xy[0] - x, h.xy[1] - y); if (d < bd) { bd = d; best = h.el; } }
      E.pick = best;
      if (best?.edit) { E.sel = best.edit.split(".")[0]; renderForm(); }
      $("m-form-title").textContent = best ? best.name : E.sel;
    }
    V.drag = null;
  };
  cv.onwheel = (e) => { e.preventDefault(); V.zoom = Math.max(0.3, Math.min(6, V.zoom * (e.deltaY < 0 ? 1.1 : 0.9))); };
  let last = 0;
  const loop = (t) => { if (t - last > 33) { last = t; draw3d(); } requestAnimationFrame(loop); };  // ≤ 30 FPS
  requestAnimationFrame(loop);
  setInterval(async () => {  // koniec narzędzia na żywo
    if (E.tab === "maszyna" && E.scene) { try { E.scene.tool = (await api("/api/machine/scene")).tool; } catch (_) { /* brak */ } }
  }, 500);
})();

// ---- Napędy ------------------------------------------------------------------------------------
async function loadDrives() {
  E.d.list = await api("/api/drives/templates");
  E.d.inst = await api("/api/drives/instances");
  $("d-count").textContent = E.d.list.length;
  if (!E.d.sel) E.d.sel = E.d.list[0]?.id;
  renderDriveList(); renderInstances(); showTemplate(E.d.sel);
}
function renderDriveList() {
  const box = $("d-list"); box.innerHTML = "";
  for (const t of E.d.list) {
    const b = document.createElement("button");
    b.className = "item" + (t.id === E.d.sel ? " on" : "");
    b.innerHTML = `${esc(t.name)} <span class="note">v${t.version}</span><small>${esc(t.id)} · ${esc(t.type)}` +
      `${t.based_on ? " · based_on " + esc(t.based_on) : ""}</small>`;
    b.onclick = () => { E.d.sel = t.id; E.d.selInst = null; renderDriveList(); renderInstances(); showTemplate(t.id); };
    box.appendChild(b);
  }
}
function renderInstances() {
  const box = $("d-inst"); box.innerHTML = "";
  for (const i of E.d.inst) {
    const b = document.createElement("button");
    const ov = Object.keys(i.overrides).length ? JSON.stringify(i.overrides).replace(/[{}"]/g, "").slice(0, 60) : "—";
    b.className = "item" + (i.id === E.d.selInst ? " on" : "");
    b.innerHTML = `<span class="c-teal mono">${esc(i.axis || "·")}</span> ${esc(i.id)}<small>${esc(i.template)}</small>` +
      `<small class="${ov === "—" ? "" : "warn"}">nadpisania: ${esc(ov)}</small>`;
    b.onclick = () => { E.d.selInst = i.id; E.d.sel = i.template; renderDriveList(); renderInstances(); showTemplate(i.template); };
    box.appendChild(b);
  }
}
const SHOW = [["type", "Typ"], ["motor.rotor_inertia", "J wirnika [kg·m²]"], ["motor.rated_torque", "Moment znam. [N·m]"],
  ["motor.peak_torque", "Moment szczyt. [N·m]"], ["motor.encoder_counts_per_rev", "Enkoder [imp/obr]"],
  ["controller.kp_pos", "Kp położenia [1/s]"], ["controller.kv", "Kv [N·m·s/rad]"],
  ["limits.following_window", "Okno błędu [imp]"], ["limits.torque_limit_permille", "Limit momentu [‰]"],
  ["mechanics.load", "Obciążenie"], ["mechanics.ratio", "Przełożenie"]];
async function showTemplate(id) {
  if (!id) return;
  const r = await api(`/api/drives/templates/${encodeURIComponent(id)}`);
  const t = r.template;
  $("d-title").textContent = `Szablon · ${t.id} · v${t.version}` + (t.based_on ? ` · based_on ${t.based_on}` : "");
  const diffPaths = new Set(r.diff.map((d) => d.path));
  $("d-detail").innerHTML = SHOW.map(([p, l]) => { const v = getp(t, p); return v === undefined ? "" :
    `<label>${esc(l)}<input readonly value="${esc(v)}" class="${diffPaths.has(p) ? "changed" : ""}"></label>`; }).join("") +
    `<label class="wide">Parametry live<input readonly value="${esc((t.live || []).join(", ") || "—")}"></label>`;
  $("d-curve").innerHTML = curve(t.motor?.torque_curve || []);
  $("d-diff").innerHTML = "<h3>Różnice względem szablonu bazowego</h3>" + (r.diff.length ? r.diff.map((d) =>
    `<div class="diffrow"><span>${esc(d.path)}</span><span>${esc(JSON.stringify(d.base))}</span><span class="new">${esc(JSON.stringify(d.value))}</span></div>`).join("")
    : "<p class='note'>brak (szablon bazowy albo bez based_on)</p>");
}
function curve(pts) {
  if (pts.length < 2) return "";
  const W = 520, H = 170, wmax = Math.max(...pts.map((p) => p[0])) || 1, tmax = Math.max(...pts.map((p) => p[1])) || 1;
  const xy = (p) => `${40 + p[0] / wmax * (W - 60)},${H - 24 - p[1] / tmax * (H - 44)}`;
  return `<h3>Krzywa moment–prędkość</h3><svg viewBox="0 0 ${W} ${H}" width="100%">` +
    `<polyline fill="none" stroke="${col("--teal")}" stroke-width="2" points="${pts.map(xy).join(" ")}"/>` +
    pts.map((p) => `<circle cx="${xy(p).split(",")[0]}" cy="${xy(p).split(",")[1]}" r="3" fill="${col("--bg2")}" stroke="${col("--teal")}"/>`).join("") +
    `<text x="40" y="14" fill="${col("--fg3")}" font-size="11" font-family="monospace">${tmax.toFixed(2)} N·m</text>` +
    `<text x="${W - 20}" y="${H - 6}" fill="${col("--fg3")}" font-size="11" text-anchor="end" font-family="monospace">${wmax.toFixed(0)} rad/s</text></svg>`;
}
async function cloneDrive(source) {
  if (!source) { alert("Wybierz szablon albo instancję."); return; }
  const id = prompt(`Nowy identyfikator szablonu (kopia ${source}):`, `${source}_kopia`);
  if (!id) return;
  try { await api("/api/drives/clone", { source, new_id: id }); E.d.sel = id; await loadDrives(); }
  catch (e) { alert(e.message); }
}

// ---- Awarie --------------------------------------------------------------------------------------
async function loadFaults() {
  try {
    const [f, m] = [await api("/api/faults"), E.m ? { data: E.m } : await api("/api/machine")];
    E.f = { ...f, inputs: Object.keys(m.data?.io?.inputs || {}), axes: (S.state?.drives || []).map((d) => d.axis) };
    renderFaults();
  } catch (e) { $("f-err").textContent = e.message; }
}
const DRIVE_CODES = ["GENERIC", "FOLLOWING_ERROR", "OVERLOAD", "OVERCURRENT", "OVERTEMP", "DC_BUS", "ENCODER_LOST", "HW_LIMIT", "STO"];
function paramInput(name) {
  const opts = (xs) => xs.map((x) => `<option>${esc(x)}</option>`).join("");
  const f = E.f;
  return {
    drive: `<select data-p="drive">${opts(Object.keys(f.drives))}</select>`,
    code: `<select data-p="code">${opts(DRIVE_CODES)}</select>`,
    axis: `<select data-p="axis">${opts([...new Set(f.axes)])}</select>`,
    input: `<select data-p="input">${opts(f.inputs)}</select>`,
    percent: `<input data-p="percent" type="number" value="5" min="1" max="100" title="%">`,
    ms: `<input data-p="ms" type="number" value="20" min="1" max="10000" title="ms">`,
    closed: `<select data-p="closed"><option value="true">zamknięty</option><option value="false">otwarty</option></select>`,
  }[name] || "";
}
function renderFaults() {
  const box = $("f-catalog"); box.innerHTML = "";
  for (const c of E.f.catalog) {
    const card = document.createElement("div");
    card.className = "fault" + (c.kind === "estop" ? " danger" : "");
    card.innerHTML = `<b>${esc(c.desc)}</b><span class="note mono">${esc(c.kind)}</span>${c.params.map(paramInput).join("")}` +
      `<div class="row"><button class="btn small" data-a="on">Włącz</button><button class="btn small" data-a="off">Zdejmij</button></div>`;
    const params = () => { const o = {}; card.querySelectorAll("[data-p]").forEach((el) => {
      o[el.dataset.p] = el.type === "number" ? Number(el.value) : el.value === "true" ? true : el.value === "false" ? false : el.value; }); return o; };
    card.querySelector("[data-a=on]").onclick = () => faultCall(`/api/faults/${c.kind}`, params());
    card.querySelector("[data-a=off]").onclick = () => faultCall(`/api/faults/${c.kind}/clear`, params());
    box.appendChild(card);
  }
  renderActive();
}
function renderActive() {
  const box = $("f-active");
  box.innerHTML = E.f.active.length ? "" : "<p class='note'>brak aktywnych awarii</p>";
  for (const a of E.f.active) {
    const b = document.createElement("button"); b.className = "item";
    const { kind, ...p } = a;
    b.innerHTML = `${esc(kind)}<small>${esc(JSON.stringify(p))} · kliknij, aby zdjąć</small>`;
    b.onclick = () => faultCall(`/api/faults/${kind}/clear`, Object.fromEntries(Object.entries(p).filter(([k]) => k !== "alarm")));
    box.appendChild(b);
  }
  $("f-drives").textContent = Object.entries(E.f.drives).map(([d, s]) => `${d}: ${s}`).join(" · ") + ` · utracone ramki ${E.f.dropped}`;
}
async function faultCall(path, body) {
  $("f-err").textContent = "";
  try { await api(path, body); } catch (e) { $("f-err").textContent = e.message; }
  const f = await api("/api/faults"); Object.assign(E.f, f); renderActive();
}
setInterval(async () => { if (E.tab === "awarie" && E.f) { try { Object.assign(E.f, await api("/api/faults")); renderActive(); } catch (_) { /* brak */ } } }, 1000);
actions();
