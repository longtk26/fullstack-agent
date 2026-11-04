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

- [ ] BackendSpec `payments` (additive): `provider: "fake"`, `entity`, `amountField` (or computed with a `sumEquals`
      rule), `currency` or `currencyField`, `statusField`, `paidStatus`, `failedStatus`.
- [ ] An `IPaymentProvider` port (`create_checkout`, `parse_webhook`) and a **fake adapter** in
      `src/libs/payments/`; a `payments` table (record, provider, session id, status, amount, currency, raw event).
- [ ] The amount always comes from the server-side record, never from the client; a second checkout for a paid record
      is refused (409).
- [ ] The fake checkout page lets the user pay, fail or cancel; it sends a signed webhook through 10.8's incoming
      path, so the real flow (signature, idempotency, job) is exercised. It refuses to run when `APP_ENV=production`.
- [ ] Marking paid uses the `transition` rule when the spec has one (10.4) and emits `<entity>.paid` (email and
      webhooks can subscribe).
- [ ] Frontend: a Pay action on the record, success and cancel pages that poll the status; MSW mocks the checkout.
- [ ] The port is documented for a developer adding Stripe (`PAYMENT_PROVIDER=stripe`, `STRIPE_SECRET_KEY`,
      `STRIPE_WEBHOOK_SECRET`, Checkout Sessions + `checkout.session.completed`); the Stripe adapter itself is a
      follow-up, not this story.
- [ ] Template tests: pay, fail, cancel, a repeated webhook, a forged signature, a second checkout; the validation
      smoke check pays a seeded record through the fake page.
- [ ] The fake provider is listed in `docs/development/test-doubles.md` as a feature of generated apps.

## Status

**Planned (2026-11-04).**
