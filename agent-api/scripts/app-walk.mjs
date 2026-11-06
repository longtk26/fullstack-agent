// The app walk (Story 22.4): drives a generated app of the dynamic app flow through every screen and action in a
// real browser, from its own `src/content/app.json`, and fails on any API call that fails, any error state and any
// page error. Runs inside bga-runner-node against a running app (a preview, live or on mocks).
//
//   node app-walk.mjs <base url> <app.json> [shots dir]
//
// Steps: every page without route parameters loads; every list opens its first record; every record page's "Edit"
// saves; every create form (a list's "New", a parent's "Add") submits with its required fields filled by type; every
// list deletes a record through its row menu (confirm included); every record action without a form runs. Prints
// one line per step and a JSON summary; exits 1 when a step fails.
import { readFileSync, mkdirSync } from "node:fs";
import { chromium } from "@playwright/test";

const [base, appFile, shots] = process.argv.slice(2);
const app = JSON.parse(readFileSync(appFile, "utf8"));
if (shots) mkdirSync(shots, { recursive: true });
// WALK_HOST: the host that `localhost` means (an app on the Docker host, walked from a container).
const host = process.env.WALK_HOST;
const browser = await chromium.launch({ args: host ? [`--host-resolver-rules=MAP localhost ${host}`] : [] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const results = [];
let problems = [];
page.on("pageerror", (error) => problems.push(`page error: ${error.message.slice(0, 200)}`));
page.on("response", (response) => {
  const url = response.url();
  if (response.status() >= 400 && !url.includes("/_next/") && response.request().resourceType() === "fetch") {
    problems.push(`${response.request().method()} ${new URL(url).pathname} → ${response.status()}`);
  }
});
page.on("requestfailed", (request) => {
  // Next prefetches linked pages (`?_rsc=`) and cancels them on navigation: not a failure.
  if (request.resourceType() === "fetch" && !request.url().includes("_rsc=")) problems.push(`${request.method()} ${request.url()} failed: ${request.failure()?.errorText}`);
});

const run = Date.now().toString(36).slice(-5); // unique values per walk (names may be unique in the API)
const pageRoutes = Object.fromEntries(Object.entries(app.pages).map(([id, p]) => [id, p.route]));

async function settle() {
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(400);
}

async function step(name, run) {
  problems = [];
  let error = null;
  try {
    await run();
    await settle();
    const broken = await page.getByText("Could not load this").count();
    if (broken) error = "an error state is shown";
  } catch (caught) {
    error = String(caught.message || caught).split("\n")[0].slice(0, 200);
  }
  const failed = Boolean(error) || problems.length > 0;
  results.push({ step: name, ok: !failed, error, problems: [...problems] });
  console.log(`${failed ? "FAIL" : "ok  "} ${name}${error ? ` — ${error}` : ""}${problems.length ? ` — ${problems.join("; ")}` : ""}`);
  if (failed && shots) await page.screenshot({ path: `${shots}/fail-${results.length}.png`, fullPage: true }).catch(() => {});
}

async function fill(field, form) {
  const id = `${form}-${field.name}`;
  const control = page.locator(`[id="${id}"]`);
  if (field.reference) {
    // the kit's picker (Story 22.6): open it, take the first record
    await control.click();
    await page.locator('[data-slot="popover-content"] [data-slot="command-item"]').first().click();
    return;
  }
  switch (field.type) {
    case "enum": {
      const style = await control.getAttribute("data-bga-input");
      if (style === "radio") return control.getByRole("radio").first().click();
      if (style === "toggle") return control.locator("button").first().click();
      await control.click();
      await page.getByRole("option").first().click();
      return;
    }
    case "boolean":
      return;
    case "date":
    case "datetime": {
      // the kit's calendar (Story 22.5): today, picked in the popover
      await control.click();
      const day = page.locator('[data-slot="popover-content"] [data-today] button, [data-slot="popover-content"] td[data-today="true"] button');
      await (await day.count() ? day.first() : page.locator('[data-slot="popover-content"] [role="gridcell"] button').nth(10)).click();
      if (field.type === "datetime") await page.locator(`[id="${id}-time"]`).fill("10:00");
      return;
    }
    case "integer":
      return page.locator(`[id="${id}"]`).fill(String(field.min ?? 1));
    case "number":
    case "decimal":
      return page.locator(`[id="${id}"]`).fill(String(field.min ?? 1));
    case "email":
      return page.locator(`[id="${id}"]`).fill("walk@example.com");
    case "url":
      return page.locator(`[id="${id}"]`).fill("https://example.com");
    default:
      return page.locator(`[id="${id}"]`).fill(`Walk ${field.name} ${run}`.slice(0, field.maxLength ?? 60));
  }
}

async function submitForm(formId) {
  const form = app.forms[formId];
  for (const field of form.fields.filter((f) => !f.hidden && f.required)) await fill(field, formId);
  const writes = page.waitForResponse((r) => r.request().method() !== "GET" && r.request().resourceType() === "fetch", { timeout: 10000 });
  await page.locator('form button[type="submit"]').last().click();
  const response = await writes;
  if (response.status() >= 300) throw new Error(`${response.request().method()} → ${response.status()}`);
}

// 1. Pages without route parameters
for (const [id, p] of Object.entries(app.pages)) {
  if (p.route.includes("[")) continue;
  await step(`open ${p.route}`, () => page.goto(base + p.route, { waitUntil: "domcontentloaded" }));
}

// 2–5. Per list page: open a record, edit it, create one, delete one
const lists = Object.entries(app.pages).filter(([, p]) => !p.route.includes("[") && p.sections.some((s) => s.component === "AppList" && !s.content?.tab && s.content?.variant !== "recent"));
for (const [id, p] of lists) {
  const list = p.sections.find((s) => s.component === "AppList" && !s.content?.tab);
  const actions = list.content?.actions ?? [];
  const view = actions.find((a) => a.id === "view");
  // A list the walk emptied earlier (a custom list of due records, say) has no record to open: skipped, not failed.
  let empty = false;
  if (view) {
    await page.goto(base + p.route, { waitUntil: "domcontentloaded" });
    await settle();
    empty = (await page.locator(`[data-bga-section$="/${list.id}"] tbody a, [data-bga-section$="/${list.id}"] ul a`).count()) === 0;
    if (empty) {
      results.push({ step: `${p.route}: records`, ok: true, skipped: true });
      console.log(`skip ${p.route}: empty, nothing to open`);
    }
  }
  if (view && !empty) {
    await step(`${p.route}: open a record`, async () => {
      await page.goto(base + p.route, { waitUntil: "domcontentloaded" });
      await settle();
      const section = `[data-bga-section$="/${list.id}"]`;
      const link = page.locator(`${section} tbody a, ${section} ul a`).first();
      await link.click();
      await page.waitForURL((url) => url.pathname !== p.route, { timeout: 10000 });
    });
    const record = page.url();
    const detail = Object.values(app.pages).find((d) => d.route === pageRoutes[view.page]);
    for (const action of detail?.sections[0]?.content?.actions ?? []) {
      if (action.kind === "link" && action.id === "edit") {
        await step(`${p.route}: edit and save a record`, async () => {
          await page.goto(record, { waitUntil: "domcontentloaded" });
          await settle();
          await page.locator('[data-bga-action="edit"]').first().click();
          await page.waitForURL(/\/edit$/, { timeout: 10000 });
          await settle();
          const formId = Object.values(app.pages).find((f) => f.route === pageRoutes[action.page])?.sections[0]?.form;
          const field = app.forms[formId]?.fields.find((f) => !f.hidden && !f.reference && ["string", "text"].includes(f.type));
          if (field) await page.locator(`[id="${formId}-${field.name}"]`).fill(`Edited ${field.name} ${run}`.slice(0, field.maxLength ?? 60));
          // a reference is picked by name (Story 22.6): the picker lists the parents and the save sends one
          const reference = app.forms[formId]?.fields.find((f) => !f.hidden && f.reference);
          if (reference) await fill(reference, formId);
          const writes = page.waitForResponse((r) => ["PATCH", "PUT"].includes(r.request().method()), { timeout: 10000 });
          await page.locator('form button[type="submit"]').click();
          const response = await writes;
          if (response.status() >= 300) throw new Error(`save → ${response.status()}`);
        });
      } else if (action.kind === "mutation" && action.form) {
        await step(`${p.route}: record action ${action.id} (its form in a dialog)`, async () => {
          await page.goto(record, { waitUntil: "domcontentloaded" });
          await settle();
          await page.locator(`[data-bga-action="${action.id}"]`).first().click();
          await page.getByRole("dialog").waitFor();
          await submitForm(action.form);
        });
      } else if (action.kind === "mutation" && !action.form && action.id !== "delete") {
        await step(`${p.route}: record action ${action.id}`, async () => {
          await page.goto(record, { waitUntil: "domcontentloaded" });
          await settle();
          const writes = page.waitForResponse((r) => r.request().method() !== "GET" && r.request().resourceType() === "fetch", { timeout: 10000 });
          await page.locator(`[data-bga-action="${action.id}"]`).first().click();
          if (action.confirm) await page.getByRole("alertdialog").getByRole("button").last().click();
          const response = await writes;
          if (response.status() >= 300) throw new Error(`${action.id} → ${response.status()}`);
        });
      }
    }
    // a parent's "Add" for each child tab
    for (const tab of (detail?.sections ?? []).filter((s) => s.content?.tab && s.content?.create)) {
      await step(`${p.route}: add ${tab.content.title} from a record's page`, async () => {
        await page.goto(record, { waitUntil: "domcontentloaded" });
        await settle();
        const tabButton = page.getByRole("tab", { name: tab.content.tab, exact: true });
        if (await tabButton.count()) await tabButton.click();
        await page.locator(`[data-bga-section$="/${tab.id}"] [data-bga-action="create"]`).first().click();
        await page.waitForURL(/\/new$/, { timeout: 10000 });
        await settle();
        const formId = Object.values(app.pages).find((f) => f.route === pageRoutes[tab.content.create.page])?.sections[0]?.form;
        await submitForm(formId);
      });
    }
  }
  if (list.content?.create) {
    await step(`${p.route}: create a record`, async () => {
      await page.goto(base + p.route, { waitUntil: "domcontentloaded" });
      await settle();
      await page.locator('[data-bga-action="create"]').first().click();
      await page.waitForURL(/\/new$/, { timeout: 10000 });
      await settle();
      const formId = Object.values(app.pages).find((f) => f.route === pageRoutes[list.content.create.page])?.sections[0]?.form;
      await submitForm(formId);
    });
  }
  if (actions.some((a) => a.id === "delete") && !empty) {
    // an earlier step may have emptied the list (a review moves a card off the due list): skipped, not failed
    await page.goto(base + p.route, { waitUntil: "domcontentloaded" });
    await settle();
    if ((await page.locator('button[aria-label^="Actions for"]').count()) === 0) {
      results.push({ step: `${p.route}: delete`, ok: true, skipped: true });
      console.log(`skip ${p.route}: emptied by an earlier step, nothing to delete`);
      continue;
    }
    await step(`${p.route}: delete a record from its row menu`, async () => {
      await page.goto(base + p.route, { waitUntil: "domcontentloaded" });
      await settle();
      await page.locator('button[aria-label^="Actions for"]').last().click();
      await page.locator('[role="menuitem"][data-bga-action="delete"]').click();
      const writes = page.waitForResponse((r) => r.request().method() === "DELETE", { timeout: 10000 });
      await page.getByRole("alertdialog").getByRole("button").last().click();
      const response = await writes;
      if (response.status() >= 300) throw new Error(`delete → ${response.status()}`);
    });
  }
}

await browser.close();
const failed = results.filter((r) => !r.ok);
console.log(JSON.stringify({ steps: results.length, failed: failed.length }));
process.exit(failed.length ? 1 : 0);
