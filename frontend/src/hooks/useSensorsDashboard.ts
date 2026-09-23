import { sensorsDashboardApi } from "@/lib/api/sensors-dashboard";
import { usePollingData } from "./usePollingData";

export function useEsp8266Dashboard() {
  return usePollingData(sensorsDashboardApi.getEsp8266, "Failed to load sensors data");
}

export function useDs18B20Dashboard() {
  return usePollingData(sensorsDashboardApi.getDs18b20, "Failed to load sensors data");
}
