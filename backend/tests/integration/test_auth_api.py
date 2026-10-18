import pytest
from rest_framework.throttling import ScopedRateThrottle

pytestmark = pytest.mark.django_db


def test_register_login_me_flow(client):
    res = client.post(
        "/api/auth/register/",
        {"username": "newbie", "email": "n@x.com", "password": "Str0ngPass!"},
        content_type="application/json",
    )
    assert res.status_code == 201 and "password" not in res.json()

    tokens = client.post(
        "/api/auth/token/",
        {"username": "newbie", "password": "Str0ngPass!"},
        content_type="application/json",
    ).json()
    me = client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert me.status_code == 200 and me.json()["username"] == "newbie"

    refreshed = client.post(
        "/api/auth/token/refresh/", {"refresh": tokens["refresh"]}, content_type="application/json"
    )
    assert refreshed.status_code == 200 and "access" in refreshed.json()


def test_register_rejects_weak_password_and_duplicate_email(client, alice):
    weak = client.post(
        "/api/auth/register/",
        {"username": "u", "email": "u@x.com", "password": "123"},
        content_type="application/json",
    )
    assert weak.status_code == 400
    dup = client.post(
        "/api/auth/register/",
        {"username": "other", "email": "ALICE@x.com", "password": "Str0ngPass!"},
        content_type="application/json",
    )
    assert dup.status_code == 400 and "email" in dup.json()


def test_wrong_password_is_rejected(client, alice):
    res = client.post(
        "/api/auth/token/", {"username": "alice", "password": "nope"}, content_type="application/json"
    )
    assert res.status_code == 401


def test_protected_endpoints_require_token(client):
    assert client.get("/api/tasks/").status_code == 401
    assert client.get("/api/users/").status_code == 401
    assert client.get("/api/tasks/", HTTP_AUTHORIZATION="Bearer garbage").status_code == 401


def test_user_list_for_assignee_picker(auth_client, alice, bob):
    res = auth_client(alice).get("/api/users/")
    assert res.status_code == 200
    assert [u["username"] for u in res.json()] == ["alice", "bob"]


def test_login_is_rate_limited(client, alice, monkeypatch):
    monkeypatch.setitem(ScopedRateThrottle.THROTTLE_RATES, "auth", "3/min")
    codes = [
        client.post(
            "/api/auth/token/", {"username": "alice", "password": "bad"}, content_type="application/json"
        ).status_code
        for _ in range(5)
    ]
    assert codes[:3] == [401, 401, 401]
    assert codes[3:] == [429, 429]
