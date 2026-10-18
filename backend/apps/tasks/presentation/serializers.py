"""DRF serializers: HTTP <-> plain data. Business validation stays in the domain."""

from rest_framework import serializers

from ..domain.entities import Task, TaskStatus

STATUS_CHOICES = [s.value for s in TaskStatus]


class TaskWriteSerializer(serializers.Serializer):
    """Input for create (POST), full update (PUT) and partial update (PATCH)."""

    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(choices=STATUS_CHOICES, required=False)
    due_date = serializers.DateField(required=False, allow_null=True)
    assignee_id = serializers.IntegerField(required=False, allow_null=True)


class AssignSerializer(serializers.Serializer):
    assignee_id = serializers.IntegerField(allow_null=True)


class TaskReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField()
    status = serializers.CharField()
    due_date = serializers.DateField(allow_null=True)
    owner_id = serializers.IntegerField()
    assignee_id = serializers.IntegerField(allow_null=True)
    is_overdue = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True)


def task_to_dict(task: Task, today) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "due_date": task.due_date,
        "owner_id": task.owner_id,
        "assignee_id": task.assignee_id,
        "is_overdue": task.is_overdue(today),
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "completed_at": task.completed_at,
    }


class TaskPageSerializer(serializers.Serializer):
    """Documentation-only shape of the paginated list response."""

    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = TaskReadSerializer(many=True)
