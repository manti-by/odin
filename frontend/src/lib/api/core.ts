import { api } from "./client";

export type SystemdStatus = Record<string, { status?: string; error?: string }>;

export const coreApi = {
  getSystemdStatus: () => api.get<SystemdStatus>("core/systemd/"),
};
