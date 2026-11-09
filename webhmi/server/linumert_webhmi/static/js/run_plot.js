/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
*/
"use strict";

const $ = (id) => document.getElementById(id);
const num = (v, digits = 4) => Number.isFinite(v) ? v.toFixed(digits) : "brak danych";

function plot(svg, series, elapsed, symmetric = false, peak = null) {
  svg.replaceChildren();
  const points = series.flatMap((s) => s.points);
  if (!points.length) return;
  const xmax = Math.max(elapsed || 0, ...points.map((p) => p[0]), .001);
  let low = Math.min(...points.map((p) => p[1]), peak?.value_mm ?? Infinity);
  let high = Math.max(...points.map((p) => p[1]), peak?.value_mm ?? -Infinity);
  if (symmetric) { high = Math.max(Math.abs(low), Math.abs(high), .001); low = -high; }
  const margin = Math.max((high - low) * .06, .0001);
  low -= margin; high += margin;
  const x = (t) => 72 + 700 * t / xmax;
  const y = (v) => 190 - 170 * (v - low) / (high - low);
  function node(name, attrs, text = null) {
    const element = document.createElementNS(svg.namespaceURI, name);
    for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, String(value));
    if (text !== null) element.textContent = text;
    svg.append(element); return element;
  }
  node("path", {d: "M72 20V190H772", class: "report-axis"});
  node("text", {x: 4, y: 24}, num(high));
  node("text", {x: 4, y: 190}, num(low));
  node("text", {x: 72, y: 215}, "0 s");
  node("text", {x: 700, y: 215}, num(xmax, 2) + " s");
  if (symmetric) node("path", {d: "M72 " + y(0) + "H772", class: "report-axis"});
  for (const s of series) {
    const group = node("g", {class: "report-series " + s.style});
    for (const [t, v] of s.points) {
      const circle = document.createElementNS(svg.namespaceURI, "circle");
      circle.setAttribute("cx", x(t)); circle.setAttribute("cy", y(v));
      circle.setAttribute("r", "1.4"); group.append(circle);
    }
  }
  if (peak) node("circle", {cx: x(peak.t), cy: y(peak.value_mm), r: 4,
                          class: "report-peak"});
}

export function createRunPlots() {
  let report = null;
  function redraw() {
    if (!report) return;
    const axis = $("jobReportAxis").value;
    const points = report.trajectory;
    const series = (key, style) => ({style, points: points.map((r) => [r.t, r.axes[axis][key]])});
    plot($("jobPositionPlot"), [series("commanded", "commanded"), series("actual", "actual")],
         report.time.elapsed_s);
    const peak = report.axes[axis].following_error.peak;
    plot($("jobErrorPlot"), [series("following_error", "error")], report.time.elapsed_s, true, peak);
    $("jobReportPeak").textContent = "Oś " + axis + " · maksimum w pełnym zapisie: " +
      num(report.axes[axis].following_error.max_abs_mm) + " mm · czas " + num(peak?.t, 3) +
      " s · linia ruchu " + (peak?.motion_line ?? "brak danych");
  }
  $("jobReportAxis").addEventListener("change", redraw);
  return {clear() {
    report = null; $("jobReportPlots").hidden = true;
    $("jobReportAlarms").replaceChildren();
    $("jobReportTiming").textContent = "";
  }, show(value) {
    report = value; $("jobReportPlots").hidden = false;
    $("jobReportQuality").textContent = report.quality.samples + " próbek NML · widok " +
      report.trajectory.length + " punktów · najdłuższy odstęp " +
      num(report.quality.max_gap_s, 3) + " s. Wspólna oś czasu od Start; współrzędne maszyny [mm]. " +
      "Punkty są zachowanymi odczytami, bez rekonstrukcji pomiędzy nimi. " +
      "Maksima/RMS obejmują pełny zapis, końcowe kryterium dotyczy trzech ostatnich odczytów.";
    $("jobReportTiming").textContent = report.time.comparison_available
      ? "Czas bez pauz minus dolna granica modelu: " +
        num(report.time.excess_over_lower_bound_s, 2) + " s (" +
        num(report.time.excess_over_lower_bound_percent, 2) + "%). Model jest dolną granicą."
      : "Porównanie czasu całego programu niedostępne dla tego wyniku lub niepełnego zapisu.";
    $("jobReportAlarms").replaceChildren();
    const alarms = [...report.alarms, ...report.controller_errors];
    for (const alarm of alarms.slice(0, 200)) {
      const li = document.createElement("li");
      li.textContent = num(alarm.observed_at_s, 3) + " s · ruch N" +
        (alarm.motion_line ?? "?") + " · odczyt N" + (alarm.line ?? "?") + " · " +
        (alarm.code || "LinuxCNC") + " · " + alarm.text;
      $("jobReportAlarms").append(li);
    }
    if (!alarms.length) $("jobReportAlarms").textContent = "Brak alarmów w zapisanych próbkach.";
    if (alarms.length > 200) $("jobReportAlarms").append("Pozostałe zdarzenia są w raporcie JSON.");
    redraw();
  }};
}
