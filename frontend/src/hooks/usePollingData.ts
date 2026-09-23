import { useCallback, useEffect, useRef, useState } from "react";

const POLL_INTERVAL = 300_000;

export interface PollingResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

export function usePollingData<T>(fetcher: () => Promise<T>, errorMessage: string): PollingResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fetchIdRef = useRef(0);
  const fetcherRef = useRef(fetcher);

  useEffect(() => {
    fetcherRef.current = fetcher;
  }, [fetcher]);

  const fetchData = useCallback(async () => {
    const id = ++fetchIdRef.current;
    setError(null);
    try {
      const result = await fetcherRef.current();
      if (id === fetchIdRef.current) {
        setData(result);
      }
    } catch {
      if (id === fetchIdRef.current) {
        setError(errorMessage);
      }
    } finally {
      if (id === fetchIdRef.current) {
        setLoading(false);
      }
    }
  }, [errorMessage]);

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
