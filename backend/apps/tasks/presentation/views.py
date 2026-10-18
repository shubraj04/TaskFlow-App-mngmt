from datetime import date

from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..domain.entities import TaskStatus
from ..domain.exceptions import ValidationError
from . import container
from .serializers import (
    AssignSerializer,
    TaskPageSerializer,
    TaskReadSerializer,
    TaskWriteSerializer,
    task_to_dict,
)

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100


def _render(task) -> dict:
    return TaskReadSerializer(task_to_dict(task, timezone.now().date())).data


def _int_param(request, name: str, default: int) -> int:
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValidationError({name: "Must be an integer."}) from None


def _date_param(request, name: str) -> date | None:
    raw = request.query_params.get(name)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValidationError({name: "Use the format YYYY-MM-DD."}) from None


def _page_url(request, page: int | None) -> str | None:
    if page is None:
        return None
    query = request.query_params.copy()
    query["page"] = str(page)
    return request.build_absolute_uri(f"{request.path}?{query.urlencode()}")


LIST_PARAMS = [
    openapi.Parameter(
        "status",
        openapi.IN_QUERY,
        description="todo | in_progress | completed",
        type=openapi.TYPE_STRING,
        enum=[s.value for s in TaskStatus],
    ),
    openapi.Parameter(
        "due_before",
        openapi.IN_QUERY,
        description="Due on or before (YYYY-MM-DD)",
        type=openapi.TYPE_STRING,
        format="date",
    ),
    openapi.Parameter(
        "due_after",
        openapi.IN_QUERY,
        description="Due on or after (YYYY-MM-DD)",
        type=openapi.TYPE_STRING,
        format="date",
    ),
    openapi.Parameter(
        "assignee", openapi.IN_QUERY, description="Filter by assignee user id", type=openapi.TYPE_INTEGER
    ),
    openapi.Parameter(
        "ordering",
        openapi.IN_QUERY,
        description="created_at, due_date, title or status; prefix '-' to reverse",
        type=openapi.TYPE_STRING,
    ),
    openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
    openapi.Parameter(
        "page_size", openapi.IN_QUERY, description=f"Max {MAX_PAGE_SIZE}", type=openapi.TYPE_INTEGER
    ),
]


class TaskListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(manual_parameters=LIST_PARAMS, responses={200: TaskPageSerializer})
    def get(self, request):
        """List tasks you own or are assigned to (paginated, filterable)."""
        status_raw = request.query_params.get("status")
        if status_raw and status_raw not in {s.value for s in TaskStatus}:
            raise ValidationError({"status": f"Choose one of {[s.value for s in TaskStatus]}."})
        assignee_raw = request.query_params.get("assignee")
        page = _int_param(request, "page", 1)
        page_size = min(_int_param(request, "page_size", DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE)

        result = container.list_tasks().execute(
            actor_id=request.user.id,
            status=TaskStatus(status_raw) if status_raw else None,
            due_before=_date_param(request, "due_before"),
            due_after=_date_param(request, "due_after"),
            assigned_to=_int_param(request, "assignee", 0) if assignee_raw else None,
            ordering=request.query_params.get("ordering", "-created_at"),
            page=page,
            page_size=page_size,
        )
        last_page = max(1, -(-result.total // page_size))
        return Response(
            {
                "count": result.total,
                "next": _page_url(request, page + 1 if page < last_page else None),
                "previous": _page_url(request, page - 1 if page > 1 else None),
                "results": [_render(t) for t in result.items],
            }
        )

    @swagger_auto_schema(request_body=TaskWriteSerializer, responses={201: TaskReadSerializer})
    def post(self, request):
        """Create a task. You become its owner; optionally assign it right away."""
        data = TaskWriteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        task = container.create_task().execute(
            actor_id=request.user.id,
            title=v["title"],
            description=v.get("description", ""),
            due_date=v.get("due_date"),
            status=TaskStatus(v.get("status", TaskStatus.TODO.value)),
            assignee_id=v.get("assignee_id"),
        )
        return Response(_render(task), status=status.HTTP_201_CREATED)


class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: TaskReadSerializer})
    def get(self, request, task_id: int):
        """Retrieve one task (owner or assignee only)."""
        task = container.get_task().execute(actor_id=request.user.id, task_id=task_id)
        return Response(_render(task))

    @swagger_auto_schema(request_body=TaskWriteSerializer, responses={200: TaskReadSerializer})
    def put(self, request, task_id: int):
        """Replace editable fields (title is required). Use /assign/ to change the assignee."""
        return self._update(request, task_id, partial=False)

    @swagger_auto_schema(request_body=TaskWriteSerializer, responses={200: TaskReadSerializer})
    def patch(self, request, task_id: int):
        """Partially update a task."""
        return self._update(request, task_id, partial=True)

    @swagger_auto_schema(responses={204: "Deleted"})
    def delete(self, request, task_id: int):
        """Delete a task (owner only)."""
        container.delete_task().execute(actor_id=request.user.id, task_id=task_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _update(self, request, task_id: int, *, partial: bool):
        data = TaskWriteSerializer(data=request.data, partial=partial)
        data.is_valid(raise_exception=True)
        changes = {k: v for k, v in data.validated_data.items() if k in request.data or not partial}
        changes.pop("assignee_id", None)  # assignment has its own endpoint/rules
        if not partial:
            changes.setdefault("description", "")
            changes.setdefault("due_date", None)  # PUT replaces the whole resource
        task = container.update_task().execute(actor_id=request.user.id, task_id=task_id, changes=changes)
        return Response(_render(task))


class TaskAssignView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=AssignSerializer, responses={200: TaskReadSerializer})
    def post(self, request, task_id: int):
        """Assign the task to a user (owner only). Send `assignee_id: null` to unassign."""
        data = AssignSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        task = container.assign_task().execute(
            actor_id=request.user.id,
            task_id=task_id,
            assignee_id=data.validated_data["assignee_id"],
        )
        return Response(_render(task))


class TaskCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT), responses={200: TaskReadSerializer}
    )
    def post(self, request, task_id: int):
        """Mark the task as completed (owner or assignee). 409 if it already is."""
        task = container.complete_task().execute(actor_id=request.user.id, task_id=task_id)
        return Response(_render(task))
