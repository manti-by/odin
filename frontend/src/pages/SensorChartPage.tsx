import { TemperatureChart } from "@/components/chart/TemperatureChart";
import { Form } from "@/components/form/Form";
import { SubmitButton } from "@/components/form/SubmitButton";
import { TextField } from "@/components/form/TextField";
import type { ChartData, ChartOptions, SensorType } from "@/lib/api/charts";
import { chartsApi } from "@/lib/api/charts";
import { ApiError } from "@/lib/api/client";
import { datetimeLocalToIso, toLocalDatetimeValue } from "@/lib/datetime";
import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

type SensorLocation = "home" | "boiler";

const LOCATION_MAP: Record<SensorLocation, SensorType> = {
  home: "ESP8266",
  boiler: "DS18B20",
};

const TITLES: Record<SensorLocation, string> = {
  home: "Home temperature",
  boiler: "Boiler temperature",
};

function isSensorLocation(value: string | undefined): value is SensorLocation {
  return value === "home" || value === "boiler";
}

export function SensorChartPage() {
  const { location } = useParams();
  const sensorLocation = isSensorLocation(location) ? location : "home";
  const title = TITLES[sensorLocation];
  const sensorType = LOCATION_MAP[sensorLocation];

  const now = new Date();
  const past = new Date(now.getTime() - 24 * 60 * 60 * 1000);

  const [start, setStart] = useState(() => toLocalDatetimeValue(past));
  const [end, setEnd] = useState(() => toLocalDatetimeValue(now));
  const [data, setData] = useState<ChartData | null>(null);
  const [options, setOptions] = useState<ChartOptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Monotonic counter to discard stale async responses
  const fetchIdRef = useRef(0);

  const load = useCallback(
    async (loadStart: string, loadEnd: string) => {
      if (!loadStart || !loadEnd) {
        setLoading(false);
        return;
      }

      const id = ++fetchIdRef.current;
      setLoading(true);
      setError(null);

      try {
        const [chartData, chartOptions] = await Promise.all([
          chartsApi.getSensorData(sensorType, {
            start: datetimeLocalToIso(loadStart),
            end: datetimeLocalToIso(loadEnd),
          }),
          chartsApi.getChartOptions(sensorType),
        ]);

        if (id !== fetchIdRef.current) {
          return; // stale response
        }

        setData(chartData);
        setOptions(chartOptions);
      } catch (err) {
        if (id !== fetchIdRef.current) {
          return; // stale response
        }
        setError(err instanceof ApiError ? err.message : "Failed to load chart data");
      } finally {
        if (id === fetchIdRef.current) {
          setLoading(false);
        }
      }
    },
    [sensorType],
  );

  // Initial fetch on mount (not on every start/end change)
  // biome-ignore lint/correctness/useExhaustiveDependencies: only re-run when sensorType changes
  useEffect(() => {
    void load(start, end);
  }, [sensorType]);

  const handleSubmit = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      void load(start, end);
    },
    [load, start, end],
  );

  return (
    <section>
      <h2>{title}</h2>

      <Form onSubmit={handleSubmit}>
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "flex-end" }}>
          <TextField
            id="dateFrom"
            label="From"
            type="datetime-local"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            required
          />
          <TextField
            id="dateTo"
            label="To"
            type="datetime-local"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            required
          />
          <SubmitButton label="Apply" />
        </div>
      </Form>

      {loading && <p>Loading chart data…</p>}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!loading && !error && <TemperatureChart data={data} options={options} />}
    </section>
  );
}
