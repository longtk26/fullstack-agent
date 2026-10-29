# Golden projects — TESTING ONLY

`two_entity/` and `shop/` are hand-written, convention-correct implementations of `examples/specs/two-entity.json`
and `examples/specs/shop.json`, split into the steps the fake engine replays (`database`, one directory per
module, and `tests_<module>`). `frontend/corner_shop/` is the golden frontend for
`examples/frontend-specs/shop-dynamic.json` on the engine path (its components without a `propsSchema`);
`frontend/custom_components/` holds its three custom components, written one by one when the section renderer builds
the site (Story 17.3). `static-landing.json` and `project-tracker-dynamic.json` need none: the
section renderer builds them without the engine (Stories 17.2, 17.4).

They are used only by the **fake engine** (`../fake_engine.py`, `demo_scenario`) and by tests
(`tests/generation_helpers.py`). Real engines never read them. See `docs/development/test-doubles.md`.
