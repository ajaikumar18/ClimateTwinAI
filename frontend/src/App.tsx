import React, { Suspense } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  NavLink,
  Navigate,
  useLocation,
} from "react-router-dom";
import { CloudRain, LayoutDashboard, FlaskConical, Sparkles } from "lucide-react";
import ClimateDashboard from "./pages/ClimateDashboard";

const SimulatePage = React.lazy(() => import("./pages/SimulatePage"));

function AppShell() {
  const location = useLocation();

  return (
    <>
      <nav className="glass-nav sticky top-0 z-50 px-4 py-3 sm:px-6">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-3">
          <NavLink to="/" className="group flex items-center gap-3">
            <div className="relative rounded-2xl border border-cyan-500/20 bg-gradient-to-br from-cyan-500/20 to-blue-600/20 p-2.5 shadow-[0_0_30px_rgba(34,211,238,0.1)] transition-all duration-300 group-hover:border-cyan-400/40 group-hover:shadow-[0_0_40px_rgba(34,211,238,0.16)]">
              <CloudRain className="h-6 w-6 animate-float text-cyan-400" />
              <span className="absolute inset-0 rounded-2xl bg-cyan-400/10 opacity-0 blur-md transition-opacity duration-500 group-hover:opacity-100" />
            </div>
            <div className="flex flex-col">
              <span className="bg-gradient-to-r from-cyan-300 via-sky-300 to-blue-400 bg-clip-text text-lg font-semibold leading-tight text-transparent">
                ClimateTwin AI
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                Digital Twin Platform
              </span>
            </div>
          </NavLink>

          <div className="hidden items-center gap-2 rounded-full border border-slate-800/80 bg-slate-900/60 p-1.5 shadow-inner sm:flex">
            <NavLink
              to="/dashboard"
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition-all duration-300 ${
                  isActive
                    ? "bg-cyan-500/10 text-cyan-300 shadow-[0_0_20px_rgba(34,211,238,0.1)]"
                    : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                }`
              }
            >
              <LayoutDashboard className="h-4 w-4" />
              Dashboard
            </NavLink>

            <NavLink
              to="/simulate"
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition-all duration-300 ${
                  isActive
                    ? "bg-emerald-500/10 text-emerald-300 shadow-[0_0_20px_rgba(52,211,153,0.1)]"
                    : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                }`
              }
            >
              <FlaskConical className="h-4 w-4" />
              Simulator
            </NavLink>
          </div>

          <div className="relative flex items-center gap-2 overflow-hidden rounded-full border border-slate-700/50 bg-slate-800/60 px-3 py-1.5">
            <div className="absolute inset-0 animate-shimmer" />
            <Sparkles className="relative h-3.5 w-3.5 text-cyan-400" />
            <span className="relative text-xs font-semibold text-slate-400">
              Powered by <span className="text-cyan-400">IMD</span> + <span className="text-emerald-400">INSAT</span>
            </span>
          </div>
        </div>
      </nav>

      <main className="relative flex-1">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-48 bg-gradient-to-b from-cyan-500/5 to-transparent" />
        <div className="animate-fade-in-up h-full">
          <Suspense
            fallback={
              <div className="flex h-[60vh] items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                  <div className="h-12 w-12 animate-spin rounded-full border-4 border-cyan-500/20 border-t-cyan-400" />
                  <span className="text-sm font-medium text-slate-400">Loading module...</span>
                </div>
              </div>
            }
          >
            <Routes location={location}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<ClimateDashboard />} />
              <Route path="/simulate" element={<SimulatePage />} />
            </Routes>
          </Suspense>
        </div>
      </main>
    </>
  );
}

function App() {
  return (
    <Router>
      <AppShell />
    </Router>
  );
}

export default App;