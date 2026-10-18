export type TaskStatus = "todo" | "in_progress" | "completed";

export const STATUS_LABEL: Record<TaskStatus, string> = {
  todo: "To do",
  in_progress: "In progress",
  completed: "Completed",
};

export interface Task {
  id: number;
  title: string;
  description: string;
  status: TaskStatus;
  due_date: string | null;
  owner_id: number;
  assignee_id: number | null;
  is_overdue: boolean;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface User {
  id: number;
  username: string;
  email: string;
}

export interface TaskInput {
  title: string;
  description: string;
  status: TaskStatus;
  due_date: string | null;
  assignee_id?: number | null;
}

export interface TaskQuery {
  status: TaskStatus | "";
  due_after: string;
  due_before: string;
  mine: boolean; // only tasks assigned to me
  ordering: string;
  page: number;
}
