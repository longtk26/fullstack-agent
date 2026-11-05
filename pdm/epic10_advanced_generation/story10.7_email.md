# Story 10.7 — Email

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-34 · **Depends on:** 10.6

## User story

As a spec author, I want the app to send emails on events (a booking confirmation, a reminder) through any SMTP
provider; as a user of the agent, I want to see the emails a preview sent.

## Acceptance criteria

- [x] BackendSpec `emails[]` (additive): `name`, `to` (a field path such as `booking.user.email`, the current user, or
      a literal), `subject` and `body` with `{{placeholders}}` from the event payload, and a `trigger` as in 10.6. The
      validator checks paths and placeholders; the drafter writes the subject and body.
- [x] An `IEmailSender` port with an SMTP adapter and a console adapter (`EMAIL_BACKEND=smtp|console`), in
      `src/libs/email/`; Jinja templates in `src/templates/emails/<name>.{subject,html,txt}.j2`, HTML escaped.
- [x] Emails are always sent through jobs (10.6), so failures retry; env `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
      `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TLS`.
- [x] With 10.2: optional email verification and password reset (`auth.emailVerification`, `auth.passwordReset`)
      with signed, expiring tokens (their app screens:
      [22.7](../epic22_dynamic_app_frontend/story22.7_plugin_frontends.md)).
- [x] One shared Mailpit container for previews and sandboxes (SMTP and web UI bound to `127.0.0.1`); messages are
      tagged with the generation id, and the agent UI links to that generation's emails.
- [x] Template tests render each template; the validation smoke check triggers one email and finds it in Mailpit.
- [x] The console adapter is listed in `docs/development/test-doubles.md`.

## Status

**Done (2026-11-05)** on `feat/epic10-backend-plugins`.

- **Spec**: `emails[]` (additive): `name`, a `trigger` as in 10.6, `to` (a literal address or a path from the
  trigger's record through its references: `task.project.ownerEmail`), `subject` and `body` with `{{path}}`
  placeholders. The validator checks the trigger, the paths (each reference is a foreign key `<name>Id`) and every
  placeholder; a scheduled email takes a literal address and no placeholders. `auth.passwordReset` and
  `auth.emailVerification` (booleans, with JWT auth).
- **The `email` plugin** (`orchestrator/plugins/email.py`, `templates/plugins/email`, needs `jobs`, `jinja2==3.1.6`
  baked into the runner): `src/libs/email/` — the `IEmailSender` port, `SmtpEmailSender` and `ConsoleEmailSender`
  (`EMAIL_BACKEND=smtp|console`, console the default), `render` and `send_template` (Jinja, `StrictUndefined`, values
  escaped in the HTML part only; `X-Tags` from `EMAIL_TAG`; the job id as `Message-ID`). Each email becomes a job of
  its trigger (`emailTaskAdded`, `src/jobs/email_task_added.py`) that loads the records its paths reach and renders
  `src/templates/emails/<name>.{subject,txt,html}.j2`; failures retry as jobs do. Env `SMTP_HOST`, `SMTP_PORT`,
  `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TLS`, `EMAIL_TAG`, `APP_BASE_URL` (links).
- **Account emails** (the plugin's `account` module): `POST /auth/password-reset` (202 for any address, so it tells
  nobody which accounts exist), `/auth/password-reset/confirm` (a 30-minute token that also carries a fingerprint of
  the current password hash, so it works once), `/auth/email-verification` (signed in) and
  `/auth/email-verification/confirm` (48 hours; sets the user's new `emailVerifiedAt`); a wrong, used or expired token
  is 400 `INVALID_TOKEN` (added to the overlay's `ErrorCode`). The emails are sent by jobs.
- **Template tests**: every template renders with sample values, escaped in HTML; the account flows (a reset link
  sets a new password once and its email job sends; an unknown address gets the same answer and no email; a
  verification link verifies).
- **Mailpit**: one shared container (`src/sandbox/mail_service.py`, `axllent/mailpit:v1.31.2`, UI on
  `127.0.0.1:8125`, SMTP on `127.0.0.1:1125`) joins a sandbox's or preview's network as `mailpit`; previews tag their
  messages with the generation id, sandboxes with `sandbox-<id>`. The smoke check, after the worker's run, finds the
  generation's email in Mailpit when a scenario fires an email's trigger. The manifest's `email.inbox` links to the
  preview's messages, and the agent UI's API tab shows it ("Open this preview's inbox").
- The console adapter is listed in `docs/development/test-doubles.md`.

**Deviations:**

- `to: currentUser` is refused by the validator for now: events carry the record, not who made the change. A path to
  the user's address works (`booking.user.email`).
- The drafter does not write emails yet (drafting the backend's extras belongs with Epic 22's sign-in and screens).
- Mailpit's messages are not deleted with a generation; it keeps the newest 2000.
- Registering does not send the verification email by itself: the app asks for it (`/auth/email-verification`).

**Verified:** `make lint`, `pnpm exec tsc --noEmit`; `tests/test_email.py` (5) and the jobs tests; `make test` (all
pass after the contract and schema digest snapshots, whose only change is `specSha256`: the normalized spec now has
`emails: []`); `BGA_SANDBOX_TESTS=1` for an email generation through the workflow, without and with account emails
(`test_a_backend_that_sends_email_passes_its_tests_and_finds_its_email[emails|with-account-emails]`): every check
passes on the first try (47 template tests and 31 scenarios with account emails), and Mailpit holds the generation's
"New task", "Reset your password" and "Verify your email address" messages. `make up`, then a fake-engine backend
generation with account emails (`gen_01M6N7B1ZDKDWMB5VZ0WX2XY58`): creating a task emails the project's owner,
tagged with the generation, the project's name escaped in HTML (`Launch &lt;beta&gt;`); a reset request's link sets
a new password (204), which signs in, and the same link again is 400 `INVALID_TOKEN`; the manifest links the inbox.
