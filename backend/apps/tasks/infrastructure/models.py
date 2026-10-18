from django.conf import settings
from django.db import models

from ..domain.entities import TaskStatus


class TaskModel(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name.replace("_", " ").title()) for s in TaskStatus],
        default=TaskStatus.TODO.value,
        db_index=True,
    )
    due_date = models.DateField(null=True, blank=True, db_index=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_tasks")
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tasks_task"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "due_date"], name="task_status_due_idx")]

    def __str__(self) -> str:
        return self.title
