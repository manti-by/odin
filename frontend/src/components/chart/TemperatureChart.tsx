import type { ChartData, ChartOptions } from "@/lib/api/charts";
import { format } from "date-fns";
import { useMemo } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const PALETTE = [
  "rgba(255, 99, 132, 1)",
  "rgba(54, 162, 235, 1)",
  "rgba(75, 192, 192, 1)",
  "rgba(153, 102, 255, 1)",
  "rgba(255, 159, 64, 1)",
  "rgba(199, 199, 199, 1)",
  "rgba(83, 102, 255, 1)",
] as const;

interface TemperatureChartProps {
  data: ChartData | null;
  options: ChartOptions | null;
}

// Moment.js → date-fns token mapping.
// Single-pass tokenizer walks left-to-right matching the longest known key,
// so no output is ever re-scanned (no cascading).
const MOMENT_TO_DATEFNS: Record<string, string> = {
  YYYY: "yyyy",
  MMMM: "MMMM",
  MMM: "MMM",
  DD: "dd",
  D: "d",
  dddd: "EEEE",
  ddd: "EEE",
  d: "i",
  LLLL: "EEEE, MMMM d, yyyy h:mm a",
  LLL: "MMMM d, yyyy h:mm a",
  LL: "MMMM d, yyyy",
  L: "MM/dd/yyyy",
  llll: "MMM d, yyyy h:mm a",
  lll: "MMM d, yyyy h:mm",
  ll: "MMM d",
  LTS: "h:mm:ss a",
  LT: "h:mm a",
  YY: "yy",
  HH: "HH",
  hh: "hh",
  mm: "mm",
  ss: "ss",
  a: "a",
  A: "a",
};

const TOKEN_KEYS = Object.keys(MOMENT_TO_DATEFNS).sort((a, b) => b.length - a.length);

function momentToDateFns(fmt: string): string {
  let result = "";
  let i = 0;
  while (i < fmt.length) {
    // Moment literal escape: [...] → date-fns single-quoted literal: '...'
    if (fmt[i] === "[") {
      const end = fmt.indexOf("]", i + 1);
      const inner = end === -1 ? fmt.slice(i + 1) : fmt.slice(i + 1, end);
      result += `'${inner.replace(/'/g, "''")}'`;
      i += end === -1 ? fmt.length - i : end - i + 1;
      continue;
    }
    let matched = false;
    for (const key of TOKEN_KEYS) {
      if (fmt.startsWith(key, i)) {
        result += MOMENT_TO_DATEFNS[key];
        i += key.length;
        matched = true;
        break;
      }
    }
    if (!matched) {
      result += fmt[i];
      i++;
    }
  }
  return result;
}

function buildPoints(data: ChartData) {
  const { timestamps, sensors } = data;
  const ids = sensors.map((s) => s.sensor_id);

  return timestamps
    .map((iso, i) => {
      const time = new Date(iso).getTime();
      if (!Number.isFinite(time)) {
        return null;
      }
      const point: Record<string, number | null> = { time };
      for (let s = 0; s < sensors.length; s++) {
        point[ids[s]] = i < sensors[s].data.length ? sensors[s].data[i] : null;
      }
      return point;
    })
    .filter((p): p is Record<string, number | null> => p !== null);
}

const DAY_MS = 24 * 60 * 60 * 1000;

export function TemperatureChart({ data, options }: TemperatureChartProps) {
  const points = useMemo(() => (data ? buildPoints(data) : []), [data]);
  const sensors = data?.sensors ?? [];
  const ids = sensors.map((s) => s.sensor_id);
  const names = sensors.map((s) => s.name || s.sensor_id);

  const yMin = options?.y_min ?? 20;
  const yMax = options?.y_max ?? 45;
  const yTitle = options?.y_title ?? "Temperature °C";
  const xTitle = options?.x_title ?? "Time";
  const tooltipFormat = options?.time_tooltip_format ? momentToDateFns(options.time_tooltip_format) : "MMM d HH:mm";

  // Ticks show only HH:mm for short ranges; once the selected span exceeds a
  // day, "HH:mm" alone is ambiguous across multiple days, so include the date.
  const spanMs = points.length > 1 ? Number(points[points.length - 1].time) - Number(points[0].time) : 0;
  const tickFormat = spanMs > DAY_MS ? "MMM d HH:mm" : "HH:mm";

  if (!data || points.length === 0) {
    return <div className="placeholder">No chart data available.</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={480}>
      <LineChart data={points} margin={{ top: 16, right: 16, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
        <XAxis
          dataKey="time"
          type="number"
          scale="time"
          domain={["dataMin", "dataMax"]}
          tickFormatter={(ts: number) => format(new Date(ts), tickFormat)}
          stroke="var(--color-text-secondary)"
          label={{ value: xTitle, position: "insideBottomRight", offset: -4, fill: "var(--color-text-secondary)" }}
        />
        <YAxis
          domain={[yMin, yMax]}
          tickFormatter={(v: number) => `${v}°`}
          stroke="var(--color-text-secondary)"
          label={{
            value: yTitle,
            angle: -90,
            position: "insideLeft",
            fill: "var(--color-text-secondary)",
            style: { textAnchor: "middle" },
          }}
        />
        <Tooltip
          labelFormatter={(label) => {
            const ts = typeof label === "number" ? label : Number(label);
            return Number.isFinite(ts) ? format(new Date(ts), tooltipFormat) : "";
          }}
          formatter={(value) => {
            const v = typeof value === "number" ? value : null;
            return v !== null ? `${v.toFixed(1)}°C` : "—";
          }}
          contentStyle={{
            background: "var(--color-surface-2)",
            border: "1px solid var(--color-border)",
            borderRadius: 6,
            color: "var(--color-text-primary)",
          }}
        />
        <Legend
          wrapperStyle={{ color: "var(--color-text-secondary)" }}
          formatter={(value: string) => <span style={{ color: "var(--color-text-secondary)" }}>{value}</span>}
        />
        {ids.map((id, i) => (
          <Line
            key={id}
            dataKey={id}
            name={names[i]}
            type="monotone"
            stroke={PALETTE[i % PALETTE.length]}
            strokeWidth={2}
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
