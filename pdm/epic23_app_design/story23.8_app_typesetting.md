# Story 23.8 — Japanese and English typesetting for apps

**Epic:** [23 — App design](epic23_app_design.md) · **Requirements:** FR-37, FR-22 · **Depends on:** 23.7

## User story

As a user drafting an app in Japanese (or with Japanese content), I want Japanese labels, buttons, dates and a
Japanese typeface chosen for the look, so that the app reads naturally and doesn't fall back to the device's font.

## Context

- `fonts.py` has 30 Latin-only `@fontsource` families; `theme.py` `FONT_FALLBACK` has no CJK fonts.
- The kit's own strings ("New", "Search", "Not for your role", "Load more", form errors) are English; dates use
  `date-locale.ts`.
- Story 20.10 plans the same fonts for static sites. **This story does the shared part once** (base fonts,
  `fonts.py` scripts, CSS stacks); 20.10 keeps its static-only parts (direction cards, static checks) and reuses it.

## Steps

1. **Base fonts.** Add Japanese families with `make frontend-base` (exact pins): Noto Sans JP, Noto Serif JP,
   Zen Kaku Gothic New, M PLUS 1p, BIZ UDPGothic (for dense business screens), Shippori Mincho. Fontsource's
   `unicode-range` slices, so a page loads only what it uses; check the build size. `make runner-node`.
2. **Fonts.** `fonts.py` marks scripts (`latin`, `ja`); the theme may name `typography.jaFont`. CSS stacks: Latin face
   → Japanese face → `"Hiragino Sans", "Yu Gothic", "Noto Sans JP", sans-serif`. Each recipe (23.7) names a default
   Japanese face (e.g. `editorial` → Shippori Mincho headings, `enterprise` → BIZ UDPGothic).
3. **Locale.** `draft_app` sets `project.locale` from the requirement's language (`ja` or `en`); outline labels are
   written in that language. Code checks it (a `ja` locale with English labels is a note, not an error).
4. **Typesetting** under `:lang(ja)`: body line height 1.7–1.9, no uppercase, no wide tracking, heading weight capped
   at 700, a display scale for kanji widths, `word-break: auto-phrase` where supported, `font-feature-settings:
   "palt"` on headings only.
5. **Kit strings.** `src/components/app/messages/{en,ja}.ts` for every kit string (shell, lists, forms, auth,
   payments, empty and error states); `date-locale.ts`, number and currency formats follow the locale (yen with no
   decimals). Contract error messages stay the backend's (`x-bga.errors`), so a Japanese app's backend messages are
   drafted in Japanese.
6. **Checks.** `design-check-app` gets a Japanese fixture app: no fallback font for kana or kanji, no overflow at
   375 px, line height in range, no English kit string on screen.
7. Tests: font scripts and stacks, typesetting tokens for `ja`, messages complete for both locales (every key in
   both), locale from the requirement, recipe faces.

## Acceptance criteria

- [x] Japanese families are in the pinned base, render offline, and only the used slices load.
- [ ] A Japanese requirement drafts an app with Japanese labels, kit strings, dates and yen, in a bundled Japanese
      face.
- [x] Japanese text gets suitable line height, no uppercase or wide tracking, and capped heading weight.
- [x] English apps render as before (their snapshots unchanged apart from the new message lookups).
- [x] The Japanese case passes the design check.
- [x] Static golden passes (Latin static sites unchanged).

## Verify

`make lint`, `make test`, `make frontend-base` + `make runner-node`, `BGA_SANDBOX_TESTS=1 make test`,
`make design-check-app` with the Japanese fixture, `make up` with a Japanese requirement on the fake engine.

## Status

**Implemented (2026-11-06), on the fake engine and mocks.**
- **Base:** six Japanese families added with `pnpm add -E --lockfile-only` (Noto Sans JP, Noto Serif JP, Zen Kaku
  Gothic New, BIZ UDPGothic, Shippori Mincho, M PLUS 1p; only additions to the lock), the overlay manifest rebuilt,
  `make runner-node` rebuilt (the pre-warmed store has them). `fonts.JA_FONTS`, apart from `FONTS`, so no Latin pairing
  or static site ever picks one (a first try put them in `FONTS` and a static draft's pairing changed: caught by the
  static golden). The Makefile's `frontend-base` lists both.
- **Apps:** `typesetting.py`: `locale_of` (kana present and a fifth of the letters CJK), `ja_face` by look, the face
  after the Latin one with CJK fallbacks, `:lang(ja)` rules (line height 1.8, phrase breaks, no uppercase or wide
  tracking, heading weight ≤ 700, `palt` on headings); `fonts.ts` imports the face. `AppOutline.locale` → `project.locale`.
- **Words:** the kit's `messages.ts` (en, ja; every key in both, tested), the auth and payment screens, and the
  planner's own words (`screens.WORDS`: Dashboard, New, Edit, Delete, toasts, sign-in labels); English output is byte
  for byte as before.
- Verified: `tests/test_app_typesetting.py`; the clinic and the news feed built as Japanese apps (0 failures).

Deviations: the static golden was refreshed for `package.json`, `pnpm-lock.yaml` and `.bga/owned.json` only (the base
gained the fonts; every rendered file unchanged); a real Japanese draft waits for the user's real test.
