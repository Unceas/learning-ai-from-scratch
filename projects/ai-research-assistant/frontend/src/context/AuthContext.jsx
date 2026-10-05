/**
 * Authentication Context and Provider.
 *
 * Manages authenticated user identity, session initialization, login, registration,
 * and automatic session expiration handling.
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";

import {
  getCurrentUser,
  login as loginRequest,
  register as registerRequest,
} from "../api/auth";

import {
  getToken,
  removeToken,
  setToken,
} from "../auth/storage";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function initializeAuth() {
      const token = getToken();

      if (!token) {
        setInitializing(false);
        return;
      }

      try {
        const currentUser = await getCurrentUser();
        setUser(currentUser);
      } catch {
        removeToken();
        setUser(null);
      } finally {
        setInitializing(false);
      }
    }

    initializeAuth();
  }, []);

  useEffect(() => {
    function handleExpired() {
      removeToken();
      setUser(null);
    }

    if (typeof window !== "undefined") {
      window.addEventListener("auth:expired", handleExpired);
      return () => {
        window.removeEventListener("auth:expired", handleExpired);
      };
    }
  }, []);

  async function login(credentials) {
    setError(null);

    try {
      const data = await loginRequest(credentials);
      setToken(data.access_token);

      const currentUser = await getCurrentUser();
      setUser(currentUser);
      return currentUser;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }

  async function register(credentials) {
    setError(null);

    try {
      await registerRequest(credentials);
      return await login(credentials);
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }

  function logout() {
    removeToken();
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        initializing,
        authenticated: Boolean(user),
        error,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}

export default AuthContext;
