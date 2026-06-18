from __future__ import annotations


def _register(client, email="alice@example.com", password="secret123"):
    code = client.post("/auth/send-code", json={"email": email}).json()["code"]
    return client.post("/auth/register", json={"email": email, "password": password, "code": code})


def test_register_grants_free_credit_and_key(client):
    r = _register(client)
    assert r.status_code == 200
    data = r.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    acc = data["account"]
    assert acc["email"] == "alice@example.com"
    assert acc["membership_tier"] == "free"
    assert acc["credit_balance_cny"] == 20.0  # FREE_TRIAL_CREDIT_CNY
    assert acc["api_key"].startswith("sk-geniuscode-")


def test_register_duplicate_email(client):
    _register(client, email="dup@example.com")
    # 已注册邮箱再发码 → 409(引导登录)
    r = client.post("/auth/send-code", json={"email": "dup@example.com"})
    assert r.status_code == 409


def test_send_code_dev_returns_code(client):
    r = client.post("/auth/send-code", json={"email": "newcode@example.com"})
    assert r.status_code == 200
    assert r.json().get("dev_mode") is True
    assert len(r.json()["code"]) == 6


def test_register_requires_valid_code(client):
    client.post("/auth/send-code", json={"email": "needcode@example.com"})
    # 无 code
    assert client.post("/auth/register", json={"email": "needcode@example.com", "password": "secret123"}).status_code == 400
    # 错误 code
    assert client.post("/auth/register", json={"email": "needcode@example.com", "password": "secret123", "code": "000000"}).status_code == 400


def test_register_weak_password(client):
    r = _register(client, email="bob@example.com", password="123")
    assert r.status_code == 400


def test_login_ok_and_bad(client):
    _register(client, email="carol@example.com", password="secret123")
    ok = client.post("/auth/login", json={"email": "carol@example.com", "password": "secret123"})
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = client.post("/auth/login", json={"email": "carol@example.com", "password": "wrong"})
    assert bad.status_code == 401


def test_account_requires_token(client):
    assert client.get("/auth/account").status_code == 401
    token = _register(client, email="dave@example.com").json()["access_token"]
    r = client.get("/auth/account", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "dave@example.com"


def test_membership_tiers_public(client):
    r = client.get("/auth/membership/tiers")
    assert r.status_code == 200
    ids = {t["id"] for t in r.json()["tiers"]}
    assert ids == {"starter", "pro", "ultimate"}


def test_purchase_membership_adds_credit(client):
    token = _register(client, email="erin@example.com").json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/auth/membership/purchase", json={"tier": "starter"}, headers=h)
    assert r.status_code == 200
    acc = r.json()
    assert acc["membership_tier"] == "starter"
    assert acc["credit_balance_cny"] == 20.0 + 399.0
    assert acc["membership_expires_at"] is not None


def test_purchase_unknown_tier(client):
    token = _register(client, email="frank@example.com").json()["access_token"]
    r = client.post("/auth/membership/purchase", json={"tier": "platinum"},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400


def test_chat_deducts_member_credit(client):
    acc = _register(client, email="gina@example.com").json()["account"]
    api_key = acc["api_key"]
    before = acc["credit_balance_cny"]

    chat = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "deepseek-v3.2", "messages": [{"role": "user", "content": "你好"}]},
    )
    assert chat.status_code == 200
    assert chat.json()["x_cost_usd"] >= 0

    # 账户余额应被扣减（成本以 ¥ 计）
    token = client.post("/auth/login", json={"email": "gina@example.com", "password": "secret123"}).json()["access_token"]
    after = client.get("/auth/account", headers={"Authorization": f"Bearer {token}"}).json()["credit_balance_cny"]
    assert after <= before


def test_topup_adds_credit(client):
    token = _register(client, email="ivy@example.com").json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/auth/topup", json={"amount_cny": 100}, headers=h)
    assert r.status_code == 200
    acc = r.json()
    assert acc["credit_balance_cny"] == 20.0 + 100.0
    assert acc["membership_expires_at"] is not None


def test_topup_below_min_rejected(client):
    token = _register(client, email="jack@example.com").json()["access_token"]
    r = client.post("/auth/topup", json={"amount_cny": 10},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400


def test_usage_empty_then_after_chat(client):
    reg = _register(client, email="kate@example.com").json()
    token = reg["access_token"]
    api_key = reg["account"]["api_key"]
    h = {"Authorization": f"Bearer {token}"}

    empty = client.get("/auth/usage", headers=h).json()
    assert empty["total_calls"] == 0

    client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "deepseek-v3.2", "messages": [{"role": "user", "content": "hi"}]},
    )

    u = client.get("/auth/usage", headers=h).json()
    assert u["total_calls"] >= 1
    assert u["total_tokens"] > 0
    assert len(u["recent"]) >= 1
    assert u["recent"][0]["model"] == "deepseek-v3.2"


def test_usage_requires_token(client):
    assert client.get("/auth/usage").status_code == 401


def test_chat_blocked_when_no_credit(client, db_session):
    from app.models.user import User

    acc = _register(client, email="hank@example.com").json()["account"]
    api_key = acc["api_key"]

    user = db_session.query(User).filter(User.email == "hank@example.com").first()
    user.credit_balance_cny = 0.0
    db_session.commit()

    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "deepseek-v3.2", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 402
