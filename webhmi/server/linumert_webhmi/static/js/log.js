/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: ChatGPT
*/
"use strict";

const CAPACITY = 500;
const LEVELS = new Set(["info", "warn", "alarm"]);
const $ = (id) => document.getElementById(id);
const timeText = (date) => {
  const pad = (n, size = 2) => String(n).padStart(size, "0");
  return [pad(date.getHours()), pad(date.getMinutes()), pad(date.getSeconds())].join(":") +
    "." + pad(date.getMilliseconds(), 3);
};
const clean = (value) => String(value ?? "").replace(/[\r\n\t]+/g, " ").slice(0, 600);
const pad = (n) => String(n).padStart(2, "0");

export function createLog() {
  // Pamięć ograniczona: najstarsze zdarzenie jest nadpisywane po 500 wpisach.
  const buffer = new Array(CAPACITY);
  let first = 0;
  let length = 0;
  let filter = "all";
  const list = $("eventLog");
  const selector = $("logFilter");
  const exportButton = $("logExport");
  const clearButton = $("logClear");
  const selected = () => {
    const values = [];
    for (let i = 0; i < length; i++) {
      const item = buffer[(first + i) % CAPACITY];
      if (filter === "all" || filter === "warn" && item.level !== "info" ||
          filter === "alarm" && item.level === "alarm") values.push(item);
    }
    return values;
  };
  const nearBottom = () => list.scrollHeight - list.scrollTop - list.clientHeight <= 30;
  function redraw(follow = false) {
    const previousScroll = list.scrollTop;
    const items = selected();
    const nodes = document.createDocumentFragment();
    for (const entry of items) {
      const row = document.createElement("li");
      row.className = "event-row level-" + entry.level;
      const timestamp = document.createElement("time");
      timestamp.textContent = entry.time;
      const level = document.createElement("strong");
      level.textContent = { info: "INFO", warn: "UWAGA", alarm: "ALARM" }[entry.level];
      const message = document.createElement("span");
      message.textContent = entry.source + " · " + entry.text;
      row.append(timestamp, level, message);
      nodes.appendChild(row);
    }
    list.replaceChildren(nodes);
    if (follow) list.scrollTop = list.scrollHeight;
    else list.scrollTop = previousScroll;
  }
  function add(level, source, text) {
    const follow = nearBottom();
    const entry = { time: timeText(new Date()), level: LEVELS.has(level) ? level : "info",
                    source: clean(source), text: clean(text) };
    if (length < CAPACITY) {
      buffer[(first + length) % CAPACITY] = entry;
      length++;
    } else {
      buffer[first] = entry;
      first = (first + 1) % CAPACITY;
    }
    redraw(follow);
    return entry;
  }
  function appendAll(events) {
    // Wiele zmian tej samej migawki zostaje zapisanych z kolejnymi czasami.
    for (const entry of events) add(entry.level, entry.source, entry.text);
  }
  function exportText() {
    const stamp = new Date();
    const day = "" + stamp.getFullYear() + pad(stamp.getMonth() + 1) + pad(stamp.getDate());
    const clock = pad(stamp.getHours()) + pad(stamp.getMinutes()) + pad(stamp.getSeconds());
    const name = "linumert-webhmi-" + day + "-" + clock + ".txt";
    // Eksport zawiera wszystkie zdarzenia z bufora, niezależnie od filtra.
    const lines = ["linumeRT WebHMI — dziennik operatora",
      "Eksport: " + stamp.toLocaleString("pl-PL"),
      "Wpisy: " + length, ""];
    for (let i = 0; i < length; i++) {
      const entry = buffer[(first + i) % CAPACITY];
      lines.push("[" + entry.time + "] [" + entry.level.toUpperCase() + "] [" +
        entry.source + "] " + entry.text);
    }
    const blob = new Blob([lines.join("\n") + "\n"], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    link.hidden = true;
    document.body.appendChild(link);
    link.click();
    link.remove();
    // Zwolnienie w kolejnym obrocie kolejki zdarzeń pozwala pobrać plik w Chromium.
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  selector.addEventListener("change", () => { filter = selector.value; redraw(true); });
  clearButton.addEventListener("click", () => {
    first = 0;
    length = 0;
    buffer.fill(undefined);
    redraw(false);
  });
  exportButton.addEventListener("click", exportText);

  function lamps(state, connected, fresh, jogStatus) {
    const axes = Array.isArray(state?.axes) ? state.axes : [];
    const pending = Array.isArray(state?.jog_stop_pending) ? state.jog_stop_pending : [];
    const moving = Array.isArray(state?.jog_active) ? state.jog_active : [];
    const errs = Array.isArray(state?.errors) ? state.errors : [];
    const stale = !connected || !fresh || !state;
    const lamp = (name, level, text) => ({ name, level, text });
    const unknown = (name) => lamp(name, "warn", "NIEAKTUALNE");
    const items = [
      lamp("ŁĄCZE", !connected ? "alarm" : fresh ? "info" : "warn",
        !connected ? "OFFLINE" : fresh ? "ONLINE" : "NIEAKTUALNE"),
      stale ? unknown("E-STOP") : lamp("E-STOP", state.task_state === "estop" ? "alarm" :
        state.task_state === "estop_reset" ? "warn" : "info",
        state.task_state === "estop" ? "AKTYWNY" :
          state.task_state === "estop_reset" ? "RESET" : "ZWOLNIONY"),
      stale ? unknown("ZASILANIE") : lamp("ZASILANIE", state.task_state === "on" ? "info" : "warn",
        state.task_state === "on" ? "ON" : state.task_state === "off" ? "OFF" :
          String(state.task_state).toUpperCase()),
      stale ? unknown("BAZOWANIE") : lamp("BAZOWANIE", state.all_homed ? "info" : "warn",
        state.all_homed ? "WSZYSTKIE OK" : "WYMAGANE"),
      stale ? unknown("KRAŃCÓWKI") : lamp("KRAŃCÓWKI", axes.some(a => a.limit_hit) ? "alarm" : "info",
        axes.some(a => a.limit_hit) ? "AKTYWNE: " +
          axes.filter(a => a.limit_hit).map(a => a.name).join(", ") : "BRAK AKTYWNYCH"),
      stale ? unknown("JOG") : lamp("JOG",
        pending.length || String(jogStatus).includes("NIEPOTWIERDZONY") ? "alarm" :
          moving.length || String(jogStatus).includes("ZATRZYMYWANIE") ? "warn" : "info",
        pending.length ? "STOP OCZEKUJE: " + pending.join(", ") :
          moving.length ? "RUCH: " + moving.join(", ") : String(jogStatus).includes("ZATRZYMYWANIE") ?
            "ZATRZYMYWANIE" : "BEZ RUCHU"),
      stale ? unknown("BŁĘDY") : lamp("BŁĘDY",
        errs.length || state.gateway_error ? "alarm" : "info",
        state.gateway_error ? "BŁĄD BRAMY" : errs.length ? "AKTYWNE: " + errs.length : "BRAK"),
    ];
    const fragment = document.createDocumentFragment();
    for (const item of items) {
      const row = document.createElement("div");
      row.className = "lamp level-" + item.level;
      const dot = document.createElement("span");
      dot.className = "lamp-dot";
      dot.setAttribute("aria-hidden", "true");
      const name = document.createElement("strong");
      name.textContent = item.name;
      const value = document.createElement("span");
      value.textContent = item.text;
      row.append(dot, name, value);
      fragment.appendChild(row);
    }
    $("lamps").replaceChildren(fragment);
  }
  function metrics(statesPerSecond, age, ackMs) {
    $("stateRate").textContent = statesPerSecond.toFixed(1) + " stanów/s";
    $("stateAge").textContent = Number.isFinite(age) ? Math.round(age) + " ms" : "BRAK";
    $("ackLatency").textContent = Number.isFinite(ackMs) ? Math.round(ackMs) + " ms" : "—";
  }
  redraw();
  return { add, appendAll, lamps, metrics };
}
