import React, { Suspense } from "react";
import { BrowserRouter as Router, Routes, Route, NavLink, Navigate } from "react-router-dom";
import { CloudRain, LayoutDashboard, FlaskConical } from "lucide-react";
import ClimateDashboard from "./pages/ClimateDashboard";

const SimulatePage = React.lazy(() => import("./pages/SimulatePage"));

function App() {
  return (
    <Router>
      {/* ── Glassmorphic Navbar ────────────────── */}
      <nav className="glass-nav sticky top-0 z-50 px-6 py-3">
        <div className="max-w-[1400px] mx-auto flex items-center justify-between">
          {/* Logo & Brand */}
          <NavLink to="/" className="flex items-center gap-3 group">
            <div className="relative p-2 bg-gradient-to-br from-cyan-500/20 to-blue-600/20 rounded-xl border border-cyan-500/20 group-hover:border-cyan-400/40 transition-all duration-300">
              <CloudRain className="w-6 h-6 text-cyan-400 animate-float" />
              <div className="absolute inset-0 rounded-xl bg-cyan-400/10 blur-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-bold bg-gradient-to-r from-cyan-300 to-blue-400 bg-clip-text text-transparent leading-tight">
                ClimateTwin AI
              </span>
              <span className="text-[10px] text-slate-500 font-medium tracking-wider uppercase">
                Digital Twin Platform
              </span>
            </div>
          </NavLink>

          {/* Navigation Links */}
          <div className="flex items-center gap-2">
            <NavLink
              to="/dashboard"
              className={({ isActive }) =>
                `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-300 ${
                  isActive
                    ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 shadow-[0_0_20px_rgba(34,211,238,0.1)]"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                }`
              }
            >
              <LayoutDashboard className="w-4 h-4" />
              Dashboard
            </NavLink>

            <NavLink
              to="/simulate"
              className={({ isActive }) =>
                `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-300 ${
                  isActive
                    ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 shadow-[0_0_20px_rgba(52,211,153,0.1)]"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                }`
              }
            >
              <FlaskConical className="w-4 h-4" />
              Simulator
            </NavLink>
          </div>

          {/* Badge */}
          <div className="relative overflow-hidden px-4 py-1.5 rounded-full border border-slate-700/50 bg-slate-800/50">
            <div className="absolute inset-0 animate-shimmer" />
            <span className="relative text-xs font-semibold text-slate-400">
              Powered by <span className="text-cyan-400">IMD</span> + <span className="text-emerald-400">INSAT</span>
            </span>
          </div>
        </div>
      </nav>

      {/* ── Routes ─────────────────────────────── */}
      <main className="flex-1">
        <Suspense
          fallback={
            <div className="flex items-center justify-center h-[60vh]">
              <div className="flex flex-col items-center gap-4">
                <div className="w-12 h-12 border-4 border-cyan-500/20 border-t-cyan-400 rounded-full animate-spin" />
                <span className="text-slate-400 text-sm font-medium">Loading module...</span>
              </div>
            </div>
          }
        >
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<ClimateDashboard />} />
            <Route path="/simulate" element={<SimulatePage />} />
          </Routes>
        </Suspense>
      </main>
    </Router>
  );
}

export default App;