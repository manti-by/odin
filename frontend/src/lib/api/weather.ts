import { api } from "./client";

export interface WeatherData {
  temp: string | null;
  temp_display: string;
  temp_min: string | null;
  temp_min_display: string;
  temp_max: string | null;
  temp_max_display: string;
  pressure: number | null;
  humidity: string | null;
  wind: {
    direction: number | null;
    speed: string | null;
    gusts: string | null;
  };
  attributes: {
    fog: boolean;
    snow: boolean;
    thunderstorm: boolean;
    black_ice: boolean;
  };
  has_attrs: boolean;
  period: string;
  synced_at: string;
  provider: string;
}

export const weatherApi = {
  getCurrent: () => api.get<WeatherData | null>("weather/current/"),
};
