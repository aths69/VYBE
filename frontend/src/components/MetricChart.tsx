import { Line, LineChart, ResponsiveContainer, Tooltip, YAxis } from "recharts";

interface Point {
  index: number;
  value: number | null;
}

export function MetricChart({
  title,
  unit,
  data,
  color,
  domain,
}: {
  title: string;
  unit: string;
  data: Point[];
  color: string;
  domain?: [number, number];
}) {
  const latest = [...data].reverse().find((p) => p.value !== null)?.value ?? null;

  return (
    <div className="panel">
      <div className="chart-title">
        {title}
        {latest !== null && (
          <span style={{ float: "right", color: "var(--text)", fontFamily: "var(--font-mono)" }}>
            {latest.toFixed(1)} {unit}
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={90}>
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
          <YAxis hide domain={domain ?? ["auto", "auto"]} />
          <Tooltip
            contentStyle={{
              background: "var(--bg-panel-raised)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              fontSize: 11,
            }}
            labelFormatter={() => ""}
            formatter={(value) => [
              `${typeof value === "number" ? value.toFixed(1) : value} ${unit}`,
              title,
            ]}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.75}
            dot={false}
            isAnimationActive={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
