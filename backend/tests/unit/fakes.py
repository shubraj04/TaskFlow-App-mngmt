"""In-memory adapters: prove the use cases run with zero Django / database."""

from __future__ import annotations

import copy
from datetime import datetime

from apps.tasks.domain.entities import Task
from apps.tasks.domain.repositories import Page, TaskFilter, TaskNotifier, TaskRepository, UserRepository


class InMemoryTaskRepository(TaskRepository):
    def __init__(self):
        self._rows: dict[int, Task] = {}
        self._next = 1

    def add(self, task):
        task = copy.deepcopy(task)
        task.id = self._next
        self._next += 1
        self._rows[task.id] = task
        return copy.deepcopy(task)

    def get(self, task_id):
        row = self._rows.get(task_id)
        return copy.deepcopy(row) if row else None

    def save(self, task):
        self._rows[task.id] = copy.deepcopy(task)
        return copy.deepcopy(task)

    def delete(self, task_id):
        self._rows.pop(task_id, None)

    def list(self, c: TaskFilter, page, page_size):
        rows = [t for t in self._rows.values() if c.visible_to in (t.owner_id, t.assignee_id)]
        if c.status:
            rows = [t for t in rows if t.status == c.status]
        if c.due_before:
            rows = [t for t in rows if t.due_date and t.due_date <= c.due_before]
        if c.due_after:
            rows = [t for t in rows if t.due_date and t.due_date >= c.due_after]
        if c.assigned_to is not None:
            rows = [t for t in rows if t.assignee_id == c.assigned_to]
        rows.sort(key=lambda t: t.id)
        start = (page - 1) * page_size
        return Page(rows[start : start + page_size], len(rows), page, page_size)


class FakeUserRepository(UserRepository):
    def __init__(self, *ids: int):
        self.ids = set(ids)

    def exists(self, user_id):
        return user_id in self.ids


class RecordingNotifier(TaskNotifier):
    def __init__(self):
        self.calls: list[tuple[int, int]] = []

    def task_assigned(self, task_id, assignee_id):
        self.calls.append((task_id, assignee_id))


class FixedClock:
    def __init__(self, now: datetime):
        self.now = now

    def __call__(self):
        return self.now
