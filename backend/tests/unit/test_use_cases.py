from datetime import UTC, date, datetime

import pytest

from apps.tasks.application import use_cases as uc
from apps.tasks.domain.entities import TaskStatus
from apps.tasks.domain.exceptions import (
    PermissionDenied,
    TaskAlreadyCompleted,
    TaskNotFound,
    UserNotFound,
    ValidationError,
)

from .fakes import FakeUserRepository, FixedClock, InMemoryTaskRepository, RecordingNotifier

OWNER, ASSIGNEE, STRANGER = 1, 2, 3
CLOCK = FixedClock(datetime(2026, 1, 10, 9, tzinfo=UTC))


@pytest.fixture
def repo():
    return InMemoryTaskRepository()


@pytest.fixture
def notifier():
    return RecordingNotifier()


@pytest.fixture
def users():
    return FakeUserRepository(OWNER, ASSIGNEE, STRANGER)


@pytest.fixture
def created(repo, users, notifier):
    return uc.CreateTask(repo, users, notifier, CLOCK).execute(
        actor_id=OWNER, title="Write docs", due_date=date(2026, 1, 20)
    )


# --- create ------------------------------------------------------------------
def test_create_sets_owner_and_defaults(created):
    assert created.id == 1 and created.owner_id == OWNER
    assert created.status is TaskStatus.TODO and created.assignee_id is None


def test_create_rejects_blank_title_and_past_due_date(repo, users, notifier):
    create = uc.CreateTask(repo, users, notifier, CLOCK)
    with pytest.raises(ValidationError):
        create.execute(actor_id=OWNER, title=" ")
    with pytest.raises(ValidationError) as err:
        create.execute(actor_id=OWNER, title="x", due_date=date(2026, 1, 9))
    assert "due_date" in err.value.errors


def test_create_with_unknown_assignee_fails(repo, users, notifier):
    with pytest.raises(UserNotFound):
        uc.CreateTask(repo, users, notifier, CLOCK).execute(actor_id=OWNER, title="x", assignee_id=99)


def test_create_with_assignee_notifies_unless_self_assigned(repo, users, notifier):
    create = uc.CreateTask(repo, users, notifier, CLOCK)
    task = create.execute(actor_id=OWNER, title="a", assignee_id=ASSIGNEE)
    create.execute(actor_id=OWNER, title="b", assignee_id=OWNER)
    assert notifier.calls == [(task.id, ASSIGNEE)]


def test_create_as_completed_stamps_completion(repo, users, notifier):
    task = uc.CreateTask(repo, users, notifier, CLOCK).execute(
        actor_id=OWNER, title="done already", status=TaskStatus.COMPLETED
    )
    assert task.completed_at == CLOCK.now


# --- update ------------------------------------------------------------------
def test_update_changes_only_given_fields(repo, created):
    task = uc.UpdateTask(repo, CLOCK).execute(actor_id=OWNER, task_id=created.id, changes={"title": "New"})
    assert task.title == "New" and task.due_date == created.due_date


def test_update_rejects_unknown_fields_and_strangers(repo, created):
    update = uc.UpdateTask(repo, CLOCK)
    with pytest.raises(ValidationError):
        update.execute(actor_id=OWNER, task_id=created.id, changes={"owner_id": 5})
    with pytest.raises(PermissionDenied):
        update.execute(actor_id=STRANGER, task_id=created.id, changes={"title": "hack"})


def test_update_due_date_validation_only_when_changed(repo, users, notifier):
    past = uc.CreateTask(repo, users, notifier, FixedClock(datetime(2025, 1, 1, tzinfo=UTC))).execute(
        actor_id=OWNER, title="old", due_date=date(2025, 1, 5)
    )
    update = uc.UpdateTask(repo, CLOCK)
    # unchanged (already-past) due date is tolerated, e.g. when only the title changes
    update.execute(actor_id=OWNER, task_id=past.id, changes={"due_date": date(2025, 1, 5), "title": "ok"})
    with pytest.raises(ValidationError):
        update.execute(actor_id=OWNER, task_id=past.id, changes={"due_date": date(2025, 12, 1)})


def test_update_status_to_completed_and_back(repo, created):
    update = uc.UpdateTask(repo, CLOCK)
    done = update.execute(actor_id=OWNER, task_id=created.id, changes={"status": "completed"})
    assert done.completed_at == CLOCK.now
    reopened = update.execute(actor_id=OWNER, task_id=created.id, changes={"status": "todo"})
    assert reopened.completed_at is None


