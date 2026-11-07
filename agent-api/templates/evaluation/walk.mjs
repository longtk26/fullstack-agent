// Story 26.5: the evaluation's browser (from the business-value lab): one Playwright process driven with JSON lines
// on stdin, so a screen is captured at the exact moment of a workflow step (between two API calls). One browser
// context per signed-in user. Runs inside bga-runner-node (Chromium in /ms-playwright).
//
//   node walk.mjs [host]      host: what `localhost` means (host.docker.internal from a container)
//
// Commands (one JSON object per line), each answered by one JSON line on stdout:
//   {"cmd":"login","user":"<key>","url":"<sign-in page>","field":"email","login":"...","password":"...","file":"..."}
//   {"cmd":"shot","user":"<key>|null","url":"...","file":"/out/x.png"}
//   {"cmd":"quit"}
import { createInterface } from "node:readline";
import { chromium } from "playwright-core";

const host = process.argv[2];
const browser = await chromium.launch({
  args: host ? [`--host-resolver-rules=MAP localhost ${host}`] : [],
});
const contexts = new Map();

async function context(user) {
  const key = user || "anonymous";
  if (!contexts.has(key)) {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    // the screens as they are: the guided tour (Story 26.4) does not start on its own in this browser
    if (!process.env.BGA_TOUR) await ctx.addInitScript(() => { try { localStorage.setItem("bga-tour-off", "1"); } catch {} });
    contexts.set(key, ctx);
  }
  return contexts.get(key);
}

function watch(page) {
  const problems = [];
  page.on("pageerror", (error) => problems.push(`page error: ${error.message.slice(0, 200)}`));
  page.on("response", (response) => {
    if (response.status() >= 400 && response.request().resourceType() === "fetch" && !response.url().includes("/_next/")) {
      problems.push(`${response.request().method()} ${new URL(response.url()).pathname} → ${response.status()}`);
    }
  });
  return problems;
}

async function settle(page) {
  await page.waitForLoadState("networkidle", { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(800);
}

async function pageText(page) {
  return (await page.locator("body").innerText().catch(() => "")).replace(/\s+/g, " ").slice(0, 3000);
}

async function login(cmd) {
  const ctx = await context(cmd.user);
  const page = await ctx.newPage();
  const problems = watch(page);
  await page.goto(cmd.url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await settle(page);
  const field = page.locator(`input[name="${cmd.field}"], input[type="email"]`).first();
  await field.fill(cmd.login, { timeout: 15000 });
  await page.locator('input[type="password"]').first().fill(cmd.password);
  await page.locator('form button[type="submit"]').first().click();
  await page.waitForURL((url) => !url.toString().startsWith(cmd.url), { timeout: 20000 }).catch(() => {});
  await settle(page);
  const stillOnSignIn = await page.locator('input[type="password"]').count();
  if (cmd.wait) await page.waitForTimeout(cmd.wait);
  if (cmd.file) await page.screenshot({ path: cmd.file });
  const result = { ok: stillOnSignIn === 0, url: page.url(), problems, text: await pageText(page) };
  await page.close();
  return result;
}

async function shot(cmd) {
  const ctx = await context(cmd.user);
  const page = await ctx.newPage();
  const problems = watch(page);
  const response = await page.goto(cmd.url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await settle(page);
  if (cmd.wait) await page.waitForTimeout(cmd.wait);
  await page.screenshot({ path: cmd.file, fullPage: true });
  const result = { ok: true, status: response?.status() ?? null, url: page.url(), problems, text: await pageText(page) };
  await page.close();
  return result;
}

const rl = createInterface({ input: process.stdin });
for await (const line of rl) {
  if (!line.trim()) continue;
  let cmd;
  try {
    cmd = JSON.parse(line);
    if (cmd.cmd === "quit") break;
    const result = cmd.cmd === "login" ? await login(cmd) : await shot(cmd);
    process.stdout.write(JSON.stringify(result) + "\n");
  } catch (error) {
    process.stdout.write(JSON.stringify({ ok: false, error: String(error?.message || error).slice(0, 500) }) + "\n");
  }
}
await browser.close();
