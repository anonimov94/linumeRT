// linumeRT Plant: zakładka „Maszyny” — biblioteka maszyn i edycja YAML aktywnej maszyny.
// SPDX-License-Identifier: GPL-2.0-or-later. Model-Author: Claude.
// API: /api/machines*, /api/machine/text* (plant/server/linumert_plant/panel/machine_library.py).
"use strict";

const L = { list: [], trash: [], sel: null, orig: "", file: "", timer: null };

const lerr = (msg) => { $("l-err").textContent = msg || ""; };
const lsel = () => L.list.find((m) => m.file === L.sel);
const lname = () => $("l-name").value.trim();

async function lcall(path, body, okText) {
  lerr("");
  try {
    const r = await api(path, body);
    await loadLibrary();
    if (okText) $("l-valid").className = "valid ok", $("l-valid").textContent = okText;
    return r;
  } catch (e) { lerr(e.message); return null; }
}

async function loadLibrary() {
  const [lib, txt] = await Promise.all([api("/api/machines"), api("/api/machine/text")]);
  L.list = lib.machines; L.trash = lib.trash;
  $("l-dir").textContent = lib.directory;
  const active = L.list.find((m) => m.active);
  if (!lsel()) L.sel = active ? active.file : L.list[0]?.file ?? null;
  renderLibrary();
  if (L.file !== txt.file || $("l-text").value === L.orig) {  // nie nadpisuj niezapisanych zmian
    L.file = txt.file; L.orig = txt.text; $("l-text").value = txt.text; validateText();
  }
  $("l-title").textContent = `Aktywna maszyna — ${txt.file} (YAML)`;
  actions();
}

function renderLibrary() {
  const box = $("l-list"); box.innerHTML = "";
  for (const m of L.list) {
    const b = document.createElement("button");
    b.className = "item" + (m.file === L.sel ? " on" : "");
    b.innerHTML = `${esc(m.name)}${m.active ? ' <span class="badge-on">● aktywna</span>' : ""}` +
      `<small>${esc(m.file)} · ${esc(m.type)} · osie ${esc(m.axes)} · napędy ${m.drives}</small>` +
      (m.valid ? "" : `<small class="bad">niepoprawna: ${esc(m.errors.join("; "))}</small>`);
    b.onclick = () => { L.sel = m.file; renderLibrary(); actions(); };
    box.appendChild(b);
  }
  if (!L.list.length) box.innerHTML = "<p class='note'>brak maszyn w katalogu</p>";
  const tr = $("l-trash"); tr.innerHTML = L.trash.length ? "" : "<p class='note'>kosz pusty</p>";
  for (const t of L.trash) {
    const b = document.createElement("button"); b.className = "item";
    b.innerHTML = `${esc(t.machine)}<small>kliknij, aby przywrócić</small>`;
    b.onclick = () => lcall("/api/machines/restore", { file: t.file }, `Przywrócono ${t.machine}`);
    tr.appendChild(b);
  }
}

async function validateText() {
  const text = $("l-text").value, v = $("l-valid");
  try {
    const r = await api("/api/machine/text/validate", { text });
    const dirty = text !== L.orig;
    v.className = "valid " + (r.errors.length ? "bad" : "ok");
    v.textContent = r.errors.length ? r.errors.join("\n") : dirty ? "Poprawne — niezapisane zmiany" : "Poprawne";
    v.style.whiteSpace = "pre-wrap";
  } catch (e) { v.className = "valid bad"; v.textContent = e.message; }
}

async function saveText() {
  lerr("");
  try {
    const r = await api("/api/machine/text/save", { text: $("l-text").value, comment: $("l-comment").value });
    L.orig = $("l-text").value;
    await loadLibrary();
    $("l-valid").className = "valid ok";
    $("l-valid").textContent = `Zapisano${r.version ? " " + r.version : ""}. Przeładuj model (zakładka Maszyna), aby użyć zmian.`;
  } catch (e) { lerr(e.message); $("l-valid").className = "valid bad"; $("l-valid").textContent = e.message; }
}

function needSel() { const m = lsel(); if (!m) lerr("Wybierz maszynę z listy."); return m; }
function needName() { const n = lname(); if (!n) lerr("Wpisz nazwę w polu pod listą."); return n; }

window.loadLibrary = loadLibrary;
window.libraryActions = () => [
  ["primary", "Aktywuj", "podmień model w Plant", () => { const m = needSel(); if (m) lcall("/api/machines/activate", { file: m.file }, `Aktywna: ${m.name}`); }],
  ["", "Kopiuj", "→ nowa maszyna", () => { const m = needSel(), n = m && needName(); if (n) lcall("/api/machines/clone", { file: m.file, name: n }, `Utworzono ${n}`); }],
  ["", "Zmień nazwę", "nieaktywna", () => { const m = needSel(), n = m && needName(); if (n) lcall("/api/machines/rename", { file: m.file, name: n }, `Nazwa: ${n}`); }],
  ["warn", "Usuń", "do kosza", () => { const m = needSel(); if (m) lcall("/api/machines/delete", { file: m.file }, `${m.name} w koszu`); }],
  ["", "Zapisz YAML", "walidacja i historia", saveText],
];

$("l-text").addEventListener("input", () => { clearTimeout(L.timer); L.timer = setTimeout(validateText, 300); });
