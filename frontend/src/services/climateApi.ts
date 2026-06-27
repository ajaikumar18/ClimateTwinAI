import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api/v1",
});

export const getClimateRecords = async () => {
  const response = await api.get("/climate");
  return response.data;
};

export const getRegion = async (bbox: string, limit: number = 5000) => {
  const response = await api.get(`/climate/region`, {
    params: { bbox, limit },
  });
  return response.data;
};

export const getTimeSeries = async (lat: number, lon: number, start: string, end: string) => {
  const response = await api.get(`/climate/timeseries`, {
    params: { lat, lon, start, end },
  });
  return response.data;
};

export interface ForecastResponse {
  date: string;
  rainfall: number;
  rainfall_lower: number;
  rainfall_upper: number;
  tmax: number;
  tmax_lower: number;
  tmax_upper: number;
  tmin: number;
  tmin_lower: number;
  tmin_upper: number;
}

export const getForecast = async (lat: number, lon: number): Promise<ForecastResponse[]> => {
  try {
    const [rainRes, tmaxRes, tminRes] = await Promise.all([
      api.post("/predict", { lat, lon, variable: "rainfall" }),
      api.post("/predict", { lat, lon, variable: "tmax" }),
      api.post("/predict", { lat, lon, variable: "tmin" }),
    ]);

    const rainData = rainRes.data.forecast || [];
    const tmaxData = tmaxRes.data.forecast || [];
    const tminData = tminRes.data.forecast || [];

    // Stitch the 3 arrays together by index
    const merged: ForecastResponse[] = rainData.map((day: any, i: number) => {
      const maxDay = tmaxData[i] || {};
      const minDay = tminData[i] || {};
      return {
        date: day.date,
        rainfall: day.predicted_value,
        rainfall_lower: day.lower_bound,
        rainfall_upper: day.upper_bound,
        tmax: maxDay.predicted_value || 0,
        tmax_lower: maxDay.lower_bound || 0,
        tmax_upper: maxDay.upper_bound || 0,
        tmin: minDay.predicted_value || 0,
        tmin_lower: minDay.lower_bound || 0,
        tmin_upper: minDay.upper_bound || 0,
      };
    });
    return merged;
  } catch (error) {
    console.error("Forecast API Error:", error);
    return [];
  }
};

export interface SimulateRequest {
  lat: number;
  lon: number;
  variable: "rainfall" | "tmax" | "tmin";
  temp_delta: number;
  rainfall_multiplier: number;
  horizon_days: number;
}

export interface DataPoint {
  date: string;
  value: number;
}

export interface DeltaPoint {
  date: string;
  difference: number;
  percent_change: number;
}

export interface SimulateResponse {
  baseline: DataPoint[];
  scenario: DataPoint[];
  delta: DeltaPoint[];
  impact_summary: string;
}

export const simulateScenario = async (params: SimulateRequest): Promise<SimulateResponse> => {
  const response = await api.post<SimulateResponse>("/simulate", params);
  return response.data;
};