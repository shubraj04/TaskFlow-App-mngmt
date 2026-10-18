# Django discovers models from this module; the real definition lives in infrastructure.
from .infrastructure.models import TaskModel

__all__ = ["TaskModel"]
