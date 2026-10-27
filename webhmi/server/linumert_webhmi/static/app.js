/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: ChatGPT
*/
"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const SCHEMA = 1;
  const JOG_INTERVAL_MS = 150;
  const socket = { ws: null, authenticated: false, sequence: 0, activeJog: null,
                   jogTimer: null, lastState: null, reconnecting: false };
  const pending = new Map();
  const axisNames = new Set(["X", "Y", "Z", "A", "B", "C", "U", "V", "W"]);
  const readout = new Map();
  const controls = [...document.querySelectorAll("[data-cmd], [data-mode]")];
  const fmt = (number, places = 3) => Number.isFinite(Number(number)) && number != null
    ? Number(number).toFixed(places) : "—";
  const plain = (value) => value == null || value === "" ? "—" : String(value);
  const percentage = (value) => value == null ? "—" : fmt(value * 100, 0) + "%";

  function status(message, online = false) {
    $("connectionStatus").textContent = message;
    $("connectionStatus").className = "status-tag " + (online ? "online" : "offline");
  }
  function result(message, kind = "") {
    $("commandResult").textContent = message;
    $("commandResult").className = "command-result " + kind;
  }
  function showBanner(message) { $("banner").textContent = message; }
  function isReady() {
    return socket.authenticated && socket.ws && socket.ws.readyState === WebSocket.OPEN;
  }
  function setControls() {
    const ready = Boolean(isReady());
    controls.forEach((button) => { button.disabled = !ready; });
    $("mdiText").disabled = !ready;
    $("mdiSend").disabled = !ready;
    $("connect").disabled = Boolean(socket.ws && socket.ws.readyState < WebSocket.CLOSING);
    $("disconnect").disabled = !socket.ws || socket.ws.readyState >= WebSocket.CLOSING;
    document.querySelectorAll(".jog-button").forEach((button) => { button.disabled = !ready; });
  }
  function send(command, notify = true) {
    if (!isReady()) {
      if (notify) result("Brak uwierzytelnionego połączenia.", "error");
      return false;
    }
    const id = ++socket.sequence;
    try {
      socket.ws.send(JSON.stringify({ id, ...command }));
      if (notify) pending.set(id, command.cmd);
      return true;
    } catch (_) {
      if (notify) result("Nie udało się wysłać polecenia.", "error");
      stopJog();
      return false;
    }
  }
  function stopJog() {
    const jog = socket.activeJog;
    socket.activeJog = null;
    if (socket.jogTimer !== null) {
      clearInterval(socket.jogTimer);
      socket.jogTimer = null;
    }
    $("jogStatus").textContent = "JOG: BEZ RUCHU";
    if (jog && isReady()) {
      // Dwa niezależne warianty zatrzymania: stop osi i stop wszystkich jogów.
      send({ cmd: "jog_stop", axis: jog.axis }, true);
    }
  }
  function startJog(event, axis, direction) {
    if (!isReady() || !axisNames.has(axis) || !event.isPrimary || event.button !== 0) return;
    event.preventDefault();
    if (socket.activeJog) stopJog();
    const speed = Number($("jogSpeed").value) * direction;
    if (!Number.isFinite(speed) || speed === 0) return;
    socket.activeJog = { axis, pointerId: event.pointerId, speed };
    event.currentTarget.setPointerCapture(event.pointerId);
    $("jogStatus").textContent = "JOG: " + axis + " " + (direction > 0 ? "+" : "−");
    send({ cmd: "jog", axis, speed }, false);
    socket.jogTimer = setInterval(() => {
      if (!isReady() || document.hidden || !document.hasFocus()) {
        stopJog();
      } else if (socket.activeJog) {
        send({ cmd: "jog", axis: socket.activeJog.axis, speed: socket.activeJog.speed }, false);
      }
    }, JOG_INTERVAL_MS);
  }
  function createJogButton(axis, direction) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "jog-button";
    button.textContent = direction < 0 ? "−" : "+";
    button.setAttribute("aria-label", "Jog " + axis + " " + (direction < 0 ? "minus" : "plus"));
    button.disabled = !isReady();
    button.addEventListener("pointerdown", (event) => startJog(event, axis, direction));
    for (const name of ["pointerup", "pointercancel", "lostpointercapture"]) {
      button.addEventListener(name, (event) => {
        if (socket.activeJog && socket.activeJog.pointerId === event.pointerId) stopJog();
      });
    }
    return button;
  }
  function buildAxes(axes) {
    if (!Array.isArray(axes)) return;
    const names = axes.filter((a) => a && axisNames.has(a.name)).map((a) => a.name);
    if (names.join(",") === [...readout.keys()].join(",")) return;
    stopJog();
    readout.clear();
    $("axisRows").replaceChildren();
    for (const axis of names) {
      const tr = document.createElement("tr");
      const cells = Array.from({ length: 5 }, () => document.createElement("td"));
      cells[0].className = "axis-badge";
      cells[0].textContent = axis;
      cells[1].className = "numeric";
      cells[2].className = "numeric";
      for (const cell of cells) tr.appendChild(cell);
      const minus = document.createElement("td");
      const plus = document.createElement("td");
      minus.appendChild(createJogButton(axis, -1));
      plus.appendChild(createJogButton(axis, 1));
      tr.append(minus, plus);
      $("axisRows").appendChild(tr);
      readout.set(axis, cells);
    }
    setControls();
  }
  function renderErrors(errors, gatewayError) {
    const list = $("errors");
    list.replaceChildren();
    const entries = Array.isArray(errors) ? errors.slice(-30).map(String) : [];
    if (gatewayError) entries.unshift("BRAMA: " + String(gatewayError));
    if (!entries.length) entries.push("Brak aktywnych błędów.");
    entries.forEach((entry) => {
      const item = document.createElement("li");
      item.textContent = entry;
      list.appendChild(item);
    });
  }
  function renderState(state, version) {
    if (!state || state.schema !== SCHEMA) {
      showBanner("Niezgodny schemat stanu. Wymagany schema = " + SCHEMA + ". Sterowanie zablokowane.");
      stopJog();
      socket.authenticated = false;
      socket.ws?.close(1000, "schema mismatch");
      setControls();
      return;
    }
    socket.lastState = state;
    buildAxes(state.axes);
    for (const axis of (state.axes || [])) {
      const cells = readout.get(axis.name);
      if (!cells) continue;
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
    $("feedOverride").textContent = percentage(state.feed_override);
    $("rapidOverride").textContent = percentage(state.rapid_override);
    $("spindleOverride").textContent = percentage(state.spindle_override);
    $("spindleState").textContent = fmt(state.spindle_speed, 0) + " rpm / " + plain(state.spindle_direction);
    $("toolState").textContent = plain(state.tool);
    $("programState").textContent = plain(state.program) + " / " + plain(state.line);
    $("schemaLabel").textContent = "SCHEMA " + state.schema;
    $("versionState").textContent = plain(version);
    const axes = Object.fromEntries((state.axes || []).filter(a => axisNames.has(a.name)).map(a => [a.name, a]));
    $("toolCoordinates").textContent = ["X", "Y", "Z"].map(a => a + " " + fmt(axes[a]?.work_position, 3)).join("  ·  ");
    renderErrors(state.errors, state.gateway_error);
    if (Array.isArray(state.jog_stop_pending) && state.jog_stop_pending.length) {
      showBanner("UWAGA: zatrzymanie jogu oczekuje na potwierdzenie bramy. Kontroluj maszynę.");
    }
  }
  function disconnect() {
    stopJog();
    socket.authenticated = false;
    const ws = socket.ws;
    socket.ws = null;
    if (ws && ws.readyState < WebSocket.CLOSING) ws.close(1000, "user disconnect");
    pending.clear();
    status("ROZŁĄCZONO");
    setControls();
  }
  function connect() {
    disconnect();
    const token = $("token").value;
    if (token.length < 16) {
      result("Token musi mieć przynajmniej 16 znaków.", "error");
      return;
    }
    // Token nie trafia do URI, localStorage ani logów.
    const address = new URL("/ws", window.location.href);
    address.protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(address.href);
    socket.ws = ws;
    status("ŁĄCZENIE");
    setControls();
    ws.addEventListener("open", () => {
      if (socket.ws !== ws) return;
      ws.send(JSON.stringify({ auth: token }));
      $("token").value = "";
    });
    ws.addEventListener("message", (event) => {
      if (socket.ws !== ws) return;
      let data;
      try { data = JSON.parse(event.data); } catch (_) {
        result("Odebrano niepoprawny JSON.", "error"); return;
      }
      if (data.type === "state") {
        if (!socket.authenticated) {
          if (!data.state || data.state.schema !== SCHEMA) {
            renderState(data.state, data.version); return;
          }
          socket.authenticated = true;
          status("ONLINE", true);
          showBanner("Brama online. WebHMI PoC nie zastępuje obwodu E-STOP ani watchdog HAL.");
          setControls();
        }
        renderState(data.state, data.version);
      } else if (data.type === "ack" || data.type === "error") {
        const cmd = pending.get(data.id);
        pending.delete(data.id);
        if (data.type === "error") {
          result("ODRZUCONO [" + plain(cmd || data.id) + "]: " + plain(data.message), "error");
          if (socket.activeJog) stopJog();
        } else if (cmd) {
          result("POTWIERDZONO [" + cmd + "] ID " + data.id, "ok");
        }
      }
    });
    ws.addEventListener("close", (event) => {
      if (socket.ws !== ws) return;
      stopJog(); // lokalny stop; rozłączenie sesji zatrzymuje jog również po stronie bramy
      socket.ws = null;
      socket.authenticated = false;
      pending.clear();
      status("ROZŁĄCZONO (" + event.code + ")");
      showBanner("Połączenie przerwane. Polecenia zablokowane. Zweryfikuj fizyczny stan maszyny.");
      setControls();
    });
    ws.addEventListener("error", () => result("Błąd transportu WebSocket.", "error"));
  }
  $("connect").addEventListener("click", connect);
  $("disconnect").addEventListener("click", disconnect);
  $("token").addEventListener("keydown", (event) => {
    if (event.key === "Enter") { event.preventDefault(); connect(); }
  });
  controls.forEach((button) => button.addEventListener("click", () => {
    stopJog();
    if (button.dataset.mode) send({ cmd: "mode", mode: button.dataset.mode });
    else send({ cmd: button.dataset.cmd });
  }));
  $("mdiForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const text = $("mdiText").value.trim();
    if (!text || text.length > 200 || /[\r\n\x00-\x1f]/.test(text)) {
      result("MDI: jedna niepusta linia, maks. 200 znaków.", "error"); return;
    }
    stopJog();
    send({ cmd: "mdi", text });
  });
  $("jogSpeed").addEventListener("input", () => {
    $("jogSpeedValue").textContent = fmt($("jogSpeed").value, 1) + " mm/s";
    if (socket.activeJog) stopJog();
  });
  window.addEventListener("blur", stopJog);
  document.addEventListener("visibilitychange", () => { if (document.hidden) stopJog(); });
  window.addEventListener("pagehide", () => { stopJog(); disconnect(); });

  // Minimalny renderer WebGL 1: kolorowe linie XYZ w widoku izometrycznym.
  const canvas = $("scene");
  const gl = canvas.getContext("webgl", { antialias: false, depth: false, alpha: false });
  if (!gl) { $("glMessage").hidden = false; return; }
  const vertexSource = `attribute vec3 aPosition; attribute vec3 aColor;
    uniform mat4 uMatrix; varying vec3 vColor;
    void main(){gl_Position=uMatrix*vec4(aPosition,1.0);vColor=aColor;gl_PointSize=9.0;}`;
  const fragmentSource = `precision mediump float; varying vec3 vColor;
    void main(){gl_FragColor=vec4(vColor,1.0);}`;
  function shader(type, source) {
    const s = gl.createShader(type);
    gl.shaderSource(s, source); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  }
  let program;
  try {
    program = gl.createProgram();
    gl.attachShader(program, shader(gl.VERTEX_SHADER, vertexSource));
    gl.attachShader(program, shader(gl.FRAGMENT_SHADER, fragmentSource));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
  } catch (_) { $("glMessage").hidden = false; return; }
  gl.useProgram(program);
  const positionAttr = gl.getAttribLocation(program, "aPosition");
  const colorAttr = gl.getAttribLocation(program, "aColor");
  const matrixUniform = gl.getUniformLocation(program, "uMatrix");
  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.enableVertexAttribArray(positionAttr);
  gl.enableVertexAttribArray(colorAttr);
  gl.vertexAttribPointer(positionAttr, 3, gl.FLOAT, false, 24, 0);
  gl.vertexAttribPointer(colorAttr, 3, gl.FLOAT, false, 24, 12);
  const vertices = [];
  const push = (a, b, color) => {
    vertices.push(...a, ...color, ...b, ...color);
  };
  for (let i = -10; i <= 10; ++i) {
    const v = i * 10;
    push([v,-100,0],[v,100,0],[.10,.31,.36]);
    push([-100,v,0],[100,v,0],[.10,.31,.36]);
  }
  push([-100,0,0],[100,0,0],[.18,.9,.9]);
  push([0,-100,0],[0,100,0],[.18,.9,.9]);
  push([0,0,0],[0,0,100],[.97,.73,.31]);
  const staticData = vertices.slice();
  // Widok izometryczny: X,Y -> ekran; Z pionowo, skalowanie współrzędnych.
  const projection = new Float32Array([
     .006,-.0035,0,0,
    -.006,-.0035,0,0,
     0,.009,0,0,
     0,-.08,0,1
  ]);
  function frame() {
    if (canvas.width === 0 || canvas.height === 0) return;
    const width = Math.min(canvas.clientWidth * Math.min(devicePixelRatio || 1, 2), 1600);
    const height = Math.min(canvas.clientHeight * Math.min(devicePixelRatio || 1, 2), 1000);
    if (canvas.width !== Math.floor(width) || canvas.height !== Math.floor(height)) {
      canvas.width = Math.floor(width); canvas.height = Math.floor(height);
    }
    const aspect = canvas.width / canvas.height;
    const matrix = projection.slice();
    matrix[0] /= Math.max(1, aspect); matrix[4] /= Math.max(1, aspect);
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(.025,.06,.09,1); gl.clear(gl.COLOR_BUFFER_BIT);
    gl.uniformMatrix4fv(matrixUniform, false, matrix);
    const axes = Object.fromEntries((socket.lastState?.axes || []).map(a => [a.name, a]));
    const coords = ["X","Y","Z"].map(a => Number(axes[a]?.work_position) || 0);
    const [x,y,z] = coords.map(v => Math.max(-100, Math.min(100, v)));
    const data = [...staticData];
    const marker = (a,b) => data.push(...a,1,.76,.27,...b,1,.76,.27);
    marker([x-4,y,z],[x+4,y,z]); marker([x,y-4,z],[x,y+4,z]);
    marker([x,y,z-4],[x,y,z+4]);
    marker([x,y,0],[x,y,z]);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(data), gl.DYNAMIC_DRAW);
    gl.drawArrays(gl.LINES, 0, data.length / 6);
  }
  let lastFrame = 0;
  function animate(timestamp) {
    if (timestamp - lastFrame >= 1000 / 30) {
      lastFrame = timestamp;
      if (!document.hidden) frame();
    }
    requestAnimationFrame(animate);
  }
  requestAnimationFrame(animate);
  setControls();
})();
