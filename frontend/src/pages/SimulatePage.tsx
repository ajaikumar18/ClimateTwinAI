import { useState } from "react";
import {
  simulateScenario,
  type SimulateRequest,
  type SimulateResponse,
} from "../services/climateApi";
import {
  ComposedChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from "recharts";
import {
  AlertTriangle,
  Thermometer,
  Droplets,
  MapPin,
  Activity,
  ChevronRight,
  Zap,
  FlaskConical,
} from "lucide-react";

export default function SimulatePage() {
  const [lat, setLat] = useState<number>(22.5);
  const [lon, setLon] = useState<number>(79.0);
  const [variable, setVariable] = useState<"rainfall" | "tmax" | "tmin">(
    "rainfall"
  );
  const [tempDelta, setTempDelta] = useState<number>(0);
  const [rainfallMult, setRainfallMult] = useState<number>(1);
  const [horizon, setHorizon] = useState<number>(7);

  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<SimulateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload: SimulateRequest = {
        lat,
        lon,
        variable,
        temp_delta: tempDelta,
        rainfall_multiplier: rainfallMult,
        horizon_days: horizon,
      };
      const res = await simulateScenario(payload);
      setResult(res);
    } catch (err: any) {
      setError(
        err.response?.data?.detail || err.message || "Failed to run simulation"
      );
    } finally {
      setLoading(false);
    }
  };

  const combinedData = result
    ? result.baseline.map((b, i) => ({
        date: b.date,
        baseline: b.value,
        scenario: result.scenario[i].value,
        difference: result.delta[i].difference,
        percent_change: result.delta[i].percent_change,
      }))
    : [];

  return (
    <div className="min-h-screen bg-[#030712] text-slate-100">
      <div className="max-w-[1400px] mx-auto px-6 py-8 space-y-8">
        {/* Header */}
        <div className="animate-fade-in-up">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-emerald-500/10 rounded-xl text-emerald-400">
              <FlaskConical className="w-6 h-6" />
            </div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-300 to-cyan-300 bg-clip-text text-transparent">
              What-If Scenario Simulator
            </h1>
          </div>
          <p className="text-slate-500 ml-14">
            Perturb historical inputs to model future climate impacts using our
            trained AI digital twin.
          </p>
        </div>

        {/* Controls Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-fade-in-up-delay-1">
          <div className="glass-card p-6 space-y-6">
            <h2 className="text-lg font-semibold flex items-center gap-2 text-emerald-400">
              <Activity className="w-5 h-5" /> Scenario Parameters
            </h2>

            <div className="space-y-5">
              <div>
                <div className="flex justify-between mb-2">
                  <label className="text-sm font-medium text-slate-400 flex items-center gap-2">
                    <Thermometer className="w-4 h-4 text-rose-400" />
                    Temperature Delta
                  </label>
                  <span className="text-sm font-bold text-white px-2 py-0.5 bg-rose-500/10 rounded border border-rose-500/20">
                    {tempDelta > 0 ? "+" : ""}
                    {tempDelta}°C
                  </span>
                </div>
                <input
                  type="range"
                  min="-5"
                  max="5"
                  step="0.5"
                  value={tempDelta}
                  onChange={(e) => setTempDelta(parseFloat(e.target.value))}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-rose-500"
                />
                <div className="flex justify-between text-[10px] text-slate-600 mt-1">
                  <span>-5°C</span>
                  <span>+5°C</span>
                </div>
              </div>

              <div>
                <div className="flex justify-between mb-2">
                  <label className="text-sm font-medium text-slate-400 flex items-center gap-2">
                    <Droplets className="w-4 h-4 text-blue-400" />
                    Rainfall Multiplier
                  </label>
                  <span className="text-sm font-bold text-white px-2 py-0.5 bg-blue-500/10 rounded border border-blue-500/20">
                    {rainfallMult.toFixed(1)}x
                  </span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="2"
                  step="0.1"
                  value={rainfallMult}
                  onChange={(e) =>
                    setRainfallMult(parseFloat(e.target.value))
                  }
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                />
                <div className="flex justify-between text-[10px] text-slate-600 mt-1">
                  <span>0.5x (drought)</span>
                  <span>2.0x (flood)</span>
                </div>
              </div>
            </div>
          </div>

          <div className="glass-card p-6 space-y-6">
            <h2 className="text-lg font-semibold flex items-center gap-2 text-cyan-400">
              <MapPin className="w-5 h-5" /> Location & Target
            </h2>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">
                  Latitude
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={lat}
                  onChange={(e) => setLat(parseFloat(e.target.value))}
                  className="w-full bg-slate-800/80 border border-slate-700/50 rounded-lg px-3 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-cyan-500/50 focus:shadow-[0_0_15px_rgba(34,211,238,0.1)] transition-all"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">
                  Longitude
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={lon}
                  onChange={(e) => setLon(parseFloat(e.target.value))}
                  className="w-full bg-slate-800/80 border border-slate-700/50 rounded-lg px-3 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-cyan-500/50 focus:shadow-[0_0_15px_rgba(34,211,238,0.1)] transition-all"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">
                  Target Variable
                </label>
                <select
                  value={variable}
                  onChange={(e: any) => setVariable(e.target.value)}
                  className="w-full bg-slate-800/80 border border-slate-700/50 rounded-lg px-3 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-cyan-500/50 transition-all"
                >
                  <option value="rainfall">Rainfall (mm)</option>
                  <option value="tmax">Max Temp (°C)</option>
                  <option value="tmin">Min Temp (°C)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">
                  Horizon (Days)
                </label>
                <input
                  type="number"
                  min="1"
                  max="7"
                  value={horizon}
                  onChange={(e) => setHorizon(parseInt(e.target.value))}
                  className="w-full bg-slate-800/80 border border-slate-700/50 rounded-lg px-3 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-cyan-500/50 transition-all"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex justify-end animate-fade-in-up-delay-2">
          <button
            onClick={runSimulation}
            disabled={loading}
            className="group relative inline-flex items-center justify-center px-8 py-3.5 text-sm font-bold text-white transition-all duration-300 bg-gradient-to-r from-emerald-500 to-cyan-600 rounded-xl hover:from-emerald-400 hover:to-cyan-500 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden shadow-[0_0_30px_rgba(16,185,129,0.2)] hover:shadow-[0_0_50px_rgba(16,185,129,0.4)]"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg
                  className="animate-spin h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Simulating...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Zap className="w-5 h-5" />
                Run Simulation
                <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </span>
            )}
          </button>
        </div>

        {error && (
          <div className="p-4 glass-card-static border-red-500/30 bg-red-900/10 flex items-start gap-3 animate-fade-in-up">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <p className="text-red-300 text-sm">{error}</p>
          </div>
        )}

        {/* Results Section */}
        {result && !loading && (
          <div className="space-y-6 animate-fade-in-up">
            {/* Impact Summary */}
            <div className="glass-card p-6 flex items-start gap-4 border-indigo-500/20 animate-pulse-glow">
              <div className="p-3 bg-indigo-500/10 rounded-xl text-indigo-400 shrink-0">
                <Zap className="w-7 h-7" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-indigo-300 mb-1 uppercase tracking-wider">
                  Impact Summary
                </h3>
                <p className="text-lg text-slate-200 font-medium leading-relaxed">
                  {result.impact_summary}
                </p>
              </div>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="glass-card-static p-5 h-[400px] flex flex-col">
                <div className="flex items-center gap-2 mb-4">
                  <Activity className="w-5 h-5 text-emerald-400" />
                  <h3 className="text-sm font-bold text-slate-200">
                    Forecast Trajectory
                  </h3>
                </div>
                <div className="flex-1 min-h-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart
                      data={combinedData}
                      margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#1e293b"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="date"
                        stroke="#475569"
                        fontSize={11}
                        tickFormatter={(str) => str.split("-").slice(1).join("/")}
                      />
                      <YAxis stroke="#475569" fontSize={11} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "rgba(15,23,42,0.95)",
                          borderColor: "rgba(56,189,248,0.2)",
                          borderRadius: "8px",
                          color: "#e2e8f0",
                          fontSize: "12px",
                        }}
                      />
                      <Legend wrapperStyle={{ fontSize: "11px" }} />
                      <Line
                        type="monotone"
                        dataKey="baseline"
                        name="Baseline"
                        stroke="#3b82f6"
                        strokeWidth={2.5}
                        dot={{ r: 3 }}
                        activeDot={{ r: 5 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="scenario"
                        name="Scenario"
                        stroke="#f43f5e"
                        strokeWidth={2.5}
                        strokeDasharray="5 5"
                        dot={{ r: 3 }}
                        activeDot={{ r: 5 }}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="glass-card-static p-5 h-[400px] flex flex-col">
                <div className="flex items-center gap-2 mb-4">
                  <Activity className="w-5 h-5 text-cyan-400" />
                  <h3 className="text-sm font-bold text-slate-200">
                    Daily Difference (Delta)
                  </h3>
                </div>
                <div className="flex-1 min-h-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={combinedData}
                      margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#1e293b"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="date"
                        stroke="#475569"
                        fontSize={11}
                        tickFormatter={(str) => str.split("-").slice(1).join("/")}
                      />
                      <YAxis stroke="#475569" fontSize={11} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "rgba(15,23,42,0.95)",
                          borderColor: "rgba(56,189,248,0.2)",
                          borderRadius: "8px",
                          color: "#e2e8f0",
                          fontSize: "12px",
                        }}
                        cursor={{ fill: "rgba(51,65,85,0.3)" }}
                      />
                      <ReferenceLine y={0} stroke="#475569" />
                      <Bar
                        dataKey="difference"
                        name="Delta"
                        radius={[4, 4, 0, 0]}
                      >
                        {combinedData.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={entry.difference > 0 ? "#10b981" : "#ef4444"}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
