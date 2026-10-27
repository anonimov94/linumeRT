/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: ChatGPT
*/
"use strict";

import { allowed } from "./interlocks.js";
import { createConnection } from "./connection.js";
import { createJog } from "./jog.js";
import { createDRO } from "./dro.js";
import { initScene } from "./scene.js";
import { diffState } from "./events.js";
import { createLog } from "./log.js";

const $ = (id) => document.getElementById(id);
const FRESH_MS = 500;
const LOST_MS = 2000;
const controls = [...document.querySelectorAll("[data-cmd], [data-mode]")];
let state = null;
let receivedAt = 0;
let version = -1;
let haveConnected = false;
let jog;
let dro;
const journal = createLog();
let stateReceipts = [];
let lastAckMs = null;
let telemetryWasFresh = false;
let previousLinkStatus = "";

function refreshDiagnostics() {
  const now = Date.now();
  stateReceipts = stateReceipts.filter((time) => now - time < 1000);
  journal.metrics(stateReceipts.length, age(), lastAckMs);
  journal.lamps(state, connection.ready(), fresh(), $("jogStatus").textContent);
}

function result(message, kind = "") {
  $("commandResult").textContent = message;
  $("commandResult").className = "command-result " + kind;
}
function banner(message) { $("banner").textContent = message; }
function age() { return receivedAt ? Math.max(0, Date.now() - receivedAt) : Infinity; }
function fresh() { return connection.ready() && age() <= FRESH_MS; }
function rights() {
  return allowed(state, { connected: connection.ready(), fresh: fresh() });
}
function access(key) {
  return rights()[key] ?? { ok: false, reason: "Polecenie nieobsługiwane" };
}
function setButton(button, rule) {
  button.disabled = !rule.ok;
  button.title = rule.ok ? "" : rule.reason;
  const hint = button.querySelector(".interlock-reason");
  if (hint) hint.textContent = rule.ok ? "" : rule.reason;
}
function updateControls() {
  const connected = connection.ready();
  const rules = rights();
  for (const button of controls) {
    const key = button.dataset.mode ? "mode:" + button.dataset.mode : button.dataset.cmd;
    setButton(button, rules[key]);
  }
  const mdi = rules.mdi;
  $("mdiText").disabled = $("mdiSend").disabled = !mdi.ok;
  $("mdiText").title = mdi.ok ? "" : mdi.reason;
  $("mdiSend").title = mdi.ok ? "" : mdi.reason;
  const mdiHint = $("mdiSend").querySelector(".interlock-reason");
  mdiHint.textContent = mdi.ok ? "" : mdi.reason;
  const jogRule = rules.jog;
  const jogOK = jogRule.ok && (jog.canStart() || jog.isActive());
  const jogReason = jogRule.ok ? (jog.canStart() || jog.isActive() ? "" : "Oczekiwanie na potwierdzenie JOG STOP") : jogRule.reason;
  dro.jogButtons(jogOK, jogReason);
  $("jogLockReason").textContent = jogReason;
  $("connect").disabled = connection.isOpening();
  $("disconnect").disabled = !connection.isOpening();
  $("connect").textContent = haveConnected && connection.hasToken() ? "Połącz ponownie" : "Połącz";
  dro.freshness(age(), connected);
  refreshDiagnostics();
}
function send(command, onReply = null) {
  const id = connection.send(command, onReply);
  if (id === null) result("Nie wysłano polecenia: brak aktywnego WebSocket.", "error");
  return id;
}
function execute(command) {
  const key = command.cmd === "mode" ? "mode:" + command.mode : command.cmd;
  const rule = access(key);
  if (!rule.ok) {
    result("Zablokowano " + key + ": " + rule.reason, "error");
    journal.add("warn", "BLOKADA", key + ": " + rule.reason);
    return;
  }
  // STOP i E-STOP wysyłamy bez opóźniania przez inne polecenia.
  if (command.cmd === "stop" || command.cmd === "estop") {
    send(command);
    jog.stop("Polecenie zatrzymania operatora");
    if (command.cmd === "stop") jog.retryStop();
  } else {
    jog.stop("Zmiana polecenia operatora");
    send(command);
  }
}
const connection = createConnection({
  onStatus(text, online) {
    $("connectionStatus").textContent = text;
    $("connectionStatus").className = "status-tag " + (online ? "online" : "offline");
    if (text !== previousLinkStatus) {
      if (online) journal.add("info", "ŁĄCZE", "Połączono i uwierzytelniono WebSocket");
      else if (text === "ŁĄCZENIE") journal.add("info", "ŁĄCZE", "Łączenie z bramą");
      previousLinkStatus = text;
    }
    updateControls();
  },
  onState(next, nextVersion) {
    journal.appendAll(diffState(state, next));
    state = next;
    receivedAt = Date.now();
    stateReceipts.push(receivedAt);
    if (!telemetryWasFresh) journal.add("info", "TELEMETRIA", "Dane aktualne");
    telemetryWasFresh = true;
    version = nextVersion;
    dro.render(state, version);
    jog.onState(state);
    updateControls();
    if (Array.isArray(state.jog_stop_pending) && state.jog_stop_pending.length) {
      banner("UWAGA: brama zgłasza zatrzymanie JOG oczekujące na potwierdzenie.");
    } else if (state.gateway_error) {
      banner("Błąd odczytu bramy. Sterowanie ruchem zablokowane.");
    } else {
      banner("Brama online. Panel WebHMI nie zastępuje sprzętowego E-STOP i watchdog HAL.");
    }
  },
  onReply(reply, command, latencyMs) {
    const cmd = command ?? "id=" + String(reply.id ?? "?");
    journal.add(reply.type === "error" ? "alarm" : "info", "POLECENIE",
      (reply.type === "error" ? "ERROR " : "ACK ") + cmd + " (#" + String(reply.id ?? "?") +
      ")" + (Number.isFinite(latencyMs) ? " " + Math.round(latencyMs) + " ms" : "") +
      (reply.type === "error" ? ": " + String(reply.message ?? "błąd") : ""));
    if (reply.type === "ack" && Number.isFinite(latencyMs)) lastAckMs = latencyMs;
    if (reply.type === "error") {
      const message = "ODRZUCONO [" + (command ?? reply.id ?? "?") + "]: " +
        String(reply.message ?? "Nieznany błąd");
      result(message, "error");
      banner(message);
      if (jog.isActive()) jog.stop("Odmowa bramy");
    } else if (command && command !== "jog") {
      result("POTWIERDZONO [" + command + "] ID " + reply.id, "ok");
    }
    updateControls();
  },
  onDisconnect(message) {
    journal.add("warn", "ŁĄCZE", "Rozłączono: " + message);
    telemetryWasFresh = false;
    receivedAt = 0;
    jog.onLost();
    result(message + " — sprawdź fizyczny stan maszyny.", "error");
    banner("BRAK POŁĄCZENIA. DRO NIEAKTUALNE. Nie potwierdzono stanu ruchu.");
    updateControls();
  },
  onError(message) {
    journal.add("alarm", "KLIENT", message);
    result(message, "error"); banner(message);
  },
});
jog = createJog({
  send,
  ready: () => connection.ready(),
  mayJog: (axis) => {
    const rule = access("jog");
    return rule.ok && Array.isArray(state?.axes) &&
      state.axes.some((a) => a.name === axis && !a.limit_hit);
  },
  onAlarm(message) {
    journal.add("alarm", "JOG", message);
    result("ALARM: " + message, "error"); banner("ALARM: " + message);
  },
  onEvent(level, source, text) { journal.add(level, source, text); },
  onChange() { updateControls(); },
});
dro = createDRO(jog, () => jog.stop("Zmiana konfiguracji osi"));

