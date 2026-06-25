export interface ClimateRecord {
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
