import uuid


def test_create_contact_message__ok(client):
    response = client.post(
        "/contact-messages",
        json={"name": "Sam", "email": "sam@example.com", "message": "Hello from the street"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Sam" and body["email"] == "sam@example.com"
    assert uuid.UUID(body["id"]) and body["createdAt"]


def test_create_contact_message__invalid(client):
    assert client.post("/contact-messages", json={"name": "Sam"}).status_code == 422
    assert (
        client.post(
            "/contact-messages",
            json={"name": "", "email": "sam@example.com", "message": "Hi"},
        ).status_code
        == 422
    )
