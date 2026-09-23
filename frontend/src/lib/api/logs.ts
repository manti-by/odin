import { api } from "./client";

export interface ErrorLogEntry {
  asctime: string;
  msg: string;
  name: string;
  levelname: string;
  filename: string;
}

export const logsApi = {
  getErrors: () => api.get<ErrorLogEntry[]>("logs/errors/"),
};
