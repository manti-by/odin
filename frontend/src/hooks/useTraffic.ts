import { providerApi } from "@/lib/api/provider";
import { usePollingData } from "./usePollingData";

export function useTraffic() {
  return usePollingData(providerApi.getTraffic, "Failed to load traffic data");
}
