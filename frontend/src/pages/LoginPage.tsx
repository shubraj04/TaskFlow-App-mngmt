import { useState, type FormEvent } from "react";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export default function LoginPage() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    try {
      if (mode === "login") await login(form.username, form.password);
      else await register(form.username, form.email, form.password);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrors(err.status === 401 ? { form: "Wrong username or password." } : { ...err.fieldErrors, form: "" });
        if (err.status === 429 || err.status >= 500) setErrors({ form: err.message });
      } else {
        setErrors({ form: "Could not reach the server." });
      }
    } finally {
      setBusy(false);
    }
  }

  const demo = (username: string) => setForm({ username, email: "", password: "Demo1234!" });

  return (
    <main className="login">
      <section className="login-card">
        <h1 className="brand">TaskFlow</h1>
        <p className="muted">Keep track of what you own and what others handed you.</p>

        <form onSubmit={submit} noValidate>
          <label>
            Username
            <input value={form.username} onChange={set("username")} autoComplete="username" required />
            {errors.username && <span className="field-error">{errors.username}</span>}
          </label>
          {mode === "register" && (
            <label>
              Email
              <input type="email" value={form.email} onChange={set("email")} autoComplete="email" required />
              {errors.email && <span className="field-error">{errors.email}</span>}
            </label>
          )}
          <label>
            Password
            <input
              type="password"
              value={form.password}
              onChange={set("password")}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
            />
            {errors.password && <span className="field-error">{errors.password}</span>}
          </label>
          {errors.form && (
            <p className="banner error" role="alert">
              {errors.form}
            </p>
          )}
          <button className="btn primary" disabled={busy}>
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>

        <button className="link" type="button" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "New here? Create an account" : "Have an account? Sign in"}
        </button>

        {mode === "login" && (
          <div className="demo">
            <p className="muted">Demo accounts (password Demo1234!)</p>
            <div className="chips">
              {["alice", "bob", "carol"].map((u) => (
                <button key={u} type="button" className="chip" onClick={() => demo(u)}>
                  {u}
                </button>
              ))}
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
