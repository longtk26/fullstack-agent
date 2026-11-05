# Story 10.7 — Email

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-34 · **Depends on:** 10.6

## User story

As a spec author, I want the app to send emails on events (a booking confirmation, a reminder) through any SMTP
provider; as a user of the agent, I want to see the emails a preview sent.

## Acceptance criteria

- [ ] BackendSpec `emails[]` (additive): `name`, `to` (a field path such as `booking.user.email`, the current user, or
      a literal), `subject` and `body` with `{{placeholders}}` from the event payload, and a `trigger` as in 10.6. The
      validator checks paths and placeholders; the drafter writes the subject and body.
- [ ] An `IEmailSender` port with an SMTP adapter and a console adapter (`EMAIL_BACKEND=smtp|console`), in
      `src/libs/email/`; Jinja templates in `src/templates/emails/<name>.{subject,html,txt}.j2`, HTML escaped.
- [ ] Emails are always sent through jobs (10.6), so failures retry; env `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
      `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TLS`.
- [ ] With 10.2: optional email verification and password reset (`auth.emailVerification`, `auth.passwordReset`)
      with signed, expiring tokens (their app screens:
      [22.7](../epic22_dynamic_app_frontend/story22.7_plugin_frontends.md)).
- [ ] One shared Mailpit container for previews and sandboxes (SMTP and web UI bound to `127.0.0.1`); messages are
      tagged with the generation id, and the agent UI links to that generation's emails.
- [ ] Template tests render each template; the validation smoke check triggers one email and finds it in Mailpit.
- [ ] The console adapter is listed in `docs/development/test-doubles.md`.

## Status

**Planned (2026-11-04).**
