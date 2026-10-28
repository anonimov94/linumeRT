/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: ChatGPT
Incremental jog: Model-Author: Codex
Focused keyboard jog: Model-Author: Codex
*/
"use strict";

const INTERVAL_MS = 150;
const ROTARY = new Set(["A", "B", "C"]);
const AXES = new Set(["X", "Y", "Z", "A", "B", "C", "U", "V", "W"]);

export function createJog({ send, ready, mayJog, onAlarm, onChange, onEvent = () => {} }) {
  const status = document.getElementById("jogStatus");
  const slider = document.getElementById("jogSpeed");
  const label = document.getElementById("jogSpeedValue");
  const increment = document.getElementById("jogIncrement");
  const incrementUnit = document.getElementById("jogIncrementUnit");
  const choices = new Set(["continuous", "0.001", "0.01", "0.1", "1"]);
  let active = null;
  let timer = null;
  let phase = "idle"; // idle / moving / stopping / fault
  let reason = "";
  let stopPending = false;
  let stopAcked = false;

  function indicate(text, next) {
    phase = next;
    status.textContent = text;
    status.title = reason;
    onChange();
  }
  function unit(axis) { return ROTARY.has(axis) ? "deg/s" : "mm/s"; }
  function units(axis = "X") {
    label.textContent = Number(slider.value).toFixed(1) + " " + unit(axis);
    slider.title = "Prędkość dla osi " + axis + " w " + unit(axis);
    incrementUnit.textContent = ROTARY.has(axis) ? "deg" : "mm";
  }
  function clearTimer() {
    if (timer !== null) clearInterval(timer);
    timer = null;
  }
  function stop(why = "Zatrzymywanie jogu") {
    if (!active) return;
    const axis = active.axis;
    active = null;
    clearTimer();
    reason = why;
    onEvent("warn", "JOG", "Żądanie STOP dla osi " + axis + " — " + why);
    stopAcked = false;
    indicate("JOG: ZATRZYMYWANIE…", "stopping");
    const id = send({ cmd: "jog_stop", axis }, (reply) => {
      if (reply.type === "error") {
        fault("Niepotwierdzony JOG STOP: " + String(reply.message || "błąd bramy"));
      } else {
        stopAcked = true;
        if (!stopPending) {
          reason = "";
          indicate("JOG: BEZ RUCHU", "idle");
        }
      }
    });
    if (id === null) fault("JOG STOP nie został wysłany — brak łączności.");
  }
  function fault(message) {
    clearTimer();
    active = null;
    reason = message;
    indicate("JOG: STOP NIEPOTWIERDZONY", "fault");
    onAlarm(message);
  }
  function retryStop() {
    if (phase !== "fault" || !ready()) return;
    reason = "Ponawianie zatrzymania jogu";
    onEvent("warn", "JOG", "Ponowne żądanie JOG STOP");
    stopAcked = false;
    indicate("JOG: ZATRZYMYWANIE…", "stopping");
    const id = send({ cmd: "jog_stop" }, (reply) => {
      if (reply.type === "error") fault("JOG STOP nadal niepotwierdzony: " + String(reply.message));
      else {
        stopAcked = true;
        if (!stopPending) { reason = ""; indicate("JOG: BEZ RUCHU", "idle"); }
      }
    });
    if (id === null) fault("Nie można ponowić JOG STOP.");
  }
  function start(event, axis, direction, keyboard = false) {
    if (!AXES.has(axis) || (!keyboard && (!event.isPrimary || event.button !== 0))) return;
    if (phase !== "idle" || !ready() || !mayJog(axis)) return;
    const magnitude = Number(slider.value);
    if (!Number.isFinite(magnitude) || magnitude <= 0 || magnitude > 50) return;
    const selected = increment.value;
    if (!choices.has(selected)) return;
    const distance = selected === "continuous" ? null : Number(selected);
    event.preventDefault();
    active = { axis, pointerId: keyboard ? null : event.pointerId,
      key: keyboard ? event.key : null, node: event.currentTarget,
      speed: direction * magnitude, distance, sent: false };
    reason = "";
    indicate("JOG: " + axis + " " + (direction > 0 ? "+" : "−"), "moving");
    units(axis);
    if (!keyboard) {
      try { event.currentTarget.setPointerCapture(event.pointerId); }
      catch (_) { stop("Utrata przechwycenia wskaźnika"); return; }
    }
    function pulse() {
      if (!active) return;
      if (!ready() || !mayJog(axis) || document.hidden || !document.hasFocus()) {
        stop("Utrata warunków bezpiecznego JOG"); return;
      }
      const command = active.distance === null
        ? { cmd: "jog", axis, speed: active.speed }
        : active.sent ? { cmd: "jog_keepalive", axis }
          : { cmd: "jog_increment", axis, speed: active.speed, distance: active.distance };
      active.sent = true;
      const id = send(command, (reply) => {
        if (reply.type === "error" && phase === "moving") {
          onAlarm("Odrzucono JOG: " + String(reply.message || "błąd"));
          stop("Brama odrzuciła JOG");
        }
      });
      if (id === null) stop("Błąd wysyłania JOG");
    }
    pulse();
    if (active && timer === null) {
      onEvent("info", "JOG", "START " + axis + " " +
        (direction > 0 ? "+" : "−") + " " + magnitude + " " + unit(axis) +
        (distance === null ? " · ciągły" : " · krok " + distance + " " + incrementUnit.textContent));
      timer = setInterval(pulse, INTERVAL_MS);
    }
  }
  function button(axis, direction) {
    const node = document.createElement("button");
    node.type = "button";
    node.className = "jog-button";
    node.textContent = direction < 0 ? "−" : "+";
    node.disabled = true;
    node.setAttribute("aria-label", "Jog " + axis + " " + (direction < 0 ? "minus" : "plus"));
    node.setAttribute("aria-keyshortcuts", "Space Enter");
    node.addEventListener("pointerdown", (event) => start(event, axis, direction));
    for (const eventName of ["pointerup", "pointercancel", "lostpointercapture"]) {
      node.addEventListener(eventName, (event) => {
        if (active && active.key === null && active.pointerId === event.pointerId) {
          stop("Zwolnienie przycisku JOG");
        }
      });
    }
    // Only the focused JOG button handles keys; typing in a field never starts movement.
    node.addEventListener("keydown", (event) => {
      if (event.key !== " " && event.key !== "Enter") return;
      event.preventDefault();
      if (event.repeat || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      if (!node.disabled) start(event, axis, direction, true);
    });
    node.addEventListener("keyup", (event) => {
      if (event.key !== " " && event.key !== "Enter") return;
      event.preventDefault();
      if (active && active.node === node && active.key === event.key) {
        stop("Zwolnienie klawisza JOG");
      }
    });
    node.addEventListener("blur", () => {
      if (active && active.node === node && active.key !== null) stop("Utrata fokusu przycisku JOG");
    });
    node.addEventListener("pointerenter", () => { if (!active) units(axis); });
    node.addEventListener("focus", () => { if (!active) units(axis); });
    return node;
  }
  function onState(state) {
    stopPending = Array.isArray(state?.jog_stop_pending) && state.jog_stop_pending.length > 0;
    if (stopPending) {
      if (phase === "idle") fault("Brama zgłasza niepotwierdzony stop jogu.");
      else if (phase === "stopping") status.textContent = "JOG: ZATRZYMYWANIE…";
    }
    if (phase === "stopping" && stopAcked && !stopPending) {
      reason = "";
      indicate("JOG: BEZ RUCHU", "idle");
    }
    if (active && (!mayJog(active.axis) || !ready())) stop("Zmiana stanu maszyny");
  }
  function onLost() {
    if (active || phase === "stopping") {
      clearTimer();
      active = null;
      fault("Połączenie utracone przed potwierdzeniem zatrzymania JOG.");
    }
  }
  function canStart() { return phase === "idle"; }
  function isActive() { return Boolean(active); }
  slider.addEventListener("input", () => {
    units(active?.axis || "X");
    if (active) stop("Zmiana prędkości podczas JOG");
  });
  increment.addEventListener("change", () => {
    if (active) stop("Zmiana przyrostu podczas JOG");
    onChange();
  });
  window.addEventListener("blur", () => stop("Utrata fokusu okna"));
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop("Ukrycie karty");
  });
  window.addEventListener("pagehide", () => stop("Zamknięcie karty"));
  units();
  return { button, start, stop, retryStop, onState, onLost, canStart, isActive, units };
}
