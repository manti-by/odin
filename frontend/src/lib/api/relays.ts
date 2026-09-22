import { api } from "./client";

export type RelayType = "PUMP" | "SERVO" | "VALVE";
export type RelayTargetState = "ON" | "OFF";

export interface RelayPeriod {
  start_time: string;
  end_time: string;
  target_temp?: number | null;
  target_state?: RelayTargetState | null;
}

export interface RelaySchedule {
  periods: RelayPeriod[];
}

export interface RelayContext {
  schedule?: RelaySchedule;
  [key: string]: unknown;
}

export interface Relay {
  relay_id: string;
  name: string;
  type: RelayType;
  state: string | null;
  mode: string | null;
  context: RelayContext;
  target_state: string;
  created_at: string | null;
}

export interface RelayContextUpdate {
  context: {
    schedule?: RelaySchedule;
  };
}

export const MAX_SCHEDULE_PERIODS = 5;

export const relaysApi = {
  retrieve: (relayId: string) => api.get<Relay>(`relays/${encodeURIComponent(relayId)}/`),
  updateContext: (relayId: string, body: RelayContextUpdate) =>
    api.patch<unknown>(`relays/${encodeURIComponent(relayId)}/`, body),
};
