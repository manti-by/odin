const DEFAULT_API_BASE_URL = "/api/v1/";

function normalizeBase(value: string | undefined): string {
  if (!value) {
    return DEFAULT_API_BASE_URL;
  }
  return value.endsWith("/") ? value : `${value}/`;
}

export const config = {
  apiBaseUrl: normalizeBase(import.meta.env.VITE_API_BASE_URL),
  adminUrl: "/admin/",
} as const;
