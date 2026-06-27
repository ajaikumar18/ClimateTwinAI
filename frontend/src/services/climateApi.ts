import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api/v1",
});

export const getClimateRecords = async () => {
  const response = await api.get("/climate");
  return response.data;
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