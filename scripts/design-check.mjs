// Design checklist measurements for a built static site (Story 17.7, templates/nextjs_overlay/DESIGN_CHECKLIST.md).
// Runs inside bga-runner-node from the project directory, after `pnpm build` (static export in out/):
//
//   node design-check.mjs <shots-dir> <page-route>...
//
// For every page at 390 / 768 / 1440 px, light and dark: a full-page screenshot and the measurements below, written
// to <shots-dir>/report.json. Dev tool only; not part of the generation pipeline.
import { mkdirSync, writeFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { chromium } from "@playwright/test";

const [shots = "shots", ...routes] = process.argv.slice(2);
const WIDTHS = [390, 768, 1440];
const PORT = 3199;
mkdirSync(shots, { recursive: true });

const server = spawn("node", ["scripts/serve-static.mjs", "out", String(PORT)], { stdio: "inherit" });
await new Promise((resolve) => setTimeout(resolve, 500));

function measure() {
  const visible = (el) => {
    const box = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return box.width > 0 && box.height > 0 && style.visibility !== "hidden" && style.display !== "none";
  };
  const lines = (el) => {
    const style = getComputedStyle(el);
    const lineHeight = parseFloat(style.lineHeight) || parseFloat(style.fontSize) * 1.2;
    return Math.round(el.getBoundingClientRect().height / lineHeight);
  };
  const textElements = [...document.querySelectorAll("body *")].filter(
    (el) => visible(el) && [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()),
  );
  const sizes = [...new Set(textElements.map((el) => getComputedStyle(el).fontSize))].sort(
    (a, b) => parseFloat(a) - parseFloat(b),
  );
  const families = [...new Set(textElements.map((el) => getComputedStyle(el).fontFamily.split(",")[0].trim()))];
  const loaded = [...document.fonts].filter((f) => f.status === "loaded").map((f) => f.family.replaceAll('"', ""));
  const h1 = document.querySelector("h1");
  const header = document.querySelector("header");
  const hero = document.querySelector('[data-bga-component="Hero"]');
  const cta = hero?.querySelector("a");
  const paragraphs = [...document.querySelectorAll("main p")].filter((p) => visible(p) && lines(p) >= 2);
  const perLine = paragraphs.map((p) => Math.round(p.textContent.length / lines(p)));
  const body = getComputedStyle(document.body);
  return {
    h1Lines: h1 ? lines(h1) : null,
    navHeight: header ? Math.round(header.getBoundingClientRect().height) : null,
    ctaAboveFold: cta ? cta.getBoundingClientRect().bottom <= window.innerHeight : null,
    typeSizes: sizes,
    families,
    loadedFonts: [...new Set(loaded)],
    maxCharsPerLine: perLine.length ? Math.max(...perLine) : null,
    background: body.backgroundColor,
    foreground: body.color,
  };
}

const browser = await chromium.launch();
const report = {};
try {
  for (const scheme of ["light", "dark"]) {
    for (const width of WIDTHS) {
      const page = await browser.newPage({ viewport: { width, height: 900 }, colorScheme: scheme });
      for (const route of routes) {
        await page.goto(`http://127.0.0.1:${PORT}${route}`, { waitUntil: "networkidle" });
        await page.evaluate(() => document.fonts.ready);
        const name = `${route === "/" ? "home" : route.slice(1).replaceAll("/", "-")}-${width}-${scheme}`;
        await page.screenshot({ path: `${shots}/${name}.png`, fullPage: true });
        report[name] = await page.evaluate(measure);
      }
      await page.close();
    }
  }
} finally {
  await browser.close();
  server.kill();
}
writeFileSync(`${shots}/report.json`, JSON.stringify(report, null, 2));
console.log(`design check: ${Object.keys(report).length} page views → ${shots}/report.json`);
