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

    if (lat && lon) fetchData();
  }, [lat, lon]);

  if (loading) {
    return (
      <div className="glass-card-static p-6 h-[380px] flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
        <span className="text-slate-500 text-sm">Loading historical data...</span>
      </div>
    );
  }

  if (error || data.length === 0) {
    return (
      <div className="glass-card-static p-6 h-[380px] flex flex-col items-center justify-center gap-3">
        <DatabaseZap className="w-10 h-10 text-slate-600" />
        <div className="text-center">
          <p className="text-slate-400 font-semibold">No historical data</p>
          <p className="text-slate-600 text-sm mt-1">
            Click a station on the map to load time-series data
          </p>
        </div>
      </div>
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
    <div className="glass-card-static p-5 h-[380px] flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">
              90-Day Historical Trend
            </h3>
            <p className="text-[11px] text-slate-500">
              {lat.toFixed(2)}°N, {lon.toFixed(2)}°E • {chartData.length} records
            </p>
          </div>
        </div>
        <span className="px-2.5 py-1 text-[10px] font-bold bg-indigo-500/10 text-indigo-400 rounded-md border border-indigo-500/20">
          IMD + INSAT
        </span>
      </div>

      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={chartData}
            margin={{ top: 5, right: 0, left: -20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis
              dataKey="date"
              stroke="#475569"
              fontSize={10}
              tickMargin={8}
              minTickGap={20}
            />
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
            <Bar
              yAxisId="rain"
              dataKey="rainfall"
              name="Rainfall"
              fill="#10b981"
              barSize={6}
              opacity={0.7}
              radius={[2, 2, 0, 0]}
            />
            <Line
              yAxisId="temp"
              type="monotone"
              dataKey="tmax"
              name="Max Temp"
              stroke="#ef4444"
              strokeWidth={2}
              dot={false}
            />
            <Line
              yAxisId="temp"
              type="monotone"
              dataKey="tmin"
              name="Min Temp"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
