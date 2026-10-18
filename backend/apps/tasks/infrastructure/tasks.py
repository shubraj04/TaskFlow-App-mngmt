"""Celery tasks (background processing)."""

from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone

from ..domain.entities import TaskStatus
from .models import TaskModel


@shared_task(name="tasks.notify_task_assigned", ignore_result=True)
def notify_task_assigned(task_id: int) -> bool:
    """Tell the assignee they received a task. Returns False when nothing was sent."""
    task = TaskModel.objects.select_related("assignee", "owner").filter(pk=task_id).first()
    if task is None or task.assignee is None or not task.assignee.email:
        return False
    due = task.due_date.isoformat() if task.due_date else "no due date"
    send_mail(
        subject=f"[TaskFlow] You were assigned: {task.title}",
        message=f"{task.owner.username} assigned you '{task.title}' (due: {due}).",
        from_email=None,
        recipient_list=[task.assignee.email],
    )
    return True


@shared_task(name="tasks.send_due_soon_reminders")
def send_due_soon_reminders(days: int = 1) -> int:
    """Periodic job (Celery beat): remind assignees of open tasks due within ``days`` days."""
    today = timezone.now().date()
    horizon = today + timedelta(days=days)
    qs = (
        TaskModel.objects.select_related("assignee")
        .exclude(status=TaskStatus.COMPLETED.value)
        .filter(due_date__gte=today, due_date__lte=horizon, assignee__isnull=False)
    )
    sent = 0
    for task in qs:
        if not task.assignee.email:
            continue
        send_mail(
            subject=f"[TaskFlow] Due soon: {task.title}",
            message=f"'{task.title}' is due on {task.due_date.isoformat()}.",
            from_email=None,
            recipient_list=[task.assignee.email],
        )
        sent += 1
    return sent
