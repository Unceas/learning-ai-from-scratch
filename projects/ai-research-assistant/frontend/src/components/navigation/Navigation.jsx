/**
 * Navigation component.
 *
 * Persistent application header with branding, route navigation links,
 * authenticated user identity display, and sign out control.
 */

import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

export default function Navigation() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <nav className="navigation">
      <div className="navigation-brand">
        <div className="brand-mark">RA</div>
        <div>
          <strong>Research Assistant</strong>
          <span>AI Research Workspace</span>
        </div>
      </div>

      <div className="navigation-links">
        <NavLink
          to="/chat"
          className={({ isActive }) =>
            `navigation-link ${isActive ? "active" : ""}`
          }
        >
          Chat
        </NavLink>

        <NavLink
          to="/documents"
          className={({ isActive }) =>
            `navigation-link ${isActive ? "active" : ""}`
          }
        >
          Documents
        </NavLink>

        <span className="navigation-user">
          {user?.username || user?.user_id}
        </span>

        <button
          type="button"
          className="navigation-signout-btn"
          onClick={handleLogout}
        >
          Sign out
        </button>
      </div>
    </nav>
  );
}
