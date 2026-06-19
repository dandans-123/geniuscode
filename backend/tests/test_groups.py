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


def test_my_groups_any_user(client):
    tok = _token(client, "u1@example.com")
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/auth/my-groups", headers=h).json()["groups"] == []
    g = client.post("/auth/my-groups", headers=h, json={"name": "我的项目A", "rpm": 120, "models": ["deepseek-v3.2"]}).json()
    assert g["name"] == "我的项目A" and g["rpm"] == 120
    assert g["models"] == ["deepseek-v3.2"] and g["rate_multiplier"] == 1.0  # 用户分组无费率,恒 1.0
    assert len(client.get("/auth/my-groups", headers=h).json()["groups"]) == 1
    assert client.delete(f"/auth/my-groups/{g['id']}", headers=h).json()["deleted"] is True


def test_my_groups_isolated_between_users(client):
    t1 = _token(client, "owner1@example.com")
    t2 = _token(client, "owner2@example.com")
    g = client.post("/auth/my-groups", headers={"Authorization": f"Bearer {t1}"}, json={"name": "私有"}).json()
    assert client.get("/auth/my-groups", headers={"Authorization": f"Bearer {t2}"}).json()["groups"] == []
    assert client.delete(f"/auth/my-groups/{g['id']}", headers={"Authorization": f"Bearer {t2}"}).status_code == 404


def test_admin_groups_exclude_user_groups(client):
    # 用户自建分组不应出现在管理员的平台分组列表里
    utok = _token(client, "uu@example.com")
    client.post("/auth/my-groups", headers={"Authorization": f"Bearer {utok}"}, json={"name": "用户组"})
    atok = _token(client, "liuchulong163@gmail.com")
    assert client.get("/auth/groups", headers={"Authorization": f"Bearer {atok}"}).json()["groups"] == []


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
