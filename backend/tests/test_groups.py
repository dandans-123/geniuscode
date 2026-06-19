from __future__ import annotations


def _register(client, email, password="secret123"):
    code = client.post("/auth/send-code", json={"email": email}).json()["code"]
    return client.post("/auth/register", json={"email": email, "password": password, "code": code}).json()


def _token(client, email):
    return _register(client, email)["access_token"]


def test_account_is_admin_flag(client):
    # 普通用户 → 非管理员
    normal = _register(client, "normaluser@example.com")["account"]
    assert normal["is_admin"] is False
    # ADMIN_EMAILS 里的邮箱 → 管理员
    admin = _register(client, "liuchulong163@gmail.com")["account"]
    assert admin["is_admin"] is True


def test_groups_require_admin(client):
    tok = _token(client, "notadmin@example.com")
    r = client.get("/auth/groups", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403


def test_group_crud_admin(client):
    tok = _token(client, "liuchulong163@gmail.com")
    h = {"Authorization": f"Bearer {tok}"}

    assert client.get("/auth/groups", headers=h).json()["groups"] == []

    created = client.post("/auth/groups", headers=h, json={
        "name": "VIP专线", "description": "高质量", "platform": "aicodewith",
        "rate_multiplier": 1.5, "rpm": 120, "visibility": "private", "billing_type": "standard",
    }).json()
    assert created["name"] == "VIP专线" and created["rate_multiplier"] == 1.5
    gid = created["id"]

    assert len(client.get("/auth/groups", headers=h).json()["groups"]) == 1

    upd = client.post(f"/auth/groups/{gid}", headers=h, json={
        "name": "VIP专线", "rate_multiplier": 2.0, "platform": "aicodewith",
        "rpm": 300, "visibility": "private", "billing_type": "standard", "description": "",
    }).json()
    assert upd["rate_multiplier"] == 2.0 and upd["rpm"] == 300

    assert client.delete(f"/auth/groups/{gid}", headers=h).json()["deleted"] is True
    assert client.get("/auth/groups", headers=h).json()["groups"] == []
