"use client";

import styles from "./RangeControls.module.css";

type Preset = "7d" | "14d" | "30d" | "90d";

interface Props {
  preset: Preset;
  onPreset: (p: Preset) => void;
  view: "hour" | "day";
  onView: (v: "hour" | "day") => void;
  loading: boolean;
  label: string;
}

const PRESETS: { id: Preset; label: string }[] = [
  { id: "7d", label: "7 days" },
  { id: "14d", label: "14 days" },
  { id: "30d", label: "30 days" },
  { id: "90d", label: "90 days" },
];

export function RangeControls({
  preset,
  onPreset,
  view,
  onView,
  loading,
  label,
}: Props) {
  return (
    <div className={styles.bar}>
      <div className={styles.left}>
        <div className={styles.seg} role="group" aria-label="Date range">
          {PRESETS.map((p) => (
            <button
              key={p.id}
              type="button"
              className={preset === p.id ? styles.active : undefined}
              onClick={() => onPreset(p.id)}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className={styles.seg} role="group" aria-label="Chart resolution">
          <button
            type="button"
            className={view === "hour" ? styles.active : undefined}
            onClick={() => onView("hour")}
          >
            Hour
          </button>
          <button
            type="button"
            className={view === "day" ? styles.active : undefined}
            onClick={() => onView("day")}
          >
            Day
          </button>
        </div>
      </div>
      <p className={styles.meta}>
        {loading ? "Loading…" : label}
      </p>
    </div>
  );
}
