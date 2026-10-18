/** Local-date helpers. Dates travel as "YYYY-MM-DD" and are never parsed through UTC. */
export function parseDate(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function formatDate(iso: string | null): string {
  if (!iso) return "No due date";
  return parseDate(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export function todayIso(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function dueHint(iso: string | null, overdue: boolean): string {
  if (!iso) return "No due date";
  const days = Math.round((parseDate(iso).getTime() - parseDate(todayIso()).getTime()) / 86_400_000);
  if (overdue) return `${Math.abs(days)} day${Math.abs(days) === 1 ? "" : "s"} overdue`;
  if (days === 0) return "Due today";
  if (days === 1) return "Due tomorrow";
  return `Due ${formatDate(iso)}`;
}
