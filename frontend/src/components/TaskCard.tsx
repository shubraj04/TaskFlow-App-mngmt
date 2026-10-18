import { useState } from "react";
import { STATUS_LABEL, type Task, type User } from "../api/types";
import { dueHint } from "../utils/dates";

interface Props {
  task: Task;
  me: User;
  usersById: Map<number, User>;
  busy: boolean;
  onComplete: (task: Task) => void;
  onEdit: (task: Task) => void;
  onDelete: (task: Task) => void;
}

export default function TaskCard({ task, me, usersById, busy, onComplete, onEdit, onDelete }: Props) {
  const [confirming, setConfirming] = useState(false);
  const isOwner = task.owner_id === me.id;
  const name = (id: number | null) => (id === null ? "Unassigned" : id === me.id ? "you" : (usersById.get(id)?.username ?? `user ${id}`));

  return (
    <li className={`task ${task.status}`}>
      <div className="task-main">
        <div className="task-head">
          <h3>{task.title}</h3>
          <span className={`status ${task.status}`}>{STATUS_LABEL[task.status]}</span>
        </div>
        {task.description && <p className="task-desc">{task.description}</p>}
        <p className="task-meta">
          <span className={task.is_overdue ? "overdue" : ""}>{dueHint(task.due_date, task.is_overdue)}</span>
          <span>Owner: {name(task.owner_id)}</span>
          <span>Assigned to: {name(task.assignee_id)}</span>
        </p>
      </div>

      <div className="task-actions">
        {confirming ? (
          <>
            <span className="muted">Delete this task?</span>
            <button className="btn danger" disabled={busy} onClick={() => onDelete(task)}>
              Yes, delete
            </button>
            <button className="btn ghost" onClick={() => setConfirming(false)}>
              Keep
            </button>
          </>
        ) : (
          <>
            {task.status !== "completed" && (
              <button className="btn primary" disabled={busy} onClick={() => onComplete(task)}>
                Mark complete
              </button>
            )}
            <button className="btn" disabled={busy} onClick={() => onEdit(task)}>
              Edit
            </button>
            {isOwner && (
              <button className="btn ghost" disabled={busy} onClick={() => setConfirming(true)}>
                Delete
              </button>
            )}
          </>
        )}
      </div>
    </li>
  );
}
