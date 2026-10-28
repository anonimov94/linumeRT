/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: ChatGPT
*/
import assert from "node:assert/strict";
import test from "node:test";
import { allowed } from "../../webhmi/server/linumert_webhmi/static/js/interlocks.js";

const state = (changes = {}) => ({
  schema: 1, task_state: "on", mode: "manual", interp_state: "idle",
  all_homed: true, program: "part.ngc", axes: [{ name: "X", homed: true }],
  jog_stop_pending: [], ...changes,
});
const link = { connected: true, fresh: true };
const can = (key, s = state(), l = link) => allowed(s, l)[key].ok;

test("STOP / ESTOP remain available with stale telemetry but not with lost link", () => {
  for (const key of ["stop", "estop", "jog_stop"]) {
    assert.equal(can(key, null, { connected: true, fresh: false }), true);
    assert.equal(can(key, null, { connected: false, fresh: false }), false);
  }
  assert.equal(can("jog", state(), { connected: true, fresh: false }), false);
});
test("unknown schema or gateway error blocks motion", () => {
  for (const invalid of [null, state({ schema: 2 }), state({ gateway_error: "bad read" })]) {
    assert.equal(can("jog", invalid), false);
    assert.equal(can("run", invalid), false);
    assert.equal(can("estop", invalid), true);
  }
});
test("power on only from OFF or ESTOP_RESET (not ESTOP)", () => {
  for (const task_state of ["off", "estop_reset"]) assert.equal(can("power_on", state({ task_state })), true);
  for (const task_state of ["on", "estop", "unknown"]) assert.equal(can("power_on", state({ task_state })), false);
  assert.equal(can("power_off", state({ task_state: "on" })), true);
  assert.equal(can("power_off", state({ task_state: "off" })), false);
});
test("MANUAL and idle required for home and jog", () => {
  assert.equal(can("home"), true);
  assert.equal(can("jog"), true);
  assert.equal(can("jog", state({ mode: "mdi" })), false);
  assert.equal(can("home", state({ mode: "auto" })), false);
  for (const interp_state of ["reading", "waiting", "paused"]) {
    assert.equal(can("home", state({ interp_state })), false);
    assert.equal(can("jog", state({ interp_state })), false);
  }
  assert.equal(can("jog", state({ jog_stop_pending: ["X"] })), false);
});
test("MDI only on+mdi+idle", () => {
  assert.equal(can("mdi", state({ mode: "mdi" })), true);
  assert.equal(can("mdi"), false);
  assert.equal(can("mdi", state({ mode: "mdi", interp_state: "reading" })), false);
  assert.equal(can("mdi", state({ mode: "mdi", task_state: "off" })), false);
});
test("RUN requires AUTO, homing, program and idle", () => {
  assert.equal(can("run", state({ mode: "auto" })), true);
  assert.equal(can("run"), false);
  assert.equal(can("run", state({ mode: "auto", all_homed: false })), false);
  assert.equal(can("run", state({ mode: "auto", program: "" })), false);
  assert.equal(can("run", state({ mode: "auto", interp_state: "paused" })), false);
});
test("PAUSE while READING or WAITING, RESUME when PAUSED", () => {
  assert.equal(can("pause", state({ interp_state: "reading" })), true);
  assert.equal(can("pause", state({ interp_state: "waiting" })), true);
  assert.equal(can("pause"), false);
  assert.equal(can("resume", state({ interp_state: "paused" })), true);
  assert.equal(can("resume", state({ interp_state: "reading" })), false);
});
test("mode switching requires ON, IDLE and homed for AUTO/MDI", () => {
  assert.equal(can("mode:mdi"), true);
  assert.equal(can("mode:auto"), true);
  assert.equal(can("mode:manual"), false);
  assert.equal(can("mode:manual", state({ mode: "auto", all_homed: false })), true);
  assert.equal(can("mode:auto", state({ all_homed: false })), false);
  assert.equal(can("mode:mdi", state({ interp_state: "reading" })), false);
});
test("every denial has an actionable textual reason", () => {
  for (const [key, rule] of Object.entries(allowed(state(), { connected: false, fresh: false }))) {
    assert.equal(rule.ok, false, key);
    assert.ok(rule.reason.length > 5, key);
  }
  assert.equal(allowed(state(), link).jog.reason, "");
});
