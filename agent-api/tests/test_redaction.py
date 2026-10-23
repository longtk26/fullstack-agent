from src.libs.redaction import MASK, Redactor


def test_masks_known_values_and_credential_shapes():
    redactor = Redactor(["my-jwt-secret-value"])
    text = (
        "jwt=my-jwt-secret-value key=sk-ant-api03-abcdefghijkl google=AIzaSyA1234567890abcdefghijk "
        "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig "
        "db=postgresql+psycopg://bga:hunter2@postgres:5432/agent "
        '{"password": "pa55word", "accessToken": "tok-123456"}'
    )

    redacted = redactor.redact(text)

    for secret in ("my-jwt-secret-value", "sk-ant-api03", "AIzaSy", "eyJhbGci", "hunter2", "pa55word", "tok-123456"):
        assert secret not in redacted
    assert "postgresql+psycopg://bga:" + MASK + "@postgres" in redacted


def test_short_values_are_not_treated_as_secrets():
    assert Redactor(["abc"]).redact("abc abc") == "abc abc"


def test_redacts_nested_structures():
    redactor = Redactor(["supersecretvalue"])

    assert redactor.redact_obj({"a": ["x supersecretvalue"], "n": 3}) == {"a": [f"x {MASK}"], "n": 3}
