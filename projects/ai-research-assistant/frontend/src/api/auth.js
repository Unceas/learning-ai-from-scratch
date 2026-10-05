/**
 * Authentication API client.
 *
 * Handles user registration, login, and profile hydration against FastAPI auth endpoints.
 */

import { apiFetch } from "./client";

export async function login(credentials) {
  const payload = {
    user_id: credentials.user_id || credentials.username,
    username: credentials.username || credentials.user_id,
    password: credentials.password,
  };

  return apiFetch("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function register(credentials) {
  const payload = {
    user_id: credentials.user_id || credentials.username,
    username: credentials.username || credentials.user_id,
    password: credentials.password,
  };

  return apiFetch("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getCurrentUser() {
  return apiFetch("/api/auth/me");
}
