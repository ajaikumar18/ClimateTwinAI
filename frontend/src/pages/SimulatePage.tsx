import { useState } from "react";
import { simulateScenario, type SimulateRequest, type SimulateResponse } from "../services/climateApi";
import { ComposedChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from "recharts";
import { AlertTriangle, Thermometer, Droplets, MapPin, Calendar, Activity, ChevronRight } from "lucide-react";

export default function SimulatePage() {
  const [lat, setLat] = useState<number>(10.0);
  const [lon, setLon] = useState<number>(76.0);
  const [variable, setVariable] = useState<"rainfall" | "tmax" | "tmin">("rainfall");
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
        horizon_days: horizon
      };
      const res = await simulateScenario(payload);
      setResult(res);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || "Failed to run simulation");
    } finally {
      setLoading(false);
    }
  };

  // Combine baseline and scenario for composed chart
  const combinedData = result ? result.baseline.map((b, i) => ({
    date: b.date,
    baseline: b.value,
    scenario: result.scenario[i].value,
    difference: result.delta[i].difference,
    percent_change: result.delta[i].percent_change
  })) : [];

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8 font-sans">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent inline-block">
            What-If Scenario Simulator
          </h1>
          <p className="text-slate-400 text-lg">
            Perturb historical inputs to model future climate impacts using our trained AI digital twin.
          </p>
        </div>

        {/* Controls Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700/50 shadow-xl space-y-6">
            <h2 className="text-xl font-semibold flex items-center gap-2 text-emerald-400">
              <Activity className="w-5 h-5" /> Scenario Parameters
            </h2>
            
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-1">
                  <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                    <Thermometer className="w-4 h-4 text-rose-400" /> Temperature Delta (°C)
                  </label>
                  <span className="text-sm font-bold text-slate-100">{tempDelta > 0 ? '+' : ''}{tempDelta}°C</span>
                </div>
                <input 
                  type="range" min="-5" max="5" step="0.5" 
                  value={tempDelta} onChange={(e) => setTempDelta(parseFloat(e.target.value))}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-rose-500"
                />
              </div>

              <div>
                <div className="flex justify-between mb-1">
                  <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                    <Droplets className="w-4 h-4 text-blue-400" /> Rainfall Multiplier
                  </label>
                  <span className="text-sm font-bold text-slate-100">{rainfallMult.toFixed(1)}x</span>
                </div>
                <input 
                  type="range" min="0.5" max="2" step="0.1" 
                  value={rainfallMult} onChange={(e) => setRainfallMult(parseFloat(e.target.value))}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                />
              </div>
            </div>
          </div>

          <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700/50 shadow-xl space-y-6">
            <h2 className="text-xl font-semibold flex items-center gap-2 text-cyan-400">
              <MapPin className="w-5 h-5" /> Location & Target
            </h2>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Latitude</label>
                <input 
                  type="number" step="0.1" value={lat} onChange={(e) => setLat(parseFloat(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Longitude</label>
                <input 
                  type="number" step="0.1" value={lon} onChange={(e) => setLon(parseFloat(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Target Variable</label>
                <select 
                  value={variable} onChange={(e: any) => setVariable(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
                >
                  <option value="rainfall">Rainfall (mm)</option>
                  <option value="tmax">Max Temp (°C)</option>
                  <option value="tmin">Min Temp (°C)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Horizon (Days)</label>
                <input 
                  type="number" min="1" max="7" value={horizon} onChange={(e) => setHorizon(parseInt(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex justify-end">
          <button 
            onClick={runSimulation}
            disabled={loading}
            className="group relative inline-flex items-center justify-center px-8 py-3.5 text-base font-bold text-white transition-all duration-200 bg-gradient-to-r from-emerald-500 to-cyan-600 border border-transparent rounded-xl hover:from-emerald-400 hover:to-cyan-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-600 focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden shadow-[0_0_40px_rgba(16,185,129,0.3)] hover:shadow-[0_0_60px_rgba(16,185,129,0.5)]"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Simulating...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                Run Simulation <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </span>
            )}
          </button>
        </div>

        {error && (
          <div className="p-4 bg-red-900/50 border border-red-500/50 rounded-xl text-red-200 flex items-start gap-3">
            <AlertTriangle className="w-6 h-6 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {/* Results Section */}
        {result && !loading && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            
            {/* Impact Summary */}
            <div className="p-6 bg-gradient-to-br from-indigo-900/40 to-purple-900/40 border border-indigo-500/30 rounded-2xl shadow-xl flex items-center gap-4">
              <div className="p-3 bg-indigo-500/20 rounded-xl">
                <AlertTriangle className="w-8 h-8 text-indigo-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-indigo-300 mb-1">Impact Summary</h3>
                <p className="text-xl text-slate-100 font-medium leading-relaxed">
                  {result.impact_summary}
                </p>
              </div>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              
              {/* Baseline vs Scenario */}
              <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700/50 shadow-xl h-[400px] flex flex-col">
                <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-emerald-400" /> Forecast Trajectory
                </h3>
                <div className="flex-1">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={combinedData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                      <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} tickFormatter={(str) => str.split('-').slice(1).join('/')} />
                      <YAxis stroke="#94a3b8" fontSize={12} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px' }}
                        itemStyle={{ color: '#f8fafc' }}
                      />
                      <Legend />
                      <Line type="monotone" dataKey="baseline" name="Baseline" stroke="#3b82f6" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                      <Line type="monotone" dataKey="scenario" name="Scenario" stroke="#f43f5e" strokeWidth={3} strokeDasharray="5 5" dot={{ r: 4 }} activeDot={{ r: 6 }} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Delta Bar Chart */}
              <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700/50 shadow-xl h-[400px] flex flex-col">
                <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-cyan-400" /> Daily Difference (Delta)
                </h3>
                <div className="flex-1">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={combinedData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                      <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} tickFormatter={(str) => str.split('-').slice(1).join('/')} />
                      <YAxis stroke="#94a3b8" fontSize={12} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px' }}
                        cursor={{ fill: '#334155', opacity: 0.4 }}
                      />
                      <ReferenceLine y={0} stroke="#64748b" />
                      <Bar 
                        dataKey="difference" 
                        name="Delta" 
                        radius={[4, 4, 0, 0]}
                      >
                        {combinedData.map((entry, index) => (
                          <cell key={`cell-${index}`} fill={entry.difference > 0 ? '#10b981' : '#ef4444'} />
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
