import { request } from "./client";
import type { Paginated, Task, TaskInput, TaskQuery } from "./types";

export const PAGE_SIZE = 8;

export function listTasks(q: TaskQuery, myId: number, signal?: AbortSignal) {
  const params = new URLSearchParams({ page: String(q.page), page_size: String(PAGE_SIZE), ordering: q.ordering });
  if (q.status) params.set("status", q.status);
  if (q.due_after) params.set("due_after", q.due_after);
  if (q.due_before) params.set("due_before", q.due_before);
  if (q.mine) params.set("assignee", String(myId));
  return request<Paginated<Task>>(`/tasks/?${params}`, { signal });
}

export const createTask = (input: TaskInput) => request<Task>("/tasks/", { method: "POST", body: input });

export const updateTask = (id: number, changes: Partial<Omit<TaskInput, "assignee_id">>) =>
  request<Task>(`/tasks/${id}/`, { method: "PATCH", body: changes });

export const assignTask = (id: number, assigneeId: number | null) =>
  request<Task>(`/tasks/${id}/assign/`, { method: "POST", body: { assignee_id: assigneeId } });

export const completeTask = (id: number) => request<Task>(`/tasks/${id}/complete/`, { method: "POST", body: {} });

export const deleteTask = (id: number) => request<void>(`/tasks/${id}/`, { method: "DELETE" });
