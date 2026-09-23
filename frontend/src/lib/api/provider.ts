import { api } from "./client";

export interface TrafficData {
  value: string;
  unit: string;
  created_at: string;
}

export const providerApi = {
  getTraffic: () => api.get<TrafficData | null>("provider/traffic/"),
};
