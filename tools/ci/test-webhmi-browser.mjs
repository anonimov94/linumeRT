/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
*/
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { setTimeout as delay } from "node:timers/promises";
import { chromium } from "playwright";

const token = process.env.LINUMERT_WEBHMI_TEST_TOKEN;
if (!token || token.length < 16) throw new Error("Brak tokenu startowego WebHMI");

const base = "http://127.0.0.1:8765";
const output = process.argv[2];
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: "chrome", headless: true });
const steps = {};
const axis = (state, name) => state.axes.find((item) => item.name === name);
const commanded = (state, name, coordinate = "position") => {
  const reading = axis(state, name);
  return reading[coordinate] + reading.following_error;
};
const near = (actual, expected, tolerance = 0.001) => Math.abs(actual - expected) < tolerance;
const running = (state) => ["reading", "waiting"].includes(state.interp_state);
const idle = (state) => state.interp_state === "idle";
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 768 } });
  page.setDefaultTimeout(15000);
  const button = (command) => page.locator(`button[data-cmd="${command}"]`);
  const alarm = (code) => page.locator("#alarmRows").getByText(code, { exact: true });

  async function openProgram(name) {
    await page.locator("#programSelect").selectOption(name);
    await page.locator("#programOpen").click();
  }

  async function readState() {
    const response = await page.request.get(base + "/api/state", {
      headers: { "X-Linumert-Token": token },
      timeout: 5000,
    });
    try {
      if (!response.ok()) throw new Error(`Odczyt stanu WebHMI: HTTP ${response.status()}`);
      return (await response.json()).state;
    } finally {
      await response.dispose();
    }
  }

  async function waitState(label, predicate, timeout = 15000) {
    const end = performance.now() + timeout;
    let state;
    do {
      state = await readState();
      if (predicate(state)) return state;
      await delay(75);
    } while (performance.now() < end);
    throw new Error(`${label}: ${JSON.stringify(state)}`);
  }

  async function record(name, data = {}) {
    const { width, height } = page.viewportSize();
    const screenshot = `webhmi-g2-${name}-${width}.png`;
    await page.screenshot({ path: output + "/" + screenshot, fullPage: true });
    steps[name] = { viewport: [width, height], screenshot, ...data };
    console.log("G2", name, JSON.stringify(steps[name]));
  }

  async function waitForX(target, { minimumTravel = false } = {}) {
    return waitState(`X ${target} mm`, (state) => {
      const x = axis(state, "X").position;
      return minimumTravel ? running(state) && x > target : idle(state) && near(x, target);
    });
  }

  async function mode(name) {
    await page.locator(`button[data-mode="${name}"]`).click();
    await page.locator("#modeState").getByText(name.toUpperCase(), { exact: true }).waitFor();
  }

  async function mdi(text) {
    const field = page.locator("#mdiText");
    await field.fill(text);
    await field.press("Enter");
  }

  async function driveFault(action = "") {
    const response = await page.request.post("http://127.0.0.1:8080/api/faults/drive_fault" + action, {
      data: { drive: "drv_x" },
    });
    if (!response.ok()) throw new Error(`Plant: HTTP ${response.status()} dla awarii osi X (${action})`);
  }

  await page.goto(base + "/");
  const language = page.locator("#operatorLanguage");
  await language.selectOption("en");
  const englishControls = page.getByRole("heading", { name: "Controls", exact: true });
  await englishControls.waitFor();
  await page.reload();
  await englishControls.waitFor();
  assert.equal(await language.inputValue(), "en");
  await record("00-language-en");
  await language.selectOption("pl");
  await page.getByRole("heading", { name: "Sterowanie", exact: true }).waitFor();
  await page.locator("#token").fill(token);
  await page.locator("#token").press("Enter");
  await page.locator("#connectionStatus.online").waitFor();
  const reset = page.locator("#alarmReset");
  const task = page.locator("#taskState");
  await alarm("E-1100").waitFor();
  assert.equal(await button("power_on").isDisabled(), true);
  await reset.dblclick();
  await button("power_on").click();
  await task.getByText("ON", { exact: true }).waitFor();
  await record("01-power");
  await button("home").click();
  await page.locator("#homingStatus").getByText("OSIE ZBAZOWANE", { exact: true })
    .waitFor({ timeout: 240000 });
  await record("02-home");
  await openProgram("webhmi-ci-m6.ngc");
  await button("run").click();

  await page.locator("#manualToolChange").getByText(/narzędzie T1 i potwierdź/).waitFor();
  await page.locator("#manualToolChange").scrollIntoViewIfNeeded();
  await page.screenshot({ path: output + "/webhmi-m6-1280.png" });
  await page.locator("#manualToolConfirm").focus();
  await page.locator("#manualToolConfirm").press("Enter");

  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.locator("#manualToolChange").getByText(/narzędzie T2 i potwierdź/).waitFor();
  await page.locator("#manualToolCancel").click();
  await page.locator("#alarmRows").getByText("W-2130", { exact: true }).waitFor();
  await page.locator("#manualToolChange").waitFor({ state: "hidden" });
  await page.locator("#alarmRows").scrollIntoViewIfNeeded();
  await page.locator("#toolState").filter({ hasText: /^1$/ }).waitFor();
  await page.screenshot({ path: output + "/webhmi-m6-cancel-1920.png" });

  await openProgram("webhmi-ci-drive-fault.ngc");
  const initialX = axis(await readState(), "X").position;
  await button("run").click();
  await waitForX(initialX + 0.1, { minimumTravel: true });
  await driveFault();
  try {
    await alarm("E-4200").waitFor();
    for (const cmd of ["run", "resume"]) {
      await page.locator(`button[data-cmd="${cmd}"][disabled][title="Aktywna awaria napędu: X"]`).waitFor();
    }
    await page.locator("#interpState").filter({ hasText: /^idle$/ }).waitFor();
    assert.ok(axis(await readState(), "X").position < initialX + 80,
      "Program osiągnął cel pomimo awarii osi X");
    await page.locator("#alarmRows").scrollIntoViewIfNeeded();
    await page.screenshot({ path: output + "/webhmi-drive-fault-1920.png", fullPage: true });
  } finally {
    await driveFault("/clear");
  }

  await button("power_on").click();
  await page.locator("#taskState").filter({ hasText: /^ON$/ }).waitFor();
  await page.waitForFunction(async (token) => {
    const response = await fetch("/api/state", { headers: { "X-Linumert-Token": token } });
    const { state } = await response.json();
    return state.drive_fault_axes.length === 0;
  }, token, { polling: 100 });
  await page.locator("#alarmReset").click();
  await alarm("E-4200").waitFor({ state: "hidden" });
  const recoveryX = axis(await readState(), "X").position;
  await openProgram("webhmi-ci-recovery.ngc");
  await waitForX(recoveryX);
  await button("run").click();
  await waitForX(recoveryX + 1);
  await page.screenshot({ path: output + "/webhmi-drive-recovery-1920.png", fullPage: true });

  await page.setViewportSize({ width: 1280, height: 768 });
  await mode("mdi");
  await mdi("G21 G90 G94 G49 G54 G53 G0 Z-30");
  await waitState("MDI Z", (state) => idle(state) && near(commanded(state, "Z"), -30));
  await mdi("G53 G0 X150 Y599");
  const positioned = await waitState("MDI XY", (state) => idle(state)
    && near(commanded(state, "X"), 150) && near(commanded(state, "Y"), 599), 60000);
  await mode("manual");
  const yBefore = commanded(positioned, "Y");
  const targetY = yBefore + 1;
  await page.locator("#jogIncrement").selectOption("1");
  const jog = page.getByRole("button", { name: "Jog Y plus", exact: true });
  await jog.focus();
  await page.keyboard.down("Space");
  try {
    await waitState("Przyrost JOG Y", (state) => near(commanded(state, "Y"), targetY));
  } finally {
    await page.keyboard.up("Space");
  }
  const jogEnd = await waitState("Zwolnienie JOG Y", (state) => !state.jog_active.length
    && !state.jog_stop_pending.length && near(commanded(state, "Y"), targetY)
    && near(axis(state, "Y").position, targetY, 0.02));
  await record("03-jog", { yBefore, yAfter: commanded(jogEnd, "Y"), axis: axis(jogEnd, "Y") });

  await button("work_zero").filter({ hasText: "XYZ = 0" }).click();
  const zero = await waitState("Zero detalu G54", (state) => idle(state) && state.mode === "manual"
    && [..."XYZ"].every((name) => near(commanded(state, name, "work_position"), 0)));
  await record("04-work-zero", { workOffset: zero.work_offset, axes: zero.axes });

  await page.setViewportSize({ width: 1920, height: 1080 });
  const program = "linumert_g2_odbior.ngc";
  await openProgram(program);
  await page.locator("#programState").getByText(/linumert_g2_odbior\.ngc/).waitFor();
  await record("05-program");
  await button("run").click();
  await waitState("Początek frezowania", (state) => running(state) && axis(state, "X").work_position > 2);
  await button("pause").click();
  await page.locator("#interpState").getByText("paused", { exact: true }).waitFor();
  await record("06-paused");
  await button("resume").click();
  const bounds = { xMax: 0, yMax: 0, zMin: 0 };
  const completed = await waitState("Koniec kwadratu G2", (state) => {
    bounds.xMax = Math.max(bounds.xMax, axis(state, "X").work_position);
    bounds.yMax = Math.max(bounds.yMax, axis(state, "Y").work_position);
    bounds.zMin = Math.min(bounds.zMin, axis(state, "Z").work_position);
    return idle(state) && near(commanded(state, "Z", "work_position"), 5);
  }, 60000);
  assert.ok(near(bounds.xMax, 20, 0.05) && near(bounds.yMax, 20, 0.05)
    && near(bounds.zMin, -1, 0.05), JSON.stringify(bounds));
  assert.ok([..."XY"].every((name) => near(commanded(completed, name, "work_position"), 0)));
  assert.deepEqual(completed.alarms, []);
  await record("07-auto", { bounds, axesAtEnd: completed.axes });

  await mode("mdi");
  await mdi("G53 G0 Z-5");
  await waitState("Dojazd Z przed sondą", (state) => idle(state) && near(commanded(state, "Z"), -5));
  await mdi("G53 G0 X300 Y400");
  await waitState("Dojazd XY nad sondę", (state) => idle(state)
    && near(commanded(state, "X"), 300) && near(commanded(state, "Y"), 400));
  await page.locator("#probeDistance").fill("40");
  await page.locator("#probeValue").fill("5");
  await page.locator("#probeRun").click();
  const probed = await waitState("Sonda Z: odjazd i zapis G54", (state) => {
    const z = axis(state, "Z");
    return idle(state) && near(z.position - z.work_position, -35, 0.02)
      && near(z.work_position, 7, 0.02);
  }, 60000);
  assert.deepEqual(probed.alarms, []);
  await record("08-probe", { axis: axis(probed, "Z") });

  await mdi("G53 G0 X9999");
  for (const message of [/positive limit/i, /invalid params in linear command/i]) {
    await page.locator("#alarmRows li").filter({ hasText: message }).first().waitFor();
  }
  await record("09-limit");
  await reset.click();
  await alarm("E-1000").first().waitFor({ state: "hidden" });
  await button("estop").click();
  await alarm("E-1100").waitFor();
  // Keep the single Reset separate from the UI's 600 ms double-Reset gesture.
  await delay(650);
  await reset.click();
  const singleReset = page.locator("#commandResult").getByText(/POTWIERDZONO \[reset\]/);
  await singleReset.waitFor();
  assert.equal(await task.textContent(), "ESTOP");
  assert.equal(await button("power_on").isDisabled(), true);
  await record("10-estop");
  await delay(650);
  await reset.dblclick();
  await button("power_on").click();
  await task.getByText("ON", { exact: true }).waitFor();
  await reset.click();
  await alarm("E-1100").waitFor({ state: "hidden" });
  await record("11-reset");
} catch (error) {
  for (const page of browser.contexts()[0]?.pages() ?? []) {
    await page.screenshot({ path: output + "/webhmi-g2-failure.png", fullPage: true }).catch(() => {});
  }
  throw error;
} finally {
  await writeFile(output + "/webhmi-g2-steps.json",
    JSON.stringify({ sha: process.env.GITHUB_SHA ?? null, steps }, null, 2) + "\n");
  await browser.close();
}
