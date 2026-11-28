/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
*/
import assert from "node:assert/strict";
import test from "node:test";
import { bindLanguage } from "../../webhmi/server/linumert_webhmi/static/js/language.js";

function interfaceWith(storage) {
  let change;
  const selector = { value: "", addEventListener: (event, handler) => { change = handler; } };
  const child = { textContent: "G54" };
  const label = { dataset: { en: "Axis positions " }, firstChild: { data: "Pozycje osi " }, child };
  const doc = {
    defaultView: { localStorage: storage },
    getElementById: () => selector,
    querySelectorAll: () => [label],
  };
  const language = bindLanguage(doc);
  return { label, selector, language, choose(value) { selector.value = value; change(); } };
}

test("labels switch in both directions and the live child stays in place", () => {
  const storage = new Map();
  const localStorage = { getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value) };
  const ui = interfaceWith(localStorage);
  assert.equal(ui.selector.value, "pl");
  ui.choose("en");
  assert.equal(ui.label.firstChild.data, "Axis positions ");
  assert.equal(ui.label.lang, "en");
  assert.equal(ui.label.child.textContent, "G54");
  assert.equal(ui.language.text("Połącz ponownie", "Reconnect"), "Reconnect");
  assert.equal(interfaceWith(localStorage).selector.value, "en");
  ui.choose("pl");
  assert.equal(ui.label.firstChild.data, "Pozycje osi ");
  assert.equal(ui.label.lang, "pl");
});

test("disabled storage still allows switching in the active page", () => {
  const denied = () => { throw new Error("storage denied"); };
  const ui = interfaceWith({ getItem: denied, setItem: denied });
  assert.equal(ui.selector.value, "pl");
  ui.choose("en");
  assert.equal(ui.label.firstChild.data, "Axis positions ");
  ui.choose("unsupported");
  assert.equal(ui.selector.value, "pl");
});

test("live messages refresh their text and language for the current choice", () => {
  const ui = interfaceWith({ getItem: () => "pl", setItem: () => {} });
  const message = { textContent: "", lang: "" };
  const render = () => ui.language.render(message, "Załóż narzędzie T1.", "Install tool T1.");
  render();
  assert.deepEqual(message, { textContent: "Załóż narzędzie T1.", lang: "pl" });
  ui.choose("en");
  render();
  assert.deepEqual(message, { textContent: "Install tool T1.", lang: "en" });
});
