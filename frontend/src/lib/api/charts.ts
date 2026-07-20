import { api } from "./client";

export type SensorType = "DS18B20" | "ESP8266";

export interface SensorSeries {
  sensor_id: string;
  name: string;
  data: (number | null)[];
}

export interface ChartData {
  timestamps: string[];
  sensors: SensorSeries[];
}

export interface ChartOptions {
  y_min: number;
  y_max: number;
  y_title: string;
  x_title: string;
  time_unit: string;
  time_tooltip_format: string;
}

interface ChartQuery {
  start?: string;
  end?: string;
}

function buildSearch(params?: ChartQuery): string {
  const search = new URLSearchParams();
  if (params?.start) {
    search.set("start", params.start);
  }
  if (params?.end) {
    search.set("end", params.end);
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

function sensorEndpoint(type: SensorType): string {
  return `sensors/${type.toLowerCase()}/`;
}

export const chartsApi = {
  getSensorData: (type: SensorType, params?: ChartQuery) => {
    const query = buildSearch(params);
    return api.get<ChartData>(`${sensorEndpoint(type)}${query}`);
  },

  getChartOptions: (type: SensorType) => {
    return api.get<ChartOptions>(`sensors/chart-options/?type=${type}`);
  },
};
