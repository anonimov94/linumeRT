/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: ChatGPT
*/
"use strict";

// Wartości enumeracji: core/linumert/cnc/model.py.
// Stan bramy: webhmi/server/linumert_webhmi/schema.py.
const deny = (reason) => ({ ok: false, reason });
const permit = () => ({ ok: true, reason: "" });

export function allowed(state, link, translate = (pl) => pl) {
  const connected = typeof link === "boolean" ? link : Boolean(link?.connected);
  const fresh = typeof link === "boolean" ? link : Boolean(link?.fresh);
  const stop = connected ? permit() : deny(translate("Brak połączenia z bramą", "No connection to the gateway"));
  const result = { estop: stop, stop, jog_stop: stop };
  const ruleKeys = [
    "power_on", "power_off", "home", "jog", "mdi", "run",
    "pause", "resume", "override", "mode:manual", "mode:mdi", "mode:auto",
    "work_zero", "open", "reset", "probe",
  ];
  const rejectAll = (reason) => {
    for (const key of ruleKeys) result[key] = deny(reason);
    return result;
  };
  if (!connected) return rejectAll(translate("Brak połączenia z bramą", "No connection to the gateway"));
  if (!fresh) return rejectAll(translate("Telemetria nieaktualna (> 500 ms)", "Telemetry is stale (> 500 ms)"));
  if (!state || state.schema !== 1) return rejectAll(translate("Brak poprawnej migawki stanu", "No valid machine state"));
  if (state.read_only === true) {
    for (const key of Object.keys(result)) result[key] = deny(translate("Przegląd raportów offline", "Offline report viewer"));
    return rejectAll(translate("Przegląd raportów offline", "Offline report viewer"));
  }
  if (state.gateway_error) return rejectAll(translate("Błąd odczytu stanu bramy", "Cannot read the gateway state"));
  const { task_state: task, mode, interp_state: interp } = state;
  const machineOn = task === "on";
  const idle = interp === "idle";
  const running = interp === "reading" || interp === "waiting";
  const paused = interp === "paused";
  const homed = state.all_homed === true;
  const program = typeof state.program === "string" && state.program.trim().length > 0;
  const common = !machineOn ? translate("Maszyna nie jest w stanie ON", "Machine is not powered on") : "";
  const needsIdle = translate("Interpreter nie jest w stanie IDLE", "Interpreter is not idle");
  const modeReason = (target) => translate("Wymagany tryb ", "Required mode: ") + target.toUpperCase();

  result.power_on = task === "estop_reset" || task === "off"
    ? permit() : deny(task === "estop"
      ? (state.hmi_hal === true ? translate("Najpierw podwójny Reset (potwierdzenie E-STOP)", "Press Reset twice to acknowledge E-STOP first")
        : translate("Najpierw sprzętowy reset E-STOP poza bramą", "Reset the hardware E-STOP outside the gateway first"))
      : translate("Zasilanie jest już włączone lub stan nieznany", "Power is already on or the power state is unknown"));
  result.power_off = machineOn ? permit() : deny(common);
  result.home = !machineOn ? deny(common) : mode !== "manual"
    ? deny(modeReason("manual")) : !idle ? deny(needsIdle) : permit();
  result.jog = !machineOn ? deny(common) : mode !== "manual"
    ? deny(modeReason("manual")) : !idle ? deny(needsIdle)
      : Array.isArray(state.jog_stop_pending) && state.jog_stop_pending.length
        ? deny(translate("Niepotwierdzone zatrzymanie JOG", "JOG stop is not confirmed")) : permit();
  result.mdi = !machineOn ? deny(common) : mode !== "mdi"
    ? deny(modeReason("mdi")) : !idle ? deny(needsIdle) : permit();
  result.run = !machineOn ? deny(common) : mode !== "auto"
    ? deny(modeReason("auto")) : !idle ? deny(needsIdle)
      : !homed ? deny(translate("Wymagane bazowanie wszystkich osi", "Home all axes first"))
        : !program ? deny(translate("Nie wybrano programu", "Select a program first")) : permit();
  result.pause = !machineOn ? deny(common) : running ? permit()
    : deny(translate("Brak wykonywanego programu", "No program is running"));
  result.resume = !machineOn ? deny(common) : paused ? permit()
    : deny(translate("Program nie jest wstrzymany", "Program is not paused"));
  if (state.execution && state.execution.can_start !== true) {
    result.run = deny(state.execution.reason || translate("Instancja zadania niegotowa", "Job instance is not ready"));
  }
  if (state.execution && state.execution.can_resume !== true) {
    result.resume = deny(state.execution.resume_reason ||
      translate("Zadanie nie ma potwierdzonego stanu do wznowienia", "Job has no confirmed state to resume"));
  }
  if (Array.isArray(state.drive_fault_axes) && state.drive_fault_axes.length) {
    result.run = result.resume = deny(translate("Aktywna awaria napędu: ", "Active drive fault: ") + state.drive_fault_axes.join(", "));
  }
  result.override = machineOn ? permit() : deny(common);
  const jogging = Array.isArray(state.jog_active) && state.jog_active.length > 0;
  const pendingStop = Array.isArray(state.jog_stop_pending) && state.jog_stop_pending.length > 0;
  result.work_zero = !machineOn ? deny(common) : mode !== "manual"
    ? deny(modeReason("manual")) : !idle ? deny(needsIdle)
      : !homed ? deny(translate("Wymagane bazowanie wszystkich osi", "Home all axes first"))
        : pendingStop ? deny(translate("Niepotwierdzone zatrzymanie JOG", "JOG stop is not confirmed"))
          : jogging ? deny(translate("Najpierw zatrzymaj JOG", "Stop JOG first")) : permit();
  // Sonda: makro przez MDI (przełącza tryb sama), więc tryb MANUAL albo MDI.
  result.probe = !machineOn ? deny(common) : mode === "auto" ? deny(translate("Sonda w trybie AUTO niedostępna", "Probing is unavailable in AUTO mode"))
    : !idle ? deny(needsIdle) : !homed ? deny(translate("Wymagane bazowanie wszystkich osi", "Home all axes first"))
      : pendingStop ? deny(translate("Niepotwierdzone zatrzymanie JOG", "JOG stop is not confirmed"))
        : jogging ? deny(translate("Najpierw zatrzymaj JOG", "Stop JOG first")) : permit();
  const programs = Array.isArray(state.programs) ? state.programs : [];
  result.open = !machineOn ? deny(common) : !idle ? deny(needsIdle)
    : !homed ? deny(translate("Wymagane bazowanie wszystkich osi", "Home all axes first"))
      : pendingStop ? deny(translate("Niepotwierdzone zatrzymanie JOG", "JOG stop is not confirmed"))
        : !programs.length ? deny(translate("Brak plików w katalogu programów", "No files in the program directory")) : permit();
  const alarms = Array.isArray(state.alarms) ? state.alarms : [];
  result.reset = alarms.length ? permit() : deny(translate("Brak aktywnych alarmów", "No active alarms"));

  for (const target of ["manual", "mdi", "auto"]) {
    const key = "mode:" + target;
    result[key] = !machineOn ? deny(common) : !idle ? deny(needsIdle)
      : target !== "manual" && !homed ? deny(translate("Wymagane bazowanie wszystkich osi", "Home all axes first"))
        : mode === target ? deny(translate("Tryb " + target.toUpperCase() + " już aktywny", target.toUpperCase() + " mode is already active"))
          : permit();
  }
  return result;
}
