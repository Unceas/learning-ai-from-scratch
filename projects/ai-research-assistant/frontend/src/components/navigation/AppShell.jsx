/**
 * AppShell component.
 *
 * Persistent application frame providing sticky navigation and Outlet container.
 */

import { Outlet } from "react-router-dom";
import Navigation from "./Navigation";

export default function AppShell() {
  return (
    <div className="app-shell">
      <Navigation />

      <main className="app-content">
        <Outlet />
      </main>
    </div>
  );
}
