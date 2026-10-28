/* SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex */
import assert from "node:assert/strict";
import test from "node:test";
import { createJog } from "../../webhmi/server/linumert_webhmi/static/js/jog.js";

function element(value = "") {
  const listeners = new Map();
  return { value, textContent: "", title: "", disabled: false,
    addEventListener(name, handler) { listeners.set(name, handler); },
    emit(name, event = {}) { listeners.get(name)?.(event); },
    setPointerCapture() {}, setAttribute() {},
  };
}
function setup(increment = "0.1") {
  const nodes = Object.fromEntries(["jogStatus", "jogSpeed", "jogSpeedValue",
    "jogIncrement", "jogIncrementUnit"].map(id => [id, element()]));
  nodes.jogSpeed.value = "10";
  nodes.jogIncrement.value = increment;
  const document = element(), window = element(), timers = new Map();
  Object.assign(document, { hidden: false, hasFocus: () => true,
    getElementById: id => nodes[id], createElement: () => element() });
  globalThis.document = document;
  globalThis.window = window;
  globalThis.setInterval = callback => { timers.set(1, callback); return 1; };
  globalThis.clearInterval = id => timers.delete(id);
  const sent = [], alarms = [];
  const jog = createJog({ send(command, reply) {
    sent.push(command);
    if (command.cmd === "jog_stop") reply({ type: "ack" });
    return sent.length;
  }, ready: () => true, mayJog: () => true, onAlarm: message => alarms.push(message),
  onChange() {} });
  function press(axis = "X", direction = 1) {
    const button = jog.button(axis, direction);
    button.emit("pointerdown", { isPrimary: true, button: 0, pointerId: 7,
      currentTarget: button, preventDefault() {} });
    return button;
  }
  return { nodes, document, window, timers, sent, alarms, jog, press,
    tick: () => [...timers.values()].forEach(callback => callback()) };
}

test("holding increment dispatches once; keepalive cannot repeat the distance", () => {
  const h = setup(), button = h.press();
  h.tick(); h.tick(); h.tick();
  assert.deepEqual(h.sent, [{ cmd: "jog_increment", axis: "X", speed: 10, distance: 0.1 },
    ...Array.from({ length: 3 }, () => ({ cmd: "jog_keepalive", axis: "X" }))]);
  button.emit("pointerup", { pointerId: 7 });
  h.tick();
  assert.equal(h.sent.at(-1).cmd, "jog_stop");
  assert.equal(h.jog.canStart(), true);
  h.press();
  assert.equal(h.sent.filter(c => c.cmd === "jog_increment").length, 2);
});

test("continuous jog retains its repeated signed speed commands", () => {
  const h = setup("continuous"); h.press("Y", -1); h.tick();
  assert.deepEqual(h.sent, Array.from({ length: 2 }, () => ({ cmd: "jog", axis: "Y", speed: -10 })));
});

for (const loss of ["blur", "visibility", "pointercancel", "lostpointercapture", "increment change"]) {
  test("increment is stopped on " + loss, () => {
    const h = setup(), button = h.press();
    if (loss === "blur") h.window.emit("blur");
    else if (loss === "visibility") { h.document.hidden = true; h.document.emit("visibilitychange"); }
    else if (loss === "increment change") h.nodes.jogIncrement.emit("change");
    else button.emit(loss, { pointerId: 7 });
    h.tick();
    assert.deepEqual(h.sent.at(-1), { cmd: "jog_stop", axis: "X" });
    assert.equal(h.timers.size, 0);
  });
}

test("disconnect clears keepalive and blocks another increment until stop confirmation", () => {
  const h = setup(); h.press(); h.jog.onLost(); h.tick();
  assert.equal(h.timers.size, 0);
  assert.equal(h.jog.canStart(), false);
  h.press();
  assert.equal(h.sent.length, 1);
  assert.match(h.alarms[0], /utracone/);
});

