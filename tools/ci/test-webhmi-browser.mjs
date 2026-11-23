/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
*/
import { mkdir } from "node:fs/promises";
import { chromium } from "playwright";

const token = process.env.LINUMERT_WEBHMI_TEST_TOKEN;
if (!token || token.length < 16) throw new Error("Brak tokenu startowego WebHMI");

const output = process.argv[2];
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: "chrome", headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 768 } });
  page.setDefaultTimeout(15000);
  await page.goto("http://127.0.0.1:8765/");
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
  await page.screenshot({ path: output + "/webhmi-m6-cancel-1920.png" });
} finally {
  await browser.close();
}
