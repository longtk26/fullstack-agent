# Story 12.4 — Requirement → FrontendSpec (+ BackendSpec) drafting

**Epic:** [12 — Modes, FrontendSpec & contract](epic12_contract_and_frontend_spec.md) · **Requirements:** FR-24, FR-01 · **Depends on:** 12.1, 2.4, 3.2
**Planned:** first item after Epic 17's main stories, together with 2.4 and 9.7b (re-planned 2026-10-30).

## User story

As a user, I want to describe my site in plain language, typed or as a Markdown / text file, and get a FrontendSpec
(and, for a dynamic app, the matching BackendSpec) that I can review, instead of writing JSON.

## Acceptance criteria

- [x] Draft job (same infrastructure and endpoint as 2.4, `mode: static | dynamic`): requirement + mode → the engine
      writes `frontend-spec.json` and, in `dynamic` mode, `backend-spec.json`. Both are validated (12.1, 2.2) and
      repaired by the engine up to 2 times; the result lists **assumptions** (e.g. "added a contact page") and
      **unresolved** questions the user must acknowledge.
- [x] The requirement is plain text or Markdown, typed or from a `.md` / `.txt` file (2.4). Headings and lists in a
      Markdown requirement are kept as they are in the prompt.
- [x] The drafter decides the page list from the requirement (every user-visible feature maps to at least one
      page or section) and picks a theme preset and colours from any brand words in the requirement. With no brand
      words, the theme comes from the design direction (12.6).
- [x] Drafts aim at the typed section catalogue (17.1): catalogue sections with typed props wherever they fit, so a
      static draft renders with no engine call; custom components only for what the catalogue cannot show.
- [x] Copy rules in the prompt: short headlines (two lines at most), hero text ≤ 20 words, real content from the
      requirement. Testimonials, client logos, numbers and awards are never invented: when the requirement gives
      none, sample content is used and listed in `assumptions[]` as "sample content, replace before publishing".
- [x] In `dynamic` mode the BackendSpec is derived from the FrontendSpec's data needs (every `operationId` used
      by a page or form exists as an operation), reusing the deterministic rules of 2.5 where possible. The pair
      passes the consistency check (12.5) before the draft is returned.
- [x] `static` mode never produces a BackendSpec or bindings; data shown on pages goes into `content`.
- [x] Prompt versions and outputs are stored; the draft can be edited in the UI (9.7b) before generation.
- [x] Draft jobs are counted in usage (8.4).

**Status (2026-10-30):** done on `feat/story2.4-requirement-drafting` (see 2.4 for the shared runner). Deviations:
- One engine call writes both specs in dynamic mode; the deterministic rules of 2.5 are not reused (they convert a
  Frontend-Agent site, not a FrontendSpec). The pair is validated and its consistency checked (12.5) before the draft
  is returned; errors go back to the engine (`repair_spec`, up to `DRAFT_REPAIR_ATTEMPTS_FRONTEND=2`).
- A static draft's spec must declare `project.mode: "static"` (else `MODE_MISMATCH`); the static validator rejects API
  bindings, so no backend leaks in. A `backend-spec.json` written in static mode is ignored.
- The engine gets the section catalogue (`.bga/sections.md`, generated from the props models) and one example per mode
  (`static-landing.json`, `shop-dynamic.json`, `shop.json`). Theme: brand words or a preset; the design direction
  (palette, fonts, section order) comes with 12.6.
- Page coverage, theme choice and copy rules depend on the prompt; they were not checked with a paid engine.
