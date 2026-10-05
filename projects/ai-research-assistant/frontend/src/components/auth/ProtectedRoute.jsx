/**
 * Protected Route wrapper.
 *
 * Ensures only authenticated users access protected nested routes,
 * rendering a session check loader during initialization and redirecting
 * unauthenticated visitors to /login with return state.
 */

import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import LoadingState from "../common/LoadingState";

export default function ProtectedRoute({ children }) {
  const location = useLocation();
  const { authenticated, initializing } = useAuth();

  if (initializing) {
    return <LoadingState message="Checking session..." />;
  }

  if (!authenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{
          from: location.pathname + location.search,
        }}
      />
    );
  }

  return children;
}
