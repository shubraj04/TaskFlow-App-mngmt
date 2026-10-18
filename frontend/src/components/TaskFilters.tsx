import { STATUS_LABEL, type TaskQuery, type TaskStatus } from "../api/types";

interface Props {
  query: TaskQuery;
  onChange: (changes: Partial<TaskQuery>) => void;
  onReset: () => void;
}

const ORDERINGS: [string, string][] = [
  ["-created_at", "Newest first"],
  ["created_at", "Oldest first"],
  ["due_date", "Due soonest"],
  ["-due_date", "Due latest"],
  ["title", "Title A–Z"],
];

export default function TaskFilters({ query, onChange, onReset }: Props) {
  return (
    <form className="filters" onSubmit={(e) => e.preventDefault()} aria-label="Filter tasks">
      <label>
        Status
        <select value={query.status} onChange={(e) => onChange({ status: e.target.value as TaskStatus | "" })}>
          <option value="">All</option>
          {(Object.keys(STATUS_LABEL) as TaskStatus[]).map((s) => (
            <option key={s} value={s}>
              {STATUS_LABEL[s]}
            </option>
          ))}
        </select>
      </label>
      <label>
        Due after
        <input type="date" value={query.due_after} max={query.due_before || undefined}
          onChange={(e) => onChange({ due_after: e.target.value })} />
      </label>
      <label>
        Due before
        <input type="date" value={query.due_before} min={query.due_after || undefined}
          onChange={(e) => onChange({ due_before: e.target.value })} />
      </label>
      <label>
        Sort
        <select value={query.ordering} onChange={(e) => onChange({ ordering: e.target.value })}>
          {ORDERINGS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label className="check">
        <input type="checkbox" checked={query.mine} onChange={(e) => onChange({ mine: e.target.checked })} />
        Assigned to me
      </label>
      <button type="button" className="btn ghost" onClick={onReset}>
        Clear filters
      </button>
    </form>
  );
}
