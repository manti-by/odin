import { api } from "./client";

export interface Sensor {
  sensor_id: string;
  name: string;
  type: string;
  context: Record<string, unknown>;
  temp: string;
  humidity: string;
  temp_offset: string;
  humidity_offset: string;
  created_at: string | null;
}

export interface PaginatedSensors {
  count: number;
  next: string | null;
  previous: string | null;
  results: Sensor[];
}

export const sensorsApi = {
  list: (params?: { page?: number }) => {
    const search = new URLSearchParams();
    if (params?.page) {
      search.set("page", String(params.page));
    }
    const query = search.toString();
    return api.get<PaginatedSensors>(`sensors/${query ? `?${query}` : ""}`);
  },
};
