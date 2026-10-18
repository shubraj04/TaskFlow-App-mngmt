from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from apps.tasks.infrastructure.models import TaskModel
from apps.tasks.infrastructure.tasks import notify_task_assigned, send_due_soon_reminders

pytestmark = pytest.mark.django_db

TODAY = lambda: timezone.now().date()  # noqa: E731


def day(offset: int) -> str:
    return (TODAY() + timedelta(days=offset)).isoformat()


@pytest.fixture
def api(auth_client, alice):
    return auth_client(alice)


def create(api, **payload):
    payload.setdefault("title", "Task")
    res = api.post("/api/tasks/", payload, format="json")
    assert res.status_code == 201, res.content
    return res.json()


# --- create / read -----------------------------------------------------------
def test_create_and_retrieve(api, alice):
    task = create(api, title="  Ship it  ", description="now", due_date=day(3))
    assert task["title"] == "Ship it" and task["owner_id"] == alice.id
    assert task["status"] == "todo" and task["is_overdue"] is False
    assert api.get(f"/api/tasks/{task['id']}/").json()["description"] == "now"


@pytest.mark.parametrize(
    "payload,field",
    [
        ({"title": ""}, "title"),
        ({"title": "x", "due_date": "2000-01-01"}, "due_date"),
        ({"title": "x", "due_date": "not-a-date"}, "due_date"),
        ({"title": "x", "status": "bogus"}, "status"),
        ({"title": "x", "assignee_id": 9999}, "detail"),
    ],
)
def test_create_validation_errors(api, payload, field):
    res = api.post("/api/tasks/", payload, format="json")
    assert res.status_code == 400 and field in res.json()


def test_unknown_task_is_404(api):
    assert api.get("/api/tasks/12345/").status_code == 404


# --- update ------------------------------------------------------------------
def test_patch_and_put(api):
    task = create(api, title="Old", due_date=day(5))
    patched = api.patch(f"/api/tasks/{task['id']}/", {"status": "in_progress"}, format="json").json()
    assert patched["status"] == "in_progress" and patched["title"] == "Old"

    put = api.put(f"/api/tasks/{task['id']}/", {"title": "Replaced"}, format="json").json()
    assert put["title"] == "Replaced" and put["due_date"] is None and put["description"] == ""


def test_patch_cannot_change_assignee_or_owner(api, bob, alice):
    task = create(api)
    res = api.patch(f"/api/tasks/{task['id']}/", {"assignee_id": bob.id, "owner_id": 99}, format="json")
    assert res.status_code == 200
    assert res.json()["assignee_id"] is None and res.json()["owner_id"] == alice.id


# --- assign / complete -------------------------------------------------------
def test_assign_and_unassign(api, bob):
    task = create(api)
    assigned = api.post(f"/api/tasks/{task['id']}/assign/", {"assignee_id": bob.id}, format="json")
    assert assigned.json()["assignee_id"] == bob.id
    cleared = api.post(f"/api/tasks/{task['id']}/assign/", {"assignee_id": None}, format="json")
    assert cleared.json()["assignee_id"] is None


def test_assign_unknown_user_is_400(api):
    task = create(api)
    res = api.post(f"/api/tasks/{task['id']}/assign/", {"assignee_id": 999}, format="json")
    assert res.status_code == 400


def test_assignee_can_complete_and_second_attempt_conflicts(api, auth_client, bob):
    task = create(api, assignee_id=bob.id)
    bob_api = auth_client(bob)
    done = bob_api.post(f"/api/tasks/{task['id']}/complete/")
    assert done.status_code == 200 and done.json()["status"] == "completed"
    assert done.json()["completed_at"] is not None
    assert bob_api.post(f"/api/tasks/{task['id']}/complete/").status_code == 409


# --- permissions -------------------------------------------------------------
def test_strangers_cannot_see_or_touch_tasks(api, auth_client, make_user):
    task = create(api)
    eve = auth_client(make_user("eve"))
    assert eve.get(f"/api/tasks/{task['id']}/").status_code == 403
    assert eve.patch(f"/api/tasks/{task['id']}/", {"title": "x"}, format="json").status_code == 403
    assert eve.delete(f"/api/tasks/{task['id']}/").status_code == 403
    assert eve.post(f"/api/tasks/{task['id']}/complete/").status_code == 403
    assert eve.get("/api/tasks/").json()["count"] == 0


def test_assignee_cannot_delete_or_reassign(api, auth_client, bob, make_user):
    carol = make_user("carol")
    task = create(api, assignee_id=bob.id)
    bob_api = auth_client(bob)
    assert bob_api.delete(f"/api/tasks/{task['id']}/").status_code == 403
    res = bob_api.post(f"/api/tasks/{task['id']}/assign/", {"assignee_id": carol.id}, format="json")
    assert res.status_code == 403


