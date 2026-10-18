from datetime import UTC, date, datetime

import pytest

from apps.tasks.domain.entities import Task, TaskStatus
from apps.tasks.domain.exceptions import PermissionDenied, TaskAlreadyCompleted, ValidationError

NOW = datetime(2026, 1, 10, 12, tzinfo=UTC)


def make(**kw):
    return Task(title="t", owner_id=1, **kw)


def test_title_is_trimmed_and_required():
    assert Task.validate_title("  hi  ") == "hi"
    with pytest.raises(ValidationError):
        Task.validate_title("   ")
    with pytest.raises(ValidationError):
        Task.validate_title("x" * 201)


def test_mark_completed_sets_timestamp_and_blocks_second_time():
    task = make()
    task.mark_completed(NOW)
    assert task.status is TaskStatus.COMPLETED and task.completed_at == NOW
    with pytest.raises(TaskAlreadyCompleted):
        task.mark_completed(NOW)


def test_reopening_clears_completed_at():
    task = make()
    task.mark_completed(NOW)
    task.change_status(TaskStatus.IN_PROGRESS, NOW)
    assert task.completed_at is None and task.status is TaskStatus.IN_PROGRESS


def test_access_rules():
    task = make(assignee_id=2)
    task.ensure_can_edit(1)
    task.ensure_can_edit(2)
    task.ensure_is_owner(1)
    with pytest.raises(PermissionDenied):
        task.ensure_can_edit(3)
    with pytest.raises(PermissionDenied):
        task.ensure_is_owner(2)


def test_overdue_logic():
    today = date(2026, 1, 10)
    assert make(due_date=date(2026, 1, 9)).is_overdue(today)
    assert not make(due_date=date(2026, 1, 10)).is_overdue(today)
    assert not make().is_overdue(today)
    done = make(due_date=date(2026, 1, 1), status=TaskStatus.COMPLETED)
    assert not done.is_overdue(today)
