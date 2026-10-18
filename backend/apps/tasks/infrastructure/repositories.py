"""Django ORM implementations of the domain ports."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Q

from ..domain.entities import Task, TaskStatus
from ..domain.repositories import Page, TaskFilter, TaskRepository, UserRepository
from .models import TaskModel


def to_entity(row: TaskModel) -> Task:
    return Task(
        id=row.pk,
        title=row.title,
        description=row.description,
        status=TaskStatus(row.status),
        due_date=row.due_date,
        owner_id=row.owner_id,
        assignee_id=row.assignee_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        completed_at=row.completed_at,
    )


def _apply(row: TaskModel, task: Task) -> TaskModel:
    row.title = task.title
    row.description = task.description
    row.status = task.status.value
    row.due_date = task.due_date
    row.owner_id = task.owner_id
    row.assignee_id = task.assignee_id
    row.completed_at = task.completed_at
    return row


class DjangoTaskRepository(TaskRepository):
    def add(self, task: Task) -> Task:
        row = _apply(TaskModel(), task)
        row.save()
        return to_entity(row)

    def get(self, task_id: int) -> Task | None:
        row = TaskModel.objects.filter(pk=task_id).first()
        return to_entity(row) if row else None

    def save(self, task: Task) -> Task:
        row = _apply(TaskModel.objects.get(pk=task.id), task)
        row.save()
        return to_entity(row)

    def delete(self, task_id: int) -> None:
        TaskModel.objects.filter(pk=task_id).delete()

    def list(self, criteria: TaskFilter, page: int, page_size: int) -> Page:
        qs = TaskModel.objects.filter(Q(owner_id=criteria.visible_to) | Q(assignee_id=criteria.visible_to))
        if criteria.status:
            qs = qs.filter(status=criteria.status.value)
        if criteria.due_before:
            qs = qs.filter(due_date__lte=criteria.due_before)
        if criteria.due_after:
            qs = qs.filter(due_date__gte=criteria.due_after)
        if criteria.assigned_to is not None:
            qs = qs.filter(assignee_id=criteria.assigned_to)

        # secondary key keeps pagination stable when the primary key has ties
        qs = qs.order_by(criteria.ordering, "-id")
        total = qs.count()
        start = (page - 1) * page_size
        rows = qs[start : start + page_size]
        return Page(items=[to_entity(r) for r in rows], total=total, page=page, page_size=page_size)


class DjangoUserRepository(UserRepository):
    def exists(self, user_id: int) -> bool:
        return get_user_model().objects.filter(pk=user_id, is_active=True).exists()
