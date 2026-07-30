"use client";

import type { SummaryStats } from "@/lib/analytics";
import styles from "./OverviewStrip.module.css";

interface Props {
  stats: SummaryStats;
}

function euros(n: number) {
  return `${n.toLocaleString("de-DE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} €`;
}

export function OverviewStrip({ stats }: Props) {
  const items = [
    {
      label: "Total use",
      value: `${stats.totalKwh.toLocaleString("de-DE")} kWh`,
      hint: null as string | null,
    },
    {
      label: "Est. total cost",
      value: stats.totalCostEur == null ? "—" : euros(stats.totalCostEur),
      hint:
        stats.variableCostEur != null && stats.fixedCostEur != null
          ? `${euros(stats.variableCostEur)} energy + ${euros(stats.fixedCostEur)} fixed`
          : null,
    },
    {
      label: "Avg / day",
      value: `${stats.avgDailyKwh.toLocaleString("de-DE")} kWh`,
      hint: null,
    },
    {
      label: "Avg price",
      value:
        stats.avgPriceCt == null
          ? "—"
          : `${stats.avgPriceCt.toLocaleString("de-DE")} ct/kWh`,
      hint: null,
    },
  ];

  return (
    <section className={styles.strip} aria-label="Summary">
      {items.map((item) => (
        <div key={item.label} className={styles.item}>
          <p className={styles.label}>{item.label}</p>
          <p className={styles.value}>{item.value}</p>
          {item.hint && <p className={styles.hint}>{item.hint}</p>}
        </div>
      ))}
    </section>
  );
}
