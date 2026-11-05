/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
*/
"use strict";

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
  let online = false;
  let available = false;
  let busy = false;
  let prepared = null;
  let jobId = null;
  let checked = null;
  let generation = 0;

  function controls() {
    $("jobFields").disabled = !online || !available || busy;
    $("jobDownload").disabled = !online || busy || !prepared;
    $("jobPreflightFields").disabled = !online || busy || !prepared;
    $("jobCheckDownload").disabled = !checked;
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
  return { setOnline(value) {
    online = value;
    controls();
    if (online) refresh();
    else { ++generation; available = false; controls(); }
  } };
}
