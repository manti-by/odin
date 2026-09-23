import { api } from "./client";

export interface DashboardRelay {
  relay_id: string;
  name: string;
  type: string;
  state: string | null;
  mode: string | null;
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

export interface DashboardSensors {
  is_alive: boolean;
  sensors: DashboardSensor[];
}

export const sensorsDashboardApi = {
  getEsp8266: () => api.get<DashboardSensors>("sensors/esp8266/dashboard/"),
  getDs18b20: () => api.get<DashboardSensors>("sensors/ds18b20/dashboard/"),
};
