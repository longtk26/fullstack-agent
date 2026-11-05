# Story 10.9 — Payments (fake provider first)

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-34 · **Depends on:** 10.8, 10.4

## User story

As a user of a generated app, I want to pay for an order or booking through a checkout page and see it marked
paid; as a developer, I want to switch to a real provider (Stripe first) by adding one adapter.

## Design (decision P6)

```
Pay ─▶ POST /<entity>s/{id}/checkout ─▶ provider.create_checkout(amount from the record, currency, urls)
     ◀── {checkoutUrl} ── browser opens it
fake checkout page (served by the backend): Pay / Fail / Cancel
     ─▶ signed webhook to POST /webhooks/payments (10.8) ─▶ job: mark paid (once), emit <entity>.paid
     ─▶ redirect to successUrl / cancelUrl ─▶ frontend shows the status
```

## Acceptance criteria

- [x] BackendSpec `payments` (additive): `provider: "fake"`, `entity`, `amountField` (or computed with a `sumEquals`
      rule), `currency` or `currencyField`, `statusField`, `paidStatus`, `failedStatus`.
- [x] An `IPaymentProvider` port (`create_checkout`, `parse_webhook`) and a **fake adapter** in
      `src/libs/payments/`; a `payments` table (record, provider, session id, status, amount, currency, raw event).
- [x] The amount always comes from the server-side record, never from the client; a second checkout for a paid record
      is refused (409).
- [x] The fake checkout page lets the user pay, fail or cancel; it sends a signed webhook through 10.8's incoming
      path, so the real flow (signature, idempotency, job) is exercised. It refuses to run when `APP_ENV=production`.
- [x] Marking paid uses the `transition` rule when the spec has one (10.4) and emits `<entity>.paid` (email and
      webhooks can subscribe).
- [x] `pay` is in `allowedActions` only for an unpaid record; a status endpoint the app's success and cancel screens poll (the Pay action and screens: [22.7](../epic22_dynamic_app_frontend/story22.7_plugin_frontends.md)).
- [x] The port is documented for a developer adding Stripe (`PAYMENT_PROVIDER=stripe`, `STRIPE_SECRET_KEY`,
      `STRIPE_WEBHOOK_SECRET`, Checkout Sessions + `checkout.session.completed`); the Stripe adapter itself is a
      follow-up, not this story.
- [x] Template tests: pay, fail, cancel, a repeated webhook, a forged signature, a second checkout; the validation
      smoke check pays a seeded record through the fake page.
- [x] The fake provider is listed in `docs/development/test-doubles.md` as a feature of generated apps.

## Status

**Done (2026-11-05)** on `feat/epic10-backend-plugins`.

- **Spec**: `payments` (additive): `provider: fake`, `entity`, `amountField` (or the field of a `sumEquals` rule on
  the entity), `currency` or `currencyField`, `statusField` (an enum), `paidStatus`, `failedStatus`; validated.
- **The `payments` plugin** (`orchestrator/plugins/payments.py`, `templates/plugins/payments`, needs `webhooks` and
  so `jobs`): `src/libs/payments/` — the `IPaymentProvider` port (`create_checkout`, `parse_webhook`; its docstring
  says how to add Stripe: `PAYMENT_PROVIDER=stripe`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, Checkout Sessions
  and `checkout.session.completed`), the `FakePaymentProvider`, the `payments` table (record, provider, session id,
  status, amount, currency, raw event, return URLs), `settle` and a generated `catalog.py` (`PAYABLE`).
- **Flow**: `POST /payments/<records>/{recordId}/checkout` (signed in with auth) takes the amount from the record
  (422 `NOTHING_TO_PAY` when not above zero; 409 `ALREADY_PAID` once paid) and answers the payment with its checkout
  URL; the fake page (`/payments/fake/checkout/<session>`, outside the OpenAPI, 404 when `APP_ENV=production`) pays,
  fails or cancels by posting a signed event to the app's own `/webhooks/payments` (10.8: signature, idempotency by
  event id, a job), then redirects to the checkout's `successUrl` / `cancelUrl` when given. The job settles the
  payment once and moves the record to `paidStatus` / `failedStatus` — through the spec's transition rule when there
  is one (10.4; a refusal leaves the record as it was and is recorded on the payment) — and a paid record emits
  `<entity>.paid` (emails and webhooks can subscribe). `GET /payments/{paymentId}` is what success and cancel screens
  poll. `pay` is in a record's `allowedActions` until it is paid (`x-bga.entities[...].actionPolicies.pay`).
- **Template tests**, in the entity's tests: pay, fail and cancel through the fake page and the worker (pay also checks
  the record's status and that `pay` is gone), and a second checkout of a paid record (409); the webhooks plugin's
  tests cover the repeated and the forged event of the `payments` source.
- **Validation**: the smoke check checks out a seeded unpaid record, pays on the fake page, runs the worker and finds
  the payment paid. Sandboxes and previews get a `PAYMENT_WEBHOOK_SECRET` (per job; derived per preview).
- The fake provider is listed in `docs/development/test-doubles.md`.

**Deviations:**

- No Stripe adapter (as planned: the port is documented for it).
- The fake page posts its event in-process (`httpx.ASGITransport` on the app) rather than over the network, so it
  works the same in tests and previews; it is still the real webhook route (signature, idempotency, job).
- A checkout is not limited to the record's owner (10.3); a policy on the entity does not reach the payments routes.

**Verified:** `make lint`; `tests/test_payments.py` (4); `make test` (all pass after the schema digest update);
`BGA_SANDBOX_TESTS=1` for a payments generation through the workflow, open and signed in with a transition rule
(`test_a_backend_with_payments_passes_its_tests_and_pays_a_seeded_record[...]`): every check passes on the first try
(signed in: 48 template tests, 30 scenarios, the smoke check's payment). Found on the way: a cancel left the payment
pending (the settling job failed on a log line); fixed before the run above. `make up`, then a fake-engine backend
generation of the signed-in variant (`gen_01M6N9KADR6TXT42FBXF2EK2SY`): a task of 12.50 lists `pay`; its checkout
answers the fake page (12.50 USD, three buttons); paying there settles it through the preview's worker; the task is
`PAID` without `pay` in its actions; a second checkout is 409 `ALREADY_PAID`.
