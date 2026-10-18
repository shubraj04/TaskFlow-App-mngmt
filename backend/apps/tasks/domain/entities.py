"""Task aggregate. No Django, no DRF: only business rules live here."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

from .exceptions import PermissionDenied, TaskAlreadyCompleted, ValidationError

TITLE_MAX_LENGTH = 200


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class Task:
    title: str
    owner_id: int
    description: str = ""
    status: TaskStatus = TaskStatus.TODO
    due_date: date | None = None
    assignee_id: int | None = None
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = field(default=None)

    # --- invariants ---------------------------------------------------------
    @staticmethod
    def validate_title(title: str) -> str:
        title = (title or "").strip()
        if not title:
            raise ValidationError({"title": "Title cannot be blank."})
        if len(title) > TITLE_MAX_LENGTH:
            raise ValidationError({"title": f"Title cannot exceed {TITLE_MAX_LENGTH} characters."})
        return title

    # --- access rules -------------------------------------------------------
    def is_owner(self, user_id: int) -> bool:
        return self.owner_id == user_id

    def is_participant(self, user_id: int) -> bool:
        return user_id in (self.owner_id, self.assignee_id)

    def ensure_can_edit(self, user_id: int) -> None:
        """Owner and assignee may edit or complete the task."""
        if not self.is_participant(user_id):
            raise PermissionDenied("You do not have access to this task.")

    def ensure_is_owner(self, user_id: int) -> None:
        """Only the owner may delete or (re)assign the task."""
        if not self.is_owner(user_id):
            raise PermissionDenied("Only the task owner can perform this action.")

    # --- behaviour ----------------------------------------------------------
    def assign_to(self, assignee_id: int | None) -> None:
        self.assignee_id = assignee_id

    def change_status(self, status: TaskStatus, now: datetime) -> None:
        if status == TaskStatus.COMPLETED:
            self.mark_completed(now)
            return
        self.status = status
        self.completed_at = None

    def mark_completed(self, now: datetime) -> None:
        if self.status == TaskStatus.COMPLETED:
            raise TaskAlreadyCompleted("Task is already completed.")
        self.status = TaskStatus.COMPLETED
        self.completed_at = now

    def is_overdue(self, today: date) -> bool:
        return self.due_date is not None and self.due_date < today and self.status != TaskStatus.COMPLETED
