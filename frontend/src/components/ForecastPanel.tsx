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
import { BrainCircuit, Loader2, AlertCircle } from "lucide-react";

interface Props {
  lat: number;
  lon: number;
}

export default function ForecastPanel({ lat, lon }: Props) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchForecast = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await getForecast(lat, lon);

        if (result.length === 0) {
          setError("AI models not trained yet. Run training scripts first.");
          setData([]);
          return;
        }

        const formatted = result.map((d: ForecastResponse) => ({
          ...d,
          dateFormatted: new Date(d.date).toLocaleDateString(undefined, {
            weekday: "short",
            day: "numeric",
          }),
          rainfall_range: [d.rainfall_lower, d.rainfall_upper],
          tmax_range: [d.tmax_lower, d.tmax_upper],
          tmin_range: [d.tmin_lower, d.tmin_upper],
        }));

        setData(formatted);
      } catch (err: any) {
        console.error("Failed to fetch forecast:", err);
        setError(err?.message || "Prediction service unavailable");
      } finally {
        setLoading(false);
      }
    };

    if (lat && lon) fetchForecast();
  }, [lat, lon]);

  if (loading) {
    return (
      <div className="glass-card-static p-6 h-[380px] flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
        <span className="text-slate-500 text-sm">Running AI predictions...</span>
      </div>
    );
  }

  if (error || data.length === 0) {
    return (
      <div className="glass-card-static p-6 h-[380px] flex flex-col items-center justify-center gap-3">
        <AlertCircle className="w-10 h-10 text-amber-500/50" />
        <div className="text-center">
          <p className="text-slate-400 font-semibold">Forecast Unavailable</p>
          <p className="text-slate-600 text-sm mt-1 max-w-xs">
            {error || "No prediction data available for this location."}
          </p>
        </div>
      </div>
    );
  }

  const renderForecastCard = (
    title: string,
    dataKeyMean: string,
    dataKeyRange: string,
    color: string,
    unit: string
  ) => (
    <div className="bg-slate-800/40 rounded-lg p-2.5 border border-slate-700/30">
      <h4 className="text-[11px] font-semibold text-slate-300 mb-1.5">{title}</h4>
      <div className="h-[80px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{ top: 2, right: 2, left: -30, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis
              dataKey="dateFormatted"
              stroke="#475569"
              fontSize={9}
              tickMargin={4}
            />
            <YAxis
              stroke="#475569"
              fontSize={9}
              tickFormatter={(val) => `${val}`}
            />
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
    <div className="glass-card-static p-5 h-[380px] flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-500/10 rounded-lg text-purple-400">
            <BrainCircuit className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">7-Day AI Forecast</h3>
            <p className="text-[11px] text-slate-500">
              {lat.toFixed(2)}°N, {lon.toFixed(2)}°E • LSTM Model
            </p>
          </div>
        </div>
        <span className="px-2.5 py-1 text-[10px] font-bold bg-purple-500/10 text-purple-400 rounded-md border border-purple-500/20">
          Predictive
        </span>
      </div>

      <div className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-3 gap-3">
        {renderForecastCard("Rainfall", "rainfall", "rainfall_range", "#10b981", "mm")}
        {renderForecastCard("Max Temp", "tmax", "tmax_range", "#ef4444", "°C")}
        {renderForecastCard("Min Temp", "tmin", "tmin_range", "#3b82f6", "°C")}
      </div>
    </div>
  );
}
