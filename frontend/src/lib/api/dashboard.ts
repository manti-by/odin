import { api } from "./client";

export interface DashboardRelay {
  relay_id: string;
  name: string;
  type: string;
  state: string;
  is_on: boolean;
}

export interface LinkedSensor {
  sensor_id: string;
  name: string;
  temp: string | null;
}

export interface DashboardSensor {
  sensor_id: string;
  name: string;
  type: string;
  context: Record<string, unknown>;
  temp: string | null;
  humidity: string | null;
  temp_offset: string | null;
  humidity_offset: string | null;
  created_at: string;
  relay: DashboardRelay | null;
  linked_sensor: LinkedSensor | null;
  is_alive: boolean;
}

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

export interface ExchangeRate {
  currency: string;
  rate: string;
  rate_per_unit: string;
  scale: number;
  date: string;
}

export interface TrafficData {
  value: string;
  unit: string;
  created_at: string;
}

export interface VoltageData {
  voltage: string;
  created_at: string;
}

export interface ErrorLogEntry {
  asctime: string;
  msg: string;
  name: string;
  levelname: string;
  filename: string;
}

export interface DashboardData {
  weather: WeatherData | null;
  sensors: {
    esp8266: DashboardSensor[];
    ds18b20: DashboardSensor[];
  };
  home_sensors_is_alive: boolean;
  boiler_sensors_is_alive: boolean;
  error_logs: ErrorLogEntry[];
  voltage: VoltageData | null;
  exchange_rates: ExchangeRate[];
  exchange_rates_trends: Record<string, number>;
  systemd_status: Record<string, { status?: string; error?: string }>;
  traffic: TrafficData | null;
}

export const dashboardApi = {
  get: () => api.get<DashboardData>("core/dashboard/"),
};
