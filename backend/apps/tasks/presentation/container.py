"""Composition root: the only place where ports are bound to concrete adapters."""

from ..application import use_cases as uc
from ..infrastructure.notifier import CeleryTaskNotifier
from ..infrastructure.repositories import DjangoTaskRepository, DjangoUserRepository


def _deps():
    return DjangoTaskRepository(), DjangoUserRepository(), CeleryTaskNotifier()


def create_task() -> uc.CreateTask:
    tasks, users, notifier = _deps()
    return uc.CreateTask(tasks, users, notifier)


def update_task() -> uc.UpdateTask:
    return uc.UpdateTask(DjangoTaskRepository())


def assign_task() -> uc.AssignTask:
    tasks, users, notifier = _deps()
    return uc.AssignTask(tasks, users, notifier)


def complete_task() -> uc.CompleteTask:
    return uc.CompleteTask(DjangoTaskRepository())


def delete_task() -> uc.DeleteTask:
    return uc.DeleteTask(DjangoTaskRepository())


def get_task() -> uc.GetTask:
    return uc.GetTask(DjangoTaskRepository())


def list_tasks() -> uc.ListTasks:
    return uc.ListTasks(DjangoTaskRepository())
