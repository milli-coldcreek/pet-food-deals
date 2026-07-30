"use client";

import type { LoadShiftInsight, SummaryStats } from "@/lib/analytics";
import styles from "./InsightsPanel.module.css";

interface Props {
  insights: LoadShiftInsight[];
  stats: SummaryStats;
  peakAt: string | null;
  peakKwh: number;
}

export function InsightsPanel({ insights, stats, peakAt, peakKwh }: Props) {
  return (
    <section className={styles.panel}>
      <div className={styles.head}>
        <h2>Insights to play with</h2>
        <p>Pattern-based suggestions from your selected window.</p>
      </div>
      <div className={styles.list}>
        {(stats.variableCostEur != null || stats.fixedCostEur != null) && (
          <article className={styles.item}>
            <h3>Ostrom price breakdown</h3>
            <p>
              Per the{" "}
              <a
                href="https://docs.ostrom-api.io/docs/fetching-prices"
                target="_blank"
                rel="noreferrer"
              >
                Ostrom pricing docs
              </a>
              : variable energy is{" "}
              <code>(grossKwhPrice + grossKwhTaxAndLevies) × kWh</code>
              {stats.variableCostEur != null && (
                <>
                  {" "}
                  →{" "}
                  <strong>
                    {stats.variableCostEur.toLocaleString("de-DE", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}{" "}
                    €
                  </strong>
                </>
              )}
              {stats.monthlyFixedEur != null && stats.fixedCostEur != null && (
                <>
                  . Fixed fees are{" "}
                  <strong>
                    {stats.monthlyFixedEur.toLocaleString("de-DE", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}{" "}
                    €/month
                  </strong>{" "}
                  (base + grid), prorated to{" "}
                  <strong>
                    {stats.fixedCostEur.toLocaleString("de-DE", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}{" "}
                    €
                  </strong>{" "}
                  over {stats.daysCovered} days.
                </>
              )}
            </p>
          </article>
        )}
        {peakAt && (
          <article className={styles.item}>
            <h3>Peak interval</h3>
            <p>
              Highest draw was <strong>{peakKwh.toFixed(3)} kWh</strong> at{" "}
              {peakAt}.
            </p>
          </article>
        )}
        {insights.map((insight) => (
          <article key={insight.title} className={styles.item}>
            <h3>{insight.title}</h3>
            <p>{insight.detail}</p>
            {insight.potentialSavingEur != null && (
              <p className={styles.save}>
                ~{insight.potentialSavingEur.toLocaleString("de-DE", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}{" "}
                € in this window
              </p>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
