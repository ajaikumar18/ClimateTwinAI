import { useEffect, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { getForecast, type ForecastResponse } from "../services/climateApi";
import { AlertCircle, BrainCircuit, Loader2, Sparkles, Satellite } from "lucide-react";

interface Props {
  lat: number;
  lon: number;
}

interface ForecastPoint extends ForecastResponse {
  dateFormatted: string;
  rainfall_range: [number, number];
  tmax_range: [number, number];
  tmin_range: [number, number];
}

const isValidCoordinate = (value: number) => Number.isFinite(value);

export default function ForecastPanel({ lat, lon }: Props) {
  const [data, setData] = useState<ForecastPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    const fetchForecast = async () => {
      setLoading(true);
      setError(null);

      try {
        const result = await getForecast(lat, lon);

        if (!isActive) {
          return;
        }

        if (result.length === 0) {
          setData([]);
          setError(
            "No forecast points were returned. The backend may be offline or the model has not been trained for this region yet."
          );
          return;
        }

        const formatted: ForecastPoint[] = result.map((d) => ({
          ...d,
          dateFormatted: new Date(d.date).toLocaleDateString(undefined, {
            weekday: "short",
            day: "numeric",
          }),
          rainfall_range: [d.rainfall_lower, d.rainfall_upper] as [number, number],
          tmax_range: [d.tmax_lower, d.tmax_upper] as [number, number],
          tmin_range: [d.tmin_lower, d.tmin_upper] as [number, number],
        }));

        setData(formatted);
      } catch (err) {
        if (!isActive) {
          return;
        }

        console.error("Failed to fetch forecast:", err);
        setData([]);
        setError(
          err instanceof Error && err.message
            ? err.message
            : "Prediction service unavailable. Please check the backend connection."
        );
      } finally {
        if (isActive) {
          setLoading(false);
        }
      }
    };

    if (isValidCoordinate(lat) && isValidCoordinate(lon)) {
      fetchForecast();
    } else {
      setData([]);
      setError("Select a valid location to load the AI forecast.");
      setLoading(false);
    }

    return () => {
      isActive = false;
    };
  }, [lat, lon]);

  const renderEmptyState = (title: string, message: string) => (
    <div className="glass-card-static flex h-95 min-h-[320px] flex-col items-center justify-center gap-3 rounded-3xl border border-white/10 bg-slate-900/85 p-6 text-center shadow-[0_20px_80px_rgba(15,23,42,0.55)]">
      <div className="rounded-2xl border border-purple-500/20 bg-purple-500/10 p-3 text-purple-300">
        {error ? <AlertCircle className="h-8 w-8" /> : <BrainCircuit className="h-8 w-8" />}
      </div>
      <div className="space-y-1">
        <p className="text-base font-semibold text-white">{title}</p>
        <p className="max-w-sm text-sm text-slate-400">{message}</p>
      </div>
      <div className="flex items-center gap-2 rounded-full border border-cyan-500/20 bg-cyan-500/10 px-3 py-1 text-[11px] font-medium uppercase tracking-[0.24em] text-cyan-300">
        <Sparkles className="h-3.5 w-3.5" /> AI insights standby
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="glass-card-static flex h-95 min-h-[320px] flex-col items-center justify-center gap-3 rounded-3xl border border-white/10 bg-slate-900/80 p-6 shadow-[0_20px_80px_rgba(15,23,42,0.5)]">
        <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
        <div className="text-center">
          <p className="text-sm font-semibold text-white">Running AI predictions</p>
          <p className="mt-1 text-sm text-slate-500">Gathering the latest climate outlook for this location.</p>
        </div>
      </div>
    );
  }

  if (error || data.length === 0) {
    return renderEmptyState(
      error ? "Forecast unavailable" : "No forecast data",
      error || "No prediction data is available for this location yet."
    );
  }

  const renderForecastCard = (
    title: string,
    dataKeyMean: keyof ForecastPoint,
    dataKeyRange: keyof ForecastPoint,
    color: string
  ) => (
    <div className="rounded-2xl border border-slate-700/40 bg-slate-800/45 p-2.5 shadow-inner shadow-slate-950/30">
      <h4 className="mb-1.5 text-[11px] font-semibold text-slate-300">{title}</h4>
      <div className="h-20 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 2, right: 2, left: -30, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis dataKey="dateFormatted" stroke="#475569" fontSize={9} tickMargin={4} />
            <YAxis stroke="#475569" fontSize={9} tickFormatter={(val) => `${val}`} />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(15,23,42,0.95)",
                borderColor: "rgba(56,189,248,0.2)",
                borderRadius: "8px",
                color: "#e2e8f0",
                fontSize: "11px",
              }}
              itemStyle={{ color: "#e2e8f0" }}
            />
            <Area
              type="monotone"
              dataKey={dataKeyRange}
              stroke="none"
              fill={color}
              fillOpacity={0.15}
              activeDot={false}
            />
            <Area
              type="monotone"
              dataKey={dataKeyMean}
              stroke={color}
              strokeWidth={2}
              fill={color}
              fillOpacity={0.05}
              dot={{ r: 2, fill: color }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );

  return (
    <div className="glass-card-static flex h-95 flex-col rounded-3xl border border-white/10 bg-slate-900/80 p-5 shadow-[0_20px_90px_rgba(8,15,30,0.45)]">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-purple-500/10 p-2 text-purple-400 shadow-[0_0_15px_rgba(168,85,247,0.3)]">
            <Satellite className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">IMD + INSAT Fused AI</h3>
            <p className="text-[11px] text-slate-500">
              {lat.toFixed(2)}°N, {lon.toFixed(2)}°E • Multi-modal LSTM
            </p>
          </div>
        </div>
        <span className="rounded-md border border-cyan-500/20 bg-cyan-500/10 px-2.5 py-1 text-[10px] font-bold text-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.2)]">
          Fused Satellite Data
        </span>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 md:grid-cols-3">
        {renderForecastCard("Rainfall", "rainfall", "rainfall_range", "#10b981")}
        {renderForecastCard("Max Temp", "tmax", "tmax_range", "#ef4444")}
        {renderForecastCard("Min Temp", "tmin", "tmin_range", "#3b82f6")}
      </div>
    </div>
  );
}
