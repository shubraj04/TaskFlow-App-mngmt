"""Ports (interfaces) the application layer depends on. Infrastructure implements them."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from .entities import Task, TaskStatus


@dataclass(frozen=True)
class TaskFilter:
    visible_to: int  # users only ever see tasks they own or are assigned to
    status: TaskStatus | None = None
    due_before: date | None = None
    due_after: date | None = None
    assigned_to: int | None = None
    ordering: str = "-created_at"


@dataclass(frozen=True)
class Page:
    items: list[Task]
    total: int
    page: int
    page_size: int


class TaskRepository(ABC):
    @abstractmethod
    def add(self, task: Task) -> Task: ...

    @abstractmethod
    def get(self, task_id: int) -> Task | None: ...

    @abstractmethod
    def save(self, task: Task) -> Task: ...

    @abstractmethod
    def delete(self, task_id: int) -> None: ...

    @abstractmethod
    def list(self, criteria: TaskFilter, page: int, page_size: int) -> Page: ...


class UserRepository(ABC):
    @abstractmethod
    def exists(self, user_id: int) -> bool: ...


class TaskNotifier(ABC):
    """Outbound port: tell somebody something happened (implemented with Celery)."""

    @abstractmethod
    def task_assigned(self, task_id: int, assignee_id: int) -> None: ...
