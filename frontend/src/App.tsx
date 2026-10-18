import { useAuth } from "./auth/AuthContext";
import LoginPage from "./pages/LoginPage";
import TasksPage from "./pages/TasksPage";

export default function App() {
  const { user, loading } = useAuth();
  if (loading) return <p className="muted center">Loading…</p>;
  return user ? <TasksPage /> : <LoginPage />;
}
