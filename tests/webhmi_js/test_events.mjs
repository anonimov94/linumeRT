/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: ChatGPT
*/
import assert from "node:assert/strict";
import test from "node:test";
import { diffState } from "../../webhmi/server/linumert_webhmi/static/js/events.js";

const snapshot = (changes = {}) => ({
  schema: 1, task_state: "on", mode: "manual", interp_state: "idle",
  all_homed: true, tool: 1, program: "part.ngc", errors: [],
  axes: [
    { name: "X", homed: true, limit_hit: false, following_error: 0 },
    { name: "Y", homed: true, limit_hit: false, following_error: 0 },
  ],
  jog_stop_pending: [], ...changes,
});
const has = (items, source, fragment, level) =>
  items.some((x) => x.source === source && x.text.includes(fragment) && x.level === level);

test("unchanged state, including keepalive, generates no events", () => {
  const a = snapshot();
  assert.deepEqual(diffState(a, structuredClone(a)), []);
});
test("task state and mode transitions have correct levels", () => {
  assert.equal(has(diffState(snapshot(), snapshot({ task_state: "estop" })),
    "MASZYNA", "estop", "alarm"), true);
  assert.equal(has(diffState(snapshot({ task_state: "estop" }), snapshot()),
    "MASZYNA", "on", "info"), true);
  assert.equal(has(diffState(snapshot(), snapshot({ task_state: "off" })),
    "MASZYNA", "off", "warn"), true);
  assert.equal(has(diffState(snapshot(), snapshot({ mode: "auto" })),
    "MASZYNA", "auto", "info"), true);
});
test("interpreter transitions detect running, paused and idle", () => {
  assert.equal(has(diffState(snapshot(), snapshot({ interp_state: "reading" })),
    "MASZYNA", "reading", "info"), true);
  assert.equal(has(diffState(snapshot(), snapshot({ interp_state: "paused" })),
    "MASZYNA", "paused", "warn"), true);
  assert.equal(has(diffState(snapshot({ interp_state: "paused" }), snapshot()),
    "MASZYNA", "idle", "info"), true);
});
test("all homed and per-axis homed are independent", () => {
  const changed = snapshot({ all_homed: false, axes: [
    { name: "X", homed: false, limit_hit: false },
    { name: "Y", homed: true, limit_hit: false },
  ] });
  const output = diffState(snapshot(), changed);
  assert.equal(has(output, "BAZOWANIE", "Nie wszystkie", "warn"), true);
  assert.equal(has(output, "OŚ X", "niezbasowana", "warn"), true);
  assert.equal(output.some(e => e.source === "OŚ Y"), false);
});
test("limit hit per axis both directions", () => {
  const alarm = snapshot({ axes: [
    { name: "X", homed: true, limit_hit: true },
    { name: "Y", homed: true, limit_hit: false },
  ]});
  assert.equal(has(diffState(snapshot(), alarm), "OŚ X", "AKTYWNA", "alarm"), true);
  assert.equal(has(diffState(alarm, snapshot()), "OŚ X", "zwolniona", "info"), true);
});
test("cumulative errors are emitted only when newly introduced", () => {
  const a = snapshot({ errors: ["A"] });
  const b = snapshot({ errors: ["A", "B", "B"] });
  const output = diffState(a, b);
  assert.deepEqual(output.filter(e => e.source === "BŁĘDY CNC").map(e => e.text), ["B", "B"]);
  assert.equal(diffState(b, structuredClone(b)).length, 0);
});
test("volatile error channel: reappearance after clear is new", () => {
  const a = snapshot({ errors: ["Alarm 1"] });
  const b = snapshot();
  assert.equal(diffState(a, b).filter(e => e.source === "BŁĘDY CNC").length, 0);
  assert.equal(has(diffState(b, a), "BŁĘDY CNC", "Alarm 1", "alarm"), true);
});
test("identical repeated error across snapshots is not duplicated", () => {
  const a = snapshot({ errors: ["Alarm 1"] });
  assert.equal(diffState(a, snapshot({ errors: ["Alarm 1"] })).length, 0);
});
test("gateway error appears, changes and clears", () => {
  const failed = snapshot({ gateway_error: "I/O" });
  assert.equal(has(diffState(snapshot(), failed), "BRAMA", "I/O", "alarm"), true);
  assert.equal(has(diffState(failed, snapshot({ gateway_error: "timeout" })),
    "BRAMA", "timeout", "alarm"), true);
  assert.equal(has(diffState(failed, snapshot()), "BRAMA", "ustąpił", "info"), true);
});
test("pending jog stops detect appearance and clearing independent of order", () => {
  const wait = snapshot({ jog_stop_pending: ["Z", "X"] });
  assert.equal(has(diffState(snapshot(), wait), "JOG", "X, Z", "alarm"), true);
  assert.equal(diffState(wait, snapshot({ jog_stop_pending: ["X", "Z"] })).length, 0);
  assert.equal(has(diffState(wait, snapshot()), "JOG", "Brak oczekujących", "info"), true);
});
test("tool and program changes; null initial state; malformed input", () => {
  const changed = snapshot({ tool: 3, program: "new.ngc" });
  const output = diffState(snapshot(), changed);
  assert.equal(has(output, "NARZĘDZIE", "3", "info"), true);
  assert.equal(has(output, "PROGRAM", "new.ngc", "info"), true);
  assert.equal(diffState(null, changed).length > 0, true);
  assert.deepEqual(diffState(changed, null), []);
});
test("diffState does not mutate either snapshot", () => {
  const before = snapshot();
  const after = snapshot({ task_state: "estop" });
  Object.freeze(before); Object.freeze(after);
  const original = JSON.stringify(after);
  diffState(before, after);
  assert.equal(JSON.stringify(after), original);
});
