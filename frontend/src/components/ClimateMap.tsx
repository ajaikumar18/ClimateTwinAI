import { useEffect, useState, useMemo, useRef, useCallback } from "react";
import Map, {
  Source,
  Layer,
  Popup,
  type CircleLayerSpecification,
  type HeatmapLayerSpecification,
  type MapLayerMouseEvent,
  type MapRef,
} from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { getRegion } from "../services/climateApi";
import { Loader2, MapPin } from "lucide-react";

interface Props {
  onLocationSelect: (lat: number, lon: number) => void;
}

type Variable = "rainfall" | "temperature_max" | "temperature_min";

type RegionRecord = {
  latitude: number;
  longitude: number;
  temperature?: number | null;
  temperature_max?: number | null;
  temperature_min?: number | null;
  humidity?: number | null;
  rainfall?: number | null;
  wind_speed?: number | null;
  source?: string | null;
  timestamp?: string | null;
};

type FeatureProperties = {
  value: number;
  temperature?: number | null;
  temperature_max?: number | null;
  temperature_min?: number | null;
  rainfall?: number | null;
  humidity?: number | null;
  wind_speed?: number | null;
  source?: string | null;
  timestamp?: string | null;
};

type ClimateFeature = {
  type: "Feature";
  geometry: {
    type: "Point";
    coordinates: [number, number];
  };
  properties: FeatureProperties;
};

type ClimateGeoJson = {
  type: "FeatureCollection";
  features: ClimateFeature[];
};

type SelectedFeature = FeatureProperties & {
  longitude: number;
  latitude: number;
};

const VARIABLE_LABELS: Record<Variable, string> = {
  rainfall: "Rainfall",
  temperature_max: "Max Temp",
  temperature_min: "Min Temp",
};

const VARIABLE_UNITS: Record<Variable, string> = {
  rainfall: "mm",
  temperature_max: "°C",
  temperature_min: "°C",
};

const CARTO_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
const DEMO_STYLE = "https://demotiles.maplibre.org/style.json";

