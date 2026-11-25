/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
*/
import { mkdir } from "node:fs/promises";
import { chromium } from "playwright";

const token = process.env.LINUMERT_WEBHMI_TEST_TOKEN;
if (!token || token.length < 16) throw new Error("Brak tokenu startowego WebHMI");

const base = "http://127.0.0.1:8765";
const output = process.argv[2];
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: "chrome", headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 768 } });
  page.setDefaultTimeout(15000);
  const button = (command) => page.locator(`button[data-cmd="${command}"]`);
  const alarm = (code) => page.locator("#alarmRows").getByText(code, { exact: true });

  async function openProgram(name) {
    await page.locator("#programSelect").selectOption(name);
    await page.locator("#programOpen").click();
  }

  async function actualX() {
    const response = await page.request.get(base + "/api/state", {
      headers: { "X-Linumert-Token": token },
    });
    if (!response.ok()) throw new Error(`Odczyt stanu WebHMI: HTTP ${response.status()}`);
    const { state } = await response.json();
    return state.axes.find((axis) => axis.name === "X").position;
  }

  async function waitForX(target, { minimumTravel = false } = {}) {
    await page.waitForFunction(async ({ token, target, minimumTravel }) => {
      const response = await fetch("/api/state", { headers: { "X-Linumert-Token": token } });
      if (!response.ok) throw new Error(`Odczyt stanu WebHMI: HTTP ${response.status}`);
      const { state } = await response.json();
      const x = state.axes.find((axis) => axis.name === "X");
      return minimumTravel
        ? x.position > target && ["reading", "waiting"].includes(state.interp_state)
        : state.interp_state === "idle" && Math.abs(x.position - target) < 0.001;
    }, { token, target, minimumTravel }, { polling: 100 });
  }

  async function driveFault(action = "") {
    const response = await page.request.post("http://127.0.0.1:8080/api/faults/drive_fault" + action, {
      data: { drive: "drv_x" },
    });
    if (!response.ok()) throw new Error(`Plant: HTTP ${response.status()} dla awarii osi X (${action})`);
  }

  await page.goto(base + "/");
  await page.locator("#token").fill(token);
  await page.locator("#connect").click();
  await page.locator("#connectionStatus.online").waitFor();
  await page.locator("#alarmRows").getByText("E-1100", { exact: true }).waitFor();
  await page.locator("#alarmReset").dblclick();
  await page.locator('button[data-cmd="power_on"]').click();
  await page.locator('button[data-cmd="home"]').click();
  await page.locator("#programSelect").selectOption("webhmi-ci-m6.ngc", { timeout: 240000 });
  await page.locator("#programOpen").click();
  await page.locator('button[data-cmd="run"]').click();

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
  const initialX = await actualX();
  await button("run").click();
  await waitForX(initialX + 0.1, { minimumTravel: true });
  await driveFault();
  try {
    await alarm("E-4200").waitFor();
    for (const cmd of ["run", "resume"]) {
      await page.locator(`button[data-cmd="${cmd}"][disabled][title="Aktywna awaria napędu: X"]`).waitFor();
    }
    await page.locator("#interpState").filter({ hasText: /^idle$/ }).waitFor();
    if (await actualX() >= initialX + 80) throw new Error("Program osiągnął cel pomimo awarii osi X");
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
  const recoveryX = await actualX();
  await openProgram("webhmi-ci-recovery.ngc");
  await waitForX(recoveryX);
  await button("run").click();
  await waitForX(recoveryX + 1);
  await page.screenshot({ path: output + "/webhmi-drive-recovery-1920.png", fullPage: true });
} finally {
  await browser.close();
}
