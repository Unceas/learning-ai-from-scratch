/**
 * Token storage abstraction.
 *
 * Provides a single centralized interface for storing, reading, and clearing
 * JWT authentication tokens from browser local storage with SSR/Node guards.
 */

const TOKEN_KEY = "access_token";

export function getToken() {
  if (typeof localStorage === "undefined") {
    return null;
  }
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (typeof localStorage === "undefined") {
    return;
  }
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export function removeToken() {
  if (typeof localStorage === "undefined") {
    return;
  }
  localStorage.removeItem(TOKEN_KEY);
}
