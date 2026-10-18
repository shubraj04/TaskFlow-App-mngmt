import { useEffect, useMemo, useState } from "react";
import { fetchUsers } from "../api/auth";
import type { User } from "../api/types";

export function useUsers() {
  const [users, setUsers] = useState<User[]>([]);
  useEffect(() => {
    fetchUsers()
      .then(setUsers)
      .catch(() => setUsers([]));
  }, []);
  const byId = useMemo(() => new Map(users.map((u) => [u.id, u])), [users]);
  return { users, byId };
}
