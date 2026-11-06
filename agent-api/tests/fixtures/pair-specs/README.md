# Pair-check fixtures (TESTING ONLY)

Hand-written dynamic FrontendSpecs (the examples of the legacy dynamic flow, removed by Story 22.8), marked
`project.flow: "app"` so they validate. They bind library sections, forms, actions and Stats to the operations of
`examples/specs/shop.json`, `two-entity.json` and `flashcards.json`, which is all the pair check
(`checks/consistency.py`), `reconcile_spec_pair` and the input-validation tests need. Apps the agent builds come
from the app flow instead (`tests/generation_helpers.app_pair`); these are not planned or rendered.
