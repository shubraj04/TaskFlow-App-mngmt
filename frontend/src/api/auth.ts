import { request, tokens } from "./client";
import type { User } from "./types";

export async function login(username: string, password: string): Promise<User> {
  const res = await request<{ access: string; refresh: string }>("/auth/token/", {
    method: "POST",
    body: { username, password },
    auth: false,
  });
  tokens.set(res.access, res.refresh);
  return fetchMe();
}

export async function register(username: string, email: string, password: string): Promise<User> {
  await request("/auth/register/", { method: "POST", body: { username, email, password }, auth: false });
  return login(username, password);
}

export const fetchMe = () => request<User>("/auth/me/");
export const fetchUsers = () => request<User[]>("/users/");
