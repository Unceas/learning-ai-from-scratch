/**
 * Navigation component.
 *
 * Persistent application header with branding and route navigation links.
 */

import { NavLink } from "react-router-dom";

export default function Navigation() {
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
      </div>
    </nav>
  );
}
