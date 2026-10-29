# Story 17.8 — Custom components that fit the page

**Epic:** [17 — Fast generation](epic17_fast_generation.md) · **Requirements:** FR-30 · **Depends on:** 17.3

## User story

As a user, I want the custom components of my site to sit on the page like the library sections around them, and
their values to read like a shop or an app, not like raw data.

## Why

Found on the first `shop-dynamic` run built from cached components (2026-10-29, `gen_01M63GCRJRPQC022SDWD1VYFT4`):
each component is generated alone against data, so nothing tells it how it sits on the page, and its checks (tsc,
ESLint, render test) cannot see layout. `ProductGrid` ran edge to edge (no page container); `ProductDetail` shrank to
a thin column (`mx-auto max-w-2xl` without `w-full` in a flex parent); prices showed as `9.5`; cart lines showed a
product id; empty images were large grey boxes.

## Acceptance criteria

- [ ] The renderer wraps every custom component in the page `Section` container (with the section's title /
      description when the spec gives them), so all sections share width and spacing.
- [ ] The custom component prompt says the component is rendered inside that container, fills its width and adds no
      container, page padding or `mx-auto`; the prompt version changes, so cached components are regenerated once.
- [ ] The isolated checks add a layout check: the render test (or a Playwright snapshot at page width) fails when
      the component is much narrower than its container or overflows it.
- [ ] A `currency` value format for decimal fields named like a price / amount / cost (and a spec override), used
      by the library sections and offered to custom components (`formatValue`).
- [ ] A missing image renders as a small neutral tile, not a full-size placeholder (until Epic 15 provides real
      images).
- [ ] Showing a referenced record's name instead of its id (cart line → product name) is designed here and either
      done or moved to its own story.

**Status:** planned (2026-10-29).