def test_update_missing_task(repo):
    with pytest.raises(TaskNotFound):
        uc.UpdateTask(repo, CLOCK).execute(actor_id=OWNER, task_id=42, changes={})


# --- assign ------------------------------------------------------------------
def test_assign_notifies_once_and_unassign_does_not(repo, users, notifier, created):
    assign = uc.AssignTask(repo, users, notifier)
    assign.execute(actor_id=OWNER, task_id=created.id, assignee_id=ASSIGNEE)
    assign.execute(actor_id=OWNER, task_id=created.id, assignee_id=ASSIGNEE)  # no change
    cleared = assign.execute(actor_id=OWNER, task_id=created.id, assignee_id=None)
    assert notifier.calls == [(created.id, ASSIGNEE)] and cleared.assignee_id is None


def test_assign_is_owner_only_and_validates_user(repo, users, notifier, created):
    assign = uc.AssignTask(repo, users, notifier)
    with pytest.raises(PermissionDenied):
        assign.execute(actor_id=STRANGER, task_id=created.id, assignee_id=STRANGER)
    with pytest.raises(UserNotFound):
        assign.execute(actor_id=OWNER, task_id=created.id, assignee_id=999)


# --- complete / delete / get -------------------------------------------------
def test_assignee_can_complete_but_not_twice(repo, users, notifier, created):
    uc.AssignTask(repo, users, notifier).execute(actor_id=OWNER, task_id=created.id, assignee_id=ASSIGNEE)
    complete = uc.CompleteTask(repo, CLOCK)
    assert complete.execute(actor_id=ASSIGNEE, task_id=created.id).status is TaskStatus.COMPLETED
    with pytest.raises(TaskAlreadyCompleted):
        complete.execute(actor_id=OWNER, task_id=created.id)


def test_delete_owner_only(repo, users, notifier, created):
    uc.AssignTask(repo, users, notifier).execute(actor_id=OWNER, task_id=created.id, assignee_id=ASSIGNEE)
    with pytest.raises(PermissionDenied):
        uc.DeleteTask(repo).execute(actor_id=ASSIGNEE, task_id=created.id)
    uc.DeleteTask(repo).execute(actor_id=OWNER, task_id=created.id)
    with pytest.raises(TaskNotFound):
        uc.GetTask(repo).execute(actor_id=OWNER, task_id=created.id)


def test_get_hidden_from_strangers(repo, created):
    with pytest.raises(PermissionDenied):
        uc.GetTask(repo).execute(actor_id=STRANGER, task_id=created.id)


# --- list --------------------------------------------------------------------
@pytest.fixture
def populated(repo, users, notifier):
    create = uc.CreateTask(repo, users, notifier, CLOCK)
    create.execute(actor_id=OWNER, title="a", due_date=date(2026, 1, 12))
    create.execute(actor_id=OWNER, title="b", due_date=date(2026, 2, 1), status=TaskStatus.IN_PROGRESS)
    create.execute(actor_id=STRANGER, title="hidden", due_date=date(2026, 1, 12))
    create.execute(actor_id=STRANGER, title="shared", assignee_id=OWNER)


def test_list_shows_only_visible_tasks(repo, populated):
    page = uc.ListTasks(repo).execute(actor_id=OWNER)
    assert sorted(t.title for t in page.items) == ["a", "b", "shared"]


def test_list_filters_by_status_and_due_date(repo, populated):
    lister = uc.ListTasks(repo)
    assert [t.title for t in lister.execute(actor_id=OWNER, status=TaskStatus.IN_PROGRESS).items] == ["b"]
    assert [t.title for t in lister.execute(actor_id=OWNER, due_before=date(2026, 1, 31)).items] == ["a"]
    assert [t.title for t in lister.execute(actor_id=OWNER, due_after=date(2026, 1, 31)).items] == ["b"]
    assert [t.title for t in lister.execute(actor_id=OWNER, assigned_to=OWNER).items] == ["shared"]


def test_list_paginates(repo, populated):
    page = uc.ListTasks(repo).execute(actor_id=OWNER, page=2, page_size=2)
    assert page.total == 3 and len(page.items) == 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ordering": "owner_id"},
        {"due_after": date(2026, 3, 1), "due_before": date(2026, 1, 1)},
        {"page": 0},
    ],
)
def test_list_rejects_bad_input(repo, kwargs):
    with pytest.raises(ValidationError):
        uc.ListTasks(repo).execute(actor_id=OWNER, **kwargs)
