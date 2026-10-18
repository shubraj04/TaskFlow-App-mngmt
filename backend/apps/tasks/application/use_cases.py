"""Use cases (application services). One class per user intention.

They orchestrate domain objects through the ports in ``domain.repositories`` and know
nothing about HTTP, Django or Celery.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from ..domain.entities import Task, TaskStatus
from ..domain.exceptions import TaskNotFound, UserNotFound, ValidationError
from ..domain.repositories import (
    Page,
    TaskFilter,
    TaskNotifier,
    TaskRepository,
    UserRepository,
)

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


def _get_or_raise(repo: TaskRepository, task_id: int) -> Task:
    task = repo.get(task_id)
    if task is None:
        raise TaskNotFound(f"Task {task_id} does not exist.")
    return task


def _ensure_user_exists(users: UserRepository, user_id: int) -> None:
    if not users.exists(user_id):
        raise UserNotFound(f"User {user_id} does not exist.")


def _validate_due_date_not_past(due: date | None, today: date) -> None:
    if due is not None and due < today:
        raise ValidationError({"due_date": "Due date cannot be in the past."})


# --- commands ---------------------------------------------------------------
@dataclass
class CreateTask:
    tasks: TaskRepository
    users: UserRepository
    notifier: TaskNotifier
    clock: Clock = utc_now

    def execute(
        self,
        *,
        actor_id: int,
        title: str,
        description: str = "",
        due_date: date | None = None,
        status: TaskStatus = TaskStatus.TODO,
        assignee_id: int | None = None,
    ) -> Task:
        now = self.clock()
        _validate_due_date_not_past(due_date, now.date())
        if assignee_id is not None:
            _ensure_user_exists(self.users, assignee_id)

        task = Task(
            title=Task.validate_title(title),
            description=description or "",
            due_date=due_date,
            owner_id=actor_id,
            assignee_id=assignee_id,
        )
        task.change_status(status, now)
        saved = self.tasks.add(task)
        if assignee_id is not None and assignee_id != actor_id:
            self.notifier.task_assigned(saved.id, assignee_id)
        return saved


@dataclass
class UpdateTask:
    """Partial update: only the keys present in ``changes`` are touched."""

    tasks: TaskRepository
    clock: Clock = utc_now

    EDITABLE = frozenset({"title", "description", "due_date", "status"})

    def execute(self, *, actor_id: int, task_id: int, changes: dict) -> Task:
        unknown = set(changes) - self.EDITABLE
        if unknown:
            raise ValidationError({k: "This field cannot be updated here." for k in unknown})

        task = _get_or_raise(self.tasks, task_id)
        task.ensure_can_edit(actor_id)
        now = self.clock()

        if "title" in changes:
            task.title = Task.validate_title(changes["title"])
        if "description" in changes:
            task.description = changes["description"] or ""
        if "due_date" in changes:
            if changes["due_date"] != task.due_date:
                _validate_due_date_not_past(changes["due_date"], now.date())
            task.due_date = changes["due_date"]
        if "status" in changes and changes["status"] != task.status:
            task.change_status(TaskStatus(changes["status"]), now)
        return self.tasks.save(task)


@dataclass
class AssignTask:
    tasks: TaskRepository
    users: UserRepository
    notifier: TaskNotifier

    def execute(self, *, actor_id: int, task_id: int, assignee_id: int | None) -> Task:
        task = _get_or_raise(self.tasks, task_id)
        task.ensure_is_owner(actor_id)
        if assignee_id is not None:
            _ensure_user_exists(self.users, assignee_id)

        changed = task.assignee_id != assignee_id
        task.assign_to(assignee_id)
        saved = self.tasks.save(task)
        if changed and assignee_id is not None and assignee_id != actor_id:
            self.notifier.task_assigned(saved.id, assignee_id)
        return saved


@dataclass
class CompleteTask:
    tasks: TaskRepository
    clock: Clock = utc_now

    def execute(self, *, actor_id: int, task_id: int) -> Task:
        task = _get_or_raise(self.tasks, task_id)
        task.ensure_can_edit(actor_id)
        task.mark_completed(self.clock())
        return self.tasks.save(task)


@dataclass
class DeleteTask:
    tasks: TaskRepository

    def execute(self, *, actor_id: int, task_id: int) -> None:
        task = _get_or_raise(self.tasks, task_id)
        task.ensure_is_owner(actor_id)
        self.tasks.delete(task_id)


# --- queries ----------------------------------------------------------------
@dataclass
class GetTask:
    tasks: TaskRepository

    def execute(self, *, actor_id: int, task_id: int) -> Task:
        task = _get_or_raise(self.tasks, task_id)
        task.ensure_can_edit(actor_id)  # participants only
        return task


@dataclass
class ListTasks:
    tasks: TaskRepository

    ALLOWED_ORDERING = frozenset({"created_at", "due_date", "title", "status"})

    def execute(
        self,
        *,
        actor_id: int,
        status: TaskStatus | None = None,
        due_before: date | None = None,
        due_after: date | None = None,
        assigned_to: int | None = None,
        ordering: str = "-created_at",
        page: int = 1,
        page_size: int = 10,
    ) -> Page:
        if ordering.lstrip("-") not in self.ALLOWED_ORDERING:
            raise ValidationError({"ordering": f"Choose one of {sorted(self.ALLOWED_ORDERING)}."})
        if due_before and due_after and due_after > due_before:
            raise ValidationError({"due_after": "due_after cannot be later than due_before."})
        if page < 1 or page_size < 1:
            raise ValidationError({"page": "page and page_size must be positive."})

        criteria = TaskFilter(
            visible_to=actor_id,
            status=status,
            due_before=due_before,
            due_after=due_after,
            assigned_to=assigned_to,
            ordering=ordering,
        )
        return self.tasks.list(criteria, page, page_size)
