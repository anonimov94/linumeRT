/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: ChatGPT
*/
"use strict";

const $ = (id) => document.getElementById(id);
const LETTERS = ["X", "Y", "Z", "A", "B", "C", "U", "V", "W"];
const fmt = (value, digits = 3) => value == null || !Number.isFinite(Number(value))
  ? "—" : Number(value).toFixed(digits);
const plain = (value) => value == null || value === "" ? "—" : String(value);
const pct = (value) => value == null ? "—" : fmt(value * 100, 0) + "%";

export function createDRO(jog, onAxesChange) {
  const rows = new Map();
  function axesFor(state) {
    return (Array.isArray(state?.axes) ? state.axes : [])
      .filter((axis) => axis && LETTERS.includes(axis.name))
      .sort((a, b) => LETTERS.indexOf(a.name) - LETTERS.indexOf(b.name));
  }
  function build(axes) {
    const names = axes.map((axis) => axis.name);
    if (names.join(",") === [...rows.keys()].join(",")) return;
    onAxesChange();
    if (names.length) jog.units(names[0]);
    rows.clear();
    $("axisRows").replaceChildren();
    for (const axis of names) {
      const tr = document.createElement("tr");
      const cells = Array.from({ length: 5 }, () => document.createElement("td"));
      cells[0].textContent = axis;
      cells[0].className = "axis-badge";
      cells[1].className = cells[2].className = "numeric";
      cells.forEach((cell) => tr.appendChild(cell));
      for (const direction of [-1, 1]) {
        const td = document.createElement("td");
        td.appendChild(jog.button(axis, direction));
        tr.appendChild(td);
      }
      $("axisRows").appendChild(tr);
      rows.set(axis, cells);
    }
  }
  function errors(items, gatewayError) {
    const list = $("errors");
    list.replaceChildren();
    const entries = Array.isArray(items) ? items.slice(-30).map(String) : [];
    if (gatewayError) entries.unshift("BRAMA: " + String(gatewayError));
    if (!entries.length) entries.push("Brak aktywnych błędów.");
    for (const entry of entries) {
      const li = document.createElement("li");
      li.textContent = entry;
      list.appendChild(li);
    }
  }
  function render(state, version) {
    const axes = axesFor(state);
    build(axes);
    for (const axis of axes) {
      const cells = rows.get(axis.name);
      cells[1].textContent = fmt(axis.work_position, 4);
      cells[2].textContent = fmt(axis.position, 4);
      cells[3].textContent = axis.homed ? "OK" : "NIE";
      cells[4].textContent = axis.limit_hit ? "LIMIT !" : "OK";
      cells[4].className = axis.limit_hit ? "limit-hit" : "";
    }
    $("homingStatus").textContent = state.all_homed ? "OSIE ZBAZOWANE" : "BAZOWANIE WYMAGANE";
    $("workOffset").textContent = plain(state.work_offset);
    $("modeState").textContent = plain(state.mode).toUpperCase();
    $("taskState").textContent = plain(state.task_state).toUpperCase();
    $("interpState").textContent = plain(state.interp_state);
    $("feedOverride").textContent = pct(state.feed_override);
    $("rapidOverride").textContent = pct(state.rapid_override);
    $("spindleOverride").textContent = pct(state.spindle_override);
    $("spindleState").textContent = fmt(state.spindle_speed, 0) + " rpm / " +
      plain(state.spindle_direction);
    $("toolState").textContent = plain(state.tool);
    $("programState").textContent = plain(state.program) + " / " + plain(state.line);
    $("schemaLabel").textContent = "SCHEMA " + plain(state.schema);
    $("versionState").textContent = plain(version);
    const byName = Object.fromEntries(axes.map((axis) => [axis.name, axis]));
    $("toolCoordinates").textContent = ["X", "Y", "Z"]
      .map((axis) => axis + " " + fmt(byName[axis]?.work_position)).join("  ·  ");
    errors(state.errors, state.gateway_error);
  }
  function freshness(age, connected) {
    const fresh = connected && Number.isFinite(age) && age <= 500;
    const label = $("freshnessStatus");
    if (fresh) {
      label.textContent = "DRO AKTUALNE (" + Math.round(age) + " ms)";
      label.className = "small-tag";
    } else {
      label.textContent = connected
        ? "NIEAKTUALNE (" + (Number.isFinite(age) ? Math.round(age) + " ms" : "brak danych") + ")"
        : "NIEAKTUALNE — BRAK POŁĄCZENIA";
      label.className = "small-tag stale-label";
    }
    document.querySelector(".readout").classList.toggle("stale", !fresh);
  }
  function jogButtons(enabled, reason) {
    document.querySelectorAll("#axisRows .jog-button").forEach((button) => {
      button.disabled = !enabled;
      button.title = enabled ? button.getAttribute("aria-label") : reason;
    });
  }
  return { render, freshness, jogButtons };
}
