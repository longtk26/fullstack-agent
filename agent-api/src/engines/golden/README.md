# Golden projects — TESTING ONLY

`two_entity/` and `shop/` are hand-written, convention-correct implementations of `examples/specs/two-entity.json`
and `examples/specs/shop.json`, split into the steps the fake engine replays (`database`, one directory per
module, and `tests_<module>`). Since Story 17.6 the templates (`orchestrator/backend_codegen.py`) write CRUD backends,
so these steps run only on the engine path (`options.crudFromTemplates=false`); they also remain the reference the
templates were modelled on. `flashcards/` (over its templated base `flashcards_base/`) completes the flashcards
app's custom operations. Frontends need no golden files: static sites render on the section library, dynamic apps on
the app kit (Epic 22; Story 22.8 removed the legacy dynamic golden frontend).

They are used only by the **fake engine** (`../fake_engine.py`, `demo_scenario`) and by tests
(`tests/generation_helpers.py`). Real engines never read them. See `docs/development/test-doubles.md`.
