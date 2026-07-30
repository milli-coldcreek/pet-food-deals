"use client";

import { format, parseISO } from "date-fns";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { EnrichedPoint } from "@/lib/ostrom/types";
import styles from "./charts.module.css";

interface Props {
  data: EnrichedPoint[];
  view: "hour" | "day";
}

export function ConsumptionChart({ data, view }: Props) {
  const chartData = data.map((d) => ({
    ...d,
    label:
      view === "hour"
        ? format(parseISO(d.date), "d MMM HH:mm")
        : format(parseISO(d.date), "d MMM"),
  }));

  return (
    <div className={styles.chart}>
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="kwhFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0B4F4A" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#0B4F4A" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(11,79,74,0.08)" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: "#5a6b66", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            minTickGap={view === "hour" ? 40 : 24}
          />
          <YAxis
            yAxisId="kwh"
            tick={{ fill: "#5a6b66", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={42}
            label={{
              value: "kWh",
              angle: -90,
              position: "insideLeft",
              fill: "#5a6b66",
              fontSize: 11,
            }}
          />
          <YAxis
            yAxisId="price"
            orientation="right"
            tick={{ fill: "#5a6b66", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={48}
            label={{
              value: "ct",
              angle: 90,
              position: "insideRight",
              fill: "#5a6b66",
              fontSize: 11,
            }}
          />
          <Tooltip
            contentStyle={{
              background: "#0B4F4A",
              border: "none",
              borderRadius: 10,
              color: "#F4F7F1",
              fontSize: 12,
            }}
            labelStyle={{ color: "#C8F542", fontWeight: 600 }}
            formatter={(value, name) => {
              const n = typeof value === "number" ? value : Number(value);
              if (name === "kWh") return [`${n.toFixed(3)} kWh`, "Consumption"];
              if (name === "priceCt") return [`${n?.toFixed?.(1) ?? "—"} ct`, "Price"];
              if (name === "costEur") return [`${n?.toFixed?.(3) ?? "—"} €`, "Cost"];
              return [String(value), String(name)];
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 12, color: "#5a6b66" }}
            formatter={(value) =>
              value === "kWh" ? "Consumption" : value === "priceCt" ? "Price" : value
            }
          />
          <Area
            yAxisId="kwh"
            type="monotone"
            dataKey="kWh"
            stroke="#0B4F4A"
            strokeWidth={2}
            fill="url(#kwhFill)"
            name="kWh"
          />
          <Line
            yAxisId="price"
            type="monotone"
            dataKey="priceCt"
            stroke="#C4A035"
            strokeWidth={1.75}
            dot={false}
            name="priceCt"
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
