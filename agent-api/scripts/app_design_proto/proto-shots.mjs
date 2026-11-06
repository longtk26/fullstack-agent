// Story 23.0 prototype only: first-screen screenshots of a built app on its mock API, per variant (today's kit,
// then each look of the brief), signed out or signed in as a role's demo user. Runs inside bga-runner-node from the
// project directory, after `pnpm build`.
//
//   node proto-shots.mjs <shots-dir> <shots.json>
//
// shots.json: [{"name": "home-glass-1440-light", "route": "/?look=glass", "width": 1440, "scheme": "light",
//               "role": "organizer"?}, ...]
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { chromium } from "@playwright/test";

const [shots = "shots", config = "shots.json"] = process.argv.slice(2);
const views = JSON.parse(readFileSync(config, "utf8"));
const app = JSON.parse(readFileSync("src/content/app.json", "utf8"));
const PORT = 3199;
const base = `http://127.0.0.1:${PORT}`;
mkdirSync(shots, { recursive: true });

const server = spawn("pnpm", ["exec", "next", "start", "-p", String(PORT), "-H", "127.0.0.1"], {
  stdio: "inherit",
  env: { ...process.env, MOCK_TEST_API: "true", API_BASE_URL: "" },
});

for (let attempt = 0; ; attempt += 1) {
  try {
    if ((await fetch(`${base}/api/runtime-config`)).ok) break;
  } catch {
    // not listening yet
  }
  if (attempt > 120) throw new Error("the app did not start");
  await new Promise((resolve) => setTimeout(resolve, 500));
}

async function signIn(page, role) {
  const auth = app.auth;
  const user = auth?.demoUsers?.find((u) => u.role === role);
  if (!user) throw new Error(`no demo user for role ${role}`);
  await page.goto(base + auth.signIn, { waitUntil: "networkidle" });
  await page.locator(`[id="auth_login-${auth.loginField}"]`).fill(user.login);
  await page.locator('[id="auth_login-password"]').fill(auth.password ?? "demo12345");
  await page.locator('form button[type="submit"]').click();
  await page.waitForURL((url) => url.pathname !== auth.signIn, { timeout: 15000 });
}

const browser = await chromium.launch();
const done = [];
const groups = new Map();
for (const view of views) groups.set(view.role ?? "", [...(groups.get(view.role ?? "") ?? []), view]);
try {
  for (const [role, group] of groups) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
    const page = await context.newPage();
    try {
      if (role) await signIn(page, role);
    } catch (error) {
      console.log(`sign-in as ${role} failed: ${error}`);
      await context.close();
      continue;
    }
    for (const view of group) {
      try {
        await page.setViewportSize({ width: view.width, height: view.width < 600 ? 812 : 900 });
        await page.emulateMedia({ colorScheme: view.scheme, reducedMotion: "reduce" });
        await page.goto(`${base}${view.route}`, { waitUntil: "networkidle" });
        await page.evaluate(() => document.fonts.ready);
        await page.waitForTimeout(role ? 1200 : 400);
        await page.waitForLoadState("networkidle").catch(() => {});
        await page.screenshot({ path: `${shots}/${view.name}.png`, fullPage: false });
        done.push(view.name);
      } catch (error) {
        console.log(`shot ${view.name} failed: ${error}`);
      }
    }
    await context.close();
  }
} finally {
  await browser.close();
  server.kill();
}
writeFileSync(`${shots}/shots.json`, JSON.stringify(done, null, 2));
console.log(`proto shots: ${done.length} of ${views.length} → ${shots}`);
