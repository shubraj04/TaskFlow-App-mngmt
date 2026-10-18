import { useEffect, useRef, useState, type FormEvent } from "react";
import { assignTask, createTask, updateTask } from "../api/tasks";
import { ApiError } from "../api/client";
import { STATUS_LABEL, type Task, type TaskStatus, type User } from "../api/types";
import { todayIso } from "../utils/dates";

interface Props {
  task: Task | null; // null = create
  me: User;
  users: User[];
  onClose: () => void;
  onSaved: (message: string) => void;
}

export default function TaskFormModal({ task, me, users, onClose, onSaved }: Props) {
  const isEdit = task !== null;
  const canAssign = !isEdit || task.owner_id === me.id;
  const [title, setTitle] = useState(task?.title ?? "");
  const [description, setDescription] = useState(task?.description ?? "");
  const [status, setStatus] = useState<TaskStatus>(task?.status ?? "todo");
  const [dueDate, setDueDate] = useState(task?.due_date ?? "");
  const [assignee, setAssignee] = useState<string>(task?.assignee_id ? String(task.assignee_id) : "");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const titleRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    titleRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      setErrors({ title: "Title cannot be blank." });
      return;
    }
    setBusy(true);
    setErrors({});
    const assigneeId = assignee ? Number(assignee) : null;
    try {
      if (!isEdit) {
        await createTask({ title, description, status, due_date: dueDate || null, assignee_id: assigneeId });
        onSaved("Task created");
      } else {
        await updateTask(task.id, { title, description, status, due_date: dueDate || null });
        if (canAssign && assigneeId !== task.assignee_id) await assignTask(task.id, assigneeId);
        onSaved("Task updated");
      }
    } catch (err) {
      if (err instanceof ApiError) setErrors({ ...err.fieldErrors, form: err.fieldErrors.detail ?? "" });
      else setErrors({ form: "Could not reach the server." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="task-form-title">
        <h2 id="task-form-title">{isEdit ? "Edit task" : "New task"}</h2>
        <form onSubmit={submit} noValidate>
          <label>
            Title
            <input ref={titleRef} value={title} maxLength={200} onChange={(e) => setTitle(e.target.value)} />
            {errors.title && <span className="field-error">{errors.title}</span>}
          </label>
          <label>
            Description
            <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
          </label>
          <div className="row">
            <label>
              Status
              <select value={status} onChange={(e) => setStatus(e.target.value as TaskStatus)}>
                {(Object.keys(STATUS_LABEL) as TaskStatus[]).map((s) => (
                  <option key={s} value={s}>
                    {STATUS_LABEL[s]}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Due date
              <input type="date" value={dueDate} min={isEdit ? undefined : todayIso()} onChange={(e) => setDueDate(e.target.value)} />
              {errors.due_date && <span className="field-error">{errors.due_date}</span>}
            </label>
          </div>
          <label>
            Assign to
            <select value={assignee} disabled={!canAssign} onChange={(e) => setAssignee(e.target.value)}>
              <option value="">Nobody</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.id === me.id ? `${u.username} (you)` : u.username}
                </option>
              ))}
            </select>
            {!canAssign && <span className="muted small">Only the owner can change the assignee.</span>}
            {errors.detail && <span className="field-error">{errors.detail}</span>}
          </label>
          {errors.form && (
            <p className="banner error" role="alert">
              {errors.form}
            </p>
          )}
          <div className="modal-actions">
            <button type="button" className="btn ghost" onClick={onClose}>
              Cancel
            </button>
            <button className="btn primary" disabled={busy}>
              {busy ? "Saving…" : isEdit ? "Save changes" : "Create task"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
