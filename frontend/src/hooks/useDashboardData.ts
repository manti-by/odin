import { type DashboardData, dashboardApi } from "@/lib/api/dashboard";
import { useCallback, useEffect, useRef, useState } from "react";

const POLL_INTERVAL = 300_000;

export function useDashboardData() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fetchIdRef = useRef(0);
  const isMountedRef = useRef(true);

  const fetchData = useCallback(async () => {
    const id = ++fetchIdRef.current;
    setError(null);
    try {
      const result = await dashboardApi.get();
      if (id === fetchIdRef.current && isMountedRef.current) {
        setData(result);
      }
    } catch {
      if (id === fetchIdRef.current && isMountedRef.current) {
        setError("Failed to load dashboard data");
      }
    } finally {
      if (id === fetchIdRef.current && isMountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  const reload = useCallback(() => {
    setLoading(true);
    void fetchData();
  }, [fetchData]);

  useEffect(() => {
    void fetchData();
    intervalRef.current = setInterval(() => {
      void fetchData();
    }, POLL_INTERVAL);
    return () => {
      isMountedRef.current = false;
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchData]);

  return { data, loading, error, reload };
}
