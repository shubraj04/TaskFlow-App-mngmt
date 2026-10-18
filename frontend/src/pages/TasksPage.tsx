import { useCallback, useState } from "react";
import { completeTask, deleteTask, PAGE_SIZE } from "../api/tasks";
import { ApiError } from "../api/client";
import type { Task, TaskQuery } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import Pagination from "../components/Pagination";
import TaskCard from "../components/TaskCard";
import TaskFilters from "../components/TaskFilters";
import TaskFormModal from "../components/TaskFormModal";
import { useTasks } from "../hooks/useTasks";
import { useUsers } from "../hooks/useUsers";

const DEFAULT_QUERY: TaskQuery = { status: "", due_after: "", due_before: "", mine: false, ordering: "-created_at", page: 1 };

export default function TasksPage() {
  const { user, logout } = useAuth();
  const me = user!; // route guard in App guarantees a user
  const [query, setQuery] = useState<TaskQuery>(DEFAULT_QUERY);
  const { data, loading, error, reload } = useTasks(query, me.id);
  const { users, byId } = useUsers();
  const [editing, setEditing] = useState<Task | "new" | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [toast, setToast] = useState<{ text: string; error?: boolean } | null>(null);

  const notify = useCallback((text: string, isError = false) => {
    setToast({ text, error: isError });
    window.setTimeout(() => setToast(null), 3500);
  }, []);

  // any filter change returns to page 1
  const change = (changes: Partial<TaskQuery>) => setQuery((q) => ({ ...q, page: 1, ...changes }));

  async function run(task: Task, action: () => Promise<unknown>, success: string) {
    setBusyId(task.id);
    try {
      await action();
      notify(success);
      // deleting the last item of a page must not leave us on an empty page
      if (data && data.results.length === 1 && query.page > 1) setQuery((q) => ({ ...q, page: q.page - 1 }));
      else reload();
    } catch (e) {
      notify(e instanceof ApiError ? e.message : "Something went wrong.", true);
      reload();
    } finally {
      setBusyId(null);
    }
  }

  const tasks = data?.results ?? [];

  return (
    <div className="shell">
      <header className="topbar">
        <h1 className="brand">TaskFlow</h1>
        <div className="topbar-right">
          <span className="muted">Signed in as {me.username}</span>
          <button className="btn ghost" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>

      <main className="content">
        <div className="page-head">
          <h2>Your tasks</h2>
          <button className="btn primary" onClick={() => setEditing("new")}>
            New task
          </button>
        </div>

        <TaskFilters query={query} onChange={change} onReset={() => setQuery(DEFAULT_QUERY)} />

        {error && (
          <p className="banner error" role="alert">
            {error} <button className="link" onClick={reload}>Try again</button>
          </p>
        )}

        <section aria-busy={loading} aria-label="Task list">
          {loading && !data ? (
            <p className="muted">Loading tasks…</p>
          ) : tasks.length === 0 && !error ? (
            <div className="empty">
              <p>No tasks match these filters.</p>
              <button className="btn primary" onClick={() => setEditing("new")}>
                Create a task
              </button>
            </div>
          ) : (
            <ul className={`task-list ${loading ? "stale" : ""}`}>
              {tasks.map((t) => (
                <TaskCard
                  key={t.id}
                  task={t}
                  me={me}
                  usersById={byId}
                  busy={busyId === t.id}
                  onComplete={(task) => run(task, () => completeTask(task.id), "Task completed")}
                  onEdit={setEditing}
                  onDelete={(task) => run(task, () => deleteTask(task.id), "Task deleted")}
                />
              ))}
            </ul>
          )}
        </section>

        <Pagination page={query.page} count={data?.count ?? 0} pageSize={PAGE_SIZE} onChange={(page) => setQuery((q) => ({ ...q, page }))} />
      </main>

      {editing && (
        <TaskFormModal
          task={editing === "new" ? null : editing}
          me={me}
          users={users}
          onClose={() => setEditing(null)}
          onSaved={(msg) => {
            setEditing(null);
            notify(msg);
            reload();
          }}
        />
      )}

      {toast && (
        <div className={`toast ${toast.error ? "error" : ""}`} role="status">
          {toast.text}
        </div>
      )}
    </div>
  );
}
