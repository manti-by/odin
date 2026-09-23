import { api } from "./client";

export interface VoltageData {
  voltage: string;
  created_at: string;
}

export const electricityApi = {
  getVoltage: () => api.get<VoltageData | null>("electricity/voltage/"),
};
