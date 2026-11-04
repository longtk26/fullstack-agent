# Story 10.8 — Webhooks (outgoing and incoming)

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-34, FR-01 (item 10) · **Depends on:** 10.6

## User story

As an integrator, I want the generated app to notify my systems of its events with signed requests, and to accept
signed events from third parties (such as a payment provider) exactly once.

## Acceptance criteria

Outgoing:

- [ ] BackendSpec `webhooks.outgoing.events` (additive) lists the events that can be subscribed to (10.6 names).
- [ ] Tables `webhook_subscriptions` (url, secret, events, active) and `webhook_deliveries` (event, status, attempts,
      response code, last error); endpoints to manage subscriptions, list deliveries and send a test ping (admin role
      with 10.3).
- [ ] Each delivery is a job (10.6) with backoff; the body is signed with HMAC-SHA256:
      `X-Webhook-Signature: t=<unix>,v1=<hex>` over `<t>.<body>`, plus `X-Webhook-Id` and `X-Webhook-Event`.
- [ ] SSRF guard: private, loopback and link-local targets are refused unless `WEBHOOK_ALLOW_PRIVATE=true` (set in
      previews and sandboxes only); redirects are not followed; timeouts from env.

Incoming:

- [ ] BackendSpec `webhooks.incoming[]`: `source`, `secretEnv`, and the events it handles (each to a job, built-in or
      engine-written).
- [ ] `POST /webhooks/<source>` checks the signature and the timestamp window (`src/libs/webhooks/`), stores the
      event id in `webhook_events_received` (unique per source) so a repeat is answered 200 and ignored, and enqueues
      the handler.

Tests and checks:

- [ ] Template tests: signature round trip, a tampered body and an old timestamp rejected, a repeated event handled
      once, a private target refused.
- [ ] The validation smoke check delivers a webhook to a receiver inside the sandbox that verifies the signature.

## Status

**Planned (2026-11-04).** Replaces the integration half of the old story 10.4 for webhooks; other integrations use
the plugin framework's fallback (10.1).
