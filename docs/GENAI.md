# GenAI usage

Tool: Claude (chat) used as a pair-programmer. This file records the prompt, a sample of the output,
and how the output was checked and corrected.

## 1. The prompt

```text
You are a senior Python engineer. Build a task-management REST API with Django + Django REST
Framework, following Clean Architecture.

Functional requirements
- Users can create, read, update, delete tasks; assign a task to another user; mark it completed.
- List endpoint is paginated and filterable by status and due date (before/after).
- A user only sees tasks they own or are assigned to. Owner and assignee may edit/complete;
  only the owner may delete or reassign. Completing an already-completed task is a 409.

Non-functional requirements
- JWT auth (simplejwt), rate limiting (DRF throttling), PostgreSQL in Docker / SQLite locally.
- Background work with Celery + Redis: e-mail the assignee after assignment, hourly due-soon reminder.
- drf-yasg Swagger docs, pyproject.toml, ruff, pre-commit.
- pytest + pytest-cov, fail under 80% coverage.

Architecture constraints
- Layers: domain (pure Python entities, repository/notifier ABCs, exceptions) ->
  application (one use case class per intention) -> infrastructure (ORM, Celery) ->
  presentation (DRF). Dependencies point inwards only; no Django imports in domain/application.
- Wire adapters in a single composition root. Map domain exceptions to HTTP in one exception handler.
- Write the use-case unit tests FIRST using in-memory fakes, then the HTTP integration tests.

Edge cases to handle explicitly: blank/oversized titles, past due dates, unknown assignee,
stranger access (403), missing task (404), invalid query params (400), page_size cap, stable
pagination ordering, enqueue Celery work only after the DB transaction commits.

Output: the file tree first, then each file. Do not invent endpoints beyond the list above.
```

## 2. Representative output (kept after review)

Use case, with ports injected and no framework imports:

```python
@dataclass
class AssignTask:
    tasks: TaskRepository
    users: UserRepository
    notifier: TaskNotifier

    def execute(self, *, actor_id: int, task_id: int, assignee_id: int | None) -> Task:
        task = _get_or_raise(self.tasks, task_id)
        task.ensure_is_owner(actor_id)
        if assignee_id is not None:
            _ensure_user_exists(self.users, assignee_id)
        changed = task.assignee_id != assignee_id
        task.assign_to(assignee_id)
        saved = self.tasks.save(task)
        if changed and assignee_id is not None and assignee_id != actor_id:
            self.notifier.task_assigned(saved.id, assignee_id)
        return saved
```

Adapter that defers the Celery enqueue until the transaction commits:

```python
class CeleryTaskNotifier(TaskNotifier):
    def task_assigned(self, task_id: int, assignee_id: int) -> None:
        transaction.on_commit(lambda: notify_task_assigned.delay(task_id))
```

## 3. How the output was validated

- **Ran everything.** `pytest` (62 tests, ~99% coverage), `ruff check`, `tsc --noEmit`, `vite build`, and a live
  smoke test: migrate -> seed -> `curl` the login and list endpoints; gunicorn with `DEBUG=false` for Swagger.
- **Tests as the specification.** Unit tests assert the business rules (permissions, double-complete,
  past due date, notify-once), and integration tests assert the HTTP contract (status codes, pagination
  links, filters, throttling returning 429).
- **Read the code against the architecture rule.** Checked that `domain/` and `application/` import nothing
  from Django/DRF/Celery and that only `presentation/container.py` knows concrete adapters.
- **Checked the library behaviour I relied on**, e.g. DRF skips serializer defaults on partial updates,
  so PATCH does not wipe `description`; a test covers PATCH and PUT separately.

## 4. Corrections and improvements made to the AI output

| # | Problem found | Fix |
|---|---|---|
| 1 | Reminder job added `timedelta(hours=...)` to a `date`; hours are silently truncated, so the window was wrong | Parameter became `days`, using `timedelta(days=...)` |
| 2 | A generated serializers module contained a broken placeholder import and did not run | Rewrote the file; the test run would have caught it |
| 3 | A generated overdue test was convoluted and failed (`AttributeError` on a test-client internal) | Rewrote with a plain ORM-created task for the logged-in user |
| 4 | PUT did not clear `due_date` when omitted (not truly "replace") | PUT now defaults `due_date` to `None` |
| 5 | With `DEBUG=false` Swagger UI assets would 404 under gunicorn | Added WhiteNoise; verified `/api/docs/` and the Swagger JS bundle return 200 |
| 6 | An invented `setuptools<81` pin "for drf-yasg" | Verified the installed drf-yasg does not use `pkg_resources`; removed the pin |
| 7 | `vite.config.ts` used `process` without Node types, so `tsc` failed | Added `@types/node` |
| 8 | Deleting the last item on page N would leave the UI on an empty page | UI steps back one page |

## 5. Edge cases, authentication and validation

- **AuthN/Z:** every endpoint requires a JWT except register/login/refresh; object-level rules live on the
  `Task` entity (`ensure_can_edit`, `ensure_is_owner`) so they are unit-tested without HTTP.
- **Validation split:** shape/type checks in DRF serializers; business rules (title, due date, unknown
  assignee, ordering whitelist, date-range sanity) in the domain/use cases.
- **Abuse:** throttling on all endpoints, stricter on login/register; `page_size` capped at 100;
  `ordering` is whitelisted, so no arbitrary column sorting.
- **Concurrency/consistency:** Celery enqueues after commit; list ordering has an `-id` tiebreaker.

## 6. Performance and idiomatic quality

- Indexes on `status`, `due_date` and a composite `(status, due_date)`; list queries are a single
  `COUNT` + a single page query (no N+1, since the API returns ids, not nested users).
- Idioms: dataclasses, `StrEnum`, type hints, ports as ABCs, `transaction.on_commit`, DRF throttling
  scopes, `AbortController` for stale requests on the client.
- Known gaps I would raise myself: no `select_related` needed today but would be once owners are
  nested; the `count()` becomes the bottleneck on very large tables (keyset pagination would fix it).
