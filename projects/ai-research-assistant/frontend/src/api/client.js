/**
 * Base API client with configuration, error handling, and development token bridge.
 */

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

export function getAuthToken() {
  return localStorage.getItem("token") || import.meta.env.VITE_DEV_TOKEN || null;
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem("token", token);
  } else {
    localStorage.removeItem("token");
  }
}

/**
 * Ensure an authentication token exists during development without requiring an auth UI.
 */
export async function ensureAuth() {
  let token = getAuthToken();
  if (token) return token;

  try {
    const devUser = import.meta.env.VITE_DEV_USER || "dev_researcher";
    const devPass = import.meta.env.VITE_DEV_PASSWORD || "password123";

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

  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

  const response = await fetch(
    `${API_BASE_URL}${endpoint}`,
    {
      ...options,
      headers: {
        ...(options.body instanceof FormData
          ? {}
          : { "Content-Type": "application/json" }),
        ...authHeaders,
        ...(options.headers || {}),
      },
    }
  );

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;

    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {
      // Keep default error message.
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}
