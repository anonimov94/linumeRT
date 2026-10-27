/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: ChatGPT
*/
"use strict";

// Czyste porównanie migawek bramy (schema.py + pola runtime gateway.py).
// LinuxCNCReader opróżnia error_channel przy każdym read(), więc errors może
// zniknąć w następnej migawce; FakeMachine udostępnia także listę narastającą.
const event = (level, source, text) => ({ level, source, text });
const value = (data, key) => data?.[key] ?? null;
const axesByName = (state) => new Map(
  (Array.isArray(state?.axes) ? state.axes : [])
    .filter((a) => a && typeof a.name === "string")
    .map((a) => [a.name, a]),
);
const entries = (items) => Array.isArray(items) ? items.map(String) : [];
const unique = (items) => [...new Set(items)].sort();
const count = (list) => {
  const counts = new Map();
  for (const item of entries(list)) counts.set(item, (counts.get(item) || 0) + 1);
  return counts;
};

export function diffState(prev, next) {
  if (!next || typeof next !== "object") return [];
  const result = [];
  const add = (level, source, text) => result.push(event(level, source, text));
  for (const field of ["task_state", "mode", "interp_state"]) {
    if (value(prev, field) === value(next, field)) continue;
    const current = String(value(next, field) ?? "nieznany");
    const names = { task_state: "Zasilanie/E-STOP", mode: "Tryb", interp_state: "Interpreter" };
    const level = field === "task_state"
      ? (current === "estop" ? "alarm" : current === "on" ? "info" : "warn")
      : field === "interp_state" && current === "paused" ? "warn" : "info";
    add(level, "MASZYNA", names[field] + ": " + current);
  }
  if (prev?.all_homed !== next.all_homed && typeof next.all_homed === "boolean") {
    add(next.all_homed ? "info" : "warn", "BAZOWANIE",
      next.all_homed ? "Wszystkie osie zbazowane" : "Nie wszystkie osie zbazowane");
  }
  const previousAxes = axesByName(prev);
  for (const [name, axis] of axesByName(next)) {
    const previous = previousAxes.get(name);
    if (previous?.homed !== axis.homed && typeof axis.homed === "boolean") {
      add(axis.homed ? "info" : "warn", "OŚ " + name,
        axis.homed ? "Bazowanie potwierdzone" : "Oś niezbazowana");
    }
    if (previous?.limit_hit !== axis.limit_hit && typeof axis.limit_hit === "boolean") {
      add(axis.limit_hit ? "alarm" : "info", "OŚ " + name,
        axis.limit_hit ? "Krańcówka AKTYWNA" : "Krańcówka zwolniona");
    }
  }
  const previousErrors = count(prev?.errors);
  const seen = new Map();
  for (const message of entries(next.errors)) {
    const occurrence = (seen.get(message) || 0) + 1;
    seen.set(message, occurrence);
    if (occurrence > (previousErrors.get(message) || 0)) {
      add("alarm", "BŁĘDY CNC", message);
    }
  }
  const oldError = String(prev?.gateway_error || "");
  const newError = String(next.gateway_error || "");
  if (oldError !== newError) {
    if (newError) add("alarm", "BRAMA", "Błąd odczytu: " + newError);
    else add("info", "BRAMA", "Błąd odczytu ustąpił");
  }
  const oldPending = unique(entries(prev?.jog_stop_pending));
  const newPending = unique(entries(next.jog_stop_pending));
  if (oldPending.join("|") !== newPending.join("|")) {
    if (newPending.length) add("alarm", "JOG", "Stop niepotwierdzony dla: " + newPending.join(", "));
    else add("info", "JOG", "Brak oczekujących zatrzymań JOG");
  }
  if (prev?.tool !== next.tool && next.tool !== undefined) {
    add("info", "NARZĘDZIE", "Numer: " + String(next.tool ?? "brak"));
  }
  if (prev?.program !== next.program && next.program !== undefined) {
    add("info", "PROGRAM", "Plik: " + (next.program || "brak"));
  }
  return result;
}
