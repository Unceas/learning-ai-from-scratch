/**
 * Base API client with configuration, timeout handling, error normalization,
 * and authenticated session management.
 */

import { getToken, setToken, removeToken } from "../auth/storage";

const env = (typeof import.meta !== "undefined" && import.meta.env) ? import.meta.env : {};
const API_BASE_URL = env.VITE_API_URL || "http://localhost:8000";

const DEFAULT_TIMEOUT_MS = 60_000;

export function getAuthToken() {
  return (
    getToken() ||
    (typeof localStorage !== "undefined" ? localStorage.getItem("token") : null) ||
    env.VITE_DEV_TOKEN ||
    null
  );
}

export function setAuthToken(token) {
  setToken(token);
  if (typeof localStorage !== "undefined") {
    if (token) {
      localStorage.setItem("token", token);
    } else {
      localStorage.removeItem("token");
    }
  }
}

/**
 * Maps raw API/network errors into clear, friendly user explanations.
 */
export function getUserError(error) {
  if (!error) return "Something went wrong.";

  if (error.name === "AbortError" || error.message?.includes("took too long")) {
    return "The request took too long. Please try again.";
  }

  if (error.status === 401) {
    return "Your session has expired. Please sign in again.";
  }

  if (error.status === 404) {
    return "The requested resource could not be found.";
  }

  if (error.status >= 500) {
    return "The research assistant is temporarily unavailable.";
  }

  return error.message || "Something went wrong.";
}

/**
 * Dev-only authentication fallback if explicitly enabled via VITE_DEV_AUTH=true.
 */
export async function ensureAuth() {
  if (!(env.DEV && env.VITE_DEV_AUTH === "true")) {
    return null;
  }

  let token = getAuthToken();
  if (token) return token;

  try {
    const devUser = env.VITE_DEV_USER || "dev_researcher";
    const devPass = env.VITE_DEV_PASSWORD || "password123";

    // Attempt login first
    const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: devUser, password: devPass }),
    });

    if (res.ok) {
      const data = await res.json();
      setAuthToken(data.access_token);
      return data.access_token;
    }

    // If user does not exist yet, register dev user
    const regRes = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: devUser, password: devPass }),
    });

    if (regRes.ok) {
      const data = await regRes.json();
      setAuthToken(data.access_token);
      return data.access_token;
    }
  } catch {
    // Backend may be starting or offline
  }

  return null;
}

export async function apiFetch(endpoint, options = {}) {
  let token = getAuthToken();
  if (!token && !endpoint.startsWith("/api/auth/")) {
    token = await ensureAuth();
  }

  const headers = {
    ...options.headers,
  };

  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`;
  }

  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers["Content-Type"]
  ) {
    headers["Content-Type"] = "application/json";
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort();
  }, DEFAULT_TIMEOUT_MS);

  try {
    const response = await fetch(
      `${API_BASE_URL}${endpoint}`,
      {
        ...options,
        signal: options.signal || controller.signal,
        headers,
      }
    );

    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (response.status === 401) {
      if (typeof window !== "undefined" && typeof window.dispatchEvent === "function") {
        window.dispatchEvent(new Event("auth:expired"));
      }
    }

    if (!response.ok) {
      const message =
        data?.detail ||
        data?.message ||
        `Request failed (${response.status})`;

      const error = new Error(message);
      error.status = response.status;
      throw error;
    }

    if (response.status === 204) {
      return null;
    }

    return data;
  } catch (err) {
    if (err.name === "AbortError") {
      const timeoutErr = new Error("The request took too long. Please try again.");
      timeoutErr.name = "AbortError";
      throw timeoutErr;
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}
