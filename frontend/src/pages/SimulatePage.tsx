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
  Activity,
  AlertTriangle,
  ChevronRight,
  Droplets,
  FlaskConical,
  MapPin,
  Thermometer,
  Zap,
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
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to run simulation";
      setError(message);
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
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(20,184,166,0.12),transparent_35%),linear-gradient(135deg,#020617_0%,#030712_55%,#020617_100%)] text-slate-100">
      <div className="mx-auto flex max-w-350 flex-col gap-6 px-6 py-8 lg:px-8">
        <header className="glass-card-static rounded-[28px] border border-white/10 bg-slate-900/80 p-7 shadow-[0_24px_90px_rgba(2,6,23,0.45)]">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="rounded-2xl border border-emerald-400/20 bg-emerald-500/10 p-2.5 text-emerald-300">
                  <FlaskConical className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-300/80">
                    Digital Twin Studio
                  </p>
                  <h1 className="text-3xl font-semibold text-white">
                    What-If Scenario Simulator
                  </h1>
                </div>
              </div>
              <p className="max-w-2xl text-sm leading-6 text-slate-400">
                Perturb historical inputs to model future climate impacts using the same predictive workflows as the dashboard and map views.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              {[
                { label: "Live controls", tone: "emerald" },
                { label: "Interactive charts", tone: "cyan" },
                { label: "AI-driven insights", tone: "violet" },
              ].map((item) => (
                <span
                  key={item.label}
                  className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] ${
                    item.tone === "emerald"
                      ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-300"
                      : item.tone === "cyan"
                        ? "border-cyan-400/20 bg-cyan-500/10 text-cyan-300"
                        : "border-violet-400/20 bg-violet-500/10 text-violet-300"
                  }`}
                >
                  {item.label}
                </span>
              ))}
            </div>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="glass-card-static rounded-3xl border border-white/10 bg-slate-900/80 p-6 shadow-[0_20px_80px_rgba(15,23,42,0.35)]">
            <div className="mb-6 flex items-center gap-3">
              <div className="rounded-xl border border-emerald-400/20 bg-emerald-500/10 p-2 text-emerald-300">
                <Activity className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Scenario Parameters</h2>
                <p className="text-sm text-slate-400">Adjust the perturbations and watch the forecast shift.</p>
              </div>
            </div>

            <div className="space-y-6">
              <div className="rounded-2xl border border-white/10 bg-slate-950/45 p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
                    <Thermometer className="h-4 w-4 text-rose-400" />
                    Temperature Delta
                  </label>
                  <span className="rounded-full border border-rose-500/20 bg-rose-500/10 px-2.5 py-1 text-sm font-semibold text-white">
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
                  className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-700 accent-rose-500"
                />
                <div className="mt-2 flex justify-between text-[10px] uppercase tracking-[0.24em] text-slate-500">
                  <span>-5°C</span>
                  <span>+5°C</span>
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-slate-950/45 p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
                    <Droplets className="h-4 w-4 text-cyan-400" />
                    Rainfall Multiplier
                  </label>
                  <span className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-2.5 py-1 text-sm font-semibold text-white">
                    {rainfallMult.toFixed(1)}x
                  </span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="2"
                  step="0.1"
                  value={rainfallMult}
                  onChange={(e) => setRainfallMult(parseFloat(e.target.value))}
                  className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-700 accent-cyan-500"
                />
                <div className="mt-2 flex justify-between text-[10px] uppercase tracking-[0.24em] text-slate-500">
                  <span>0.5x (drought)</span>
                  <span>2.0x (flood)</span>
                </div>
              </div>
            </div>
          </div>

          <div className="glass-card-static rounded-3xl border border-white/10 bg-slate-900/80 p-6 shadow-[0_20px_80px_rgba(15,23,42,0.35)]">
            <div className="mb-6 flex items-center gap-3">
              <div className="rounded-xl border border-cyan-400/20 bg-cyan-500/10 p-2 text-cyan-300">
                <MapPin className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Location & Target</h2>
                <p className="text-sm text-slate-400">Select the region and metric to stress-test.</p>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                  Latitude
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={lat}
                  onChange={(e) => setLat(parseFloat(e.target.value))}
                  className="w-full rounded-xl border border-slate-700/60 bg-slate-800/70 px-3 py-2.5 text-sm text-slate-100 outline-none transition-all focus:border-cyan-500/50 focus:shadow-[0_0_15px_rgba(20,184,166,0.12)]"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                  Longitude
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={lon}
                  onChange={(e) => setLon(parseFloat(e.target.value))}
                  className="w-full rounded-xl border border-slate-700/60 bg-slate-800/70 px-3 py-2.5 text-sm text-slate-100 outline-none transition-all focus:border-cyan-500/50 focus:shadow-[0_0_15px_rgba(20,184,166,0.12)]"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                  Target Variable
                </label>
                <select
                  value={variable}
                  onChange={(e) => setVariable(e.target.value as "rainfall" | "tmax" | "tmin")}
                  className="w-full rounded-xl border border-slate-700/60 bg-slate-800/70 px-3 py-2.5 text-sm text-slate-100 outline-none transition-all focus:border-cyan-500/50"
                >
                  <option value="rainfall">Rainfall (mm)</option>
                  <option value="tmax">Max Temp (°C)</option>
                  <option value="tmin">Min Temp (°C)</option>
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                  Horizon (Days)
                </label>
                <input
                  type="number"
                  min="1"
                  max="7"
                  value={horizon}
                  onChange={(e) => setHorizon(parseInt(e.target.value, 10))}
                  className="w-full rounded-xl border border-slate-700/60 bg-slate-800/70 px-3 py-2.5 text-sm text-slate-100 outline-none transition-all focus:border-cyan-500/50"
                />
              </div>
            </div>
          </div>
        </section>

        <div className="flex justify-end">
          <button
            onClick={runSimulation}
            disabled={loading}
            className="group relative inline-flex items-center justify-center overflow-hidden rounded-2xl bg-linear-to-r from-emerald-500 to-cyan-600 px-8 py-3.5 text-sm font-semibold text-white shadow-[0_0_35px_rgba(16,185,129,0.24)] transition-all duration-300 hover:from-emerald-400 hover:to-cyan-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg
                  className="h-5 w-5 animate-spin"
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
                <Zap className="h-5 w-5" />
                Run Simulation
                <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </span>
            )}
          </button>
        </div>

        {error && (
          <div className="glass-card-static flex items-start gap-3 rounded-3xl border border-red-500/30 bg-red-900/10 p-4">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" />
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}

        {result && !loading && (
          <div className="space-y-6">
            <div className="glass-card-static rounded-3xl border border-indigo-400/20 bg-slate-900/80 p-6 shadow-[0_20px_80px_rgba(15,23,42,0.35)]">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="flex items-start gap-3">
                  <div className="rounded-xl border border-indigo-400/20 bg-indigo-500/10 p-2.5 text-indigo-300">
                    <Zap className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-indigo-300/80">
                      Impact Summary
                    </p>
                    <p className="mt-1 max-w-3xl text-lg font-medium leading-8 text-slate-200">
                      {result.impact_summary}
                    </p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <span className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-300">
                    {variable}
                  </span>
                  <span className="rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-cyan-300">
                    {horizon} day horizon
                  </span>
                </div>
              </div>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <div className="glass-card-static flex h-100 flex-col rounded-3xl border border-white/10 bg-slate-900/80 p-5 shadow-[0_18px_70px_rgba(15,23,42,0.3)]">
                <div className="mb-4 flex items-center gap-2">
                  <Activity className="h-5 w-5 text-emerald-400" />
                  <h3 className="text-sm font-semibold text-slate-200">Forecast Trajectory</h3>
                </div>
                <div className="min-h-0 flex-1">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart
                      data={combinedData}
                      margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
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

              <div className="glass-card-static flex h-100 flex-col rounded-3xl border border-white/10 bg-slate-900/80 p-5 shadow-[0_18px_70px_rgba(15,23,42,0.3)]">
                <div className="mb-4 flex items-center gap-2">
                  <Activity className="h-5 w-5 text-cyan-400" />
                  <h3 className="text-sm font-semibold text-slate-200">Daily Difference (Delta)</h3>
                </div>
                <div className="min-h-0 flex-1">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={combinedData}
                      margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
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
                      <Bar dataKey="difference" name="Delta" radius={[4, 4, 0, 0]}>
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