test("rotary axis reports degrees and sends signed speed with positive distance", () => {
  const h = setup("0.001"); h.press("A", -1);
  assert.equal(h.nodes.jogIncrementUnit.textContent, "deg");
  assert.equal(h.nodes.jogSpeedValue.textContent, "10.0 deg/s");
  assert.deepEqual(h.sent[0], { cmd: "jog_increment", axis: "A", speed: -10, distance: 0.001 });
});

test("invalid increment or speed never dispatches movement", () => {
  for (const increment of ["NaN", "0", "-1", "100", "Infinity", ""]) {
    const h = setup(increment); h.press(); assert.deepEqual(h.sent, []);
  }
  for (const speed of ["NaN", "0", "-1", "51", "Infinity"]) {
    const h = setup(); h.nodes.jogSpeed.value = speed; h.press(); assert.deepEqual(h.sent, []);
  }
});

function key(button, name, value, extra = {}) {
  button.emit(name, { key: value, currentTarget: button, preventDefault() {}, ...extra });
}

for (const value of [" ", "Enter"]) {
  test("focused keyboard hold sends one increment and stops on release: " + value, () => {
    const h = setup(), button = h.jog.button("X", -1);
    button.disabled = false;
    key(button, "keydown", value);
    key(button, "keydown", value, { repeat: true });
    h.tick(); h.tick();
    assert.deepEqual(h.sent, [
      { cmd: "jog_increment", axis: "X", speed: -10, distance: 0.1 },
      { cmd: "jog_keepalive", axis: "X" }, { cmd: "jog_keepalive", axis: "X" },
    ]);
    key(button, "keyup", value);
    h.tick();
    assert.deepEqual(h.sent.at(-1), { cmd: "jog_stop", axis: "X" });
    assert.equal(h.timers.size, 0);
    assert.equal(h.jog.canStart(), true);
  });
}

test("keyboard continuous jog stops when Tab moves focus and repeat cannot restart it", () => {
  const h = setup("continuous"), button = h.jog.button("Y", 1);
  button.disabled = false;
  key(button, "keydown", " "); h.tick();
  button.emit("blur");
  key(button, "keydown", " ", { repeat: true }); h.tick();
  assert.deepEqual(h.sent.map(c => c.cmd), ["jog", "jog", "jog_stop"]);
  assert.equal(h.timers.size, 0);
});

test("disabled buttons, modifier chords and unrelated keys never start keyboard jog", () => {
  const h = setup(), button = h.jog.button("X", 1);
  key(button, "keydown", "Enter");
  button.disabled = false;
  for (const modifier of ["altKey", "ctrlKey", "metaKey", "shiftKey"]) {
    key(button, "keydown", "Enter", { [modifier]: true });
  }
  key(button, "keydown", "ArrowRight");
  key(button, "keydown", "Enter", { repeat: true });
  assert.deepEqual(h.sent, []);
});

test("release from a different key, button or pointer cannot own keyboard jog", () => {
  const h = setup(), button = h.jog.button("X", 1), other = h.jog.button("Y", 1);
  button.disabled = other.disabled = false;
  key(button, "keydown", " ");
  key(button, "keyup", "Enter");
  key(other, "keyup", " ");
  button.emit("pointerup", { pointerId: 7 });
  assert.equal(h.jog.isActive(), true);
  key(button, "keyup", " ");
  assert.equal(h.jog.isActive(), false);
});

for (const loss of ["blur", "visibility", "disconnect"]) {
  test("held keyboard jog clears its timer on " + loss, () => {
    const h = setup(), button = h.jog.button("Z", 1);
    button.disabled = false;
    key(button, "keydown", "Enter");
    if (loss === "blur") h.window.emit("blur");
    else if (loss === "visibility") { h.document.hidden = true; h.document.emit("visibilitychange"); }
    else h.jog.onLost();
    h.tick();
    assert.equal(h.timers.size, 0);
    assert.equal(h.jog.isActive(), false);
    if (loss === "disconnect") assert.equal(h.jog.canStart(), false);
    else assert.deepEqual(h.sent.at(-1), { cmd: "jog_stop", axis: "Z" });
  });
}
