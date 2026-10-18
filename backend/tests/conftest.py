import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def _clear_cache():
    """Throttle counters live in the cache; isolate every test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def make_user(db):
    User = get_user_model()

    def _make(username="alice", password="Passw0rd!x", **extra):
        return User.objects.create_user(
            username=username, password=password, email=extra.pop("email", f"{username}@x.com"), **extra
        )

    return _make


@pytest.fixture
def alice(make_user):
    return make_user("alice")


@pytest.fixture
def bob(make_user):
    return make_user("bob")


@pytest.fixture
def auth_client():
    """Return a factory: auth_client(user) -> APIClient authenticated through a real JWT."""

    def _build(user, password="Passw0rd!x"):
        client = APIClient()
        res = client.post("/api/auth/token/", {"username": user.username, "password": password})
        assert res.status_code == 200, res.content
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return client

    return _build
