import { NavLink, Route, Routes } from "react-router-dom";
import { Compare } from "./pages/Compare";
import { Dashboard } from "./pages/Dashboard";
import { History } from "./pages/History";
import { SessionDetailPage } from "./pages/SessionDetailPage";

function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">VYBE</div>
          <div className="brand-sub">Virtual Yield &amp; Benchmarking Engine</div>
        </div>
        <nav className="nav">
          <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
            Dashboard
          </NavLink>
          <NavLink to="/history" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
            History
          </NavLink>
        </nav>
        <div className="sidebar-footer">
          GPU / data-center resource intelligence platform.
          <br />
          Measured, calculated, and estimated values are labeled throughout.
        </div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/history" element={<History />} />
          <Route path="/history/:id" element={<SessionDetailPage />} />
          <Route path="/compare" element={<Compare />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
