import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import ClimateDashboard from "./pages/ClimateDashboard";
import SimulatePage from "./pages/SimulatePage";

function App() {
  return (
    <Router>
      <nav className="bg-slate-900 border-b border-slate-800 p-4 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto flex gap-6">
          <Link to="/" className="text-emerald-400 font-semibold hover:text-emerald-300">Dashboard</Link>
          <Link to="/simulate" className="text-cyan-400 font-semibold hover:text-cyan-300">Scenario Simulator</Link>
        </div>
      </nav>
      <Routes>
        <Route path="/" element={<ClimateDashboard />} />
        <Route path="/simulate" element={<SimulatePage />} />
      </Routes>
    </Router>
  );
}

export default App;