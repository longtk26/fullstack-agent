# Story 20.10 — Japanese fonts and typesetting

**Epic:** [20 — Design diversity](epic20_design_diversity.md) · **Requirements:** FR-33, FR-22 · **Depends on:** 20.3, 20.4

## User story

As a user drafting a site in Japanese (or a site with Japanese words in it), I want headings and text set in a
Japanese typeface chosen for the direction, with spacing that suits Japanese, so that the site looks designed rather
than falling back to whatever font the visitor's device has.

## Context

- Today (2026-11-03): the pinned base bundles 30 `@fontsource` families (`frontend_spec/fonts.py`), all Latin only.
  Kana and kanji fall back through `FONT_FALLBACK` (`ui-sans-serif, system-ui, …`) to the device's font: Hiragino
  Sans on macOS / iOS, Yu Gothic or Meiryo on Windows, Noto Sans CJK on Android, empty boxes on Linux without CJK
  fonts. A real draft ("introduce Japanese", 2026-11-03) used Outfit / Rubik with kana drawn in the fallback.
- `project.locale` already sets `<html lang>` (`layout.tsx`), but nothing in the theme reacts to it.
- Fontsource ships Japanese families split by `unicode-range`, so a page downloads only the slices it uses.
- Japanese typesetting differs from Latin: body line height about 1.7–1.9; no uppercase; wide tracking and very heavy
  display weights look wrong on kanji; mixed text needs a Latin face first and the Japanese face second in the stack.

## Steps

1. **Base.** Add a few Japanese families with `make frontend-base` (exact pins), e.g. Noto Sans JP, Noto Serif JP,
   Zen Kaku Gothic New, M PLUS 1p, Shippori Mincho (one sans, one serif, one or two with character); `make
   runner-node`. Check build size and that only used slices load.
2. **Fonts.** `fonts.py` marks a font's scripts (`latin`, `ja`); the theme may name a Japanese face beside the Latin
   one (`typography.jaFont`, optional, additive). `fonts.ts` imports it; `globals.css` stacks Latin face → Japanese
   face → a CJK fallback (`"Hiragino Sans", "Yu Gothic", "Noto Sans JP", sans-serif`), for headings and body.
3. **Typesetting.** With `locale: "ja"` (or a Japanese face set), the tone tokens adjust: looser body line height, no
   `headingCase: upper` and no wide tracking on Japanese text, heading weight capped, display scale checked for
   kanji widths.
4. **Directions.** The fact pack lists the Japanese faces; a card may name one; when the requirement is in Japanese
   or names Japanese content, every card gets a Japanese face (filled from the tone when the card has none), and the
   difference test counts it with the heading font.
5. **Drafting.** The next `draft_frontend_spec` version sets `project.locale` from the requirement's language.
6. **Checks.** `DESIGN_CHECKLIST.md`: Japanese rules. `design-check.mjs` and the fixture get a Japanese case (no
   fallback font used for kana / kanji, no overflow, line height in range). The diversity report gets a Japanese
   golden requirement.
7. Tests: font scripts and stacks, typesetting tokens for `ja`, card filling, prompt version, fixture case.

## Acceptance criteria

- [ ] Japanese families are in the pinned base and render offline; only the used slices load.
- [ ] A Japanese site uses a bundled Japanese face for kana and kanji (no device fallback) in headings and text.
- [ ] Japanese text gets suitable line height, no uppercase or wide tracking, and capped heading weight.
- [ ] Direction cards for a Japanese requirement each carry a Japanese face, chosen to fit the direction.
- [ ] Latin-only sites plan and render exactly as before.
- [ ] The checklist covers Japanese; the design check passes on the Japanese case.

## Verify

`make lint`, `make test`, `UPDATE_SNAPSHOTS=1 make test` (review), `make frontend-base` + `make runner-node`,
`BGA_SANDBOX_TESTS=1 make test`, `node scripts/design-check.mjs` with the Japanese case, `make up` with the fake
engine: a Japanese requirement drafts three directions with Japanese faces, and the site shows them.

## Status

**Planned (2026-11-03)**, added at the user's request after a real draft showed kana in the device's fallback font.
Scheduled after the spec-drafting speed work (direct API engine for drafts), which comes first.
