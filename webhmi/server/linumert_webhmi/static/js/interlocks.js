/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: ChatGPT
*/
"use strict";

// Wartości enumeracji: core/linumert/cnc/model.py.
// Stan bramy: webhmi/server/linumert_webhmi/schema.py.
const deny = (reason) => ({ ok: false, reason });
const permit = () => ({ ok: true, reason: "" });

export function allowed(state, link) {
  const connected = typeof link === "boolean" ? link : Boolean(link?.connected);
  const fresh = typeof link === "boolean" ? link : Boolean(link?.fresh);
  const stop = connected ? permit() : deny("Brak połączenia z bramą");
  const result = { estop: stop, stop, jog_stop: stop };
  const ruleKeys = [
    "power_on", "power_off", "home", "jog", "mdi", "run",
    "pause", "resume", "override", "mode:manual", "mode:mdi", "mode:auto",
  ];
  const rejectAll = (reason) => {
    for (const key of ruleKeys) result[key] = deny(reason);
    return result;
  };
  if (!connected) return rejectAll("Brak połączenia z bramą");
  if (!fresh) return rejectAll("Telemetria nieaktualna (> 500 ms)");
  if (!state || state.schema !== 1) return rejectAll("Brak poprawnej migawki stanu");
  if (state.gateway_error) return rejectAll("Błąd odczytu stanu bramy");
  const { task_state: task, mode, interp_state: interp } = state;
  const machineOn = task === "on";
  const idle = interp === "idle";
  const running = interp === "reading" || interp === "waiting";
  const paused = interp === "paused";
  const homed = state.all_homed === true;
  const program = typeof state.program === "string" && state.program.trim().length > 0;
  const common = !machineOn ? "Maszyna nie jest w stanie ON" : "";
  const needsIdle = "Interpreter nie jest w stanie IDLE";
  const modeReason = (target) => "Wymagany tryb " + target.toUpperCase();

  result.power_on = task === "estop_reset" || task === "off"
    ? permit() : deny(task === "estop" ? "Najpierw sprzętowy reset E-STOP poza bramą"
      : "Zasilanie jest już włączone lub stan nieznany");
  result.power_off = machineOn ? permit() : deny(common);
  result.home = !machineOn ? deny(common) : mode !== "manual"
    ? deny(modeReason("manual")) : !idle ? deny(needsIdle) : permit();
  result.jog = !machineOn ? deny(common) : mode !== "manual"
    ? deny(modeReason("manual")) : !idle ? deny(needsIdle)
      : Array.isArray(state.jog_stop_pending) && state.jog_stop_pending.length
        ? deny("Niepotwierdzone zatrzymanie JOG") : permit();
  result.mdi = !machineOn ? deny(common) : mode !== "mdi"
    ? deny(modeReason("mdi")) : !idle ? deny(needsIdle) : permit();
  result.run = !machineOn ? deny(common) : mode !== "auto"
    ? deny(modeReason("auto")) : !idle ? deny(needsIdle)
      : !homed ? deny("Wymagane bazowanie wszystkich osi")
        : !program ? deny("Nie wybrano programu") : permit();
  result.pause = !machineOn ? deny(common) : running ? permit()
    : deny("Brak wykonywanego programu");
  result.resume = !machineOn ? deny(common) : paused ? permit()
    : deny("Program nie jest wstrzymany");
  result.override = machineOn ? permit() : deny(common);

  for (const target of ["manual", "mdi", "auto"]) {
    const key = "mode:" + target;
    result[key] = !machineOn ? deny(common) : !idle ? deny(needsIdle)
      : target !== "manual" && !homed ? deny("Wymagane bazowanie wszystkich osi")
        : mode === target ? deny("Tryb " + target.toUpperCase() + " już aktywny")
          : permit();
  }
  return result;
}