const mdiHint = document.createElement("span");
mdiHint.className = "interlock-reason";
mdiHint.setAttribute("aria-hidden", "true");
$("mdiSend").appendChild(mdiHint);
for (const button of controls) {
  const hint = document.createElement("span");
  hint.className = "interlock-reason";
  hint.setAttribute("aria-hidden", "true");
  button.appendChild(hint);
  button.addEventListener("click", () => {
    const command = button.dataset.mode
      ? { cmd: "mode", mode: button.dataset.mode }
      : { cmd: button.dataset.cmd };
    execute(command);
  });
}
$("connect").addEventListener("click", () => {
  const entered = $("token").value;
  if (connection.connect(entered)) {
    haveConnected = true;
    $("token").value = "";
  }
});
$("disconnect").addEventListener("click", () => {
  jog.stop("Rozłączenie na żądanie operatora");
  connection.close("Operator rozłączył panel");
});
$("token").addEventListener("keydown", (event) => {
  if (event.key === "Enter") { event.preventDefault(); $("connect").click(); }
});
$("mdiForm").addEventListener("submit", (event) => {
  event.preventDefault();
  if (!access("mdi").ok) {
    result("MDI: " + access("mdi").reason, "error");
    journal.add("warn", "BLOKADA", "MDI: " + access("mdi").reason);
    return;
  }
  const text = $("mdiText").value.trim();
  if (!text || text.length > 200 || /[\r\n\x00-\x1f]/.test(text)) {
    result("MDI: jedna niepusta linia, maks. 200 znaków.", "error");
    journal.add("warn", "BLOKADA", "MDI: niepoprawne polecenie");
    return;
  }
  jog.stop("Wysyłanie MDI");
  send({ cmd: "mdi", text });
});

const watch = setInterval(() => {
  const currentAge = age();
  if (connection.ready()) {
    if (currentAge > FRESH_MS && telemetryWasFresh) {
      telemetryWasFresh = false;
      journal.add("warn", "TELEMETRIA", "NIEAKTUALNE: " + Math.round(currentAge) + " ms");
    }
    if (currentAge > FRESH_MS) {
      jog.stop("Telemetria starsza niż 500 ms");
      banner("NIEAKTUALNA TELEMETRIA (" + Math.round(currentAge) + " ms). JOG ZABLOKOWANY.");
    }
    if (currentAge > LOST_MS) {
      jog.stop("Brak stanu dłużej niż 2 sekundy");
      connection.close("Brak telemetrii przez ponad 2 sekundy");
    }
  } else if (connection.isOpening() && connection.ageFromOpen() > LOST_MS) {
    connection.close("Brak pierwszego stanu bramy przez ponad 2 sekundy");
  }
  updateControls();
}, 100);

window.addEventListener("pagehide", () => {
  clearInterval(watch);
  jog.stop("Zamknięcie karty");
  connection.close("Zamknięcie karty");
});
initScene(() => state);
updateControls();
