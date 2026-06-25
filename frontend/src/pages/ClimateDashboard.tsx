import { useEffect, useState } from "react";
import { getClimateRecords } from "../services/climateApi";
import ClimateMap from "../components/ClimateMap";
import type { ClimateRecord } from "../types/climate";

export default function ClimateDashboard() {
  const [records, setRecords] = useState<ClimateRecord[]>([]);
  const [loading, setLoading] = useState(true);
    const avgTemp =
  records.length > 0
    ? records.reduce((sum, r) => sum + r.temperature, 0) /
      records.length
    : 0;

const avgRain =
  records.length > 0
    ? records.reduce((sum, r) => sum + r.rainfall, 0) /
      records.length
    : 0;

const avgHumidity =
  records.length > 0
    ? records.reduce((sum, r) => sum + r.humidity, 0) /
      records.length
    : 0;

const totalStations = records.length;
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

  return (
    <div
      style={{
        padding: "20px",
        backgroundColor: "#0f172a",
        color: "white",
        minHeight: "100vh",
      }}
    >
      <h1
        style={{
          textAlign: "center",
          marginBottom: "10px",
        }}
      >
        🌍 ClimateTwin AI
      </h1>

      <h2
        style={{
          textAlign: "center",
          marginBottom: "30px",
        }}
      >
        India Climate Digital Twin
      </h2>

      {loading ? (
        <p>Loading climate data...</p>
      ) : (
        <><div
  style={{
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: "20px",
    marginBottom: "25px",
  }}
>
  <div
    style={{
      background: "#1e293b",
      padding: "20px",
      borderRadius: "12px",
      textAlign: "center",
      boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
    }}
  >
    <h3>🌡 Avg Temperature</h3>
    <h1>{avgTemp.toFixed(1)}°C</h1>
  </div>

  <div
    style={{
      background: "#1e293b",
      padding: "20px",
      borderRadius: "12px",
      textAlign: "center",
      boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
    }}
  >
    <h3>🌧 Avg Rainfall</h3>
    <h1>{avgRain.toFixed(1)} mm</h1>
  </div>

  <div
    style={{
      background: "#1e293b",
      padding: "20px",
      borderRadius: "12px",
      textAlign: "center",
      boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
    }}
  >
    <h3>💧 Avg Humidity</h3>
    <h1>{avgHumidity.toFixed(1)}%</h1>
  </div>

  <div
    style={{
      background: "#1e293b",
      padding: "20px",
      borderRadius: "12px",
      textAlign: "center",
      boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
    }}
  >
    <h3>📡 Climate Stations</h3>
    <h1>{totalStations}</h1>
  </div>
</div>
          <ClimateMap records={records} />

          <div style={{ marginTop: "30px" }}>
            <h2>Climate Records</h2>

            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                marginTop: "15px",
              }}
            >
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Latitude</th>
                  <th>Longitude</th>
                  <th>Temperature</th>
                  <th>Humidity</th>
                  <th>Rainfall</th>
                  <th>Wind Speed</th>
                  <th>Source</th>
                </tr>
              </thead>

              <tbody>
                {records.map((record) => (
                  <tr key={record.id}>
                    <td>{record.id}</td>
                    <td>{record.latitude}</td>
                    <td>{record.longitude}</td>
                    <td>{record.temperature}°C</td>
                    <td>{record.humidity}%</td>
                    <td>{record.rainfall} mm</td>
                    <td>{record.wind_speed} km/h</td>
                    <td>{record.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}