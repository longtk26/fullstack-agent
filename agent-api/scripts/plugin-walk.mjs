// The plugin walk (Story 22.7): drives an app with sign-in, roles, rules, uploads, payments and links (the
// workshop-bookings example) through its plugins' screens in a real browser, on mocks or live, from its own
// `src/content/app.json`. Runs inside bga-runner-node against a running app.
//
//   node plugin-walk.mjs <base url> <app.json> [shots dir]
//
// Steps: sign up a new account (and see it in the top bar); sign out; a page behind sign-in sends to the sign-in page
// and back after it; as a member, no "New" and no "Edit" on what only organizers may do; a booking from a workshop's
// page (a full workshop is refused with its message); pay for it (the fake provider's page live) and see it paid; move
// its status; as an organizer, upload a workshop's cover and see it; link a tag and unlink it. Prints one line per step
// and a JSON summary; exits 1 when a step fails.
import { readFileSync, mkdirSync } from "node:fs";
import { chromium } from "@playwright/test";

const [base, appFile, shots] = process.argv.slice(2);
const app = JSON.parse(readFileSync(appFile, "utf8"));
if (shots) mkdirSync(shots, { recursive: true });
const host = process.env.WALK_HOST;
const browser = await chromium.launch({ args: host ? [`--host-resolver-rules=MAP localhost ${host}`] : [] });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
const results = [];
let problems = [];
page.on("pageerror", (error) => problems.push(`page error: ${error.message.slice(0, 200)}`));
page.on("response", (response) => {
  const url = response.url();
  const expected = response.status() === 401 && url.includes("/auth/"); // a signed-out `me`, a wrong password
  if (response.status() >= 400 && !expected && !url.includes("/_next/") && response.request().resourceType() === "fetch") {
    problems.push(`${response.request().method()} ${new URL(url).pathname} → ${response.status()}`);
  }
});

const run = Date.now().toString(36).slice(-5);
const auth = app.auth;
const login = auth.loginField;
const password = auth.password ?? "demo12345";
const route = (pageId) => app.routes[pageId];
const member = auth.demoUsers.find((user) => user.role === "member") ?? auth.demoUsers[0];
const organizer = auth.demoUsers.find((user) => user.role === "organizer") ?? auth.demoUsers[auth.demoUsers.length - 1];
// 1×1 PNG: an image to upload
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==", "base64");

async function settle() {
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(400);
}

async function step(name, body, allowed = []) {
  problems = [];
  let error = null;
  try {
    await body();
    await settle();
  } catch (caught) {
    error = String(caught.message || caught).split("\n")[0].slice(0, 220);
  }
  const left = problems.filter((problem) => !allowed.some((pattern) => problem.includes(pattern)));
  const failed = Boolean(error) || left.length > 0;
  results.push({ step: name, ok: !failed, error, problems: left });
  console.log(`${failed ? "FAIL" : "ok  "} ${name}${error ? ` — ${error}` : ""}${left.length ? ` — ${left.join("; ")}` : ""}`);
  if (failed && shots) await page.screenshot({ path: `${shots}/fail-${results.length}.png`, fullPage: true }).catch(() => {});
  return !failed;
}

async function signIn(user, pass = password) {
  await page.goto(base + auth.signIn, { waitUntil: "domcontentloaded" });
  await settle();
  await page.locator(`[id="auth_login-${login}"]`).fill(user);
  await page.locator('[id="auth_login-password"]').fill(pass);
  await page.locator('form button[type="submit"]').click();
  await page.waitForURL((url) => url.pathname !== auth.signIn, { timeout: 15000 });
  await settle();
}

async function signOut() {
  await page.locator('[data-bga-action="account"]').click();
  await page.locator('[data-bga-action="sign-out"]').click();
  await page.waitForURL((url) => url.pathname === "/", { timeout: 10000 });
  await settle();
}

async function firstRecord(listRoute) {
  await page.goto(base + listRoute, { waitUntil: "domcontentloaded" });
  await settle();
  const link = page.locator(`main a[href^="${listRoute}/"]`).filter({ hasNotText: "New" });
  const hrefs = await link.evaluateAll((links) => [...new Set(links.map((a) => a.getAttribute("href")))]);
  return hrefs.filter((href) => !href.endsWith("/new"));
}

