# Golden projects — TESTING ONLY

`two_entity/` and `shop/` are hand-written, convention-correct implementations of `examples/specs/two-entity.json`
and `examples/specs/shop.json`, split into the steps the fake engine replays (`database`, one directory per
module, and `tests_<module>`). `frontend/{project_tracker,corner_shop}/` are the corresponding golden frontends
for `examples/frontend-specs/{project-tracker-dynamic,shop-dynamic}.json`. `static-landing.json` needs none: the
section renderer builds it without the engine (Story 17.2).

They are used only by the **fake engine** (`../fake_engine.py`, `demo_scenario`) and by tests
(`tests/generation_helpers.py`). Real engines never read them. See `docs/development/test-doubles.md`.
