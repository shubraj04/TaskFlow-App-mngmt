import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { listTasks } from "../api/tasks";
import type { Paginated, Task, TaskQuery } from "../api/types";

export function useTasks(query: TaskQuery, myId: number) {
  const [data, setData] = useState<Paginated<Task> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    listTasks(query, myId, controller.signal)
      .then((page) => {
        setData(page);
        setError(null);
      })
      .catch((e: unknown) => {
        if (e instanceof DOMException && e.name === "AbortError") return; // superseded request
        setError(e instanceof ApiError ? e.message : "Could not load tasks. Is the API running?");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [query, myId, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { data, loading, error, reload };
}
