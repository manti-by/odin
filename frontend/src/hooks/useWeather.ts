import { weatherApi } from "@/lib/api/weather";
import { usePollingData } from "./usePollingData";

export function useWeather() {
  return usePollingData(weatherApi.getCurrent, "Failed to load weather data");
}
