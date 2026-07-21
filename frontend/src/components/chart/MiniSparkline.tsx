import { Line, LineChart, ResponsiveContainer, Tooltip } from "recharts";

const DEFAULT_COLOR = "var(--color-accent)";

interface SparklinePoint {
  timestamp: string;
  value: number | null;
}

interface MiniSparklineProps {
  points: SparklinePoint[];
  color?: string;
  height?: number;
}

export function MiniSparkline({ points, color = DEFAULT_COLOR, height = 48 }: MiniSparklineProps) {
  const data = points.map((p) => ({ v: p.value }));

  if (data.length === 0) {
    return (
      <div style={{ height }} className="placeholder">
        —
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
        <Line
          dataKey="v"
          type="monotone"
          stroke={color}
          strokeWidth={1.5}
          dot={false}
          connectNulls={false}
          isAnimationActive={false}
        />
        <Tooltip
          contentStyle={{
            background: "var(--color-surface-2)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            color: "var(--color-text-primary)",
            fontSize: 12,
          }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
