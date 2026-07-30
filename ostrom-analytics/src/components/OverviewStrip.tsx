"use client";

import type { SummaryStats } from "@/lib/analytics";
import styles from "./OverviewStrip.module.css";

interface Props {
  stats: SummaryStats;
}

export function OverviewStrip({ stats }: Props) {
  const items = [
    {
      label: "Total use",
      value: `${stats.totalKwh.toLocaleString("de-DE")} kWh`,
    },
    {
      label: "Est. energy cost",
      value:
        stats.totalCostEur == null
          ? "—"
          : `${stats.totalCostEur.toLocaleString("de-DE", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })} €`,
    },
    {
      label: "Avg / day",
      value: `${stats.avgDailyKwh.toLocaleString("de-DE")} kWh`,
    },
    {
      label: "Avg price",
      value:
        stats.avgPriceCt == null
          ? "—"
          : `${stats.avgPriceCt.toLocaleString("de-DE")} ct/kWh`,
    },
  ];

  return (
    <section className={styles.strip} aria-label="Summary">
      {items.map((item) => (
        <div key={item.label} className={styles.item}>
          <p className={styles.label}>{item.label}</p>
          <p className={styles.value}>{item.value}</p>
        </div>
      ))}
    </section>
  );
}
