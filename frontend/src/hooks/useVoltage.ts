import { electricityApi } from "@/lib/api/electricity";
import { usePollingData } from "./usePollingData";

export function useVoltage() {
  return usePollingData(electricityApi.getVoltage, "Failed to load voltage data");
}
