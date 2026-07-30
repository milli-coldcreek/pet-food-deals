"use client";

import type { LoadShiftInsight } from "@/lib/analytics";
import styles from "./InsightsPanel.module.css";

interface Props {
  insights: LoadShiftInsight[];
  peakAt: string | null;
  peakKwh: number;
}

export function InsightsPanel({ insights, peakAt, peakKwh }: Props) {
  return (
    <section className={styles.panel}>
      <div className={styles.head}>
        <h2>Insights to play with</h2>
        <p>Pattern-based suggestions from your selected window.</p>
      </div>
      <div className={styles.list}>
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
