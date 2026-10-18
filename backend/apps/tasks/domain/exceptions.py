"""Domain errors. Pure Python: the presentation layer maps them to HTTP codes."""


class DomainError(Exception):
    """Base class for every business-rule violation."""


class ValidationError(DomainError):
    def __init__(self, errors: dict[str, str] | str):
        self.errors = errors if isinstance(errors, dict) else {"detail": errors}
        super().__init__(str(self.errors))


class TaskNotFound(DomainError):
    pass


class UserNotFound(DomainError):
    pass


class PermissionDenied(DomainError):
    pass


class TaskAlreadyCompleted(DomainError):
    pass