export default function ClimateMap({ onLocationSelect }: Props) {
  const mapRef = useRef<MapRef>(null);
  const [data, setData] = useState<ClimateGeoJson | null>(null);
  const [variable, setVariable] = useState<Variable>("rainfall");
  const [loading, setLoading] = useState(false);
  const [featureCount, setFeatureCount] = useState(0);
  const [selectedFeature, setSelectedFeature] = useState<SelectedFeature | null>(null);
  const [mapStyle, setMapStyle] = useState<string>(CARTO_STYLE);

  const fetchHeatmapData = useCallback(async () => {
    setLoading(true);
    try {
      const bbox = "6.75,68.0,37.1,97.4";
      const records = (await getRegion(bbox, 6000)) as RegionRecord[];

      const features = records
        .filter((record) => {
          if (variable === "rainfall") return record.rainfall != null;
          if (variable === "temperature_max")
            return record.temperature_max != null || record.temperature != null;
          if (variable === "temperature_min")
            return record.temperature_min != null || record.temperature != null;
          return false;
        })
        .map((record) => {
          let value: number;
          if (variable === "rainfall") {
            value = record.rainfall ?? 0;
          } else if (variable === "temperature_max") {
            value = record.temperature_max ?? record.temperature ?? 0;
          } else {
            value = record.temperature_min ?? record.temperature ?? 0;
          }

          return {
            type: "Feature" as const,
            geometry: {
              type: "Point" as const,
              coordinates: [record.longitude, record.latitude] as [number, number],
            },
            properties: {
              value,
              temperature: record.temperature,
              temperature_max: record.temperature_max,
              temperature_min: record.temperature_min,
              rainfall: record.rainfall,
              humidity: record.humidity,
              wind_speed: record.wind_speed,
              source: record.source,
              timestamp: record.timestamp,
            },
          } satisfies ClimateFeature;
        });

      setFeatureCount(features.length);
      setData({ type: "FeatureCollection", features });
    } catch (error) {
      console.error("Failed to fetch region data:", error);
      setFeatureCount(0);
      setData({ type: "FeatureCollection", features: [] });
    } finally {
      setLoading(false);
    }
  }, [variable]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void fetchHeatmapData();
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [fetchHeatmapData]);

  const onClick = useCallback(
    (event: MapLayerMouseEvent) => {
      const feature = event.features?.find(
        (item) => item.layer?.id === "climate-circles" && item.geometry?.type === "Point"
      );

      if (feature && feature.geometry.type === "Point") {
        const [lng, lat] = feature.geometry.coordinates;
        const properties = (feature.properties ?? {}) as Partial<FeatureProperties>;
        setSelectedFeature({
          longitude: lng,
          latitude: lat,
          value: properties.value ?? 0,
          ...properties,
        });
        onLocationSelect(lat, lng);
      } else {
        setSelectedFeature(null);
        onLocationSelect(event.lngLat.lat, event.lngLat.lng);
      }
    },
    [onLocationSelect]
  );

  const getCircleColorExpr = useCallback(() => {
    if (variable === "rainfall") {
      return [
        "interpolate",
        ["linear"],
        ["get", "value"],
        0,
        "#3b82f6",
        5,
        "#22d3ee",
        20,
        "#10b981",
        50,
        "#f59e0b",
        100,
        "#ef4444",
        200,
        "#dc2626",
      ];
    }

    return [
      "interpolate",
      ["linear"],
      ["get", "value"],
      0,
      "#3b82f6",
      15,
      "#06b6d4",
      25,
      "#22c55e",
      30,
      "#f59e0b",
      35,
      "#f97316",
      40,
      "#ef4444",
      45,
      "#dc2626",
    ];
  }, [variable]);

  const heatmapLayer = useMemo<HeatmapLayerSpecification>(
    () => ({
      id: "climate-heatmap",
      type: "heatmap",
      source: "climate-data",
      paint: {
        "heatmap-weight": ["interpolate", ["linear"], ["get", "value"], 0, 0, 50, 1],
        "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 0, 1, 9, 3],
        "heatmap-color": [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0,
          "rgba(0,0,0,0)",
          0.1,
          "rgba(34,211,238,0.2)",
          0.3,
          "rgba(16,185,129,0.4)",
          0.5,
          "rgba(245,158,11,0.5)",
          0.7,
          "rgba(239,68,68,0.6)",
          1,
          "rgba(220,38,38,0.8)",
        ],
        "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 3, 8, 6, 20, 9, 35],
        "heatmap-opacity": ["interpolate", ["linear"], ["zoom"], 5, 0.7, 8, 0.3],
      },
    }),
    []
  );

  const circleLayer = useMemo<CircleLayerSpecification>(
    () => ({
      id: "climate-circles",
      type: "circle",
      source: "climate-data",
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 3, 6, 5, 9, 10],
        "circle-color": getCircleColorExpr() as unknown as string,
        "circle-stroke-width": 1,
        "circle-stroke-color": "rgba(255,255,255,0.4)",
        "circle-opacity": ["interpolate", ["linear"], ["zoom"], 5, 0.6, 8, 0.9],
      },
    }),
    [getCircleColorExpr]
  );

  const formatValue = (value: number | null | undefined) => {
    if (value == null || Number.isNaN(value)) return "—";
    return value >= 100 ? value.toFixed(0) : value.toFixed(1);
  };

  return (
    <div className="relative h-150 w-full overflow-hidden rounded-2xl glass-card-static animate-fade-in-up-delay-2">
      <div className="absolute left-4 top-4 z-10 max-w-75 space-y-3 rounded-2xl border border-slate-800/70 bg-slate-900/70 p-3 backdrop-blur-xl">
        <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.24em] text-slate-300">
          <MapPin className="h-3.5 w-3.5 text-cyan-400" /> Climate Variable
        </div>
        <div className="flex flex-wrap gap-1.5">
          {(Object.keys(VARIABLE_LABELS) as Variable[]).map((option) => (
            <button
              key={option}
              onClick={() => setVariable(option)}
              className={`rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all duration-300 ${
                variable === option
                  ? "border-cyan-500/30 bg-cyan-500/20 text-cyan-300 shadow-[0_0_15px_rgba(34,211,238,0.15)]"
                  : "border-transparent text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
              }`}
            >
              {VARIABLE_LABELS[option]}
            </button>
          ))}
        </div>
        <div className="flex items-center justify-between text-[11px] text-slate-500">
          <span>{featureCount.toLocaleString()} stations</span>
          {loading && (
            <span className="flex items-center gap-1 text-cyan-400">
              <Loader2 className="h-3 w-3 animate-spin" /> Loading...
            </span>
          )}
        </div>
      </div>

      <div className="absolute bottom-5 right-5 z-10 w-44 rounded-2xl border border-slate-800/70 bg-slate-900/70 p-3 backdrop-blur-xl">
        <div className="mb-2 text-xs font-bold text-slate-300">
          {VARIABLE_LABELS[variable]} ({VARIABLE_UNITS[variable]})
        </div>
        <div
          className="h-2.5 w-full rounded-full"
          style={{
            background:
              variable === "rainfall"
                ? "linear-gradient(90deg, #3b82f6, #22d3ee, #10b981, #f59e0b, #ef4444)"
                : "linear-gradient(90deg, #3b82f6, #06b6d4, #22c55e, #f59e0b, #ef4444)",
          }}
        />
        <div className="mt-1 flex justify-between text-[10px] text-slate-500">
          <span>Low</span>
          <span>High</span>
        </div>
      </div>

      <Map
        ref={mapRef}
        initialViewState={{ longitude: 79.0, latitude: 22.5, zoom: 4.3 }}
        style={{ width: "100%", height: "100%" }}
        mapStyle={mapStyle}
        onClick={onClick}
        interactiveLayerIds={data ? ["climate-circles"] : undefined}
        cursor="crosshair"
        attributionControl={false}
        onError={() => {
          if (mapStyle !== DEMO_STYLE) {
            setMapStyle(DEMO_STYLE);
          }
        }}
      >
        {data && (
          <Source id="climate-data" type="geojson" data={data}>
            <Layer {...heatmapLayer} />
            <Layer {...circleLayer} />
          </Source>
        )}

        {selectedFeature && (
          <Popup
            longitude={selectedFeature.longitude}
            latitude={selectedFeature.latitude}
            anchor="bottom"
            closeButton={true}
            closeOnClick={false}
            onClose={() => setSelectedFeature(null)}
            maxWidth="280px"
          >
            <div className="space-y-2">
              <div className="flex items-center gap-2 border-b border-slate-700/50 pb-2">
                <div className={`h-2 w-2 animate-pulse rounded-full ${selectedFeature.source?.includes("INSAT") || selectedFeature.source?.includes("weighted") ? "bg-purple-400 shadow-[0_0_8px_#a855f7]" : "bg-cyan-400"}`} />
                <span className="text-sm font-bold text-white">
                  {selectedFeature.source?.includes("INSAT") || selectedFeature.source?.includes("weighted")
                    ? "INSAT-3DR Satellite Fusion"
                    : selectedFeature.source || "IMD Ground Station"}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
                <span className="text-slate-400">{VARIABLE_LABELS[variable]}</span>
                <span className="text-right font-semibold text-white">
                  {formatValue(selectedFeature.value)} {VARIABLE_UNITS[variable]}
                </span>
                {selectedFeature.temperature != null && (
                  <>
                    <span className="text-slate-400">Temperature</span>
                    <span className="text-right font-semibold text-white">{formatValue(selectedFeature.temperature)}°C</span>
                  </>
                )}
                {selectedFeature.rainfall != null && variable !== "rainfall" && (
                  <>
                    <span className="text-slate-400">Rainfall</span>
                    <span className="text-right font-semibold text-white">{formatValue(selectedFeature.rainfall)} mm</span>
                  </>
                )}
                {selectedFeature.humidity != null && (
                  <>
                    <span className="text-slate-400">Humidity</span>
                    <span className="text-right font-semibold text-white">{formatValue(selectedFeature.humidity)}%</span>
                  </>
                )}
                {selectedFeature.wind_speed != null && (
                  <>
                    <span className="text-slate-400">Wind</span>
                    <span className="text-right font-semibold text-white">{formatValue(selectedFeature.wind_speed)} km/h</span>
                  </>
                )}
              </div>

              {selectedFeature.timestamp && (
                <div className="border-t border-slate-700/50 pt-1 text-[10px] text-slate-500">
                  {new Date(selectedFeature.timestamp).toLocaleString()}
                </div>
              )}
            </div>
          </Popup>
        )}
      </Map>
    </div>
  );
}