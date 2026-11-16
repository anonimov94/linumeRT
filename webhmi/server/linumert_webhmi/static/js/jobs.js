/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
*/
"use strict";

import { createRunPlots } from "./run_plot.js";

const labels = { machine_model: "Model maszyny", program_and_tools: "Program i narzędzia",
  units_and_setup: "Jednostki i ustawienie detalu", interpreter: "Interpreter LinuxCNC",
  motion_limits: "Limity ruchu", material: "Materiał", collisions: "Bryły i strefy",
  loads: "Obciążenia", execution: "Wykonanie",
  integrity: "Integralność pakietu" };
const verdicts = { passed: "Poprawne", pending: "Oczekuje na weryfikację",
  not_started: "Nie rozpoczęto", failed: "Odrzucone", unavailable: "Niedostępne",
  incomplete: "Kontrola nieukończona" };

export function createJobs(request) {
  const $ = (id) => document.getElementById(id);
  const plots = createRunPlots();
  let online = false;
  let available = false;
  let busy = false;
  let prepared = null;
  let jobId = null;
  let checked = null;
  let generation = 0;
  let runId = null, terminalRun = false, runReport = null, runReportRaw = "";
  let viewer = false, viewerLoaded = false;

  function controls() {
    $("jobRunReport").disabled = !online || !terminalRun || busy;
    $("jobReportFile").disabled = !online || busy;
    $("jobRunReportDownload").disabled = !runReport;
    $("jobFields").disabled = !online || !available || busy;
    $("jobDownload").disabled = !online || busy || !prepared;
    $("jobPreflightFields").disabled = !online || busy || !prepared;
    $("jobCheckDownload").disabled = !checked;
    $("jobExecutionFields").disabled = !online || busy || checked?.status !== "verified";
  }
  function status(text, error = false) {
    $("jobStatus").textContent = text;
    $("jobStatus").className = "job-status" + (error ? " error" : "");
  }
  async function response(path, options) {
    const result = await request(path, options);
    if (!result.ok) {
      const error = await result.json();
      throw new Error(typeof error.detail === "string" ? error.detail : "Niepoprawne dane zadania.");
    }
    return result;
  }
  function showChecks(id, checks) {
    $(id).replaceChildren();
    for (const [key, verdict] of Object.entries(checks)) {
      const row = document.createElement("div");
      const title = document.createElement("dt");
      const value = document.createElement("dd");
      title.textContent = labels[key] || key;
      value.textContent = verdicts[verdict] || verdict;
      row.append(title, value);
      $(id).appendChild(row);
    }
  }
  function download(blob, name) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function showReport(result, raw) {
      runReport = result;
      runReportRaw = raw;
      $("jobReportIdentity").textContent = "Przebieg " + result.run_id + " · " + result.target +
        " · zadanie " + result.job_id;
      const num = (v, digits = 4) => Number.isFinite(v) ? v.toFixed(digits) : "brak danych";
      const outcome = { completed_observed: "Program zakończony", aborted: "Przerwano przez Stop",
        estop: "Zatrzymanie E-STOP", client_lost: "Utrata klienta i E-STOP", fault: "Błąd przebiegu",
        start_timeout: "Timeout Start", resume_timeout: "Timeout wznowienia",
        settle_timeout: "Timeout ustalenia osi", unavailable: "Wynik niedostępny" };
      $("jobRunReportStatus").textContent = (outcome[result.execution_status] || "Wynik nieznany") +
        " · zapis " + (result.status === "incomplete" ? "niepełny" : "obserwacyjny") +
        " · czas " + num(result.time.elapsed_s, 2) + " s · pauza " +
        num(result.time.paused_observed_s, 2) + " s · bez pauz " +
        num(result.time.unpaused_elapsed_s, 2) + " s · dolna granica modelu " +
        num(result.time.predicted_lower_bound_s, 2) + " s. " +
        "Końcowe ustalenie < 0,001 mm: " +
        ({passed: "potwierdzone w trzech próbkach", failed: "próg przekroczony",
          unavailable: "brak potwierdzenia"}[result.positioning.status]) + ". " +
        "Maksima dotyczą całego zapisu NML. " + result.quality.issues.join("; ");
      $("jobRunMetrics").replaceChildren();
      for (const [axis, values] of Object.entries(result.axes)) {
        const row = document.createElement("div"), title = document.createElement("dt"),
          value = document.createElement("dd");
        title.textContent = "Oś " + axis + " · błąd zadana − rzeczywista [mm]";
        value.textContent = "max " + num(values.following_error.max_abs_mm) +
          " · RMS " + num(values.following_error.rms_mm) +
          " · końcowe 3 max " + num(result.positioning.last3_max_abs_mm?.[axis]);
        row.append(title, value); $("jobRunMetrics").append(row);
      }
      const joints = result.joint_following_error;
      $("jobReportJointStatus").textContent = joints?.status === "available"
        ? "Błąd nadążania przegubów: surowe ferror_current LinuxCNC [mm]."
        : "Surowy błąd nadążania przegubów: brak kompletnego kanału w tym zapisie.";
      for (const [joint, values] of Object.entries(joints?.joints || {})) {
        const row = document.createElement("div"), title = document.createElement("dt"),
          value = document.createElement("dd");
        title.textContent = "Przegub " + joint + " (" +
          (joints.joint_axes?.[joint] || "?") + ") · FERR [mm]";
        value.textContent = "max " + num(values.max_abs_mm) + " · RMS " + num(values.rms_mm) +
          " · końcowe 3 max " + num(joints.last3_max_abs_mm?.[joint]);
        row.append(title, value); $("jobRunMetrics").append(row);
      }
      showChecks("jobReportChecks", result.verification.checks);
      $("jobReportHash").textContent = "SHA-256 raportu: " + result.report_id +
        ". Sprawdzono spójność pliku; źródłowe archiwa są identyfikowane hashami w JSON.";
      plots.show(result);
  }
  $("jobRunReport").addEventListener("click", async () => {
    if (!online || !terminalRun || busy) return;
    busy = true; controls();
    try {
      const raw = await (await response("/api/execution/report")).text();
      const result = JSON.parse(raw);
      if (!viewer && result.run_id !== runId) return;
      showReport(result, raw);
    } catch (error) { $("jobRunReportStatus").textContent = error.message; }
    finally { busy = false; controls(); }
  });
  $("jobReportFile").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file || !online || busy) return;
    runReport = null; runReportRaw = "";
    plots.clear(); $("jobReportChecks").replaceChildren();
    $("jobReportIdentity").textContent = "Sprawdzanie raportu „" + file.name + "”…";
    $("jobRunMetrics").replaceChildren();
    busy = true; controls();
    try {
      if (file.size > 32 * 1024 * 1024) throw new Error("Raport przekracza limit 32 MiB.");
      const raw = await (await response("/api/reports/open", {method: "POST",
        headers: {"Content-Type": "application/json"}, body: await file.text()})).text();
      showReport(JSON.parse(raw), raw);
    } catch (error) { $("jobRunReportStatus").textContent = error.message; }
    finally { busy = false; controls(); event.target.value = ""; }
  });
  $("jobRunReportDownload").addEventListener("click", () => {
    if (runReport) download(new Blob([runReportRaw],
      {type: "application/json"}), "run-report-" + runReport.run_id + ".json");
  });
  async function refresh() {
    const current = ++generation;
    try {
      const context = await (await response("/api/jobs/context")).json();
      if (current !== generation || !online) return;
      available = context.available;
      $("jobContext").textContent = available
        ? "Aktywna maszyna: " + context.machine + " · Baza narzędzi: " + context.tools
        : context.reason;
      const selected = $("jobSource").value;
      $("jobSource").replaceChildren(new Option("— wybierz program —", ""));
      for (const name of context.programs || []) $("jobSource").add(new Option(name, name));
      $("jobSource").value = selected;
      if (available && !context.programs.length) status("Brak plików .lnx w katalogu źródeł.");
    } catch (error) {
      if (current === generation) { available = false; status(error.message, true); }
    }
    controls();
  }
  $("jobForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!online || !available || busy || !$("jobForm").reportValidity()) return;
    const origin = ["jobX", "jobY", "jobZ"].map((id) => Number($(id).value));
    if (!origin.every(Number.isFinite)) { status("Wpisz trzy skończone współrzędne.", true); return; }
    busy = true;
    prepared = null;
    jobId = null;
    checked = null;
    const current = generation;
    $("jobPreflightResult").hidden = true;
    $("jobResult").hidden = true;
    controls();
    status("Przygotowywanie pakietu…");
    try {
      const payload = { program: $("jobSource").value, name: $("jobName").value,
        origin, offset: $("jobOffset").value };
      const result = await (await response("/api/jobs/prepare", { method: "POST",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })).json();
      if (current !== generation || !online) return;
      prepared = result.name;
      jobId = result.manifest.job_id;
      $("jobCode").textContent = result.gcode;
      $("jobId").textContent = result.manifest.job_id;
      showChecks("jobChecks", result.report.checks);
      $("jobResult").hidden = false;
      status("Pakiet „" + result.name + "” przygotowany. Weryfikacja toru oczekuje.");
    } catch (error) { status(error.message, true); }
    finally { busy = false; controls(); }
  });
  $("jobPreflightForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!online || busy || !prepared || !$("jobPreflightForm").reportValidity()) return;
    const start_mm = ["jobStartX", "jobStartY", "jobStartZ"].map((id) => Number($(id).value));
    if (!start_mm.every(Number.isFinite)) return;
    const current = generation;
    busy = true;
    checked = null;
    $("jobPreflightResult").hidden = true;
    controls();
    status("Kontrola w interpreterze LinuxCNC…");
    try {
      const result = await (await response("/api/jobs/" + encodeURIComponent(prepared) + "/verify",
        { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ job_id: jobId, start_mm }) })).json();
      if (current !== generation || !online) return;
      checked = result;
      const summary = { verified: "Zadanie zweryfikowane offline.",
        partial: "Kontrola częściowa — pełna weryfikacja oczekuje.",
        rejected: "Zadanie odrzucone przez kontrolę.", unavailable: "Interpreter LinuxCNC niedostępny.",
        incomplete: "Kontrola przerwana — wynik niepełny." }[result.status] || "Wynik niepełny.";
      $("jobPreflightSummary").textContent = summary;
      const diagnostic = result.material_diagnostic;
      const executionNote = result.status === "verified"
        ? "Przed uruchomieniem trzeba powiązać pakiet z aktualną instancją maszyny. "
        : "Wynik częściowy nie dopuszcza wykonania. ";
      $("jobCheckScope").textContent = diagnostic
        ? "Dokładny tor LinuxCNC; diagnostyka materiału 2.5D i zadeklarowanych brył. " +
          "Usunięty materiał: " + diagnostic.removed_mm3.toFixed(1) + " mm³. " +
          "Czas ruchów od " + diagnostic.time_lower_bound_s.toFixed(1) + " s. " +
          executionNote + "Szczegóły i ograniczenia w raporcie JSON."
        : result.checks.motion_limits === "passed"
          ? "Limity osi sprawdzone na dokładnym torze LinuxCNC. Diagnostyka materiału nieukończona. Wynik częściowy nie dopuszcza wykonania."
          : "Materiał, kolizje i pełna precyzja toru oczekują. Wynik częściowy nie dopuszcza zadania do wykonania.";
      showChecks("jobPreflightChecks", result.checks);
      $("jobPreflightMessages").replaceChildren();
      for (const message of result.messages) {
        const item = document.createElement("li");
        item.textContent = message;
        $("jobPreflightMessages").appendChild(item);
      }
      $("jobPreflightResult").hidden = false;
      status(summary, !["partial", "verified"].includes(result.status));
    } catch (error) { status(error.message, true); }
    finally { busy = false; controls(); }
  });
  $("jobCheckDownload").addEventListener("click", () => {
    if (checked) download(new Blob([JSON.stringify(checked, null, 2) + "\n"],
      { type: "application/json" }), prepared + "-preflight.json");
  });
  $("jobExecutionDownload").addEventListener("click", async () => {
    if (!online || busy || !prepared || checked?.status !== "verified") return;
    busy = true;
    controls();
    const target = $("jobExecutionTarget").value;
    try {
      const result = await response("/api/jobs/" + encodeURIComponent(prepared) + "/execution-config",
        { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ job_id: jobId, verification_id: checked.report_id, target }) });
      download(await result.blob(), prepared + "-" + target + ".zip");
      status("Konfiguracja symulacji pobrana. Uruchomienie i powiązanie z maszyną to kolejny krok.");
    } catch (error) { status(error.message, true); }
    finally { busy = false; controls(); }
  });
  $("jobDownload").addEventListener("click", async () => {
    if (!prepared || busy || !online) return;
    busy = true;
    controls();
    try {
      const result = await response("/api/jobs/" + encodeURIComponent(prepared) + "/archive");
      download(await result.blob(), prepared + ".zip");
    } catch (error) { status(error.message, true); }
    finally { busy = false; controls(); }
  });
  controls();
  return { update(state) {
    viewer = state?.read_only === true;
    $("jobTitle").textContent = viewer ? "Raport zapisanego zadania" : "Przygotowanie zadania";
    $("jobPanelScope").textContent = viewer ? "ODCZYT BEZ KONTROLERA"
      : "PRZYGOTOWANIE / WERYFIKACJA OFFLINE";
    const instance = state?.execution;
    $("jobInstance").hidden = !instance;
    if (instance) {
      $("jobInstanceIdentity").textContent = "Zadanie " + instance.job_id + " · " + instance.target;
      $("jobInstanceStatus").textContent = instance.reason;
      const run = instance.run;
      if ((run?.run_id || null) !== runId) {
        runId = run?.run_id || null; runReport = null;
        $("jobRunReportStatus").textContent = ""; $("jobRunMetrics").replaceChildren();
        plots.clear();
      }
      terminalRun = !!run && ["completed_observed", "aborted", "estop", "fault", "start_timeout",
        "resume_timeout", "settle_timeout", "unavailable", "client_lost"].includes(run.phase);
      controls();
      const phases = { starting: "Uruchamianie", running: "Wykonywanie", paused: "Wstrzymano",
        settling: "Oczekiwanie na ustalenie osi",
        stopping: "Zatrzymywanie", completed_observed: "Interpreter zakończył program",
        aborted: "Przerwano przez Stop", estop: "Zatrzymanie E-STOP", fault: "Błąd przebiegu",
        client_lost: "Utrata klienta i zatrzymanie E-STOP",
        start_timeout: "Przekroczony czas startu", resume_timeout: "Przekroczony czas wznowienia",
        settle_timeout: "Przekroczony czas ustalenia osi",
        unavailable: "Zapis lub odczyt niepełny" };
      $("jobRunStatus").textContent = run
        ? (phases[run.phase] || run.phase) + " · " + run.elapsed_s.toFixed(1) +
          " s · linia " + run.line + " · próbek " + run.samples : "Jeszcze nie uruchomiono zadania.";
      $("jobInstanceChecks").replaceChildren();
      for (const check of Object.values(instance.checks || {})) {
        const row = document.createElement("div");
        const title = document.createElement("dt");
        const verdict = document.createElement("dd");
        title.textContent = check.reason;
        verdict.textContent = { passed: "Spełnione", failed: "Niespełnione",
          unavailable: "Brak odczytu" }[check.status] || check.status;
        row.append(title, verdict);
        $("jobInstanceChecks").appendChild(row);
      }
    }
    if (viewer) {
      terminalRun = true;
      if (online && !viewerLoaded) {
        viewerLoaded = true;
        controls(); $("jobRunReport").click();
      }
    } else if (!instance) terminalRun = false;
    controls();
  }, setOnline(value) {
    online = value;
    controls();
    if (online) refresh();
    else { ++generation; available = false; controls(); }
  } };
}
