import { useEffect, useState } from "react";
import { getClimateRecords } from "../services/climateApi";
import ClimateMap from "../components/ClimateMap";
import ClimateChart from "../components/ClimateChart";
import ForecastPanel from "../components/ForecastPanel";
import type { ClimateRecord } from "../types/climate";
import {
  Thermometer,
  CloudRain,
  Droplets,
  RadioTower,
  MapPin,
  Sparkles,
  ShieldCheck,
} from "lucide-react";

export default function ClimateDashboard() {
  const [records, setRecords] = useState<ClimateRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedLocation, setSelectedLocation] = useState({
    lat: 22.5,
    lon: 79.0,
  });

  useEffect(() => {
    const fetchClimateData = async () => {
      try {
        const data = await getClimateRecords();
        setRecords(data);
      } catch (error) {
        console.error("Failed to fetch climate records:", error);
      } finally {
        setLoading(false);
      }
    };
    void fetchClimateData();
  }, []);

  const avgTemp =
    records.length > 0
      ? records.reduce((sum, r) => sum + (r.temperature || 0), 0) /
        records.filter((r) => r.temperature != null).length
      : 0;

  const avgRain =
    records.length > 0
      ? records.reduce((sum, r) => sum + (r.rainfall || 0), 0) /
        records.filter((r) => r.rainfall != null).length
      : 0;

  const avgHumidity =
    records.length > 0
      ? records.reduce((sum, r) => sum + (r.humidity || 0), 0) /
        records.filter((r) => r.humidity != null).length
      : 0;

  const totalStations = records.length;

  const statCards = [
    {
      label: "Avg Temperature",
      value: loading ? "—" : `${avgTemp.toFixed(1)}°C`,
      icon: Thermometer,
      color: "text-red-400",
      bgColor: "bg-red-500/10",
      cssClass: "stat-card-temp",
    },
    {
      label: "Avg Rainfall",
      value: loading ? "—" : `${avgRain.toFixed(1)} mm`,
      icon: CloudRain,
      color: "text-blue-400",
      bgColor: "bg-blue-500/10",
      cssClass: "stat-card-rain",
    },
    {
      label: "Avg Humidity",
      value: loading ? "—" : `${avgHumidity.toFixed(1)}%`,
      icon: Droplets,
      color: "text-cyan-400",
      bgColor: "bg-cyan-500/10",
      cssClass: "stat-card-humidity",
    },
    {
      label: "Active Stations",
      value: loading ? "—" : totalStations.toLocaleString(),
      icon: RadioTower,
      color: "text-emerald-400",
      bgColor: "bg-emerald-500/10",
      cssClass: "stat-card-stations",
    },
  ];

  return (
    <div className="min-h-screen bg-[#030712] text-white">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-8 px-4 py-8 sm:px-6 lg:px-8">
        <section className="animate-fade-in-up rounded-[28px] border border-slate-800/70 bg-slate-900/50 p-6 shadow-[0_0_60px_rgba(34,211,238,0.06)] backdrop-blur-xl sm:p-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <div className="mb-4 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-cyan-400">
                <Sparkles className="h-3.5 w-3.5" />
                Climate Intelligence Layer
              </div>
              <h1 className="bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-3xl font-semibold text-transparent sm:text-4xl">
                Climate Dashboard
              </h1>
              <p className="mt-3 text-sm leading-7 text-slate-500 sm:text-base">
                Monitor real-time climate conditions across India with a unified view of observations, forecasts, and scenario insights.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-800/70 bg-slate-950/70 p-3">
              <div className="flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1.5 text-sm text-emerald-300">
                <ShieldCheck className="h-4 w-4" />
                Live data sync
              </div>
              <div className="flex items-center gap-2 rounded-full border border-cyan-500/20 bg-cyan-500/10 px-3 py-1.5 text-sm text-cyan-300">
                <MapPin className="h-4 w-4" />
                {selectedLocation.lat.toFixed(2)}°N, {selectedLocation.lon.toFixed(2)}°E
              </div>
            </div>
          </div>
        </section>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {statCards.map((card, index) => (
            <div
              key={card.label}
              className={`relative flex items-center gap-4 overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-900/60 p-5 backdrop-blur-xl animate-fade-in-up-delay-${index + 1} ${card.cssClass}`}
            >
              <div className={`${card.bgColor} rounded-xl p-3 ${card.color} icon-glow`}>
                <card.icon size={22} />
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                  {card.label}
                </p>
                <h3 className="mt-0.5 text-2xl font-semibold text-white">
                  {card.value}
                </h3>
              </div>
            </div>
          ))}
        </div>

        <div className="rounded-[28px] border border-slate-800/70 bg-slate-900/40 p-3 shadow-[0_0_80px_rgba(2,8,23,0.4)] backdrop-blur-xl sm:p-4">
          <ClimateMap onLocationSelect={(lat, lon) => setSelectedLocation({ lat, lon })} />
        </div>

        <div className="grid grid-cols-1 gap-6 pb-12 xl:grid-cols-2">
          <div className="animate-fade-in-up-delay-3">
            <ClimateChart lat={selectedLocation.lat} lon={selectedLocation.lon} />
          </div>
          <div className="animate-fade-in-up-delay-4">
            <ForecastPanel lat={selectedLocation.lat} lon={selectedLocation.lon} />
          </div>
        </div>
      </div>
    </div>
  );
}