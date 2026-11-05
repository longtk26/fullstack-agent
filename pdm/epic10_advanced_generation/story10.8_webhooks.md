# Story 10.8 — Webhooks (outgoing and incoming)

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-34, FR-01 (item 10) · **Depends on:** 10.6

## User story

As an integrator, I want the generated app to notify my systems of its events with signed requests, and to accept
signed events from third parties (such as a payment provider) exactly once.

## Acceptance criteria

Outgoing:

- [x] BackendSpec `webhooks.outgoing.events` (additive) lists the events that can be subscribed to (10.6 names).
- [x] Tables `webhook_subscriptions` (url, secret, events, active) and `webhook_deliveries` (event, status, attempts,
      response code, last error); endpoints to manage subscriptions, list deliveries and send a test ping (admin role
      with 10.3).
- [x] Each delivery is a job (10.6) with backoff; the body is signed with HMAC-SHA256:
      `X-Webhook-Signature: t=<unix>,v1=<hex>` over `<t>.<body>`, plus `X-Webhook-Id` and `X-Webhook-Event`.
- [x] SSRF guard: private, loopback and link-local targets are refused unless `WEBHOOK_ALLOW_PRIVATE=true` (set in
      previews and sandboxes only); redirects are not followed; timeouts from env.

Incoming:

- [x] BackendSpec `webhooks.incoming[]`: `source`, `secretEnv`, and the events it handles (each to a job, built-in or
      engine-written).
- [x] `POST /webhooks/<source>` checks the signature and the timestamp window (`src/libs/webhooks/`), stores the
      event id in `webhook_events_received` (unique per source) so a repeat is answered 200 and ignored, and enqueues
      the handler.

Tests and checks:

- [x] Template tests: signature round trip, a tampered body and an old timestamp rejected, a repeated event handled
      once, a private target refused.
- [x] The validation smoke check delivers a webhook to a receiver inside the sandbox that verifies the signature.

## Status

**Done (2026-11-05)** on `feat/epic10-backend-plugins`.

- **Spec**: `webhooks.outgoing.events` (10.6 event names) and `webhooks.incoming[]` (`source`, `secretEnv`, `events`,
  `action` `log` or `custom` with a `description`); validated (events, unique sources, `subscriptions` and
  `deliveries` are taken).
- **The `webhooks` plugin** (`orchestrator/plugins/webhooks.py`, `templates/plugins/webhooks`, needs `jobs`):
  `src/libs/webhooks/` — `sign` / `verify` (HMAC-SHA256 over `<t>.<body>`, `X-Webhook-Signature: t=<unix>,v1=<hex>`,
  a timestamp window), `check_target` (the SSRF guard: http(s) only, no private, loopback, link-local, reserved or
  multicast address after DNS, unless `WEBHOOK_ALLOW_PRIVATE`), tables `webhook_subscriptions`, `webhook_deliveries`
  and `webhook_events_received` (unique per source), `fan_out` and `deliver` (httpx, no redirects,
  `WEBHOOK_TIMEOUT_SECONDS`; `X-Webhook-Id`, `X-Webhook-Event`; a delivered webhook is not sent again).
- **Outgoing**: each event is a job (`webhookOut<Event>`) that creates a delivery per active subscription, each a
  `webhooks.deliver` job retried with backoff (failed after 6 attempts). Routes: `GET|POST /webhooks/subscriptions`
  (the secret is answered once), `DELETE /webhooks/subscriptions/{subscriptionId}`, `POST …/{subscriptionId}/ping`,
  `GET /webhooks/deliveries`; for an admin when the spec has an `admin` role, a signed-in user with auth, open without.
- **Incoming**: `POST /webhooks/<source>` checks the signature against `<SECRET_ENV>` and its age
  (`WEBHOOK_TOLERANCE_SECONDS`), stores the event id (a repeat is answered 200 `duplicate`, not handled again),
  enqueues `webhookIn<Source><Type>` with `{id, type, data}` (`log` built in; `custom` an engine gap) and answers
  200 `accepted` (or `ignored` for a type it does not handle); a bad signature is 400 `INVALID_SIGNATURE`.
- **Template tests**: a signature round trip, a tampered body, another secret and an old timestamp refused; private
  targets refused; a subscription receives a signed ping from the worker and its delivery is recorded; an incoming
  event is handled once and a forged one is 400; an unknown event or private URL cannot be subscribed (422).
- **Validation**: the smoke check starts a receiver inside the sandbox, subscribes it (as the admin demo user with
  roles) and pings it before the worker's run, then checks the delivery's signature. Sandboxes and previews set
  `WEBHOOK_ALLOW_PRIVATE=true`; tests get it as their setting's test value.
- **Contract**: the routes with their errors and scenarios (unknown event, unknown id, unsigned), and
  `x-bga.webhooks` (outgoing events and the signature format, incoming sources).

**Deviations:**

- The incoming format is this app's own (`{id, type, data}`, the same signature header): a provider with its own
  scheme (Stripe) needs an adapter, which 10.9's note covers.
- Fixing the route parameter name took one sandbox run: the generated path said `{subscription_id}`, the plan
  `{subscriptionId}`; the fake engine's repair then broke the project (its repairs are not plugin-aware).

**Verified:** `make lint`; `tests/test_webhooks.py` (4); `make test` (all pass after the schema digest update);
`BGA_SANDBOX_TESTS=1` for a webhooks generation through the workflow, with roles and open
(`test_a_backend_with_webhooks_passes_its_tests_and_delivers_a_signed_webhook[admin|open]`): every check passes on the
first try (with roles: 47 template tests, 32 scenarios, the signed delivery to the sandbox's receiver, 20 operations
matching). `make up`, then a fake-engine backend generation of the open variant (`gen_01M6N8H0NBBKAV6FTAADCG33VQ`):
a subscription to `task.created` gets its secret once; creating a task delivers a webhook to a receiver on this
machine (`host.docker.internal`) whose signature verifies with that secret, and the delivery is listed as delivered
(200); an unsigned incoming event is 400; a non-http URL is `UNSAFE_TARGET`.
