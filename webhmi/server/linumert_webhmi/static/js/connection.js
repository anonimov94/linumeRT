/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: ChatGPT
*/
"use strict";

export function createConnection(handlers) {
  let token = ""; // wyłącznie pamięć bieżącej karty; bez storage i URL
  let ws = null;
  let authenticated = false;
  let serial = 0;
  let openedAt = 0;
  const pending = new Map();
  // Sygnał życia karty dla watchdog HAL (brama z --hal): bez niego "heartbeat" gaśnie po 1 s.
  // Przeglądarka dławi zegary ukrytej karty; wtedy watchdog może otworzyć E-STOP (fail-safe).
  const ALIVE_MS = 250;
  let aliveTimer = null;
  function startAlive(socket) {
    stopAlive();
    aliveTimer = setInterval(() => {
      if (ws === socket && authenticated && socket.readyState === WebSocket.OPEN) {
        try { socket.send('{"alive":1}'); } catch (_) { /* zamknięcie obsłuży "close" */ }
      }
    }, ALIVE_MS);
  }
  function stopAlive() {
    if (aliveTimer !== null) clearInterval(aliveTimer);
    aliveTimer = null;
  }

  const ready = () => authenticated && ws !== null && ws.readyState === WebSocket.OPEN;
  const isOpening = () => ws !== null && ws.readyState < WebSocket.CLOSING;
  function publish(text, online = false) {
    handlers.onStatus(text, online);
  }
  function notifyDisconnect(message) {
    pending.clear();
    handlers.onDisconnect(message);
  }
  function send(command, onReply = null) {
    if (!ready()) return null;
    const id = ++serial;
    const payload = { id, ...command };
    try {
      ws.send(JSON.stringify(payload));
      pending.set(id, { cmd: command.cmd, onReply, sentAt: performance.now() });
      return id;
    } catch (_) {
      handlers.onError("Nie można wysłać " + command.cmd + " przez WebSocket");
      return null;
    }
  }
  function close(reason = "Rozłączono") {
    const old = ws;
    ws = null;
    authenticated = false;
    stopAlive();
    if (old && old.readyState < WebSocket.CLOSING) old.close(1000, "client disconnect");
    publish("ROZŁĄCZONO");
    notifyDisconnect(reason);
  }
  function connect(value = "") {
    if (isOpening()) return false;
    if (value) token = value;
    if (token.length < 16) {
      handlers.onError("Token musi mieć co najmniej 16 znaków.");
      return false;
    }
    const url = new URL("/ws", window.location.href);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    let next;
    try { next = new WebSocket(url.href); }
    catch (_) {
      handlers.onError("Nie udało się utworzyć połączenia WebSocket.");
      return false;
    }
    ws = next;
    authenticated = false;
    openedAt = Date.now();
    publish("ŁĄCZENIE");
    next.addEventListener("open", () => {
      if (ws !== next) return;
      next.send(JSON.stringify({ auth: token }));
    });
    next.addEventListener("message", (event) => {
      if (ws !== next) return;
      let data;
      try { data = JSON.parse(event.data); }
      catch (_) { handlers.onError("Brama wysłała niepoprawny JSON."); return; }
      if (data.type === "state") {
        if (!data.state || data.state.schema !== 1) {
          handlers.onError("Niezgodny schemat bramy (oczekiwano schema=1).");
          close("Nieobsługiwany schemat");
          return;
        }
        if (!authenticated) {
          authenticated = true;
          startAlive(next);
          publish("ONLINE", true);
        }
        handlers.onState(data.state, data.version);
        return;
      }
      if (data.type === "ack" || data.type === "error") {
        const entry = pending.get(data.id);
        if (entry) pending.delete(data.id);
        if (entry?.onReply) entry.onReply(data);
        handlers.onReply(data, entry?.cmd ?? null,
          entry ? Math.max(0, performance.now() - entry.sentAt) : null);
      }
    });
    next.addEventListener("close", (event) => {
      if (ws !== next) return;
      ws = null;
      authenticated = false;
      stopAlive();
      publish("ROZŁĄCZONO (" + event.code + ")");
      notifyDisconnect("Utrata WebSocket (" + event.code + ")");
    });
    next.addEventListener("error", () => {
      if (ws === next) handlers.onError("Błąd transportu WebSocket.");
    });
    return true;
  }
  return { connect, close, send, ready, isOpening, ageFromOpen: () => Date.now() - openedAt,
    hasToken: () => token.length >= 16 };
}
