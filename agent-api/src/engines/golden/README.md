# Golden projects — TESTING ONLY

`two_entity/` is a hand-written, convention-correct implementation of `examples/specs/two-entity.json`, split
into the steps the fake engine replays (`database`, `projects`, `tasks`, `tests_projects`, `tests_tasks`).

It is used only by the **fake engine** (`../fake_engine.py`, `demo_scenario`) and by tests
(`tests/generation_helpers.py`). Real engines never read it. It only matches the two-entity example: a fake
run with any other spec fails validation. See `docs/development/test-doubles.md`.