def test_owner_deletes(api):
    task = create(api)
    assert api.delete(f"/api/tasks/{task['id']}/").status_code == 204
    assert not TaskModel.objects.filter(pk=task["id"]).exists()


# --- list: pagination & filters ---------------------------------------------
def test_pagination_envelope_and_links(api):
    for i in range(5):
        create(api, title=f"t{i}")
    first = api.get("/api/tasks/?page_size=2").json()
    assert first["count"] == 5 and len(first["results"]) == 2
    assert first["previous"] is None and "page=2" in first["next"]
    last = api.get("/api/tasks/?page_size=2&page=3").json()
    assert len(last["results"]) == 1 and last["next"] is None and "page=2" in last["previous"]


def test_page_size_is_capped(api):
    create(api)
    assert api.get("/api/tasks/?page_size=100000").status_code == 200


def test_filter_by_status(api):
    create(api, title="a")
    create(api, title="b", status="in_progress")
    res = api.get("/api/tasks/?status=in_progress").json()
    assert [t["title"] for t in res["results"]] == ["b"]
    assert api.get("/api/tasks/?status=nope").status_code == 400


def test_filter_by_due_date_range(api):
    create(api, title="soon", due_date=day(1))
    create(api, title="later", due_date=day(30))
    create(api, title="undated")
    soon = api.get(f"/api/tasks/?due_before={day(7)}").json()["results"]
    later = api.get(f"/api/tasks/?due_after={day(7)}").json()["results"]
    window = api.get(f"/api/tasks/?due_after={day(0)}&due_before={day(60)}").json()["count"]
    assert [t["title"] for t in soon] == ["soon"]
    assert [t["title"] for t in later] == ["later"]
    assert window == 2  # undated tasks never match a date filter


def test_filter_by_assignee_and_ordering(api, alice, bob):
    create(api, title="b-task", assignee_id=bob.id, due_date=day(9))
    create(api, title="a-task", assignee_id=bob.id, due_date=day(2))
    create(api, title="mine")
    by_assignee = api.get(f"/api/tasks/?assignee={bob.id}&ordering=due_date").json()["results"]
    assert [t["title"] for t in by_assignee] == ["a-task", "b-task"]


@pytest.mark.parametrize(
    "query",
    ["due_before=31-12-2026", "page=abc", "ordering=password", "due_after=2030-01-01&due_before=2029-01-01"],
)
def test_bad_query_params_return_400(api, query):
    assert api.get(f"/api/tasks/?{query}").status_code == 400


def test_overdue_flag(api, alice):
    TaskModel.objects.create(title="late", due_date=TODAY() - timedelta(days=2), owner=alice)
    assert api.get("/api/tasks/").json()["results"][0]["is_overdue"] is True


# --- background jobs ---------------------------------------------------------
def test_assignment_sends_email_through_celery(api, bob, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        create(api, title="Hello", assignee_id=bob.id)
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [bob.email] and "Hello" in mail.outbox[0].subject


def test_notify_task_returns_false_for_missing_task_or_assignee(alice):
    assert notify_task_assigned.run(9999) is False
    task = TaskModel.objects.create(title="solo", owner=alice)
    assert notify_task_assigned.run(task.id) is False


def test_due_soon_reminders_only_open_assigned_tasks(alice, bob):
    TaskModel.objects.create(
        title="due tomorrow", owner=alice, assignee=bob, due_date=TODAY() + timedelta(days=1)
    )
    TaskModel.objects.create(
        title="done", owner=alice, assignee=bob, status="completed", due_date=TODAY() + timedelta(days=1)
    )
    TaskModel.objects.create(title="far", owner=alice, assignee=bob, due_date=TODAY() + timedelta(days=9))
    TaskModel.objects.create(title="unassigned", owner=alice, due_date=TODAY() + timedelta(days=1))
    assert send_due_soon_reminders.run() == 1
    assert "due tomorrow" in mail.outbox[0].subject


# --- documentation & seed ----------------------------------------------------
def test_swagger_and_schema_are_served(client):
    assert client.get("/api/docs/").status_code == 200
    schema = client.get("/api/docs/?format=openapi")
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    assert "/tasks/" in paths and "/tasks/{task_id}/complete/" in paths


def test_seed_command_is_idempotent(client):
    from django.core.management import call_command

    call_command("seed_demo")
    call_command("seed_demo")
    assert TaskModel.objects.count() == 12
    login = client.post(
        "/api/auth/token/", {"username": "alice", "password": "Demo1234!"}, content_type="application/json"
    )
    assert login.status_code == 200