// 1. sign up, signed in at once
const email = `walk-${run}@example.com`;
await step("sign up a new account", async () => {
  await page.goto(base + auth.signUp, { waitUntil: "domcontentloaded" });
  await settle();
  await page.locator(`[id="auth_register-${login}"]`).fill(email);
  await page.locator('[id="auth_register-password"]').fill(`walk-${run}-secret`);
  await page.locator('form button[type="submit"]').click();
  await page.waitForURL((url) => url.pathname !== auth.signUp, { timeout: 15000 });
  await settle();
  const account = await page.locator('[data-bga-action="account"]').getAttribute("aria-label");
  if (!account?.includes(email)) throw new Error(`the top bar shows ${account}`);
});

// 2. a page behind sign-in, signed out: to the sign-in page, and back after signing in
const bookings = route("bookings");
await step("a protected page asks to sign in, then opens", async () => {
  await signOut();
  await page.goto(base + bookings, { waitUntil: "domcontentloaded" });
  await page.waitForURL((url) => url.pathname === auth.signIn, { timeout: 10000 });
  const next = new URL(page.url()).searchParams.get("next");
  if (next !== bookings) throw new Error(`next is ${next}`);
  await page.locator(`[id="auth_login-${login}"]`).fill(member.login);
  await page.locator('[id="auth_login-password"]').fill(password);
  await page.locator('form button[type="submit"]').click();
  await page.waitForURL((url) => url.pathname === bookings, { timeout: 15000 });
});

await step("a wrong password is refused on the form", async () => {
  await signOut();
  await page.goto(base + auth.signIn, { waitUntil: "domcontentloaded" });
  await settle();
  await page.locator(`[id="auth_login-${login}"]`).fill(member.login);
  await page.locator('[id="auth_login-password"]').fill("not-the-password");
  await page.locator('form button[type="submit"]').click();
  await page.getByText(/wrong|password/i).first().waitFor({ timeout: 10000 });
}, ["→ 401"]);

// 3. a member: no "New" and no "Edit" where only organizers may
const workshops = route("workshops");
let workshopPages = [];
await step("a member sees no organizer actions", async () => {
  await signIn(member.login);
  workshopPages = await firstRecord(workshops);
  if ((await page.locator('[data-bga-action="create"]').count()) > 0) throw new Error("a member sees New workshop");
  await page.goto(base + workshopPages[0], { waitUntil: "domcontentloaded" });
  await settle();
  if ((await page.locator('[data-bga-action="edit"]').count()) > 0) throw new Error("a member sees Edit on a workshop");
  const nav = await page.locator('[data-sidebar="menu-button"], [data-slot="sidebar-menu-button"]').allInnerTexts();
  if (!nav.join(" ").includes("bookings")) throw new Error(`navigation: ${nav.join(", ")}`);
});

// 4. a booking from a workshop's page; a full workshop answers with its message
let booking = null;
await step("book a seat from a workshop's page", async () => {
  for (const workshop of workshopPages) {
    await page.goto(base + workshop, { waitUntil: "domcontentloaded" });
    await settle();
    const tab = page.getByRole("tab", { name: "Bookings", exact: true });
    if (await tab.count()) await tab.click();
    await page.locator('[data-bga-action="create"]').first().click();
    await page.waitForURL(/\/new$/, { timeout: 10000 });
    await settle();
    const form = Object.values(app.pages).find((p) => /\/\[id\]\/bookings\/new$/.test(p.route));
    const formId = form?.sections[0]?.form ?? "booking_create_in_workshop";
    await page.locator(`[id="${formId}-attendeeName"]`).fill(`Walk attendee ${run}`);
    await page.locator(`[id="${formId}-amount"]`).fill("12");
    const write = page.waitForResponse((r) => r.request().method() === "POST" && r.request().resourceType() === "fetch", { timeout: 10000 });
    await page.locator('form button[type="submit"]').click();
    const response = await write;
    if (response.status() === 409) {
      await page.getByText(/full/i).first().waitFor({ timeout: 5000 }); // the rule's message, as a toast
      continue;
    }
    if (response.status() >= 300) throw new Error(`booking → ${response.status()}`);
    booking = (await response.json()).id;
    break;
  }
  if (!booking) throw new Error("every workshop is full");
}, ["→ 409"]);

