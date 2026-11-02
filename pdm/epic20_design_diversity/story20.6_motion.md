# Story 20.6 — Motion

**Epic:** [20 — Design diversity](epic20_design_diversity.md) · **Requirements:** FR-33, FR-22 · **Depends on:** 20.4

## User story

As a visitor of a generated site, I want buttons to respond, tabs and questions to open with continuity, and sections
to arrive in a way that suits the site, with one memorable moment, so that the site feels made and alive, without
motion ever hiding content or slowing me down.

## Context

- Today: the only library motion is the CardGrid hover lift (`transition-transform`, `motion-reduce:`);
  `DESIGN_CHECKLIST.md` (17.7) allows transform and opacity only, with a `prefers-reduced-motion` fallback;
  `tw-animate-css` is in the pinned base; shadcn primitives keep their own motion.
- Sites are static exports (and dynamic Next.js apps) built from the spec by the renderer, with no engine call.
- `scripts/design-check.mjs` does not control motion: entrance animations would be screenshotted half-way.
- Research (`docs/research/design-diversity.md`): oil-ui's three baseline motions, reveals by content, feel presets
  (action + object, spring stiffness / damping), springs as CSS `linear()`; scroll-driven CSS is Chrome / Edge and
  Safari 26 only (Firefox behind a flag in mid-2026); GSAP's licence excludes tools competing with Webflow, so no
  GSAP; generated animation code is often wrong (MoVer, LogoMotion), so motion comes from tested presets.

## Steps

1. **Spec.** `theme.motion` = `{feel: "none" | "click" | "slide" | "flow" | "drop" | "bounce" | "float" | "cut",
   signature: "none" | "countUp" | "headlineRise" | "imageUnmask" | "indicator"}` (optional; default `none` /
   `none`, so existing sites stay still).
2. **Feel presets** (`files/renderer/src/motion/`): each feel = durations, an easing written as CSS `linear()` from a
   spring (stiffness / damping from the research table; sampled at build time by a small script, stored as
   constants) with a `cubic-bezier` fallback, and overshoot limits (≤ 2% on large surfaces, ≤ 15% on small marks).
   `cut` = 80–150 ms linear steps, for loud and raw directions. Exposed as CSS variables in `globals.css`.
3. **Three baseline motions** (when `feel` ≠ `none`):
   - buttons and links: press scale 0.97, 150–300 ms, instant on press, spring on release;
   - one state change with continuity: the Tabs indicator slides to the new tab; Faq items expand with height and
     opacity (content readable immediately);
   - first entrance: the hero's headline, then text and CTA, then the image, 40–80 ms apart, ≤ 600 ms in total,
     played once per page load.
4. **Reveals by content** (below the hero, once, when 15% of a section is visible): cards and pricing drop in with
   the feel's spring; lists and steps unfold in reading order; stats count to their value; images unmask from the
   subject side while scaling 1.08 → 1; headlines rise by line. Followers 40–80 ms after the lead, ≤ 900 ms per
   section. One small client component (`Reveal`, IntersectionObserver, sets `data-revealed`); the CSS does the rest
   (`@starting-style` and transitions on transform and opacity).
5. **Signature moment.** The card's `signature` turns on one stronger version on one section: `countUp` (stats),
   `headlineRise` (hero headline by line), `imageUnmask` (hero or gallery image), `indicator` (a sliding highlight
   on nav or tabs). Only one per site.
6. **Safety rules** (checklist and code):
   - content is visible without JS: the hidden start state applies only under `html[data-motion="on"]`, set by an
     inline script; no JS → no hiding;
   - `prefers-reduced-motion: reduce` → every element in its final state, no reveal, no count-up (final numbers);
   - motion never delays a primary action or blocks input; exits run at 60–70% of the entry time;
   - transform and opacity only (heights only for Faq panels, with `interpolate-size` where supported, else instant);
   - scroll-driven CSS (`animation-timeline: view()`) only as an enhancement behind `@supports`.
7. **Direction.** The card (20.4) gets `motion` from the tone: energy and weight pick the feel (heavy → `click` /
   `drop`, light → `float` / `flow`, raw and loud → `cut`, very quiet → `none`); the card names its signature. The
   fake engine fills them from its concept library.
8. **Design check.** `design-check.mjs` runs two passes: (a) reduced motion emulated (`reducedMotion: "reduce"`) for
   the layout measurements and screenshots, as today; (b) motion on: scroll the page to the end in steps, wait for
   reveals, then fail if any element with text or an image is still at opacity < 1 or transformed off its box;
   also record the time from load to the CTA being visible (must stay under 1 s).
9. **Custom components.** The `generate_custom_component` prompt (next version) gets the site's feel, the rules and
   the `Reveal` component; the isolated render test runs with reduced motion and checks nothing stays hidden.
10. Tests: easing generation (spring → `linear()` points end at 1 within 0.5%); `globals.css` snapshot per feel;
    fixture pages in each feel and signature; sandbox build; both design-check passes on the fixture in 3 feels;
    no-JS render (JS disabled in Playwright) shows all content.

## Acceptance criteria

- [ ] `theme.motion` exists; `none` (the default) keeps sites exactly as today.
- [ ] With a feel: button feedback, the Tabs / Faq continuity, a staged hero entrance and reveals by content work in
      every section of the library, once per load.
- [ ] One signature moment per site, from the direction card.
- [ ] Content is complete with JS disabled and with reduced motion; motion never delays the primary CTA (< 1 s to
      visible).
- [ ] `design-check.mjs` runs both passes; no element is left hidden; checklist updated.
- [ ] No animation library added; no GSAP.

## Verify

`make lint`, `make test`, `UPDATE_SNAPSHOTS=1 make test` (review), `BGA_SANDBOX_TESTS=1 make test`,
`node scripts/design-check.mjs` (both passes), `make up` with the fake engine: a drafted site in a `drop` direction and
one in `float` feel different in the preview; with the OS setting "reduce motion" both are still.

## Status
