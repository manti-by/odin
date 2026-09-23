import { currencyApi } from "@/lib/api/currency";
import { usePollingData } from "./usePollingData";

export function useExchangeRates() {
  return usePollingData(currencyApi.getRates, "Failed to load exchange rates");
}