const bookingPage = `${bookings}/${booking}`;
// 5. pay: the provider's page (live) or the mock checkout, then the success page follows the payment
await step("pay for the booking", async () => {
  await page.goto(base + bookingPage, { waitUntil: "domcontentloaded" });
  await settle();
  await page.locator('[data-bga-action="pay"]').click();
  await page.waitForURL((url) => url.pathname.includes("/payments/"), { timeout: 15000 });
  if (!page.url().startsWith(base)) {
    // live: the fake provider's checkout page
    await page.getByRole("button", { name: /^pay/i }).first().click();
    await page.waitForURL((url) => url.href.startsWith(base), { timeout: 20000 });
  }
  await page.locator('[data-bga-payment="paid"]').waitFor({ timeout: 60000 });
  await page.goto(base + bookingPage, { waitUntil: "domcontentloaded" });
  await settle();
  if ((await page.locator('[data-bga-action="pay"]').count()) > 0) throw new Error("still payable after paying");
});

// 6. a status change through its transition; the next state only offers what may follow
await step("confirm the booking (a transition)", async () => {
  await page.goto(base + bookingPage, { waitUntil: "domcontentloaded" });
  await settle();
  const write = page.waitForResponse((r) => r.request().method() === "PATCH", { timeout: 10000 });
  await page.locator('[data-bga-action="transition-confirmed"]').click();
  const response = await write;
  if (response.status() >= 300) throw new Error(`confirm → ${response.status()}`);
  await settle();
  if ((await page.locator('[data-bga-action="transition-confirmed"]').count()) > 0) throw new Error("confirmed twice");
  if ((await page.locator('[data-bga-action="transition-cancelled"]').count()) === 0) throw new Error("cannot cancel");
});

// 7. an organizer uploads a workshop's cover; the record shows it
await step("upload a workshop cover as an organizer", async () => {
  await signOut();
  await signIn(organizer.login);
  await page.goto(`${base}${workshopPages[0]}/edit`, { waitUntil: "domcontentloaded" });
  await settle();
  const formId = Object.keys(app.forms).find((id) => id.startsWith("workshop_update")) ?? "workshop_update";
  await page.locator(`[id="${formId}-cover"]`).setInputFiles({ name: `cover-${run}.png`, mimeType: "image/png", buffer: PNG });
  await page.locator('[data-bga-input="upload"] img').first().waitFor({ timeout: 20000 });
  const write = page.waitForResponse((r) => r.request().method() === "PATCH", { timeout: 10000 });
  await page.locator('form button[type="submit"]').click();
  const response = await write;
  if (response.status() >= 300) throw new Error(`save → ${response.status()}`);
  await page.goto(base + workshopPages[0], { waitUntil: "domcontentloaded" });
  await settle();
  const src = await page.locator("main img").first().getAttribute("src");
  if (!src) throw new Error("no cover shown");
});

// 8. link a tag to a workshop, then unlink it
await step("link a tag and unlink it", async () => {
  await page.goto(base + workshopPages[0], { waitUntil: "domcontentloaded" });
  await settle();
  const tab = page.getByRole("tab", { name: "Tags", exact: true });
  if (await tab.count()) await tab.click();
  await page.locator("[data-bga-links-add]").waitFor({ timeout: 10000 });
  await settle(); // the links list loaded before counting its chips
  const chips = page.locator('[data-bga-action="unlink"]');
  const before = await chips.count();
  await page.locator('[data-bga-links-add] [data-bga-input="reference"]').click();
  const options = page.locator('[data-slot="popover-content"] [data-slot="command-item"]:not([data-checked="true"])');
  await options.first().waitFor({ timeout: 10000 });
  await options.last().click();
  const add = page.waitForResponse((r) => r.request().method() === "POST" && r.request().resourceType() === "fetch", { timeout: 10000 });
  await page.locator('[data-bga-action="link"]').click();
  const added = await add;
  if (added.status() === 409) {
    // that tag was linked already: unlink it below all the same
  } else if (added.status() >= 300) throw new Error(`link → ${added.status()}`);
  await settle();
  const after = await chips.count();
  if (added.status() < 300 && after !== before + 1) throw new Error(`${before} → ${after} chips`);
  const remove = page.waitForResponse((r) => r.request().method() === "DELETE", { timeout: 10000 });
  await chips.last().click();
  if ((await remove).status() >= 300) throw new Error("unlink failed");
  await settle();
  if ((await chips.count()) !== after - 1) throw new Error("the chip stayed");
}, ["→ 409"]);

if (shots) await page.screenshot({ path: `${shots}/last.png`, fullPage: true }).catch(() => {});
await browser.close();
const failed = results.filter((r) => !r.ok);
console.log(JSON.stringify({ steps: results.length, failed: failed.length }));
process.exit(failed.length ? 1 : 0);
