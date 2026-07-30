"use client";

import type { HeatCell } from "@/lib/analytics";
import styles from "./HeatmapChart.module.css";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

interface Props {
  data: HeatCell[];
}

export function HeatmapChart({ data }: Props) {
  const max = Math.max(...data.map((c) => c.avgKwh), 0.001);
  const lookup = new Map(data.map((c) => [`${c.day}-${c.hour}`, c]));

  return (
    <div className={styles.wrap}>
      <div className={styles.scroll}>
        <div className={styles.grid} role="img" aria-label="Consumption heatmap">
          <div className={styles.corner} />
          {Array.from({ length: 24 }, (_, h) => (
            <div key={`h-${h}`} className={styles.hourLabel}>
              {h % 3 === 0 ? String(h).padStart(2, "0") : ""}
            </div>
          ))}
          {DAYS.map((day, dayIdx) => (
            <div key={day} className={styles.dayContents}>
              <div className={styles.dayLabel}>{day}</div>
              {Array.from({ length: 24 }, (_, hour) => {
                const cell = lookup.get(`${dayIdx}-${hour}`);
                const intensity = cell ? cell.avgKwh / max : 0;
                return (
                  <div
                    key={`${day}-${hour}`}
                    className={styles.cell}
                    title={`${day} ${String(hour).padStart(2, "0")}:00 — ${(cell?.avgKwh ?? 0).toFixed(3)} kWh`}
                    style={{
                      background: `color-mix(in srgb, var(--ink) ${Math.round(intensity * 92)}%, rgba(11,79,74,0.06))`,
                    }}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>
      <div className={styles.legend}>
        <span>Low</span>
        <div className={styles.ramp} />
        <span>High</span>
      </div>
    </div>
  );
}
