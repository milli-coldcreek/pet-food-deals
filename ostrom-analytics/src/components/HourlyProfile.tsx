"use client";

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HourBucket } from "@/lib/analytics";
import styles from "./charts.module.css";

interface Props {
  data: HourBucket[];
}

export function HourlyProfile({ data }: Props) {
  const chartData = data.map((d) => ({
    ...d,
    label: `${String(d.hour).padStart(2, "0")}:00`,
  }));

  return (
    <div className={styles.chart}>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="rgba(11,79,74,0.08)" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: "#5a6b66", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            interval={2}
          />
          <YAxis
            yAxisId="kwh"
            tick={{ fill: "#5a6b66", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={40}
          />
          <YAxis
            yAxisId="price"
            orientation="right"
            tick={{ fill: "#5a6b66", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={40}
          />
          <Tooltip
            contentStyle={{
              background: "#0B4F4A",
              border: "none",
              borderRadius: 10,
              color: "#F4F7F1",
              fontSize: 12,
            }}
            formatter={(value, name) => {
              const n = typeof value === "number" ? value : Number(value);
              if (name === "avgKwh") return [`${n.toFixed(3)} kWh`, "Avg use"];
              if (name === "avgPriceCt")
                return [`${n?.toFixed?.(1) ?? "—"} ct`, "Avg price"];
              return [String(value), String(name)];
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 12 }}
            formatter={(v) => (v === "avgKwh" ? "Avg use" : "Avg price")}
          />
          <Bar
            yAxisId="kwh"
            dataKey="avgKwh"
            fill="#0B4F4A"
            radius={[4, 4, 0, 0]}
            name="avgKwh"
            maxBarSize={18}
          />
          <Line
            yAxisId="price"
            type="monotone"
            dataKey="avgPriceCt"
            stroke="#C4A035"
            strokeWidth={2}
            dot={false}
            name="avgPriceCt"
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
