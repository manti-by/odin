import { type BoilerStatus, boilerApi } from "@/lib/api/boiler";
import { useCallback, useEffect, useRef, useState } from "react";

const POLL_INTERVAL = 60_000;

export function useBoilerStatus() {
  const [data, setData] = useState<BoilerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fetchIdRef = useRef(0);

  const fetchData = useCallback(async () => {
    const id = ++fetchIdRef.current;
    setError(null);
    try {
      const result = await boilerApi.get();
      if (id === fetchIdRef.current) {
        setData(result);
      }
    } catch {
      if (id === fetchIdRef.current) {
        setError("Failed to load boiler status");
      }
    } finally {
      if (id === fetchIdRef.current) {
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
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchData]);

  return { data, loading, error, reload };
}
