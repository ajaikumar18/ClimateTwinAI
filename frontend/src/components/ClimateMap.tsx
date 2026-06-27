import { useEffect, useState, useMemo, useRef, useCallback } from "react";
import Map, {
  Source,
  Layer,
  Popup,
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

export default function ClimateMap({ onLocationSelect }: Props) {
  const mapRef = useRef<MapRef>(null);
  const [data, setData] = useState<any>(null);
  const [variable, setVariable] = useState<Variable>("rainfall");
  const [loading, setLoading] = useState(false);
  const [featureCount, setFeatureCount] = useState(0);
  const [selectedFeature, setSelectedFeature] = useState<any>(null);

  const fetchHeatmapData = useCallback(async () => {
    setLoading(true);
    try {
      const bbox = "6.75,68.0,37.1,97.4";
      const records = await getRegion(bbox, 6000);

      const features = records
        .filter((r: any) => {
          if (variable === "rainfall") return r.rainfall != null;
          if (variable === "temperature_max")
            return r.temperature_max != null || r.temperature != null;
          if (variable === "temperature_min")
            return r.temperature_min != null || r.temperature != null;
          return false;
        })
        .map((r: any) => {
          let value: number;
          if (variable === "rainfall") {
            value = r.rainfall ?? 0;
          } else if (variable === "temperature_max") {
            value = r.temperature_max ?? r.temperature ?? 0;
          } else {
            value = r.temperature_min ?? r.temperature ?? 0;
          }

          return {
            type: "Feature" as const,
            geometry: {
              type: "Point" as const,
              coordinates: [r.longitude, r.latitude],
            },
            properties: {
              value,
              temperature: r.temperature,
              temperature_max: r.temperature_max,
              temperature_min: r.temperature_min,
              rainfall: r.rainfall,
              humidity: r.humidity,
              wind_speed: r.wind_speed,
              source: r.source,
              timestamp: r.timestamp,
            },
          };
        });

      setFeatureCount(features.length);
      setData({ type: "FeatureCollection", features });
    } catch (error) {
      console.error("Failed to fetch region data:", error);
    } finally {
      setLoading(false);
    }
  }, [variable]);

  useEffect(() => {
    fetchHeatmapData();
  }, [fetchHeatmapData]);

  const onClick = useCallback(
    (e: MapLayerMouseEvent) => {
      const feature = e.features?.[0];
      if (feature && feature.geometry.type === "Point") {
        const [lng, lat] = feature.geometry.coordinates;
        setSelectedFeature({
          longitude: lng,
          latitude: lat,
          ...feature.properties,
        });
        onLocationSelect(lat, lng);
      } else {
        setSelectedFeature(null);
        onLocationSelect(e.lngLat.lat, e.lngLat.lng);
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
        0,   "#3b82f6",
        5,   "#22d3ee",
        20,  "#10b981",
        50,  "#f59e0b",
        100, "#ef4444",
        200, "#dc2626",
      ];
    }
    // Temperature
    return [
      "interpolate",
      ["linear"],
      ["get", "value"],
      0,   "#3b82f6",
      15,  "#06b6d4",
      25,  "#22c55e",
      30,  "#f59e0b",
      35,  "#f97316",
      40,  "#ef4444",
      45,  "#dc2626",
    ];
  }, [variable]);

  const heatmapLayer: any = useMemo(
    () => ({
      id: "climate-heatmap",
      type: "heatmap",
      paint: {
        "heatmap-weight": ["interpolate", ["linear"], ["get", "value"], 0, 0, 50, 1],
        "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 0, 1, 9, 3],
        "heatmap-color": [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0,   "rgba(0,0,0,0)",
          0.1, "rgba(34,211,238,0.2)",
          0.3, "rgba(16,185,129,0.4)",
          0.5, "rgba(245,158,11,0.5)",
          0.7, "rgba(239,68,68,0.6)",
          1,   "rgba(220,38,38,0.8)",
        ],
        "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 3, 8, 6, 20, 9, 35],
        "heatmap-opacity": ["interpolate", ["linear"], ["zoom"], 5, 0.7, 8, 0.3],
      },
    }),
    []
  );

  const circleLayer: any = useMemo(
    () => ({
      id: "climate-circles",
      type: "circle",
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 3, 6, 5, 9, 10],
        "circle-color": getCircleColorExpr(),
        "circle-stroke-width": 1,
        "circle-stroke-color": "rgba(255,255,255,0.4)",
        "circle-opacity": ["interpolate", ["linear"], ["zoom"], 5, 0.6, 8, 0.9],
      },
    }),
    [getCircleColorExpr]
  );

  return (
    <div className="relative w-full h-[600px] rounded-2xl overflow-hidden glass-card-static animate-fade-in-up-delay-2">
      {/* Control Panel */}
      <div className="absolute top-4 left-4 z-10 glass-card-static p-3 space-y-3 max-w-[280px]">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-300 uppercase tracking-wider">
          <MapPin className="w-3.5 h-3.5 text-cyan-400" /> Climate Variable
        </div>
        <div className="flex gap-1.5">
          {(Object.keys(VARIABLE_LABELS) as Variable[]).map((v) => (
            <button
              key={v}
              onClick={() => setVariable(v)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all duration-300 ${
                variable === v
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-[0_0_15px_rgba(34,211,238,0.15)]"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 border border-transparent"
              }`}
            >
              {VARIABLE_LABELS[v]}
            </button>
          ))}
        </div>
        <div className="flex items-center justify-between text-[11px] text-slate-500">
          <span>{featureCount.toLocaleString()} stations</span>
          {loading && (
            <span className="flex items-center gap-1 text-cyan-400">
              <Loader2 className="w-3 h-3 animate-spin" /> Loading...
            </span>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="absolute bottom-5 right-5 z-10 glass-card-static p-3 w-44">
        <div className="text-xs font-bold text-slate-300 mb-2">
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
        <div className="flex justify-between mt-1 text-[10px] text-slate-500">
          <span>Low</span>
          <span>High</span>
        </div>
      </div>

      {/* Map */}
      <Map
        ref={mapRef}
        initialViewState={{ longitude: 79.0, latitude: 22.5, zoom: 4.3 }}
        style={{ width: "100%", height: "100%" }}
        mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
        onClick={onClick}
        interactiveLayerIds={data ? ["climate-circles"] : undefined}
        cursor="crosshair"
        attributionControl={false}
        onError={() => {
          // Fallback to demo tiles if CARTO fails
          mapRef.current?.getMap().setStyle("https://demotiles.maplibre.org/style.json");
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
                <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                <span className="text-sm font-bold text-white">
                  {selectedFeature.source || "Station"}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
                {selectedFeature.temperature != null && (
                  <>
                    <span className="text-slate-400">Temperature</span>
                    <span className="text-white font-semibold text-right">
                      {selectedFeature.temperature}°C
                    </span>
                  </>
                )}
                {selectedFeature.rainfall != null && (
                  <>
                    <span className="text-slate-400">Rainfall</span>
                    <span className="text-white font-semibold text-right">
                      {selectedFeature.rainfall} mm
                    </span>
                  </>
                )}
                {selectedFeature.humidity != null && (
                  <>
                    <span className="text-slate-400">Humidity</span>
                    <span className="text-white font-semibold text-right">
                      {selectedFeature.humidity}%
                    </span>
                  </>
                )}
                {selectedFeature.wind_speed != null && (
                  <>
                    <span className="text-slate-400">Wind</span>
                    <span className="text-white font-semibold text-right">
                      {selectedFeature.wind_speed} km/h
                    </span>
                  </>
                )}
              </div>

              {selectedFeature.timestamp && (
                <div className="text-[10px] text-slate-500 pt-1 border-t border-slate-700/50">
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