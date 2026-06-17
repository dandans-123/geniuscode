from __future__ import annotations


def _member_key(client, email):
    r = client.post("/auth/register", json={"email": email, "password": "secret123"})
    return r.json()["account"]["api_key"]


def test_messages_basic(client):
    key = _member_key(client, "cc1@example.com")
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
        json={"model": "claude-code", "max_tokens": 256,
              "messages": [{"role": "user", "content": "Hello"}]},
    )
    assert r.status_code == 200
    d = r.json()
    assert d["type"] == "message"
    assert d["role"] == "assistant"
    assert d["content"][0]["type"] == "text"
    assert d["content"][0]["text"]
    assert "input_tokens" in d["usage"] and "output_tokens" in d["usage"]


def test_messages_accepts_bearer_too(client):
    key = _member_key(client, "cc2@example.com")
    r = client.post(
        "/v1/messages",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": "claude-code", "max_tokens": 64,
              "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200


def test_messages_no_auth(client):
    r = client.post("/v1/messages", json={"model": "claude-code", "max_tokens": 64,
                                          "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 401


def test_messages_stream(client):
    key = _member_key(client, "cc3@example.com")
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": key},
        json={"model": "claude-code", "max_tokens": 64, "stream": True,
              "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    body = r.text
    assert "message_start" in body
    assert "message_stop" in body


def test_messages_blocked_when_no_credit(client, db_session):
    from app.models.user import User
    key = _member_key(client, "cc4@example.com")
    user = db_session.query(User).filter(User.email == "cc4@example.com").first()
    user.credit_balance_cny = 0.0
    db_session.commit()
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": key},
        json={"model": "claude-code", "max_tokens": 64,
              "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 402
