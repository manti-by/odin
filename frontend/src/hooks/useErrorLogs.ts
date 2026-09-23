import { logsApi } from "@/lib/api/logs";
import { usePollingData } from "./usePollingData";

export function useErrorLogs() {
  return usePollingData(logsApi.getErrors, "Failed to load error logs");
}
