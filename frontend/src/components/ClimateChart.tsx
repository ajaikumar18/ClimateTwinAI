import { useEffect, useState } from "react";
import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { getTimeSeries } from "../services/climateApi";
import type { ClimateRecord } from "../types/climate";
import { TrendingUp, Loader2, DatabaseZap } from "lucide-react";

interface Props {
  lat: number;
  lon: number;
}

export default function ClimateChart({ lat, lon }: Props) {
  const [data, setData] = useState<ClimateRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(false);
      try {
        const end = new Date();
        const start = new Date();
        start.setDate(end.getDate() - 90);

        const result = await getTimeSeries(
          lat,
          lon,
          start.toISOString().split("T")[0],
          end.toISOString().split("T")[0]
        );
        setData(result);
      } catch (err) {
        console.error("Failed to fetch timeseries:", err);
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    if (lat && lon) {
      void fetchData();
    }
  }, [lat, lon]);

  const renderState = (title: string, description: string, icon: React.ReactNode) => (
    <div className="flex h-[380px] flex-col items-center justify-center gap-3 rounded-[24px] border border-slate-800/70 bg-slate-900/50 p-6 text-center backdrop-blur-xl">
      <div className="rounded-2xl border border-slate-800/70 bg-slate-950/70 p-3 text-cyan-400">
        {icon}
      </div>
      <div>
        <p className="text-sm font-semibold text-slate-200">{title}</p>
        <p className="mt-1 text-sm leading-6 text-slate-500">{description}</p>
      </div>
    </div>
  );

  if (loading) {
    return renderState(
      "Loading historical data",
      "Preparing the last 90 days of climate signals for this location.",
      <Loader2 className="h-7 w-7 animate-spin" />
    );
  }

  if (error || data.length === 0) {
    return renderState(
      "No historical data",
      "Select a station on the map to load the 90-day trend for that point.",
      <DatabaseZap className="h-7 w-7" />
    );
  }

  const chartData = data.map((d) => ({
    date: new Date(d.timestamp).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    }),
    tmax: d.temperature_max || d.temperature || 0,
    tmin: d.temperature_min || d.temperature || 0,
    rainfall: d.rainfall || 0,
  }));

  return (
    <div className="flex h-[380px] flex-col rounded-[24px] border border-slate-800/70 bg-slate-900/50 p-5 backdrop-blur-xl">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/10 p-2 text-indigo-400">
            <TrendingUp className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">90-Day Historical Trend</h3>
            <p className="text-[11px] text-slate-500">
              {lat.toFixed(2)}°N, {lon.toFixed(2)}°E • {chartData.length} records
            </p>
          </div>
        </div>
        <span className="rounded-full border border-indigo-500/20 bg-indigo-500/10 px-2.5 py-1 text-[10px] font-semibold text-indigo-300">
          IMD + INSAT
        </span>
      </div>

      <div className="min-h-0 flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis dataKey="date" stroke="#475569" fontSize={10} tickMargin={8} minTickGap={20} />
            <YAxis
              yAxisId="temp"
              stroke="#475569"
              fontSize={10}
              label={{
                value: "°C",
                angle: -90,
                position: "insideLeft",
                fill: "#64748b",
                fontSize: 10,
              }}
            />
            <YAxis
              yAxisId="rain"
              orientation="right"
              stroke="#475569"
              fontSize={10}
              label={{
                value: "mm",
                angle: 90,
                position: "insideRight",
                fill: "#64748b",
                fontSize: 10,
              }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(15,23,42,0.95)",
                borderColor: "rgba(56,189,248,0.2)",
                borderRadius: "8px",
                color: "#e2e8f0",
                fontSize: "12px",
              }}
              itemStyle={{ color: "#e2e8f0" }}
            />
            <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
            <Bar yAxisId="rain" dataKey="rainfall" name="Rainfall" fill="#10b981" barSize={6} opacity={0.75} radius={[2, 2, 0, 0]} />
            <Line yAxisId="temp" type="monotone" dataKey="tmax" name="Max Temp" stroke="#ef4444" strokeWidth={2.2} dot={false} />
            <Line yAxisId="temp" type="monotone" dataKey="tmin" name="Min Temp" stroke="#3b82f6" strokeWidth={2.2} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
