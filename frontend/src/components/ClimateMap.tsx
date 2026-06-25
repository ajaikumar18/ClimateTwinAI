import { useState } from "react";
import Map, { Marker, Popup } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";

interface ClimateRecord {
  id: number;
  latitude: number;
  longitude: number;
  temperature: number;
  humidity: number;
  rainfall: number;
  wind_speed: number;
  source: string;
  timestamp: string;
}

interface Props {
  records: ClimateRecord[];
}

const getTemperatureColor = (temp: number) => {
  if (temp < 20) return "blue";
  if (temp < 30) return "green";
  if (temp < 40) return "orange";
  return "red";
};

export default function ClimateMap({ records }: Props) {
  const [selected, setSelected] = useState<ClimateRecord | null>(null);

  return (
    <Map
      initialViewState={{
        longitude: 78.9629,
        latitude: 22.5937,
        zoom: 4,
      }}
      style={{
        width: "100%",
        height: "500px",
        borderRadius: "12px",
      }}
      mapStyle="https://demotiles.maplibre.org/style.json"
      onClick={() => setSelected(null)}
    >
      {records.map((record) => (
        <Marker
          key={record.id}
          longitude={record.longitude}
          latitude={record.latitude}
        >
          <div
            onClick={(e) => {
              e.stopPropagation();
              setSelected(record);
            }}
            style={{
              width: "20px",
              height: "20px",
              borderRadius: "50%",
              backgroundColor: getTemperatureColor(record.temperature),
              border: "2px solid white",
              cursor: "pointer",
              boxShadow: "0 0 10px rgba(255,255,255,0.5)",
            }}
          />
        </Marker>
      ))}

      {selected && (
        <Popup
          longitude={selected.longitude}
          latitude={selected.latitude}
          anchor="top"
          closeButton={true}
          closeOnClick={true}
          onClose={() => setSelected(null)}
        >
          <div
            style={{
              minWidth: "200px",
              color: "black",
              fontSize: "14px",
              lineHeight: "1.5",
            }}
          >
            <h3
              style={{
                color: "black",
                margin: "0 0 10px 0",
              }}
            >
              {selected.source}
            </h3>

            <p>
              <strong>Temperature:</strong>{" "}
              {selected.temperature}°C
            </p>

            <p>
              <strong>Rainfall:</strong>{" "}
              {selected.rainfall} mm
            </p>

            <p>
              <strong>Humidity:</strong>{" "}
              {selected.humidity}%
            </p>

            <p>
              <strong>Wind Speed:</strong>{" "}
              {selected.wind_speed} km/h
            </p>

            <p>
              <strong>Timestamp:</strong>
              <br />
              {new Date(selected.timestamp).toLocaleString()}
            </p>
          </div>
        </Popup>
      )}
    </Map>
  );
}