interface Props {
  page: number;
  count: number;
  pageSize: number;
  onChange: (page: number) => void;
}

export default function Pagination({ page, count, pageSize, onChange }: Props) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (count === 0) return null;
  return (
    <nav className="pagination" aria-label="Pagination">
      <button className="btn" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        Previous
      </button>
      <span aria-live="polite">
        Page {page} of {pages} ({count} task{count === 1 ? "" : "s"})
      </span>
      <button className="btn" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Next
      </button>
    </nav>
  );
}
