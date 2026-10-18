"""Translate domain errors into HTTP responses (keeps use cases HTTP-agnostic)."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from ..domain import exceptions as exc

_STATUS_MAP = {
    exc.TaskNotFound: status.HTTP_404_NOT_FOUND,
    exc.UserNotFound: status.HTTP_400_BAD_REQUEST,
    exc.PermissionDenied: status.HTTP_403_FORBIDDEN,
    exc.TaskAlreadyCompleted: status.HTTP_409_CONFLICT,
    exc.ValidationError: status.HTTP_400_BAD_REQUEST,
}


def api_exception_handler(error, context):
    if isinstance(error, exc.DomainError):
        code = next(
            (c for cls, c in _STATUS_MAP.items() if isinstance(error, cls)),
            status.HTTP_400_BAD_REQUEST,
        )
        body = error.errors if isinstance(error, exc.ValidationError) else {"detail": str(error)}
        return Response(body, status=code)
    return exception_handler(error, context)
