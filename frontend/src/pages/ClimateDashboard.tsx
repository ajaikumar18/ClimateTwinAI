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
    fetchClimateData();
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
      <div className="max-w-[1400px] mx-auto px-6 py-8 space-y-8">
        {/* ── Hero Section ─────────────────────── */}
        <div className="animate-fade-in-up">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                Climate Dashboard
              </h1>
              <p className="text-slate-500 mt-1">
                Real-time climate intelligence across India • 5,600+ stations
              </p>
            </div>
            {selectedLocation && (
              <div className="glass-card-static px-4 py-2 flex items-center gap-2 text-sm">
                <MapPin className="w-4 h-4 text-cyan-400" />
                <span className="text-slate-400">Selected:</span>
                <span className="font-semibold text-cyan-300">
                  {selectedLocation.lat.toFixed(2)}°N,{" "}
                  {selectedLocation.lon.toFixed(2)}°E
                </span>
              </div>
            )}
          </div>
        </div>

        {/* ── Stat Cards ──────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map((card, i) => (
            <div
              key={card.label}
              className={`relative glass-card p-5 flex items-center gap-4 overflow-hidden animate-fade-in-up-delay-${i + 1} ${card.cssClass}`}
            >
              <div className={`${card.bgColor} p-3 rounded-xl ${card.color} icon-glow`}>
                <card.icon size={22} />
              </div>
              <div>
                <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">
                  {card.label}
                </p>
                <h3 className="text-2xl font-bold text-white mt-0.5">
                  {card.value}
                </h3>
              </div>
            </div>
          ))}
        </div>

        {/* ── Map Section ─────────────────────── */}
        <ClimateMap
          onLocationSelect={(lat, lon) => setSelectedLocation({ lat, lon })}
        />

        {/* ── Analytics Section ────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pb-12">
          <div className="animate-fade-in-up-delay-3">
            <ClimateChart
              lat={selectedLocation.lat}
              lon={selectedLocation.lon}
            />
          </div>
          <div className="animate-fade-in-up-delay-4">
            <ForecastPanel
              lat={selectedLocation.lat}
              lon={selectedLocation.lon}
            />
          </div>
        </div>
      </div>
    </div>
  );
}