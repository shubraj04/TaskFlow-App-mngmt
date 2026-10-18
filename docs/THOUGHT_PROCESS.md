# Thought process

## 1. Reading the brief
The brief grades on Clean Architecture, tests, code quality, functionality, presentation and GenAI
fluency, so I optimised for *explainable structure* over feature count. I chose the suggested
"task management" domain, Django REST Framework (drf-yasg is named for Django) and React + TypeScript.

## 2. User story
> As a team member I want to create tasks, hand them to colleagues, and see what is overdue,
> so that nothing slips through the cracks.

Resulting rules: you see tasks you own or are assigned to; owner and assignee can edit and complete;
only the owner deletes or reassigns; completing twice is a conflict; past due dates are rejected.

## 3. Order of work (TDD-leaning)
1. **Domain + use cases first**, tested with in-memory fakes, so the business rules are pinned down
   before any framework code exists.
2. Django model, repositories, DRF views, JWT, throttling, integration tests through real HTTP.
3. Celery tasks (assignment e-mail after commit, periodic due-soon reminder).
4. Seed command, Docker/compose, pre-commit, README.
5. React client: API layer -> hooks -> pages/components.
6. GenAI write-up (`GENAI.md`).

## 4. Trade-offs I made on purpose
| Decision | Why | Cost |
|---|---|---|
| Hand-rolled use cases instead of "fat" DRF viewsets | Business rules testable without Django; shows separation of concerns | More files than a plain ModelViewSet |
| Domain `Task` dataclass separate from the ORM model | Independence of components | Mapping code in the repository |
| DRF throttling instead of a gateway | Built in, configurable via env, Redis-backed in Docker | Per-process counters without Redis |
| `localStorage` tokens | Simple for a demo | XSS exposure; would use httpOnly cookie in production |
| No frontend test suite | Time; backend carries the 80% requirement | Listed as next step |

## 5. What I would do next
Vitest/Testing Library for the UI, e2e with Playwright, a `GET /tasks/{id}/history` audit log,
optimistic UI updates, and moving reminders to per-user time zones.

## 6. Demo script (for the interview)
1. `docker compose up --build`, open the app, sign in as `alice`.
2. Filter by status and by due-date range; show pagination and the overdue badge.
3. Create a task assigned to `bob`; show the e-mail in the worker logs (Celery).
4. Sign in as `bob`: complete the task; try deleting it (blocked, owner-only).
5. Swagger at `/api/docs/`; show the 429 after repeated bad logins.
6. Walk through `domain/ -> application/ -> infrastructure/ -> presentation/`, then a unit test with fakes.
