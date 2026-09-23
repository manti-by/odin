import { api } from "./client";

export interface ExchangeRate {
  currency: string;
  rate: string;
  rate_per_unit: string;
  scale: number;
  date: string;
}

export interface ExchangeRates {
  rates: ExchangeRate[];
  trends: Record<string, number>;
}

export const currencyApi = {
  getRates: () => api.get<ExchangeRates>("currency/rates/"),
};
