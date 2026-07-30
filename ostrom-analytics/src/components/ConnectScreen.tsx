"use client";

import { FormEvent, useState } from "react";
import type { Environment } from "@/lib/ostrom/types";
import styles from "./ConnectScreen.module.css";

interface Props {
  onDemo: () => void;
  onConnect: (creds: {
    clientId: string;
    clientSecret: string;
    environment: Environment;
  }) => void;
}

export function ConnectScreen({ onDemo, onConnect }: Props) {
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [environment, setEnvironment] = useState<Environment>("production");
  const [showForm, setShowForm] = useState(false);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!clientId.trim() || !clientSecret.trim()) return;
    onConnect({
      clientId: clientId.trim(),
      clientSecret: clientSecret.trim(),
      environment,
    });
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.atmosphere} aria-hidden />
      <div className={styles.content}>
        <p className={styles.brand}>Wattwise</p>
        <h1 className={styles.title}>
          Play with your
          <br />
          Ostrom data
        </h1>
        <p className={styles.lead}>
          Deeper charts, heatmaps, and load-shift estimates than the app gives
          you — powered by the official Ostrom API.
        </p>

        <div className={styles.ctaRow}>
          <button type="button" className={styles.primary} onClick={onDemo}>
            Explore demo data
          </button>
          <button
            type="button"
            className={styles.secondary}
            onClick={() => setShowForm((v) => !v)}
          >
            Connect my account
          </button>
        </div>

        {showForm && (
          <form className={styles.form} onSubmit={submit}>
            <p className={styles.help}>
              Follow the{" "}
              <a
                href="https://docs.ostrom-api.io/docs/getting-started"
                target="_blank"
                rel="noreferrer"
              >
                Ostrom getting started
              </a>{" "}
              guide: sign in at{" "}
              <a
                href="https://developer.ostrom-api.io/"
                target="_blank"
                rel="noreferrer"
              >
                developer.ostrom-api.io
              </a>{" "}
              with your Ostrom app account, create a Production client, then
              paste the credentials below.
            </p>
            <label>
              Client ID
              <input
                value={clientId}
                onChange={(e) => setClientId(e.target.value)}
                autoComplete="off"
                required
              />
            </label>
            <label>
              Client secret
              <input
                type="password"
                value={clientSecret}
                onChange={(e) => setClientSecret(e.target.value)}
                autoComplete="off"
                required
              />
            </label>
            <label>
              Environment
              <select
                value={environment}
                onChange={(e) => setEnvironment(e.target.value as Environment)}
              >
                <option value="production">Production</option>
                <option value="sandbox">Sandbox</option>
              </select>
            </label>
            <button type="submit" className={styles.primary}>
              Load my consumption
            </button>
          </form>
        )}

        <ul className={styles.perks}>
          <li>Hourly & daily consumption with cost overlay</li>
          <li>Week × hour heatmap of usage patterns</li>
          <li>Spot price vs load and shift suggestions</li>
        </ul>
      </div>
    </div>
  );
}
