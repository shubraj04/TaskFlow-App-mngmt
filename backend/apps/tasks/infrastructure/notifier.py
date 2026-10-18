from django.db import transaction

from ..domain.repositories import TaskNotifier
from .tasks import notify_task_assigned


class CeleryTaskNotifier(TaskNotifier):
    def task_assigned(self, task_id: int, assignee_id: int) -> None:
        # Enqueue only after the DB transaction commits, so the worker can see the row.
        transaction.on_commit(lambda: notify_task_assigned.delay(task_id))
