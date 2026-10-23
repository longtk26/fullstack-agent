# Story 10.1 — JWT authentication generation

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-06

## User story

As a backend consumer, I want generated backends with working registration, login and protected endpoints when
the spec asks for JWT auth.

## Acceptance criteria

- [ ] When `spec.auth.type=jwt`, the planner adds a `users` module (the template's sample, which 5.2 removes, is the
      reference shape) with a `User` entity (or extends `auth.userEntity`) holding `email` (unique), `password_hash` and
      `role`, plus operations `auth.register` (201), `auth.login` (200, `{accessToken, tokenType}`) and `auth.me`.
- [ ] Deterministic overlay code (not LLM-generated, because it is security-sensitive): `src/libs/security/`
      (argon2/bcrypt hashing, PyJWT encode/decode, expiry from env) and `CurrentUserDep = Annotated[UserEntity,
      Depends(get_current_user)]`, following the skill's DI type-alias pattern. Login is rate-limited.
- [ ] Operations with `auth: jwt` require the bearer token (401 otherwise). OpenAPI declares a `bearerAuth` security
      scheme on exactly those operations.
- [ ] `JWT_SECRET` and `ACCESS_TOKEN_EXPIRE_MINUTES` come from env only. `.env.example` lists them without real values.
- [ ] Generated tests: register, login, `me`, wrong password 401, missing or expired token 401, duplicate email 409.
- [ ] Manifest `auth` block filled in (7.1).
