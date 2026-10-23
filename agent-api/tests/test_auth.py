from src.libs.security import create_access_token


def test_login_returns_bearer_token(client):
    response = client.post("/api/v1/auth/login", json={"email": "user@test.local", "password": "userpass"})

    assert response.status_code == 200
    body = response.json()
    assert body["tokenType"] == "bearer"
    assert body["expiresIn"] > 0
    assert body["accessToken"]


def test_login_email_is_case_insensitive(client):
    response = client.post("/api/v1/auth/login", json={"email": "USER@test.local", "password": "userpass"})

    assert response.status_code == 200


def test_login_rejects_wrong_password_with_error_envelope(client):
    response = client.post("/api/v1/auth/login", json={"email": "user@test.local", "password": "nope"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_rejects_unknown_email_the_same_way(client):
    response = client.post("/api/v1/auth/login", json={"email": "ghost@test.local", "password": "userpass"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_validates_body(client):
    response = client.post("/api/v1/auth/login", json={"email": "not-an-email", "password": "x"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_is_rate_limited(client):
    statuses = [
        client.post("/api/v1/auth/login", json={"email": "user@test.local", "password": "nope"}).status_code
        for _ in range(6)
    ]

    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429


def test_me_requires_authentication(client):
    response = client.get("/api/v1/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_accepts_bearer_token(client, login):
    token = login("admin@test.local", "adminpass")

    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "admin@test.local"
    assert response.json()["role"] == "ADMIN"


def test_me_accepts_cookie_token_for_sse_clients(client, login):
    token = login("user@test.local", "userpass")

    response = client.get("/api/v1/me", cookies={"bga_token": token})
    client.cookies.clear()

    assert response.status_code == 200
    assert response.json()["role"] == "USER"


def test_me_rejects_tampered_token(client, login):
    token = login("user@test.local", "userpass")

    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token[:-2]}xx"})

    assert response.status_code == 401


def test_me_rejects_token_for_unknown_user(client):
    token, _ = create_access_token("00000000-0000-0000-0000-000000000000")

    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
