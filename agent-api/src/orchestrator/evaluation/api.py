"""Calls to a generated backend (its live preview) as the demo users of each role (Story 26.5, from the lab)."""

import json
import re
import secrets
import time
from typing import Any

import httpx

VAR = re.compile(r"\{\{\s*([A-Za-z0-9_.:-]+)\s*\}\}")


class EvaluationError(Exception):
    pass


def var_name(word: str) -> str:
    """A business word as a variable name: `service request` → `service_request`."""
    return re.sub(r"[^a-z0-9]+", "_", (word or "").lower()).strip("_")


def render(text: str, variables: dict[str, Any]) -> str:
    def swap(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        if name not in variables:
            raise EvaluationError(f"unresolved {{{{{name}}}}}")
        return str(variables[name])

    return VAR.sub(swap, text or "")


def get_path(value: Any, path: str) -> Any:
    for part in [p for p in (path or "").split(".") if p]:
        if isinstance(value, list) and part.isdigit():
            value = value[int(part)] if int(part) < len(value) else None
        elif isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


class Api:
    """`as_key` is a role (its first demo user) or `other:<role>` (a second user of that role)."""

    def __init__(self, base: str, auth: dict[str, Any] | None, operations: list[dict[str, Any]], timeout_s: float = 60):
        self.base = base.rstrip("/")
        self.auth = auth
        self.operations = {op["operationId"]: op for op in operations}
        self.timeout_s = timeout_s
        self.tokens: dict[str, str] = {}
        self.others: dict[str, tuple[str | None, str]] = {}

    def login_of(self, as_key: str) -> str | None:
        if not self.auth or as_key in ("", "anonymous"):
            return None
        other = as_key.startswith("other:")
        role = as_key.split(":", 1)[1] if other else as_key
        logins = self.auth["roles"].get(role) or []
        if not logins:
            raise EvaluationError(f"no demo user for role {role!r} (roles: {sorted(self.auth['roles'])})")
        if other and len(logins) < 2:
            login, why = self.sign_up_other(role)
            if login is None:
                raise EvaluationError(f"no second {role}: {why}")
            return login
        return logins[1] if other else logins[0]

    def sign_up_other(self, role: str) -> tuple[str | None, str]:
        """A second user of `role` when the app seeds only one: signed up through the app's own sign-up, kept only
        when `/auth/me` says it really has that role."""
        if role in self.others:
            return self.others[role]
        assert self.auth is not None
        login = f"eval-other-{role.replace('_', '-')}-{secrets.token_hex(3)}@example.com"
        credentials = {self.auth["field"]: login, "password": self.auth["password"]}
        try:
            response = httpx.post(self.base + self.auth["register"], json=credentials, timeout=30)
            if response.status_code not in (200, 201):
                self.others[role] = (None, f"sign-up refused ({response.status_code})")
                return self.others[role]
            signed = httpx.post(self.base + self.auth["login"], json=credentials, timeout=30)
            if signed.status_code != 200:
                self.others[role] = (None, f"the new account cannot sign in ({signed.status_code})")
                return self.others[role]
            token = signed.json()["accessToken"]
            me = httpx.get(self.base + self.auth["me"], headers={"Authorization": f"Bearer {token}"}, timeout=30)
        except httpx.HTTPError as exc:
            self.others[role] = (None, f"no answer: {exc!r}")
            return self.others[role]
        got = me.json().get("role") if me.status_code == 200 else None
        if got != role:
            self.others[role] = (None, f"sign-up gives role {got!r}, not {role!r}")
            return self.others[role]
        self.tokens[login] = token
        self.others[role] = (login, "")
        return self.others[role]

    def token(self, as_key: str) -> str | None:
        login = self.login_of(as_key)
        if login is None:
            return None
        if login not in self.tokens:
            assert self.auth is not None
            credentials = {self.auth["field"]: login, "password": self.auth["password"]}
            try:
                response = httpx.post(self.base + self.auth["login"], json=credentials, timeout=30)
            except httpx.HTTPError as exc:
                raise EvaluationError(f"sign-in as {login}: no answer ({exc!r})") from exc
            if response.status_code != 200:
                raise EvaluationError(f"sign-in as {login} failed: {response.status_code} {response.text[:200]}")
            self.tokens[login] = response.json()["accessToken"]
        return self.tokens[login]

    def user_variables(self) -> dict[str, Any]:
        """`user.<role>.email` / `.id` (and `user.other:<role>.…`) for every demo user, from `/auth/me`."""
        out: dict[str, Any] = {}
        if not self.auth:
            return out
        for role, logins in self.auth["roles"].items():
            for key, login in zip((role, f"other:{role}"), logins[:2], strict=False):
                out[f"user.{key}.email"] = login
                try:
                    status, data, _ = self.request("GET", self.auth["me"], None, None, key)
                except EvaluationError:
                    continue
                if status == 200 and isinstance(data, dict) and data.get("id"):
                    out[f"user.{key}.id"] = data["id"]
        return out

    def request(self, method: str, path: str, query: dict[str, Any] | None, body: Any, as_key: str):
        token = self.token(as_key)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        started = time.monotonic()
        try:
            response = httpx.request(
                method, self.base + path, params=query or None, json=body, headers=headers, timeout=self.timeout_s
            )
        except httpx.HTTPError as exc:
            return 0, f"no answer: {exc!r}", 0
        try:
            data = response.json()
        except ValueError:
            data = response.text[:500]
        return response.status_code, data, int((time.monotonic() - started) * 1000)

    def build(self, call: dict[str, Any], variables: dict[str, Any]) -> tuple[str, str, dict[str, Any], Any]:
        """(method, path, query, body) of a bound call: an operation id plus JSON texts with {{variables}}."""
        op = self.operations.get(call.get("operationId") or "")
        if op is None:
            raise EvaluationError(f"unknown operation {call.get('operationId')!r}")
        params = json.loads(render(call.get("pathParamsJson") or "", variables) or "{}")
        missing = [name for name in re.findall(r"\{([^}]+)\}", op["path"]) if name not in params]
        if missing:
            raise EvaluationError(f"{op['operationId']}: no value for path parameter(s) {missing}")
        path = re.sub(r"\{([^}]+)\}", lambda m: str(params[m.group(1)]), op["path"])
        query = json.loads(render(call.get("queryJson") or "", variables) or "{}")
        body_text = render(call.get("bodyJson") or "", variables)
        body = json.loads(body_text) if body_text.strip() else None
        return op["method"], path, query, body

    def call(self, call: dict[str, Any], variables: dict[str, Any], as_key: str) -> dict[str, Any]:
        """Runs a bound call; the result carries the evidence the report shows."""
        try:
            method, path, query, body = self.build(call, variables)
        except (EvaluationError, json.JSONDecodeError) as exc:
            return {"ok": None, "error": f"cannot build the call: {exc}", "as": as_key}
        try:
            status, data, ms = self.request(method, path, query, body, as_key)
        except EvaluationError as exc:
            return {"ok": None, "error": str(exc), "as": as_key, "call": f"{method} {path}"}
        return {"call": f"{method} {path}", "as": as_key, "status": status, "data": data, "ms": ms, "body": body}
