import { coreApi } from "@/lib/api/core";
import { usePollingData } from "./usePollingData";

export function useSystemdStatus() {
  return usePollingData(coreApi.getSystemdStatus, "Failed to load system status");
}
