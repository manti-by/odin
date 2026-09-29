import { api } from "./client";

export type BoilerMode = "heating" | "mixed" | "off" | "boiling" | "clear_override";

export interface BoilerLiveStatus {
  FlowTempDesired: string;
  HwcTempDesired: string;
  StorageTempDesired: string;
  FlowTemp: string;
  ReturnTemp: string;
  StorageTemp: string;
  ModulationDesired: string;
  Status01: string;
  Status02: string;
}

export interface BoilerStatus {
  mode: BoilerMode | null;
  target_temp: number | null;
  hwc_temp: number | null;
  override_active: boolean;
  override_updated_at: string | null;
  ebusd_alive: boolean;
  next_boil_at: string | null;
  next_clear_at: string | null;
  status: BoilerLiveStatus;
}

export const boilerApi = {
  get: () => api.get<BoilerStatus>("boiler/status/"),
};
