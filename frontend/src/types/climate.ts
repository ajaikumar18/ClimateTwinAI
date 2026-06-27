export interface ClimateRecord {
  id: number;
  latitude: number;
  longitude: number;
  temperature?: number | null;
  temperature_min?: number | null;
  temperature_max?: number | null;
  humidity?: number | null;
  rainfall?: number | null;
  wind_speed?: number | null;
  source: string;
  timestamp: string;
}
